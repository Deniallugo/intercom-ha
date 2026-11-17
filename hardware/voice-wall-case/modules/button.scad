// ===== dome button: plunger + dome (+ voice-case holder) and the mic clamp =====
// Three printed parts and an 11 mm tactile:
//   plunger  voice-case's snap-lip cap with its dome cut off: a flat flange disc on top, the
//            Ø19.6 journal body, the snap lip and the centre post. Prints FLANGE DOWN.
//   dome     the big visible cap, glued onto the flange. Prints FLAT SIDE DOWN, any colour.
//   holder   voice-case's cup, unchanged except a longer guide (bh_guide_h 8).
// Assembly: snap the plunger through the face from the front (exactly as voice-case), screw the
// holder on from inside with the switch in it, THEN glue the dome onto the flange. Glue last, so the
// plunger can still be pulled for a holder change until you commit.

module plunger() {
    pz      = -btn_flange_top_z();     // case z + pz = print z (flange top on the bed)
    r_fl    = btn_flange_d/2;
    r_wall  = btn_wall_od/2;
    r_in    = btn_wall_id()/2;
    r_lip   = btn_lip_od()/2;
    z_fl1   = pz + btn_face_bot_z();   // flange underside = inner ceiling
    z_catch = pz + bh_catch_z();
    z_end   = pz + btn_wall_z1();
    z_slit0 = pz + btn_slit_z0;
    big     = 4*btn_flange_d;
    difference() {
        union() {
            rotate_extrude(convexity = 8) polygon([
                [0, 0], [r_fl, 0], [r_fl, z_fl1], [r_wall, z_fl1],
                [r_wall, z_catch], [r_lip, z_catch], [r_wall, z_end],
                [r_in, z_end], [r_in, z_fl1], [0, z_fl1]]);
            cylinder(h = z_fl1 + btn_post_h(), d = btn_post_d);
        }
        for (i = [0 : btn_slits - 1])
            rotate([0, 0, i*360/btn_slits])
                translate([0, big/2, (z_slit0 + z_end + 0.2)/2])
                    cube([btn_slit_w, big, z_end + 0.2 - z_slit0], center = true);
    }
}

// Spherical cap on a flat underside. The underside is flat out to btn_dome_flat_r(), then a 45 deg
// chamfer lifts the rim btn_rim_lift — that chamfer is what lets the part print with no support and
// is also the rim's clearance when the cap rocks. A shallow pocket takes the plunger flange: it
// centres the dome for gluing and is a 22 mm bridge, which an A1 handles.
module dome() {
    R0  = btn_dome_d/2;
    h   = btn_dome_h;
    Rs  = (R0*R0 + h*h)/(2*h);
    cz  = btn_rim_lift + h - Rs;                     // sphere centre
    a0  = atan2(btn_rim_lift - cz, R0);
    rs  = btn_flange_d/2 + 0.15;
    rotate_extrude(convexity = 6) polygon(concat(
        [[0, btn_dome_seat], [rs, btn_dome_seat], [rs, 0],
         [btn_dome_flat_r(), 0], [R0, btn_rim_lift]],
        arc_pts(0, cz, Rs, a0, 90, 48)));
}

// ---- holder: voice-case module, verbatim apart from the parameters ----
module button_holder() {
    h       = bh_z1() - bh_z0();
    z_floor = bh_floor_t;
    z_catch = bh_z1() - bh_catch_z();
    ear_x   = btn_pilot_pitch/2;
    lead_in = 0.6;
    union() {
        difference() {
            union() {
                cylinder(h = h, d = bh_collar_od());
                for (sx = [-1, 1]) {
                    translate([sx*ear_x, 0, 0]) cylinder(h = h, d = bh_ear_d);
                    translate([sx*(bh_collar_od()/2 + ear_x)/2, 0, h/2])
                        cube([ear_x - bh_collar_od()/2 + 2, bh_fin_t, h], center = true);
                }
            }
            translate([0, 0, z_catch]) cylinder(h = h - z_catch + 0.1, d = bh_bore_d());
            translate([0, 0, h - lead_in])
                cylinder(h = lead_in + 0.1, d1 = bh_bore_d(), d2 = bh_bore_d() + 2*lead_in);
            translate([0, 0, z_floor - bh_relief_eps])
                cylinder(h = z_catch - z_floor + 2*bh_relief_eps, d = bh_relief_d());
            for (sx = [-1, 1]) translate([sx*ear_x, 0, -0.1]) {
                cylinder(h = h + 0.2, d = bh_screw_clear);
                cylinder(h = bh_screw_cbore_h + 0.1, d = bh_screw_cbore_d);
            }
            pin_windows(z_floor);
        }
        switch_ribs(z_floor);
    }
}

module switch_ribs(z_floor) {
    z_seat = z_floor - bh_relief_eps;
    h      = sw_locate_h + bh_rib_embed;
    for (i = [0 : 3]) {
        pinned = (i % 2) == sw_pin_axis;
        len    = pinned ? sw_locate_len_pin : sw_locate_len;
        rotate([0, 0, i*90])
            translate([(sw_locate_r0() + sw_locate_r1())/2, 0, z_seat - bh_rib_embed + h/2])
                cube([sw_locate_t, len, h], center = true);
    }
}

module pin_windows(z_floor) {
    w = sw_pin_win_xy();
    for (p = sw_pin_pos())
        translate([p[0], p[1], (z_floor + 0.2)/2 - 0.1])
            cube([w[0], w[1], z_floor + 0.2], center = true);
}

// ---- mic clamp: voice-case module ----
module mic_clamp() {
    difference() {
        union() {
            translate([0, 0, mic_clamp_t/2]) cube([mic_clamp_len(), mic_clamp_w, mic_clamp_t], center = true);
            translate([0, 0, mic_clamp_t + mic_clamp_pad_h()/2])
                cube([mic_clamp_pad, min(mic_clamp_pad, mic_clamp_w), mic_clamp_pad_h()], center = true);
        }
        for (sx = [-1, 1])
            translate([sx*mic_post_pitch/2, 0, -0.1]) cylinder(h = mic_clamp_t + 0.2, d = mic_screw_clear);
    }
}
