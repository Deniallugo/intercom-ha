// ===== button holder — the separate switch carrier (no top-level geometry) =====
// A plate that screws to the inside of the top face on two blind M2 pilots, carrying
// the 6x6 tactile switch in a block below it and providing the shoulder the cap's lip
// snaps onto. The shell keeps nothing but a bore, a cosmetic recess and those pilots.
//
// Why it is a separate part: with the seat moulded into the shell, tuning the snap, the
// travel or the switch fit meant reprinting the shell, and the switch had to be pushed
// into a blind pocket down a 15 mm hole and glued by feel. Now the mechanism assembles
// in the open, is tested by pressing it with a finger, and reprints in minutes.
//
// Internal profile, from the wall inward (all case z):
//   bh_z0     .. bh_catch_z   bore for the cap skirt; its UNDERSIDE is the catch
//   bh_catch_z.. bh_plate_z1  relief the cap's lip sits in
//   bh_plate_z1..bh_apert_z1  plunger aperture — too narrow for the switch body to pass
//   bh_apert_z1..bh_z1        switch body pocket, with leg slots out both +-x walls
//
// Drawn in PRINTING orientation: the plate face that mates the wall is flat on the
// build plate at z = 0 and the part grows +z, which is also the direction it grows in
// the case. The one internal overhang is the short annular bridge where the aperture
// closes over the lip relief — a normal bridge at 0.2 mm layers, no support needed.
module button_holder() {
    // local z: 0 = the plate face that touches the wall's inner surface
    plate_h  = bh_plate_z1() - bh_z0();
    bore_h   = bh_bore_t;
    relief_h = bh_relief_h;
    apert_h  = bh_apert_z1() - bh_plate_z1();
    body_h   = bh_z1() - bh_apert_z1();
    total_h  = bh_z1() - bh_z0();
    difference() {
        union() {
            linear_extrude(plate_h) rounded_rect(bh_plate_w, bh_plate_l, bh_plate_r);
            translate([0, 0, plate_h - 0.01])
                linear_extrude(total_h - plate_h + 0.01)
                    square([bh_block, bh_block], center = true);
        }
        // cap-skirt bore — the shoulder at its far end is what the lip catches on
        translate([0, 0, -0.1]) cylinder(h = bore_h + 0.1, d = bh_bore_d());
        // lip relief
        translate([0, 0, bore_h]) cylinder(h = relief_h + 0.01, d = bh_relief_d());
        // plunger aperture: narrower than the switch body, so the body cannot pass and
        // its top face lands on the ledge at the far end
        translate([0, 0, bore_h + relief_h])
            cylinder(h = apert_h + 0.01, d = bh_apert_d());
        // switch body pocket, open at the far end so the switch pushes straight in
        translate([0, 0, bore_h + relief_h + apert_h])
            linear_extrude(body_h + 0.1)
                square([sw_body + 2*clr, sw_body + 2*clr], center = true);
        // leg slots out both +-x walls, at the body
        for (sx = [-1, 1])
            translate([sx*bh_block/2, 0, bh_z1() - bh_z0() - sw_leg_slot_h/2 - 0.2])
                cube([bh_wall*3, sw_leg_slot_w, sw_leg_slot_h + 0.4], center = true);
        // M2 clearance holes onto the shell's blind pilots
        for (sy = [-1, 1])
            translate([0, sy*btn_pilot_pitch/2, -0.1])
                cylinder(h = plate_h + 0.2, d = bh_screw_clear);
    }
}
