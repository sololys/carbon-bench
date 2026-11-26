# Celle 11 — Bell–KY 7-Qubit CPTP-Sluse (`C11 == iCE40UP5K RTL` & 128D $\mathbb{Q}$-Kanal)

> **Avgrensning:** `INSPIRED_BY != IMPLEMENTS != PROVES` · `AUTHORITY = NONE` (`0.00 V DC`).  
> Lukket bruddprøve i `L1` C11, `L1` eksakt 128-dimensjonal $\mathbb{Q}$-aritmetikk og `L1.5` syntetisert SystemVerilog RTL (`Lattice iCE40UP5K-SG48`).

---

## 1. De fem bruddene i råutkastet som drepes i denne cellen

1. **Spor-divisjonsfelle ($\tilde{\rho}_K = M\rho M^\dagger / \operatorname{Tr}(\cdot)$):** Brøkformen i eldre utkast krever enten skjult post-seleksjon (deteksjons-smutthull) eller ikke-lineær tilstandsavbildning som bryter No-Signalling. Erstattet med sporlåst 128D CPTP Kraus-kanal $\sum_\alpha K_\alpha^\dagger K_\alpha = I_{128}$ der nevneren er identisk lik $1$.
2. **Faste $45^\circ$-vinkler mot Horodecki-optimum ($w \in \{0, \dots, 5\}$):** Skiller rotfri fastvinkel $S_{45^\circ}^2(w) = \frac{2(10-w)^2}{25}$ ($\frac{98}{25} < 4$ ved $w = 3$) fra Horodecki-rotasjon $S_{\max}^2(w) = 4(1 + \frac{(5-w)^2}{25})$ ($\frac{116}{25} > 4$ ved $w = 3$).
3. **Fortegnsblindhet i $\lvert\Sigma_1^2 - \Sigma_2^2\rvert$ (`V06`):** Ren fortegnsvending $\Sigma(K_2) = -\Sigma(K_1) \neq 0$ gir $\Sigma_1^2 = \Sigma_2^2$. Slusen håndhever derfor også $(\Sigma_1 - \Sigma_2)^2 > \tau_{\mathrm{diff,sq}}$ i 128-bits heltall.
4. **2-Qubit ($d = 4$) Frobenius `L1 != L3`-skraper (`V02`):** Ruter enhver lokal kildedrift $\|\rho_{AB}(w) - \rho_{AB}(0)\|_F^2 = \frac{w^2}{50} > \tau_{\mathrm{tomo}}$ til `PORT_HOLD` slik at vanlig **L1**-støy aldri åpner porten.
5. **SI-2019 heltalls lyskjeglesperre og $2^{38}$-bøttevern (`V07`, `V09`–`V12`):** Låser $299\,792\,458 \cdot \Delta k \cdot T_{\mathrm{clk,ps}} < 2 \cdot 10^9 L_{\mathrm{mm}}$ (`200` sykluser PASS mot `201` `PORT_KILL` ved $2L = 60\text{ m}$), 8 No-Signalling-marginaler og bit-eksakt `128`-bits skuddskala $N = 2^{32}$.

---

6. **Sekvensiell slot-rekkefølgelås og knivseggsvektorer (`V13`–`V20`):** Låser `loaded_mask == (1 << slot) - 1` mot krysset arm-innlasting (`V19`), tester eksakt klassisk Bell-grense $\Sigma_1^2 = 4N^2$ mot $+1$ fysisk skudd (`V13`–`V14`), 64/128-bits låneovergang $2^{68}$ mot $2^{68}-1$ (`V15`–`V16`), $N = 2^{38}$ takmetning mot $2^{38}+1$ (`V17`–`V18`) og eksakt lyslik SI-grense `lc_lhs == lc_rhs` (`V20`).

---

## 2. Silisiumutlegg (`UPduino v3.1` / `iCE40UP5K-SG48`)

- **Yosys `0.23` (`bell_ky_sluice`):** `3 755 SB_LUT4` (`71,1 %`), **`0 / 8 SB_MAC16`**, **`20/20 XOR == 0`** mot `cells_sim.v`.
- **Post-PnR `nextpnr-ice40` + `icetime`:** **`4 883 / 5 280 ICESTORM_LC` (`92 %`)**, `0 DSP`, kritisk sti **`72,69 ns` (`13,76 MHz > 12,00 MHz` krystall, `89` logikknivåer)**.
