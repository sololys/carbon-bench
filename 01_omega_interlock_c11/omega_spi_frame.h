#ifndef OMEGA_SPI_FRAME_H
#define OMEGA_SPI_FRAME_H

#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/build_bug.h>
#define OMEGA_STATIC_ASSERT(cond, msg) static_assert(cond)
#else
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define OMEGA_STATIC_ASSERT(cond, msg) _Static_assert(cond, msg)
#endif

/*
 * SPI-RAMMEFORMAT OG C-HAL REGISTERKART: /dev/omega_interlock <-> UPduino v3.1
 *
 * Eksakt 64-byte (512-bit) wire-ramme, little-endian slik at wire[i] == f[8*i +: 8]
 * i tb_omega_gate_fsm.sv:
 *
 *   Byte  0..3   (  32 b) : MAGIC      = 0x4F4D4741 ("OMGA")
 *   Byte  4..5   (  16 b) : CMD        = 0x5A01 (ARM), 0xA502 (OPEN), 0xC303 (KILL)
 *   Byte  6..7   (  16 b) : WIN        = TTL / WINDOW_CYC (heltall klokkesykluser)
 *   Byte  8..11  (  32 b) : SEQ        = Monotont sekvensnummer
 *   Byte 12..15  (  32 b) : EPOCH      = BOOT_EPOCH (kaldstart-epoke)
 *   Byte 16..19  (  32 b) : REF_SEQ    = Referert ARM-sekvens (for OPEN)
 *   Byte 20..23  (  32 b) : REF_EPOCH  = Referert ARM-epoke   (for OPEN)
 *   Byte 24..31  (  64 b) : EVIDENCE   = Eksplisitt evidens-ID (maa != 0 i OPEN)
 *   Byte 32..43  (  96 b) : Q_XYZ      = 3 x 32-bit 3D-koordinat (maa == 0 i OPEN)
 *   Byte 44..59  ( 128 b) : AUTH_TAG   = 128-bit MAC over byte 0..43
 *   Byte 60..63  (  32 b) : CRC32C     = Castagnoli CRC32C (0x82F63B78) over byte 0..59
 *
 * TILLITSMODELL (KILL > HOLD > OPEN):
 *   - Fysisk kill_raw (kobber, Level 01) kutter i 0 sykluser uten SPI/MAC.
 *   - Buss-kommando OMEGA_CMD_KILL (Level 02) er IKKE en noedstopp: den krever
 *     full CRC32C + AUTH_TAG (MAC) + EPOCH + SEQ foer ST_KILL latches.
 */

#define OMEGA_SPI_FRAME_BYTES   64u
#define OMEGA_SPI_STATUS_BYTES  16u
#define OMEGA_FRAME_MAGIC       0x4F4D4741u /* "OMGA" */

#define OMEGA_CMD_ARM           0x5A01u
#define OMEGA_CMD_OPEN          0xA502u
#define OMEGA_CMD_KILL          0xC303u     /* Autentisert buss-KILL (krever MAC) */

/* FPGA-statuskoder i 16-byte SPI-returramme (C-HAL registerkart) */
#define OMEGA_FPGA_ST_KILL      0x00u
#define OMEGA_FPGA_ST_HOLD      0x3Cu
#define OMEGA_FPGA_ST_ARMED     0x5Au
#define OMEGA_FPGA_ST_OPEN      0xA5u

/* Feilflagg-bitmaske i FPGA-statussvar */
#define OMEGA_FLT_CRC           (1u << 0)
#define OMEGA_FLT_MAC           (1u << 1)
#define OMEGA_FLT_EPOCH         (1u << 2)
#define OMEGA_FLT_SEQ           (1u << 3)
#define OMEGA_FLT_NONCANON_Q    (1u << 4)
#define OMEGA_FLT_HW_KILL_RAW   (1u << 5)
#define OMEGA_FLT_VOUT_SENSE    (1u << 6)

typedef enum {
	OMEGA_PARSE_OK               = 0,
	OMEGA_PARSE_ERR_NULL         = 1,
	OMEGA_PARSE_ERR_MAGIC        = 2,
	OMEGA_PARSE_ERR_CRC          = 3,
	OMEGA_PARSE_ERR_CMD          = 4,
	OMEGA_PARSE_ERR_NONCANON_Q   = 5,
	OMEGA_PARSE_ERR_NO_EVIDENCE  = 6
} omega_parse_rc_t;

typedef struct {
	uint32_t magic;
	uint16_t cmd;
	uint16_t win;
	uint32_t seq;
	uint32_t epoch;
	uint32_t ref_seq;
	uint32_t ref_epoch;
	uint64_t evidence;
	uint32_t q_xyz[3];       /* qx=q_xyz[0], qy=q_xyz[1], qz=q_xyz[2] */
	uint8_t  auth_tag[16];
	uint32_t crc32c;
} omega_spi_frame_t;

typedef struct {
	uint8_t  fpga_state;     /* OMEGA_FPGA_ST_*              */
	uint8_t  fault_flags;    /* OMEGA_FLT_*                  */
	uint8_t  w_ext_live;     /* 1 = fysisk W_ext hoey        */
	uint8_t  reserved;
	uint32_t active_epoch;
	uint32_t last_seq;
	uint32_t crc32c;         /* CRC32C over byte 0..11       */
} omega_fpga_status_t;

/* Flyttallsfri CRC32C (Castagnoli, reflektert polynom 0x82F63B78) */
uint32_t omega_crc32c(const uint8_t *data, size_t len);

/* Pakk og beregn CRC32C til eksakt 64-byte SPI-wire-buffer */
omega_parse_rc_t omega_spi_frame_pack(const omega_spi_frame_t *in,
				      uint8_t wire[OMEGA_SPI_FRAME_BYTES]);

/* Pakk ut 64-byte SPI-wire-buffer, verifiser MAGIC, CRC32C, CMD og kanonisk OPEN */
omega_parse_rc_t omega_spi_frame_unpack(const uint8_t wire[OMEGA_SPI_FRAME_BYTES],
					omega_spi_frame_t *out,
					bool *requires_mac_auth);

/* Pakk/pakk ut 16-byte FPGA-statussvar (UPduino -> Linux C-HAL) */
omega_parse_rc_t omega_fpga_status_pack(const omega_fpga_status_t *in,
					uint8_t wire[OMEGA_SPI_STATUS_BYTES]);
omega_parse_rc_t omega_fpga_status_unpack(const uint8_t wire[OMEGA_SPI_STATUS_BYTES],
					  omega_fpga_status_t *out);

#endif /* OMEGA_SPI_FRAME_H */
