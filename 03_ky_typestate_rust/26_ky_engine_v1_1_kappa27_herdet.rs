//! KY Engine v1.1 (κ_27 Herdet) — Fail-Closed Meta-Engine Kernel (L1 Reference)
//! ============================================================================
//! Epistemisk status : L1 (lokalt demonstrert, deterministisk programvarekjerne)
//! Kontraktregel     : INSPIRED_BY != IMPLEMENTS != PROVES
//! Flyttallsforbud   : 0 forekomster av IEEE-754 flyttall; eksakt heltall / Q-brøk
//! Avhengigheter     : 0 eksterne crates (ren Rust std, rustc 1.63.0-kompatibel)
//! L1-avgrensning    : SHA-256-kjeden i WitnessLog er en append-only programvare-
//!                     kjede i RAM, IKKE fysisk WORM-maskinvare (krever separat L3).
//!
//! Kjerneformel:
//!   x_tilde_{t+1} = Pi_K(Phi(x_t))
//!   d_{t+1}       = Omega(x_tilde_{t+1}, pi, g, h, evidence_id) in {OPEN, HOLD, KILL}
//!   x_{t+1}       = x_tilde_{t+1} (OPEN) | x_t (HOLD) | bot (KILL)
//!   tau_{t+1}     = tau_t + 1     (OPEN) | tau_t      (HOLD, KILL)
//!   V_coil        = 5000 mV       (OPEN) | 0 mV       (HOLD, KILL)

#![forbid(unsafe_code)]
#![deny(warnings)]

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::marker::PhantomData;

// ============================================================================
// 0. EKSAKT HELTALLS- OG RASJONAL ARITMETIKK (NULL FLYTTALL)
// ============================================================================

/// Største felles divisor over u128 (Euclids algoritme).
pub const fn gcd_u128(mut a: u128, mut b: u128) -> u128 {
    while b != 0 {
        let r = a % b;
        a = b;
        b = r;
    }
    a
}

/// Eksakt forkortet rasjonalt tall i Q (num / den, med den > 0).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RatioI128 {
    num: i128,
    den: i128,
}

impl RatioI128 {
    pub fn new(num: i128, den: i128) -> Result<Self, FailureCode> {
        if den == 0 {
            return Err(FailureCode::StructureInvalid);
        }
        if num == 0 {
            return Ok(Self { num: 0, den: 1 });
        }
        let sign = if (num < 0) ^ (den < 0) { -1i128 } else { 1i128 };
        let abs_n = num.unsigned_abs();
        let abs_d = den.unsigned_abs();
        let g = gcd_u128(abs_n, abs_d);
        let red_n = (abs_n / g) as i128;
        let red_d = (abs_d / g) as i128;
        Ok(Self {
            num: sign * red_n,
            den: red_d,
        })
    }

    pub const fn from_int(n: i128) -> Self {
        Self { num: n, den: 1 }
    }

    pub const fn numerator(&self) -> i128 {
        self.num
    }

    pub const fn denominator(&self) -> i128 {
        self.den
    }

    pub fn add(self, rhs: Self) -> Result<Self, FailureCode> {
        let n1 = self.num.checked_mul(rhs.den).ok_or(FailureCode::StructureInvalid)?;
        let n2 = rhs.num.checked_mul(self.den).ok_or(FailureCode::StructureInvalid)?;
        let num = n1.checked_add(n2).ok_or(FailureCode::StructureInvalid)?;
        let den = self.den.checked_mul(rhs.den).ok_or(FailureCode::StructureInvalid)?;
        Self::new(num, den)
    }

    pub fn mul(self, rhs: Self) -> Result<Self, FailureCode> {
        let num = self.num.checked_mul(rhs.num).ok_or(FailureCode::StructureInvalid)?;
        let den = self.den.checked_mul(rhs.den).ok_or(FailureCode::StructureInvalid)?;
        Self::new(num, den)
    }

    pub fn square(self) -> Result<Self, FailureCode> {
        self.mul(self)
    }

    pub fn le(self, rhs: Self) -> Result<bool, FailureCode> {
        let lhs_cross = self.num.checked_mul(rhs.den).ok_or(FailureCode::StructureInvalid)?;
        let rhs_cross = rhs.num.checked_mul(self.den).ok_or(FailureCode::StructureInvalid)?;
        Ok(lhs_cross <= rhs_cross)
    }
}

/// Klamming = amplitudekontroll før mening: tvinger rå promilleverdi inn i [0, 1000].
pub const fn clamp_permille_0_1000(val_permille: i64) -> u16 {
    if val_permille <= 0 {
        0
    } else if val_permille >= 1_000 {
        1_000
    } else {
        val_permille as u16
    }
}

// ============================================================================
// 1. REN RUST FIPS 180-4 SHA-256 (LENGDEPREFIKSET, 0 EKSTERNE CRATES)
// ============================================================================

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

const SHA256_H0: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

#[derive(Clone)]
pub struct Sha256Hasher {
    state: [u32; 8],
    block: [u8; 64],
    block_len: usize,
    total_bytes: u64,
}

impl Sha256Hasher {
    pub const fn new() -> Self {
        Self {
            state: SHA256_H0,
            block: [0u8; 64],
            block_len: 0,
            total_bytes: 0,
        }
    }

    pub fn update(&mut self, data: &[u8]) {
        let mut idx = 0usize;
        self.total_bytes = self.total_bytes.wrapping_add(data.len() as u64);

        while idx < data.len() {
            let space = 64 - self.block_len;
            let take = if data.len() - idx < space {
                data.len() - idx
            } else {
                space
            };
            self.block[self.block_len..self.block_len + take]
                .copy_from_slice(&data[idx..idx + take]);
            self.block_len += take;
            idx += take;

            if self.block_len == 64 {
                let blk = self.block;
                self.compress_block(&blk);
                self.block_len = 0;
            }
        }
    }

    pub fn update_u8(&mut self, v: u8) {
        self.update(&[v]);
    }

    pub fn update_u16_le(&mut self, v: u16) {
        self.update(&v.to_le_bytes());
    }

    pub fn update_u64_le(&mut self, v: u64) {
        self.update(&v.to_le_bytes());
    }

    /// Eksplisitt lengdeprefikset strenginnkoding: hindrer grenseforskyvnings-kollisjoner
    /// som ellers oppstår ved rå konkatenering ("AB" || "C" vs. "A" || "BC").
    pub fn update_len_prefixed_str(&mut self, s: &str) {
        self.update_u64_le(s.len() as u64);
        self.update(s.as_bytes());
    }

    pub fn finalize(mut self) -> [u8; 32] {
        let bit_len = self.total_bytes.wrapping_mul(8);
        self.update(&[0x80]);
        while self.block_len != 56 {
            if self.block_len == 64 {
                let blk = self.block;
                self.compress_block(&blk);
                self.block_len = 0;
            }
            self.block[self.block_len] = 0;
            self.block_len += 1;
        }
        let bit_bytes = bit_len.to_be_bytes();
        self.block[56..64].copy_from_slice(&bit_bytes);
        let blk = self.block;
        self.compress_block(&blk);

        let mut out = [0u8; 32];
        let mut i = 0usize;
        while i < 8 {
            let word_bytes = self.state[i].to_be_bytes();
            out[i * 4..i * 4 + 4].copy_from_slice(&word_bytes);
            i += 1;
        }
        out
    }

    pub fn digest(data: &[u8]) -> [u8; 32] {
        let mut h = Self::new();
        h.update(data);
        h.finalize()
    }

    fn compress_block(&mut self, blk: &[u8; 64]) {
        let mut w = [0u32; 64];
        let mut i = 0usize;
        while i < 16 {
            let j = i * 4;
            w[i] = u32::from_be_bytes([blk[j], blk[j + 1], blk[j + 2], blk[j + 3]]);
            i += 1;
        }
        while i < 64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
            i += 1;
        }

        let mut a = self.state[0];
        let mut b = self.state[1];
        let mut c = self.state[2];
        let mut d = self.state[3];
        let mut e = self.state[4];
        let mut f = self.state[5];
        let mut g = self.state[6];
        let mut h = self.state[7];

        let mut round = 0usize;
        while round < 64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[round])
                .wrapping_add(w[round]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
            round += 1;
        }

        self.state[0] = self.state[0].wrapping_add(a);
        self.state[1] = self.state[1].wrapping_add(b);
        self.state[2] = self.state[2].wrapping_add(c);
        self.state[3] = self.state[3].wrapping_add(d);
        self.state[4] = self.state[4].wrapping_add(e);
        self.state[5] = self.state[5].wrapping_add(f);
        self.state[6] = self.state[6].wrapping_add(g);
        self.state[7] = self.state[7].wrapping_add(h);
    }
}

pub fn hex_encode_32(digest: &[u8; 32]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(64);
    let mut i = 0usize;
    while i < 32 {
        let b = digest[i];
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
        i += 1;
    }
    out
}

/// Trekker ut de nedre 64 bitene av et SHA-256-digest for monoton OR-fuse-maske.
pub fn digest_low_u64(digest: &[u8; 32]) -> u64 {
    u64::from_le_bytes([
        digest[0], digest[1], digest[2], digest[3],
        digest[4], digest[5], digest[6], digest[7],
    ])
}

// ============================================================================
// 2. DOMENE, PORTDOMMER OG FORSEGLEDE KOMPILERINGSTIDS-TYPESTATES
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum GateStatus {
    Open = 1,
    Hold = 2,
    Kill = 3,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum FailureCode {
    None = 0,
    IllegalStateTransition = 1,
    SyntaxError = 2,
    StructureInvalid = 3,
    HashChainBroken = 4,
    Inadmissible = 5,
    AuditFailed = 6,
    NonReproducible = 7,
    IksReversibilityFailed = 8,
    RosettaIdentityDrift = 9,
    NashCollapse = 10,
    NashRegularizableResidual = 11,
    EtorRiskExceeded = 12,
    PostCausalBoundaryCrossed = 13,
    HighUncertainty = 14,
    MissingEvidenceId = 15,
    ZoneOccupiedDefer = 16,
    HoldDeadlineExceeded = 17,
    ExternalAuthorityRequired = 18,
    KillLatchActive = 19,
}

/// Eier av autoritet i HOLD (jf. den doble klokkeloven i CARBON 02 & light_bridge.gd).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum HoldAuthority {
    None = 0,
    Internal = 1, // P_int innenfor avtalt t_max
    External = 2, // P_ext etter fristbrudd (t - created_tick > max_hold_ticks)
}

/// Dom er ikke dynamikk: Omega returnerer en ren avgjørelse, ikke en tilstand.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GateVerdict {
    pub decision: GateStatus,
    pub reason: FailureCode,
}

/// Kontekst ved portpassering (Reality Forge light_bridge-invarianter).
#[derive(Debug, Clone, Copy)]
pub struct StepContext<'a> {
    pub evidence_id: &'a str,
    pub zone_occupied: bool,
    pub max_hold_ticks: u64,
}

impl<'a> StepContext<'a> {
    pub const fn standard(evidence_id: &'a str) -> Self {
        Self {
            evidence_id,
            zone_occupied: false,
            max_hold_ticks: 8,
        }
    }
}

mod sealed {
    pub trait Sealed {}
}

/// Forseglet markør-trait: ekstern kode kan ikke finne opp falske livssyklustrinn.
pub trait LifecyclePhase: sealed::Sealed {
    const PHASE_NAME: &'static str;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Raw; // ○
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Estimate; // ◇
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Struct; // □
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Viability; // ⬡
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Committed; // ◉

impl sealed::Sealed for Raw {}
impl sealed::Sealed for Estimate {}
impl sealed::Sealed for Struct {}
impl sealed::Sealed for Viability {}
impl sealed::Sealed for Committed {}

impl LifecyclePhase for Raw {
    const PHASE_NAME: &'static str = "RAW";
}
impl LifecyclePhase for Estimate {
    const PHASE_NAME: &'static str = "ESTIMATE";
}
impl LifecyclePhase for Struct {
    const PHASE_NAME: &'static str = "STRUCT";
}
impl LifecyclePhase for Viability {
    const PHASE_NAME: &'static str = "VIABILITY";
}
impl LifecyclePhase for Committed {
    const PHASE_NAME: &'static str = "COMMITTED";
}

/// Typet tilstandspost med PRIVATE felter:
/// Ingen ekstern kode kan mutere `gate_status = Open` eller snike en uprøvd post
/// forbi `GateOmega::admit` inn i `Record<Committed>`.
#[derive(Debug, Clone)]
pub struct Record<S: LifecyclePhase> {
    object_id: u64,
    payload: String,
    gate_status: GateStatus,
    structure_valid: bool,
    admissibility_flag: bool,
    irreversible: bool,
    audit_required: bool,
    audit_pass: bool,
    reproducible: bool,
    iks_reversible: bool,
    rosetta_identity_ok: bool,
    etor_risk_permille: u16,
    etor_threshold_permille: u16,
    pre_commit_g_milli: i64,
    clamped_amplitude_permille: u16,
    uncertainty_high: bool,
    failure_code: FailureCode,
    integrity_hash: [u8; 32],
    or_fuse_latch: u64,
    created_tick: u64,
    tau_coord: u64,
    approved_evidence_id: String,
    _state: PhantomData<S>,
}

impl<S: LifecyclePhase> Record<S> {
    pub fn phase_name(&self) -> &'static str {
        S::PHASE_NAME
    }
    pub fn object_id(&self) -> u64 {
        self.object_id
    }
    pub fn payload(&self) -> &str {
        &self.payload
    }
    pub fn gate_status(&self) -> GateStatus {
        self.gate_status
    }
    pub fn structure_valid(&self) -> bool {
        self.structure_valid
    }
    pub fn admissibility_flag(&self) -> bool {
        self.admissibility_flag
    }
    pub fn irreversible(&self) -> bool {
        self.irreversible
    }
    pub fn audit_required(&self) -> bool {
        self.audit_required
    }
    pub fn audit_pass(&self) -> bool {
        self.audit_pass
    }
    pub fn reproducible(&self) -> bool {
        self.reproducible
    }
    pub fn iks_reversible(&self) -> bool {
        self.iks_reversible
    }
    pub fn rosetta_identity_ok(&self) -> bool {
        self.rosetta_identity_ok
    }
    pub fn etor_risk_permille(&self) -> u16 {
        self.etor_risk_permille
    }
    pub fn etor_threshold_permille(&self) -> u16 {
        self.etor_threshold_permille
    }
    pub fn pre_commit_g_milli(&self) -> i64 {
        self.pre_commit_g_milli
    }
    pub fn clamped_amplitude_permille(&self) -> u16 {
        self.clamped_amplitude_permille
    }
    pub fn uncertainty_high(&self) -> bool {
        self.uncertainty_high
    }
    pub fn failure_code(&self) -> FailureCode {
        self.failure_code
    }
    pub fn integrity_hash(&self) -> &[u8; 32] {
        &self.integrity_hash
    }
    pub fn or_fuse_latch(&self) -> u64 {
        self.or_fuse_latch
    }
    pub fn created_tick(&self) -> u64 {
        self.created_tick
    }
    pub fn tau_coord(&self) -> u64 {
        self.tau_coord
    }
    pub fn approved_evidence_id(&self) -> &str {
        &self.approved_evidence_id
    }

    fn recast<T: LifecyclePhase>(self) -> Record<T> {
        Record {
            object_id: self.object_id,
            payload: self.payload,
            gate_status: self.gate_status,
            structure_valid: self.structure_valid,
            admissibility_flag: self.admissibility_flag,
            irreversible: self.irreversible,
            audit_required: self.audit_required,
            audit_pass: self.audit_pass,
            reproducible: self.reproducible,
            iks_reversible: self.iks_reversible,
            rosetta_identity_ok: self.rosetta_identity_ok,
            etor_risk_permille: self.etor_risk_permille,
            etor_threshold_permille: self.etor_threshold_permille,
            pre_commit_g_milli: self.pre_commit_g_milli,
            clamped_amplitude_permille: self.clamped_amplitude_permille,
            uncertainty_high: self.uncertainty_high,
            failure_code: self.failure_code,
            integrity_hash: self.integrity_hash,
            or_fuse_latch: self.or_fuse_latch,
            created_tick: self.created_tick,
            tau_coord: self.tau_coord,
            approved_evidence_id: self.approved_evidence_id,
            _state: PhantomData,
        }
    }
}

// ============================================================================
// 3. FASELOGIKK, IKS-KOHERENS & EKS-RASJONAL NASH-MODUL
// ============================================================================

pub struct PhaseCommitLogic;

impl PhaseCommitLogic {
    /// XOR = reversibel fase/maske: (a ^ b) ^ b == a
    pub const fn xor_reversible_phase(state_mask: u64, delta_mask: u64) -> u64 {
        state_mask ^ delta_mask
    }

    /// OR-fuse = irreversibel commit: P_{t+1} = P_t | Delta_t med P_{t+1} >= P_t
    pub const fn or_fuse_commit(prev_latch: u64, delta_mask: u64) -> u64 {
        prev_latch | delta_mask
    }
}

/// IKS: Ikke-vakuøs kanoniserings- og involusjonstest.
/// Retter blindgjengeren i v1 (`s.chars().rev().collect()`, som alltid ga `true` på enhver `&str`).
/// Her avvises tapspreget innkoding (U+FFFD), kontrolltegn og ikke-kanoniske mellomrom/tomme segmenter,
/// før involutiv byte-speiling + UTF-8-rekonstruksjon verifiserer tapsfri F_dec(F_enc(s)) == s.
pub struct IksCoherenceTest;

impl IksCoherenceTest {
    pub fn canonicalize(s: &str) -> Option<String> {
        if s.is_empty() {
            return None;
        }
        for ch in s.chars() {
            if ch == '\u{FFFD}' || ch.is_control() {
                return None;
            }
        }
        let mut parts = Vec::new();
        for seg in s.split('|') {
            let clean_words: Vec<&str> = seg.split_whitespace().collect();
            if clean_words.is_empty() {
                return None;
            }
            parts.push(clean_words.join(" "));
        }
        Some(parts.join(" | "))
    }

    pub fn involution_encode_decode(s: &str) -> Option<String> {
        let canon = Self::canonicalize(s)?;
        // Involutiv transform over u32 Unicode scalar-verdier (XOR med involutiv maske + reversering)
        let encoded: Vec<u32> = canon
            .chars()
            .rev()
            .map(|c| (c as u32) ^ 0x0005_A5A5)
            .collect();
        let mut decoded = String::with_capacity(canon.len());
        for code in encoded.into_iter().rev() {
            let restored = std::char::from_u32(code ^ 0x0005_A5A5)?;
            decoded.push(restored);
        }
        Some(decoded)
    }

    pub fn verify_roundtrip(s: &str) -> bool {
        match (Self::canonicalize(s), Self::involution_encode_decode(s)) {
            (Some(canon), Some(roundtripped)) => canon == s && roundtripped == s,
            _ => false,
        }
    }
}

/// Eksakt rasjonal Nash-residual N(x) = (r_br, r_embed, r_tame, r_curv) i Q^4 (null flyttall).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct NashResidualQ {
    pub r_br: RatioI128,
    pub r_embed: RatioI128,
    pub r_tame: RatioI128,
    pub r_curv: RatioI128,
}

impl NashResidualQ {
    /// Eksakt kvadratnorm ||N(x)||^2 = r_br^2 + r_embed^2 + r_tame^2 + r_curv^2 i Q (uten sqrt!).
    pub fn norm_sq(&self) -> Result<RatioI128, FailureCode> {
        let s1 = self.r_br.square()?.add(self.r_embed.square()?)?;
        let s2 = self.r_tame.square()?.add(self.r_curv.square()?)?;
        s1.add(s2)
    }

    /// Eksakt rasjonal Nash-Moser glatteoperator S_lambda(r) = r / (1 + max(0, lambda)).
    pub fn smooth_s_lambda(&self, lambda: RatioI128) -> Result<Self, FailureCode> {
        let clamped_lambda = if lambda.numerator() < 0 {
            RatioI128::from_int(0)
        } else {
            lambda
        };
        let one_plus_lambda = RatioI128::from_int(1).add(clamped_lambda)?;
        let inv_factor = RatioI128::new(one_plus_lambda.denominator(), one_plus_lambda.numerator())?;
        Ok(Self {
            r_br: self.r_br.mul(inv_factor)?,
            r_embed: self.r_embed.mul(inv_factor)?,
            r_tame: self.r_tame.mul(inv_factor)?,
            r_curv: self.r_curv.mul(inv_factor)?,
        })
    }
}

pub struct NashGate;

impl NashGate {
    /// Eksakt sammenligning ||N(x)||^2 <= eps^2 (OPEN), <= tau^2 (HOLD), ellers KILL.
    pub fn evaluate_exact(
        residual: &NashResidualQ,
        eps: RatioI128,
        tau: RatioI128,
        regularizable: bool,
    ) -> GateVerdict {
        if eps.numerator() < 0 || tau.numerator() < 0 {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::StructureInvalid,
            };
        }
        let norm_sq = match residual.norm_sq() {
            Ok(v) => v,
            Err(code) => {
                return GateVerdict {
                    decision: GateStatus::Kill,
                    reason: code,
                };
            }
        };
        let eps_sq = match eps.square() {
            Ok(v) => v,
            Err(code) => {
                return GateVerdict {
                    decision: GateStatus::Kill,
                    reason: code,
                };
            }
        };
        let tau_sq = match tau.square() {
            Ok(v) => v,
            Err(code) => {
                return GateVerdict {
                    decision: GateStatus::Kill,
                    reason: code,
                };
            }
        };

        if norm_sq.le(eps_sq).unwrap_or(false) {
            GateVerdict {
                decision: GateStatus::Open,
                reason: FailureCode::None,
            }
        } else if regularizable && norm_sq.le(tau_sq).unwrap_or(false) {
            GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::NashRegularizableResidual,
            }
        } else {
            GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::NashCollapse,
            }
        }
    }

    /// 2x2 ren-strategi Nash-likevektssjekk (heltallsutbetalinger).
    pub fn verify_2x2_best_response(
        u1: [[i64; 2]; 2],
        u2: [[i64; 2]; 2],
        s1: usize,
        s2: usize,
    ) -> GateStatus {
        if s1 > 1 || s2 > 1 {
            return GateStatus::Kill;
        }
        let other_s1 = 1 - s1;
        let other_s2 = 1 - s2;
        let p1_best = u1[s1][s2] >= u1[other_s1][s2];
        let p2_best = u2[s1][s2] >= u2[s1][other_s2];
        if p1_best && p2_best {
            GateStatus::Open
        } else {
            GateStatus::Kill
        }
    }
}

/// Overlevelsesobservabel S_N(x_0) = prod_{t=0}^{N-1} C(x_t) over eksakte heltallsbaner (0 float).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SurvivalObservableReport {
    pub survival_observable_s_n: u8,
    pub in_realizable_core_r_k: bool,
    pub gate_verdict: GateStatus,
    pub visual_mode: &'static str,
}

pub fn evaluate_survival_observable_exact(
    candidate_milli: &[i64],
    projected_milli: &[i64],
    witness_flags: &[bool],
    q_max_milli: i64,
    residual_tol_milli: i64,
) -> SurvivalObservableReport {
    if candidate_milli.is_empty()
        || candidate_milli.len() != projected_milli.len()
        || candidate_milli.len() != witness_flags.len()
        || residual_tol_milli < 0
    {
        return SurvivalObservableReport {
            survival_observable_s_n: 0,
            in_realizable_core_r_k: false,
            gate_verdict: GateStatus::Kill,
            visual_mode: "VOID_KILLED",
        };
    }

    let mut all_in_core = true;
    let mut i = 0usize;
    while i < candidate_milli.len() {
        let c = candidate_milli[i];
        let p = projected_milli[i];
        if p.abs() > q_max_milli {
            return SurvivalObservableReport {
                survival_observable_s_n: 0,
                in_realizable_core_r_k: false,
                gate_verdict: GateStatus::Kill,
                visual_mode: "VOID_KILLED",
            };
        }
        let defect = (c - p).abs();
        if defect > residual_tol_milli || !witness_flags[i] {
            all_in_core = false;
        }
        i += 1;
    }

    if all_in_core {
        SurvivalObservableReport {
            survival_observable_s_n: 1,
            in_realizable_core_r_k: true,
            gate_verdict: GateStatus::Open,
            visual_mode: "SOLID_COMMITTED_GEOMETRY",
        }
    } else {
        SurvivalObservableReport {
            survival_observable_s_n: 0,
            in_realizable_core_r_k: false,
            gate_verdict: GateStatus::Hold,
            visual_mode: "HOLOGRAM_BLUEPRINT_HOLD",
        }
    }
}

// ============================================================================
// 4. PARSER, GENERATOR (Phi), PROJECTOR (Pi_K) OG PORT (Omega)
// ============================================================================

#[derive(Debug, Clone)]
pub struct RawInput {
    pub object_id: u64,
    pub expression: String,
    pub audit_flag: bool,        // #
    pub irreversible_flag: bool, // !
    pub execute_flag: bool,      // ▶
}

pub struct Parser;

impl Parser {
    pub fn parse(object_id: u64, input: &str) -> Result<Record<Raw>, FailureCode> {
        let trimmed = input.trim();
        if trimmed.is_empty() {
            return Err(FailureCode::SyntaxError);
        }
        let audit_flag = trimmed.contains('#');
        let irreversible_flag = trimmed.contains('!');
        let execute_flag = trimmed.contains('▶');

        if !execute_flag {
            return Err(FailureCode::SyntaxError);
        }

        Ok(Record {
            object_id,
            payload: trimmed.to_string(),
            gate_status: GateStatus::Hold,
            structure_valid: false,
            admissibility_flag: false,
            irreversible: irreversible_flag,
            // HERDET (Funn 3): Irreversibel handling (!) tvinger ALLTID frem revisjonskrav!
            audit_required: audit_flag || irreversible_flag,
            audit_pass: false,
            reproducible: false,
            iks_reversible: false,
            rosetta_identity_ok: false,
            etor_risk_permille: 0,
            etor_threshold_permille: 500,
            pre_commit_g_milli: -1_000,
            clamped_amplitude_permille: clamp_permille_0_1000(500),
            uncertainty_high: false,
            failure_code: FailureCode::None,
            integrity_hash: [0u8; 32],
            or_fuse_latch: 0,
            created_tick: 0,
            tau_coord: 0,
            approved_evidence_id: String::new(),
            _state: PhantomData,
        })
    }
}

/// Flyttallsfritt regelgrensesnitt for domenet (Reality Forge, Poncare.Game m.m.).
pub trait WorldRules {
    fn check_structure(&self, payload: &str) -> bool;
    fn check_admissibility(&self, payload: &str) -> bool;
    fn check_audit(&self, payload: &str) -> bool;
    fn check_reproducible(&self, payload: &str) -> bool;
    fn check_uncertainty(&self, payload: &str) -> bool;
    fn check_rosetta_identity(&self, _payload: &str) -> bool {
        true
    }
    /// Epistemisk risiko pi i promille [0, 1000] (terskel tau = 500 promille).
    fn compute_etor_risk_permille(&self, payload: &str) -> u16 {
        if self.check_uncertainty(payload) {
            750
        } else {
            100
        }
    }
    /// Pre-commit-grense g(x) i tusendeler: må være strengt negativ (< 0) før porten.
    fn compute_pre_commit_g_milli(&self, _payload: &str) -> i64 {
        -1_000
    }
    /// Rå amplitude i promille (klammes til [0, 1000]).
    fn compute_raw_amplitude_permille(&self, _payload: &str) -> i64 {
        500
    }
}

impl Record<Raw> {
    /// Kun Record<Raw> kan gå til Record<Estimate> via Phi.
    pub fn into_estimate(mut self, current_tick: u64, current_tau: u64) -> Record<Estimate> {
        self.created_tick = current_tick;
        self.tau_coord = current_tau;
        self.recast()
    }
}

impl Record<Estimate> {
    /// Steg 1 i Pi_K: Estimate -> Struct.
    pub fn into_struct<R: WorldRules>(mut self, rules: &R) -> Record<Struct> {
        self.structure_valid = rules.check_structure(&self.payload);
        self.clamped_amplitude_permille =
            clamp_permille_0_1000(rules.compute_raw_amplitude_permille(&self.payload));
        self.recast()
    }
}

impl Record<Struct> {
    /// Steg 2 i Pi_K: Struct -> Viability (beregner SHA-256 integritetshash over lengdeprefiksede felt).
    pub fn into_viability<R: WorldRules>(
        mut self,
        rules: &R,
        prev_chain_hash: &[u8; 32],
    ) -> Record<Viability> {
        self.admissibility_flag = rules.check_admissibility(&self.payload);
        self.audit_pass = if self.audit_required {
            rules.check_audit(&self.payload)
        } else {
            true
        };
        self.reproducible = rules.check_reproducible(&self.payload);
        self.iks_reversible = IksCoherenceTest::verify_roundtrip(&self.payload);
        self.rosetta_identity_ok = rules.check_rosetta_identity(&self.payload);
        self.etor_risk_permille =
            clamp_permille_0_1000(rules.compute_etor_risk_permille(&self.payload) as i64);
        self.pre_commit_g_milli = rules.compute_pre_commit_g_milli(&self.payload);
        self.uncertainty_high = rules.check_uncertainty(&self.payload);
        self.integrity_hash = ProjectorPi::compute_record_hash(
            prev_chain_hash,
            self.object_id,
            self.created_tick,
            self.irreversible,
            self.audit_required,
            &self.payload,
        );
        self.recast()
    }
}

pub struct ProjectorPi;

impl ProjectorPi {
    pub fn compute_record_hash(
        prev_chain_hash: &[u8; 32],
        object_id: u64,
        created_tick: u64,
        irreversible: bool,
        audit_required: bool,
        payload: &str,
    ) -> [u8; 32] {
        let mut h = Sha256Hasher::new();
        h.update(b"KY_KAPPA27_RECORD_V1_1");
        h.update(prev_chain_hash);
        h.update_u64_le(object_id);
        h.update_u64_le(created_tick);
        h.update_u8(if irreversible { 1 } else { 0 });
        h.update_u8(if audit_required { 1 } else { 0 });
        h.update_len_prefixed_str(payload);
        h.finalize()
    }
}

/// Mellomlagret blueprint i HOLD (Gamma_eta), sikret med den doble klokkeloven:
/// - Kan ALDRI være taus (krever ikke-tom `defect_note`).
/// - Tid alene åpner ALDRI porten; ved `tick - created_tick > max_hold_ticks` eskalerer
///   autoriteten fra `HoldAuthority::Internal` (P_int) til `HoldAuthority::External` (P_ext).
#[derive(Debug, Clone)]
pub struct HoldBlueprint {
    record: Record<Viability>,
    created_tick: u64,
    max_hold_ticks: u64,
    authority: HoldAuthority,
    defect_note: &'static str,
}

impl HoldBlueprint {
    pub fn record(&self) -> &Record<Viability> {
        &self.record
    }
    pub fn created_tick(&self) -> u64 {
        self.created_tick
    }
    pub fn max_hold_ticks(&self) -> u64 {
        self.max_hold_ticks
    }
    pub fn authority(&self) -> HoldAuthority {
        self.authority
    }
    pub fn defect_note(&self) -> &'static str {
        self.defect_note
    }
}

/// Typet utfall fra GateOmega::admit — den ENESTE måten `Record<Committed>` kan skapes på.
pub enum AdmitOutcome {
    Committed(Record<Committed>),
    Hold {
        blueprint: HoldBlueprint,
        reason: FailureCode,
    },
    Killed {
        reason: FailureCode,
    },
}

pub struct GateOmega;

impl GateOmega {
    pub fn defect_label(reason: FailureCode) -> &'static str {
        match reason {
            FailureCode::None => "NOMINAL_OPEN",
            FailureCode::IllegalStateTransition => "ILLEGAL_STATE_TRANSITION",
            FailureCode::SyntaxError => "SYNTAX_ERROR",
            FailureCode::StructureInvalid => "STRUCTURE_INVALID",
            FailureCode::HashChainBroken => "WITNESS_HASH_CHAIN_BROKEN",
            FailureCode::Inadmissible => "DOMAIN_INADMISSIBLE",
            FailureCode::AuditFailed => "AUDIT_SIGNATURE_MISSING",
            FailureCode::NonReproducible => "NON_REPRODUCIBLE_TRACE",
            FailureCode::IksReversibilityFailed => "IKS_CANONICAL_ROUNDTRIP_FAILED",
            FailureCode::RosettaIdentityDrift => "ROSETTA_IDENTITY_DRIFT",
            FailureCode::NashCollapse => "NASH_EQUILIBRIUM_COLLAPSE",
            FailureCode::NashRegularizableResidual => "HOLD_NASH_REGULARIZABLE_RESIDUAL",
            FailureCode::EtorRiskExceeded => "HOLD_ETOR_RISK_EXCEEDED",
            FailureCode::PostCausalBoundaryCrossed => "POST_CAUSAL_BOUNDARY_CROSSED",
            FailureCode::HighUncertainty => "HOLD_HIGH_UNCERTAINTY_UNANCHORED",
            FailureCode::MissingEvidenceId => "HOLD_MISSING_EXPLICIT_EVIDENCE_ID",
            FailureCode::ZoneOccupiedDefer => "HOLD_BRIDGE_ZONE_OCCUPIED_DEFER",
            FailureCode::HoldDeadlineExceeded => "HOLD_DEADLINE_EXCEEDED_ESCALATE_P_EXT",
            FailureCode::ExternalAuthorityRequired => "HOLD_REQUIRES_P_EXT_AUTHORITY",
            FailureCode::KillLatchActive => "KILL_LATCH_ACTIVE_AWAITING_L01_RESET",
        }
    }

    /// Ren domfunksjon over en uforanderlig kandidat i Viability-fasen.
    pub fn evaluate_verdict(
        candidate: &Record<Viability>,
        witness_ready: bool,
        ctx: &StepContext<'_>,
        requires_external_authority: bool,
    ) -> GateVerdict {
        // 1. Harde sikkerhets- og domenekrav -> KILL
        if !candidate.structure_valid {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::StructureInvalid,
            };
        }
        if !witness_ready {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::HashChainBroken,
            };
        }
        if !candidate.admissibility_flag {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::Inadmissible,
            };
        }
        if !candidate.iks_reversible {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::IksReversibilityFailed,
            };
        }
        if !candidate.rosetta_identity_ok {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::RosettaIdentityDrift,
            };
        }
        if candidate.audit_required && !candidate.audit_pass {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::AuditFailed,
            };
        }
        if !candidate.reproducible {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::NonReproducible,
            };
        }
        if candidate.pre_commit_g_milli >= 0 {
            return GateVerdict {
                decision: GateStatus::Kill,
                reason: FailureCode::PostCausalBoundaryCrossed,
            };
        }

        // 2. Myke port- og sikkerhetssperrer -> HOLD (0 mV, ikke-tom defektårsak)
        if candidate.uncertainty_high {
            return GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::HighUncertainty,
            };
        }
        if candidate.etor_risk_permille >= candidate.etor_threshold_permille {
            return GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::EtorRiskExceeded,
            };
        }
        let clean_evidence = ctx.evidence_id.trim();
        if clean_evidence.is_empty() {
            // Reality Forge-lov: OPEN krever eksplisitt ikke-tom evidence_id!
            return GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::MissingEvidenceId,
            };
        }
        if requires_external_authority && !clean_evidence.starts_with("P_EXT:") {
            // Etter utløpt t_max i HOLD er P_int uttømt; kun P_ext kan løse ut utkastet!
            return GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::ExternalAuthorityRequired,
            };
        }
        if ctx.zone_occupied {
            // Reality Forge-lov: Okkupert bro-sone utsetter (HOLD) fremfor å omgå eller drepe!
            return GateVerdict {
                decision: GateStatus::Hold,
                reason: FailureCode::ZoneOccupiedDefer,
            };
        }

        GateVerdict {
            decision: GateStatus::Open,
            reason: FailureCode::None,
        }
    }

    /// Den ENESTE konstruktørveien til `Record<Committed>`.
    /// Konsumerer `Record<Viability>` ved verdi: på KILL destrueres kandidaten permanent.
    pub fn admit(
        mut candidate: Record<Viability>,
        witness_ready: bool,
        ctx: &StepContext<'_>,
        prior_hold: Option<&HoldBlueprint>,
        next_tau_on_open: u64,
        prev_or_fuse: u64,
    ) -> AdmitOutcome {
        let requires_ext = match prior_hold {
            Some(bp) => bp.authority == HoldAuthority::External,
            None => false,
        };
        let verdict = Self::evaluate_verdict(&candidate, witness_ready, ctx, requires_ext);
        candidate.gate_status = verdict.decision;
        candidate.failure_code = verdict.reason;

        match verdict.decision {
            GateStatus::Open => {
                let fuse_next = PhaseCommitLogic::or_fuse_commit(
                    prev_or_fuse,
                    digest_low_u64(&candidate.integrity_hash),
                );
                candidate.or_fuse_latch = fuse_next;
                candidate.tau_coord = next_tau_on_open;
                candidate.approved_evidence_id = ctx.evidence_id.trim().to_string();
                AdmitOutcome::Committed(candidate.recast())
            }
            GateStatus::Hold => {
                let max_ticks = if ctx.max_hold_ticks == 0 {
                    1
                } else {
                    ctx.max_hold_ticks
                };
                // Bevar opprinnelig created_tick og eskalert autoritet hvis allerede i HOLD!
                let (origin_tick, authority) = match prior_hold {
                    Some(bp) => (bp.created_tick, bp.authority),
                    None => (candidate.created_tick, HoldAuthority::Internal),
                };
                let defect_note = Self::defect_label(verdict.reason);
                AdmitOutcome::Hold {
                    blueprint: HoldBlueprint {
                        record: candidate,
                        created_tick: origin_tick,
                        max_hold_ticks: max_ticks,
                        authority,
                        defect_note,
                    },
                    reason: verdict.reason,
                }
            }
            GateStatus::Kill => AdmitOutcome::Killed {
                reason: verdict.reason,
            },
        }
    }
}

// ============================================================================
// 5. FORSEGLET WITNESS LOG (SHA-256 OVER ALLE FELT, APPEND-ONLY)
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WitnessEvent {
    event_id: u64,
    object_id: u64,
    prev_hash: [u8; 32],
    record_integrity_hash: [u8; 32],
    event_hash: [u8; 32],
    operation: &'static str,
    evidence_id: String,
    note: &'static str,
    result: GateStatus,
    reason_code: FailureCode,
    hold_authority: HoldAuthority,
    actuator_mv: u16,
    timestamp: u64,
    tau_coord: u64,
}

impl WitnessEvent {
    pub fn event_id(&self) -> u64 {
        self.event_id
    }
    pub fn object_id(&self) -> u64 {
        self.object_id
    }
    pub fn prev_hash(&self) -> &[u8; 32] {
        &self.prev_hash
    }
    pub fn record_integrity_hash(&self) -> &[u8; 32] {
        &self.record_integrity_hash
    }
    pub fn event_hash(&self) -> &[u8; 32] {
        &self.event_hash
    }
    pub fn operation(&self) -> &'static str {
        self.operation
    }
    pub fn evidence_id(&self) -> &str {
        &self.evidence_id
    }
    pub fn note(&self) -> &'static str {
        self.note
    }
    pub fn result(&self) -> GateStatus {
        self.result
    }
    pub fn reason_code(&self) -> FailureCode {
        self.reason_code
    }
    pub fn hold_authority(&self) -> HoldAuthority {
        self.hold_authority
    }
    pub fn actuator_mv(&self) -> u16 {
        self.actuator_mv
    }
    pub fn timestamp(&self) -> u64 {
        self.timestamp
    }
    pub fn tau_coord(&self) -> u64 {
        self.tau_coord
    }

    /// Rekalkulerer SHA-256 over SAMTLIGE felt i hendelsen med lengdeprefikset strenginnramming.
    pub fn compute_expected_hash(&self) -> [u8; 32] {
        let mut h = Sha256Hasher::new();
        h.update(b"KY_KAPPA27_WITNESS_V1_1");
        h.update(&self.prev_hash);
        h.update_u64_le(self.event_id);
        h.update_u64_le(self.object_id);
        h.update(&self.record_integrity_hash);
        h.update_u64_le(self.timestamp);
        h.update_u64_le(self.tau_coord);
        h.update_u16_le(self.actuator_mv);
        h.update_u8(self.result as u8);
        h.update_u8(self.reason_code as u8);
        h.update_u8(self.hold_authority as u8);
        h.update_len_prefixed_str(self.operation);
        h.update_len_prefixed_str(&self.evidence_id);
        h.update_len_prefixed_str(self.note);
        h.finalize()
    }
}

#[derive(Debug, Clone)]
pub struct WitnessLog {
    events: Vec<WitnessEvent>,
    head_hash: [u8; 32],
}

impl WitnessLog {
    pub const fn new() -> Self {
        Self {
            events: Vec::new(),
            head_hash: [0u8; 32],
        }
    }

    pub fn events(&self) -> &[WitnessEvent] {
        &self.events
    }

    pub fn head_hash(&self) -> &[u8; 32] {
        &self.head_hash
    }

    pub fn len(&self) -> usize {
        self.events.len()
    }

    pub fn is_empty(&self) -> bool {
        self.events.is_empty()
    }

    /// Full kjede- og innholdsverifikasjon: sjekker sekvensnummer, prev_hash-lenking,
    /// spenningsinvariant (`0 mV` i HOLD/KILL) OG rekalkulerer SHA-256 for hvert eneste ledd.
    pub fn verify_chain(&self) -> bool {
        let mut expected_prev = [0u8; 32];
        for (idx, ev) in self.events.iter().enumerate() {
            if ev.event_id != (idx as u64) + 1 {
                return false;
            }
            if ev.prev_hash != expected_prev {
                return false;
            }
            // Spenningsinvariant: HOLD og KILL skal ALDRI bære hvilespenning (> 0 mV)!
            if ev.result != GateStatus::Open && ev.actuator_mv != 0 {
                return false;
            }
            if ev.event_hash != ev.compute_expected_hash() {
                return false;
            }
            expected_prev = ev.event_hash;
        }
        expected_prev == self.head_hash
    }

    #[allow(clippy::too_many_arguments)]
    pub fn append(
        &mut self,
        object_id: u64,
        record_integrity_hash: [u8; 32],
        operation: &'static str,
        evidence_id: &str,
        note: &'static str,
        result: GateStatus,
        reason_code: FailureCode,
        hold_authority: HoldAuthority,
        actuator_mv: u16,
        timestamp: u64,
        tau_coord: u64,
    ) -> [u8; 32] {
        let event_id = (self.events.len() as u64) + 1;
        let prev_hash = self.head_hash;
        let mut ev = WitnessEvent {
            event_id,
            object_id,
            prev_hash,
            record_integrity_hash,
            event_hash: [0u8; 32],
            operation,
            evidence_id: evidence_id.trim().to_string(),
            note,
            result,
            reason_code,
            hold_authority,
            actuator_mv,
            timestamp,
            tau_coord,
        };
        let digest = ev.compute_expected_hash();
        ev.event_hash = digest;
        self.events.push(ev);
        self.head_hash = digest;
        digest
    }
}

// ============================================================================
// 6. KY ENGINE LOOP — KOMPILERINGSTIDS-LÅST REALISERINGSKJEDE
// ============================================================================

pub const ACTUATOR_OPEN_MV: u16 = 5_000;
pub const ACTUATOR_SAFE_ZERO_MV: u16 = 0;

pub struct KyEngine<R: WorldRules> {
    pub rules: R,
    world_state: HashMap<u64, Record<Committed>>,
    blueprints: HashMap<u64, HoldBlueprint>,
    killed_objects: HashSet<u64>,
    witness_log: WitnessLog,
    or_fuse_state: u64,
    actuator_voltage_mv: u16,
    tick: u64,
    tau: u64,
}

impl<R: WorldRules> KyEngine<R> {
    pub fn new(rules: R) -> Self {
        Self {
            rules,
            world_state: HashMap::new(),
            blueprints: HashMap::new(),
            killed_objects: HashSet::new(),
            witness_log: WitnessLog::new(),
            or_fuse_state: 0,
            actuator_voltage_mv: ACTUATOR_SAFE_ZERO_MV,
            tick: 0,
            tau: 0,
        }
    }

    pub fn world_state(&self) -> &HashMap<u64, Record<Committed>> {
        &self.world_state
    }
    pub fn blueprints(&self) -> &HashMap<u64, HoldBlueprint> {
        &self.blueprints
    }
    pub fn killed_objects(&self) -> &HashSet<u64> {
        &self.killed_objects
    }
    pub fn witness_log(&self) -> &WitnessLog {
        &self.witness_log
    }
    pub fn or_fuse_state(&self) -> u64 {
        self.or_fuse_state
    }
    pub fn actuator_voltage_mv(&self) -> u16 {
        self.actuator_voltage_mv
    }
    pub fn tick(&self) -> u64 {
        self.tick
    }
    pub fn tau(&self) -> u64 {
        self.tau
    }

    /// Standard steg med eksplisitt `evidence_id` (sone ledig, `max_hold_ticks = 8`).
    pub fn step(&mut self, object_id: u64, raw_input: &str, evidence_id: &str) -> GateStatus {
        let ctx = StepContext::standard(evidence_id);
        self.step_with_context(object_id, raw_input, &ctx)
    }

    /// Fullstendig typet realiseringssteg:
    /// Raw (○) -> Estimate (◇) -> Struct (□) -> Viability (⬡) -> GateOmega::admit -> Committed (◉)
    pub fn step_with_context(
        &mut self,
        object_id: u64,
        raw_input: &str,
        ctx: &StepContext<'_>,
    ) -> GateStatus {
        self.tick = self.tick.saturating_add(1);

        // 0. Sjekk om objektet står i mekanisk/logisk KILL-lås (krever eksplisitt L01-reset!)
        if self.killed_objects.contains(&object_id) {
            self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
            self.blueprints.remove(&object_id);
            self.witness_log.append(
                object_id,
                [0u8; 32],
                "BLOCKED_BY_KILL_LATCH",
                ctx.evidence_id,
                GateOmega::defect_label(FailureCode::KillLatchActive),
                GateStatus::Kill,
                FailureCode::KillLatchActive,
                HoldAuthority::None,
                ACTUATOR_SAFE_ZERO_MV,
                self.tick,
                self.tau,
            );
            return GateStatus::Kill;
        }

        // Sjekk eventuelt utløpte HOLD-frister ved nåværende klokkeslag før evaluering
        self.sweep_expired_holds();

        // 1. PARSE -> Record<Raw>
        let raw_rec = match Parser::parse(object_id, raw_input) {
            Ok(r) => r,
            Err(code) => {
                self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
                self.blueprints.remove(&object_id);
                self.killed_objects.insert(object_id);
                self.witness_log.append(
                    object_id,
                    [0u8; 32],
                    "PARSE_KILL",
                    ctx.evidence_id,
                    GateOmega::defect_label(code),
                    GateStatus::Kill,
                    code,
                    HoldAuthority::None,
                    ACTUATOR_SAFE_ZERO_MV,
                    self.tick,
                    self.tau,
                );
                return GateStatus::Kill;
            }
        };

        // 2. Phi: Record<Raw> -> Record<Estimate>
        let est_rec: Record<Estimate> = raw_rec.into_estimate(self.tick, self.tau);

        // 3. Pi_K: Record<Estimate> -> Record<Struct> -> Record<Viability>
        let struct_rec: Record<Struct> = est_rec.into_struct(&self.rules);
        let viab_rec: Record<Viability> =
            struct_rec.into_viability(&self.rules, self.witness_log.head_hash());
        let rec_hash = *viab_rec.integrity_hash();

        // 4. Omega: Eneste port inn til Record<Committed>
        let witness_ready = self.witness_log.verify_chain();
        let next_tau = self.tau.saturating_add(1);
        let prior_hold = self.blueprints.get(&object_id);

        match GateOmega::admit(
            viab_rec,
            witness_ready,
            ctx,
            prior_hold,
            next_tau,
            self.or_fuse_state,
        ) {
            AdmitOutcome::Committed(committed_rec) => {
                self.tau = next_tau;
                self.or_fuse_state = committed_rec.or_fuse_latch();
                self.actuator_voltage_mv = ACTUATOR_OPEN_MV;
                self.blueprints.remove(&object_id);
                self.world_state.insert(object_id, committed_rec);
                self.witness_log.append(
                    object_id,
                    rec_hash,
                    "COMMIT_OPEN",
                    ctx.evidence_id,
                    GateOmega::defect_label(FailureCode::None),
                    GateStatus::Open,
                    FailureCode::None,
                    HoldAuthority::None,
                    ACTUATOR_OPEN_MV,
                    self.tick,
                    self.tau,
                );
                GateStatus::Open
            }
            AdmitOutcome::Hold { blueprint, reason } => {
                // 0.00 V i HOLD! Kausal tid tau står stille.
                self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
                let auth = blueprint.authority();
                let note = blueprint.defect_note();
                self.blueprints.insert(object_id, blueprint);
                self.witness_log.append(
                    object_id,
                    rec_hash,
                    "FREEZE_HOLD",
                    ctx.evidence_id,
                    note,
                    GateStatus::Hold,
                    reason,
                    auth,
                    ACTUATOR_SAFE_ZERO_MV,
                    self.tick,
                    self.tau,
                );
                GateStatus::Hold
            }
            AdmitOutcome::Killed { reason } => {
                // KILL kutter spenning til 0 mV, kansellerer ventende blueprint og låser objektet.
                self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
                self.blueprints.remove(&object_id);
                self.killed_objects.insert(object_id);
                self.witness_log.append(
                    object_id,
                    rec_hash,
                    "TERMINATE_KILL",
                    ctx.evidence_id,
                    GateOmega::defect_label(reason),
                    GateStatus::Kill,
                    reason,
                    HoldAuthority::None,
                    ACTUATOR_SAFE_ZERO_MV,
                    self.tick,
                    self.tau,
                );
                GateStatus::Kill
            }
        }
    }

    /// Fremmer veggklokken `tick` uten ny kandidatinnsending.
    /// INVARIANT (Reality Forge & CARBON 02):
    /// - HOLD går ALDRI over til OPEN bare fordi tid går (`tau` og `world_state` er uendret).
    /// - Utløpte blueprints eskalerer autoritet `P_int -> P_ext` og loggføres i `WitnessLog`.
    pub fn advance_ticks(&mut self, delta_ticks: u64) -> usize {
        self.tick = self.tick.saturating_add(delta_ticks);
        if self.actuator_voltage_mv != ACTUATOR_SAFE_ZERO_MV && !self.blueprints.is_empty() {
            self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
        }
        self.sweep_expired_holds()
    }

    fn sweep_expired_holds(&mut self) -> usize {
        let mut expired_ids: Vec<u64> = self
            .blueprints
            .iter()
            .filter_map(|(&obj_id, bp)| {
                let elapsed = self.tick.saturating_sub(bp.created_tick);
                if bp.authority == HoldAuthority::Internal && elapsed > bp.max_hold_ticks {
                    Some(obj_id)
                } else {
                    None
                }
            })
            .collect();
        // Sorter ID-er for 100 % deterministisk hash-rekkefølge uavhengig av HashMap-seed!
        expired_ids.sort_unstable();

        let count = expired_ids.len();
        for obj_id in expired_ids {
            if let Some(bp) = self.blueprints.get_mut(&obj_id) {
                bp.authority = HoldAuthority::External;
                bp.defect_note = GateOmega::defect_label(FailureCode::HoldDeadlineExceeded);
                let rec_hash = *bp.record.integrity_hash();
                self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
                self.witness_log.append(
                    obj_id,
                    rec_hash,
                    "ESCALATE_HOLD_TIMEOUT",
                    "",
                    bp.defect_note,
                    GateStatus::Hold,
                    FailureCode::HoldDeadlineExceeded,
                    HoldAuthority::External,
                    ACTUATOR_SAFE_ZERO_MV,
                    self.tick,
                    self.tau,
                );
            }
        }
        count
    }

    /// Autorisert L01-tilbakestilling etter KILL:
    /// Sletter ALDRI vitnehistorikken — krever ikke-tom `l01_evidence_id` og føyer til nytt ledd!
    pub fn reset_kill_latch(
        &mut self,
        object_id: u64,
        l01_evidence_id: &str,
    ) -> Result<(), FailureCode> {
        let clean_ev = l01_evidence_id.trim();
        if clean_ev.is_empty() {
            return Err(FailureCode::MissingEvidenceId);
        }
        self.tick = self.tick.saturating_add(1);
        self.killed_objects.remove(&object_id);
        self.actuator_voltage_mv = ACTUATOR_SAFE_ZERO_MV;
        self.witness_log.append(
            object_id,
            [0u8; 32],
            "RESET_BY_L01",
            clean_ev,
            "L01_MANUAL_RESET_APPENDED",
            GateStatus::Hold,
            FailureCode::None,
            HoldAuthority::External,
            ACTUATOR_SAFE_ZERO_MV,
            self.tick,
            self.tau,
        );
        Ok(())
    }
}

// ============================================================================
// 7A. REALITY FORGE STANDARD REGLER (LIGHT BRIDGE & ØKONOMISK INVARIANT)
// ============================================================================

pub struct RealityForgeRules;

impl WorldRules for RealityForgeRules {
    fn check_structure(&self, payload: &str) -> bool {
        payload.contains("object:")
    }
    fn check_admissibility(&self, payload: &str) -> bool {
        !payload.contains("infinite_gold")
    }
    fn check_audit(&self, payload: &str) -> bool {
        payload.contains("audit_signed")
    }
    fn check_reproducible(&self, _payload: &str) -> bool {
        true
    }
    fn check_uncertainty(&self, payload: &str) -> bool {
        payload.contains("unanchored")
    }
}

// ============================================================================
// 7B. BRO MOT PONCARE.GAME / MOREAU DUAL-KJEGLE & SO(2) CAYLEY (0 FLOAT)
// ============================================================================

/// Eksakt 2D heltalls-/rasjonal tilstand for Poncare.Game:
/// - Domene K(R_k) = { x in Q^2 | h(x) <= 0 }, der h(x) = x^2 + y^2 - R_k^2
/// - Kontrollbarriere b(x) = -h(x) = R_k^2 - (x^2 + y^2) >= 0 (jf. CARBON 23/24)
/// - Krympende trygg havn S_A(R_k): tom og død (`VOID`) når R_k <= r_min
/// - Moreaus dualkjeglespalting på randen (h(x) == 0):
///     sigma = <x, v> = x*vx + y*vy
///     * sigma < 0  : strengt innover i T_K(x) (0 rekyl)
///     * sigma == 0 : eksakt tangentglidning på Knivseggen (SO(2) Cayley -> 10x resonans!)
///     * sigma > 0  : utover-normalkomponent i N_K(x); krever Moreau-rekylbudsjett mu >= sigma,
///                    ellers HOLD (hvis mu kan hvile opp) eller KILL (hvis rått steg krysser K uten vern).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PoincareStateI64 {
    pub x: i64,
    pub y: i64,
    pub vx: i64,
    pub vy: i64,
    pub radius_r: i64,
    pub stamina_mu: i64,
    pub moreau_projected: bool,
}

impl fmt::Display for PoincareStateI64 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "poincare:x={},y={},vx={},vy={},R={},mu={},moreau={}",
            self.x,
            self.y,
            self.vx,
            self.vy,
            self.radius_r,
            self.stamina_mu,
            if self.moreau_projected { 1 } else { 0 }
        )
    }
}

/// Eksakt rasjonal Cayley-rotasjon Q(p/q) i SO(2) over Q^2:
///   x' = ((q^2 - p^2)*x - 2*p*q*y) / (q^2 + p^2)
///   y' = (2*p*q*x + (q^2 - p^2)*y) / (q^2 + p^2)
/// Bevarer x'^2 + y'^2 == x^2 + y^2 eksakt uten kvadratrøtter eller flyttall!
pub fn cayley_so2_step_exact(
    x: i128,
    y: i128,
    p: i128,
    q: i128,
) -> Result<(RatioI128, RatioI128), FailureCode> {
    if q == 0 && p == 0 {
        return Err(FailureCode::StructureInvalid);
    }
    let q2 = q.checked_mul(q).ok_or(FailureCode::StructureInvalid)?;
    let p2 = p.checked_mul(p).ok_or(FailureCode::StructureInvalid)?;
    let den = q2.checked_add(p2).ok_or(FailureCode::StructureInvalid)?;
    let q2_minus_p2 = q2.checked_sub(p2).ok_or(FailureCode::StructureInvalid)?;
    let two_pq = 2i128
        .checked_mul(p)
        .and_then(|v| v.checked_mul(q))
        .ok_or(FailureCode::StructureInvalid)?;

    let nx_num = q2_minus_p2
        .checked_mul(x)
        .and_then(|a| {
            let b = two_pq.checked_mul(y)?;
            a.checked_sub(b)
        })
        .ok_or(FailureCode::StructureInvalid)?;

    let ny_num = two_pq
        .checked_mul(x)
        .and_then(|a| {
            let b = q2_minus_p2.checked_mul(y)?;
            a.checked_add(b)
        })
        .ok_or(FailureCode::StructureInvalid)?;

    Ok((RatioI128::new(nx_num, den)?, RatioI128::new(ny_num, den)?))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct KnivseggEvaluation {
    pub h_val: i128,
    pub cbf_b_val: i128,
    pub radial_dot_sigma: i128,
    pub on_knife_edge: bool,
    pub resonance_multiplier: u8, // 10x ved eksakt tangentglidning på randen, ellers 1x
    pub moreau_recoil_cost: i128,
}

pub struct PoincareMoreauWorldRules {
    pub r_min_void: i64,
}

impl PoincareMoreauWorldRules {
    pub const fn new(r_min_void: i64) -> Self {
        Self { r_min_void }
    }

    /// Parser "poincare:x=100,y=0,vx=0,vy=10,R=100,mu=500,moreau=1 | audit_signed # ! ▶"
    pub fn parse_state(payload: &str) -> Option<PoincareStateI64> {
        let first_seg = payload.split('|').next()?.trim();
        let token = first_seg.split_whitespace().next()?;
        let kv_part = token.strip_prefix("poincare:")?;

        let mut x = None;
        let mut y = None;
        let mut vx = None;
        let mut vy = None;
        let mut radius_r = None;
        let mut stamina_mu = None;
        let mut moreau_projected = None;

        for pair in kv_part.split(',') {
            let mut it = pair.split('=');
            let k = it.next()?.trim();
            let v = it.next()?.trim();
            if it.next().is_some() {
                return None;
            }
            match k {
                "x" => x = v.parse::<i64>().ok(),
                "y" => y = v.parse::<i64>().ok(),
                "vx" => vx = v.parse::<i64>().ok(),
                "vy" => vy = v.parse::<i64>().ok(),
                "R" => radius_r = v.parse::<i64>().ok(),
                "mu" => stamina_mu = v.parse::<i64>().ok(),
                "moreau" => {
                    moreau_projected = match v {
                        "1" | "true" => Some(true),
                        "0" | "false" => Some(false),
                        _ => None,
                    }
                }
                _ => return None,
            }
        }

        Some(PoincareStateI64 {
            x: x?,
            y: y?,
            vx: vx?,
            vy: vy?,
            radius_r: radius_r?,
            stamina_mu: stamina_mu?,
            moreau_projected: moreau_projected?,
        })
    }

    pub fn evaluate_geometry(&self, s: &PoincareStateI64) -> KnivseggEvaluation {
        let x = s.x as i128;
        let y = s.y as i128;
        let vx = s.vx as i128;
        let vy = s.vy as i128;
        let r = s.radius_r as i128;

        let norm_sq = x * x + y * y;
        let r_sq = r * r;
        let h_val = norm_sq - r_sq; // h(x) <= 0 i K
        let cbf_b_val = -h_val;     // b(x) = -h(x) >= 0 i K
        let sigma = x * vx + y * vy;

        let on_boundary = h_val == 0 && r > (self.r_min_void as i128);
        let tangential_glide = on_boundary && sigma == 0 && (vx != 0 || vy != 0);
        let recoil = if h_val == 0 && sigma > 0 { sigma } else { 0 };

        KnivseggEvaluation {
            h_val,
            cbf_b_val,
            radial_dot_sigma: sigma,
            on_knife_edge: on_boundary,
            resonance_multiplier: if tangential_glide { 10 } else { 1 },
            moreau_recoil_cost: recoil,
        }
    }
}

impl WorldRules for PoincareMoreauWorldRules {
    fn check_structure(&self, payload: &str) -> bool {
        Self::parse_state(payload).is_some()
    }

    fn check_admissibility(&self, payload: &str) -> bool {
        let s = match Self::parse_state(payload) {
            Some(v) => v,
            None => return false,
        };
        // 1. Krympende trygg havn S_A(R_k) = tom mengde når R_k <= r_min -> VOID (KILL)
        if s.radius_r <= self.r_min_void || s.stamina_mu < 0 {
            return false;
        }
        let g = self.evaluate_geometry(&s);
        // 2. Punktet selv må ligge i K (h(x) <= 0 <=> b(x) >= 0)
        if g.h_val > 0 {
            return false;
        }
        // 3. Nagumo-kjeglen på randen (h(x) == 0): hvis sigma > 0 og Moreau-projeksjon er AV,
        //    peker hastigheten rett ut i N_K(x) og bryter levedyktigheten!
        if g.h_val == 0 && g.radial_dot_sigma > 0 && !s.moreau_projected {
            return false;
        }
        true
    }

    fn check_audit(&self, payload: &str) -> bool {
        payload.contains("audit_signed")
    }

    fn check_reproducible(&self, _payload: &str) -> bool {
        true
    }

    fn check_uncertainty(&self, payload: &str) -> bool {
        let s = match Self::parse_state(payload) {
            Some(v) => v,
            None => return true,
        };
        let g = self.evaluate_geometry(&s);
        // Hvis Moreau-projeksjon fanger opp et utover-støt på randen, men rekylkostnaden
        // overstiger nåværende tretthetsmargin mu, fryses overgangen i HOLD (0 mV) til hvile!
        s.moreau_projected && g.moreau_recoil_cost > (s.stamina_mu as i128)
    }

    fn compute_pre_commit_g_milli(&self, payload: &str) -> i64 {
        match Self::parse_state(payload) {
            Some(s) => {
                let g = self.evaluate_geometry(&s);
                // g_pre < 0 i hele det lovlige domenet h(x) <= 0 (inkl. Knivseggen h == 0 -> -1)
                if g.h_val <= 0 {
                    -1_000
                } else {
                    1_000
                }
            }
            None => 1_000,
        }
    }
}

// ============================================================================
// 8. DEMONSTRASJONSKJØRING (BINÆR ENTRYPOINT)
// ============================================================================

fn main() {
    let mut engine = KyEngine::new(RealityForgeRules);

    // 1. Uendelig gull -> KILL (Inadmissible, 0 mV, tau = 0)
    let s1 = engine.step(101, "object:infinite_gold # ! ▶", "WITNESS-101");
    assert_eq!(s1, GateStatus::Kill);
    assert_eq!(engine.tau(), 0);
    assert_eq!(engine.actuator_voltage_mv(), 0);

    // 2. Uforankret lysbro -> HOLD (0 mV, tau = 0, registrert i blueprints med t_max)
    let s2 = engine.step(
        102,
        "object:light_bridge | unanchored | audit_signed # ! ▶",
        "WITNESS-102-DRAFT",
    );
    assert_eq!(s2, GateStatus::Hold);
    assert_eq!(engine.tau(), 0);
    assert_eq!(engine.actuator_voltage_mv(), 0);

    // 3. Forankret lysbro med eksplisitt evidence_id -> OPEN (5000 mV, tau: 0 -> 1)
    let s3 = engine.step(
        102,
        "object:light_bridge | anchored | audit_signed # ! ▶",
        "WITNESS-102-ANCHORED",
    );
    assert_eq!(s3, GateStatus::Open);
    assert_eq!(engine.tau(), 1);
    assert_eq!(engine.actuator_voltage_mv(), 5_000);

    // 4. Poncare.Game / Moreau + SO(2) Knivsegg-bro
    let mut poincare_engine = KyEngine::new(PoincareMoreauWorldRules::new(10));
    let cmd = "poincare:x=60,y=80,vx=-80,vy=60,R=100,mu=250,moreau=1 | audit_signed # ! ▶";
    let s4 = poincare_engine.step(201, cmd, "WITNESS-POINCARE-KNIVSEGG");
    assert_eq!(s4, GateStatus::Open);

    println!("KY Engine v1.1 (kappa_27 Herdet) — L1 Verification Summary");
    println!("  Committed objects (world):  {}", engine.world_state().len());
    println!("  Active blueprints (HOLD):   {}", engine.blueprints().len());
    println!("  Witness log entries:        {}", engine.witness_log().len());
    println!("  Wall-clock ticks (t):       {}", engine.tick());
    println!("  Causal coordinate (tau):    {}", engine.tau());
    println!("  Head SHA-256:               {}", hex_encode_32(engine.witness_log().head_hash()));
    println!("  SHA-256 chain valid:        {}", engine.witness_log().verify_chain());
    println!("  Poincare Knivsegg tau:      {}", poincare_engine.tau());
}

// ============================================================================
// 9. KOMPLETT REGRESJONS- OG BRUDDPRØVESUITE (15 TESTER)
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_01_sha256_nist_vectors() {
        let empty_hex = hex_encode_32(&Sha256Hasher::digest(b""));
        assert_eq!(
            empty_hex,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );

        let abc_hex = hex_encode_32(&Sha256Hasher::digest(b"abc"));
        assert_eq!(
            abc_hex,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn test_02_witness_log_detects_every_field_tampering_and_boundary_shift() {
        let mut engine = KyEngine::new(RealityForgeRules);
        assert_eq!(
            engine.step(
                10,
                "object:light_bridge | unanchored | audit_signed # ! ▶",
                "EV-HOLD-10"
            ),
            GateStatus::Hold
        );
        assert_eq!(
            engine.step(
                10,
                "object:light_bridge | anchored | audit_signed # ! ▶",
                "EV-OPEN-10"
            ),
            GateStatus::Open
        );
        assert!(engine.witness_log().verify_chain());

        // 1. Mutasjon av result (Hold -> Open) fanges umiddelbart
        let mut t1 = engine.witness_log().clone();
        t1.events[0].result = GateStatus::Open;
        assert!(!t1.verify_chain());

        // 2. Mutasjon av reason_code fanges
        let mut t2 = engine.witness_log().clone();
        t2.events[0].reason_code = FailureCode::None;
        assert!(!t2.verify_chain());

        // 3. Mutasjon av object_id fanges
        let mut t3 = engine.witness_log().clone();
        t3.events[1].object_id = 999;
        assert!(!t3.verify_chain());

        // 4. Mutasjon av tau_coord fanges (manglet i både v1 og utkastet!)
        let mut t4 = engine.witness_log().clone();
        t4.events[1].tau_coord = 42;
        assert!(!t4.verify_chain());

        // 5. Mutasjon av timestamp fanges
        let mut t5 = engine.witness_log().clone();
        t5.events[1].timestamp = 99;
        assert!(!t5.verify_chain());

        // 6. Mutasjon av record_integrity_hash fanges
        let mut t6 = engine.witness_log().clone();
        t6.events[1].record_integrity_hash[0] ^= 0x01;
        assert!(!t6.verify_chain());

        // 7. Mutasjon av evidence_id fanges
        let mut t7 = engine.witness_log().clone();
        t7.events[1].evidence_id = "FORGED-EV".to_string();
        assert!(!t7.verify_chain());

        // 8. Ulovlig spenning (> 0 mV) i HOLD avvises selv om hash rekalkuleres!
        let mut t8 = WitnessLog::new();
        t8.append(
            10,
            [0u8; 32],
            "ILLEGAL_HOLD_VOLTAGE",
            "EV",
            "BAD_VOLTAGE",
            GateStatus::Hold,
            FailureCode::HighUncertainty,
            HoldAuthority::Internal,
            2_500, // Forbudt 2.50 V lekkasje!
            1,
            0,
        );
        assert!(!t8.verify_chain());

        // 9. Lengdeprefiks hindrer grenseforskyvnings-kollisjon ("AB","C") != ("A","BC")
        let mut h_left = Sha256Hasher::new();
        h_left.update_len_prefixed_str("AB");
        h_left.update_len_prefixed_str("C");
        let mut h_right = Sha256Hasher::new();
        h_right.update_len_prefixed_str("A");
        h_right.update_len_prefixed_str("BC");
        assert_ne!(h_left.finalize(), h_right.finalize());
    }

    #[test]
    fn test_03_sealed_typestate_pipeline_and_consumed_kill() {
        let rules = RealityForgeRules;
        let raw = Parser::parse(7, "object:light_bridge | anchored | audit_signed # ! ▶").unwrap();
        assert_eq!(raw.phase_name(), "RAW");

        let est = raw.into_estimate(1, 0);
        assert_eq!(est.phase_name(), "ESTIMATE");

        let st = est.into_struct(&rules);
        assert_eq!(st.phase_name(), "STRUCT");
        assert!(st.structure_valid());

        let viab = st.into_viability(&rules, &[0u8; 32]);
        assert_eq!(viab.phase_name(), "VIABILITY");

        let ctx = StepContext::standard("WITNESS-TYPESTATE-7");
        match GateOmega::admit(viab, true, &ctx, None, 1, 0) {
            AdmitOutcome::Committed(comm) => {
                assert_eq!(comm.phase_name(), "COMMITTED");
                assert_eq!(comm.gate_status(), GateStatus::Open);
                assert_eq!(comm.tau_coord(), 1);
                assert_eq!(comm.approved_evidence_id(), "WITNESS-TYPESTATE-7");
            }
            _ => panic!("Forventet Committed fra GateOmega::admit"),
        }
    }

    #[test]
    fn test_04_irreversible_bang_forces_audit_requirement() {
        let mut engine = KyEngine::new(RealityForgeRules);
        // '!' er satt uten '#' og uten 'audit_signed' -> MÅ tvinge audit_required = true og gi KILL!
        let verdict = engine.step(44, "object:reactor_vent ! ▶", "WITNESS-44");
        assert_eq!(verdict, GateStatus::Kill);
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::AuditFailed
        );
        assert_eq!(engine.tau(), 0);
        assert!(engine.world_state().is_empty());

        // Med 'audit_signed' på nytt objekt passerer '!' rent
        let verdict_ok = engine.step(45, "object:reactor_vent | audit_signed ! ▶", "WITNESS-45");
        assert_eq!(verdict_ok, GateStatus::Open);
        assert_eq!(engine.tau(), 1);
    }

    #[test]
    fn test_05_open_requires_non_empty_explicit_evidence_id() {
        let mut engine = KyEngine::new(RealityForgeRules);
        // Gyldig, forankret og signert kandidat, men tom/blank evidence_id -> HOLD (aldri OPEN!)
        let s_empty = engine.step(
            50,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            "   ",
        );
        assert_eq!(s_empty, GateStatus::Hold);
        assert_eq!(engine.tau(), 0);
        assert_eq!(engine.actuator_voltage_mv(), 0);
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::MissingEvidenceId
        );

        // Når gyldig evidence_id leveres, åpner porten
        let s_open = engine.step(
            50,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            "WITNESS-50-VERIFIED",
        );
        assert_eq!(s_open, GateStatus::Open);
        assert_eq!(engine.tau(), 1);
        assert_eq!(engine.actuator_voltage_mv(), 5_000);
        assert!(engine.blueprints().is_empty());
    }

    #[test]
    fn test_06_occupied_zone_defers_rather_than_bypasses_or_kills() {
        let mut engine = KyEngine::new(RealityForgeRules);
        let ctx_busy = StepContext {
            evidence_id: "WITNESS-60",
            zone_occupied: true,
            max_hold_ticks: 5,
        };
        let s1 = engine.step_with_context(
            60,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            &ctx_busy,
        );
        assert_eq!(s1, GateStatus::Hold);
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::ZoneOccupiedDefer
        );
        assert_eq!(engine.tau(), 0);
        assert_eq!(engine.actuator_voltage_mv(), 0);
        assert!(engine.blueprints().contains_key(&60));

        // Sonen frigjøres -> realisering gjennomføres uten tap
        let ctx_clear = StepContext {
            evidence_id: "WITNESS-60",
            zone_occupied: false,
            max_hold_ticks: 5,
        };
        let s2 = engine.step_with_context(
            60,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            &ctx_clear,
        );
        assert_eq!(s2, GateStatus::Open);
        assert_eq!(engine.tau(), 1);
    }

    #[test]
    fn test_07_dual_clock_hold_never_opens_by_time_and_escalates_authority() {
        let mut engine = KyEngine::new(RealityForgeRules);
        let ctx = StepContext {
            evidence_id: "WITNESS-70",
            zone_occupied: false,
            max_hold_ticks: 4,
        };
        assert_eq!(
            engine.step_with_context(
                70,
                "object:light_bridge | unanchored | audit_signed # ! ▶",
                &ctx
            ),
            GateStatus::Hold
        );
        assert_eq!(
            engine.blueprints().get(&70).unwrap().authority(),
            HoldAuthority::Internal
        );

        // Innenfor t_max = 4 ticks: fortsatt P_int, ingen eskalering, ingen OPEN
        assert_eq!(engine.advance_ticks(4), 0);
        assert_eq!(engine.tau(), 0);
        assert!(engine.world_state().is_empty());
        assert_eq!(
            engine.blueprints().get(&70).unwrap().authority(),
            HoldAuthority::Internal
        );

        // Tick +1 passerer fristen (elapsed = 5 > 4): eskalerer P_int -> P_ext, fortsatt 0 mV og tau = 0!
        assert_eq!(engine.advance_ticks(1), 1);
        assert_eq!(engine.tau(), 0);
        assert_eq!(engine.actuator_voltage_mv(), 0);
        assert!(engine.world_state().is_empty());
        assert_eq!(
            engine.blueprints().get(&70).unwrap().authority(),
            HoldAuthority::External
        );
        assert_eq!(
            engine.witness_log().events().last().unwrap().operation(),
            "ESCALATE_HOLD_TIMEOUT"
        );

        // Forsøk på å åpne med kun intern P_int-evidens avvises i HOLD (ExternalAuthorityRequired)
        let s_int_denied = engine.step(
            70,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            "P_INT:SELF_APPROVAL",
        );
        assert_eq!(s_int_denied, GateStatus::Hold);
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::ExternalAuthorityRequired
        );

        // Eksplisitt ekstern autoritet P_EXT løser ut til OPEN
        let s_ext_ok = engine.step(
            70,
            "object:light_bridge | anchored | audit_signed # ! ▶",
            "P_EXT:HARBOR_MASTER_SEAL_70",
        );
        assert_eq!(s_ext_ok, GateStatus::Open);
        assert_eq!(engine.tau(), 1);
    }

    #[test]
    fn test_08_kill_cancels_blueprint_latches_and_reset_appends_witness() {
        let mut engine = KyEngine::new(RealityForgeRules);
        assert_eq!(
            engine.step(
                80,
                "object:light_bridge | unanchored | audit_signed # ! ▶",
                "EV-80"
            ),
            GateStatus::Hold
        );
        assert!(engine.blueprints().contains_key(&80));

        // Ulovlig ressurs på samme ID -> KILL kansellerer ventende blueprint og setter KILL-lås
        assert_eq!(
            engine.step(80, "object:infinite_gold # ! ▶", "EV-80-BAD"),
            GateStatus::Kill
        );
        assert!(!engine.blueprints().contains_key(&80));
        assert!(engine.killed_objects().contains(&80));
        assert_eq!(engine.actuator_voltage_mv(), 0);

        // Forsøk på å kjøre videre uten L01-reset blokkeres av KILL-låsen
        assert_eq!(
            engine.step(
                80,
                "object:light_bridge | anchored | audit_signed # ! ▶",
                "EV-80-RETRY"
            ),
            GateStatus::Kill
        );
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::KillLatchActive
        );

        // Tom reset-ID avvises
        assert_eq!(
            engine.reset_kill_latch(80, ""),
            Err(FailureCode::MissingEvidenceId)
        );

        // Autorisert L01-reset sletter IKKE vitnehistorikken — den legger til nytt ledd!
        let len_before = engine.witness_log().len();
        engine.reset_kill_latch(80, "L01-MARIUS-BENCH-RESET").unwrap();
        assert_eq!(engine.witness_log().len(), len_before + 1);
        assert_eq!(
            engine.witness_log().events().last().unwrap().operation(),
            "RESET_BY_L01"
        );

        // Nå kan objekt 80 realiseres på nytt
        assert_eq!(
            engine.step(
                80,
                "object:light_bridge | anchored | audit_signed # ! ▶",
                "EV-80-CLEAN"
            ),
            GateStatus::Open
        );
        assert!(engine.witness_log().verify_chain());
    }

    #[test]
    fn test_09_iks_coherence_rejects_lossy_and_control_corruption() {
        assert!(IksCoherenceTest::verify_roundtrip(
            "object:light_bridge | anchored | audit_signed # ! ▶"
        ));
        // U+FFFD replacement char (tapspreget dekoding) avvises!
        assert!(!IksCoherenceTest::verify_roundtrip(
            "object:light_bridge\u{FFFD} | anchored ▶"
        ));
        // Kontrolltegn avvises!
        assert!(!IksCoherenceTest::verify_roundtrip(
            "object:light_bridge\x07 | anchored ▶"
        ));

        let mut engine = KyEngine::new(RealityForgeRules);
        let res = engine.step(
            90,
            "object:light_bridge\u{FFFD} | anchored | audit_signed # ! ▶",
            "EV-90",
        );
        assert_eq!(res, GateStatus::Kill);
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::IksReversibilityFailed
        );
    }

    #[test]
    fn test_10_tau_causal_coordinate_and_monotonic_or_fuse() {
        let s0 = 0b1010_u64;
        let delta = 0b0101_u64;
        let phase = PhaseCommitLogic::xor_reversible_phase(s0, delta);
        assert_eq!(PhaseCommitLogic::xor_reversible_phase(phase, delta), s0);

        let p1 = PhaseCommitLogic::or_fuse_commit(s0, delta);
        assert_eq!(p1 & s0, s0);
        assert_eq!(p1, 0b1111_u64);
    }

    #[test]
    fn test_11_exact_rational_nash_gate_and_nash_moser_smoothing() {
        let u1 = [[3, 0], [5, 1]];
        let u2 = [[3, 5], [0, 1]];
        assert_eq!(NashGate::verify_2x2_best_response(u1, u2, 0, 0), GateStatus::Kill);
        assert_eq!(NashGate::verify_2x2_best_response(u1, u2, 0, 1), GateStatus::Kill);
        assert_eq!(NashGate::verify_2x2_best_response(u1, u2, 1, 0), GateStatus::Kill);
        assert_eq!(NashGate::verify_2x2_best_response(u1, u2, 1, 1), GateStatus::Open);

        // Residual (1/5, 1/5, 1/5, 1/5) har ||N||^2 = 4/25 = 0.16 > eps^2 = (3/20)^2 = 9/400 = 0.0225
        let fifth = RatioI128::new(1, 5).unwrap();
        let res = NashResidualQ {
            r_br: fifth,
            r_embed: fifth,
            r_tame: fifth,
            r_curv: fifth,
        };
        let eps = RatioI128::new(3, 20).unwrap(); // 0.15
        let tau = RatioI128::new(1, 2).unwrap();  // 0.50
        assert_eq!(
            NashGate::evaluate_exact(&res, eps, tau, true).decision,
            GateStatus::Hold
        );

        // Nash-Moser S_lambda med lambda = 4 skalerer hver komponent med 1/5 -> ||N||^2 = 4/625 <= 9/400 -> OPEN!
        let smoothed = res.smooth_s_lambda(RatioI128::from_int(4)).unwrap();
        assert_eq!(
            NashGate::evaluate_exact(&smoothed, eps, tau, true).decision,
            GateStatus::Open
        );
    }

    #[test]
    fn test_12_survival_observable_s_n_and_visual_modes() {
        let open_rep = evaluate_survival_observable_exact(
            &[200, 400, 600, 800],
            &[200, 400, 600, 800],
            &[true, true, true, true],
            1_000,
            0,
        );
        assert_eq!(open_rep.survival_observable_s_n, 1);
        assert!(open_rep.in_realizable_core_r_k);
        assert_eq!(open_rep.gate_verdict, GateStatus::Open);
        assert_eq!(open_rep.visual_mode, "SOLID_COMMITTED_GEOMETRY");

        let hold_rep = evaluate_survival_observable_exact(
            &[200, 550, 700],
            &[200, 500, 700],
            &[true, true, true],
            1_000,
            0,
        );
        assert_eq!(hold_rep.survival_observable_s_n, 0);
        assert!(!hold_rep.in_realizable_core_r_k);
        assert_eq!(hold_rep.gate_verdict, GateStatus::Hold);
        assert_eq!(hold_rep.visual_mode, "HOLOGRAM_BLUEPRINT_HOLD");
    }

    #[test]
    fn test_13_poincare_moreau_world_rules_nagumo_and_knivsegg_cayley() {
        // 1. Verifiser eksakt rasjonal Cayley SO(2)-rotasjon uten kvadratrot:
        //    (100, 0) med p=1, q=2 -> (60, 80), og 60^2 + 80^2 == 100^2!
        let (rx, ry) = cayley_so2_step_exact(100, 0, 1, 2).unwrap();
        assert_eq!(rx, RatioI128::from_int(60));
        assert_eq!(ry, RatioI128::from_int(80));
        assert_eq!(
            rx.square().unwrap().add(ry.square().unwrap()).unwrap(),
            RatioI128::from_int(10_000)
        );

        let rules = PoincareMoreauWorldRules::new(10);
        // 2. Tangentiell glidning på Knivseggen (x=60, y=80, vx=-80, vy=60 -> <x,v> = 0, h = 0) -> 10x resonans!
        let st_glide = PoincareStateI64 {
            x: 60,
            y: 80,
            vx: -80,
            vy: 60,
            radius_r: 100,
            stamina_mu: 200,
            moreau_projected: true,
        };
        let eval_glide = rules.evaluate_geometry(&st_glide);
        assert_eq!(eval_glide.h_val, 0);
        assert_eq!(eval_glide.cbf_b_val, 0);
        assert_eq!(eval_glide.radial_dot_sigma, 0);
        assert!(eval_glide.on_knife_edge);
        assert_eq!(eval_glide.resonance_multiplier, 10);

        let mut engine = KyEngine::new(rules);
        let cmd_glide = format!("{} | audit_signed # ! ▶", st_glide);
        assert_eq!(engine.step(301, &cmd_glide, "EV-301"), GateStatus::Open);

        // 3. Utover-hastighet på randen UTEN Moreau-projeksjon (<x,v> = +1000 > 0) -> Nagumo-brudd (KILL)
        let st_escape = PoincareStateI64 {
            x: 100,
            y: 0,
            vx: 10,
            vy: 0,
            radius_r: 100,
            stamina_mu: 5_000,
            moreau_projected: false,
        };
        let cmd_escape = format!("{} | audit_signed # ! ▶", st_escape);
        assert_eq!(engine.step(302, &cmd_escape, "EV-302"), GateStatus::Kill);

        // 4. Med Moreau-projeksjon, men rekylkostnad (1000) > rest-stamina mu (400) -> HOLD (0 mV hvile!)
        let st_tired = PoincareStateI64 {
            x: 100,
            y: 0,
            vx: 10,
            vy: 0,
            radius_r: 100,
            stamina_mu: 400,
            moreau_projected: true,
        };
        let cmd_tired = format!("{} | audit_signed # ! ▶", st_tired);
        assert_eq!(engine.step(303, &cmd_tired, "EV-303"), GateStatus::Hold);

        // 5. Krympet S_A(R_k) = tom mengde (R = 10 <= r_min = 10) -> VOID (KILL)
        let st_void = PoincareStateI64 {
            x: 0,
            y: 0,
            vx: 0,
            vy: 0,
            radius_r: 10,
            stamina_mu: 500,
            moreau_projected: true,
        };
        let cmd_void = format!("{} | audit_signed # ! ▶", st_void);
        assert_eq!(engine.step(304, &cmd_void, "EV-304"), GateStatus::Kill);
    }

    #[test]
    fn test_14_pre_commit_boundary_and_permille_clamping() {
        assert_eq!(clamp_permille_0_1000(-250), 0);
        assert_eq!(clamp_permille_0_1000(425), 425);
        assert_eq!(clamp_permille_0_1000(9_999), 1_000);

        struct PostCausalViolationRules;
        impl WorldRules for PostCausalViolationRules {
            fn check_structure(&self, _p: &str) -> bool { true }
            fn check_admissibility(&self, _p: &str) -> bool { true }
            fn check_audit(&self, _p: &str) -> bool { true }
            fn check_reproducible(&self, _p: &str) -> bool { true }
            fn check_uncertainty(&self, _p: &str) -> bool { false }
            fn compute_pre_commit_g_milli(&self, _p: &str) -> i64 { 0 } // g >= 0 -> KILL!
        }

        let mut engine = KyEngine::new(PostCausalViolationRules);
        assert_eq!(
            engine.step(401, "object:tachyon_jump ▶", "EV-401"),
            GateStatus::Kill
        );
        assert_eq!(
            engine.witness_log().events().last().unwrap().reason_code(),
            FailureCode::PostCausalBoundaryCrossed
        );
    }

    #[test]
    fn test_15_zero_float_tokens_in_executable_rust_source() {
        let src = include_str!("26_ky_engine_v1_1_kappa27_herdet.rs");
        let bytes = src.as_bytes();
        let mut code_only = String::with_capacity(src.len());
        let mut i = 0usize;

        // Stripp linjekommentarer, blokkommentarer og strengliteraler før token-sjekk
        while i < bytes.len() {
            if i + 1 < bytes.len() && bytes[i] == b'/' && bytes[i + 1] == b'/' {
                while i < bytes.len() && bytes[i] != b'\n' {
                    i += 1;
                }
            } else if i + 1 < bytes.len() && bytes[i] == b'/' && bytes[i + 1] == b'*' {
                i += 2;
                while i + 1 < bytes.len() && !(bytes[i] == b'*' && bytes[i + 1] == b'/') {
                    i += 1;
                }
                i += 2;
            } else if bytes[i] == b'"' {
                i += 1;
                while i < bytes.len() {
                    if bytes[i] == b'\\' {
                        i += 2;
                    } else if bytes[i] == b'"' {
                        i += 1;
                        break;
                    } else {
                        i += 1;
                    }
                }
                code_only.push(' ');
            } else {
                code_only.push(bytes[i] as char);
                i += 1;
            }
        }

        // Erstatt Rusts intervall-operator ".." med mellomrom slik at slice-ranges (56..64)
        // skilles rent fra desimalpunktum i flyttallsliteraler (0.5, 1.0).
        let normalized = code_only.replace("..", " ");

        // Bygg opp de forbudte type-identifikatorene dynamisk så selv strengstripping er dobbeltsikret
        let forbidden_a = ['f', '3', '2'].iter().collect::<String>();
        let forbidden_b = ['f', '6', '4'].iter().collect::<String>();

        for token in normalized.split(|c: char| !c.is_ascii_alphanumeric() && c != '_' && c != '.') {
            if token.is_empty() {
                continue;
            }
            assert_ne!(token, forbidden_a, "Fant forbudt flyttallstype i kildekoden!");
            assert_ne!(token, forbidden_b, "Fant forbudt flyttallstype i kildekoden!");

            // Sjekk at ingen talliteraler inneholder desimalpunktum (f.eks. 0.5 eller 1.0)
            let first = token.as_bytes()[0];
            if first.is_ascii_digit() && !token.starts_with("0x") {
                assert!(
                    !token.contains('.'),
                    "Fant forbudt flyttallsliteral i kildekoden: {}",
                    token
                );
            }
        }
    }
}
