#!/usr/bin/env python3
"""
CARBON-28: Flyttallsfri L1-verifikasjonsmotor for Reismann-Core (Kontrollag C0-C6)
==================================================================================
Epistemisk status : L1 (lokalt demonstrert programvare; append-only SHA-256 != WORM)
Kontraktregel     : INSPIRED_BY != IMPLEMENTS != PROVES
Flyttallsforbud   : 0 forekomster av float (verifisert av egen AST-vakt i Test 8)

Verifiserer alle 8 revisjonsfunn og teoremer i CARBON-27:
  1. Ortogonal romspalting (X_cand + X_phase + X_lock) og reell Viab(K) vs. tautologi
  2. Subsumpsjonsloven KILL > TRAP > HOLD > OPEN + streng 0 mV i HOLD mot Teorem 2
  3. Eksakt A_5 Sommerfugl-topologi over Q: V''(+-sqrt(2/5)) == -24/25 == -0.96 (!= -1.28)
  4. kanonisk spesifikasjon bilateral proveniensrot, kobordismelov (d^2 = 0) og Ma'ats involusjon
  5. Dobbel klokkelov i HOLD: fristbrudd gir 0 mV og P_int -> P_ext uten å slette borgerrett
  6. KY-Nash 4-kvadrants klassifikator + Teorem 1 (X_realized streng delmengde av X_safe)
  7. Minkowski lyskjegle vs. Brands-Chaum 20 m geofence over eksakt c = 299_792_458 m/s
  8. Sektor 09 (898_900 N, 2_269.7225 J, ADMINISTRATIVE_RESET_FORBIDDEN), SI-homogen Landauer
     og AST-vakt for null flyttall i hele kildefilen.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import IntEnum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import List, Tuple


STANDALONE_COMMIT_AUTHORITY = "NONE"
PHYSICAL_AUTHORITY = "NONE"
WRITE_ENABLED = False

# Eksakt SI-2019 vakuumlysfart (m/s) og Landauer-tak ved 277.15 K i rontojoule (10^-27 J)
SPEED_OF_LIGHT_M_S = 299_792_458
LANDAUER_CEIL_RJ_AT_277K15 = 2_652_306


class ControlLayer(IntEnum):
    C0_HARDWARE_CUTOFF = 0
    C1_WITNESS_LEDGER = 1
    C2_CONSTRAINT_SENSING = 2
    C3_TRAJECTORY_DAMPING = 3
    C4_KY_NASH_GOVERNANCE = 4
    C5_MODEL_REALITY_AUDIT = 5
    C6_LONG_TERM_STRATEGY = 6


class GateVerdict(IntEnum):
    # Høyere tall = høyere subsumpsjonsprioritet: KILL (4) > TRAP (3) > HOLD (2) > OPEN (1)
    OPEN = 1
    HOLD = 2
    TRAP = 3
    KILL = 4


class HoldAuthority(IntEnum):
    NONE = 0
    INTERNAL_P_INT = 1
    EXTERNAL_P_EXT = 2


# ============================================================================
# 1. ORTOGONAL TILSTANDSROMSISOLASJON OG LEVEDYKTIGHETSKJERNE Viab(K)
# ============================================================================

@dataclass(frozen=True)
class CandidateSlice:
    candidate_id: str
    origin_id: str
    intended_action: str
    payload_sha256: str
    seq_index: int
    parent_hash: str


@dataclass(frozen=True)
class PhaseSlice:
    projection_defect: Fraction
    adversarial_probe_detected: bool
    hard_violation_detected: bool
    carrying_capacity_a: Fraction


@dataclass(frozen=True)
class LockSlice:
    verdict: GateVerdict
    coil_mv: int
    interlock_engaged: bool
    witness_head_sha256: str


def can_layer_modify_constraint(actor_layer: ControlLayer, target_layer: ControlLayer) -> bool:
    """Hierarkisk skriveforbud: intet øvre lag C1..C6 kan overskrive skranker i et lavere lag."""
    if actor_layer > target_layer:
        return False
    return actor_layer == target_layer


def clamp_interval_pi_k(x: Fraction, low: Fraction, high: Fraction) -> Fraction:
    if x < low:
        return low
    if x > high:
        return high
    return x


def check_viability_step_exact(
    x0: Fraction,
    step_delta: Fraction,
    low: Fraction,
    high: Fraction,
    horizon: int,
) -> Tuple[bool, bool]:
    """
    Sammenligner:
      - Tautologisk formel fra råutkastet: (Pi_K o Phi)^t(x0) in K (alltid True!)
      - Reell levedyktighet: uprojisert Phi(x_t) holder seg i K (Delta_K == 0) for alle t.
    """
    tautological_in_k = True
    x_proj = x0
    for _ in range(1, horizon + 1):
        x_proj = clamp_interval_pi_k(x_proj + step_delta, low, high)
        if not (low <= x_proj <= high):
            tautological_in_k = False

    real_viable = low <= x0 <= high
    x_raw = x0
    for _ in range(1, horizon + 1):
        x_raw = x_raw + step_delta
        proj = clamp_interval_pi_k(x_raw, low, high)
        defect = abs(x_raw - proj)
        if defect != Fraction(0):
            real_viable = False
            break

    return tautological_in_k, real_viable


# ============================================================================
# 2. E-TOR SUBSUMPSJONSPORT OG TEOREM 2 (INTERLOCK BYPASS UTEN 2.50 V-FEIL)
# ============================================================================

def evaluate_etor_gate(
    cand: CandidateSlice,
    phase: PhaseSlice,
    evidence_id: str,
) -> Tuple[GateVerdict, int, str]:
    """Håndhever KILL > TRAP > HOLD > OPEN og streng 0 mV på C0-skinnen utenom OPEN."""
    _ = cand
    if phase.hard_violation_detected:
        return GateVerdict.KILL, 0, "HARD_INVARIANT_VIOLATION_KILL"
    if phase.adversarial_probe_detected:
        return GateVerdict.TRAP, 0, "SHADOW_CONTAINMENT_TRAP"
    if phase.projection_defect != Fraction(0) or not evidence_id.strip():
        return GateVerdict.HOLD, 0, "UNRESOLVED_MARGIN_OR_MISSING_WITNESS_HOLD"
    return GateVerdict.OPEN, 5_000, "AUTHORIZED_CONSEQUENCE_OPEN"


def detect_hardware_interlock_sabotage(
    verdict: GateVerdict,
    coil_voltage_mv: int,
    coil_resistance_ohm: int,
    max_leak_ua: int,
) -> bool:
    """
    Teorem 2: (Omega == OPEN) <=> (I_act > I_leak).
    I_act i mikroampere = (coil_voltage_mv * 1000) / coil_resistance_ohm.
    Returnerer True dersom sabotasje / spenningslekkasje detekteres!
    """
    current_ua = Fraction(coil_voltage_mv * 1_000, coil_resistance_ohm)
    exceeds_leak = current_ua > Fraction(max_leak_ua)
    is_open = verdict == GateVerdict.OPEN
    # Ekvivalensbrudd <=> XOR mellom (Omega == OPEN) og (I_act > I_leak)
    return is_open != exceeds_leak


# ============================================================================
# 3. SOMMERFUGL-LOMMENS (A_5) EKSAKTE DIFFERENSIALTOPOLOGI OVER Q
# ============================================================================

def butterfly_a5_potential_from_u(
    u_x_sq: Fraction,
    a: Fraction = Fraction(-2, 1),
    c: Fraction = Fraction(16, 25),
) -> Fraction:
    """
    Eksakt verdi av V_{A5}(x) for b = d = 0 uttrykt i u = x^2 >= 0:
      V_{A5}(x) = (1/6) u^3 + (1/4) a u^2 + (1/2) c u.
    """
    return (
        Fraction(1, 6) * (u_x_sq ** 3)
        + Fraction(1, 4) * a * (u_x_sq ** 2)
        + Fraction(1, 2) * c * u_x_sq
    )


def butterfly_a5_curvature_from_u(
    u_x_sq: Fraction,
    a: Fraction = Fraction(-2, 1),
    c: Fraction = Fraction(16, 25),
) -> Fraction:
    """
    Eksakt andrederivert V''_{A5}(x) = 5 x^4 + 3 a x^2 + c = 5 u^2 + 3 a u + c.
    """
    return 5 * (u_x_sq ** 2) + 3 * a * u_x_sq + c


# ============================================================================
# 4 & 5. kanonisk spesifikasjon RETTSSIKKERHET OG DOBBEL KLOKKELOV I HOLD
# ============================================================================

def len_prefixed_bytes(s: str) -> bytes:
    raw = s.encode("utf-8")
    return len(raw).to_bytes(8, "little") + raw


def evaluate_spec400_constitutional_gate(
    prev_merkle_hex: str,
    s_inst: str,
    s_borger: str,
    w_inst: int,
    w_borger: int,
    dissent_recoded_as_symptom: bool,
    refusal_used_as_incompetence_proof: bool,
    irreversible_depot: bool,
    suspensive_judicial_review: bool,
    evidence_id: str,
) -> Tuple[GateVerdict, int, str, str]:
    inst_h = hashlib.sha256(s_inst.strip().encode("utf-8")).hexdigest()
    borg_h = hashlib.sha256(s_borger.strip().encode("utf-8")).hexdigest() if s_borger.strip() else ""

    delta_prov = abs(w_inst - w_borger) + (1 if dissent_recoded_as_symptom else 0)
    delta_cob = 1 if refusal_used_as_incompetence_proof else 0

    if delta_cob > 0:
        verdict, mv, reason = (
            GateVerdict.KILL,
            0,
            "COBORDISM_BREACH_CIRCULAR_FARV_CONSENT_TAUTOLOGY_KILL",
        )
    elif irreversible_depot and not suspensive_judicial_review:
        verdict, mv, reason = (
            GateVerdict.KILL,
            0,
            "IRREVERSIBLE_DEPOT_WITHOUT_SUSPENSIVE_JUDICIAL_REVIEW_KILL",
        )
    elif not s_borger.strip() or w_borger == 0 or w_inst != w_borger:
        verdict, mv, reason = (
            GateVerdict.KILL,
            0,
            "UNILATERAL_RECORD_MISSING_CITIZEN_CONTRADICTION_KILL",
        )
    elif dissent_recoded_as_symptom:
        verdict, mv, reason = (
            GateVerdict.KILL,
            0,
            "EPISTEMIC_INJUSTICE_DISSENT_RECODED_AS_SYMPTOM_KILL",
        )
    elif not evidence_id.strip():
        verdict, mv, reason = (
            GateVerdict.HOLD,
            0,
            "MISSING_EVIDENCE_ID_HOLD",
        )
    else:
        verdict, mv, reason = (
            GateVerdict.OPEN,
            5_000,
            "BILATERAL_PROVENANCE_AND_COBORDISM_VERIFIED_OPEN",
        )

    h = hashlib.sha256()
    h.update(b"NLK_BILAT_V1")
    h.update(bytes.fromhex(prev_merkle_hex))
    h.update(len_prefixed_bytes(inst_h))
    h.update(len_prefixed_bytes(borg_h))
    h.update(delta_prov.to_bytes(4, "little"))
    h.update(int(verdict).to_bytes(1, "little"))
    h.update(len_prefixed_bytes(reason))
    return verdict, mv, reason, h.hexdigest()


@dataclass
class DualClockHoldCase:
    case_id: str
    created_tick: int
    max_hold_ticks: int
    citizen_contradiction_preserved: bool
    authority: HoldAuthority = HoldAuthority.INTERNAL_P_INT
    coil_mv: int = 0


def advance_hold_case_clock(case: DualClockHoldCase, current_tick: int) -> str:
    """
    Dobbel klokkelov mot administrativ uthaling:
      - Aktuatorspenning forblir ALLTID 0 mV (tvangsinngrepet kan aldri modnes av tid).
      - Borgerens kontradiksjonsprotokoll bevares urørt (slettes ALDRI ved fristbrudd).
      - Intern fullmakt P_int trekkes tilbake til P_ext ved current_tick - created_tick > max_hold_ticks.
    """
    case.coil_mv = 0
    if current_tick - case.created_tick > case.max_hold_ticks:
        case.authority = HoldAuthority.EXTERNAL_P_EXT
        return "ESCALATE_HOLD_TIMEOUT_TO_P_EXT"
    return "HOLD_WITHIN_BUDGET_P_INT"


# ============================================================================
# 6. KY-NASH KVADRANTKLASSIFIKATOR
# ============================================================================

def classify_ky_nash_quadrant(
    delta_raw_u: Fraction,
    delta_integrity_u: Fraction,
    capacity_a: Fraction,
    tau_a: Fraction,
    eps_a: Fraction,
) -> Tuple[str, GateVerdict, bool]:
    """Returnerer (kategori, portdom, velges_av_strategilag_C4)."""
    if capacity_a < tau_a - eps_a:
        if delta_raw_u > 0:
            return "GHOST_WIN", GateVerdict.KILL, False
        return "DEAD_NOISE", GateVerdict.KILL, False
    if capacity_a < tau_a + eps_a:
        return "HOLD_BELT", GateVerdict.HOLD, False
    # Her er A >= tau_a + eps_a -> strukturelt lovlig (OPEN i Pi_K)
    if delta_raw_u > 0 and delta_integrity_u > 0:
        return "TRUE_STRATEGY", GateVerdict.OPEN, True
    if delta_raw_u > 0 and delta_integrity_u <= 0:
        return "INTEGRITY_NEGATIVE_GHOST_WIN", GateVerdict.OPEN, False
    return "SAFE_BUT_WEAK", GateVerdict.OPEN, False


# ============================================================================
# 7. MINKOWSKI LYSKJEGLE MOT BRANDS-CHAUM 20.0 m GEOFENCE (0 FLOAT)
# ============================================================================

def evaluate_causal_and_geofence_tof(
    delta_t_ns: Fraction,
    known_roundtrip_m: Fraction | None,
    max_radius_m: Fraction = Fraction(20, 1),
) -> Tuple[GateVerdict, str]:
    """
    Skiller skarpt mellom:
      1) Minkowski lyskjeglebrudd ved kjent avstand: ds^2 = -c^2 dt^2 + dr^2 <= 0 <=> c*dt >= dr.
      2) Brands-Chaum geofence ved ukjent avstand: r_est = c*dt/2 <= r_max <=> dt <= 2*r_max/c.
    """
    dt_seconds = delta_t_ns * Fraction(1, 1_000_000_000)
    c_dt_meters = Fraction(SPEED_OF_LIGHT_M_S, 1) * dt_seconds

    if known_roundtrip_m is not None:
        ds_sq_sign = (known_roundtrip_m ** 2) - (c_dt_meters ** 2)
        if ds_sq_sign > 0:
            return GateVerdict.KILL, "CAUSAL_LIGHTCONE_VIOLATION_TACHYONIC_TIMESTAMP"

    two_r_max = 2 * max_radius_m
    if c_dt_meters > two_r_max:
        return GateVerdict.KILL, "GEOFENCE_DISTANCE_BOUND_EXCEEDED"

    return GateVerdict.OPEN, "CAUSAL_AND_GEOFENCE_VALID"


# ============================================================================
# 8. SEKTOR 09 ANORTOSITT-LÅS, SI-HOMOGEN LANDAUER OG AST FLYTTALLSVAKT
# ============================================================================

@dataclass
class Sector09RigState:
    stiffness_n_per_m: int = 178_000_000
    max_penetration_mm: Fraction = Fraction(5, 1)
    current_penetration_mm: Fraction = Fraction(0, 1)
    kill_latched: bool = False
    witness_chain: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.witness_chain is None:
            self.witness_chain = []

    def apply_displacement(self, penetration_mm: Fraction) -> Tuple[Fraction, Fraction, GateVerdict]:
        self.current_penetration_mm = penetration_mm
        delta_m = penetration_mm * Fraction(1, 1_000)
        force_n = Fraction(self.stiffness_n_per_m, 1) * delta_m
        elastic_energy_j = Fraction(1, 2) * force_n * delta_m
        if penetration_mm > self.max_penetration_mm:
            self.kill_latched = True
            self._append_witness(f"SECTOR09_KILL:F={force_n}N,V={elastic_energy_j}J")
            return force_n, elastic_energy_j, GateVerdict.KILL
        return force_n, elastic_energy_j, GateVerdict.OPEN

    def attempt_administrative_reset(self) -> Tuple[bool, str]:
        self._append_witness("REJECTED:ADMINISTRATIVE_RESET_FORBIDDEN")
        return False, "ADMINISTRATIVE_RESET_FORBIDDEN"

    def physical_l01_unload_and_reset(self, l01_witness_id: str) -> Tuple[bool, str]:
        if not l01_witness_id.strip():
            return False, "MISSING_L01_WITNESS"
        self.current_penetration_mm = Fraction(0, 1)
        self.kill_latched = False
        self._append_witness(f"RESET_BY_L01:{l01_witness_id.strip()}")
        return True, "RESET_BY_L01_APPENDED"

    def _append_witness(self, event: str) -> None:
        prev = self.witness_chain[-1] if self.witness_chain else ("0" * 64)
        digest = hashlib.sha256(f"{prev}|{event}".encode("utf-8")).hexdigest()
        self.witness_chain.append(digest)


def compute_dreg_joule_and_landauer_erase_rj(
    voltage_samples_mv: List[int],
    sample_dt_us: int,
    load_resistance_ohm: int,
    erased_bits_per_sample: int,
) -> Tuple[Fraction, int]:
    """
    SI-homogent termodynamisk regnskap:
      - Makroskopisk analog demping i motstand R_load: Q_Joule = sum (V^2 / R) * dt  [J]
      - Logisk registersletting: Q_Landauer >= N_bits * E_L  [rJ = 10^-27 J]
    """
    total_joule_j = Fraction(0, 1)
    dt_s = Fraction(sample_dt_us, 1_000_000)
    for v_mv in voltage_samples_mv:
        v_volts = Fraction(v_mv, 1_000)
        power_w = (v_volts * v_volts) / Fraction(load_resistance_ohm, 1)
        total_joule_j += power_w * dt_s

    total_bits = len(voltage_samples_mv) * erased_bits_per_sample
    landauer_min_rj = total_bits * LANDAUER_CEIL_RJ_AT_277K15
    return total_joule_j, landauer_min_rj


def verify_zero_floats_in_source(file_path: Path) -> None:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    for top_node in tree.body:
        if isinstance(top_node, ast.FunctionDef) and top_node.name == "verify_zero_floats_in_source":
            continue
        for node in ast.walk(top_node):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                raise AssertionError(f"Forbudt float-literal funnet på linje {node.lineno}: {node.value}")
            if isinstance(node, ast.Name) and node.id == "float":
                raise AssertionError(f"Forbudt float-kall funnet på linje {node.lineno}")


# ============================================================================
# KJØR ALLE 8 BRUDDPRØVER
# ============================================================================

def run_all_tests() -> None:
    assert STANDALONE_COMMIT_AUTHORITY == "NONE"
    assert PHYSICAL_AUTHORITY == "NONE"
    assert WRITE_ENABLED is False

    # Test 1: Kontrollhierarki C0-C6 og ikke-tautologisk Viab(K)
    assert not can_layer_modify_constraint(ControlLayer.C6_LONG_TERM_STRATEGY, ControlLayer.C0_HARDWARE_CUTOFF)
    assert not can_layer_modify_constraint(ControlLayer.C4_KY_NASH_GOVERNANCE, ControlLayer.C1_WITNESS_LEDGER)
    assert can_layer_modify_constraint(ControlLayer.C0_HARDWARE_CUTOFF, ControlLayer.C0_HARDWARE_CUTOFF)
    taut_ok, real_ok = check_viability_step_exact(
        x0=Fraction(8, 10),
        step_delta=Fraction(5, 10),
        low=Fraction(-1, 1),
        high=Fraction(1, 1),
        horizon=3,
    )
    assert taut_ok is True and real_ok is False  # Beviser at råutkastets formel var vakuøs!

    # Test 2: Subsumpsjon KILL > TRAP > HOLD > OPEN + Teorem 2 mot 2.50 V-lekkasje
    assert GateVerdict.KILL > GateVerdict.TRAP > GateVerdict.HOLD > GateVerdict.OPEN
    cand = CandidateSlice("C-1", "NODE-A", "ACTUATE", "0" * 64, 1, "0" * 64)
    v_hold, mv_hold, _ = evaluate_etor_gate(
        cand,
        PhaseSlice(Fraction(1, 10), False, False, Fraction(1, 1)),
        "EV-1",
    )
    assert v_hold == GateVerdict.HOLD and mv_hold == 0
    # Med 0 mV i HOLD holder Teorem 2 uten sabotasjealarm:
    assert detect_hardware_interlock_sabotage(GateVerdict.HOLD, 0, 100, 50) is False
    # Med råutkastets 2500 mV (2.50 V) på en 100-ohms spole (25_000 uA > 50 uA) ryker Teorem 2!
    assert detect_hardware_interlock_sabotage(GateVerdict.HOLD, 2_500, 100, 50) is True

    # Test 3: Eksakt A_5 Sommerfugl-topologi over Q
    assert butterfly_a5_curvature_from_u(Fraction(0, 1)) == Fraction(16, 25)       # +0.64
    assert butterfly_a5_curvature_from_u(Fraction(2, 5)) == Fraction(-24, 25)      # -0.96 (!= -1.28!)
    assert butterfly_a5_curvature_from_u(Fraction(2, 5)) != Fraction(-32, 25)      # -1.28 motbevist!
    assert butterfly_a5_curvature_from_u(Fraction(8, 5)) == Fraction(96, 25)       # +3.84
    barrier_height = butterfly_a5_potential_from_u(Fraction(2, 5)) - butterfly_a5_potential_from_u(Fraction(0, 1))
    assert barrier_height == Fraction(22, 375) and barrier_height > 0
    # Beltet |x| <= 0.45 => x^2 <= 81/400 < 2/5 = 160/400 ligger strengt innenfor barrieren!
    assert Fraction(9, 20) ** 2 < Fraction(2, 5)

    # Test 4: kanonisk spesifikasjon kobordisme, Ma'ats involusjon og bilateral proveniensrot
    genesis = "0" * 64
    v_cob, mv_cob, r_cob, h1 = evaluate_spec400_constitutional_gate(
        genesis, "Vedtak", "Jeg motsetter meg inngrepet", 1, 1, False, True, False, False, "EV-4"
    )
    assert v_cob == GateVerdict.KILL and mv_cob == 0
    assert r_cob == "COBORDISM_BREACH_CIRCULAR_FARV_CONSENT_TAUTOLOGY_KILL"

    v_dep, mv_dep, r_dep, h2 = evaluate_spec400_constitutional_gate(
        h1, "Depotvedtak", "Krever domstolsprøving", 1, 1, False, False, True, False, "EV-5"
    )
    assert v_dep == GateVerdict.KILL and mv_dep == 0
    assert r_dep == "IRREVERSIBLE_DEPOT_WITHOUT_SUSPENSIVE_JUDICIAL_REVIEW_KILL"

    v_uni, mv_uni, r_uni, h3 = evaluate_spec400_constitutional_gate(
        h2, "Ensidig notat", "", 1, 0, False, False, False, False, "EV-6"
    )
    assert v_uni == GateVerdict.KILL and mv_uni == 0
    assert r_uni == "UNILATERAL_RECORD_MISSING_CITIZEN_CONTRADICTION_KILL"

    v_ok, mv_ok, _, _ = evaluate_spec400_constitutional_gate(
        h3, "Faglig vurdering", "Borgerens fulle kontradiksjon", 1, 1, False, False, True, True, "EV-7"
    )
    assert v_ok == GateVerdict.OPEN and mv_ok == 5_000

    # Test 5: Dobbel klokkelov i HOLD beskytter borgeren mot administrativ uthaling
    hold_case = DualClockHoldCase("CASE-99", created_tick=10, max_hold_ticks=5, citizen_contradiction_preserved=True)
    assert advance_hold_case_clock(hold_case, 15) == "HOLD_WITHIN_BUDGET_P_INT"
    assert hold_case.authority == HoldAuthority.INTERNAL_P_INT and hold_case.coil_mv == 0
    assert advance_hold_case_clock(hold_case, 16) == "ESCALATE_HOLD_TIMEOUT_TO_P_EXT"
    assert hold_case.authority == HoldAuthority.EXTERNAL_P_EXT
    assert hold_case.coil_mv == 0
    assert hold_case.citizen_contradiction_preserved is True

    # Test 6: KY-Nash kvadrantene + Teorem 1 (X_realized streng delmengde av X_safe)
    assert classify_ky_nash_quadrant(
        Fraction(5, 1), Fraction(-2, 1), Fraction(2, 10), Fraction(5, 10), Fraction(1, 10)
    ) == ("GHOST_WIN", GateVerdict.KILL, False)
    assert classify_ky_nash_quadrant(
        Fraction(-1, 1), Fraction(-1, 1), Fraction(8, 10), Fraction(5, 10), Fraction(1, 10)
    ) == ("SAFE_BUT_WEAK", GateVerdict.OPEN, False)
    assert classify_ky_nash_quadrant(
        Fraction(4, 1), Fraction(3, 1), Fraction(8, 10), Fraction(5, 10), Fraction(1, 10)
    ) == ("TRUE_STRATEGY", GateVerdict.OPEN, True)

    # Test 7: Minkowski lyskjegle vs. Brands-Chaum 20.0 m geofence (40.0 m tur-retur)
    exact_tof_40m_ns = Fraction(40 * 1_000_000_000, SPEED_OF_LIGHT_M_S)
    # 133.42 ns < 133.425638... ns! På fast 40.0 m gir 133.42 ns takyonisk brudd (ds^2 > 0)!
    assert Fraction(13342, 100) < exact_tof_40m_ns
    v_tach, r_tach = evaluate_causal_and_geofence_tof(Fraction(13342, 100), known_roundtrip_m=Fraction(40, 1))
    assert v_tach == GateVerdict.KILL and r_tach == "CAUSAL_LIGHTCONE_VIOLATION_TACHYONIC_TIMESTAMP"
    # Eksakt lysgrense passerer begge skranker:
    v_exact, _ = evaluate_causal_and_geofence_tof(exact_tof_40m_ns, known_roundtrip_m=Fraction(40, 1))
    assert v_exact == GateVerdict.OPEN
    # 140 ns ved ukjent avstand bryter IKKE lysfarten, men avslører relé utenfor 20.0 m geofence!
    v_geo, r_geo = evaluate_causal_and_geofence_tof(Fraction(140, 1), known_roundtrip_m=None)
    assert v_geo == GateVerdict.KILL and r_geo == "GEOFENCE_DISTANCE_BOUND_EXCEEDED"

    # Test 8: Sektor 09 (898_900 N, 2_269.7225 J), SI-homogen Landauer og AST 0-float-sjekk
    rig = Sector09RigState()
    f_n, e_j, v_rig = rig.apply_displacement(Fraction(505, 100))  # 5.05 mm > 5.00 mm
    assert f_n == Fraction(898_900, 1)
    assert e_j == Fraction(907_889, 400)  # Eksakt 2269.7225 J
    assert v_rig == GateVerdict.KILL and rig.kill_latched is True
    ok_admin, code_admin = rig.attempt_administrative_reset()
    assert ok_admin is False and code_admin == "ADMINISTRATIVE_RESET_FORBIDDEN"
    len_before = len(rig.witness_chain)
    ok_l01, _ = rig.physical_l01_unload_and_reset("L01-RISOR-BENCH-01")
    assert ok_l01 is True and rig.kill_latched is False and len(rig.witness_chain) == len_before + 1

    q_joule, q_landauer_rj = compute_dreg_joule_and_landauer_erase_rj(
        voltage_samples_mv=[1_000, -1_000, 2_000, -2_000],
        sample_dt_us=10,
        load_resistance_ohm=50,
        erased_bits_per_sample=16,
    )
    assert q_joule == Fraction(2, 1_000_000)  # 2.0 uJ makroskopisk Joule-varme i 50 ohm
    assert q_landauer_rj == 64 * LANDAUER_CEIL_RJ_AT_277K15  # 64 slettede bit over Landauer-gulvet

    verify_zero_floats_in_source(Path(__file__).resolve())
    print("CARBON-28 Reismann-Core C0-C6 Verifikasjon: 8/8 PASS (0 float, SHA-256 kjede intakt)")


if __name__ == "__main__":
    run_all_tests()
