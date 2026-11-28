#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "rns_compact_nash_sluice.h"

#define NX 5u
#define NY 5u
#define NZ 5u
#define VOL (NX * NY * NZ)

static bool is_prime_u32(uint32_t n) {
    if (n < 2u || (n % 2u) == 0u) {
        return n == 2u;
    }
    for (uint32_t d = 3u; (uint64_t)d * (uint64_t)d <= (uint64_t)n; d += 2u) {
        if ((n % d) == 0u) {
            return false;
        }
    }
    return true;
}

static void build_valid_cocycle(
    c107_chart_morphism_t *ij,
    c107_chart_morphism_t *jk,
    c107_chart_morphism_t *ik
) {
    /* Exact integer affine charts over Z:
     * phi_ij(u) = 7 * u - 19
     * phi_jk(w) = -13 * w + 45
     * => (phi_ij o phi_jk)(w) = 7 * (-13 * w + 45) - 19 = -91 * w + 296 */
    if (!c107_rns_from_bounded_i64(7,    &ij->scale) ||
        !c107_rns_from_bounded_i64(-19,  &ij->shift) ||
        !c107_rns_from_bounded_i64(-13,  &jk->scale) ||
        !c107_rns_from_bounded_i64(45,   &jk->shift) ||
        !c107_rns_from_bounded_i64(-91,  &ik->scale) ||
        !c107_rns_from_bounded_i64(296,  &ik->shift)) {
        fprintf(stderr, "Failed to encode valid cocycle\n");
        exit(1);
    }
}

int main(void) {
    /* T01: Trial-division proof that all 4 pseudo-Mersenne moduli are prime */
    for (size_t c = 0u; c < C107_RNS_CHANNELS; c++) {
        uint32_t p = C107_RNS_PRIMES[c];
        uint32_t k = C107_RNS_K[c];
        if (((uint64_t)p + (uint64_t)k) != (1ULL << 31) || !is_prime_u32(p)) {
            fprintf(stderr, "T01 FAIL: non-prime modulus %u\n", p);
            return 1;
        }
        /* Cross-check division-free mul against exact uint64 `%` on edge & pseudo-random values */
        uint32_t samples[6] = {0u, 1u, 2u, 123456789u, p - 2u, p - 1u};
        for (size_t i = 0u; i < 6u; i++) {
            for (size_t j = 0u; j < 6u; j++) {
                uint32_t got = c107_mod_mul_divfree(samples[i], samples[j], p, k);
                uint32_t exp = (uint32_t)(((uint64_t)samples[i] * (uint64_t)samples[j]) % (uint64_t)p);
                if (got != exp) {
                    fprintf(stderr, "T01 FAIL: divfree mul mismatch on channel %zu\n", c);
                    return 1;
                }
            }
        }
    }

    static c107_qp_node_t src[VOL];
    static c107_qp_node_t mid[VOL];
    static c107_qp_node_t rt[VOL];

    /* Initialize 5x5x5 grid WITH NON-ZERO BOUNDARY MOMENTUM (where raw web draft failed!) */
    for (size_t z = 0u; z < NZ; z++) {
        for (size_t y = 0u; y < NY; y++) {
            for (size_t x = 0u; x < NX; x++) {
                size_t id = c107_idx3(x, y, z, NX, NY);
                src[id].q[0] = (int64_t)(x * 100u);
                src[id].q[1] = (int64_t)(y * 100u);
                src[id].q[2] = (int64_t)(z * 100u);
                if (c107_is_boundary(x, y, z, NX, NY, NZ)) {
                    /* Non-zero boundary momentum p = (+37, -19, +83) */
                    src[id].p[0] = 37;
                    src[id].p[1] = -19;
                    src[id].p[2] = 83;
                } else {
                    src[id].p[0] = 0;
                    src[id].p[1] = 0;
                    src[id].p[2] = 0;
                }
            }
        }
    }
    /* Interior impulse spike at center (2, 2, 2): L_!(p) = -72 => |3 * (-72)| = 216 */
    src[c107_idx3(2u, 2u, 2u, NX, NY)].p[0] = 12;

    if (!c107_nash_compact_step_3d(src, mid, NX, NY, NZ, 3)) {
        fprintf(stderr, "Forward compact Nash step failed\n");
        return 1;
    }

    c107_chart_morphism_t ij, jk, ik;
    build_valid_cocycle(&ij, &jk, &ik);

    /* T02: Valid RNS cocycle + non-zero boundary p + W_ext=0 -> HOLD, XOR=0, tension=216 */
    c107_sluice_verdict_t v_hold = c107_evaluate_sluice(
        &ij, &jk, &ik, src, mid, rt, NX, NY, NZ, 3, 250, false);
    if (v_hold.port_out != C107_PORT_HOLD || v_hold.xor_residual != 0u || v_hold.max_edge_tension != 216) {
        fprintf(stderr, "T02 FAIL: port=%u xor=%" PRIx64 " ten=%" PRId64 "\n",
                v_hold.port_out, v_hold.xor_residual, v_hold.max_edge_tension);
        return 1;
    }

    /* T03: Same with W_ext=1 -> OPEN */
    c107_sluice_verdict_t v_open = c107_evaluate_sluice(
        &ij, &jk, &ik, src, mid, rt, NX, NY, NZ, 3, 250, true);
    if (v_open.port_out != C107_PORT_OPEN || v_open.fault_mask != 0u) {
        fprintf(stderr, "T03 FAIL\n");
        return 1;
    }

    /* T04: Non-canonical residue spoof (`scale.res[0] = p_0 == 0 mod p_0`) -> KILL (0x02) */
    c107_chart_morphism_t ij_spoof = ij;
    ij_spoof.scale.res[0] = C107_RNS_PRIMES[0];
    c107_sluice_verdict_t v_spoof = c107_evaluate_sluice(
        &ij_spoof, &jk, &ik, src, mid, rt, NX, NY, NZ, 3, 250, true);
    if (v_spoof.port_out != C107_PORT_KILL || (v_spoof.fault_mask & C107_FAULT_RNS_NON_CANON) == 0u) {
        fprintf(stderr, "T04 FAIL\n");
        return 1;
    }

    /* T05: 1-LSB cocycle break in Z (`296 -> 297`) caught across all 4 F_p fibers -> KILL (0x08) */
    c107_chart_morphism_t ik_bad = ik;
    (void)c107_rns_from_bounded_i64(297, &ik_bad.shift);
    c107_sluice_verdict_t v_cocyc = c107_evaluate_sluice(
        &ij, &jk, &ik_bad, src, mid, rt, NX, NY, NZ, 3, 250, true);
    if (v_cocyc.port_out != C107_PORT_KILL ||
        (v_cocyc.fault_mask & C107_FAULT_RNS_COCYCLE) == 0u ||
        v_cocyc.rns_channel_faults != 0xFu) {
        fprintf(stderr, "T05 FAIL\n");
        return 1;
    }

    /* T06: Tightened tension threshold (100 < 216) -> KILL (0x40) */
    c107_sluice_verdict_t v_ten = c107_evaluate_sluice(
        &ij, &jk, &ik, src, mid, rt, NX, NY, NZ, 3, 100, true);
    if (v_ten.port_out != C107_PORT_KILL || (v_ten.fault_mask & C107_FAULT_TENSION_ROOF) == 0u) {
        fprintf(stderr, "T06 FAIL\n");
        return 1;
    }

    /* T07: 1-bit RAM corruption in mid state during HOLD stasis -> KILL (0x20, xor != 0) */
    mid[c107_idx3(1u, 2u, 2u, NX, NY)].q[1] ^= 1LL;
    c107_sluice_verdict_t v_bit = c107_evaluate_sluice(
        &ij, &jk, &ik, src, mid, rt, NX, NY, NZ, 3, 250, true);
    if (v_bit.port_out != C107_PORT_KILL ||
        (v_bit.fault_mask & C107_FAULT_MIRROR_CORRUPT) == 0u ||
        v_bit.xor_residual == 0u) {
        fprintf(stderr, "T07 FAIL\n");
        return 1;
    }

    /* T08: 3-stage dyadic cascade K = S_(0) o S_(1) o S_(2) and K^-1 = S_(2) o S_(1) o S_(0)
     *      with non-zero boundary p = (+37, -19, +83) -> exact bit-for-bit XOR == 0! */
    static c107_qp_node_t b1[VOL], b2[VOL], b3[VOL], r1[VOL], r2[VOL], r3[VOL];
    if (!c107_nash_dyadic_step_3d(src, b1, NX, NY, NZ, 2u) ||
        !c107_nash_dyadic_step_3d(b1,  b2, NX, NY, NZ, 1u) ||
        !c107_nash_dyadic_step_3d(b2,  b3, NX, NY, NZ, 0u) ||
        !c107_nash_dyadic_step_3d(b3,  r1, NX, NY, NZ, 0u) ||
        !c107_nash_dyadic_step_3d(r1,  r2, NX, NY, NZ, 1u) ||
        !c107_nash_dyadic_step_3d(r2,  r3, NX, NY, NZ, 2u)) {
        fprintf(stderr, "T08 FAIL: cascade execution failed\n");
        return 1;
    }
    uint64_t casc_xor = 0u;
    for (size_t i = 0u; i < VOL; i++) {
        for (size_t ax = 0u; ax < 3u; ax++) {
            casc_xor |= ((uint64_t)src[i].q[ax] ^ (uint64_t)r3[i].q[ax]);
            casc_xor |= ((uint64_t)src[i].p[ax] ^ (uint64_t)r3[i].p[ax]);
        }
    }
    if (casc_xor != 0u) {
        fprintf(stderr, "T08 FAIL: cascade XOR=%" PRIx64 "\n", casc_xor);
        return 1;
    }

    printf("[PASS] RNS Fiber-Product (0 div) + f_! Compact Nash Cascade: 8/8 tests PASS (0 FP).\n");
    return 0;
}
