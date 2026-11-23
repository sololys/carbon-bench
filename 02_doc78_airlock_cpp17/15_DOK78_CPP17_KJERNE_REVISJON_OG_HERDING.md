# Dokument 78 i C++17: Benkrevisjon og Herding av Reversiblus-kjernen

> **Grenseoppgang:** `INSPIRED_BY != IMPLEMENTS != PROVES`. All kode her er `L1` (lokalt demonstrert C++17-programvare kompilert og kjørt på `g++ (Debian 12.2.0-14+deb12u1) 12.2.0`). Programvarebaserte vitnelogger er append-only `SHA-256`-hashkjeder i minne/fil, **ikke** fysisk WORM-maskinvare. Originalkilden `78_TIDSREVERSIBEL_INVOLUSJONSDYNAMIKK_OG_FASEMINNE.tex` står fortsatt helt urørt i arkivet.

---

## 1. Hva som bærer ekte vekt i Reversiblus-utkastet (`BEVARES`)

Tre byggesteiner i det innsendte C++17-utkastet er håndverksmessig sterke og er tatt rett videre inn i den herdede kjernen `16_doc78_reversiblus_herdet_kjerne.cpp`:

* **Flyttallsfri `constexpr` FIPS 180-4 SHA-256-motor:** Utledningen av alle 8 startord (`IV`) og 64 rundekonstanter (`RC`) ved kompilering via 128-bits heltallsbiseksjon (`mul64` / `mul128_u64` for $p \le 311$) er eksakt, fri for tabell-magi og fri for flyttall.
* **Bijektiv 1000-trinns Feistel-/paritetskaskade med `LIFO`-faseminne:** Partnerdimensjonen $p(k) = (613k + 37) \bmod 1000$ oppfyller $p(k) \neq k$ for alle $k \in \{0,\dots,999\}$ (siden $\gcd(612, 1000) = 4 \nmid 963$). Dermed kobles kandidatpådrag, dobbeltlagsfase $\delta\phi_{\mathrm{dl}}$, arbeidsstakk `scratchpad` og $\mathbb{Z}_2^{1000}$ uten tap under $U_{1000}\cdots U_1$, og 1-bits lekkasje i både tilstand og `LifoPhaseMemory` fanges umiddelbart.
* **Galvanisk dødtid mot shoot-through:** Overgangsloven $+1 \to 0/\mathrm{HOLD} \to -1$ stopper direkte polaritetsvending mellom anodisk og katodisk pådrag.

---

## 2. Seks feil og sikkerhetsbrudd som knakk under benkprøving (`RETTET I CARBON/16`)

Da vi la råutkastet direkte på `g++ 12.2.0` på Debian Linux med `-std=c++17 -O2 -Wall -Wextra -Werror -pedantic` og deretter under `-fsanitize=undefined,address`, brast seks punkter som er herdet i `16_doc78_reversiblus_herdet_kjerne.cpp`:

### Brudd 1 — Kompilerer ikke under oppgitt `g++ -std=c++17`-kommando på Debian

* **Feil i råkoden:** `struct FaultInjection` er deklarert *inne i* klassen `ReversiblusGateMachine` med medlemsinitialiserere (`bool flip_rev_bit_during_hold{false}; ...`) og brukt som standardargument `FaultInjection fault = {}` på linje 456 før den omsluttende klassen er lukket med `};`. På Debian `g++ 12.2.0` avbryter kompilatoren med:
  `error: could not convert '<brace-enclosed initializer list>()' ... to 'ReversiblusGateMachine::FaultInjection'`.
* **Herding:** `FaultInjection` løftes ut på navneromsnivå før `ReversiblusGateMachine`. Kjernen kompilerer nå med null advarsler under `-std=c++17 -O2 -Wall -Wextra -Werror -pedantic -Wconversion -Wsign-conversion`.

### Brudd 2 — Dobbelt luftslusebrudd: `2500 mV` i `HOLD` + skriving til `world_irr` *før* snapshot

* **Feil i råkoden:**
  1. Koden setter `v_hw_mv = 2500` (`2.50 V DC`) i `HOLD`. Hverken `78_TIDSREVERSIBEL_INVOLUSJONSDYNAMIKK_OG_FASEMINNE.tex` (`linje 129` og `linje 245`) eller portkontrakten har `2.50 V` i `HOLD`: før porten faller skal fysisk utgang være **`0 mV` (`0.00 V DC`)**; `5000 mV` legges *kun* ved `OPEN`.
  2. På linje 473–474 muterer `evaluate_and_commit` den levende omverdenen (`world_irr.v_hw_mv = 2500U;`) **før** den tar `irr_snapshot = codec::hash_s_irr(world_irr)`. Hvis systemet stod i `KILL` (`0 mV`) og mottar en ugyldig kandidat, pulserer utgangen opp til `2500 mV` og ned igjen til `0 mV` midt under prøvingen, samtidig som rapporten påstår `s_irr_untouched_in_airlock = true`!
* **Herding:** `v_hw_mv` er strengt **`0 mV`** i både oppstart, `HOLD`, `KILL` og `SAFE_STOP`. `irr_snapshot` tas gjennom en `const IrreversibleWorld&`-referanse helt øverst i luftslusen før noe berøres, og `world_irr` er skrivebeskyttet gjennom hele 1000-trinnsprøvingen.

### Brudd 3 — Skjult kollisjon i `encode_s_rev` bryter injektivitetskravet ($2^{40}$ skyggetilstander)

* **Feil i råkoden:** `hypercube_addr` er en 32-bits `uint32_t`, men `encode_s_rev` maskerer vekk de øvre 16 bitene (`& 0xFFFFU`), og `clean_psi.sanitize()` maskerer i stillhet vekk de 24 øvre bitene i `words[15]` før `SHA-256`. Dermed gir $2^{16 + 24} = 2^{40}$ ulike C++-tilstander **nøyaktig samme `SHA-256`-hash**, i strid med Dokument 78 sitt krav om at `encode` må være strengt injektiv.
* **Herding:** `hypercube_addr` er skjerpet til eksakt `uint16_t` (ingen døde biter), og `encode_s_rev` serialiserer alle 64 biter i `words[0..15]` rått uten maskering, mens $\Pi_K$ renser bit `40..63` i `words[15]`. Enhver innsmuglet padding-bit avsløres nå umiddelbart som `hash(proj_1) != pre_hash -> GATE :: KILL` (bevist i **PASS 7/9**).

### Brudd 4 — C++17 Undefined Behavior (`signed int64_t overflow`) i paritet og dobbeltlagsfase

* **Feil i råkoden:** `c = -c` på `int64_t` gir udefinert oppførsel (`UB`) i C++17 ved `c == INT64_MIN`, og `s.theta.delta_phi_dl_uv += delta_uv` over 1000 trinn gir `UB` ved verdier nær `INT64_MAX`/`INT64_MIN` fordi `project_admissible_pi_k` kun avgrenser `eta_uv`, ikke `field_3d` eller `delta_phi_dl_uv`.
* **Herding:** To-komplement wraparound via `uint64_t` (`wrapping_neg_i64`, `wrapping_add_i64`, `wrapping_sub_i64`) gjør selve trajektorieoperatorene 100 % UB-frie for *ethvert* 64-bits bitmønster, samtidig som $\Pi_K$ håndhever eksplisitte fysiske grenser på både `eta_uv`, `delta_phi_dl_uv` og `field_3d` (bevist under `-fsanitize=undefined,address` i **PASS 8/9**).

### Brudd 5 — Manglende `KILL`-lås og `WORM`-begrepsglidning

* **Feil i råkoden:** Etter 1-bits tilstandslekkasje i Vektor 2 og ulovlig shoot-through i Vektor 3 går portmaskinen rett tilbake til `OPEN` (`5000 mV`) i Vektor 4 uten noen loggført tilbakestilling. I tillegg kaller koden en vanlig `std::vector<Digest256>` i RAM for `worm_witness` og re-hasher hele vektoren i $O(N^2)$ tid.
* **Herding:** `GATE :: KILL` setter en hard `kill_latched_`-lås (`0 mV`). Porten kan kun gjenåpnes gjennom `reset_kill_latch(world, evidence_id)` med ikke-tom bevis-ID, som legger til et uforanderlig `RESET_AFTER_KILL`-ledd i en $O(1)$ `AppendOnlyHashChain` med full `verify_chain()`-kontroll (**PASS 4/9** og **PASS 9/9**).

### Brudd 6 — Manglende hovedakse-ortogonalitet for 4-legemerotoren (§4.3)

* **Feil i råkoden:** Råkoden utfører kun paritetsvending `c = -c`, uten å håndheve hovedakse-betingelsen $\mathbf{r}_0 \cdot \hat{n} = 0$ fra revisjonen i `13_DOK78_REVERSIBLUS_REVISJON_OG_SKRAPJERN.md`.
* **Herding:** `verify_counter_rotor_zero_momenta` krever $\hat{n} \neq \mathbf{0}$ og eksakt $\mathbf{r}_0 \cdot \hat{n} = 0$ for kontraroterende 4-legemepar, og stopper skrå rotorarm med `GATE :: KILL` (**PASS 9/9**).
