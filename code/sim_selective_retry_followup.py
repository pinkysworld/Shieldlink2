#!/usr/bin/env python3
"""Preliminary ShieldLink-SR simulator.

This model is intentionally compact. It compares reliability-only CRC+ARQ,
ShieldLink Mode A, Mode B flush-all, and Mode B selective retry under a
Gilbert-Elliott burst-error model. It is for follow-up paper exploration, not a
full CXL/UCIe traffic model.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Params:
    frames: int = 20000
    payload_bytes: int = 256
    link_bytes_per_cycle: int = 8
    mode_a_bytes: int = 288
    crc_arq_bytes: int = 268
    mode_b_frame_bytes: int = 276
    mode_b_epoch: int = 32
    crc_delay: int = 1
    aead_delay: int = 8
    prop_delay: int = 2
    p_good: float = 1e-6
    p_bad: float = 0.1
    beta: float = 0.2


def ci95(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return 1.96 * statistics.stdev(values) / math.sqrt(len(values))


def ge_corruptions(n: int, pi_b: float, p_good: float, p_bad: float, beta: float, rng: random.Random) -> list[bool]:
    if pi_b <= 0:
        alpha = 0.0
    elif pi_b >= 1:
        alpha = 1.0
    else:
        alpha = (pi_b * beta) / (1.0 - pi_b)

    bad = rng.random() < pi_b
    out: list[bool] = []
    for _ in range(n):
        p = p_bad if bad else p_good
        out.append(rng.random() < p)
        if bad:
            if rng.random() < beta:
                bad = False
        else:
            if rng.random() < alpha:
                bad = True
    return out


def simulate_per_frame(corrupt: list[bool], bytes_per_frame: int, params: Params, verify_delay: int) -> tuple[float, float]:
    t_tx = math.ceil(bytes_per_frame / params.link_bytes_per_cycle)
    delivered = 0
    cycles = 0
    latencies: list[int] = []
    for bad in corrupt:
        attempts = 1 + int(bad)
        cycles += attempts * t_tx + params.prop_delay + params.crc_delay + verify_delay
        delivered += 1
        latencies.append(t_tx + params.prop_delay + params.crc_delay + verify_delay if not bad else 2 * t_tx + params.prop_delay + params.crc_delay + verify_delay)
    goodput = delivered * params.payload_bytes / (cycles * params.link_bytes_per_cycle)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
    return goodput, float(p99)


def simulate_mode_b_flush(corrupt: list[bool], params: Params) -> tuple[float, float]:
    m = params.mode_b_epoch
    t_frame = math.ceil(params.mode_b_frame_bytes / params.link_bytes_per_cycle)
    delivered = 0
    cycles = 0
    latencies: list[int] = []
    for i in range(0, len(corrupt), m):
        epoch = corrupt[i:i + m]
        if len(epoch) < m:
            break
        rounds = 1 + int(any(epoch))
        epoch_cycles = rounds * m * t_frame + params.prop_delay + params.crc_delay + params.aead_delay
        cycles += epoch_cycles
        delivered += m
        latencies.append(epoch_cycles)
    goodput = delivered * params.payload_bytes / (cycles * params.link_bytes_per_cycle)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
    return goodput, float(p99)


def simulate_mode_b_sr(corrupt: list[bool], params: Params) -> tuple[float, float]:
    m = params.mode_b_epoch
    t_frame = math.ceil(params.mode_b_frame_bytes / params.link_bytes_per_cycle)
    delivered = 0
    cycles = 0
    latencies: list[int] = []
    for i in range(0, len(corrupt), m):
        epoch = corrupt[i:i + m]
        if len(epoch) < m:
            break
        failed = sum(1 for x in epoch if x)
        epoch_cycles = m * t_frame + params.prop_delay + params.crc_delay + params.aead_delay
        if failed:
            # One repair round. Retried frames are assumed successful for this preliminary model.
            epoch_cycles += failed * t_frame + params.prop_delay + params.crc_delay + params.aead_delay
        cycles += epoch_cycles
        delivered += m
        latencies.append(epoch_cycles)
    goodput = delivered * params.payload_bytes / (cycles * params.link_bytes_per_cycle)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
    return goodput, float(p99)


def run(pi_values: Iterable[float], seeds: Iterable[int], params: Params) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    schemes = ["crc_arq", "modeA", "modeB_flush", "modeB_selective_retry"]
    for pi_b in pi_values:
        by_scheme: dict[str, list[tuple[float, float]]] = {s: [] for s in schemes}
        for seed in seeds:
            rng = random.Random(seed)
            corrupt = ge_corruptions(params.frames, pi_b, params.p_good, params.p_bad, params.beta, rng)
            by_scheme["crc_arq"].append(simulate_per_frame(corrupt, params.crc_arq_bytes, params, verify_delay=0))
            by_scheme["modeA"].append(simulate_per_frame(corrupt, params.mode_a_bytes, params, verify_delay=params.aead_delay))
            by_scheme["modeB_flush"].append(simulate_mode_b_flush(corrupt, params))
            by_scheme["modeB_selective_retry"].append(simulate_mode_b_sr(corrupt, params))
        for scheme in schemes:
            goodputs = [x[0] for x in by_scheme[scheme]]
            p99s = [x[1] for x in by_scheme[scheme]]
            rows.append({
                "piB": pi_b,
                "scheme": scheme,
                "goodput_mean": statistics.mean(goodputs),
                "goodput_ci95": ci95(goodputs),
                "p99_latency_cycles_mean": statistics.mean(p99s),
                "p99_latency_cycles_ci95": ci95(p99s),
            })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/selective_retry_followup_results.csv")
    ap.add_argument("--frames", type=int, default=20000)
    args = ap.parse_args()
    params = Params(frames=args.frames)
    pi_values = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10]
    rows = run(pi_values, range(5), params)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
