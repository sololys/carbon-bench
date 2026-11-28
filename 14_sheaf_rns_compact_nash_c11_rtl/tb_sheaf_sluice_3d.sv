`timescale 1ns / 1ps
`default_nettype none

module tb_sheaf_sluice_3d;

    reg          clk;
    reg          rst_n;
    reg          l01_reset_strobe;
    reg          l01_witness_ok;
    reg          selftest_ok;
    reg          eval_strobe;
    reg          witness_ext;

    reg signed [15:0] cq [0:2];
    reg signed [15:0] nq [0:17];
    reg signed [15:0] lattice_pitch;
    reg signed [15:0] max_jitter;
    reg signed [15:0] cf [0:5];
    reg signed [15:0] nf [0:5];
    reg signed [15:0] cell_source_q;
    reg signed [15:0] pe [0:11];

    reg [31:0]   center_rail_true;
    reg [31:0]   center_rail_comp;
    reg [5:0]    nb_rail_true_mask;
    reg [5:0]    nb_rail_comp_mask;

    wire [47:0]  center_q_flat    = {cq[2], cq[1], cq[0]};
    wire [287:0] nb_q_flat        = {
        nq[17], nq[16], nq[15], nq[14], nq[13], nq[12],
        nq[11], nq[10], nq[9],  nq[8],  nq[7],  nq[6],
        nq[5],  nq[4],  nq[3],  nq[2],  nq[1],  nq[0]
    };
    wire [95:0]  center_flux_flat = {cf[5], cf[4], cf[3], cf[2], cf[1], cf[0]};
    wire [95:0]  nb_opp_flux_flat = {nf[5], nf[4], nf[3], nf[2], nf[1], nf[0]};
    wire [191:0] plaq_edges_flat  = {
        pe[11], pe[10], pe[9], pe[8], pe[7], pe[6],
        pe[5],  pe[4],  pe[3], pe[2], pe[1], pe[0]
    };

    wire [1:0]   port_out;
    wire [7:0]   fault_mask_out;
    wire         kill_latched_out;
    wire         monitor_coupled_out;
    wire         actuator_v_en_out;
    wire [31:0]  out_rail_true;
    wire [31:0]  out_rail_comp;
    wire [31:0]  reset_epoch_out;
    wire [63:0]  cycle_out;

    sheaf_sluice_3d dut (
        .clk                 (clk),
        .rst_n               (rst_n),
        .l01_reset_strobe    (l01_reset_strobe),
        .l01_witness_ok      (l01_witness_ok),
        .selftest_ok         (selftest_ok),
        .eval_strobe         (eval_strobe),
        .witness_ext         (witness_ext),
        .center_q_flat       (center_q_flat),
        .nb_q_flat           (nb_q_flat),
        .lattice_pitch       (lattice_pitch),
        .max_jitter          (max_jitter),
        .center_flux_flat    (center_flux_flat),
        .nb_opp_flux_flat    (nb_opp_flux_flat),
        .cell_source_q       (cell_source_q),
        .plaq_edges_flat     (plaq_edges_flat),
        .center_rail_true    (center_rail_true),
        .center_rail_comp    (center_rail_comp),
        .nb_rail_true_mask   (nb_rail_true_mask),
        .nb_rail_comp_mask   (nb_rail_comp_mask),
        .port_out            (port_out),
        .fault_mask_out      (fault_mask_out),
        .kill_latched_out    (kill_latched_out),
        .monitor_coupled_out (monitor_coupled_out),
        .actuator_v_en_out   (actuator_v_en_out),
        .out_rail_true       (out_rail_true),
        .out_rail_comp       (out_rail_comp),
        .reset_epoch_out     (reset_epoch_out),
        .cycle_out           (cycle_out)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    integer f, ax;

    task set_nominal;
        begin
            l01_reset_strobe = 1'b0;
            l01_witness_ok   = 1'b0;
            selftest_ok      = 1'b1;
            eval_strobe      = 1'b1;
            witness_ext      = 1'b1;

            cq[0] = 16'sd100;
            cq[1] = 16'sd200;
            cq[2] = -16'sd300;
            lattice_pitch = 16'sd50;
            max_jitter    = 16'sd5;

            for (f = 0; f < 6; f = f + 1) begin
                ax = f / 2;
                nq[f*3 + 0] = cq[0];
                nq[f*3 + 1] = cq[1];
                nq[f*3 + 2] = cq[2];
                nq[f*3 + ax] = cq[ax] + (((f % 2) == 0) ? -16'sd50 : 16'sd50);
            end

            cf[0] = -16'sd25; nf[0] =  16'sd25;
            cf[1] =  16'sd25; nf[1] = -16'sd25;
            cf[2] =  16'sd40; nf[2] = -16'sd40;
            cf[3] = -16'sd40; nf[3] =  16'sd40;
            cf[4] = -16'sd10; nf[4] =  16'sd10;
            cf[5] =  16'sd10; nf[5] = -16'sd10;
            cell_source_q = 16'sd0;

            pe[0] =  16'sd12; pe[1] =   16'sd8; pe[2] = -16'sd12; pe[3] =  -16'sd8;
            pe[4] =  -16'sd5; pe[5] =  16'sd19; pe[6] =   16'sd5; pe[7] = -16'sd19;
            pe[8] =  16'sd30; pe[9] = -16'sd11; pe[10] = -16'sd20; pe[11] =  16'sd1;

            center_rail_true  = 32'hCAFE_BABE;
            center_rail_comp  = 32'h3501_4541;
            nb_rail_true_mask = 6'h2A;
            nb_rail_comp_mask = 6'h15;
        end
    endtask

    task set_l01_rst(input reg w_ok, input reg st_ok);
        begin
            set_nominal();
            l01_reset_strobe = 1'b1;
            l01_witness_ok   = w_ok;
            selftest_ok      = st_ok;
            eval_strobe      = 1'b0;
        end
    endtask

    task step_and_print(input integer sid);
        begin
            @(negedge clk);
            @(posedge clk);
            #1;
            $display(
                "S%02d port=%0d fault=%02h kill=%0d mon=%0d act=%0d rail=%08h comp=%08h epoch=%0d cyc=%0d",
                sid, port_out, fault_mask_out, kill_latched_out,
                monitor_coupled_out, actuator_v_en_out,
                out_rail_true, out_rail_comp, reset_epoch_out, cycle_out
            );
        end
    endtask

    initial begin
        set_nominal();
        rst_n = 1'b0;
        @(posedge clk);
        #1;
        rst_n = 1'b1;

        set_nominal(); witness_ext = 1'b0; step_and_print(1);
        set_nominal(); step_and_print(2);

        set_nominal();
        for (f = 0; f < 6; f = f + 1) begin
            cf[f] = 16'sd5;
            nf[f] = -16'sd5;
        end
        cell_source_q = 16'sd30;
        step_and_print(3);

        set_nominal(); eval_strobe = 1'b0; step_and_print(4);
        set_nominal(); nf[5] = -16'sd9; step_and_print(5);
        set_nominal(); step_and_print(6);
        set_l01_rst(1'b0, 1'b1); step_and_print(7);
        set_l01_rst(1'b1, 1'b1); step_and_print(8);
        set_nominal(); nq[1*3 + 1] = 16'sd206; step_and_print(9);
        set_l01_rst(1'b1, 1'b1); step_and_print(10);
        set_nominal(); pe[3] = -16'sd7; step_and_print(11);
        set_l01_rst(1'b1, 1'b1); step_and_print(12);
        set_nominal(); cell_source_q = 16'sd1; step_and_print(13);
        set_l01_rst(1'b1, 1'b1); step_and_print(14);
        set_nominal(); center_rail_comp = center_rail_comp ^ 32'd1; lattice_pitch = 16'sd0; step_and_print(15);
        set_l01_rst(1'b1, 1'b1); step_and_print(16);

        $finish;
    end

endmodule

`default_nettype wire
