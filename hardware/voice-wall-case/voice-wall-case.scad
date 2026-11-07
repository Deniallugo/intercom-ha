// ===== Voice S3 wall unit — render entry point =====
// openscad -D 'part="amp-shell"' -o out.stl voice-wall-case.scad
// Parts (each in its print orientation):
//   amp-shell  amp-lid  amp-sled            amplifier box
//   voice-shell voice-lid voice-tray sleeve  Voice S3 box
//   plunger dome holder clamp               button + mic
//   plate lock                              wall plate + anti-lift bracket
//   coupon-amp coupon-voice                 front-wall fit slices (~20 min each)
//   as (default)  exploded  section         previews, world frame — F5 only; a full CGAL
//                                           render (F6) of the whole assembly is slow and trips
//                                           "mesh not closed" in 2021.01. Every printed part exports clean.
include <modules/params.scad>
include <modules/lib.scad>
include <modules/amp_box.scad>
include <modules/voice_box.scad>
include <modules/button.scad>
include <modules/wall_plate.scad>

part = "as";
section_x = sleeve_x;   // "section" cuts here; everything at larger x is removed

// Box-local -> world. rotate([90,0,0]) sends local y (up) to world z and local z (into the box)
// to world -y, so the front face lands at y = front_y() and the lid's legs end on the plate.
module place_box(z0) { translate([0, front_y(), z0]) rotate([90, 0, 0]) children(); }
module place_plate() { mirror([0, 1, 0]) rotate([90, 0, 0]) children(); }
// sled / tray: lie flat for printing
module flat(t) { rotate([90, 0, 0]) translate([0, -wall, 0]) children(); }

module voice_front_parts() {
    color("crimson")  translate([btn_pos[0], btn_pos[1], btn_dome_base_z()]) mirror([0, 0, 1]) dome();
    color("silver")   translate([btn_pos[0], btn_pos[1], btn_flange_top_z()]) plunger();
    color("seagreen") translate([btn_pos[0], btn_pos[1], bh_z1()]) rotate([180, 0, 0]) button_holder();
    color("orange")   multmatrix(top_face_m(voice_h)) translate([mic_pos[0], mic_pos[1], wall + mic_post_h + mic_clamp_t]) rotate([180, 0, 0]) mic_clamp();
}

module assembly(e = 0) {   // e: explode distance
    color("dimgray") place_plate() wall_plate();
    color("dimgray") translate([0, 0, plate_h() + e]) lock_bracket();
    place_box(0) translate([0, 0, -e]) {
        color("gainsboro") amp_shell();
        color("slategray") translate([0, 0, box_d() + e]) amp_lid();
        color("tan") translate([0, -e/2, 0]) amp_sled();
    }
    place_box(voice_z0() + e) translate([0, 0, -e]) {
        color("whitesmoke") voice_shell();
        color("slategray") translate([0, 0, box_d() + e]) voice_lid();
        color("tan") translate([0, -e/4, 0]) voice_tray();
        color("gold") translate([sleeve_x, tray_top() + 1.6, sleeve_zc()]) rotate([90, 0, 0]) sleeve();
        translate([0, 0, -e/2]) voice_front_parts();
    }
}

module coupon(h, depth) {
    intersection() {
        children();
        translate([-box_w, -1, -1]) cube([2*box_w, h + 2, depth + 1]);
    }
}

if      (part == "amp-shell")   amp_shell();
else if (part == "amp-lid")     amp_lid();
else if (part == "amp-sled")    flat() amp_sled();
else if (part == "voice-shell") voice_shell();
else if (part == "voice-lid")   voice_lid();
else if (part == "voice-tray")  flat() voice_tray();
else if (part == "sleeve")      sleeve();
else if (part == "plunger")     plunger();
else if (part == "dome")        dome();
else if (part == "holder")      button_holder();
else if (part == "clamp")       mic_clamp();
else if (part == "plate")       wall_plate();
else if (part == "lock")        lock_bracket();
else if (part == "coupon-amp")  coupon(amp_h(), wall + 3) amp_shell();
else if (part == "coupon-voice") intersection() {   // front wall (button) + top wall over the mic
                                    voice_shell();
                                    union() {
                                        translate([-box_w, -1, -1]) cube([2*box_w, voice_h + 2, wall + 3]);
                                        translate([-box_w, voice_h - wall - mic_post_h - 1, -1])
                                            cube([2*box_w, wall + mic_post_h + 2, mic_pos[1] + mic_size()[1]/2 + 3]);
                                    }
                                }
else if (part == "exploded")    assembly(40);
else if (part == "section")     difference() {   // cut on the sleeve axis, looking from +x
                                    assembly(0);
                                    translate([section_x, -1, -50]) cube([200, 400, 400]);
                                }
else                            assembly(0);
