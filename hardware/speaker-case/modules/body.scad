// ===== combined-device shell body (no top-level geometry) =====
// Open-back box. A horizontal divider seals the upper SPEAKER CHAMBER (two
// drivers on the flat front baffle) off from the lower vented ELECTRONICS BAY
// (VoiceS3R module + 2x MAX98357A amps + button + mic + USB-C). Speaker wires run
// up through one sealed pass in the divider.

// ---- speaker zone (upper, sealed) -----------------------------------------

// raised locating rings on the inner front face (each driver centers in one)
module speaker_seats() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            difference() {
                cylinder(h = spk_seat_depth, d = spk_od + 2*seat_wall);
                translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
            }
}

// open cone cutouts through the front wall (the cone radiates through these)
module cone_cuts() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy()]) circle(d = spk_cut);
}

// annular groove in the baffle inner face under each driver flange (foam ring)
module gasket_grooves() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall - gasket_depth])
            difference() {
                cylinder(h = gasket_depth + 0.1, d = gasket_od);
                translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
            }
}

// 4 bosses per driver on the 43 mm square; the flange screws into them from the back
module speaker_screw_bosses() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            for (cx = [-1, 1], cy = [-1, 1])
                translate([cx*spk_screw_square/2, cy*spk_screw_square/2, 0])
                    screw_boss(spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// ---- divider (sealing floor of the speaker chamber) ------------------------

// sealed wire passes: one bounded hole per driver, directly below it, so each
// driver's 2-wire pair runs straight up from the amps (grommet + silicone each).
module divider_wire_cut() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), divider_cy(), divider_wire_z])
            rotate([90, 0, 0])
                cylinder(h = divider_t*3, d = divider_wire_d, center = true);
}

// horizontal slab spanning the full inner width and full cavity depth; butts the
// rear lid (foam tape on its back edge for the seam).
module divider() {
    difference() {
        translate([0, divider_cy(), wall + cavity_depth/2])
            cube([outer_w() - 2*wall, divider_t, cavity_depth], center = true);
        divider_wire_cut();
    }
}

// ---- electronics bay (lower, vented) — ported from terrace-case ------------

// 3-wall pocket holding the module button-forward; open at the back (+z),
// USB-C slot toward the bottom edge, wire windows toward the amps (+/-x).
module voicesr_cradle() {
    cw = mod_w + 2*mod_clr;                 // inner pocket size
    translate([cradle_cx(), board_cy(), wall]) difference() {
        translate([0, 0, mod_d/2]) cube([cw + 2*cradle_wall, cw + 2*cradle_wall, mod_d], center = true);
        // pocket, open at back
        translate([0, 0, mod_d/2 + cradle_wall]) cube([cw, cw, mod_d], center = true);
        // USB-C slot through the bottom (-y) wall, bounded at the port depth (usb_z)
        translate([0, -(cw/2 + cradle_wall), usb_z - wall])
            cube([usb_conn_w + usb_clr, cradle_wall*3, usb_conn_t + usb_clr], center = true);
        // wire windows toward the amps on both sides (+/-x)
        for (s = [-1, 1])
            translate([s*(cw/2 + cradle_wall), 0, mod_d*0.55])
                cube([cradle_wall*3, mod_w*0.6, mod_d*0.6], center = true);
    }
}

// two amp boards flanking the centered module, on standoff posts with M2 pilots
module amp_mounts() {
    for (s = [-1, 1]) {
        bx = cradle_cx() + s*amp_off();
        translate([bx, board_cy(), wall])
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx*(amp_w/2 - 2), sy*(amp_l/2 - 2), 0])
                    screw_boss(amp_standoff_h, amp_standoff_od, amp_screw_pilot);
    }
}

// well bored through the front wall AND the cradle floor so the plunger nub can
// reach the module switch; a retaining shoulder sits at the front-wall inner face.
module button_well() {
    translate([cradle_cx(), board_cy(), -0.1]) {
        cylinder(h = wall + cradle_wall + 0.2, d = btn_well_d);
        translate([0, 0, wall]) cylinder(h = 1.2, d = btn_well_d + 1.6);
    }
}

// mic perforation cluster through the front wall AND the cradle floor, opening
// into the pocket at the module's mic.
module mic_perf() {
    translate([mic_x(), mic_y(), -0.1]) linear_extrude(wall + cradle_wall + 0.2) {
        circle(d = mic_hole_d);
        for (i = [0 : mic_ring_n - 1])
            rotate(i*360/mic_ring_n) translate([mic_ring_r, 0]) circle(d = mic_hole_d);
    }
}

// USB-C exit through the bottom (-y) perimeter wall: a bounded (sealed) hole
// centered under the cradle at the port depth (usb_z); does NOT run to the back edge.
module usb_floor_cut() {
    translate([cradle_cx(), -outer_h()/2, usb_z])
        cube([usb_conn_w + usb_clr, wall*3, usb_conn_t + usb_clr], center = true);
}

// ---- corners --------------------------------------------------------------

// 4 corner M3 bosses (front side), full internal depth — the rear lid screws into these
module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            divider();
            // speaker zone
            speaker_seats();
            speaker_screw_bosses();
            // electronics bay
            voicesr_cradle();
            amp_mounts();
            // corners
            corner_bosses();
        }
        cone_cuts();
        gasket_grooves();
        button_well();
        mic_perf();
        usb_floor_cut();
    }
}
