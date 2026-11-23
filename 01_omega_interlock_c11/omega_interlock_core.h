#ifndef OMEGA_INTERLOCK_CORE_H
#define OMEGA_INTERLOCK_CORE_H

#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/limits.h>
#define OMEGA_U64_MAX U64_MAX
#else
#include <stdint.h>
#include <stdbool.h>
#define OMEGA_U64_MAX UINT64_MAX
#endif

/*
 * MASKINVAREKONTRAKT (FAIL-CLOSED):
 * 1. `wdt_pin` driver en AC-koblet ladepumpe (ekstern HW-watchdog).
 *    Kun veksling (0 -> 1 -> 0 -> 1) holder spenningen oppe.
 *    Fryser CPU, stopper vekslingen og kobberet faller til 0,00 V.
 * 2. Fysisk W_ext-bryter (Level 01) ligger ALLTID i serie i kobberet utenfor CPU.
 */

typedef enum {
	OMEGA_KILL = 0x00u, /* 0,00 V LAST til kald omstart */
	OMEGA_HOLD = 0x3Cu, /* 0,00 V TRYGG hviletilstand   */
	OMEGA_OPEN = 0xA5u  /* HOY utgang (kun med W_ext=1) */
} omega_state_t;

typedef struct {
	omega_state_t state;
	uint64_t      last_seq;
	uint64_t      last_step_ns;    /* Monoton sjekk hvert eneste steg     */
	uint64_t      last_frame_ns;   /* Tidsstempel for siste gyldige ramme */
	uint64_t      timeout_ns;
	bool          seq_initialized;
	bool          wdt_toggle;      /* AC-veksling til ladepumpe           */
} omega_interlock_t;

typedef struct {
	uint64_t now_ns;        /* Monoton klokke (CLOCK_MONOTONIC / ktime_get_ns) */
	uint64_t seq;           /* Sekvensnummer fra ramme                         */
	bool     frame_valid;   /* True hvis ny, verifisert ramme ankom            */
	bool     w_ext_high;    /* Fysisk menneskelig noekkelpinne                 */
	bool     hw_fault;      /* Maskinvarefeil / sensoravvik / kapringsforsoek  */
} omega_input_t;

typedef struct {
	omega_state_t state;
	bool          out_enable; /* 1 = tillat utgang, 0 = streng 0,00 V        */
	bool          wdt_pin;    /* Veksler 0/1 i OPEN, streng 0 i HOLD og KILL */
} omega_output_t;

void           omega_init(omega_interlock_t *ctx, uint64_t timeout_ns, uint64_t now_ns);
omega_output_t omega_step(omega_interlock_t *ctx, const omega_input_t *in);

#endif /* OMEGA_INTERLOCK_CORE_H */
