extern crate dual_base_witness;

use dual_base_witness::*;

fn m31_add_ref(a: u32, b: u32) -> u32 {
    let s = (a as u64) + (b as u64);
    let mut f = (s & 0x7FFF_FFFF) + (s >> 31);
    if f >= (MERSENNE_P31 as u64) {
        f -= MERSENNE_P31 as u64;
    }
    f as u32
}

fn m31_mul_ref(a: u32, b: u32) -> u32 {
    let m = (a as u64) * (b as u64);
    let m0 = (m & 0x7FFF_FFFF) + (m >> 31);
    let mut m1 = (m0 & 0x7FFF_FFFF) + (m0 >> 31);
    if m1 >= (MERSENNE_P31 as u64) {
        m1 -= MERSENNE_P31 as u64;
    }
    m1 as u32
}

fn nominal() -> CycleInput {
    CycleInput {
        rail_pos: 0x55AA_33CC,
        rail_neg: !0x55AA_33CC,
        q_prev: [3, -2, 0],
        p_prev: [6, 4, 5],
        q_curr: [3, -2, 4],
        p_curr: [3, 3, 4],
        nb_pz_raw: [18, -4, 6, 2, 16, 999],
        nb_interior_mask: 0x1F,
        shift_s: 1,
        hold_mid_qz: 4,
        hold_mid_pz: -5,
        rough_max: 10,
        xi1_q: [12, 12, 12],
        xi1_p: [2, 2, 2],
        xi2_q: [5, 5, 5],
        xi2_p: [11, 11, 11],
        c_min_area: 100,
        kappa_q: 2,
        r_max_sq: 500,
        p_max_sq: 500,
        e_max: 100_000,
        e_fiber_prev: 50,
        delta_e_shed: 11,
        e_fiber_curr: 61,
        poincare_inv_ref: 153,
        sol_q_prev: 40,
        sol_w_prev: 25,
        sol_q_curr: 43,
        sol_w_curr: 27,
        lam_ij: 7,
        tau_ij: 13,
        lam_jk: 11,
        tau_jk: 5,
        lam_ik: 77,
        tau_ik: 48,
        w_ext_valid: false,
        l01_reset_req: false,
        l01_token: 0,
    }
}

fn main() {
    let emit_hex = std::env::args().any(|a| a == "--emit-hex");
    let mut vecs = [nominal(); 20];

    vecs[0].w_ext_valid = false;

    vecs[1].q_prev = [0, 0, 0];
    vecs[1].p_prev = [0, 0, 0];
    vecs[1].q_curr = [0, 0, 0];
    vecs[1].p_curr = [0, 0, 0];
    vecs[1].nb_pz_raw = [0, 0, 0, 0, 0, -777];
    vecs[1].hold_mid_qz = 0;
    vecs[1].hold_mid_pz = 0;
    vecs[1].e_fiber_prev = 153;
    vecs[1].delta_e_shed = 0;
    vecs[1].e_fiber_curr = 153;
    vecs[1].sol_q_curr = 40;
    vecs[1].sol_w_curr = 25;
    vecs[1].w_ext_valid = true;

    vecs[2].w_ext_valid = true;
    vecs[2].lam_ij = 65537;
    vecs[2].tau_ij = 2_147_483_600;
    vecs[2].lam_jk = 65539;
    vecs[2].tau_jk = 123_456_789;
    vecs[2].lam_ik = m31_mul_ref(65537, 65539);
    vecs[2].tau_ik = m31_add_ref(m31_mul_ref(65537, 123_456_789), 2_147_483_600);

    vecs[3].w_ext_valid = true;
    vecs[3].rail_neg ^= 1;

    vecs[4].w_ext_valid = true;

    vecs[5].w_ext_valid = true;
    vecs[5].l01_reset_req = true;
    vecs[5].l01_token = 0xDEAD_BEEF;

    vecs[6].w_ext_valid = true;
    vecs[6].l01_reset_req = true;
    vecs[6].l01_token = L01_RESET_TOKEN;

    vecs[7].w_ext_valid = true;
    vecs[7].hold_mid_qz = 503;
    vecs[7].rough_max = 1000;

    vecs[8].l01_reset_req = true;
    vecs[8].l01_token = L01_RESET_TOKEN;

    vecs[9].nb_pz_raw[0] = 46;
    vecs[9].hold_mid_qz = 18;
    vecs[9].w_ext_valid = true;

    vecs[10].w_ext_valid = true;
    vecs[10].l01_reset_req = true;
    vecs[10].l01_token = L01_RESET_TOKEN;

    vecs[11].w_ext_valid = true;
    vecs[11].delta_e_shed = 10;
    vecs[11].e_fiber_curr = 60;

    vecs[12].l01_reset_req = true;
    vecs[12].l01_token = L01_RESET_TOKEN;

    vecs[13].w_ext_valid = true;
    vecs[13].poincare_inv_ref = 154;

    vecs[14].l01_reset_req = true;
    vecs[14].l01_token = L01_RESET_TOKEN;

    vecs[15].w_ext_valid = true;
    vecs[15].xi1_q[1] = 6;
    vecs[15].xi1_p[1] = 3;
    vecs[15].xi2_q[1] = 12;
    vecs[15].xi2_p[1] = 6;

    vecs[16].l01_reset_req = true;
    vecs[16].l01_token = L01_RESET_TOKEN;

    vecs[17].w_ext_valid = true;
    vecs[17].sol_q_curr = 38;
    vecs[17].sol_w_curr = 28;

    vecs[18].w_ext_valid = true;
    vecs[18].l01_reset_req = true;
    vecs[18].l01_token = L01_RESET_TOKEN;
    vecs[18].sol_q_curr = 40;
    vecs[18].sol_w_curr = 27;

    vecs[19].w_ext_valid = true;
    vecs[19].l01_reset_req = true;
    vecs[19].l01_token = L01_RESET_TOKEN;
    vecs[19].tau_ik += 1;

    let mut st = GateState::new();
    for (i, v) in vecs.iter().enumerate() {
        let (out, wit) = step_and_bind(&mut st, v);
        assert_eq!(wit.is_some(), out.port_out == PORT_OPEN);
        if let Some(w) = wit {
            assert_eq!(w.step_id(), out.step_counter);
            assert_eq!(w.verified_q_curr(), v.q_curr);
        }
        if emit_hex {
            println!(
                "V{:02} port={} open={} mon={} kill={} sig={} fault=0x{:03x} step={} cross={}",
                i,
                out.port_out,
                out.actuator_open as u8,
                out.monitor_coupled as u8,
                out.kill_latched as u8,
                out.sigma_crossed as u8,
                out.fault_mask,
                out.step_counter,
                out.sigma_crossings
            );
        }
    }
    assert_eq!(st.sigma_crossings, 8);
    if !emit_hex {
        println!("[PASS] #![no_std] Rust DualBaseWitness: 20/20 vectors OK.");
    }
}
