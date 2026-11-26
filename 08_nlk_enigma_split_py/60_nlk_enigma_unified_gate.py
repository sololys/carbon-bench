#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
CARBON-60: KY-ENIGMA v1.1 -> NLK kanonisk spesifikasjon UNIFIED L1 GATE ENGINE (0 FLOAT)
===============================================================================
Spesifikasjon : NLK_ENIGMA_UNIFIED_BLUEPRINT_v1_0
Grunnlag      : kanonisk spesifikasjon (NLK) + KY-ENIGMA v1.1 + Fase-speil x Enigma v1.0
Klassifikasjon: L1 Demonstrator (lokal programvare, 0 float, fail-closed)
Kardinalaksiom: GENERERER != AUTORISERER != REALISERER != BEVISER
                INSPIRED_BY != IMPLEMENTS != PROVES

Merknad:
  * KY-Enigma er en deterministisk, reversibel demonstrator — IKKE sikker
    kryptografi for sensitive data.
  * Programvare-WAL er en append-only SHA-256-hashkjede, ikke fysisk WORM.
  * Alle portterskler og regnestykker bruker kun eksakte heltall / Fraction.
===============================================================================
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
import struct
import unittest
from typing import Callable, Dict, List, Optional, Tuple


DOMAIN_PREFIX = b"NLK-ENIGMA/v1.0"
SCHEMA_VERSION = "NLK-ENIGMA/v1.0"
# Eksakt SI-2019 rontojoule-gulv ved 277 K (jf. CARBON-18 / kanonisk spesifikasjon):
# k_B * 277 K * ln(2) ~= 2 652 305.5... rJ/bit -> konservativt tak 2_652_306 rJ/bit
LANDAUER_FLOOR_RJ_PER_BIT = 2_652_306

THRESH_HOLD_LOW = Fraction(9, 10)   # 0.90 * sigma
THRESH_KILL_HIGH = Fraction(3, 2)   # 1.50 * sigma


class GlyphState(str, Enum):
    REST = "0"
    KEY_PRESS = "○"
    VALIDATED_INPUT = "◇"
    PROPOSED_STEP = "□"
    PERMUTED_CANDIDATE = "△"
    GATE_EVALUATION = "⬡"
    COMMITTED_STEP = "◉"
    CONSEQUENCE = "1"


class GateVerdict(str, Enum):
    OPEN = "OPEN"
    HOLD = "HOLD"
    KILL = "KILL"


class ObservationStatus(str, Enum):
    SIMULATED = "SIMULATED"
    OBSERVED_ELECTRICAL = "OBSERVED_ELECTRICAL"
    OBSERVED_OPTICAL = "OBSERVED_OPTICAL"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


@dataclass(frozen=True)
class RotorSpec:
    name: str
    wiring: Tuple[int, ...]
    notch: int

    @staticmethod
    def from_letters(name: str, wiring_str: str, notch_char: str) -> "RotorSpec":
        wiring = tuple(ord(c) - ord("A") for c in wiring_str)
        notch = ord(notch_char) - ord("A")
        return RotorSpec(name=name, wiring=wiring, notch=notch)


STANDARD_ROTORS: Dict[str, RotorSpec] = {
    "I": RotorSpec.from_letters("Rotor-I", "EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II": RotorSpec.from_letters("Rotor-II", "AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III": RotorSpec.from_letters("Rotor-III", "BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
}

UKW_78_WIRING: Tuple[int, ...] = tuple(
    ord(c) - ord("A") for c in "YRUHQSLDPXNGOKMIEBFZCWVJAT"
)
IDENTITY_26: Tuple[int, ...] = tuple(range(26))


def is_valid_bijection_26(table: Tuple[int, ...]) -> bool:
    return len(table) == 26 and set(table) == set(range(26))


def invert_bijection_26(table: Tuple[int, ...]) -> Tuple[int, ...]:
    inv = [0] * 26
    for idx, val in enumerate(table):
        inv[val] = idx
    return tuple(inv)


def is_valid_reflector_26(table: Tuple[int, ...]) -> bool:
    if not is_valid_bijection_26(table):
        return False
    for i in range(26):
        if table[i] == i:
            return False
        if table[table[i]] != i:
            return False
    return True


def make_plugboard(pairs: Tuple[Tuple[str, str], ...] = ()) -> Tuple[int, ...]:
    board = list(range(26))
    used = set()
    for a, b in pairs:
        ia, ib = ord(a) - ord("A"), ord(b) - ord("A")
        if ia == ib or ia in used or ib in used or not (0 <= ia < 26 and 0 <= ib < 26):
            raise ValueError("Ugyldig pluggbrettpar")
        board[ia], board[ib] = ib, ia
        used.add(ia)
        used.add(ib)
    return tuple(board)


def encode_lp_bytes(fields: Tuple[bytes, ...]) -> bytes:
    """Kanonisk lengdeprefikset bytekoding (uint32 big-endian lengde + payload)."""
    parts = [DOMAIN_PREFIX, struct.pack(">I", len(fields))]
    for item in fields:
        parts.append(struct.pack(">I", len(item)))
        parts.append(item)
    return b"".join(parts)


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class EnigmaConfig:
    """Uforanderlig konfigurasjon for KY-Enigma v1.1 (venstre, midtre, høyre)."""
    rotors: Tuple[RotorSpec, RotorSpec, RotorSpec]
    ring_settings: Tuple[int, int, int] = (0, 0, 0)
    plugboard: Tuple[int, ...] = IDENTITY_26
    aux_table: Tuple[int, ...] = IDENTITY_26
    reflector: Tuple[int, ...] = UKW_78_WIRING

    def validate_tables(self) -> bool:
        if len(self.rotors) != 3 or len(self.ring_settings) != 3:
            return False
        if any(not (0 <= r < 26) for r in self.ring_settings):
            return False
        for rotor in self.rotors:
            if not is_valid_bijection_26(rotor.wiring):
                return False
            if not (0 <= rotor.notch < 26):
                return False
        if not is_valid_bijection_26(self.plugboard):
            return False
        if not is_valid_bijection_26(self.aux_table):
            return False
        if not is_valid_reflector_26(self.reflector):
            return False
        return True

    def config_hash(self) -> str:
        fields = (
            self.rotors[0].name.encode("ascii"),
            bytes(self.rotors[0].wiring),
            bytes([self.rotors[0].notch]),
            self.rotors[1].name.encode("ascii"),
            bytes(self.rotors[1].wiring),
            bytes([self.rotors[1].notch]),
            self.rotors[2].name.encode("ascii"),
            bytes(self.rotors[2].wiring),
            bytes([self.rotors[2].notch]),
            bytes(self.ring_settings),
            bytes(self.plugboard),
            bytes(self.aux_table),
            bytes(self.reflector),
        )
        return sha256_hex(encode_lp_bytes(fields))


@dataclass(frozen=True)
class EnigmaCandidate:
    """Rent forslag fra Lag 1 (KY-Enigma) ved tilstand ⬡ — ingen mutasjonsrett."""
    event_id: str
    seq: int
    config_hash: str
    x_in: str
    y_cand: str
    q_before: Tuple[int, int, int]
    q_prop: Tuple[int, int, int]
    trace: Tuple[GlyphState, ...]


@dataclass(frozen=True)
class CoordinateSlot:
    """Én romlig rute k på et utspent koordinatbrett (q_0, q_1, ..., q_K)."""
    k: int
    x_in: str
    y_cand: Optional[str]
    q_coord: Tuple[int, int, int]


@dataclass(frozen=True)
class CoordinateBoard:
    """Tidsløst, romlig arbeidstykke (q_0, q_1, ..., q_K) lagt i NLK-tolken."""
    board_id: str
    q_0: Tuple[int, int, int]
    expected_steps: int
    slots: Tuple[CoordinateSlot, ...]


@dataclass(frozen=True)
class MeasurementProfile:
    """Valgfri kontinuerlig måleprofil med eksakt rasjonal aritmetikk (0 float)."""
    e: object           # Skal være Fraction eller int (IEEE float avvises)
    sigma: object       # Skal være positiv Fraction eller int
    stale: bool = False


@dataclass(frozen=True)
class WitnessRecord:
    schema_version: str
    event_id: str
    seq: int
    config_hash: str
    x_in: str
    y_cand: str
    q_before: Tuple[int, int, int]
    q_after: Tuple[int, int, int]
    involution_ok: bool
    gate_decision: GateVerdict
    reason_code: str
    dispatch_status: str
    observation_status: ObservationStatus
    rail_mv: int
    prev_record_hash: str
    record_hash: str


@dataclass(frozen=True)
class GateResult:
    verdict: GateVerdict
    reason_code: str
    y_out: Optional[str]
    q_after: Tuple[int, int, int]
    rail_mv: int
    final_glyph: GlyphState
    observation_status: ObservationStatus
    witness: WitnessRecord


# =============================================================================
# LAG 1: KY-ENIGMA v1.1 (Φ — REVERSIBELT SPEILROM, 0.00 V DC, INGEN COMMIT)
# =============================================================================

class KyEnigmaMirror:
    """
    Ren, tilstandsløs kandidatgenerator for KY-Enigma v1.1.
    Beregner E_q = A_q^-1 o R o A_q og foreslår q_prop uten å eie q_auth.
    """

    def __init__(self, config: EnigmaConfig) -> None:
        self.config = config
        self._rotor_inv = tuple(
            invert_bijection_26(r.wiring) if is_valid_bijection_26(r.wiring) else ()
            for r in config.rotors
        )
        self._plug_inv = (
            invert_bijection_26(config.plugboard)
            if is_valid_bijection_26(config.plugboard)
            else ()
        )
        self._aux_inv = (
            invert_bijection_26(config.aux_table)
            if is_valid_bijection_26(config.aux_table)
            else ()
        )

    def propose_next_positions(self, q_before: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Pre-step Enigma-rotasjon med korrekt double-stepping ved hakk Q/E/V."""
        left, mid, right = q_before
        r_left, r_mid, r_right = self.config.rotors
        mid_at_notch = mid == r_mid.notch
        right_at_notch = right == r_right.notch

        new_left = (left + 1) % 26 if mid_at_notch else left
        new_mid = (mid + 1) % 26 if (mid_at_notch or right_at_notch) else mid
        new_right = (right + 1) % 26
        return (new_left, new_mid, new_right)

    def eval_fixed_state(self, x_idx: int, q: Tuple[int, int, int]) -> int:
        """Evaluerer E_q(x) = A_q^-1(R(A_q(x))) eksakt på {0..25}."""
        c = x_idx
        # Forbehandling S = M o P
        c = self.config.plugboard[c]
        c = self.config.aux_table[c]

        # Fremoverrotorer: høyre (2) -> midtre (1) -> venstre (0)
        for slot in (2, 1, 0):
            shift = (q[slot] - self.config.ring_settings[slot]) % 26
            c = (self.config.rotors[slot].wiring[(c + shift) % 26] - shift) % 26

        # Reflektor R
        c = self.config.reflector[c]

        # Inversrotorer: venstre (0) -> midtre (1) -> høyre (2)
        for slot in (0, 1, 2):
            shift = (q[slot] - self.config.ring_settings[slot]) % 26
            c = (self._rotor_inv[slot][(c + shift) % 26] - shift) % 26

        # Invers forbehandling S^-1 = P^-1 o M^-1
        c = self._aux_inv[c]
        c = self._plug_inv[c]
        return c

    def propose(
        self,
        x_in: str,
        q_auth: Tuple[int, int, int],
        event_id: str,
        seq: int,
    ) -> EnigmaCandidate:
        """Kjører 0 -> ○ -> ◇ -> □ -> △ -> ⬡ og returnerer uforpliktet kandidat."""
        if len(x_in) != 1 or not ("A" <= x_in <= "Z"):
            raise ValueError("INVALID_ASCII_CHAR")
        if not self.config.validate_tables():
            raise ValueError("ERR_TABLE_INTEGRITY")

        q_prop = self.propose_next_positions(q_auth)
        y_idx = self.eval_fixed_state(ord(x_in) - ord("A"), q_prop)
        y_cand = chr(ord("A") + y_idx)

        trace = (
            GlyphState.REST,
            GlyphState.KEY_PRESS,
            GlyphState.VALIDATED_INPUT,
            GlyphState.PROPOSED_STEP,
            GlyphState.PERMUTED_CANDIDATE,
            GlyphState.GATE_EVALUATION,
        )
        return EnigmaCandidate(
            event_id=event_id,
            seq=seq,
            config_hash=self.config.config_hash(),
            x_in=x_in,
            y_cand=y_cand,
            q_before=q_auth,
            q_prop=q_prop,
            trace=trace,
        )


# =============================================================================
# LAG 2: NLK kanonisk spesifikasjon (Π_K -> Ω — ABSOLUTT FORRIGLING OG VITNEKJEDE)
# =============================================================================

def _compute_witness_hash(
    *,
    schema_version: str,
    event_id: str,
    seq: int,
    config_hash: str,
    x_in: str,
    y_cand: str,
    q_before: Tuple[int, int, int],
    q_after: Tuple[int, int, int],
    involution_ok: bool,
    gate_decision: GateVerdict,
    reason_code: str,
    dispatch_status: str,
    observation_status: ObservationStatus,
    rail_mv: int,
    prev_record_hash: str,
) -> str:
    fields = (
        schema_version.encode("ascii"),
        event_id.encode("utf-8"),
        str(seq).encode("ascii"),
        config_hash.encode("ascii"),
        x_in.encode("utf-8"),
        y_cand.encode("utf-8"),
        f"{q_before[0]},{q_before[1]},{q_before[2]}".encode("ascii"),
        f"{q_after[0]},{q_after[1]},{q_after[2]}".encode("ascii"),
        b"1" if involution_ok else b"0",
        gate_decision.value.encode("ascii"),
        reason_code.encode("ascii"),
        dispatch_status.encode("ascii"),
        observation_status.value.encode("ascii"),
        str(rail_mv).encode("ascii"),
        prev_record_hash.encode("ascii"),
    )
    return sha256_hex(encode_lp_bytes(fields))


def _is_exact_rational(val: object) -> bool:
    """Godtar kun int (ikke bool) eller Fraction — avviser IEEE 754 float."""
    if isinstance(val, bool):
        return False
    return isinstance(val, (int, Fraction))


class NlkInterlockGate:
    """
    The Non-Lying Kernel (kanonisk spesifikasjon) koblet i serie etter KY-Enigma v1.1.
    Eier q_auth, sekvensnummer, klebrig KILL-lås, LIFO-faseminne og SHA-256 WAL.
    """

    GENESIS_HASH = "0" * 64

    def __init__(
        self,
        config: EnigmaConfig,
        initial_q: Tuple[int, int, int] = (0, 0, 0),
        wal_sink: Optional[Callable[[WitnessRecord], None]] = None,
    ) -> None:
        self.config = config
        self._verifier_mirror = KyEnigmaMirror(config)
        self.q_auth: Tuple[int, int, int] = initial_q
        self.seq_prev: int = 0
        self.seen_event_ids: set[str] = set()
        self.kill_latched: bool = False
        self.outcome_unknown_hold: bool = False
        self.pending_dispatch_event: Optional[str] = None
        self.lifo_stack: List[Tuple[Tuple[int, int, int], str, str]] = []
        self.wal: List[WitnessRecord] = []
        self._wal_sink = wal_sink

    def _prev_hash(self) -> str:
        return self.wal[-1].record_hash if self.wal else self.GENESIS_HASH

    def _append_wal(
        self,
        *,
        event_id: str,
        seq: int,
        x_in: str,
        y_cand: str,
        q_before: Tuple[int, int, int],
        q_after: Tuple[int, int, int],
        involution_ok: bool,
        gate_decision: GateVerdict,
        reason_code: str,
        dispatch_status: str,
        observation_status: ObservationStatus,
        rail_mv: int,
    ) -> WitnessRecord:
        prev_h = self._prev_hash()
        rec_hash = _compute_witness_hash(
            schema_version=SCHEMA_VERSION,
            event_id=event_id,
            seq=seq,
            config_hash=self.config.config_hash(),
            x_in=x_in,
            y_cand=y_cand,
            q_before=q_before,
            q_after=q_after,
            involution_ok=involution_ok,
            gate_decision=gate_decision,
            reason_code=reason_code,
            dispatch_status=dispatch_status,
            observation_status=observation_status,
            rail_mv=rail_mv,
            prev_record_hash=prev_h,
        )
        rec = WitnessRecord(
            schema_version=SCHEMA_VERSION,
            event_id=event_id,
            seq=seq,
            config_hash=self.config.config_hash(),
            x_in=x_in,
            y_cand=y_cand,
            q_before=q_before,
            q_after=q_after,
            involution_ok=involution_ok,
            gate_decision=gate_decision,
            reason_code=reason_code,
            dispatch_status=dispatch_status,
            observation_status=observation_status,
            rail_mv=rail_mv,
            prev_record_hash=prev_h,
            record_hash=rec_hash,
        )
        if self._wal_sink is not None:
            self._wal_sink(rec)
        self.wal.append(rec)
        return rec

    def verify_wal_chain(self) -> bool:
        expected_prev = self.GENESIS_HASH
        for rec in self.wal:
            if rec.prev_record_hash != expected_prev:
                return False
            recomputed = _compute_witness_hash(
                schema_version=rec.schema_version,
                event_id=rec.event_id,
                seq=rec.seq,
                config_hash=rec.config_hash,
                x_in=rec.x_in,
                y_cand=rec.y_cand,
                q_before=rec.q_before,
                q_after=rec.q_after,
                involution_ok=rec.involution_ok,
                gate_decision=rec.gate_decision,
                reason_code=rec.reason_code,
                dispatch_status=rec.dispatch_status,
                observation_status=rec.observation_status,
                rail_mv=rec.rail_mv,
                prev_record_hash=rec.prev_record_hash,
            )
            if recomputed != rec.record_hash:
                return False
            expected_prev = rec.record_hash
        return True

    def _emit_blocked(
        self,
        *,
        verdict: GateVerdict,
        reason_code: str,
        candidate: EnigmaCandidate,
        involution_ok: bool,
        obs_status: ObservationStatus = ObservationStatus.FAILED,
    ) -> GateResult:
        if verdict == GateVerdict.KILL:
            self.kill_latched = True
        rec = self._append_wal(
            event_id=candidate.event_id,
            seq=candidate.seq,
            x_in=candidate.x_in,
            y_cand=candidate.y_cand,
            q_before=self.q_auth,
            q_after=self.q_auth,
            involution_ok=involution_ok,
            gate_decision=verdict,
            reason_code=reason_code,
            dispatch_status="BLOCKED_0MV",
            observation_status=obs_status,
            rail_mv=0,
        )
        return GateResult(
            verdict=verdict,
            reason_code=reason_code,
            y_out=None,
            q_after=self.q_auth,
            rail_mv=0,
            final_glyph=GlyphState.GATE_EVALUATION,
            observation_status=obs_status,
            witness=rec,
        )

    def evaluate_and_commit(
        self,
        candidate: EnigmaCandidate,
        *,
        evidence_id: Optional[str] = "L1_LOCAL_EVIDENCE",
        measurement: Optional[MeasurementProfile] = None,
        bits_erased: int = 0,
        q_diss_rj: int = 0,
        target_profile: str = "L1_SIMULATED",
        hw_profile_verified: bool = False,
        simulate_crash_before_observe: bool = False,
    ) -> GateResult:
        """
        Evaluerer kandidat fra Lag 1 på snittet ⬡ og håndhever KILL > HOLD > OPEN.
        Returnerer aldri OPEN uten varig WAL først (◉ -> 1).
        """
        # 0. Klebrig KILL-lås har absolutt prioritet
        if self.kill_latched:
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="KILL_LATCHED",
                candidate=candidate,
                involution_ok=False,
            )

        # 1. Integritet på eksisterende vitnekjede
        if not self.verify_wal_chain():
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_THRESHOLD_OR_WAL_BREACH",
                candidate=candidate,
                involution_ok=False,
            )

        # 2. Tabellbijeksjon og konfigurasjonshash
        if not self.config.validate_tables() or candidate.config_hash != self.config.config_hash():
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_TABLE_INTEGRITY",
                candidate=candidate,
                involution_ok=False,
            )

        # 3. Tilstandsisolasjon: Lag 1 må ha beregnet fra gjeldende q_auth
        if candidate.q_before != self.q_auth:
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_STATE_BYPASS",
                candidate=candidate,
                involution_ok=False,
            )

        # 4. Ma'ats Fjær: eksakt rundtur-involusjon og fikspunktfrihet
        if (
            len(candidate.x_in) != 1
            or len(candidate.y_cand) != 1
            or not ("A" <= candidate.x_in <= "Z")
            or not ("A" <= candidate.y_cand <= "Z")
        ):
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_INVOLUTION_BREACH",
                candidate=candidate,
                involution_ok=False,
            )

        x_idx = ord(candidate.x_in) - ord("A")
        y_idx = ord(candidate.y_cand) - ord("A")

        if y_idx == x_idx:
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_FIXED_POINT_VIOLATION",
                candidate=candidate,
                involution_ok=False,
            )

        roundtrip_idx = self._verifier_mirror.eval_fixed_state(y_idx, candidate.q_prop)
        expected_q_prop = self._verifier_mirror.propose_next_positions(self.q_auth)
        if roundtrip_idx != x_idx or candidate.q_prop != expected_q_prop:
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_INVOLUTION_BREACH",
                candidate=candidate,
                involution_ok=False,
            )

        # 5. Landauer-gulv (kanonisk spesifikasjon §3 — gratis bitsletting gir KILL)
        if bits_erased < 0 or q_diss_rj < bits_erased * LANDAUER_FLOOR_RJ_PER_BIT:
            return self._emit_blocked(
                verdict=GateVerdict.KILL,
                reason_code="ERR_LANDAUER_VIOLATION",
                candidate=candidate,
                involution_ok=True,
            )

        # 6. Valgfri kontinuerlig måleprofil (0 float, eksakt Fraction)
        if measurement is not None:
            if not _is_exact_rational(measurement.e) or not _is_exact_rational(measurement.sigma):
                return self._emit_blocked(
                    verdict=GateVerdict.KILL,
                    reason_code="ERR_FLOAT_OR_INVALID_MEASUREMENT",
                    candidate=candidate,
                    involution_ok=True,
                )
            e_val = Fraction(measurement.e)
            sigma_val = Fraction(measurement.sigma)
            if sigma_val <= 0 or e_val < 0 or measurement.stale:
                return self._emit_blocked(
                    verdict=GateVerdict.HOLD,
                    reason_code="HOLD_INVALID_OR_STALE_MEASUREMENT",
                    candidate=candidate,
                    involution_ok=True,
                )
            if e_val > THRESH_KILL_HIGH * sigma_val:
                return self._emit_blocked(
                    verdict=GateVerdict.KILL,
                    reason_code="ERR_THRESHOLD_OR_WAL_BREACH",
                    candidate=candidate,
                    involution_ok=True,
                )
            if e_val >= THRESH_HOLD_LOW * sigma_val:
                return self._emit_blocked(
                    verdict=GateVerdict.HOLD,
                    reason_code="HOLD_BOUNDARY_BAND",
                    candidate=candidate,
                    involution_ok=True,
                )

        # 7. Krasj-gjenopprettingslås (OUTCOME_UNKNOWN -> HOLD)
        if self.outcome_unknown_hold or self.pending_dispatch_event is not None:
            return self._emit_blocked(
                verdict=GateVerdict.HOLD,
                reason_code="OUTCOME_UNKNOWN",
                candidate=candidate,
                involution_ok=True,
                obs_status=ObservationStatus.OUTCOME_UNKNOWN,
            )

        # 8. Eksplisitt bevis-ID, monoton sekvens og replay-sperre
        if not evidence_id or candidate.seq <= self.seq_prev or candidate.event_id in self.seen_event_ids:
            return self._emit_blocked(
                verdict=GateVerdict.HOLD,
                reason_code="HOLD_AUTH_OR_REPLAY",
                candidate=candidate,
                involution_ok=True,
            )

        # 9. Uverifisert fysisk maskinvareprofil kan aldri dispatche L2
        if target_profile == "L2_PHYSICAL" and not hw_profile_verified:
            return self._emit_blocked(
                verdict=GateVerdict.HOLD,
                reason_code="HOLD_UNVERIFIED_HW_PROFILE",
                candidate=candidate,
                involution_ok=True,
            )

        # 10. Trinn ◉: Varig før-utførelse (Durable-First WAL før q_auth / dispatch)
        obs_status = (
            ObservationStatus.OBSERVED_ELECTRICAL
            if target_profile == "L2_PHYSICAL"
            else ObservationStatus.SIMULATED
        )
        rail_mv = 5000 if target_profile == "L2_PHYSICAL" else 0
        dispatch_status = (
            "PENDING_DISPATCH"
            if simulate_crash_before_observe
            else ("DISPATCHED_L2" if target_profile == "L2_PHYSICAL" else "SIMULATED_EFFECT")
        )

        try:
            rec = self._append_wal(
                event_id=candidate.event_id,
                seq=candidate.seq,
                x_in=candidate.x_in,
                y_cand=candidate.y_cand,
                q_before=self.q_auth,
                q_after=candidate.q_prop,
                involution_ok=True,
                gate_decision=GateVerdict.OPEN,
                reason_code="OK_VERIFIED",
                dispatch_status=dispatch_status,
                observation_status=(
                    ObservationStatus.OUTCOME_UNKNOWN
                    if simulate_crash_before_observe
                    else obs_status
                ),
                rail_mv=rail_mv,
            )
        except OSError:
            # Journalfeil før dispatch: ingen tilstandsendring, ingen dispatch
            fallback_rec = WitnessRecord(
                schema_version=SCHEMA_VERSION,
                event_id=candidate.event_id,
                seq=candidate.seq,
                config_hash=self.config.config_hash(),
                x_in=candidate.x_in,
                y_cand=candidate.y_cand,
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=True,
                gate_decision=GateVerdict.HOLD,
                reason_code="HOLD_WAL_FAILURE",
                dispatch_status="ABORTED_BEFORE_DISPATCH",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
                prev_record_hash=self._prev_hash(),
                record_hash=self._prev_hash(),
            )
            return GateResult(
                verdict=GateVerdict.HOLD,
                reason_code="HOLD_WAL_FAILURE",
                y_out=None,
                q_after=self.q_auth,
                rail_mv=0,
                final_glyph=GlyphState.GATE_EVALUATION,
                observation_status=ObservationStatus.FAILED,
                witness=fallback_rec,
            )

        # Atomisk forpliktelse etter bekreftet WAL
        self.q_auth = candidate.q_prop
        self.seq_prev = candidate.seq
        self.seen_event_ids.add(candidate.event_id)
        self.lifo_stack.append((candidate.q_prop, candidate.x_in, candidate.y_cand))

        if simulate_crash_before_observe:
            self.pending_dispatch_event = candidate.event_id
            raise RuntimeError("SIMULATED_CRASH_AFTER_COMMIT_BEFORE_OBSERVE")

        return GateResult(
            verdict=GateVerdict.OPEN,
            reason_code="OK_VERIFIED",
            y_out=candidate.y_cand,
            q_after=self.q_auth,
            rail_mv=rail_mv,
            final_glyph=GlyphState.CONSEQUENCE,
            observation_status=obs_status,
            witness=rec,
        )

    def recover_after_crash(self, recovery_event_id: str) -> WitnessRecord:
        """Gjenvinning etter krasj mellom ◉ og 1: setter OUTCOME_UNKNOWN + HOLD."""
        if self.pending_dispatch_event is not None:
            self.outcome_unknown_hold = True
            self.pending_dispatch_event = None
        return self._append_wal(
            event_id=recovery_event_id,
            seq=self.seq_prev,
            x_in="-",
            y_cand="-",
            q_before=self.q_auth,
            q_after=self.q_auth,
            involution_ok=True,
            gate_decision=GateVerdict.HOLD,
            reason_code="OUTCOME_UNKNOWN",
            dispatch_status="NO_AUTO_REDISPATCH",
            observation_status=ObservationStatus.OUTCOME_UNKNOWN,
            rail_mv=0,
        )

    def uncompute_lifo(self) -> Tuple[GateVerdict, Optional[str]]:
        """Dok. 78 LIFO-reversering: verifiserer E_q(y) == x ved utpopping."""
        if self.kill_latched or not self.lifo_stack:
            return (GateVerdict.HOLD, None)
        q_step, x_orig, y_cipher = self.lifo_stack.pop()
        recovered = chr(
            ord("A") + self._verifier_mirror.eval_fixed_state(ord(y_cipher) - ord("A"), q_step)
        )
        if recovered != x_orig:
            self.kill_latched = True
            self._append_wal(
                event_id=f"LIFO_BREACH_{len(self.wal) + 1}",
                seq=self.seq_prev,
                x_in=x_orig,
                y_cand=y_cipher,
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=False,
                gate_decision=GateVerdict.KILL,
                reason_code="ERR_LIFO_UNCOMPUTE_BREACH",
                dispatch_status="BLOCKED_0MV",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
            )
            return (GateVerdict.KILL, None)
        return (GateVerdict.OPEN, recovered)

    def verify_coordinate_board(
        self,
        board: CoordinateBoard,
    ) -> Tuple[GateVerdict, str, WitnessRecord]:
        """
        Romlig stål-tolk (go/no-go) over et utspent koordinatbrett (q_0..q_K).
        Ingen søk i tid: kontrollerer kun lokale naboskjøter (q_{k-1} -> q_k)
        og involusjon (E_{q_k}(y_k) == x_k, y_k != x_k).
          * Passer på tusendelen -> OPEN (OK_BOARD_FITS_GAUGE)
          * Mangler siste brikke -> HOLD (HOLD_INCOMPLETE_BOARD)
          * Knekker mot malen    -> KILL (ERR_BOARD_SEAM_BREACH)
        """
        if self.kill_latched:
            rec = self._append_wal(
                event_id=board.board_id,
                seq=self.seq_prev,
                x_in="-",
                y_cand="-",
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=False,
                gate_decision=GateVerdict.KILL,
                reason_code="KILL_LATCHED",
                dispatch_status="BLOCKED_0MV",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
            )
            return (GateVerdict.KILL, "KILL_LATCHED", rec)

        if board.expected_steps <= 0 or board.q_0 != self.q_auth:
            self.kill_latched = True
            rec = self._append_wal(
                event_id=board.board_id,
                seq=self.seq_prev,
                x_in="-",
                y_cand="-",
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=False,
                gate_decision=GateVerdict.KILL,
                reason_code="ERR_BOARD_SEAM_BREACH",
                dispatch_status="BLOCKED_0MV",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
            )
            return (GateVerdict.KILL, "ERR_BOARD_SEAM_BREACH", rec)

        # Sjekk alle fremlagte skjøter først: et brudd har alltid prioritet (KILL > HOLD)
        prev_q = board.q_0
        missing_piece = len(board.slots) < board.expected_steps
        for idx, slot in enumerate(board.slots, start=1):
            if slot.k != idx:
                self.kill_latched = True
                rec = self._append_wal(
                    event_id=board.board_id,
                    seq=self.seq_prev,
                    x_in=slot.x_in,
                    y_cand=slot.y_cand or "-",
                    q_before=self.q_auth,
                    q_after=self.q_auth,
                    involution_ok=False,
                    gate_decision=GateVerdict.KILL,
                    reason_code="ERR_BOARD_SEAM_BREACH",
                    dispatch_status="BLOCKED_0MV",
                    observation_status=ObservationStatus.FAILED,
                    rail_mv=0,
                )
                return (GateVerdict.KILL, "ERR_BOARD_SEAM_BREACH", rec)

            expected_q = self._verifier_mirror.propose_next_positions(prev_q)
            if slot.q_coord != expected_q:
                self.kill_latched = True
                rec = self._append_wal(
                    event_id=board.board_id,
                    seq=self.seq_prev,
                    x_in=slot.x_in,
                    y_cand=slot.y_cand or "-",
                    q_before=self.q_auth,
                    q_after=self.q_auth,
                    involution_ok=False,
                    gate_decision=GateVerdict.KILL,
                    reason_code="ERR_BOARD_SEAM_BREACH",
                    dispatch_status="BLOCKED_0MV",
                    observation_status=ObservationStatus.FAILED,
                    rail_mv=0,
                )
                return (GateVerdict.KILL, "ERR_BOARD_SEAM_BREACH", rec)

            if slot.y_cand is None:
                missing_piece = True
                prev_q = slot.q_coord
                continue

            if (
                len(slot.x_in) != 1
                or len(slot.y_cand) != 1
                or not ("A" <= slot.x_in <= "Z")
                or not ("A" <= slot.y_cand <= "Z")
            ):
                self.kill_latched = True
                rec = self._append_wal(
                    event_id=board.board_id,
                    seq=self.seq_prev,
                    x_in=slot.x_in,
                    y_cand=slot.y_cand,
                    q_before=self.q_auth,
                    q_after=self.q_auth,
                    involution_ok=False,
                    gate_decision=GateVerdict.KILL,
                    reason_code="ERR_BOARD_SEAM_BREACH",
                    dispatch_status="BLOCKED_0MV",
                    observation_status=ObservationStatus.FAILED,
                    rail_mv=0,
                )
                return (GateVerdict.KILL, "ERR_BOARD_SEAM_BREACH", rec)

            x_idx = ord(slot.x_in) - ord("A")
            y_idx = ord(slot.y_cand) - ord("A")
            rt_idx = self._verifier_mirror.eval_fixed_state(y_idx, slot.q_coord)
            if y_idx == x_idx or rt_idx != x_idx:
                self.kill_latched = True
                rec = self._append_wal(
                    event_id=board.board_id,
                    seq=self.seq_prev,
                    x_in=slot.x_in,
                    y_cand=slot.y_cand,
                    q_before=self.q_auth,
                    q_after=self.q_auth,
                    involution_ok=False,
                    gate_decision=GateVerdict.KILL,
                    reason_code="ERR_BOARD_SEAM_BREACH",
                    dispatch_status="BLOCKED_0MV",
                    observation_status=ObservationStatus.FAILED,
                    rail_mv=0,
                )
                return (GateVerdict.KILL, "ERR_BOARD_SEAM_BREACH", rec)

            prev_q = slot.q_coord

        if missing_piece or len(board.slots) > board.expected_steps:
            verdict = GateVerdict.KILL if len(board.slots) > board.expected_steps else GateVerdict.HOLD
            code = "ERR_BOARD_SEAM_BREACH" if verdict == GateVerdict.KILL else "HOLD_INCOMPLETE_BOARD"
            if verdict == GateVerdict.KILL:
                self.kill_latched = True
            rec = self._append_wal(
                event_id=board.board_id,
                seq=self.seq_prev,
                x_in="-",
                y_cand="-",
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=(verdict == GateVerdict.HOLD),
                gate_decision=verdict,
                reason_code=code,
                dispatch_status="BLOCKED_0MV",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
            )
            return (verdict, code, rec)

        rec = self._append_wal(
            event_id=board.board_id,
            seq=self.seq_prev + 1,
            x_in=board.slots[0].x_in,
            y_cand=board.slots[-1].y_cand or "-",
            q_before=self.q_auth,
            q_after=prev_q,
            involution_ok=True,
            gate_decision=GateVerdict.OPEN,
            reason_code="OK_BOARD_FITS_GAUGE",
            dispatch_status="SIMULATED_EFFECT",
            observation_status=ObservationStatus.SIMULATED,
            rail_mv=0,
        )
        self.q_auth = prev_q
        self.seq_prev += 1
        return (GateVerdict.OPEN, "OK_BOARD_FITS_GAUGE", rec)

    def reset_from_kill(
        self,
        operator_id: str,
        self_test_passed: bool,
    ) -> WitnessRecord:
        """Eksplisitt reset fra KILL: krever bestått selvtest, bevarer WAL-historikk."""
        if not operator_id or not self_test_passed:
            return self._append_wal(
                event_id=f"RESET_DENIED_{len(self.wal) + 1}",
                seq=self.seq_prev,
                x_in="-",
                y_cand="-",
                q_before=self.q_auth,
                q_after=self.q_auth,
                involution_ok=False,
                gate_decision=GateVerdict.KILL,
                reason_code="RESET_SELFTEST_FAILED",
                dispatch_status="BLOCKED_0MV",
                observation_status=ObservationStatus.FAILED,
                rail_mv=0,
            )
        self.kill_latched = False
        self.outcome_unknown_hold = False
        return self._append_wal(
            event_id=f"RESET_BY_{operator_id}_{len(self.wal) + 1}",
            seq=self.seq_prev,
            x_in="-",
            y_cand="-",
            q_before=self.q_auth,
            q_after=self.q_auth,
            involution_ok=True,
            gate_decision=GateVerdict.HOLD,
            reason_code="RESET_SELFTEST_PASSED",
            dispatch_status="SAFE_IDLE_0MV",
            observation_status=ObservationStatus.SIMULATED,
            rail_mv=0,
        )


# =============================================================================
# SAMSVARSTESTER T01–T12 (CARBON-59 SEKSJON VI)
# =============================================================================

def _default_config(
    rings: Tuple[int, int, int] = (0, 0, 0),
    plugs: Tuple[Tuple[str, str], ...] = (("A", "M"), ("F", "I"), ("N", "V")),
) -> EnigmaConfig:
    return EnigmaConfig(
        rotors=(STANDARD_ROTORS["I"], STANDARD_ROTORS["II"], STANDARD_ROTORS["III"]),
        ring_settings=rings,
        plugboard=make_plugboard(plugs),
        aux_table=IDENTITY_26,
        reflector=UKW_78_WIRING,
    )


class TestNlkEnigmaCompliance(unittest.TestCase):
    def test_T01_table_bijections_and_reflector(self) -> None:
        cfg = _default_config()
        self.assertTrue(cfg.validate_tables())
        for rotor in cfg.rotors:
            inv = invert_bijection_26(rotor.wiring)
            for i in range(26):
                self.assertEqual(inv[rotor.wiring[i]], i)
        for i in range(26):
            self.assertNotEqual(cfg.reflector[i], i)
            self.assertEqual(cfg.reflector[cfg.reflector[i]], i)

    def test_T02_conjugated_involution_and_no_fixed_points(self) -> None:
        for rings in ((0, 0, 0), (3, 11, 22)):
            cfg = _default_config(rings=rings)
            mirror = KyEnigmaMirror(cfg)
            for q in ((0, 0, 0), (16, 4, 21), (25, 25, 25), (7, 13, 19)):
                for x in range(26):
                    y = mirror.eval_fixed_state(x, q)
                    self.assertNotEqual(y, x)
                    self.assertEqual(mirror.eval_fixed_state(y, q), x)

    def test_T03_message_roundtrip_with_double_stepping(self) -> None:
        cfg = _default_config()
        # Starter rett før hakk på høyre (V=21) og midtre (E=4) for å utløse double-step
        start_q = (0, 3, 20)
        plaintext = "GRANITTBAERERIKKEPLASTIKK"

        mirror_enc = KyEnigmaMirror(cfg)
        gate_enc = NlkInterlockGate(cfg, initial_q=start_q)
        ciphertext = []
        for idx, ch in enumerate(plaintext, start=1):
            cand = mirror_enc.propose(ch, gate_enc.q_auth, f"enc-{idx}", idx)
            res = gate_enc.evaluate_and_commit(cand)
            self.assertEqual(res.verdict, GateVerdict.OPEN)
            self.assertIsNotNone(res.y_out)
            ciphertext.append(res.y_out)

        # Verifiser at venstre rotor faktisk har avansert via double-step
        self.assertGreater(gate_enc.q_auth[0], 0)

        mirror_dec = KyEnigmaMirror(cfg)
        gate_dec = NlkInterlockGate(cfg, initial_q=start_q)
        recovered = []
        for idx, ch in enumerate(ciphertext, start=1):
            cand = mirror_dec.propose(ch, gate_dec.q_auth, f"dec-{idx}", idx)
            res = gate_dec.evaluate_and_commit(cand)
            self.assertEqual(res.verdict, GateVerdict.OPEN)
            recovered.append(res.y_out)

        self.assertEqual("".join(recovered), plaintext)

    def test_T04_involution_sabotage_triggers_kill(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(1, 2, 3))
        cand = mirror.propose("A", gate.q_auth, "evt-1", 1)
        # Saboter y_cand med et annet tegn (ikke lik x_in)
        tampered_char = "B" if cand.y_cand != "B" else "C"
        tampered = EnigmaCandidate(
            event_id=cand.event_id,
            seq=cand.seq,
            config_hash=cand.config_hash,
            x_in=cand.x_in,
            y_cand=tampered_char,
            q_before=cand.q_before,
            q_prop=cand.q_prop,
            trace=cand.trace,
        )
        res = gate.evaluate_and_commit(tampered)
        self.assertEqual(res.verdict, GateVerdict.KILL)
        self.assertEqual(res.reason_code, "ERR_INVOLUTION_BREACH")
        self.assertEqual(res.rail_mv, 0)
        self.assertEqual(gate.q_auth, (1, 2, 3))

    def test_T05_fixed_point_sabotage_triggers_kill(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        cand = mirror.propose("K", gate.q_auth, "evt-fp", 1)
        tampered = EnigmaCandidate(
            event_id=cand.event_id,
            seq=cand.seq,
            config_hash=cand.config_hash,
            x_in="K",
            y_cand="K",
            q_before=cand.q_before,
            q_prop=cand.q_prop,
            trace=cand.trace,
        )
        res = gate.evaluate_and_commit(tampered)
        self.assertEqual(res.verdict, GateVerdict.KILL)
        self.assertEqual(res.reason_code, "ERR_FIXED_POINT_VIOLATION")
        self.assertEqual(gate.q_auth, (0, 0, 0))

    def test_T06_state_isolation_on_hold_and_kill(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(4, 5, 6))
        cand = mirror.propose("Z", gate.q_auth, "evt-hold", 1)
        res_hold = gate.evaluate_and_commit(
            cand,
            target_profile="L2_PHYSICAL",
            hw_profile_verified=False,
        )
        self.assertEqual(res_hold.verdict, GateVerdict.HOLD)
        self.assertEqual(res_hold.rail_mv, 0)
        self.assertEqual(gate.q_auth, (4, 5, 6))

        # Landauer-brudd (gratis bitsletting) -> KILL, fortsatt frosset q_auth
        res_kill = gate.evaluate_and_commit(
            cand,
            bits_erased=1,
            q_diss_rj=LANDAUER_FLOOR_RJ_PER_BIT - 1,
        )
        self.assertEqual(res_kill.verdict, GateVerdict.KILL)
        self.assertEqual(res_kill.reason_code, "ERR_LANDAUER_VIOLATION")
        self.assertEqual(gate.q_auth, (4, 5, 6))

    def test_T07_sticky_kill_and_audited_reset(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        cand1 = mirror.propose("A", gate.q_auth, "evt-1", 1)
        gate.evaluate_and_commit(cand1, bits_erased=1, q_diss_rj=0)
        self.assertTrue(gate.kill_latched)

        # Gyldig neste forespørsel skal fortsatt blokkeres
        cand2 = mirror.propose("B", gate.q_auth, "evt-2", 2)
        res2 = gate.evaluate_and_commit(cand2)
        self.assertEqual(res2.verdict, GateVerdict.KILL)
        self.assertEqual(res2.reason_code, "KILL_LATCHED")

        # Feilet selvtest åpner ikke låsen
        gate.reset_from_kill("L01_OP", self_test_passed=False)
        self.assertTrue(gate.kill_latched)

        # Bestått selvtest låser opp og bevarer hele WAL-historikken
        wal_before = len(gate.wal)
        gate.reset_from_kill("L01_OP", self_test_passed=True)
        self.assertFalse(gate.kill_latched)
        self.assertEqual(len(gate.wal), wal_before + 1)
        self.assertTrue(gate.verify_wal_chain())

        cand3 = mirror.propose("C", gate.q_auth, "evt-3", 3)
        res3 = gate.evaluate_and_commit(cand3)
        self.assertEqual(res3.verdict, GateVerdict.OPEN)

    def test_T08_exact_thresholds_nan_rejection_and_zero_float_ast(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        sigma = Fraction(10, 1)

        # Eksakt nedre grense e == 0.90 * sigma -> HOLD
        cand_low = mirror.propose("A", gate.q_auth, "e-low", 1)
        r_low = gate.evaluate_and_commit(
            cand_low, measurement=MeasurementProfile(e=Fraction(9, 1), sigma=sigma)
        )
        self.assertEqual(r_low.verdict, GateVerdict.HOLD)
        self.assertEqual(r_low.reason_code, "HOLD_BOUNDARY_BAND")

        # Eksakt øvre grense e == 1.50 * sigma -> HOLD
        cand_high = mirror.propose("A", gate.q_auth, "e-high", 2)
        r_high = gate.evaluate_and_commit(
            cand_high, measurement=MeasurementProfile(e=Fraction(15, 1), sigma=sigma)
        )
        self.assertEqual(r_high.verdict, GateVerdict.HOLD)
        self.assertEqual(r_high.reason_code, "HOLD_BOUNDARY_BAND")

        # Rett under 0.90 * sigma -> OPEN
        cand_ok = mirror.propose("A", gate.q_auth, "e-ok", 3)
        r_ok = gate.evaluate_and_commit(
            cand_ok, measurement=MeasurementProfile(e=Fraction(8999, 1000), sigma=sigma)
        )
        self.assertEqual(r_ok.verdict, GateVerdict.OPEN)

        # Rå IEEE-754 NaN og Inf (pakket uten float-literal i kildekode) -> KILL
        raw_nan = struct.unpack(">d", b"\x7f\xf8\x00\x00\x00\x00\x00\x00")[0]
        cand_nan = mirror.propose("B", gate.q_auth, "e-nan", 4)
        r_nan = gate.evaluate_and_commit(
            cand_nan, measurement=MeasurementProfile(e=raw_nan, sigma=sigma)
        )
        self.assertEqual(r_nan.verdict, GateVerdict.KILL)
        self.assertEqual(r_nan.reason_code, "ERR_FLOAT_OR_INVALID_MEASUREMENT")

        # AST-revisjon av hele filen: 0 float-literaler og 0 float()-kall
        source = inspect.getsource(inspect.getmodule(NlkInterlockGate))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and type(node.value).__name__ == "float":
                self.fail(f"Fant forbudt float-literal på linje {node.lineno}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "float")

    def test_T09_replay_and_monotonic_sequence(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        c1 = mirror.propose("D", gate.q_auth, "uniq-1", 10)
        self.assertEqual(gate.evaluate_and_commit(c1).verdict, GateVerdict.OPEN)

        # Duplikat event_id med høyere seq -> HOLD
        c_dup = mirror.propose("E", gate.q_auth, "uniq-1", 11)
        r_dup = gate.evaluate_and_commit(c_dup)
        self.assertEqual(r_dup.verdict, GateVerdict.HOLD)
        self.assertEqual(r_dup.reason_code, "HOLD_AUTH_OR_REPLAY")

        # Ikke-monoton seq (seq <= seq_prev) -> HOLD
        c_old = mirror.propose("E", gate.q_auth, "uniq-2", 10)
        r_old = gate.evaluate_and_commit(c_old)
        self.assertEqual(r_old.verdict, GateVerdict.HOLD)
        self.assertEqual(r_old.reason_code, "HOLD_AUTH_OR_REPLAY")

    def test_T10_durable_first_wal_failure_aborts_before_dispatch(self) -> None:
        def failing_sink(_rec: WitnessRecord) -> None:
            raise OSError("DISK_FULL")

        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(2, 3, 4), wal_sink=failing_sink)
        cand = mirror.propose("H", gate.q_auth, "wal-fail-1", 1)
        res = gate.evaluate_and_commit(cand)
        self.assertEqual(res.verdict, GateVerdict.HOLD)
        self.assertEqual(res.reason_code, "HOLD_WAL_FAILURE")
        self.assertEqual(gate.q_auth, (2, 3, 4))
        self.assertEqual(len(gate.wal), 0)

    def test_T11_crash_window_outcome_unknown_no_auto_redispatch(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        cand = mirror.propose("M", gate.q_auth, "crash-1", 1)

        with self.assertRaises(RuntimeError):
            gate.evaluate_and_commit(cand, simulate_crash_before_observe=True)

        rec_rec = gate.recover_after_crash("recover-1")
        self.assertEqual(rec_rec.observation_status, ObservationStatus.OUTCOME_UNKNOWN)
        self.assertEqual(rec_rec.gate_decision, GateVerdict.HOLD)

        # Etterfølgende kall låses i HOLD (ingen auto-redispatch)
        cand2 = mirror.propose("N", gate.q_auth, "after-crash-2", 2)
        res2 = gate.evaluate_and_commit(cand2)
        self.assertEqual(res2.verdict, GateVerdict.HOLD)
        self.assertEqual(res2.reason_code, "OUTCOME_UNKNOWN")

    def test_T12_witness_chain_tamper_and_lifo_uncompute(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        gate = NlkInterlockGate(cfg, initial_q=(0, 0, 0))
        cand = mirror.propose("Q", gate.q_auth, "lifo-1", 1)
        res = gate.evaluate_and_commit(cand)
        self.assertEqual(res.verdict, GateVerdict.OPEN)
        self.assertTrue(gate.verify_wal_chain())

        # Normal LIFO uncompute gjenoppretter Q
        v_ok, x_rec = gate.uncompute_lifo()
        self.assertEqual(v_ok, GateVerdict.OPEN)
        self.assertEqual(x_rec, "Q")

        # Korrupt LIFO-oppføring utløser KILL
        gate.lifo_stack.append(((0, 0, 1), "Q", "Q"))
        v_bad, x_bad = gate.uncompute_lifo()
        self.assertEqual(v_bad, GateVerdict.KILL)
        self.assertIsNone(x_bad)
        self.assertTrue(gate.kill_latched)

        # Manipulasjon av felt i WAL bryter kjeden
        orig = gate.wal[0]
        gate.wal[0] = WitnessRecord(
            schema_version=orig.schema_version,
            event_id="TAMPERED",
            seq=orig.seq,
            config_hash=orig.config_hash,
            x_in=orig.x_in,
            y_cand=orig.y_cand,
            q_before=orig.q_before,
            q_after=orig.q_after,
            involution_ok=orig.involution_ok,
            gate_decision=orig.gate_decision,
            reason_code=orig.reason_code,
            dispatch_status=orig.dispatch_status,
            observation_status=orig.observation_status,
            rail_mv=orig.rail_mv,
            prev_record_hash=orig.prev_record_hash,
            record_hash=orig.record_hash,
        )
        self.assertFalse(gate.verify_wal_chain())

    def test_T13_coordinate_board_gauge(self) -> None:
        cfg = _default_config()
        mirror = KyEnigmaMirror(cfg)
        q0 = (0, 3, 20)
        word = "STAL"

        # Spenn opp et komplett koordinatbrett (q_0..q_K) i Lag 1 uten å røre gate
        slots = []
        q_cur = q0
        for k, ch in enumerate(word, start=1):
            cand = mirror.propose(ch, q_cur, f"b-{k}", k)
            slots.append(CoordinateSlot(k=k, x_in=ch, y_cand=cand.y_cand, q_coord=cand.q_prop))
            q_cur = cand.q_prop

        # 1. Mangler siste brikke -> HOLD (q_auth frosset)
        gate_hold = NlkInterlockGate(cfg, initial_q=q0)
        incomplete = CoordinateBoard(
            board_id="board-hold",
            q_0=q0,
            expected_steps=len(word),
            slots=tuple(slots[:-1]),
        )
        v_h, c_h, _ = gate_hold.verify_coordinate_board(incomplete)
        self.assertEqual(v_h, GateVerdict.HOLD)
        self.assertEqual(c_h, "HOLD_INCOMPLETE_BOARD")
        self.assertEqual(gate_hold.q_auth, q0)

        # 2. Passer på tusendelen i tolken -> OPEN (q_auth hopper rent til q_K)
        complete = CoordinateBoard(
            board_id="board-open",
            q_0=q0,
            expected_steps=len(word),
            slots=tuple(slots),
        )
        v_o, c_o, _ = gate_hold.verify_coordinate_board(complete)
        self.assertEqual(v_o, GateVerdict.OPEN)
        self.assertEqual(c_o, "OK_BOARD_FITS_GAUGE")
        self.assertEqual(gate_hold.q_auth, q_cur)

        # 3. Knekker mot malen (skjøtbrudd i rute 2) -> KILL
        gate_kill = NlkInterlockGate(cfg, initial_q=q0)
        bad_slots = list(slots)
        bad_slots[1] = CoordinateSlot(
            k=2,
            x_in=slots[1].x_in,
            y_cand=slots[1].y_cand,
            q_coord=(9, 9, 9),
        )
        broken = CoordinateBoard(
            board_id="board-kill",
            q_0=q0,
            expected_steps=len(word),
            slots=tuple(bad_slots),
        )
        v_k, c_k, _ = gate_kill.verify_coordinate_board(broken)
        self.assertEqual(v_k, GateVerdict.KILL)
        self.assertEqual(c_k, "ERR_BOARD_SEAM_BREACH")
        self.assertTrue(gate_kill.kill_latched)
        self.assertEqual(gate_kill.q_auth, q0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
