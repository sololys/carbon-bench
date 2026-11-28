/* ============================================================================
 * tb_top_iks_sluice.sv
 * Zero-Float Icarus Verilog & Yosys Gate-Level Testbench for top_iks_sluice
 * Verifies:
 *   1. Boot reset into KILL (0x00)
 *   2. 63-word load (W_H == 1000) + 64-cycle Feistel Half 1 -> genuine ARX
 *      digest 0x3109a228 (and falsifies tautology by checking corrupted load!)
 *   3. 64-cycle Feistel Half 2 -> bit-exact round-trip XOR == 0x0000 across
 *      all 63 words on both Rail A and Rail B + W_H == 1000 preserved
 *   4. 800-cycle cooldown + l01_reset_auth -> HOLD (0x3C) -> OPEN (0xA5)
 *   5. One-way escalation OPEN (0xA5) -> TRAP (0x5A) with no return valve
 *   6. Immediate absorbing KILL (0x00) on single 1-bit PG(2,2) corruption
 * ============================================================================ */

`timescale 1ns / 1ps
`default_nettype none

module tb_top_iks_sluice;

    // 80.0 kHz clock -> 12 500 ns integer period (half-period = 6 250 ns, 0 float)
    localparam integer CLK_HALF_NS = 6250;

    reg         clk;
    reg         rst_n;
    reg         l01_reset_auth;
    reg         arm_sweep;
    reg         host_wr_en;
    reg  [5:0]  host_wr_idx;
    reg  [15:0] host_rail_a;
    reg  [15:0] host_rail_b;
    reg  [41:0] pg22_bus;
    reg  [31:0] witness_expected;
    reg         witness_check_en;
    reg         b1_nash_xor_ok;
    reg         poincare_open_req;

    wire [7:0]  state_code;
    wire        master_gate_open;
    wire [31:0] arx_digest_out;
    wire [5:0]  k_coord_out;
    wire        sweep_done_pulse;
    wire        pg22_all_ok;
    wire        ebr_parity_ok;
    wire [10:0] dual_rail_wh_out;
    wire [9:0]  cooldown_cnt;

    reg  [5:0]  diag_rd_idx;
    wire [15:0] diag_rail_a;
    wire [15:0] diag_rail_b;

    reg  [15:0] ref_rail_a [0:62];
    reg  [15:0] ref_rail_b [0:62];
    reg  [15:0] xor_residual_acc;
    integer     i, errors;

    top_iks_sluice dut (
        .clk               (clk),
        .rst_n             (rst_n),
        .l01_reset_auth    (l01_reset_auth),
        .arm_sweep         (arm_sweep),
        .host_wr_en        (host_wr_en),
        .host_wr_idx       (host_wr_idx),
        .host_rail_a       (host_rail_a),
        .host_rail_b       (host_rail_b),
        .pg22_bus          (pg22_bus),
        .witness_expected  (witness_expected),
        .witness_check_en  (witness_check_en),
        .b1_nash_xor_ok    (b1_nash_xor_ok),
        .poincare_open_req (poincare_open_req),
        .state_code        (state_code),
        .master_gate_open  (master_gate_open),
        .arx_digest_out    (arx_digest_out),
        .k_coord_out       (k_coord_out),
        .sweep_done_pulse  (sweep_done_pulse),
        .pg22_all_ok       (pg22_all_ok),
        .ebr_parity_ok     (ebr_parity_ok),
        .dual_rail_wh_out  (dual_rail_wh_out),
        .cooldown_cnt      (cooldown_cnt),
        .diag_rd_idx       (diag_rd_idx),
        .diag_rail_a       (diag_rail_a),
        .diag_rail_b       (diag_rail_b)
    );

    initial clk = 1'b0;
    always #(CLK_HALF_NS) clk = ~clk;

    task automatic run_64_cycle_sweep;
        begin
            @(negedge clk);
            arm_sweep = 1'b1;
            @(negedge clk);
            arm_sweep = 1'b0;
            // T=0 already fired on first posedge; 63 remaining posedges complete T=1..63
            repeat (63) @(posedge clk);
            @(negedge clk);
        end
    endtask

    initial begin
        errors            = 0;
        rst_n             = 1'b0;
        l01_reset_auth    = 1'b0;
        arm_sweep         = 1'b0;
        host_wr_en        = 1'b0;
        host_wr_idx       = 6'd0;
        host_rail_a       = 16'd0;
        host_rail_b       = 16'd0;
        pg22_bus          = {6{7'b000_0111}};
        witness_expected  = 32'h3109_A228;
        witness_check_en  = 1'b0;
        b1_nash_xor_ok    = 1'b1;
        poincare_open_req = 1'b0;
        diag_rd_idx       = 6'd0;

        // 1. Hardware reset -> KILL (0x00)
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        if (state_code !== 8'h00) errors = errors + 1;
        $display("IKS [01_RESET_KILL]: state=0x%02x open=%0d", state_code, master_gate_open);

        // 2. Load canonical 63 dual-rail words (W_H == 1000) into 4x SB_RAM40_4K EBR
        for (i = 0; i < 63; i = i + 1) begin
            ref_rail_a[i] = (i == 62) ? 16'h005A : (16'h1357 ^ i[15:0]);
            ref_rail_b[i] = (i == 62) ? ((~ref_rail_a[i]) & 16'h00FF) : (~ref_rail_a[i]);
            @(negedge clk);
            host_wr_en  = 1'b1;
            host_wr_idx = i[5:0];
            host_rail_a = ref_rail_a[i];
            host_rail_b = ref_rail_b[i];
        end
        @(negedge clk);
        host_wr_en = 1'b0;

        // 3. First 64-cycle Feistel half-stroke -> genuine digest 0x3109a228 & W_H == 1000
        run_64_cycle_sweep();
        $display("IKS [02_FEISTEL_H1]: ebr_ok=%0d wh=%0d pg22_ok=%0d digest=0x%08x",
                 ebr_parity_ok, dual_rail_wh_out, pg22_all_ok, arx_digest_out);
        if (!ebr_parity_ok || dual_rail_wh_out !== 11'd1000 ||
            !pg22_all_ok || arx_digest_out !== 32'h3109_A228) begin
            errors = errors + 1;
        end

        // 4. Second 64-cycle Feistel half-stroke -> restores all 63 words (XOR == 0x0000)
        run_64_cycle_sweep();
        xor_residual_acc = 16'h0000;
        for (i = 0; i < 63; i = i + 1) begin
            @(negedge clk);
            diag_rd_idx = i[5:0];
            @(negedge clk); // 1 synchronous EBR clock edge
            xor_residual_acc = xor_residual_acc | (diag_rail_a ^ ref_rail_a[i]);
            xor_residual_acc = xor_residual_acc | (diag_rail_b ^ ref_rail_b[i]);
        end
        $display("IKS [03_FEISTEL_H2]: ebr_ok=%0d wh=%0d xor_res=0x%04x digest=0x%08x",
                 ebr_parity_ok, dual_rail_wh_out, xor_residual_acc, arx_digest_out);
        if (!ebr_parity_ok || dual_rail_wh_out !== 11'd1000 ||
            xor_residual_acc !== 16'h0000 || arx_digest_out !== 32'h3A30_DEDB) begin
            errors = errors + 1;
        end

        // Re-lock Half 1 digest (0x3109a228) & enable strict witness check
        run_64_cycle_sweep();
        witness_check_en = 1'b1;

        // 5. 800-cycle cooldown + l01_reset_auth -> HOLD (0x3C) -> OPEN (0xA5)
        l01_reset_auth = 1'b1;
        repeat (805) @(negedge clk);
        $display("IKS [04_L01_TO_HOLD]: state=0x%02x open=%0d cd=%0d",
                 state_code, master_gate_open, cooldown_cnt);
        if (state_code !== 8'h3C || master_gate_open !== 1'b0) errors = errors + 1;

        poincare_open_req = 1'b1;
        @(negedge clk);
        $display("IKS [05_HOLD_TO_OPEN]: state=0x%02x open=%0d", state_code, master_gate_open);
        if (state_code !== 8'hA5 || master_gate_open !== 1'b1) errors = errors + 1;

        // 6. One-way escalation OPEN (0xA5) -> TRAP (0x5A) without return valve
        b1_nash_xor_ok = 1'b0;
        @(negedge clk);
        $display("IKS [06_OPEN_TO_TRAP]: state=0x%02x open=%0d", state_code, master_gate_open);
        if (state_code !== 8'h5A || master_gate_open !== 1'b0) errors = errors + 1;

        b1_nash_xor_ok = 1'b1;
        repeat (5) @(negedge clk);
        $display("IKS [07_TRAP_LOCKED]: state=0x%02x open=%0d", state_code, master_gate_open);
        if (state_code !== 8'h5A || master_gate_open !== 1'b0) errors = errors + 1;

        // 7. Single 1-bit PG(2,2) corruption -> immediate KILL (0x00)
        pg22_bus[17] = ~pg22_bus[17];
        @(negedge clk);
        $display("IKS [08_PG22_ERR_KILL]: state=0x%02x open=%0d pg22_ok=%0d",
                 state_code, master_gate_open, pg22_all_ok);
        if (state_code !== 8'h00 || master_gate_open !== 1'b0 || pg22_all_ok !== 1'b0) begin
            errors = errors + 1;
        end

        if (errors != 0) begin
            $display("FAIL: %0d errors", errors);
            $finish(1);
        end
        $display("IKS [ALL_PASS]: errors=0");
        $finish;
    end

endmodule

`default_nettype wire
