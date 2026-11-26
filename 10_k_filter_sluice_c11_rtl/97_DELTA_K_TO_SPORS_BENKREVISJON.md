# Celle 10 — To-Spors $\Delta_K$-Sluse (`C11 == iCE40UP5K RTL` & Rasjonal 2-Qubit Miljørekobling)

> **Avgrensning:** `INSPIRED_BY != IMPLEMENTS != PROVES` · `AUTHORITY = NONE` (`0.00 V DC`).  
> Lukket bruddprøve i `L1` C11, `L1` eksakt $\mathbb{Q}$-aritmetikk og `L1.5` syntetisert SystemVerilog RTL (`Lattice iCE40UP5K-SG48`).

---

## 1. De fem bruddene i råutkastet som drepes i denne cellen

1. **Skrivefri `kill_latched` i `const`-evaluering:** Råutkastet leste kun `s->kill_latched` uten å sette selve maskinvarelåsen når en arm feilet. Sveist til sekvensielt register `k_sluice_reg_t` (`kill_latched = 1`, `monitor_coupled = 0`, `actuator_v_en = 0`) med vitneført, ikke-slettende `k_sluice_l01_reset()` (`V05`–`V07`).
2. **Kausal overtellings-lekkasje (`valid_steps > total_steps`):** Ulikheten `valid_steps < total_steps` slapp korrupte tellere som `65 > 64` igjennom som gyldige. Skjerpet til streng likhet `valid_steps != total_steps -> PORT_KILL` (`V08`).
3. **Toerkomplement-singularitet (`INT64_MIN` = $-2^{63}$):** Fasespeilet $J(q, p) = (q, -p)$ mangler positiv motpart i $-2^{63}$. Gjerdet ut til umiddelbar `PORT_KILL` i både C11 og RTL (`V12`).
4. **Frakoblet inngangssjekk og 64/96-bits overløpsvern:** Kobler inn heltalls-makroakkumulator $\widetilde{C}_{n+1} \in [0, 100\,000]$, kovariansskranke $\lambda_{\mathrm{bound}} \le \lambda_{\max}$, 96-bits overløpsvakt på $\Delta_K^{(s)}$ og eksplisitt inngangslikhet `(q_A, p_A) == (q_B, p_B)` (`prep_match_ok == 0 -> PORT_HOLD`, `V03`).
5. **Spornorm-rot i dimensjon $d \ge 3$:** For én qubit ($d = 2$) er $\|\rho_A - \rho_B\|_1^2 \equiv 2\operatorname{Tr}((\rho_A - \rho_B)^2) \in \mathbb{Q}$; for $d \ge 3$ gir $\|\Delta\rho\|_1^2$ irrasjonale kryssledd $2\lvert\lambda_i\rvert\lvert\lambda_j\rvert$. Pre-porten låses derfor i Frobenius-kvadratet $\operatorname{Tr}((\rho_A - \rho_B)^2)\cdot Q_\rho \le P_\rho$.

---

## 2. Spor I ($\mathbb{Q}$) og Spor II (`iCE40UP5K-SG48` Post-PnR Timing)

- **Spor I (Pytagoreisk $(3, 4, 5) \to (7, 24, 25)$ 2-qubit rekobling i $\mathbb{Q}$):** Ved $n_1$ har $\lvert\psi^{(\pm)}\rangle = \frac{1}{5}(3\lvert 00\rangle \pm 4\lvert 11\rangle)$ identisk lokal tilstand $\rho_S = \operatorname{diag}(\frac{9}{25}, \frac{16}{25})$. Uten rekobling og ved Markoviansk fasesletting er $\Delta p = 0$ ($p = \frac{337}{625}$); med felles $U_{SE} = (R_S(-\theta)\otimes I_E)\,\mathrm{CNOT}_{S\to E}$ ved $n_2 > n_1$ blir $p_A = 1$, $p_B = \frac{49}{625}$ og **$\Delta p = \frac{576}{625} = 0{,}9216$**.
- **Spor II (`C11 == RTL == cells_sim.v`, `12/12 XOR == 0`):** Plassert og rutet på `UPduino v3.1` (`iCE40UP5K-SG48`, alle `901` inn-biter og `73` ut-biter skift-registrert): **`2 595 / 5 280 ICESTORM_LC` (`49 %`)**, **`0 / 8 DSP` (`0 SB_MAC16`)**, `75` logikknivåer og post-PnR `icetime` kritisk sti **`67,25 ns` (`F_max = 14,87 MHz` > `12,00 MHz` krystall)**.
