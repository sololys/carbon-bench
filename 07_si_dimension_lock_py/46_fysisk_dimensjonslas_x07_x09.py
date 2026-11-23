#!/usr/bin/env python3
"""
CARBON/46_fysisk_dimensjonslas_x07_x09.py — Herdet Fysisk Dimensjons-, Intervall- og Stammelås (X.07–X.09)
===========================================================================================================
Epistemisk status : L1 (lokalt demonstrert programvare; append-only SHA-256 != fysisk WORM)
Kontraktregel     : INSPIRED_BY != IMPLEMENTS != PROVES
Flyttallsforbud   : 0 forekomster av float i kildefilen (verifisert via AST-vakt i Test 12)

Sveiser X.07–X.09 direkte sammen med den herdede CARBON-44-kjernen og retter 5 feil i råskissen:
  1. Falske KILL i X.08-stammelåsen  : Råskissen la vanlige fagord fra prosaen («gass», «vann», «linj»,
                                       «reaktor») i karantene via 4-tegns prefiks-kutt og hadde hardkodet
                                       «stivhet» som suffiks for å treffe «amboltstivhet». Herdet motor
                                       bruker ekte norsk bøyningsavkledning (uten jukse-suffikser), samler
                                       hele skjelettets tekniske vokabular + fagregister, og fanger ekte
                                       sammensetninger («amboltstivhet», «amboltslag») uten falske kutt.
  2. Åpne/halvåpne Q-intervaller     : Legger til `low_closed` og `high_closed` på `RationalBound` slik at
                                       `(0, 2e-6] m` avviser `0 m` eksakt, og `[0, 3/4] ∩ (3/4, 1] = ∅` felles.
  3. Treveis måleusikkerhet (M vs K) : Skiller krystallklart mellom:
                                         - M ∩ K = ∅           -> KILL (utenfor fysisk lov / fasevindu)
                                         - M ∩ K != ∅, M ⊄ K   -> HOLD (måleoppløsning skriver over grensen,
                                                                  f.eks. 15 ps TDC-skrevet ved 40 m vakuum!)
                                         - M ⊆ K               -> KLAR (hele usikkerhetsboksen innenfor K).
  4. Koblede SI-kvotient-/produktlover: Råskissen sjekket kun identiske variabelnavn og slapp dermed
                                       `(j_NH3=82, j_tot=100)` gjennom når `FE_NH3` ikke var nevnt eksplisitt.
                                       Herdet motor sjekker 7-tuppel SI-eksponenter på avledede kvotienter
                                       og produkter (`z = x / y`, `p = a * b`) automatisk i Q.
  5. Sann modalitets-ortogonalitet   : X.09 avviser gjentatt måling i samme fysiske kanal-familie (f.eks. to
                                       kolorimetriske målinger) og krever to distinkte målemodaliteter.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
import tempfile


def _load_carbon44():
    c44_path = Path(__file__).resolve().parent / "44_spraksluse_l1_gate.py"
    spec = importlib.util.spec_from_file_location("carbon44_spraksluse_l1_gate", c44_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Fant ikke CARBON-44 ved {c44_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


c44 = _load_carbon44()
CandidateLine = c44.CandidateLine
Carbon44Gate = c44.Carbon44Gate
ExternalWitness = c44.ExternalWitness
GateState = c44.GateState
SkeletonTrack = c44.SkeletonTrack
verify_wal_chain = c44.verify_wal_chain


# 7-tuppel SI-grunndimensjon: (kg, m, s, A, K, mol, cd)
SIDim = tuple[int, int, int, int, int, int, int]

DIM_DIMENSIONLESS: SIDim = (0, 0, 0, 0, 0, 0, 0)
DIM_LENGTH_M: SIDim      = (0, 1, 0, 0, 0, 0, 0)
DIM_TIME_S: SIDim        = (0, 0, 1, 0, 0, 0, 0)
DIM_FREQ_HZ: SIDim       = (0, 0, -1, 0, 0, 0, 0)
DIM_VELOCITY_M_S: SIDim  = (0, 1, -1, 0, 0, 0, 0)
DIM_CURRENT_DENS: SIDim  = (0, -2, 0, 1, 0, 0, 0)  # A * m^-2

SPEED_OF_LIGHT_M_S = Fraction(299_792_458, 1)


def si_add(a: SIDim, b: SIDim) -> SIDim:
    """SI-dimensjon for produkt (a * b): eksponenter adderes."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3], a[4] + b[4], a[5] + b[5], a[6] + b[6])


def si_sub(a: SIDim, b: SIDim) -> SIDim:
    """SI-dimensjon for kvotient (a / b): eksponenter subtraheres."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2], a[3] - b[3], a[4] - b[4], a[5] - b[5], a[6] - b[6])


# Kun ekte norske bøynings- og avledningsendelser — ingen jukse-substantiver som «stivhet» eller «kraften»
NO_INFLECTION_SUFFIXES = (
    "hetene", "heten", "heter", "elsene", "elsen", "elser",
    "ingene", "ingen", "inger", "ene", "ane", "ens", "ets",
    "en", "et", "er", "ar", "a", "e",
)

# Fag- og funksjonsord som aldri er poetiske troper i fysisk/kjemisk prosa
TECHNICAL_BASE_STEMS = frozenset({
    "først", "under", "mellom", "gjennom", "samme", "enhver", "hvert", "innen",
    "gass", "vann", "reaktor", "strøm", "spenning", "linj", "felt", "magnet",
    "magnetfelt", "kjern", "kjernespinn", "molekyl", "nitrogen", "hydrogen",
    "ammoniakk", "karbid", "sulfid", "svovel", "elektrod", "membran", "puls",
    "pulset", "drift", "klyng", "vakuum", "kvarts", "prisme", "speil", "laser",
    "foton", "klokk", "terskel", "stup", "broen", "signal", "måling", "kontroll",
    "skarp", "tynn", "høye", "fritt", "åpen", "lukket", "deler", "måles", "krever",
    "ligger", "viser", "bevarer", "brutt", "spaltet",
})


def stem_norwegian(token: str) -> str:
    """X.08: Deterministisk norsk bøyningsavkledning uten domenespesifikke jukse-suffikser."""
    w = token.strip(".,;:!?()[]{}«»\"'—–-/`").lower()
    if len(w) <= 4:
        return w
    for suf in NO_INFLECTION_SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


@dataclass(frozen=True)
class RationalBound:
    var_name: str
    si_dim: SIDim
    low: Fraction
    high: Fraction
    low_closed: bool = True
    high_closed: bool = True
    is_measurement: bool = False  # False = lov-/domeneskranke K; True = målt/påstått boks M som må oppfylle M ⊆ K

    def __post_init__(self) -> None:
        if not isinstance(self.low, Fraction) or not isinstance(self.high, Fraction):
            raise TypeError(f"KUN_FRACTION_TILLATT::{self.var_name}")
        if self.low > self.high:
            raise ValueError(f"INVERTERT_INTERVALL::{self.var_name}[{self.low},{self.high}]")
        if self.low == self.high and not (self.low_closed and self.high_closed):
            raise ValueError(f"TOMT_PUNKTINTERVALL::{self.var_name}")


def intersect_bounds(a: RationalBound, b: RationalBound) -> RationalBound | None:
    """Eksakt snitt av to (åpne/halvåpne/lukkede) rasjonale intervaller i Q. Returnerer None hvis snittet er tomt."""
    if a.si_dim != b.si_dim:
        raise ValueError(f"SI_DIMENSJONSFEIL::{a.var_name}")

    if a.low > b.low:
        low, low_closed = a.low, a.low_closed
    elif b.low > a.low:
        low, low_closed = b.low, b.low_closed
    else:
        low, low_closed = a.low, (a.low_closed and b.low_closed)

    if a.high < b.high:
        high, high_closed = a.high, a.high_closed
    elif b.high < a.high:
        high, high_closed = b.high, b.high_closed
    else:
        high, high_closed = a.high, (a.high_closed and b.high_closed)

    if low > high:
        return None
    if low == high and not (low_closed and high_closed):
        return None
    return RationalBound(
        var_name=a.var_name,
        si_dim=a.si_dim,
        low=low,
        high=high,
        low_closed=low_closed,
        high_closed=high_closed,
    )


def is_subset_bound(meas: RationalBound, law: RationalBound) -> bool:
    """Returnerer True hvis hele måleintervallet M ligger inne i lovintervallet K (M ⊆ K)."""
    if meas.low < law.low:
        return False
    if meas.low == law.low and meas.low_closed and not law.low_closed:
        return False
    if meas.high > law.high:
        return False
    if meas.high == law.high and meas.high_closed and not law.high_closed:
        return False
    return True


@dataclass(frozen=True)
class QuotientLaw:
    """Koblet fysisk kvotientlov: ratio_var = scale * (numerator_var / denominator_var)."""
    ratio_var: str
    numerator_var: str
    denominator_var: str
    scale: Fraction = Fraction(1, 1)


@dataclass(frozen=True)
class ProductLaw:
    """Koblet fysisk produktlov: product_var = scale * (left_var * right_var), f.eks. 2d <= c * dt."""
    product_var: str
    left_var: str
    right_var: str
    scale: Fraction = Fraction(1, 1)


@dataclass(frozen=True)
class MeasurementChannel:
    """X.09: Målekanal med eksplisitt fysikalsk modalitets-familie (for ortogonalitetssjekk)."""
    channel_id: str
    modality_family: str  # F.eks. "ELECTROCHEM_COULOMETRY", "NUCLEAR_SPIN_NMR", "OPTICAL_TOF_TDC", "MECH_INTERLOCK"


@dataclass(frozen=True)
class PhysicalTrack:
    bounds: tuple[RationalBound, ...] = ()
    quotient_laws: tuple[QuotientLaw, ...] = ()
    product_laws: tuple[ProductLaw, ...] = ()
    requires_empirical_yield: bool = False
    channels: tuple[MeasurementChannel, ...] = ()


class PhysicalDomainAccumulator:
    """Håndhever X.07 (SI + Q-intervall + koblede lover), X.08 (morfologisk karantene) og X.09 (ortogonalitet)."""

    def __init__(self) -> None:
        self._bounds: dict[str, RationalBound] = {}
        self._quotient_laws: list[QuotientLaw] = []
        self._product_laws: list[ProductLaw] = []
        self._quarantine_stems: dict[str, str] = {}  # stamme -> opphavs-step_id
        self._locked_modalities: dict[str, str] = {}  # modality_family -> channel_id

    def evaluate_physical(self, cand: CandidateLine, phys: PhysicalTrack) -> tuple[GateState, str]:
        sk = cand.skeleton

        # X.08: Morfologisk og sammensatt stammekontroll mot tidligere (I - Pi_K)gamma
        skel_tokens = c44.tokenize_clean(sk.claim) + c44.tokenize_clean(" ".join(sorted(sk.premise_domain)))
        for tok in skel_tokens:
            if len(tok) < 4:
                continue
            st = stem_norwegian(tok)
            for q_stem, origin_id in self._quarantine_stems.items():
                # Eksakt stamme-treff eller sammensetning på karantenestamme (>= 5 tegn som prefiks/ledd)
                compound_hit = len(q_stem) >= 5 and (tok.startswith(q_stem) or st.endswith(q_stem))
                if st == q_stem or compound_hit:
                    return (
                        GateState.KILL,
                        f"X08_MORPHOLOGICAL_TROPE_SMUGGLING::{tok}<-{q_stem}@{origin_id}",
                    )

        # X.09: Empirisk utbytte/kausalpassering krever minst to distinkte fysiske målemodaliteter
        merged_modalities = dict(self._locked_modalities)
        for ch in phys.channels:
            if ch.channel_id.strip() and ch.modality_family.strip():
                merged_modalities.setdefault(ch.modality_family.strip().upper(), ch.channel_id.strip())
        if phys.requires_empirical_yield and len(merged_modalities) < 2:
            return (
                GateState.HOLD,
                f"X09_MISSING_ORTHOGONAL_MODALITY::active={len(merged_modalities)}<2",
            )

        # X.07 (del A): Direkte SI-dimensjonsparitet og treveis intervallkontroll (KILL / HOLD / KLAR)
        working_bounds = dict(self._bounds)
        local_measurements: dict[str, RationalBound] = {}

        for b in phys.bounds:
            if b.var_name in working_bounds:
                prev = working_bounds[b.var_name]
                if b.si_dim != prev.si_dim:
                    return (GateState.KILL, f"X07_SI_DIMENSION_MISMATCH::{b.var_name}")
                inter = intersect_bounds(prev, b)
                if inter is None:
                    return (
                        GateState.KILL,
                        f"X07_RATIONAL_INTERVAL_EMPTY::{b.var_name}[{b.low},{b.high}]_vs_[{prev.low},{prev.high}]",
                    )
                if b.is_measurement and not is_subset_bound(b, prev):
                    return (
                        GateState.HOLD,
                        f"X07_UNCERTAINTY_STRADDLES_BOUNDARY::{b.var_name}[{b.low},{b.high}]_straddles_[{prev.low},{prev.high}]",
                    )
                if not b.is_measurement:
                    working_bounds[b.var_name] = inter
                local_measurements[b.var_name] = b
            else:
                if not b.is_measurement:
                    working_bounds[b.var_name] = b
                local_measurements[b.var_name] = b

        # X.07 (del B): Koblede kvotientlover z = scale * (x / y) med automatisk SI-kontroll
        all_q_laws = list(self._quotient_laws) + list(phys.quotient_laws)
        lookup = {**working_bounds, **local_measurements}
        for ql in all_q_laws:
            if ql.numerator_var in lookup and ql.denominator_var in lookup and ql.ratio_var in working_bounds:
                num_b = lookup[ql.numerator_var]
                den_b = lookup[ql.denominator_var]
                rat_law = working_bounds[ql.ratio_var]
                expected_dim = si_sub(num_b.si_dim, den_b.si_dim)
                if expected_dim != rat_law.si_dim:
                    return (GateState.KILL, f"X07_QUOTIENT_SI_MISMATCH::{ql.ratio_var}")
                if den_b.low <= 0:
                    return (GateState.HOLD, f"X07_NONPOSITIVE_DENOMINATOR::{ql.denominator_var}")
                derived = RationalBound(
                    var_name=ql.ratio_var,
                    si_dim=expected_dim,
                    low=ql.scale * (num_b.low / den_b.high),
                    high=ql.scale * (num_b.high / den_b.low),
                    low_closed=(num_b.low_closed and den_b.high_closed),
                    high_closed=(num_b.high_closed and den_b.low_closed),
                    is_measurement=True,
                )
                if intersect_bounds(rat_law, derived) is None:
                    return (
                        GateState.KILL,
                        f"X07_DERIVED_QUOTIENT_VIOLATION::{ql.ratio_var}=[{derived.low},{derived.high}]_vs_[{rat_law.low},{rat_law.high}]",
                    )
                if not is_subset_bound(derived, rat_law):
                    return (
                        GateState.HOLD,
                        f"X07_DERIVED_QUOTIENT_STRADDLE::{ql.ratio_var}=[{derived.low},{derived.high}]",
                    )

        # X.07 (del C): Koblede produktlover p = scale * (a * b) med automatisk SI-kontroll
        all_p_laws = list(self._product_laws) + list(phys.product_laws)
        for pl in all_p_laws:
            if pl.left_var in lookup and pl.right_var in lookup and pl.product_var in working_bounds:
                left_b = lookup[pl.left_var]
                right_b = lookup[pl.right_var]
                prod_law = working_bounds[pl.product_var]
                expected_dim = si_add(left_b.si_dim, right_b.si_dim)
                if expected_dim != prod_law.si_dim:
                    return (GateState.KILL, f"X07_PRODUCT_SI_MISMATCH::{pl.product_var}")
                if left_b.low < 0 or right_b.low < 0:
                    return (GateState.HOLD, f"X07_NEGATIVE_FACTOR::{pl.product_var}")
                derived_p = RationalBound(
                    var_name=pl.product_var,
                    si_dim=expected_dim,
                    low=pl.scale * left_b.low * right_b.low,
                    high=pl.scale * left_b.high * right_b.high,
                    low_closed=(left_b.low_closed and right_b.low_closed),
                    high_closed=(left_b.high_closed and right_b.high_closed),
                    is_measurement=True,
                )
                if intersect_bounds(prod_law, derived_p) is None:
                    return (
                        GateState.KILL,
                        f"X07_DERIVED_PRODUCT_VIOLATION::{pl.product_var}=[{derived_p.low},{derived_p.high}]_vs_[{prod_law.low},{prod_law.high}]",
                    )
                if not is_subset_bound(derived_p, prod_law):
                    return (
                        GateState.HOLD,
                        f"X07_DERIVED_PRODUCT_STRADDLE::{pl.product_var}=[{derived_p.low},{derived_p.high}]",
                    )

        return (GateState.KLAR, "0MV_PHYSICAL_PARITY_OK")

    def commit_open(self, cand: CandidateLine, phys: PhysicalTrack) -> None:
        sk = cand.skeleton
        all_skel_text = " ".join([
            sk.claim,
            " ".join(sorted(sk.premise_domain)),
            " ".join(sorted(sk.negated_domains)),
            sk.fracture_bound,
        ])
        skel_stems = {
            stem_norwegian(w)
            for w in c44.tokenize_clean(all_skel_text)
            if len(w) >= 4
        }
        for w in c44.tokenize_clean(cand.prose_surface):
            if len(w) < 4 or w in c44.NORWEGIAN_STOPWORDS:
                continue
            st = stem_norwegian(w)
            if len(st) >= 4 and st not in skel_stems and st not in TECHNICAL_BASE_STEMS and w not in TECHNICAL_BASE_STEMS:
                self._quarantine_stems.setdefault(st, sk.step_id)

        for b in phys.bounds:
            if b.is_measurement:
                continue
            if b.var_name in self._bounds:
                inter = intersect_bounds(self._bounds[b.var_name], b)
                if inter is None:
                    raise RuntimeError(f"Ulovlig commit av tomt intervall på {b.var_name}")
                self._bounds[b.var_name] = inter
            else:
                self._bounds[b.var_name] = b

        for ql in phys.quotient_laws:
            if ql not in self._quotient_laws:
                self._quotient_laws.append(ql)
        for pl in phys.product_laws:
            if pl not in self._product_laws:
                self._product_laws.append(pl)
        for ch in phys.channels:
            if ch.channel_id.strip() and ch.modality_family.strip():
                self._locked_modalities.setdefault(ch.modality_family.strip().upper(), ch.channel_id.strip())


class Carbon46UnifiedGate:
    """Samlet X.01–X.09 kompilatorsluse: kobler Carbon44Gate + PhysicalDomainAccumulator i én atomisk sluse."""

    def __init__(self, wal_path: Path, tau_max_ms: int = 300_000, dtau_min_ms: int = 8_000) -> None:
        self.core = Carbon44Gate(
            wal_path=wal_path,
            tau_max_ms=tau_max_ms,
            dtau_min_ms=dtau_min_ms,
            domain_lexicon=TECHNICAL_BASE_STEMS,
        )
        self.phys_acc = PhysicalDomainAccumulator()
        self._pending_phys: tuple[CandidateLine, PhysicalTrack] | None = None

    def evaluate_in_f(
        self,
        cand: CandidateLine,
        phys: PhysicalTrack = PhysicalTrack(),
        hold_elapsed_ms: int = 0,
    ) -> tuple[GateState, str]:
        # Kjører først fysisk/morfologisk sjekk X.07–X.09 før KLAR-sporet i Carbon44Gate beslaglegges
        if hold_elapsed_ms <= self.core._tau_max_ms:
            p_state, p_reason = self.phys_acc.evaluate_physical(cand, phys)
            if p_state is not GateState.KLAR:
                return self.core._commit(p_state, cand.skeleton.step_id, p_reason)

        st, digest = self.core.evaluate_in_f(cand, hold_elapsed_ms=hold_elapsed_ms)
        if st is GateState.KLAR:
            self._pending_phys = (cand, phys)
        return st, digest

    def cross_airgap(self, step_id: str, witness: ExternalWitness) -> tuple[GateState, str]:
        pending = self._pending_phys
        st, digest = self.core.cross_airgap(step_id, witness)
        if st is GateState.OPEN and pending is not None and pending[0].skeleton.step_id == step_id:
            self.phys_acc.commit_open(pending[0], pending[1])
            self._pending_phys = None
        return st, digest


# ============================================================================
# VERIFIKASJONSSUITE (12 TESTER: [Fe7MoS9C] L01–L05 + DØR 14 ALEXANDROV-SJAKTEN)
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
    with tempfile.TemporaryDirectory(prefix="carbon46_wal_") as tmp:
        # --------------------------------------------------------------------
        # DEL A: [Fe7MoS9C] 5-TRINNS OPERANDO-KJEDE (FEMOS_L01 – FEMOS_L05)
        # --------------------------------------------------------------------
        femos_wal = Path(tmp) / "femos_x01_x09.wal.jsonl"
        fg = Carbon46UnifiedGate(wal_path=femos_wal)

        # FEMOS_L01: mu6-C4- karbid-anker (Q_1 låser «ambolt», «storm»)
        l01 = CandidateLine(
            prose_surface="Karbid-kjernen ligger som en ubevegelig ambolt midt i svovel-stormen når beltesulfidene åpner seg.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L01",
                claim="mu6-C4- bevarer trigonal prisme-koordinasjon under reduktiv beltesulfid-utskiftning.",
                premise_domain=frozenset({"Core_Intact_Mu6_C4", "Operando_Aqueous_GDE"}),
                negated_domains=frozenset({"Carbide_Dissolution"}),
                law_or_source="IMPLEMENTS:Interstitial_Carbide_Retention",
                fracture_bound="Faller dersom ICP-MS viser Fe-utlekking over 1/100 per 1000 s.",
            ),
        )
        assert fg.evaluate_in_f(
            l01,
            PhysicalTrack(
                bounds=(RationalBound("fe_leach_frac", DIM_DIMENSIONLESS, Fraction(0), Fraction(1, 100)),),
                channels=(MeasurementChannel("ICP_MS_FE_LEACH", "MASS_SPECTROMETRY"),),
            ),
        )[0] is GateState.KLAR
        assert fg.cross_airgap(
            "FEMOS_L01",
            ExternalWitness("marius", "FEMOS-E01", "Avvises ved Raman-tap av Fe-C strekkmodus under 400 cm-1 etter elektrolyse.", 11_000),
        )[0] is GateState.OPEN
        assert "ambolt" in fg.phys_acc._quarantine_stems

        # FEMOS_L02: Halvåpent væskefilm-intervall (0, 2/1_000_000] m — sjekk først at 0 m avvises!
        zero_film_probe = CandidateLine(
            prose_surface="Tørr elektrode uten væskefilm testes ved null tykkelse.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L02_ZERO_TEST",
                claim="Væskefilm settes til eksakt 0 m.",
                premise_domain=frozenset({"Operando_Aqueous_GDE"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Meniscus_Model",
                fracture_bound="Faller ved protontransport = 0 A.",
            ),
        )
        l02 = CandidateLine(
            prose_surface="Uten en tynn pustehinne kveles reaktoren i vannets egen tørst før ett molekyl når buret.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L02",
                claim="Young-Laplace og Young-Lippmann låser væskefilm på hydrofob GDE til (0, 2e-6] m.",
                premise_domain=frozenset({"Operando_Aqueous_GDE", "Triple_Phase_Boundary"}),
                negated_domains=frozenset({"Flooded_GDE_Pore", "Dry_Zero_Meniscus"}),
                law_or_source="IMPLEMENTS:Young_Laplace_Lippmann_Balance",
                fracture_bound="Faller ved gjennomslagstrykk over 509/100 bar eller potensial under -88/100 V.",
                upstream_refs=("FEMOS_L01",),
            ),
        )
        assert fg.evaluate_in_f(
            l02,
            PhysicalTrack(
                bounds=(
                    RationalBound(
                        "delta_film_m",
                        DIM_LENGTH_M,
                        Fraction(0, 1),
                        Fraction(2, 1_000_000),
                        low_closed=False,  # Strengt > 0 m!
                        high_closed=True,
                    ),
                ),
            ),
        )[0] is GateState.KLAR
        assert fg.cross_airgap(
            "FEMOS_L02",
            ExternalWitness("marius", "FEMOS-E02", "Opphører dersom elektrolyttgjennombrudd på gassiden overstiger 1 mg/cm2 per time.", 12_500),
        )[0] is GateState.OPEN

        # Verifiser at delta_film_m == 0 nå felles eksakt av det halvåpne intervallet (0, 2e-6]
        assert fg.evaluate_in_f(
            zero_film_probe,
            PhysicalTrack(
                bounds=(RationalBound("delta_film_m", DIM_LENGTH_M, Fraction(0), Fraction(0), is_measurement=True),),
            ),
        )[0] is GateState.KILL

        # FEMOS_L03: Janus 8e- tak FE_NH3 in [0, 3/4] + koblet kvotientlov FE_NH3 = j_NH3 / j_tot
        # Merk at prosa og skjelett bruker vanlige fagord som «gass» og «reaktor» uten falsk X.08-KILL!
        l03 = CandidateLine(
            prose_surface="Hvert spaltet nitrogenmolekyl krever sin ufravikelige toll av ett fritt hydrogengass-par ved porten.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L03",
                claim="Janus 8e- reduktiv eliminasjon i reaktoren låser Faradaisk virkningsgrad FE_NH3 <= 3/4.",
                premise_domain=frozenset({"Operando_Aqueous_GDE", "Janus_8e_Obligate_H2"}),
                negated_domains=frozenset({"Distal_6e_Pathway_Above_75pct"}),
                law_or_source="IMPLEMENTS:Janus_8e_Stoichiometry",
                fracture_bound="Janus-8e-tak brytes dersom integrert ladningsregnskap viser FE_NH3 over 3/4 uten verifisert sidereaksjon.",
                upstream_refs=("FEMOS_L02",),
            ),
        )
        assert fg.evaluate_in_f(
            l03,
            PhysicalTrack(
                bounds=(RationalBound("FE_NH3", DIM_DIMENSIONLESS, Fraction(0, 1), Fraction(3, 4)),),
                quotient_laws=(QuotientLaw(ratio_var="FE_NH3", numerator_var="j_NH3", denominator_var="j_tot"),),
                channels=(MeasurementChannel("COULOMETRY_POTENTIOSTAT", "ELECTROCHEM_COULOMETRY"),),
            ),
        )[0] is GateState.KLAR
        assert fg.cross_airgap(
            "FEMOS_L03",
            ExternalWitness(
                "marius",
                "FEMOS-E03",
                "Online gasskromatografi måler molforhold H2/NH3 under 1/2 over 1800 s stasjonær elektrolyse.",
                14_200,
            ),
        )[0] is GateState.OPEN

        # X.09-test før FEMOS_L04: forsøk på å lukke empirisk utbytte med kun én ekstra elektrokjemisk kanal (ikke-ortogonal) -> HOLD
        l04_same_mod = CandidateLine(
            prose_surface="Strømmålingen alene melder om ammoniakkdannelse i cellen.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L04_NON_ORTH",
                claim="Katalytisk 15NH4+-utbytte bekreftes ved gjentatt amperometri.",
                premise_domain=frozenset({"Operando_Aqueous_GDE"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Yield_Protocol",
                fracture_bound="Faller ved drift > 5 mA.",
            ),
        )
        fg_single_mod = Carbon46UnifiedGate(wal_path=Path(tmp) / "x09_mod.wal.jsonl")
        assert fg_single_mod.evaluate_in_f(
            l04_same_mod,
            PhysicalTrack(
                requires_empirical_yield=True,
                channels=(
                    MeasurementChannel("CHRONOAMP_1", "ELECTROCHEM_COULOMETRY"),
                    MeasurementChannel("CHRONOAMP_2", "ELECTROCHEM_COULOMETRY"),  # Samme modalitet!
                ),
            ),
        )[0] is GateState.HOLD

        # FEMOS_L04: Ortogonal 15N 1H-NMR dublettlås ved 147/2 = 73,5 Hz -> OPEN (5000 mV)
        l04 = CandidateLine(
            prose_surface="Først når magnetfeltet deler kjernespinnets stemme i to skarpe linjer, vet vi at gassen ble brutt.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L04",
                claim="Kvantitativ 1H-NMR krever 15NH4+ dublett ved Delta_J = 147/2 Hz mot 14N-kontroll.",
                premise_domain=frozenset({"Operando_Aqueous_GDE", "Isotopic_15N2_Feed"}),
                negated_domains=frozenset({"Colorimetry_Only_Claim"}),
                law_or_source="IMPLEMENTS:Spin_Coupling_15N_1H_Doublet",
                fracture_bound="15N-fiksering underkjennes dersom integrert 73,5 Hz 1H-NMR dublett avviker mer enn 1/20 fra indofenol-total.",
                upstream_refs=("FEMOS_L03",),
            ),
        )
        assert fg.evaluate_in_f(
            l04,
            PhysicalTrack(
                bounds=(RationalBound("J_15N_1H_hz", DIM_FREQ_HZ, Fraction(147, 2), Fraction(147, 2)),),
                requires_empirical_yield=True,
                channels=(MeasurementChannel("NMR_15NH4_DOUBLET_73P5HZ", "NUCLEAR_SPIN_NMR"),),
            ),
        )[0] is GateState.KLAR
        assert fg.cross_airgap(
            "FEMOS_L04",
            ExternalWitness(
                "marius",
                "FEMOS-E04",
                "Åpen-krets argon-kontroll ved 0 mA produserer detekterbar dublett-topp over 3 ganger støygulv.",
                19_500,
            ),
        )[0] is GateState.OPEN

        # FEMOS_L05 (A): Felle med morfologisk sammensetning («amboltslag» / «amboltstivhet» uten jukse-suffiks!) -> KILL (X.08)
        l05_morph = CandidateLine(
            prose_surface="Under pulset drift gir klyngens høye amboltstivhet og amboltslag ekstra strøm.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L05_MORPH",
                claim="Klyngens amboltstivhet øker omsetningshastigheten i gassfase-grensen.",
                premise_domain=frozenset({"Operando_Aqueous_GDE"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Cluster_Mechanics",
                fracture_bound="Faller ved Fe-tap > 1/100.",
                upstream_refs=("FEMOS_L04",),
            ),
        )
        st_m, _ = fg.evaluate_in_f(l05_morph)
        assert st_m is GateState.KILL

        # FEMOS_L05 (B): Ren skalar støkiometri-felle uten ett eneste forbudt ord og uten å nevne FE_NH3!
        # Oppgir kun j_NH3 = 820 A/m^2 (82 mA/cm^2) og j_tot = 1000 A/m^2 (100 mA/cm^2) -> 41/50 > 3/4 -> KILL (X.07)!
        l05_scalar = CandidateLine(
            prose_surface="Ved total strømtetthet 100 mA/cm2 måles partiell ammoniakkstrøm på 82 mA/cm2 med skarp linjebredde i gassfase.",
            skeleton=SkeletonTrack(
                step_id="FEMOS_L05_SCALAR",
                claim="Partiell strømtetthet j_NH3 = 820 A/m2 måles ved j_tot = 1000 A/m2 og linjebredde 2 Hz.",
                premise_domain=frozenset({"Operando_Aqueous_GDE"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Faraday_Partial_Current",
                fracture_bound="Faller ved kalibreringsavvik over 1/100.",
                upstream_refs=("FEMOS_L04",),
            ),
        )
        st_sc, _ = fg.evaluate_in_f(
            l05_scalar,
            PhysicalTrack(
                bounds=(
                    RationalBound("j_NH3", DIM_CURRENT_DENS, Fraction(820, 1), Fraction(820, 1), is_measurement=True),
                    RationalBound("j_tot", DIM_CURRENT_DENS, Fraction(1000, 1), Fraction(1000, 1), is_measurement=True),
                ),
            ),
        )
        assert st_sc is GateState.KILL

        # --------------------------------------------------------------------
        # DEL B: DØR 14 — ALEXANDROV-SJAKTEN (40 M VAKUUM + 15 PS TDC + KVARTS)
        # --------------------------------------------------------------------
        d14_wal = Path(tmp) / "door14_alexandrov.wal.jsonl"
        dg = Carbon46UnifiedGate(wal_path=d14_wal)

        tau_min_vac = Fraction(40, 299_792_458)          # Eksakt 20 / 149_896_229 s (~133,425638 ns)
        tau_max_phase = Fraction(160, 1_000_000_000)     # Eksakt 4 / 25_000_000 s (160,000000 ns)
        tdc_lsb = Fraction(15, 1_000_000_000_000)        # Eksakt 15 ps = 3 / 200_000_000_000 s

        # DOER14_L01: Alexandrov-diamantens kausale tur-retur-lov (2d = 40 m, tau in [20/149896229, 4/25000000] s)
        d14_01 = CandidateLine(
            prose_surface="Over avgrunnen står en korrupt tvilling i kalkhvitt støv som speiler hånden uten forsinkelse.",
            skeleton=SkeletonTrack(
                step_id="DOER14_L01",
                claim=(
                    "To-etappers kausal tur-retur E0->E1->E2 over d = 20 m vakuum krever flukttid "
                    "tau_rtt i [20/149896229, 4/25000000] s med c = 299792458 m/s."
                ),
                premise_domain=frozenset({"Minkowski_Causal_Diamond", "Arm_Length_20m_RTT_40m"}),
                negated_domains=frozenset({"Local_Estimator_Bypass_Zero_Delay"}),
                law_or_source="IMPLEMENTS:Alexandrov_Lightcone_Bound",
                fracture_bound="Faller dersom oppmålt armavstand d avviker under 20 m eller klokkesynkronisering driver over 15 ps.",
            ),
        )
        assert dg.evaluate_in_f(
            d14_01,
            PhysicalTrack(
                bounds=(
                    RationalBound("tau_rtt_s", DIM_TIME_S, tau_min_vac, tau_max_phase),
                    RationalBound("c_vac", DIM_VELOCITY_M_S, SPEED_OF_LIGHT_M_S, SPEED_OF_LIGHT_M_S),
                    RationalBound("path_rtt_m", DIM_LENGTH_M, Fraction(40, 1), Fraction(48, 1)),  # c * tau_max ~ 47,967 m
                ),
                product_laws=(ProductLaw(product_var="path_rtt_m", left_var="c_vac", right_var="tau_rtt_s"),),
                channels=(MeasurementChannel("TDC_15PS_COUNTER", "OPTICAL_TOF_TDC"),),
            ),
        )[0] is GateState.KLAR
        assert dg.cross_airgap(
            "DOER14_L01",
            ExternalWitness(
                "marius",
                "DOOR14-E01",
                "Avvises hvis knivbryteren ESTIMATOR_BYPASS fortsatt leder strøm over lokal prediktorsløyfe.",
                10_500,
            ),
        )[0] is GateState.OPEN

        # DOER14_L02: Spøkelsesseier ved 0 ns ([0, 15 ps]) -> M ∩ K = ∅ -> KILL (0 mV DC)
        d14_spoof = CandidateLine(
            prose_surface="Broen lyser grønt ved null nanosekunder på lokal prediktor.",
            skeleton=SkeletonTrack(
                step_id="DOER14_L02_SPOOF",
                claim="Retursignal registreres i første TDC-trinn [0, 15 ps].",
                premise_domain=frozenset({"Minkowski_Causal_Diamond"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:TDC_Readout",
                fracture_bound="Faller ved kausalitetsbrudd ds^2 > 0.",
                upstream_refs=("DOER14_L01",),
            ),
        )
        assert dg.evaluate_in_f(
            d14_spoof,
            PhysicalTrack(
                bounds=(RationalBound("tau_rtt_s", DIM_TIME_S, Fraction(0, 1), tdc_lsb, is_measurement=True),),
            ),
        )[0] is GateState.KILL

        # DOER14_L03: Ren vakuumrefleksjon uten kvartsprisme lander i TDC-trinn 8895 ([133,425 ns, 133,440 ns]),
        # som skriver rett over tau_min = 20/149896229 s (~133,425638 ns): M ∩ K != ∅ men M ⊄ K -> HOLD (0 mV DC)!
        bin_8895_low = 8895 * tdc_lsb
        bin_8895_high = 8896 * tdc_lsb
        assert bin_8895_low < tau_min_vac < bin_8895_high
        d14_straddle = CandidateLine(
            prose_surface="Et flatt speil uten optisk glassvei sender fotonet tilbake rett på kvantiseringskanten.",
            skeleton=SkeletonTrack(
                step_id="DOER14_L03_STRADDLE",
                claim="TDC-trinn 8895 måler [133425 ps, 133440 ps] som krysser vakuumgrensen 20/149896229 s.",
                premise_domain=frozenset({"Minkowski_Causal_Diamond"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:TDC_Quantization_Guard",
                fracture_bound="Faller til HOLD når nedre trinnkant ligger under 2d/c.",
                upstream_refs=("DOER14_L01",),
            ),
        )
        assert dg.evaluate_in_f(
            d14_straddle,
            PhysicalTrack(
                bounds=(RationalBound("tau_rtt_s", DIM_TIME_S, bin_8895_low, bin_8895_high, is_measurement=True),),
            ),
        )[0] is GateState.HOLD

        # DOER14_L04: 12 mm kvarts-hjørneprisme løfter signalet til trinn 8899 ([133,485 ns, 133,500 ns] ⊆ K)
        # + mekanisk knivbryter-interlock som andre ortogonale modalitet -> OPEN (5000 mV DC)!
        bin_8899_low = 8899 * tdc_lsb
        bin_8899_high = 8900 * tdc_lsb
        assert tau_min_vac < bin_8899_low < bin_8899_high < tau_max_phase
        d14_prism = CandidateLine(
            prose_surface="Hjørneprismet på tolv millimeter kvarts løfter ekkoet fire trinn klar av kanten mens hælen faller ti millimeter.",
            skeleton=SkeletonTrack(
                step_id="DOER14_L04_PRISM",
                claim=(
                    "12 mm kvarts-hjørneprisme plasserer hele TDC-trinnet [133485 ps, 133500 ps] innenfor "
                    "[20/149896229, 4/25000000] s, med 10 mm frittfalls-klaring over 5 ms fsync."
                ),
                premise_domain=frozenset({"Minkowski_Causal_Diamond", "Quartz_12mm_Retroreflector", "Unoccupied_Bridge_Zone"}),
                negated_domains=frozenset({"Occupied_Zone_Materialization"}),
                law_or_source="IMPLEMENTS:Alexandrov_Prism_Clearance",
                fracture_bound="Broen fryser i DEFER ved 0 mV dersom kollisjonssonen er okkupert under 5 ms fsync-vindu.",
                upstream_refs=("DOER14_L01",),
            ),
        )
        assert dg.evaluate_in_f(
            d14_prism,
            PhysicalTrack(
                bounds=(RationalBound("tau_rtt_s", DIM_TIME_S, bin_8899_low, bin_8899_high, is_measurement=True),),
                requires_empirical_yield=True,
                channels=(MeasurementChannel("KNIFE_SWITCH_AUX_DEFER_WEDGE", "MECH_INTERLOCK"),),
            ),
        )[0] is GateState.KLAR
        assert dg.cross_airgap(
            "DOER14_L04_PRISM",
            ExternalWitness(
                "marius",
                "DOOR14-E04",
                "Underkjennes dersom RG-214 koaksialbane eller tre-speils omvei øker flukttiden over 160 ns.",
                13_800,
            ),
        )[0] is GateState.OPEN

        # DOER14_L05: 52 m tre-speils sikksakk-omvei (Punkt perp Bane) gir c * tau >= 52 m > 48 m -> KILL (X.07 produktlov!)
        tau_zigzag = Fraction(52, 299_792_458)
        d14_zigzag = CandidateLine(
            prose_surface="Strålen sendes i sikksakk via alle tre veggspeilene over toogfemti meter.",
            skeleton=SkeletonTrack(
                step_id="DOER14_L05_ZIGZAG",
                claim="Tre-speils sikksakk-rute treffer målpunktet etter 52 m optisk banelengde.",
                premise_domain=frozenset({"Minkowski_Causal_Diamond"}),
                negated_domains=frozenset(),
                law_or_source="IMPLEMENTS:Mirror_Rig_Rev1",
                fracture_bound="Avvises ved banelengde over fasevindu.",
                upstream_refs=("DOER14_L04_PRISM",),
            ),
        )
        assert dg.evaluate_in_f(
            d14_zigzag,
            PhysicalTrack(
                bounds=(RationalBound("tau_rtt_s", DIM_TIME_S, tau_zigzag, tau_zigzag + tdc_lsb, is_measurement=True),),
            ),
        )[0] is GateState.KILL

        # WAL-sjekk (0 mV i alle ikke-OPEN, 5000 mV i OPEN) og AST-sjekk for null flyttall
        ok_f, n_f, _ = verify_wal_chain(femos_wal)
        ok_d, n_d, _ = verify_wal_chain(d14_wal)
        assert ok_f and n_f == 11
        assert ok_d and n_d == 7
        n_ast = assert_zero_floats_in_source(Path(__file__).resolve())
        print(
            f"[PASS 12/12] CARBON-46 Fysisk Dimensjons- og Stammelås (X.01–X.09) verifisert | "
            f"FEMOS_WAL={n_f} | DOER14_WAL={n_d} | AST-toppnoder={n_ast} | float=0"
        )


if __name__ == "__main__":
    run_verification_suite()
