#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "sheaf_sluice_3d.h"

static sheaf_sluice_input_t make_nominal_uniform(void) {
    sheaf_sluice_input_t in;
    in.l01_reset_strobe = false;
    in.l01_witness_ok   = false;
    in.selftest_ok      = true;
    in.eval_strobe      = true;
    in.witness_ext      = true;

    in.center_q[0] = 100;
    in.center_q[1] = 200;
    in.center_q[2] = -300;
    in.lattice_pitch = 50;
    in.max_jitter    = 5;

    for (int f = 0; f < 6; f++) {
        int ax = f / 2;
        int16_t step = ((f % 2) == 0) ? -50 : 50;
        in.nb_q[f][0] = in.center_q[0];
        in.nb_q[f][1] = in.center_q[1];
        in.nb_q[f][2] = in.center_q[2];
        in.nb_q[f][ax] = (int16_t)(in.center_q[ax] + step);
    }

    /* Uniform flow v = (+25, -40, +10): outward fluxes sum to 0 */
    in.center_flux[0] = -25; in.nb_opp_flux[0] =  25;
    in.center_flux[1] =  25; in.nb_opp_flux[1] = -25;
    in.center_flux[2] =  40; in.nb_opp_flux[2] = -40;
    in.center_flux[3] = -40; in.nb_opp_flux[3] =  40;
    in.center_flux[4] = -10; in.nb_opp_flux[4] =  10;
    in.center_flux[5] =  10; in.nb_opp_flux[5] = -10;
    in.cell_source_q  = 0;

    in.plaq_edges[0][0] =  12; in.plaq_edges[0][1] =   8; in.plaq_edges[0][2] = -12; in.plaq_edges[0][3] =  -8;
    in.plaq_edges[1][0] =  -5; in.plaq_edges[1][1] =  19; in.plaq_edges[1][2] =   5; in.plaq_edges[1][3] = -19;
    in.plaq_edges[2][0] =  30; in.plaq_edges[2][1] = -11; in.plaq_edges[2][2] = -20; in.plaq_edges[2][3] =   1;

    in.center_rail_true  = 0xCAFEBABEu;
    in.center_rail_comp  = 0x35014541u;
    in.nb_rail_true_mask = 0x2Au;
    in.nb_rail_comp_mask = 0x15u;
    return in;
}

static sheaf_sluice_input_t make_l01_rst(bool w_ok, bool st_ok) {
    sheaf_sluice_input_t in = make_nominal_uniform();
    in.l01_reset_strobe = true;
    in.l01_witness_ok   = w_ok;
    in.selftest_ok      = st_ok;
    in.eval_strobe      = false;
    return in;
}

static void step_print_check(
    int sid,
    sheaf_sluice_state_t *st,
    const sheaf_sluice_input_t *in,
    uint8_t exp_port,
    uint8_t exp_fault,
    bool exp_kill
) {
    sheaf_sluice_step(st, in);
    printf(
        "S%02d port=%u fault=%02x kill=%u mon=%u act=%u rail=%08" PRIx32
        " comp=%08" PRIx32 " epoch=%" PRIu32 " cyc=%" PRIu64 "\n",
        sid,
        (unsigned)st->port_out,
        (unsigned)st->fault_mask,
        st->kill_latched ? 1u : 0u,
        st->monitor_coupled ? 1u : 0u,
        st->actuator_v_en ? 1u : 0u,
        st->out_rail_true,
        st->out_rail_comp,
        st->reset_epoch,
        st->cycle_counter
    );
    if (st->port_out != exp_port || st->fault_mask != exp_fault || st->kill_latched != exp_kill) {
        fprintf(stderr, "C11 ASSERTION FAILED on S%02d\n", sid);
        exit(1);
    }
}

int main(void) {
    sheaf_sluice_state_t st;
    sheaf_sluice_reset(&st);
    sheaf_sluice_input_t in;

    /* S01: Uniform 3D flow without W_ext -> HOLD */
    in = make_nominal_uniform();
    in.witness_ext = false;
    step_print_check(1, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S02: Uniform 3D flow with W_ext -> OPEN */
    in = make_nominal_uniform();
    step_print_check(2, &st, &in, SHEAF_PORT_OPEN, 0x00u, false);

    /* S03: Non-zero radial source (+5 x 6 = +30) -> OPEN */
    in = make_nominal_uniform();
    for (int f = 0; f < 6; f++) {
        in.center_flux[f] = 5;
        in.nb_opp_flux[f] = -5;
    }
    in.cell_source_q = 30;
    step_print_check(3, &st, &in, SHEAF_PORT_OPEN, 0x00u, false);

    /* S04: Idle tick (eval_strobe=0) -> HOLD */
    in = make_nominal_uniform();
    in.eval_strobe = false;
    step_print_check(4, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S05: 1-LSB face flux mismatch on +z -> KILL (0x02) */
    in = make_nominal_uniform();
    in.nb_opp_flux[5] = -9;
    step_print_check(5, &st, &in, SHEAF_PORT_KILL, 0x02u, true);

    /* S06: Sticky KILL rejects valid cover */
    in = make_nominal_uniform();
    step_print_check(6, &st, &in, SHEAF_PORT_KILL, 0x02u, true);

    /* S07: Unauthenticated L01 reset rejected */
    in = make_l01_rst(false, true);
    step_print_check(7, &st, &in, SHEAF_PORT_KILL, 0x02u, true);

    /* S08: Authenticated L01 reset -> HOLD (epoch=1) */
    in = make_l01_rst(true, true);
    step_print_check(8, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S09: Tangential shear slip on +x neighbor along y (dy=+6 > 5) -> KILL (0x08) */
    in = make_nominal_uniform();
    in.nb_q[1][1] = 206;
    step_print_check(9, &st, &in, SHEAF_PORT_KILL, 0x08u, true);

    /* S10: Authenticated L01 reset -> HOLD (epoch=2) */
    in = make_l01_rst(true, true);
    step_print_check(10, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S11: Non-closing XY plaquette holonomy seam (sum=+1) -> KILL (0x10) */
    in = make_nominal_uniform();
    in.plaq_edges[0][3] = -7;
    step_print_check(11, &st, &in, SHEAF_PORT_KILL, 0x10u, true);

    /* S12: Authenticated L01 reset -> HOLD (epoch=3) */
    in = make_l01_rst(true, true);
    step_print_check(12, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S13: Interior divergence bubble mismatch (sum=0 != source=1) -> KILL (0x04) */
    in = make_nominal_uniform();
    in.cell_source_q = 1;
    step_print_check(13, &st, &in, SHEAF_PORT_KILL, 0x04u, true);

    /* S14: Authenticated L01 reset -> HOLD (epoch=4) */
    in = make_l01_rst(true, true);
    step_print_check(14, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    /* S15: Multi-fault (dual-rail flip 0x01 + pitch=0 0x20 -> 0x21) -> KILL */
    in = make_nominal_uniform();
    in.center_rail_comp ^= 1u;
    in.lattice_pitch = 0;
    step_print_check(15, &st, &in, SHEAF_PORT_KILL, 0x21u, true);

    /* S16: Authenticated L01 reset -> HOLD (epoch=5) */
    in = make_l01_rst(true, true);
    step_print_check(16, &st, &in, SHEAF_PORT_HOLD, 0x00u, false);

    return 0;
}
