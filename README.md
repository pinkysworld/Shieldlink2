# ShieldLink-SR

Selective-retry epoch authentication for secure chiplet interconnects.

This repository is the follow-up artifact track for **ShieldLink-SR**, a proposed extension of the accepted ShieldLink work. The original ShieldLink paper introduced the Deliverability Invariant, requiring authenticated delivery before ACK and buffer retirement. ShieldLink-SR focuses on the main practical weakness of epoch authentication: flush-all retransmission under burst errors.

## Core idea

Original ShieldLink Mode B amortizes authentication by verifying an epoch of `M` frames with one epoch tag. That improves wire efficiency, but a single CRC-failed frame can force retransmission of the whole epoch. ShieldLink-SR keeps the epoch-level authentication boundary but adds selective repair:

- Track which epoch slots have been received.
- Track which slots failed CRC.
- Emit a bitmap NAK for only missing or corrupted slots.
- Retain good frames across repair rounds.
- Commit the epoch only when all slots are present, no CRC failures remain, and epoch AEAD verification succeeds.

The security rule remains unchanged:

```text
ACK / commit only after authenticated deliverability.
```

## Repository contents

- `rtl/` contains synthesizable SystemVerilog control-plane skeletons:
  - `baseline_ctrl_crc_arq.sv`
  - `shieldlink_ctrl_modeA.sv`
  - `shieldlink_ctrl_modeB_flush.sv`
  - `shieldlink_ctrl_modeB_sr.sv`
  - synthesis top modules for comparison
- `tb/` contains deterministic and randomized RTL regressions.
- `formal/` contains Yosys SAT and optional SymbiYosys proof harnesses.
- `code/` contains the simulators, policy ablations, trace replay, tests, and plotting scripts.
- `data/` contains generated compact result summaries.
- `synth/` contains generic and iCE40 technology-mapped Yosys synthesis scripts.
- `.github/workflows/` contains reproducible Python, RTL, formal, and synthesis validation.
- `FOLLOWUP_PAPER_PLAN.md` outlines the planned paper.
- `docs/VALIDATION.md` documents the expanded validation suite and claim boundaries.

## Preliminary result snapshot

The preliminary Monte Carlo simulator compares CRC+ARQ, ShieldLink Mode A, original Mode B flush-all, and Mode B selective retry under a Gilbert-Elliott burst-error model. At the default `M=32`, `p_bad=0.1`, and `beta=0.2` stress regime, selective retry preserves most of Mode B's wire-efficiency advantage while avoiding the flush-all goodput cliff.

Representative points from `data/selective_retry_followup_results.csv`:

| Bad-state probability | Mode B flush-all goodput | Mode B-SR goodput |
|---:|---:|---:|
| 0.04 | 0.8396 | 0.9225 |
| 0.10 | 0.7196 | 0.9167 |

These are preliminary simulation results, not final publication claims.

## Expanded validation suite

The expanded suite adds:

- 20-seed protocol experiments with ACK/NAK serialization, propagation, timeouts, repair authentication, pipelining, and abstract FEC.
- Adversarial schedules for repeated corruption, final-frame targeting, tag targeting, replay, and reordering.
- Fixed, threshold, EWMA, and offline-oracle epoch-size policies.
- Synthetic mixed-workload trace replay with coherence-like, packet, DMA, and bulk traffic.
- Deterministic and randomized RTL regression tests.
- RTL assertions plus bounded Yosys SAT checking.
- Generic and iCE40 technology-mapped synthesis comparisons.

See [`docs/VALIDATION.md`](docs/VALIDATION.md) for results, interpretation, and limitations.

## Reproduce the Python experiments

```bash
python3 code/sim_selective_retry_followup.py --out data/selective_retry_followup_results.csv
python3 code/resource_estimator_selective_retry.py --out data/modeB_sr_resource_sizing.csv
python3 code/extended_experiments.py --out-dir data
python3 code/generate_synthetic_trace.py --out traces/synthetic_mixed_workload.csv
python3 code/protocol_realism_experiments.py --out-dir data --epochs 300 --seeds 20
PYTHONPATH=code python3 code/adaptive_policy_ablation.py --out-dir data --seeds 20
python3 code/trace_replay_experiments.py --trace traces/synthetic_mixed_workload.csv --out data/trace_replay_summary.csv --seeds 20
PYTHONPATH=code python3 code/test_models.py -v
python3 code/make_validation_plots.py --data-dir data --fig-dir figures
```

## Run RTL, formal, and synthesis validation

Install Icarus Verilog, Verilator, and Yosys, then run:

```bash
iverilog -g2012 -s tb_shieldlink_ctrl_modeB_sr -o /tmp/tb_smoke rtl/shieldlink_ctrl_modeB_sr.sv tb/tb_shieldlink_ctrl_modeB_sr.sv
vvp /tmp/tb_smoke

iverilog -g2012 -s tb_shieldlink_ctrl_modeB_sr_random -o /tmp/tb_random rtl/shieldlink_ctrl_modeB_sr.sv tb/tb_shieldlink_ctrl_modeB_sr_random.sv
vvp /tmp/tb_random

bash formal/run_yosys_formal.sh
bash synth/run_yosys_synthesis.sh synth/out
bash synth/run_ice40_synthesis.sh synth/ice40-out
```

The `Full validation` GitHub Actions workflow runs the same checks and uploads the generated logs and reports.

## Scope and limitations

This repository provides control-plane RTL, abstract simulation models, generated result summaries, formal harnesses, testbenches, and synthesis automation. It does not yet include an integrated PHY, full AEAD cipher core, measured CXL/UCIe traces, post-place-and-route timing, ASIC PPA, or a proof of liveness against an unconstrained active attacker.

## License

MIT License. See `LICENSE`.
