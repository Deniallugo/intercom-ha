// ===== Voice S3 desk puck — render entry point =====
// Render a single part:  openscad -D 'part="shell"' -o out.stl voice-case.scad
// Parts: "shell" | "base" | "button" | "coupon" | "all" (assembled preview)
// NOTE: use a normal variable `part` (overridable by -D), NOT a special $-variable —
// OpenSCAD's -D does not reliably set $-prefixed variables.
include <modules/params.scad>
include <modules/lib.scad>
include <modules/shell.scad>
include <modules/base_plate.scad>
include <modules/button_cap.scad>

part = "all";   // override on the CLI: -D 'part="shell"'

// Fit-test coupon: the button + switch-seat column and the mic seat cut out of the
// real top face, plus a cap to snap into it. Ten minutes of printing tells you
// whether the snap, the travel and the mic gasket land before you commit four hours
// to the shell.
module coupon() {
    intersection() {
        shell();
        translate([-24, -18, -6]) cube([48, 60, wall + sw_seat_h() + 4]);
    }
    translate([0, -34, 0]) button_cap();
}

if (part == "shell")       shell();
else if (part == "base")   base_plate();
else if (part == "button") button_cap();
else if (part == "coupon") coupon();
else {  // assembled preview
    shell();
    color("gray")  translate([0, 0, top_depth()]) base_plate();
    color("red")   translate([btn_pos[0], btn_pos[1], -btn_proud()]) button_cap();
}
