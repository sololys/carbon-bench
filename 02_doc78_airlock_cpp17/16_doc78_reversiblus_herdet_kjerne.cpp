// 16_doc78_reversiblus_herdet_kjerne.cpp
// Herdet, UB-fri L1 C++17-referansekjerne for Dokument 78 (CARBON / 16).
//
// Grenseoppgang:
//   - Nivå: L1 (lokalt demonstrert programvare; INSPIRED_BY != IMPLEMENTS != PROVES).
//   - Vitnelogg i programvare er en append-only SHA-256-hashkjede, IKKE fysisk WORM-maskinvare.
//   - Spenning før porten (HOLD / KILL / SAFE_STOP) er strengt 0 mV (0.00 V DC);
//     5000 mV (5.00 V DC) legges kun ved verifisert GATE :: OPEN.
//
// Kompileres og verifiseres med:
//   g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic -Wconversion -Wsign-conversion
//       -fsanitize=undefined,address 16_doc78_reversiblus_herdet_kjerne.cpp -o doc78_herdet

#include <array>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace carbon::doc78 {

// ============================================================================
// 1. EKSAKT 128-BITS HELTALLSARITMETIKK OG CONSTEXPR FIPS 180-4 SHA-256
// ============================================================================

using Digest256 = std::array<uint8_t, 32>;

namespace crypto {

struct U128 {
    uint64_t hi;
    uint64_t lo;
};

constexpr bool leq(U128 a, U128 b) noexcept {
    return (a.hi < b.hi) || (a.hi == b.hi && a.lo <= b.lo);
}

constexpr U128 mul64(uint64_t u, uint64_t v) noexcept {
    const uint64_t u_lo = u & 0xFFFFFFFFULL;
    const uint64_t u_hi = u >> 32U;
    const uint64_t v_lo = v & 0xFFFFFFFFULL;
    const uint64_t v_hi = v >> 32U;

    const uint64_t p0 = u_lo * v_lo;
    const uint64_t p1 = u_lo * v_hi;
    const uint64_t p2 = u_hi * v_lo;
    const uint64_t p3 = u_hi * v_hi;

    const uint64_t mid = (p0 >> 32U) + (p1 & 0xFFFFFFFFULL) + (p2 & 0xFFFFFFFFULL);
    const uint64_t hi  = p3 + (p1 >> 32U) + (p2 >> 32U) + (mid >> 32U);
    const uint64_t lo  = (p0 & 0xFFFFFFFFULL) | (mid << 32U);
    return U128{hi, lo};
}

constexpr U128 mul128_u64(U128 a, uint64_t b) noexcept {
    const U128 low = mul64(a.lo, b);
    return U128{a.hi * b + low.hi, low.lo};
}

constexpr std::array<uint32_t, 64> generate_first_64_primes() noexcept {
    std::array<uint32_t, 64> primes{};
    std::size_t found = 0;
    for (uint32_t cand = 2; found < 64; ++cand) {
        bool is_prime = true;
        for (uint32_t div = 2; div * div <= cand; ++div) {
            if (cand % div == 0U) {
                is_prime = false;
                break;
            }
        }
        if (is_prime) {
            primes[found++] = cand;
        }
    }
    return primes;
}

constexpr uint32_t frac32_sqrt_prime(uint32_t p) noexcept {
    uint32_t m = 1;
    while ((m + 1U) * (m + 1U) <= p) {
        ++m;
    }
    uint64_t lo = 0ULL;
    uint64_t hi = 0xFFFFFFFFULL;
    const U128 target{static_cast<uint64_t>(p), 0ULL};
    while (lo < hi) {
        const uint64_t mid = lo + ((hi - lo + 1ULL) >> 1U);
        const uint64_t y   = (static_cast<uint64_t>(m) << 32U) | mid;
        if (leq(mul64(y, y), target)) {
            lo = mid;
        } else {
            hi = mid - 1ULL;
        }
    }
    return static_cast<uint32_t>(lo);
}

constexpr uint32_t frac32_cbrt_prime(uint32_t p) noexcept {
    uint32_t m = 1;
    while ((m + 1U) * (m + 1U) * (m + 1U) <= p) {
        ++m;
    }
    uint64_t lo = 0ULL;
    uint64_t hi = 0xFFFFFFFFULL;
    const U128 target{static_cast<uint64_t>(p) << 32U, 0ULL};
    while (lo < hi) {
        const uint64_t mid = lo + ((hi - lo + 1ULL) >> 1U);
        const uint64_t y   = (static_cast<uint64_t>(m) << 32U) | mid;
        const U128 sq      = mul64(y, y);
        const U128 cb      = mul128_u64(sq, y);
        if (leq(cb, target)) {
            lo = mid;
        } else {
            hi = mid - 1ULL;
        }
    }
    return static_cast<uint32_t>(lo);
}

constexpr std::array<uint32_t, 8> make_sha256_iv() noexcept {
    const auto primes = generate_first_64_primes();
    std::array<uint32_t, 8> iv{};
    for (std::size_t i = 0; i < 8; ++i) {
        iv[i] = frac32_sqrt_prime(primes[i]);
    }
    return iv;
}

constexpr std::array<uint32_t, 64> make_sha256_rc() noexcept {
    const auto primes = generate_first_64_primes();
    std::array<uint32_t, 64> rc{};
    for (std::size_t i = 0; i < 64; ++i) {
        rc[i] = frac32_cbrt_prime(primes[i]);
    }
    return rc;
}

constexpr auto kSha256IV = make_sha256_iv();
constexpr auto kSha256RC = make_sha256_rc();

constexpr uint32_t rotr32(uint32_t v, uint32_t shift) noexcept {
    return (v >> shift) | (v << (32U - shift));
}

class Sha256Engine {
public:
    static Digest256 compute(const std::vector<uint8_t>& bytes) noexcept {
        return compute(bytes.data(), bytes.size());
    }

    static Digest256 compute(const uint8_t* data, std::size_t len) noexcept {
        std::array<uint32_t, 8> state = kSha256IV;

        std::size_t offset = 0;
        while (offset + 64U <= len) {
            compress_block(state, data + offset);
            offset += 64U;
        }

        std::array<uint8_t, 128> tail{};
        const std::size_t rem = len - offset;
        for (std::size_t i = 0; i < rem; ++i) {
            tail[i] = data[offset + i];
        }
        tail[rem] = 0x80U;

        const uint64_t total_bits = static_cast<uint64_t>(len) * 8ULL;
        const std::size_t total_padded = (rem < 56U) ? 64U : 128U;
        for (std::size_t i = 0; i < 8U; ++i) {
            const unsigned shift = static_cast<unsigned>((7U - i) * 8U);
            tail[total_padded - 8U + i] = static_cast<uint8_t>((total_bits >> shift) & 0xFFU);
        }

        compress_block(state, tail.data());
        if (total_padded == 128U) {
            compress_block(state, tail.data() + 64U);
        }

        Digest256 digest{};
        for (std::size_t i = 0; i < 8U; ++i) {
            digest[4U * i + 0U] = static_cast<uint8_t>((state[i] >> 24U) & 0xFFU);
            digest[4U * i + 1U] = static_cast<uint8_t>((state[i] >> 16U) & 0xFFU);
            digest[4U * i + 2U] = static_cast<uint8_t>((state[i] >> 8U) & 0xFFU);
            digest[4U * i + 3U] = static_cast<uint8_t>(state[i] & 0xFFU);
        }
        return digest;
    }

    static std::string to_hex(const Digest256& d) {
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (uint8_t b : d) {
            oss << std::setw(2) << static_cast<unsigned>(b);
        }
        return oss.str();
    }

    static bool verify_fips_self_test() noexcept {
        // Test 1: FIPS 180-4 "abc" (full 256-bits kontroll, ikke kun første/siste ord)
        const std::array<uint8_t, 3> abc{0x61U, 0x62U, 0x63U};
        constexpr Digest256 kExpectedAbc{
            0xBAU, 0x78U, 0x16U, 0xBFU, 0x8FU, 0x01U, 0xCFU, 0xEAU,
            0x41U, 0x41U, 0x40U, 0xDEU, 0x5DU, 0xAEU, 0x22U, 0x23U,
            0xB0U, 0x03U, 0x61U, 0xA3U, 0x96U, 0x17U, 0x7AU, 0x9CU,
            0xB4U, 0x10U, 0xFFU, 0x61U, 0xF2U, 0x00U, 0x15U, 0xADU
        };
        if (compute(abc.data(), abc.size()) != kExpectedAbc) {
            return false;
        }
        // Test 2: Tom streng ""
        constexpr Digest256 kExpectedEmpty{
            0xE3U, 0xB0U, 0xC4U, 0x42U, 0x98U, 0xFCU, 0x1CU, 0x14U,
            0x9AU, 0xFBU, 0xF4U, 0xC8U, 0x99U, 0x6FU, 0xB9U, 0x24U,
            0x27U, 0xAEU, 0x41U, 0xE4U, 0x64U, 0x9BU, 0x93U, 0x4CU,
            0xA4U, 0x95U, 0x99U, 0x1BU, 0x78U, 0x52U, 0xB8U, 0x55U
        };
        return compute(nullptr, 0U) == kExpectedEmpty;
    }

private:
    static void compress_block(std::array<uint32_t, 8>& state, const uint8_t* block) noexcept {
        std::array<uint32_t, 64> w{};
        for (std::size_t i = 0; i < 16U; ++i) {
            w[i] = (static_cast<uint32_t>(block[4U * i + 0U]) << 24U) |
                   (static_cast<uint32_t>(block[4U * i + 1U]) << 16U) |
                   (static_cast<uint32_t>(block[4U * i + 2U]) << 8U)  |
                    static_cast<uint32_t>(block[4U * i + 3U]);
        }
        for (std::size_t i = 16U; i < 64U; ++i) {
            const uint32_t g0 = rotr32(w[i - 15U], 7U) ^ rotr32(w[i - 15U], 18U) ^ (w[i - 15U] >> 3U);
            const uint32_t g1 = rotr32(w[i - 2U], 17U) ^ rotr32(w[i - 2U], 19U) ^ (w[i - 2U] >> 10U);
            w[i] = w[i - 16U] + g0 + w[i - 7U] + g1;
        }

        uint32_t a = state[0];
        uint32_t b = state[1];
        uint32_t c = state[2];
        uint32_t d = state[3];
        uint32_t e = state[4];
        uint32_t f = state[5];
        uint32_t g = state[6];
        uint32_t h = state[7];

        for (std::size_t i = 0; i < 64U; ++i) {
            const uint32_t sum1 = rotr32(e, 6U) ^ rotr32(e, 11U) ^ rotr32(e, 25U);
            const uint32_t ch   = (e & f) ^ ((~e) & g);
            const uint32_t t1   = h + sum1 + ch + kSha256RC[i] + w[i];
            const uint32_t sum0 = rotr32(a, 2U) ^ rotr32(a, 13U) ^ rotr32(a, 22U);
            const uint32_t maj  = (a & b) ^ (a & c) ^ (b & c);
            const uint32_t t2   = sum0 + maj;

            h = g;
            g = f;
            f = e;
            e = d + t1;
            d = c;
            c = b;
            b = a;
            a = t1 + t2;
        }

        state[0] += a;
        state[1] += b;
        state[2] += c;
        state[3] += d;
        state[4] += e;
        state[5] += f;
        state[6] += g;
        state[7] += h;
    }
};

static_assert(kSha256IV[0] == 0x6A09E667U, "FIPS 180-4 IV[0] avvik");
static_assert(kSha256RC[0] == 0x428A2F98U, "FIPS 180-4 RC[0] avvik");
static_assert(kSha256RC[63] == 0xC67178F2U, "FIPS 180-4 RC[63] avvik");

} // namespace crypto

// ============================================================================
// 2. TILSTANDSSPALTING: s = (s_rev, s_irr) MED STRENG 0 mV FØR PORTEN
// ============================================================================

enum class GateVerdict : uint8_t {
    OPEN      = 0, // Verifisert invariant: V_hw = 5000 mV (5.00 V DC)
    HOLD      = 1, // Luftsluse / likevekt: V_hw = 0 mV (0.00 V DC), Omega = NO_EFFECT
    KILL      = 2, // Invariansbrudd / låst kutt: V_hw = 0 mV (0.00 V DC), krever eksplisitt reset
    SAFE_STOP = 3  // Ressursbudsjett nådd: kontrollert hvile, V_hw = 0 mV
};

enum class OmegaEffect : uint8_t {
    NO_EFFECT = 0,
    REALIZED  = 1
};

// UB-sikker to-komplement negasjon og addisjon/subtraksjon for int64_t
constexpr int64_t wrapping_neg_i64(int64_t v) noexcept {
    return static_cast<int64_t>(0ULL - static_cast<uint64_t>(v));
}

constexpr int64_t wrapping_add_i64(int64_t a, int64_t b) noexcept {
    return static_cast<int64_t>(static_cast<uint64_t>(a) + static_cast<uint64_t>(b));
}

constexpr int64_t wrapping_sub_i64(int64_t a, int64_t b) noexcept {
    return static_cast<int64_t>(static_cast<uint64_t>(a) - static_cast<uint64_t>(b));
}

// 1000-dimensjonalt diskret tilstandsrom Z_2^1000
struct StateZ2_1000 {
    static constexpr std::size_t kDimensions   = 1000;
    static constexpr uint64_t    kLastWordMask = (1ULL << 40U) - 1ULL; // Biter 960..999

    std::array<uint64_t, 16> words{};

    bool is_canonical() const noexcept {
        return (words[15] & ~kLastWordMask) == 0ULL;
    }

    void sanitize() noexcept {
        words[15] &= kLastWordMask;
    }

    bool get_bit(std::size_t idx) const noexcept {
        const std::size_t w = idx / 64U;
        const std::size_t b = idx % 64U;
        return ((words[w] >> b) & 1ULL) != 0ULL;
    }

    void xor_bit(std::size_t idx, bool bit_val) noexcept {
        if (!bit_val || idx >= kDimensions) {
            return;
        }
        const std::size_t w = idx / 64U;
        const std::size_t b = idx % 64U;
        words[w] ^= (1ULL << b);
    }
};

// x: Kandidat- og pådragsvektor (med eksakt uint16_t hyperkube og 4-legeme hovedakserotor)
struct CandidateDriveX {
    int64_t                eta_uv{0};                  // Overpotensial eta i mikrovolt
    std::array<int64_t, 3> field_3d{};                 // 3D involutivt paritetsfelt
    std::array<int64_t, 3> rotor_arm_r0{300, 400, 0};  // §4.3: armvektor r_0 (må ha r_0 . n_hat == 0)
    std::array<int64_t, 3> rotor_axis_n{0, 0, 1};      // §4.3: rotasjonsakse n_hat != 0
    uint16_t               hypercube_addr{0};          // Eksakt 16-bits node i {0,1}^16 (ingen døde biter)
    StateZ2_1000           psi_1000{};                 // 1000-dimensjonal diskret tilstand
};

struct DoubleLayerTheta {
    int64_t delta_phi_dl_uv{0}; // Overskuddspotensial (q_dl - q_dl,eq) / C_dl i mikrovolt
};

struct InvariantKernelK {
    static constexpr int64_t kHardMaxEtaUv      = 5000000LL;     // 5.00 V øvre fysisk tak
    static constexpr int64_t kHardMaxDeltaPhiUv = 5000000LL;     // +/- 5.00 V (trygg mot 1000*128 overflow)
    static constexpr int64_t kHardMaxCoord      = 1000000000LL;  // +/- 10^9 mikroenheter (trygg i kryssprodukt)

    uint64_t j0_na_cm2{10000};
    uint32_t alpha_permille{500};
    uint32_t temp_mk{298150};
    uint32_t electron_n{2};
    int64_t  e0_uv{0};
    int64_t  admissible_eta_max_uv{500000}; // |eta| <= 0.50 V
};

struct ReversibleMemoryM {
    int64_t                 e_eq_uv{0};
    std::array<int64_t, 3>  barycenter_m{};
    std::array<uint64_t, 8> scratchpad{};
};

struct ReversibleCore {
    CandidateDriveX   x{};
    DoubleLayerTheta  theta{};
    InvariantKernelK  K{};
    int8_t            sigma{0};
    ReversibleMemoryM m{};
};

// ============================================================================
// 3. O(1) APPEND-ONLY SHA-256 VITNEKJEDE (L1 PROGRAMVARE, IKKE FYSISK WORM)
// ============================================================================

struct WitnessRecord {
    uint64_t    step{0};
    std::string event_tag{};
    Digest256   prev_hash{};
    Digest256   payload_hash{};
    Digest256   entry_hash{};
};

class AppendOnlyHashChain {
public:
    static constexpr Digest256 kGenesisHash{}; // 32 null-bytes

    std::size_t size() const noexcept { return records_.size(); }
    const Digest256& head_hash() const noexcept {
        return records_.empty() ? kGenesisHash : records_.back().entry_hash;
    }

    Digest256 append(const std::string& event_tag, const Digest256& payload_hash) {
        const uint64_t next_step = static_cast<uint64_t>(records_.size()) + 1ULL;
        const Digest256 prev     = head_hash();
        const Digest256 entry    = compute_entry_digest(next_step, event_tag, prev, payload_hash);
        records_.push_back(WitnessRecord{next_step, event_tag, prev, payload_hash, entry});
        return entry;
    }

    bool verify_chain() const {
        Digest256 expected_prev = kGenesisHash;
        for (std::size_t i = 0; i < records_.size(); ++i) {
            const auto& r = records_[i];
            if (r.step != static_cast<uint64_t>(i) + 1ULL) {
                return false;
            }
            if (r.prev_hash != expected_prev) {
                return false;
            }
            if (r.entry_hash != compute_entry_digest(r.step, r.event_tag, r.prev_hash, r.payload_hash)) {
                return false;
            }
            expected_prev = r.entry_hash;
        }
        return true;
    }

private:
    std::vector<WitnessRecord> records_{};

    static Digest256 compute_entry_digest(
        uint64_t           step,
        const std::string& tag,
        const Digest256&   prev,
        const Digest256&   payload) {
        std::vector<uint8_t> buf;
        buf.reserve(80U + tag.size());
        for (int shift = 56; shift >= 0; shift -= 8) {
            buf.push_back(static_cast<uint8_t>((step >> static_cast<unsigned>(shift)) & 0xFFU));
        }
        const uint32_t tag_len = static_cast<uint32_t>(tag.size());
        for (int shift = 24; shift >= 0; shift -= 8) {
            buf.push_back(static_cast<uint8_t>((tag_len >> static_cast<unsigned>(shift)) & 0xFFU));
        }
        buf.insert(buf.end(), tag.begin(), tag.end());
        buf.insert(buf.end(), prev.begin(), prev.end());
        buf.insert(buf.end(), payload.begin(), payload.end());
        return crypto::Sha256Engine::compute(buf);
    }
};

// Det irreversible omverdensheftet s_irr = (t, Q, W_sha256, V_hw)
// NB: v_hw_mv starter på 0 mV (0.00 V DC) — ALDRI 2500 mV i HOLD!
struct IrreversibleWorld {
    uint64_t            t_ns{0};
    uint64_t            q_diss_pj{0};
    AppendOnlyHashChain witness_chain{};
    uint32_t            v_hw_mv{0}; // 0 mV = HOLD / KILL / SAFE_STOP, 5000 mV = OPEN
};

// ============================================================================
// 4. STRENGT INJEKTIV BIG-ENDIAN SERIALISERING (UTEN SKJULT BITMASKERING)
// ============================================================================

namespace codec {

inline void append_u8(std::vector<uint8_t>& out, uint8_t v) {
    out.push_back(v);
}

inline void append_u16_be(std::vector<uint8_t>& out, uint16_t v) {
    out.push_back(static_cast<uint8_t>((v >> 8U) & 0xFFU));
    out.push_back(static_cast<uint8_t>(v & 0xFFU));
}

inline void append_u32_be(std::vector<uint8_t>& out, uint32_t v) {
    for (int shift = 24; shift >= 0; shift -= 8) {
        out.push_back(static_cast<uint8_t>((v >> static_cast<unsigned>(shift)) & 0xFFU));
    }
}

inline void append_u64_be(std::vector<uint8_t>& out, uint64_t v) {
    for (int shift = 56; shift >= 0; shift -= 8) {
        out.push_back(static_cast<uint8_t>((v >> static_cast<unsigned>(shift)) & 0xFFU));
    }
}

inline void append_i64_be(std::vector<uint8_t>& out, int64_t v) {
    append_u64_be(out, static_cast<uint64_t>(v));
}

inline std::vector<uint8_t> encode_s_rev(const ReversibleCore& s) {
    std::vector<uint8_t> buf;
    buf.reserve(304U);

    // 1. x (ALLE biter i words[0..15] serialiseres rått uten skjult sanitize-maskering,
    //    slik at encode er 1-til-1 injektiv på C++-tilstanden!)
    append_u64_be(buf, static_cast<uint64_t>(s.x.eta_uv));
    for (int64_t coord : s.x.field_3d) {
        append_u64_be(buf, static_cast<uint64_t>(coord));
    }
    for (int64_t r_comp : s.x.rotor_arm_r0) {
        append_u64_be(buf, static_cast<uint64_t>(r_comp));
    }
    for (int64_t n_comp : s.x.rotor_axis_n) {
        append_u64_be(buf, static_cast<uint64_t>(n_comp));
    }
    append_u16_be(buf, s.x.hypercube_addr);
    for (uint64_t w : s.x.psi_1000.words) {
        append_u64_be(buf, w);
    }

    // 2. theta
    append_u64_be(buf, static_cast<uint64_t>(s.theta.delta_phi_dl_uv));

    // 3. K
    append_u64_be(buf, s.K.j0_na_cm2);
    append_u32_be(buf, s.K.alpha_permille);
    append_u32_be(buf, s.K.temp_mk);
    append_u32_be(buf, s.K.electron_n);
    append_u64_be(buf, static_cast<uint64_t>(s.K.e0_uv));
    append_u64_be(buf, static_cast<uint64_t>(s.K.admissible_eta_max_uv));

    // 4. sigma
    append_u8(buf, static_cast<uint8_t>(s.sigma));

    // 5. m
    append_u64_be(buf, static_cast<uint64_t>(s.m.e_eq_uv));
    for (int64_t bc : s.m.barycenter_m) {
        append_u64_be(buf, static_cast<uint64_t>(bc));
    }
    for (uint64_t sp : s.m.scratchpad) {
        append_u64_be(buf, sp);
    }

    return buf;
}

// O(1) serialisering av s_irr via kjedehodet head_hash() og lengde
inline std::vector<uint8_t> encode_s_irr(const IrreversibleWorld& irr) {
    std::vector<uint8_t> buf;
    buf.reserve(60U);
    append_u64_be(buf, irr.t_ns);
    append_u64_be(buf, irr.q_diss_pj);
    append_u64_be(buf, static_cast<uint64_t>(irr.witness_chain.size()));
    const Digest256& head = irr.witness_chain.head_hash();
    buf.insert(buf.end(), head.begin(), head.end());
    append_u32_be(buf, irr.v_hw_mv);
    return buf;
}

inline Digest256 hash_s_rev(const ReversibleCore& s) {
    return crypto::Sha256Engine::compute(encode_s_rev(s));
}

inline Digest256 hash_s_irr(const IrreversibleWorld& irr) {
    return crypto::Sha256Engine::compute(encode_s_irr(irr));
}

} // namespace codec

// ============================================================================
// 5. 4-LEGEME HOVEDAKSEROTOR (§4.3) OG 1000-D REVERSIBEL LIFO-KASKADE
// ============================================================================

struct PhaseStepToken {
    uint16_t step_index{0};
    uint64_t post_step_tag{0};
};

class LifoPhaseMemory {
public:
    static constexpr std::size_t kCapacity = StateZ2_1000::kDimensions;

    void clear() noexcept { stack_.clear(); }
    std::size_t size() const noexcept { return stack_.size(); }
    bool empty() const noexcept { return stack_.empty(); }

    void push(PhaseStepToken tok) { stack_.push_back(tok); }

    bool pop(PhaseStepToken& out) noexcept {
        if (stack_.empty()) {
            return false;
        }
        out = stack_.back();
        stack_.pop_back();
        return true;
    }

    void inject_single_bit_fault(std::size_t pos) noexcept {
        if (pos < stack_.size()) {
            stack_[pos].post_step_tag ^= 1ULL;
        }
    }

private:
    std::vector<PhaseStepToken> stack_{};
};

namespace dynamics {

constexpr uint16_t kHypercubeMask16 = 0xFFFFU;

inline int64_t clamp_sym(int64_t v, int64_t bound) noexcept {
    if (v > bound) {
        return bound;
    }
    if (v < -bound) {
        return -bound;
    }
    return v;
}

inline std::array<int64_t, 3> cross3(
    const std::array<int64_t, 3>& a,
    const std::array<int64_t, 3>& b) noexcept {
    return {
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    };
}

// Verifiserer §4.3 (CARBON/13-14): Kontraroterende 4-legemerotor har eksakt
// P_tot == 0 og L_tot(t) == 0 for ALLE rotasjoner hvis og bare hvis n_hat != 0 og r_0 . n_hat == 0.
inline bool verify_counter_rotor_zero_momenta(const CandidateDriveX& x) noexcept {
    for (int64_t r_c : x.rotor_arm_r0) {
        if (r_c > InvariantKernelK::kHardMaxCoord || r_c < -InvariantKernelK::kHardMaxCoord) {
            return false;
        }
    }
    for (int64_t n_c : x.rotor_axis_n) {
        if (n_c > 1000LL || n_c < -1000LL) {
            return false;
        }
    }
    const int64_t n_norm_sq =
        x.rotor_axis_n[0] * x.rotor_axis_n[0] +
        x.rotor_axis_n[1] * x.rotor_axis_n[1] +
        x.rotor_axis_n[2] * x.rotor_axis_n[2];
    if (n_norm_sq == 0) {
        return false;
    }
    // Hovedakse-ortogonalitet r_0 . n_hat == 0 (eliminerer -4*mu*omega*r_perp*r_par*sin(omega t))
    const int64_t dot_rn =
        x.rotor_arm_r0[0] * x.rotor_axis_n[0] +
        x.rotor_arm_r0[1] * x.rotor_axis_n[1] +
        x.rotor_arm_r0[2] * x.rotor_axis_n[2];
    if (dot_rn != 0) {
        return false;
    }

    // Eksakt kontroll ved start og 90-graders kvadrantvending r_90 = (n x r0):
    // L^+ + L^- ved 90 grader med skrå arm ville gitt ikke-null vippemoment; her er alt eksakt 0.
    const auto v_plus_0  = cross3(x.rotor_axis_n, x.rotor_arm_r0);
    const std::array<int64_t, 3> neg_n{-x.rotor_axis_n[0], -x.rotor_axis_n[1], -x.rotor_axis_n[2]};
    const auto v_minus_0 = cross3(neg_n, x.rotor_arm_r0);
    const auto l_plus_0  = cross3(x.rotor_arm_r0, v_plus_0);
    const auto l_minus_0 = cross3(x.rotor_arm_r0, v_minus_0);
    for (std::size_t i = 0; i < 3U; ++i) {
        if (2LL * (l_plus_0[i] + l_minus_0[i]) != 0LL) {
            return false;
        }
    }
    return true;
}

inline std::size_t partner_dimension(std::size_t k) noexcept {
    std::size_t p = (k * 613U + 37U) % StateZ2_1000::kDimensions;
    if (p == k) {
        p = (k + 1U) % StateZ2_1000::kDimensions;
    }
    return p;
}

inline uint64_t compute_feistel_key(const ReversibleCore& s, std::size_t k) noexcept {
    const uint64_t u_eta = static_cast<uint64_t>(s.x.eta_uv);
    const uint64_t u_sig = static_cast<uint64_t>(static_cast<uint8_t>(s.sigma));
    uint64_t z = u_eta ^ (s.K.j0_na_cm2 * 0x9E3779B97F4A7C15ULL) ^
                 (static_cast<uint64_t>(k + 1U) * 0xBF58476D1CE4E5B9ULL) ^ (u_sig << 48U);
    z = (z ^ (z >> 30U)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27U)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31U);
}

inline uint64_t compute_step_tag(const ReversibleCore& s, std::size_t k) noexcept {
    const uint64_t b_k = s.x.psi_1000.get_bit(k) ? 0xA5A5A5A5A5A5A5A5ULL : 0x5A5A5A5A5A5A5A5AULL;
    return s.m.scratchpad[k & 7U] ^ static_cast<uint64_t>(s.theta.delta_phi_dl_uv) ^ b_k ^
           static_cast<uint64_t>(k);
}

// UB-fri bijeksjon U_{k+1}
inline void step_unitary_forward(ReversibleCore& s, std::size_t k) noexcept {
    const std::size_t p     = partner_dimension(k);
    const uint64_t    f_key = compute_feistel_key(s, k);
    const uint64_t    p_bit = s.x.psi_1000.get_bit(p) ? 1ULL : 0ULL;

    s.m.scratchpad[k & 7U] ^= (f_key + (p_bit * 0x9E3779B97F4A7C15ULL));

    const int64_t delta_uv = static_cast<int64_t>(s.m.scratchpad[k & 7U] & 0xFFULL) - 128LL;
    s.theta.delta_phi_dl_uv = wrapping_add_i64(s.theta.delta_phi_dl_uv, delta_uv);

    const bool flip = ((s.m.scratchpad[k & 7U] ^
                        static_cast<uint64_t>(s.theta.delta_phi_dl_uv)) & 1ULL) != 0ULL;
    s.x.psi_1000.xor_bit(k, flip);
}

// UB-fri eksakt invers U_{k+1}^{-1}
inline void step_unitary_inverse(ReversibleCore& s, std::size_t k) noexcept {
    const bool flip = ((s.m.scratchpad[k & 7U] ^
                        static_cast<uint64_t>(s.theta.delta_phi_dl_uv)) & 1ULL) != 0ULL;
    s.x.psi_1000.xor_bit(k, flip);

    const int64_t delta_uv = static_cast<int64_t>(s.m.scratchpad[k & 7U] & 0xFFULL) - 128LL;
    s.theta.delta_phi_dl_uv = wrapping_sub_i64(s.theta.delta_phi_dl_uv, delta_uv);

    const std::size_t p     = partner_dimension(k);
    const uint64_t    f_key = compute_feistel_key(s, k);
    const uint64_t    p_bit = s.x.psi_1000.get_bit(p) ? 1ULL : 0ULL;
    s.m.scratchpad[k & 7U] ^= (f_key + (p_bit * 0x9E3779B97F4A7C15ULL));
}

inline ReversibleCore trajectory_forward(ReversibleCore s) noexcept {
    for (int64_t& c : s.x.field_3d) {
        c = wrapping_neg_i64(c); // UB-sikker paritetsvending
    }
    s.x.hypercube_addr = static_cast<uint16_t>(s.x.hypercube_addr ^ kHypercubeMask16);

    for (std::size_t k = 0; k < StateZ2_1000::kDimensions; ++k) {
        step_unitary_forward(s, k);
    }
    return s;
}

inline ReversibleCore trajectory_inverse(ReversibleCore s) noexcept {
    for (std::size_t idx = StateZ2_1000::kDimensions; idx > 0U; --idx) {
        step_unitary_inverse(s, idx - 1U);
    }

    s.x.hypercube_addr = static_cast<uint16_t>(s.x.hypercube_addr ^ kHypercubeMask16);
    for (int64_t& c : s.x.field_3d) {
        c = wrapping_neg_i64(c);
    }
    return s;
}

struct DualTrajectoryPair {
    ReversibleCore s_plus{};
    ReversibleCore s_minus{};
};

inline DualTrajectoryPair cross_involution(const DualTrajectoryPair& pair) noexcept {
    return DualTrajectoryPair{
        trajectory_inverse(pair.s_minus),
        trajectory_forward(pair.s_plus)
    };
}

inline ReversibleCore fragment_with_lifo(ReversibleCore s, LifoPhaseMemory& mem) {
    mem.clear();
    for (int64_t& c : s.x.field_3d) {
        c = wrapping_neg_i64(c);
    }
    s.x.hypercube_addr = static_cast<uint16_t>(s.x.hypercube_addr ^ kHypercubeMask16);

    for (std::size_t k = 0; k < StateZ2_1000::kDimensions; ++k) {
        step_unitary_forward(s, k);
        mem.push(PhaseStepToken{
            static_cast<uint16_t>(k),
            compute_step_tag(s, k)
        });
    }
    return s;
}

inline bool defragment_with_lifo(ReversibleCore& s, LifoPhaseMemory& mem) noexcept {
    if (mem.size() != StateZ2_1000::kDimensions) {
        return false;
    }

    for (std::size_t idx = StateZ2_1000::kDimensions; idx > 0U; --idx) {
        const std::size_t expected_k = idx - 1U;
        PhaseStepToken tok{};
        if (!mem.pop(tok)) {
            return false;
        }
        if (tok.step_index != expected_k) {
            return false;
        }
        if (tok.post_step_tag != compute_step_tag(s, expected_k)) {
            return false;
        }
        step_unitary_inverse(s, expected_k);
    }

    s.x.hypercube_addr = static_cast<uint16_t>(s.x.hypercube_addr ^ kHypercubeMask16);
    for (int64_t& c : s.x.field_3d) {
        c = wrapping_neg_i64(c);
    }
    return mem.empty();
}

// Moreau-/boksprojeksjon Pi_K på det lukkede konvekse admissible settet K (Pi_K^2 = Pi_K).
// NB (CARBON/13): Pi_K er ikke-lineær metrisk projeksjon på boks; 2*Pi_K - I brukes IKKE som involusjon!
inline ReversibleCore project_admissible_pi_k(ReversibleCore s) noexcept {
    int64_t lim = s.K.admissible_eta_max_uv;
    if (lim < 0LL) {
        lim = 0LL;
    } else if (lim > InvariantKernelK::kHardMaxEtaUv) {
        lim = InvariantKernelK::kHardMaxEtaUv;
    }
    s.K.admissible_eta_max_uv = lim;

    s.x.eta_uv = clamp_sym(s.x.eta_uv, lim);
    for (int64_t& c : s.x.field_3d) {
        c = clamp_sym(c, InvariantKernelK::kHardMaxCoord);
    }
    s.theta.delta_phi_dl_uv = clamp_sym(s.theta.delta_phi_dl_uv, InvariantKernelK::kHardMaxDeltaPhiUv);

    s.sigma = (s.x.eta_uv > 0LL) ? int8_t{1} : ((s.x.eta_uv < 0LL) ? int8_t{-1} : int8_t{0});
    if (s.x.eta_uv == 0LL) {
        s.theta.delta_phi_dl_uv = 0LL; // Origo-invarians Psi(0) = 0 ved Nernst-likevekt
    }
    s.x.psi_1000.sanitize(); // Renser bits 1000..1023 slik at ikke-kanoniske råbiter fanges mot pre_hash!
    return s;
}

} // namespace dynamics

// ============================================================================
// 6. FAIL-CLOSED LUFTSLUSEPORT MED KILL-LÅS OG NULL MUTASJON FØR DOM
// ============================================================================

// Deklarert på navneromsnivå (fikser C++17 GCC-feilen med nøstet default member initializer)
struct FaultInjection {
    bool        flip_rev_bit_during_hold{false};
    std::size_t rev_bit_index{0};
    bool        flip_lifo_tag_bit{false};
    std::size_t lifo_step_index{500};
};

struct AirlockAuditReport {
    GateVerdict verdict{GateVerdict::KILL};
    OmegaEffect omega{OmegaEffect::NO_EFFECT};
    Digest256   pre_hash{};
    Digest256   return_hash{};
    Digest256   post_witness_seal{};
    bool        s_irr_untouched_in_airlock{false};
    bool        double_closure_verified{false};
    bool        rotor_zero_momenta_verified{false};
    bool        dead_time_compliant{false};
    std::string reason{};
};

class ReversiblusGateMachine {
public:
    explicit ReversiblusGateMachine(uint64_t watchdog_limit_us = 50000ULL,
                                    uint64_t energy_budget_pj  = 10000000ULL) noexcept
        : watchdog_limit_us_(watchdog_limit_us),
          energy_budget_pj_(energy_budget_pj) {}

    bool is_kill_latched() const noexcept { return kill_latched_; }

    // portkontrakten: KILL låser porten. Reset sletter aldri historikk, men appender et eksplisitt
    // bevisvitne i append-only-kjeden og setter systemet tilbake i galvanisk nullpunkt (0 mV).
    bool reset_kill_latch(IrreversibleWorld& world_irr, const std::string& evidence_id) {
        if (evidence_id.empty()) {
            return false;
        }
        world_irr.v_hw_mv = 0U;
        const auto ev_bytes = std::vector<uint8_t>(evidence_id.begin(), evidence_id.end());
        const Digest256 ev_hash = crypto::Sha256Engine::compute(ev_bytes);
        world_irr.witness_chain.append("RESET_AFTER_KILL:" + evidence_id, ev_hash);
        kill_latched_         = false;
        last_committed_sigma_ = 0;
        return true;
    }

    AirlockAuditReport evaluate_and_commit(
        const ReversibleCore& candidate_rev,
        IrreversibleWorld&    world_irr,
        uint64_t              elapsed_eval_us,
        FaultInjection        fault = {}) {

        AirlockAuditReport report{};

        // 0A. Hvis porten allerede er låst i KILL, avvises alt umiddelbart ved 0 mV
        if (kill_latched_) {
            world_irr.v_hw_mv = 0U;
            report.verdict    = GateVerdict::KILL;
            report.omega      = OmegaEffect::NO_EFFECT;
            report.reason     = "Porten er KILL-låst; krever eksplisitt reset med bevis-ID -> 0 mV";
            return report;
        }

        // 0B. Ta snapshot av urørt world_irr FØR én eneste variabel berøres!
        const IrreversibleWorld& const_irr = world_irr;
        const Digest256 irr_snapshot       = codec::hash_s_irr(const_irr);

        if (elapsed_eval_us > watchdog_limit_us_) {
            return engage_kill(world_irr, report, "Watchdog tau_watchdog utløpt -> GATE :: KILL");
        }
        if (const_irr.q_diss_pj >= energy_budget_pj_) {
            world_irr.v_hw_mv         = 0U;
            last_committed_sigma_     = 0;
            report.verdict            = GateVerdict::SAFE_STOP;
            report.omega              = OmegaEffect::NO_EFFECT;
            report.reason             = "Energi-/ressursgrense nådd -> kontrollert SAFE_STOP (0 mV)";
            return report;
        }

        // 1. Kiralitets- og kanonisitetssjekk (uten å skrive til world_irr!)
        const int8_t target_sigma =
            (candidate_rev.x.eta_uv > 0LL) ? int8_t{1}
                                           : ((candidate_rev.x.eta_uv < 0LL) ? int8_t{-1} : int8_t{0});
        if (candidate_rev.sigma != target_sigma) {
            return engage_kill(world_irr, report,
                               "Inkonsekvent kiralitet sigma != sgn(eta) -> GATE :: KILL");
        }

        // 2. Galvanisk dødtidssjekk (+U -> 0/HOLD -> -U)
        if ((last_committed_sigma_ == 1 && target_sigma == -1) ||
            (last_committed_sigma_ == -1 && target_sigma == 1)) {
            report.dead_time_compliant = false;
            return engage_kill(
                world_irr, report,
                "Brudd på galvanisk dødtid (+U direkte til -U uten 0/HOLD) -> GATE :: KILL");
        }
        report.dead_time_compliant = true;

        // 3. Rå, injektiv start-hash H(encode(s_rev)) uten skjult bitmaskering!
        report.pre_hash = codec::hash_s_rev(candidate_rev);

        // 4. §4.3 Kontraroterende 4-legeme hovedaksekontroll (r_0 . n_hat == 0 => P_tot = 0, L_tot = 0)
        report.rotor_zero_momenta_verified =
            dynamics::verify_counter_rotor_zero_momenta(candidate_rev.x);
        if (!report.rotor_zero_momenta_verified) {
            return engage_kill(
                world_irr, report,
                "Brudd på §4.3 hovedakse-ortogonalitet (r_0 . n_hat != 0 gir L_tot != 0) -> GATE :: KILL");
        }

        // 5. Admissibel projeksjon Pi_K^2 = Pi_K FØR dynamikk (hindrer ekstreme tall og råbit-smugling)
        const ReversibleCore proj_1 = dynamics::project_admissible_pi_k(candidate_rev);
        const ReversibleCore proj_2 = dynamics::project_admissible_pi_k(proj_1);
        const bool pi_idempotent_ok   = (codec::hash_s_rev(proj_1) == codec::hash_s_rev(proj_2));
        const bool within_admissible_k = (codec::hash_s_rev(proj_1) == report.pre_hash) &&
                                         candidate_rev.x.psi_1000.is_canonical();
        if (!pi_idempotent_ok || !within_admissible_k) {
            return engage_kill(
                world_irr, report,
                "Kandidat utenfor admissibelt sett K eller ikke-kanoniske biter -> GATE :: KILL");
        }

        // 6. Eksakt tosidig kryss-involusjon I^2(S) == S (tester både F_- o F_+ = I og F_+ o F_- = I)
        const dynamics::DualTrajectoryPair s_pair_0{
            candidate_rev,
            candidate_rev // Uavhengig andrekomponent sikrer at F_+ o F_- = I også prøves direkte!
        };
        const auto s_pair_1 = dynamics::cross_involution(s_pair_0);
        const auto s_pair_2 = dynamics::cross_involution(s_pair_1);

        const bool i_squared_ok =
            (codec::hash_s_rev(s_pair_2.s_plus) == report.pre_hash) &&
            (codec::hash_s_rev(s_pair_2.s_minus) == report.pre_hash);
        report.double_closure_verified = i_squared_ok && pi_idempotent_ok;
        if (!report.double_closure_verified) {
            return engage_kill(world_irr, report, "Kryss-involusjon I^2 != I -> GATE :: KILL");
        }

        // 7. 1000-trinns fragmentering D(s_rev) og antiautomorf LIFO-retur A(s_frag, M_phi)
        LifoPhaseMemory lifo_mem{};
        ReversibleCore  working_state = dynamics::fragment_with_lifo(candidate_rev, lifo_mem);

        if (fault.flip_rev_bit_during_hold) {
            working_state.x.psi_1000.xor_bit(fault.rev_bit_index, true);
        }
        if (fault.flip_lifo_tag_bit) {
            lifo_mem.inject_single_bit_fault(fault.lifo_step_index);
        }

        const bool lifo_clean = dynamics::defragment_with_lifo(working_state, lifo_mem);
        report.return_hash    = codec::hash_s_rev(working_state);

        // 8. Ekte luftslusebevis: const_irr er fortsatt 100 % identisk med irr_snapshot før inngang!
        report.s_irr_untouched_in_airlock = (codec::hash_s_irr(const_irr) == irr_snapshot);
        if (!report.s_irr_untouched_in_airlock) {
            return engage_kill(world_irr, report,
                               "Ulovlig lekkasje til s_irr under luftsluseprøving -> GATE :: KILL");
        }

        // 9. Streng kryptografisk bit-identitet: H(encode(s''_rev)) == H(encode(s_rev))
        if (!lifo_clean || (report.return_hash != report.pre_hash)) {
            return engage_kill(
                world_irr, report,
                "1-bits avvik detektert i LIFO-retur / SHA-256 -> momentant GATE :: KILL");
        }

        // 10. Galvanisk nullpunkt (eta == 0 -> sigma == 0): HOLD ved streng 0 mV (0.00 V DC)!
        last_committed_sigma_ = target_sigma;
        if (target_sigma == 0) {
            world_irr.v_hw_mv = 0U; // Strengt 0.00 V DC i HOLD (aldri 2500 mV!)
            report.verdict    = GateVerdict::HOLD;
            report.omega      = OmegaEffect::NO_EFFECT;
            report.reason     = "Galvanisk nullpunkt verifisert (HOLD ved 0 mV / 0.00 V DC)";
            return report;
        }

        // 11. GATE :: OPEN -> Konsekvensporten Omega utløses (5000 mV + append-only SHA-256 kjede)
        world_irr.t_ns      += elapsed_eval_us * 1000ULL + 1000ULL;
        world_irr.q_diss_pj += 4200ULL;
        world_irr.v_hw_mv    = 5000U;

        std::vector<uint8_t> commit_event = codec::encode_s_irr(world_irr);
        commit_event.insert(commit_event.end(), report.return_hash.begin(), report.return_hash.end());
        const Digest256 event_digest = crypto::Sha256Engine::compute(commit_event);
        report.post_witness_seal     = world_irr.witness_chain.append("GATE_OPEN_COMMIT", event_digest);

        report.verdict = GateVerdict::OPEN;
        report.omega   = OmegaEffect::REALIZED;
        report.reason  = "Bit-eksakt retur verifisert -> GATE :: OPEN (5000 mV, SHA-256-kjede forseglet)";
        return report;
    }

private:
    uint64_t watchdog_limit_us_;
    uint64_t energy_budget_pj_;
    int8_t   last_committed_sigma_{0};
    bool     kill_latched_{false};

    AirlockAuditReport engage_kill(
        IrreversibleWorld&  world_irr,
        AirlockAuditReport& report,
        const std::string&  why) {
        world_irr.v_hw_mv = 0U; // Umiddelbart 0.00 V DC spenningskutt
        kill_latched_     = true;
        report.verdict    = GateVerdict::KILL;
        report.omega      = OmegaEffect::NO_EFFECT;
        report.reason     = why;
        return report;
    }
};

inline const char* verdict_name(GateVerdict v) noexcept {
    switch (v) {
        case GateVerdict::OPEN:      return "OPEN";
        case GateVerdict::HOLD:      return "HOLD";
        case GateVerdict::KILL:      return "KILL";
        case GateVerdict::SAFE_STOP: return "SAFE_STOP";
    }
    return "UNKNOWN";
}

} // namespace carbon::doc78

int main() {
    using namespace carbon::doc78;

    std::cout << "=== CARBON / 16 :: DOKUMENT 78 HERDET C++17 L1-KJERNE (NULL FLOAT, UB-FRI) ===\n\n";

    // [VEKTOR 0] Full 256-bits FIPS 180-4 SHA-256 selvtest ("abc" + "")
    if (!crypto::Sha256Engine::verify_fips_self_test()) {
        std::cerr << "[FATAL] FIPS 180-4 SHA-256 selvtest feilet\n";
        return 1;
    }
    std::cout << "[PASS 1/9] FIPS 180-4 constexpr SHA-256 (full 256-bit 'abc' + '')\n";

    ReversiblusGateMachine gate{};
    IrreversibleWorld      world{};

    // Bekreft streng 0 mV før porten
    if (world.v_hw_mv != 0U) {
        return 2;
    }

    ReversibleCore s_cand{};
    s_cand.x.eta_uv               = 250000;
    s_cand.x.field_3d             = {1200, -450, 800};
    s_cand.x.rotor_arm_r0         = {300, 400, 0}; // r_0 . n_hat == 0
    s_cand.x.rotor_axis_n         = {0, 0, 1};
    s_cand.x.hypercube_addr       = 0x3CA5U;
    s_cand.x.psi_1000.words[0]    = 0xCAFEBABEDEADBEEFULL;
    s_cand.x.psi_1000.words[15]   = 0x000000AA55AA55AAULL;
    s_cand.theta.delta_phi_dl_uv  = 18500;
    s_cand.sigma                  = 1;
    s_cand.m.e_eq_uv              = 1229000;
    s_cand.m.barycenter_m         = {0, 0, 0};
    s_cand.m.scratchpad[0]        = 0x1122334455667788ULL;

    // [PASS 2/9] Nominell 1000-D LIFO, tosidig I^2=I, Pi_K^2=Pi_K og 4-legeme rotor -> OPEN
    const auto rep1 = gate.evaluate_and_commit(s_cand, world, 420ULL);
    if (rep1.verdict != GateVerdict::OPEN || !rep1.s_irr_untouched_in_airlock ||
        world.v_hw_mv != 5000U || world.witness_chain.size() != 1U) {
        return 3;
    }
    std::cout << "[PASS 2/9] Nominell 1000-D LIFO & hovedakserotor -> OPEN (5000 mV, kjede=1)\n";

    // [PASS 3/9] 1-bits lekkasje i Z_2^1000 (dim 777) -> KILL (0 mV) + KILL-lås aktiv
    FaultInjection bit_leak{};
    bit_leak.flip_rev_bit_during_hold = true;
    bit_leak.rev_bit_index            = 777U;
    const auto rep2 = gate.evaluate_and_commit(s_cand, world, 380ULL, bit_leak);
    if (rep2.verdict != GateVerdict::KILL || world.v_hw_mv != 0U || !gate.is_kill_latched() ||
        world.witness_chain.size() != 1U) {
        return 4;
    }
    std::cout << "[PASS 3/9] 1-bits lekkasje i dim 777 -> GATE :: KILL (0 mV, låst)\n";

    // [PASS 4/9] KILL-lås blokkerer videre OPEN inntil eksplisitt reset med bevis-ID appender vitne
    const auto rep3_blocked = gate.evaluate_and_commit(s_cand, world, 100ULL);
    if (rep3_blocked.verdict != GateVerdict::KILL || world.v_hw_mv != 0U) {
        return 5;
    }
    if (gate.reset_kill_latch(world, "")) { // Tom bevis-ID må avvises!
        return 6;
    }
    if (!gate.reset_kill_latch(world, "AUTH-AUDIT-DOK78-RESET-01") ||
        gate.is_kill_latched() || world.witness_chain.size() != 2U || world.v_hw_mv != 0U) {
        return 7;
    }
    std::cout << "[PASS 4/9] KILL-lås krever bevis-ID; reset appender vitne uten å slette historikk\n";

    // Sett opp anodisk OPEN igjen (+1) for å prøve ulovlig direkte polaritetsvending (+1 -> -1)
    const auto rep_rearm = gate.evaluate_and_commit(s_cand, world, 200ULL);
    if (rep_rearm.verdict != GateVerdict::OPEN || world.witness_chain.size() != 3U) {
        return 8;
    }

    // [PASS 5/9] Direkte +U -> -U uten dødtid -> KILL + etterfølgende revidert reset
    ReversibleCore s_cathodic = s_cand;
    s_cathodic.x.eta_uv       = -250000;
    s_cathodic.sigma          = -1;
    const auto rep_shoot = gate.evaluate_and_commit(s_cathodic, world, 300ULL);
    if (rep_shoot.verdict != GateVerdict::KILL || world.v_hw_mv != 0U) {
        return 9;
    }
    if (!gate.reset_kill_latch(world, "AUTH-AUDIT-DOK78-RESET-02")) {
        return 10;
    }
    std::cout << "[PASS 5/9] Direkte +U -> -U uten dødtid stoppet med GATE :: KILL (0 mV)\n";

    // [PASS 6/9] Lovlig sekvens: +U (OPEN 5000 mV) -> 0/HOLD (0 mV!) -> -U (OPEN 5000 mV)
    const auto rep_anodic = gate.evaluate_and_commit(s_cand, world, 210ULL);
    ReversibleCore s_zero = s_cand;
    s_zero.x.eta_uv              = 0;
    s_zero.theta.delta_phi_dl_uv = 0;
    s_zero.sigma                 = 0;
    const auto rep_hold = gate.evaluate_and_commit(s_zero, world, 150ULL);
    if (rep_anodic.verdict != GateVerdict::OPEN || rep_hold.verdict != GateVerdict::HOLD ||
        world.v_hw_mv != 0U) { // Strengt 0 mV i HOLD!
        return 11;
    }
    const auto rep_cathodic_ok = gate.evaluate_and_commit(s_cathodic, world, 260ULL);
    if (rep_cathodic_ok.verdict != GateVerdict::OPEN || world.v_hw_mv != 5000U) {
        return 12;
    }
    std::cout << "[PASS 6/9] Lovlig +U -> 0/HOLD (strengt 0 mV) -> -U (OPEN 5000 mV)\n";

    // [PASS 7/9] Injektivitetstest: smuglet bit 55 i words[15] fanges (ikke maskert vekk i encode!)
    ReversibleCore s_smuggled = s_zero;
    s_smuggled.x.psi_1000.words[15] |= (1ULL << 55U); // Utenfor bit 0..39 i siste ord!
    const auto rep_smuggled = gate.evaluate_and_commit(s_smuggled, world, 100ULL);
    if (rep_smuggled.verdict != GateVerdict::KILL || world.v_hw_mv != 0U) {
        return 13;
    }
    gate.reset_kill_latch(world, "AUTH-AUDIT-DOK78-RESET-03");
    std::cout << "[PASS 7/9] Smuglet padding-bit i words[15] avvist av injektiv encode_s_rev\n";

    // [PASS 8/9] UB-torturtest med INT64_MIN og INT64_MAX under -fsanitize=undefined,address
    ReversibleCore s_ub = s_cand;
    s_ub.x.field_3d            = {INT64_MIN, INT64_MAX, INT64_MIN};
    s_ub.theta.delta_phi_dl_uv = INT64_MAX;
    // Både direkte trajektoriekjøring og portprøving er 100 % fri for signed overflow UB:
    const ReversibleCore s_ub_roundtrip =
        dynamics::trajectory_inverse(dynamics::trajectory_forward(s_ub));
    if (codec::hash_s_rev(s_ub_roundtrip) != codec::hash_s_rev(s_ub)) {
        return 14;
    }
    const auto rep_ub = gate.evaluate_and_commit(s_ub, world, 100ULL);
    if (rep_ub.verdict != GateVerdict::KILL || world.v_hw_mv != 0U) {
        return 15;
    }
    gate.reset_kill_latch(world, "AUTH-AUDIT-DOK78-RESET-04");
    std::cout << "[PASS 8/9] INT64_MIN / INT64_MAX UB-torturtest bestått uten sanitizer-avvik\n";

    // [PASS 9/9] Skrå rotorarm r_0 = (300, 0, 200) rundt z-aksen (r_0 . n_hat != 0) -> KILL + kjedebevis
    ReversibleCore s_tilted = s_cand;
    s_tilted.x.rotor_arm_r0 = {300, 0, 200};
    const auto rep_tilt     = gate.evaluate_and_commit(s_tilted, world, 120ULL);
    if (rep_tilt.verdict != GateVerdict::KILL || rep_tilt.rotor_zero_momenta_verified ||
        !world.witness_chain.verify_chain()) {
        return 16;
    }
    std::cout << "[PASS 9/9] Skrå 4-legemerotor (r_0 . n_hat != 0) stoppet & SHA-256-kjede verifisert ("
              << world.witness_chain.size() << " ledd)\n\n";

    std::cout << "Resultat: 9/9 PASS | Append-only SHA-256 head: "
              << crypto::Sha256Engine::to_hex(world.witness_chain.head_hash()).substr(0, 24)
              << "...\n";
    return 0;
}
