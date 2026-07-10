// SPDX-License-Identifier: MIT
// Minimal behavioral smoke test for shieldlink_ctrl_modeB_sr.
// Run with a SystemVerilog simulator after installing one, for example:
//   verilator --lint-only rtl/shieldlink_ctrl_modeB_sr.sv tb/tb_shieldlink_ctrl_modeB_sr.sv

module tb_shieldlink_ctrl_modeB_sr;
    localparam int SEQ_W = 8;
    localparam int M = 4;
    localparam int FRAME_BITS = 32;

    logic clk = 0;
    logic rst_n = 0;
    logic rx_valid = 0;
    logic [SEQ_W-1:0] rx_seq = 0;
    logic rx_crc_ok = 0;
    logic [FRAME_BITS-1:0] rx_frame_bits = 0;
    logic epoch_tag_valid = 0;
    logic epoch_aead_ok = 0;
    logic [SEQ_W-1:0] next_expected;
    logic ack_valid;
    logic [SEQ_W-1:0] ack_seq;
    logic nak_valid;
    logic [M-1:0] nak_bitmap;
    logic [SEQ_W-1:0] nak_seq;
    logic epoch_commit_pulse;
    logic epoch_repair_pulse;
    logic security_drop_pulse;

    always #5 clk = ~clk;

    shieldlink_ctrl_modeB_sr #(
        .SEQ_W(SEQ_W), .M(M), .FRAME_BITS(FRAME_BITS)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .rx_valid(rx_valid), .rx_seq(rx_seq), .rx_crc_ok(rx_crc_ok), .rx_frame_bits(rx_frame_bits),
        .epoch_tag_valid(epoch_tag_valid), .epoch_aead_ok(epoch_aead_ok),
        .next_expected(next_expected), .ack_valid(ack_valid), .ack_seq(ack_seq),
        .nak_valid(nak_valid), .nak_seq(nak_seq), .nak_bitmap(nak_bitmap),
        .epoch_commit_pulse(epoch_commit_pulse), .epoch_repair_pulse(epoch_repair_pulse),
        .security_drop_pulse(security_drop_pulse)
    );

    task tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    task send_frame(input [SEQ_W-1:0] seq, input crc_ok);
        begin
            rx_valid = 1'b1;
            rx_seq = seq;
            rx_crc_ok = crc_ok;
            rx_frame_bits = {24'h0, seq};
            tick();
            rx_valid = 1'b0;
            rx_crc_ok = 1'b0;
        end
    endtask

    task send_tag(input aead_ok);
        begin
            epoch_tag_valid = 1'b1;
            epoch_aead_ok = aead_ok;
            tick();
            epoch_tag_valid = 1'b0;
            epoch_aead_ok = 1'b0;
        end
    endtask

    initial begin
        repeat (2) tick();
        rst_n = 1'b1;
        tick();

        send_frame(8'd0, 1'b1);
        send_frame(8'd1, 1'b0);
        send_frame(8'd2, 1'b1);
        send_frame(8'd3, 1'b1);
        send_tag(1'b1);
        assert(!ack_valid) else $fatal("ACK emitted before repair");
        assert(nak_valid) else $fatal("Expected bitmap NAK");
        assert(nak_bitmap == 4'b0010) else $fatal("Expected repair bitmap 0010, got %b", nak_bitmap);

        send_frame(8'd1, 1'b1);
        send_tag(1'b1);
        assert(ack_valid) else $fatal("Expected ACK after clean authenticated epoch");
        assert(ack_seq == 8'd4) else $fatal("Expected ACK sequence 4, got %0d", ack_seq);
        assert(next_expected == 8'd4) else $fatal("Expected next_expected 4, got %0d", next_expected);

        send_frame(8'd4, 1'b1);
        send_frame(8'd5, 1'b1);
        send_frame(8'd6, 1'b1);
        send_frame(8'd7, 1'b1);
        send_tag(1'b0);
        assert(security_drop_pulse) else $fatal("Expected security drop on AEAD failure");
        assert(!nak_valid) else $fatal("AEAD failure must not emit reliability NAK");

        $display("tb_shieldlink_ctrl_modeB_sr PASS");
        $finish;
    end
endmodule
