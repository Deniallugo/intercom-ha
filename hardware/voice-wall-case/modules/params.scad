// ===== Voice S3 wall unit — parameters (no geometry) =====
// Two stacked boxes on one wall plate: the Voice S3 box (ESP32-S3 devkit, PCM5102A, INMP441,
// dome button) on top, the ZK-502MT amplifier box underneath. Both hang on the plate by printed
// pegs in keyholes and lift off for service.
//
// TAGS used below — read them before trusting a number:
//   [measured]   caliper value carried over from hardware/voice-case (printed and fitted there)
//   [user]       nominal given by the user, not yet checked against a print
//   [photo]      estimated from photos (IMG_4057..4062). NOT a measurement — fit-check it
//   [assumed]    no evidence at all; a typical value for the part
//   [choice]     a design decision, free to change
//
// FRAMES.
//   World:  x across (+x = right as you face the unit), y OUT of the wall (y = 0 is the wall),
//           z up (z = 0 is the bottom of the amp box).
//   Box-local (every shell, lid, sled and tray is modelled in it, and the shells print in it):
//           x across, y UP (0 = the box's bottom outer face), z INTO the box from the FRONT
//           outer face (z = 0). This is the voice-case convention (z runs inward from the face
//           the button is on), which is what lets the button and mic modules carry over as-is.
//           A box goes to the world by translate([0, y_front, z_bottom]) rotate([90, 0, 0]).
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for parts that locate precisely
wall = 3;                  // shell walls

// =====================================================================================
// SHARED ENVELOPE — both boxes have the same width, depth and corner treatment
// =====================================================================================
// Width is set by the VOICE box, not the amp: the 63 mm devkit has to lie across x in its tray
// (see voice_tray layout below), and that needs 63 + 2 x 0.5 + 2 x 1.6 = 67.2 inside. 76 leaves
// the tray 2.8 mm of side play. The amp (60 wide) then has 5 mm each side, which is where its
// side vents and wires go. Asserted from both sides.
box_w   = 76;              // [choice] outer width, both boxes
box_r   = 4;               // [choice] vertical-edge radius (plan corners of the front face)
front_chamfer = 1.5;       // [choice] 45 deg front edge; the shells print front-face-down
lid_t   = 4;               // [choice] rear lid plate

// Rear-lid screws: M3 into heat-set inserts in short bosses on the TOP and BOTTOM walls, at the
// rear rim. Not in the corners: corner pillars would sit exactly where the sled, the tray and the
// side vents want to be. Top and bottom pairs use DIFFERENT x on purpose — the bottom pair sits
// outboard of the MP1584 pocket and the top pair inboard of the amp's panel switch body.
insert_m3_d  = 4.0;        // [measured] heat-set bore (voice-case)
insert_m3_h  = 5.0;        // [measured]
screw_clear  = 3.4;
lid_boss_od  = 8;
lid_boss_len = 10;         // [choice] full-diameter length along z, from the rear rim
lid_boss_x_top = 18;       // [choice] +- x of the top pair
lid_boss_x_bot = 27;       // [choice] +- x of the bottom pair

// Vents: plain slots, long axis along z (box depth), so in print orientation (front face down)
// every slot is a vertical slit closed by a 3 mm bridge.
vent_w     = 2.5;          // [choice]
vent_pitch = 5.5;          // [choice]

// =====================================================================================
// AMPLIFIER — ZK-502MT
// =====================================================================================
// Orientation in the box: component side UP, faceplate at the FRONT (knobs out into the room),
// connector edge at the REAR (toward the wall). Looking at the front: VOL is on the RIGHT (+x),
// TREBLE on the LEFT — from the photos, the faceplate LED is at the VOL end. On the rear edge,
// from +x to -x: 3.5 mm AUX jack, a small yellow part, the 4-way barrier block, the DC barrel.
//
// The 73 x 60 x 18 envelope is the user's nominal. What it INCLUDES is not confirmed, so it is
// split into the pieces the box actually depends on, each with its own tag:
amp_w        = 60;         // [user] board width, along the faceplate
amp_l        = 73;         // [user] PCB REAR EDGE to the faceplate's FRONT face. The ruler photo
                           //   (IMG_4060) puts the faceplate at ~7.3 cm from the barrel end, so
                           //   this is taken to include the faceplate. CONFIRM.
amp_env_h    = 18;         // [user] PCB underside to the highest point (heatsink / caps /
                           //   faceplate top). CONFIRM it is not measured from the PCB top.
amp_tail_h   = 2.5;        // [assumed] through-hole tails under the PCB
amp_rear_over = 2.0;       // [photo] how far the barrel / AUX bodies stand past the rear edge
// The faceplate. In the photos it is a separate black panel the pot bushings pass through, held by
// the pot nuts. The default front treatment USES it as the front skin (see ctrl_mode).
amp_face_w   = 60;         // [assumed] = board width. MEASURE
amp_face_h   = 18;         // [assumed] MEASURE — probably the "18" in 73 x 60 x 18
amp_face_t   = 1.6;        // [assumed] PCB-stock panel. MEASURE
amp_face_y0  = -1.0;       // [photo] faceplate bottom edge relative to the PCB UNDERSIDE
                           //   (negative = it hangs below the PCB). MEASURE
amp_face_x   = 0;          // [assumed] faceplate centre vs board centre, across x
// ---- PLACEMENT — the numbers fusion/VoiceWallCase/vwc/placement.py owns ----
// Moving a component in Fusion and running `sync` rewrites that file; tests pass its values
// back in here with -D, so these defaults only matter for a bare OpenSCAD render.
amp_x        = 0;          // [choice] board centre across x
amp_lift     = 0;          // [choice] extra standoff height: raises the board (and the box)
amp_setback  = 0;          // [choice] faceplate behind the front wall ("holes" mode only)
// Mounting holes, board frame: [x from board centre (+ = VOL end), distance from the REAR edge].
// Read off IMG_4057/4060 — four holes are visible but NOT symmetric, and every coordinate here is a
// perspective estimate good to a few mm. They only place the sled's standoffs, and the sled is a
// 30-minute reprint precisely so these can be wrong.
// The front-right hole reads ~70 in the photo, but that would put its standoff into the faceplate
// (asserted), so the photo is wrong there by at least 3 mm; 66 is a placeholder that fits.
amp_holes = [[ 26.5, 19], [ 19, 66],
             [-21,   22], [-23, 64]];   // [photo] MEASURE with calipers
amp_hole_pilot   = 2.6;    // M3 self-tap into the standoff
amp_standoff_od  = 6.5;
// 6 mm under the PCB: tails (2.5) plus room to run the two 24 V tap wires from the barrel
// jack's solder pins to the MP1584 without touching anything.
amp_standoff_h   = 6;      // [choice]
sled_t           = 2;      // [choice] removable board sled under the amp
// Air above the envelope. The TPA3116 heatsink sits mid-board; 8 mm under a vented top.
amp_hs_clr       = 8;      // [choice]
// Heatsink footprint, board frame [x centre, distance from rear edge to its centre, size x, size y].
amp_hs = [-4, 32, 20, 20]; // [photo] only places the top vent field
// ---- rear connectors, board frame: x from board centre (+ = VOL end) ----
amp_dc_x     = -23;        // [photo] barrel jack centre
amp_dc_axis  = 6.0;        // [assumed] barrel axis above the PCB TOP face. MEASURE
amp_dc_plug_d = 11;        // [assumed] plug body diameter (straight plugs are ~10-12)
amp_term_x   = [-11, 16];  // [photo] barrier block span across x
amp_term_h   = 10;         // [assumed] block height above the PCB top
amp_term_screw_from_rear = 5; // [photo] screw-head line, measured in from the rear edge
amp_aux_x    = 22;         // [photo] AUX jack centre
amp_aux_axis = 3.0;        // [assumed] AUX axis above the PCB top. MEASURE
// ---- plug zone: the free strip between the connector faces and the rear lid ----
// It holds the AUX plug (right-angle preferred), the MP1584, the barrel plug's body, the switch
// body and a service loop of wire. Its floor is the rear of the sled, where the MP1584 pocket is.
// 24 is the MP1584's 17 mm + pocket + clearances; a right-angle AUX plug head is ~12-15 mm.
plug_zone = 24;            // [choice]

// ---- front: how the controls come through ----
// "faceplate": the front wall has a window the board's OWN faceplate sits in, from inside, against
//   a lip. Shaft spacing, shaft height and the LED stop mattering — they only have to land inside
//   the window, not in individual holes — so the photo estimates for them cannot cause a misfit.
//   What has to be right instead is the faceplate's outline, which is one caliper reading.
// "holes": a closed front wall with one hole per shaft plus the LED. Use it if the faceplate turns
//   out to be unsuitable as a skin (bent, oversized, or you want a cleaner front). Every input to
//   it is a photo estimate, so print coupon-amp before the shell.
ctrl_mode   = "faceplate"; // [choice] "faceplate" | "holes"
face_lip    = 1.5;         // [choice] how far the window's lip overlaps the faceplate edge
face_rebate = 1.0;         // [choice] faceplate nests this deep into the wall's inner face
face_fit    = 0.3;         // [choice] per side, faceplate in its rebate
// holes mode only:
ctrl_pitch  = 20;          // [photo] 18-22 from IMG_4060/4062 — perspective, not a measurement
ctrl_x0     = 0;           // [assumed] middle shaft, from board centre
ctrl_axis   = 9;           // [photo] shaft axis above the PCB UNDERSIDE. MEASURE
ctrl_bush_d = 7;           // [assumed] M7 bushing. MEASURE
ctrl_slack  = 1.0;         // [choice] radial slack on top of clr, for the estimates above
ctrl_led    = [27, 5];     // [photo] LED vs board centre x / PCB underside; VOL end
ctrl_led_d  = 3.5;
// Shafts project ~15 mm past the faceplate [photo, IMG_4062]. In faceplate mode the faceplate sits
// face_rebate behind the outer face... see amp_knob_proj() — asserted to leave a usable grip.
ctrl_shaft_proj = 15;      // [photo]
knob_min_grip   = 8;       // [choice] shaft that must remain outside the box for a knob

// ---- power switch on the side wall ----
// The board's own switch cannot be reached in this layout: it is on the rear edge, inside the box,
// facing the wall. So a PANEL switch goes on the box's +x side wall, in the plug zone, wired in place
// of (or in series with) the board's switch — see README "Power wiring". +x because the yellow part
// beside the AUX jack (the likeliest candidate for the board's switch) is at the +x end, so the
// wires are short, and because the -x end of the plug zone belongs to the barrel plug.
amp_psw         = true;    // [choice]
amp_psw_shape   = "rect";  // "rect" (snap-in mini rocker, KCD11 type) | "round" (toggle)
amp_psw_cut     = [15, 10];// [assumed] rect cut-out, along z x along y. Check YOUR switch
amp_psw_round_d = 6.2;     // [assumed] e.g. MTS-102 toggle
amp_psw_y       = 28;      // [choice] cut-out centre above the box bottom
psw_dz          = 0;       // [choice] cut-out centre along z, from the plug zone's middle
amp_psw_body    = [12, 14, 10]; // [assumed] body behind the panel: depth in x, z, y. Collision box

// ---- MP1584 buck, in a pocket at the rear of the sled ----
mp_w = 22; mp_l = 17;      // [user] confirmed module size (22 along x, 17 along z)
mp_h = 5;                  // [assumed] tallest part (inductor) above its PCB underside
mp_x = 2;                  // [choice] pocket centre across x
mp_dz = 0;                 // [choice] pocket centre along z, from the plug zone's middle
mp_wall = 1.6; mp_lip = 2.5;

// ---- terminal-screw access + pass-through in the amp top ----
term_access   = true;      // [choice] screwdriver holes over the barrier-block screws
term_access_d = 6;
term_pitch    = 9;         // [photo] 4 positions over ~27 mm

// =====================================================================================
// VOICE BOX — reference parts from hardware/voice-case
// =====================================================================================
// The front face carries the dome button and the mic. Everything else lies on a removable TRAY on
// the floor, laid out front-to-back (z) so nothing has to stack:
//     z  ~3..19    button holder + switch pins, hanging off the front wall
//     z ~19..51    devkit, LONG AXIS ACROSS x (63 of the 70 inside)
//     z ~51..77    DAC, long axis across x, its socket facing the REAR
//     z ~77..102   right-angle AUX plug, the sleeve down to the amp, wire service loop
// The old desk puck put both boards side by side and ran the socket out of a side wall; here the
// socket is an internal connection, so it simply faces the cable.
voice_h = 48;              // [choice] floored by voice_h_min() — the dome on the face. Was 70 with the
                           //   mic on the face too; the mic moved to the TOP face

s3_w = 63; s3_l = 28;      // [measured] ESP32-S3-DevKitC-1 (N16R8): length x width
s3_comp_h   = 11;          // [measured] headers + dressed wire above the PCB
s3_board_clr = 0.5;        // [measured] per side — the value voice-case converged on
dac_w = 20; dac_l = 33;    // [measured] PCM5102A "LINE" board
dac_jack_w  = 6.0;         // [measured] socket body width along its edge
dac_jack_h  = 6.5;         // voice-case value; that case needed a +2 mm correction — MEASURE
dac_jack_overhang = 2.5;   // past the PCB edge
dac_jack_inset = 3.0;      // [measured] board END edge to the socket body
board_clr   = 1.0;         // [measured] per side, DAC pocket
pcb_t       = 1.6;
pocket_wall = 1.6;
board_pin_h = 2.0;         // tails under both boards [voice-case value, still MEASURE there]
tray_t      = 2;           // [choice]
tray_seat   = 2.5;         // [choice] pocket floor above the tray: deeper than the pin relief
tray_lip    = 3.5;         // [measured] pocket wall above the seated board (voice-case s3_lip)
pin_row_w   = 6;           // [measured] relief strip under each header row
s3_z0       = 19.5;        // [choice] devkit pocket's front face, from the box front
s3_x        = 0;           // [choice] devkit pocket centre across x
dac_dx      = 0;           // [choice] DAC off its derived spot (socket over the sleeve), x
dac_dz      = 0;           // [choice] ... and z (>= 0: behind the shared wall)
dac_aux_plug = 12;         // [assumed] right-angle 3.5 mm plug head, past the socket face

// ---- pass-through: a printed sleeve from the voice floor down into the amp top ----
// It sits over the amp's plug zone, so both cables drop straight from the voice box's rear zone
// to the AUX jack and the MP1584. Its ID has to pass a 3.5 mm PLUG during assembly, not just a
// cable — a right-angle plug head is the binding size.
sleeve_x      = 4;         // [choice] across x
sleeve_dz     = 0;         // [choice] along z, from the plug zone's middle
sleeve_id     = 12;        // [assumed] MEASURE your patch cable's plug heads
sleeve_wall   = 1.6;
sleeve_flange = 3;         // radial, resting on the tray inside the voice box
sleeve_engage = 3;         // [choice] how far it reaches into the amp top. < peg_drop, asserted

// ---- dome button: voice-case mechanism, bigger visible cap ----
// The mechanism is voice-case's, unchanged where it was proven in print: an 11 mm tactile standing
// in a printed holder cup, a snap-lip plunger in a 19.6 mm journal. Two things change:
//   * the visible top is a SEPARATE dome, Ø40, glued onto the plunger's flange. A dome cannot print
//     well in one piece with a snap plunger (one of them is always an overhang), and as a separate
//     part it prints flat-side-down and can be a different colour.
//   * the holder's guide is longer (8 vs 5 mm). A Ø40 cap pressed at its rim levers twice as hard as
//     the Ø22 one did, and journal length is what fights that. See btn_edge_drop().
btn_pos      = [0, 24];    // [choice] on the front face, (x, y) in box-local
btn_dome_d   = 40;         // [choice] the diameter you see and press
btn_dome_h   = 8;          // [choice] crown above the dome's rim
btn_rim_lift = 2.0;        // [choice] 45 deg chamfer under the dome's rim
btn_dome_seat = 1.0;       // pocket in the dome's underside that takes the flange
btn_flange_d = 22;         // [measured] voice-case flange — the recess in the face is sized to it
btn_flange_t = 3.0;        // [choice] thicker than voice-case: it lifts the dome rim clear
btn_wall_od  = 19.6;       // [measured] plunger body = journal
btn_guide_clr = 0.3;       // [measured] per side in the shell bore
btn_recess_depth = 1.6;    // [measured]
btn_face_gap = 1.6;        // [measured] flange to recess floor at rest
btn_pilot_pitch = 30;      // [measured] holder screws, M2 self-tap, blind
btn_pilot_depth = 2.2;
btn_wall_t   = 1.2;        // [measured]
btn_preload  = 0.25;       // [measured]
btn_lip_t    = 1.0;
btn_lip_over = 0.8;
btn_lip_slack = 0.8;
btn_slits    = 8;
btn_slit_w   = 1.0;
btn_slit_z0  = 3.5;
btn_post_d   = 2.0;
bh_guide_h   = 8.0;        // [choice] voice-case had 5
bh_floor_t   = 1.6;
bh_guide_clr = 0.45;
bh_wall      = 1.6;
bh_ear_d     = 7;
bh_fin_t     = 3;
bh_screw_clear = 2.2;
bh_screw_cbore_d = 4.0;
bh_screw_cbore_h = 1.2;
bh_relief_eps = 0.01;
bh_rib_embed  = 0.3;
board_screw_pilot = 1.6;   // M2 self-tap
// 11 x 11 tactile [measured unless tagged]
sw_body = 11.0; sw_h = 8.0;
sw_plunger_d = 3.0; sw_plunger_h = 1.8; sw_travel = 0.7;
sw_pin_axis = 0; sw_pin_out = 1.0; sw_pin_slack = 1.5; sw_pin_gap = 5.0;
sw_pin_win = 2.2; sw_pin_len = 3.5;
sw_locate_clr = 0.4; sw_locate_t = 1.6; sw_locate_len = 5.0; sw_locate_len_pin = 1.8;
sw_locate_h = 2.0;

// ---- microphone: voice-case single-port gasket seat, moved to the top of the front face ----
// As far from the amp as the face allows: top of the upper box, facing the room.
// On the TOP face, as on the voice-case desk puck: (x, z) — across, and depth from the front
// face. The front face holds only the dome, which is what takes the box from 70 to 48 tall.
mic_pos      = [0, 30];    // [choice]
mic_board_w = 17; mic_board_l = 15;   // [measured] INMP441
mic_seat_depth = 1.0; mic_gasket_d = 12; mic_gasket_depth = 0.8; mic_hole_d = 2.0;
mic_post_pitch = 24; mic_post_od = 5; mic_post_h = 4;
mic_clamp_w = 5; mic_clamp_t = 1.25; mic_clamp_pad = 10; mic_screw_clear = 2.4;

// =====================================================================================
// WALL PLATE, LEGS, PEGS
// =====================================================================================
// The cable channel is made by two LEGS on the back of each lid, not by rails on the plate: the plate
// stays a flat 6 mm part, the legs print straight up off the lid, and the peg sits on the end of each
// leg. Cables run between the legs and leave the channel at the bottom, which is open.
chan_d      = 30;          // [choice] channel depth = leg length, lid to plate
leg_w       = 8;
stack_gap   = 6;           // [choice] air gap between the boxes; < peg_drop, so the upper box
                           //   stops the lower one lifting off its pegs
plate_t     = 6;           // keyhole lip + a cavity deep enough for the peg head
plate_margin = 4;          // plate is this much wider than the boxes, each side
// Pegs: neck + 45 deg cone head (prints upward off the leg). The plate's keyhole lip is caught
// between the leg end and the cone, so hanging the box pulls it tight against the plate.
peg_neck_d  = 4.5;
peg_head_d  = 8.0;
peg_head_h  = 1.5;
kh_lip      = 2.0;         // keyhole lip = the plate's front skin
kh_clr      = 0.4;
peg_drop    = 8;           // box drops this far to engage; lifts this far to come off
peg_y_amp   = [10, 30];    // [choice] peg heights on the amp lid (box-local y)
peg_y_voice = [12, 34];    // [choice] ... on the voice lid
// wall screws: 4 x 4 mm countersunk, between the legs
ws_d = 4.5; ws_head_d = 9; ws_x = 16;
// Lock: an L-bracket on a header block at the plate top, its lip over the voice legs' top ends.
// Two vertical M3 into inserts, reached from above. Remove it and the voice box lifts off; the
// voice box gone, the amp lifts off. That ordering is the whole anti-lift scheme.
lock_gap   = 3;            // < peg_drop
header_h   = 10;
header_d   = 14;          // from the wall; deep enough for an M3 insert with 2 mm walls
lock_t     = 4;
lock_screw_x = 14;

// =====================================================================================
// DERIVED
// =====================================================================================
function inner_w()      = box_w - 2*wall;
function amp_front_z()  = (ctrl_mode == "faceplate" ? wall - face_rebate : wall) + amp_setback; // faceplate FRONT face
function amp_rear_z()   = amp_front_z() + amp_l;                                  // PCB rear edge
function plug_z0()      = amp_rear_z() + amp_rear_over;                           // connector faces
function box_d()        = plug_z0() + plug_zone;                                  // shell depth to rear rim
function amp_standoff_len() = amp_standoff_h + amp_lift;
function amp_pcb_y()    = wall + sled_t + amp_standoff_len();                      // PCB underside
function amp_pcb_top()  = amp_pcb_y() + pcb_t;
function amp_env_top()  = amp_pcb_y() + amp_env_h;
function amp_h()        = amp_env_top() + amp_hs_clr + wall;
function amp_face_y()   = amp_pcb_y() + amp_face_y0;
function amp_knob_proj()= ctrl_shaft_proj - amp_front_z();       // shaft left outside the box
function amp_bz(from_rear) = amp_rear_z() - from_rear;           // board frame -> local z
function plug_zc()      = (plug_z0() + box_d())/2;
function mp_zc()        = plug_zc() + mp_dz;
function psw_zc()       = plug_zc() + psw_dz;
function sleeve_zc()    = plug_zc() + sleeve_dz;
// world placement
function lid_back_y()   = plate_t + chan_d;                      // lid outer face
function front_y()      = lid_back_y() + lid_t + box_d();        // box front face
function voice_z0()     = amp_h() + stack_gap;
function voice_top()    = voice_z0() + voice_h;
function plate_h()      = voice_top() + lock_gap;
function plate_w()      = box_w + 2*plate_margin;
function peg_x()        = box_w/2 - leg_w/2;
// lid bosses, box-local [x, y]
function lid_boss_pts(h) = [[-lid_boss_x_bot, wall + lid_boss_od/2 - 1],
                            [ lid_boss_x_bot, wall + lid_boss_od/2 - 1],
                            [-lid_boss_x_top, h - wall - lid_boss_od/2 + 1],
                            [ lid_boss_x_top, h - wall - lid_boss_od/2 + 1]];
function lid_boss_taper() = lid_boss_od + 1;                      // 45 deg support, in z
function lid_boss_z0()  = box_d() - lid_boss_len - lid_boss_taper();
// amp lid cable window: the barrel plug and the barrier block, with margin
function amp_win_x0()   = amp_x + amp_dc_x - amp_dc_plug_d/2 - 1;
function amp_win_x1()   = amp_x + amp_term_x[1] + 2;
function amp_win_y0()   = amp_pcb_y();
function amp_win_y1()   = amp_pcb_top() + amp_term_h + 4;
// faceplate window
function face_c()       = [amp_x + amp_face_x, amp_face_y() + amp_face_h/2];

// ---- button (same chains as voice-case; z is depth from the front face) ----
function btn_bore_d()   = btn_wall_od + 2*btn_guide_clr;
function btn_recess_d() = btn_flange_d + 2*clr;
function btn_wall_id()  = btn_wall_od - 2*btn_wall_t;
function btn_lip_od()   = btn_wall_od + 2*btn_lip_over;
function bh_bore_d()    = btn_wall_od + 2*bh_guide_clr;
function bh_relief_d()  = btn_lip_od() + 2*clr;
function bh_collar_od() = bh_relief_d() + 2*bh_wall;
function btn_stroke()   = sw_travel - btn_preload;
function bh_relief_h()  = btn_lip_t + btn_stroke() + btn_lip_slack;
function sw_diag()      = sqrt(2)*sw_body;
function sw_pin_a()     = sw_body/2 + sw_pin_out;
function sw_pin_b()     = sw_pin_gap/2;
function sw_pin_slot()  = 2*sw_pin_slack;
function sw_pin_pos()   = [for (sa = [-1,1], sb = [-1,1])
                             sw_pin_axis == 0 ? [sa*sw_pin_a(), sb*sw_pin_b()]
                                              : [sb*sw_pin_b(), sa*sw_pin_a()]];
function sw_pin_win_xy()= sw_pin_axis == 0 ? [sw_pin_slot(), sw_pin_win] : [sw_pin_win, sw_pin_slot()];
function sw_locate_r0() = sw_body/2 + sw_locate_clr;
function sw_locate_r1() = sw_locate_r0() + sw_locate_t;
function bh_z0()        = wall;
function bh_catch_z()   = bh_z0() + bh_guide_h;
function bh_relief_z1() = bh_catch_z() + bh_relief_h();
function bh_z1()        = bh_relief_z1() + bh_floor_t;
function sw_pin_z1()    = bh_relief_z1() + sw_pin_len;
function bh_deep_z()    = max(bh_z1(), sw_pin_z1());
function sw_body_h()    = sw_h - sw_plunger_h;
function sw_top_z()     = bh_relief_z1() - sw_body_h();
function plunger_z()    = bh_relief_z1() - sw_h;
function bh_plate_w()   = btn_pilot_pitch + bh_ear_d;
function btn_face_bot_z()   = btn_recess_depth - btn_face_gap;      // flange underside, at rest
function btn_flange_top_z() = btn_face_bot_z() - btn_flange_t;      // flange top (outer)
function btn_ceil_z()       = btn_face_bot_z();                     // plunger's inner ceiling
function btn_wall_z1()      = bh_catch_z() + btn_lip_t;             // body's far edge
function btn_post_h()       = plunger_z() + btn_preload - btn_ceil_z();
function btn_dome_base_z()  = btn_flange_top_z() + btn_dome_seat;   // dome underside plane
function btn_rim_gap()      = -btn_dome_base_z();                   // dome's flat underside above the face
function btn_dome_flat_r()  = btn_dome_d/2 - btn_rim_lift;
// Worst-case tilt of the plunger in its two journals (shell bore + holder bore), and what it does
// at the edge of the dome's flat underside. The press at that radius must not land the dome on the
// face before the switch has travelled.
function btn_tilt()         = (2*btn_guide_clr + 2*bh_guide_clr)/2 / (wall + bh_guide_h);
function btn_edge_drop()    = btn_dome_flat_r()*btn_tilt() + btn_stroke();
function btn_proud()        = -btn_dome_base_z() + btn_rim_lift + btn_dome_h;  // crown above the face

function mic_size()         = [mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od)];
function mic_board_top_z()  = wall - mic_seat_depth + pcb_t;
function mic_clamp_pad_h()  = (wall + mic_post_h) - mic_board_top_z();
function mic_clamp_len()    = mic_post_pitch + mic_post_od;

// ---- voice tray layout (box-local z = depth, x across) ----
function tray_top()     = wall + tray_t;                                    // tray upper face (y)
function s3_cav()       = [s3_w + 2*s3_board_clr, s3_l + 2*s3_board_clr];   // x, z
function s3_pocket()    = s3_cav() + [2*pocket_wall, 2*pocket_wall];
function s3_zc()        = s3_z0 + s3_pocket()[1]/2;
function dac_cav()      = [dac_l + 2*board_clr, dac_w + 2*board_clr];       // long axis across x
function dac_z0()       = s3_z0 + s3_pocket()[1] - pocket_wall + dac_dz;    // shares one wall
function dac_zc()       = dac_z0() + dac_cav()[1]/2 + pocket_wall;
function dac_edge_z()   = dac_zc() + dac_w/2;                               // socket edge (rear)
function dac_socket_z() = dac_edge_z() + dac_jack_overhang;                 // socket face
// socket sits dac_jack_inset from the +x end; put it over the sleeve
function dac_xc()       = sleeve_x - (dac_l/2 - dac_jack_inset - dac_jack_w/2) + dac_dx;
function dac_jack_x()   = dac_xc() + dac_l/2 - dac_jack_inset - dac_jack_w/2;
function sleeve_od()    = sleeve_id + 2*sleeve_wall;
function sleeve_len()   = tray_t + wall + stack_gap + sleeve_engage;
function voice_h_min()  = btn_pos[1] + btn_dome_d/2 + front_chamfer + 2;   // the dome, on the face
// the top face, as a frame: the front-face modules (x, y along the face, z = depth) drawn on it
function top_face_m(h)  = [[1, 0, 0, 0], [0, 0, -1, h], [0, 1, 0, 0], [0, 0, 0, 1]];
