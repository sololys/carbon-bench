# Celle 12 — Konjunktiv $L_\infty$ Treveis Krasjsluse (`Crash_3` & Gullsnittring $\mathbb{Z}[\varphi]$)

> **Avgrensning:** `INSPIRED_BY != IMPLEMENTS != PROVES` · `AUTHORITY = NONE` (`0.00 V DC`).  
> Lukket bruddprøve i `L1` C11, `L1` eksakt kvadratisk heltallsring $\mathbb{Z}[\varphi]$ og `L1.5` syntetisert SystemVerilog RTL (`Lattice iCE40UP5K-SG48`).

---

## 1. De seks bruddene i eldre utkast som drepes i denne cellen

1. **IEEE-754 `NaN`-gjennomslipp til `5,00 V DC`:** Flyttallssammenligninger `NaN > terskel` returnerte `false` på tvers av alle vakter og slapp korrupte målinger rett gjennom til `OPEN`. Erstattet med 32/64-bits heltallsregistre (`0` flyttalls-/SIMD-instruksjoner i `objdump -d`).
2. **Vektet $L_1$-sum (`C_crash`) og glemt $\dot{R} > \delta_R$ (`V03`):** Den gamle vektsummen blandet enheter og hadde utelatt $\dot{R} > \delta_R$ i portstigen. Erstattet med verste-akse $L_\infty$-overskudd og eksplisitt `r_dot > delta_r -> PORT_HOLD`.
3. **Tautologisk involusjons-attrapp `(s ^ r) ^ r == s` (`V09`, `V12`):** Lokal XOR-rundtur er alltid sann uansett bitfeil på linjen. Erstattet med mottatt trådord-sjekk `(m_rx_16 ^ r_mask_16) == s_phase_16` og `INT32_MIN`-gjerde før $J(q, p) = (q, -p)$.
4. **Eksakt gullsnittring $\mathbb{Z}[\varphi]$ uten $\sqrt{5}$ (`V01`, `V05`):** Via $\varphi^2 = \varphi + 1$ og $\varphi^{-1} = \varphi - 1$ evalueres $2H_\varphi(x) = A_H + B_H\varphi$ eksakt i heltall (`237 100 + 650 phi` i `V01`), med rotfri ordning $5B^2$ mot $(2A + B)^2$.
5. **SI-2019 lyskjeglediamant og strukturell QR-dekoding (`V10`–`V11`):** Håndhever $2\,000\,000\,000 \cdot r_{\mathrm{mm}} \le 299\,792\,458 \cdot \tau_{\mathrm{ps}}$ inne i $20{,}0\text{ m}$ / $133\,425\text{ ps}$ samt Finder-signatur `0x7F415D417F` og Quiet-Zone $\Gamma \ge 4$.
6. **Divisjonsfri GKO-R horisont og monoton OR-sikring (`V04`, `V07`, `V08`):** Evaluerer $(-g) < \dot{g}\tau_{\mathrm{hold}}$ uten divisjon, brenner inn monoton 16-bits OR-sikring `0xf5aa` kun ved `PORT_OPEN`, og sporer baneklassene `O_2 -> O_1` mot `O_0`.

---

7. **63-bits $\mathbb{Z}[\varphi]$-hjørnelås, stasjonær MSB=0 MAC og kantvektorer (`V13`–`V20`):** Gjerder ut MSB-overløp (`k_defect[31] | b_barrier[31] | c_care[31]`, `V20`) og `UINT32_MAX`-epoke, verifiserer motsatt fortegn $2H_\varphi = -800 + 1000\varphi > 0$ (`V15`), negativ $L_\infty$-kant `250` mot `251` (`V14`, `V17`), $+1\text{ LSB}$ `pi == tau` (`V16`), sub-millimeter SI-lyskjegle `19 999` mot `20 000 mm` ved `133 425 ps` (`V13`, `V18`) og det eksakte 63-bits maks-hjørnet `0x7FFFFFFF` (`V19`).

---

## 2. Silisiumutlegg (`UPduino v3.1` / `iCE40UP5K-SG48`)

- **Yosys `0.23` (`omni_crash3_sluice`):** `2 582 SB_LUT4` (`48,9 %`), **`0 / 8 SB_MAC16`**, **`20/20 XOR == 0`** mot `cells_sim.v`.
- **Post-PnR `nextpnr-ice40` + `icetime`:** **`3 649 / 5 280 ICESTORM_LC` (`69 %`)**, `0 DSP`, kritisk sti **`37,22 ns` (`26,86 MHz > 12,00 MHz` krystall, `38` logikknivåer)**.
