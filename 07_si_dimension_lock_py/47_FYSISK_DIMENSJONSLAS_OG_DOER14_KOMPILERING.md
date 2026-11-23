# Fysisk dimensjonslås (`X.07`–`X.09`) og kompilering av `[Fe7MoS9C]` + `Dør 14: Alexandrov-sjakten`

> **Grenseoppgang:** `INSPIRED_BY != IMPLEMENTS != PROVES`. Dette arbeidsstykket dokumenterer de fem sveisene som herdet `PhysicalDomainAccumulator` (`X.07`–`X.09`) sammen med `44_spraksluse_l1_gate.py` til den samlede `L1`-motoren i `46_fysisk_dimensjonslas_x07_x09.py` (`12/12 PASS`, `0` flyttall). Append-only `SHA-256 WAL` er en programvarekjede på disk, ikke fysisk WORM-maskinvare.

---

## 1. Fem krets- og fysikkfeil som ble funnet og tettet i `CARBON-46`-råskissen

Da den innkomne `PhysicalDomainAccumulator`-skissen ble prøvd mot sin egen 5-trinns `[Fe7MoS9C]`-tabell og fysikken i `35_DOER14_ALEXANDROV_SJAKTEN_REVISJON.md`, røk fem punkter som nå er sveiset igjen i `46_fysisk_dimensjonslas_x07_x09.py`:

1. **Falske `X.08`-drap på vanlige fagord (`gass`, `vann`, `linj`, `reaktor`) + hardkodet `stivhet` i suffikslisten:** Råskissen la `"stivhet"` og `"kraften"` inn i `NO_SUFFIXES` for å treffe testordet `"amboltstivhet"`, samtidig som 4-tegns prefiks-kutt sendte `"reaktoren"`, `"vannets"`, `"linjer"` og `"gassen"` fra trinn `L02`–`L04` rett i karantene — slik at ethvert senere fagledd med `"gasskromatografi"`, `"linjebredde"` eller `"reaktor"` ble skutt ned som poetisk kontrabande. Rettet med ren norsk bøyningsavkledning uten jukse-suffikser, delt teknisk fagvokabular mellom `CARBON-44` og `CARBON-46`, og ekte sammensetningsdeteksjon som feller både `"amboltstivhet"` og `"amboltslag"` uten falske kutt.
2. **Lukkede intervaller slapp `delta_film = 0 m` og `[0, 3/4] ∩ (3/4, 1]` gjennom:** Tabelltrinn `FEMOS_L02` krevde halvåpent intervall $\delta_{\text{film}} \in (0, 2 \cdot 10^{-6}]\text{ m}$, men `RationalBound` i råskissen manglet lukkethetsflagg og godtok dermed tørr elektrode (`0 m`). Rettet med eksakte `low_closed` og `high_closed` i $\mathbb{Q}$.
3. **Manglende kobling mellom `j_NH3`, `j_tot` og `FE_NH3` i `X.07`:** Selve begrunnelsen for `X.07` var at en forfatter oppgir $j_{\text{NH}_3} = 82\text{ mA/cm}^2$ og $j_{\text{tot}} = 100\text{ mA/cm}^2$ *uten* å nevne `FE_NH3`. Likevel sjekket råskissen kun identiske variabelnavn (`b.var_name in self._bounds`). Herdet motor innfører eksakte 7-tuppel SI-dimensjonssjekkede `QuotientLaw` ($\operatorname{dim}(z) = \operatorname{dim}(x) - \operatorname{dim}(y)$) og `ProductLaw` ($\operatorname{dim}(p) = \operatorname{dim}(a) + \operatorname{dim}(b)$), som automatisk regner ut $\frac{820}{1000} = \frac{41}{50} > \frac{3}{4}$ og feller `FEMOS_L05_SCALAR` på `0 mV DC`.
4. **Punktlikhets-fellen i Dør 14 (`[20/149896229, 20/149896229]` s) mot `15 ps` TDC-skrevet:** Sluttavsnittet i råskissen foreslo å låse Dør 14 til punktintervallet $\left[\frac{20}{149\,896\,229},\, \frac{20}{149\,896\,229}\right]\text{ s}$. I `Dør 14` er $\tau_{\min} = \frac{20}{149\,896\,229}\text{ s}$ **nedre kausal skranke**, ikke et punkt: et nakent vakuumspeil lander i TDC-trinn `8895` ($\left[\frac{26\,685}{2\cdot 10^{11}},\, \frac{26\,688}{2\cdot 10^{11}}\right]\text{ s} = [133{,}425\text{ ns},\, 133{,}440\text{ ns}]$), som skriver rett over $\tau_{\min}$ fordi $3\,999\,980\,870\,865 < 4\,000\,000\,000\,000 < 4\,000\,430\,559\,552$. Herdet motor innfører derfor den eksakte mengde-trikotomien mellom måleboks $M$ og lovrom $K$:
   - $M \cap K = \varnothing \implies \mathbf{KILL}$ (`0 mV DC` — utenfor fysisk lov / fasevindu),
   - $M \cap K \neq \varnothing \;\land\; M \not\subseteq K \implies \mathbf{HOLD}$ (`0 mV DC` — oppløsningen skriver over grensen, som i `DOER14_L03_STRADDLE`),
   - $M \subseteq K \implies \mathbf{KLAR}$ (`0 mV DC` — hele måleboksen ligger trygt innenfor $K$, som ved det $12\text{ mm}$ tykke kvarts-hjørneprismet i trinn `8899`: $[133{,}485\text{ ns},\, 133{,}500\text{ ns}] \subset K$).
5. **Modalitets-likhet i `X.09`:** Ikke-tom streng alene hindrer ikke at to målinger tas fra samme feilkilde (f.eks. to amperometriske eller to kolorimetriske kanaler). Herdet motor krever minst to distinkte fysikalske modalitetsfamilier (`ELECTROCHEM_COULOMETRY` $\perp$ `NUCLEAR_SPIN_NMR`, eller `OPTICAL_TOF_TDC` $\perp$ `MECH_INTERLOCK`) før `KLAR`.

---

## 2. Forseglet kompilat B: `Dør 14 — Alexandrov-sjakten` (`DOER14_L01`–`DOER14_L05`)

```text
[DOER14_L01: Kausal diamant 2d=40 m] ──► KLAR (0 mV) ══[W_ext]══► OPEN (5000 mV)
       │ K: tau_rtt ∈ [20/149896229, 4/25000000] s | Produktlov: path_rtt = c * tau_rtt
       ├──► [DOER14_L02_SPOOF: 0..15 ps lokal prediktor]   ──► KILL (0 mV, M ∩ K = ∅)
       ├──► [DOER14_L03_STRADDLE: TDC-trinn 8895 u/ prisme]──► HOLD (0 mV, M ⊄ K)
       ▼
[DOER14_L04_PRISM: 12 mm kvarts, trinn 8899 + knivbryter]  ══[W_ext]══► OPEN (5000 mV)
       │ M = [26697/2e11, 26700/2e11] s ⊂ K | Ortogonalitet: OPTICAL_TOF_TDC ⊥ MECH_INTERLOCK
       ▼
[DOER14_L05_ZIGZAG: 52 m tre-speils omvei (Punkt ⊥ Bane)] ──► KILL (0 mV, M ∩ K = ∅)
```

| Steg | Fysisk størrelse i $\mathbb{Q}$ (`0 float`) | Relasjon mellom $M$ og $K$ | Portdom / Spenning |
| :--- | :--- | :--- | :--- |
| **`DOER14_L01`** | $K = \left[\frac{20}{149\,896\,229},\, \frac{4}{25\,000\,000}\right]\text{ s}$, $c = 299\,792\,458\text{ m/s}$ | Etablerer kausalt diamantvindu og `path_rtt = c * tau_rtt` | `OPEN` (`5000 mV`) |
| **`DOER14_L02_SPOOF`** | $M = \left[0,\, \frac{3}{200\,000\,000\,000}\right]\text{ s}$ (`0..15 ps`) | $M \cap K = \varnothing$ (overlyspåstand / lokal prediktor) | `KILL` (`0 mV`) |
| **`DOER14_L03_STRADDLE`** | $M = \left[\frac{26\,685}{2\cdot 10^{11}},\, \frac{26\,688}{2\cdot 10^{11}}\right]\text{ s}$ (`133,425..133,440 ns`) | $M \cap K \neq \varnothing$, men $M \not\subseteq K$ (nedre kant $< \frac{20}{149\,896\,229}\text{ s}$) | `HOLD` (`0 mV`) |
| **`DOER14_L04_PRISM`** | $M = \left[\frac{26\,697}{2\cdot 10^{11}},\, \frac{26\,700}{2\cdot 10^{11}}\right]\text{ s}$ (`133,485..133,500 ns`) | $M \subseteq K$ + `OPTICAL_TOF_TDC` $\perp$ `MECH_INTERLOCK` + $W_{\text{ext}}$ | `OPEN` (`5000 mV`) |
| **`DOER14_L05_ZIGZAG`** | $M = \left[\frac{26}{149\,896\,229},\, \frac{26}{149\,896\,229} + 15\text{ ps}\right]\text{ s}$ (`52 m` sikksakk) | $M \cap K = \varnothing$ ($\tau_{\text{zigzag}} \approx 173{,}453\text{ ns} > 160\text{ ns}$) | `KILL` (`0 mV`) |
