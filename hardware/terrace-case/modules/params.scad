// ===== Terrace VoiceS3R enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
front_depth = 38;          // inner depth of the front shell — clears the 35 mm-deep driver
rear_depth  = 12;          // depth of the rear plate body

// ---- speakers (2" full-range) ----
spk_od         = 53;       // driver face diameter (locating ring ID) — 2" driver
spk_cut        = 44;       // grille perforation field diameter
spk_gap        = 3;        // gap between the two drivers
spk_seat_depth = 4;        // height of the inner locating ring
spk_depth      = 35;       // driver depth front-to-back (sets front_depth clearance)

// ---- speaker frame-hole screw bosses (fasten each driver flange) ----
spk_screw_n     = 4;       // mounting holes on the driver flange
spk_bolt_circle = 56;      // bolt-circle diameter; MUST clear the driver OD
spk_screw_pilot = 1.6;     // M2 self-tap pilot
spk_boss_od     = 5;       // mounting boss outer diameter
spk_boss_h      = spk_seat_depth + 1;  // boss height on the inner baffle
spk_screw_a0    = 45;      // start angle (deg); 45 dodges the center gap for n=4

// ---- margins / board zone ----
side_margin   = 7;
top_margin    = 7;
board_zone_h  = 30;
bottom_margin = 8;

// ---- grille ----
grille_hole_d    = 3;
grille_ring_step = 6;      // radial spacing between hole rings

// ---- VoiceS3R module (24x24 footprint, button-forward) ----
mod_w   = 24;              // module footprint (square)
mod_d   = 17;              // module depth front-to-back inside the case
mod_clr = clr;
mod_usb_w = 10;            // USB-C cutout width
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

// ---- amp boards (MAX98357A breakout, generic clone) ----
amp_w = 18;
amp_l = 16;
amp_standoff_h = 3;
amp_standoff_od = 4.5;     // post OD (wide enough to take a pilot)
amp_screw_pilot = 1.6;     // M2 self-tap pilot in each amp standoff

// ---- wall mount ----
keyhole_spacing = 90;
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;

// ---- screws (M3) ----
boss_od     = 7;
screw_pilot = 2.6;         // self-tap pilot in the front bosses
screw_clear = 3.4;         // clearance hole in the rear plate
boss_inset  = radius + 2;  // corner inset for the 4 screw bosses

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()  = spk_od*2 + spk_gap + side_margin*2;            // 123
function outer_h()  = top_margin + spk_od + board_zone_h + bottom_margin; // 98
function outer_d()  = front_depth + rear_depth;                      // 50
function spk_cx()   = spk_od/2 + spk_gap/2;                          // 28
function spk_cy()   = outer_h()/2 - top_margin - spk_od/2;
function board_cy() = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()= -outer_w()/2 + side_margin + cradle_wall + (mod_w+2*mod_clr)/2;
function mic_x()    = cradle_cx();                  // centered on the module / button
function mic_y()    = board_cy() - mic_below_btn;   // just below the button
