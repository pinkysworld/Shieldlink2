#!/usr/bin/env bash
set -euo pipefail
OUT_DIR=${1:-synth/ice40-pnr};mkdir -p "$OUT_DIR"
yosys -q -p "read_verilog -sv rtl/shieldlink_ctrl_modeB_sr.sv rtl/top_ice40_timing_sr.sv; synth_ice40 -top top_ice40_timing_sr -json $OUT_DIR/shieldlink_sr_timing.json; stat" | tee "$OUT_DIR/yosys.log"
nextpnr-ice40 --hx8k --package ct256 --json "$OUT_DIR/shieldlink_sr_timing.json" --asc "$OUT_DIR/shieldlink_sr_timing.asc" --freq 50 --pcf-allow-unconstrained 2>&1 | tee "$OUT_DIR/nextpnr.log"
grep -E "Max frequency|Info: Device utilisation|ICESTORM_LC|SB_RAM" "$OUT_DIR/nextpnr.log" "$OUT_DIR/yosys.log" > "$OUT_DIR/timing_summary.txt" || true
echo "Reduced-width control-plane place-and-route outputs are in $OUT_DIR"
