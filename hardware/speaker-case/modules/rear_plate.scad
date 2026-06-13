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

// TPA3116 amp mounts on the lid INNER face (standoffs toward the bay)
module tpa_mount() {
    translate([tpa_pos[0], board_cy()+tpa_pos[1], -board_standoff_h])
        mirror([0,0,1])
            board_standoffs(tpa_w, tpa_l, board_standoff_h, board_standoff_od, board_screw_pilot);
}

module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
            keyhole_bosses();
            tpa_mount();
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
