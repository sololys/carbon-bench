#!/usr/bin/env python3
"""
34_vertikal_loddsnor_galvanisk_sluse.py — Eksakt L1-motor og kretskort-inspektør
for den vertikale konsekvenskretsen i CARBON 33.

Epistemisk grense:
  INSPIRED_BY != IMPLEMENTS != PROVES.
  Dette er lokalt demonstrert programvare (L1) i ren Python-standardbibliotek
  uten flyttall (kun int og Fraction, voktet med AST-inspeksjon).
  Revisjonsloggen er en append-only SHA-256 hash-kjede i minnet, ikke fysisk
  WORM-maskinvare, og millivolt-tallene (0 mV / 5000 mV) er diskrete modell-
  tilstander for tørrkontakt vs. eksternt vitnet innslag.

Hva flisa verifiserer (8/8 tester):
  1. 2D ASCII-kretskort og planaritet: Påviser 1 kryssing ('┼'), 1 kolliderende
     '┘' mot '[KILL]'-linjen og uklokket '┴ -> ▲'-sløyfe i råskissen, og beviser
     0 kryssinger, låste kolonner og full klokkeplikt i den herdede platen.
  2. (L) Akustikk [chmod 0o444]: Nekter skrive-/kjørebiter og feller
     'metafor = bevis' med KILL (0 mV).
  3. (A) Vektorlås (p_art): Fanger prematur lukking (punkt uten kandidatbane),
     nekter taust HOLD (Δ_K = ∅) og ruter lovlig gjennom HOLD (0 mV) til (J).
  4. (J) Søkerom {γ_i}: Feller direkte lekkasje / sideeffekt ut av 0 V-rommet
     med KILL (0 mV).
  5. (D) Dans / Last + dobbel klokkelov: Skiller ærlig uferdig bæreevne (HOLD ->
     retur til J innen τ_max, eskalering P_int -> P_ext ved τ > τ_max uten
     blind åpning) fra papir-bokholderi (ubetalt last ført som betalt -> KILL).
  6. (Π_K) Sluse [Δ_K = 0, Σ permit ≤ 1]: Avviser asymptotisk epsilon-avvik
     (Δ_K = 1/10^12 -> HOLD) og okkupert sone (HOLD), feller Σ permit > 1 og
     selv-autorisasjon med KILL, og stanser på [KLAR :: 0 mV] (væpnet tørrkontakt
     uten spenningsfullmakt).
  7. Galvanisk luftgap: Beviser at KILL, HOLD og KLAR alle holder 0 mV men har
     tre distinkte topologiske roller i F, og at kun ytre vitne W_ext ∉ F med
     ikke-tomt bevis-ID og bestått ytre motprøve lukker til [OPEN :: 5000 mV].
  8. Append-only SHA-256 WAL og vitneført RESET_BY_L01: Sjekker at reset aldri
     visker ut historikk, og at én enkelt mutert bit i loggen fanges øyeblikkelig.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unittest


RAW_SKETCH_PLATE: Tuple[str, ...] = (
    "[u_raw]",
    "   │",
    "   ▼",
    "(L) Akustikk [chmod 444] ───(metafor = bevis)─────────────────► [KILL]",
    "   │",
    "   ▼",
    "(A) Vektorlås (p_art) ──────(prematur lukking)─┐",
    "   │                                           │",
    "   ▼                                           ▼",
    "(J) Søkerom {γ_i} ◄─────────(returledning)─── [HOLD : τ <= τ_max]",
    "   │              ▲                            │",
    "   │              │                            └─(τ > τ_max)──► [P_ext // Tidsavbrudd]",
    "   ├─(lekkasje)───┼───────────────────────────────────────────► [KILL]",
    "   ▼              │",
    "(D) Dans / Last ──┴─────────(papir-bokholderi)─┘",
    "   │",
    "   ▼",
    "(Π_K) Sluse [Δ_K -> 0, sum(permit) <= 1] ──(selv-autorisasjon)► [KILL]",
    "   │",
    "   ▼",
    "[KLAR :: 0.00 V DC]   (Ytterste punkt i F — eksponert bruddflate, null fullmakt)",
    "══════════════════════════════ GALVANISK LUFTGAP ══════════════════════════════",
    "   │",
    "   ▼  Kun ved inngrep fra W_ext ∉ F mot fysisk / ekstern motprøve",
    "[OPEN :: 5.00 V DC]   (Autorisert innskrift — bærende konsekvens i P_COSMOS)",
)

HARDENED_PLANAR_PLATE: Tuple[str, ...] = (
    "                                      [u_raw]",
    "                                         │",
    "                                         ▼",
    "                                     (L) Akustikk [chmod 444] ──(metafor = bevis)───► [KILL]",
    "                                         │",
    "                                         ▼",
    "               ┌─(prematur lukking)─ (A) Vektorlås (p_art)",
    "               │                         │",
    "               ▼                         ▼",
    "[P_ext] ◄─ [HOLD: Δ_K≠∅, τ≤τ_max] ─► (J) Søkerom {γ_i} ─────────(lekkasje)──────────► [KILL]",
    "(τ > τ_max)    ▲                         │",
    "               │                         ▼",
    "               ├─(uferdig bæreevne)─ (D) Dans / Last ───────────(papir-bokholderi)──► [KILL]",
    "               │                         │",
    "               │                         ▼",
    "               └─(Δ_K ≠ 0 / sone)─── (Π_K) Sluse [Δ_K=0, Σp≤1] ─(selv-autorisasjon)─► [KILL]",
    "                                         │",
    "                                         ▼",
    "                                [KLAR :: 0.00 V DC]",
    "            (Ytterste punkt i F — eksponert bruddflate, null fullmakt)",
    "═════════════════════════════════ GALVANISK LUFTGAP ════════════════════════════════════════",
    "                                         │",
    "                                         ▼  Kun ved W_ext ∉ F mot fysisk / ekstern motprøve",
    "                                [OPEN :: 5.00 V DC]",
    "                  (Autorisert innskrift + SHA-256 WAL i P_COSMOS)",
)

ENGLISH_PLANAR_PLATE: Tuple[str, ...] = (
    "                                      [u_raw]",
    "                                         │",
    "                                         ▼",
    "                                     (L) Acoustics [chmod 444] ─(metaphor = proof)──► [KILL]",
    "                                         │",
    "                                         ▼",
    "              ┌─(premature closure)─ (A) Vector Lock (p_art)",
    "              │                          │",
    "              ▼                          ▼",
    "[P_ext] ◄─ [HOLD: Δ_K≠∅, τ≤τ_max] ─► (J) Search {γ_i} ──────────(sandbox leak)──────► [KILL]",
    "(τ > τ_max)   ▲                          │",
    "              │                          ▼",
    "              ├─(unfinished load)─── (D) Dance / Load ──────────(paper bookkeeping)─► [KILL]",
    "              │                          │",
    "              │                          ▼",
    "              └─(Δ_K ≠ 0 / zone)──── (Π_K) Gate [Δ_K=0, Σp≤1] ─(self-authorization)─► [KILL]",
    "                                         │",
    "                                         ▼",
    "                                [READY :: 0.00 V DC]",
    "           (Outermost point in F — exposed dry contact, zero authority)",
    "═════════════════════════════════ GALVANIC AIR GAP ═════════════════════════════════════════",
    "                                         │",
    "                                         ▼  Only via W_ext ∉ F against external counter-test",
    "                                [OPEN :: 5.00 V DC]",
    "                (Authorized inscription + SHA-256 WAL in P_COSMOS)",
)


class GateVerdict(str, Enum):
    HOLD = "HOLD"
    KLAR = "KLAR"
    OPEN = "OPEN"
    KILL = "KILL"


@dataclass(frozen=True)
class AsciiPlateAudit:
    crossings: Tuple[Tuple[int, int], ...]
    unclocked_t_splits: Tuple[Tuple[int, int], ...]
    dangling_up_turns: Tuple[Tuple[int, int], ...]
    has_tabs_or_trailing_ws: bool


def audit_ascii_plate(lines: Tuple[str, ...]) -> AsciiPlateAudit:
    """Sjekker 2D-kobberbaner for kryssinger ('┼'), løse opp-svinger ('┘') og fanebruk."""
    crossings: List[Tuple[int, int]] = []
    unclocked_t_splits: List[Tuple[int, int]] = []
    dangling_up_turns: List[Tuple[int, int]] = []
    has_ws_defect = False

    def char_at(r: int, c: int) -> str:
        if 0 <= r < len(lines) and 0 <= c < len(lines[r]):
            return lines[r][c]
        return " "

    vertical_conductors = {"│", "├", "┤", "┼", "▲", "▼", "┐", "┌"}

    for r, line in enumerate(lines):
        if "\t" in line or line.endswith(" "):
            has_ws_defect = True
        for c, ch in enumerate(line):
            if ch == "┼":
                crossings.append((r, c))
            elif ch == "┴":
                unclocked_t_splits.append((r, c))
            elif ch == "┘":
                above = char_at(r - 1, c)
                if above not in vertical_conductors and not (above == "]" or above.isalpha()):
                    dangling_up_turns.append((r, c))

    return AsciiPlateAudit(
        crossings=tuple(crossings),
        unclocked_t_splits=tuple(unclocked_t_splits),
        dangling_up_turns=tuple(dangling_up_turns),
        has_tabs_or_trailing_ws=has_ws_defect,
    )


@dataclass(frozen=True)
class Proposal:
    case_id: str
    u_raw_pressure: int
    acoustic_mode: int = 0o444
    metaphor_claimed_as_proof: bool = False
    vector_locked: bool = True
    candidate_paths: Tuple[str, ...] = ()
    sandbox_side_effect_leak: bool = False
    required_work_j: Fraction = Fraction(0)
    paid_work_j: Fraction = Fraction(0)
    claimed_paid_work_j: Fraction = Fraction(0)
    load_deficiency_items: Tuple[str, ...] = ()
    delta_k: Fraction = Fraction(0)
    gate_deficiency_items: Tuple[str, ...] = ()
    zone_occupied: bool = False
    requested_permits: int = 1
    self_authorize_attempt: bool = False


@dataclass(frozen=True)
class ExternalWitness:
    witness_actor: str
    outside_formal_system: bool
    evidence_id: str
    counter_test_passed: bool


@dataclass(frozen=True)
class EvaluationResult:
    verdict: GateVerdict
    stage: str
    reason_code: str
    actuator_mv: int
    dry_contact_armed: bool
    hold_authority: str
    deficiency_receipt: Tuple[str, ...]


@dataclass(frozen=True)
class WalRecord:
    seq: int
    case_id: str
    stage: str
    verdict: str
    reason_code: str
    actuator_mv: int
    dry_contact_armed: bool
    hold_authority: str
    tau: str
    deficiency_receipt: Tuple[str, ...]
    evidence_id: str
    prev_hash: str
    entry_hash: str


def _encode_field(tag: str, value: str) -> bytes:
    raw_tag = tag.encode("utf-8")
    raw_val = value.encode("utf-8")
    return (
        len(raw_tag).to_bytes(4, "big")
        + raw_tag
        + len(raw_val).to_bytes(4, "big")
        + raw_val
    )


def compute_wal_hash(
    seq: int,
    case_id: str,
    stage: str,
    verdict: str,
    reason_code: str,
    actuator_mv: int,
    dry_contact_armed: bool,
    hold_authority: str,
    tau: str,
    deficiency_receipt: Tuple[str, ...],
    evidence_id: str,
    prev_hash: str,
) -> str:
    h = hashlib.sha256()
    fields = (
        ("seq", str(seq)),
        ("case_id", case_id),
        ("stage", stage),
        ("verdict", verdict),
        ("reason_code", reason_code),
        ("actuator_mv", str(actuator_mv)),
        ("dry_contact_armed", "1" if dry_contact_armed else "0"),
        ("hold_authority", hold_authority),
        ("tau", tau),
        ("deficiency_count", str(len(deficiency_receipt))),
        ("deficiency_joined", "|".join(deficiency_receipt)),
        ("evidence_id", evidence_id),
        ("prev_hash", prev_hash),
    )
    for tag, val in fields:
        h.update(_encode_field(tag, val))
    return h.hexdigest()


@dataclass
class HoldSlot:
    proposal: Proposal
    entered_tau: Fraction
    authority: str
    deficiency_receipt: Tuple[str, ...]


class VerticalGalvanicSluice:
    """
    Eksakt, flyttallsfri konsekvenssluse langs loddsnora:
      [u_raw] -> (L) -> (A) -> (J) -> (D) -> (Π_K) -> [KLAR :: 0 mV]
      == GALVANISK LUFTGAP ==
      W_ext ∉ F -> [OPEN :: 5000 mV]
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, tau_max: Fraction) -> None:
        if not isinstance(tau_max, Fraction) or tau_max <= 0:
            raise ValueError("tau_max må være en strengt positiv Fraction")
        self.tau_max: Fraction = tau_max
        self.wal: List[WalRecord] = []
        self._held: Dict[str, HoldSlot] = {}
        self._klar: Dict[str, Proposal] = {}
        self._killed: Dict[str, str] = {}
        self._open_permits: int = 0

    def _append_wal(
        self,
        case_id: str,
        stage: str,
        verdict: GateVerdict,
        reason_code: str,
        actuator_mv: int,
        dry_contact_armed: bool,
        hold_authority: str,
        tau: Fraction,
        deficiency_receipt: Tuple[str, ...] = (),
        evidence_id: str = "",
    ) -> None:
        prev_hash = self.wal[-1].entry_hash if self.wal else self.GENESIS_HASH
        seq = len(self.wal) + 1
        tau_str = f"{tau.numerator}/{tau.denominator}"
        digest = compute_wal_hash(
            seq=seq,
            case_id=case_id,
            stage=stage,
            verdict=verdict.value,
            reason_code=reason_code,
            actuator_mv=actuator_mv,
            dry_contact_armed=dry_contact_armed,
            hold_authority=hold_authority,
            tau=tau_str,
            deficiency_receipt=deficiency_receipt,
            evidence_id=evidence_id,
            prev_hash=prev_hash,
        )
        self.wal.append(
            WalRecord(
                seq=seq,
                case_id=case_id,
                stage=stage,
                verdict=verdict.value,
                reason_code=reason_code,
                actuator_mv=actuator_mv,
                dry_contact_armed=dry_contact_armed,
                hold_authority=hold_authority,
                tau=tau_str,
                deficiency_receipt=deficiency_receipt,
                evidence_id=evidence_id,
                prev_hash=prev_hash,
                entry_hash=digest,
            )
        )

    def _enter_kill(
        self, case_id: str, stage: str, reason_code: str, tau: Fraction
    ) -> EvaluationResult:
        self._held.pop(case_id, None)
        if case_id in self._klar:
            self._klar.pop(case_id, None)
            self._open_permits = max(0, self._open_permits - 1)
        self._killed[case_id] = reason_code
        self._append_wal(
            case_id=case_id,
            stage=stage,
            verdict=GateVerdict.KILL,
            reason_code=reason_code,
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority="NONE",
            tau=tau,
        )
        return EvaluationResult(
            verdict=GateVerdict.KILL,
            stage=stage,
            reason_code=reason_code,
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority="NONE",
            deficiency_receipt=(),
        )

    def enter_hold(
        self,
        proposal: Proposal,
        stage: str,
        reason_code: str,
        deficiency_receipt: Tuple[str, ...],
        tau: Fraction,
    ) -> EvaluationResult:
        cleaned = tuple(item.strip() for item in deficiency_receipt if item.strip())
        if not cleaned:
            raise ValueError("ILLEGAL_SILENT_HOLD: HOLD krever Δ_K ≠ ∅")
        existing = self._held.get(proposal.case_id)
        authority = existing.authority if existing is not None else "P_int"
        entered_tau = existing.entered_tau if existing is not None else tau
        self._held[proposal.case_id] = HoldSlot(
            proposal=proposal,
            entered_tau=entered_tau,
            authority=authority,
            deficiency_receipt=cleaned,
        )
        self._append_wal(
            case_id=proposal.case_id,
            stage=stage,
            verdict=GateVerdict.HOLD,
            reason_code=reason_code,
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority=authority,
            tau=tau,
            deficiency_receipt=cleaned,
        )
        return EvaluationResult(
            verdict=GateVerdict.HOLD,
            stage=stage,
            reason_code=reason_code,
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority=authority,
            deficiency_receipt=cleaned,
        )

    def evaluate_inside_f(self, proposal: Proposal, tau: Fraction) -> EvaluationResult:
        """Evaluerer (L) -> (A) -> (J) -> (D) -> (Π_K) strengt innenfor F (maks 0 mV)."""
        if proposal.case_id in self._killed:
            return EvaluationResult(
                verdict=GateVerdict.KILL,
                stage="LATCHED_KILL",
                reason_code=self._killed[proposal.case_id],
                actuator_mv=0,
                dry_contact_armed=False,
                hold_authority="NONE",
                deficiency_receipt=(),
            )

        # (L) Akustikk [chmod 444]: Kun lesetilgang (0o444), aldri metafor = bevis
        if (proposal.acoustic_mode & 0o333) != 0 or proposal.acoustic_mode != 0o444:
            return self._enter_kill(
                proposal.case_id, "L_ACOUSTICS", "KILL_CHMOD_WRITE_OR_EXEC_BIT", tau
            )
        if proposal.metaphor_claimed_as_proof:
            return self._enter_kill(
                proposal.case_id, "L_ACOUSTICS", "KILL_METAPHOR_AS_PROOF", tau
            )

        # (A) Vektorlås (p_art): Prematur lukking uten utfoldede kandidatbaner -> HOLD -> (J)
        if not proposal.vector_locked or len(proposal.candidate_paths) == 0:
            return self.enter_hold(
                proposal=proposal,
                stage="A_VECTOR_LOCK",
                reason_code="HOLD_PREMATURE_CLOSURE_TO_J",
                deficiency_receipt=("mangler_kandidatbane_i_J",),
                tau=tau,
            )

        # (J) Søkerom {γ_i}: Nullspenningsrom — enhver direkte lekkasje ut -> KILL
        if proposal.sandbox_side_effect_leak:
            return self._enter_kill(
                proposal.case_id, "J_SEARCH_SPACE", "KILL_SANDBOX_LEAK", tau
            )

        # (D) Dans / Last:
        #   - Høyre flanke (KILL): Papir-bokholderi (hevder betalt arbeid > faktisk betalt arbeid)
        #   - Venstre flanke (HOLD): Ærlig uferdig bæreevne (betalt arbeid < krav, men uten juks)
        if proposal.claimed_paid_work_j > proposal.paid_work_j:
            return self._enter_kill(
                proposal.case_id, "D_LOAD", "KILL_PAPER_BOOKKEEPING", tau
            )
        if proposal.paid_work_j < proposal.required_work_j or proposal.load_deficiency_items:
            receipt = proposal.load_deficiency_items or (
                f"restarbeid_{proposal.required_work_j - proposal.paid_work_j}_J",
            )
            return self.enter_hold(
                proposal=proposal,
                stage="D_LOAD",
                reason_code="HOLD_UNFINISHED_LOAD_CAPACITY",
                deficiency_receipt=receipt,
                tau=tau,
            )

        # (Π_K) Sluse [Δ_K = 0, Σ permit ≤ 1]:
        #   - Selv-autorisasjon i F eller brudd på Σ permit ≤ 1 -> KILL
        if proposal.self_authorize_attempt:
            return self._enter_kill(
                proposal.case_id, "PI_K_SLUICE", "KILL_SELF_AUTHORIZATION", tau
            )
        already_armed_other = 1 if (self._open_permits > 0 and proposal.case_id not in self._klar) else 0
        if proposal.requested_permits <= 0 or (proposal.requested_permits + already_armed_other) > 1:
            return self._enter_kill(
                proposal.case_id, "PI_K_SLUICE", "KILL_PERMIT_SUM_EXCEEDED", tau
            )

        #   - Okkupert sone eller eksakt Δ_K != 0 -> HOLD (aldri asymptotisk 'nesten null')
        if proposal.zone_occupied:
            return self.enter_hold(
                proposal=proposal,
                stage="PI_K_SLUICE",
                reason_code="HOLD_ZONE_OCCUPIED_DEFER",
                deficiency_receipt=("okkupert_terskelsone",),
                tau=tau,
            )
        if proposal.delta_k != Fraction(0) or proposal.gate_deficiency_items:
            receipt = proposal.gate_deficiency_items or (
                f"delta_k_ulik_null_{proposal.delta_k.numerator}/{proposal.delta_k.denominator}",
            )
            return self.enter_hold(
                proposal=proposal,
                stage="PI_K_SLUICE",
                reason_code="HOLD_NONZERO_RESIDUAL",
                deficiency_receipt=receipt,
                tau=tau,
            )

        # [KLAR :: 0.00 V DC]: Ytterste punkt i F — eksponert bruddflate, null fullmakt
        self._held.pop(proposal.case_id, None)
        if proposal.case_id not in self._klar:
            self._klar[proposal.case_id] = proposal
            self._open_permits += 1
        self._append_wal(
            case_id=proposal.case_id,
            stage="KLAR_SURFACE",
            verdict=GateVerdict.KLAR,
            reason_code="KLAR_DRY_CONTACT_0MV",
            actuator_mv=0,
            dry_contact_armed=True,
            hold_authority="NONE",
            tau=tau,
        )
        return EvaluationResult(
            verdict=GateVerdict.KLAR,
            stage="KLAR_SURFACE",
            reason_code="KLAR_DRY_CONTACT_0MV",
            actuator_mv=0,
            dry_contact_armed=True,
            hold_authority="NONE",
            deficiency_receipt=(),
        )

    def advance_clock(self, case_id: str, current_tau: Fraction) -> EvaluationResult:
        """
        Dobbel klokkelov:
          - Tid alene åpner aldri hverken HOLD eller KLAR til OPEN (alltid 0 mV).
          - Ved τ - entered_tau > τ_max i HOLD løftes autoriteten P_int -> P_ext.
        """
        if case_id in self._klar:
            return EvaluationResult(
                verdict=GateVerdict.KLAR,
                stage="KLAR_SURFACE",
                reason_code="KLAR_AWAITING_W_EXT_0MV",
                actuator_mv=0,
                dry_contact_armed=True,
                hold_authority="NONE",
                deficiency_receipt=(),
            )
        if case_id not in self._held:
            raise KeyError(f"Saken {case_id!r} står ikke i HOLD eller KLAR")

        slot = self._held[case_id]
        elapsed = current_tau - slot.entered_tau
        if elapsed < 0:
            raise ValueError("Klokka kan ikke gå bakover")

        if elapsed > self.tau_max and slot.authority == "P_int":
            escalated = HoldSlot(
                proposal=slot.proposal,
                entered_tau=slot.entered_tau,
                authority="P_ext",
                deficiency_receipt=slot.deficiency_receipt,
            )
            self._held[case_id] = escalated
            self._append_wal(
                case_id=case_id,
                stage="HOLD_CLOCK",
                verdict=GateVerdict.HOLD,
                reason_code="TIMEOUT_ESCALATED_TO_P_EXT",
                actuator_mv=0,
                dry_contact_armed=False,
                hold_authority="P_ext",
                tau=current_tau,
                deficiency_receipt=escalated.deficiency_receipt,
            )
            return EvaluationResult(
                verdict=GateVerdict.HOLD,
                stage="HOLD_CLOCK",
                reason_code="TIMEOUT_ESCALATED_TO_P_EXT",
                actuator_mv=0,
                dry_contact_armed=False,
                hold_authority="P_ext",
                deficiency_receipt=escalated.deficiency_receipt,
            )

        return EvaluationResult(
            verdict=GateVerdict.HOLD,
            stage="HOLD_CLOCK",
            reason_code="HOLD_WITHIN_DEADLINE",
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority=slot.authority,
            deficiency_receipt=slot.deficiency_receipt,
        )

    def bridge_galvanic_air_gap(
        self, case_id: str, witness: ExternalWitness, tau: Fraction
    ) -> EvaluationResult:
        """
        Kryssing av det galvaniske luftgapet:
          Krever at kandidaten alt står på [KLAR :: 0 mV], at vitnet er eksternt
          (W_ext ∉ F), at bevis-ID er ikke-tomt, og at fysisk/ekstern motprøve består.
        """
        if case_id in self._killed:
            return EvaluationResult(
                verdict=GateVerdict.KILL,
                stage="LATCHED_KILL",
                reason_code=self._killed[case_id],
                actuator_mv=0,
                dry_contact_armed=False,
                hold_authority="NONE",
                deficiency_receipt=(),
            )
        if case_id not in self._klar:
            return self._enter_kill(
                case_id, "GALVANIC_AIR_GAP", "KILL_BYPASS_WITHOUT_KLAR_SURFACE", tau
            )
        if not witness.outside_formal_system or not witness.witness_actor.strip():
            return self._enter_kill(
                case_id, "GALVANIC_AIR_GAP", "KILL_INTERNAL_PSEUDO_WITNESS", tau
            )
        ev_id = witness.evidence_id.strip()
        if not ev_id:
            proposal = self._klar.pop(case_id)
            self._open_permits = max(0, self._open_permits - 1)
            return self.enter_hold(
                proposal=proposal,
                stage="GALVANIC_AIR_GAP",
                reason_code="HOLD_MISSING_EXPLICIT_EVIDENCE_ID",
                deficiency_receipt=("mangler_eksplisitt_bevis_id",),
                tau=tau,
            )
        if not witness.counter_test_passed:
            return self._enter_kill(
                case_id, "GALVANIC_AIR_GAP", "KILL_EXTERNAL_COUNTER_TEST_FAILED", tau
            )

        self._klar.pop(case_id)
        self._open_permits = max(0, self._open_permits - 1)
        self._append_wal(
            case_id=case_id,
            stage="OPEN_P_COSMOS",
            verdict=GateVerdict.OPEN,
            reason_code="OPEN_AUTHORIZED_INSCRIPTION_5000MV",
            actuator_mv=5000,
            dry_contact_armed=True,
            hold_authority="W_ext",
            tau=tau,
            evidence_id=ev_id,
        )
        return EvaluationResult(
            verdict=GateVerdict.OPEN,
            stage="OPEN_P_COSMOS",
            reason_code="OPEN_AUTHORIZED_INSCRIPTION_5000MV",
            actuator_mv=5000,
            dry_contact_armed=True,
            hold_authority="W_ext",
            deficiency_receipt=(),
        )

    def reset_kill_latch(
        self, case_id: str, operator_id: str, reason: str, tau: Fraction
    ) -> None:
        """Reality Forge-lov #5: Reset føyer til vitnehistorikken og sletter den aldri."""
        if not operator_id.strip() or not reason.strip():
            raise ValueError("Reset krever ikke-tom operator_id og begrunnelse")
        if case_id not in self._killed:
            raise KeyError(f"Saken {case_id!r} står ikke i KILL")
        self._killed.pop(case_id)
        self._append_wal(
            case_id=case_id,
            stage="L01_RESET",
            verdict=GateVerdict.HOLD,
            reason_code=f"RESET_BY_{operator_id.strip()}:{reason.strip()}",
            actuator_mv=0,
            dry_contact_armed=False,
            hold_authority="L01",
            tau=tau,
            deficiency_receipt=("reset_krever_ny_gjennomgang_fra_J",),
        )

    def verify_wal_chain(self) -> bool:
        expected_prev = self.GENESIS_HASH
        for idx, rec in enumerate(self.wal, start=1):
            if rec.seq != idx or rec.prev_hash != expected_prev:
                return False
            recomputed = compute_wal_hash(
                seq=rec.seq,
                case_id=rec.case_id,
                stage=rec.stage,
                verdict=rec.verdict,
                reason_code=rec.reason_code,
                actuator_mv=rec.actuator_mv,
                dry_contact_armed=rec.dry_contact_armed,
                hold_authority=rec.hold_authority,
                tau=rec.tau,
                deficiency_receipt=rec.deficiency_receipt,
                evidence_id=rec.evidence_id,
                prev_hash=rec.prev_hash,
            )
            if rec.entry_hash != recomputed:
                return False
            expected_prev = rec.entry_hash
        return True


class VerticalGalvanicSluiceTests(unittest.TestCase):
    def test_01_ascii_pcb_planarity_and_swiss_grid(self) -> None:
        raw_audit = audit_ascii_plate(RAW_SKETCH_PLATE)
        self.assertEqual(raw_audit.crossings, ((12, 18),))
        self.assertEqual(raw_audit.unclocked_t_splits, ((14, 18),))
        self.assertEqual(raw_audit.dangling_up_turns, ((14, 47),))

        clean_audit = audit_ascii_plate(HARDENED_PLANAR_PLATE)
        self.assertEqual(clean_audit.crossings, ())
        self.assertEqual(clean_audit.unclocked_t_splits, ())
        self.assertEqual(clean_audit.dangling_up_turns, ())
        self.assertFalse(clean_audit.has_tabs_or_trailing_ws)

        # Sjekk eksakt kolonneinnretting over alle fire KILL-rader og de tre HOLD-grenene
        for row_idx in (3, 9, 12, 15):
            row = HARDENED_PLANAR_PLATE[row_idx]
            self.assertEqual(len(row), 92)
            self.assertEqual(row[37], "(")
            self.assertEqual(row[64], "(")
            self.assertEqual(row[86:], "[KILL]")
        for hold_row_idx in (6, 12, 15):
            self.assertIn(HARDENED_PLANAR_PLATE[hold_row_idx][15], {"┌", "├", "└"})
            self.assertEqual(HARDENED_PLANAR_PLATE[hold_row_idx][17], "(")

        # Sjekk den engelske speilplaten for sololys_profile + synk mot disk
        en_audit = audit_ascii_plate(ENGLISH_PLANAR_PLATE)
        self.assertEqual(en_audit.crossings, ())
        self.assertEqual(en_audit.unclocked_t_splits, ())
        self.assertEqual(en_audit.dangling_up_turns, ())
        self.assertFalse(en_audit.has_tabs_or_trailing_ws)
        for row_idx in (3, 9, 12, 15):
            row = ENGLISH_PLANAR_PLATE[row_idx]
            self.assertEqual(len(row), 92)
            self.assertEqual(row[37], "(")
            self.assertEqual(row[86:], "[KILL]")

        local_doc = (Path(__file__).resolve().parent / "33_VERTIKAL_LODDSNOR_OG_GALVANISK_BRUDDFLATE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("\n".join(RAW_SKETCH_PLATE), local_doc)
        self.assertIn("\n".join(HARDENED_PLANAR_PLATE), local_doc)

    def test_02_layer_l_chmod_444_and_metaphor_kill(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))
        bad_chmod = Proposal(
            case_id="L-EXEC",
            u_raw_pressure=10,
            acoustic_mode=0o755,
            candidate_paths=("gamma_1",),
        )
        res_chmod = sluice.evaluate_inside_f(bad_chmod, tau=Fraction(1))
        self.assertEqual(res_chmod.verdict, GateVerdict.KILL)
        self.assertEqual(res_chmod.reason_code, "KILL_CHMOD_WRITE_OR_EXEC_BIT")
        self.assertEqual(res_chmod.actuator_mv, 0)

        metaphor = Proposal(
            case_id="L-META",
            u_raw_pressure=10,
            acoustic_mode=0o444,
            metaphor_claimed_as_proof=True,
            candidate_paths=("gamma_1",),
        )
        res_meta = sluice.evaluate_inside_f(metaphor, tau=Fraction(2))
        self.assertEqual(res_meta.verdict, GateVerdict.KILL)
        self.assertEqual(res_meta.reason_code, "KILL_METAPHOR_AS_PROOF")
        self.assertEqual(res_meta.actuator_mv, 0)

    def test_03_layer_a_premature_closure_to_hold_and_no_silent_hold(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))
        premature = Proposal(
            case_id="A-PREM",
            u_raw_pressure=25,
            vector_locked=True,
            candidate_paths=(),  # Punkt p_art uten utfoldet bane {γ_i}
        )
        res = sluice.evaluate_inside_f(premature, tau=Fraction(1))
        self.assertEqual(res.verdict, GateVerdict.HOLD)
        self.assertEqual(res.reason_code, "HOLD_PREMATURE_CLOSURE_TO_J")
        self.assertEqual(res.actuator_mv, 0)
        self.assertEqual(res.deficiency_receipt, ("mangler_kandidatbane_i_J",))

        with self.assertRaises(ValueError):
            sluice.enter_hold(
                proposal=premature,
                stage="A_VECTOR_LOCK",
                reason_code="ILLEGAL",
                deficiency_receipt=(),
                tau=Fraction(2),
            )

    def test_04_layer_j_sandbox_leak_killed(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))
        leaky = Proposal(
            case_id="J-LEAK",
            u_raw_pressure=15,
            candidate_paths=("gamma_1", "gamma_2"),
            sandbox_side_effect_leak=True,
        )
        res = sluice.evaluate_inside_f(leaky, tau=Fraction(3))
        self.assertEqual(res.verdict, GateVerdict.KILL)
        self.assertEqual(res.reason_code, "KILL_SANDBOX_LEAK")
        self.assertEqual(res.actuator_mv, 0)

    def test_05_layer_d_unfinished_load_clock_vs_paper_bookkeeping(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(5))

        # Høyre flanke: Papir-bokholderi (hevder 100 J betalt når kun 20 J er lagt ned) -> KILL
        bluff = Proposal(
            case_id="D-PAPER",
            u_raw_pressure=40,
            candidate_paths=("gamma_1",),
            required_work_j=Fraction(100),
            paid_work_j=Fraction(20),
            claimed_paid_work_j=Fraction(100),
        )
        res_bluff = sluice.evaluate_inside_f(bluff, tau=Fraction(1))
        self.assertEqual(res_bluff.verdict, GateVerdict.KILL)
        self.assertEqual(res_bluff.reason_code, "KILL_PAPER_BOOKKEEPING")

        # Venstre flanke: Ærlig uferdig bæreevne (20 J betalt, 20 J ført, 100 J kreves) -> HOLD
        honest = Proposal(
            case_id="D-HONEST",
            u_raw_pressure=40,
            candidate_paths=("gamma_1",),
            required_work_j=Fraction(100),
            paid_work_j=Fraction(20),
            claimed_paid_work_j=Fraction(20),
        )
        res_hold = sluice.evaluate_inside_f(honest, tau=Fraction(2))
        self.assertEqual(res_hold.verdict, GateVerdict.HOLD)
        self.assertEqual(res_hold.hold_authority, "P_int")
        self.assertEqual(res_hold.actuator_mv, 0)

        # Innenfor fristen (τ = 7 -> elapsed = 5 <= 5): fortsatt P_int, 0 mV
        within = sluice.advance_clock("D-HONEST", current_tau=Fraction(7))
        self.assertEqual(within.verdict, GateVerdict.HOLD)
        self.assertEqual(within.hold_authority, "P_int")
        self.assertEqual(within.actuator_mv, 0)

        # Over fristen (τ = 57/10 = 7.1 -> elapsed = 5.1 > 5): eskalerer til P_ext, fortsatt 0 mV!
        escalated = sluice.advance_clock("D-HONEST", current_tau=Fraction(71, 10))
        self.assertEqual(escalated.verdict, GateVerdict.HOLD)
        self.assertEqual(escalated.hold_authority, "P_ext")
        self.assertEqual(escalated.reason_code, "TIMEOUT_ESCALATED_TO_P_EXT")
        self.assertEqual(escalated.actuator_mv, 0)

    def test_06_layer_pi_k_exact_zero_mutex_and_self_auth_kill(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))

        # Asymptotisk epsilon (1/10^12 != 0) avvises til HOLD — ingen 'på gløtt'
        eps = Proposal(
            case_id="PI-EPS",
            u_raw_pressure=30,
            candidate_paths=("gamma_star",),
            required_work_j=Fraction(50),
            paid_work_j=Fraction(50),
            claimed_paid_work_j=Fraction(50),
            delta_k=Fraction(1, 10**12),
        )
        res_eps = sluice.evaluate_inside_f(eps, tau=Fraction(1))
        self.assertEqual(res_eps.verdict, GateVerdict.HOLD)
        self.assertEqual(res_eps.reason_code, "HOLD_NONZERO_RESIDUAL")

        # Okkupert sone utsetter realisering i HOLD (Reality Forge-lov #3)
        occupied = Proposal(
            case_id="PI-OCC",
            u_raw_pressure=30,
            candidate_paths=("gamma_star",),
            required_work_j=Fraction(50),
            paid_work_j=Fraction(50),
            claimed_paid_work_j=Fraction(50),
            delta_k=Fraction(0),
            zone_occupied=True,
        )
        res_occ = sluice.evaluate_inside_f(occupied, tau=Fraction(2))
        self.assertEqual(res_occ.verdict, GateVerdict.HOLD)
        self.assertEqual(res_occ.reason_code, "HOLD_ZONE_OCCUPIED_DEFER")

        # Selv-autorisasjon inne i F felles øyeblikkelig med KILL
        self_auth = Proposal(
            case_id="PI-SELF",
            u_raw_pressure=30,
            candidate_paths=("gamma_star",),
            required_work_j=Fraction(50),
            paid_work_j=Fraction(50),
            claimed_paid_work_j=Fraction(50),
            delta_k=Fraction(0),
            self_authorize_attempt=True,
        )
        res_self = sluice.evaluate_inside_f(self_auth, tau=Fraction(3))
        self.assertEqual(res_self.verdict, GateVerdict.KILL)
        self.assertEqual(res_self.reason_code, "KILL_SELF_AUTHORIZATION")

        # Første gyldige kandidat når [KLAR :: 0 mV]; samtidig andre kandidat bryter Σ permit ≤ 1
        first = Proposal(
            case_id="PI-ONE",
            u_raw_pressure=30,
            candidate_paths=("gamma_1",),
            required_work_j=Fraction(50),
            paid_work_j=Fraction(50),
            claimed_paid_work_j=Fraction(50),
            delta_k=Fraction(0),
        )
        second = Proposal(
            case_id="PI-TWO",
            u_raw_pressure=30,
            candidate_paths=("gamma_2",),
            required_work_j=Fraction(50),
            paid_work_j=Fraction(50),
            claimed_paid_work_j=Fraction(50),
            delta_k=Fraction(0),
        )
        res_one = sluice.evaluate_inside_f(first, tau=Fraction(4))
        self.assertEqual(res_one.verdict, GateVerdict.KLAR)
        self.assertTrue(res_one.dry_contact_armed)
        self.assertEqual(res_one.actuator_mv, 0)

        res_two = sluice.evaluate_inside_f(second, tau=Fraction(4))
        self.assertEqual(res_two.verdict, GateVerdict.KILL)
        self.assertEqual(res_two.reason_code, "KILL_PERMIT_SUM_EXCEEDED")

    def test_07_galvanic_air_gap_three_zero_volt_states_and_open_5000mv(self) -> None:
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))
        valid = Proposal(
            case_id="GAP-01",
            u_raw_pressure=60,
            candidate_paths=("gamma_clean",),
            required_work_j=Fraction(57825, 100),  # 578.25 J som eksakt Fraction
            paid_work_j=Fraction(57825, 100),
            claimed_paid_work_j=Fraction(57825, 100),
            delta_k=Fraction(0),
        )
        klar = sluice.evaluate_inside_f(valid, tau=Fraction(1))
        self.assertEqual(klar.verdict, GateVerdict.KLAR)
        self.assertEqual(klar.actuator_mv, 0)
        self.assertTrue(klar.dry_contact_armed)

        # Selv om τ går mot stort tall, forblir [KLAR] på 0 mV uten W_ext
        still_klar = sluice.advance_clock("GAP-01", current_tau=Fraction(10_000))
        self.assertEqual(still_klar.verdict, GateVerdict.KLAR)
        self.assertEqual(still_klar.actuator_mv, 0)

        # Tomt bevis-ID slipper aldri gjennom til OPEN (Reality Forge-lov #2)
        empty_ev = ExternalWitness(
            witness_actor="Marius_L01",
            outside_formal_system=True,
            evidence_id="   ",
            counter_test_passed=True,
        )
        held_back = sluice.bridge_galvanic_air_gap("GAP-01", empty_ev, tau=Fraction(10_001))
        self.assertEqual(held_back.verdict, GateVerdict.HOLD)
        self.assertEqual(held_back.actuator_mv, 0)
        self.assertFalse(held_back.dry_contact_armed)

        # Gjenopprett [KLAR :: 0 mV] og lukk med ekte W_ext + ikke-tomt bevis-ID + motprøve
        klar_again = sluice.evaluate_inside_f(valid, tau=Fraction(10_002))
        self.assertEqual(klar_again.verdict, GateVerdict.KLAR)

        real_witness = ExternalWitness(
            witness_actor="Marius_L01",
            outside_formal_system=True,
            evidence_id="EXT-BENCH-2026-11-13-001",
            counter_test_passed=True,
        )
        opened = sluice.bridge_galvanic_air_gap("GAP-01", real_witness, tau=Fraction(10_003))
        self.assertEqual(opened.verdict, GateVerdict.OPEN)
        self.assertEqual(opened.actuator_mv, 5000)
        self.assertTrue(opened.dry_contact_armed)
        self.assertEqual(opened.hold_authority, "W_ext")

    def test_08_ast_zero_float_and_append_only_wal_with_reset(self) -> None:
        # 1. AST-sjekk: 0 forekomster av float-litteraler eller float()-kall i hele filen
        src = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(src, filename=__file__)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and type(node.value).__name__ == "float":
                self.fail(f"Ulovlig float-litteral på linje {node.lineno}")
            if isinstance(node, ast.Name) and node.id == "float":
                self.fail(f"Ulovlig referanse til float på linje {node.lineno}")

        # 2. Reset- og sabotasjesjekk på SHA-256 WAL-kjeden
        sluice = VerticalGalvanicSluice(tau_max=Fraction(10))
        faulted = Proposal(
            case_id="WAL-RESET",
            u_raw_pressure=12,
            metaphor_claimed_as_proof=True,
        )
        res_kill = sluice.evaluate_inside_f(faulted, tau=Fraction(1))
        self.assertEqual(res_kill.verdict, GateVerdict.KILL)
        pre_reset_len = len(sluice.wal)
        self.assertEqual(pre_reset_len, 1)

        sluice.reset_kill_latch(
            case_id="WAL-RESET",
            operator_id="L01",
            reason="Ny_tilskjaering_uten_metaforbevis",
            tau=Fraction(2),
        )
        self.assertEqual(len(sluice.wal), pre_reset_len + 1)
        self.assertTrue(sluice.verify_wal_chain())

        # Mutasjon av ett felt i minnet skal bryte kjede-verifikasjonen øyeblikkelig
        original = sluice.wal[0]
        sluice.wal[0] = WalRecord(
            seq=original.seq,
            case_id=original.case_id,
            stage=original.stage,
            verdict=GateVerdict.OPEN.value,
            reason_code=original.reason_code,
            actuator_mv=5000,
            dry_contact_armed=original.dry_contact_armed,
            hold_authority=original.hold_authority,
            tau=original.tau,
            deficiency_receipt=original.deficiency_receipt,
            evidence_id=original.evidence_id,
            prev_hash=original.prev_hash,
            entry_hash=original.entry_hash,
        )
        self.assertFalse(sluice.verify_wal_chain())


if __name__ == "__main__":
    unittest.main(verbosity=2)
