// ===== wall plate + lock bracket =====
// Plate frame: x across, y up (= world z, 0 at the bottom of the amp box), z out of the wall
// (z = 0 is the wall side). Printed BACK DOWN: the keyhole cavities open onto the bed and the lip
// over them is an ~8.4 mm bridge; the header block and the countersinks are on top.

function kh_slot_w() = peg_neck_d + 2*kh_clr;
function kh_head_d() = peg_head_d + 2*kh_clr;
// every peg, in plate coordinates, at its HUNG position (bottom of its slot)
function peg_pts() = concat(
    [for (sx = [-1, 1], py = peg_y_amp)   [sx*peg_x(), py]],
    [for (sx = [-1, 1], py = peg_y_voice) [sx*peg_x(), voice_z0() + py]]);
function header_w() = 2*(peg_x() - leg_w/2 - 1);
function ws_pts() = [for (sx = [-1, 1], y = [12, plate_h() - header_h - 12]) [sx*ws_x, y]];

module wall_plate() {
    difference() {
        union() {
            translate([-plate_w()/2, 0, 0]) cube([plate_w(), plate_h(), plate_t]);
            // header between the legs, for the lock bracket's inserts
            translate([-header_w()/2, plate_h() - header_h, plate_t - 0.01])
                cube([header_w(), header_h, header_d - plate_t + 0.01]);
        }
        for (p = peg_pts()) translate([p[0], p[1], 0]) {
            // lip: the keyhole proper
            translate([0, 0, plate_t - kh_lip - 0.1]) linear_extrude(kh_lip + 0.2)
                keyhole2d(kh_slot_w(), kh_head_d(), peg_drop);
            // cavity behind it, head-wide over the whole travel, open to the wall
            translate([0, 0, -0.1]) linear_extrude(plate_t - kh_lip + 0.1)
                keyhole2d(kh_head_d(), kh_head_d(), peg_drop);
        }
        // wall screws, countersunk on the front face
        for (p = ws_pts()) translate([p[0], p[1], 0]) {
            translate([0, 0, -0.1]) cylinder(h = plate_t + 0.2, d = ws_d);
            translate([0, 0, plate_t - (ws_head_d - ws_d)/2])
                cylinder(h = (ws_head_d - ws_d)/2 + 0.01, d1 = ws_d, d2 = ws_head_d);
        }
        // lock-bracket inserts, down into the header's top face
        for (sx = [-1, 1])
            translate([sx*lock_screw_x, plate_h() + 0.1, (plate_t + header_d)/2])
                rotate([90, 0, 0]) cylinder(h = insert_m3_h + 1.1, d = insert_m3_d);
    }
}

// Lock bracket, world-aligned but printed flat: x across, y = distance from the wall, z = up from
// the plate top. It sits on the header and spans over both voice legs' top ends lock_gap below it.
module lock_bracket() {
    y1 = lid_back_y() - 0.5;
    difference() {
        translate([-box_w/2, 0.5, 0]) cube([box_w, y1 - 0.5, lock_t]);
        for (sx = [-1, 1]) translate([sx*lock_screw_x, (plate_t + header_d)/2, -0.1]) {
            cylinder(h = lock_t + 0.2, d = screw_clear);
            translate([0, 0, lock_t - 1.8]) cylinder(h = 2, d = 6.2);
        }
    }
}
