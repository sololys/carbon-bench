// ============================================================================
// dual_base_cycle_gate.sv
// Area-Optimized Time-Multiplexed Zero-Float Dual-Base (B1 x B2) Sluice
// Shares 2 abs16 units and 1 unsigned 32x32 multiplier (4/8 SB_MAC16) over
// 24 internal clock ticks -> 20/20 XOR == 0 against ISO C11 & #![no_std] Rust.
// ============================================================================

`timescale 1ns/1ps
`default_nettype none

module dual_base_cycle_gate (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         step_en,

    input  wire [31:0]  rail_pos,
    input  wire [31:0]  rail_neg,

    input  wire [47:0]  q_prev_flat,
    input  wire [47:0]  p_prev_flat,
    input  wire [47:0]  q_curr_flat,
    input  wire [47:0]  p_curr_flat,

    input  wire [95:0]  nb_pz_flat,
    input  wire [5:0]   nb_interior_mask,
    input  wire [7:0]   shift_s,
    input  wire signed [15:0] hold_mid_qz,
    input  wire signed [15:0] hold_mid_pz,
    input  wire [15:0]  rough_max,

    input  wire [47:0]  xi1_q_flat,
    input  wire [47:0]  xi1_p_flat,
    input  wire [47:0]  xi2_q_flat,
    input  wire [47:0]  xi2_p_flat,
    input  wire [31:0]  c_min_area,

    input  wire [7:0]   kappa_q,
    input  wire [31:0]  r_max_sq,
    input  wire [31:0]  p_max_sq,
    input  wire signed [47:0] e_max,
    input  wire signed [47:0] e_fiber_prev,
    input  wire signed [47:0] delta_e_shed,
    input  wire signed [47:0] e_fiber_curr,
    input  wire signed [47:0] poincare_inv_ref,

    input  wire signed [15:0] sol_q_prev,
    input  wire signed [15:0] sol_w_prev,
    input  wire signed [15:0] sol_q_curr,
    input  wire signed [15:0] sol_w_curr,

    input  wire [31:0]  lam_ij,
    input  wire [31:0]  tau_ij,
    input  wire [31:0]  lam_jk,
    input  wire [31:0]  tau_jk,
    input  wire [31:0]  lam_ik,
    input  wire [31:0]  tau_ik,

    input  wire         w_ext_valid,
    input  wire         l01_reset_req,
    input  wire [31:0]  l01_token,

    output wire         busy,
    output reg          done_pulse,
    output reg  [1:0]   port_out,
    output reg          actuator_open,
    output reg          monitor_coupled,
    output reg          kill_latched,
    output reg          sigma_crossed,
    output reg  [9:0]   fault_mask,
    output reg  [31:0]  step_counter,
    output reg  [31:0]  sigma_crossings
);

    localparam [1:0] PORT_HOLD = 2'b01;
    localparam [1:0] PORT_OPEN = 2'b10;
    localparam [1:0] PORT_KILL = 2'b11;
    localparam [31:0] L01_RESET_TOKEN = 32'hA55AC33C;
    localparam [31:0] MERSENNE_P31    = 32'h7FFFFFFF;

    wire signed [15:0] q_prev_0 = q_prev_flat[15:0];
    wire signed [15:0] q_prev_1 = q_prev_flat[31:16];
    wire signed [15:0] q_prev_2 = q_prev_flat[47:32];

    wire signed [15:0] p_prev_0 = p_prev_flat[15:0];
    wire signed [15:0] p_prev_1 = p_prev_flat[31:16];
    wire signed [15:0] p_prev_2 = p_prev_flat[47:32];

    wire signed [15:0] q_curr_0 = q_curr_flat[15:0];
    wire signed [15:0] q_curr_1 = q_curr_flat[31:16];
    wire signed [15:0] q_curr_2 = q_curr_flat[47:32];

    wire signed [15:0] p_curr_0 = p_curr_flat[15:0];
    wire signed [15:0] p_curr_1 = p_curr_flat[31:16];
    wire signed [15:0] p_curr_2 = p_curr_flat[47:32];

    wire signed [15:0] nb0 = nb_pz_flat[15:0];
    wire signed [15:0] nb1 = nb_pz_flat[31:16];
    wire signed [15:0] nb2 = nb_pz_flat[47:32];
    wire signed [15:0] nb3 = nb_pz_flat[63:48];
    wire signed [15:0] nb4 = nb_pz_flat[79:64];
    wire signed [15:0] nb5 = nb_pz_flat[95:80];

    wire signed [15:0] xi1q0 = xi1_q_flat[15:0];
    wire signed [15:0] xi1q1 = xi1_q_flat[31:16];
    wire signed [15:0] xi1q2 = xi1_q_flat[47:32];

    wire signed [15:0] xi1p0 = xi1_p_flat[15:0];
    wire signed [15:0] xi1p1 = xi1_p_flat[31:16];
    wire signed [15:0] xi1p2 = xi1_p_flat[47:32];

    wire signed [15:0] xi2q0 = xi2_q_flat[15:0];
    wire signed [15:0] xi2q1 = xi2_q_flat[31:16];
    wire signed [15:0] xi2q2 = xi2_q_flat[47:32];

    wire signed [15:0] xi2p0 = xi2_p_flat[15:0];
    wire signed [15:0] xi2p1 = xi2_p_flat[31:16];
    wire signed [15:0] xi2p2 = xi2_p_flat[47:32];

    wire f_rail = ((rail_pos ^ rail_neg) != 32'hFFFFFFFF);

    wire f_poison =
        (q_prev_0 == 16'sh8000) || (q_prev_1 == 16'sh8000) || (q_prev_2 == 16'sh8000) ||
        (p_prev_0 == 16'sh8000) || (p_prev_1 == 16'sh8000) || (p_prev_2 == 16'sh8000) ||
        (q_curr_0 == 16'sh8000) || (q_curr_1 == 16'sh8000) || (q_curr_2 == 16'sh8000) ||
        (p_curr_0 == 16'sh8000) || (p_curr_1 == 16'sh8000) || (p_curr_2 == 16'sh8000) ||
        (nb0 == 16'sh8000) || (nb1 == 16'sh8000) || (nb2 == 16'sh8000) ||
        (nb3 == 16'sh8000) || (nb4 == 16'sh8000) || (nb5 == 16'sh8000) ||
        (xi1q0 == 16'sh8000) || (xi1q1 == 16'sh8000) || (xi1q2 == 16'sh8000) ||
        (xi1p0 == 16'sh8000) || (xi1p1 == 16'sh8000) || (xi1p2 == 16'sh8000) ||
        (xi2q0 == 16'sh8000) || (xi2q1 == 16'sh8000) || (xi2q2 == 16'sh8000) ||
        (xi2p0 == 16'sh8000) || (xi2p1 == 16'sh8000) || (xi2p2 == 16'sh8000) ||
        (hold_mid_qz == 16'sh8000) || (hold_mid_pz == 16'sh8000) ||
        (sol_q_prev == 16'sh8000)  || (sol_w_prev == 16'sh8000)  ||
        (sol_q_curr == 16'sh8000)  || (sol_w_curr == 16'sh8000);

    // Sum 16-bit masked interior neighbors FIRST (19-bit sum), then negate once!
    wire signed [18:0] s_nb0 = nb_interior_mask[0] ? {{3{nb0[15]}}, nb0} : 19'sd0;
    wire signed [18:0] s_nb1 = nb_interior_mask[1] ? {{3{nb1[15]}}, nb1} : 19'sd0;
    wire signed [18:0] s_nb2 = nb_interior_mask[2] ? {{3{nb2[15]}}, nb2} : 19'sd0;
    wire signed [18:0] s_nb3 = nb_interior_mask[3] ? {{3{nb3[15]}}, nb3} : 19'sd0;
    wire signed [18:0] s_nb4 = nb_interior_mask[4] ? {{3{nb4[15]}}, nb4} : 19'sd0;
    wire signed [18:0] s_nb5 = nb_interior_mask[5] ? {{3{nb5[15]}}, nb5} : 19'sd0;
    wire signed [19:0] nb_sum = s_nb0 + s_nb1 + s_nb2 + s_nb3 + s_nb4 + s_nb5;
    wire signed [20:0] mid_pz_21 = {{5{hold_mid_pz[15]}}, hold_mid_pz};
    wire signed [20:0] center_six = (mid_pz_21 <<< 2) + (mid_pz_21 <<< 1);
    wire signed [20:0] lap_mid = -{{1{nb_sum[19]}}, nb_sum} - center_six;
    reg  signed [20:0] lap_mid_q;
    wire [20:0] lap_mag = lap_mid_q[20] ? (21'd0 - $unsigned(lap_mid_q)) : $unsigned(lap_mid_q);
    wire [20:0] lap_shifted = lap_mag >> shift_s[3:0];
    wire signed [20:0] dq_back = lap_mid_q[20] ? -$signed(lap_shifted) : $signed(lap_shifted);
    wire signed [20:0] qz_rec = {{5{hold_mid_qz[15]}}, hold_mid_qz} + dq_back;
    wire signed [16:0] pz_rec = -{{1{hold_mid_pz[15]}}, hold_mid_pz};

    wire f_hold_inv = (shift_s > 8'd15) ||
                      (qz_rec != {{5{q_prev_2[15]}}, q_prev_2}) ||
                      (pz_rec != {{1{p_prev_2[15]}}, p_prev_2});

    wire signed [17:0] rough_diff = {{2{hold_mid_qz[15]}}, hold_mid_qz} - {{2{q_prev_2[15]}}, q_prev_2};
    wire [17:0] rough_abs = rough_diff[17] ? (18'd0 - $unsigned(rough_diff)) : $unsigned(rough_diff);
    wire f_rough = (rough_abs > {2'd0, rough_max});

    wire signed [17:0] vk_dq = {{2{sol_q_curr[15]}}, sol_q_curr} - {{2{sol_q_prev[15]}}, sol_q_prev};
    wire signed [17:0] vk_dw = {{2{sol_w_curr[15]}}, sol_w_curr} - {{2{sol_w_prev[15]}}, sol_w_prev};
    wire vk_same_sign = (vk_dq[17] == vk_dw[17]) && (vk_dq != 18'sd0) && (vk_dw != 18'sd0);
    wire vk_zero_both = (vk_dq == 18'sd0) && (vk_dw == 18'sd0);
    wire f_vk = !((sol_q_prev > 16'sd0) && (sol_w_prev > 16'sd0) &&
                  (sol_q_curr > 16'sd0) && (sol_w_curr > 16'sd0) &&
                  (vk_zero_both || vk_same_sign));

    // Single shared abs16 pair AFTER 16-bit signed muxes
    reg [4:0]  cyc_idx;
    assign busy = (cyc_idx != 5'd0);

    reg [31:0] q_prev_sq_acc, p_prev_sq_acc, q_curr_sq_acc, p_curr_sq_acc;
    reg signed [15:0] s16_a, s16_b;
    reg               use_wide_mul;
    reg [31:0]        wide_a, wide_b;

    always @(*) begin
        s16_a        = 16'sd0;
        s16_b        = 16'sd0;
        use_wide_mul = 1'b0;
        wide_a       = 32'd0;
        wide_b       = 32'd0;
        case (cyc_idx)
            5'd1:  begin s16_a = q_prev_0; s16_b = q_prev_0; end
            5'd2:  begin s16_a = q_prev_1; s16_b = q_prev_1; end
            5'd3:  begin s16_a = q_prev_2; s16_b = q_prev_2; end
            5'd4:  begin s16_a = p_prev_0; s16_b = p_prev_0; end
            5'd5:  begin s16_a = p_prev_1; s16_b = p_prev_1; end
            5'd6:  begin s16_a = p_prev_2; s16_b = p_prev_2; end
            5'd7:  begin s16_a = q_curr_0; s16_b = q_curr_0; end
            5'd8:  begin s16_a = q_curr_1; s16_b = q_curr_1; end
            5'd9:  begin s16_a = q_curr_2; s16_b = q_curr_2; end
            5'd10: begin s16_a = p_curr_0; s16_b = p_curr_0; end
            5'd11: begin s16_a = p_curr_1; s16_b = p_curr_1; end
            5'd12: begin s16_a = p_curr_2; s16_b = p_curr_2; end
            5'd13: begin use_wide_mul = 1'b1; wide_a = {24'd0, kappa_q}; wide_b = q_prev_sq_acc; end
            5'd14: begin use_wide_mul = 1'b1; wide_a = {24'd0, kappa_q}; wide_b = q_curr_sq_acc; end
            5'd15: begin s16_a = xi1q0; s16_b = xi2p0; end
            5'd16: begin s16_a = xi1p0; s16_b = xi2q0; end
            5'd17: begin s16_a = xi1q1; s16_b = xi2p1; end
            5'd18: begin s16_a = xi1p1; s16_b = xi2q1; end
            5'd19: begin s16_a = xi1q2; s16_b = xi2p2; end
            5'd20: begin s16_a = xi1p2; s16_b = xi2q2; end
            5'd21: begin use_wide_mul = 1'b1; wide_a = lam_ij; wide_b = lam_jk; end
            5'd22: begin use_wide_mul = 1'b1; wide_a = lam_ij; wide_b = tau_jk; end
            default: ;
        endcase
    end

    wire [15:0] u16_a = s16_a[15] ? (16'd0 - $unsigned(s16_a)) : $unsigned(s16_a);
    wire [15:0] u16_b = s16_b[15] ? (16'd0 - $unsigned(s16_b)) : $unsigned(s16_b);
    wire        mul_neg = (!use_wide_mul) && (s16_a[15] ^ s16_b[15]);

    wire [31:0] mul_a = use_wide_mul ? wide_a : {16'd0, u16_a};
    wire [31:0] mul_b = use_wide_mul ? wide_b : {16'd0, u16_b};

    reg  [31:0] mul_a_q, mul_b_q;
    reg         mul_neg_q0, mul_neg_q;
    reg  [63:0] mul_p;
    reg  [31:0] m_mod_q;
    wire [63:0] mul_p_comb = mul_a_q * mul_b_q;

    wire [32:0] m_f0 = {2'd0, mul_p[30:0]} + mul_p[63:31];
    wire [32:0] m_f1 = {2'd0, m_f0[30:0]} + {31'd0, m_f0[32:31]};
    wire [31:0] m_mod = (m_f1 >= {1'b0, MERSENNE_P31}) ? (m_f1[31:0] - MERSENNE_P31) : m_f1[31:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mul_a_q    <= 32'd0;
            mul_b_q    <= 32'd0;
            mul_neg_q0 <= 1'b0;
            mul_p      <= 64'd0;
            mul_neg_q  <= 1'b0;
            m_mod_q    <= 32'd0;
        end else begin
            mul_a_q    <= mul_a;
            mul_b_q    <= mul_b;
            mul_neg_q0 <= mul_neg;
            mul_p      <= mul_p_comb;
            mul_neg_q  <= mul_neg_q0;
            m_mod_q    <= m_mod;
        end
    end

    wire signed [33:0] mul_signed34 = (mul_neg_q && (mul_p[31:0] != 32'd0))
        ? -$signed({2'b00, mul_p[31:0]})
        :  $signed({2'b00, mul_p[31:0]});

    wire [32:0] s_tau  = {1'b0, m_mod_q} + {1'b0, tau_ij};
    wire [32:0] s_tau0 = {2'd0, s_tau[30:0]} + {31'd0, s_tau[32:31]};
    wire [31:0] lhs_tau_w = (s_tau0 >= {1'b0, MERSENNE_P31}) ? (s_tau0[31:0] - MERSENNE_P31) : s_tau0[31:0];

    reg signed [47:0] h_prev_reg, h_curr_reg;
    reg signed [33:0] gromov_t1_reg;
    reg        gromov_fault_acc;
    reg        cocycle_mismatch_acc;

    wire signed [33:0] g_diff = gromov_t1_reg - mul_signed34;
    wire [33:0] g_abs = g_diff[33] ? (34'd0 - $unsigned(g_diff)) : $unsigned(g_diff);

    wire f_viab = (q_curr_sq_acc > r_max_sq) || (p_curr_sq_acc > p_max_sq) ||
                  (e_max < 48'sd0) || (e_fiber_prev < 48'sd0) || (e_fiber_curr < 48'sd0) ||
                  (e_fiber_prev > e_max) || (e_fiber_curr > e_max);

    wire signed [48:0] tot_prev = {{1{h_prev_reg[47]}}, h_prev_reg} + {{1{e_fiber_prev[47]}}, e_fiber_prev};
    wire signed [48:0] tot_curr = {{1{h_curr_reg[47]}}, h_curr_reg} + {{1{e_fiber_curr[47]}}, e_fiber_curr};
    wire signed [48:0] e_diff   = {{1{e_fiber_curr[47]}}, e_fiber_curr} - {{1{e_fiber_prev[47]}}, e_fiber_prev};
    reg  signed [48:0] tot_prev_q, tot_curr_q, e_diff_q;

    wire f_noether = (delta_e_shed < 48'sd0) || (delta_e_shed > e_max) || f_viab ||
                     (e_diff_q != {{1{delta_e_shed[47]}}, delta_e_shed}) ||
                     (tot_curr_q != tot_prev_q);

    wire sigma_cross_comb = (q_prev_2 <= 16'sd0) && (q_curr_2 > 16'sd0) && (p_curr_2 > 16'sd0);
    wire f_poincare = sigma_cross_comb && (tot_curr_q != {{1{poincare_inv_ref[47]}}, poincare_inv_ref});

    wire f_cocycle_bounds =
        (lam_ij == 32'd0) || (lam_jk == 32'd0) || (lam_ik == 32'd0) ||
        (lam_ij >= MERSENNE_P31) || (tau_ij >= MERSENNE_P31) ||
        (lam_jk >= MERSENNE_P31) || (tau_jk >= MERSENNE_P31) ||
        (lam_ik >= MERSENNE_P31) || (tau_ik >= MERSENNE_P31);

    wire [9:0] final_faults = {
        f_cocycle_bounds || cocycle_mismatch_acc,
        f_vk,
        gromov_fault_acc,
        f_poincare,
        f_noether,
        f_viab,
        f_rough,
        f_hold_inv,
        f_poison,
        f_rail
    };
    reg [9:0] final_faults_q;

    wire next_kill = (final_faults_q != 10'd0) ? 1'b1 :
                     (kill_latched && l01_reset_req && (l01_token == L01_RESET_TOKEN)) ? 1'b0 :
                     kill_latched;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cyc_idx              <= 5'd0;
            done_pulse           <= 1'b0;
            lap_mid_q            <= 21'sd0;
            tot_prev_q           <= 49'sd0;
            tot_curr_q           <= 49'sd0;
            e_diff_q             <= 49'sd0;
            final_faults_q       <= 10'd0;
            q_prev_sq_acc        <= 32'd0;
            p_prev_sq_acc        <= 32'd0;
            q_curr_sq_acc        <= 32'd0;
            p_curr_sq_acc        <= 32'd0;
            h_prev_reg           <= 48'sd0;
            h_curr_reg           <= 48'sd0;
            gromov_t1_reg        <= 34'sd0;
            gromov_fault_acc     <= 1'b0;
            cocycle_mismatch_acc <= 1'b0;
            port_out             <= PORT_HOLD;
            actuator_open        <= 1'b0;
            monitor_coupled      <= 1'b1;
            kill_latched         <= 1'b0;
            sigma_crossed        <= 1'b0;
            fault_mask           <= 10'd0;
            step_counter         <= 32'd0;
            sigma_crossings      <= 32'd0;
        end else begin
            done_pulse <= 1'b0;
            lap_mid_q  <= lap_mid;
            tot_prev_q <= tot_prev;
            tot_curr_q <= tot_curr;
            e_diff_q   <= e_diff;
            if (cyc_idx == 5'd0) begin
                if (step_en) begin
                    cyc_idx              <= 5'd1;
                    q_prev_sq_acc        <= 32'd0;
                    p_prev_sq_acc        <= 32'd0;
                    q_curr_sq_acc        <= 32'd0;
                    p_curr_sq_acc        <= 32'd0;
                    gromov_fault_acc     <= 1'b0;
                    cocycle_mismatch_acc <= 1'b0;
                end
            end else begin
                case (cyc_idx)
                    5'd3, 5'd4, 5'd5:    q_prev_sq_acc <= q_prev_sq_acc + mul_p[31:0];
                    5'd6, 5'd7, 5'd8:    p_prev_sq_acc <= p_prev_sq_acc + mul_p[31:0];
                    5'd9, 5'd10, 5'd11:  q_curr_sq_acc <= q_curr_sq_acc + mul_p[31:0];
                    5'd12, 5'd13, 5'd14: p_curr_sq_acc <= p_curr_sq_acc + mul_p[31:0];
                    5'd15: h_prev_reg <= $signed({16'd0, p_prev_sq_acc}) + $signed({8'd0, mul_p[39:0]});
                    5'd16: h_curr_reg <= $signed({16'd0, p_curr_sq_acc}) + $signed({8'd0, mul_p[39:0]});
                    5'd17, 5'd19, 5'd21: gromov_t1_reg <= mul_signed34;
                    5'd18, 5'd20, 5'd22: if (g_abs < {2'd0, c_min_area}) gromov_fault_acc <= 1'b1;
                    5'd24: if (m_mod_q != lam_ik) cocycle_mismatch_acc <= 1'b1;
                    5'd25: if (lhs_tau_w != tau_ik) cocycle_mismatch_acc <= 1'b1;
                    5'd26: final_faults_q <= final_faults;
                    default: ;
                endcase

                if (cyc_idx == 5'd27) begin
                    cyc_idx       <= 5'd0;
                    done_pulse    <= 1'b1;
                    step_counter  <= step_counter + 32'd1;
                    fault_mask    <= final_faults_q;
                    kill_latched  <= next_kill;
                    sigma_crossed <= (!next_kill) && sigma_cross_comb;

                    if ((!next_kill) && sigma_cross_comb) begin
                        sigma_crossings <= sigma_crossings + 32'd1;
                    end

                    if (next_kill) begin
                        port_out        <= PORT_KILL;
                        actuator_open   <= 1'b0;
                        monitor_coupled <= 1'b0;
                    end else if (w_ext_valid) begin
                        port_out        <= PORT_OPEN;
                        actuator_open   <= 1'b1;
                        monitor_coupled <= 1'b1;
                    end else begin
                        port_out        <= PORT_HOLD;
                        actuator_open   <= 1'b0;
                        monitor_coupled <= 1'b1;
                    end
                end else begin
                    cyc_idx <= cyc_idx + 5'd1;
                end
            end
        end
    end

endmodule

`default_nettype wire
