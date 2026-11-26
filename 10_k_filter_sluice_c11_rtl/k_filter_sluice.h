#ifndef K_FILTER_SLUICE_H
#define K_FILTER_SLUICE_H

#include <stdbool.h>
#include <stdint.h>

/* ============================================================================
 * Hardened Single-Arm & Twin-Point K-Filter Sluice (L1 C11 Reference Header)
 * Arithmetic   : Exact 64-bit / 128-bit split integer logic (no IEEE-754 FP)
 * Authority    : NONE (0.00 V DC bounded software/RTL demonstrator)
 *
 * Five Welded Hardening Invariants:
 *   1. Sequential sticky kill_latched + monitor_coupled + actuator_v_en state
 *      with witnessed, non-erasing Level 01 recovery reset.
 *   2. Strict causal transition equality (valid_steps != total_steps -> KILL,
 *      closing the valid_steps > total_steps overcount loophole).
 *   3. Twos-complement INT64_MIN (-2^63) poison fence on q[3], p[3], spec_max_re
 *      preserving exact phase-mirror involution J(q, p) = (q, -p).
 *   4. Clamped integer macro-accumulator C_tilde in [0, 100 000], covariance
 *      bound lambda_bound <= lambda_max, overflow-safe 64-bit Delta_K^(s), and
 *      explicit twin-arm entry pre-gate (q_A == q_B && p_A == p_B).
 *   5. Root-free 128-bit rational kernel-drift comparison mul_u64_le without
 *      requiring compiler-specific 128-bit integer extensions.
 * ============================================================================ */

#define K_POISON_INT64_MIN  INT64_MIN
#define K_MACRO_ACCUM_MAX   (100000LL)
#define K_MACRO_STEP_GAIN   (1127LL)

typedef enum {
    PORT_HOLD = 0, /* Inner reversible space M_hold: u = 0, monitor coupled */
    PORT_OPEN = 1, /* Boundary gate dM: W_ext != 0 & all invariants green */
    PORT_KILL = 2  /* Boundary gate dM: physical detachment -> 0.00 V airgap */
} omega_port_t;

typedef enum {
    REASON_OPEN_WITNESSED     = 0,
    REASON_HOLD_NO_WITNESS    = 1,
    REASON_HOLD_PHI_RESIDUAL  = 2,
    REASON_HOLD_PREP_MISMATCH = 3,
    REASON_KILL_NULL_OR_ZERO  = 4,
    REASON_KILL_LATCHED       = 5,
    REASON_KILL_POISON_MIN    = 6,
    REASON_KILL_SPECTRAL_RE   = 7,
    REASON_KILL_HASH_CHAIN    = 8,
    REASON_KILL_CHAIN_STEPS   = 9,
    REASON_KILL_LANDAUER_DEBT = 10,
    REASON_KILL_KERNEL_DRIFT  = 11,
    REASON_KILL_COV_BOUND     = 12,
    REASON_KILL_SCORE_OVF     = 13
} k_reason_t;

typedef struct {
    int64_t  q[3];          /* 3D configuration point (x, y, z) */
    int64_t  p[3];          /* 3D dual momentum / tension (px, py, pz) */
    uint64_t norm_err_sq;   /* ||K(n) - K_ref||_F^2 */
    uint64_t norm_ref_sq;   /* ||K_ref||_F^2 > 0 */
    uint32_t valid_steps;   /* Verified transitions V_sum in K_gamma */
    uint32_t total_steps;   /* Elapsed discrete cycles T > 0 */
    uint64_t phi_res_abs;   /* Absolute conservation/field residual |phi_res| */
    uint64_t lambda_bound;  /* Integer covariance bound lambda_max(P_k) */
    int64_t  spec_max_re;   /* Max spectral real part (0 allowed in lossless HOLD) */
    uint64_t entropy_paid;  /* Realized Landauer dissipation Q_paid */
    uint64_t entropy_req;   /* Required Landauer floor Q_min */
    bool     hash_valid;    /* h_n == H(h_{n-1}, q_n) */
    bool     witness_ext;   /* External Level 01 witness W_ext != empty */
} k_arm_state_t;

typedef struct {
    uint64_t delta_num;     /* Numerator P_delta for allowed kernel drift^2 */
    uint64_t delta_den;     /* Denominator Q_delta > 0 */
    uint64_t phi_res_max;   /* Max residual for OPEN readiness */
    uint64_t lambda_max;    /* Hard upper bound on covariance eigenvalue */
    uint32_t w_k;           /* Positive integer weight w_K > 0 */
    uint32_t w_v;           /* Positive integer weight w_V > 0 */
    uint32_t w_phi;         /* Positive integer weight w_phi > 0 */
    uint32_t w_p;           /* Positive integer weight w_P > 0 */
} k_gate_cfg_t;

typedef struct {
    uint64_t     cycle;
    uint32_t     reset_epoch;
    bool         kill_latched;
    bool         monitor_coupled;
    bool         actuator_v_en;
    omega_port_t last_port;
    k_reason_t   last_reason;
    uint64_t     last_delta_k;
} k_sluice_reg_t;

static inline uint32_t k_macro_accum_step(uint32_t c_tilde, int32_t i_n) {
    int64_t base = (c_tilde > (uint32_t)K_MACRO_ACCUM_MAX)
        ? K_MACRO_ACCUM_MAX
        : (int64_t)c_tilde;
    int64_t next = base + K_MACRO_STEP_GAIN * (int64_t)i_n;
    if (next < 0LL) {
        return 0U;
    }
    if (next > K_MACRO_ACCUM_MAX) {
        return (uint32_t)K_MACRO_ACCUM_MAX;
    }
    return (uint32_t)next;
}

static inline bool mul_u64_le(uint64_t a, uint64_t b, uint64_t c, uint64_t d) {
    uint64_t a_lo = a & 0xFFFFFFFFULL, a_hi = a >> 32;
    uint64_t b_lo = b & 0xFFFFFFFFULL, b_hi = b >> 32;
    uint64_t c_lo = c & 0xFFFFFFFFULL, c_hi = c >> 32;
    uint64_t d_lo = d & 0xFFFFFFFFULL, d_hi = d >> 32;

    uint64_t ab_p0 = a_lo * b_lo;
    uint64_t ab_p1 = a_lo * b_hi;
    uint64_t ab_p2 = a_hi * b_lo;
    uint64_t ab_p3 = a_hi * b_hi;

    uint64_t ab_mid = (ab_p0 >> 32) + (ab_p1 & 0xFFFFFFFFULL) + (ab_p2 & 0xFFFFFFFFULL);
    uint64_t ab_hi  = ab_p3 + (ab_p1 >> 32) + (ab_p2 >> 32) + (ab_mid >> 32);
    uint64_t ab_lo  = (ab_mid << 32) | (ab_p0 & 0xFFFFFFFFULL);

    uint64_t cd_p0 = c_lo * d_lo;
    uint64_t cd_p1 = c_lo * d_hi;
    uint64_t cd_p2 = c_hi * d_lo;
    uint64_t cd_p3 = c_hi * d_hi;

    uint64_t cd_mid = (cd_p0 >> 32) + (cd_p1 & 0xFFFFFFFFULL) + (cd_p2 & 0xFFFFFFFFULL);
    uint64_t cd_hi  = cd_p3 + (cd_p1 >> 32) + (cd_p2 >> 32) + (cd_mid >> 32);
    uint64_t cd_lo  = (cd_mid << 32) | (cd_p0 & 0xFFFFFFFFULL);

    return (ab_hi < cd_hi) || (ab_hi == cd_hi && ab_lo <= cd_lo);
}

static inline bool k_mul_add_u64_checked(uint64_t *acc, uint32_t w, uint64_t x) {
    if (w == 0U) {
        return false;
    }
    if (x > UINT64_MAX / (uint64_t)w) {
        return false;
    }
    uint64_t prod = (uint64_t)w * x;
    if (*acc > UINT64_MAX - prod) {
        return false;
    }
    *acc += prod;
    return true;
}

static inline bool k_has_poison_min(const k_arm_state_t *s) {
    for (int i = 0; i < 3; ++i) {
        if (s->q[i] == K_POISON_INT64_MIN || s->p[i] == K_POISON_INT64_MIN) {
            return true;
        }
    }
    return (s->spec_max_re == K_POISON_INT64_MIN);
}

static inline bool k_twin_point_equal(const k_arm_state_t *a, const k_arm_state_t *b) {
    if (a == 0 || b == 0) {
        return false;
    }
    for (int i = 0; i < 3; ++i) {
        if (a->q[i] != b->q[i] || a->p[i] != b->p[i]) {
            return false;
        }
    }
    return true;
}

static inline omega_port_t k_sluice_eval_comb(
    const k_arm_state_t *s,
    const k_gate_cfg_t  *cfg,
    bool                 kill_latched_in,
    bool                 prep_match_ok,
    k_reason_t          *out_reason,
    uint64_t            *out_delta_k
) {
    uint64_t score = 0ULL;
    if (out_delta_k != 0) {
        *out_delta_k = 0ULL;
    }

    if (kill_latched_in) {
        if (out_reason != 0) *out_reason = REASON_KILL_LATCHED;
        return PORT_KILL;
    }
    if (s == 0 || cfg == 0 || s->norm_ref_sq == 0ULL || cfg->delta_den == 0ULL ||
        s->total_steps == 0U || cfg->w_k == 0U || cfg->w_v == 0U ||
        cfg->w_phi == 0U || cfg->w_p == 0U) {
        if (out_reason != 0) *out_reason = REASON_KILL_NULL_OR_ZERO;
        return PORT_KILL;
    }
    if (k_has_poison_min(s)) {
        if (out_reason != 0) *out_reason = REASON_KILL_POISON_MIN;
        return PORT_KILL;
    }
    if (s->valid_steps != s->total_steps) {
        if (out_reason != 0) *out_reason = REASON_KILL_CHAIN_STEPS;
        return PORT_KILL;
    }

    uint64_t b_chain = (uint64_t)(s->total_steps - s->valid_steps);
    bool ok_score = k_mul_add_u64_checked(&score, cfg->w_k, s->norm_err_sq)
                 && k_mul_add_u64_checked(&score, cfg->w_v, b_chain)
                 && k_mul_add_u64_checked(&score, cfg->w_phi, s->phi_res_abs)
                 && k_mul_add_u64_checked(&score, cfg->w_p, s->lambda_bound);
    if (!ok_score) {
        if (out_reason != 0) *out_reason = REASON_KILL_SCORE_OVF;
        return PORT_KILL;
    }
    if (out_delta_k != 0) {
        *out_delta_k = score;
    }

    if (s->spec_max_re > 0LL) {
        if (out_reason != 0) *out_reason = REASON_KILL_SPECTRAL_RE;
        return PORT_KILL;
    }
    if (!s->hash_valid) {
        if (out_reason != 0) *out_reason = REASON_KILL_HASH_CHAIN;
        return PORT_KILL;
    }
    if (s->entropy_paid < s->entropy_req) {
        if (out_reason != 0) *out_reason = REASON_KILL_LANDAUER_DEBT;
        return PORT_KILL;
    }
    if (!mul_u64_le(s->norm_err_sq, cfg->delta_den, cfg->delta_num, s->norm_ref_sq)) {
        if (out_reason != 0) *out_reason = REASON_KILL_KERNEL_DRIFT;
        return PORT_KILL;
    }
    if (s->lambda_bound > cfg->lambda_max) {
        if (out_reason != 0) *out_reason = REASON_KILL_COV_BOUND;
        return PORT_KILL;
    }

    if (!prep_match_ok) {
        if (out_reason != 0) *out_reason = REASON_HOLD_PREP_MISMATCH;
        return PORT_HOLD;
    }
    if (s->phi_res_abs > cfg->phi_res_max) {
        if (out_reason != 0) *out_reason = REASON_HOLD_PHI_RESIDUAL;
        return PORT_HOLD;
    }
    if (!s->witness_ext) {
        if (out_reason != 0) *out_reason = REASON_HOLD_NO_WITNESS;
        return PORT_HOLD;
    }

    if (out_reason != 0) *out_reason = REASON_OPEN_WITNESSED;
    return PORT_OPEN;
}

static inline void k_sluice_reg_init(k_sluice_reg_t *r) {
    r->cycle           = 0ULL;
    r->reset_epoch     = 0U;
    r->kill_latched    = false;
    r->monitor_coupled = true;
    r->actuator_v_en   = false;
    r->last_port       = PORT_HOLD;
    r->last_reason     = REASON_HOLD_NO_WITNESS;
    r->last_delta_k    = 0ULL;
}

static inline omega_port_t k_sluice_step(
    k_sluice_reg_t      *r,
    const k_arm_state_t *s,
    const k_gate_cfg_t  *cfg,
    bool                 prep_match_ok
) {
    k_reason_t reason  = REASON_KILL_NULL_OR_ZERO;
    uint64_t   delta_k = 0ULL;
    omega_port_t v = k_sluice_eval_comb(
        s, cfg, r->kill_latched, prep_match_ok, &reason, &delta_k
    );

    r->cycle        += 1ULL;
    r->last_port     = v;
    r->last_reason   = reason;
    r->last_delta_k  = delta_k;

    if (v == PORT_KILL) {
        r->kill_latched    = true;
        r->monitor_coupled = false;
        r->actuator_v_en   = false;
    } else if (v == PORT_OPEN) {
        r->monitor_coupled = true;
        r->actuator_v_en   = true;
    } else {
        r->monitor_coupled = true;
        r->actuator_v_en   = false;
    }
    return v;
}

static inline bool k_sluice_l01_reset(k_sluice_reg_t *r, bool witness_l01) {
    r->cycle += 1ULL;
    if (!witness_l01) {
        r->kill_latched    = true;
        r->monitor_coupled = false;
        r->actuator_v_en   = false;
        r->last_port       = PORT_KILL;
        r->last_reason     = REASON_KILL_LATCHED;
        return false;
    }
    r->reset_epoch    += 1U;
    r->kill_latched    = false;
    r->monitor_coupled = true;
    r->actuator_v_en   = false;
    r->last_port       = PORT_HOLD;
    r->last_reason     = REASON_HOLD_NO_WITNESS;
    return true;
}

#endif /* K_FILTER_SLUICE_H */
