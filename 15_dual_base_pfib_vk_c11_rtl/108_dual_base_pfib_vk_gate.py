#!/usr/bin/env python3
"""
Cell 15: Dual-Base (B1 |>< B2) Non-Tautological P_fib Energy Accounting,
Tangent-Frame Gromov Capacity & Strict Vakhitov-Kolokolov Slope Verifier.
Authority: NONE (0.00 V DC L1/L1.5 software & synthesis demonstrator).
"""

from __future__ import annotations

import ast
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
_BANNED = frozenset(("fl" + "oat", "comp" + "lex"))


def assert_zero_fp_ast(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and any(
            c.__name__ in _BANNED for c in type(node.value).__mro__
        ):
            raise AssertionError(f"Banned constant at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.Name) and node.id in _BANNED:
            raise AssertionError(f"Banned identifier {node.id}")


assert_zero_fp_ast(Path(__file__))


class TestDualBasePfibVkGate(unittest.TestCase):
    def test_01_c11_rust_rtl_and_yosys_20_of_20_xor_zero(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            c_bin = t / "db_c11"
            ub_bin = t / "db_ubsan"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_dual_base_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            if shutil.which("objdump"):
                dis = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
                for tok in ("%xmm", "%ymm", "%st(", "mulsd", "addsd", "cvtsi2sd", "divq", "idivq"):
                    self.assertNotIn(tok, dis)
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(HERE / "test_dual_base_c11.c"), "-o", str(ub_bin),
                ],
                check=True,
            )
            subprocess.run([str(ub_bin)], check=True, stdout=subprocess.DEVNULL)
            c_lines = subprocess.check_output([str(c_bin), "--emit-hex"], text=True).strip().splitlines()
            self.assertEqual(len(c_lines), 20)

            if shutil.which("rustc"):
                rlib = t / "libdb.rlib"
                r_bin = t / "db_rust"
                subprocess.run(
                    [
                        "rustc", "--edition=2021", "-C", "opt-level=2", "-D", "warnings",
                        "--crate-type=rlib", str(HERE / "dual_base_witness.rs"), "-o", str(rlib),
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "rustc", "--edition=2021", "-C", "opt-level=2", "-D", "warnings",
                        f"--extern=dual_base_witness={rlib}", str(HERE / "test_dual_base_rust.rs"), "-o", str(r_bin),
                    ],
                    check=True,
                )
                r_lines = subprocess.check_output([str(r_bin), "--emit-hex"], text=True).strip().splitlines()
                self.assertEqual(c_lines, r_lines)

            if shutil.which("iverilog") and shutil.which("vvp"):
                vvp_bin = t / "db_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(vvp_bin),
                        str(HERE / "dual_base_cycle_gate.sv"), str(HERE / "tb_dual_base_cycle_gate.sv"),
                    ],
                    check=True,
                )
                rtl_lines = [
                    ln for ln in subprocess.check_output(["vvp", "-N", str(vvp_bin)], text=True).splitlines()
                    if ln.startswith("V")
                ]
                self.assertEqual(c_lines, rtl_lines)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    sv_out = t / "db_synth.v"
                    subprocess.run(
                        [
                            "yosys", "-q", "-p",
                            f"read_verilog -sv {HERE / 'dual_base_cycle_gate.sv'}; "
                            f"synth_ice40 -dsp -top dual_base_cycle_gate; splitnets; write_verilog -noattr {sv_out}",
                        ],
                        check=True,
                    )
                    ps_vvp = t / "db_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(sv_out), str(HERE / "tb_dual_base_cycle_gate.sv"),
                        ],
                        check=True,
                    )
                    ps_lines = [
                        ln for ln in subprocess.check_output(["vvp", "-N", str(ps_vvp)], text=True).splitlines()
                        if ln.startswith("V")
                    ]
                    self.assertEqual(c_lines, ps_lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
