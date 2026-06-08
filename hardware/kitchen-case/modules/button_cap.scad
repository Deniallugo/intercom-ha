// ===== captive button plunger (no top-level geometry) =====
module button_cap() {
    face_t  = 1.6;
    skirt_h = wall + 1.0;
    union() {
        cylinder(h = face_t, d = btn_cap_d);                                  // proud face
        translate([0, 0, -skirt_h]) cylinder(h = skirt_h, d = btn_well_d - 2*clr); // skirt in well
        translate([0, 0, -skirt_h]) cylinder(h = 1.0, d = btn_well_d - 2*clr + 1.4); // retention lip
        translate([0, btn_above_center, -skirt_h - btn_travel]) cylinder(h = btn_travel + 0.5, d = btn_nub_d); // contact nub, offset toward the top switch
    }
}
