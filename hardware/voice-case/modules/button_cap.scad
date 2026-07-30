// ===== snap-in button cap (no top-level geometry) =====
// Drawn in PRINTING orientation: the face is flat on the build plate at z = 0 and the
// part grows +z. That happens to be the same direction as case z (into the box), so
// the assembled preview is a plain translate.
//
// It is a cup, not a plug. A solid skirt the width of the bore cannot flex through it,
// so the skirt is a thin annulus split by radial slits; it collapses on the way in and
// springs back, and the lip on its lower edge then catches on the top wall's inner
// face. The switch spring holds the cap up against that lip — the recess floor is
// never the stop, which is what leaves `btn_face_gap` of free travel above it.
//
// The centre post reaches down the plunger bore in the switch seat. Nothing keys the
// cap's rotation and nothing needs to: the post is on axis.
module button_cap() {
    face_bottom = btn_face_t;
    lip_top     = face_bottom + btn_skirt_h();
    lip_bottom  = lip_top + btn_lip_t;
    big         = 4*btn_cap_d;
    difference() {
        union() {
            cylinder(h = btn_face_t, d = btn_cap_d);                 // face disc
            translate([0, 0, face_bottom])                            // skirt annulus
                difference() {
                    cylinder(h = btn_skirt_h() + btn_lip_t, d = btn_skirt_od());
                    translate([0, 0, -0.1])
                        cylinder(h = btn_skirt_h() + btn_lip_t + 0.2, d = btn_skirt_id());
                }
            translate([0, 0, lip_top])                                // retention lip
                difference() {
                    cylinder(h = btn_lip_t, d = btn_lip_od());
                    translate([0, 0, -0.1]) cylinder(h = btn_lip_t + 0.2, d = btn_skirt_id());
                }
            translate([0, 0, face_bottom])                            // centre post
                cylinder(h = btn_post_h(), d = btn_post_d);
        }
        // radial slits through skirt AND lip, so the skirt can collapse through the
        // bore. They stop short of the face, which stays a solid disc. Each cut runs
        // outward from the axis only, so btn_slits is the slit count, not half of it.
        for (i = [0 : btn_slits - 1])
            rotate([0, 0, i*360/btn_slits])
                translate([0, big/2, face_bottom + (lip_bottom - face_bottom)/2 + 0.1])
                    cube([btn_slit_w, big, lip_bottom - face_bottom + 0.4], center = true);
    }
}
