// ===== shared helpers (no top-level geometry) =====

// 2D rounded rectangle centered at origin
module rounded_rect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - r), sy*(h/2 - r)]) circle(r);
}

// hollow shell body: outer rounded box with a 45 deg CHAMFERED TOP edge, open at the
// +z (base) face, leaving a `wall`-thick top face at z in [0, wall].
//
// Chamfer rather than fillet: the shell prints top-face-down, so the top edge is on
// the build plate and a tangent fillet would start horizontal there — a local 90 deg
// overhang. A 45 deg chamfer is support-free and reads the same from a metre away.
module shell_body(depth) {
    difference() {
        hull() {
            linear_extrude(0.01)
                rounded_rect(2*flat_half_x(), 2*flat_half_y(), max(0.5, radius - chamfer));
            translate([0, 0, chamfer])
                linear_extrude(depth - chamfer)
                    rounded_rect(outer_w(), outer_h(), radius);
        }
        translate([0, 0, wall])
            linear_extrude(depth)
                rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
    }
}

// points along a circular arc, for building rotate_extrude profiles. Angles in degrees,
// CCW positive, and a0/a1 may run either way — the caller picks the direction so the
// points come out in polygon order.
function arc_pts(cx, cz, r, a0, a1, n = 24) =
    [for (i = [0 : n]) let (a = a0 + (a1 - a0)*i/n) [cx + r*cos(a), cz + r*sin(a)]];

// screw boss with a self-tap pilot (or a heat-set insert bore), base at z=0
module screw_boss(h, od, pilot) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1]) cylinder(h = h + 0.2, d = pilot);
    }
}

// boolean helper: do two centered AABBs (at p1/p2, sizes s1/s2) clear each other?
function aabb_clear(p1, s1, p2, s2) =
    (abs(p1[0]-p2[0]) >= (s1[0]+s2[0])/2) || (abs(p1[1]-p2[1]) >= (s1[1]+s2[1])/2);
