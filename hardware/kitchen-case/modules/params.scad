// ===== Kitchen Atom Echo enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
front_depth = 26;          // inner depth of the front shell — clears the 20 mm-deep drivers (min = spk_depth; extra clears wiring)
rear_depth  = 12;          // depth of the rear plate body

// ---- speakers (two 4 cm full-range, side by side, driven by one amp) ----
spk_od         = 40;       // driver locating-ring dia (cone+surround drops into the ring) [confirm vs hardware]
spk_cut        = 33;       // grille perforation field diameter                            [confirm vs hardware]
spk_gap        = 3;        // gap between the two drivers
spk_seat_depth = 4;        // height of the inner locating ring
spk_depth      = 20;       // driver depth front-to-back (2 cm) — sets front_depth clearance

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1;   // groove outer diameter (just inside the locating ring)
gasket_id    = spk_cut + 1;  // groove inner diameter (just outside the grille field)
gasket_depth = 1.0;          // groove depth cut into the baffle inner face

// ---- speaker mounting (friction/glue) ----
// The 4 cm drivers are held by the locating ring + gasket + a dab of glue/foam
// (no flange screws). spk_screw_n = 0 disables the per-driver bolt-circle bosses
// — in this tight envelope the diagonal top-outer bosses collided with the
// corner M3 lid bosses. To re-enable driver screws, set spk_screw_n > 0 AND
// enlarge the shell until tests/asserts.scad passes (it guards this collision).
spk_screw_n     = 0;       // 0 = friction/glue mount (no driver screws)
spk_bolt_circle = 46;      // bolt-circle diameter; MUST clear the driver OD [confirm vs hardware]
spk_screw_pilot = 1.6;     // M2 self-tap pilot (only used when spk_screw_n > 0)
spk_boss_od     = 5;       // mounting boss outer diameter
spk_boss_h      = spk_seat_depth + 1;  // boss height on the inner baffle
spk_screw_a0    = 45;      // start angle (deg); 45 dodges the center gap for n=4

// ---- margins / board zone ----
side_margin   = 6;
top_margin    = 7;
board_zone_h  = 30;
bottom_margin = 8;

// ---- grille ----
grille_hole_d    = 3;
grille_ring_step = 6;      // radial spacing between hole rings

// ---- Atom Echo module (24x24 footprint, top-face forward) ----
mod_w   = 24;              // module footprint (square)            [confirm vs hardware]
mod_d   = 17;              // module depth front-to-back in the case [confirm vs hardware]
mod_clr = clr;
mod_usb_w = 10;            // USB-C connector width                [confirm position vs hardware]
mod_usb_h = 4;             // USB-C connector height
usb_floor_clr = 4;         // extra width on the bottom-of-case USB exit, for the cable
cradle_wall = 1.6;

// ---- button ----
btn_well_d = 12.5;         // well bore (cap skirt rides in this)
btn_cap_d  = 12;           // cap face diameter (slightly proud)
btn_travel = 2;
btn_nub_d  = 4;            // nub that contacts the module switch

// ---- microphone (perforation under the button, over the module's mic) ----
mic_below_btn = 8;         // cluster center, this far below the button center
mic_hole_d    = 1.5;       // perforation hole diameter
mic_ring_r    = 2.6;       // radius of the surrounding ring of holes
mic_ring_n    = 6;         // holes in the ring (plus one in the center)

// ---- amp board (one MAX98357A breakout, right of the module) ----
amp_w = 18;
amp_l = 16;
amp_gap = 4;               // gap between the cradle wall and the amp board
amp_standoff_h = 3;
amp_standoff_od = 4.5;     // post OD (wide enough to take a pilot)
amp_screw_pilot = 1.6;     // M2 self-tap pilot in each amp standoff

// ---- wall mount ----
keyhole_spacing = 70;      // scaled to the two-driver footprint
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;

// ---- screws (M3) ----
boss_od     = 7;
screw_pilot = 2.6;         // self-tap pilot in the front bosses
screw_clear = 3.4;         // clearance hole in the rear plate
boss_inset  = radius + 2;  // corner inset for the 4 screw bosses

// ---- derived dimensions (functions so tests can assert them) ----
function amp_cx()      = (mod_w + 2*mod_clr)/2 + cradle_wall + amp_gap + amp_w/2; // amp center x (right of module)
function board_reach() = amp_cx() + amp_w/2;                  // right-most board extent from center
function outer_w()     = max(spk_od*2 + spk_gap, 2*board_reach()) + side_margin*2; // wider of the driver pair or the board row
function outer_h()     = top_margin + spk_od + board_zone_h + bottom_margin;
function outer_d()     = front_depth + rear_depth;
function spk_cx()      = spk_od/2 + spk_gap/2;                // half-pitch: drivers sit at ±spk_cx()
function spk_cy()      = outer_h()/2 - top_margin - spk_od/2;
function board_cy()    = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()   = 0;                                   // module centered; amp to the right
function mic_x()       = cradle_cx();                         // centered on the module / button
function mic_y()       = board_cy() - mic_below_btn;          // just below the button
