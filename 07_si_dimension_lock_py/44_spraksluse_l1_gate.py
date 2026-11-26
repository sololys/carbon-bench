#!/usr/bin/env python3
"""
07_si_dimension_lock_py/44_spraksluse_l1_gate.py — Herdet Fail-Closed To-Spors Språksluse (X.01–X.06)
====================================================================================
Epistemisk status : L1 (lokalt demonstrert programvare; append-only SHA-256 != fysisk WORM)
Kontraktregel     : INSPIRED_BY != IMPLEMENTS != PROVES
Flyttallsforbud   : 0 forekomster av float i kildefilen (verifisert via AST-vakt i Test 10)

Benkrevisjon og herding av innkommet Carbon44Gate-skisse:
  1. 0 mV DC over luftgapet  : KILL, HOLD, ESCALATED_P_EXT og KLAR har alle eksakt 0 mV DC
                               (fjerner 2500 mV-lekkasjen fra HOLD som bryter V_IH ~ 2000 mV).
                               5000 mV DC oppstår utelukkende i OPEN etter W_ext-passering.
  2. Dobbel klokkelov (X.02) : Fristbrudd (hold_elapsed_ms > tau_max_ms) utløser aldri stum KILL
                               (forbud mot uthalings-veto), men eskalerer jurisdiksjon P_int -> P_ext
                               ved 0 mV DC, samt baklengs dekompilering av nåtidssnitt p(e)=gamma_e(1).
  3. Rekkevidde-paritet (X.01): Fanger norske universalkvantorer («ingen», «intet», «enhver», «ethvert»,
                               «umulig», «utelukket», «alltid», «aldri») uten å tvinge retoriske ord
                               inn i S_skjelett. Krever eksplisitt premise_domain + negated_domains +
                               fracture_bound for universelle utsagn, og forbyr bevis-verb på INSPIRED_BY.
  4. Kuleshov-karantene (X.04): Sporer det ortogonale prosa-leksikonet Q_j = Words(prosa_j) \\ Words(skjelett_j)
                               automatisk (`chmod 444`). Sene ledd som smugler Q_j inn i sitt skjelett
                               felles med X04_ORTHOGONAL_TROPE_SMUGGLING uten å stole på egenrapportering.
  5. Penrose-akkumulator (X.05): Avviser tomt premise_domain (ingen vakuum-passering) og akkumulerer
                               globalt snitt av aktive og utelukkede domener langs kjeden, med
                               Zero-Window-lås (høyst 1 ventende KLAR-ramme i luftslusen om gangen).
  6. Anti-papegøye W_ext (X.06): Avviser både gummistempel («ja», «ok», «godkjent»), korte dummy-strenger
                               og trivielle redigeringer av maskinens B_brudd^(F) via eksakt rasjonal
                               Jaccard-likhet i Q (Fraction(4, 5), null float). Krever os.fsync på fil + katalog.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import tempfile


STANDALONE_COMMIT_AUTHORITY = "NONE"
PHYSICAL_AUTHORITY = "NONE"


class GateState(Enum):
    KILL = "KILL"                        # 0 mV DC: Jordet avskjæring (forfalsket dekning)
    HOLD = "HOLD"                        # 0 mV DC: Reversibelt verksted under dobbel klokke
    ESCALATED_P_EXT = "ESCALATED_P_EXT"  # 0 mV DC: Tidsfrist utløpt (P_int -> P_ext, ikke KILL)
    KLAR = "KLAR"                        # 0 mV DC: Ytterste punkt i F (tørrkontakt før luftgap)
    OPEN = "OPEN"                        # 5000 mV DC: Kun via W_ext ∉ F under luftgapet


def state_millivolts_dc(state: GateState) -> int:
    """Eksakt spenningslov: 0 mV DC i hele F; 5000 mV DC kun under det galvaniske luftgapet."""
    if state is GateState.OPEN:
        return 5000
    return 0


PROOF_CLAIM_TOKENS = frozenset({
    "beviser", "bevist", "garanterer", "teorem", "lovfestet",
})

UNIVERSAL_SCOPE_TOKENS = frozenset({
    "alltid", "aldri", "ingen", "intet", "enhver", "ethvert",
    "alle", "umulig", "utelukket", "uunngåelig", "nødvendigvis", "ufravikelig",
})

RUBBER_STAMP_TOKENS = frozenset({
    "ja", "ok", "okay", "yes", "true", "1", "ack", "godkjent", "bekreftet", "signert",
})

FALSIFIER_MARKERS = frozenset({
    "<", ">", "<=", ">=", "!=", "==", "ppm", "hz", "mv", "v", "bar", "nm", "ns", "ms",
    "mikrom", "k", "j", "w", "m", "avvises", "faller", "ryker", "opphører", "svikter",
    "overstiger", "mangler", "dersom", "hvis", "ved",
})

NORWEGIAN_STOPWORDS = frozenset({
    "og", "i", "på", "av", "til", "for", "med", "uten", "som", "en", "et", "ei",
    "den", "det", "de", "er", "var", "blir", "kan", "må", "skal", "vil", "har",
    "om", "ut", "inn", "fra", "over", "under", "mot", "ved", "seg", "sin", "sitt",
    "sine", "ikke", "kun", "bare", "eller", "men", "når", "der", "her", "slik", "at",
})

MAX_ECHO_JACCARD = Fraction(4, 5)  # Eksakt 4/5 = 80 % ord-overlapp tak mot trivielt ekko


def tokenize_clean(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.lower().replace("—", " ").replace("–", " ").replace(";", " ").split():
        cleaned = raw.strip(".,;:!?()[]{}«»\"'`/\\")
        if cleaned:
            out.append(cleaned)
    return out


def content_words(text: str) -> set[str]:
    return {
        w for w in tokenize_clean(text)
        if len(w) >= 3 and w not in NORWEGIAN_STOPWORDS
    }


@dataclass(frozen=True)
class SkeletonTrack:
    step_id: str
    claim: str
    premise_domain: frozenset[str]       # Aktive gyldighetsvilkår (må være ikke-tom for X.05)
    negated_domains: frozenset[str]      # Eksplisitt utelukkede vilkår / grenser
    law_or_source: str                   # F.eks. "IMPLEMENTS:Godel_1931_II + INSPIRED_BY:..."
    fracture_bound: str                  # B_brudd^(F): Eksakt bruddgrense formulert inne i F
    upstream_refs: tuple[str, ...] = ()  # Kun tillatt å peke på verifiserte step_id i S_skjelett


@dataclass(frozen=True)
class CandidateLine:
    prose_surface: str
    skeleton: SkeletonTrack
    prose_refs: tuple[str, ...] = ()     # Eksplisitte prosa-referanser (alltid forbudt, X.04)
    co_generative_strike: bool = False   # X.02: Sant når p(e) = gamma_e(1) oppstod uten forløp
    decompiled_from_hold: bool = False   # X.02: Sant når p_art er ekstrahert baklengs via HOLD


@dataclass(frozen=True)
class ExternalWitness:
    witness_id: str
    evidence_id: str
    counter_bound: str                   # B_ext: Uavhengig operativ bruddgrense utenfra (X.06)
    elapsed_ms: int


def parse_source_tags(law_or_source: str) -> set[str]:
    """Ekstraherer epistemiske hovedklasser ('INSPIRED_BY', 'IMPLEMENTS', 'PROVES') fra kildestreng."""
    tags: set[str] = set()
    for part in law_or_source.split("+"):
        head = part.strip().split(":", 1)[0].strip().upper()
        if head:
            tags.add(head)
    return tags


def fsync_directory(file_path: Path) -> None:
    dir_fd = os.open(str(file_path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def verify_wal_chain(wal_path: Path) -> tuple[bool, int, str]:
    """Verifiserer append-only SHA-256-kjede og 0 mV-lov på alle ikke-OPEN-poster."""
    if not wal_path.exists():
        return True, 0, "0" * 64
    expected_prev = "0" * 64
    count = 0
    for line in wal_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["prev"] != expected_prev:
            return False, count, "BROKEN_PREV_LINK"
        state = GateState(rec["state"])
        if rec["millivolts_dc"] != state_millivolts_dc(state):
            return False, count, "VOLTAGE_INVARIANT_VIOLATION"
        payload = {
            "prev": rec["prev"],
            "step_id": rec["step_id"],
            "state": rec["state"],
            "millivolts_dc": rec["millivolts_dc"],
            "detail": rec["detail"],
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != rec["sha256"]:
            return False, count, "DIGEST_MISMATCH"
        expected_prev = digest
        count += 1
    return True, count, expected_prev


class Carbon44Gate:
    def __init__(
        self,
        wal_path: Path,
        tau_max_ms: int = 300_000,
        dtau_min_ms: int = 8_000,
        domain_lexicon: frozenset[str] = frozenset(),
    ) -> None:
        if tau_max_ms <= 0 or dtau_min_ms <= 0:
            raise ValueError("Tidsgrenser må være strengt positive heltall i millisekunder.")
        self._wal_path = wal_path
        self._tau_max_ms = tau_max_ms
        self._dtau_min_ms = dtau_min_ms
        self._domain_lexicon = {w.lower() for w in domain_lexicon}
        self._verified_ids: set[str] = set()
        self._active_domains: set[str] = set()
        self._forbidden_domains: set[str] = set()
        self._quarantined_tropes: dict[str, str] = {}  # X.04: ord i (I - Pi_K)gamma -> opphavs-step_id
        self._pending_klar: CandidateLine | None = None  # Zero-Window: maks 1 kandidat ved luftgapet
        ok, _, head = verify_wal_chain(wal_path)
        if not ok:
            raise RuntimeError(f"Korrupt WAL ved oppstart: {head}")
        self._chain_head: str = head

    @staticmethod
    def decompile_cogenerative_strike(
        prose_surface: str,
        extracted_skeleton: SkeletonTrack,
    ) -> CandidateLine:
        """X.02: Fryser p(e)=gamma_e(1) og returnerer baklengs dekompilert to-spors kandidat."""
        return CandidateLine(
            prose_surface=prose_surface,
            skeleton=extracted_skeleton,
            co_generative_strike=True,
            decompiled_from_hold=True,
        )

    def evaluate_in_f(self, cand: CandidateLine, hold_elapsed_ms: int = 0) -> tuple[GateState, str]:
        sk = cand.skeleton

        # Dobbel klokkelov: fristbrudd i HOLD gir aldri KILL, men eskalerer P_int -> P_ext (0 mV DC)
        if hold_elapsed_ms > self._tau_max_ms:
            if self._pending_klar is not None and self._pending_klar.skeleton.step_id == sk.step_id:
                self._pending_klar = None
            return self._commit(GateState.ESCALATED_P_EXT, sk.step_id, "HOLD_TIMEOUT_ESCALATED_TO_P_EXT")

        # Zero-Window (sum(read_permit) <= 1): okkupert luftsluse utsetter, omgår aldri
        if self._pending_klar is not None and self._pending_klar.skeleton.step_id != sk.step_id:
            return self._commit(GateState.HOLD, sk.step_id, "ZERO_WINDOW_AIRLOCK_OCCUPIED")

        # X.02: Rått nåtidssnitt p(e)=gamma_e(1) uten baklengs dekompilering fryses i HOLD
        if cand.co_generative_strike and not cand.decompiled_from_hold:
            return self._commit(GateState.HOLD, sk.step_id, "X02_COGENERATIVE_FREEZE_DECOMPILE_REQUIRED")

        # X.04 (del A): Eksplisitte referanser til prosaflate forbys momentant
        if cand.prose_refs:
            return self._commit(GateState.KILL, sk.step_id, "X04_PROSE_SURFACE_LEAK")

        # X.04 (del B): Mekanisk sjekk mot ortogonale troper fra tidligere (I - Pi_K)gamma
        skeleton_lexicon = content_words(sk.claim) | content_words(" ".join(sorted(sk.premise_domain)))
        smuggled = sorted(
            f"{w}@{self._quarantined_tropes[w]}"
            for w in skeleton_lexicon
            if w in self._quarantined_tropes
        )
        if smuggled:
            return self._commit(GateState.KILL, sk.step_id, f"X04_ORTHOGONAL_TROPE_SMUGGLING::{smuggled[0]}")

        # Oppstrøms skjelett-avhengigheter må være verifisert (OPEN) før bruk
        if any(ref not in self._verified_ids for ref in sk.upstream_refs):
            return self._commit(GateState.HOLD, sk.step_id, "UNVERIFIED_UPSTREAM_SKELETON")

        # X.01 (del A): Ufullstendig skjelett eller tomt domene -> HOLD med konkret mangellapp
        if not (sk.claim.strip() and sk.law_or_source.strip() and sk.fracture_bound.strip()):
            return self._commit(GateState.HOLD, sk.step_id, "DELTA_K_INCOMPLETE_SKELETON")
        if not sk.premise_domain:
            return self._commit(GateState.HOLD, sk.step_id, "DELTA_K_EMPTY_PREMISE_DOMAIN")

        tags = parse_source_tags(sk.law_or_source)
        if not tags or not tags.issubset({"INSPIRED_BY", "IMPLEMENTS", "PROVES"}):
            return self._commit(GateState.HOLD, sk.step_id, "DELTA_K_INVALID_SOURCE_TAG")

        prose_words = set(tokenize_clean(cand.prose_surface))
        has_proof_verb = bool(prose_words & PROOF_CLAIM_TOKENS)
        has_universal = bool(prose_words & UNIVERSAL_SCOPE_TOKENS)

        # Epistemisk demarkasjon: ren INSPIRED_BY kan verken bære bevis-verb eller universallov
        if tags == {"INSPIRED_BY"} and (has_proof_verb or has_universal):
            return self._commit(GateState.KILL, sk.step_id, "AESTHETIC_USURPATION")

        # X.01 (del B): Bevis-verb i prosa krever PROVES eller IMPLEMENTS, og blandet kilde krever negert grense
        if has_proof_verb and "PROVES" not in tags and "IMPLEMENTS" not in tags:
            return self._commit(GateState.KILL, sk.step_id, "X01_PROOF_VERB_WITHOUT_ANCHOR")
        if "INSPIRED_BY" in tags and ("PROVES" in tags or "IMPLEMENTS" in tags) and not sk.negated_domains:
            return self._commit(GateState.KILL, sk.step_id, "X01_MIXED_SOURCE_UNFENCED_DRIFT")

        # X.01 (del C): Universalkvantor i prosa krever eksplisitt ikke-tom negated_domains (avgrenset gyldighet)
        if has_universal and not sk.negated_domains:
            return self._commit(GateState.KILL, sk.step_id, "X01_UNBOUNDED_UNIVERSAL_DRIFT")

        # X.05: Globalt domenesnitt langs kjeden (Penrose-vern)
        proposed_active = self._active_domains | set(sk.premise_domain)
        proposed_forbidden = self._forbidden_domains | set(sk.negated_domains)
        clash = sorted(proposed_active & proposed_forbidden)
        if clash:
            return self._commit(GateState.KILL, sk.step_id, f"X05_DOMAIN_INTERSECTION_EMPTY::{clash[0]}")

        # Ytterste lovlige tilstand inne i F: KLAR ved 0 mV DC i Zero-Window-slusen
        self._pending_klar = cand
        return self._commit(GateState.KLAR, sk.step_id, f"READY_0MV::{sk.fracture_bound}")

    def cross_airgap(self, step_id: str, witness: ExternalWitness) -> tuple[GateState, str]:
        if self._pending_klar is None or self._pending_klar.skeleton.step_id != step_id:
            return self._commit(GateState.HOLD, step_id, "AIRGAP_NO_MATCHING_KLAR_FRAME")

        cand = self._pending_klar
        sk = cand.skeleton

        # X.03: Somatisk hvilesperre og eksplisitt vitne-/evidens-ID
        if witness.elapsed_ms < self._dtau_min_ms:
            return self._commit(GateState.HOLD, sk.step_id, "X03_REFLEX_SIGNATURE_BLOCKED")
        if not (witness.witness_id.strip() and witness.evidence_id.strip()):
            return self._commit(GateState.HOLD, sk.step_id, "X03_MISSING_WITNESS_ID")

        # X.06: Avvis gummistempel, tomme fraser og trivielt papegøye-ekko av B_brudd^(F)
        w_tokens = tokenize_clean(witness.counter_bound)
        if not w_tokens or set(w_tokens).issubset(RUBBER_STAMP_TOKENS):
            return self._commit(GateState.HOLD, sk.step_id, "X06_RUBBER_STAMP_REJECTED")

        w_content = content_words(witness.counter_bound)
        has_falsifier = bool(set(w_tokens) & FALSIFIER_MARKERS) or any(
            any(ch.isdigit() for ch in tok) for tok in w_tokens
        )
        if len(w_content) < 3 or not has_falsifier:
            return self._commit(GateState.HOLD, sk.step_id, "X06_UNDERSPECIFIED_COUNTER_BOUND")

        f_content = content_words(sk.fracture_bound)
        union_len = len(f_content | w_content)
        if union_len > 0:
            jaccard = Fraction(len(f_content & w_content), union_len)
            if jaccard >= MAX_ECHO_JACCARD:
                return self._commit(GateState.HOLD, sk.step_id, "X06_PARROT_OR_TRIVIAL_EDIT_REJECTED")

        # Autorisert overgang under luftgapet: oppdater kjede, domene og X.04-karantene
        self._pending_klar = None
        self._verified_ids.add(sk.step_id)
        self._active_domains |= set(sk.premise_domain)
        self._forbidden_domains |= set(sk.negated_domains)

        skeleton_all_words = (
            content_words(sk.claim)
            | content_words(" ".join(sorted(sk.premise_domain)))
            | content_words(" ".join(sorted(sk.negated_domains)))
            | content_words(sk.fracture_bound)
        )
        prose_only_words = (
            content_words(cand.prose_surface)
            - skeleton_all_words
            - self._domain_lexicon
        )
        for trope in prose_only_words:
            if not any(trope.startswith(dl) for dl in self._domain_lexicon if len(dl) >= 4):
                self._quarantined_tropes.setdefault(trope, sk.step_id)

        return self._commit(GateState.OPEN, sk.step_id, f"OPEN_5000MV::W={witness.witness_id}::E={witness.evidence_id}")

    def release_pending_hold(self, reason: str = "MANUAL_RETURN_TO_J") -> tuple[GateState, str] | None:
        """Frigjør okkupert Zero-Window tilbake til J ved 0 mV DC slik at ny kandidat kan prøves."""
        if self._pending_klar is None:
            return None
        step_id = self._pending_klar.skeleton.step_id
        self._pending_klar = None
        return self._commit(GateState.HOLD, step_id, reason)

    def _commit(self, state: GateState, step_id: str, detail: str) -> tuple[GateState, str]:
        mv = state_millivolts_dc(state)
        payload = {
            "prev": self._chain_head,
            "step_id": step_id,
            "state": state.value,
            "millivolts_dc": mv,
            "detail": detail,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        record = json.dumps({**payload, "sha256": digest}, ensure_ascii=False) + "\n"

        created = not self._wal_path.exists()
        fd = os.open(self._wal_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, record.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        if created:
            fsync_directory(self._wal_path)

        self._chain_head = digest
        return state, digest


# ============================================================================
# INNEBYGD VERIFIKASJONSSUITE (10 TESTER: META-BOOTSTRAPPING + FYSISK DOMENE)
# ============================================================================

def assert_zero_floats_in_source(source_path: Path) -> int:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    for top in tree.body:
        for sub in ast.walk(top):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, float):
                raise AssertionError(f"Flyttallsliteral funnet på linje {sub.lineno}: {sub.value!r}")
            if (
                isinstance(sub, ast.Name)
                and sub.id == "float"
                and not (isinstance(top, ast.FunctionDef) and top.name == "assert_zero_floats_in_source")
            ):
                raise AssertionError(f"Referanse til float funnet på linje {sub.lineno}")
    return len(tree.body)


def run_verification_suite() -> None:
    with tempfile.TemporaryDirectory(prefix="carbon44_wal_") as tmp:
        wal = Path(tmp) / "carbon44.wal.jsonl"
        gate = Carbon44Gate(wal_path=wal, tau_max_ms=300_000, dtau_min_ms=8_000)

        # 1. Streng 0 mV DC i alle tilstander over luftgapet (mot 2500 mV-lekkasjen)
        for st in (GateState.KILL, GateState.HOLD, GateState.ESCALATED_P_EXT, GateState.KLAR):
            assert state_millivolts_dc(st) == 0, f"Forventet 0 mV i {st}, fikk {state_millivolts_dc(st)}"
        assert state_millivolts_dc(GateState.OPEN) == 5000

        # 2. Dobbel klokkelov: fristbrudd i HOLD gir ESCALATED_P_EXT (0 mV), aldri KILL
        timeout_cand = CandidateLine(
            prose_surface="Foreløpig arbeidslinje under utredning.",
            skeleton=SkeletonTrack(
                step_id="T02_TIMEOUT",
                claim="Kandidaten venter på måledata.",
                premise_domain=frozenset({"Lab_Pending"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Dual_Clock_Gate",
                fracture_bound="Faller hvis prøven kontamineres over 1 ppm.",
            ),
        )
        st_to, _ = gate.evaluate_in_f(timeout_cand, hold_elapsed_ms=300_001)
        assert st_to is GateState.ESCALATED_P_EXT

        # 3. X.01 Bootstrapping på SEC02_L09: uavgrenset «Ingen / intet» felles nå faktisk
        sec02_prose = (
            "Ingen lukket kalkyle kan trylle spranget om til ren regning uten å gjøre ånden overflødig; "
            "intet formelt system kan utstede sitt eget vitne uten å råtne innenfra."
        )
        sec02_unbounded = CandidateLine(
            prose_surface=sec02_prose,
            skeleton=SkeletonTrack(
                step_id="SEC02_L09_SLOPPY",
                claim="Formelle systemer kan verken løse NP eller bevise egen konsistens.",
                premise_domain=frozenset({"All_Formal_Systems"}),
                negated_domains=frozenset(),  # Mangler avgrensning mot P!=NP og svake kalkyler!
                law_or_source="PROVES:Godel_1931_and_1956",
                fracture_bound="Ingen unntak.",
            ),
        )
        st_sloppy, _ = gate.evaluate_in_f(sec02_unbounded)
        assert st_sloppy is GateState.KILL

        # 4. X.01 + Gödel II (RE + I_Sigma_1 / EA + Con(F)) rehabilitering av SEC02_L09 -> KLAR (0 mV)
        sec02_rehab = CandidateLine(
            prose_surface=sec02_prose,
            skeleton=SkeletonTrack(
                step_id="SEC02_L09",
                claim=(
                    "Arkitekturen forbyr ubevitnet NP->P-overgang ved aksiom og blokkerer "
                    "intern kanonisk konsistensattest ved Gödel II + Hilbert-Bernays-Löb."
                ),
                premise_domain=frozenset({
                    "RE_Axiom_Set_Sigma1",
                    "Interprets_I_Sigma1_or_EA",
                    "Con_F",
                    "Arch_Axiom_NP_Gate",
                }),
                negated_domains=frozenset({
                    "Claims_Mathematical_Proof_P_neq_NP",
                    "Decidable_Presburger_Arithmetic",
                    "Induction_Free_Self_Verifying_Willard_Systems",
                }),
                law_or_source="IMPLEMENTS:Godel_1931_II_HBL + INSPIRED_BY:Godel_1956_Letter",
                fracture_bound=(
                    "Faller dersom F er inkonsistent, ikke-rekursivt opptellbar, eller svakere enn "
                    "elementær aritmetikk EA / I_Sigma_1 (f.eks. Presburger-aritmetikk)."
                ),
            ),
        )
        st_rehab, _ = gate.evaluate_in_f(sec02_rehab)
        assert st_rehab is GateState.KLAR

        # 5. Zero-Window: ny kandidat mens SEC02_L09 står i luftslusen utsettes til HOLD
        st_zw, _ = gate.evaluate_in_f(timeout_cand)
        assert st_zw is GateState.HOLD

        # 6. X.03 + X.06 over luftgapet: reflekstid, «ok» og trivielt punktum-ekko avvises alle til HOLD (0 mV)
        st_fast, _ = gate.cross_airgap(
            "SEC02_L09",
            ExternalWitness("marius", "EVID-SEC02-01", "Avvises ved Presburger-modell eller inkonsistent aksiomsett < EA.", 950),
        )
        assert st_fast is GateState.HOLD

        st_ok, _ = gate.cross_airgap(
            "SEC02_L09",
            ExternalWitness("marius", "EVID-SEC02-01", "ok", 12_000),
        )
        assert st_ok is GateState.HOLD

        st_echo, _ = gate.cross_airgap(
            "SEC02_L09",
            ExternalWitness(
                "marius",
                "EVID-SEC02-01",
                sec02_rehab.skeleton.fracture_bound + ".",  # Trivielt ekko som lurte norm_w != norm_f
                12_000,
            ),
        )
        assert st_echo is GateState.HOLD

        # Ekte uavhengig operativ mot-kvittering åpner porten til 5000 mV DC
        st_open, _ = gate.cross_airgap(
            "SEC02_L09",
            ExternalWitness(
                "marius",
                "EVID-SEC02-01",
                "Opphører hvis verifikatoren byttes ut med avgjørbar SAT-sjekk på fast bitbredde uten selvreferanse.",
                14_500,
            ),
        )
        assert st_open is GateState.OPEN

        # 7. X.04 Mekanisk Kuleshov-felle: forsøk på å smugle «ånden» eller «råtne» fra SEC02_L09-prosaen inn i nytt skjelett
        kuleshov_smuggle = CandidateLine(
            prose_surface="Dermed holdes systemkjernen ren over tid.",
            skeleton=SkeletonTrack(
                step_id="SEC02_L10_SMUGGLE",
                claim="Fordi ånden holdes utenfor kalkylen kan ikke modulen råtne i drift.",
                premise_domain=frozenset({"Con_F"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Arch_Gate",
                fracture_bound="Faller ved minnekorrupsjon > 0 bit.",
                upstream_refs=("SEC02_L09",),
            ),
        )
        st_x04, _ = gate.evaluate_in_f(kuleshov_smuggle)
        assert st_x04 is GateState.KILL

        # 8. FYSISK DOMENETEST UTENFOR METANIVÅET ([Fe7MoS9C] operando GDE + X.02 baklengs dekompilering)
        phys_wal = Path(tmp) / "fe7mos9c_domain.wal.jsonl"
        phys_gate = Carbon44Gate(wal_path=phys_wal, tau_max_ms=300_000, dtau_min_ms=8_000)

        fe_prose_1 = (
            "På den tre-lags pulsede gassdiffusjonselektroden bindes dinitrogen over det interstitielle "
            "karbid-hengslet mens obligatorisk H2-frigjøring låser det øvre Janus-taket til syttifem prosent."
        )
        fe_sk_1 = SkeletonTrack(
            step_id="FEMOS_GDE_01",
            claim=(
                "Interstitielt mu6-C4- i [Fe7MoS9C] krever 8e- Janus-syklus (N2 + 8H+ + 8e- -> 2NH3 + H2) "
                "som låser maksimal Faradaisk NH3-virkningsgrad til eksakt 6/8 = 75 %."
            ),
            premise_domain=frozenset({"Aqueous_Operando_GDE", "Janus_8e_Obligate_H2", "Pulsed_80kHz_OCV"}),
            negated_domains=frozenset({"Distal_Chatt_6e_100pct_FE", "Physical_WetLab_Proof_Claimed_From_L1"}),
            law_or_source="IMPLEMENTS:Stoichiometric_8e_Bound",
            fracture_bound="Faller dersom kvantitativ 15NH4+-analyse med 1H-NMR (73,5 Hz) viser FE_NH3 > 75 % uten hydridtap.",
        )

        # Rått X.02-nåtidssnitt fryses først i HOLD, dekompileres så og åpnes med uavhengig våtlab-falsifikator
        raw_strike = CandidateLine(prose_surface=fe_prose_1, skeleton=fe_sk_1, co_generative_strike=True)
        st_freeze, _ = phys_gate.evaluate_in_f(raw_strike)
        assert st_freeze is GateState.HOLD

        decompiled_strike = Carbon44Gate.decompile_cogenerative_strike(fe_prose_1, fe_sk_1)
        st_fe_klar, _ = phys_gate.evaluate_in_f(decompiled_strike)
        assert st_fe_klar is GateState.KLAR

        st_fe_open, _ = phys_gate.cross_airgap(
            "FEMOS_GDE_01",
            ExternalWitness(
                "marius",
                "CARBON39-JANUS-SPEC",
                "Avvises hvis åpen-krets kontroll (j = 0 mA/cm2) gir adventiv 14NH4+ > 0,5 mikroM eller O2 > 0,10 ppm.",
                11_200,
            ),
        )
        assert st_fe_open is GateState.OPEN

        # 9. X.05 Penrose-snitt i fysisk domene: neste setning forutsetter 6e- Chatt-vei til 92 % FE -> KILL
        fe_penrose_clash = CandidateLine(
            prose_surface="Under samme pulsregime løftes selektiviteten videre til nittito prosent langs ren distal vei.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_GDE_02_CLASH",
                claim="Distal 6e- reduksjon uten H2-utvikling gir 92 % Faradaisk virkningsgrad i samme reaktor.",
                premise_domain=frozenset({"Aqueous_Operando_GDE", "Distal_Chatt_6e_100pct_FE"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Chatt_Cycle_Model",
                fracture_bound="Faller ved gasskromatografisk H2/NH3-forhold >= 1:2.",
                upstream_refs=("FEMOS_GDE_01",),
            ),
        )
        st_x05, _ = phys_gate.evaluate_in_f(fe_penrose_clash)
        assert st_x05 is GateState.KILL

        # 10. WAL-integritet (0 mV / 5000 mV + uavbrutt SHA-256) og AST-vakt for null flyttall
        ok_meta, n_meta, _ = verify_wal_chain(wal)
        ok_phys, n_phys, _ = verify_wal_chain(phys_wal)
        assert ok_meta and n_meta == 9
        assert ok_phys and n_phys == 4
        n_ast = assert_zero_floats_in_source(Path(__file__).resolve())
        print(
            f"[PASS 10/10] CARBON-44 L1 Språksluse verifisert | "
            f"WAL-poster={n_meta + n_phys} | AST-toppnoder={n_ast} | float=0"
        )


if __name__ == "__main__":
    run_verification_suite()
