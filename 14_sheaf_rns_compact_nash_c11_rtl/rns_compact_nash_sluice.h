#ifndef RNS_COMPACT_NASH_SLUICE_H
#define RNS_COMPACT_NASH_SLUICE_H

/*
 * ============================================================================
 * Division-Free Pseudo-Mersenne RNS Cocycle & f_! Compact-Support
 *              Symplectic Involution Sluice (Zero-FP, Zero-Modulo C11)
 * ============================================================================
 * Fixes six defects in raw web drafts (`rns_scheme_sluice.c` & `involutive_nash_3d.c`):
 *   1. Strict ISO C11 `-Werror -pedantic -mgeneral-regs-only` cleanliness (0 raw `__int128`).
 *   2. Division-free (zero modulo) pseudo-Mersenne reduction for all 4 primes p_c = 2^31 - k_c
 *      with k_c in {1, 19, 61, 69}.
 *   3. Canonical residue gate (`res[c] < p_c`) blocking `res[c] == p_c` (`0 mod p`) from
 *      masquerading as an invertible unit in F_p, plus explicit |x| <= 2^30 - 1 CRT bound.
 *   4. True compact-support (`f_!` / `iota_!`) zero-masking on boundary momentum `p|_{dM}`
 *      inside the discrete 3D Laplacian so S(S(x)) == x holds bit-for-bit EVEN WHEN
 *      boundary cells carry non-zero momentum `p != 0` (where the raw draft drifted by
 *      `+2 * gain * p_boundary`).
 *   5. Non-tautological mid-state HOLD verification (`nash_verify_received_mid_3d`) that
 *      detects genuine RAM bit-flips during HOLD stasis alongside edge-tension bounds.
 *   6. Canonical consequence priority `KILL > HOLD > OPEN` gated on explicit `witness_ext`.
 *
 * Epistemic Boundary: INSPIRED_BY != IMPLEMENTS != PROVES (L1 C11 verification).
 * ============================================================================
 */

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define C107_RNS_CHANNELS 4
#define C107_CRT_SAFE_MAX 1073741823LL /* 2^30 - 1: guarantees 2*B^2 << prod(p_c) ~ 2^124 */

static const uint32_t C107_RNS_PRIMES[C107_RNS_CHANNELS] = {
    2147483647u, /* 2^31 - 1  */
    2147483629u, /* 2^31 - 19 */
    2147483587u, /* 2^31 - 61 */
    2147483579u  /* 2^31 - 69 */
};

static const uint32_t C107_RNS_K[C107_RNS_CHANNELS] = {
    1u, 19u, 61u, 69u
};

enum {
    C107_PORT_HOLD = 1u,
    C107_PORT_OPEN = 2u,
    C107_PORT_KILL = 3u
};

enum {
    C107_FAULT_NULL_OR_DIM     = (1u << 0), /* 0x01 */
    C107_FAULT_RNS_NON_CANON   = (1u << 1), /* 0x02: res[c] >= p_c */
    C107_FAULT_RNS_NON_UNIT    = (1u << 2), /* 0x04: scale.res[c] == 0 */
    C107_FAULT_RNS_COCYCLE     = (1u << 3), /* 0x08: phi_ij o phi_jk != phi_ik */
    C107_FAULT_NASH_OVERFLOW   = (1u << 4), /* 0x10: arithmetic bound exceeded */
    C107_FAULT_MIRROR_CORRUPT  = (1u << 5), /* 0x20: S(mid_rx) ^ src != 0 */
    C107_FAULT_TENSION_ROOF    = (1u << 6)  /* 0x40: |q_mid - q_src| > max_tension */
};

typedef struct {
    uint32_t res[C107_RNS_CHANNELS];
} c107_rns_elem_t;

typedef struct {
    c107_rns_elem_t scale;
    c107_rns_elem_t shift;
} c107_chart_morphism_t;

typedef struct {
    int64_t q[3];
    int64_t p[3];
} c107_qp_node_t;

typedef struct {
    uint8_t  port_out;
    uint32_t fault_mask;
    uint32_t rns_channel_faults;
    uint64_t xor_residual;
    int64_t  max_edge_tension;
} c107_sluice_verdict_t;

/* Division-free addition in F_p for canonical a, b < p < 2^31 */
static inline uint32_t c107_mod_add_divfree(uint32_t a, uint32_t b, uint32_t p) {
    uint64_t s = (uint64_t)a + (uint64_t)b;
    return (s >= (uint64_t)p) ? (uint32_t)(s - (uint64_t)p) : (uint32_t)s;
}

/* Division-free multiplication in F_p for p = 2^31 - k (k <= 69) and canonical a, b < p */
static inline uint32_t c107_mod_mul_divfree(uint32_t a, uint32_t b, uint32_t p, uint32_t k) {
    uint64_t m  = (uint64_t)a * (uint64_t)b;
    uint64_t m0 = (m & 0x7FFFFFFFu) + (m >> 31) * (uint64_t)k;
    uint64_t m1 = (m0 & 0x7FFFFFFFu) + (m0 >> 31) * (uint64_t)k;
    return (m1 >= (uint64_t)p) ? (uint32_t)(m1 - (uint64_t)p) : (uint32_t)m1;
}

/* Safe projection of bounded signed integer |x| <= C107_CRT_SAFE_MAX without modulo */
static inline bool c107_rns_from_bounded_i64(int64_t x, c107_rns_elem_t *out) {
    if (out == NULL || x > C107_CRT_SAFE_MAX || x < -C107_CRT_SAFE_MAX) {
        return false;
    }
    for (size_t c = 0u; c < C107_RNS_CHANNELS; c++) {
        uint32_t p = C107_RNS_PRIMES[c];
        if (x >= 0) {
            out->res[c] = (uint32_t)x; /* |x| <= 2^30 - 1 < p_c always */
        } else {
            uint32_t mag = (uint32_t)(-x);
            out->res[c] = p - mag;
        }
    }
    return true;
}

static inline uint32_t c107_verify_rns_cocycle(
    const c107_chart_morphism_t *phi_ij,
    const c107_chart_morphism_t *phi_jk,
    const c107_chart_morphism_t *phi_ik,
    uint32_t *chan_mask_out
) {
    if (!phi_ij || !phi_jk || !phi_ik || !chan_mask_out) {
        if (chan_mask_out) {
            *chan_mask_out = 0xFu;
        }
        return C107_FAULT_NULL_OR_DIM;
    }

    uint32_t faults = 0u;
    uint32_t ch_bad = 0u;

    for (size_t c = 0u; c < C107_RNS_CHANNELS; c++) {
        uint32_t p = C107_RNS_PRIMES[c];
        uint32_t k = C107_RNS_K[c];

        uint32_t sij = phi_ij->scale.res[c];
        uint32_t sjk = phi_jk->scale.res[c];
        uint32_t sik = phi_ik->scale.res[c];
        uint32_t tij = phi_ij->shift.res[c];
        uint32_t tjk = phi_jk->shift.res[c];
        uint32_t tik = phi_ik->shift.res[c];

        /* 1. Canonical range check [0, p-1] prevents `p` masquerading as non-zero unit */
        if (sij >= p || sjk >= p || sik >= p || tij >= p || tjk >= p || tik >= p) {
            faults |= C107_FAULT_RNS_NON_CANON;
            ch_bad |= (uint32_t)(1u << c);
            continue;
        }

        /* 2. Multiplicative unit requirement in F_p^* */
        if (sij == 0u || sjk == 0u || sik == 0u) {
            faults |= C107_FAULT_RNS_NON_UNIT;
            ch_bad |= (uint32_t)(1u << c);
            continue;
        }

        /* 3. Division-free composition phi_ij o phi_jk == phi_ik */
        uint32_t comp_s = c107_mod_mul_divfree(sij, sjk, p, k);
        uint32_t prod_t = c107_mod_mul_divfree(sij, tjk, p, k);
        uint32_t comp_t = c107_mod_add_divfree(prod_t, tij, p);

        if (comp_s != sik || comp_t != tik) {
            faults |= C107_FAULT_RNS_COCYCLE;
            ch_bad |= (uint32_t)(1u << c);
        }
    }

    *chan_mask_out = ch_bad;
    return faults;
}

static inline size_t c107_idx3(size_t x, size_t y, size_t z, size_t nx, size_t ny) {
    return (z * ny + y) * nx + x;
}

static inline bool c107_is_boundary(size_t x, size_t y, size_t z, size_t nx, size_t ny, size_t nz) {
    return (x == 0u || x == nx - 1u || y == 0u || y == ny - 1u || z == 0u || z == nz - 1u);
}

/* Compact-support projection iota_!(p): returns 0 on dM so L_!(p) anti-commutes strictly! */
static inline int64_t c107_compact_p(
    const c107_qp_node_t *grid,
    size_t x, size_t y, size_t z,
    size_t nx, size_t ny, size_t nz,
    size_t ax
) {
    if (c107_is_boundary(x, y, z, nx, ny, nz)) {
        return 0;
    }
    return grid[c107_idx3(x, y, z, nx, ny)].p[ax];
}

/* Overflow-checked 64-bit step without __int128 (strict ISO C11 -pedantic) */
static inline bool c107_nash_compact_step_3d(
    const c107_qp_node_t *src,
    c107_qp_node_t *dst,
    size_t nx, size_t ny, size_t nz,
    int32_t nash_gain
) {
    if (!src || !dst || src == dst || nx < 3u || ny < 3u || nz < 3u) {
        return false;
    }
    if (nash_gain == INT32_MIN) {
        return false;
    }

    /* Limit interior |p| <= 2^28 and |q| <= 2^60 so 12 * |gain| * |p| never overflows int64_t */
    const int64_t P_BOUND = (1LL << 28);
    const int64_t Q_BOUND = (1LL << 60);

    for (size_t z = 0u; z < nz; z++) {
        for (size_t y = 0u; y < ny; y++) {
            for (size_t x = 0u; x < nx; x++) {
                size_t id = c107_idx3(x, y, z, nx, ny);
                if (c107_is_boundary(x, y, z, nx, ny, nz)) {
                    /* Boundary cells preserved intact (including arbitrary boundary p != 0!) */
                    dst[id] = src[id];
                    continue;
                }

                for (size_t ax = 0u; ax < 3u; ax++) {
                    int64_t pc = src[id].p[ax];
                    int64_t qc = src[id].q[ax];
                    if (pc > P_BOUND || pc < -P_BOUND || qc > Q_BOUND || qc < -Q_BOUND) {
                        return false;
                    }
                    int64_t pxm = c107_compact_p(src, x - 1u, y, z, nx, ny, nz, ax);
                    int64_t pxp = c107_compact_p(src, x + 1u, y, z, nx, ny, nz, ax);
                    int64_t pym = c107_compact_p(src, x, y - 1u, z, nx, ny, nz, ax);
                    int64_t pyp = c107_compact_p(src, x, y + 1u, z, nx, ny, nz, ax);
                    int64_t pzm = c107_compact_p(src, x, y, z - 1u, nx, ny, nz, ax);
                    int64_t pzp = c107_compact_p(src, x, y, z + 1u, nx, ny, nz, ax);

                    if (pxm > P_BOUND || pxm < -P_BOUND || pxp > P_BOUND || pxp < -P_BOUND ||
                        pym > P_BOUND || pym < -P_BOUND || pyp > P_BOUND || pyp < -P_BOUND ||
                        pzm > P_BOUND || pzm < -P_BOUND || pzp > P_BOUND || pzp < -P_BOUND) {
                        return false;
                    }

                    int64_t lap_compact = (pxm + pxp + pym + pyp + pzm + pzp) - 6LL * pc;
                    int64_t delta_q     = (int64_t)nash_gain * lap_compact;

                    dst[id].q[ax] = qc + delta_q;
                    dst[id].p[ax] = -pc;
                }
            }
        }
    }
    return true;
}

/* Exact dyadic shift step S_(s)(q, p) = (q + trunc0(L_!(p) / 2^s), -p) for s in 0..15 */
static inline bool c107_nash_dyadic_step_3d(
    const c107_qp_node_t *src,
    c107_qp_node_t *dst,
    size_t nx, size_t ny, size_t nz,
    uint8_t dyadic_shift
) {
    if (!src || !dst || src == dst || nx < 3u || ny < 3u || nz < 3u || dyadic_shift > 15u) {
        return false;
    }
    const int64_t P_BOUND = (1LL << 28);
    const int64_t Q_BOUND = (1LL << 60);
    int64_t div_pow2 = (int64_t)(1ULL << dyadic_shift);

    for (size_t z = 0u; z < nz; z++) {
        for (size_t y = 0u; y < ny; y++) {
            for (size_t x = 0u; x < nx; x++) {
                size_t id = c107_idx3(x, y, z, nx, ny);
                if (c107_is_boundary(x, y, z, nx, ny, nz)) {
                    dst[id] = src[id];
                    continue;
                }
                for (size_t ax = 0u; ax < 3u; ax++) {
                    int64_t pc = src[id].p[ax];
                    int64_t qc = src[id].q[ax];
                    if (pc > P_BOUND || pc < -P_BOUND || qc > Q_BOUND || qc < -Q_BOUND) {
                        return false;
                    }
                    int64_t lap = (
                        c107_compact_p(src, x - 1u, y, z, nx, ny, nz, ax) +
                        c107_compact_p(src, x + 1u, y, z, nx, ny, nz, ax) +
                        c107_compact_p(src, x, y - 1u, z, nx, ny, nz, ax) +
                        c107_compact_p(src, x, y + 1u, z, nx, ny, nz, ax) +
                        c107_compact_p(src, x, y, z - 1u, nx, ny, nz, ax) +
                        c107_compact_p(src, x, y, z + 1u, nx, ny, nz, ax)
                    ) - 6LL * pc;
                    /* Division-free symmetric truncation toward zero by power of two */
                    uint64_t mag = (lap < 0) ? (uint64_t)(-lap) : (uint64_t)lap;
                    uint64_t qmag = mag >> dyadic_shift;
                    int64_t delta_q = (lap < 0) ? -(int64_t)qmag : (int64_t)qmag;
                    (void)div_pow2;
                    dst[id].q[ax] = qc + delta_q;
                    dst[id].p[ax] = -pc;
                }
            }
        }
    }
    return true;
}

/* Combined RNS cocycle + Compact-Support Nash HOLD mirror & W_ext consequence gate */
static inline c107_sluice_verdict_t c107_evaluate_sluice(
    const c107_chart_morphism_t *phi_ij,
    const c107_chart_morphism_t *phi_jk,
    const c107_chart_morphism_t *phi_ik,
    const c107_qp_node_t *src,
    const c107_qp_node_t *mid_rx,
    c107_qp_node_t *roundtrip_buf,
    size_t nx, size_t ny, size_t nz,
    int32_t nash_gain,
    int64_t max_allowed_tension,
    bool witness_ext
) {
    c107_sluice_verdict_t v;
    v.port_out           = (uint8_t)C107_PORT_KILL;
    v.fault_mask         = 0u;
    v.rns_channel_faults = 0u;
    v.xor_residual       = 0u;
    v.max_edge_tension   = 0;

    if (!src || !mid_rx || !roundtrip_buf || max_allowed_tension < 0) {
        v.fault_mask = C107_FAULT_NULL_OR_DIM;
        return v;
    }

    v.fault_mask |= c107_verify_rns_cocycle(phi_ij, phi_jk, phi_ik, &v.rns_channel_faults);

    /* Apply second involution stroke S(mid_rx) -> roundtrip_buf to verify received HOLD state */
    if (!c107_nash_compact_step_3d(mid_rx, roundtrip_buf, nx, ny, nz, nash_gain)) {
        v.fault_mask |= C107_FAULT_NASH_OVERFLOW;
        return v;
    }

    size_t total = nx * ny * nz;
    uint64_t xor_acc = 0u;
    int64_t max_ten  = 0;

    for (size_t i = 0u; i < total; i++) {
        for (size_t ax = 0u; ax < 3u; ax++) {
            xor_acc |= ((uint64_t)src[i].q[ax] ^ (uint64_t)roundtrip_buf[i].q[ax]);
            xor_acc |= ((uint64_t)src[i].p[ax] ^ (uint64_t)roundtrip_buf[i].p[ax]);

            int64_t dq  = mid_rx[i].q[ax] - src[i].q[ax];
            int64_t adq = (dq < 0) ? -dq : dq;
            if (adq > max_ten) {
                max_ten = adq;
            }
        }
    }

    v.xor_residual     = xor_acc;
    v.max_edge_tension = max_ten;

    if (xor_acc != 0u) {
        v.fault_mask |= C107_FAULT_MIRROR_CORRUPT;
    }
    if (max_ten > max_allowed_tension) {
        v.fault_mask |= C107_FAULT_TENSION_ROOF;
    }

    if (v.fault_mask != 0u) {
        v.port_out = (uint8_t)C107_PORT_KILL;
    } else if (!witness_ext) {
        v.port_out = (uint8_t)C107_PORT_HOLD;
    } else {
        v.port_out = (uint8_t)C107_PORT_OPEN;
    }
    return v;
}

#endif /* RNS_COMPACT_NASH_SLUICE_H */
