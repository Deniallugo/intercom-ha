// ===== front shell + sub-modules (no top-level geometry) =====

// raised locating ring on the inside of the front wall (driver drops in)
module speaker_seats() {
    translate([spk_cx(), spk_cy(), wall])
        difference() {
            cylinder(h = spk_seat_depth, d = spk_od + 2*cradle_wall);
            translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
        }
}

// perforations through the front wall over the speaker
module grille_cut() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        translate([spk_cx(), spk_cy()]) grille(spk_cut);
}

// annular groove in the baffle inner face under the driver flange — seats a
// foam/EVA gasket ring so the flange seals the front wave from the back wave.
module gasket_grooves() {
    translate([spk_cx(), spk_cy(), wall - gasket_depth])
        difference() {
            cylinder(h = gasket_depth + 0.1, d = gasket_od);
            translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
        }
}

// 3-wall pocket holding the Atom Echo top-face-forward; open at the back (+z),
// USB-C slot toward the bottom edge, wire window toward the amp (+x).
module atom_cradle() {
    cw = mod_w + 2*mod_clr;                 // inner pocket size
    translate([cradle_cx(), board_cy(), wall]) difference() {
        translate([0, 0, mod_d/2]) cube([cw + 2*cradle_wall, cw + 2*cradle_wall, mod_d], center = true);
        // pocket, open at back
        translate([0, 0, mod_d/2 + cradle_wall]) cube([cw, cw, mod_d], center = true);
        // USB-C slot through the bottom wall (toward -y)
        translate([0, -(cw/2 + cradle_wall), mod_usb_h/2 + 1])
            cube([mod_usb_w, cradle_wall*3, mod_usb_h], center = true);
        // wire window toward the amp on the +x side
        translate([(cw/2 + cradle_wall), 0, mod_d*0.55])
            cube([cradle_wall*3, mod_w*0.6, mod_d*0.6], center = true);
    }
}

// well bored through the front wall AND the cradle floor behind it, so the
// plunger nub can reach the module's switch. A retaining shoulder the cap's
// lip catches behind sits at the front-wall inner face.
module button_well() {
    translate([cradle_cx(), board_cy(), -0.1]) {
        cylinder(h = wall + cradle_wall + 0.2, d = btn_well_d);          // bore through wall + cradle floor
        translate([0, 0, wall]) cylinder(h = 1.2, d = btn_well_d + 1.6); // shoulder pocket
    }
}

// mic perforation: a small cluster of holes through the front wall AND the
// cradle floor, so the holes open into the pocket right at the module's mic.
module mic_perf() {
    translate([mic_x(), mic_y(), -0.1]) linear_extrude(wall + cradle_wall + 0.2) {
        circle(d = mic_hole_d);
        for (i = [0 : mic_ring_n - 1])
            rotate(i*360/mic_ring_n) translate([mic_ring_r, 0]) circle(d = mic_hole_d);
    }
}

// frame-hole screw bosses around the driver: the flange screws down into these
// from inside the case (bolt circle clears the driver OD).
module speaker_screw_bosses() {
    translate([spk_cx(), spk_cy(), wall])
        for (i = [0 : spk_screw_n - 1])
            rotate(spk_screw_a0 + i*360/spk_screw_n)
                translate([spk_bolt_circle/2, 0, 0])
                    screw_boss(spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// one amp board to the right of the centered module, on standoff posts with M2
// self-tap pilots so the board screws down.
module amp_mounts() {
    translate([amp_cx(), board_cy(), wall])
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(amp_w/2 - 2), sy*(amp_l/2 - 2), 0])
                screw_boss(amp_standoff_h, amp_standoff_od, amp_screw_pilot);
}

// 4 corner screw bosses (front side), self-tap pilots
module front_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

module front_shell() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
            speaker_screw_bosses();
            atom_cradle();
            amp_mounts();
            front_bosses();
        }
        grille_cut();
        gasket_grooves();
        button_well();
        mic_perf();
    }
}

// fit-test coupon: the lower band of the front shell — the bottom arc of the
// speaker seat, the cradle, button well, mic, and amp standoffs — plus a button
// cap printed alongside it (placed in the empty top area).
module coupon_render() {
    intersection() {
        front_shell();
        translate([-outer_w()/2 - 1, -outer_h()/2 - 1, -5])
            cube([outer_w() + 2, board_zone_h + bottom_margin + 18, front_depth + 10]);
    }
    translate([0, outer_h()/2 - 8, 0]) button_cap();
}
