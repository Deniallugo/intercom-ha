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

part = "as";   // override on the CLI: -D 'part="shell"'

// Fit-test coupon: the button bore + pilots and the mic seat cut out of the real top
// face, plus the three small parts that mate with them. Ten minutes of printing tells
// you whether the snap, the travel and the mic gasket land before you commit four
// hours to the shell. With the mechanism now in `holder`, this is also the cheapest
// way to iterate it — reprint the coupon and the holder, never the shell.
// The slice is DERIVED from the two features it has to contain, not typed in: it used to
// be a hard-coded 62 x 64 cube sized for a 96 mm plan, which quietly starts hanging off
// the part the moment `plan` changes. It spans the button holder's footprint and reaches
// forward past the mic posts, clamped to the case so it cannot run off the edge.
function coupon_w()  = min(2*(max(abs(btn_pos[0]) + bh_plate_w()/2,
                                  abs(mic_pos[0]) + mic_size()[0]/2) + 4), 2*flat_half_x());
function coupon_y0() = max(btn_pos[1] - bh_plate_l()/2 - 4, -flat_half_y());
function coupon_y1() = min(mic_pos[1] + mic_size()[1]/2 + 3, inner_half_y());
module coupon() {
    intersection() {
        shell();
        translate([-coupon_w()/2, coupon_y0(), -6])
            cube([coupon_w(), coupon_y1() - coupon_y0(), wall + 8]);
    }
    // the three mating parts, laid out clear of the slice
    translate([0, coupon_y0() - 20, 0]) button_cap();
    translate([coupon_w()/2 + 24, coupon_y0() - 6, 0]) button_holder();
    translate([-coupon_w()/2 - 16, coupon_y0() - 14, 0]) mic_clamp();
}

// Fit coupon for the DEVKIT BED — the WHOLE bed, end to end, not a slice of it.
//
// It started as a 25 mm slice off the front, which was enough while the only questions were
// "is the pocket the right width" and "does the tab catch". Adding the rear stops made that
// useless: the board no longer slides in, it goes in TILTED, and a slice cannot tell you
// whether that works because the two features you are tilting between are 65 mm apart. What
// you need to rehearse is the real motion — front edge under the tab, rear corners dropping
// behind the stops — and for that the coupon has to be the whole bed.
//
// It is still much cheaper than the thing it saves you from: a plate is four hours, this is
// well under one, and the plate is the part you cannot iterate.
//
// The x span is the pocket EXACTLY, with no skirt. Not laziness — the vent slots either side
// run within half a millimetre of the pocket walls, so any skirt at all would slice a channel
// down the coupon's own edges and leave it flexing where it has to be stiff. In y it takes a
// small skirt, because there the nearest thing outboard is plate.
// ...and it is shaved to `s3_fit_base` of plate rather than the real `wall`. Taking the whole
// bed instead of a slice quadrupled this part, to half the volume of the plate it is meant to
// save — at which point you may as well print the plate. But none of that plate thickness is
// under test: the bed is everything above the inner face, and 1.2 mm plus the pocket's own
// 3.5 mm floor is more than stiff enough to push a board into. Nothing is lost because there
// are no vents or counterbores inside the bed's x span to cut through.
s3_fit_skirt = 2;          // plate left beyond the bed, y only
s3_fit_base  = 1.2;        // plate thickness kept under it — the bed is what is on test
module fit_coupon() {
    zlo = -4*outer_d();
    intersection() {
        base_plate();
        translate([s3_pos_x, 0, (zlo + s3_fit_base)/2])
            cube([s3_pocket_f()[0],
                  2*(lip_outer_half_y() + s3_fit_skirt),
                  s3_fit_base - zlo], center = true);
    }
}

if (part == "shell")       shell();
else if (part == "fit")    fit_coupon();
else if (part == "base")   base_plate();
else if (part == "button") button_cap();
else if (part == "holder") button_holder();
else if (part == "clamp")  mic_clamp();
else if (part == "coupon") coupon();
else {  // assembled preview
    shell();
    color("gray")   translate([0, 0, top_depth()]) base_plate();
    color("red")    translate([btn_pos[0], btn_pos[1], -btn_proud()]) button_cap();
    // the holder is the one part drawn against the case's z, so it flips into place
    color("green")  translate([btn_pos[0], btn_pos[1], bh_z1()])
                        rotate([180, 0, 0]) button_holder();
    // clamp flipped over onto the mic posts: its pad points back at the top face
    color("orange") translate([mic_pos[0], mic_pos[1], wall + mic_post_h])
                        rotate([180, 0, 0]) mic_clamp();
}
