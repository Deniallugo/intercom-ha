// ===== rear wall plate (no top-level geometry) =====
module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);   // plate
            for (sx = [-1, 1], sy = [-1, 1])                                    // mating bosses
                translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
                    cylinder(h = rear_depth - wall, d = boss_od);
        }
        // screw clearance holes (rear -> into front bosses)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = rear_depth + 0.2, d = screw_clear);
        // keyhole wall-mount slots
        for (sx = [-1, 1])
            translate([sx*keyhole_spacing/2, 0, -0.1])
                linear_extrude(wall + 0.2) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
        // (no USB notch — the USB-C exit is a bounded hole in the front shell's
        //  bottom wall, so the rear plate's bottom edge stays solid)
    }
}
