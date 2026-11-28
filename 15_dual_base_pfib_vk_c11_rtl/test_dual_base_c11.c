/*
 * 20-Vector Torture & Fault-Injection Test Suite (ISO C11)
 * Also supports --emit-hex to verify 4-way bit-exact parity (XOR == 0)
 * against #![no_std] Rust, behavioral SystemVerilog, and iCE40UP5K gates.
 */

#include "dual_base_cycle_gate.h"
#include <stdio.h>
#include <string.h>

static c108_cycle_in_t make_nominal_frame(void) {
    c108_cycle_in_t in;
    memset(&in, 0, sizeof(in));
    in.rail_pos = 0x55AA33CCu;
    in.rail_neg = ~0x55AA33CCu;

    /* Transverse crossing step: q_prev_z = 0 -> q_curr_z = +4 with p_curr_z = +4 */
    in.q_prev[0] = 3;  in.q_prev[1] = -2; in.q_prev[2] = 0;
    in.p_prev[0] = 6;  in.p_prev[1] = 4;  in.p_prev[2] = 5;
    /* |q_prev|^2 = 9+4+0 = 13, |p_prev|^2 = 36+16+25 = 77; kappa_q = 2 -> H_prev = 77 + 26 = 103 */

    in.q_curr[0] = 3;  in.q_curr[1] = -2; in.q_curr[2] = 4;
    in.p_curr[0] = 4;  in.p_curr[1] = 4;  in.p_curr[2] = 4;
    /* |q_curr|^2 = 9+4+16 = 29, |p_curr|^2 = 16+16+16 = 48; kappa_q = 2 -> H_curr = 48 + 58 = 106
     * Wait: H_curr must be <= H_prev when delta_e_shed >= 0! Let's choose p_curr = (3, 3, 4):
     * |p_curr|^2 = 9+9+16 = 34 -> H_curr = 34 + 58 = 92; shed = 103 - 92 = +11! */
    in.p_curr[0] = 3;  in.p_curr[1] = 3;  in.p_curr[2] = 4;

    /* Compact-support HOLD mirror on z: q_prev_z = 0, p_prev_z = 5.
     * Suppose interior mask = 0x1F (nb5 is on boundary dM with wild p = +999!).
     * Interior nb0..nb4 = {10, -4, 6, 2, 16} -> sum_int = 30.
     * Forward stroke S_(s=1): lap_fwd = 30 - 6*5 = 0 -> hold_mid_qz = 0, hold_mid_pz = -5.
     * Let's pick nb0 = 18 so sum_int = 38 -> lap_fwd = 38 - 30 = +8 -> >>1 = +4 -> mid_qz = 4, mid_pz = -5! */
    in.nb_pz_raw[0] = 18;
    in.nb_pz_raw[1] = -4;
    in.nb_pz_raw[2] = 6;
    in.nb_pz_raw[3] = 2;
    in.nb_pz_raw[4] = 16;
    in.nb_pz_raw[5] = 999; /* Boundary node dM: masked to 0 by iota_! */
    in.nb_interior_mask = 0x1Fu;
    in.shift_s = 1u;
    in.hold_mid_qz = 4;
    in.hold_mid_pz = -5;
    in.rough_max = 10u;

    /* Symplectic tangent frames: area = 12*10 - 0 = 120 >= 100 in all 3 planes */
    for (int a = 0; a < 3; ++a) {
        in.xi1_q[a] = 12; in.xi1_p[a] = 2;
        in.xi2_q[a] = 5;  in.xi2_p[a] = 11; /* 12*11 - 2*5 = 122 >= 100 */
    }
    in.c_min_area = 100u;

    in.kappa_q = 2u;
    in.r_max_sq = 500u;
    in.p_max_sq = 500u;
    in.e_max = 100000LL;
    in.e_fiber_prev = 50LL;
    in.delta_e_shed = 11LL;
    in.e_fiber_curr = 61LL;
    in.poincare_inv_ref = 153LL; /* H_prev (103) + E_prev (50) == H_curr (92) + E_curr (61) == 153 */

    /* Vakhitov-Kolokolov: positive slope dQ = +3, dw = +2 -> prod = +6 > 0 */
    in.sol_q_prev = 40; in.sol_w_prev = 25;
    in.sol_q_curr = 43; in.sol_w_curr = 27;

    /* Mersenne M_31 = 2^31 - 1 cocycle:
     * phi_ij(u) = 7u + 13, phi_jk(u) = 11u + 5 -> phi_ik(u) = 77u + (7*5 + 13) = 77u + 48 */
    in.lam_ij = 7u;  in.tau_ij = 13u;
    in.lam_jk = 11u; in.tau_jk = 5u;
    in.lam_ik = 77u; in.tau_ik = 48u;

    in.w_ext_valid = false;
    in.l01_reset_req = false;
    in.l01_token = 0u;
    return in;
}

static void build_20_vectors(c108_cycle_in_t vecs[20]) {
    for (int i = 0; i < 20; ++i) {
        vecs[i] = make_nominal_frame();
    }

    /* V00: Valid frame without W_ext -> PORT_HOLD (sigma_crossed=1, crossings=1) */
    vecs[0].w_ext_valid = false;

    /* V01: Valid resting state in HOLD (q=p=0, stationary dQ=dw=0) WITH W_ext -> PORT_OPEN!
     * Proves Gromov tangent frame does NOT false-kill resting states! */
    for (int a = 0; a < 3; ++a) {
        vecs[1].q_prev[a] = 0; vecs[1].p_prev[a] = 0;
        vecs[1].q_curr[a] = 0; vecs[1].p_curr[a] = 0;
    }
    for (int d = 0; d < 6; ++d) { vecs[1].nb_pz_raw[d] = 0; }
    vecs[1].nb_pz_raw[5] = -777; /* non-zero dM momentum still masked cleanly! */
    vecs[1].hold_mid_qz = 0; vecs[1].hold_mid_pz = 0;
    vecs[1].e_fiber_prev = 153LL; vecs[1].delta_e_shed = 0LL; vecs[1].e_fiber_curr = 153LL;
    vecs[1].sol_q_curr = 40; vecs[1].sol_w_curr = 25; /* dQ=0, dw=0 allowed! */
    vecs[1].w_ext_valid = true;

    /* V02: Valid transverse crossing WITH W_ext + large Mersenne wraparound near 2^31-1 -> PORT_OPEN (crossings=2) */
    vecs[2].w_ext_valid = true;
    vecs[2].lam_ij = 65537u;
    vecs[2].tau_ij = 2147483600u;
    vecs[2].lam_jk = 65539u;
    vecs[2].tau_jk = 123456789u;
    vecs[2].lam_ik = c108_m31_mul(65537u, 65539u);
    vecs[2].tau_ik = c108_m31_add(c108_m31_mul(65537u, 123456789u), 2147483600u);

    /* V03: Dual-rail 1-bit flip -> FAULT_DUAL_RAIL -> PORT_KILL */
    vecs[3].w_ext_valid = true;
    vecs[3].rail_neg ^= 1u;

    /* V04: Sticky KILL persists on nominal frame without L01 token -> PORT_KILL */
    vecs[4].w_ext_valid = true;

    /* V05: Wrong L01 token -> remains PORT_KILL */
    vecs[5].w_ext_valid = true;
    vecs[5].l01_reset_req = true;
    vecs[5].l01_token = 0xDEADBEEFu;

    /* V06: Valid L01 reset on clean frame -> clears KILL, crossings preserved at 3, PORT_OPEN! */
    vecs[6].w_ext_valid = true;
    vecs[6].l01_reset_req = true;
    vecs[6].l01_token = C108_L01_RESET_TOKEN;

    /* V07: Unmasked boundary leak in HOLD (if mid_qz forgot iota_! on nb5=999) -> FAULT_HOLD_INV -> KILL */
    vecs[7].w_ext_valid = true;
    vecs[7].hold_mid_qz = 503; /* corrupted by unmasked dM momentum */
    vecs[7].rough_max = 1000u;

    /* V08: L01 reset recovers -> HOLD */
    vecs[8].l01_reset_req = true;
    vecs[8].l01_token = C108_L01_RESET_TOKEN;

    /* V09: Roughness spike |mid_qz - q_prev_z| = 11 > rough_max=10 -> FAULT_ROUGHNESS -> KILL */
    vecs[9].nb_pz_raw[0] = 46; /* sum_int = 66, lap_fwd = 66-30 = 36, >>1 = 18 > 10 */
    vecs[9].hold_mid_qz = 18;
    vecs[9].w_ext_valid = true;

    /* V10: L01 reset recovers -> OPEN */
    vecs[10].w_ext_valid = true;
    vecs[10].l01_reset_req = true;
    vecs[10].l01_token = C108_L01_RESET_TOKEN;

    /* V11: Unaccounted energy leak in B_1 (dH + dE != 0, non-tautological P_fib!) -> FAULT_NOETHER_LED -> KILL */
    vecs[11].w_ext_valid = true;
    vecs[11].delta_e_shed = 10LL; /* 1 unit missing! */
    vecs[11].e_fiber_curr = 60LL;

    /* V12: L01 reset recovers -> HOLD */
    vecs[12].l01_reset_req = true;
    vecs[12].l01_token = C108_L01_RESET_TOKEN;

    /* V13: Transverse Poincare invariant drift (H + E == 153 != poincare_inv_ref 154) -> FAULT_POINCARE_REF -> KILL */
    vecs[13].w_ext_valid = true;
    vecs[13].poincare_inv_ref = 154LL;

    /* V14: L01 reset recovers -> HOLD */
    vecs[14].l01_reset_req = true;
    vecs[14].l01_token = C108_L01_RESET_TOKEN;

    /* V15: Gromov symplectic pinching on y-plane (collinear tangent vectors -> area = 0 < 100) -> FAULT_GROMOV_AREA -> KILL */
    vecs[15].w_ext_valid = true;
    vecs[15].xi1_q[1] = 6;  vecs[15].xi1_p[1] = 3;
    vecs[15].xi2_q[1] = 12; vecs[15].xi2_p[1] = 6; /* 6*6 - 3*12 = 0 */

    /* V16: L01 reset recovers -> HOLD */
    vecs[16].l01_reset_req = true;
    vecs[16].l01_token = C108_L01_RESET_TOKEN;

    /* V17: Vakhitov-Kolokolov supercritical collapse (dQ = -2, dw = +3 -> prod = -6 < 0) -> FAULT_VK_COLLAPSE -> KILL */
    vecs[17].w_ext_valid = true;
    vecs[17].sol_q_curr = 38;
    vecs[17].sol_w_curr = 28;

    /* V18: L01 reset attempted WHILE Townes zero-slope fault active (dQ = 0, dw = +2) -> stays KILL! */
    vecs[18].w_ext_valid = true;
    vecs[18].l01_reset_req = true;
    vecs[18].l01_token = C108_L01_RESET_TOKEN;
    vecs[18].sol_q_curr = 40;
    vecs[18].sol_w_curr = 27;

    /* V19: Clean L01 reset + RNS cocycle non-canonical p_0 = 2^31-1 disguise check?
     * Let's make V19 clean L01 reset EXCEPT 1-LSB cocycle mismatch tau_ik + 1 -> FAULT_RNS_COCYCLE -> KILL! */
    vecs[19].w_ext_valid = true;
    vecs[19].l01_reset_req = true;
    vecs[19].l01_token = C108_L01_RESET_TOKEN;
    vecs[19].tau_ik += 1u;
}

int main(int argc, char **argv) {
    bool emit_hex = (argc > 1 && strcmp(argv[1], "--emit-hex") == 0);
    c108_cycle_in_t vecs[20];
    build_20_vectors(vecs);

    c108_state_t st;
    c108_state_init(&st);

    const uint8_t exp_port[20] = {
        C108_PORT_HOLD, /* 0 */
        C108_PORT_OPEN, /* 1 */
        C108_PORT_OPEN, /* 2 */
        C108_PORT_KILL, /* 3 */
        C108_PORT_KILL, /* 4 */
        C108_PORT_KILL, /* 5 */
        C108_PORT_OPEN, /* 6 */
        C108_PORT_KILL, /* 7 */
        C108_PORT_HOLD, /* 8 */
        C108_PORT_KILL, /* 9 */
        C108_PORT_OPEN, /* 10 */
        C108_PORT_KILL, /* 11 */
        C108_PORT_HOLD, /* 12 */
        C108_PORT_KILL, /* 13 */
        C108_PORT_HOLD, /* 14 */
        C108_PORT_KILL, /* 15 */
        C108_PORT_HOLD, /* 16 */
        C108_PORT_KILL, /* 17 */
        C108_PORT_KILL, /* 18 */
        C108_PORT_KILL  /* 19 */
    };

    const uint16_t exp_fault[20] = {
        0u,
        0u,
        0u,
        C108_FAULT_DUAL_RAIL,
        0u,
        0u,
        0u,
        C108_FAULT_HOLD_INV,
        0u,
        C108_FAULT_ROUGHNESS,
        0u,
        C108_FAULT_NOETHER_LED | C108_FAULT_POINCARE_REF,
        0u,
        C108_FAULT_POINCARE_REF,
        0u,
        C108_FAULT_GROMOV_AREA,
        0u,
        C108_FAULT_VK_COLLAPSE,
        C108_FAULT_VK_COLLAPSE,
        C108_FAULT_RNS_COCYCLE
    };

    int failed = 0;
    for (int i = 0; i < 20; ++i) {
        c108_cycle_out_t out = c108_step(&st, &vecs[i]);
        if (emit_hex) {
            printf("V%02d port=%u open=%u mon=%u kill=%u sig=%u fault=0x%03x step=%u cross=%u\n",
                   i,
                   (unsigned)out.port_out,
                   (unsigned)out.actuator_open,
                   (unsigned)out.monitor_coupled,
                   (unsigned)out.kill_latched,
                   (unsigned)out.sigma_crossed,
                   (unsigned)out.fault_mask,
                   (unsigned)out.step_counter,
                   (unsigned)out.sigma_crossings);
        }
        if (out.port_out != exp_port[i] || out.fault_mask != exp_fault[i]) {
            fprintf(stderr, "[FAIL] V%02d got port=%u fault=0x%03x, expected port=%u fault=0x%03x\n",
                    i, out.port_out, out.fault_mask, exp_port[i], exp_fault[i]);
            failed = 1;
        }
    }

    /* Verify non-erasing sigma_crossings count across resets:
     * Valid crossing frames were V00, V02, V06, V08, V10, V12, V14, V16 (8 crossings; V01 had qz=0->0) */
    if (st.sigma_crossings != 8u) {
        fprintf(stderr, "[FAIL] sigma_crossings=%u expected 8\n", st.sigma_crossings);
        failed = 1;
    }

    if (!emit_hex && failed == 0) {
        printf("[PASS] ISO C11 Dual-Base (B1 x B2) Cycle Gate: 20/20 vectors OK (sigma_crossings=8).\n");
    }
    return failed;
}
