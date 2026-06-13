// ===== rear wall plate (no top-level geometry) =====
// A FLAT lid `wall` thick. The corner M3 bosses are full-depth on the FRONT
// shell (see front_bosses); the screws drop through these clearance holes from
// the back and self-tap straight into those front bosses. The plate grows no
// proud bosses of its own — they would poke out the back (fouling the flush
// keyhole wall-mount) or collide with the front bosses at the same corners.
module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);   // flat plate
            if (mod_clamp) module_clamp();                                     // retention collar (inner face)
        }
        // screw clearance holes (rear -> into front bosses)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = wall + 0.2, d = screw_clear);
        // keyhole wall-mount slots
        for (sx = [-1, 1])
            translate([sx*keyhole_spacing/2, 0, -0.1])
                linear_extrude(wall + 0.2) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
        // (no USB notch — the USB-C exit is a bounded hole in the front shell's
        //  bottom wall, so the rear plate's bottom edge stays solid)
    }
}

// Screwless module clamp: a square perimeter collar grown off the plate's INNER
// face (local -z, toward the module) and centered on the cradle. Its leading
// rim lands on the module's back edge and preloads it forward into the cradle
// floor. Hollow center clears back-side components; OUTER footprint is < the
// pocket inner so the collar drops into the pocket at assembly.
module module_clamp() {
    o = mod_clamp_foot;                 // collar outer
    i = o - 2*mod_clamp_wall;           // collar inner (open center)
    translate([cradle_cx(), board_cy(), -mod_clamp_h()])
        linear_extrude(mod_clamp_h())
            difference() {
                square(o, center = true);
                square(i, center = true);
            }
}
