# Benkrevisjon og herding av `KY Engine v1` ($\kappa_{27}$) $\to$ `v1.1`

```text
========================================================================================
DOKUMENT-ID             : CARBON-25 (REVISJON AV KY ENGINE KAPPA_27 OG NOTEBOOKLM-UTKAST)
KILDEFIL (OPPGRADERT)   : ky_engine_v1_kappa27.rs (Løftet v1.1, 15/15 PASS)
BENKEKOPI               : 03_ky_typestate_rust/26_ky_engine_v1_1_kappa27_herdet.rs (15/15 PASS, 0 float)
VERKTØYKJEDE            : rustc 1.63.0 (-D warnings, Edition 2015 & 2021, 0 crates)
EPISTEMISK STATUS       : L1 (lokalt demonstrert programvare; append-only SHA-256 != WORM)
KONTRAKTREGEL           : INSPIRED_BY != IMPLEMENTS != PROVES
========================================================================================
```

---

## 1. Hva NotebookLM-gjennomgangen traff helt rent på i `ky_engine_v1_kappa27.rs`

Alle de fire feilene som ble påpekt i gjennomgangen av `ky_engine_v1_kappa27.rs`, er reelle i nåværende `v1`-kode:

1. **Hull i `WitnessLog::append` og blind `verify_chain()` (`linje 459–497`):** `append` beregner kun 64-bits FNV-1a over `(prev_hash, event_id, operation)` og utelater `object_id`, `result`, `reason_code`, `timestamp`, `tau_coord` og `integrity_hash`. I tillegg sjekker `verify_chain()` bare at `ev.prev_hash == expected_prev` uten å rekalkulere `event_hash`. Dermed kan `ev.result = GateStatus::Open` muteres fritt i RAM mens `verify_chain()` fortsatt returnerer `true`.
2. **Runtime-`enum` i stedet for kompileringstids typestate (`linje 15–21, 506–507`):** Både `world_state` og `blueprints` lagrer ubeskyttede `Record`-instanser, slik at Rust-kompilatoren ikke hindrer feilaktig innsetting i `world_state` før `Committed`.
3. **Irreversibilitetsflagget `!` kastes i `GeneratorPhi::generate` (`linje 230, 286`):** `Parser::parse` leser ut `irreversible_flag` ved `!`, men `GeneratorPhi` setter `audit_required: raw.audit_flag` og ignorerer `raw.irreversible_flag`. En irreversibel kommando med `!` uten `#` slipper dermed rett gjennom uten revisjonskrav.
4. **Evig taus `HOLD` i `blueprints` uten klokkelov (`linje 588–592`):** `blueprints` lagrer `Hold`-utkast på ubestemt tid uten `created_tick`, `max_hold_ticks`, defektetikett eller autoritetseskalering (`P_int -> P_ext`).

---

## 2. Seks feil og blindsoner vi avdekket i selve utkastet og i `v1` på benken

Når vi prøver det foreslåtte Rust-utsnittet fra gjennomgangen direkte mot `rustc 1.63.0` og mot korpusets egne lover (portkontrakten, `light_bridge.gd`, `CARBON 02` og `CARBON 23/24`), ryker seks punkter som må tettes før innfelling:

| Funn | Hva som sviktet i utkastet / `v1` | Hvordan det er sveiset i `26_ky_engine_v1_1_kappa27_herdet.rs` |
| :--- | :--- | :--- |
| **`K1` Åpne `pub`-felt og blindlås i `try_commit()`** | Utkastet gjør alle felt på `Record<State>` `pub`, setter `gate_status: GateStatus::Hold` i `into_estimate`, oppdaterer den aldri i `into_struct` / `into_viability`, og lar `try_commit()` kun sjekke `self.gate_status == GateStatus::Open`. Enten låser `try_commit()` seg alltid, eller så muterer kaller `rec.gate_status = GateStatus::Open` direkte via det åpne `pub`-feltet og omgår hele `GateOmega`! | Forseglet `LifecyclePhase`-trait (`mod sealed`), **private** felt på `Record<S>` med rene lesemetoder, og `GateOmega::admit(...)` som den **eneste** konstruktørveien som kan utstede `Record<Committed>` (og som konsumerer og destruerer kandidaten ved verdi på `Kill`). |
| **`K2` Kompileringsbrudd på `rustc 1.63.0` (`E0271`) + svak hash** | Ved vanlig `rustc`-kall (Edition 2015-standard) feiler `prev_hash.to_le_bytes().into_iter().chain([self.result as u8, ...])` med `error[E0271]: expected &u8, found u8`. I tillegg manglet `tau_coord` fortsatt i utkastets hash, strengkonkatenering uten lengdeprefiks tillot grenseforskyvnings-kollisjoner (`"AB"\|\|"C"` vs. `"A"\|\|"BC"`), og 64-bits FNV-1a er lineært inverterbar. | Byttet til ren Rust **FIPS 180-4 SHA-256 (`[u8; 32]`)** (verifisert mot NIST-vektorene `""` og `"abc"`) med eksplisitt `u64`-lengdeprefikset strenginnkoding over *samtlige* 14 felt inkl. `tau_coord`, `actuator_mv` og `hold_authority`. Kompilerer uten advarsler i både Edition 2015 og 2021. |
| **`K3` Skjulte IEEE-754 `f64` midt i portlogikken** | `v1` bruker `f64` i `etor_risk_pi`, `pre_commit_g`, `clamp01` og `NashResidual::norm().sqrt()` (`linje 69–72, 140–190, 422–427`). | **0 forekomster av `f32`/`f64`** i hele filen (voktet av kildekode-skanner i `test_15`): promille-heltall `u16`/`i64` for `etor_risk_permille` og `pre_commit_g_milli`, samt eksakt forkortet brøkaritmetikk `RatioI128` (`gcd_u128`) og kvadratnorm $\|N(x)\|^2 \le \varepsilon^2$ i `NashResidualQ`. |
| **`K4` Manglende `RealityForge`-invarianter (`light_bridge`)** | Verken `v1` eller utkastet krevde ikke-tom `evidence_id` for `OPEN`, okkupert bro-sone var udefinert, spenningsloven (`0 mV` i `HOLD`/`KILL`) manglet, og `KILL`-reset var ikke vitneført. | Alle fem invarianter er låst i `KyEngine`: (1) `HOLD` åpner aldri av tid alene, men eskalerer `P_int -> P_ext` etter `max_hold_ticks`; (2) `OPEN` krever ikke-tom `evidence_id`; (3) `zone_occupied == true` utsetter i `HOLD` (`ZoneOccupiedDefer`); (4) `KILL` kutter til `0 mV`, fjerner `blueprints` og setter `killed_objects`-lås; (5) `reset_kill_latch` føyer `RESET_BY_L01` til `WitnessLog` uten å slette historikk. |
| **`K5` Vakuøs tautologi i `IksCoherenceTest`** | I `v1` (`linje 127–135`) var `involution_transform` kun `s.chars().rev().collect()`. Å reversere gyldige UTF-8 `char`-sekvenser to ganger gir `true` for **100 %** av alle Rust-`&str` — så `FailureCode::IksReversibilityFailed` var død, uoppnåelig kode! | `IksCoherenceTest` sjekker nå kanonisk segmentstruktur, avviser tapspreget dekoding (`U+FFFD`) og kontrolltegn, og kjører involutiv kodek-rundtur (`test_09`). |
| **`K6` Lukket bro mot *Poncare.Game* / Moreau & Cayley (`SO(2)`)** | Punkt 2 nederst i gjennomgangen sto som et åpent veivalg uten kode. | Implementert direkte som `PoincareMoreauWorldRules` + `cayley_so2_step_exact` i samme fil (`test_13`): kobler `WorldRules` til $h(x) = \|x\|^2 - R_k^2 \le 0$, $b(x) = -h(x) \ge 0$, krympende $S_A(R_k) = \emptyset \implies \text{Kill}$, Moreaus dualkjeglespalting $\sigma = \langle x, v \rangle$ mot tretthetsbudsjett $\mu$, og eksakt rasjonal `SO(2)`-glidning på Knivseggen ($10\times$ resonans). |

---

## 3. Verifikasjon på benken

Kjørt lokalt på `rustc 1.63.0` med `-D warnings` og `#![forbid(unsafe_code)]`:

```bash
rustc -D warnings 03_ky_typestate_rust/26_ky_engine_v1_1_kappa27_herdet.rs -o /tmp/ky_v1_1 && /tmp/ky_v1_1
rustc --test -D warnings 03_ky_typestate_rust/26_ky_engine_v1_1_kappa27_herdet.rs -o /tmp/ky_v1_1_t && /tmp/ky_v1_1_t
rustc --edition 2021 --test -D warnings 03_ky_typestate_rust/26_ky_engine_v1_1_kappa27_herdet.rs -o /tmp/ky_v1_1_t21 && /tmp/ky_v1_1_t21
```

Resultat: **`15/15 PASS`** i både Edition 2015 og Edition 2021, `0` kompilatoradvarsler, `0` eksterne crates og `0` flyttall.
