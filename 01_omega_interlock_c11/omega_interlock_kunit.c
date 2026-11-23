// SPDX-License-Identifier: GPL-2.0
#include <kunit/test.h>
#include "omega_interlock_core.h"

/* 1. Oppstart skal alltid vaere HOLD (0,00 V) */
static void test_init_is_hold(struct kunit *test)
{
	omega_interlock_t ctx;

	omega_init(&ctx, 1000u, 100u);

	KUNIT_EXPECT_EQ(test, ctx.state, OMEGA_HOLD);
	KUNIT_EXPECT_FALSE(test, ctx.wdt_toggle);
}

/* 2. Gyldig sekvens + W_ext gir OPEN og AC-veksling (1 -> 0 -> 1) */
static void test_open_and_ac_toggle(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);

	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_OPEN);
	KUNIT_EXPECT_TRUE(test, out.out_enable);
	KUNIT_EXPECT_TRUE(test, out.wdt_pin);

	in.now_ns = 120u;
	in.seq    = 2u;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_OPEN);
	KUNIT_EXPECT_FALSE(test, out.wdt_pin); /* Maa veksle til 0 */

	in.now_ns = 130u;
	in.seq    = 3u;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_TRUE(test, out.wdt_pin);  /* Maa veksle tilbake til 1 */
}

/* 3. Sluppet W_ext faller trygt til HOLD og kan aapnes igjen */
static void test_w_ext_drop_returns_to_hold(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);
	omega_step(&ctx, &in);

	in.now_ns      = 120u;
	in.frame_valid = false;
	in.w_ext_high  = false;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_HOLD);
	KUNIT_EXPECT_FALSE(test, out.out_enable);
	KUNIT_EXPECT_FALSE(test, out.wdt_pin);

	/* Mennesket trykker inn W_ext igjen -> skal aapne rent */
	in.now_ns     = 130u;
	in.w_ext_high = true;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_OPEN);
}

/* 4. Tidsfrist (elapsed >= timeout_ns) og timeout == 0 holder HOLD */
static void test_timeout_returns_to_hold(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 100u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 50u, 100u);
	omega_step(&ctx, &in);

	in.now_ns      = 150u; /* elapsed == 50 >= 50 */
	in.frame_valid = false;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_HOLD);
	KUNIT_EXPECT_FALSE(test, out.out_enable);

	/* timeout_ns == 0 skal aldri aapne */
	omega_init(&ctx, 0u, 100u);
	in.now_ns      = 100u;
	in.frame_valid = true;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_HOLD);
}

/* 5. Replay eller sekvenshopp laaser klebrig KILL */
static void test_seq_violation_locks_kill(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);
	omega_step(&ctx, &in);

	/* Replay av seq=1 -> KILL */
	in.now_ns = 120u;
	in.seq    = 1u;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_KILL);
	KUNIT_EXPECT_FALSE(test, out.out_enable);

	/* Gyldig ramme etter KILL skal fortsatt avvises */
	in.now_ns = 130u;
	in.seq    = 2u;
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_KILL);
}

/* 6. Baklengs klokke mellom to tomme steg laaser KILL */
static void test_backwards_clock_locks_kill(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 100u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);
	omega_step(&ctx, &in);

	in.now_ns      = 150u;
	in.frame_valid = false;
	omega_step(&ctx, &in);

	in.now_ns = 120u; /* Klokka hoppet baklengs */
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_KILL);
}

/* 7. U64_MAX-wraparound laaser KILL */
static void test_u64_wraparound_locks_kill(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 110u, .seq = OMEGA_U64_MAX, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);
	omega_step(&ctx, &in);

	in.now_ns = 120u;
	in.seq    = 0u; /* Wraparound-forsoek */
	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_KILL);
}

/* 8. Korrupt tilstand (bit-flip i RAM) laaser KILL */
static void test_corrupt_state_locks_kill(struct kunit *test)
{
	omega_interlock_t ctx;
	omega_input_t in = { .now_ns = 110u, .seq = 1u, .frame_valid = true, .w_ext_high = true };
	omega_output_t out;

	omega_init(&ctx, 1000u, 100u);
	ctx.state = (omega_state_t)0xFFu; /* Simulert straaling / minnefeil */

	out = omega_step(&ctx, &in);
	KUNIT_EXPECT_EQ(test, out.state, OMEGA_KILL);
	KUNIT_EXPECT_FALSE(test, out.out_enable);
}

static struct kunit_case omega_test_cases[] = {
	KUNIT_CASE(test_init_is_hold),
	KUNIT_CASE(test_open_and_ac_toggle),
	KUNIT_CASE(test_w_ext_drop_returns_to_hold),
	KUNIT_CASE(test_timeout_returns_to_hold),
	KUNIT_CASE(test_seq_violation_locks_kill),
	KUNIT_CASE(test_backwards_clock_locks_kill),
	KUNIT_CASE(test_u64_wraparound_locks_kill),
	KUNIT_CASE(test_corrupt_state_locks_kill),
	{}
};

static struct kunit_suite omega_interlock_suite = {
	.name = "omega_interlock",
	.test_cases = omega_test_cases,
};

kunit_test_suite(omega_interlock_suite);

MODULE_LICENSE("GPL");
