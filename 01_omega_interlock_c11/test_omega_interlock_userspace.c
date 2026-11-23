#include <stdio.h>
#include "omega_interlock_core.h"

static int pass_cnt = 0;
static int fail_cnt = 0;

static void check(const char *name, bool cond)
{
	if (cond) {
		printf("[PASS] %s\n", name);
		pass_cnt++;
	} else {
		printf("[FAIL] %s\n", name);
		fail_cnt++;
	}
}

int main(void)
{
	omega_interlock_t ctx;
	omega_input_t in;
	omega_output_t out;

	/* 1. Init -> HOLD */
	omega_init(&ctx, 1000u, 100u);
	check("T01 init is HOLD (0.00 V)", ctx.state == OMEGA_HOLD && !ctx.wdt_toggle);

	/* 2. OPEN + AC toggle (1 -> 0 -> 1) */
	in = (omega_input_t){ .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	out = omega_step(&ctx, &in);
	bool t2_a = (out.state == OMEGA_OPEN && out.out_enable && out.wdt_pin);
	in.now_ns = 120u; in.seq = 2u;
	out = omega_step(&ctx, &in);
	bool t2_b = (out.state == OMEGA_OPEN && !out.wdt_pin);
	in.now_ns = 130u; in.seq = 3u;
	out = omega_step(&ctx, &in);
	bool t2_c = (out.state == OMEGA_OPEN && out.wdt_pin);
	check("T02 OPEN + AC-puls (1 -> 0 -> 1)", t2_a && t2_b && t2_c);

	/* 3. Sluppet W_ext -> HOLD og gjenopptak */
	in.now_ns = 140u; in.frame_valid = false; in.w_ext_high = false;
	out = omega_step(&ctx, &in);
	bool t3_a = (out.state == OMEGA_HOLD && !out.out_enable && !out.wdt_pin);
	in.now_ns = 150u; in.w_ext_high = true;
	out = omega_step(&ctx, &in);
	bool t3_b = (out.state == OMEGA_OPEN && out.out_enable);
	check("T03 W_ext-drop -> HOLD -> OPEN", t3_a && t3_b);

	/* 4. Timeout + timeout_ns == 0 */
	omega_init(&ctx, 50u, 100u);
	in = (omega_input_t){ .now_ns = 100u, .seq = 1u, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	omega_step(&ctx, &in);
	in.now_ns = 150u; in.frame_valid = false;
	out = omega_step(&ctx, &in);
	bool t4_a = (out.state == OMEGA_HOLD && !out.out_enable);
	omega_init(&ctx, 0u, 100u);
	in.now_ns = 100u; in.frame_valid = true;
	out = omega_step(&ctx, &in);
	bool t4_b = (out.state == OMEGA_HOLD && !out.out_enable);
	check("T04 Timeout + timeout_ns==0 -> HOLD", t4_a && t4_b);

	/* 5. Replay -> klebrig KILL */
	omega_init(&ctx, 1000u, 100u);
	in = (omega_input_t){ .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	omega_step(&ctx, &in);
	in.now_ns = 120u; in.seq = 1u;
	out = omega_step(&ctx, &in);
	bool t5_a = (out.state == OMEGA_KILL && !out.out_enable);
	in.now_ns = 130u; in.seq = 2u;
	out = omega_step(&ctx, &in);
	bool t5_b = (out.state == OMEGA_KILL && !out.out_enable);
	check("T05 Replay -> klebrig KILL", t5_a && t5_b);

	/* 6. Baklengs klokke mellom tomme steg -> KILL */
	omega_init(&ctx, 1000u, 100u);
	in = (omega_input_t){ .now_ns = 100u, .seq = 1u, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	omega_step(&ctx, &in);
	in.now_ns = 150u; in.frame_valid = false;
	omega_step(&ctx, &in);
	in.now_ns = 120u;
	out = omega_step(&ctx, &in);
	check("T06 Baklengs klokke -> KILL", out.state == OMEGA_KILL && !out.out_enable);

	/* 7. U64_MAX wraparound -> KILL */
	omega_init(&ctx, 1000u, 100u);
	in = (omega_input_t){ .now_ns = 110u, .seq = OMEGA_U64_MAX, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	omega_step(&ctx, &in);
	in.now_ns = 120u; in.seq = 0u;
	out = omega_step(&ctx, &in);
	check("T07 U64_MAX wraparound -> KILL", out.state == OMEGA_KILL && !out.out_enable);

	/* 8. Korrupt tilstand -> KILL */
	omega_init(&ctx, 1000u, 100u);
	ctx.state = (omega_state_t)0xFFu;
	in = (omega_input_t){ .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true, .hw_fault = false };
	out = omega_step(&ctx, &in);
	check("T08 Korrupt tilstand -> KILL", out.state == OMEGA_KILL && !out.out_enable);

	printf("RESULTAT: %d PASS / %d FAIL\n", pass_cnt, fail_cnt);
	return fail_cnt == 0 ? 0 : 1;
}
