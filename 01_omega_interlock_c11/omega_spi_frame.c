#include "omega_spi_frame.h"

static void put_le16(uint8_t *p, uint16_t v)
{
	p[0] = (uint8_t)(v & 0xFFu);
	p[1] = (uint8_t)((v >> 8) & 0xFFu);
}

static void put_le32(uint8_t *p, uint32_t v)
{
	p[0] = (uint8_t)(v & 0xFFu);
	p[1] = (uint8_t)((v >> 8) & 0xFFu);
	p[2] = (uint8_t)((v >> 16) & 0xFFu);
	p[3] = (uint8_t)((v >> 24) & 0xFFu);
}

static void put_le64(uint8_t *p, uint64_t v)
{
	put_le32(p, (uint32_t)(v & 0xFFFFFFFFu));
	put_le32(p + 4, (uint32_t)((v >> 32) & 0xFFFFFFFFu));
}

static uint16_t get_le16(const uint8_t *p)
{
	return (uint16_t)(((uint16_t)p[0]) | ((uint16_t)p[1] << 8));
}

static uint32_t get_le32(const uint8_t *p)
{
	return ((uint32_t)p[0]) |
	       ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) |
	       ((uint32_t)p[3] << 24);
}

static uint64_t get_le64(const uint8_t *p)
{
	return ((uint64_t)get_le32(p)) | ((uint64_t)get_le32(p + 4) << 32);
}

uint32_t omega_crc32c(const uint8_t *data, size_t len)
{
	uint32_t crc = 0xFFFFFFFFu;
	size_t i;
	int b;

	for (i = 0u; i < len; i++) {
		crc ^= (uint32_t)data[i];
		for (b = 0; b < 8; b++) {
			uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
			crc = (crc >> 1) ^ (0x82F63B78u & mask);
		}
	}
	return ~crc;
}

static omega_parse_rc_t validate_cmd_and_payload(const omega_spi_frame_t *f)
{
	if (f->cmd != OMEGA_CMD_ARM &&
	    f->cmd != OMEGA_CMD_OPEN &&
	    f->cmd != OMEGA_CMD_KILL) {
		return OMEGA_PARSE_ERR_CMD;
	}

	if (f->cmd == OMEGA_CMD_OPEN) {
		/* Kanonisk OPEN: Q_XYZ maa vaere eksakt 0 og EVIDENCE maa vaere != 0 */
		if (f->q_xyz[0] != 0u || f->q_xyz[1] != 0u || f->q_xyz[2] != 0u)
			return OMEGA_PARSE_ERR_NONCANON_Q;
		if (f->evidence == 0u)
			return OMEGA_PARSE_ERR_NO_EVIDENCE;
	}

	return OMEGA_PARSE_OK;
}

omega_parse_rc_t omega_spi_frame_pack(const omega_spi_frame_t *in,
				      uint8_t wire[OMEGA_SPI_FRAME_BYTES])
{
	omega_parse_rc_t rc;
	size_t i;
	uint32_t crc;

	if (!in || !wire)
		return OMEGA_PARSE_ERR_NULL;

	rc = validate_cmd_and_payload(in);
	if (rc != OMEGA_PARSE_OK)
		return rc;

	put_le32(wire + 0,  OMEGA_FRAME_MAGIC);
	put_le16(wire + 4,  in->cmd);
	put_le16(wire + 6,  in->win);
	put_le32(wire + 8,  in->seq);
	put_le32(wire + 12, in->epoch);
	put_le32(wire + 16, in->ref_seq);
	put_le32(wire + 20, in->ref_epoch);
	put_le64(wire + 24, in->evidence);
	put_le32(wire + 32, in->q_xyz[0]);
	put_le32(wire + 36, in->q_xyz[1]);
	put_le32(wire + 40, in->q_xyz[2]);

	for (i = 0u; i < 16u; i++)
		wire[44u + i] = in->auth_tag[i];

	crc = omega_crc32c(wire, 60u);
	put_le32(wire + 60, crc);
	return OMEGA_PARSE_OK;
}

omega_parse_rc_t omega_spi_frame_unpack(const uint8_t wire[OMEGA_SPI_FRAME_BYTES],
					omega_spi_frame_t *out,
					bool *requires_mac_auth)
{
	uint32_t calc_crc;
	size_t i;
	omega_parse_rc_t rc;

	if (!wire || !out)
		return OMEGA_PARSE_ERR_NULL;

	out->magic     = get_le32(wire + 0);
	out->cmd       = get_le16(wire + 4);
	out->win       = get_le16(wire + 6);
	out->seq       = get_le32(wire + 8);
	out->epoch     = get_le32(wire + 12);
	out->ref_seq   = get_le32(wire + 16);
	out->ref_epoch = get_le32(wire + 20);
	out->evidence  = get_le64(wire + 24);
	out->q_xyz[0]  = get_le32(wire + 32);
	out->q_xyz[1]  = get_le32(wire + 36);
	out->q_xyz[2]  = get_le32(wire + 40);

	for (i = 0u; i < 16u; i++)
		out->auth_tag[i] = wire[44u + i];

	out->crc32c = get_le32(wire + 60);

	if (out->magic != OMEGA_FRAME_MAGIC)
		return OMEGA_PARSE_ERR_MAGIC;

	calc_crc = omega_crc32c(wire, 60u);
	if (calc_crc != out->crc32c)
		return OMEGA_PARSE_ERR_CRC;

	rc = validate_cmd_and_payload(out);
	if (rc != OMEGA_PARSE_OK)
		return rc;

	/* Alle buss-kommandoer (inkl. OMEGA_CMD_KILL) krever MAC foer virkning */
	if (requires_mac_auth)
		*requires_mac_auth = true;

	return OMEGA_PARSE_OK;
}

omega_parse_rc_t omega_fpga_status_pack(const omega_fpga_status_t *in,
					uint8_t wire[OMEGA_SPI_STATUS_BYTES])
{
	uint32_t crc;

	if (!in || !wire)
		return OMEGA_PARSE_ERR_NULL;

	wire[0] = in->fpga_state;
	wire[1] = in->fault_flags;
	wire[2] = in->w_ext_live ? 1u : 0u;
	wire[3] = 0u;
	put_le32(wire + 4, in->active_epoch);
	put_le32(wire + 8, in->last_seq);

	crc = omega_crc32c(wire, 12u);
	put_le32(wire + 12, crc);
	return OMEGA_PARSE_OK;
}

omega_parse_rc_t omega_fpga_status_unpack(const uint8_t wire[OMEGA_SPI_STATUS_BYTES],
					  omega_fpga_status_t *out)
{
	uint32_t calc_crc;

	if (!wire || !out)
		return OMEGA_PARSE_ERR_NULL;

	out->fpga_state   = wire[0];
	out->fault_flags  = wire[1];
	out->w_ext_live   = wire[2];
	out->reserved     = wire[3];
	out->active_epoch = get_le32(wire + 4);
	out->last_seq     = get_le32(wire + 8);
	out->crc32c       = get_le32(wire + 12);

	calc_crc = omega_crc32c(wire, 12u);
	if (calc_crc != out->crc32c)
		return OMEGA_PARSE_ERR_CRC;

	return OMEGA_PARSE_OK;
}
