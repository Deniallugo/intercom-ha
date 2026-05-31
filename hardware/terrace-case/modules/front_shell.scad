// ===== front shell + sub-modules (no top-level geometry) =====

// raised locating rings on the inside of the front wall (driver drops in)
module speaker_seats() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            difference() {
                cylinder(h = spk_seat_depth, d = spk_od + 2*cradle_wall);
                translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
            }
}

// perforations through the front wall over each speaker
module grille_cut() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy()]) grille(spk_cut);
}

// 3-wall pocket holding the module button-forward; open at the back (+z),
// USB-C slot toward the bottom edge, wire window toward the amps (+x).
module voicesr_cradle() {
    cw = mod_w + 2*mod_clr;                 // inner pocket size
    translate([cradle_cx(), board_cy(), wall]) difference() {
        translate([0, 0, mod_d/2]) cube([cw + 2*cradle_wall, cw + 2*cradle_wall, mod_d], center = true);
        // pocket, open at back
        translate([0, 0, mod_d/2 + cradle_wall]) cube([cw, cw, mod_d], center = true);
        // USB-C slot through the bottom wall (toward -y)
        translate([0, -(cw/2 + cradle_wall), mod_usb_h/2 + 1])
            cube([mod_usb_w, cradle_wall*3, mod_usb_h], center = true);
        // wire window toward the amps (+x)
        translate([cw/2 + cradle_wall, 0, mod_d*0.55])
            cube([cradle_wall*3, mod_w*0.6, mod_d*0.6], center = true);
    }
}

// well bored through the front wall, centered over the module button,
// with an internal retaining shoulder the cap's lip catches behind.
module button_well() {
    translate([cradle_cx(), board_cy(), -0.1]) {
        cylinder(h = wall + 0.2, d = btn_well_d);                       // bore
        translate([0, 0, wall]) cylinder(h = 1.2, d = btn_well_d + 1.6); // shoulder pocket
    }
}

// acoustic hole through the front wall (subtracted)
module mic_port() {
    translate([mic_x(), mic_y(), -0.1]) cylinder(h = wall + 0.2, d = mic_port_d);
}
// sealing collar on the inside, gasket seats on its top face (added)
module mic_boss() {
    translate([mic_x(), mic_y(), wall]) difference() {
        cylinder(h = mic_boss_h, d = mic_boss_od);
        translate([0, 0, -0.1]) cylinder(h = mic_boss_h + 0.2, d = mic_port_d + 0.6);
    }
}

// frame-hole screw bosses around each driver: the flange screws down into
// these from inside the case (bolt circle clears the driver OD).
module speaker_screw_bosses() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            for (i = [0 : spk_screw_n - 1])
                rotate(spk_screw_a0 + i*360/spk_screw_n)
                    translate([spk_bolt_circle/2, 0, 0])
                        screw_boss(spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// two amp boards in a row, right of the cradle, on standoff posts with
// M2 self-tap pilots so each board screws down.
module amp_mounts() {
    base_x = cradle_cx() + (mod_w/2) + cradle_wall + 6 + amp_w/2;
    for (i = [0 : 1]) {
        bx = base_x + i*(amp_w + 6);
        translate([bx, board_cy(), wall])
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx*(amp_w/2 - 2), sy*(amp_l/2 - 2), 0])
                    screw_boss(amp_standoff_h, amp_standoff_od, amp_screw_pilot);
    }
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
            voicesr_cradle();
            mic_boss();
            amp_mounts();
            front_bosses();
        }
        grille_cut();
        button_well();
        mic_port();
    }
}

// fit-test coupon: the left slice of the front shell — one speaker seat,
// the cradle, button well, and mic features — plus a button cap to test.
module coupon_render() {
    intersection() {
        front_shell();
        translate([-outer_w()/2 - 1, board_cy() - 28, -5])
            cube([outer_w()/2 + 12, 70, front_depth + 10]);
    }
    translate([-outer_w()/2 + 6, board_cy() + 40, 0]) button_cap();
}
