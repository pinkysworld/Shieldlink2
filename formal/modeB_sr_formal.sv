// SPDX-License-Identifier: MIT
module modeB_sr_formal;
    localparam int SEQ_W=4, M=4, FRAME_BITS=8;
    (* gclk *) logic clk;
    (* anyseq *) logic rst_n,rx_valid,rx_crc_ok,epoch_tag_valid,epoch_aead_ok;
    (* anyseq *) logic [SEQ_W-1:0] rx_seq;
    (* anyseq *) logic [FRAME_BITS-1:0] rx_frame_bits;
    logic [SEQ_W-1:0] next_expected,ack_seq,nak_seq;
    logic ack_valid,nak_valid,epoch_commit_pulse,epoch_repair_pulse,security_drop_pulse;
    logic [M-1:0] nak_bitmap;
    shieldlink_ctrl_modeB_sr #(.SEQ_W(SEQ_W),.M(M),.FRAME_BITS(FRAME_BITS)) dut(
        .clk,.rst_n,.rx_valid,.rx_seq,.rx_crc_ok,.rx_frame_bits,.epoch_tag_valid,.epoch_aead_ok,
        .next_expected,.ack_valid,.ack_seq,.nak_valid,.nak_seq,.nak_bitmap,
        .epoch_commit_pulse,.epoch_repair_pulse,.security_drop_pulse);
endmodule
