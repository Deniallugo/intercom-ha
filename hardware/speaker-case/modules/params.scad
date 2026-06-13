// ===== Speaker case — sound-first PR-loaded device — parameters =====
// No geometry here. ONE Dayton PS95-8 3.5" full-range on the front baffle, a
// side-mounted passive radiator, and a vented electronics bay holding the stack:
// ESP32-S3 devkit + PCM5102A DAC + TPA3116 mono amp + MP1584 buck + CH224K PD
// trigger + ICS-43434 mic + PTT switch + USB-C power in.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // clearance for inserted parts

// ---- shell ----
wall   = 4;                // walls + lid + divider thickness (airtight chamber)
radius = 8;                // rounded vertical edges (baffle diffraction)
inner_w = 150;             // interior width set directly -> outer_w 158

// ---- driver: Dayton PS95-8 (single, centered) [confirm vs hardware] ----
spk_od    = 91;            // frame OD — locating-ring ID
spk_cut   = 76;            // OPEN cone cutout through the baffle
spk_depth = 45;            // seated depth front->back [confirm]
seat_wall = 1.6;           // locating-ring wall
spk_seat_depth = 4;        // locating-ring height on the inner baffle
spk_bolt_circle = 83;      // 4 screws on an 83 mm bolt CIRCLE [confirm]
spk_screw_n     = 4;
spk_screw_pilot = 1.6;     // M2 self-tap
spk_boss_od     = 5;
spk_boss_h      = spk_seat_depth + 1;

// ---- driver gasket groove ----
gasket_od    = spk_od - 1;
gasket_id    = spk_cut + 1;
gasket_depth = 1.0;

// ---- passive radiator (side panel, +x) [confirm vs hardware] ----
pr_od    = 80;             // PR frame OD
pr_cut   = 66;             // PR moving-mass cutout through the side wall
pr_depth = 25;            // PR intrusion into the chamber
pr_seat_wall   = 1.6;
pr_seat_depth  = 4;
pr_bolt_circle = 72;       // 4 screws on a bolt circle [confirm]
pr_screw_n     = 4;
pr_screw_pilot = 1.6;
pr_boss_od     = 5;
pr_boss_h      = pr_seat_depth + 1;
pr_gasket_od   = pr_od - 1;
pr_gasket_id   = pr_cut + 1;
pr_gasket_depth = 1.0;

// ---- vertical stack: speaker zone (top) | divider | board zone (bottom) ----
spk_zone_h   = 103;        // sealed chamber interior height (fits the 91 mm driver)
divider_t    = wall;
board_zone_h = 44;         // vented electronics-bay height

// ---- chamber depth (sets the sealed volume + front-to-back board room) ----
cavity_depth = 110;
front_depth  = wall + cavity_depth;   // front wall + cavity = 114

// ---- net-volume target (acoustic floor) ----
driver_disp = 60000;       // mm^3 displaced by the PS95 basket [confirm]
pr_disp     = 40000;       // mm^3 displaced by the PR assembly [confirm]
vol_target  = 1400000;     // 1.4 L net floor

// ---- divider single sealed wire pass (driver pair: 2 conductors) ----
divider_wire_d = 6;
divider_wire_z = wall + 12;

// ---- electronics-bay boards (footprints, [confirm vs hardware]) ----
// Each board placed by (x,y) center on a mounting plane. front-baffle boards
// stand on standoffs/pockets off the front wall (+z); the TPA mounts on the rear
// lid inner face (handled in rear_plate). The *_pos placement vectors below are
// (x,y) offsets relative to board_cy() (the board-zone center), not box center.
s3_w   = 69; s3_l   = 26;          // ESP32-S3-DevKitC-1
dac_w  = 27; dac_l  = 27;          // GY-PCM5102
buck_w = 22; buck_l = 17;          // MP1584
trig_w = 25; trig_l = 15;          // CH224K
tpa_w  = 50; tpa_l  = 30;          // TPA3116 mono (mounts on the rear lid)
board_standoff_h  = 3;
board_standoff_od = 4.5;
board_screw_pilot = 1.6;           // M2 self-tap
pocket_wall = 1.6;                 // friction-pocket wall (boards without holes)

// board placements (x,y centers) — tuned to satisfy the no-overlap asserts
s3_pos   = [0,   8];               // relative to board_cy(): +y toward divider
dac_pos  = [-58, 8];
buck_pos = [58,  8];
trig_pos = [50, -12];              // low, by the USB-C exit
mic_pos  = [-50, -12];             // mic board, front baffle, away from button
tpa_pos  = [0,   0];               // on the rear lid, centered in the bay

// ---- USB-C power IN (CH224K receptacle at the bottom edge) ----
usb_conn_w   = 10;
usb_conn_t   = 10;
usb_clr      = 3;
usb_z        = wall + 8;           // receptacle center depth from the front face [confirm]

// ---- PTT panel-mount momentary switch (front bore) [confirm vs hardware] ----
btn_bore_d   = 12.2;               // 12 mm panel-mount thread + clearance
btn_nut_d    = 14;                 // wrench-flat clearance behind the panel

// ---- microphone (ICS-43434 board + front perforation) ----
mic_board_w  = 17; mic_board_l = 14;
mic_hole_d   = 1.5;
mic_ring_r   = 2.6;
mic_ring_n   = 6;

// ---- wall mount: BLIND keyhole bosses on the lid OUTER face ----
keyhole_spacing = 120;             // wider for the bigger/heavier box
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;
kb_h            = 4;
kb_pad          = 3.5;
function key_cy() = 30;            // keyhole height on the lid (upper, chamber region)

// ---- rear-plate perimeter gasket groove ----
lid_gasket_inset = wall + 3;
lid_gasket_w     = 2.0;
lid_gasket_depth = 1.0;

// ---- corner screws (M3) fastening the rear plate ----
boss_od     = 7;
screw_pilot = 2.6;
screw_clear = 3.4;
boss_inset  = radius + 3;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()    = inner_w + 2*wall;                                  // 158
function outer_h()    = 2*wall + spk_zone_h + divider_t + board_zone_h;    // 159
function outer_d()    = front_depth + wall;                                // 118
function spk_cx()     = 0;                                                 // driver centered
function spk_cy()     = (outer_h()/2 - wall) - spk_zone_h/2;               // speaker-zone center
function divider_cy() = (outer_h()/2 - wall) - spk_zone_h - divider_t/2;   // divider center
function board_cy()   = -outer_h()/2 + wall + board_zone_h/2;              // board-zone center
function side_x()     = outer_w()/2 - wall;                                // inner face of the +x side wall
function pr_cz()      = wall + cavity_depth/2;                             // PR center depth
function gross_vol()  = (outer_w()-2*wall) * spk_zone_h * cavity_depth;    // chamber only
function net_vol()    = gross_vol() - driver_disp - pr_disp;
