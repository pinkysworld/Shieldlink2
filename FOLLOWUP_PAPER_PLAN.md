# Follow-up paper plan: ShieldLink-SR

## Working title

**ShieldLink-SR: Selective-Retry Epoch Authentication for Low-Latency Secure Chiplet Interconnects**

Alternative title:

**Adaptive ShieldLink: Selective-Retry Epoch Authentication for Secure Chiplet Links**

## Motivation

The first ShieldLink paper defines the Deliverability Invariant and evaluates two operating modes:

- Mode A: per-frame authentication with low latency and straightforward ACK gating.
- Mode B: epoch authentication with better wire efficiency but high tail latency and a goodput cliff under burst errors.

The follow-up paper focuses on Mode B's main limitation. A flush-all epoch policy retransmits an entire epoch even when only one frame fails CRC. This is simple but inefficient under burst errors.

## Research question

Can selective retry preserve the wire-efficiency advantage of epoch authentication while avoiding the burst-induced goodput cliff and tail-latency penalty of flush-all Mode B?

## Proposed contribution

ShieldLink-SR adds a bitmap NAK path to epoch authentication. The receiver tracks received and CRC-failed epoch slots, retains good frames, and requests retransmission only for missing or corrupted slots.

The epoch still commits only when:

```text
all frames are present AND no CRC failures remain AND epoch AEAD verifies
```

Security failures remain non-recoverable data-plane events: an epoch with all frames present and CRC-clean but AEAD-failed triggers a security drop rather than a reliability NAK.

## Planned paper structure

1. Introduction
   - Problem: secure chiplet links need authenticated delivery and retry efficiency.
   - Gap: epoch authentication is efficient but flush-all retransmission is fragile under bursts.

2. Background
   - Short summary of ShieldLink D-Inv.
   - Mode A and original Mode B.
   - Why burst errors and fault injection motivate selective repair.

3. ShieldLink-SR design
   - Epoch slot indexing.
   - Received bitmap.
   - CRC-failure bitmap.
   - Bitmap NAK format.
   - Repair loop.
   - Authenticated epoch commit rule.

4. Security analysis
   - D-Inv preservation.
   - No ACK before authenticated commit.
   - No AEAD-failure NAK oracle.
   - Replay and nonce assumptions.
   - Denial-of-service boundary.

5. Simulation methodology
   - Gilbert-Elliott channel.
   - Baselines: CRC+ARQ, Mode A, Mode B flush-all, Mode B-SR.
   - Metrics: goodput, p99 commit latency, repair rounds, buffer pressure.

6. RTL and synthesis methodology
   - Control-plane RTL modules.
   - Yosys synthesis comparison.
   - Scope: skeleton/control-plane only, no cipher core or PHY timing closure.

7. Results
   - Goodput vs burst probability.
   - Tail latency vs burst probability.
   - Bitmap overhead and resource cost.
   - Synthesis table when available.

8. Discussion
   - When Mode A remains preferable.
   - When Mode B-SR dominates flush-all Mode B.
   - Adaptive epoch sizing as next step.

9. Conclusion

## Claim boundary

Preliminary claim:

> Selective-retry epoch authentication preserves most of Mode B's wire-efficiency advantage while reducing retransmission waste and delaying or eliminating the flush-all Mode B goodput cliff under burst-error regimes.

Do not claim final FPGA/ASIC PPA until Yosys or vendor synthesis outputs are generated and reviewed.

## Immediate next steps

- Run the GitHub Actions synthesis workflow.
- Archive the synthesis artifact.
- Add synthesis summary CSV to the repository.
- Add additional simulations for M = 8, 16, 32, 64.
- Add a draft manuscript once results stabilize.
