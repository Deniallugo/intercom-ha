// ===== shared helpers (no top-level geometry) =====

// 2D rounded rectangle centered at origin
module rounded_rect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - r), sy*(h/2 - r)]) circle(r);
}

// hollow shell body: outer rounded box with a 45 deg CHAMFERED front edge, open at
// the +z (back) face, leaving a `wall`-thick front face at z in [0, wall].
//
// The chamfer is the diffraction control. An 8 mm radius on a 158 mm baffle did
// nothing (the baffle step sits near lambda ~ W, and smearing it needs r >~ 15 mm);
// a 6 mm chamfer on a 74 mm front face is a real transition. It is a chamfer rather
// than a true fillet on purpose: printed back-down the baffle is on top, and a
// tangent fillet starts horizontal there — a local 90 deg overhang. A chamfer is
// support-free.
module shell_body(depth) {
    difference() {
        hull() {
            linear_extrude(0.01)
                rounded_rect(flat_w(), flat_h(), max(0.5, radius - chamfer));
            translate([0, 0, chamfer])
                linear_extrude(depth - chamfer)
                    rounded_rect(outer_w(), outer_h(), radius);
        }
        translate([0, 0, wall])
            linear_extrude(depth)
                rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
    }
}

// 2D keyhole: head circle on top, slot dropping down by `drop`
module keyhole(slot_w, head_d, drop) {
    union() {
        circle(d = head_d);
        translate([0, -drop/2]) square([slot_w, drop], center = true);
        translate([0, -drop]) circle(d = slot_w);
    }
}

// screw boss with a self-tap pilot (or a heat-set insert bore), base at z=0
module screw_boss(h, od, pilot) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1]) cylinder(h = h + 0.2, d = pilot);
    }
}

// place children at N points on a bolt CIRCLE of diameter `bc`. The 45 deg offset
// puts 4 points on a square, which is how small-driver flanges are drilled.
module on_bolt_circle(n, bc) {
    for (i = [0 : n - 1])
        rotate([0, 0, i*360/n + 45]) translate([bc/2, 0, 0]) children();
}

// 4 corner standoffs for a board of footprint w x l, centered at origin, base z=0.
// `inset` = hole center distance from each board edge (M2 default ~2 mm).
module board_standoffs(w, l, h, od, pilot, inset=2) {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - inset), sy*(l/2 - inset), 0]) screw_boss(h, od, pilot);
}

// friction pocket (floor + 4 walls, open at +z) for a board w x l, centered at origin
module board_pocket(w, l, h, pw) {
    difference() {
        translate([0, 0, h/2]) cube([w + 2*pw, l + 2*pw, h], center = true);
        translate([0, 0, h/2 + pw]) cube([w, l, h], center = true);
    }
}

// boolean helper: do two centered AABBs (at p1/p2, sizes s1/s2) clear each other?
function aabb_clear(p1, s1, p2, s2) =
    (abs(p1[0]-p2[0]) >= (s1[0]+s2[0])/2) || (abs(p1[1]-p2[1]) >= (s1[1]+s2[1])/2);
