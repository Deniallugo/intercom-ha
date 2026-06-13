// ===== sealed shell body (no top-level geometry) =====
// Open-back box with a flat front baffle carrying both drivers. Drivers drop in
// from the back against the baffle inner face, seal on a foam gasket ring, and
// screw to bosses on the 43 mm square. One sealed wire pass exits the bottom.

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

// 4 corner M3 bosses (front side), full internal depth — the rear lid screws into these
module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

// single sealed wire pass: a bounded hole through the bottom (-y) perimeter wall,
// centered on X at depth wire_pass_z, so the cable leaves out the bottom while the
// rest of the bottom wall stays solid (does NOT run to the back edge).
module wire_pass_cut() {
    translate([0, -outer_h()/2, wire_pass_z])
        rotate([90, 0, 0])
            cylinder(h = wall*3, d = wire_pass_d, center = true);
}

// optional internal brace: a thin rib spanning top<->bottom behind the divider line
module brace_rib() {
    if (brace)
        translate([0, 0, wall])
            linear_extrude(cavity_depth)
                translate([-brace_w/2, -(outer_h()/2 - wall)])
                    square([brace_w, outer_h() - 2*wall]);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
            speaker_screw_bosses();
            corner_bosses();
            brace_rib();
        }
        cone_cuts();
        gasket_grooves();
        wire_pass_cut();
    }
}
