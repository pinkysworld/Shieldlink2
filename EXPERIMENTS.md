# Extended Experiments and Preliminary Results

This repository now includes the next experiment layer for the ShieldLink-SR follow-up paper. The goal is to evaluate whether selective-retry epoch authentication preserves the authenticated-delivery invariant while avoiding the flush-all goodput cliff of original Mode B.

## Added experiments

### 1. Epoch-size sweep

Script: `code/extended_experiments.py`

The script sweeps:

```text
M = 4, 8, 16, 32, 64, 128
```

Schemes:

```text
modeA
modeB_flush
modeB_selective_retry
```

A compact checked-in summary for `piB=0.10`, `beta=0.2`, `p_bad=0.1` is in:

```text
data/m_sweep_piB0p10_summary.csv
```

Preliminary result:

| M | Mode B flush-all goodput | Mode B-SR goodput | Mode B flush-all p99 cycles | Mode B-SR p99 cycles |
|---:|---:|---:|---:|---:|
| 4 | 0.8812 | 0.9095 | 299.0 | 197.5 |
| 8 | 0.8607 | 0.9128 | 766.7 | 363.0 |
| 16 | 0.8163 | 0.9144 | 1502.7 | 662.0 |
| 32 | 0.7047 | 0.9156 | 4462.0 | 1255.5 |
| 64 | 0.5628 | 0.9168 | 11097.5 | 2391.5 |
| 128 | 0.3406 | 0.9174 | 45750.8 | 4657.0 |

Interpretation: selective retry lets epoch authentication scale to larger M values without the flush-all retransmission cliff.

### 2. Channel sensitivity sweep

Script: `code/extended_experiments.py`

The script sweeps:

```text
beta = 0.05, 0.10, 0.20, 0.50
p_bad = 0.01, 0.05, 0.10, 0.20
piB = 0.00, 0.01, 0.02, 0.04, 0.075, 0.10, 0.15, 0.20
```

Schemes:

```text
crc_arq
modeA
modeB_flush
modeB_selective_retry
adaptive_sr
```

A compact checked-in summary for the default stress case is in:

```text
data/extended_highlights.csv
```

Representative default-stress highlights for `M=32`, `beta=0.2`, `p_bad=0.1`:

| piB | Mode B flush-all goodput | Mode B-SR goodput | Adaptive SR goodput |
|---:|---:|---:|---:|
| 0.04 | 0.8293 | 0.9213 | 0.9226 |
| 0.10 | 0.7047 | 0.9156 | 0.9152 |
| 0.20 | 0.5271 | 0.9065 | 0.9070 |

Interpretation: selective retry recovers most of Mode B's wire-efficiency advantage even when flush-all retransmission collapses.

### 3. Tail-latency and repair metrics

The extended simulator reports:

```text
p50, p95, p99, p99.9, maximum latency
average repair rounds per epoch
average repair frames per epoch
peak repair frames
average and peak buffer frames
```

This addresses the likely reviewer concern that selective retry may improve goodput while hiding tail latency or bookkeeping costs.

### 4. Bounded safety sanity check

Script: `code/formal_sanity_check_modeB_sr.py`

Output:

```text
data/formal_sanity_modeB_sr.txt
```

The bounded explicit-state checker explores a small receiver model with `M=4`, `SEQ_MOD=8`, and depth 10. It checks:

```text
P1: no ACK unless the epoch is complete, CRC-clean, and AEAD accepted.
P2: next_expected advances only on authenticated epoch commit.
P3: AEAD failure causes security_drop, not reliability repair NAK.
P4: bitmap NAK requests exactly missing or CRC-failed slots.
P5: CRC-failed slots cannot be committed unless repaired.
```

Current result:

```text
states_explored=479
transitions_explored=4210
result=PASS
```

This is not a full formal proof, but it is a useful bounded safety check for the added bitmap-repair state machine.

### 5. RTL smoke test and synthesis hooks

Added:

```text
tb/tb_shieldlink_ctrl_modeB_sr.sv
```

The testbench checks a simple failed-slot repair scenario and an AEAD-failure security-drop scenario.

The existing Yosys script remains the synthesis entry point:

```bash
bash synth/run_yosys_synthesis.sh synth/out
```

The local runtime used for this update did not include Yosys, so no local synthesis logs are included yet. Use GitHub Actions or a local Yosys install to generate `synthesis_summary.csv`.

## Reproduction commands

```bash
python3 code/extended_experiments.py --out-dir data
python3 code/formal_sanity_check_modeB_sr.py | tee data/formal_sanity_modeB_sr.txt
python3 code/make_experiment_plots.py --data-dir data --fig-dir figures
bash synth/run_yosys_synthesis.sh synth/out
```

## Claim boundary

The current results support a preliminary follow-up claim:

> ShieldLink-SR preserves ShieldLink's authenticated-delivery invariant while avoiding the flush-all goodput cliff of epoch authentication under burst errors, with bitmap-scale control overhead.

The claim should remain preliminary until real synthesis logs, lint/testbench output, and ideally trace-driven CXL/UCIe traffic experiments are added.
