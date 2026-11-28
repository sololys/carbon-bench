#ifndef SHEAF_SLUICE_3D_H
#define SHEAF_SLUICE_3D_H

/*
 * ============================================================================
 * 3D Skeletal Grothendieck Sheaf Sluice (FPU-Free C11)
 * ============================================================================
 * Local-to-global consistency gate over a 3D cubic cover (U_center + 6 faces):
 *   1. Dual-Rail Identity: 32-bit center word + 6-bit neighbor rail mask.
 *   2. Skeletal Face Gluing (Stokes / Newton III on U_center x_U U_f):
 *        center_flux[f] + nb_opp_flux[f] == 0   for all 6 faces (-x,+x,-y,+y,-z,+z).
 *      Admits uniform 3D flows without checkerboard lockup.
 *   3. Local Divergence Bubble (Gauss's Law inside U_center):
 *        sum_{f=0..5} center_flux[f] == cell_source_q.
 *   4. Full 3D Metric Continuity (normal AND tangential axes dx, dy, dz):
 *        |nb_q[f][a] - expected_q[f][a]| <= max_jitter   for all f in 0..5, a in 0..2.
 *   5. Plaquette Holonomy (Cech H^1 / discrete curl around XY, YZ, ZX loops):
 *        e0 + e1 + e2 + e3 == 0   for all 3 orthogonal square plaquettes.
 *   6. Consequence Law (KILL > HOLD > OPEN):
 *        PORT_HOLD (2'b01), PORT_OPEN (2'b10 iff witness_ext), PORT_KILL (2'b11 sticky).
 *
 * Epistemic Boundary: INSPIRED_BY != IMPLEMENTS != PROVES (L1/L1.5 hardware/SW).
 * ============================================================================
 */

#include <stdint.h>
#include <stdbool.h>

enum {
    SHEAF_PORT_DEAD_WIRE = 0u, /* 2'b00 wire-cut crowbar fault */
    SHEAF_PORT_HOLD      = 1u, /* 2'b01 0.00 V resting phase space */
    SHEAF_PORT_OPEN      = 2u, /* 2'b10 authorized global section */
    SHEAF_PORT_KILL      = 3u  /* 2'b11 sticky detached shutdown */
};

enum {
    SHEAF_FAULT_DUAL_RAIL     = (1u << 0), /* 0x01 */
    SHEAF_FAULT_FACE_FLUX     = (1u << 1), /* 0x02 */
    SHEAF_FAULT_DIV_BUBBLE    = (1u << 2), /* 0x04 */
    SHEAF_FAULT_GEOM_TEAR     = (1u << 3), /* 0x08 */
    SHEAF_FAULT_HOLONOMY_SEAM = (1u << 4), /* 0x10 */
    SHEAF_FAULT_PARAM_BOUNDS  = (1u << 5)  /* 0x20 */
};

typedef struct {
    bool     l01_reset_strobe;
    bool     l01_witness_ok;
    bool     selftest_ok;
    bool     eval_strobe;
    bool     witness_ext;

    int16_t  center_q[3];        /* (qx, qy, qz) */
    int16_t  nb_q[6][3];         /* 6 neighbors x 3 axes (-x,+x,-y,+y,-z,+z) */
    int16_t  lattice_pitch;      /* Nominal grid spacing > 0 */
    int16_t  max_jitter;         /* Max coordinate deviation >= 0 */

    int16_t  center_flux[6];     /* Outward face fluxes on 6 faces */
    int16_t  nb_opp_flux[6];     /* Neighbor outward flux on shared face */
    int16_t  cell_source_q;      /* Expected interior divergence sum */

    int16_t  plaq_edges[3][4];   /* XY, YZ, ZX closed 4-edge loop jumps */

    uint32_t center_rail_true;
    uint32_t center_rail_comp;
    uint8_t  nb_rail_true_mask;  /* 6-bit mask [5:0] */
    uint8_t  nb_rail_comp_mask;  /* 6-bit complement mask [5:0] */
} sheaf_sluice_input_t;

typedef struct {
    uint8_t  port_out;
    uint8_t  fault_mask;
    bool     kill_latched;
    bool     monitor_coupled;
    bool     actuator_v_en;
    uint32_t out_rail_true;
    uint32_t out_rail_comp;
    uint32_t reset_epoch;
    uint64_t cycle_counter;
} sheaf_sluice_state_t;

static inline void sheaf_sluice_reset(sheaf_sluice_state_t *st) {
    if (st == 0) {
        return;
    }
    st->port_out        = (uint8_t)SHEAF_PORT_HOLD;
    st->fault_mask      = 0u;
    st->kill_latched    = false;
    st->monitor_coupled = true;
    st->actuator_v_en   = false;
    st->out_rail_true   = 0u;
    st->out_rail_comp   = 0u;
    st->reset_epoch     = 0u;
    st->cycle_counter   = 0u;
}

static inline uint8_t sheaf_eval_comb_faults(const sheaf_sluice_input_t *in) {
    uint8_t faults = 0u;

    /* 1. Dual-rail identity check */
    bool c_rail_ok  = ((in->center_rail_true ^ in->center_rail_comp) == 0xFFFFFFFFu);
    uint8_t nb_xor  = (uint8_t)((in->nb_rail_true_mask ^ in->nb_rail_comp_mask) & 0x3Fu);
    if (!c_rail_ok || nb_xor != 0x3Fu) {
        faults |= (uint8_t)SHEAF_FAULT_DUAL_RAIL;
    }

    /* 2. Parameter & ADC rail-sentinel (-32768) bounds */
    bool param_bad = (in->lattice_pitch <= 0) || (in->max_jitter < 0);
    for (int a = 0; a < 3; a++) {
        if (in->center_q[a] == INT16_MIN) {
            param_bad = true;
        }
    }
    for (int f = 0; f < 6; f++) {
        for (int a = 0; a < 3; a++) {
            if (in->nb_q[f][a] == INT16_MIN) {
                param_bad = true;
            }
        }
    }
    if (param_bad) {
        faults |= (uint8_t)SHEAF_FAULT_PARAM_BOUNDS;
    }

    /* 3. Skeletal face flux gluing & interior divergence bubble (exact 32-bit) */
    int32_t div_sum = 0;
    for (int f = 0; f < 6; f++) {
        int32_t cf = (int32_t)in->center_flux[f];
        int32_t nf = (int32_t)in->nb_opp_flux[f];
        if ((cf + nf) != 0) {
            faults |= (uint8_t)SHEAF_FAULT_FACE_FLUX;
        }
        div_sum += cf;
    }
    if (div_sum != (int32_t)in->cell_source_q) {
        faults |= (uint8_t)SHEAF_FAULT_DIV_BUBBLE;
    }

    /* 4. Full 3D metric continuity across all 3 axes (normal + tangential) */
    if (!param_bad) {
        int32_t pitch = (int32_t)in->lattice_pitch;
        int32_t jit   = (int32_t)in->max_jitter;
        for (int f = 0; f < 6; f++) {
            int normal_axis = f / 2;
            int32_t step = ((f % 2) == 0) ? -pitch : pitch;
            for (int a = 0; a < 3; a++) {
                int32_t exp_q = (int32_t)in->center_q[a] + ((a == normal_axis) ? step : 0);
                int32_t diff  = (int32_t)in->nb_q[f][a] - exp_q;
                int32_t adiff = (diff < 0) ? -diff : diff;
                if (adiff > jit) {
                    faults |= (uint8_t)SHEAF_FAULT_GEOM_TEAR;
                }
            }
        }
    }

    /* 5. Closed square plaquette holonomy (XY, YZ, ZX loops) */
    for (int p = 0; p < 3; p++) {
        int32_t loop_sum =
            (int32_t)in->plaq_edges[p][0] +
            (int32_t)in->plaq_edges[p][1] +
            (int32_t)in->plaq_edges[p][2] +
            (int32_t)in->plaq_edges[p][3];
        if (loop_sum != 0) {
            faults |= (uint8_t)SHEAF_FAULT_HOLONOMY_SEAM;
        }
    }

    return faults;
}

static inline void sheaf_sluice_step(
    sheaf_sluice_state_t *st,
    const sheaf_sluice_input_t *in
) {
    if (st == 0 || in == 0) {
        return;
    }

    st->cycle_counter += 1u;

    if (in->l01_reset_strobe) {
        if (in->l01_witness_ok && in->selftest_ok && st->reset_epoch < 0xFFFFFFFFu) {
            st->kill_latched    = false;
            st->monitor_coupled = true;
            st->actuator_v_en   = false;
            st->port_out        = (uint8_t)SHEAF_PORT_HOLD;
            st->fault_mask      = 0u;
            st->out_rail_true   = 0u;
            st->out_rail_comp   = 0u;
            st->reset_epoch    += 1u;
        } else {
            st->kill_latched    = true;
            st->monitor_coupled = false;
            st->actuator_v_en   = false;
            st->port_out        = (uint8_t)SHEAF_PORT_KILL;
            st->out_rail_true   = 0u;
            st->out_rail_comp   = 0u;
        }
        return;
    }

    if (st->kill_latched) {
        st->port_out        = (uint8_t)SHEAF_PORT_KILL;
        st->monitor_coupled = false;
        st->actuator_v_en   = false;
        st->out_rail_true   = 0u;
        st->out_rail_comp   = 0u;
        return;
    }

    if (!in->eval_strobe) {
        st->port_out        = (uint8_t)SHEAF_PORT_HOLD;
        st->fault_mask      = 0u;
        st->monitor_coupled = true;
        st->actuator_v_en   = false;
        st->out_rail_true   = 0u;
        st->out_rail_comp   = 0u;
        return;
    }

    uint8_t faults = sheaf_eval_comb_faults(in);
    if (faults != 0u) {
        st->kill_latched    = true;
        st->monitor_coupled = false;
        st->actuator_v_en   = false;
        st->port_out        = (uint8_t)SHEAF_PORT_KILL;
        st->fault_mask      = faults;
        st->out_rail_true   = 0u;
        st->out_rail_comp   = 0u;
    } else if (!in->witness_ext) {
        st->port_out        = (uint8_t)SHEAF_PORT_HOLD;
        st->fault_mask      = 0u;
        st->monitor_coupled = true;
        st->actuator_v_en   = false;
        st->out_rail_true   = 0u;
        st->out_rail_comp   = 0u;
    } else {
        st->port_out        = (uint8_t)SHEAF_PORT_OPEN;
        st->fault_mask      = 0u;
        st->monitor_coupled = true;
        st->actuator_v_en   = true;
        st->out_rail_true   = in->center_rail_true;
        st->out_rail_comp   = in->center_rail_comp;
    }
}

#endif /* SHEAF_SLUICE_3D_H */
