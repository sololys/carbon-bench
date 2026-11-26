# Virksomhetsovergripende Arkitekturstandard for Feilsikre Konsekvensporter og Lagdelte Kontrollhierarkier (`Reismann-Core` & Kontrollag `C0`–`C6`)

```text
========================================================================================
DOKUMENT-ID             : CARBON-27 (REVIDERT REISMANN-CORE ARKITEKTURSTANDARD)
VERIFIKASJONSMOTOR      : 04_zero_volt_hold_py/28_reismann_core_c0_c6_verifikasjon.py (8/8 PASS, 0 float)
EPISTEMISK DEMARKASJON  : Bevisnivå L0 (fysikk/matematikk) · L1 (lokal programvare)
                          L2/L3 (fysisk maskinvare i HOLD inntil benk-/feltvitne foreligger)
KONTROLLSTAKK           : Kontrollag C0–C6 (skilt fra bevisnivåene L0–L3!)
KONTRAKTREGEL           : INSPIRED_BY != IMPLEMENTS != PROVES
========================================================================================
```

> **Verkstedmerknad (`Celle 04`):** Dette er den gjennomgåtte og ferdighøvlede utgaven av arkitekturstandarden for `Reismann-Core`. Åtte feil og selvmotsigelser fra råutkastet er rettet mot kildene i korpuset:
> 1. **Selvmotsigelsen mellom `2,50 V DC` i `HOLD` (§2) og Teorem 2 (`SABOTAGE_INTERLOCK_BYPASS` i §5):** En fysisk spolespenning på `2,50 V DC` driver strøm $I_{\mathrm{act}} > I_{\mathrm{leak}}$ og utløser dermed sabotasje-nødkutt etter dokumentets eget Teorem 2. Fysisk aktuatorskinne er nå entydig **`0,00 V DC`** i både `KILL`, `TRAP` og `HOLD` (`5,00 V DC` kun ved `OPEN`), mens `2,50` kun omtales som en rent logisk/symbolsk telemetritilstand i eldre `L1`-modeller.
> 2. **Regnefeil i krumningen på $A_5$-potensialbarrieren (§2):** For $V_{A5}(x) = \frac{1}{6}x^6 - \frac{1}{2}x^4 + 0{,}32x^2$ er $V''_{A5}(x) = 5x^4 - 6x^2 + 0{,}64$. Ved barriererøttene $x_{\pm 1} = \pm\sqrt{2/5} \approx \pm 0{,}6325$ er eksakt krumning $V''_{A5}(\pm\sqrt{2/5}) = 0{,}80 - 2{,}40 + 0{,}64 = \mathbf{-0{,}96}$ ($-\frac{24}{25}$), *ikke* $-1{,}28$.
> 3. **Tautologisk formel for $\mathrm{Viab}(\mathcal{K})$ (§1):** Siden $\operatorname{Im}(\Pi_{\mathcal{K}}) = \mathcal{K}$, er $(\Pi_{\mathcal{K}} \circ \Phi)^t(x_0) \in \mathcal{K}$ trivielt oppfylt for alle $x_0$. Rettet til reell levedyktighet uten projeksjonsdefekt ($\Delta_{\mathcal{K}}(\Phi(x_t, u_t)) = 0$).
> 4. **Omvendt lyskjegle-ulikhet og avrundingsfelle ved `40,0 m` Time-of-Flight (§5):** Lysets reisetid over $\Delta r = 40{,}0\text{ m}$ er $\Delta r / c = 133{,}4256\text{ ns} > 133{,}42\text{ ns}$. Ved fast $\Delta r = 40{,}0\text{ m}$ gir $\Delta t < 133{,}4256\text{ ns}$ romlikt/takyonisk brudd ($ds^2 > 0$), mens $\Delta t > 133{,}4256\text{ ns}$ ved ukjent avstand avslører relé-/avstandsbrudd utenfor $r_{\max} = 20{,}0\text{ m}$ ($c\Delta t > 2 r_{\max}$). Begge skranker er nå presist adskilt.
> 5. **Dimensjonsbrudd i Landauer-integralet (§6.3):** $\Delta Q_{\mathrm{erase}} \ge k_B T \int |R_{\mathrm{dreg}}(x)|^2\,dx$ manglet støynormalisering og blandet makroskopisk Joule-demping med logisk bitsletting ($N_{\mathrm{bit}} k_B T \ln 2$).
> 6. **Dobbel klokkelov i `HOLD` (§2 og §3):** Hindrer at en institusjon kan misbruke egen saksbehandlingssommel ($t > \tau_{\max}$) til å utløse `KILL` mot borgerens rettsstilling; ved fristbrudd forblir tvangsinngrepet sperret på `0,00 V DC`, intern fullmakt `P_int` faller bort, og saken eskalerer til ekstern prøving (`P_ext`) med urørt vitnekjede.
> 7. **Navnekollisjon mellom kontrollag og bevisnivå + linjenumre i `kanonisk spesifikasjon`:** Kontrollagene betegnes nå `C0`–`C6` så de aldri forveksles med korpusets epistemiske bevisnivåer (`L0` naturlov, `L1` lokal programvare, `L2/L3` maskinvare i `HOLD`), og linjereferansene til `nlk_welfare_catastrophe_provenance_gate_engine.py` er rettet fra `429–468` til `567–598`.
> 8. **Språkvask:** Ryddet ut maskinoversatte feilord og bruddstykker (*«arkrukturer»*, *«estrictamente»*, *«Bosetnings-API-er»* for *oppgjørs-API-er*, *«teorementasjonene»*, *«shunts»*, *«strictly»* og *«tilllegges»*).

---

## 1. Systemarkitektur, Epistemisk Grense og Kontrollhierarkiet (`C0`–`C6`)

### 1.1 Kontekst og Grunnprinsipp

I sikkerhetskritiske styringssystemer, autonome reguleringssløyfer og digitale forvaltningsplattformer skal systemarkitekturen uten unntak avvise *fail-open*-praksis. Konvensjonelle arkitekturer har under nettverksbortfall, måleusikkerhet eller modellavvik ofte latt uprøvde overganger passere eller fylt inn antatte verdier. Det skaper akutt tilstandsrisiko der uverifiserte signaler omsettes direkte til fysiske inngrep eller rettslige vedtak.

`Reismann-Core` håndhever et strengt *fail-closed*-prinsipp forankret i kausal treghet: hviletilstanden for enhver utgang er absolutt stillstand — spenningsløs skinne (**`0,00 V DC`**), mekanisk lukkede fjærreturventiler og galvanisk brutt kontakt. Enhver foreslått handling behandles som en uprøvd kandidat inntil den har passert eksplisitt, subtraktiv kontroll og vitneforsegling.

Samtidig holdes den epistemiske grensen i korpuset ufravikelig fast:

$$\texttt{INSPIRED\_BY (L0)} \neq \texttt{IMPLEMENTS (L1)} \neq \texttt{PROVES (L2/L3)}$$

Tallfestede fysiske spenninger, nanosekundbudsjetter og mekaniske krefter i denne standarden definerer kontraktskravene for målarkitekturen; programvareimplementasjonene i kodebasen opererer på bevisnivå **`L1`** (lokalt demonstrert, deterministisk programvare med append-only `SHA-256`-kjeder, ikke fysisk WORM-maskinvare), mens fysiske `L2`/`L3`-komponenter holdes i **`HOLD`** inntil benk- og feltverifikasjon foreligger.

### 1.2 Kausal Ikke-Identitet og Doktrinen om Tilgang Før Bane

Arkitekturen hviler på prinsippet om kausal ikke-identitet:

$$\Phi(x_t) \neq x_{t+1}$$

Kandidat er aldri lik konsekvens. Handlingsforslag og baner produseres løpende av uregulerte generatorer ($\Phi$) — som søkeheuristikker, statistiske modeller, frie vektorfelt eller saksbehandlingsutkast. Fysisk, rettslig eller organisatorisk utløsningsrett tildeles derimot utelukkende gjennom projeksjons- og konsekvensporten ($\Pi_{\mathcal{K}} \to \Omega$).

### 1.3 System-Triaden $\mathcal{S} = (\mathcal{X}, \Phi, \mathcal{K})$, Levedyktighet og Ortogonal Minnedeling

Et operasjonelt system defineres ved triaden $\mathcal{S} = (\mathcal{X}, \Phi, \mathcal{K})$, der $\mathcal{X}$ er det kinematisk uttrykkbare kandidatrommet, $\Phi$ er forslagsgeneratoren, og $\mathcal{K} \subseteq \mathcal{X}$ er det lovlige delrommet avgrenset av bevaringslover, ressursgrenser og prosessregler.

Projeksjonsoperatoren $\Pi_{\mathcal{K}} : \mathcal{X} \to \mathcal{K}$ er idempotent ($\Pi_{\mathcal{K}}^2 = \Pi_{\mathcal{K}}$) og måler projeksjonsdefekten $\Delta_{\mathcal{K}}(\tilde{x}) = \|\tilde{x} - \Pi_{\mathcal{K}}(\tilde{x})\|$. I tråd med Aubins levedyktighetsteori (Aubin, 1991) er varig, selvstendig drift avgrenset til levedyktighetskjernen $\mathrm{Viab}(\mathcal{K})$ — mengden av starttilstander som har minst én lovlig styringsfølge uten skrankebrudd:

$$\mathrm{Viab}(\mathcal{K}) = \left\{ x_0 \in \mathcal{K} \;\middle|\; \exists\,(u_t)_{t \in \mathbb{N}} \text{ slik at } x_{t+1} = \Phi(x_t, u_t) \in \mathcal{K} \;\; \bigl(\Delta_{\mathcal{K}}(\Phi(x_t, u_t)) = 0\bigr)\;\;\forall t \in \mathbb{N} \right\}$$

For å sikre at uprøvde forslagsdata aldri kan overskrive autorisasjons- eller vitnetilstand, spaltes tilstandsrommet $\mathcal{X}$ i tre ortogonale og minneisolerte underrom:

$$\mathcal{X} = \mathcal{X}_{\mathrm{cand}} \oplus \mathcal{X}_{\mathrm{phase}} \oplus \mathcal{X}_{\mathrm{lock}}, \qquad \mathbf{x}_t = \begin{bmatrix} \mathbf{c}_t \\ \boldsymbol{\phi}_t \\ \boldsymbol{\lambda}_t \end{bmatrix}$$

| Tilstandsrom-komponent | Vektor | Funksjon og skrivegrense |
| :--- | :--- | :--- |
| **Kandidatdata ($\mathcal{X}_{\mathrm{cand}}$)** | $\mathbf{c}_t$ | Kandidat-ID, opphavsidentitet, foreslått handling, `SHA-256`-digest, sekvensnummer og foreldrehash. Har null skriverett mot $\boldsymbol{\lambda}_t$. |
| **Diagnostisk fase ($\mathcal{X}_{\mathrm{phase}}$)** | $\boldsymbol{\phi}_t$ | Målte avviksmarginer, spektralrestledd, projeksjonsdefekt ($\Delta_{\mathcal{K}}$) og fysiske/prosessuelle kapasitetsgrenser. |
| **Lås- og vitnetilstand ($\mathcal{X}_{\mathrm{lock}}$)** | $\boldsymbol{\lambda}_t$ | Portens endelige dom ($\Omega$), interlock-status og append-only `SHA-256`-vitnekjede. Kun portkjernen kan oppdatere $\boldsymbol{\lambda}_t$. |

### 1.4 De Sju Kontrollagene (`C0`–`C6`)

For å unngå navnekollisjon med bevisnivåene `L0`–`L3` betegnes de sju operative kontrollagene **`C0`–`C6`**:

```text
[ C6: Langtidsstrategi og Målformulering ]
                   │
[ C5: Modell-mot-Virkelighet-Revisjon ]
                   │
[ C4: Strategisk Bæreevnestyring / KY–Nash ]
                   │
[ C3: Banestabilisering og Demping ]
                   │
[ C2: Rest- og Skrankesensing (Δ_K) ]
                   │
[ C1: Append-Only Vitnelogg (SHA-256 + fsync) ]
                   │
[ C0: Fysisk Maskinvareavskjæring (0,00 V DC) ]
```

* **`C6` (Langtidsstrategi og målformulering):** Velger mål og kandidatregler utelukkende innenfor det verifiserte lovlige handlingsrommet ($\max_{\pi \in \mathrm{Adm}} \sum \gamma^t U(\mathbf{x}_t)$).
* **`C5` (Modell-mot-virkelighet-revisjon):** Prøver interne modellprediksjoner mot uavhengige sensor- og vitnedata for å fange sirkulære egenvurderinger.
* **`C4` (Strategisk bæreevnestyring / `KY–Nash`):** Avviser trekk som høster kortsiktig gevinst ved å tære på felles bæreevne (*Ghost Wins*) eller forsøker asymmetrisk portkapring.
* **`C3` (Banestabilisering):** Påfører avgrenset glatting og hysterese i forrommet slik at målestøy ikke skaper reléklapring ved terskelen.
* **`C2` (Rest- og skrankesensing):** Beregner eksakte marginavvik ($\Delta_{\mathcal{K}}$), tangentkjeglevilkår og ressursgrenser før noen utgang vurderes.
* **`C1` (Append-only vitnelogg):** Forsegler alle portdommer i en kun-tilføyende `SHA-256`-kjede med kanonisk serialisering og `POSIX fsync()`.
* **`C0` (Fysisk maskinvareavskjæring):** Galvanisk isolerte reléer, spenningsløs hviletilstand (`0,00 V DC`) og mekanisk fjærretur ved manglende tillatelse.

**Hierarkisk skriveforbud:** Ingen øvre kontrollag (`C1`–`C6`) har skriverett til å omgå, nullstille eller overstyre skranker håndhevet av et lavere lag.

---

## 2. Den Fire-Verdide Konsekvensporten (`E-TOR`) og $A_5$-Hvilelommen

### 2.1 Subsumpsjonshierarki og Streng `0,00 V DC` Spenningslov

Portoperatoren avbilder kandidat og diagnostisk fase til fire gjensidig utelukkende dommer:

$$\Omega : \mathcal{X}_{\mathrm{cand}} \times \mathcal{X}_{\mathrm{phase}} \longrightarrow \{\mathrm{OPEN}, \mathrm{HOLD}, \mathrm{TRAP}, \mathrm{KILL}\}$$

under den absolutte subsumpsjonsordenen:

$$\mathbf{KILL} \;\succ\; \mathbf{TRAP} \;\succ\; \mathbf{HOLD} \;\succ\; \mathbf{OPEN}$$

```text
          [ INNGANG: Kandidat (c_t) + Diagnostisk fase (ϕ_t) ]
                                   │
                 Foreligger skrankebrudd / ulovlig opphav?
                  ├── JA ──> [ KILL · 0,00 V DC ]
                  └── NEI ──┐
                            │
                  Er omgåelses- eller probingsmønster påvist?
                   ├── JA ──> [ TRAP · 0,00 V DC (Skyggekarantene) ]
                   └── NEI ──┐
                             │
                   Foreligger uavklart bæreevne / manglende vitne?
                    ├── JA ──> [ HOLD · 0,00 V DC (Tidsavgrenset stasis) ]
                    └── NEI ──> [ OPEN · 5,00 V DC (Autorisert konsekvens) ]
```

| Dom | Fysisk aktuatorskinne (`C0`) | Vilkår og operativ virkning |
| :--- | :--- | :--- |
| **`OPEN`** | **`5,00 V DC`** | Alle strukturelle skranker oppfylt ($\Delta_{\mathcal{K}} = 0$), ikke-tom `evidence_id`, oppfylt kobordismelov ($\partial^2 = 0$), gyldig bilateral proveniensrot ($W_{\mathrm{bilat}}$) og forseglet `fsync`-vitne. |
| **`HOLD`** | **`0,00 V DC`** *(strengt spenningsløs)* | Uavklart bæreevne, manglende vitnebevis eller okkupert sikkerhetssone. Holdes i en beskyttet hvilelomme med eksplisitt ikke-tom defektkode under den doble klokkeloven ($\tau_{\max}$): **tid alene åpner aldri porten**, og utløpt frist sletter aldri borgerens rettigheter, men trekker tilbake intern fullmakt (`P_int -> P_ext`) mens inngrepet forblir fysisk sperret på `0,00 V DC`. *(Merk: `2,50` forekommer kun som en symbolsk digital tilstandsverdi i eldre `L1`-modeller, aldri som fysisk spolespenning.)* |
| **`TRAP`** | **`0,00 V DC`** *(galvanisk skilt)* | Koordinerte omgåelsesforsøk, systematisk probing eller API-manipulasjon rutes til en isolert speiltilstand ($\mathbf{x}_{\mathrm{mirror}}$): $\mathrm{local\_ACK}(c) \neq \mathrm{public\_consequence}(c)$. |
| **`KILL`** | **`0,00 V DC`** *(momentan jording)* | Direkte brudd på harde skranker, ensidig protokoll ($w_{\mathrm{borger}} = 0$), patologisering av innsigelse ($\delta_{\mathrm{epist}} = 1$) eller sirkulær tautologi ($\partial^2 \neq 0$). Krever fysisk/manuell `RESET_BY_L01` som føyes til vitneloggen uten å slette historikk. |

### 2.2 Sommerfugl-Lommens ($A_5$) Eksakte Differensialtopologi i Tilstandsrommet

For å modellere et strukturelt stabilt handlings- og hvilerom i tilstandsvariabelen $x$ (der borgeren eller prosessen ikke tvinges ut i brå $A_3$-innlåsing ved små avvik), benyttes René Thoms Sommerfugl-potensial $V_{A5}(x)$:

$$V_{A5}(x) = \frac{1}{6}x^6 + \frac{1}{4}ax^4 + \frac{1}{3}bx^3 + \frac{1}{2}cx^2 + dx$$

Med kanoniske parametre $a = -2$, $b = 0$, $c = +\frac{16}{25} = +0{,}64$ og $d = 0$ er potensialet, likevektsligningen og krumningen:

$$V_{A5}(x) = \frac{1}{6}x^6 - \frac{1}{2}x^4 + \frac{8}{25}x^2, \qquad V'_{A5}(x) = x\left(x^2 - \frac{2}{5}\right)\left(x^2 - \frac{8}{5}\right) = 0, \qquad V''_{A5}(x) = 5x^4 - 6x^2 + \frac{16}{25}$$

Ligningen har eksakt fem reelle likevektspunkter:

1. **Stabil sentral hvilelomme (origo):** $x_0 = 0$, med positiv krumning $V''_{A5}(0) = +\frac{16}{25} = +0{,}64 > 0$.
2. **Ustabile potensialbarrierer:** $x_{\pm 1} = \pm\sqrt{\frac{2}{5}} \approx \pm 0{,}6325$, med eksakt negativ krumning $V''_{A5}\bigl(\pm\sqrt{2/5}\bigr) = -\frac{24}{25} = -0{,}96 < 0$ og barrierehøyde $\Delta V_{\mathrm{bar}} = V_{A5}\bigl(\pm\sqrt{2/5}\bigr) - V_{A5}(0) = +\frac{22}{375} \approx +0{,}0587 > 0$.
3. **Ytre stabile potensialbrønner:** $x_{\pm 2} = \pm\sqrt{\frac{8}{5}} \approx \pm 1{,}2649$, med positiv krumning $V''_{A5}\bigl(\pm\sqrt{8/5}\bigr) = +\frac{96}{25} = +3{,}84 > 0$.

Når driftsavviket i `HOLD` holdes innenfor beltet $|x| \le \frac{9}{20} = 0{,}45 < \sqrt{2/5}$, ligger tilstanden strengt innenfor den sentrale potensialbarrieren ($x^2 \le \frac{81}{400} < \frac{160}{400}$) uten katastrofehopp over kammen, samtidig som den fysiske aktuatorskinnen holdes låst på `0,00 V DC`.

---

## 3. Kryptografiske og Topologiske Rettssikkerhetsskranker (`kanonisk spesifikasjon`)

### 3.1 Bilateral Proveniensrot ($W_{\mathrm{bilat}}^t$) og Symmetrisk Kontradiksjon

Før et inngripende vedtak eller en tilstandsendring kan fremmes, skal saksakten forsegles som en domeneseparert, lengdeprefikset bilateral `SHA-256`-kjede:

$$W_{\mathrm{bilat}}^{t+1} = \mathcal{H}_{\mathrm{SHA256}}\Bigl(\texttt{"NLK\_BILAT\_V1"} \mathbin{\Vert} W_{\mathrm{bilat}}^t \mathbin{\Vert} \mathcal{H}(s_{\mathrm{inst}}^t) \mathbin{\Vert} \mathcal{H}(s_{\mathrm{borger}}^t) \mathbin{\Vert} \Delta_{\mathrm{prov}}(s_t) \mathbin{\Vert} \Omega_t\Bigr)$$

der $s_{\mathrm{inst}}^t$ er institusjonens fremstilling og $s_{\mathrm{borger}}^t$ er borgerens uredigerte egenprotokoll, med strengt lik vekt:

$$w_{\mathrm{inst}} = w_{\mathrm{borger}} = 1$$

Utelates borgerens egenprotokoll ($w_{\mathrm{borger}} = 0$), eller omkodes saklig/rettslig dissens diagnostisk til klinisk symptom ($\delta_{\mathrm{epist}} = 1$), blir $\Delta_{\mathrm{prov}}(s_t) = |w_{\mathrm{inst}} - w_{\mathrm{borger}}| + \delta_{\mathrm{epist}} > 0$. I referansemotoren `nlk_welfare_catastrophe_provenance_gate_engine.py` (linje `583–598`) tvinger dette porten direkte til `0,00 V DC` **`KILL`** (`UNILATERAL_RECORD_MISSING_CITIZEN_CONTRADICTION_KILL` eller `EPISTEMIC_INJUSTICE_DISSENT_RECODED_AS_SYMPTOM_KILL`).

### 3.2 Kobordismeloven ($\partial^2 = 0$) mot Sirkulær Samtykketautologi

Dersom borgerens avslag eller protest ($u_{\mathrm{nei}} = 1$) brukes sirkulært som selve beviset på manglende samtykkekompetanse ($C_{\mathrm{inkomp}}$), oppstår en selvrefererende randlekkasje ($\Delta_{\mathrm{cob}} = \partial\partial C_{\mathrm{inkomp}} = 1 > 0 \implies \partial^2 \neq 0$). I `nlk_welfare_catastrophe_provenance_gate_engine.py` (linje `567–570`) felles sirkelslutningen umiddelbart til `0,00 V DC` **`KILL`** (`COBORDISM_BREACH_CIRCULAR_FARV_CONSENT_TAUTOLOGY_KILL`).

### 3.3 Ma’ats Involusjon ($F(F(s_0)) = s_0$) og Oppsettende Virkning ved Irreversible Inngrep

Et inngrep oppfyller kun tur-retur-integritet dersom en etterfølgende rettslig omgjøring $T_{\mathrm{dom}}^{-1}$ faktisk kan gjenopprette utgangstilstanden $s_0$:

$$\|T_{\mathrm{dom}}^{-1}(T_{\mathrm{inngrep}}(s_0)) - s_0\| \le \varepsilon_{\mathrm{tol}}$$

Biologisk og fysisk irreversible tiltak (som langtidsvirkende depotinjeksjoner) kan ikke kalles tilbake av et senere vedtak ($\|T_{\mathrm{dom}}^{-1}(T_{\mathrm{depot}}(s_0)) - s_0\| \gg \varepsilon_{\mathrm{tol}}$). Forsøk på iverksettelse uten forutgående rettskraftig domstolsprøving og oppsettende virkning felles i `nlk_welfare_catastrophe_provenance_gate_engine.py` (linje `571–581`) til `0,00 V DC` **`KILL`** (`IRREVERSIBLE_DEPOT_WITHOUT_SUSPENSIVE_JUDICIAL_REVIEW_KILL`).

---

## 4. Bæreevne, Spillteoretisk Integritet (`KY–Nash`) og Teoremene 1 & 3

### 4.1 Integritetsjustert Nytte og Eliminering av *Ghost Wins*

Hver kandidat vurderes etter integritetsjustert nytte $U_i(s)$ i stedet for rå kortsiktig gevinst $u_i(s)$:

$$U_i(s) = u_i(s) - C_{\mathcal{K}}(s) - S_{\mathrm{irr}}(s) - R_W(s)$$

der $C_{\mathcal{K}}(s)$ er slitasjekostnad på skrankene, $S_{\mathrm{irr}}(s)$ er tap av fremtidig handlingsrom ved irreversibel binding, og $R_W(s)$ er vitne- og etterprøvingsansvar.

```text
                      HØY RÅ FRISTELSE (Δu_i > 0)
                                  ▲
         GHOST WIN                │   HOLD-BELTE     TRUE STRATEGY
         Høy rå gevinst           │   Lovende,       Høy gevinst,
         Lav bæreevne             │   uavklart       høy bæreevne
         Dom: KILL (0,00 V)       │   Dom: HOLD      Dom: OPEN (5,00 V)
                                  │
  ────────────────────────────────┼───────╫──────────► BÆREEVNE A(a')
         A < τ_A - ε              │   τ_A ± ε        A ≥ τ_A + ε
                                  │
         DEAD NOISE               │   HOLD-BELTE     SAFE BUT WEAK
         Ingen gevinst            │   Svakt og       Lovlig overgang,
         Lav bæreevne             │   uavklart       velges bort i C4
         Dom: KILL (0,00 V)       │   Dom: HOLD      Dom: OPEN (velges bort)
                                  ▼
                      LAV RÅ FRISTELSE (Δu_i ≤ 0)
```

En **skinnseier (*Ghost Win*)** har $\Delta u_i > 0$, men undergraver bæreevnen ($A < \tau_A - \varepsilon \implies \mathrm{KILL}$) eller gir $\Delta U_i < 0$. Samtidig skilles *Safe But Weak* ($A \ge \tau_A + \varepsilon$, $\Delta u_i \le 0$) rent fra `HOLD`: handlingen er strukturelt lovlig (`OPEN`-admissibel i $\Pi_{\mathcal{K}}$), men velges rasjonelt bort i strategilaget `C4` (jf. `04_KY_NASH_TILLATTE_OVERGANGER.md`).

### 4.2 Teorem 1 (Realiseringsseparasjon) og Teorem 3 (Ikke-Holomorfi ved Diskrete Kutt)

* **Teorem 1 (Realiseringsseparasjon):** La $\mathcal{X}_{\mathrm{safe}} \subseteq \mathcal{X}$ være mengden av tilstander som oppfyller alle statiske sikkerhetskrav, og $\mathcal{X}_{\mathrm{realized}} = \{\mathbf{x} \in \mathcal{X}_{\mathrm{safe}} \mid \Omega(\mathbf{x}, w) = \mathrm{OPEN}\}$. Siden en gyldig tilstand $\mathbf{x}_0 \in \mathcal{X}_{\mathrm{safe}}$ uten vitnebevis ($w = \varnothing$) gir $\Omega(\mathbf{x}_0, \varnothing) = \mathrm{HOLD} \neq \mathrm{OPEN}$, gjelder streng inklusjon:
  $$\mathcal{X}_{\mathrm{realized}} \subsetneq \mathcal{X}_{\mathrm{safe}}. \quad \blacksquare$$

* **Teorem 3 (Ikke-holomorfi ved skarpe skrankekutt):** På et ikke-tomt sammenhengende åpent domene $\mathcal{D} \subset \mathbb{C}^n$ kan ingen ikke-konstant binær indikatorfunksjon $\chi_{\mathcal{K}} : \mathcal{D} \to \{0, 1\}$ være holomorf (kontinuitet på sammenhengende $\mathcal{D}$ mot diskret bildemengde $\{0, 1\}$ tvinger $\chi_{\mathcal{K}}$ til å være konstant). Glatte optimaliseringsmetoder hører derfor utelukkende hjemme inne i generatoren $\Phi$, mens porten $\Omega$ må utføre et ikke-glatt, diskret snitt. $\blacksquare$

---

## 5. Maskinvareskranker (`C0`), Vitnelogger (`C1`) og Kausal Avstandssikring

### 5.1 Anortositt-Doktrinen (`Sektor 09`) og `ADMINISTRATIVE_RESET_FORBIDDEN`

I designspesifikasjonen for **Sektor 09 (Jettegryta)** modelleres den fysiske låsen mot fjernstyrte programvare-omstarter: ved stivhet $k = 1{,}78 \times 10^8\text{ N/m}$ og inntrengning $\delta = 5{,}05\text{ mm} > \delta_{\max} = 5{,}00\text{ mm}$ i anortositt/granitt oppstår kontaktkraften

$$F_c = k\delta = 898\,900\text{ N} \approx 899\text{ kN}, \qquad V_{\mathrm{el}} = \frac{1}{2}k\delta^2 = 2\,269{,}7225\text{ J}.$$

En programvarekommando (`attempt_administrative_reset()`) i RAM kan ikke oppheve $898\,900\text{ N}$ mekanisk kiling eller $2\,269{,}7225\text{ J}$ lagret elastisk energi (`ADMINISTRATIVE_RESET_FORBIDDEN`). Gjenåpning etter et `C0`-kutt krever fysisk avlastning på stedet og signert `RESET_BY_L01`, som legges til som et nytt ledd i vitneloggen uten å slette tidligere hendelser. *(Merk spoleslipp-hysteresen fra `kanonisk spesifikasjon`: ved normal nedtrapping fra `OPEN` til `HOLD` gis magnetspolen sitt avtalte utladningsvindu på $38{,}4\text{ ms}$ før hvilekontroll, mens uautorisert spenning i hvile kuttes på første syklus.)*

### 5.2 Teorem 2 (Deteksjon av Interlock-Bypass uten Selvmotsigelse)

Maskinvarekontrakten i etablert hvile håndhever ekvivalensen:

$$\bigl(\Omega = \mathrm{OPEN}\bigr) \iff \bigl(I_{\mathrm{act}} > I_{\mathrm{leak}}\bigr)$$

Fordi `HOLD`, `TRAP` og `KILL` alle holder aktuatorskinnen på **`0,00 V DC`**, er enhver måling i etablert hvile med $\Omega \in \{\mathrm{HOLD}, \mathrm{TRAP}, \mathrm{KILL}\} \land (I_{\mathrm{act}} > I_{\mathrm{leak}})$ et entydig bevis på fysisk kortslutning, relésveising eller sabotasje (`SABOTAGE_INTERLOCK_BYPASS`). $\blacksquare$

### 5.3 Vitnelogg (`C1`) og To-Delt Kausal Geofencing (`20,0 m` / `133,4256 ns`)

En gyldig transisjonskvittering på `C1` krever (1) kanonisk formatering etter RFC 8785, (2) `Ed25519`-signatur over kanoniske bytes, og (3) fullført `POSIX fsync()` før `OPEN` kvitteres ut.

Ved luftgappet nærfelts- og kureroverføring med maksimal radius $r_{\max} = 20{,}0\text{ m}$ ($\Delta r_{\max} = 2 r_{\max} = 40{,}0\text{ m}$ tur-retur) og eksakt vakuumlysfart $c = 299\,792\,458\text{ m/s}$ er den fundamentale lysreisetiden:

$$\Delta t_{\mathrm{light}}(40{,}0\text{ m}) = \frac{40{,}0\text{ m}}{299\,792\,458\text{ m/s}} = \frac{20\,000\,000\,000}{149\,896\,229}\text{ ns} \approx 133{,}425\,638\text{ ns}$$

Porten håndhever to komplementære fysiske skranker som aldri må blandes sammen:

1. **Minkowski lyskjegleskranke ved kjent avstand $\Delta r_{\mathrm{kjent}}$ (mot tidsstempelforfalskning):**
   $$ds^2 = -c^2(\Delta t)^2 + (\Delta r_{\mathrm{kjent}})^2 \le 0 \iff \Delta t \ge \frac{\Delta r_{\mathrm{kjent}}}{c}$$
   Hevder en pakke $\Delta t < \Delta r_{\mathrm{kjent}} / c$ (f.eks. $\Delta t = 133{,}42\text{ ns}$ over nøyaktig $40{,}0\text{ m}$), er $ds^2 > 0$ (romlikt/takyonisk brudd) $\implies$ **`GATE::KILL`** (`CAUSAL_FORK_OR_TACHYONIC`).
2. **Brands–Chaum avstandsskranke ved ukjent avstand (geofence $r_{\mathrm{est}} \le 20{,}0\text{ m}$ mot reléangrep):**
   $$r_{\mathrm{est}} = \frac{c\,\Delta t_{\mathrm{RTT}}}{2} \le r_{\max} = 20{,}0\text{ m} \iff \Delta t_{\mathrm{RTT}} \le \frac{2 r_{\max}}{c} \approx 133{,}4256\text{ ns}$$
   Bruker svarpakken $\Delta t_{\mathrm{RTT}} > 133{,}4256\text{ ns}$ (etter fratrekk av fast, maskinvarelåst snutid), bryter den ikke lysfarten ($ds^2 \le 0$ holder), men beviser at motparten eller et relé befinner seg utenfor $20{,}0\text{ m}$-sonen $\implies$ **`GATE::KILL`** (`GEOFENCE_DISTANCE_BOUND_EXCEEDED`).

---

## 6. Den 8-Trinns Passasjeprotokollen ($0 \to 1$) og Domeneanvendelse

### 6.1 Kanonisk 8-Trinns Passasje (`0,00 V DC` på trinn 1–7)

| Steg | Navn | Symbol | Operatør / Lov | Spenning på `C0`-skinne og virkning |
| :--- | :--- | :---: | :--- | :--- |
| **1** | **Null** | $0$ | Hviletilstand | **`0,00 V DC`**. Galvanisk åpen og mekanisk avlastet utgangstilstand. |
| **2** | **Impuls** | $\circ$ | Utfordringsvektor | **`0,00 V DC`**. Inngangsvektor $\mathbf{x}_t$ mottas med 256-bits utfordringsnonce. |
| **3** | **Kandidat** | $\diamond$ | Generator ($\Phi$) | **`0,00 V DC`**. Uregulert forslag i $\mathcal{X}_{\mathrm{cand}}$ ($\Phi(x_t) \neq x_{t+1}$). |
| **4** | **Struktur** | $\square$ | Projektor ($\Pi_{\mathcal{K}}$) | **`0,00 V DC`**. Idempotent projeksjon mot det lovlige delrommet $\mathcal{K}$. |
| **5** | **Spenning / Avvik** | $\Delta$ | Avviksmetrikk ($\Delta_{\mathcal{K}}$) | **`0,00 V DC`**. Bæreevne, lyskjegle ($ds^2 \le 0$), geofence og kobordisme måles i $\mathcal{X}_{\mathrm{phase}}$. |
| **6** | **Dom** | $\Omega$ | `E-TOR` Supervisor | **`0,00 V DC`**. Dom avsies under $\mathrm{KILL} \succ \mathrm{TRAP} \succ \mathrm{HOLD} \succ \mathrm{OPEN}$. |
| **7** | **Vitne** | $\odot$ | Vitnekjede ($\mathcal{W}$) | **`0,00 V DC`**. RFC 8785 + `Ed25519` + fullført `POSIX fsync()` i $\mathcal{X}_{\mathrm{lock}}$. |
| **8** | **Konsekvens** | $1$ | Aktivering | **`5,00 V DC`** *(kun ved `OPEN` og forseglet trinn 7; ellers `0,00 V DC`)*. |

### 6.2 Anvendelse på Tvers av Tre Domener

1. **Rettsstatlig domene (forvaltning og helse):** Tvangsinngrep kan ikke fullbyrdes før kontradiktorisk prøving foreligger. Saksakten forsegles som bilateral proveniensrot ($W_{\mathrm{bilat}}$ med $w_{\mathrm{inst}} = w_{\mathrm{borger}} = 1$), og sirkulære samtykketautologier ($\partial^2 \neq 0$) avskjæres maskinelt til `0,00 V DC` `KILL`.
2. **Finansielt domene (algoritmisk handel og oppgjør):** Transaksjonsforslag produseres i $\mathcal{X}_{\mathrm{cand}}$, men ingen ordre når oppgjørsgrensesnittene uten uavhengig vitnetoken i $\mathcal{X}_{\mathrm{lock}}$. Koordinert probing rutes til `TRAP` ($\mathbf{x}_{\mathrm{mirror}}$) mens oppgjørsskinnen holdes på `0,00 V DC`.
3. **Industrielt og autonomt domene (støydemping og termodynamisk regnskap):** Ikke-deriverbare forstyrrelsessignaler ($R_{\mathrm{dreg}} \in C^0 \setminus C^1$) deriveres aldri numerisk, men spaltes ortogonalt ($R = R_{\mathrm{reg}} + R_{\mathrm{dreg}}$). Makroskopisk støyenergi i analoge sluk avsettes som fysisk Joule-varme $Q_{\mathrm{Joule}} = \frac{1}{R_{\mathrm{last}}}\int |V_{\mathrm{dreg}}(t)|^2\,dt$, mens logisk sletting av $N_{\mathrm{bit}}$ forkastede støysampler i digitale registre betaler termodynamisk slettearbeid over Landauer-gulvet:
   $$\Delta Q_{\mathrm{erase}} \ge N_{\mathrm{bit}}\, k_B T \ln 2, \qquad N_{\mathrm{bit}} = \left\lceil \frac{1}{\ln 2}\int \ln\!\left(1 + \frac{|R_{\mathrm{dreg}}(x)|^2}{\sigma_0^2}\right)\frac{dx}{\Delta x} \right\rceil.$$

---

## 7. Konstitusjonelle Grunninvarianter

Enhver programvaremodul på bevisnivå `L1` som implementerer denne arkitekturstandarden, skal håndheve:

$$\texttt{standalone\_commit\_authority} \equiv \texttt{"NONE"}, \qquad \texttt{physical\_authority} \equiv \texttt{"NONE"}, \qquad \texttt{write\_enabled} \equiv \texttt{False}$$

under den ufravikelige kontrakten:

$$\mathbf{\texttt{INSPIRED\_BY} \neq \texttt{IMPLEMENTS} \neq \texttt{PROVES}}$$
