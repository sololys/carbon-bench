// SPDX-License-Identifier: GPL-2.0
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/spinlock.h>
#include <linux/ktime.h>
#include <linux/gpio/consumer.h>
#include <linux/ioctl.h>
#include <linux/build_bug.h>

#include "omega_interlock_core.h"

#define OMEGA_IOC_MAGIC 'O'

/* Fast 16-byte ramme over brukergrensesnittet (null flyttall) */
struct omega_user_frame {
	__u64 seq;
	__u8  frame_valid;
	__u8  hw_fault;
	__u8  out_state;      /* Returneres til bruker */
	__u8  out_enable;     /* Returneres til bruker */
	__u8  wdt_pin;        /* Returneres til bruker */
	__u8  reserved[3];
};

static_assert(sizeof(struct omega_user_frame) == 16);

#define OMEGA_IOC_STEP _IOWR(OMEGA_IOC_MAGIC, 1, struct omega_user_frame)

static DEFINE_SPINLOCK(omega_lock);
static omega_interlock_t omega_ctx;

/*
 * Valgfrie GPIO-pinner (NULL i QEMU-modus, kobber paa Raspberry Pi).
 * Merk: gpiod_get_value()/gpiod_set_value() kalles under spin_lock_irqsave,
 * som krever ikke-sovende, minnekartlagte SoC-GPIO-er (ikke I2C/SPI-expandere).
 */
static struct gpio_desc *gpio_out_enable;
static struct gpio_desc *gpio_wdt_pin;
static struct gpio_desc *gpio_w_ext_in;

static unsigned long timeout_ms = 50;
module_param(timeout_ms, ulong, 0444);
MODULE_PARM_DESC(timeout_ms, "Watchdog-frist i millisekunder (0 = alltid HOLD)");

static void omega_drive_copper(bool enable, bool wdt_level)
{
	if (gpio_out_enable)
		gpiod_set_value(gpio_out_enable, enable ? 1 : 0);
	if (gpio_wdt_pin)
		gpiod_set_value(gpio_wdt_pin, wdt_level ? 1 : 0);
}

static long omega_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct omega_user_frame uf;
	omega_input_t in;
	omega_output_t out;
	unsigned long flags;

	if (cmd != OMEGA_IOC_STEP)
		return -ENOTTY;

	if (copy_from_user(&uf, (void __user *)arg, sizeof(uf)))
		return -EFAULT;

	spin_lock_irqsave(&omega_lock, flags);

	in.now_ns      = ktime_get_ns();
	in.seq         = uf.seq;
	in.frame_valid = (uf.frame_valid != 0);
	in.hw_fault    = (uf.hw_fault != 0);
	/* Fysisk W_ext leses fra pinne hvis tilkoblet, ellers fail-closed 0 */
	in.w_ext_high  = gpio_w_ext_in ? (gpiod_get_value(gpio_w_ext_in) != 0) : false;

	out = omega_step(&omega_ctx, &in);
	omega_drive_copper(out.out_enable, out.wdt_pin);

	spin_unlock_irqrestore(&omega_lock, flags);

	uf.out_state  = (__u8)out.state;
	uf.out_enable = out.out_enable ? 1 : 0;
	uf.wdt_pin    = out.wdt_pin ? 1 : 0;

	if (copy_to_user((void __user *)arg, &uf, sizeof(uf)))
		return -EFAULT;

	return 0;
}

static const struct file_operations omega_fops = {
	.owner          = THIS_MODULE,
	.unlocked_ioctl = omega_ioctl,
};

static struct miscdevice omega_miscdev = {
	.minor = MISC_DYNAMIC_MINOR,
	.name  = "omega_interlock",
	.fops  = &omega_fops,
};

static int __init omega_kmod_init(void)
{
	u64 timeout_ns = (u64)timeout_ms * NSEC_PER_MSEC;

	omega_init(&omega_ctx, timeout_ns, ktime_get_ns());
	omega_drive_copper(false, false); /* Streng 0,00 V ved oppstart */

	pr_info("omega_interlock: lastet i HOLD (0,00 V), frist=%lu ms\n", timeout_ms);
	return misc_register(&omega_miscdev);
}

static void __exit omega_kmod_exit(void)
{
	unsigned long flags;

	spin_lock_irqsave(&omega_lock, flags);
	omega_ctx.state = OMEGA_KILL;
	omega_drive_copper(false, false); /* Kutt stroemmen foer avlasting */
	spin_unlock_irqrestore(&omega_lock, flags);

	misc_deregister(&omega_miscdev);
	pr_info("omega_interlock: avlastet i KILL (0,00 V)\n");
}

module_init(omega_kmod_init);
module_exit(omega_kmod_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Marius Egerhei Torjusen");
MODULE_DESCRIPTION("Fail-closed GPIO/Watchdog-forrigling med AC-ladepumpe");
