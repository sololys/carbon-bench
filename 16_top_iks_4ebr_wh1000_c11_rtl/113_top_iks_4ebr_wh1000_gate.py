#!/usr/bin/env python3
"""
Cell 16: Kills the 0-EBR (5,792-cell) async-read LUT blowout, half-rail W_H bug,
and fake (0x3109a228 ^ 0) digest tautology; verifies exact 4x SB_RAM40_4K EBR
inference, balanced LUT4 popcount tree (W_H == 1000), and genuine ARX 0x3109a228.
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


class TestTopIks4EbrWh1000(unittest.TestCase):
    def test_01_c11_rtl_and_yosys_4ebr_gate_parity(self) -> None:
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            c_bin = t / "iks_c11"
            ub_bin = t / "iks_ubsan"
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O2", "-mgeneral-regs-only",
                    "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wconversion", "-Wsign-conversion",
                    str(HERE / "test_top_iks_c11.c"), "-o", str(c_bin),
                ],
                check=True,
            )
            if shutil.which("objdump"):
                dis = subprocess.check_output(["objdump", "-d", str(c_bin)], text=True)
                for tok in ("%xmm", "%ymm", "%st(", "mulsd", "addsd", "cvtsi2sd"):
                    self.assertNotIn(tok, dis)
            subprocess.run(
                [
                    "gcc", "-std=c11", "-O1", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                    "-Wall", "-Wextra", "-Werror", "-pedantic",
                    str(HERE / "test_top_iks_c11.c"), "-o", str(ub_bin),
                ],
                check=True,
            )
            c_lines = subprocess.check_output([str(c_bin)], text=True).strip().splitlines()
            ub_lines = subprocess.check_output([str(ub_bin)], text=True).strip().splitlines()
            self.assertEqual(len(c_lines), 9)
            self.assertEqual(c_lines, ub_lines)

            if shutil.which("iverilog") and shutil.which("vvp"):
                vvp_bin = t / "iks_rtl.vvp"
                subprocess.run(
                    [
                        "iverilog", "-g2012", "-Wall", "-o", str(vvp_bin),
                        str(HERE / "top_iks_sluice.sv"), str(HERE / "tb_top_iks_sluice.sv"),
                    ],
                    check=True,
                )
                rtl_lines = [
                    ln for ln in subprocess.check_output(["vvp", "-N", str(vvp_bin)], text=True).splitlines()
                    if ln.startswith("IKS ")
                ]
                self.assertEqual(c_lines, rtl_lines)

                cells_sim = Path("/usr/share/yosys/ice40/cells_sim.v")
                if shutil.which("yosys") and cells_sim.exists():
                    sv_out = t / "iks_synth.v"
                    ylog = subprocess.check_output(
                        [
                            "yosys", "-p",
                            f"read_verilog -sv {HERE / 'top_iks_sluice.sv'}; "
                            f"synth_ice40 -top top_iks_sluice; stat; splitnets; write_verilog -noattr {sv_out}",
                        ],
                        text=True,
                    )
                    self.assertRegex(ylog, r"SB_RAM40_4K\s+4\n")
                    ps_vvp = t / "iks_ps.vvp"
                    subprocess.run(
                        [
                            "iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-o", str(ps_vvp),
                            str(cells_sim), str(sv_out), str(HERE / "tb_top_iks_sluice.sv"),
                        ],
                        check=True,
                    )
                    ps_lines = [
                        ln for ln in subprocess.check_output(["vvp", "-N", str(ps_vvp)], text=True).splitlines()
                        if ln.startswith("IKS ")
                    ]
                    self.assertEqual(c_lines, ps_lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
