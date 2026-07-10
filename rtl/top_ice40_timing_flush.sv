// SPDX-License-Identifier: MIT
// Reduced-width physical top for Mode B flush-all control-path synthesis.
module top_ice40_timing_flush (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        rx_valid,
    input  logic [15:0] rx_seq,
    input  logic        rx_crc_ok,
    input  logic [31:0] rx_frame_bits,
    input  logic        epoch_tag_valid,
    input  logic        epoch_aead_ok,
    output logic        ack_valid,
    output logic        nak_valid,
    output logic        security_drop_pulse,
    output logic [15:0] next_expected_probe
);
    logic [15:0] ack_seq,nak_seq;
    logic epoch_commit_pulse,epoch_flush_pulse;
    shieldlink_ctrl_modeB_flush #(.SEQ_W(16),.M(32),.FRAME_BITS(32)) dut (
        .clk,.rst_n,.rx_valid,.rx_seq,.rx_crc_ok,.rx_frame_bits,
        .epoch_tag_valid,.epoch_aead_ok,.next_expected(next_expected_probe),
        .ack_valid,.ack_seq,.nak_valid,.nak_seq,
        .epoch_commit_pulse,.epoch_flush_pulse,.security_drop_pulse
    );
endmodule
