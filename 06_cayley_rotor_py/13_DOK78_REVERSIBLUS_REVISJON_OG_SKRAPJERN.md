# Dokument 78 i Luftslusen: Revisjon av Reversiblus-rapporten mot kildetekst og benkprøve

> **Grenseoppgang:** `INSPIRED_BY != IMPLEMENTS != PROVES`. Originalmonografien `78_TIDSREVERSIBEL_INVOLUSJONSDYNAMIKK_OG_FASEMINNE.tex` (datert 18. september 2026) holdes urørt i `HOLD` av hensyn til arkivproveniens. Her kontrolleres revisjonsrapporten fra **Reversiblus** både mot selve LaTeX-kilden og mot eksakte moteksempler og rasjonal lineæralgebra i `14_dok78_cayley_rotor_og_konveks_moteksempel.py` (`6/6 PASS`, null flyttall). Programvarebaserte `Witness`-logger er append-only SHA-256-kjeder, ikke fysisk WORM-maskinvare.

---

## 1. Hva Reversiblus treffer helt presist i Dokument 78 (`JA`)

Kontrollert direkte mot `78_TIDSREVERSIBEL_INVOLUSJONSDYNAMIKK_OG_FASEMINNE.tex` sitter alle de tre påpekte punktene i seksjon 2 (`2A`, `2B`, `2C`) på ekte steder i kildeteksten:

* **2A — Dreiemoment i Seksjon 4.3 (`linje 275–285`):** Kildeteksten påstår både $\mathbf{P}_{\mathrm{tot}} = \mathbf{0}$ og $\mathbf{L}_{\mathrm{tot}} = \mathbf{0}$ for én enkelt to-legeme rotor $p_{1,2}(t) = m \pm R_{\hat{n}}(\omega t)r$. Fordi både arm og hastighet skifter fortegn samtidig under paritet ($(\pm 1)(\pm 1) = +1$), kansellerer $\mathbf{P}_{\mathrm{tot}}$, mens spinnmomentet **dobles** til $\mathbf{L}_{\mathrm{tot}} = 2\mu\,\mathbf{r}(t) \times (\vec{\omega} \times \mathbf{r}(t)) \neq \mathbf{0}$.
* **2B — Rasjonal Cayley-bro for SHA-256 (`linje 90 og 379–388`):** Kontinuerlige trigonometriske matriser i IEEE-754 gir uunngåelig $1\text{ ULP}$ avrundingsavvik under inversjon og utløser falsk `GATE::KILL` i $H(\operatorname{encode}(s''_{\mathrm{rev}})) \equiv H(\operatorname{encode}(s_{\mathrm{rev}}))$. Eksakt rasjonal Cayley-transform $R(S) = (I - S)(I + S)^{-1}$ med skjevsymmetrisk $S^\top = -S \in \mathbb{Q}^{n \times n}$ er alltid veldefinert ($\det(I + S) \ge 1 \gt 0$) og gir $R(-S)R(S) = I$ uten bit-tap.
* **2C — Elektrokjemisk origo ved $E_{\mathrm{eq}} \neq E_{\mathrm{pzc}}$ (`linje 307 og 314`):** Ved Nernst-likevekt ($\eta = 0$) bærer Helmholtz-dobbeltlaget normalt likevektsladning $q_{\mathrm{dl,eq}} \neq 0$ fordi $E_{\mathrm{eq}} \neq E_{\mathrm{pzc}}$. Å bruke overskuddspotensialet $\delta\phi_{\mathrm{dl}}(t) = (q_{\mathrm{dl}}(t) - q_{\mathrm{dl,eq}})/C_{\mathrm{dl}}$ gjør homomorfien strengt origo-bevarende ($\Psi(0) = 0$).

---

## 2. Tre skjerpelser der Reversiblus-rapporten selv må korrigeres før låsing (`SKRAPJERN-SJEKK`)

Når vi setter tall på selve revisjonsteksten fra Reversiblus, dukker det opp **én ren matematisk feilslutning i Seksjon 1** og **to skjulte randbetingelser i 2A og 2B** som må rettes så de ikke føres inn som nye feil i en eventuell `v2.0` av Dokument 78:

### Kritisk korreksjon 1 — Moteksempel mot påstanden i Seksjon 1 ($R_{N_K} = 2\Pi_K - I$ for konvekse sett)

I Seksjon 1 skriver Reversiblus:

> *«Når $A = N_K$ (normalkjeglen til det lukkede, konvekse admissible settet $K$), reduseres resolventen $J_{\gamma N_K} = (I + \gamma N_K)^{-1}$ eksakt til den idempotente ortogonale projeksjonen $\Pi_K$ ($\Pi_K^2 = \Pi_K$). Dermed bevarer Cayley-reflektoren $R_{N_K} = 2\Pi_K - I$ både involusjon ($R_{N_K}^2 = I$) og isometri ($R_{N_K}^\dagger R_{N_K} = I$)...»*

**Dette er usant for generelle lukkede konvekse mengder $K$:**

* Ta det enkleste konvekse settet med rand: halvlinjen $K = [0, \infty) \subset \mathbb{R}$. Da er Moreau-/metrikkprojeksjonen $\Pi_K(x) = \max(0, x)$ ($\Pi_K^2 = \Pi_K$), mens Cayley-reflektoren blir absoluttverdien:
  $$R_{N_K}(x) = 2\max(0, x) - x = |x|$$
  For $x = -1$ gir dette $R_{N_K}(-1) = +1$ og $R_{N_K}(R_{N_K}(-1)) = +1 \neq -1$ (**ikke involusjon!**), og avstanden mellom $+1$ og $-1$ kollapser fra $|1 - (-1)| = 2$ til $|R_{N_K}(1) - R_{N_K}(-1)| = 0$ (**ikke isometri!** — tvert imot en irreversibel $2\text{-til-}1\text{-bretting}$ som sletter fortegnsbiten). På enhetskula $K = \{x : \|x\| \le 1\}$ sendes til og med ethvert punkt med $\|x\| = 2$ rett i origo: $R_{N_K}(x) = 2(x/2) - x = \mathbf{0}$.
* **Eksakt gyldighetsområde:** $R_K = 2\Pi_K - I$ er en involusjon og isometri **hvis og bare hvis $K$ er et lukket lineært underrom** (eller affint underrom ved translasjon), der $\Pi_K$ er en *lineær* selvadjungert operator ($P = P^\dagger$, jf. Teorem 3 i Dokument 78). For et generelt konvekst sett med indre og rand er $R_{N_K}$ kun **ikke-ekspansiv** ($\|R_{N_K}x - R_{N_K}y\| \le \|x - y\|$), aldri involutiv på utsiden av $K$.

### Kritisk korreksjon 2 — Skjult gyroskopisk tverrmoment i 2A når $\mathbf{r} \not\perp \hat{n}$

I 2A foreslår Reversiblus å koble to rotorer med $+\vec{\omega}$ og $-\vec{\omega}$ for å oppnå $\mathbf{L}_{\mathrm{tot}} = \mathbf{0}$. Det holder **kun dersom armvektoren står vinkelrett på rotasjonsaksen ($\mathbf{r} \perp \hat{n}$)**!

Hvis $\hat{n} = \hat{z}$ og startvektoren har både ekvatorialkomponent $r_\perp \neq 0$ og aksial komponent $r_\parallel = \mathbf{r} \cdot \hat{n} \neq 0$, gir det kontraroterende 4-legemesystemet $p_{1,2}^\pm(t) = m \pm R_{\hat{z}}(\pm\omega t)\mathbf{r}_0$:

$$\mathbf{L}_{\mathrm{tot}}(t) = \mathbf{L}^+(t) + \mathbf{L}^-(t) = \bigl(0,\; -4\mu\,\omega\,r_\perp r_\parallel \sin(\omega t),\; 0\bigr) \neq \mathbf{0}$$

Aksialspinnene langs $\hat{z}$ kansellerer, men det ikke-diagonale treghetsleddet dobler seg langs $\hat{y}$ som et oscillerende vippemoment! Ligningen i Seksjon 4.3 må derfor kreve **både** kontraroterende par $(+\vec{\omega}, -\vec{\omega})$ **og** hovedakse-ortogonalitet $\mathbf{r}_0 \cdot \hat{n} = 0$ (eventuelt et 4-punkts hovedaksekryss per rotor).

### Kritisk korreksjon 3 — Kanonisk $\gcd$-forkorting i `encode` under 2B

Selv om $R(-S)R(S)s_{\mathrm{rev}} = s_{\mathrm{rev}}$ holder eksakt som rasjonale tall over $\mathbb{Q}$, opererer SHA-256 på **rå bytes**, ikke på ekvivalensklasser i $\mathbb{Q}$. Hvis en matriseimplementasjon lagrer homogene heltallspar $(p, q)$ uten forkorting (slik at returen gir $(2p, 2q)$ i stedet for $(p, q)$), feiler $H(\operatorname{encode}(s''_{\mathrm{rev}})) \equiv H(\operatorname{encode}(s_{\mathrm{rev}}))$ med falsk `GATE::KILL`. Spesifikasjonen av $\operatorname{encode}$ må derfor påby kanonisk forkortet brøkform ($\gcd(|p|, q) = 1,\; q \gt 0$).

---

## 3. Revidert låsematrise klar for eventuell `v2.0` av Dokument 78

| Seksjon i Dok. 78 | Reversiblus-status | Benkens sluttstatus | Nødvendig presisering ved opplåsing |
| :--- | :--- | :--- | :--- |
| **Seksjon 1 & 6 (`encode` + Cayley)** | `PRESISERES` | **`L1 PASS` med `gcd`-krav** | Bruk $R(S)=(I-S)(I+S)^{-1}$ over $\mathbb{Q}^{n \times n}$ med kanonisk brøkforkorting i `encode`, eller Feistel på $\mathbb{Z}_2^{1000}$; presiser at programvare-`Witness` er append-only SHA-256 (ikke fysisk WORM) |
| **Seksjon 3 (Teorem 1–3 vs. $N_K$)** | `VERIFISERT` *(men med feil påstand om $R_{N_K}$)* | **SKJERPES SKARP** | Skill strengt mellom **lineært underrom** $K$ ($R_K = 2\Pi_K - I$ er involusjon og isometri) og **generelt konvekst sett** $K$ ($\Pi_K = J_{\gamma N_K}$ er ikke-lineær Moreau-projeksjon, der $R_{N_K}$ *ikke* er involusjon) |
| **Seksjon 4.3 (Rigid Rotor)** | `KORRIGERES` *(4-punkts $\pm\omega$)* | **KORRIGERES + $\mathbf{r} \perp \hat{n}$** | Krev kontraroterende 4-legemepar $(+\vec{\omega}, -\vec{\omega})$ **samt** $\mathbf{r}_0 \cdot \hat{n} = 0$ så også det gyroskopiske tverrmomentet $-4\mu\omega r_\perp r_\parallel \sin(\omega t)$ forsvinner |
| **Seksjon 5.1 (Homomorfien $\Psi$)** | `PRESISERES` | **`L1 PASS`** | Erstatt $q_{\mathrm{dl}}/C_{\mathrm{dl}}$ med overskuddspotensialet $\delta\phi_{\mathrm{dl}} = (q_{\mathrm{dl}} - q_{\mathrm{dl,eq}})/C_{\mathrm{dl}}$ for origo-invarians ved $E_{\mathrm{eq}} \neq E_{\mathrm{pzc}}$ |
