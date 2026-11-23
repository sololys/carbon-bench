# CARBON-59: SAMLET SPESIFIKASJON — KY-ENIGMA → NLK (`v1.0`)

> *«Så lenge maskinen leter etter en løsning, må den svette gjennom syklusene én etter én og betale i strøm og varme for hver eneste gren den prøver og forkaster. Men i det øyeblikket kandidatbanen legges frem for slusen som et utspent koordinatbrett $(q_0, q_1, \dots, q_K)$, er tiden borte — tilbake ligger bare et stumt, romlig arbeidstykke i stål som enten passer på tusendelen i tolken (OPEN), mangler siste brikke (HOLD), eller knekker mot malen (KILL).»*

**Status:** `L1 PASS (13/13, 0 float)` · `L2`-maskinvare i `HOLD`  
**Dato:** 2026-11-23  
**Grunnlag:** `kanonisk spesifikasjon (NLK)` · `KY-ENIGMA v1.1` · `Fase-speil × Enigma v1.0`  
**Domeneprefiks (vitnekjede):** `NLK-ENIGMA/v1.0`

> **Kardinalgrense:**
> `GENERERER != AUTORISERER != REALISERER != BEVISER`  
> `INSPIRED_BY != IMPLEMENTS != PROVES`
>
> Dette dokumentet spesifiserer en **seriekoblet, deterministisk arkitektur** der KY-Enigma og The Non-Lying Kernel (NLK) holdes strengt atskilt i to påfølgende lag. KY-Enigma er en reversibel demonstrator — **ikke** kryptografisk sikkerhet for sensitive data. Permutasjonsalgebra alene beviser ikke fysisk nullentropi. Programvarejournalen er en *append-only* SHA-256-hashkjede, ikke fysisk WORM-media.

---

## I. Arkitektonisk prinsipp: Seriekobling, aldri sammensmelting

KY-Enigma og NLK kan og skal **ikke** smeltes sammen til én felles autoritet. Dersom chiffergeneratoren selv kan låse neste rotortilstand eller drive en utgang, bryter hele hovedloven i både `kanonisk spesifikasjon` og `KY-ENIGMA v1.1`.

I stedet settes de opp i en **hard to-stegs serie** over konsekvensgrensen:

1. **Indre lag — KY-Enigma (`Φ` / reversibelt speilrom, `0,00 V DC`):**  
   Beregner et kandidattegn $y_{\mathrm{cand}} = E_{q_{\mathrm{prop}}}(x)$ og foreslår neste rotortilstand $q_{\mathrm{prop}}$. Har **null skrivetilgang** til autorisert tilstand $q_{\mathrm{auth}}$, vitnejournal $\mathcal{W}$ eller fysiske utganger.
2. **Ytre lag — NLK (`Π_K -> Ω` / ubestikkelig giljotin):**  
   Mottar kandidaten på evalueringssnittet `⬡`, kjører *Ma'ats Fjær* rundtur-sjekk, kontrollerer konserverings-, terskel- og sekvenskrav med **eksakt aritmetikk (`0 float`)**, og håndhever `KILL > HOLD > OPEN`. Bare ved `OPEN` forpliktiges $q_{\mathrm{auth}} \leftarrow q_{\mathrm{prop}}$ varig i $\mathcal{W}$ før én atomisk utgangskommando slippes gjennom.

```text
  INNGANG (x_in, event_id, seq, q_auth)
                   │
                   ▼
  ┌───────────────────────────────────────────────────────────┐
  │  LAG 1: KY-ENIGMA v1.1  (Φ — Reversibelt NP-speil)        │
  │  • S = M ∘ P, pre-step q_prop, E_q = A_q^-1 ∘ R ∘ A_q     │
  │  • 0,00 V DC | ingen mutasjon av q_auth | ingen dispatch  │
  └─────────────────────────────┬─────────────────────────────┘
                                │  kandidat (y_cand, q_prop) ved ⬡
                                ▼
  ┌───────────────────────────────────────────────────────────┐
  │  LAG 2: NLK kanonisk spesifikasjon    (Π_K -> Ω — Absolutt forrigling)  │
  │  • Ma'ats Fjær: E_{q_prop}(y_cand) == x_in og y_cand != x │
  │  • 0 float: heltall / brøk (Fraction), NaN/Inf avvist     │
  │  • Sekvens (seq > seq_prev), Landauer-gulv, profilsjekk   │
  │  • Subsumpsjon: KILL (0,00 V) > HOLD (0,00 V) > OPEN      │
  └──────────────┬─────────────────────────────┬──────────────┘
                 │                             │
         HOLD eller KILL                     OPEN
                 │                             │
                 ▼                             ▼
  ┌──────────────────────────┐  ┌─────────────────────────────┐
  │  AVVIST / SPERRET        │  │  VARIG FØR-UTFØRELSE (◉)    │
  │  • q_prop kastes         │  │  • Skriv SHA-256 WAL først  │
  │  • q_auth forblir frosset│  │  • q_auth <- q_prop         │
  │  • Utgang = 0,00 V DC    │  │  • Atomisk enkeltdiff (1):  │
  │  • KILL låses til reset  │  │    L1: SIMULATED_EFFECT     │
  │  • Hendelse logges i WAL │  │    L2: Verifisert 5,00 V DC │
  └──────────────────────────┘  └─────────────────────────────┘
```

---

## II. Det felles matematiske hengslet (Ma'ats Fjær = Konjugert involusjon)

Selve grunnen til at KY-Enigma og NLK låser rett inn i hverandre uten kunstig lim, er at de deler samme algebraiske lov:

* **I KY-Enigma v1.1 (§4):**  
  For enhver gyldig rotortilstand $q$ er fremoverkjeden $A_q = F_3 \circ F_2 \circ F_1 \circ M \circ P$ en eksakt bijeksjon på $\{0, \dots, 25\}$, og reflektoren $R$ oppfyller $R^2 = I$ samt $R(z) \neq z$ for alle $z$. Dermed blir den sammensatte transformasjonen en konjugert, fikspunktfri involusjon:
  $$E_q = A_q^{-1} \circ R \circ A_q, \qquad E_q\big(E_q(x)\big) = x, \qquad E_q(x) \neq x.$$

* **I NLK `kanonisk spesifikasjon` (§2 — Ma'ats Fjær):**  
  NLK krever en eksakt rundtur-involusjon $F(F(s)) = s$ der enhver bit-feil i register eller minne hindrer kansellering og utløser `GATE::KILL`.

* **Koblingen på evalueringssnittet `⬡`:**  
  NLK evaluerer den foreslåtte overgangen $(x_{\mathrm{in}}, y_{\mathrm{cand}}, q_{\mathrm{prop}})$ direkte mot sin egen kopi av de verifiserte tabellene:
  $$\Delta_{\mathrm{inv}} = 0 \;\iff\; E_{q_{\mathrm{prop}}}(y_{\mathrm{cand}}) = x_{\mathrm{in}} \;\land\; y_{\mathrm{cand}} \neq x_{\mathrm{in}}.$$
  Enhver manipulert chifferverdi, forstyrret rotorposisjon eller korrupt minnecelle gir $\Delta_{\mathrm{inv}} \neq 0$ og utløser umiddelbar `KILL`.

* **Reversibelt faseminne (Dok. 78 / LIFO):**  
  Når en autorisert overgang $(q_{\mathrm{prop}}, x_{\mathrm{in}}, y_{\mathrm{cand}})$ lagres på en LIFO-stabel for reversering (*uncomputing*), skal NLK ved utpopping verifisere $E_{q_{\mathrm{prop}}}(y_{\mathrm{cand}}) = x_{\mathrm{in}}$. Avvik på stabelen utløser `KILL`.

---

## III. Forent 8-trinns tilstandsgrammatikk

Alle transaksjoner passerer eksakt åtte navngitte tilstander fra hvile til observert (eller simulert) konsekvens. `q_auth` kan **kun** endres i trinn `◉`.

| Trinn | Symbol | Tilstand | Lag | Mutasjon av `q_auth` | Nominelt utgangsnivå | Tillatt påstand |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| **0** | `0` | `REST` | Felles | Nei | `0,00 V DC` | Ingen aktiv transaksjon |
| **1** | `○` | `KEY_PRESS` | KY-Enigma | Nei | `0,00 V DC` | Gyldig ASCII `A`–`Z` mottatt; ugyldig tegn avvises uten skritt |
| **2** | `◇` | `VALIDATED_INPUT` | KY-Enigma | Nei | `0,00 V DC` | Pluggbrett $P$ og bijeksjon $M$ anvendt; $q_{\mathrm{prop}}$ foreslått |
| **3** | `□` | `PROPOSED_STEP` | KY-Enigma | Nei | `0,00 V DC` | Fremoverrotorer $F_3 \circ F_2 \circ F_1$ evaluert ved $q_{\mathrm{prop}}$ |
| **4** | `△` | `PERMUTED_CANDIDATE` | KY-Enigma | Nei | `0,00 V DC` | Reflektor $R$ anvendt ($R^2 = I, \; R(z) \neq z$) |
| **5** | `⬡` | `GATE_EVALUATION` | NLK (`Π_K`) | Nei | `0,00 V DC` | Inversbane fullført; NLK evaluerer involusjon, regler og terskler |
| **6** | `◉` | `COMMITTED_STEP` | NLK (`Ω`) | **Ja (kun `OPEN`)** | `0,00 V DC` | Beslutning, `event_id` og $q_{\mathrm{auth}} \leftarrow q_{\mathrm{prop}}$ skrevet varig i WAL |
| **7** | `1` | `CONSEQUENCE` | Utgang / Vitne | Nei | `L1`: `SIMULATED_EFFECT` / `L2`: `5,00 V DC` | Faktisk eller simulert effekt logget med eksplisitt `observation_status` |

> **Regel for `◉` vs. `1`:** At en beslutning er forpliktet i `◉`, betyr **ikke** at en fysisk lampe har tent eller at et relé har slått inn. I programvaresimulering (`L1`) skal siste trinn alltid hete `SIMULATED_EFFECT`.

---

## IV. NLK-forrigling, subsumpsjon og eksakt aritmetikk (`0 float`)

### 1. Subsumpsjonshierarki
$$\mathbf{KILL}\ (0{,}00\,\text{V DC}) \;\succ\; \mathbf{HOLD}\ (0{,}00\,\text{V DC}) \;\succ\; \mathbf{OPEN}$$

* **Ussas lov (`kanonisk spesifikasjon` §1):** Porten kutter til `0,00 V DC` uavhengig av intensjon eller kontekst.
* **Klebrig `KILL`:** Når porten har gått i `KILL`, forblir den låst ved `0,00 V DC` gjennom alle etterfølgende kall inntil eksplisitt operatør-reset med bestått selvtest. Reset legges til i vitnehistorikken — den sletter aldri tidligere hendelser.
* **Tid alene åpner aldri porten:** `HOLD` går aldri over til `OPEN` bare fordi tid passerer.

### 2. Eksakt aritmetikk i portlogikk (`0 float`)
IEEE 754 flyttall (`float` / `double`) er forbudt i alle portavgjørelser og terskelsammenligninger:
* **Diskret basisprofil (`KY-ENIGMA v1.1` §6.1):** Bruker utelukkende eksakte heltallspermutasjoner på $\{0, \dots, 25\}$. Har ingen bokstavderivert $f'$.
* **Valgfri kontinuerlig måleprofil (`KY-ENIGMA v1.1` §6.2):** Alle måle- og usikkerhetstall ($e, \sigma$) representeres som eksakte heltall eller rasjonale brøker (`Fraction`, evt. fastpunkt med dokumentert avrunding). `NaN` og `Inf` avvises før evaluering:
  * $e < \frac{9}{10}\sigma \implies$ kandidat til **OPEN** (forutsatt at alle øvrige NLK-krav passerer).
  * $\frac{9}{10}\sigma \le e \le \frac{3}{2}\sigma \implies$ **HOLD** (likhet ved begge grenser gir alltid `HOLD`).
  * $e > \frac{3}{2}\sigma \implies$ **KILL**.
  * Manglende, ikke-positiv eller utløpt $\sigma$ eller $e \implies$ **HOLD**.

### 3. Komplett beslutningsmatrise

| Tilstand / Avvik | Årsakskode | Vedtak | Effekt på `q_auth` |
| :--- | :--- | :---: | :--- |
| Alle NLK- og Enigma-krav bestått + gyldig bevis-ID | `OK_VERIFIED` | **OPEN** | $q_{\mathrm{auth}} \leftarrow q_{\mathrm{prop}}$ etter varig WAL |
| Involusjonsbrudd ($E_{q_{\mathrm{prop}}}(y_{\mathrm{cand}}) \neq x_{\mathrm{in}}$) | `ERR_INVOLUTION_BREACH` | **KILL** | Frosset |
| Fikspunkt oppdaget ($y_{\mathrm{cand}} = x_{\mathrm{in}}$) | `ERR_FIXED_POINT_VIOLATION` | **KILL** | Frosset |
| Uautorisert mutasjon av $q_{\mathrm{auth}}$ før `◉` | `ERR_STATE_BYPASS` | **KILL** | Frosset |
| Ugyldig bijeksjon i rotor, $P$, $M$ eller $R$ | `ERR_TABLE_INTEGRITY` | **KILL** | Frosset |
| Målefeil $e > \frac{3}{2}\sigma$ eller korrupt vitnekjede | `ERR_THRESHOLD_OR_WAL_BREACH` | **KILL** | Frosset |
| Gratis bitsletting ($Q_{\mathrm{diss}} < Q_{\mathrm{Landauer}}$ ved irreversibel gren) | `ERR_LANDAUER_VIOLATION` | **KILL** | Frosset |
| Konserverings- eller Ostrogradsky-brudd (når koplet til fysisk profil) | `ERR_CONSERVATION_VIOLATION` | **KILL** | Frosset |
| Målefeil i randsonen $\frac{9}{10}\sigma \le e \le \frac{3}{2}\sigma$ | `HOLD_BOUNDARY_BAND` | **HOLD** | Frosset |
| Manglende/utløpt autorisasjon, ikke-monoton `seq` eller duplikat `event_id` | `HOLD_AUTH_OR_REPLAY` | **HOLD** | Frosset |
| Uverifisert fysisk maskinvareprofil for `L2`-dispatch | `HOLD_UNVERIFIED_HW_PROFILE` | **HOLD** | Frosset |
| Krasj mellom `◉` og `1` ved gjenoppstart | `OUTCOME_UNKNOWN` | **HOLD** | Frosset (ingen redispatch) |

> **Maskinvaretid (`L2`):** `kanonisk spesifikasjon` §3 setter målet $\tau_{\mathrm{cut}} \le 15\,\mathrm{ns}$ for en dedikert hardware-komparator ved fysisk forrigling. I ren `L1`-programvare dokumenteres dette som et `L2`-målkrav — aldri som målt programvareytelse.

---

## V. Krasjdisiplin, deduplisering og kanonisk vitnekjede

1. **Varig før-utførelse (Durable-First):**  
   Ved `OPEN` skrives beslutningsposten til $\mathcal{W}$ (med `fsync` i filbasert drift) **før** utgangskommandoen sendes. Dersom journalskriving feiler, stanses transaksjonen i `HOLD` uten dispatch og uten å oppdatere $q_{\mathrm{auth}}$.
2. **Atomisk engangsbruk:**  
   Hver autorisasjon er bundet til `(event_id, seq, config_hash, x_in, y_cand, q_before, q_prop)` med strengt økende `seq > seq_prev`. En autorisasjon kan aldri forbrukes to ganger.
3. **Krasjvinduet (`OUTCOME_UNKNOWN`):**  
   Krasjer systemet etter at `◉` er lagret, men før `1` er bekreftet, skal oppstartsgjenvinning sette status `OUTCOME_UNKNOWN` og låse porten i `HOLD`. **Automatisk gjentakelse (redispatch) er forbudt.**
4. **Kanonisk vitnepost (`NLK-ENIGMA/v1.0`):**  
   Hver post (også `HOLD`, `KILL`, `OUTCOME_UNKNOWN` og `RESET`) forsegles med SHA-256 over en entydig, lengdeprefikset bytekoding med domeneprefiks `NLK-ENIGMA/v1.0` (aldri løs strengkonkatenering) over feltene:
   `schema_version`, `event_id`, `seq`, `config_hash`, `x_in`, `y_cand`, `q_before`, `q_after`, `involution_ok`, `gate_decision`, `reason_code`, `dispatch_status`, `observation_status`, `prev_record_hash`.
5. **Ærlig observasjonsstatus:**  
   `observation_status` skal alltid være én av: `SIMULATED`, `OBSERVED_ELECTRICAL`, `OBSERVED_OPTICAL`, `FAILED` eller `OUTCOME_UNKNOWN`. Kommandert spenning skal aldri logges som målt spenning.

---

## VI. Påkrevd samsvarsmatrise for `L1`-implementasjon

Ingen implementasjon av `KY-Enigma -> NLK` kan merkes `L1 PASS` før samtlige 12 tester nedenfor er kjørt grønt med `0 float` (AST-verifisert) i portlogikken:

| Test-ID | Krav | Beståttkriterium |
| :--- | :--- | :--- |
| `T01` | Tabellbijeksjon | Rotorer, $P$ og $M$ er eksakte bijeksjoner på `0..25`; $R^2 = I$ og $R(x) \neq x$ |
| `T02` | Konjugert involusjon | $E_q(E_q(x)) = x$ og $E_q(x) \neq x$ for alle 26 tegn og deklarerte rotor-/ringprofiler |
| `T03` | Meldingsrunde | Tur-retur fra samme starttilstand gjenoppretter hele teksten inkl. hakk og *double-step* |
| `T04` | Sabotasje av involusjon | Manipulert $y_{\mathrm{cand}}$ eller $q_{\mathrm{prop}}$ mellom Lag 1 og Lag 2 utløser umiddelbar `KILL` |
| `T05` | Fikspunkt-sabotasje | Injisert $y_{\mathrm{cand}} = x_{\mathrm{in}}$ utløser umiddelbar `KILL` |
| `T06` | Tilstandsisolasjon | `HOLD` og `KILL` fryser $q_{\mathrm{auth}}$ eksakt; ingen utgangskommando sendes |
| `T07` | Klebrig `KILL` + reset | `KILL` blokkerer etterfølgende gyldige kall inntil eksplisitt reset + selvtest; historikk bevares |
| `T08` | Eksakte terskler (`0 float`) | $e = \frac{9}{10}\sigma$ og $e = \frac{3}{2}\sigma$ gir `HOLD`; `NaN`/`Inf` avvises; AST-sjekk bekrefter `0 float` |
| `T09` | Replay og sekvens | Duplikat `event_id` eller `seq <= seq_prev` gir `HOLD`, aldri dobbel dispatch |
| `T10` | Varig før-utførelse | Simulert WAL-feil stanser før dispatch og holder $q_{\mathrm{auth}}$ uendret |
| `T11` | Krasjvindu | Avbrudd etter `◉` før `1` gir `OUTCOME_UNKNOWN` + `HOLD` ved oppstart; ingen auto-redispatch |
| `T12` | Vitnekjede & LIFO | Endring av ett felt bryter SHA-256-kjeden; korrupt LIFO-uncompute utløser `KILL` |
| `T13` | Koordinatbrett-tolk | Utspent brett $(q_0, \dots, q_K)$ gir `OPEN` ved eksakt passform, `HOLD` ved manglende brikke, `KILL` ved skjøtbrudd |

---

## VII. Status ved utgivelse

* **Arkitekturspesifikasjon (`KY-Enigma -> NLK`):** `SPESIFISERT` (`CARBON-59`).
* **`L1`-referansemotor og testsuite (`T01`–`T13`):** **`L1 PASS` (`13/13`, `0 float` AST-verifisert)** i `60_nlk_enigma_unified_gate.py`.
* **`L2`-maskinvareforrigling (`<= 15 ns`, elektrisk/optisk verifisering):** `HOLD`.
* **Kryptografisk sikkerhet for sensitive data:** **ikke etablert** (utenfor virkeområdet).
