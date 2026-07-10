#!/usr/bin/env bash
set -euo pipefail
mkdir -p formal/out
yosys -q -p 'read_verilog -formal -sv -D FORMAL rtl/shieldlink_ctrl_modeB_sr.sv formal/modeB_sr_formal.sv; prep -top modeB_sr_formal; flatten; memory_map; opt; sat -verify -prove-asserts -seq 20 -set-init-zero -show-ports' | tee formal/out/yosys_sat.log
