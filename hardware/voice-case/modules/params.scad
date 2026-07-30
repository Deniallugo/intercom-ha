// ===== Voice S3 desk puck — parameters (no geometry) =====
// A tabletop voice-satellite puck in the shape of the Home Assistant Voice PE:
// square rounded plan, chamfered top edge, one big button and the mic port on the
// top face. What it does NOT have is VPE's internal speaker — devices/voice-s3.yaml
// is a LINE-OUT device, so the driver and its grille are replaced by a panel-mount
// 3.5 mm jack on the rear wall. That is the whole reason this is a separate case:
// with no driver and no sealed chamber, the box is a board carrier, and every
// dimension below is set by the boards, not by an acoustic volume.
//
// Contents: ESP32-S3-DevKitC-1 (N16R8) + GY-PCM5102A DAC + INMP441 mic + one 6x6
// tactile switch under a printed cap. Power and flashing are the devkit's own USB-C.
//
// Axes. +y is the FRONT (toward you), -y the REAR (both cables leave there), and z
// runs from the TOP face (z = 0) down into the box. The shell prints top-face-down,
// which is why the top edge is a 45 deg chamfer and not a fillet — a fillet would
// start horizontal on the build plate.
//
// Vertical layout is the point of the design. The devkit is 69 mm long and the four
// corner bosses are full-depth pillars, so no plan arrangement fits the devkit AND
// the DAC AND the button side by side in an 86-90 mm square. So the two big boards
// are STACKED: the devkit on the base plate, the DAC hanging off the top face, with
// the button, the mic and the switch seat sharing the remaining top-face area.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall         = 3;          // walls, top face and base plate
radius       = 12;         // rounded vertical corners
chamfer      = 5;          // 45 deg top-edge chamfer (prints support-free top-down)
plan         = 90;         // square footprint. VPE is 86; the extra 4 mm is what the
                           // 69 mm devkit needs to clear the corner bosses in y.
cavity_depth = 23;         // interior height: the stacked DAC + devkit column

// ---- corner screws (M3 heat-set inserts) ----
// Inserts, not self-tap: the base plate is the only access to every solder joint in
// the box, so this joint gets opened repeatedly. Same call the speaker case made.
boss_od       = 8;
insert_m3_d   = 4.0;       // heat-set insert bore
screw_clear   = 3.4;
screw_cbore_d = 6.2;       // counterbore in the base plate's OUTER face, so no screw
screw_cbore_h = 1.6;       // head stands proud to scratch the desk
boss_inset    = radius + 3;

// ---- boards [confirm vs hardware] ----
s3_w = 69; s3_l = 26;      // ESP32-S3-DevKitC-1 (N16R8); LONG AXIS ALONG Y here, so
                           // its USB-C end faces the rear wall
dac_w = 27; dac_l = 27;    // GY-PCM5102A breakout
mic_board_w = 17; mic_board_l = 14;   // INMP441 breakout
pcb_t             = 1.6;
pocket_wall       = 1.6;   // friction-pocket wall (boards without usable mount holes)
board_standoff_h  = 3;
board_standoff_od = 4.5;
board_screw_pilot = 1.6;   // M2 self-tap
// The devkit sits in a pocket on the base plate. The floor is 3.5 mm rather than a
// bare 1.6 mm because the floor height is what sets the USB-C receptacle height, and
// the rear window has to stay a BOUNDED hole with material left below it.
s3_seat_h = 3.5;           // pocket floor under the devkit
s3_lip    = 1.5;           // pocket wall standing above the seated board
s3_comp_h = 6;             // tallest thing on the devkit's component side [confirm]

// plan placements (x, y)
s3_pos  = [-6, -3];        // base plate; pushed rearward so the USB plug reaches
dac_pos = [26,  6];        // top face, +x side — clear of the devkit column below
mic_pos = [-4, 28];        // top face, front edge
btn_pos = [ 0,  0];        // top face, centred

// ---- rear wall (-y): devkit USB-C + 3.5 mm line-out ----
// One window over the devkit's own two USB-C ports: that is power AND flashing AND
// the serial log, so there is no separate panel-mount USB socket to wire.
usb_recept_h = 3.2;        // USB-C receptacle height above the PCB [confirm]
s3_usb_w = 14;             // window width (x) — wide enough for a cable overmold
s3_usb_h = 9;              // window height (z)
// Panel-mount 3.5 mm stereo jack (PJ-392 style), fed from the PCM5102's LROUT/RROUT.
jack_bore_d = 6.2;
jack_nut_d  = 11;
jack_body_h = 12;          // how far the barrel reaches into the cavity
jack_pos    = [18, 14];    // (x, z): +x of the devkit column, mid-height

// ---- button: printed cap over a 6x6 tactile switch ----
// A panel-mount switch was the other option and is what the speaker case uses, but
// its body + terminals need ~30 mm behind the panel and would have made this puck
// ~45 mm tall. A cap over a tactile switch keeps it at 29 mm and looks like VPE.
//
// The cap is a snap-in CUP, not a solid plunger: a solid skirt cannot flex past the
// bore, so the skirt is a thin annulus split by radial slits, and a lip on its lower
// edge catches on the top wall's inner face. The switch spring pushes the cap up
// until that lip lands — that, not the recess floor, is what sets the rest height.
btn_well_d       = 16.5;   // bore through the top wall (skirt rides in this)
btn_cap_d        = 18;     // face disc — MUST be wider than the bore
btn_recess_d     = 18.8;   // shallow recess the face sits in (cap + 2*clr)
btn_recess_depth = 1.2;
btn_face_t       = 2.0;
btn_face_gap     = 0.5;    // cap floats this far above the recess floor at rest;
                           // this, minus switch travel, is the anti-bottoming margin
btn_lip_t        = 1.0;
btn_lip_over     = 0.9;    // radial catch beyond the skirt OD
btn_skirt_t      = 1.2;    // skirt annulus wall
btn_slits        = 4;      // radial slits so the skirt can collapse through the bore
btn_slit_w       = 1.2;
btn_post_d       = 3.4;    // central post, face underside down to the plunger
// tactile/visual halo on the OUTER face, so the button is findable without looking
btn_halo_id      = 21;
btn_halo_od      = 25;
btn_halo_depth   = 0.6;

// ---- 6x6 tactile switch + its seat [confirm vs hardware] ----
sw_body       = 6.0;
sw_body_h     = 3.5;       // body height (excl. plunger)
sw_plunger_d  = 3.5;
sw_plunger_h  = 1.2;       // plunger proud of the body
sw_travel     = 0.25;      // actuation travel — tiny, as on every tactile switch
sw_gap        = 3.0;       // clear air between the top wall's inner face and the
                           // plunger top; sets the cap post length, so keep it
                           // printable rather than minimal
sw_seat_wall  = 1.6;
sw_leg_slot_w = 5.0;       // slots in the +-x seat walls for the switch legs
sw_leg_slot_h = 2.0;

// ---- microphone (INMP441, top face, gasket-sealed single port) ----
// Straight from the speaker case, and for the same reason: a multi-hole cluster
// through a 3 mm wall is a Helmholtz resonator sitting on top of speech. ONE short
// hole with the MEMS port pressed to a gasket leaves near-zero front volume.
mic_seat_depth   = 1.0;    // board-locating recess in the inner face
mic_gasket_d     = 12;
mic_gasket_depth = 0.8;
mic_hole_d       = 2.0;    // single port, as short as the wall allows
mic_post_pitch   = 24;     // 2x M2 posts flanking the seat
mic_post_od      = 5;
mic_post_h       = 4;

// ---- base plate: registration lip, vents, feet ----
reg_h = 2.0;               // lip nesting into the shell cavity (alignment + light gap)
reg_t = 1.2;

// The box is otherwise closed and an S3 at 240 MHz with PSRAM is not cold. The vents
// face the desk, so they are invisible, and they sit in the two x-bands the devkit
// pocket leaves free.
vent_xs = [-27, -23, 13, 17, 21, 25];
vent_w  = 2.5;
vent_l  = 24;
// Four self-adhesive feet at the mid-edges rather than the corners: the corners are
// where the screw counterbores are.
foot_positions = [[34, 0], [-34, 0], [0, 34], [0, -34]];
foot_d         = 10;
foot_depth     = 0.6;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()   = plan;
function outer_h()   = plan;
function top_depth() = wall + cavity_depth;          // top wall + cavity = 26
function outer_d()   = top_depth() + wall;           // + flat base plate = 29
function inner_half()= plan/2 - wall;                // 42
function flat_half() = plan/2 - chamfer;             // 40: the flat top face after the chamfer
function boss_c()    = plan/2 - boss_inset;          // 30: corner boss/screw centres

// board footprints as placed (x-size, y-size) — the devkit is turned 90 deg
function s3_size()      = [s3_l, s3_w];
function s3_pocket_sz() = [s3_l + 2*clr + 2*pocket_wall, s3_w + 2*clr + 2*pocket_wall];
function mic_size()     = [mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od)];

// button / switch column, all in case z (0 = top outer face, +z into the box)
function btn_proud()    = btn_face_t + btn_face_gap - btn_recess_depth;  // 1.3 proud
function btn_skirt_h()  = wall - (btn_recess_depth - btn_face_gap);      // 2.3
function btn_skirt_od() = btn_well_d - 2*clr;                            // 15.7
function btn_skirt_id() = btn_skirt_od() - 2*btn_skirt_t;                // 13.3
function btn_lip_od()   = btn_skirt_od() + 2*btn_lip_over;               // 17.5
function plunger_z()    = wall + sw_gap;                                 // 6.0
function btn_post_h()   = plunger_z() - (btn_recess_depth - btn_face_gap); // face underside -> plunger
function sw_seat_h()    = sw_gap + sw_plunger_h + sw_body_h;             // 7.7, from z = wall
function sw_seat_z()    = wall + sw_seat_h();                            // deepest point of the seat
function sw_seat_od()   = sw_body + 2*clr + 2*sw_seat_wall;              // 10.0 square

// devkit column, measured down from the top face
function plate_inner_z()= top_depth();                                   // base plate inner face
function s3_pcb_top_z() = plate_inner_z() - s3_seat_h - pcb_t;           // component-side surface
function s3_top_z()     = s3_pcb_top_z() - s3_comp_h;                    // tallest devkit part
function s3_usb_cz()    = s3_pcb_top_z() - usb_recept_h/2;               // rear-window centre
// depth below the base plate's inner face — the plate is drawn mirrored, so its
// mounted features are authored in this coordinate
function plate_d(z)     = plate_inner_z() - z;

// DAC hangs off the top face; this is how far down its tallest part reaches
function dac_bottom_z() = wall + board_standoff_h + pcb_t + 4;
