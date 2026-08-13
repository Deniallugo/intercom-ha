// ===== rear lid (no top-level geometry) =====
// A flat lid `wall` thick. The 4 corner bosses live on the BODY at full depth and
// carry M3 HEAT-SET INSERTS; screws drop through these clearance holes into them.
// This is the joint opened repeatedly (wiring, board access, polyfill), which is why
// it gets inserts while the drivers keep self-tap pilots. A perimeter gasket groove on
// the inner face seals the lid to the body rim. Wall mounting uses RECESSED keyhole
// bosses on the OUTER face — a retaining plate carries the keyhole over a head cavity
// floored by the solid lid panel, so the screw head is captured yet the sealed
// speaker chamber behind the lid is never breached.
// The PCM5102 DAC and the PAM8406 amp stand off the inner face into the bay.

// recessed keyhole bosses on the lid's outer (wall-side) face. A retaining plate
// (kb_lip) at the boss top carries the keyhole cut; behind it a head-clearance
// cavity is floored by the solid lid panel, so the sealed chamber is never
// breached. Mirrored in y so the head-circle sits at the BOTTOM: the head drops
// in, the box settles down, the shank rides up the slot and the plate lip traps
// the head under its own weight.
//
// The pair is stacked VERTICALLY, not side by side: 120 mm spacing cannot fit an
// 86 mm lid, and on a 194 mm-tall box two vertically-spaced screws resist the
// tip-out moment far better than two at the same height.
module keyhole_bosses() {
    for (ky = keyhole_ys)
        translate([0, ky, wall])
            mirror([0, 1, 0])
            difference() {
                // raised boss standing off the lid outer face
                linear_extrude(kb_h)
                    offset(r = kb_pad) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
                // head-clearance cavity: head_d-wide the full drop so the screw head
                // slides from the entry circle to the captured position. Floored by
                // the solid lid panel (cut stops kb_lip below the wall-side face).
                translate([0, 0, -0.01])
                    linear_extrude(kb_h - kb_lip + 0.01)
                        keyhole(keyhole_head_d + kb_clr, keyhole_head_d + kb_clr, keyhole_drop);
                // keyhole through the wall-side retaining plate: circle admits the
                // head, the narrow slot captures it behind the lip.
                translate([0, 0, kb_h - kb_lip - 0.01])
                    linear_extrude(kb_lip + 0.02)
                        keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
            }
}

// PCM5102 DAC + PAM8406 amp mount on the lid INNER face (standoffs toward the bay)
module lid_boards() {
    translate([dac_pos[0], board_cy()+dac_pos[1], 0])
        mirror([0,0,1])
            board_standoffs(dac_w, dac_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    translate([amp_pos[0], board_cy()+amp_pos[1], 0])
        mirror([0,0,1])
            board_standoffs(amp_w, amp_l, board_standoff_h, board_standoff_od, board_screw_pilot);
}

module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
            keyhole_bosses();
            lid_boards();
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
