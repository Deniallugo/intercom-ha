// ===== Voice S3 desk puck — parameters (no geometry) =====
// A tabletop voice-satellite puck in the shape of the Home Assistant Voice PE:
// square rounded plan, chamfered top edge, one big button and the mic port on the
// top face. What it does NOT have is VPE's internal speaker — devices/voice-s3.yaml
// is a LINE-OUT device, so the driver and its grille are replaced by the DAC board's
// own 3.5 mm socket, used straight through the +x side wall. That is the whole reason
// this is a separate case: with no driver and no sealed chamber, the box is a board
// carrier, and every dimension below is set by the boards, not by an acoustic volume.
//
// Contents: ESP32-S3-DevKitC-1 (N16R8) + PCM5102A DAC (the variant WITH an onboard
// 3.5 mm socket) + INMP441 mic + one 6x6 tactile switch under a printed cap. Power
// and flashing are the devkit's own USB-C. Nothing else is panel-mounted, and the
// only wires in the box are digital.
//
// Axes. +y is the FRONT (toward you), -y the REAR (the USB cable leaves there), +x
// the side the audio leaves, and z runs from the TOP face (z = 0) down into the box.
// The shell prints top-face-down, which is why the top edge is a 45 deg chamfer and
// not a fillet — a fillet would start horizontal on the build plate.
//
// Layout: both boards lie FLAT on the base plate in friction pockets, side by side in x
// — devkit centred, DAC on the +x side where its socket reaches the wall. The top face
// carries only the mic and the button module. Nothing hangs off the lid, which is what
// the DAC requires: it has no mounting holes, so it has to sit on a floor with gravity
// holding it. What the case costs for that is footprint — see plan_min().
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall         = 3;          // walls, top face and base plate
radius       = 12;         // rounded vertical corners
chamfer      = 5;          // 45 deg top-edge chamfer (prints support-free top-down)
// Square footprint. NOT a style choice — it is set by the two measured boards sitting
// side by side, and plan_min() below computes the floor (94.8; this leaves 1.2 mm).
// VPE is 86 mm. The extra goes on the devkit having to be CENTRED in x: it is 64 mm
// deep, nearly the whole case, so wherever it sits a rear corner boss falls inside its
// span in y and only x clearance can save it. Centring it means the DAC has to begin
// beyond HALF the devkit pocket rather than just beside it.
plan         = 96;
// Interior height, floored by cavity_min() at 26.6 for an 11 mm component stack. 28
// leaves 1.4 mm rather than the 0.4 that 27 would — worth having on a hand-measured
// stack. What sets it is the button holder reaching 11.5 mm down into the devkit's
// airspace, not the devkit alone (which needs only 16.1).
cavity_depth = 28;

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
// MEASURED off the actual boards. Both came in larger than the datasheet-style figures
// this case was first drawn to (26 and 15 mm wide), which is why the first pockets were
// smaller than the boards they were meant to hold.
s3_w = 63; s3_l = 30;      // ESP32-S3 devkit; LONG AXIS ALONG Y, USB-C end at the rear
board_gap = 3;             // between the two board pockets on the plate
// PCM5102A "LINE" breakout — the purple board. Its 3.5 mm socket sits on a LONG SIDE
// (the edge silkscreened LINE / L R G), barrel pointing sideways out of that edge and
// the body OVERHANGING it. So the board is turned 90 deg here: LONG AXIS ALONG Y, that
// socket edge facing +x. Every gold pad on it is a header position — there are NO
// mounting holes, so it sits in a friction pocket like the devkit, not on standoffs.
// Turning it sideways costs little: it needs ~22 mm of x, which leaves the devkit the
// whole middle of the plate.
dac_w = 20;                // board size across x (its SHORT dimension)  [measured]
dac_l = 30;                // board size along y (its LONG dimension)    [measured]
dac_seat_h = 3.5;          // pocket floor under the board (deep enough for pin relief)
// The lip covers the socket rather than stopping partway up it, shrouding the tallest part
// in the pocket. It is not what resists a levered plug — the walls sit ~4 mm clear of the
// socket in y; that job belongs to the counterbore in the shell wall.
dac_lip    = 6.5;          // = dac_jack_h; asserted below
mic_board_w = 17; mic_board_l = 15;   // INMP441 breakout, 17 x 15 [measured]
pcb_t             = 1.6;
pocket_wall       = 1.6;   // friction-pocket wall (boards without usable mount holes)
board_screw_pilot = 1.6;   // M2 self-tap
// PER-SIDE clearance in the two friction pockets — deliberately much looser than the
// global `clr`, which is for parts that locate precisely. Both pockets were first built
// on `clr` (0.4) and both came out SMALLER than the real boards: printed pocket walls
// come in slightly proud, PCB edges carry snap-tab burrs, and the nominal footprints
// below are approximate to begin with. 1.0 per side means each pocket is 2 mm oversize
// on both axes, which also absorbs up to 2 mm of error in those nominals. The slack
// costs nothing: both boards are held down by the lid and their own wiring, and the
// openings they line up with are sized to tolerate the play (see s3_usb_w()).
board_clr = 1.0;
// ---- pin relief: why the pocket floors are not flat ------------------------------
// Soldered headers leave pin TAILS protruding through the solder side. On a flat floor
// the board then rests on those tails instead of the floor, sitting ~2 mm proud — and a
// lip sized for a flat-seated board ends up level with the GAP UNDER the board rather
// than with its edge, so the wall grips nothing. That is the failure that made the first
// walls look like they "covered the pins": they did, because the board was riding above
// where they expected it.
//
// The fix is relief, not a taller lip. Two strips are sunk into each pocket floor under
// the header rows (which run along the long +-x edges of both boards), leaving the board
// supported on a central land plus a land at each short end. It then seats FLAT, the
// tails hang free, and the lip engages the PCB edge as intended.
board_pin_h = 2.0;         // solder-side pin tail protrusion [MEASURE]
pin_row_w   = 6;           // width of the relief strip along each long edge
pin_land    = 4;           // supported land left at each short end
// The strips used to run flush to the cavity face, which UNDERCUT THE POCKET WALL'S BASE:
// the wall then stands on nothing at its inner face and its exposed height grows by the
// relief depth. This setback keeps a strip of full-height floor at the wall base. It costs
// nothing — the header row sits ~2.5 mm in from the board edge, so a 1.2 mm setback still
// leaves the relief right under it.
pin_relief_setback = 1.2;
// The devkit sits in a pocket on the base plate. The floor is 3.5 mm rather than a
// bare 1.6 mm because the floor height is what sets the USB-C receptacle height, and
// the rear window has to stay a BOUNDED hole with material left below it.
s3_seat_h = 3.5;           // pocket floor under the devkit
s3_lip    = 3.5;           // pocket wall standing above the seated board
s3_comp_h = 11;            // tallest thing on the devkit's component side: soldered
                           // 2.54 headers (~8.5) plus dressed wire, 11 mm total [measured]

// plan placements (x, y). The DAC's x is DERIVED, not set — see dac_pos() below.
// Both big boards live on the BASE PLATE, side by side in x: the devkit runs along y
// down the -x side, the DAC along x on the +x side. Nothing hangs off the top face
// any more except the mic and the switch seat, which is also what makes the DAC
// mountable at all — a friction-pocketed board with no screw holes has to sit on a
// floor with gravity holding it, not hang upside down off the lid.
s3_pos_x  = 0;             // devkit CENTRED in x — see plan_min(). Its y is derived.
mic_pos   = [-4, 28];      // top face, front edge
btn_pos   = [ 0,  0];      // top face, centred

// ---- rear wall (-y): devkit USB-C ----
// One window over the devkit's own USB-C ports: that is power AND flashing AND the
// serial log, so there is no separate panel-mount USB socket to wire.
//
// The DevKitC-1 has TWO USB-C receptacles side by side on its short edge, and together
// they span most of the board's width. A single narrow window straddles the gap between
// them and fully exposes NEITHER, so no plug fits either port — so the width is derived
// from the port count rather than typed in, and the pocket's rear wall is deleted
// entirely (see s3_seat): those wall stubs either side of a narrow notch sat directly in
// front of the receptacles, which is the other half of the same failure.
usb_recept_h  = 3.2;       // USB-C receptacle height above the PCB [confirm]
s3_usb_ports  = 2;         // the DevKitC-1 has two
s3_usb_port_w = 9.0;       // one USB-C receptacle across [confirm]
s3_usb_gap    = 2.0;       // between the two
s3_usb_slop   = 3.0;       // extra, to absorb the board's play in its oversize pocket
s3_usb_h      = 10;        // window height (z) — clears a plug overmold, not just the port

// ---- 3.5 mm line-out: the DAC's OWN socket, through the +x side wall ------------
// No panel-mount jack and no LROUT/RROUT flying leads. The board carries its own
// socket, so it is placed where that socket lands on a wall — one less part, one less
// solder joint, and no analog pair running across the box.
//
// It exits the +x SIDE wall, not the rear beside the USB. That is forced, not
// stylistic: to reach the rear wall the board would have to sit within |x| <= 12.5 to
// clear the rear corner bosses, and that window is already spent on the USB cutout
// with the devkit column directly underneath it.
//
// The wall is LOCALLY THINNED behind the socket, the same trick the speaker case uses
// for its PTT switch. It is not cosmetic: a 3.5 mm plug has ~14 mm of barrel and needs
// nearly all of it inserted to make the ring contact. Spend 3 mm of that on a full-
// thickness wall and the plug bottoms out on the case before it seats, which reads as
// intermittent or mono. At 1.2 mm the plug loses 1.7 mm total and seats properly.
//
// The socket also stays entirely BEHIND the outer skin — it protrudes into the
// counterbore, never through the hole. That is what lets the base plate (carrying the
// board) rise straight up into the shell at assembly; a socket poking through the wall
// would have to be threaded in sideways, which a vertical joint cannot do.
//
// MEASURE THESE on your board — they are the numbers that place the hole. [MEASURE]
dac_jack_w        = 9.0;   // socket body width along its edge (y)
dac_jack_h        = 6.5;   // socket body height above the PCB face (z)
dac_jack_axis     = 3.2;   // barrel AXIS above the PCB face — sets the hole centre
dac_jack_overhang = 2.5;   // how far the socket body sticks past that long edge
// The socket is NOT centred on its edge — it sits in the board's corner, 3 mm from the
// end. That offset has to be absorbed somewhere, and it goes into the BOARD's position,
// not the hole's: the hole is centred on the side wall and dac_pos_y() is derived to put
// the socket behind it. A hole 7.5 mm off centre on an otherwise plain wall reads as a
// mistake, while the board is hidden and does not care where it sits.
dac_jack_inset    = 3.0;   // board END edge to the near side of the socket body [measured]
dac_jack_end      = -1;    // which end the socket sits at: -1 = rear (-y), +1 = front
jack_hole_y       = 0;     // where the hole sits along the side wall. 0 = centred, and
                           // this is the number that stays put — the board moves.
dac_socket_setback = 0.5;  // socket face to the thinned panel's inner surface
jack_panel_t = 1.2;        // LOCAL wall thickness at the socket (see above)
jack_hole_d  = 7.0;        // plug clearance through the thinned panel
jack_lead_in = 0.6;        // outer-face chamfer so a plug can't ride the cut edge

// ---- DAC pull-out stop: a rib on the shell's +x inner wall ------------------------
// Pulling a plug OUT drags the board +x, and the DAC pocket is open on that side. Left
// alone, the only thing arresting the board is the socket body landing on the thinned
// panel — 1.2 mm, the thinnest member in any load path on this case, taking a repeated
// service load in bending. This rib catches the PCB EDGE instead and feeds the load
// straight into the full 3 mm side wall. It also becomes the board's x DATUM, so the
// socket's standoff from the panel stops depending on where the board drifted to in an
// oversize pocket.
//
// Its projection is DERIVED, not chosen: it is exactly the gap between the wall's inner
// face and the board's edge, so it tracks the socket like everything else here. It only
// exists at all because the socket overhangs the PCB by more than the wall's unthinned
// remainder — see the assert.
//
// Two things box in where it can go. In z it lives between the socket above it and the
// base plate's register lip below — a 2.1 mm slot. In y it must sit entirely CLEAR OF
// THE SOCKET, because the plate rises vertically into the shell at assembly and a rib
// in the socket's path would block that.
jack_stop_clr   = 0.3;     // between the rib's upper face and the socket body
jack_stop_y_clr = 2.0;     // from the socket in y
jack_stop_inset = 1.0;     // keep it short of the board's far corner

// ---- button: a SEPARATE 2-part module, not shell geometry --------------------
// A panel-mount switch was the other option and is what the speaker case uses, but its
// body + terminals need ~30 mm behind the panel and would have made this puck ~45 mm
// tall. A cap over a 6x6 tactile switch keeps it at 29 mm and looks like VPE.
//
// Everything mechanical lives in two small printed parts — the CAP and the HOLDER —
// and the shell keeps only a plain bore, a cosmetic recess and two blind M2 pilots.
// That split is deliberate. With the switch seat moulded into the shell, every tweak
// to the snap, the travel or the switch fit cost a four-hour shell reprint, and the
// switch had to be pushed into a blind pocket down a 15 mm hole and glued by feel.
// Now the whole mechanism assembles on the bench in the open, gets tested by pressing
// it with a finger, and iterates in the ten minutes it takes to reprint two parts.
//
// The cap is a snap-in CUP, not a solid plunger: a solid skirt cannot flex through the
// bore, so the skirt is a thin annulus split by radial slits. Its lip now catches on
// the HOLDER, not on the shell wall — which is the point, since the holder is the
// cheap part to reprint. The switch spring pushes the cap up until that lip lands;
// that, not the recess floor, sets the rest height.

// shell side — a hole and two pilots, nothing else
btn_bore_d       = 15;     // plain bore through the top wall
btn_recess_d     = 18.8;   // shallow recess the cap face sits in (cap + 2*clr)
btn_recess_depth = 1.2;
btn_pilot_pitch  = 28;     // 2x BLIND M2 pilots flanking the bore, along y
btn_pilot_depth  = 2.2;    // blind: must not reach the outer face
// tactile/visual halo on the OUTER face, so the button is findable without looking
btn_halo_id      = 21;
btn_halo_od      = 25;
btn_halo_depth   = 0.6;

// cap
btn_cap_d    = 18;         // face disc — MUST be wider than the bore
btn_face_t   = 2.0;
btn_face_gap = 0.5;        // cap floats this far above the recess floor at rest; this,
                           // minus switch travel, is the anti-bottoming margin
btn_lip_t    = 1.0;
btn_lip_over = 0.9;        // radial catch beyond the skirt OD
btn_skirt_t  = 1.2;        // skirt annulus wall
btn_slits    = 4;          // radial slits so the skirt can collapse through the bore
btn_slit_w   = 1.2;
btn_post_d   = 3.4;        // central post, face underside down to the plunger

// holder — a plate against the wall's inner face, carrying the switch below it.
// Printed plate-face-down: the only internal overhang is one short annular bridge
// where the plunger aperture closes over the lip relief.
bh_plate_w   = 22;         // x — must contain the lip relief with material to spare
bh_plate_l   = 36;         // y — long enough to reach both pilots and leave edge material
bh_plate_r   = 4;          // corner radius
bh_bore_t    = 1.5;        // skirt-bore section; its underside IS the cap's catch
bh_relief_h  = 1.3;        // room below the catch for the lip to sit in
bh_gap_h     = 2.2;        // plunger-aperture height: post travel + the plunger itself
bh_block     = 20;         // square block below the plate, holding the switch
bh_wall      = 1.6;
bh_screw_clear = 2.4;      // M2 clearance through the plate

// ---- 6x6 tactile switch [confirm vs hardware] ----
sw_body       = 6.0;
sw_body_h     = 3.5;       // body height (excl. plunger)
sw_plunger_d  = 3.5;
sw_plunger_h  = 1.2;       // plunger proud of the body
sw_travel     = 0.25;      // actuation travel — tiny, as on every tactile switch
sw_leg_slot_w = 5.0;       // slots in the +-x block walls for the switch legs
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
// The posts flank the board rather than sit under it — they have to, or the board
// could not lie on its own gasket. So the board is not screwed down, it is CLAMPED:
// a printed bar spans both posts and a pad in its middle presses the board's centre,
// right opposite the MEMS port, which is exactly where the sealing force belongs.
mic_clamp_w     = 8;
mic_clamp_t     = 1.25;    // half the original 2.5 — it only has to hold gasket
                           // compression, and the 10 mm pad does the actual pressing
mic_clamp_pad   = 10;      // central pressing pad (square)
mic_screw_clear = 2.4;     // M2 clearance in the clamp

// ---- base plate: registration lip, vents, feet ----
reg_h = 2.0;               // lip nesting into the shell cavity (alignment + light gap)
reg_t = 1.2;

// The box is otherwise closed and an S3 at 240 MHz with PSRAM is not cold. The vents
// face the desk, so they are invisible, and they sit in the two x-bands the devkit
// pocket leaves free.
// Slots as [x, y, w, l]. The two board pockets leave exactly two clear x-bands, and
// both of them flank the devkit — which is the only part in here that gets warm, so
// that is where the venting wants to be anyway. Turning the DAC sideways opened up the
// 15 mm channel between the two pockets that the middle bank sits in.
vent_rects = [[ 0,  26, 40, 2.5], [ 0,  31, 40, 2.5], [ 0,  36, 40, 2.5],
              [24, -19, 2.5, 14], [29, -19, 2.5, 14],
              [34, -19, 2.5, 14], [39, -19, 2.5, 14]];
// NO foot recesses. There is no clean set of four positions left: the corners are the
// screw counterbores, the +x mid-band is the DAC pocket, and a 0.6 mm recess on the
// outer face under a 2.5 mm pocket floor on the inner face does not fit in a 3 mm
// plate. Self-adhesive feet stick perfectly well to the flat plate — the recesses were
// only ever cosmetic. Populate this list to bring them back; the asserts will tell you
// if the positions you pick collide.
foot_positions = [];
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
// inner edge of the base plate's registration lip — the real inboard bound for
// anything standing on the plate
function lip_inner_half() = (plan - 2*wall - 2*clr)/2 - reg_t;

// board footprints as placed (x-size, y-size) — the devkit is turned 90 deg, so its
// LENGTH is the y dimension here
function mic_size()     = [mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od)];

// ---- devkit: pocket OPEN at the rear, board registered against the rear wall --------
// The pocket has walls on +y and +-x only. Nothing at -y, because anything there sits in
// front of the two USB-C receptacles. That also makes the board self-registering: it
// slides back until it meets the shell's rear wall, which puts the receptacles as close
// to the window as the geometry allows and makes the plug setback deterministic instead
// of depending on where the board happens to sit in an oversize pocket.
function s3_usb_w()     = s3_usb_ports*s3_usb_port_w + (s3_usb_ports-1)*s3_usb_gap + s3_usb_slop;
function s3_cy()        = -inner_half() + board_clr/2 + s3_w/2;   // board centre in y
function s3_pos()       = [s3_pos_x, s3_cy()];
// pocket block: from the register lip at the rear (no wall) to a +y wall past the board
function s3_pocket_y0() = -lip_inner_half();
function s3_pocket_y1() = s3_cy() + s3_w/2 + board_clr + pocket_wall;
function s3_pocket_c()  = [s3_pos_x, (s3_pocket_y0() + s3_pocket_y1())/2];
function s3_pocket_f()  = [s3_l + 2*board_clr + 2*pocket_wall, s3_pocket_y1() - s3_pocket_y0()];
// how far the receptacle sits in from the outer face — a USB-C plug has only ~6.5 mm of
// shell before its overmold
function usb_setback()  = wall + board_clr/2;

// ---- button module: one z chain shared by the cap, the holder and the shell bore ---
// Everything below is in case z (0 = top OUTER face, +z into the box), so the cap and
// the holder are dimensioned against the same numbers the shell is cut to. Diameters
// chain outward from the shell bore: bore -> skirt -> skirt bore in the holder -> lip
// -> lip relief. Change btn_bore_d and the whole stack follows.
function btn_skirt_od() = btn_bore_d - 2*clr;                 // 14.2 rides in the bore
function btn_skirt_id() = btn_skirt_od() - 2*btn_skirt_t;     // 11.8
function btn_lip_od()   = btn_skirt_od() + 2*btn_lip_over;    // 16.0
function bh_bore_d()    = btn_skirt_od() + 2*clr;             // 15.0 skirt bore in the holder
function bh_relief_d()  = btn_lip_od() + 2*clr;               // 16.8 room for the lip
function bh_apert_d()   = sw_plunger_d + 2*clr;               // 4.3 plunger aperture

function bh_z0()        = wall;                               // 3.0 plate on the inner face
function bh_catch_z()   = bh_z0() + bh_bore_t;                // 4.5 cap lip lands HERE
function bh_plate_z1()  = bh_catch_z() + bh_relief_h;         // 5.8 plate ends
function bh_apert_z1()  = bh_plate_z1() + bh_gap_h;           // 8.0 switch body ledge
function bh_z1()        = bh_apert_z1() + sw_body_h;          // 11.5 deepest point
function plunger_z()    = bh_apert_z1() - sw_plunger_h;       // 6.8 plunger top

function btn_face_bot_z()= btn_recess_depth - btn_face_gap;   // 0.7 cap face underside
function btn_proud()    = btn_face_t - btn_face_bot_z();      // 1.3 proud of the top face
function btn_skirt_h()  = bh_catch_z() - btn_face_bot_z();    // 3.8 face underside -> lip
function btn_post_h()   = plunger_z() - btn_face_bot_z();     // 6.1 face underside -> plunger

// devkit column, measured down from the top face
function plate_inner_z()= top_depth();                                   // base plate inner face
function s3_pcb_top_z() = plate_inner_z() - s3_seat_h - pcb_t;           // component-side surface
function s3_top_z()     = s3_pcb_top_z() - s3_comp_h;                    // tallest devkit part
function s3_usb_cz()    = s3_pcb_top_z() - usb_recept_h/2;               // rear-window centre

// DAC. The board's position is derived BACKWARDS from where its socket has to end up:
// face just behind the thinned panel, minus the overhang, gives the PCB edge. So a
// wrong dac_w only slides the FAR edge inward and the socket stays on the hole.
function dac_pcb_edge_x() = outer_w()/2 - jack_panel_t - dac_socket_setback - dac_jack_overhang;
function dac_cx()       = dac_pcb_edge_x() - dac_w/2;
// ...and its y is derived the same way, from the hole: shift the board by exactly the
// socket's own corner offset so the socket ends up behind a CENTRED hole.
function dac_pos_y()    = jack_hole_y - dac_jack_off();
function dac_pos()      = [dac_cx(), dac_pos_y()];
// Pocket is OPEN at +x (the socket overhang passes over its end) and stops at the
// register lip, so for collision purposes its footprint runs from its -x wall to there.
function dac_pocket_x0()= dac_cx() - dac_w/2 - board_clr - pocket_wall;
function dac_pocket_x1()= lip_inner_half();
function dac_pocket_c() = [(dac_pocket_x0() + dac_pocket_x1())/2, dac_pos_y()];
function dac_pocket_f() = [dac_pocket_x1() - dac_pocket_x0(), dac_l + 2*board_clr + 2*pocket_wall];
// The DAC pocket's x-SIZE is independent of `plan`: both its ends are referenced to the
// +x wall (the socket sets one, the register lip the other), so growing the case slides
// it outward without resizing it. That is what makes plan_min() below non-circular.
function dac_pocket_w() = dac_w + board_clr + pocket_wall
                        + jack_panel_t + dac_socket_setback + dac_jack_overhang
                        - wall - clr - reg_t;

// ---- how big the case has to be, derived from the boards -------------------------
// `plan` was twice set by eye and twice turned out smaller than the boards. These give
// the floor instead, and an assert holds `plan` to it. Four separate constraints:
//
//  * width   — the devkit must be CENTRED in x. With four corner bosses there is no
//              alternative: the devkit spans nearly the full depth, so a boss pushed to
//              one side always lands inside it in y, and only x clearance can save it.
//              Centring it means the DAC has to begin beyond HALF the devkit pocket,
//              which is what makes this the binding constraint (and what stacking the
//              two boards instead would avoid entirely).
//  * bosses  — each pocket must clear the corner pillars in plan.
//  * depth   — the taller pocket must fit between the register lips.
function plan_from_width()    = 2*(s3_pocket_f()[0]/2 + board_gap + dac_pocket_w()
                                  + wall + clr + reg_t);
function plan_from_boss_s3()  = 2*(s3_pocket_f()[0]/2 + boss_od/2 + boss_inset);
function plan_from_boss_dac() = 2*(abs(dac_pos_y()) + (dac_pocket_f()[1] + boss_od)/2 + boss_inset);
function plan_from_depth()    = 2*(max(s3_pocket_f()[1], dac_pocket_f()[1])/2 + wall + clr + reg_t);
function plan_min()           = max(plan_from_width(), plan_from_boss_s3(),
                                    plan_from_boss_dac(), plan_from_depth());

// ---- and how DEEP it has to be, likewise derived ---------------------------------
// Same story as plan_min(), one axis over. cavity_depth used to be guarded by a
// hard-coded "outer_d() == 29" tripwire, which stopped meaning anything the moment
// s3_comp_h became a measured number: the devkit's component stack is what sets the
// interior height, and the things hanging off the top face are what it has to clear.
//
// Three constraints, in increasing order of demand:
//   * bare      — the devkit's tallest part just misses the top face
//   * mic       — it also clears the mic board on its posts
//   * button    — it also clears the button holder, which reaches deepest of all
function cavity_for(clearance_z) = clearance_z + s3_seat_h + pcb_t + s3_comp_h - wall;
function cavity_from_bare()   = cavity_for(wall);
function cavity_from_mic()    = cavity_for(wall + mic_post_h + pcb_t + 2);
function cavity_from_button() = cavity_for(bh_z1() + 2);
function cavity_min()         = max(cavity_from_bare(), cavity_from_mic(), cavity_from_button());
// Board sits component-side UP (toward the top face) on the plate, so the socket
// stands above the PCB, i.e. at LOWER z than it.
// Board sits COMPONENT SIDE UP: the socket stands above the PCB, at the height the wall
// cutout is cut for, and the pin tails point down into the floor relief.
function dac_pcb_top_z()= plate_inner_z() - dac_seat_h - pcb_t;   // component-side face
function dac_top_z()    = dac_pcb_top_z() - dac_jack_h;           // socket top: highest point
function dac_jack_cz()  = dac_pcb_top_z() - dac_jack_h/2;         // counterbore centre
function dac_axis_z()   = dac_pcb_top_z() - dac_jack_axis;        // barrel axis = hole centre
// Socket centre in y. Derived from the board END, not from its centre — the socket sits
// in the corner, so this is the number the wall cutout must follow.
function dac_jack_off() = dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2);
function dac_jack_y()   = dac_pos_y() + dac_jack_off();

// pull-out stop. Projection is the gap between the wall's inner face and the board's
// edge, so the rib IS the board's x datum. It exists only because the socket overhangs
// the PCB by more than the wall's unthinned remainder (wall - jack_panel_t).
function jack_stop_proj() = inner_half() - dac_pcb_edge_x();
function jack_stop_z0()   = dac_pcb_top_z() + jack_stop_clr;      // top: socket clears above
function jack_stop_z1()   = top_depth() - reg_h - clr;            // bottom: lip clears below
function jack_stop_y0()   = dac_jack_y() + dac_jack_w/2 + jack_stop_y_clr;
function jack_stop_y1()   = dac_pos_y() + dac_l/2 - jack_stop_inset;

// mic clamp: the pad has to bridge from the post tops down to the seated board
function mic_board_top_z() = wall - mic_seat_depth + pcb_t;
function mic_clamp_pad_h() = (wall + mic_post_h) - mic_board_top_z();
function mic_clamp_len()   = mic_post_pitch + mic_post_od;
