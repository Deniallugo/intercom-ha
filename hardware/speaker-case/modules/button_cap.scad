// ===== captive button plunger (no top-level geometry) — ported from terrace =====
module button_cap() {
    face_t  = btn_proud;
    skirt_h = wall + 1.0;
    flat_y  = btn_cap_d/2 - btn_slice;   // bottom slice plane (-y), opposite the nub
    big     = 4*btn_well_d;
    difference() {
        union() {
            cylinder(h = face_t, d = btn_cap_d);                                  // proud face
            translate([0, 0, -skirt_h]) cylinder(h = skirt_h, d = btn_well_d - 2*clr); // skirt in well
            translate([0, 0, -skirt_h]) cylinder(h = 1.0, d = btn_well_d - 2*clr + 1.4); // retention lip
            translate([0, btn_above_center, -skirt_h - btn_travel]) cylinder(h = btn_travel + 0.5, d = btn_nub_d); // contact nub, offset toward the top switch (+y)
        }
        // orientation/fixing slice: a flat on the -y bottom (opposite the nub)
        translate([-big/2, -flat_y - big, -skirt_h - btn_travel - 1]) cube([big, big, face_t + skirt_h + btn_travel + 2]);
    }
}
