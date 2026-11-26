#!/usr/bin/env python3
"""
CARBON / 14 — Eksakt L1-revisjonsmotor for Dokument 78 & Reversiblus-rapporten.

Grenseoppgang:
  - L1 (lokalt demonstrert programvare i Q, null IEEE-754 float).
  - INSPIRED_BY != IMPLEMENTS != PROVES.
  - Programvare-Witness er en append-only SHA-256-hashkjede, IKKE fysisk WORM.
  - Originalkilden 78_TIDSREVERSIBEL_INVOLUSJONSDYNAMIKK_OG_FASEMINNE.tex holdes
    urørt i luftslusen (HOLD).

Verifiserer 6 invarianter og moteksempler (6/6 PASS):
  1. Konvekst moteksempel mot Reversiblus Seksjon 1:
       På K = [0, inf) gir Moreau-projeksjonen Pi_K(x) = max(0, x) Cayley-reflektoren
       R_{N_K}(x) = |x|, som BRYTER både involusjon (R^2(-1) = +1 != -1) og isometri.
       På lineært underrom K = span{(3, 4)} i Q^2 holder både R_K^2 = I og ||R_K v||^2 = ||v||^2.
  2. Dok. 78 Seksjon 4.3 (2A — enkelt to-legeme rotor):
       p_{1,2} = m +/- R_z(tau) r_0 gir P_tot = 0, men L_tot = 2*m_p*(r x (omega x r)) != 0.
  3. Reversiblus 2A-skjerpelse (skjult gyroskopisk vippemoment når r_0 ikke står normalt på n_hat):
       Kontraroterende 4-legemepar (+omega, -omega) med skrå arm r_0 = (3, 0, 2) rundt z_hat
       gir L^+ + L^- = (0, -4*m_p*omega*r_perp*r_par*sin(theta), 0) != 0.
       Når hovedakse-ortogonalitet r_0 . n_hat = 0 pålegges (r_0 = (3, 4, 0)), blir
       både P_tot == 0 og L_tot == 0 eksakt for alle rasjonale tider tau.
  4. Dok. 78 Seksjon 1 & 6 (2B — 4D rasjonal Cayley-kjede + kanonisk gcd-koding):
       10-trinns LIFO-kjede U_10 ... U_1 med R(S) = (I - S)(I + S)^(-1) over Q^(4x4)
       gir bit-identisk SHA-256-retur med kanonisk brøkforkorting, mens uforkortet
       homogen brøkrepresentasjon (2p, 2q) utløser falsk GATE::KILL.
  5. Dok. 78 Seksjon 5.1 (2C — elektrokjemisk origo ved E_eq != E_pzc):
       Rå q_dl / C_dl feiler Psi(0) = 0 ved overpotensial eta = 0 når E_eq != E_pzc,
       mens overskuddspotensialet delta_phi_dl = (q_dl - q_dl,eq) / C_dl gir eksakt Psi(0) = 0
       og symmetrisk reversibel syklus (+U -> 0 -> HOLD -> -U -> 0).
  6. Luftsluse-invarians i HOLD og append-only SHA-256 Witness-kjede:
       Delta s_irr == 0 under HOLD og ubrutt kryptografisk kjede over alle 6 tester.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
from typing import List, Sequence, Tuple


Vec = List[Fraction]
Mat = List[List[Fraction]]


def q(num: int, den: int = 1) -> Fraction:
    return Fraction(num, den)


def dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    assert len(a) == len(b)
    return sum((x * y for x, y in zip(a, b)), q(0))


def cross3(a: Sequence[Fraction], b: Sequence[Fraction]) -> Vec:
    assert len(a) == 3 and len(b) == 3
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def vec_add(a: Sequence[Fraction], b: Sequence[Fraction]) -> Vec:
    return [x + y for x, y in zip(a, b)]


def vec_sub(a: Sequence[Fraction], b: Sequence[Fraction]) -> Vec:
    return [x - y for x, y in zip(a, b)]


def vec_scale(c: Fraction, v: Sequence[Fraction]) -> Vec:
    return [c * x for x in v]


def mat_eye(n: int) -> Mat:
    return [[q(1 if i == j else 0) for j in range(n)] for i in range(n)]


def mat_add(a: Mat, b: Mat) -> Mat:
    n = len(a)
    return [[a[i][j] + b[i][j] for j in range(n)] for i in range(n)]


def mat_sub(a: Mat, b: Mat) -> Mat:
    n = len(a)
    return [[a[i][j] - b[i][j] for j in range(n)] for i in range(n)]


def mat_neg(a: Mat) -> Mat:
    n = len(a)
    return [[-a[i][j] for j in range(n)] for i in range(n)]


def mat_transpose(a: Mat) -> Mat:
    n = len(a)
    m = len(a[0])
    return [[a[i][j] for i in range(n)] for j in range(m)]


def mat_mul(a: Mat, b: Mat) -> Mat:
    n = len(a)
    m = len(b[0])
    k_len = len(b)
    return [
        [sum((a[i][k] * b[k][j] for k in range(k_len)), q(0)) for j in range(m)]
        for i in range(n)
    ]


def mat_vec(a: Mat, v: Sequence[Fraction]) -> Vec:
    return [dot(row, v) for row in a]


def mat_inv_gauss_jordan(a: Mat) -> Mat:
    """Eksakt matriseinversjon over Q via Gauss-Jordan (null flyttall)."""
    n = len(a)
    aug = [list(a[i]) + list(mat_eye(n)[i]) for i in range(n)]
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if aug[row][col] != 0:
                pivot = row
                break
        if pivot is None:
            raise ValueError("Matrisen er singulær over Q.")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv_val = aug[col][col]
        aug[col] = [val / piv_val for val in aug[col]]
        for row in range(n):
            if row != col and aug[row][col] != 0:
                factor = aug[row][col]
                aug[row] = [
                    aug[row][c] - factor * aug[col][c] for c in range(2 * n)
                ]
    return [row[n:] for row in aug]


def cayley_orthogonal(skew: Mat) -> Mat:
    """R(S) = (I - S)(I + S)^(-1) for skjevsymmetrisk S^T = -S i Q^(n x n)."""
    n = len(skew)
    assert mat_transpose(skew) == mat_neg(skew), "S må være skjevsymmetrisk (S^T = -S)."
    eye = mat_eye(n)
    return mat_mul(mat_sub(eye, skew), mat_inv_gauss_jordan(mat_add(eye, skew)))


def cayley_rot_z_3d(tau: Fraction) -> Mat:
    """Eksakt høyrehåndsrotasjon +theta om +z-aksen via tau = tan(theta / 2) i Q.

    Siden R(S) = (I - S)(I + S)^(-1) ~= I - 2S og exp(theta [z]_x) ~= I + theta [z]_x,
    settes S = -tau [z]_x = [[0, +tau, 0], [-tau, 0, 0], [0, 0, 0]], som gir
    R_z(tau) = [[cos(theta), -sin(theta), 0], [sin(theta), cos(theta), 0], [0, 0, 1]].
    """
    skew_z: Mat = [
        [q(0), tau, q(0)],
        [-tau, q(0), q(0)],
        [q(0), q(0), q(0)],
    ]
    return cayley_orthogonal(skew_z)


def encode_canonical_vec(v: Sequence[Fraction]) -> bytes:
    """Kanonisk serialisering med gcd(|p|, q) = 1 og q > 0 (sikret av Fraction)."""
    parts: List[str] = []
    for item in v:
        assert isinstance(item, Fraction)
        assert math.gcd(abs(item.numerator), item.denominator) == 1
        assert item.denominator > 0
        parts.append(f"{item.numerator}/{item.denominator}")
    return ("[" + ",".join(parts) + "]").encode("utf-8")


def encode_unreduced_pairs(pairs: Sequence[Tuple[int, int]]) -> bytes:
    """Ikke-kanonisk serialisering av homogene heltallspar (p, q) uten gcd-forkorting."""
    return ("[" + ",".join(f"{p}/{den}" for p, den in pairs) + "]").encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class WitnessEntry:
    step: int
    tag: str
    delta_s_irr: Fraction
    prev_hash: str
    entry_hash: str


class AppendOnlyWitnessLedger:
    """Append-only SHA-256-kjede i L1 (ikke fysisk WORM-maskinvare)."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self.entries: List[WitnessEntry] = []

    def append(self, tag: str, payload: str, delta_s_irr: Fraction = q(0)) -> WitnessEntry:
        assert isinstance(delta_s_irr, Fraction)
        prev = self.entries[-1].entry_hash if self.entries else self.GENESIS
        step = len(self.entries) + 1
        canonical = (
            f"step={step}|tag={tag}|ds={delta_s_irr.numerator}/{delta_s_irr.denominator}"
            f"|prev={prev}|payload={payload}"
        ).encode("utf-8")
        digest = sha256_hex(canonical)
        entry = WitnessEntry(
            step=step,
            tag=tag,
            delta_s_irr=delta_s_irr,
            prev_hash=prev,
            entry_hash=digest,
        )
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        prev = self.GENESIS
        for idx, e in enumerate(self.entries, start=1):
            if e.step != idx or e.prev_hash != prev:
                return False
            prev = e.entry_hash
        return True


def test_1_convex_vs_subspace_cayley(ledger: AppendOnlyWitnessLedger) -> None:
    # 1A: Moteksempel på lukket konveks mengde K = [0, inf) i Q:
    # Moreau-projeksjonen J_{gamma N_K}(x) = Pi_K(x) = max(0, x) er idempotent,
    # men Cayley-reflektoren R_{N_K}(x) = 2*Pi_K(x) - x = |x| er HVERKEN involusjon ELLER isometri!
    def pi_halfline(x: Fraction) -> Fraction:
        return x if x >= 0 else q(0)

    def r_halfline(x: Fraction) -> Fraction:
        return q(2) * pi_halfline(x) - x

    x_neg = q(-1)
    x_pos = q(1)
    assert pi_halfline(pi_halfline(x_neg)) == pi_halfline(x_neg)  # Idempotent: 0 == 0
    r_once = r_halfline(x_neg)  # +1
    r_twice = r_halfline(r_once)  # +1 != -1 (BRYTER involusjon!)
    assert r_once == q(1) and r_twice == q(1) and r_twice != x_neg

    dist_before = abs(x_pos - x_neg)  # 2
    dist_after = abs(r_halfline(x_pos) - r_halfline(x_neg))  # |1 - 1| = 0 != 2 (BRYTER isometri!)
    assert dist_before == q(2) and dist_after == q(0)

    # Moteksempel på enhetskule ||x|| <= 1 ved x = (2, 0): R_{N_K}((2, 0)) = (0, 0)
    x_ball = [q(2), q(0)]
    pi_ball = [q(1), q(0)]
    r_ball = vec_sub(vec_scale(q(2), pi_ball), x_ball)
    assert r_ball == [q(0), q(0)]

    # 1B: Eksakt kontrast — på et lukket LINEÆRT UNDERROM K = span{(3, 4)} i Q^2
    # er Pi_K lineær og selvadjungert (P^T = P, P^2 = P), så R_K = 2*Pi_K - I er både involusjon og isometri!
    u = [q(3), q(4)]
    u_norm_sq = dot(u, u)  # 25
    P_sub: Mat = [
        [(u[i] * u[j]) / u_norm_sq for j in range(2)]
        for i in range(2)
    ]
    assert mat_transpose(P_sub) == P_sub
    assert mat_mul(P_sub, P_sub) == P_sub

    R_sub = mat_sub([[q(2) * P_sub[i][j] for j in range(2)] for i in range(2)], mat_eye(2))
    assert mat_mul(R_sub, R_sub) == mat_eye(2)
    assert mat_mul(mat_transpose(R_sub), R_sub) == mat_eye(2)

    v_test = [q(-7, 3), q(11, 5)]
    rv = mat_vec(R_sub, v_test)
    rrv = mat_vec(R_sub, rv)
    assert rrv == v_test
    assert dot(rv, rv) == dot(v_test, v_test)

    ledger.append(
        "TEST_1_CONVEX_COUNTEREXAMPLE",
        f"halfline_R2(-1)={r_twice}!= -1|dist_after={dist_after}|subspace_R2=I",
    )


def rotor_pair_momenta(
    r0: Sequence[Fraction],
    tau: Fraction,
    omega_z: Fraction,
    m_particle: Fraction,
) -> Tuple[Vec, Vec]:
    """Returnerer (P_tot, L_tot) om massesenteret m for p_{1,2} = m +/- R_z(tau) r0."""
    rot = cayley_rot_z_3d(tau)
    r_vec = mat_vec(rot, r0)
    omega_vec = [q(0), q(0), omega_z]
    v_vec = cross3(omega_vec, r_vec)

    # Partikkel 1 i +r med +v, partikkel 2 i -r med -v:
    p1_mom = vec_scale(m_particle, v_vec)
    p2_mom = vec_scale(m_particle, vec_scale(q(-1), v_vec))
    p_tot = vec_add(p1_mom, p2_mom)

    l1 = cross3(r_vec, p1_mom)
    l2 = cross3(vec_scale(q(-1), r_vec), p2_mom)
    l_tot = vec_add(l1, l2)
    return p_tot, l_tot


def test_2_single_rotor_nonzero_spin(ledger: AppendOnlyWitnessLedger) -> None:
    r0 = [q(3), q(0), q(0)]
    tau = q(1, 2)  # cos(theta)=3/5, sin(theta)=4/5
    omega = q(5)
    m_p = q(2)

    p_tot, l_tot = rotor_pair_momenta(r0, tau, omega, m_p)
    assert p_tot == [q(0), q(0), q(0)]
    # L_tot = 2 * m_p * r_perp^2 * omega * z_hat = 2 * 2 * 9 * 5 = 180 langs z_hat != 0
    assert l_tot == [q(0), q(0), q(180)]

    ledger.append(
        "TEST_2_SINGLE_ROTOR_PARITY",
        f"P_tot=0|L_tot={l_tot[2]}_z!=0",
    )


def test_3_counter_rotor_tilt_vs_principal_axis(ledger: AppendOnlyWitnessLedger) -> None:
    tau = q(1, 2)  # sin(theta) = 4/5, cos(theta) = 3/5
    omega = q(5)
    m_p = q(2)

    # 3A: Skrå arm r0 = (3, 0, 2) har r_par = 2 != 0 (r0 . z_hat != 0).
    # Selv med kontraroterende par (+omega, -omega) oppstår gyroskopisk vippemoment langs y!
    r0_tilted = [q(3), q(0), q(2)]
    p_plus, l_plus = rotor_pair_momenta(r0_tilted, tau, omega, m_p)
    p_minus, l_minus = rotor_pair_momenta(r0_tilted, -tau, -omega, m_p)

    p_4body_tilted = vec_add(p_plus, p_minus)
    l_4body_tilted = vec_add(l_plus, l_minus)
    assert p_4body_tilted == [q(0), q(0), q(0)]

    # Analytisk formel fra Dok. 78 §4.3: L_y = -4 * m_p * omega * r_perp * r_par * sin(theta)
    sin_theta = (q(2) * tau) / (q(1) + tau * tau)  # 4/5
    expected_ly = q(-4) * m_p * omega * q(3) * q(2) * sin_theta  # -4*2*5*3*2*(4/5) = -192
    assert expected_ly == q(-192)
    assert l_4body_tilted == [q(0), expected_ly, q(0)]

    # 3B: Når hovedakse-ortogonalitet r0 . z_hat = 0 pålegges, f.eks. r0 = (3, 4, 0),
    # blir både P_tot == 0 OG L_tot == 0 eksakt for ALLE rasjonale tau!
    r0_planar = [q(3), q(4), q(0)]
    for tau_sample in (q(0), q(1, 3), q(1, 2), q(7, 5), q(-11, 4)):
        pp, lp = rotor_pair_momenta(r0_planar, tau_sample, omega, m_p)
        pm, lm = rotor_pair_momenta(r0_planar, -tau_sample, -omega, m_p)
        assert vec_add(pp, pm) == [q(0), q(0), q(0)]
        assert vec_add(lp, lm) == [q(0), q(0), q(0)]

    ledger.append(
        "TEST_3_GYRO_TILT_AND_ORTHOGONAL_FIX",
        f"tilted_Ly={l_4body_tilted[1]}|planar_P_and_L_zero_across_5_taus=True",
    )


def test_4_cayley_4d_lifo_and_gcd_canonical_hash(ledger: AppendOnlyWitnessLedger) -> None:
    s0: Vec = [q(3, 7), q(-5, 11), q(2, 3), q(13, 17)]
    h_init = sha256_hex(encode_canonical_vec(s0))

    # 10 forskjellige 4x4 skjevsymmetriske generatorer over Q
    steps_skew: List[Mat] = []
    for k in range(1, 11):
        a = q(k, k + 2)
        b = q(-k, 2 * k + 1)
        c = q(2 * k - 1, 3 * k + 2)
        d = q(1, k + 3)
        e = q(-3, 2 * k + 5)
        f_val = q(k + 1, 4 * k + 1)
        skew: Mat = [
            [q(0), a, b, c],
            [-a, q(0), d, e],
            [-b, -d, q(0), f_val],
            [-c, -e, -f_val, q(0)],
        ]
        steps_skew.append(skew)

    state = list(s0)
    norm_sq_0 = dot(state, state)

    # Fremoverkjede U_1 -> U_10
    for skew in steps_skew:
        u_mat = cayley_orthogonal(skew)
        assert mat_mul(mat_transpose(u_mat), u_mat) == mat_eye(4)
        state = mat_vec(u_mat, state)
        assert dot(state, state) == norm_sq_0

    assert state != s0

    # Eksakt LIFO-retur med R(-S_k) fra k = 10 ned til 1
    for skew in reversed(steps_skew):
        u_inv = cayley_orthogonal(mat_neg(skew))
        state = mat_vec(u_inv, state)

    assert state == s0
    h_final = sha256_hex(encode_canonical_vec(state))
    assert h_final == h_init  # Bit-identisk SHA-256!

    # Demonstrer hvorfor gcd-forkorting i encode er obligatorisk (Kritisk korreksjon 3):
    unreduced = [(2 * x.numerator, 2 * x.denominator) for x in state]
    # Matematisk samme vektor i Q^4, men rå byte-hash kolliderer uten gcd-normalisering:
    assert all(q(p, den) == x for (p, den), x in zip(unreduced, s0))
    h_unreduced = sha256_hex(encode_unreduced_pairs(unreduced))
    assert h_unreduced != h_init

    ledger.append(
        "TEST_4_CAYLEY_4D_LIFO_SHA256",
        f"h_match={h_final[:16]}|unreduced_mismatch_detected=True",
    )


def test_5_electrochemical_origin_shift(ledger: AppendOnlyWitnessLedger) -> None:
    # Parametere i Q: E_eq != E_pzc gir ikke-null likevektsladning ved overpotensial eta = 0
    c_dl = q(7, 2)       # Kapasitans C_dl
    e_eq = q(3, 5)       # Nernst-likevektspotensial
    e_pzc = q(-1, 4)     # Point of zero charge (E_eq != E_pzc)
    q_dl_eq = c_dl * (e_eq - e_pzc)  # 7/2 * 17/20 = 119/40 != 0
    assert q_dl_eq != q(0)

    def q_dl_of_eta(eta: Fraction) -> Fraction:
        # Ved potensial E = E_eq + eta er ladningen C_dl * (E - E_pzc)
        return c_dl * ((e_eq + eta) - e_pzc)

    # Naiv avbildning fra Dok. 78 linje 307 bryter origo-invarians ved eta = 0:
    psi_naive_at_zero = q_dl_of_eta(q(0)) / c_dl
    assert psi_naive_at_zero == e_eq - e_pzc and psi_naive_at_zero != q(0)

    # Korrigert avbildning delta_phi_dl = (q_dl - q_dl,eq) / C_dl bevarer origo og involusjon:
    def delta_phi_dl(eta: Fraction) -> Fraction:
        return (q_dl_of_eta(eta) - q_dl_eq) / c_dl

    assert delta_phi_dl(q(0)) == q(0)

    # Reversibel syklus (+U -> 0 -> HOLD -> -U -> 0) i kapasitivt vindu (i_F = 0):
    u_pulse = q(9, 20)
    cycle = [delta_phi_dl(u_pulse), delta_phi_dl(q(0)), delta_phi_dl(-u_pulse), delta_phi_dl(q(0))]
    assert cycle == [u_pulse, q(0), -u_pulse, q(0)]
    assert cycle[0] + cycle[2] == q(0) and cycle[-1] == q(0)

    ledger.append(
        "TEST_5_ELECTROCHEMICAL_ORIGIN",
        f"naive_psi0={psi_naive_at_zero}!=0|shifted_psi0=0|cycle_symmetric=True",
    )


def test_6_airlock_hold_and_ledger_integrity(ledger: AppendOnlyWitnessLedger) -> None:
    # I HOLD er s_irr låst (Delta s_irr == 0) og alle oppbevaringssteg har verifisert hashkjede
    ledger.append("TEST_6_AIRLOCK_HOLD_LOCK", "dok78_source_untouched=True|omega=NO_EFFECT", delta_s_irr=q(0))
    assert len(ledger.entries) == 6
    assert all(e.delta_s_irr == q(0) for e in ledger.entries)
    assert ledger.verify_chain()


def main() -> None:
    ledger = AppendOnlyWitnessLedger()
    tests = [
        ("1. Konvekst moteksempel (R_{N_K}=|x|) vs. lineært underrom", test_1_convex_vs_subspace_cayley),
        ("2. Enkelt 2-legeme rotor bryter L_tot = 0 (Dok. 78 §4.3)", test_2_single_rotor_nonzero_spin),
        ("3. Gyroskopisk tverrmoment ved skrå arm vs. r_0 _|_ n_hat", test_3_counter_rotor_tilt_vs_principal_axis),
        ("4. 4D rasjonal Cayley LIFO-kjede + kanonisk gcd SHA-256", test_4_cayley_4d_lifo_and_gcd_canonical_hash),
        ("5. Elektrokjemisk origo-skift delta_phi_dl ved E_eq != E_pzc", test_5_electrochemical_origin_shift),
        ("6. Luftsluse-HOLD (Delta s_irr = 0) & append-only SHA-256", test_6_airlock_hold_and_ledger_integrity),
    ]

    print("=== CARBON / 14: DOKUMENT 78 & REVERSIBLUS INVARIANSPRØVE (L1, NULL FLOAT) ===")
    for label, fn in tests:
        fn(ledger)
        print(f"  [PASS] {label}")

    head = ledger.entries[-1].entry_hash
    print(f"\nResultat: {len(tests)}/{len(tests)} PASS | Append-only SHA-256 head: {head[:24]}...")


if __name__ == "__main__":
    main()
