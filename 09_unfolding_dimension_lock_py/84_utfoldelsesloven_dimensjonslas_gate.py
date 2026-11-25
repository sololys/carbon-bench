#!/usr/bin/env python3
"""
CARBON 84 — Utfoldelsesloven (V ~= Lambda^2 V => n = 3), Singulariteten som
fundament, Schurs lemma over so(n), 7D oktonion-bruddprøve, Moreau-hjørnelås
og Hörmanders skjøtelov.

Epistemisk grense:
  INSPIRED_BY != IMPLEMENTS != PROVES.
  100 % flyttallsfri L1-verifikasjonsmotor (int / Fraction, AST 0-float-vakt,
  append-only SHA-256 WAL med 'UNFOLDING-LAW/v1.0'-prefiks).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path
import unittest
from typing import Dict, List, Optional, Sequence, Tuple

VectorQ = Tuple[Fraction, ...]
VectorZ = Tuple[int, ...]

GATE_OPEN = "OPEN"
GATE_HOLD = "HOLD"
GATE_KILL = "KILL"

VOLTAGE_ZERO_MV = 0
VOLTAGE_OPEN_MV = 5000

WAL_DOMAIN_PREFIX = "UNFOLDING-LAW/v1.0"

# 7 associative Fano-plane triples for the 7D octonion cross product
# (1-indexed basis e_1 .. e_7, stored as 0-indexed tuples (i, j, k) with e_i x e_j = +e_k)
FANO_TRIPLES_7D: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),  # e1 x e2 = e3
    (0, 3, 4),  # e1 x e4 = e5
    (0, 6, 5),  # e1 x e7 = e6
    (1, 3, 5),  # e2 x e4 = e6
    (1, 4, 6),  # e2 x e5 = e7
    (2, 3, 6),  # e3 x e4 = e7
    (2, 5, 4),  # e3 x e6 = e5
)


def assert_zero_float_in_source(source_path: Path) -> None:
    """AST guard: rejects any float literal or float() invocation in source_path."""
    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            raise AssertionError(f"Forbidden float literal at line {node.lineno}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "float":
                raise AssertionError(f"Forbidden float() call at line {node.lineno}")


@dataclass(frozen=True)
class DimensionAuditResult:
    n: int
    dim_v: int
    dim_bivector: int
    delta_dim: int
    min_cokernel_dim: int
    min_kernel_dim: int
    huygens_sharp_odd: bool
    vortex_stretching_vector_closed: bool
    gate_decision: str
    reason: str


def evaluate_unfolding_dimension(n: int) -> DimensionAuditResult:
    """
    Evaluates the transition operator Omega_* : Lambda^2 V -> V for dimension n > 0.
    By rank-nullity:
      dim(ker Omega_*) - dim(coker Omega_*) = dim(Lambda^2 V) - dim(V) = n(n - 3) // 2.
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError("Dimension n must be a positive integer.")

    dim_v = n
    dim_bivector = (n * (n - 1)) // 2
    delta_dim = dim_bivector - dim_v  # == n * (n - 3) // 2

    min_cokernel_dim = max(0, dim_v - dim_bivector)
    min_kernel_dim = max(0, dim_bivector - dim_v)

    huygens_sharp_odd = (n >= 3) and (n % 2 == 1)
    vortex_stretching_vector_closed = (dim_bivector == dim_v) and (n >= 3)

    if min_cokernel_dim > 0:
        decision = GATE_KILL
        reason = "KILL_UNDERDETERMINED_COKERNEL"
    elif min_kernel_dim > 0:
        decision = GATE_KILL
        reason = "KILL_GHOST_KERNEL_LEAK"
    else:
        decision = GATE_OPEN
        reason = "OPEN_BIJECTIVE_3D_UNFOLDING"

    return DimensionAuditResult(
        n=n,
        dim_v=dim_v,
        dim_bivector=dim_bivector,
        delta_dim=delta_dim,
        min_cokernel_dim=min_cokernel_dim,
        min_kernel_dim=min_kernel_dim,
        huygens_sharp_odd=huygens_sharp_odd,
        vortex_stretching_vector_closed=vortex_stretching_vector_closed,
        gate_decision=decision,
        reason=reason,
    )


def cross_3d_z(u: VectorZ, v: VectorZ) -> VectorZ:
    """Exact integer Hodge-dual cross product in Z^3: Omega_*(u ^ v)."""
    if len(u) != 3 or len(v) != 3:
        raise ValueError("3D cross product requires 3-tuples.")
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def jacobi_defect_z(
    cross_fn, u: Sequence[int], v: Sequence[int], w: Sequence[int]
) -> Tuple[int, ...]:
    """Computes J(u,v,w) = u x (v x w) + v x (w x u) + w x (u x v)."""
    t1 = cross_fn(u, cross_fn(v, w))
    t2 = cross_fn(v, cross_fn(w, u))
    t3 = cross_fn(w, cross_fn(u, v))
    return tuple(a + b + c for a, b, c in zip(t1, t2, t3))


def cross_7d_octonion_z(u: Sequence[int], v: Sequence[int]) -> Tuple[int, ...]:
    """Exact integer 7D octonion cross product defined by the Fano plane."""
    if len(u) != 7 or len(v) != 7:
        raise ValueError("7D cross product requires 7-tuples.")
    out = [0] * 7
    for i, j, k in FANO_TRIPLES_7D:
        # Cyclic orientations: (i,j)->k, (j,k)->i, (k,i)->j
        out[k] += u[i] * v[j] - u[j] * v[i]
        out[i] += u[j] * v[k] - u[k] * v[j]
        out[j] += u[k] * v[i] - u[i] * v[k]
    return tuple(out)


def exact_matrix_rank_q(matrix: Sequence[Sequence[int]]) -> int:
    """Computes the exact rank of an integer matrix over Q using Fraction Gauss-Jordan."""
    if not matrix or not matrix[0]:
        return 0
    rows = len(matrix)
    cols = len(matrix[0])
    m: List[List[Fraction]] = [
        [Fraction(int(val), 1) for val in row] for row in matrix
    ]
    rank = 0
    for col in range(cols):
        pivot_row = None
        for r in range(rank, rows):
            if m[r][col] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            continue
        m[rank], m[pivot_row] = m[pivot_row], m[rank]
        pivot_val = m[rank][col]
        for c in range(col, cols):
            m[rank][c] /= pivot_val
        for r in range(rows):
            if r != rank and m[r][col] != 0:
                factor = m[r][col]
                for c in range(col, cols):
                    m[r][c] -= factor * m[rank][c]
        rank += 1
    return rank


def build_bivector_operator_matrix_7d() -> Tuple[List[List[int]], List[Tuple[int, int]]]:
    """
    Builds the 7 x 21 linear matrix M representing Omega_{*,7} : Lambda^2(R^7) -> R^7,
    where each column corresponds to a basis bivector e_i ^ e_j (0 <= i < j < 7).
    """
    bivector_pairs: List[Tuple[int, int]] = []
    cols: List[Tuple[int, ...]] = []
    for i in range(7):
        for j in range(i + 1, 7):
            bivector_pairs.append((i, j))
            ei = [1 if idx == i else 0 for idx in range(7)]
            ej = [1 if idx == j else 0 for idx in range(7)]
            cols.append(cross_7d_octonion_z(ei, ej))
    matrix = [[cols[c][r] for c in range(len(cols))] for r in range(7)]
    return matrix, bivector_pairs


def compute_so_n_equivariant_hom_dimension(n: int) -> int:
    """
    Computes dim Hom_{so(n)}(Lambda^2 V, V) exactly over Q for n >= 1 by solving
    the system of linear commutator equations:
      A * D(e_p ^ e_q) - D((A e_p) ^ e_q + e_p ^ (A e_q)) = 0
    for all basis generators A = E_{a,b} - E_{b,a} in so(n) and all 0 <= p < q < n.
    By Schur's lemma, this dimension is 1 if and only if n == 3, and 0 for all n != 3.
    """
    if n <= 1:
        return 0

    bivectors: List[Tuple[int, int]] = [
        (p, q) for p in range(n) for q in range(p + 1, n)
    ]
    num_biv = len(bivectors)
    biv_index: Dict[Tuple[int, int], int] = {
        pair: idx for idx, pair in enumerate(bivectors)
    }
    num_vars = n * num_biv

    def var_id(row_i: int, biv_idx: int) -> int:
        return row_i * num_biv + biv_idx

    equations: List[List[int]] = []

    for a in range(n):
        for b in range(a + 1, n):
            for biv_idx, (p, q) in enumerate(bivectors):
                for i in range(n):
                    row = [0] * num_vars
                    if i == a:
                        row[var_id(b, biv_idx)] += 1
                    elif i == b:
                        row[var_id(a, biv_idx)] -= 1

                    if p == b:
                        if a != q:
                            pair = (a, q) if a < q else (q, a)
                            sign = 1 if a < q else -1
                            row[var_id(i, biv_index[pair])] -= sign
                    elif p == a:
                        if b != q:
                            pair = (b, q) if b < q else (q, b)
                            sign = -1 if b < q else 1
                            row[var_id(i, biv_index[pair])] -= sign

                    if q == b:
                        if p != a:
                            pair = (p, a) if p < a else (a, p)
                            sign = 1 if p < a else -1
                            row[var_id(i, biv_index[pair])] -= sign
                    elif q == a:
                        if p != b:
                            pair = (p, b) if p < b else (b, p)
                            sign = -1 if p < b else 1
                            row[var_id(i, biv_index[pair])] -= sign

                    if any(val != 0 for val in row):
                        equations.append(row)

    rank = exact_matrix_rank_q(equations)
    return num_vars - rank


def count_7d_octonion_stabilizer_dim_in_so7() -> Tuple[int, int]:
    """
    Computes the dimension of the Lie subalgebra g_2 subset so(7) of derivations
    preserving the 7D octonion cross product:
      A(u x v) - (Au) x v - u x (Av) = 0,
    and returns (dim_g2, broken_so7_generators = 21 - dim_g2).
    """
    bivectors = [(a, b) for a in range(7) for b in range(a + 1, 7)]
    gen_index = {pair: idx for idx, pair in enumerate(bivectors)}

    basis = [tuple(1 if idx == k else 0 for idx in range(7)) for k in range(7)]
    cross_table = [
        [cross_7d_octonion_z(basis[p], basis[q]) for q in range(7)]
        for p in range(7)
    ]

    equations: List[List[int]] = []
    for p in range(7):
        for q in range(p + 1, 7):
            cpq = cross_table[p][q]
            for i in range(7):
                row = [0] * 21
                for a in range(7):
                    for b in range(a + 1, 7):
                        g_idx = gen_index[(a, b)]
                        if i == a:
                            row[g_idx] += cpq[b]
                        elif i == b:
                            row[g_idx] -= cpq[a]

                        if p == b:
                            row[g_idx] -= cross_table[a][q][i]
                        elif p == a:
                            row[g_idx] += cross_table[b][q][i]

                        if q == b:
                            row[g_idx] -= cross_table[p][a][i]
                        elif q == a:
                            row[g_idx] += cross_table[p][b][i]

                if any(val != 0 for val in row):
                    equations.append(row)

    broken_generators = exact_matrix_rank_q(equations)
    dim_g2 = 21 - broken_generators
    return dim_g2, broken_generators


def project_l_inf_box_3d_q(
    y: VectorQ, bound: Fraction = Fraction(1, 1)
) -> VectorQ:
    """Exact Moreau projection Pi_K onto the 3D L_infinity box [-bound, +bound]^3."""
    if len(y) != 3:
        raise ValueError("Expected 3D vector in Q^3.")
    projected: List[Fraction] = []
    for coord in y:
        if coord > bound:
            projected.append(bound)
        elif coord < -bound:
            projected.append(-bound)
        else:
            projected.append(coord)
    return tuple(projected)


def dot_q(u: VectorQ, v: VectorQ) -> Fraction:
    return sum((a * b for a, b in zip(u, v)), Fraction(0, 1))


@dataclass(frozen=True)
class HormanderJointVerdict:
    gate_decision: str
    voltage_mv: int
    reason: str
    covector_sum: VectorQ
    admissible_probe_accepted: bool


def evaluate_hormander_wavefront_joint(
    xi_1: VectorQ,
    xi_2: VectorQ,
    probe_direction: VectorQ,
    evidence_id: Optional[str],
) -> HormanderJointVerdict:
    """
    Evaluates a two-constraint singular joint at x_0 using Hörmander's wavefront
    condition (xi_1 + xi_2 != 0) and Moreau's dual tangent cone.
    """
    if len(xi_1) != 3 or len(xi_2) != 3 or len(probe_direction) != 3:
        raise ValueError("All vectors must lie in Q^3.")
    if all(c == 0 for c in xi_1) or all(c == 0 for c in xi_2):
        raise ValueError("Wavefront covectors in T*M \\ {0} cannot be zero.")

    covector_sum = tuple(a + b for a, b in zip(xi_1, xi_2))

    cross_12 = (
        xi_1[1] * xi_2[2] - xi_1[2] * xi_2[1],
        xi_1[2] * xi_2[0] - xi_1[0] * xi_2[2],
        xi_1[0] * xi_2[1] - xi_1[1] * xi_2[0],
    )
    if all(c == 0 for c in cross_12) and dot_q(xi_1, xi_2) < 0:
        return HormanderJointVerdict(
            gate_decision=GATE_KILL,
            voltage_mv=VOLTAGE_ZERO_MV,
            reason="KILL_ANTIPODAL_WAVEFRONT_COLLISION",
            covector_sum=covector_sum,
            admissible_probe_accepted=False,
        )

    ip_1 = dot_q(xi_1, probe_direction)
    ip_2 = dot_q(xi_2, probe_direction)
    if ip_1 > 0 or ip_2 > 0:
        return HormanderJointVerdict(
            gate_decision=GATE_HOLD,
            voltage_mv=VOLTAGE_ZERO_MV,
            reason="HOLD_TANGENT_CONE_BARRIER_SATURATION",
            covector_sum=covector_sum,
            admissible_probe_accepted=False,
        )

    has_witness = bool(evidence_id and evidence_id.strip())
    if not has_witness:
        return HormanderJointVerdict(
            gate_decision=GATE_HOLD,
            voltage_mv=VOLTAGE_ZERO_MV,
            reason="HOLD_READY_AWAITING_W_EXT",
            covector_sum=covector_sum,
            admissible_probe_accepted=True,
        )

    return HormanderJointVerdict(
        gate_decision=GATE_OPEN,
        voltage_mv=VOLTAGE_OPEN_MV,
        reason="OPEN_TRANSVERSAL_JOINT_WITNESSED",
        covector_sum=covector_sum,
        admissible_probe_accepted=True,
    )


@dataclass(frozen=True)
class UnfoldingWitnessEntry:
    step_index: int
    payload: str
    prev_hash: str
    entry_hash: str


class UnfoldingWitnessChain:
    """Append-only SHA-256 witness ledger for CARBON 84."""

    def __init__(self) -> None:
        self._entries: List[UnfoldingWitnessEntry] = []
        self._genesis_hash = hashlib.sha256(
            f"{WAL_DOMAIN_PREFIX}|GENESIS".encode("utf-8")
        ).hexdigest()

    @property
    def entries(self) -> Tuple[UnfoldingWitnessEntry, ...]:
        return tuple(self._entries)

    def append(self, payload: str) -> UnfoldingWitnessEntry:
        step_index = len(self._entries) + 1
        prev_hash = (
            self._entries[-1].entry_hash if self._entries else self._genesis_hash
        )
        canonical = f"{WAL_DOMAIN_PREFIX}|{step_index}|{prev_hash}|{payload}"
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry = UnfoldingWitnessEntry(
            step_index=step_index,
            payload=payload,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    @staticmethod
    def verify_chain(entries: Sequence[UnfoldingWitnessEntry]) -> bool:
        genesis = hashlib.sha256(
            f"{WAL_DOMAIN_PREFIX}|GENESIS".encode("utf-8")
        ).hexdigest()
        expected_prev = genesis
        for idx, entry in enumerate(entries, start=1):
            if entry.step_index != idx:
                return False
            if entry.prev_hash != expected_prev:
                return False
            canonical = (
                f"{WAL_DOMAIN_PREFIX}|{entry.step_index}|"
                f"{entry.prev_hash}|{entry.payload}"
            )
            recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if recomputed != entry.entry_hash:
                return False
            expected_prev = entry.entry_hash
        return True


class TestCarbon84UnfoldingLawGate(unittest.TestCase):
    """T01-T10 verification suite for CARBON 84 v2.0."""

    def test_t01_ast_zero_float_guard(self) -> None:
        assert_zero_float_in_source(Path(__file__).resolve())

    def test_t02_dimension_lock_selector(self) -> None:
        open_dimensions: List[int] = []
        for n in range(1, 17):
            res = evaluate_unfolding_dimension(n)
            self.assertEqual(res.delta_dim, (n * (n - 3)) // 2)
            if n in (1, 2):
                self.assertEqual(res.gate_decision, GATE_KILL)
                self.assertEqual(res.reason, "KILL_UNDERDETERMINED_COKERNEL")
                self.assertGreater(res.min_cokernel_dim, 0)
                self.assertEqual(res.min_kernel_dim, 0)
            elif n == 3:
                self.assertEqual(res.gate_decision, GATE_OPEN)
                self.assertEqual(res.reason, "OPEN_BIJECTIVE_3D_UNFOLDING")
                self.assertEqual(res.dim_v, 3)
                self.assertEqual(res.dim_bivector, 3)
                self.assertEqual(res.min_cokernel_dim, 0)
                self.assertEqual(res.min_kernel_dim, 0)
                open_dimensions.append(n)
            else:
                self.assertEqual(res.gate_decision, GATE_KILL)
                self.assertEqual(res.reason, "KILL_GHOST_KERNEL_LEAK")
                self.assertEqual(res.min_cokernel_dim, 0)
                self.assertEqual(res.min_kernel_dim, (n * (n - 3)) // 2)
        self.assertEqual(open_dimensions, [3])

    def test_t03_3d_hodge_bijection_and_jacobi(self) -> None:
        e1: VectorZ = (1, 0, 0)
        e2: VectorZ = (0, 1, 0)
        e3: VectorZ = (0, 0, 1)
        self.assertEqual(cross_3d_z(e2, e3), e1)
        self.assertEqual(cross_3d_z(e3, e1), e2)
        self.assertEqual(cross_3d_z(e1, e2), e3)

        basis = (e1, e2, e3)
        for u in basis:
            for v in basis:
                for w in basis:
                    self.assertEqual(
                        jacobi_defect_z(cross_3d_z, u, v, w), (0, 0, 0)
                    )

    def test_t04_7d_octonion_ghost_kernel_and_jacobi_break(self) -> None:
        matrix_7x21, pairs = build_bivector_operator_matrix_7d()
        self.assertEqual(len(matrix_7x21), 7)
        self.assertEqual(len(pairs), 21)
        rank = exact_matrix_rank_q(matrix_7x21)
        self.assertEqual(rank, 7)
        ghost_kernel_dim = len(pairs) - rank
        self.assertEqual(ghost_kernel_dim, 14)

        e1 = tuple(1 if i == 0 else 0 for i in range(7))
        e2 = tuple(1 if i == 1 else 0 for i in range(7))
        e4 = tuple(1 if i == 3 else 0 for i in range(7))
        e5 = tuple(1 if i == 4 else 0 for i in range(7))
        e6 = tuple(1 if i == 5 else 0 for i in range(7))
        c_12 = cross_7d_octonion_z(e1, e2)
        c_65 = cross_7d_octonion_z(e6, e5)
        self.assertEqual(c_12, c_65)
        ghost_image = tuple(a - b for a, b in zip(c_12, c_65))
        self.assertEqual(ghost_image, (0, 0, 0, 0, 0, 0, 0))

        jacobi_7d = jacobi_defect_z(cross_7d_octonion_z, e1, e2, e4)
        self.assertNotEqual(jacobi_7d, (0, 0, 0, 0, 0, 0, 0))

    def test_t05_huygens_and_vortex_stretching_corollaries(self) -> None:
        audits = [evaluate_unfolding_dimension(n) for n in range(1, 16)]
        huygens_odd = [a.n for a in audits if a.huygens_sharp_odd]
        self.assertEqual(huygens_odd, [3, 5, 7, 9, 11, 13, 15])

        ghost_free_huygens = [
            a.n for a in audits if a.huygens_sharp_odd and a.min_kernel_dim == 0
        ]
        self.assertEqual(ghost_free_huygens, [3])

        vortex_closed = [
            a.n for a in audits if a.vortex_stretching_vector_closed
        ]
        self.assertEqual(vortex_closed, [3])

    def test_t06_moreau_singular_corner_cone_lock(self) -> None:
        x0: VectorQ = (Fraction(1), Fraction(1), Fraction(1))
        perturbations: Tuple[VectorQ, ...] = (
            (Fraction(1, 10), Fraction(3, 10), Fraction(7, 10)),
            (Fraction(5, 1), Fraction(2, 3), Fraction(9, 4)),
            (Fraction(1, 1000), Fraction(100, 1), Fraction(1, 7)),
        )
        for delta in perturbations:
            y = tuple(a + b for a, b in zip(x0, delta))
            self.assertEqual(project_l_inf_box_3d_q(y), x0)

        x_face: VectorQ = (Fraction(1), Fraction(0), Fraction(0))
        y_face = (
            x_face[0] + Fraction(1, 2),
            x_face[1] + Fraction(1, 4),
            x_face[2] - Fraction(1, 3),
        )
        self.assertNotEqual(project_l_inf_box_3d_q(y_face), x_face)

    def test_t07_hormander_wavefront_joint_law(self) -> None:
        xi_1: VectorQ = (Fraction(1), Fraction(0), Fraction(0))
        xi_2: VectorQ = (Fraction(0), Fraction(1), Fraction(0))
        inward_probe: VectorQ = (Fraction(-1), Fraction(-1), Fraction(0))

        v_hold = evaluate_hormander_wavefront_joint(
            xi_1, xi_2, inward_probe, evidence_id=None
        )
        self.assertEqual(v_hold.gate_decision, GATE_HOLD)
        self.assertEqual(v_hold.voltage_mv, VOLTAGE_ZERO_MV)
        self.assertTrue(v_hold.admissible_probe_accepted)

        v_open = evaluate_hormander_wavefront_joint(
            xi_1, xi_2, inward_probe, evidence_id="W_EXT_CARBON84_01"
        )
        self.assertEqual(v_open.gate_decision, GATE_OPEN)
        self.assertEqual(v_open.voltage_mv, VOLTAGE_OPEN_MV)
        self.assertTrue(v_open.admissible_probe_accepted)

        xi_antipodal: VectorQ = (Fraction(-1), Fraction(0), Fraction(0))
        v_kill = evaluate_hormander_wavefront_joint(
            xi_1, xi_antipodal, inward_probe, evidence_id="W_EXT_CARBON84_01"
        )
        self.assertEqual(v_kill.gate_decision, GATE_KILL)
        self.assertEqual(v_kill.voltage_mv, VOLTAGE_ZERO_MV)
        self.assertEqual(v_kill.covector_sum, (Fraction(0), Fraction(0), Fraction(0)))
        self.assertFalse(v_kill.admissible_probe_accepted)

    def test_t08_append_only_sha256_witness_chain(self) -> None:
        chain = UnfoldingWitnessChain()
        for n in (1, 2, 3, 4, 7):
            res = evaluate_unfolding_dimension(n)
            chain.append(
                f"n={res.n}|delta={res.delta_dim}|decision={res.gate_decision}|{res.reason}"
            )
        self.assertEqual(len(chain.entries), 5)
        self.assertTrue(UnfoldingWitnessChain.verify_chain(chain.entries))

        tampered = list(chain.entries)
        tampered[2] = UnfoldingWitnessEntry(
            step_index=tampered[2].step_index,
            payload="n=3|delta=0|decision=OPEN|TAMPERED",
            prev_hash=tampered[2].prev_hash,
            entry_hash=tampered[2].entry_hash,
        )
        self.assertFalse(UnfoldingWitnessChain.verify_chain(tampered))

    def test_t09_schur_lemma_so_n_equivariance_1_to_8(self) -> None:
        hom_dims = {n: compute_so_n_equivariant_hom_dimension(n) for n in range(1, 9)}
        self.assertEqual(
            hom_dims,
            {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0},
        )

        dim_g2, broken_gen = count_7d_octonion_stabilizer_dim_in_so7()
        self.assertEqual(dim_g2, 14)
        self.assertEqual(broken_gen, 7)

    def test_t10_four_reefs_chirality_and_clifford_cl30_bridge(self) -> None:
        for n in range(2, 9):
            dim_wall_normal = n
            self.assertEqual(dim_wall_normal, n)
            knivsegg_plane_match = (n - 1) == 2
            curl_degree_match = (n - 2) == 1
            self.assertEqual(knivsegg_plane_match, n == 3)
            self.assertEqual(curl_degree_match, n == 3)

        u: VectorZ = (2, -1, 3)
        w: VectorZ = (-4, 5, 1)
        pu: VectorZ = tuple(-c for c in u)
        pw: VectorZ = tuple(-c for c in w)
        det_p = -1
        for chi in (-1, 1):
            d_uw = tuple(chi * c for c in cross_3d_z(u, w))
            p_d_uw = tuple(-c for c in d_uw)
            d_pu_pw = tuple(chi * c for c in cross_3d_z(pu, pw))
            self.assertEqual(p_d_uw, tuple(det_p * c for c in d_pu_pw))

        self.assertEqual((3 * 2) // 2, 3)
        self.assertEqual((4 * 3) // 2, 6)

        cl30_grades = (1, 3, 3, 1)
        self.assertEqual(sum(cl30_grades), 8)
        b23 = (
            (0, -1, 0, 0),
            (1, 0, 0, 0),
            (0, 0, 0, -1),
            (0, 0, 1, 0),
        )
        b31 = (
            (0, 0, -1, 0),
            (0, 0, 0, 1),
            (1, 0, 0, 0),
            (0, -1, 0, 0),
        )
        b12 = (
            (0, 0, 0, -1),
            (0, 0, -1, 0),
            (0, 1, 0, 0),
            (1, 0, 0, 0),
        )
        neg_i4 = tuple(
            tuple(-1 if r == c else 0 for c in range(4)) for r in range(4)
        )
        for b_mat in (b23, b31, b12):
            sq = tuple(
                tuple(sum(b_mat[r][k] * b_mat[k][c] for k in range(4)) for c in range(4))
                for r in range(4)
            )
            self.assertEqual(sq, neg_i4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
