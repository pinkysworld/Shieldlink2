// SPDX-License-Identifier: MIT
// ShieldLink Mode B-SR: epoch authentication with selective retry.
//
// Commit is permitted only when every epoch slot has a retained CRC-clean copy
// and the epoch AEAD verifier accepts. Missing or CRC-failed slots are requested
// through a bitmap NAK. A corrupted duplicate never invalidates a retained good
// copy. CRC, AEAD, PHY, timeout and sender scheduling remain external blocks.

module shieldlink_ctrl_modeB_sr #(
    parameter int SEQ_W = 64,
    parameter int M = 32,
    parameter int FRAME_BITS = 276*8
) (
    input  logic                  clk,
    input  logic                  rst_n,

    input  logic                  rx_valid,
    input  logic [SEQ_W-1:0]      rx_seq,
    input  logic                  rx_crc_ok,
    input  logic [FRAME_BITS-1:0] rx_frame_bits,

    input  logic                  epoch_tag_valid,
    input  logic                  epoch_aead_ok,

    output logic [SEQ_W-1:0]      next_expected,
    output logic                  ack_valid,
    output logic [SEQ_W-1:0]      ack_seq,

    output logic                  nak_valid,
    output logic [SEQ_W-1:0]      nak_seq,
    output logic [M-1:0]          nak_bitmap,

    output logic                  epoch_commit_pulse,
    output logic                  epoch_repair_pulse,
    output logic                  security_drop_pulse
);

    localparam int IDX_W = (M <= 1) ? 1 : $clog2(M);

    logic [FRAME_BITS-1:0] epoch_mem [0:M-1];
    logic [M-1:0] received_bitmap;
    logic [M-1:0] crc_fail_bitmap;
    logic [M-1:0] repair_bitmap;

    logic [SEQ_W-1:0] epoch_start_seq;
    logic [SEQ_W-1:0] active_epoch_start;
    logic [SEQ_W-1:0] seq_delta;
    logic [IDX_W-1:0] rx_idx;
    logic in_epoch;
    logic epoch_active;
    logic epoch_complete;
    logic epoch_clean;

    always_comb begin
        active_epoch_start = epoch_active ? epoch_start_seq : next_expected;
        seq_delta = rx_seq - active_epoch_start;
        rx_idx = seq_delta[IDX_W-1:0];
        in_epoch = (seq_delta < M);
        repair_bitmap = (~received_bitmap) | crc_fail_bitmap;
        epoch_complete = (&received_bitmap);
        epoch_clean = (crc_fail_bitmap == '0);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_expected <= '0;
            epoch_start_seq <= '0;
            received_bitmap <= '0;
            crc_fail_bitmap <= '0;
            epoch_active <= 1'b0;
            ack_valid <= 1'b0;
            ack_seq <= '0;
            nak_valid <= 1'b0;
            nak_seq <= '0;
            nak_bitmap <= '0;
            epoch_commit_pulse <= 1'b0;
            epoch_repair_pulse <= 1'b0;
            security_drop_pulse <= 1'b0;
        end else begin
            ack_valid <= 1'b0;
            nak_valid <= 1'b0;
            epoch_commit_pulse <= 1'b0;
            epoch_repair_pulse <= 1'b0;
            security_drop_pulse <= 1'b0;

            if (!epoch_active) begin
                if (rx_valid && in_epoch) begin
                    epoch_active <= 1'b1;
                    epoch_start_seq <= next_expected;
                    nak_bitmap <= '0;
                    if (rx_crc_ok) begin
                        epoch_mem[rx_idx] <= rx_frame_bits;
                        received_bitmap <= ({{(M-1){1'b0}},1'b1} << rx_idx);
                        crc_fail_bitmap <= '0;
                    end else begin
                        received_bitmap <= '0;
                        crc_fail_bitmap <= ({{(M-1){1'b0}},1'b1} << rx_idx);
                    end
                end
            end else begin
                if (rx_valid && in_epoch) begin
                    if (rx_crc_ok) begin
                        epoch_mem[rx_idx] <= rx_frame_bits;
                        received_bitmap[rx_idx] <= 1'b1;
                        crc_fail_bitmap[rx_idx] <= 1'b0;
                    end else if (!received_bitmap[rx_idx]) begin
                        // A corrupt duplicate cannot invalidate a retained good copy.
                        crc_fail_bitmap[rx_idx] <= 1'b1;
                    end
                end

                // epoch_tag_valid is expected after the candidate epoch or repair
                // round has been registered.
                if (epoch_tag_valid) begin
                    if (epoch_complete && epoch_clean && epoch_aead_ok) begin
                        next_expected <= epoch_start_seq + M;
                        ack_valid <= 1'b1;
                        ack_seq <= epoch_start_seq + M;
                        epoch_commit_pulse <= 1'b1;
                        epoch_active <= 1'b0;
                    end else if (epoch_complete && epoch_clean && !epoch_aead_ok) begin
                        security_drop_pulse <= 1'b1;
                        epoch_active <= 1'b0;
                    end else begin
                        nak_valid <= 1'b1;
                        nak_seq <= epoch_start_seq;
                        nak_bitmap <= repair_bitmap;
                        epoch_repair_pulse <= 1'b1;
                    end
                end
            end
        end
    end

`ifdef FORMAL
    // Two-cycle warm-up ensures every $past() sample below is defined after reset.
    logic [1:0] f_history_valid = '0;
    always_ff @(posedge clk) begin
        f_history_valid <= {f_history_valid[0], 1'b1};

        if (!f_history_valid[0]) begin
            assume(!rst_n);
        end else begin
            assume(rst_n);
        end

        if (f_history_valid[1]) begin
            a_no_ack_nak_overlap: assert(!(ack_valid && nak_valid));
            a_no_ack_security_overlap: assert(!(ack_valid && security_drop_pulse));
            a_no_commit_repair_overlap: assert(!(epoch_commit_pulse && epoch_repair_pulse));
            a_ack_is_commit: assert(ack_valid == epoch_commit_pulse);

            if (ack_valid) begin
                a_ack_requires_tag: assert($past(epoch_tag_valid));
                a_ack_requires_aead: assert($past(epoch_aead_ok));
                a_ack_requires_complete: assert($past(epoch_complete));
                a_ack_requires_clean: assert($past(epoch_clean));
                a_ack_advances_one_epoch: assert(next_expected == ($past(next_expected) + M));
            end

            if (next_expected != $past(next_expected)) begin
                a_state_change_requires_ack: assert(ack_valid && epoch_commit_pulse);
            end

            if (nak_valid || security_drop_pulse) begin
                a_no_advance_on_failure: assert(next_expected == $past(next_expected));
            end

            if (security_drop_pulse) begin
                a_drop_requires_tag: assert($past(epoch_tag_valid));
                a_drop_requires_failed_aead: assert(!$past(epoch_aead_ok));
                a_drop_requires_complete: assert($past(epoch_complete));
                a_drop_requires_clean: assert($past(epoch_clean));
                a_drop_is_not_nak: assert(!nak_valid);
            end
        end
    end
`endif

endmodule
