// ===== Speaker case — 53 mm vertical pair, ported — parameters =====
// No geometry here. TWO AIYIMA 53 mm full-range drivers STACKED VERTICALLY on the
// front baffle (dual mono, one amp channel each), a side-wall tuned port (~145 Hz),
// and a vented electronics bay holding: ESP32-S3 devkit + PCM5102A DAC + PAM8406
// 5 V amp + USB-C 5 V breakout + ICS-43434 mic + PTT switch + 3.5 mm sub line-out.
//
// Why this shape (see docs/superpowers/specs/2026-07-29-speaker-case-53mm-review.md):
//   * Fs 145 Hz / Vas ~0.2 L per driver => box volume barely matters. 0.7 L net is
//     past the knee; the old 1.6 L bought 18 Hz for 3x the plastic.
//   * VERTICAL pair, not side-by-side: comb filtering moves into the vertical plane
//     where nobody moves. Horizontal polar response stays clean.
//   * Narrow 86 mm baffle + a 6 mm front chamfer: real diffraction control, unlike
//     an 8 mm radius on a 158 mm baffle.
//   * Port tuned AT Fs, never below it. A resonator below Fs is the PR mistake.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // clearance for inserted parts

// ---- shell ----
wall    = 4;               // walls + lid + divider thickness (airtight chamber)
radius  = 10;              // rounded vertical edges
chamfer = 6;               // 45 deg front-edge chamfer (baffle diffraction; prints
                           // support-free back-down, unlike a true fillet)
inner_w = 78;              // interior width set directly -> outer_w 86

// ---- drivers: 2x AIYIMA 53 mm, stacked vertically [confirm vs hardware] ----
// Measured T/S (per driver, both identical): Fs ~145 Hz, Re ~3.4 ohm, Qts ~0.61,
// sensitivity ~83-84 dB. 4 ohm. Sd ~14.5 cm^2, Xmax ~1 mm [MEASURE].
spk_n     = 2;
spk_od    = 53;            // frame OD
spk_cut   = 46;            // OPEN cone cutout through the baffle
spk_depth = 28;            // seated depth front->back [confirm]
spk_pitch = 57;            // vertical centre-to-centre (tight: pushes the first
                           // off-axis null up to ~3 kHz at 90 deg)
// The published "4 x on a 43 mm square (60 mm diagonal)" is self-contradictory for a
// 53 mm frame: a 43 mm SQUARE puts screws at r=30.4 (outside the frame), a 43 mm
// bolt CIRCLE puts them at r=21.5 (inside the 46 mm cutout). The pattern must land
// between cut/2=23 and od/2=26.5. 49 mm is the typical value for this frame size.
spk_bolt_circle = 49;      // 4 screws, 45 deg offset [CONFIRM vs hardware]
spk_screw_n     = 4;
spk_screw_pilot = 1.6;     // M2 self-tap, BLIND into the baffle
spk_pilot_depth = 3.5;     // blind: recess + pilot must stay inside wall + spk_pad_t
// Local baffle pad on the INNER face behind each driver. Two jobs: it gives the blind
// pilots real material to bite (wall 4 + pad 2 - recess 1 = 5 mm, so a 3.5 mm pilot
// still leaves 1.5 mm of solid floor), and it stiffens the baffle exactly where the
// driver's reaction force is applied — the one place a printed box should be thick.
spk_pad_d = spk_od + 3;    // 56: clears the neighbour at pitch 57
spk_pad_t = 2;
// No raised bosses and no annular gasket groove: at r=24.5 a boss would overlap both
// the cutout and the frame edge, and a 53 mm frame leaves only a 3.5 mm annulus. A
// shallow full-circle recess locates the frame AND lands a punched foam ring.
spk_recess_d     = spk_od + 2*clr;
spk_recess_depth = 1.0;

// ---- tuned port (+x side wall, fires sideways) ----
// Fb ~145 Hz in 0.705 L. Lv = 23562.5*d^2/(Fb^2*Vb) - 0.732*d  (d cm, Vb litres).
// Printed as a SEPARATE PART so Fb is tunable by printing another length:
//   40 mm -> ~156 Hz | 49 mm -> ~145 Hz | 60 mm -> ~134 Hz | 75 mm -> ~122 Hz
// Tuning below ~130 Hz is pointless: that is under Fs, where the cones cannot drive
// the port. Port area 3.14 cm^2 >= 0.1*Sd_total; peak air velocity ~8.4 m/s at Xmax,
// well under the ~17 m/s chuffing threshold.
port_id        = 20;
port_wall      = 2;
port_len       = 49;       // acoustic length, outer face -> inner end
port_flange_od = 30;
port_flange_t  = 1.5;
port_cz        = 50;       // axis depth from the front face: clear behind the baskets

// ---- vertical stack: speaker zone (top) | divider | board zone (bottom) ----
// spk_zone_h is DRIVER-limited, not volume-limited: pitch 57 + recess 53.8 = 110.8
// plus clearance to the divider and the chamber top.
spk_zone_h   = 120;
divider_t    = wall;
// The bay height is set by the front-baffle feature stack, not by the boards: the
// S3 pocket (26 + 2*1.6 = 29.2), the PTT counterbore (20) and halo, the mic pocket
// (18), and the halo's clearance to the chamfered front face. At 62 the mic squeezed
// in with 0.4 mm to the corner-boss notch; 70 puts every margin at 1.4-7 mm.
// Costs 8 mm of height and nothing else — the chamber and Fb are untouched.
board_zone_h = 70;

// ---- chamber depth (sets the sealed volume + front-to-back board room) ----
cavity_depth = 80;
front_depth  = wall + cavity_depth;   // front wall + cavity = 84

// ---- net-volume target (acoustic floor) ----
driver_disp = 10000;       // mm^3 displaced by ONE 53 mm basket [confirm]
vol_target  = 650000;      // 0.65 L net floor

// ---- divider: sealed terminal bolts (NOT a wire pass) ----
// Dual mono on a BTL class-D amp means 4 independent conductors (the two channels'
// returns are not common). A silicone-smeared 6 mm hole is the leak that ruins Qtc in
// a 0.7 L box, so each conductor gets an M3 brass bolt with an O-ring under a washer.
// Solder each 330 uF series cap between the amp output and its bay-side terminal.
term_n            = 4;
term_d            = 3.4;   // M3 clearance
term_pitch        = 10;
term_cz           = 60;    // depth: behind the baskets, clear of the bay boards
term_oring_od     = 9;
term_oring_depth  = 1.0;

// ---- electronics-bay boards (footprints, [confirm vs hardware]) ----
// The 15 V PD tree is gone: a 53 mm 4 ohm driver wants 3-5 W, and TPA3116 on 15 V
// into 4 ohm delivers ~40 W. PAM8406 on plain 5 V gives 2x3 W and CLIPS BEFORE THE
// DRIVER DIES. That deletes CH224K + MP1584 + TPA3116 -> 5 boards down to 3.
s3_w   = 69; s3_l   = 26;          // ESP32-S3-DevKitC-1 (N16R8)  -- front wall
dac_w  = 27; dac_l  = 27;          // GY-PCM5102A                 -- rear lid
amp_w  = 24; amp_l  = 16;          // PAM8406 5 V stereo class-D  -- rear lid
// Power entry is a PANEL-MOUNT USB-C socket, not a breakout board. A flat breakout
// with its connector facing the side wall has to sit at x ~ -30 to reach it, which is
// exactly where a corner lid boss runs: the receptacle ended up 2.8 mm INSIDE the boss.
// A panel-mount socket lives in the boss-free window, anchors to the case rather than
// to a 15 mm PCB, and sends the cable straight down — the natural exit for a
// wall-mounted box. [confirm vs hardware: these vary a lot between modules]
usbc_cut_w      = 9.5;             // receptacle body through the wall (x)
usbc_cut_l      = 4.5;             // ... and in z
usbc_screw_pitch = 20;             // 2 x M2 blind pilots flanking
usbc_pilot_depth = 2.5;
usbc_body_h      = 10;             // how far the socket body reaches into the bay
board_standoff_h  = 3;
board_standoff_od = 4.5;
board_screw_pilot = 1.6;           // M2 self-tap
pocket_wall = 1.6;                 // friction-pocket wall (boards without holes)

// front-wall placements (x,y) relative to board_cy()
s3_pos  = [  0,  19];              // rides high; frees the bottom strip for PTT + mic
btn_pos = [  0, -19];              // PTT switch, bottom-centre
mic_pos = [-24,  -7];              // mic pocket, LEFT OF THE PTT on the front baffle —
                                   // you talk to the front of an intercom. Isolation
                                   // barely differs: the bay is at the bottom either
                                   // way, so this is ~80 mm from the lower driver vs
                                   // ~90 mm on the bottom wall. The gasket is what
                                   // actually decouples it.
// rear-lid inner-face placements (x,y) relative to board_cy()
dac_pos = [-20, 0];
amp_pos = [ 16, 0];
// bottom-wall placements — these are (x, z): z = depth from the front face
usbc_pos = [-12, 16];              // panel-mount socket; cable exits straight down
jack_pos = [ 18, 20];

// ---- S3 service slot (+x side wall, over the devkit's own USB-C ports) ----
// Exposes both devkit ports for the first flash and serial logs. Breaches the BAY
// only. Do NOT power the amp through them — see README.
s3_usb_w = 20;                     // along y (spans both ports)
s3_usb_h = 10;                     // along z
function s3_usb_z() = wall + board_standoff_h + 1.6 + 3;

// ---- 3.5 mm sub line-out (bottom wall) ----
// Fed from the PASSIVELY SUMMED L+R node (2 x 10k into a common point), the same node
// that feeds the amp. Summing in hardware means devices/speaker-s3.yaml needs no
// change at all — it stays `channel: stereo` — and both the drivers and the sub get a
// true mono mix rather than one arbitrary channel. A powered sub's own low-pass does
// the crossover. This is the ONLY route to output below ~120 Hz; see the review doc.
jack_bore_d = 6.2;
jack_nut_d  = 11;
jack_body_h = 12;                  // how far the jack barrel reaches into the bay

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

// ---- microphone (ICS-43434, front baffle, gasket-sealed single port) ----
// The old 7 x 1.5 mm cluster was a ~5.7 kHz Helmholtz resonator sitting on top of
// speech. ONE short hole with the mic port pressed onto a gasket (near-zero front
// volume) puts the resonance at ~14 kHz instead.
// A friction pocket, not flanking screw posts: posts at any workable pitch collided
// with either the PTT halo or the bay edge.
mic_board_w  = 17; mic_board_l = 14;
mic_gasket_d     = 12;             // gasket seat, recessed into the pocket floor
mic_gasket_depth = 0.8;            // < pocket_wall, so floor + wall still carry the port
mic_hole_d       = 2.0;            // single port: wall + pocket floor - gasket = 4.8 mm

// ---- wall mount: BLIND recessed keyhole bosses on the lid OUTER face ----
// Raised bosses hold a wall-side retaining plate (kb_lip) with a keyhole cut,
// backed by a head-clearance cavity floored by the SOLID lid panel. The head
// enters the circle, the box drops, the shank rides up the slot and the head is
// trapped behind the plate lip. Panel never breaches -> chamber stays sealed.
// VERTICAL pair, not side-by-side: 120 mm spacing cannot fit an 86 mm lid, and two
// vertically-spaced screws resist tip-out far better on a tall narrow box.
keyhole_ys      = [10, 60];        // lid y positions (both in the chamber region)
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;
kb_h            = 6;               // boss height: retaining plate + head cavity
kb_pad          = 5;               // boss wall around the widened head cavity
kb_lip          = 1.4;             // wall-side retaining plate thickness (traps the head)
kb_clr          = 0.6;             // head sliding clearance inside the cavity

// ---- rear-plate perimeter gasket groove ----
// Must land ON the shell rim. The rim is just the wall cross-section at the rear face:
// 0 to `wall` (4 mm) inboard of the outer edge. The old `wall + 3` = 7 mm put the
// groove centreline 3 mm INBOARD of the rim's inner face, i.e. hanging over the open
// cavity — the gasket compressed against nothing and the chamber never sealed.
// Centre it on the rim instead, and keep it well outboard of the corner bosses.
lid_gasket_inset = wall/2;         // 2 mm: groove spans 1-3 mm from the edge
lid_gasket_w     = 2.0;
lid_gasket_depth = 1.0;

// ---- corner screws (M3) fastening the rear plate ----
// M3 HEAT-SET INSERTS, not self-tap: this is the joint that gets opened repeatedly
// for wiring, board access and polyfill. The drivers keep self-tap pilots (opened
// once or twice — the port, not the driver, is the tuning element here).
boss_od      = 8;
insert_m3_d  = 4.0;                // heat-set insert bore
screw_clear  = 3.4;
boss_inset   = radius + 3;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()    = inner_w + 2*wall;                                  // 86
function outer_h()    = 2*wall + spk_zone_h + divider_t + board_zone_h;    // 202
function outer_d()    = front_depth + wall;                                // 88
function spk_cx()     = 0;                                                 // drivers centred
function spk_zone_cy()= (outer_h()/2 - wall) - spk_zone_h/2;               // chamber centre
// driver i (0 = lower, 1 = upper) centre height
function spk_cy(i)    = spk_zone_cy() + (i - (spk_n-1)/2) * spk_pitch;
function divider_cy() = (outer_h()/2 - wall) - spk_zone_h - divider_t/2;
function board_cy()   = -outer_h()/2 + wall + board_zone_h/2;
function side_x()     = outer_w()/2 - wall;                                // inner face, +x wall
function port_od()    = port_id + 2*port_wall;                             // 24
// the front face after the chamfer: every front-baffle feature must live inside it
function flat_w()     = outer_w() - 2*chamfer;
function flat_h()     = outer_h() - 2*chamfer;
// chamber volume. Unlike the old model this subtracts the rounded-corner slivers and
// the port tube envelope, so the number is honest rather than merely precise.
function corner_loss()= 4 * (pow(radius-wall,2) - PI*pow(radius-wall,2)/4) * spk_zone_h;
function port_disp()  = PI/4 * pow(port_od(),2) * (port_len - wall);
function pad_disp()   = spk_n * PI/4 * (pow(spk_pad_d,2) - pow(spk_cut,2)) * spk_pad_t;
function gross_vol()  = inner_w * spk_zone_h * cavity_depth;
function net_vol()    = gross_vol() - corner_loss() - spk_n*driver_disp - port_disp() - pad_disp();
function btn_nut_ac() = btn_nut_af * 2/sqrt(3);                            // nut across corners (~19.05)
