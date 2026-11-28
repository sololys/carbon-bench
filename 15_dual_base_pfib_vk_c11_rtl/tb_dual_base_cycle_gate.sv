`timescale 1ns/1ps
`default_nettype none

module tb_dual_base_cycle_gate;
    reg         clk;
    reg         rst_n;
    reg         step_en;
    reg [31:0]  rail_pos;
    reg [31:0]  rail_neg;
    reg [47:0]  q_prev_flat;
    reg [47:0]  p_prev_flat;
    reg [47:0]  q_curr_flat;
    reg [47:0]  p_curr_flat;
    reg [95:0]  nb_pz_flat;
    reg [5:0]   nb_interior_mask;
    reg [7:0]   shift_s;
    reg signed [15:0] hold_mid_qz;
    reg signed [15:0] hold_mid_pz;
    reg [15:0]  rough_max;
    reg [47:0]  xi1_q_flat;
    reg [47:0]  xi1_p_flat;
    reg [47:0]  xi2_q_flat;
    reg [47:0]  xi2_p_flat;
    reg [31:0]  c_min_area;
    reg [7:0]   kappa_q;
    reg [31:0]  r_max_sq;
    reg [31:0]  p_max_sq;
    reg signed [47:0] e_max;
    reg signed [47:0] e_fiber_prev;
    reg signed [47:0] delta_e_shed;
    reg signed [47:0] e_fiber_curr;
    reg signed [47:0] poincare_inv_ref;
    reg signed [15:0] sol_q_prev;
    reg signed [15:0] sol_w_prev;
    reg signed [15:0] sol_q_curr;
    reg signed [15:0] sol_w_curr;
    reg [31:0]  lam_ij, tau_ij, lam_jk, tau_jk, lam_ik, tau_ik;
    reg         w_ext_valid;
    reg         l01_reset_req;
    reg [31:0]  l01_token;

    wire        busy;
    wire        done_pulse;
    wire [1:0]  port_out;
    wire        actuator_open;
    wire        monitor_coupled;
    wire        kill_latched;
    wire        sigma_crossed;
    wire [9:0]  fault_mask;
    wire [31:0] step_counter;
    wire [31:0] sigma_crossings;

    dual_base_cycle_gate dut (
        .clk(clk),
        .rst_n(rst_n),
        .step_en(step_en),
        .rail_pos(rail_pos),
        .rail_neg(rail_neg),
        .q_prev_flat(q_prev_flat),
        .p_prev_flat(p_prev_flat),
        .q_curr_flat(q_curr_flat),
        .p_curr_flat(p_curr_flat),
        .nb_pz_flat(nb_pz_flat),
        .nb_interior_mask(nb_interior_mask),
        .shift_s(shift_s),
        .hold_mid_qz(hold_mid_qz),
        .hold_mid_pz(hold_mid_pz),
        .rough_max(rough_max),
        .xi1_q_flat(xi1_q_flat),
        .xi1_p_flat(xi1_p_flat),
        .xi2_q_flat(xi2_q_flat),
        .xi2_p_flat(xi2_p_flat),
        .c_min_area(c_min_area),
        .kappa_q(kappa_q),
        .r_max_sq(r_max_sq),
        .p_max_sq(p_max_sq),
        .e_max(e_max),
        .e_fiber_prev(e_fiber_prev),
        .delta_e_shed(delta_e_shed),
        .e_fiber_curr(e_fiber_curr),
        .poincare_inv_ref(poincare_inv_ref),
        .sol_q_prev(sol_q_prev),
        .sol_w_prev(sol_w_prev),
        .sol_q_curr(sol_q_curr),
        .sol_w_curr(sol_w_curr),
        .lam_ij(lam_ij),
        .tau_ij(tau_ij),
        .lam_jk(lam_jk),
        .tau_jk(tau_jk),
        .lam_ik(lam_ik),
        .tau_ik(tau_ik),
        .w_ext_valid(w_ext_valid),
        .l01_reset_req(l01_reset_req),
        .l01_token(l01_token),
        .busy(busy),
        .done_pulse(done_pulse),
        .port_out(port_out),
        .actuator_open(actuator_open),
        .monitor_coupled(monitor_coupled),
        .kill_latched(kill_latched),
        .sigma_crossed(sigma_crossed),
        .fault_mask(fault_mask),
        .step_counter(step_counter),
        .sigma_crossings(sigma_crossings)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    function [31:0] m31_mul_fn(input [31:0] a, input [31:0] b);
        reg [63:0] m;
        reg [32:0] m0, m1;
        begin
            m  = {32'd0, a} * {32'd0, b};
            m0 = {2'd0, m[30:0]} + m[63:31];
            m1 = {2'd0, m0[30:0]} + {31'd0, m0[32:31]};
            if (m1 >= 33'h07FFFFFFF)
                m31_mul_fn = m1[31:0] - 32'h7FFFFFFF;
            else
                m31_mul_fn = m1[31:0];
        end
    endfunction

    function [31:0] m31_add_fn(input [31:0] a, input [31:0] b);
        reg [32:0] s, f;
        begin
            s = {1'b0, a} + {1'b0, b};
            f = {2'd0, s[30:0]} + {31'd0, s[32:31]};
            if (f >= 33'h07FFFFFFF)
                m31_add_fn = f[31:0] - 32'h7FFFFFFF;
            else
                m31_add_fn = f[31:0];
        end
    endfunction

    task set_nominal;
        begin
            rail_pos = 32'h55AA33CC;
            rail_neg = ~32'h55AA33CC;
            q_prev_flat = {16'sd0, -16'sd2, 16'sd3};
            p_prev_flat = {16'sd5,  16'sd4, 16'sd6};
            q_curr_flat = {16'sd4, -16'sd2, 16'sd3};
            p_curr_flat = {16'sd4,  16'sd3, 16'sd3};
            nb_pz_flat  = {16'sd999, 16'sd16, 16'sd2, 16'sd6, -16'sd4, 16'sd18};
            nb_interior_mask = 6'h1F;
            shift_s     = 8'd1;
            hold_mid_qz = 16'sd4;
            hold_mid_pz = -16'sd5;
            rough_max   = 16'd10;
            xi1_q_flat  = {16'sd12, 16'sd12, 16'sd12};
            xi1_p_flat  = {16'sd2,  16'sd2,  16'sd2};
            xi2_q_flat  = {16'sd5,  16'sd5,  16'sd5};
            xi2_p_flat  = {16'sd11, 16'sd11, 16'sd11};
            c_min_area  = 32'd100;
            kappa_q     = 8'd2;
            r_max_sq    = 32'd500;
            p_max_sq    = 32'd500;
            e_max            = 48'sd100000;
            e_fiber_prev     = 48'sd50;
            delta_e_shed     = 48'sd11;
            e_fiber_curr     = 48'sd61;
            poincare_inv_ref = 48'sd153;
            sol_q_prev = 16'sd40; sol_w_prev = 16'sd25;
            sol_q_curr = 16'sd43; sol_w_curr = 16'sd27;
            lam_ij = 32'd7;  tau_ij = 32'd13;
            lam_jk = 32'd11; tau_jk = 32'd5;
            lam_ik = 32'd77; tau_ik = 32'd48;
            w_ext_valid   = 1'b0;
            l01_reset_req = 1'b0;
            l01_token     = 32'd0;
        end
    endtask

    integer v;
    initial begin
        step_en = 1'b0;
        set_nominal();
        rst_n = 1'b0;
        #20;
        rst_n = 1'b1;
        #10;

        for (v = 0; v < 20; v = v + 1) begin
            @(negedge clk);
            set_nominal();
            step_en = 1'b1;
            case (v)
                0: w_ext_valid = 1'b0;
                1: begin
                    q_prev_flat = 48'd0; p_prev_flat = 48'd0;
                    q_curr_flat = 48'd0; p_curr_flat = 48'd0;
                    nb_pz_flat  = {-16'sd777, 16'sd0, 16'sd0, 16'sd0, 16'sd0, 16'sd0};
                    hold_mid_qz = 16'sd0; hold_mid_pz = 16'sd0;
                    e_fiber_prev = 48'sd153; delta_e_shed = 48'sd0; e_fiber_curr = 48'sd153;
                    sol_q_curr = 16'sd40; sol_w_curr = 16'sd25;
                    w_ext_valid = 1'b1;
                end
                2: begin
                    w_ext_valid = 1'b1;
                    lam_ij = 32'd65537; tau_ij = 32'd2147483600;
                    lam_jk = 32'd65539; tau_jk = 32'd123456789;
                    lam_ik = m31_mul_fn(32'd65537, 32'd65539);
                    tau_ik = m31_add_fn(m31_mul_fn(32'd65537, 32'd123456789), 32'd2147483600);
                end
                3: begin w_ext_valid = 1'b1; rail_neg = rail_neg ^ 32'd1; end
                4: w_ext_valid = 1'b1;
                5: begin w_ext_valid = 1'b1; l01_reset_req = 1'b1; l01_token = 32'hDEADBEEF; end
                6: begin w_ext_valid = 1'b1; l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                7: begin w_ext_valid = 1'b1; hold_mid_qz = 16'sd503; rough_max = 16'd1000; end
                8: begin l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                9: begin nb_pz_flat[15:0] = 16'sd46; hold_mid_qz = 16'sd18; w_ext_valid = 1'b1; end
                10: begin w_ext_valid = 1'b1; l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                11: begin w_ext_valid = 1'b1; delta_e_shed = 48'sd10; e_fiber_curr = 48'sd60; end
                12: begin l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                13: begin w_ext_valid = 1'b1; poincare_inv_ref = 48'sd154; end
                14: begin l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                15: begin
                    w_ext_valid = 1'b1;
                    xi1_q_flat[31:16] = 16'sd6;  xi1_p_flat[31:16] = 16'sd3;
                    xi2_q_flat[31:16] = 16'sd12; xi2_p_flat[31:16] = 16'sd6;
                end
                16: begin l01_reset_req = 1'b1; l01_token = 32'hA55AC33C; end
                17: begin w_ext_valid = 1'b1; sol_q_curr = 16'sd38; sol_w_curr = 16'sd28; end
                18: begin
                    w_ext_valid = 1'b1; l01_reset_req = 1'b1; l01_token = 32'hA55AC33C;
                    sol_q_curr = 16'sd40; sol_w_curr = 16'sd27;
                end
                19: begin
                    w_ext_valid = 1'b1; l01_reset_req = 1'b1; l01_token = 32'hA55AC33C;
                    tau_ik = tau_ik + 32'd1;
                end
            endcase
            @(posedge clk);
            @(negedge clk);
            step_en = 1'b0;
            wait (done_pulse == 1'b1);
            @(negedge clk);
            $display("V%02d port=%0d open=%0d mon=%0d kill=%0d sig=%0d fault=0x%03x step=%0d cross=%0d",
                     v, port_out, actuator_open, monitor_coupled, kill_latched,
                     sigma_crossed, fault_mask, step_counter, sigma_crossings);
        end
        #10;
        $finish;
    end
endmodule

`default_nettype wire
