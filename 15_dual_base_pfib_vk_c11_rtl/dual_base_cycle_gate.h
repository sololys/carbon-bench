/*
 * Dual-Base (B1 x B2) Symplectic Viability & RTOS Cycle Gate
 * ======================================================================
 * Strict ISO C11 (-std=c11 -Wall -Wextra -Werror -pedantic -mgeneral-regs-only)
 * Zero IEEE-754 floating-point, zero hardware modulo/division, zero __int128.
 *
 * Formalizes the skew-product realization bundle B_1 |>< B_2 (GATE-100 zero
 * backreaction d(dx_{B1}/dt)/dy_{B2} == 0):
 *   - Base B_1 (Kinematic 3D Lattice): (q, p) in (Z_16^*)^3 x (Z_16^*)^3,
 *     compact-support (iota_!) dyadic HOLD involution check, and 2-vector
 *     tangent-frame symplectic capacity |omega_a(xi_1, xi_2)| >= C_min.
 *   - Base B_2 (Conservation & Modular Accounting Fiber): independently metered
 *     dissipative energy E_fiber, transverse Poincare crossing invariant I_ref,
 *     Vakhitov-Kolokolov soliton slope (dQ * dw > 0 or dQ == dw == 0), and
 *     division-free Mersenne M_31 = 2^31 - 1 affine cocycle check.
 *
 * Epistemic Boundary:
 *   INSPIRED_BY != IMPLEMENTS != PROVES | PHYSICAL_AUTHORITY = NONE
 */

#ifndef DUAL_BASE_CYCLE_GATE_H
#define DUAL_BASE_CYCLE_GATE_H

#include <stdbool.h>
#include <stdint.h>

#define C108_PORT_WIRE_FAULT 0u /* 2'b00: broken wire / uninitialized */
#define C108_PORT_HOLD       1u /* 2'b01: 0.00 V DC resting phase space */
#define C108_PORT_OPEN       2u /* 2'b10: 5.00 V DC W_ext-authorized port */
#define C108_PORT_KILL       3u /* 2'b11: 0.00 V DC monitor-decoupled latch */

#define C108_L01_RESET_TOKEN 0xA55AC33Cu
#define C108_MERSENNE_P31    0x7FFFFFFFu /* 2^31 - 1 */
#define C108_INT16_POISON    (-32768)

/* Fault bitmask (10 bits, bit-exact across C11, #![no_std] Rust, and SV RTL) */
#define C108_FAULT_DUAL_RAIL    (1u << 0) /* 0x001: rail_pos ^ rail_neg != 0xFFFFFFFF */
#define C108_FAULT_SENSOR_MIN   (1u << 1) /* 0x002: -32768 sentinel on int16 input */
#define C108_FAULT_HOLD_INV     (1u << 2) /* 0x004: S_(s)(mid_rx) ^ src != 0 in B_1 */
#define C108_FAULT_ROUGHNESS    (1u << 3) /* 0x008: |mid_qz - q_prev_z| > rough_max */
#define C108_FAULT_VIABILITY    (1u << 4) /* 0x010: |q|^2 > R^2, |p|^2 > P^2, or E out of [0,E_max] */
#define C108_FAULT_NOETHER_LED  (1u << 5) /* 0x020: dE_shed < 0, dE != dE_shed, or dH_B1 + dE_B2 != 0 */
#define C108_FAULT_POINCARE_REF (1u << 6) /* 0x040: transverse Sigma_fib H + E != I_ref */
#define C108_FAULT_GROMOV_AREA  (1u << 7) /* 0x080: |xi1_q*xi2_p - xi1_p*xi2_q| < C_min in x,y,z */
#define C108_FAULT_VK_COLLAPSE  (1u << 8) /* 0x100: Q<=0, w<=0, or !(dQ==0&&dw==0 || dQ*dw>0) */
#define C108_FAULT_RNS_COCYCLE  (1u << 9) /* 0x200: affine cocycle fault mod (2^31 - 1) */

typedef struct {
    uint32_t rail_pos;
    uint32_t rail_neg;

    /* Base B_1: 3D configuration & momentum at n-1 and n */
    int16_t q_prev[3];
    int16_t p_prev[3];
    int16_t q_curr[3];
    int16_t p_curr[3];

    /* Base B_1: Compact-support (iota_!) HOLD mirror inputs on z-channel */
    int16_t nb_pz_raw[6];
    uint8_t nb_interior_mask; /* 6-bit mask: 1 = interior, 0 = dM (iota_! masks to 0) */
    uint8_t shift_s;          /* dyadic scale shift in 0..15 */
    int16_t hold_mid_qz;
    int16_t hold_mid_pz;
    uint16_t rough_max;

    /* Base B_1: Tangent-frame perturbation vectors (xi_1, xi_2) in planes x, y, z */
    int16_t xi1_q[3];
    int16_t xi1_p[3];
    int16_t xi2_q[3];
    int16_t xi2_p[3];
    uint32_t c_min_area;

    /* Base B_1 x B_2: Fiber-lifted Poincare & Noether energy ledger */
    uint8_t kappa_q;          /* harmonic potential stiffness >= 0 */
    uint32_t r_max_sq;
    uint32_t p_max_sq;
    int64_t e_max;
    int64_t e_fiber_prev;
    int64_t delta_e_shed;     /* independently metered dissipation >= 0 */
    int64_t e_fiber_curr;
    int64_t poincare_inv_ref; /* sealed H_0 + E_0 reference on Sigma_fib */

    /* Base B_2: Vakhitov-Kolokolov bound charge Q > 0 and binding depth w > 0 */
    int16_t sol_q_prev;
    int16_t sol_w_prev;
    int16_t sol_q_curr;
    int16_t sol_w_curr;

    /* Base B_2: Division-free Mersenne M_31 = 2^31 - 1 affine cocycle triple */
    uint32_t lam_ij;
    uint32_t tau_ij;
    uint32_t lam_jk;
    uint32_t tau_jk;
    uint32_t lam_ik;
    uint32_t tau_ik;

    /* External witness & Level 01 authenticated reset */
    bool w_ext_valid;
    bool l01_reset_req;
    uint32_t l01_token;
} c108_cycle_in_t;

typedef struct {
    bool kill_latched;
    uint32_t step_counter;
    uint32_t sigma_crossings; /* non-erasing transverse Poincare crossing witness count */
} c108_state_t;

typedef struct {
    uint8_t port_out;         /* 2-bit dual-rail port */
    bool actuator_open;
    bool monitor_coupled;
    bool kill_latched;
    bool sigma_crossed;
    uint16_t fault_mask;      /* 10-bit exact fault syndrome */
    uint32_t step_counter;
    uint32_t sigma_crossings;
} c108_cycle_out_t;

static inline void c108_state_init(c108_state_t *st) {
    st->kill_latched = false;
    st->step_counter = 0u;
    st->sigma_crossings = 0u;
}

static inline uint32_t c108_abs_i32(int32_t v) {
    return (v < 0) ? (uint32_t)(-(int64_t)v) : (uint32_t)v;
}

static inline uint32_t c108_m31_add(uint32_t a, uint32_t b) {
    uint64_t s = (uint64_t)a + (uint64_t)b;
    uint64_t f = (s & 0x7FFFFFFFu) + (s >> 31);
    if (f >= (uint64_t)C108_MERSENNE_P31) {
        f -= (uint64_t)C108_MERSENNE_P31;
    }
    return (uint32_t)f;
}

static inline uint32_t c108_m31_mul(uint32_t a, uint32_t b) {
    uint64_t m  = (uint64_t)a * (uint64_t)b;
    uint64_t m0 = (m & 0x7FFFFFFFu) + (m >> 31);
    uint64_t m1 = (m0 & 0x7FFFFFFFu) + (m0 >> 31);
    if (m1 >= (uint64_t)C108_MERSENNE_P31) {
        m1 -= (uint64_t)C108_MERSENNE_P31;
    }
    return (uint32_t)m1;
}

static inline uint32_t c108_norm3_sq(const int16_t v[3]) {
    uint32_t ax = c108_abs_i32((int32_t)v[0]);
    uint32_t ay = c108_abs_i32((int32_t)v[1]);
    uint32_t az = c108_abs_i32((int32_t)v[2]);
    return (ax * ax) + (ay * ay) + (az * az);
}

static inline uint16_t c108_eval_faults(const c108_cycle_in_t *in, bool *out_sigma_cross) {
    uint32_t faults = 0u;

    /* 1. Dual-rail health check */
    if ((in->rail_pos ^ in->rail_neg) != 0xFFFFFFFFu) {
        faults |= C108_FAULT_DUAL_RAIL;
    }

    /* 2. -32768 poison sentinel check across all signed 16-bit channels */
    bool poison = false;
    for (int a = 0; a < 3; ++a) {
        if (in->q_prev[a] == C108_INT16_POISON || in->p_prev[a] == C108_INT16_POISON ||
            in->q_curr[a] == C108_INT16_POISON || in->p_curr[a] == C108_INT16_POISON ||
            in->xi1_q[a]  == C108_INT16_POISON || in->xi1_p[a]  == C108_INT16_POISON ||
            in->xi2_q[a]  == C108_INT16_POISON || in->xi2_p[a]  == C108_INT16_POISON) {
            poison = true;
        }
    }
    for (int d = 0; d < 6; ++d) {
        if (in->nb_pz_raw[d] == C108_INT16_POISON) {
            poison = true;
        }
    }
    if (in->hold_mid_qz == C108_INT16_POISON || in->hold_mid_pz == C108_INT16_POISON ||
        in->sol_q_prev  == C108_INT16_POISON || in->sol_w_prev  == C108_INT16_POISON ||
        in->sol_q_curr  == C108_INT16_POISON || in->sol_w_curr  == C108_INT16_POISON) {
        poison = true;
    }
    if (poison) {
        faults |= C108_FAULT_SENSOR_MIN;
    }

    /* 3. Base B_1 compact-support (iota_!) dyadic HOLD mirror check */
    if (in->shift_s > 15u) {
        faults |= C108_FAULT_HOLD_INV;
    } else {
        int32_t lap_mid = -6 * (int32_t)in->hold_mid_pz;
        for (unsigned d = 0u; d < 6u; ++d) {
            if ((((uint32_t)in->nb_interior_mask >> d) & 1u) != 0u) {
                /* Interior neighbor was negated by first stroke S_(s) */
                lap_mid += -(int32_t)in->nb_pz_raw[d];
            }
            /* Boundary neighbor (mask bit == 0) is zero-masked by iota_! */
        }
        uint32_t mag = c108_abs_i32(lap_mid);
        int32_t dq_back = (lap_mid < 0)
            ? -(int32_t)(mag >> in->shift_s)
            :  (int32_t)(mag >> in->shift_s);
        int32_t qz_rec = (int32_t)in->hold_mid_qz + dq_back;
        int32_t pz_rec = -(int32_t)in->hold_mid_pz;
        if (qz_rec != (int32_t)in->q_prev[2] || pz_rec != (int32_t)in->p_prev[2]) {
            faults |= C108_FAULT_HOLD_INV;
        }
    }

    uint32_t rough = c108_abs_i32((int32_t)in->hold_mid_qz - (int32_t)in->q_prev[2]);
    if (rough > (uint32_t)in->rough_max) {
        faults |= C108_FAULT_ROUGHNESS;
    }

    /* 4. Base B_1 x B_2 Viability, Noether Ledger & Transverse Poincare Section */
    uint32_t q_prev_sq = c108_norm3_sq(in->q_prev);
    uint32_t p_prev_sq = c108_norm3_sq(in->p_prev);
    uint32_t q_curr_sq = c108_norm3_sq(in->q_curr);
    uint32_t p_curr_sq = c108_norm3_sq(in->p_curr);

    if (q_curr_sq > in->r_max_sq || p_curr_sq > in->p_max_sq ||
        in->e_max < 0 || in->e_fiber_prev < 0 || in->e_fiber_curr < 0 ||
        in->e_fiber_prev > in->e_max || in->e_fiber_curr > in->e_max) {
        faults |= C108_FAULT_VIABILITY;
    }

    int64_t h_prev = (int64_t)p_prev_sq + (int64_t)in->kappa_q * (int64_t)q_prev_sq;
    int64_t h_curr = (int64_t)p_curr_sq + (int64_t)in->kappa_q * (int64_t)q_curr_sq;

    /* Guard signed 64-bit overflow before summing H + E_fiber */
    if (in->delta_e_shed < 0 || in->delta_e_shed > in->e_max) {
        faults |= C108_FAULT_NOETHER_LED;
    } else if (in->e_fiber_prev <= in->e_max && in->e_fiber_curr <= in->e_max &&
               in->e_max <= 0x1FFFFFFFFFFFFFFFLL) {
        if ((in->e_fiber_curr - in->e_fiber_prev) != in->delta_e_shed) {
            faults |= C108_FAULT_NOETHER_LED;
        }
        if ((h_curr + in->e_fiber_curr) != (h_prev + in->e_fiber_prev)) {
            faults |= C108_FAULT_NOETHER_LED;
        }
    } else {
        faults |= C108_FAULT_NOETHER_LED;
    }

    bool sigma_cross = (in->q_prev[2] <= 0) && (in->q_curr[2] > 0) && (in->p_curr[2] > 0);
    *out_sigma_cross = sigma_cross;
    if (sigma_cross && (faults & (C108_FAULT_VIABILITY | C108_FAULT_NOETHER_LED)) == 0u) {
        if ((h_curr + in->e_fiber_curr) != in->poincare_inv_ref) {
            faults |= C108_FAULT_POINCARE_REF;
        }
    } else if (sigma_cross && ((h_curr & 0x3FFFFFFFFFFFFFFFLL) + (in->e_fiber_curr & 0x3FFFFFFFFFFFFFFFLL) != in->poincare_inv_ref)) {
        faults |= C108_FAULT_POINCARE_REF;
    }

    /* 5. Base B_1 Tangent-Frame Symplectic Capacity |omega_a| >= C_min */
    for (int a = 0; a < 3; ++a) {
        int32_t term1 = (int32_t)in->xi1_q[a] * (int32_t)in->xi2_p[a];
        int32_t term2 = (int32_t)in->xi1_p[a] * (int32_t)in->xi2_q[a];
        int64_t diff  = (int64_t)term1 - (int64_t)term2;
        uint64_t area = (diff < 0) ? (uint64_t)(-diff) : (uint64_t)diff;
        if (area < (uint64_t)in->c_min_area) {
            faults |= C108_FAULT_GROMOV_AREA;
        }
    }

    /* 6. Base B_2 Vakhitov-Kolokolov Soliton Stability (w = -mu > 0, Q > 0) */
    if (in->sol_q_prev <= 0 || in->sol_w_prev <= 0 ||
        in->sol_q_curr <= 0 || in->sol_w_curr <= 0) {
        faults |= C108_FAULT_VK_COLLAPSE;
    } else {
        int64_t dq = (int64_t)in->sol_q_curr - (int64_t)in->sol_q_prev;
        int64_t dw = (int64_t)in->sol_w_curr - (int64_t)in->sol_w_prev;
        bool stationary = (dq == 0) && (dw == 0);
        bool pos_slope  = (dq * dw) > 0;
        if (!stationary && !pos_slope) {
            faults |= C108_FAULT_VK_COLLAPSE;
        }
    }

    /* 7. Base B_2 Division-Free Mersenne M_31 = 2^31 - 1 Affine Cocycle */
    if (in->lam_ij == 0u || in->lam_jk == 0u || in->lam_ik == 0u ||
        in->lam_ij >= C108_MERSENNE_P31 || in->tau_ij >= C108_MERSENNE_P31 ||
        in->lam_jk >= C108_MERSENNE_P31 || in->tau_jk >= C108_MERSENNE_P31 ||
        in->lam_ik >= C108_MERSENNE_P31 || in->tau_ik >= C108_MERSENNE_P31) {
        faults |= C108_FAULT_RNS_COCYCLE;
    } else {
        uint32_t lhs_lam = c108_m31_mul(in->lam_ij, in->lam_jk);
        uint32_t lhs_tau = c108_m31_add(c108_m31_mul(in->lam_ij, in->tau_jk), in->tau_ij);
        if (lhs_lam != in->lam_ik || lhs_tau != in->tau_ik) {
            faults |= C108_FAULT_RNS_COCYCLE;
        }
    }

    return (uint16_t)faults;
}

static inline c108_cycle_out_t c108_step(c108_state_t *st, const c108_cycle_in_t *in) {
    bool sigma_cross = false;
    uint16_t faults = c108_eval_faults(in, &sigma_cross);

    st->step_counter += 1u;

    /* Authenticated Level 01 reset clears kill_latched ONLY if current frame is fault-free;
     * witness history (sigma_crossings, step_counter) is NEVER erased. */
    if (st->kill_latched && in->l01_reset_req &&
        in->l01_token == C108_L01_RESET_TOKEN && faults == 0u) {
        st->kill_latched = false;
    }

    if (faults != 0u) {
        st->kill_latched = true;
    }

    c108_cycle_out_t out;
    out.fault_mask      = faults;
    out.kill_latched    = st->kill_latched;
    out.sigma_crossed   = (!st->kill_latched) && sigma_cross;
    out.step_counter    = st->step_counter;

    if (out.sigma_crossed) {
        st->sigma_crossings += 1u;
    }
    out.sigma_crossings = st->sigma_crossings;

    if (st->kill_latched) {
        out.port_out        = C108_PORT_KILL;
        out.actuator_open   = false;
        out.monitor_coupled = false;
    } else if (in->w_ext_valid) {
        out.port_out        = C108_PORT_OPEN;
        out.actuator_open   = true;
        out.monitor_coupled = true;
    } else {
        out.port_out        = C108_PORT_HOLD;
        out.actuator_open   = false;
        out.monitor_coupled = true;
    }

    return out;
}

#endif /* DUAL_BASE_CYCLE_GATE_H */
