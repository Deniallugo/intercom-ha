// ===== Kitchen Atom Echo enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
front_depth = 38;          // inner depth of the front shell — clears the 35 mm-deep driver
rear_depth  = 12;          // depth of the rear plate body

// ---- speaker (one 2" full-range, centered) ----
spk_od         = 53;       // driver face diameter (locating ring ID) — 2" driver
spk_cut        = 44;       // grille perforation field diameter
spk_seat_depth = 4;        // height of the inner locating ring
spk_depth      = 35;       // driver depth front-to-back (sets front_depth clearance)

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1;   // groove outer diameter (just inside the locating ring)
gasket_id    = spk_cut + 1;  // groove inner diameter (just outside the grille field)
gasket_depth = 1.0;          // groove depth cut into the baffle inner face

// ---- speaker frame-hole screw bosses (fasten the driver flange) ----
spk_screw_n     = 4;       // mounting holes on the driver flange
spk_bolt_circle = 56;      // bolt-circle diameter; MUST clear the driver OD
spk_screw_pilot = 1.6;     // M2 self-tap pilot
spk_boss_od     = 5;       // mounting boss outer diameter
spk_boss_h      = spk_seat_depth + 1;  // boss height on the inner baffle
spk_screw_a0    = 45;      // start angle (deg)

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
mod_usb_w = 10;            // USB-C cutout width                   [confirm position vs hardware]
mod_usb_h = 4;             // USB-C cutout height
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
keyhole_spacing = 60;      // narrower than terrace (single-driver footprint)
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
function outer_w()     = max(spk_od, 2*board_reach()) + side_margin*2;
function outer_h()     = top_margin + spk_od + board_zone_h + bottom_margin;
function outer_d()     = front_depth + rear_depth;
function spk_cx()      = 0;                                   // single driver, centered
function spk_cy()      = outer_h()/2 - top_margin - spk_od/2;
function board_cy()    = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()   = 0;                                   // module centered; amp to the right
function mic_x()       = cradle_cx();                         // centered on the module / button
function mic_y()       = board_cy() - mic_below_btn;          // just below the button
