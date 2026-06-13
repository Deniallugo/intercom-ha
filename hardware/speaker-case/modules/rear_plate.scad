// ===== rear lid (no top-level geometry) =====
// A flat lid `wall` thick. The 4 corner M3 bosses live on the BODY at full depth;
// screws drop through these clearance holes and self-tap into them. A perimeter
// gasket groove on the inner face seals the lid to the body rim. Wall mounting
// uses BLIND keyhole bosses on the OUTER face — cut through the boss only, never
// through the lid panel, so the sealed speaker chamber behind the lid stays sealed.
// A module-retention collar on the inner face preloads the module in its cradle.

// blind keyhole bosses on the lid's outer (wall-side) face. The keyhole is cut
// through the raised boss down to the lid panel surface; the panel stays solid.
module keyhole_bosses() {
    for (sx = [-1, 1])
        translate([sx*keyhole_spacing/2, key_cy(), wall])
            difference() {
                linear_extrude(kb_h)
                    offset(r = kb_pad) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
                translate([0, 0, -0.01])
                    linear_extrude(kb_h + 0.02) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
            }
}

// screwless module clamp: a square perimeter collar grown off the plate's INNER
// face (toward the module) and centered on the cradle. Its rim lands on the
// module's back edge and preloads it forward into the cradle floor.
module module_clamp() {
    o = mod_clamp_foot;                 // collar outer
    i = o - 2*mod_clamp_wall;           // collar inner (open center)
    translate([cradle_cx(), board_cy(), -mod_clamp_h()])
        linear_extrude(mod_clamp_h())
            difference() {
                square(o, center = true);
                square(i, center = true);
            }
}

module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);   // flat plate
            keyhole_bosses();                                                  // wall mount (outer face)
            if (mod_clamp) module_clamp();                                     // retention collar (inner face)
        }
        // perimeter gasket groove on the inner (z=0) face
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
    }
}
