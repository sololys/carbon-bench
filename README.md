# carbon-bench

> Før sjetongen slipper: kandidat (`NP`).  
> Klinket i bordplata: bruddprøve (`VS`).  
> Låst i regnskapet: realisert tilstand (`P`).

Dette er ikke et bibliotek og ikke et rammeverk. Det er **12 lukkede bruddprøver** som viser hvordan en konkret feil eller bløff i sanntids-, fysikk- eller portlogikk blir funnet, regnet ihjel og sveiset igjen i kjørbar kode.

- **Forfatter:** Marius Egerhei Torjusen (`ORCID: 0009-0006-0431-6637`)
- **Lisens:** Apache-2.0
- **Epistemisk grense:** `L1 Deterministisk Programvare` · `INSPIRED_BY != IMPLEMENTS != PROVES`

---

## Kontrakt

- **0 float:** Kun heltall, eksakte rasjonale brøker og bit-operasjoner (AST-/kodeskanner-verifisert).
- **0 eksterne avhengigheter:** Ren C11, C++17, Rust stdlib og Python stdlib.
- **Fail-Closed:** `OPEN` frigir. `HOLD` bevarer (`0.00 V DC`). `KILL` beskytter (`KILL > HOLD > OPEN`).
- **0 LEAKS:** Innebygd `make leak-check` vokter mot private stier og interne referanser.

---

## De 12 bruddprøvene

| Celle | Språk | Kjernebrudd (bløffen som drepes) | Søsterrom (`@sololys`) |
| :--- | :--- | :--- | :--- |
| **`01_omega_interlock_c11`** | C11 / KUnit | Kjernefrys holder vanlig GPIO `HØY`; krever AC-pulset `wdt_toggle` mot ladepumpe + autentisert buss-`CMD_KILL` | [omega-gate-qnx](https://github.com/sololys/omega-gate-qnx) |
| **`02_doc78_airlock_cpp17`** | C++17 | Tilstandsmutasjon før snapshot, `2^40`-kollisjon i `encode`, signed `int64_t` UB under ASan/UBSan | *(selvforsynt)* |
| **`03_ky_typestate_rust`** | Rust | `pub`-felt-bakdør forbi typestate, `f64` i portlogikk og tautologisk koherenstest | [epistemic-architectures](https://github.com/sololys/epistemic-architectures) |
| **`04_zero_volt_hold_py`** | Python | `2.50 V DC` i `HOLD` bryter eget teorem; skiller lyskjegle (`ds^2 <= 0`) fra `20 m` geofence | [epistemic-architectures](https://github.com/sololys/epistemic-architectures) |
| **`05_galvanic_ascii_py`** | Python | Uklokket snarvei og kryssende ledere i 2D PCB-skisse som kortslutter `HOLD`/`KILL` | [@sololys](https://github.com/sololys/sololys) |
| **`06_cayley_rotor_py`** | Python | Involusjonsbrudd på konveks mengde ($R_{N_K}(x)=\|x\|$) og uforkortede brøker i SHA-256 | *(selvforsynt)* |
| **`07_si_dimension_lock_py`** | Python | Enhetsbløff, lukkede intervallfeller og 7-tuppel SI-dimensjonslås (`X.01–X.09`) | [femos-biomimetic-nitrogenase](https://github.com/sololys/femos-biomimetic-nitrogenase) · [epistemic-architectures](https://github.com/sololys/epistemic-architectures) |
| **`08_nlk_enigma_split_py`** | Python | Sammensmelting av tilstandsløs transformasjon (Lag 1) og forrigling (Lag 2) skjuler krasj (`OUTCOME_UNKNOWN`) | *(selvforsynt)* |
| **`09_unfolding_dimension_lock_py`** | Python | Sirkulær $T^*_q M\text{-forutsetning}$ av 3D-rommet og 7D-oktonionbløff ($\dim\ker = 14$ spøkelsesplan, $\mathrm{SO}(7) \to G_2\text{-brudd}$ og brutt Jacobi-lås); utleder $V \cong \Lambda^2 V \otimes \Lambda^3 V \implies n = 3$ via Schurs lemma | [epistemic-architectures](https://github.com/sololys/epistemic-architectures) |
| **`10_k_filter_sluice_c11_rtl`** | C11 / RTL / Python | Skrivefri `kill_latched`, kausal overtelling (`valid_steps > total_steps`), `-2^63` speilbrudd og spornorm-rot i $d \ge 3$; sveiser $(3,4,5)\to(7,24,25)$ $\mathbb{Q}$-rekobling ($\Delta p = 576/625$) og `12/12 XOR == 0` mot `iCE40UP5K` (`14,87 MHz` post-PnR) | [ky-rox-public-demonstrators](https://github.com/sololys/ky-rox-public-demonstrators) |
| **`11_bell_ky_7qubit_cptp_c11_rtl`** | C11 / RTL / Python | Spor-divisjonsfelle ($M\rho M^\dagger / \operatorname{Tr}$), fortegnsblind $\lvert\Sigma_1^2 - \Sigma_2^2\rvert$ og `L1`-dekoherens i CHSH; sveiser sporlåst 128D 7-qubit $\mathbb{Q}\text{-CPTP}$, Frobenius-skraper og `22/22 XOR == 0` mot `iCE40UP5K` (`21,34 MHz` post-PnR) | [ky-rox-public-demonstrators](https://github.com/sololys/ky-rox-public-demonstrators) |
| **`12_omni_crash3_linf_c11_rtl`** | C11 / RTL / Python | IEEE-754 `NaN -> OPEN`-gjennomslipp, frakoblet $\dot{R} > \delta_R$ i vektet $L_1$-sum og tautologisk `(s^r)^r == s`; sveiser eksakt gullsnittring $\mathbb{Z}[\varphi]$, konjunktiv $L_\infty$-sluse og `22/22 XOR == 0` mot `iCE40UP5K` (`26,86 MHz` post-PnR) | [ky-rox-public-demonstrators](https://github.com/sololys/ky-rox-public-demonstrators) |

---

## Kjør alle 12 bruddprøver

```bash
make verify-all
```

Kommandoen kjører `leak-check` etterfulgt av samtlige 12 celler i C11 (`gcc -Werror`), C++17 (`g++ -Werror -fsanitize=address,undefined`), Rust (`rustc --test -D warnings`), SystemVerilog RTL (`iverilog`/`yosys`) og Python (`python3`).
