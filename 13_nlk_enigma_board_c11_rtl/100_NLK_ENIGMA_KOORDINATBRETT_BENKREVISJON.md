# Celle 13 — `KY-Enigma v1.1 -> NLK` Konsekvenssluse og Romlig Stål-Koordinatbrett (`C11 == iCE40UP5K RTL`)

> **Avgrensning:** `INSPIRED_BY != IMPLEMENTS != PROVES` · `AUTHORITY = NONE` (`0.00 V DC`).  
> Lukket bruddprøve i `L1` C11, `L1` eksakt mod-26 permutasjonsalgebra og `L1.5` syntetisert SystemVerilog RTL (`Lattice iCE40UP5K-SG48`). KY-Enigma er en reversibel tilstandsdemonstrator, ikke kryptografi for sensitive data.

---

## 1. De seks bruddene som drepes ved overgang fra programvareskisse til silisium

1. **Strandede rotorposisjoner ved LIFO-reversering (`V02`–`V04`):** Å poppe LIFO-stabelen uten å verifisere `top.q_prop == q_auth` og spole `q_auth` tilbake til `q_bef` etterlater rotorvognen i fremtiden. Maskinvareslusen verifiserer $E_{q_{\mathrm{prop}}}(y_{\mathrm{cand}}) = x_{\mathrm{in}}$ på silisium og spoler `q_auth` eksakt baklengs over tre-rotors hakk-kaskaden `(1, 5, 23) -> (0, 4, 22)` ved `0.00 V DC`.
2. **Koordinatbrett-omgåelse av krasjlås og enveis-lov (`V19`, `V21`–`V22`):** I en naiv programvareimplementasjon kan `verify_coordinate_board` kalles mens `outcome_unknown_hold == 1` eller uten eksternt vitne $W_{\mathrm{ext}}$. Her stanser både `outcome_unknown_hold` (`V19 -> HOLD`) og manglende `witness_ext` (`V21 -> HOLD`) brettet ved `0.00 V DC` før `W_ext` utløser atomisk sprang `q_0 -> q_K` (`V22 -> OPEN`).
3. **Falsk `5.00 V`-loggføring i krasjvinduet mellom `◉` og `1` (`V18`):** Ved avbrudd etter varig forpliktelse før observasjon låses `outcome_unknown_out = 1` med `actuator_v_en_out = 0` (`0.00 V DC`).
4. **Konstant-tids 8-spors stål-tolk med `KILL > HOLD` (`V20`, `V23`):** Evaluerer alle 8 brettspor i konstant tid (`130` sykluser), håndhever sekvensiell innlastingsmaske og feller umiddelbar `PORT_KILL` ved skjøtbrudd på rute 1 selv når rute 3 mangler (`V23`).
5. **Divisjonsfri mod-26 kjerne, kryssterskler og SI-2019 Landauer-gulv (`V05`–`V08`, `V13`–`V15`):** To-takts `SB_LUT4`-permutasjonsmotor (`0` `%`-divisorer, `0` `SB_MAC16` DSP-er), eksakt heltallskryssing `10e` mot `9sigma` / `15sigma`, og 22-syklus skift-addering for `bits_erased * 2 652 306 rJ`.
6. **Monitor-frakobling og selvtest-låst Level 01-reset (`V08`–`V12`, `V24`):** `PORT_KILL` setter `kill_latched = 1` og `monitor_coupled = 0`; gjenåpning til `HOLD` avvises dersom `selftest_ok == 0` (`V10`), og korrupt LIFO-minne utløser umiddelbar `PORT_KILL` (`V24`).

---

## 2. Silisiumutlegg (`UPduino v3.1` / `iCE40UP5K-SG48`)

- **Yosys `0.23` (`nlk_enigma_sluice`):** `2 406 SB_LUT4` (`45,6 %`), **`0 / 8 SB_MAC16`**, `0` advarsler, **`24/24 XOR == 0`** mot `cells_sim.v`.
- **Post-PnR `nextpnr-ice40` + `icetime`:** **`3 348 / 5 280 ICESTORM_LC` (`63 %`)**, `0 DSP`, **`17` logikknivåer**, kritisk sti **`42,81 ns` (`23,36 MHz > 12,00 MHz` krystall, `+40,52 ns` klaring)**.
