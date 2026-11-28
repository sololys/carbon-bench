//! `#![no_std]` Curry-Howard Witness Binding for Dual-Base (B1 x B2) Cycle Gate.
//! Forbids `unsafe` and IEEE-754 floating-point; `DualBaseWitness` can ONLY be constructed
//! inside this module when `fault_mask == 0`, `!kill_latched`, and `w_ext_valid == true`.

#![no_std]
#![forbid(unsafe_code)]

pub const PORT_WIRE_FAULT: u8 = 0;
pub const PORT_HOLD: u8 = 1;
pub const PORT_OPEN: u8 = 2;
pub const PORT_KILL: u8 = 3;

pub const L01_RESET_TOKEN: u32 = 0xA55A_C33C;
pub const MERSENNE_P31: u32 = 0x7FFF_FFFF;
pub const INT16_POISON: i16 = i16::MIN;

pub const FAULT_DUAL_RAIL: u16 = 1 << 0;
pub const FAULT_SENSOR_MIN: u16 = 1 << 1;
pub const FAULT_HOLD_INV: u16 = 1 << 2;
pub const FAULT_ROUGHNESS: u16 = 1 << 3;
pub const FAULT_VIABILITY: u16 = 1 << 4;
pub const FAULT_NOETHER_LED: u16 = 1 << 5;
pub const FAULT_POINCARE_REF: u16 = 1 << 6;
pub const FAULT_GROMOV_AREA: u16 = 1 << 7;
pub const FAULT_VK_COLLAPSE: u16 = 1 << 8;
pub const FAULT_RNS_COCYCLE: u16 = 1 << 9;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CycleInput {
    pub rail_pos: u32,
    pub rail_neg: u32,
    pub q_prev: [i16; 3],
    pub p_prev: [i16; 3],
    pub q_curr: [i16; 3],
    pub p_curr: [i16; 3],
    pub nb_pz_raw: [i16; 6],
    pub nb_interior_mask: u8,
    pub shift_s: u8,
    pub hold_mid_qz: i16,
    pub hold_mid_pz: i16,
    pub rough_max: u16,
    pub xi1_q: [i16; 3],
    pub xi1_p: [i16; 3],
    pub xi2_q: [i16; 3],
    pub xi2_p: [i16; 3],
    pub c_min_area: u32,
    pub kappa_q: u8,
    pub r_max_sq: u32,
    pub p_max_sq: u32,
    pub e_max: i64,
    pub e_fiber_prev: i64,
    pub delta_e_shed: i64,
    pub e_fiber_curr: i64,
    pub poincare_inv_ref: i64,
    pub sol_q_prev: i16,
    pub sol_w_prev: i16,
    pub sol_q_curr: i16,
    pub sol_w_curr: i16,
    pub lam_ij: u32,
    pub tau_ij: u32,
    pub lam_jk: u32,
    pub tau_jk: u32,
    pub lam_ik: u32,
    pub tau_ik: u32,
    pub w_ext_valid: bool,
    pub l01_reset_req: bool,
    pub l01_token: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GateState {
    pub kill_latched: bool,
    pub step_counter: u32,
    pub sigma_crossings: u32,
}

impl GateState {
    pub const fn new() -> Self {
        Self {
            kill_latched: false,
            step_counter: 0,
            sigma_crossings: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CycleOutput {
    pub port_out: u8,
    pub actuator_open: bool,
    pub monitor_coupled: bool,
    pub kill_latched: bool,
    pub sigma_crossed: bool,
    pub fault_mask: u16,
    pub step_counter: u32,
    pub sigma_crossings: u32,
}

/// Sealed intuitionistic proof token: private field `_seal` prevents external forgery.
#[derive(Debug, PartialEq, Eq)]
pub struct DualBaseWitness<'a> {
    input_ref: &'a CycleInput,
    step_id: u32,
    _seal: (),
}

impl<'a> DualBaseWitness<'a> {
    pub fn verified_q_curr(&self) -> [i16; 3] {
        self.input_ref.q_curr
    }
    pub fn step_id(&self) -> u32 {
        self.step_id
    }
}

#[inline]
fn abs_i32(v: i32) -> u32 {
    if v < 0 {
        (-(v as i64)) as u32
    } else {
        v as u32
    }
}

#[inline]
fn m31_add(a: u32, b: u32) -> u32 {
    let s = (a as u64) + (b as u64);
    let mut f = (s & 0x7FFF_FFFF) + (s >> 31);
    if f >= (MERSENNE_P31 as u64) {
        f -= MERSENNE_P31 as u64;
    }
    f as u32
}

#[inline]
fn m31_mul(a: u32, b: u32) -> u32 {
    let m = (a as u64) * (b as u64);
    let m0 = (m & 0x7FFF_FFFF) + (m >> 31);
    let mut m1 = (m0 & 0x7FFF_FFFF) + (m0 >> 31);
    if m1 >= (MERSENNE_P31 as u64) {
        m1 -= MERSENNE_P31 as u64;
    }
    m1 as u32
}

#[inline]
fn norm3_sq(v: [i16; 3]) -> u32 {
    let x = v[0] as i32;
    let y = v[1] as i32;
    let z = v[2] as i32;
    ((x * x) as u32) + ((y * y) as u32) + ((z * z) as u32)
}

pub fn eval_faults(inp: &CycleInput) -> (u16, bool) {
    let mut faults: u16 = 0;

    if (inp.rail_pos ^ inp.rail_neg) != 0xFFFF_FFFF {
        faults |= FAULT_DUAL_RAIL;
    }

    let mut poison = false;
    let mut a = 0;
    while a < 3 {
        if inp.q_prev[a] == INT16_POISON
            || inp.p_prev[a] == INT16_POISON
            || inp.q_curr[a] == INT16_POISON
            || inp.p_curr[a] == INT16_POISON
            || inp.xi1_q[a] == INT16_POISON
            || inp.xi1_p[a] == INT16_POISON
            || inp.xi2_q[a] == INT16_POISON
            || inp.xi2_p[a] == INT16_POISON
        {
            poison = true;
        }
        a += 1;
    }
    let mut d = 0;
    while d < 6 {
        if inp.nb_pz_raw[d] == INT16_POISON {
            poison = true;
        }
        d += 1;
    }
    if inp.hold_mid_qz == INT16_POISON
        || inp.hold_mid_pz == INT16_POISON
        || inp.sol_q_prev == INT16_POISON
        || inp.sol_w_prev == INT16_POISON
        || inp.sol_q_curr == INT16_POISON
        || inp.sol_w_curr == INT16_POISON
    {
        poison = true;
    }
    if poison {
        faults |= FAULT_SENSOR_MIN;
    }

    if inp.shift_s > 15 {
        faults |= FAULT_HOLD_INV;
    } else {
        let mut lap_mid: i32 = -6 * (inp.hold_mid_pz as i32);
        let mut idx = 0;
        while idx < 6 {
            if ((inp.nb_interior_mask >> idx) & 1) != 0 {
                lap_mid += -(inp.nb_pz_raw[idx] as i32);
            }
            idx += 1;
        }
        let mag = abs_i32(lap_mid);
        let dq_back: i32 = if lap_mid < 0 {
            -((mag >> inp.shift_s) as i32)
        } else {
            (mag >> inp.shift_s) as i32
        };
        let qz_rec = (inp.hold_mid_qz as i32) + dq_back;
        let pz_rec = -(inp.hold_mid_pz as i32);
        if qz_rec != (inp.q_prev[2] as i32) || pz_rec != (inp.p_prev[2] as i32) {
            faults |= FAULT_HOLD_INV;
        }
    }

    let rough = abs_i32((inp.hold_mid_qz as i32) - (inp.q_prev[2] as i32));
    if rough > (inp.rough_max as u32) {
        faults |= FAULT_ROUGHNESS;
    }

    let q_prev_sq = norm3_sq(inp.q_prev);
    let p_prev_sq = norm3_sq(inp.p_prev);
    let q_curr_sq = norm3_sq(inp.q_curr);
    let p_curr_sq = norm3_sq(inp.p_curr);

    if q_curr_sq > inp.r_max_sq
        || p_curr_sq > inp.p_max_sq
        || inp.e_max < 0
        || inp.e_fiber_prev < 0
        || inp.e_fiber_curr < 0
        || inp.e_fiber_prev > inp.e_max
        || inp.e_fiber_curr > inp.e_max
    {
        faults |= FAULT_VIABILITY;
    }

    let h_prev = (p_prev_sq as i64) + (inp.kappa_q as i64) * (q_prev_sq as i64);
    let h_curr = (p_curr_sq as i64) + (inp.kappa_q as i64) * (q_curr_sq as i64);

    if inp.delta_e_shed < 0 || inp.delta_e_shed > inp.e_max {
        faults |= FAULT_NOETHER_LED;
    } else if inp.e_fiber_prev <= inp.e_max
        && inp.e_fiber_curr <= inp.e_max
        && inp.e_max <= 0x1FFF_FFFF_FFFF_FFFF
    {
        if (inp.e_fiber_curr - inp.e_fiber_prev) != inp.delta_e_shed {
            faults |= FAULT_NOETHER_LED;
        }
        if (h_curr + inp.e_fiber_curr) != (h_prev + inp.e_fiber_prev) {
            faults |= FAULT_NOETHER_LED;
        }
    } else {
        faults |= FAULT_NOETHER_LED;
    }

    let sigma_cross = (inp.q_prev[2] <= 0) && (inp.q_curr[2] > 0) && (inp.p_curr[2] > 0);
    if sigma_cross && (faults & (FAULT_VIABILITY | FAULT_NOETHER_LED)) == 0 {
        if (h_curr + inp.e_fiber_curr) != inp.poincare_inv_ref {
            faults |= FAULT_POINCARE_REF;
        }
    } else if sigma_cross
        && ((h_curr & 0x3FFF_FFFF_FFFF_FFFF) + (inp.e_fiber_curr & 0x3FFF_FFFF_FFFF_FFFF)
            != inp.poincare_inv_ref)
    {
        faults |= FAULT_POINCARE_REF;
    }

    let mut plane = 0;
    while plane < 3 {
        let t1 = (inp.xi1_q[plane] as i32) * (inp.xi2_p[plane] as i32);
        let t2 = (inp.xi1_p[plane] as i32) * (inp.xi2_q[plane] as i32);
        let diff = (t1 as i64) - (t2 as i64);
        let area = if diff < 0 { (-diff) as u64 } else { diff as u64 };
        if area < (inp.c_min_area as u64) {
            faults |= FAULT_GROMOV_AREA;
        }
        plane += 1;
    }

    if inp.sol_q_prev <= 0
        || inp.sol_w_prev <= 0
        || inp.sol_q_curr <= 0
        || inp.sol_w_curr <= 0
    {
        faults |= FAULT_VK_COLLAPSE;
    } else {
        let dq = (inp.sol_q_curr as i64) - (inp.sol_q_prev as i64);
        let dw = (inp.sol_w_curr as i64) - (inp.sol_w_prev as i64);
        let stationary = (dq == 0) && (dw == 0);
        let pos_slope = (dq * dw) > 0;
        if !stationary && !pos_slope {
            faults |= FAULT_VK_COLLAPSE;
        }
    }

    if inp.lam_ij == 0
        || inp.lam_jk == 0
        || inp.lam_ik == 0
        || inp.lam_ij >= MERSENNE_P31
        || inp.tau_ij >= MERSENNE_P31
        || inp.lam_jk >= MERSENNE_P31
        || inp.tau_jk >= MERSENNE_P31
        || inp.lam_ik >= MERSENNE_P31
        || inp.tau_ik >= MERSENNE_P31
    {
        faults |= FAULT_RNS_COCYCLE;
    } else {
        let lhs_lam = m31_mul(inp.lam_ij, inp.lam_jk);
        let lhs_tau = m31_add(m31_mul(inp.lam_ij, inp.tau_jk), inp.tau_ij);
        if lhs_lam != inp.lam_ik || lhs_tau != inp.tau_ik {
            faults |= FAULT_RNS_COCYCLE;
        }
    }

    (faults, sigma_cross)
}

pub fn step_and_bind<'a>(
    st: &mut GateState,
    inp: &'a CycleInput,
) -> (CycleOutput, Option<DualBaseWitness<'a>>) {
    let (faults, sigma_cross) = eval_faults(inp);
    st.step_counter = st.step_counter.wrapping_add(1);

    if st.kill_latched && inp.l01_reset_req && inp.l01_token == L01_RESET_TOKEN && faults == 0 {
        st.kill_latched = false;
    }
    if faults != 0 {
        st.kill_latched = true;
    }

    let sigma_crossed = (!st.kill_latched) && sigma_cross;
    if sigma_crossed {
        st.sigma_crossings = st.sigma_crossings.wrapping_add(1);
    }

    if st.kill_latched {
        (
            CycleOutput {
                port_out: PORT_KILL,
                actuator_open: false,
                monitor_coupled: false,
                kill_latched: true,
                sigma_crossed: false,
                fault_mask: faults,
                step_counter: st.step_counter,
                sigma_crossings: st.sigma_crossings,
            },
            None,
        )
    } else if inp.w_ext_valid {
        (
            CycleOutput {
                port_out: PORT_OPEN,
                actuator_open: true,
                monitor_coupled: true,
                kill_latched: false,
                sigma_crossed,
                fault_mask: 0,
                step_counter: st.step_counter,
                sigma_crossings: st.sigma_crossings,
            },
            Some(DualBaseWitness {
                input_ref: inp,
                step_id: st.step_counter,
                _seal: (),
            }),
        )
    } else {
        (
            CycleOutput {
                port_out: PORT_HOLD,
                actuator_open: false,
                monitor_coupled: true,
                kill_latched: false,
                sigma_crossed,
                fault_mask: 0,
                step_counter: st.step_counter,
                sigma_crossings: st.sigma_crossings,
            },
            None,
        )
    }
}
