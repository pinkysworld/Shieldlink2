# ShieldLink-SR validation and extended experiments

This validation layer tests the selective-retry extension at four levels: abstract performance modeling, adversarial availability experiments, RTL simulation/formal checking, and synthesis automation. Results generated on 2026-07-10 are preliminary and should not be treated as measured CXL/UCIe or ASIC performance.

## 1. Protocol-realism model

`code/protocol_realism_experiments.py` adds ACK and bitmap-NAK serialization, propagation, timeout, three repair-authentication policies, bounded repair rounds, finite pipeline depth, workload utilization, abstract FEC, adversarial schedules, and 20-seed confidence intervals.

The checked-in run uses `M=32`, `pi_bad=0.10`, `beta=0.20`, `p_bad=0.10`, 300 epochs per seed and 20 seeds.

| Scheme | Schedule | Goodput | Mean p99 cycles | Mean security drops |
|---|---|---:|---:|---:|
| Mode B flush-all | none | 0.7175 | 4020.5 | 0 |
| Mode B-SR | none | 0.9155 | 1328.4 | 0 |
| Mode B flush-all | one corrupted frame per epoch | 0.4036 | 5323.5 | 0 |
| Mode B-SR | one corrupted frame per epoch | 0.8863 | 1368.9 | 0 |
| Mode B-SR | epoch-tag attack | 0.9163 | 1397.4 | 300 |
| Mode B-SR | persistent repair attack | 0.5964 | 3136.2 | 300 |

The tag-target result illustrates the safety/availability boundary. Authentication failure does not produce successful delivery, but an attacker can still force security drops. Persistent corruption remains a denial-of-service vector for every retry protocol.

For the default regime, `tag_once`, `resend_epoch_tag`, and a per-round repair authenticator differ only slightly because 12 bytes are small relative to a 32-frame epoch. This quantifies bandwidth cost only and does not establish that unauthenticated repair signaling is safe.

The abstract FEC experiment shows the expected clean-channel cost. For Mode B-SR, goodput falls from 0.9155 without FEC to 0.8664 at `t=1` and 0.8210 at `t=2`, while average repair volume decreases. A publication claim requires a specified code, decoder latency and hardware cost.

## 2. Adaptive epoch-size ablation

`code/adaptive_policy_ablation.py` evaluates fixed epoch sizes, threshold policies, EWMA policies and an offline oracle on a non-stationary synthetic channel. Utility is defined as:

```text
utility = goodput - 0.00002 * p99_latency_cycles
```

The offline oracle reached mean utility 0.9039. The strongest implementable tested policy, threshold `0.04` with a 32-clean-epoch growth window, reached 0.9026. Fixed `M=8` reached 0.9024. The preferred policy therefore depends on the latency weight.

## 3. Synthetic mixed-workload trace replay

`code/trace_replay_experiments.py` accepts external CSV traces. `code/generate_synthetic_trace.py` creates a deterministic trace with coherence-like 64-byte messages, 256-byte packets, 4 KiB DMA transactions and 16 KiB bulk transactions.

The generated trace is synthetic and trace-inspired, not measured CXL/UCIe data. At `M=32`, increasing outstanding epoch depth from 1 to 8 reduced packet-class mean latency from about 15,092 cycles to 754 cycles and peak queued transactions from 706 to 205 in this stress trace. Fairness does not improve monotonically, so scheduling remains a separate design problem.

## 4. RTL corrections and regression tests

The revised `shieldlink_ctrl_modeB_sr.sv` fixes two control-plane edge cases:

1. The first frame of a new epoch is captured immediately rather than lost while `epoch_active` is asserted.
2. A corrupted duplicate cannot invalidate a retained CRC-clean copy.

Testbenches:

- `tb/tb_shieldlink_ctrl_modeB_sr.sv`, deterministic smoke test
- `tb/tb_shieldlink_ctrl_modeB_sr_random.sv`, reverse-order delivery, random failed slots, corrupt duplicates, repair, AEAD failure and reset-during-epoch regression

## 5. RTL formal checks

The RTL includes assertions under `FORMAL`. `formal/run_yosys_formal.sh` runs a bounded 20-cycle Yosys SAT proof checking:

- no simultaneous ACK and NAK
- no ACK with a security drop
- ACK requires a prior complete, CRC-clean, AEAD-accepted epoch
- `next_expected` changes only after authenticated commit
- AEAD failure produces a security drop and no reliability NAK

`formal/modeB_sr.sby` is included for environments with SymbiYosys and Boolector.

## 6. Synthesis and CI

`.github/workflows/full-validation.yml` runs Python tests, compact experiment reproduction, Verilator lint, deterministic and randomized RTL simulations, generic Yosys synthesis, iCE40 technology mapping and bounded Yosys SAT formal checking.

The iCE40 output is technology-mapped synthesis, not place-and-route timing. Maximum frequency, power and routing congestion still require a concrete FPGA device, pin constraints and nextpnr or a vendor flow.

## Claim boundary

> Under the evaluated abstract channel, workload and adversarial schedules, selective repair preserves authenticated epoch commit and avoids the retransmission collapse of flush-all Mode B with bitmap-scale control state.

This does not establish measured CXL/UCIe performance, full cryptographic security, liveness against an unconstrained active attacker, post-route FPGA timing or ASIC PPA.
