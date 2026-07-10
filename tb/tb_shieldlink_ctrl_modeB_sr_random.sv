`timescale 1ns/1ps
// SPDX-License-Identifier: MIT
module tb_shieldlink_ctrl_modeB_sr_random;
    localparam int SEQ_W=8,M=4,FRAME_BITS=16;
    logic clk=0,rst_n=0,rx_valid=0,rx_crc_ok=0,epoch_tag_valid=0,epoch_aead_ok=0;
    logic [SEQ_W-1:0] rx_seq=0,next_expected,ack_seq,nak_seq; logic [FRAME_BITS-1:0] rx_frame_bits=0;
    logic ack_valid,nak_valid,epoch_commit_pulse,epoch_repair_pulse,security_drop_pulse;logic [M-1:0] nak_bitmap;
    integer epoch,i,fail_slot,seed;logic [SEQ_W-1:0] base;
    always #1 clk=~clk;
    shieldlink_ctrl_modeB_sr #(.SEQ_W(SEQ_W),.M(M),.FRAME_BITS(FRAME_BITS)) dut(.clk,.rst_n,.rx_valid,.rx_seq,.rx_crc_ok,.rx_frame_bits,.epoch_tag_valid,.epoch_aead_ok,.next_expected,.ack_valid,.ack_seq,.nak_valid,.nak_seq,.nak_bitmap,.epoch_commit_pulse,.epoch_repair_pulse,.security_drop_pulse);
    task tick;begin @(posedge clk);#0.1;end endtask
    task frame(input [SEQ_W-1:0] seq,input logic ok);begin rx_valid=1;rx_seq=seq;rx_crc_ok=ok;rx_frame_bits={8'hA5,seq};tick();rx_valid=0;rx_crc_ok=0;end endtask
    task tag(input logic ok);begin epoch_tag_valid=1;epoch_aead_ok=ok;tick();epoch_tag_valid=0;epoch_aead_ok=0;end endtask
    always @(posedge clk) if(rst_n) begin
        assert(!(ack_valid&&nak_valid)) else $fatal("ACK and NAK overlap");
        assert(!(ack_valid&&security_drop_pulse)) else $fatal("ACK and security drop overlap");
        if(ack_valid) assert(epoch_commit_pulse) else $fatal("ACK without commit");
    end
    initial begin
        seed=32'h5EED1234;repeat(2)tick();rst_n=1;tick();
        for(epoch=0;epoch<40;epoch=epoch+1)begin
            base=next_expected;fail_slot=$urandom(seed)%M;
            for(i=M-1;i>=0;i=i-1)frame(base+i,i!=fail_slot);
            frame(base+((fail_slot+1)%M),1'b0);tag(1'b1);
            assert(nak_valid) else $fatal("missing bitmap NAK");
            assert(nak_bitmap[fail_slot]) else $fatal("failed slot absent");
            assert(!nak_bitmap[(fail_slot+1)%M]) else $fatal("good duplicate invalidated");
            frame(base+fail_slot,1'b1);tag(1'b1);
            assert(ack_valid) else $fatal("missing ACK after repair");
            assert(next_expected==base+M) else $fatal("bad next_expected");
        end
        base=next_expected;for(i=0;i<M;i=i+1)frame(base+i,1'b1);tag(1'b0);
        assert(security_drop_pulse&&!ack_valid&&!nak_valid) else $fatal("bad AEAD-failure behavior");
        assert(next_expected==base) else $fatal("advanced on AEAD failure");
        frame(base,1'b1);frame(base+1,1'b1);rst_n=0;tick();rst_n=1;tick();
        assert(next_expected==0) else $fatal("reset failed");
        $display("tb_shieldlink_ctrl_modeB_sr_random PASS");$finish;
    end
endmodule
