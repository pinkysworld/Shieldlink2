# Synthesis

This directory contains a small Yosys-based synthesis helper for comparing the control-plane RTL skeletons.

## Usage

```bash
bash synth/run_yosys_synthesis.sh synth/out
```

The script generates `.ys` command files, Yosys logs, per-target summary text files, and a compact `synthesis_summary.csv`.

## Targets

- `baseline_crc_arq`
- `shieldlink_modeA`
- `shieldlink_modeB_flush`
- `shieldlink_modeB_selective_retry`

## Scope

The numbers produced by this script are open-source synthesis estimates for control-plane RTL only. They exclude PHY, AEAD cipher core, SRAM macro selection, post-place-and-route timing, clock constraints, and power analysis.
