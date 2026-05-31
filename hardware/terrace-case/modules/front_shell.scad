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

module front_shell() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
            voicesr_cradle();
        }
        grille_cut();
    }
}
