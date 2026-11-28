#![no_std]
#![forbid(unsafe_code)]

//! `#![no_std]` Curry-Howard 3D Skeletal Sheaf Sluice
//!
//! `SheafWitness` has private fields and can ONLY be constructed inside
//! `sheaf_sluice_step` when all 6 face fiber-products, interior divergence,
//! full 3D metric tolerances, and 3 square plaquette holonomy loops vanish
//! AND `witness_ext` is asserted without sticky `KILL`.

pub const SHEAF_PORT_HOLD: u8 = 1;
pub const SHEAF_PORT_OPEN: u8 = 2;
pub const SHEAF_PORT_KILL: u8 = 3;

pub const SHEAF_FAULT_DUAL_RAIL: u8     = 1 << 0;
pub const SHEAF_FAULT_FACE_FLUX: u8     = 1 << 1;
pub const SHEAF_FAULT_DIV_BUBBLE: u8    = 1 << 2;
pub const SHEAF_FAULT_GEOM_TEAR: u8     = 1 << 3;
pub const SHEAF_FAULT_HOLONOMY_SEAM: u8 = 1 << 4;
pub const SHEAF_FAULT_PARAM_BOUNDS: u8  = 1 << 5;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SheafWitness {
    rail_true: u32,
    rail_comp: u32,
    cycle: u64,
}

impl SheafWitness {
    pub const fn rail_true(&self) -> u32 {
        self.rail_true
    }
    pub const fn rail_comp(&self) -> u32 {
        self.rail_comp
    }
    pub const fn cycle(&self) -> u64 {
        self.cycle
    }
}

#[derive(Clone, Copy, Debug)]
pub struct SheafSluiceInput {
    pub l01_reset_strobe: bool,
    pub l01_witness_ok: bool,
    pub selftest_ok: bool,
    pub eval_strobe: bool,
    pub witness_ext: bool,

    pub center_q: [i16; 3],
    pub nb_q: [[i16; 3]; 6],
    pub lattice_pitch: i16,
    pub max_jitter: i16,

    pub center_flux: [i16; 6],
    pub nb_opp_flux: [i16; 6],
    pub cell_source_q: i16,

    pub plaq_edges: [[i16; 4]; 3],

    pub center_rail_true: u32,
    pub center_rail_comp: u32,
    pub nb_rail_true_mask: u8,
    pub nb_rail_comp_mask: u8,
}

#[derive(Clone, Copy, Debug)]
pub struct SheafSluiceState {
    pub port_out: u8,
    pub fault_mask: u8,
    pub kill_latched: bool,
    pub monitor_coupled: bool,
    pub actuator_v_en: bool,
    pub out_rail_true: u32,
    pub out_rail_comp: u32,
    pub reset_epoch: u32,
    pub cycle_counter: u64,
}

impl SheafSluiceState {
    pub const fn new() -> Self {
        Self {
            port_out: SHEAF_PORT_HOLD,
            fault_mask: 0,
            kill_latched: false,
            monitor_coupled: true,
            actuator_v_en: false,
            out_rail_true: 0,
            out_rail_comp: 0,
            reset_epoch: 0,
            cycle_counter: 0,
        }
    }
}

pub fn sheaf_eval_comb_faults(inp: &SheafSluiceInput) -> u8 {
    let mut faults: u8 = 0;

    let c_rail_ok = (inp.center_rail_true ^ inp.center_rail_comp) == 0xFFFF_FFFF;
    let nb_xor = (inp.nb_rail_true_mask ^ inp.nb_rail_comp_mask) & 0x3F;
    if !c_rail_ok || nb_xor != 0x3F {
        faults |= SHEAF_FAULT_DUAL_RAIL;
    }

    let mut param_bad = inp.lattice_pitch <= 0 || inp.max_jitter < 0;
    let mut a = 0;
    while a < 3 {
        if inp.center_q[a] == i16::MIN {
            param_bad = true;
        }
        a += 1;
    }
    let mut f = 0;
    while f < 6 {
        let mut ax = 0;
        while ax < 3 {
            if inp.nb_q[f][ax] == i16::MIN {
                param_bad = true;
            }
            ax += 1;
        }
        f += 1;
    }
    if param_bad {
        faults |= SHEAF_FAULT_PARAM_BOUNDS;
    }

    let mut div_sum: i32 = 0;
    f = 0;
    while f < 6 {
        let cf = inp.center_flux[f] as i32;
        let nf = inp.nb_opp_flux[f] as i32;
        if cf + nf != 0 {
            faults |= SHEAF_FAULT_FACE_FLUX;
        }
        div_sum += cf;
        f += 1;
    }
    if div_sum != (inp.cell_source_q as i32) {
        faults |= SHEAF_FAULT_DIV_BUBBLE;
    }

    if !param_bad {
        let pitch = inp.lattice_pitch as i32;
        let jit = inp.max_jitter as i32;
        f = 0;
        while f < 6 {
            let normal_axis = f / 2;
            let step = if (f % 2) == 0 { -pitch } else { pitch };
            let mut ax = 0;
            while ax < 3 {
                let exp_q = (inp.center_q[ax] as i32) + if ax == normal_axis { step } else { 0 };
                let diff = (inp.nb_q[f][ax] as i32) - exp_q;
                let adiff = if diff < 0 { -diff } else { diff };
                if adiff > jit {
                    faults |= SHEAF_FAULT_GEOM_TEAR;
                }
                ax += 1;
            }
            f += 1;
        }
    }

    let mut p = 0;
    while p < 3 {
        let loop_sum = (inp.plaq_edges[p][0] as i32)
            + (inp.plaq_edges[p][1] as i32)
            + (inp.plaq_edges[p][2] as i32)
            + (inp.plaq_edges[p][3] as i32);
        if loop_sum != 0 {
            faults |= SHEAF_FAULT_HOLONOMY_SEAM;
        }
        p += 1;
    }

    faults
}

pub fn sheaf_sluice_step(
    st: &mut SheafSluiceState,
    inp: &SheafSluiceInput,
) -> Option<SheafWitness> {
    st.cycle_counter = st.cycle_counter.wrapping_add(1);

    if inp.l01_reset_strobe {
        if inp.l01_witness_ok && inp.selftest_ok && st.reset_epoch < u32::MAX {
            st.kill_latched = false;
            st.monitor_coupled = true;
            st.actuator_v_en = false;
            st.port_out = SHEAF_PORT_HOLD;
            st.fault_mask = 0;
            st.out_rail_true = 0;
            st.out_rail_comp = 0;
            st.reset_epoch += 1;
        } else {
            st.kill_latched = true;
            st.monitor_coupled = false;
            st.actuator_v_en = false;
            st.port_out = SHEAF_PORT_KILL;
            st.out_rail_true = 0;
            st.out_rail_comp = 0;
        }
        return None;
    }

    if st.kill_latched {
        st.port_out = SHEAF_PORT_KILL;
        st.monitor_coupled = false;
        st.actuator_v_en = false;
        st.out_rail_true = 0;
        st.out_rail_comp = 0;
        return None;
    }

    if !inp.eval_strobe {
        st.port_out = SHEAF_PORT_HOLD;
        st.fault_mask = 0;
        st.monitor_coupled = true;
        st.actuator_v_en = false;
        st.out_rail_true = 0;
        st.out_rail_comp = 0;
        return None;
    }

    let faults = sheaf_eval_comb_faults(inp);
    if faults != 0 {
        st.kill_latched = true;
        st.monitor_coupled = false;
        st.actuator_v_en = false;
        st.port_out = SHEAF_PORT_KILL;
        st.fault_mask = faults;
        st.out_rail_true = 0;
        st.out_rail_comp = 0;
        None
    } else if !inp.witness_ext {
        st.port_out = SHEAF_PORT_HOLD;
        st.fault_mask = 0;
        st.monitor_coupled = true;
        st.actuator_v_en = false;
        st.out_rail_true = 0;
        st.out_rail_comp = 0;
        None
    } else {
        st.port_out = SHEAF_PORT_OPEN;
        st.fault_mask = 0;
        st.monitor_coupled = true;
        st.actuator_v_en = true;
        st.out_rail_true = inp.center_rail_true;
        st.out_rail_comp = inp.center_rail_comp;
        Some(SheafWitness {
            rail_true: inp.center_rail_true,
            rail_comp: inp.center_rail_comp,
            cycle: st.cycle_counter,
        })
    }
}
