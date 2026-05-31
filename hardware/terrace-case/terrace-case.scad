// ===== Terrace VoiceS3R enclosure — render entry point =====
// Render a single part:  openscad -D '$part="front"' -o out.stl terrace-case.scad
// Parts: "front" | "rear" | "button" | "coupon" | "all" (assembled preview)
include <modules/params.scad>
include <modules/lib.scad>
include <modules/front_shell.scad>
include <modules/rear_plate.scad>
include <modules/button_cap.scad>

part = is_undef($part) ? "all" : $part;

if (part == "front")       front_shell();
else if (part == "rear")   rear_plate();
else if (part == "button") button_cap();
else if (part == "coupon") coupon_render();
else {  // assembled preview
    front_shell();
    color("gray")  translate([0, 0, front_depth]) rear_plate();
    color("red")   translate([cradle_cx(), board_cy(), -3]) button_cap();
}
