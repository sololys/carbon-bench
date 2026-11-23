#include <stdio.h>
#include <string.h>
#include "omega_spi_frame.h"

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
	uint8_t wire[OMEGA_SPI_FRAME_BYTES];
	uint8_t st_wire[OMEGA_SPI_STATUS_BYTES];
	omega_spi_frame_t in, out;
	omega_fpga_status_t st_in, st_out;
	bool req_mac = false;

	/* S01: Standard Castagnoli CRC32C-vektor: "123456789" -> 0xE3069283 */
	{
		const uint8_t vec[9] = { '1','2','3','4','5','6','7','8','9' };
		uint32_t c = omega_crc32c(vec, sizeof(vec));
		check("S01 CRC32C Castagnoli standardvektor (0xE3069283)", c == 0xE3069283u);
	}

	/* S02: ARM-ramme round-trip + bit-layout paritet med tb_omega_gate_fsm.sv */
	memset(&in, 0, sizeof(in));
	in.cmd      = OMEGA_CMD_ARM;
	in.win      = 25u;
	in.seq      = 1u;
	in.epoch    = 1u;
	in.q_xyz[0] = 0x33333333u;
	in.q_xyz[1] = 0x22222222u;
	in.q_xyz[2] = 0x11111111u;
	in.auth_tag[0] = 0x88u;
	in.auth_tag[15] = 0xA5u;

	check("S02 ARM pack + unpack + MAGIC byte-paritet",
	      omega_spi_frame_pack(&in, wire) == OMEGA_PARSE_OK &&
	      wire[0] == 0x41u && wire[1] == 0x47u && wire[2] == 0x4Du && wire[3] == 0x4Fu &&
	      omega_spi_frame_unpack(wire, &out, &req_mac) == OMEGA_PARSE_OK &&
	      out.cmd == OMEGA_CMD_ARM &&
	      out.win == 25u &&
	      out.q_xyz[2] == 0x11111111u &&
	      req_mac);

	/* S03: 1-bit feil paa SPI-linjen fanges av CRC32C */
	wire[27] ^= 0x01u;
	check("S03 1-bit SPI-stoev avvises av CRC32C",
	      omega_spi_frame_unpack(wire, &out, &req_mac) == OMEGA_PARSE_ERR_CRC);

	/* S04: Ikke-kanonisk OPEN (Q_XYZ != 0) avvises */
	memset(&in, 0, sizeof(in));
	in.cmd      = OMEGA_CMD_OPEN;
	in.win      = 5u;
	in.seq      = 2u;
	in.epoch    = 1u;
	in.evidence = 0xABCDu;
	in.q_xyz[0] = 1u; /* Ulovlig i OPEN */
	check("S04 Ikke-kanonisk OPEN (Q != 0) forkastet",
	      omega_spi_frame_pack(&in, wire) == OMEGA_PARSE_ERR_NONCANON_Q);

	/* S05: OPEN uten evidens (EVIDENCE == 0) avvises */
	in.q_xyz[0] = 0u;
	in.evidence = 0u;
	check("S05 OPEN uten evidens (EVIDENCE == 0) forkastet",
	      omega_spi_frame_pack(&in, wire) == OMEGA_PARSE_ERR_NO_EVIDENCE);

	/* S06: Gyldig kanonisk OPEN passerer og krever MAC */
	in.evidence = 0xABCDu;
	req_mac = false;
	check("S06 Gyldig kanonisk OPEN passerer og krever MAC",
	      omega_spi_frame_pack(&in, wire) == OMEGA_PARSE_OK &&
	      omega_spi_frame_unpack(wire, &out, &req_mac) == OMEGA_PARSE_OK &&
	      out.cmd == OMEGA_CMD_OPEN &&
	      out.evidence == 0xABCDu &&
	      req_mac);

	/* S07: Buss-KILL (CMD_KILL) krever alltid MAC (ikke uautentisert noedstopp) */
	memset(&in, 0, sizeof(in));
	in.cmd   = OMEGA_CMD_KILL;
	in.seq   = 9u;
	in.epoch = 1u;
	req_mac  = false;
	check("S07 Buss-KILL krever MAC-verifikasjon foer ST_KILL",
	      omega_spi_frame_pack(&in, wire) == OMEGA_PARSE_OK &&
	      omega_spi_frame_unpack(wire, &out, &req_mac) == OMEGA_PARSE_OK &&
	      out.cmd == OMEGA_CMD_KILL &&
	      req_mac);

	/* S08: 16-byte FPGA-statussvar round-trip + CRC-vakt */
	memset(&st_in, 0, sizeof(st_in));
	st_in.fpga_state   = OMEGA_FPGA_ST_HOLD;
	st_in.fault_flags  = OMEGA_FLT_MAC;
	st_in.w_ext_live   = 1u;
	st_in.active_epoch = 2u;
	st_in.last_seq     = 42u;
	bool st_ok = (omega_fpga_status_pack(&st_in, st_wire) == OMEGA_PARSE_OK &&
		      omega_fpga_status_unpack(st_wire, &st_out) == OMEGA_PARSE_OK &&
		      st_out.fpga_state == OMEGA_FPGA_ST_HOLD &&
		      st_out.fault_flags == OMEGA_FLT_MAC &&
		      st_out.last_seq == 42u);
	st_wire[5] ^= 0x80u;
	bool st_err = (omega_fpga_status_unpack(st_wire, &st_out) == OMEGA_PARSE_ERR_CRC);
	check("S08 16-byte FPGA-statussvar round-trip + CRC-feildeteksjon", st_ok && st_err);

	printf("SPI-HAL RESULTAT: %d PASS / %d FAIL\n", pass_cnt, fail_cnt);
	return fail_cnt == 0 ? 0 : 1;
}
