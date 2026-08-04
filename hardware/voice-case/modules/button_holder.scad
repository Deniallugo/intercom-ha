// ===== button holder — the switch carrier and the cap's guide (no top-level geometry) =====
// A cup that screws to the inside of the top face on two blind M2 pilots. It provides three
// things the shell deliberately does not: the lower half of the journal the cap slides in,
// the shoulder its lip snaps onto, and a floor for the 11 mm tactile switch to stand on. The
// shell keeps only a bore, a recess and the two pilots, so tuning any of it never costs a
// shell reprint.
//
// It got SIMPLER when the coil spring came out. There is no boss: the boss existed only to
// raise a rim for the spring to seat on, with the switch pocket sunk inside that rim, and with
// no spring there is nothing to seat. The switch stands directly on the collar floor.
//
// There is no full pocket WALL around the switch: a wall following the body's outline would have
// to fit between the 15.6 mm diagonal and the cap's 17.2 mm bore, which is 0.8 mm at the
// corners. Instead there are four LOCATING RIBS, one at the midpoint of each edge, where the
// gap is 3.1 mm rather than 0.8. They cost no depth at all — they stand beside the body, not
// under it — and they are what stops the switch wandering; the pins alone let it slide several
// millimetres inside their own windows.
//
// Nothing holds it DOWN and nothing needs to: pressing the cap loads the switch straight into
// the floor, and the plunger's reaction on release pushes it the same way.
//
// Why it is a CUP and not a flat plate: stack guide, lip relief, plunger aperture and switch
// body in series below the top face and the module reaches ~17.5 mm down, into a devkit that
// tops out at 15.9. Standing the switch INSIDE the guide puts the two side by side rather
// than end to end.
//
// Internal profile, from the wall inward (all case z):
//   bh_z0       .. bh_catch_z    guide bore — the far half of what stops the cap rocking
//   bh_catch_z                   the catch: the guide's own end face, where the lip lands
//   bh_catch_z  .. bh_relief_z1  relief. Not just room for the lip — the lip TRAVELS
//                                down it, so it is the lip plus the whole stroke
//   bh_relief_z1                 collar floor. The switch stands on this, reaching back UP
//                                past the catch into the cap's body bore.
//   bh_relief_z1.. bh_z1         floor thickness, with four windows through it for the pins
//
// Drawn in PRINTING orientation: the floor is flat on the build plate at z = 0 and the
// part grows +z toward the face that mates the top wall. Print z is bh_z1() - case z,
// i.e. the REVERSE of the case — unlike every other part here, and that is the point. A
// cup printed mouth-down has to bridge its own floor across the full Ø34; printed
// floor-down there is nothing to support. The screw tabs follow from the same choice:
// they are full-height posts rather than a flange, because a flange standing 8 mm out
// from the collar is an overhang and a post is a vertical wall — and it buys a straight
// shot for the driver as well.
//
// Assembly order is switch, then holder, then cap: drop the switch into the collar with its
// four pins through the floor windows, screw the collar up onto the pilots, solder the pins
// from below, then snap the cap in from outside. Nothing is blind and nothing is glued.
module button_holder() {
    h       = bh_z1() - bh_z0();          // 8.35 overall
    z_floor = bh_floor_t;                 // 1.6 collar floor top — the switch stands here
    z_catch = bh_z1() - bh_catch_z();     // 3.35 relief top = the catch shoulder
    ear_x   = btn_pilot_pitch/2;
    lead_in = 0.6;
    union() {
        difference() {
            union() {
                cylinder(h = h, d = bh_collar_od());
                for (sx = [-1, 1]) {
                    translate([sx*ear_x, 0, 0]) cylinder(h = h, d = bh_ear_d);
                    // web tying each post back into the collar. A plain vertical wall,
                    // so it costs nothing to print in this orientation.
                    translate([sx*(bh_collar_od()/2 + ear_x)/2, 0, h/2])
                        cube([ear_x - bh_collar_od()/2 + 2, bh_fin_t, h], center = true);
                }
            }
            // guide bore, with a lead-in at the mouth so the cap's lip meets a chamfer
            // and not a cut edge
            translate([0, 0, z_catch]) cylinder(h = h - z_catch + 0.1, d = bh_bore_d());
            translate([0, 0, h - lead_in])
                cylinder(h = lead_in + 0.1, d1 = bh_bore_d(), d2 = bh_bore_d() + 2*lead_in);
            // lip relief. Its upper face is the guide's end, and that IS the catch.
            translate([0, 0, z_floor - 0.01])
                cylinder(h = z_catch - z_floor + 0.02, d = bh_relief_d());
            // M2 clearance up the posts, counterbored so no head stands proud of the
            // floor — the devkit is only 2.8 mm below it
            for (sx = [-1, 1]) translate([sx*ear_x, 0, -0.1]) {
                cylinder(h = h + 0.2, d = bh_screw_clear);
                cylinder(h = bh_screw_cbore_h + 0.1, d = bh_screw_cbore_d);
            }
            pin_windows(z_floor);
        }
        switch_ribs(z_floor);
    }
}

// ---- four ribs that locate the switch ------------------------------------------
// At the midpoint of each edge, standing off the floor beside the body. Plain vertical walls, so
// they cost nothing in this print orientation, and they reach no further from the axis than
// sw_locate_max() — asserted against the cap's bore, which comes down over them.
//
// Two lengths. The switch's pins stand OUT from two opposite sides, so on those two the rib has
// to fit in the gap between that side's pair of pins; on the other two it runs full length. Get
// this wrong and a rib sits over a pin window with nothing under it.
module switch_ribs(z_floor) {
    if (sw_locate_t > 0 && sw_locate_h > 0)
        for (i = [0 : 3]) {
            // i even -> the +-x pair, i odd -> the +-y pair
            pinned = (i % 2) == sw_pin_axis;
            len    = pinned ? sw_locate_len_pin : sw_locate_len;
            rotate([0, 0, i*90])
                translate([(sw_locate_r0() + sw_locate_r1())/2, 0,
                           z_floor + sw_locate_h/2])
                    cube([sw_locate_t, len, sw_locate_h], center = true);
        }
}

// ---- the four pins: straight down through the floor ----------------------------
// A 4x4's two legs came out SIDEWAYS through the pocket wall and then along the floor and out
// through the collar's rim, because a boss stood in the middle and there was nowhere else for
// them to go. With no boss the floor is the direct route, and these are the windows.
//
// Four radial SLOTS, not four squares, and that is the point: how far the legs stand out from the
// body's side faces is the one dimension this design kept getting wrong, so the slot covers a
// range of it rather than a position. As drawn each one accepts a pin anywhere from flush with the
// side face to 2.5 mm outboard.
//
// They run inboard of the body's outline on purpose, which is why sw_seat_area() is 115 rather
// than the full 121 — a cheap price for not having to know the number.
//
// The pins hang through and are soldered under the holder, which is why the module's real depth
// is sw_pin_z1() and not bh_z1(), and why cavity_depth is derived from the former.
module pin_windows(z_floor) {
    w = sw_pin_win_xy();
    for (p = sw_pin_pos())
        translate([p[0], p[1], (z_floor + 0.2)/2 - 0.1])
            cube([w[0], w[1], z_floor + 0.2], center = true);
}
