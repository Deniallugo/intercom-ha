// ===== sound-first PR-loaded shell body (no top-level geometry) =====
// Open-back box. A horizontal divider seals the upper SPEAKER CHAMBER (one
// PS95-8 on the front baffle, a passive radiator on the +x side wall) off from
// the lower vented ELECTRONICS BAY. Driver wires run up through one sealed pass
// in the divider. PR/bay geometry is added in later tasks.

// ---- speaker zone (upper, sealed) -----------------------------------------

module speaker_seat() {
    translate([spk_cx(), spk_cy(), wall])
        difference() {
            cylinder(h = spk_seat_depth, d = spk_od + 2*seat_wall);
            translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
        }
}

module cone_cut() {
    translate([spk_cx(), spk_cy(), -0.1]) linear_extrude(wall + 0.2) circle(d = spk_cut);
}

module gasket_groove() {
    translate([spk_cx(), spk_cy(), wall - gasket_depth])
        difference() {
            cylinder(h = gasket_depth + 0.1, d = gasket_od);
            translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
        }
}

module speaker_screw_bosses() {
    translate([spk_cx(), spk_cy(), wall])
        screw_circle(spk_screw_n, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// ---- divider (sealing floor) -----------------------------------------------

// single sealed wire pass, centered under the driver
module divider_wire_cut() {
    translate([spk_cx(), divider_cy(), divider_wire_z])
        rotate([90, 0, 0])
            cylinder(h = divider_t*3, d = divider_wire_d, center = true);
}

module divider() {
    difference() {
        translate([0, divider_cy(), wall + cavity_depth/2])
            cube([outer_w() - 2*wall, divider_t, cavity_depth], center = true);
        divider_wire_cut();
    }
}

// ---- corners --------------------------------------------------------------

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
            speaker_seat();
            speaker_screw_bosses();
            corner_bosses();
        }
        cone_cut();
        gasket_groove();
    }
}
