// ===== amplifier box: shell, rear lid, board sled (box-local frame) =====

// cut helpers: 2D children are drawn in the plane of the wall being cut
//   through_y: 2D (x, z), cut downward from y = y_from     (top / bottom walls)
//   through_x: 2D (z, y), cut toward +x from x = x_from    (side walls)
module through_y(y_from, len) {
    translate([0, y_from, 0]) rotate([90, 0, 0]) linear_extrude(len) children();
}
// No mirror(): a mirrored 2D profile extruded and rotated comes out with reversed winding, and
// CGAL drops it ("mesh is not closed") — silently, so every side vent went missing from the STLs.
// rotate([0, -90, 0]) maps 2D (a, b) and extrusion e to (-e, b, a); start at the far side instead.
module through_x(x_from, len) {
    translate([x_from + len, 0, 0]) rotate([0, -90, 0]) linear_extrude(len) children();
}
module top_cut(h)    { through_y(h + 0.1, wall + 0.2) children(); }
module floor_cut()   { through_y(wall + 0.1, wall + 0.2) children(); }
module side_cut(sx)  { through_x(sx > 0 ? box_w/2 - wall - 0.1 : -box_w/2 - 0.1, wall + 0.2) children(); }

module lid_bosses(h) {
    for (p = lid_boss_pts(h)) lid_boss(p, box_d(), p[1] > h/2 ? 1 : -1);
}

// ---- front: the controls ----
module amp_front_cut() {
    if (ctrl_mode == "faceplate") {
        // through-window, smaller than the faceplate by the lip on every side
        translate([0, 0, -0.1]) linear_extrude(wall + 0.2) translate(face_c())
            square([amp_face_w - 2*face_lip, amp_face_h - 2*face_lip], center = true);
        // rebate the faceplate nests in, from the inside
        translate([0, 0, wall - face_rebate]) linear_extrude(face_rebate + 0.1) translate(face_c())
            square([amp_face_w + 2*face_fit, amp_face_h + 2*face_fit], center = true);
    } else {
        translate([0, 0, -0.1]) linear_extrude(wall + 0.2) {
            for (i = [-1 : 1])
                translate([amp_x + ctrl_x0 + i*ctrl_pitch, amp_pcb_y() + ctrl_axis])
                    circle(d = ctrl_bush_d + 2*clr + 2*ctrl_slack);
            translate([amp_x + ctrl_led[0], amp_pcb_y() + ctrl_led[1]]) circle(d = ctrl_led_d);
        }
    }
}

function term_xs() = let (c = (amp_term_x[0] + amp_term_x[1])/2)
                     [for (i = [0 : 3]) amp_x + c + (i - 1.5)*term_pitch];

module amp_shell() {
    h = amp_h();
    d = box_d();
    difference() {
        union() {
            box_shell(box_w, h, d, box_r, front_chamfer);
            lid_bosses(h);
        }
        amp_front_cut();
        // top: pass-through for the sleeve, over the plug zone
        top_cut(h) translate([sleeve_x, sleeve_zc()]) circle(d = sleeve_od() + 2*clr);
        // top: exhaust over the heatsink
        top_cut(h) translate([amp_x + amp_hs[0], amp_bz(amp_hs[1])]) slot_field(5, amp_hs[3] + 12);
        // top: screwdriver access to the barrier-block screws (service, box off the wall)
        if (term_access)
            for (x = term_xs())
                top_cut(h) translate([x, amp_bz(amp_term_screw_from_rear)]) circle(d = term_access_d);
        // sides: two rows of slots high on both walls, over the board
        for (sx = [-1, 1], r = [0, 1])
            side_cut(sx) translate([amp_front_z() + 40, h - wall - 4 - r*vent_pitch])
                rotate(90) slot_field(1, 50);
        // +x side: panel power switch, in the plug zone
        if (amp_psw)
            side_cut(1) translate([psw_zc(), amp_psw_y])
                if (amp_psw_shape == "rect") square(amp_psw_cut, center = true);
                else circle(d = amp_psw_round_d);
    }
}

// ---- rear lid, shared by both boxes ----
// Plate + two legs + four pegs. The legs make the cable channel (open top and bottom); the pegs on
// their ends drop into the wall plate's keyholes. Inner face down for printing; legs grow upward.
module box_lid(h, peg_ys) {
    difference() {
        union() {
            linear_extrude(lid_t) box_outline(box_w, h, box_r);
            intersection() {
                translate([0, 0, lid_t - 0.01]) linear_extrude(chan_d + 0.01) box_outline(box_w, h, box_r);
                for (sx = [-1, 1])
                    translate([sx*peg_x() - leg_w/2, 0, lid_t - 0.01]) cube([leg_w, h, chan_d + 0.01]);
            }
            for (sx = [-1, 1], py = peg_ys)
                translate([sx*peg_x(), py, lid_t + chan_d - 0.01]) peg();
        }
        for (p = lid_boss_pts(h))
            translate([p[0], p[1], -0.1]) cylinder(h = lid_t + 0.2, d = screw_clear);
        children();   // per-box cut-outs
    }
}

module amp_lid() {
    box_lid(amp_h(), peg_y_amp)
        // cable window: barrel plug and speaker wires out into the channel
        translate([amp_win_x0(), amp_win_y0(), -0.1])
            cube([amp_win_x1() - amp_win_x0(), amp_win_y1() - amp_win_y0(), lid_t + 0.2]);
}

// ---- board sled ----
// A flat plate that runs the full inside depth, front wall to lid, so the lid is what holds it in z
// and nothing in the shell has to locate it. The board screws to it OUTSIDE the box, then the pair
// slides in from the rear until the faceplate lands in its rebate. Standoffs sit on the PHOTO-
// estimated holes: this is the part to reprint when they turn out wrong, not the shell.
module sled_plate(t = sled_t, notch = true) {
    z0 = wall + 0.2;
    z1 = box_d() - 0.2;
    w  = inner_w() - 2*clr;
    difference() {
        translate([-w/2, wall, z0]) cube([w, t, z1 - z0]);
        if (notch)   // clear the bottom lid bosses and their tapers
            for (sx = [-1, 1])
                translate([sx*lid_boss_x_bot - lid_boss_od/2 - 0.6, wall - 0.1, lid_boss_z0() - 0.6])
                    cube([lid_boss_od + 1.2, t + 0.2, box_d()]);
    }
}

module mp_pocket() {
    cav = [mp_w + 2*clr, mp_l + 2*clr];
    o   = cav + [2*mp_wall, 2*mp_wall];
    translate([mp_x, wall + sled_t, mp_zc()])
        difference() {
            translate([-o[0]/2, 0, -o[1]/2]) cube([o[0], mp_lip, o[1]]);
            translate([-cav[0]/2, -0.1, -cav[1]/2]) cube([cav[0], mp_lip + 0.2, cav[1]]);
            // wire exits at both short ends (IN on one, OUT on the other)
            translate([-o[0]/2 - 0.1, -0.1, -3]) cube([o[0] + 0.2, mp_lip + 0.2, 6]);
        }
}

module amp_sled() {
    sled_plate();
    for (p = amp_holes)
        translate([amp_x + p[0], wall + sled_t - 0.01, amp_bz(p[1])]) rotate([-90, 0, 0])
            screw_boss(amp_standoff_len() + 0.01, amp_standoff_od, amp_hole_pilot);
    mp_pocket();
}
