// =============================================================================
// 3D Skeletal Grothendieck Sheaf Sluice (IEEE 1800-2012 RTL)
// =============================================================================
// Cycle-exact, Yosys-iCE40UP5K-synthesizable mirror of sheaf_sluice_3d.h and
// sheaf_curry_howard.rs. Uses flat packed buses so Yosys 0.23 and iverilog
// synthesize cleanly without unpacked-array port failures.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module sheaf_sluice_3d (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         l01_reset_strobe,
    input  wire         l01_witness_ok,
    input  wire         selftest_ok,
    input  wire         eval_strobe,
    input  wire         witness_ext,

    input  wire [47:0]  center_q_flat,      // 3 x signed 16-bit: [15:0]=x, [31:16]=y, [47:32]=z
    input  wire [287:0] nb_q_flat,          // 6 x 3 x signed 16-bit: [(f*3 + a)*16 +: 16]
    input  wire signed [15:0] lattice_pitch,
    input  wire signed [15:0] max_jitter,

    input  wire [95:0]  center_flux_flat,   // 6 x signed 16-bit outward face fluxes
    input  wire [95:0]  nb_opp_flux_flat,   // 6 x signed 16-bit opposing neighbor fluxes
    input  wire signed [15:0] cell_source_q,

    input  wire [191:0] plaq_edges_flat,    // 3 x 4 x signed 16-bit loop edges

    input  wire [31:0]  center_rail_true,
    input  wire [31:0]  center_rail_comp,
    input  wire [5:0]   nb_rail_true_mask,
    input  wire [5:0]   nb_rail_comp_mask,

    output reg  [1:0]   port_out,
    output reg  [7:0]   fault_mask_out,
    output reg          kill_latched_out,
    output reg          monitor_coupled_out,
    output reg          actuator_v_en_out,
    output reg  [31:0]  out_rail_true,
    output reg  [31:0]  out_rail_comp,
    output reg  [31:0]  reset_epoch_out,
    output reg  [63:0]  cycle_out
);

    localparam [1:0] PORT_HOLD = 2'b01;
    localparam [1:0] PORT_OPEN = 2'b10;
    localparam [1:0] PORT_KILL = 2'b11;

    // Sign-extension helper from 16-bit to 20-bit (exact, zero overflow over [-32768..32767])
    wire signed [19:0] cq [0:2];
    assign cq[0] = {{4{center_q_flat[15]}}, center_q_flat[15:0]};
    assign cq[1] = {{4{center_q_flat[31]}}, center_q_flat[31:16]};
    assign cq[2] = {{4{center_q_flat[47]}}, center_q_flat[47:32]};

    wire signed [19:0] pitch_20 = {{4{lattice_pitch[15]}}, lattice_pitch};
    wire signed [19:0] jit_20   = {{4{max_jitter[15]}}, max_jitter};
    wire signed [19:0] src_20   = {{4{cell_source_q[15]}}, cell_source_q};

    // 1. Dual-rail identity check
    wire c_rail_ok  = ((center_rail_true ^ center_rail_comp) == 32'hFFFF_FFFF);
    wire nb_rail_ok = ((nb_rail_true_mask ^ nb_rail_comp_mask) == 6'b111111);
    wire fault_rail = (~c_rail_ok) | (~nb_rail_ok);

    // 2. Parameter & -32768 sentinel bounds
    wire cq_min_hit =
        (center_q_flat[15:0]  == 16'h8000) |
        (center_q_flat[31:16] == 16'h8000) |
        (center_q_flat[47:32] == 16'h8000);

    wire [17:0] nb_min_bits;
    genvar gi;
    generate
        for (gi = 0; gi < 18; gi = gi + 1) begin : gen_nb_min
            assign nb_min_bits[gi] = (nb_q_flat[gi*16 +: 16] == 16'h8000);
        end
    endgenerate

    wire param_bad = (lattice_pitch <= 16'sd0) | (max_jitter < 16'sd0) | cq_min_hit | (|nb_min_bits);

    // 3. Skeletal face flux gluing & interior divergence sum
    wire [5:0] face_flux_err;
    wire signed [19:0] cf_20 [0:5];
    generate
        for (gi = 0; gi < 6; gi = gi + 1) begin : gen_flux
            wire [15:0] cf_raw = center_flux_flat[gi*16 +: 16];
            wire [15:0] nf_raw = nb_opp_flux_flat[gi*16 +: 16];
            wire signed [19:0] cf_s = {{4{cf_raw[15]}}, cf_raw};
            wire signed [19:0] nf_s = {{4{nf_raw[15]}}, nf_raw};
            assign cf_20[gi]        = cf_s;
            assign face_flux_err[gi] = ((cf_s + nf_s) != 20'sd0);
        end
    endgenerate

    wire signed [19:0] div_sum_20 =
        cf_20[0] + cf_20[1] + cf_20[2] + cf_20[3] + cf_20[4] + cf_20[5];
    wire fault_div = (div_sum_20 != src_20);

    // 4. Full 3D metric continuity across all 6 faces x 3 axes
    wire [17:0] geom_err_bits;
    genvar gf, ga;
    generate
        for (gf = 0; gf < 6; gf = gf + 1) begin : gen_geom_face
            localparam integer NORM_AXIS = gf / 2;
            localparam integer IS_NEG    = ((gf % 2) == 0) ? 1 : 0;
            wire signed [19:0] step_20   = IS_NEG ? (-pitch_20) : pitch_20;

            for (ga = 0; ga < 3; ga = ga + 1) begin : gen_geom_axis
                wire [15:0] nq_raw         = nb_q_flat[(gf*3 + ga)*16 +: 16];
                wire signed [19:0] nq_20   = {{4{nq_raw[15]}}, nq_raw};
                wire signed [19:0] exp_20  = cq[ga] + ((ga == NORM_AXIS) ? step_20 : 20'sd0);
                wire signed [19:0] diff_20 = nq_20 - exp_20;
                wire signed [19:0] abs_20  = (diff_20 < 20'sd0) ? (-diff_20) : diff_20;
                assign geom_err_bits[gf*3 + ga] = (~param_bad) & (abs_20 > jit_20);
            end
        end
    endgenerate

    // 5. Square plaquette holonomy (XY, YZ, ZX loops)
    wire [2:0] plaq_err;
    generate
        for (gi = 0; gi < 3; gi = gi + 1) begin : gen_plaq
            wire [15:0] e0_raw = plaq_edges_flat[(gi*4 + 0)*16 +: 16];
            wire [15:0] e1_raw = plaq_edges_flat[(gi*4 + 1)*16 +: 16];
            wire [15:0] e2_raw = plaq_edges_flat[(gi*4 + 2)*16 +: 16];
            wire [15:0] e3_raw = plaq_edges_flat[(gi*4 + 3)*16 +: 16];
            wire signed [19:0] psum =
                {{4{e0_raw[15]}}, e0_raw} +
                {{4{e1_raw[15]}}, e1_raw} +
                {{4{e2_raw[15]}}, e2_raw} +
                {{4{e3_raw[15]}}, e3_raw};
            assign plaq_err[gi] = (psum != 20'sd0);
        end
    endgenerate

    wire [7:0] comb_faults = {
        2'b00,
        param_bad,
        (|plaq_err),
        (|geom_err_bits),
        fault_div,
        (|face_flux_err),
        fault_rail
    };

    always @(posedge clk) begin
        if (!rst_n) begin
            port_out            <= PORT_HOLD;
            fault_mask_out      <= 8'd0;
            kill_latched_out    <= 1'b0;
            monitor_coupled_out <= 1'b1;
            actuator_v_en_out   <= 1'b0;
            out_rail_true       <= 32'd0;
            out_rail_comp       <= 32'd0;
            reset_epoch_out     <= 32'd0;
            cycle_out           <= 64'd0;
        end else begin
            cycle_out <= cycle_out + 64'd1;

            if (l01_reset_strobe) begin
                if (l01_witness_ok && selftest_ok && (reset_epoch_out != 32'hFFFF_FFFF)) begin
                    kill_latched_out    <= 1'b0;
                    monitor_coupled_out <= 1'b1;
                    actuator_v_en_out   <= 1'b0;
                    port_out            <= PORT_HOLD;
                    fault_mask_out      <= 8'd0;
                    out_rail_true       <= 32'd0;
                    out_rail_comp       <= 32'd0;
                    reset_epoch_out     <= reset_epoch_out + 32'd1;
                end else begin
                    kill_latched_out    <= 1'b1;
                    monitor_coupled_out <= 1'b0;
                    actuator_v_en_out   <= 1'b0;
                    port_out            <= PORT_KILL;
                    out_rail_true       <= 32'd0;
                    out_rail_comp       <= 32'd0;
                end
            end else if (kill_latched_out) begin
                port_out            <= PORT_KILL;
                monitor_coupled_out <= 1'b0;
                actuator_v_en_out   <= 1'b0;
                out_rail_true       <= 32'd0;
                out_rail_comp       <= 32'd0;
            end else if (!eval_strobe) begin
                port_out            <= PORT_HOLD;
                fault_mask_out      <= 8'd0;
                monitor_coupled_out <= 1'b1;
                actuator_v_en_out   <= 1'b0;
                out_rail_true       <= 32'd0;
                out_rail_comp       <= 32'd0;
            end else if (comb_faults != 8'd0) begin
                kill_latched_out    <= 1'b1;
                monitor_coupled_out <= 1'b0;
                actuator_v_en_out   <= 1'b0;
                port_out            <= PORT_KILL;
                fault_mask_out      <= comb_faults;
                out_rail_true       <= 32'd0;
                out_rail_comp       <= 32'd0;
            end else if (!witness_ext) begin
                port_out            <= PORT_HOLD;
                fault_mask_out      <= 8'd0;
                monitor_coupled_out <= 1'b1;
                actuator_v_en_out   <= 1'b0;
                out_rail_true       <= 32'd0;
                out_rail_comp       <= 32'd0;
            end else begin
                port_out            <= PORT_OPEN;
                fault_mask_out      <= 8'd0;
                monitor_coupled_out <= 1'b1;
                actuator_v_en_out   <= 1'b1;
                out_rail_true       <= center_rail_true;
                out_rail_comp       <= center_rail_comp;
            end
        end
    end

endmodule

`default_nettype wire
