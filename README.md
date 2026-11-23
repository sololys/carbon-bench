# carbon-bench

> Før sjetongen slipper: kandidat (`NP`).  
> Klinket i bordplata: bruddprøve (`VS`).  
> Låst i regnskapet: realisert tilstand (`P`).

Dette er ikke et bibliotek og ikke et rammeverk. Det er **8 lukkede bruddprøver** som viser hvordan en konkret feil eller bløff i sanntids-, fysikk- eller portlogikk blir funnet, regnet ihjel og sveiset igjen i kjørbar kode.

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

## De 8 bruddprøvene

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

---

## Kjør alle 8 bruddprøver

```bash
make verify-all
```

Kommandoen kjører `leak-check` etterfulgt av samtlige 8 celler i C11 (`gcc -Werror`), C++17 (`g++ -Werror -fsanitize=address,undefined`), Rust (`rustc --test -D warnings`) og Python (`python3`).
