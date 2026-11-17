// ===== shared helpers (no top-level geometry) =====
// Box-local frame throughout: x across, y up, z into the box from the front face.

module rounded_rect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - r), sy*(h/2 - r)]) circle(r);
}

// Box outline in the x-y plane: w wide, h tall, bottom edge at y = 0.
module box_outline(w, h, r) { translate([0, h/2]) rounded_rect(w, h, r); }

// Open-backed shell: front face at z in [0, wall], walls to z = d, open at z = d.
// The front edge is a 45 deg chamfer because the shell prints front-face-down.
module box_shell(w, h, d, r, c) {
    difference() {
        hull() {
            // inset by c on EVERY side, bottom included — box_outline() puts its bottom edge at
            // y = 0, so the smaller outline has to be lifted by c or the chamfer is all on top
            translate([0, c, 0]) linear_extrude(0.01) box_outline(w - 2*c, h - 2*c, max(0.5, r - c));
            translate([0, 0, c]) linear_extrude(d - c) box_outline(w, h, r);
        }
        translate([0, wall, wall]) linear_extrude(d)
            translate([0, (h - 2*wall)/2]) rounded_rect(w - 2*wall, h - 2*wall, max(0.5, r - wall));
    }
}

// Lid-screw boss on a top or bottom wall at the rear rim, with a 45 deg taper toward the front so it
// prints unsupported in the shell's front-face-down orientation. `p` = [x, y] of the screw axis,
// `up` = +1 for a boss hanging from the top wall, -1 for one standing on the bottom wall.
module lid_boss(p, d, up) {
    wall_y = up > 0 ? p[1] + lid_boss_od/2 + 0.5 : p[1] - lid_boss_od/2 - 0.5;
    difference() {
        union() {
            // the taper: a hull of the wall line and the boss's FRONT disc — exactly what the
            // Fusion port's loft between a rectangle and a circle builds
            hull() {
                translate([p[0], p[1], d - lid_boss_len]) cylinder(h = 0.01, d = lid_boss_od);
                translate([p[0] - lid_boss_od/2, wall_y - 0.25, d - lid_boss_len - lid_boss_taper()])
                    cube([lid_boss_od, 0.5, 0.01]);
            }
            translate([p[0], p[1], d - lid_boss_len]) cylinder(h = lid_boss_len, d = lid_boss_od);
        }
        translate([p[0], p[1], d - insert_m3_h - 1]) cylinder(h = insert_m3_h + 1.1, d = insert_m3_d);
    }
}

// A field of vent slots, long axis along z, centred at (cx, cz) in the plane they are cut through.
module slot_field(n, len) {
    for (i = [0 : n - 1])
        translate([(i - (n - 1)/2)*vent_pitch, 0])
            hull() for (s = [-1, 1]) translate([0, s*(len - vent_w)/2]) circle(d = vent_w);
}

// 2D keyhole: entry circle at the top, slot dropping `drop` below it. The peg ends at the BOTTOM of
// the slot (y = 0 here) with the box hung.
module keyhole2d(slot_w, head_d, drop) {
    hull() { circle(d = slot_w); translate([0, drop]) circle(d = slot_w); }
    translate([0, drop]) circle(d = head_d);
}

// Peg standing on z = 0, pointing +z: neck, then a 45 deg cone out to the head, then a short
// cylinder. Prints upward with nothing worse than 45 deg.
module peg() {
    neck = kh_lip + kh_clr;
    cone = (peg_head_d - peg_neck_d)/2;
    cylinder(h = neck + 0.01, d = peg_neck_d);
    translate([0, 0, neck]) cylinder(h = cone, d1 = peg_neck_d, d2 = peg_head_d);
    translate([0, 0, neck + cone]) cylinder(h = peg_head_h, d = peg_head_d);
}
function peg_len() = kh_lip + kh_clr + (peg_head_d - peg_neck_d)/2 + peg_head_h;

module screw_boss(h, od, pilot) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1]) cylinder(h = h + 0.2, d = pilot);
    }
}

// points along a circular arc, for rotate_extrude profiles
function arc_pts(cx, cz, r, a0, a1, n = 24) =
    [for (i = [0 : n]) let (a = a0 + (a1 - a0)*i/n) [cx + r*cos(a), cz + r*sin(a)]];

function aabb_clear(p1, s1, p2, s2) =
    (abs(p1[0]-p2[0]) >= (s1[0]+s2[0])/2) || (abs(p1[1]-p2[1]) >= (s1[1]+s2[1])/2);
