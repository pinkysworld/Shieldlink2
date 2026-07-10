#!/usr/bin/env bash
set -euo pipefail
OUT_DIR=${1:-synth/ice40-out};mkdir -p "$OUT_DIR"
run_one(){ local name="$1" top="$2";shift 2;local sources=("$@");yosys -q -p "read_verilog -sv ${sources[*]}; synth_ice40 -top $top -json $OUT_DIR/$name.json; stat" | tee "$OUT_DIR/$name.log";grep -E "Number of cells:|SB_LUT4|SB_DFF|SB_DFFE|SB_RAM" "$OUT_DIR/$name.log" > "$OUT_DIR/$name.summary.txt" || true;}
run_one baseline_crc_arq top_fpga_baseline rtl/baseline_ctrl_crc_arq.sv rtl/top_fpga_baseline.sv
run_one shieldlink_modeA top_fpga_modeA rtl/shieldlink_ctrl_modeA.sv rtl/top_fpga_modeA.sv
run_one shieldlink_modeB_flush_proxy top_ice40_timing_flush rtl/shieldlink_ctrl_modeB_flush.sv rtl/top_ice40_timing_flush.sv
run_one shieldlink_modeB_sr_proxy top_ice40_timing_sr rtl/shieldlink_ctrl_modeB_sr.sv rtl/top_ice40_timing_sr.sv
echo "iCE40 technology-mapped control-plane proxy results are in $OUT_DIR"
