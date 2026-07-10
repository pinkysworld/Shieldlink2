#!/usr/bin/env bash
set -euo pipefail
mkdir -p formal/out
LOG=formal/out/yosys_sat.log
set +e
yosys -p 'read_verilog -formal -sv -D FORMAL rtl/shieldlink_ctrl_modeB_sr.sv formal/modeB_sr_formal.sv; prep -top modeB_sr_formal; flatten; async2sync; dffunmap; memory_map; opt_clean; sat -verify -prove-asserts -seq 20 -set-init-zero -show-ports' >"$LOG" 2>&1
status=$?
set -e
tail -n 100 "$LOG"
exit "$status"
