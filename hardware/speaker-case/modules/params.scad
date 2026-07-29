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
// The chamber height is set by the driver's SEAT RING OD (94.2), not by volume:
// 97 leaves 1.4 mm of ring clearance top and bottom and still nets 1.5 L, above
// the vol_target floor. The 6 mm freed vs. the old 103 goes to the bay, which
// needs the height for a real PTT nut pocket (see btn_* below).
spk_zone_h   = 97;         // sealed chamber interior height (ring-limited, not volume-limited)
divider_t    = wall;
board_zone_h = 56;         // vented electronics-bay height (boards + PTT nut pocket)

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
s3_pos   = [0,   10];              // relative to board_cy(): +y toward divider. Rides high so
                                   // the bottom strip stays free for the PTT nut pocket.
dac_pos  = [-58, 8];
buck_pos = [58,  8];
trig_pos = [50, -18];              // low: puts its USB-C receptacle 2.5 mm off the bay floor
mic_pos  = [-50, -15];             // mic board, front baffle, away from the PTT bore
tpa_pos  = [0,   0];               // on the rear lid, centered in the bay
btn_pos  = [0,  -16];              // PTT switch center: bottom-CENTER of the front baffle, in the
                                   // free strip between the S3 pocket and the bay floor (~2 mm each side)

// ---- USB-C power IN (CH224K receptacle at the bottom edge) ----
usb_conn_w   = 10;
usb_conn_t   = 10;
usb_clr      = 3;
usb_z        = wall + 8;           // receptacle center depth from the front face [confirm]

// ---- PTT panel-mount momentary switch (front baffle) [confirm vs hardware] ----
// Sized for a 12 mm (M12x1) panel-mount MOMENTARY switch. One geometry serves
// both mount styles: the baffle is locally THINNED to btn_panel_t behind the
// bore (short-thread switches are rated for 1-3 mm panels, not our 4 mm wall),
// and the counterbore behind it is either the NUT SEAT (metal anti-vandal
// switch: bezel in front, nut behind) or the body-shoulder relief (plastic
// switch: body behind, nut in front). Both clamp on flats, so the counterbore
// floor and the outer face are left flat — no boss, no rib, nothing to rock on.
btn_thread_d  = 12;                // switch thread nominal
btn_bore_d    = btn_thread_d + 0.4;// thread bore (12.4)
btn_panel_t   = 2.5;               // local baffle thickness at the bore
btn_nut_af    = 16.5;              // switch nut across flats
btn_pocket_d  = 20;                // counterbore: clears the nut across corners + running clearance
btn_lead_in   = 0.4;               // outer-face chamfer so the bezel/nut can't ride the bore edge
btn_body_l    = 30;                // switch length behind the panel incl. terminals
// tactile/visual halo ring on the OUTER face so the PTT is findable by touch
btn_halo_id    = 21;               // >= btn_pocket_d: never thins the panel over the counterbore
btn_halo_od    = 24;
btn_halo_depth = 0.6;

// ---- microphone (ICS-43434 board + front perforation) ----
mic_board_w  = 17; mic_board_l = 14;
mic_hole_d   = 1.5;
mic_ring_r   = 2.6;
mic_ring_n   = 6;

// ---- wall mount: BLIND recessed keyhole bosses on the lid OUTER face ----
// Raised bosses hold a wall-side retaining plate (kb_lip) with a keyhole cut,
// backed by a head-clearance cavity floored by the SOLID lid panel. The head
// enters the circle, the box drops, the shank rides up the slot and the head is
// trapped behind the plate lip. Panel never breaches -> chamber stays sealed.
keyhole_spacing = 120;             // wider for the bigger/heavier box
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;
kb_h            = 6;               // boss height: retaining plate + head cavity
kb_pad          = 5;               // boss wall around the widened head cavity
kb_lip          = 1.4;            // wall-side retaining plate thickness (traps the head)
kb_clr          = 0.6;            // head sliding clearance inside the cavity
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
function btn_nut_ac() = btn_nut_af * 2/sqrt(3);                            // nut across corners (~19.05)
