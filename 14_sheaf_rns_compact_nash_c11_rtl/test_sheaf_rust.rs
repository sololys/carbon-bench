extern crate sheaf_curry_howard;

use sheaf_curry_howard::{
    sheaf_sluice_step, SheafSluiceInput, SheafSluiceState,
    SHEAF_PORT_HOLD, SHEAF_PORT_KILL, SHEAF_PORT_OPEN,
};

fn make_nominal_uniform() -> SheafSluiceInput {
    let center_q = [100_i16, 200_i16, -300_i16];
    let mut nb_q = [[0_i16; 3]; 6];
    for f in 0..6 {
        let ax = f / 2;
        let step: i16 = if (f % 2) == 0 { -50 } else { 50 };
        nb_q[f] = center_q;
        nb_q[f][ax] += step;
    }
    SheafSluiceInput {
        l01_reset_strobe: false,
        l01_witness_ok: false,
        selftest_ok: true,
        eval_strobe: true,
        witness_ext: true,
        center_q,
        nb_q,
        lattice_pitch: 50,
        max_jitter: 5,
        center_flux: [-25, 25, 40, -40, -10, 10],
        nb_opp_flux: [25, -25, -40, 40, 10, -10],
        cell_source_q: 0,
        plaq_edges: [
            [12, 8, -12, -8],
            [-5, 19, 5, -19],
            [30, -11, -20, 1],
        ],
        center_rail_true: 0xCAFE_BABE,
        center_rail_comp: 0x3501_4541,
        nb_rail_true_mask: 0x2A,
        nb_rail_comp_mask: 0x15,
    }
}

fn make_l01_rst(w_ok: bool, st_ok: bool) -> SheafSluiceInput {
    let mut inp = make_nominal_uniform();
    inp.l01_reset_strobe = true;
    inp.l01_witness_ok = w_ok;
    inp.selftest_ok = st_ok;
    inp.eval_strobe = false;
    inp
}

fn step_print_check(
    sid: usize,
    st: &mut SheafSluiceState,
    inp: &SheafSluiceInput,
    exp_port: u8,
    exp_fault: u8,
    exp_kill: bool,
) {
    let witness = sheaf_sluice_step(st, inp);
    assert_eq!(witness.is_some(), st.port_out == SHEAF_PORT_OPEN);
    if let Some(w) = witness {
        assert_eq!(w.rail_true() ^ w.rail_comp(), 0xFFFF_FFFF);
        assert_eq!(w.cycle(), st.cycle_counter);
    }
    println!(
        "S{:02} port={} fault={:02x} kill={} mon={} act={} rail={:08x} comp={:08x} epoch={} cyc={}",
        sid,
        st.port_out,
        st.fault_mask,
        if st.kill_latched { 1 } else { 0 },
        if st.monitor_coupled { 1 } else { 0 },
        if st.actuator_v_en { 1 } else { 0 },
        st.out_rail_true,
        st.out_rail_comp,
        st.reset_epoch,
        st.cycle_counter
    );
    assert_eq!(st.port_out, exp_port);
    assert_eq!(st.fault_mask, exp_fault);
    assert_eq!(st.kill_latched, exp_kill);
}

fn main() {
    let mut st = SheafSluiceState::new();

    let mut inp = make_nominal_uniform();
    inp.witness_ext = false;
    step_print_check(1, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    step_print_check(2, &mut st, &inp, SHEAF_PORT_OPEN, 0x00, false);

    inp = make_nominal_uniform();
    inp.center_flux = [5; 6];
    inp.nb_opp_flux = [-5; 6];
    inp.cell_source_q = 30;
    step_print_check(3, &mut st, &inp, SHEAF_PORT_OPEN, 0x00, false);

    inp = make_nominal_uniform();
    inp.eval_strobe = false;
    step_print_check(4, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    inp.nb_opp_flux[5] = -9;
    step_print_check(5, &mut st, &inp, SHEAF_PORT_KILL, 0x02, true);

    inp = make_nominal_uniform();
    step_print_check(6, &mut st, &inp, SHEAF_PORT_KILL, 0x02, true);

    inp = make_l01_rst(false, true);
    step_print_check(7, &mut st, &inp, SHEAF_PORT_KILL, 0x02, true);

    inp = make_l01_rst(true, true);
    step_print_check(8, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    inp.nb_q[1][1] = 206;
    step_print_check(9, &mut st, &inp, SHEAF_PORT_KILL, 0x08, true);

    inp = make_l01_rst(true, true);
    step_print_check(10, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    inp.plaq_edges[0][3] = -7;
    step_print_check(11, &mut st, &inp, SHEAF_PORT_KILL, 0x10, true);

    inp = make_l01_rst(true, true);
    step_print_check(12, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    inp.cell_source_q = 1;
    step_print_check(13, &mut st, &inp, SHEAF_PORT_KILL, 0x04, true);

    inp = make_l01_rst(true, true);
    step_print_check(14, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);

    inp = make_nominal_uniform();
    inp.center_rail_comp ^= 1;
    inp.lattice_pitch = 0;
    step_print_check(15, &mut st, &inp, SHEAF_PORT_KILL, 0x21, true);

    inp = make_l01_rst(true, true);
    step_print_check(16, &mut st, &inp, SHEAF_PORT_HOLD, 0x00, false);
}
