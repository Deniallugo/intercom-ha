// ===== Terrace VoiceS3R enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
// Acoustic liner allowance: extra interior space on every lined face (cavity
// depth + all four margins) so a self-adhesive foam / damping liner can be
// applied without crowding the drivers, boards or rear plate. The front baffle
// is the grille face and is NOT lined. Set to 0 for a bare shell.
sound_iso   = 5;
front_depth = 38 + sound_iso;  // inner depth: 38 clears the 35 mm driver, +sound_iso for the rear-plate liner
// (no separate rear_depth: the rear plate is a FLAT lid `wall` thick — the
//  corner M3 bosses are full-depth on the front shell and take the screws.)

// ---- speakers (2" full-range) ----
spk_od         = 53;       // driver face diameter (locating ring ID) — 2" driver
spk_cut        = 44;       // grille perforation field diameter
spk_gap        = 3;        // gap between the two drivers
spk_seat_depth = 4;        // height of the inner locating ring
spk_depth      = 35;       // driver depth front-to-back (sets front_depth clearance)

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1;   // groove outer diameter (just inside the locating ring)
gasket_id    = spk_cut + 1;  // groove inner diameter (just outside the grille field)
gasket_depth = 1.0;          // groove depth cut into the baffle inner face

// ---- speaker frame-hole screw bosses (fasten each driver flange) ----
spk_screw_n     = 4;       // mounting holes on the driver flange
spk_bolt_circle = 56;      // bolt-circle diameter; MUST clear the driver OD
spk_screw_pilot = 1.6;     // M2 self-tap pilot
spk_boss_od     = 5;       // mounting boss outer diameter
spk_boss_h      = spk_seat_depth + 1;  // boss height on the inner baffle
spk_screw_a0    = 45;      // start angle (deg); 45 dodges the center gap for n=4

// ---- margins / board zone ----
side_margin   = 7 + sound_iso;
top_margin    = 7 + sound_iso;
board_zone_h  = 30;
bottom_margin = 8 + sound_iso;

// ---- grille ----
grille_hole_d    = 3;
grille_ring_step = 6;      // radial spacing between hole rings

// ---- VoiceS3R module (24x24 footprint, button-forward) ----
mod_w   = 24;              // module footprint (square)
mod_d   = 17;              // module depth front-to-back inside the case
mod_clr = clr;
// USB-C plug body (the connector + boot, not just the socket): 10×10 mm
// cross-section, ~30 mm long. The long axis points -y (down) and the plug
// protrudes out the bottom of the case; the 10×10 cross-section is what every
// opening must pass.                                    [confirm vs hardware]
usb_conn_w   = 10;         // connector width  — across the case (x)
usb_conn_t   = 10;         // connector thickness — into the case (z)
usb_conn_len = 30;         // connector length (protrudes out the bottom; reference)
usb_clr      = 3;          // clearance around the connector in every opening
usb_z        = wall + mod_d/2;  // USB-C port center depth from the front face — centers the bottom hole [confirm vs hardware]
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
function outer_d()  = front_depth + wall;       // front shell + flat rear lid
function spk_cx()   = spk_od/2 + spk_gap/2;                          // 28
function spk_cy()   = outer_h()/2 - top_margin - spk_od/2;
function board_cy() = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()= 0;   // module centered horizontally; amps flank it left/right
function mic_x()    = cradle_cx();                  // centered on the module / button
function mic_y()    = board_cy() - mic_below_btn;   // just below the button
