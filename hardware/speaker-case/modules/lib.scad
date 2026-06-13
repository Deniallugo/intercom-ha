// ===== shared helpers (no top-level geometry) =====

// 2D rounded rectangle centered at origin
module rounded_rect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - r), sy*(h/2 - r)]) circle(r);
}

// hollow shell body: outer rounded box, open at the +z (back) face,
// leaving a `wall`-thick front face at z in [0, wall].
module shell_body(depth) {
    difference() {
        linear_extrude(depth) rounded_rect(outer_w(), outer_h(), radius);
        translate([0, 0, wall])
            linear_extrude(depth)
                rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
    }
}

// 2D concentric-ring perforation field within diameter `cut_d`
module grille(cut_d) {
    grille_hole_d = 3;
    grille_ring_step = 6;
    for (r = [0 : grille_ring_step : cut_d/2 - grille_hole_d]) {
        if (r == 0) circle(d = grille_hole_d);
        else {
            n = max(1, floor(2*PI*r / (grille_hole_d*1.8)));
            for (i = [0 : n-1]) rotate(i*360/n) translate([r, 0]) circle(d = grille_hole_d);
        }
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

// screw boss with self-tap pilot, base at z=0
module screw_boss(h, od, pilot) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1]) cylinder(h = h + 0.2, d = pilot);
    }
}

// N screw bosses on a bolt CIRCLE of diameter `bc`, base at z=0
module screw_circle(n, bc, h, od, pilot) {
    for (i = [0 : n - 1])
        rotate([0, 0, i*360/n + 45]) translate([bc/2, 0, 0])
            screw_boss(h, od, pilot);
}
