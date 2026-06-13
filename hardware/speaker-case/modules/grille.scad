// ===== optional snap-on grille (no top-level geometry) =====
// A perforated disc per driver with a short skirt that snaps over the driver
// seat ring. Purely protective; never touches the sealed volume.
grille_face_t  = 1.6;          // perforated face thickness
grille_skirt_h = 5;            // skirt depth gripping the seat ring
grille_skirt_t = 1.6;          // skirt wall

module grille_cover() {
    for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy(), 0]) {
        // perforated face
        difference() {
            cylinder(h = grille_face_t, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
            translate([0, 0, -0.1]) linear_extrude(grille_face_t + 0.2) grille(spk_cut);
        }
        // grip skirt (snaps over the seat ring OD with clearance)
        translate([0, 0, -grille_skirt_h])
            difference() {
                cylinder(h = grille_skirt_h, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
                translate([0, 0, -0.1])
                    cylinder(h = grille_skirt_h + 0.2, d = spk_od + 2*seat_wall + 2*clr);
            }
    }
}
