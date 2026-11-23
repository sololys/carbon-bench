#include "omega_interlock_core.h"

static omega_output_t make_safe_output(omega_state_t st)
{
	omega_output_t out;

	out.state      = st;
	out.out_enable = false;
	out.wdt_pin    = false;
	return out;
}

void omega_init(omega_interlock_t *ctx, uint64_t timeout_ns, uint64_t now_ns)
{
	if (!ctx)
		return;
	ctx->state           = OMEGA_HOLD;
	ctx->last_seq        = 0u;
	ctx->last_step_ns    = now_ns;
	ctx->last_frame_ns   = now_ns;
	ctx->timeout_ns      = timeout_ns;
	ctx->seq_initialized = false;
	ctx->wdt_toggle      = false;
}

omega_output_t omega_step(omega_interlock_t *ctx, const omega_input_t *in)
{
	uint64_t elapsed;
	omega_output_t out;

	if (!ctx || !in)
		return make_safe_output(OMEGA_KILL);

	/* 1. Klebrig KILL-laas eller korrupt tilstand -> aldri vei tilbake uten kald reset */
	if (ctx->state != OMEGA_HOLD && ctx->state != OMEGA_OPEN) {
		ctx->state      = OMEGA_KILL;
		ctx->wdt_toggle = false;
		return make_safe_output(OMEGA_KILL);
	}

	/* 2. Maskinvarefeil eller baklengs klokke (mellom alle steg) -> umiddelbar KILL */
	if (in->hw_fault || in->now_ns < ctx->last_step_ns) {
		ctx->state      = OMEGA_KILL;
		ctx->wdt_toggle = false;
		return make_safe_output(OMEGA_KILL);
	}
	ctx->last_step_ns = in->now_ns;

	/* 3. Sekvenskontroll ved ny ramme: strengt +1 og sperre mot U64_MAX-wraparound */
	if (in->frame_valid) {
		if (ctx->seq_initialized) {
			if (ctx->last_seq == OMEGA_U64_MAX ||
			    in->seq != (ctx->last_seq + 1u)) {
				ctx->state      = OMEGA_KILL;
				ctx->wdt_toggle = false;
				return make_safe_output(OMEGA_KILL);
			}
		}
		ctx->last_seq        = in->seq;
		ctx->last_frame_ns   = in->now_ns;
		ctx->seq_initialized = true;
	}

	/* 4. Normal tidsfrist, timeout_ns == 0 eller sluppet W_ext -> trygg retur til HOLD */
	elapsed = in->now_ns - ctx->last_frame_ns;
	if (!in->w_ext_high || !ctx->seq_initialized ||
	    ctx->timeout_ns == 0u || elapsed >= ctx->timeout_ns) {
		ctx->state      = OMEGA_HOLD;
		ctx->wdt_toggle = false;
		return make_safe_output(OMEGA_HOLD);
	}

	/* 5. Alle invarianter groenne -> OPEN + flipp AC-puls til ekstern HW-watchdog */
	ctx->state      = OMEGA_OPEN;
	ctx->wdt_toggle = !ctx->wdt_toggle;

	out.state      = OMEGA_OPEN;
	out.out_enable = true;
	out.wdt_pin    = ctx->wdt_toggle;
	return out;
}
