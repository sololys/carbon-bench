CC      ?= gcc
CFLAGS  := -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Wconversion -Wsign-conversion
KDIR    ?= /lib/modules/$(shell uname -r)/build

obj-m += omega_interlock.o
omega_interlock-objs := omega_interlock_kmod.o omega_interlock_core.o omega_spi_frame.o

.PHONY: test test-core test-spi kmod clean

test: test-core test-spi

test-core: test_omega_interlock_userspace.c omega_interlock_core.c omega_interlock_core.h
	$(CC) $(CFLAGS) -o test_omega_interlock test_omega_interlock_userspace.c omega_interlock_core.c
	./test_omega_interlock

test-spi: test_omega_spi_frame.c omega_spi_frame.c omega_spi_frame.h
	$(CC) $(CFLAGS) -o test_omega_spi_frame test_omega_spi_frame.c omega_spi_frame.c
	./test_omega_spi_frame

kmod:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	rm -f test_omega_interlock test_omega_spi_frame
	$(MAKE) -C $(KDIR) M=$(PWD) clean 2>/dev/null || true
