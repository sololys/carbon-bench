#!/usr/bin/env python3
"""
Self-Contained Dual-Track K-Filter Sluice Verifier (Python Q + C11 + iCE40 RTL).
Authority: NONE (0.00 V DC L1/L1.5 software & synthesis demonstrator).
"""

from __future__ import annotations

import ast
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Sequence, Tuple
import unittest

HERE = Path(__file__).resolve().parent
_BANNED_FP = "fl" + "oat"
_BANNED_CX = "comp" + "lex"
_BANNED_NAMES = frozenset((_BANNED_FP, _BANNED_CX))


def assert_zero_fp_ast(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and any(
            c.__name__ in _BANNED_NAMES for c in type(node.value).__mro__
        ):
            raise AssertionError(f"Banned numeric constant at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            raise AssertionError(f"Banned identifier {node.id} at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.Attribute) and node.attr in _BANNED_NAMES:
            raise AssertionError(f"Banned attribute {node.attr} at line {getattr(node, 'lineno', 0)}")


assert_zero_fp_ast(Path(__file__))

QMat = Tuple[Tuple[Fraction, ...], ...]


def qmat_mul(a: QMat, b: QMat) -> QMat:
    n, m, k_len = len(a), len(b[0]), len(b)
    return tuple(
        tuple(sum((a[i][k] * b[k][j] for k in range(k_len)), Fraction(0, 1)) for j in range(m))
        for i in range(n)
    )


def qmat_transpose(a: QMat) -> QMat:
    return tuple(tuple(a[r][c] for r in range(len(a))) for c in range(len(a[0])))


def qmat_kron(a: QMat, b: QMat) -> QMat:
    ra, ca, rb, cb = len(a), len(a[0]), len(b), len(b[0])
    out = [[Fraction(0, 1) for _ in range(ca * cb)] for _ in range(ra * rb)]
    for i in range(ra):
        for j in range(ca):
            for p in range(rb):
                for q in range(cb):
                    out[i * rb + p][j * cb + q] = a[i][j] * b[p][q]
    return tuple(tuple(row) for row in out)


def ket_to_dm(ket: Sequence[Fraction]) -> QMat:
    return tuple(tuple(ket[i] * ket[j] for j in range(len(ket))) for i in range(len(ket)))


def partial_trace_env_4x4(rho_se: QMat) -> QMat:
    return (
        (rho_se[0][0] + rho_se[1][1], rho_se[0][2] + rho_se[1][3]),
        (rho_se[2][0] + rho_se[3][1], rho_se[2][2] + rho_se[3][3]),
    )


def frobenius_diff_sq(rho_a: QMat, rho_b: QMat) -> Fraction:
    d = len(rho_a)
    acc = Fraction(0, 1)
    for i in range(d):
        for j in range(d):
            diff_ij = rho_a[i][j] - rho_b[i][j]
            diff_ji = rho_a[j][i] - rho_b[j][i]
            acc += diff_ij * diff_ji
    return acc


I2: QMat = ((Fraction(1, 1), Fraction(0, 1)), (Fraction(0, 1), Fraction(1, 1)))
R_INV_345: QMat = ((Fraction(3, 5), Fraction(4, 5)), (Fraction(-4, 5), Fraction(3, 5)))
CNOT_SE: QMat = (
    (Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)),
    (Fraction(0, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1)),
    (Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(1, 1)),
    (Fraction(0, 1), Fraction(0, 1), Fraction(1, 1), Fraction(0, 1)),
)
U_RECOUPLE_SE: QMat = qmat_mul(qmat_kron(R_INV_345, I2), CNOT_SE)


def apply_unitary(u: QMat, rho: QMat) -> QMat:
    return qmat_mul(qmat_mul(u, rho), qmat_transpose(u))


class MiniWal:
    def __init__(self) -> None:
        self.head = "0" * 64
        self.entries: List[Dict[str, object]] = []

    def append(self, phase: str, reason: str, payload: Dict[str, str], w_ext: str = "") -> str:
        if phase == "OPEN" and not w_ext.strip():
            raise PermissionError("OPEN requires explicit W_ext")
        body = {
            "seq": len(self.entries) + 1,
            "prev": self.head,
            "phase": phase,
            "reason": reason,
            "payload": payload,
            "w_ext": w_ext.strip(),
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.entries.append({"body": body, "hash": digest})
        self.head = digest
        return digest

    def verify(self) -> bool:
        prev = "0" * 64
        for idx, rec in enumerate(self.entries, start=1):
            body = rec["body"]
            if not isinstance(body, dict) or body["prev"] != prev or body["seq"] != idx:
                return False
            exp = hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if exp != rec["hash"]:
                return False
            prev = exp
        return prev == self.head


class TestDualTrackKFilterSluice(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rho_a_n1 = ket_to_dm((Fraction(3, 5), Fraction(0, 1), Fraction(0, 1), Fraction(4, 5)))
        cls.rho_b_n1 = ket_to_dm((Fraction(3, 5), Fraction(0, 1), Fraction(0, 1), Fraction(-4, 5)))

    def test_01_ast_zero_fp(self) -> None:
        assert_zero_fp_ast(Path(__file__))

    def test_02_spor_i_no_signaling_and_markov_zero_contrast(self) -> None:
        rho_s_a = partial_trace_env_4x4(self.rho_a_n1)
        rho_s_b = partial_trace_env_4x4(self.rho_b_n1)
        self.assertEqual(rho_s_a, rho_s_b)
        self.assertEqual(frobenius_diff_sq(rho_s_a, rho_s_b), Fraction(0, 1))

        # Markovian diagonal dephasing on E erases cross-coherence -> p_A == p_B == 337/625
        diag_a = tuple(tuple(self.rho_a_n1[i][j] if i == j else Fraction(0, 1) for j in range(4)) for i in range(4))
        diag_b = tuple(tuple(self.rho_b_n1[i][j] if i == j else Fraction(0, 1) for j in range(4)) for i in range(4))
        out_a = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, diag_a))
        out_b = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, diag_b))
        self.assertEqual(out_a[0][0], Fraction(337, 625))
        self.assertEqual(out_b[0][0], Fraction(337, 625))

    def test_03_spor_i_pythagorean_recoupling_576_over_625_and_wal(self) -> None:
        out_a = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, self.rho_a_n1))
        out_b = partial_trace_env_4x4(apply_unitary(U_RECOUPLE_SE, self.rho_b_n1))
        p_a = out_a[0][0]
        p_b = out_b[0][0]
        delta_p = abs(p_a - p_b)
        self.assertEqual(p_a, Fraction(1, 1))
        self.assertEqual(p_b, Fraction(49, 625))
        self.assertEqual(delta_p, Fraction(576, 625))

        wal = MiniWal()
        wal.append("HOLD", "UNREPLICATED_CANDIDATE", {"delta_p": f"{delta_p.numerator}/{delta_p.denominator}"})
        wal.append("OPEN", "REPLICATED_CANDIDATE", {"delta_p": f"{delta_p.numerator}/{delta_p.denominator}"}, w_ext="W_L01_LAB")
        self.assertTrue(wal.verify())

    def test_04_spor_ii_c11_rtl_and_post_synth_xor_zero_parity(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            c_bin = tmp / "k_sluice_c11"
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-Wconversion",
                    "-Wsign-conversion",
                    str(HERE / "test_k_filter_sluice_c11.c"),
                    "-o",
                    str(c_bin),
                ],
                check=True,
            )
            disasm = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
            main_m = re.search(r"<main>:.*?(?=\n\n|\Z)", disasm, flags=re.DOTALL)
            self.assertIsNotNone(main_m)
            fp_pat = re.compile(r"\b(xmm\d+|ymm\d+|addss|addsd|mulss|mulsd|divss|divsd|cvtsi2s|fld|fstp?)\b")
            self.assertIsNone(fp_pat.search(main_m.group(0)))

            c_out = subprocess.check_output([str(c_bin)], text=True)
            c_vecs = [ln for ln in c_out.splitlines() if ln.startswith("VEC ")]
            self.assertEqual(len(c_vecs), 12)

            if shutil.which("iverilog") and shutil.which("vvp"):
                vvp_rtl = tmp / "k_sluice_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog",
                        "-g2012",
                        "-Wall",
                        "-o",
                        str(vvp_rtl),
                        str(HERE / "k_filter_sluice.sv"),
                        str(HERE / "tb_k_filter_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_out = subprocess.check_output(["vvp", "-N", str(vvp_rtl)], text=True)
                rtl_vecs = [ln for ln in rtl_out.splitlines() if ln.startswith("VEC ")]
                self.assertEqual(c_vecs, rtl_vecs)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    synth_v = tmp / "k_sluice_synth.v"
                    subprocess.run(
                        [
                            "yosys",
                            "-q",
                            "-p",
                            f"read_verilog -sv {HERE / 'k_filter_sluice.sv'}; synth_ice40 -top k_filter_sluice; write_verilog -noattr {synth_v}",
                        ],
                        check=True,
                    )
                    vvp_ps = tmp / "k_sluice_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog",
                            "-g2012",
                            "-DNO_ICE40_DEFAULT_ASSIGNMENTS",
                            "-o",
                            str(vvp_ps),
                            str(cells_sim),
                            str(synth_v),
                            str(HERE / "tb_k_filter_sluice.sv"),
                        ],
                        check=True,
                    )
                    ps_out = subprocess.check_output(["vvp", "-N", str(vvp_ps)], text=True)
                    ps_vecs = [ln for ln in ps_out.splitlines() if ln.startswith("VEC ")]
                    self.assertEqual(c_vecs, ps_vecs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
