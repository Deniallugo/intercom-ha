// ===== puck shell: top face + four walls (no top-level geometry) =====
// Open at the base (+z). The top face carries the button, the switch seat, the mic
// port and the DAC standoffs; the rear (-y) wall carries the devkit USB-C window and
// the 3.5 mm jack. The devkit itself is on the base plate, underneath all of this.

// ---- top face: button ------------------------------------------------------
// All the shell contributes to the button is a plain bore, a shallow recess for the
// flange, and two blind pilots for the holder. Everything mechanical — the switch, the
// catch, the guide's far end — is in `button_holder`, so tuning the mechanism never
// costs a shell reprint.
//
// The bore is not just a hole any more, though: below the recess it is 1.8 mm of the
// journal the Ø32 cap body runs in, and it is the accurate half of it, because the
// holder can only be located to whatever its two M2s allow. That is why it is cut at
// btn_bore_d() — cap body plus btn_guide_clr, not the global `clr`.
module button_cut() {
    translate(btn_pos) {
        translate([0, 0, -0.1]) cylinder(h = wall + 0.2, d = btn_bore_d());
        translate([0, 0, -0.1]) cylinder(h = btn_recess_depth + 0.1, d = btn_recess_d());
    }
}

// Two BLIND M2 pilots in the top wall, drilled from the inner face, on +-x: +y belongs to the
// mic and the bore between them is the button's. Blind is the point — a through-hole here would
// be two visible dots either side of the button.
//
// These briefly became bosses holding M3 inserts, on the argument that 2 mm of thread in 2.2 mm
// of blind PLA is the weakest joint in the box. A printed one works, so they are back: the M3
// version needed a boss (a 3 mm wall cannot hold a ~5 mm insert) and the boss needed the pitch
// pushed out to 34 to stop it fighting the holder's collar for the same ring of wall.
module button_pilots() {
    for (sx = [-1, 1])
        translate([btn_pos[0] + sx*btn_pilot_pitch/2, btn_pos[1], wall - btn_pilot_depth])
            cylinder(h = btn_pilot_depth + 0.1, d = board_screw_pilot);
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

// ---- rear wall -------------------------------------------------------------
// Window over the devkit's own two USB-C ports: power, first flash and serial log all
// come through here, which is why there is no separate panel-mount USB socket. It is
// a BOUNDED hole — material is left below it so the rim that meets the base plate
// stays continuous.
module usb_window() {
    translate([s3_pos_x, -outer_h()/2, s3_usb_cz_eff()])
        cube([s3_usb_w(), wall*3, s3_usb_h_eff()], center = true);
}

// ...and the wall around it thinned from the INSIDE, to usb_panel_t. Same trick and the same
// reason as the 3.5 mm socket's panel on the +x wall: a plug has a fixed amount of shell
// before its overmold, and every millimetre of wall in front of the receptacle is a
// millimetre the plug cannot use.
//
// It was not needed while the devkit registered against this wall — the receptacle sat 3.3 mm
// in and that was that. The rear stops on the base plate hold the board 2.2 mm off the wall
// now, so without this the setback would be 5.8 against a 6.5 limit.
//
// Cut on the inner face only, so the outside stays a plain flat wall, and stopped well short
// of the bottom rim, which still has to be full thickness where the base plate seats on it.
module usb_panel() {
    y_hi = -inner_half_y() + 0.05;
    y_lo = -(outer_h()/2 - usb_panel_t);
    translate([s3_pos_x, (y_hi + y_lo)/2, s3_usb_cz_eff()])
        cube([s3_usb_w() + 2*usb_cb_margin, y_hi - y_lo,
              s3_usb_h_eff() + 2*usb_cb_margin], center = true);
}

// ---- +x side wall ----------------------------------------------------------
// The DAC board's OWN 3.5 mm socket, used through a locally THINNED panel. Three cuts:
// a counterbore on the inner face that the socket body nests into, the plug hole
// through what is left, and a lead-in on the outer face.
//
// The thinning is what makes the socket usable. A 3.5 mm plug has ~14 mm of barrel and
// needs nearly all of it in to make the ring contact; a full 3 mm wall in front of the
// socket costs enough of that to leave the plug unseated. And the socket stops INSIDE
// the counterbore rather than poking through, so the base plate carrying the board can
// still rise straight up into the shell — a protruding socket would have to be threaded
// in sideways, which a vertical joint cannot do.
//
// Line level: it feeds a powered speaker or an amp, never a driver.
module dac_jack_cut() {
    cy = dac_jack_w +  2*clr;
    cz = dac_jack_h + 2*clr;
    panel_x = outer_w()/2 - jack_panel_t;
    // counterbore on the inner face — the socket body lives in here
    translate([(inner_half_x() - 0.1 + panel_x)/2, dac_jack_y(), dac_jack_cz()])
        cube([panel_x - inner_half_x() + 0.1, cy, cz], center = true);
    // plug hole through the thinned panel, on the barrel axis
    translate([panel_x - 0.1, dac_jack_y(), dac_axis_z()]) rotate([0, 90, 0])
        cylinder(h = jack_panel_t + 0.2, d = jack_hole_d);
    // lead-in on the OUTER face, so a plug meets a chamfer and not a cut edge
    translate([outer_w()/2 - jack_lead_in, dac_jack_y(), dac_axis_z()]) rotate([0, 90, 0])
       cylinder(h = jack_lead_in + 0.1, d1 = jack_hole_d, d2 = jack_hole_d + 2*jack_lead_in);
}



// ---- corners ---------------------------------------------------------------
// Full-depth pillars from the top face to the base plate rim, each taking an M3
// heat-set insert. Being full-depth is what makes them obstacles on every plane in
// the box, which is why the board layout is stacked rather than spread.
module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*boss_cx(), sy*boss_cy(), wall])
            screw_boss(cavity_depth, boss_od, insert_m3_d);
}

module shell() {
    difference() {
        union() {
            shell_body(top_depth());
            corner_bosses();
            mic_posts();
        }
        button_cut();
        button_pilots();
        mic_seat();
        usb_window();
        usb_panel();
        dac_jack_cut();
    }
}
