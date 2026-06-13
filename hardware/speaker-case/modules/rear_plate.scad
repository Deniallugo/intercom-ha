// ===== rear lid (no top-level geometry) =====
// A FLAT lid `wall` thick. The 4 corner M3 bosses live on the BODY at full depth;
// screws drop through these clearance holes from the back and self-tap into them.
// A perimeter gasket groove on the inner face seals the lid to the body rim.
// Two keyhole slots hang the box on two wall screws.
module rear_plate() {
    difference() {
        linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
        // perimeter gasket groove on the inner (-z assembled) face, cut from z=0 up
        translate([0, 0, -0.1])
            linear_extrude(lid_gasket_depth + 0.1)
                difference() {
                    rounded_rect(outer_w() - 2*lid_gasket_inset + lid_gasket_w,
                                 outer_h() - 2*lid_gasket_inset + lid_gasket_w,
                                 max(0.5, radius - lid_gasket_inset));
                    rounded_rect(outer_w() - 2*lid_gasket_inset - lid_gasket_w,
                                 outer_h() - 2*lid_gasket_inset - lid_gasket_w,
                                 max(0.5, radius - lid_gasket_inset - lid_gasket_w));
                }
        // screw clearance holes (rear -> into the body corner bosses)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = wall + 0.2, d = screw_clear);
        // keyhole wall-mount slots
        for (sx = [-1, 1])
            translate([sx*keyhole_spacing/2, 0, -0.1])
                linear_extrude(wall + 0.2) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
    }
}
