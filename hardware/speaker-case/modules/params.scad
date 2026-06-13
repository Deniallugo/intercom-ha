// ===== Speaker case — combined device — parameters =====
// No geometry here. AIYIMA 2"/53 mm full-range, 4 ohm (TWO identical drivers in
// one sealed upper chamber). Below them, a vented electronics bay houses the
// terrace stack: VoiceS3R module + 2x MAX98357A amps + PTT button + mic + USB-C.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // clearance for inserted parts

// ---- shell ----
wall   = 4;                // walls + lid + divider thickness (rigid, airtight target)
radius = 8;                // rounded vertical edges (diffraction win at this size)

// ---- drivers (measured in-hand; confirm vs your units) ----
spk_od    = 53;            // frame OD — the locating ring ID
spk_cut   = 46;            // OPEN cone cutout through the baffle (cone fires through)
spk_gap   = 20;            // gap between the two driver frame edges
spk_depth = 28;            // seated depth front->back
seat_wall = 1.6;           // locating ring wall thickness
spk_seat_depth = 4;        // locating ring height on the inner baffle

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1; // groove OD: just inside the locating ring
gasket_id    = spk_cut + 1;// groove ID: just outside the open cutout
gasket_depth = 1.0;        // depth cut into the baffle inner face

// ---- driver mounting screws: 4 on a 43 mm SQUARE (60 mm diagonal) ----
spk_screw_square = 43;     // hole-to-hole along a side of the square
spk_screw_pilot  = 1.6;    // M2 self-tap pilot
spk_boss_od      = 5;
spk_boss_h       = spk_seat_depth + 1;

// ---- horizontal layout ----
side_margin = 10;          // wall-to-driver, left/right interior

// ---- vertical stack: speaker zone (top) | divider | board zone (bottom) ----
spk_zone_h   = 62;         // interior height of the sealed speaker chamber
divider_t    = wall;       // sealing slab between chamber and electronics bay
board_zone_h = 32;         // interior height of the vented electronics bay

// ---- chamber depth (sets the sealed volume; also the box interior depth) ----
cavity_depth = 62;         // clear air behind the cones
front_depth  = wall + cavity_depth;   // front-shell extrude = front wall + cavity

// ---- net-volume target (acoustic floor) ----
driver_disp = 25000;       // mm^3 displaced by each driver basket (measured estimate)
vol_target  = 450000;      // mm^3 net floor (~0.45 L); the board zone trims the chamber

// ---- divider sealed wire pass (4 speaker conductors up to the drivers) ----
divider_wire_d = 8;        // grommet bore through the divider
divider_wire_z = wall + 10;// hole center depth from the front face

// ---- wall mount: BLIND keyhole bosses on the lid OUTER face (chamber stays sealed) ----
keyhole_spacing = 100;
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;
kb_h            = 4;       // keyhole boss height (proud of lid; also screw-head depth)
kb_pad          = 3.5;     // material around the keyhole in the boss
function key_cy() = 25;    // keyhole height on the lid (in the speaker-zone region, near top)

// ---- rear-plate perimeter gasket groove (seals the lid) ----
lid_gasket_inset = wall + 3;   // groove centerline inset from the outer edge
lid_gasket_w     = 2.0;        // groove width
lid_gasket_depth = 1.0;        // groove depth into the lid inner face

// ---- corner screws (M3) fastening the rear plate ----
boss_od     = 7;
screw_pilot = 2.6;             // self-tap pilot in the front bosses
screw_clear = 3.4;             // clearance hole in the rear plate
boss_inset  = radius + 3;      // corner inset for the 4 screw bosses

// ---- VoiceS3R module (24x24 footprint, button-forward) ----
mod_w       = 24;          // module footprint (square)
mod_d       = 17;          // module depth front-to-back inside the case
mod_clr     = clr;
cradle_wall = 1.6;

// ---- USB-C bottom exit (power/data; the device's external connection) ----
usb_conn_w   = 10;         // connector width — across the case (x)
usb_conn_t   = 10;         // connector thickness — into the case (z)
usb_conn_len = 30;         // connector length (protrudes out the bottom; reference)
usb_clr      = 3;          // clearance around the connector in every opening
usb_z        = wall + mod_d/2;  // USB-C port center depth from the front face [confirm vs hardware]

// ---- button ----
btn_well_d = 12.5;         // well bore (cap skirt rides in this)
btn_cap_d  = 12;           // cap face diameter (slightly proud)
btn_proud  = 3.0;          // how far the cap face stands proud of the front surface
btn_slice  = 1.5;          // flat on the -y bottom of the cap (orientation mark + glue gap)
btn_travel = 2;
btn_nub_d  = 4;            // nub that contacts the module switch
btn_above_center = 3.8;    // contact nub sits this far above the module center (toward the
                           // top switch); cap face stays centered, nub stays under the skirt

// ---- microphone (perforation under the button, over the module's mic) ----
mic_below_btn = 8;         // cluster center, this far below the MODULE center
mic_hole_d    = 1.5;
mic_ring_r    = 2.6;
mic_ring_n    = 6;

// ---- amp boards (MAX98357A breakout, generic clone) ----
amp_w = 18;
amp_l = 16;
amp_standoff_h = 3;
amp_standoff_od = 4.5;
amp_screw_pilot = 1.6;

// ---- module retention clamp (collar on the rear lid, presses the module) ----
mod_clamp         = true;
mod_clamp_wall    = 2.0;
mod_clamp_foot    = mod_w - 0.5;   // collar OUTER footprint (lands on the module rim)
mod_clamp_squeeze = 0.3;           // overshoot => light preload (no rattle)
function mod_clamp_h() = front_depth - (wall + mod_d) + mod_clamp_squeeze;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()   = spk_od*2 + spk_gap + side_margin*2;                  // 146
function outer_h()   = 2*wall + spk_zone_h + divider_t + board_zone_h;      // 106
function outer_d()   = front_depth + wall;                                  // front shell + flat lid
function spk_cx()    = spk_od/2 + spk_gap/2;                                // 36.5
function spk_cy()    = (outer_h()/2 - wall) - spk_zone_h/2;                 // 18  (speaker zone center)
function divider_cy()= (outer_h()/2 - wall) - spk_zone_h - divider_t/2;     // -15 (divider center)
function board_cy()  = -outer_h()/2 + wall + board_zone_h/2;                // -33 (board zone center)
function cradle_cx() = 0;                                                   // module centered; amps flank it
function mic_x()     = cradle_cx();
function mic_y()     = board_cy() - mic_below_btn;                          // below the module center
function amp_off()   = (mod_w + 2*mod_clr)/2 + cradle_wall + 6 + amp_w/2;   // amp center from module center
function gross_vol() = (outer_w()-2*wall) * spk_zone_h * cavity_depth;      // speaker chamber only
function net_vol()   = gross_vol() - 2*driver_disp;
