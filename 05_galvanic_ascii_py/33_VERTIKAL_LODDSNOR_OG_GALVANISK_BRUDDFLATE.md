# Vertikal loddsnor og galvanisk bruddflate (`u_raw -> KLAR :: 0.00 V DC // OPEN :: 5.00 V DC`)

> **Grenseoppgang:** `INSPIRED_BY != IMPLEMENTS != PROVES`. Dette arbeidsstykket dokumenterer og herder den vertikale konsekvenskretsen fra rå uro (`u_raw`) til galvanisk luftgap, verifisert lokalt i `34_vertikal_loddsnor_galvanisk_sluse.py` (`L1`, `8/8 PASS`, `0` flyttall). Revisjonskjeden er en append-only SHA-256-kjede i programvare, ikke fysisk WORM-maskinvare.

---

## 1. Innkommet råskisse på benken (bevart ordrett)

```text
[u_raw]
   │
   ▼
(L) Akustikk [chmod 444] ───(metafor = bevis)─────────────────► [KILL]
   │
   ▼
(A) Vektorlås (p_art) ──────(prematur lukking)─┐
   │                                           │
   ▼                                           ▼
(J) Søkerom {γ_i} ◄─────────(returledning)─── [HOLD : τ <= τ_max]
   │              ▲                            │
   │              │                            └─(τ > τ_max)──► [P_ext // Tidsavbrudd]
   ├─(lekkasje)───┼───────────────────────────────────────────► [KILL]
   ▼              │
(D) Dans / Last ──┴─────────(papir-bokholderi)─┘
   │
   ▼
(Π_K) Sluse [Δ_K -> 0, sum(permit) <= 1] ──(selv-autorisasjon)► [KILL]
   │
   ▼
[KLAR :: 0.00 V DC]   (Ytterste punkt i F — eksponert bruddflate, null fullmakt)
══════════════════════════════ GALVANISK LUFTGAP ══════════════════════════════
   │
   ▼  Kun ved inngrep fra W_ext ∉ F mot fysisk / ekstern motprøve
[OPEN :: 5.00 V DC]   (Autorisert innskrift — bærende konsekvens i P_COSMOS)
```

---

## 2. Hva som låser rent — og fire ledningsknuter som ble kuttet på benken

Råskissen gjør tre grep skarpere enn den tidligere horisontale sløyfen i `03_OPERATOR_TIL_GITHUB_KRYSS.md`:

- **Loddsnor med tyngdekraft:** Hovedbanen faller rett ned langs én akse i stedet for å knekke sidelengs, og hvert enkelt trinn har sin egen navngitte feilutgang.
- **`chmod 444` på `(L)` og `Vektorlås` på `(A)`:** Språkrommet er lesbart uten skrive- eller kjørebiter (`0444`), og prematur lukking i kunstpunktet $p_{\text{art}}$ drepes ikke, men tvinges via `HOLD` inn i søkerommet `(J)`.
- **Tre adskilte `0.00 V DC`-tilstander før luftgapet:** `[KLAR :: 0.00 V DC]` skiller tørrkontakten ved $\Delta_K = 0$ («eksponert bruddflate, null fullmakt») rent fra både `[HOLD :: 0.00 V DC]` og `[KILL :: 0.00 V DC]`. Inne i $\mathcal{F}$ finnes det ingen `5.00 V DC`-skinne å koble inn på egen hånd.

Når vi legger skissen under lupe på kretskortet, dukker det opp **fire konkrete knuter** i kobberbanene rundt `(J)`, `(D)` og `(Π_K)`:

| Nr. | Knute i råskissen | Hvorfor den bryter loven | Sveis i den herdede platen |
| :--- | :--- | :--- | :--- |
| **`1`** | **Ikke-planar kryssing (`┼` i kol. 19) og blind-ende (`┘` i kol. 48)** | Fordi både `HOLD`-sløyfen og `KILL`-utgangene ligger på *samme* side (høyre) av loddsnora, tvinger Jordans kurvesetning `(lekkasje) -> [KILL]` til å krysse returveien i `┼`. Samtidig ender `(papir-bokholderi)─┘` opp i den horisontale `[KILL]`-linjen etter at `└` alt har avsluttet `[HOLD]`-nedløpet. | Legg reversibel **`HOLD`-sløyfe til venstre ($X < 0$)** og irreversibel **`KILL`-avskjæring til høyre ($X > 0$)** rundt midtaksen ($X = 0$). Det gir **`0` kryssende ledere** og matcher `(0,0)`-koordinatkrysset direkte. |
| **`2`** | **Uklokket snarvei `(D) ──┴──► ▲ ──► (J)` forbi `[HOLD]`** | T-leddet `┴` på `(D)` sender en direkte pil `▲` opp i `(J)` *utenom* `[HOLD : τ <= τ_max]`. Dermed kan et system spinne evig mellom `(J)` og `(D)` uten at `HOLD`-klokka tikker mot `P_ext`. | All retur til `(J)` går utelukkende gjennom `[HOLD: Δ_K≠∅, τ≤τ_max]`. Ingen bakvei uten klokke. |
| **`3`** | **Sammenblanding av *uferdig bæreevne* og *papir-bokholderi* i `(D)`** | Ærlig kroppslig/fysisk underdekning ($\Delta_K \neq \varnothing$, hvilesperre eller ny tilskjæring) hører hjemme i `HOLD`. *Papir-bokholderi* — der ubetalte joule føres som betalt arbeid på papiret (*Ghost Win*) — er samme type forfalskning som `metafor = bevis`, `lekkasje` og `selv-autorisasjon`. | Skilt rent i to retninger fra `(D)`: **venstre** (`uferdig bæreevne` $\to$ `HOLD`) og **høyre** (`papir-bokholderi` $\to$ `KILL`). Dermed bærer alle fire `KILL`-pilene eksakt samme grunnregel: *forfalsket valuta for neste lag kuttes strømløst*. |
| **`4`** | **Asymptotisk `Δ_K -> 0`, manglende `Δ_K ≠ ∅` i `HOLD`, og manglende `HOLD`-utgang fra `Π_K`** | `Δ_K -> 0` åpner for flyttalls-epsilon («nesten null»). I tillegg må `HOLD` kreve ikke-tom mangellapp (`Δ_K ≠ ∅`), `Π_K` må kunne sende reelle restavvik / okkupert sone (`Δ_K ≠ 0`) til `HOLD`, og innskriften under luftgapet må bære append-only `SHA-256 WAL`. | Låst til eksakt **`Δ_K = 0`** i `Π_K`, **`Δ_K ≠ ∅`** i `HOLD`, egen venstreutgang fra `Π_K` til `HOLD`, og eksplisitt **`SHA-256 WAL`** i `[OPEN :: 5.00 V DC]`. |

---

## 3. Herdet, kryssfri stålplate (`0` kryssinger, `X < 0` = `HOLD`, `X = 0` = loddsnor, `X > 0` = `KILL`)

```text
                                      [u_raw]
                                         │
                                         ▼
                                     (L) Akustikk [chmod 444] ──(metafor = bevis)───► [KILL]
                                         │
                                         ▼
               ┌─(prematur lukking)─ (A) Vektorlås (p_art)
               │                         │
               ▼                         ▼
[P_ext] ◄─ [HOLD: Δ_K≠∅, τ≤τ_max] ─► (J) Søkerom {γ_i} ─────────(lekkasje)──────────► [KILL]
(τ > τ_max)    ▲                         │
               │                         ▼
               ├─(uferdig bæreevne)─ (D) Dans / Last ───────────(papir-bokholderi)──► [KILL]
               │                         │
               │                         ▼
               └─(Δ_K ≠ 0 / sone)─── (Π_K) Sluse [Δ_K=0, Σp≤1] ─(selv-autorisasjon)─► [KILL]
                                         │
                                         ▼
                                [KLAR :: 0.00 V DC]
            (Ytterste punkt i F — eksponert bruddflate, null fullmakt)
═════════════════════════════════ GALVANISK LUFTGAP ════════════════════════════════════════
                                         │
                                         ▼  Kun ved W_ext ∉ F mot fysisk / ekstern motprøve
                                [OPEN :: 5.00 V DC]
                  (Autorisert innskrift + SHA-256 WAL i P_COSMOS)
```

---

## 4. Symmetrikontroll over de to flankene

- **Venstre flanke (`HOLD :: 0.00 V DC`, $\Delta_K \neq \varnothing$, reversibel retur):** Tar imot alt som er *uferdig, men ærlig* — et punkt uten utfoldet bane fra `(A)`, en bane som trenger hvile eller ny vektfordeling fra `(D)`, eller et konkret restavvik / en okkupert sone fra `(Π_K)`. Klokka slår begge veier: `HOLD` åpner aldri av tid alene, og ved $\tau > \tau_{\max}$ løftes nøkkelen ut til `P_ext`.
- **Høyre flanke (`KILL :: 0.00 V DC`, jordet avskjæring):** Tar imot alt som *forfalsker neste lags valuta uten å betale prisen* — metafor ført som bevis i `(L)`, sideeffekt ut av nullspenningsrommet i `(J)`, gratis papir-bokholderi uten betalt last i `(D)`, og formell selv-autorisasjon utenfor eget gyldighetsområde i `(Π_K)`.
- **Bunnflate over og under luftgapet (`0.00 V DC` vs. `5.00 V DC`):** Ved `Δ_K = 0` og `Σ permit = 1` legger `Π_K` inn en spenningsløs tørrkontakt på **`[KLAR :: 0.00 V DC]`**. Selve spenningskilden (`5.00 V DC`) eksisterer først på undersiden av det galvaniske luftgapet, der ytre vitne $W_{\text{ext}} \notin \mathcal{F}$ prøver utfallet mot fysisk/ekstern virkelighet og klinker innskriften inn i append-only `SHA-256 WAL`.
