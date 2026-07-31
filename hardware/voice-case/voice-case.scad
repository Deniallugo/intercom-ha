// ===== Voice S3 desk puck — render entry point =====
// Render a single part:  openscad -D 'part="shell"' -o out.stl voice-case.scad
// Parts: "shell" | "base" | "button" | "holder" | "clamp" | "coupon" | "all" (preview)
// NOTE: use a normal variable `part` (overridable by -D), NOT a special $-variable —
// OpenSCAD's -D does not reliably set $-prefixed variables.
include <modules/params.scad>
include <modules/lib.scad>
include <modules/shell.scad>
include <modules/base_plate.scad>
include <modules/button_cap.scad>
include <modules/button_holder.scad>
include <modules/mic_clamp.scad>

part = "all";   // override on the CLI: -D 'part="shell"'

// Fit-test coupon: the button bore + pilots and the mic seat cut out of the real top
// face, plus the three small parts that mate with them. Ten minutes of printing tells
// you whether the snap, the travel and the mic gasket land before you commit four
// hours to the shell. With the mechanism now in `holder`, this is also the cheapest
// way to iterate it — reprint the coupon and the holder, never the shell.
module coupon() {
    intersection() {
        shell();
        translate([-24, -22, -6]) cube([48, 62, wall + 8]);
    }
    translate([0, -36, 0]) button_cap();
    translate([26, -30, 0]) button_holder();
    translate([0, -48, 0]) mic_clamp();
}

if (part == "shell")       shell();
else if (part == "base")   base_plate();
else if (part == "button") button_cap();
else if (part == "holder") button_holder();
else if (part == "clamp")  mic_clamp();
else if (part == "coupon") coupon();
else {  // assembled preview
    shell();
    color("gray")   translate([0, 0, top_depth()]) base_plate();
    color("red")    translate([btn_pos[0], btn_pos[1], -btn_proud()]) button_cap();
    color("green")  translate([btn_pos[0], btn_pos[1], bh_z0()]) button_holder();
    // clamp flipped over onto the mic posts: its pad points back at the top face
    color("orange") translate([mic_pos[0], mic_pos[1], wall + mic_post_h])
                        rotate([180, 0, 0]) mic_clamp();
}
