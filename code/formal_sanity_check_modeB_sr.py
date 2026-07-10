#!/usr/bin/env python3
"""Bounded safety sanity check for ShieldLink Mode B-SR.

This explicit-state model checks receiver-side selective-retry safety. It is a
bounded sanity check, not a liveness proof, timing proof, or cryptographic proof.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from typing import Iterable, Tuple

M = 4
SEQ_MOD = 8
MAX_DEPTH = 10

@dataclass(frozen=True)
class State:
    next_expected: int
    epoch_start: int
    active: bool
    received: int
    crc_fail: int
    acked_epochs: int

def bit(i: int) -> int:
    return 1 << i

def popcount(x: int) -> int:
    return bin(x).count("1")

def in_epoch(seq: int, start: int) -> Tuple[bool, int]:
    delta = (seq - start) % SEQ_MOD
    return delta < M, delta

def start_epoch(s: State) -> State:
    if s.active:
        return s
    return State(s.next_expected, s.next_expected, True, 0, 0, s.acked_epochs)

def rx_frame(s: State, seq: int, crc_ok: bool) -> State:
    s = start_epoch(s)
    ok, idx = in_epoch(seq, s.epoch_start)
    if not ok:
        return s
    received = s.received
    crc_fail = s.crc_fail
    if crc_ok:
        received |= bit(idx)
        crc_fail &= ~bit(idx)
    else:
        crc_fail |= bit(idx)
    return State(s.next_expected, s.epoch_start, True, received, crc_fail, s.acked_epochs)

def tag_event(s: State, aead_ok: bool) -> Tuple[State, bool, bool, int]:
    s = start_epoch(s)
    complete = s.received == (1 << M) - 1
    clean = s.crc_fail == 0
    if complete and clean and aead_ok:
        ns = State((s.epoch_start + M) % SEQ_MOD, s.epoch_start, False, 0, 0, s.acked_epochs + 1)
        return ns, True, False, 0
    if complete and clean and not aead_ok:
        ns = State(s.next_expected, s.epoch_start, False, 0, 0, s.acked_epochs)
        return ns, False, True, 0
    repair = ((~s.received) | s.crc_fail) & ((1 << M) - 1)
    return s, False, False, repair

def successors(s: State) -> Iterable[Tuple[str, State, bool, bool, int]]:
    base = s.next_expected if not s.active else s.epoch_start
    for i in range(M):
        seq = (base + i) % SEQ_MOD
        for crc_ok in (False, True):
            ns = rx_frame(s, seq, crc_ok)
            yield f"rx(seq={seq},crc_ok={crc_ok})", ns, False, False, 0
    for aead_ok in (False, True):
        ns, ack, sec, nak = tag_event(s, aead_ok)
        yield f"tag(aead_ok={aead_ok})", ns, ack, sec, nak

def check() -> None:
    init = State(0, 0, False, 0, 0, 0)
    q = deque([(init, 0)])
    seen = {init}
    transitions = acks = naks = security_drops = max_received_bits = 0

    while q:
        s, d = q.popleft()
        max_received_bits = max(max_received_bits, popcount(s.received))
        if d >= MAX_DEPTH:
            continue
        for action, ns, ack, sec, nak in successors(s):
            transitions += 1
            if ack:
                acks += 1
                assert s.received == (1 << M) - 1, ("ACK before complete epoch", s, action)
                assert s.crc_fail == 0, ("ACK with CRC-failed slot", s, action)
                assert ns.next_expected == (s.epoch_start + M) % SEQ_MOD, ("ACK without correct next_expected advance", s, ns, action)
            else:
                assert ns.next_expected == s.next_expected or sec, ("next_expected advanced without ACK", s, ns, action)
            if sec:
                security_drops += 1
                assert nak == 0, ("security drop also emitted NAK", s, action)
            if nak:
                naks += 1
                expected = ((~s.received) | s.crc_fail) & ((1 << M) - 1)
                assert nak == expected, ("wrong repair bitmap", s, action, nak, expected)
                assert nak != 0, ("empty repair bitmap", s, action)
            if ns not in seen:
                seen.add(ns)
                q.append((ns, d + 1))

    print("ShieldLink Mode B-SR bounded safety sanity check")
    print(f"M={M}, SEQ_MOD={SEQ_MOD}, MAX_DEPTH={MAX_DEPTH}")
    print(f"states_explored={len(seen)}")
    print(f"transitions_explored={transitions}")
    print(f"ack_events_checked={acks}")
    print(f"nak_events_checked={naks}")
    print(f"security_drop_events_checked={security_drops}")
    print(f"max_received_slots_in_state={max_received_bits}")
    print("result=PASS")

if __name__ == "__main__":
    check()
