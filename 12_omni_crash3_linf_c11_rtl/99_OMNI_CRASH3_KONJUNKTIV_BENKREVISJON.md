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

## 2. Silisiumutlegg (`UPduino v3.1` / `iCE40UP5K-SG48`)

- **Yosys `0.23` (`omni_crash3_sluice`):** `2 582 SB_LUT4` (`48,9 %`), **`0 / 8 SB_MAC16`**, **`12/12 XOR == 0`** mot `cells_sim.v`.
- **Post-PnR `nextpnr-ice40` + `icetime`:** **`3 895 / 5 280 ICESTORM_LC` (`73 %`)**, `0 DSP`, kritisk sti **`78,84 ns` (`12,68 MHz > 12,00 MHz` krystall)**.
