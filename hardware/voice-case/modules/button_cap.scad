// ===== snap-in button cap (no top-level geometry) =====
// The visible part: a scaled TalkingPetDIY dome — flange, straight body, and a top that
// is one big fillet. See the button block in params.scad for where the proportions come
// from, and which of them are the reference's and which are ours.
//
// Drawn in PRINTING orientation: the dome APEX is on the build plate at z = 0 and the
// part grows +z. That is the same direction as case z, so the assembled preview is a
// plain translate; case z maps to print z by adding btn_dome_h.
//
// Printed apex-down the whole part is a cup — floor, then walls, then a post standing up
// inside it — with no overhang anywhere. Three things make that true and each is
// load-bearing:
//   * the top fillet meets the plate tangentially, like any rounded-bottom part
//   * the step out to the flange is 45 deg, because btn_flare_h() is DERIVED from the
//     flange/body step rather than typed in
//   * the post's root is a cone that narrows upward
// The other orientation — flange-down, the way the reference part prints — leaves the
// dome's whole inner ceiling in mid-air.
//
// It is still a snap-in cup and its lip still catches on the HOLDER rather than on the
// shell, because the holder is the cheap part to reprint. The body wall is a JOURNAL first
// and a snap second — a dome shows lean that a flat disc hid, and a Ø22 flange shows it more
// than a Ø18 one did — so the slits that let the lip collapse start well below the top face
// (btn_slit_z0) and never cross the shell bore, and the lip is the only thing on the body
// that is off nominal diameter.
//
// The bore under the dome is not just clearance any more: the 11 mm switch stands UP inside it
// from the holder's floor, so Ø17.2 of it exists to clear that switch's 15.6 mm diagonal. It
// is what sets the whole cap's size.
module button_cap() {
    pz      = btn_dome_h;              // case z + pz = print z
    r_top   = btn_top_d()/2;
    r_wall  = btn_wall_od/2;
    r_in    = btn_wall_id()/2;
    r_flng  = btn_cap_d/2;
    r_lip   = btn_lip_od()/2;
    z_flare = pz + btn_flare_top_z();  // body meets the flare
    z_fl0   = pz + btn_flange_top_z(); // flange, upper face
    z_fl1   = pz + btn_face_bot_z();   // flange, underside — what rests over the recess
    z_catch = pz + bh_catch_z();       // lip's square shoulder
    z_end   = pz + btn_wall_z1();      // body's far edge
    z_slit0 = pz + btn_slit_z0;
    big     = 4*btn_cap_d;
    difference() {
        union() {
            // One revolved section for the whole shell: out from the apex and down the
            // outside, round the flange, on down the body to the lip, then back up the
            // inside and home along the axis.
            rotate_extrude(convexity = 8) polygon(concat(
                [[0, 0]],
                arc_pts(r_top, btn_dome_r, btn_dome_r, -90, 0),   // outer top fillet
                [[r_wall, z_flare],                               // body
                 [r_flng, z_fl0],                                 // 45 deg flare out
                 [r_flng, z_fl1], [r_wall, z_fl1],                // flange
                 [r_wall, z_catch],                               // body, on down to the lip
                 // Retention lip. Tapered, not a square barb: the far end enters the bore
                 // first, so it is the narrow end and the body cams inward as you press.
                 // The step back at the near end stays square — that face is the catch.
                 [r_lip, z_catch], [r_wall, z_end],
                 [r_in, z_end], [r_in, btn_dome_r]],              // back up the inside
                arc_pts(r_top, btn_dome_r, btn_dome_r - btn_wall_t, 0, -90),
                [[0, btn_wall_t]]
            ));
            // Centre post, on axis, reaching btn_preload PAST the plunger's free position —
            // so with the lip on the catch the switch is holding the cap up there, and the
            // cap cannot rattle. It carries the whole thumb load until the plunger bottoms
            // in the switch body under it. Nothing keys the cap's rotation and nothing needs
            // to.
            cylinder(h = btn_wall_t + btn_post_h(), d = btn_post_d);
        }
        // Radial slits, so the lip can collapse through the shell bore. They start below
        // the top face and run off the far edge, which leaves the body solid everywhere
        // the shell bore touches it. Each cut runs outward from the axis only, so
        // btn_slits is the slit count, not half of it.
        for (i = [0 : btn_slits - 1])
            rotate([0, 0, i*360/btn_slits])
                translate([0, big/2, (z_slit0 + z_end + 0.2)/2])
                    cube([btn_slit_w, big, z_end + 0.2 - z_slit0], center = true);
    }
}
