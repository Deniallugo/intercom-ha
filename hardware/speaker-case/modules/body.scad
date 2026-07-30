// ===== 53 mm vertical-pair ported shell body (no top-level geometry) =====
// Open-back box. A horizontal divider seals the upper SPEAKER CHAMBER (TWO 53 mm
// drivers stacked vertically on the front baffle, tuned port on the +x side wall)
// off from the lower vented ELECTRONICS BAY. Driver wires cross the divider through
// four SEALED TERMINAL BOLTS, not a wire pass.

// ---- speaker zone (upper, sealed) -----------------------------------------

// Shallow full-circle recess on the OUTER baffle face: locates the frame and lands a
// punched foam gasket ring. There is no annular groove and no raised boss — a 53 mm
// frame leaves only a 3.5 mm annulus between the cutout and the frame edge, and a
// boss at the bolt circle would overlap both.
module driver_recess(i) {
    translate([spk_cx(), spk_cy(i), -0.1])
        cylinder(h = spk_recess_depth + 0.1, d = spk_recess_d);
}

// the cutout must pierce the baffle AND the local pad behind it
module cone_cut(i) {
    translate([spk_cx(), spk_cy(i), -0.1]) cylinder(h = wall + spk_pad_t + 0.2, d = spk_cut);
}

// local baffle pad on the INNER face: material for the blind pilots to bite, and
// stiffness where the driver's reaction force lands
module driver_pad(i) {
    translate([spk_cx(), spk_cy(i), wall]) cylinder(h = spk_pad_t, d = spk_pad_d);
}

// 4 BLIND M2 pilots into the baffle, drilled from the recess floor. Blind is the
// point: a through-hole at the bolt circle would vent the chamber.
module driver_pilots(i) {
    translate([spk_cx(), spk_cy(i), spk_recess_depth])
        on_bolt_circle(spk_screw_n, spk_bolt_circle)
            translate([0, 0, -0.1]) cylinder(h = spk_pilot_depth + 0.1, d = spk_screw_pilot);
}

// ---- tuned port (+x side wall) ---------------------------------------------

// Bore for the separate printed port tube, plus a flange register on the outer face
// so the flange sits flush. Keeping the tube a separate part is what makes Fb
// tunable: print another length instead of reprinting the box.
module port_bore() {
    translate([side_x(), spk_zone_cy(), port_cz]) rotate([0, 90, 0]) {
        translate([0, 0, -0.1]) cylinder(h = wall + 0.2, d = port_od() + clr);
        // flange register, recessed into the OUTER face
        translate([0, 0, wall - port_flange_t])
            cylinder(h = port_flange_t + 0.1, d = port_flange_od + clr);
    }
}

// ---- divider (sealing floor) + sealed terminal bolts -----------------------

// One M3 clearance bore per conductor, each with an O-ring seat on the CHAMBER side.
// Four, not two: dual mono on a BTL amp gives no common return.
module divider_terminals() {
    for (i = [0 : term_n - 1]) {
        tx = (i - (term_n-1)/2) * term_pitch;
        translate([tx, divider_cy(), term_cz]) {
            rotate([90, 0, 0]) cylinder(h = divider_t*3, d = term_d, center = true);
            // O-ring seat on the chamber side (+y face of the divider)
            translate([0, divider_t/2 - term_oring_depth, 0]) rotate([-90, 0, 0])
                cylinder(h = term_oring_depth + 0.1, d = term_oring_od);
        }
    }
}

module divider() {
    difference() {
        translate([0, divider_cy(), wall + cavity_depth/2])
            cube([outer_w() - 2*wall, divider_t, cavity_depth], center = true);
        divider_terminals();
    }
}

// ---- electronics bay: front wall ------------------------------------------

module bay_boards() {
    // S3 devkit: friction pocket (no reliable mount holes). Rides high in the bay so
    // the bottom strip is free for the PTT counterbore.
    translate([s3_pos[0], board_cy()+s3_pos[1], wall])
        board_pocket(s3_w, s3_l, board_standoff_h+2, pocket_wall);
}

// PTT panel-mount momentary switch, bottom-center of the front baffle.
// The bore runs through a LOCALLY THINNED panel (btn_panel_t) so a switch rated
// for a 1-3 mm panel still gets enough thread for its nut; behind it a flat
// counterbore takes the nut (bezel-in-front switch) or the body shoulder
// (nut-in-front switch). Flat land on both faces = the switch clamps solid and
// the actuator can't rock, which is the whole point of the thinning.
module button_bore() {
    translate([btn_pos[0], board_cy()+btn_pos[1], 0]) {
        translate([0, 0, -0.1]) cylinder(h = btn_panel_t + 0.1, d = btn_bore_d);
        cylinder(h = btn_lead_in, d1 = btn_bore_d + 2*btn_lead_in, d2 = btn_bore_d);
        translate([0, 0, btn_panel_t])
            cylinder(h = wall - btn_panel_t + 0.1, d = btn_pocket_d);
        translate([0, 0, -0.1]) difference() {                  // tactile halo, outer face
            cylinder(h = btn_halo_depth + 0.1, d = btn_halo_od);
            translate([0, 0, -0.1]) cylinder(h = btn_halo_depth + 0.3, d = btn_halo_id);
        }
    }
}

// ---- electronics bay: bottom wall ------------------------------------------
// mic / USB-C / sub-jack all live on the bottom wall. The mic is here rather than on
// the front baffle so the drivers shake it as little as the box allows, and so its
// port faces down. Placements are (x, z): z = depth from the front face.

// The mic seat is the acoustic design, not just a mount: a board-locating recess, a
// gasket seat inside it, and ONE short hole. Pressing the ICS-43434's port onto the
// gasket leaves near-zero front volume, putting the port resonance ~15 kHz instead of
// the ~5.7 kHz the old 7-hole cluster produced.
module mic_seat() {
    translate([mic_pos[0], -outer_h()/2, mic_pos[1]]) rotate([-90, 0, 0]) {
        // board-locating recess in the inner face
        translate([0, 0, wall - mic_seat_depth])
            linear_extrude(mic_seat_depth + 0.1)
                square([mic_board_w + 2*clr, mic_board_l + 2*clr], center = true);
        // gasket seat, deeper still
        translate([0, 0, wall - mic_seat_depth - mic_gasket_depth])
            cylinder(h = mic_gasket_depth + 0.01, d = mic_gasket_d);
        // the single port, through whatever wall is left
        translate([0, 0, -0.1])
            cylinder(h = wall - mic_seat_depth - mic_gasket_depth + 0.2, d = mic_hole_d);
    }
}

// two M2 posts flanking the mic seat, on FULL-THICKNESS wall (never in the thinned
// zone): screw the board down and the gasket compression makes the seal
module mic_posts() {
    for (sx = [-1, 1])
        translate([mic_pos[0] + sx*mic_post_pitch/2, -outer_h()/2 + wall, mic_pos[1]])
            rotate([-90, 0, 0]) screw_boss(mic_post_h, mic_post_od, board_screw_pilot);
}

// USB-C 5 V panel-mount socket through the bottom wall: a body cutout plus two blind
// M2 pilots. Cable exits straight down. (A flat breakout facing the side wall put its
// receptacle 2.8 mm inside a corner lid boss — see params.)
module usbc_panel() {
    // body cutout, centred
    translate([usbc_pos[0], -outer_h()/2 - 0.1, usbc_pos[1]])
        translate([-usbc_cut_w/2, 0, -usbc_cut_l/2])
            cube([usbc_cut_w, wall + 0.2, usbc_cut_l]);
    // two blind mounting pilots, drilled from the OUTER face
    for (sx = [-1, 1])
        translate([usbc_pos[0] + sx*usbc_screw_pitch/2, -outer_h()/2 - 0.1, usbc_pos[1]])
            rotate([-90, 0, 0]) cylinder(h = usbc_pilot_depth + 0.1, d = board_screw_pilot);
}

// 3.5 mm sub line-out (PCM5102 R channel) through the bottom wall
module jack_bore() {
    translate([jack_pos[0], -outer_h()/2 - 0.1, jack_pos[1]]) rotate([-90, 0, 0])
        cylinder(h = wall + 0.2, d = jack_bore_d);
}

// ---- electronics bay: +x side wall ----------------------------------------
// service opening over the devkit's own USB-C ports (first flash, serial logs).
// Breaches the BAY only — the chamber is above the divider.
module s3_service_slot() {
    translate([outer_w()/2, board_cy()+s3_pos[1], s3_usb_z()])
        cube([wall*3, s3_usb_w, s3_usb_h], center = true);
}

// ---- corners --------------------------------------------------------------

module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, insert_m3_d);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            divider();
            corner_bosses();
            bay_boards();
            mic_posts();
            for (i = [0 : spk_n - 1]) driver_pad(i);
        }
        for (i = [0 : spk_n - 1]) {
            cone_cut(i);
            driver_recess(i);
            driver_pilots(i);
        }
        port_bore();
        button_bore();
        mic_seat();
        usbc_panel();
        jack_bore();
        s3_service_slot();
    }
}
