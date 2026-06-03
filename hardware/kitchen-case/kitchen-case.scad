// ===== Kitchen Atom Echo enclosure — render entry point =====
// Render a single part:  openscad -D 'part="front"' -o out.stl kitchen-case.scad
// Parts: "front" | "rear" | "button" | "coupon" | "all" (assembled preview)
// NOTE: use a normal variable `part` (overridable by -D), NOT a special
// $-variable — OpenSCAD's -D does not reliably set $-prefixed variables.
include <modules/params.scad>
include <modules/lib.scad>
include <modules/front_shell.scad>
include <modules/rear_plate.scad>
include <modules/button_cap.scad>

part = "all";   // override on the CLI: -D 'part="front"'

if (part == "front")       front_shell();
else if (part == "rear")   rear_plate();
else if (part == "button") button_cap();
else if (part == "coupon") coupon_render();
else {  // assembled preview
    front_shell();
    color("gray")  translate([0, 0, front_depth]) rear_plate();
    color("red")   translate([cradle_cx(), board_cy(), -3]) button_cap();
}
