#!/usr/bin/env python3
"""
Cell 14: 3D Skeletal Grothendieck Sheaf Sluice (6 faces + 3 plaquettes) &
Division-Free Pseudo-Mersenne RNS + Compact-Support (iota_!) Involution Verifier.
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


class TestSheafRnsCompactNash(unittest.TestCase):
    def test_01_rns_compact_nash_division_free_c11_and_ubsan(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            b1 = t / "rns_c11"
            b2 = t / "rns_ubsan"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_rns_compact_nash_c11.c"), "-o", str(b1),
                ],
                check=True,
            )
            if shutil.which("objdump"):
                dis = subprocess.check_output(["objdump", "-d", str(b1)], text=True)
                for tok in ("%xmm", "%ymm", "%st(", "mulsd", "addsd", "cvtsi2sd"):
                    self.assertNotIn(tok, dis)
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(HERE / "test_rns_compact_nash_c11.c"), "-o", str(b2),
                ],
                check=True,
            )
            subprocess.run([str(b1)], check=True, stdout=subprocess.DEVNULL)
            subprocess.run([str(b2)], check=True, stdout=subprocess.DEVNULL)

    def test_02_sheaf_3d_c11_rust_rtl_and_yosys_16_of_16_xor_zero(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            c_bin = t / "sheaf_c11"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_sheaf_sluice_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            c_lines = subprocess.check_output([str(c_bin)], text=True).strip().splitlines()
            self.assertEqual(len(c_lines), 16)

            if shutil.which("rustc"):
                rlib = t / "libsheaf.rlib"
                r_bin = t / "sheaf_rust"
                subprocess.run(
                    [
                        "rustc", "--edition=2021", "-C", "opt-level=2", "-D", "warnings",
                        "--crate-type=rlib", str(HERE / "sheaf_curry_howard.rs"), "-o", str(rlib),
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "rustc", "--edition=2021", "-C", "opt-level=2", "-D", "warnings",
                        f"--extern=sheaf_curry_howard={rlib}", str(HERE / "test_sheaf_rust.rs"), "-o", str(r_bin),
                    ],
                    check=True,
                )
                r_lines = subprocess.check_output([str(r_bin)], text=True).strip().splitlines()
                self.assertEqual(c_lines, r_lines)

            if shutil.which("iverilog") and shutil.which("vvp"):
                vvp_bin = t / "sheaf_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(vvp_bin),
                        str(HERE / "sheaf_sluice_3d.sv"), str(HERE / "tb_sheaf_sluice_3d.sv"),
                    ],
                    check=True,
                )
                rtl_lines = [
                    ln for ln in subprocess.check_output(["vvp", "-N", str(vvp_bin)], text=True).splitlines()
                    if ln.startswith("S")
                ]
                self.assertEqual(c_lines, rtl_lines)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    sv_out = t / "sheaf_synth.v"
                    subprocess.run(
                        [
                            "yosys", "-q", "-p",
                            f"read_verilog -sv {HERE / 'sheaf_sluice_3d.sv'}; "
                            f"synth_ice40 -top sheaf_sluice_3d; splitnets; write_verilog -noattr {sv_out}",
                        ],
                        check=True,
                    )
                    ps_vvp = t / "sheaf_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(sv_out), str(HERE / "tb_sheaf_sluice_3d.sv"),
                        ],
                        check=True,
                    )
                    ps_lines = [
                        ln for ln in subprocess.check_output(["vvp", "-N", str(ps_vvp)], text=True).splitlines()
                        if ln.startswith("S")
                    ]
                    self.assertEqual(c_lines, ps_lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
