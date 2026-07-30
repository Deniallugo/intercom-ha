// ===== puck shell: top face + four walls (no top-level geometry) =====
// Open at the base (+z). The top face carries the button, the switch seat, the mic
// port and the DAC standoffs; the rear (-y) wall carries the devkit USB-C window and
// the 3.5 mm jack. The devkit itself is on the base plate, underneath all of this.

// ---- top face: button ------------------------------------------------------
// Three concentric cuts in the top wall: a shallow recess the cap face sits in, the
// bore its skirt rides in, and a halo groove outboard of both so the button can be
// found by touch. The halo ID stays outside the recess so it never thins the land
// the cap's lip catches on.
module button_cut() {
    translate(btn_pos) {
        translate([0, 0, -0.1]) cylinder(h = wall + 0.2, d = btn_well_d);
        translate([0, 0, -0.1]) cylinder(h = btn_recess_depth + 0.1, d = btn_recess_d);
        translate([0, 0, -0.1]) difference() {
            cylinder(h = btn_halo_depth + 0.1, d = btn_halo_od);
            translate([0, 0, -0.1]) cylinder(h = btn_halo_depth + 0.3, d = btn_halo_id);
        }
    }
}

// Seat for the 6x6 tactile switch, standing off the top wall's inner face directly
// under the bore. The switch is pushed in from the cavity side, plunger first, until
// its body top lands on the ledge; a dab of glue retains it. The legs leave through
// slots in the +-x walls. The block's diagonal stays inside the bore's shadow, so it
// never fouls the annular land that the cap's lip lands on.
module switch_seat() {
    translate([btn_pos[0], btn_pos[1], wall]) difference() {
        translate([0, 0, sw_seat_h()/2])
            cube([sw_seat_od(), sw_seat_od(), sw_seat_h()], center = true);
        // switch body pocket, open toward the cavity
        translate([0, 0, sw_gap + sw_plunger_h + (sw_body_h + 0.2)/2])
            cube([sw_body + 2*clr, sw_body + 2*clr, sw_body_h + 0.2], center = true);
        // plunger bore up to the top wall — also the channel the cap's post runs in
        translate([0, 0, -0.1])
            cylinder(h = sw_gap + sw_plunger_h + 0.2, d = sw_plunger_d + 2*clr);
        // leg slots out both +-x walls
        for (sx = [-1, 1])
            translate([sx*sw_seat_od()/2, 0, sw_gap + sw_plunger_h + sw_body_h - sw_leg_slot_h/2])
                cube([sw_seat_wall*3, sw_leg_slot_w, sw_leg_slot_h], center = true);
    }
}

// ---- top face: microphone --------------------------------------------------
// Board recess, gasket seat, one short port. Pressing the INMP441's port onto the
// gasket leaves near-zero front volume, which puts the port resonance well above
// speech instead of in the middle of it.
module mic_seat() {
    translate([mic_pos[0], mic_pos[1], 0]) {
        translate([0, 0, wall - mic_seat_depth])
            linear_extrude(mic_seat_depth + 0.1)
                square([mic_board_w + 2*clr, mic_board_l + 2*clr], center = true);
        translate([0, 0, wall - mic_seat_depth - mic_gasket_depth])
            cylinder(h = mic_gasket_depth + 0.01, d = mic_gasket_d);
        translate([0, 0, -0.1])
            cylinder(h = wall - mic_seat_depth - mic_gasket_depth + 0.2, d = mic_hole_d);
    }
}

// two M2 posts flanking the mic seat, on full-thickness wall (never over the thinned
// gasket zone): screwing the board down is what compresses the gasket
module mic_posts() {
    for (sx = [-1, 1])
        translate([mic_pos[0] + sx*mic_post_pitch/2, mic_pos[1], wall])
            screw_boss(mic_post_h, mic_post_od, board_screw_pilot);
}

// ---- top face: DAC ---------------------------------------------------------
// The PCM5102A hangs off the top face on standoffs, in the +x strip beside the
// devkit column rather than above it — the analog leads then run straight down the
// side wall to the jack instead of across the digital board.
module dac_mounts() {
    translate([dac_pos[0], dac_pos[1], wall])
        board_standoffs(dac_w, dac_l, board_standoff_h, board_standoff_od, board_screw_pilot);
}

// ---- rear wall -------------------------------------------------------------
// Window over the devkit's own two USB-C ports: power, first flash and serial log all
// come through here, which is why there is no separate panel-mount USB socket. It is
// a BOUNDED hole — material is left below it so the rim that meets the base plate
// stays continuous.
module usb_window() {
    translate([s3_pos[0], -outer_h()/2, s3_usb_cz()])
        cube([s3_usb_w, wall*3, s3_usb_h], center = true);
}

// 3.5 mm panel-mount jack, LROUT/RROUT from the PCM5102. Line level — it feeds a
// powered speaker or an amp, never a driver directly.
module jack_bore() {
    translate([jack_pos[0], -outer_h()/2 - 0.1, jack_pos[1]]) rotate([-90, 0, 0])
        cylinder(h = wall + 0.2, d = jack_bore_d);
}

// ---- corners ---------------------------------------------------------------
// Full-depth pillars from the top face to the base plate rim, each taking an M3
// heat-set insert. Being full-depth is what makes them obstacles on every plane in
// the box, which is why the board layout is stacked rather than spread.
module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*boss_c(), sy*boss_c(), wall])
            screw_boss(cavity_depth, boss_od, insert_m3_d);
}

module shell() {
    difference() {
        union() {
            shell_body(top_depth());
            corner_bosses();
            switch_seat();
            mic_posts();
            dac_mounts();
        }
        button_cut();
        mic_seat();
        usb_window();
        jack_bore();
    }
}
