# carbon-bench — Deterministisk bruddprøve-benk (0 float, 0 eksterne pakker)
.PHONY: verify-all c11 cpp17 rust py leak-check clean

verify-all: leak-check c11 cpp17 rust py
	@echo "[PASS] Alle 8 celler verifisert (C11 + C++17 + Rust + Python)."

leak-check:
	@! grep -rnE "(/home/sololyset|AGENTS\.md|05_PATENTS|06_RESEARCH|09_SYSTEM|SPEC-[0-9]{3})" \
		--exclude="Makefile" . || (echo "[FAIL] Privat sti eller intern referanse funnet." && exit 1)
	@echo "[PASS] 0 LEAKS bekreftet."

c11:
	$(MAKE) -C 01_omega_interlock_c11 test

cpp17:
	g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic -Wconversion -Wsign-conversion \
		-fsanitize=address,undefined \
		02_doc78_airlock_cpp17/16_doc78_reversiblus_herdet_kjerne.cpp -o /tmp/cb_doc78
	/tmp/cb_doc78

rust:
	rustc --test -D warnings 03_ky_typestate_rust/26_ky_engine_v1_1_kappa27_herdet.rs -o /tmp/cb_ky_rust
	/tmp/cb_ky_rust

py:
	python3 04_zero_volt_hold_py/28_reismann_core_c0_c6_verifikasjon.py
	python3 05_galvanic_ascii_py/34_vertikal_loddsnor_galvanisk_sluse.py
	python3 06_cayley_rotor_py/14_dok78_cayley_rotor_og_konveks_moteksempel.py
	python3 07_si_dimension_lock_py/44_spraksluse_l1_gate.py
	python3 07_si_dimension_lock_py/46_fysisk_dimensjonslas_x07_x09.py
	python3 08_nlk_enigma_split_py/60_nlk_enigma_unified_gate.py

clean:
	$(MAKE) -C 01_omega_interlock_c11 clean
	rm -f /tmp/cb_doc78 /tmp/cb_ky_rust
