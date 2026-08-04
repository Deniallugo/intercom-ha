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
// 3.5 mm socket) + INMP441 mic + one 4x4 tactile switch under a sprung printed cap. Power
// and flashing are the devkit's own USB-C. Nothing else is panel-mounted, and the
// only wires in the box are digital.
//
// Axes. +y is the FRONT (toward you), -y the REAR (the USB cable leaves there), +x
// the side the audio leaves, and z runs from the TOP face (z = 0) down into the box.
// The shell prints top-face-down, which is why the top edge is a 45 deg chamfer and
// not a fillet — a fillet would start horizontal on the build plate.
//
// Layout: both boards lie FLAT on the base plate in friction pockets, side by side in x
// — devkit pushed against the -x corner bosses, DAC on the +x side where its socket
// reaches the wall. The top face carries only the mic and the button module. Nothing
// hangs off the lid, which is what the DAC requires: it has no mounting holes, so it has
// to sit on a floor with gravity holding it. What the case costs for that is footprint —
// see plan_x_min() / plan_y_min().
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall         = 3;          // walls, top face and base plate
// Rounded vertical corners. Tempting to widen this — it moves where the +x wall stops being
// flat, which is how far forward the jack hole can sit — but it is capped at ~12.4 by the
// REGISTER LIP, not by the wall.
//
// In the corners the boss and the lip share the same arc centre (plan/2 - radius), so growing
// the radius walks the lip inward while the bosses stay put, until the boss sits straight
// across the lip's annulus and the base plate cannot seat. At 17 the boss reached 13.90 into
// a 12.40..13.60 annulus. Thinning the wall does not rescue it either: that needs wall 1.5.
radius       = 12;
chamfer      = 5;          // 45 deg top-edge chamfer (prints support-free top-down)
// NOT square any more, and not a style choice either way — each axis is set by the boards
// and the two no longer want the same number. plan_x_min() and plan_y_min() below compute
// the floors.
//
// It used to be 96, and the 16 mm came off by UN-CENTRING THE DEVKIT. The old rule was
// that a board 67 mm deep has no y escape from the corner bosses, so it had to be centred
// in x — which is true, but centring is not the only way out: what the bosses actually
// demand is that the pocket sit clear of them in x, and pushing the pocket up against the
// -x pair does that just as well while handing the whole saved offset to the DAC. Centred,
// the DAC had to begin beyond HALF the devkit pocket (17.6 mm of dead plate on the -x
// side); pushed over, it begins just past the pocket's own edge. See s3_pos_x below.
//
// Then the devkit pocket lost 4 mm of WIDTH when s3_l was corrected from 30 to 26, and 2 mm
// of DEPTH when s3_w was corrected from 67 to 65. For a while the two floors were within half
// a millimetre of each other, which is why the case was square and squareness was free.
//
// Sharing ONE wall between the two beds broke the tie. Width lost the 3 mm channel and one of
// the two 1.6 mm walls that used to stand back to back in it; depth lost nothing, because
// depth is the 65 mm board and there is no wall to save along it. The two floors are now 4 mm
// apart, and spending that on squareness would be spending it on nothing — the +x half of the
// case would just get wider than the DAC needs.
plan_x       = 72;         // across x — the two beds side by side, sharing one wall
plan_y       = 76;         // along y — the devkit's length, and nothing else
// Interior height, floored by cavity_min() at 28.35 for an 11 mm component stack. What sets
// it is not the devkit (which needs only 16.1) and not even the button holder's own floor —
// it is the four SWITCH PINS hanging through that floor, whose tips reach 13.25 mm down and
// whose solder joints are the lowest thing on the top face assembly.
//
// 29 rather than 28 for exactly that reason: the 11 mm switch's pins cost the millimetre. If
// you clip them shorter than sw_pin_len this comes straight back.
cavity_depth = 29;

// ---- corner screws (M3 heat-set inserts) ----
// Inserts, not self-tap: the base plate is the only access to every solder joint in
// the box, so this joint gets opened repeatedly. Same call the speaker case made.
boss_od       = 8;
insert_m3_d   = 4.0;       // heat-set insert bore
screw_clear   = 3.4;
screw_cbore_d = 6.2;       // counterbore in the base plate's OUTER face, so no screw
screw_cbore_h = 1.6;       // head stands proud to scratch the desk
// Pushed well into the corners. This is not cosmetic: the bosses are full-depth pillars,
// and since the devkit pocket is now parked against the -x pair, THIS NUMBER SETS s3_pos_x
// — and through it the whole footprint. Every millimetre of inset is a millimetre of
// plan_x (see plan_x_min), so it wants to be as small as the corner allows.
// The floor is the boss fitting inside the inner rounded corner AND inside the register
// lip that passes through the same corner, both asserted below; at radius 12 that floor is
// 9.6, so 10 leaves 0.4 mm and there is no more to win here without shrinking `radius`.
boss_inset    = 10;

// ---- boards [confirm vs hardware] ----
// MEASURED off the actual boards.
//
// s3_l was 30 and is now 26 — the pocket built to 30 was 4 mm wider than the board needed,
// which is most of why the devkit rattled in it. 30 was measured over something that is not
// the laminate (a DevKitC-1's PCB is 25.4 across), and a pocket referenced to anything but
// the PCB edge cannot grip the PCB edge.
//
// s3_w was 67 from the same session and is now 65, measured. It is the binding constraint on
// the whole footprint — plan_y_from_depth() is just this plus two walls, two lips and two
// clearances — so a millimetre off it is a millimetre off the puck, and the 2 mm took the
// case from 78 to 76.
s3_w = 65; s3_l = 26;      // ESP32-S3 devkit; LONG AXIS ALONG Y, USB-C end at the rear
// ONE wall between the two beds, not two standing back to back with a gap. Each pocket still
// draws its own `pocket_wall` on that side, but the cavities are set exactly this far apart,
// so the two walls overlap and the union comes out as a single rib of exactly this thickness.
// 2.0 rather than 1.6 because it is doing two jobs: it retains the devkit's +x edge and the
// DAC's -x edge, and it is a free-standing wall 12.6 mm tall on the DAC side.
//
// It replaced 1.6 + 3 + 1.6 = 6.2 mm of wall-gap-wall, and that 4.2 mm is what took plan_x
// from 76 to 72. The 3 mm gap was carrying two vent slots; those moved to the -x strip, which
// was always going to be dead plate anyway.
shared_wall = 2.0;
// PCM5102A "LINE" breakout — the purple board. Its 3.5 mm socket sits on a LONG SIDE
// (the edge silkscreened LINE / L R G), barrel pointing sideways out of that edge and
// the body OVERHANGING it. So the board is turned 90 deg here: LONG AXIS ALONG Y, that
// socket edge facing +x. Every gold pad on it is a header position — there are NO
// mounting holes, so it sits in a friction pocket like the devkit, not on standoffs.
// Turning it sideways costs little: it needs ~22 mm of x, which leaves the devkit the
// whole middle of the plate.
dac_w = 20;                // board size across x (its SHORT dimension)  [measured]
dac_l = 33;                // board size along y (its LONG dimension)    [measured]
// How much of the shell's bottom RIM the socket counterbore may eat into. It used to reserve
// 1.5 mm; spending it is what lets the floor come down to 7. The cost is a ~7 mm interruption
// in the rim the base plate seats against, right where the socket is — the plate closes the
// counterbore off there instead of seating against wall.
jack_cb_rim_margin = 0.1;
// MEASURED CORRECTION, from the board sitting in the printed plate. The derived chain (pocket
// floor + pcb_t + dac_jack_axis) puts the socket 3 mm LOWER than where it actually ends up —
// the board rides proud, most likely because the real socket is taller than the 6.5 recorded
// and bottoms in the recess before the PCB reaches its seating plane.
//
// Applied to the SHELL's counterbore and plug hole only. The plate is untouched: its recess
// stays where it was printed, and being 3 mm deeper than the socket needs is harmless. This is
// a trim on estimate error, not a design change — if dac_jack_h and dac_jack_axis ever get
// measured properly, this should fall back to 0.
jack_z_rise = 3.0;
// Deep enough to HOUSE THE SOCKET. The board sits component-side DOWN, so the socket hangs
// below the PCB into a recess in this floor — which is the only way to get the jack hole
// near the base plate. Component-side UP put the axis 8 mm above the plate at best, leaving
// the hole 4.5 mm short of the seam; this gets it to 1.9 mm.
//
// 8.6 is not arbitrary: what binds is the socket's COUNTERBORE not breaking the base rim
// (it must end 1.5 mm above the seam), which caps how shallow the floor can be. 8.4 is the
// exact limit; 8.6 leaves 0.2 mm on it.
dac_seat_h = 7.0;          // PCB seating plane above the plate — AS PRINTED, frozen
// With the board flipped the socket is cradled inside the floor recess, not standing above
// the PCB, so the lip no longer has to cover it — it only retains the PCB edge and shrouds
// the pin tails, which now point UP.
dac_lip    = 4.0;
mic_board_w = 17; mic_board_l = 15;   // INMP441 breakout, 17 x 15 [measured]
pcb_t             = 1.6;
pocket_wall       = 1.6;   // friction-pocket wall (boards without usable mount holes)
board_screw_pilot = 1.6;   // M2 self-tap
screw_m2_d        = 2.0;   // the screw itself. Only used to work out how far a part can
                           // float in its own clearance holes, which is what sets the
                           // button holder's bore clearance.
// PER-SIDE clearance in the friction pockets — deliberately looser than the global `clr`,
// which is for parts that locate precisely. Both pockets were first built on `clr` (0.4)
// and both came out SMALLER than the real boards: printed pocket walls come in slightly
// proud, PCB edges carry snap-tab burrs, and the nominal footprints below are approximate
// to begin with. 1.0 per side is 2 mm oversize on both axes, which absorbs up to 2 mm of
// error in those nominals.
//
// The DAC keeps it. It is captured in a way the devkit is not — its socket sits in a
// zero-clearance recess in the floor and then inside the shell's counterbore, so the board
// is located by the socket and the slack in the pocket never shows.
board_clr = 1.0;
// The DEVKIT does not keep it, because there is nothing else locating that board and 2 mm
// of slack is 2 mm of rattle — and it lands straight on the USB-C window, which is the one
// opening that has to line up with something.
//
// 0.6 is a deliberate midpoint, not a measurement: at 0.4 the printed pocket came out
// smaller than the board and at 1.0 the board moves in it, so the truth is between them and
// this is the number to tune. Do NOT tune it by reprinting the plate — that is four hours a
// go. Print `part="fit"`: a 25 mm slice of the front of this pocket, including the retention
// tab, that tells you in ten minutes whether the board slides in and stays put.
//
//   board will not go in / needs force  ->  raise in 0.1 steps
//   board rocks side to side            ->  lower in 0.1 steps
s3_board_clr = 0.6;
// ---- devkit retention: the pocket is a SLOT, not a tray ---------------------------
// Three features, and the reason there are three is that the devkit is the only board in
// here with nothing else locating it:
//
//   * the FRONT WALL is the register lip, locally raised. It used to be a separate wall
//     standing 1.6 mm inboard of the lip, which cost 1.6 mm of depth for nothing — the lip
//     is already a 1.2 mm rib in exactly that place, and the only reason it could not serve
//     as the pocket wall is that it is 2 mm tall. Growing it to full pocket height over the
//     board's width costs no plan at all, and that 1.6 mm is what pays for the rear stops.
//   * the REAR STOPS, two blocks on the lip's own footprint at the corners, flanking a notch
//     for the USB. This is what "closes" the rear end. It could not be a wall: the notch has
//     to be wider than the USB window or it blocks the ports, which is the failure the open
//     rear was introduced to fix in the first place. Outside the window's span nothing is
//     blocked that the shell was not blocking anyway.
//   * the TAB over the board's front edge, which preloads it BACK against those stops. That
//     is what makes the board's y position deterministic now that it no longer registers
//     against the shell's rear wall.
//
// The tab is on the SHORT edge on purpose. The long +-x edges are where the devkit's header
// rows are, and a header body starts within a millimetre of the PCB edge and stands ~8.5 mm
// tall, so anything reaching in over a long edge fouls it. The short front edge (the one away
// from the USB) is the only side of this board with clear air above the laminate.
//
// Assembly is a tilt, not a straight slide any more: hold the board rear-up about 2 deg, put
// its front edge under the tab, push forward until the rear drops behind the stops. Set
// s3_tab_cover = 0 and s3_rear_stops = false to get the plain open tray back.
s3_rear_stops  = true;
// How far the stops stand above the board's SEATING PLANE. Capped at the PCB's own thickness
// and that cap is the whole assembly story: taller, and the board is captured in z at both
// ends before it is in, which is a part you cannot put together. At pcb_t it catches the full
// edge and the rear corners still clear it on a 2 deg tilt.
s3_rear_stop_h = pcb_t;
s3_tab_cover  = 1.2;       // how much of the board's front edge the tab sits over
s3_tab_w      = 10;        // across x, centred — narrow, to stay between the header rows
// PRELOAD, not a gap. The tab's underside is derived from where the board's front edge
// actually is, so it holds whatever the front clearance turns out to be — and that clearance
// is now derived too (s3_front_clr), so a fixed gap would silently stop touching the board
// the moment `plan` or s3_w moved. 0.1 mm is a push, not a press; the ramp is 45 deg so it
// is self-limiting. Raise toward 0 if the board will not go in.
s3_tab_preload = 0.1;      // how far the ramp reaches below the board's top face, AT its edge
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
// The devkit's relief length is PINNED rather than derived from s3_w, so growing the board
// lengthens its pocket without lengthening the channels. Anchored at the rear end, which
// does not move when s3_w changes (s3_cy() shifts by exactly half the growth).
s3_relief_len = 57;
// The DAC channel stops SHORT of the +x wall rather than running off the floor's edge. It is
// the jack's access, and it needs a land between it and that wall, not an open end.
dac_relief_wall_gap = 3.0;
// ONE width for both cuts in the DAC floor: the relief channel and the socket recess. With a
// 6 mm socket this is a ZERO-CLEARANCE recess — the socket is exactly as wide as the slot it
// drops into. That is deliberate, but it is the one dimension here with no tolerance in it:
// printed pockets come out slightly undersize, so if the socket will not seat, 6.8 (socket +
// clr each side) is the number that makes it drop in freely.
dac_cut_w = 6;
function dac_relief_w()  = dac_cut_w;
function dac_recess_w()  = max(dac_cut_w, dac_jack_w);
// The devkit sits in a pocket on the base plate. The floor is 3.5 mm rather than a
// bare 1.6 mm because the floor height is what sets the USB-C receptacle height, and
// the rear window has to stay a BOUNDED hole with material left below it.
s3_seat_h = 3.5;           // pocket floor under the devkit
// Back at 3.5. It went to 4.5 to fit the retention tab's 45 deg ramp between the PCB's top
// face and the wall's top; with the tab's underside now BELOW that face the ramp starts a
// millimetre lower and 3.5 is enough again (it needs 2.7). Asserted either way.
s3_lip    = 3.5;           // pocket wall standing above the seated board
s3_comp_h = 11;            // tallest thing on the devkit's component side: soldered
                           // 2.54 headers (~8.5) plus dressed wire, 11 mm total [measured]

// plan placements (x, y). The DAC's x is DERIVED, not set — see dac_pos() below.
// Both big boards live on the BASE PLATE, side by side in x: the devkit runs along y
// down the -x side, the DAC along x on the +x side. Nothing hangs off the top face
// any more except the mic and the switch seat, which is also what makes the DAC
// mountable at all — a friction-pocketed board with no screw holes has to sit on a
// floor with gravity holding it, not hang upside down off the lid.
// Devkit x is DERIVED, and the thing it is derived FROM changed when the two beds started
// sharing a wall. It used to be parked against the -x corner bosses, with everything left
// over going to the DAC; now it is parked against the DAC — one shared_wall inboard of that
// board's cavity — and the boss clearance is what falls out at the other end.
//
// That is the right way round now. The DAC's x is not free: it is pinned by its socket having
// to reach the +x wall. So the DAC is the fixed end of the chain, the devkit hangs off it, and
// plan_x is whatever leaves the devkit's outer wall clear of the bosses (plan_x_min).
//
// The assignment itself lives further down, after the DAC's jack numbers — it reads them
// through dac_cx(), and OpenSCAD evaluates variable assignments in file order, so putting it
// here would silently read them as undef.
s3_boss_margin = 0.8;      // pocket wall to boss, in x — the slack end of the chain now
function s3_pocket_w()  = s3_l + 2*s3_board_clr + 2*pocket_wall;
function s3_cavity_hw() = s3_l/2 + s3_board_clr;      // board cavity half-width
// The two CAVITY faces the shared wall stands between. Collision checks between the pockets
// have to use these rather than the pocket blocks: the blocks deliberately overlap inside the
// shared wall, so "do the blocks intersect" answers yes by design and tells you nothing.
function s3_cavity_x1()  = s3_pos_x + s3_cavity_hw();
function dac_cavity_x0() = dac_cx() - dac_w/2 - board_clr;
// Mic on the front edge, but no longer at y 28: with plan at 76 the flat top face ends at
// 33 and the board + posts are 15.8 deep, so 25.1 is the hard limit and 24 leaves a
// millimetre on it.
mic_pos   = [ 0, 24];      // top face, front edge — centred in x, on the button's axis
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
s3_usb_h      = 10;        // nominal window height (z) before the trims below
// Trimmed ASYMMETRICALLY from measurement of the printed part. z runs from the top face down,
// so "bottom" (the base plate side) is the LARGER z edge and "top" the smaller.
s3_usb_trim_bottom = 2.0;  // taken off the base-plate edge
s3_usb_trim_top    = 2.0;  // taken off the top-face edge
// LOCAL wall thickness behind the window, the same trick the +x wall uses behind the 3.5 mm
// socket and for the same reason: a plug has a fixed amount of shell before its overmold, and
// wall thickness eats it. It was free while the board registered against this wall; now that
// the rear stops hold it 2.2 mm off, 1.2 mm of wall has to come back out of the panel or the
// setback goes from 3.3 to 5.8 against a 6.5 limit.
//
// 1.8 rather than the jack's 1.2: this panel is bigger, it surrounds a 23 mm hole rather than
// a 5 mm one, and a USB-C plug is levered about far harder than a 3.5 mm one.
usb_panel_t   = 1.8;
usb_cb_margin = 2.0;       // how far the thinned patch extends past the window on each side

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
dac_jack_w        = 6.0;   // socket body width along its edge (y)  [measured]
dac_jack_h        = 6.5;   // socket body height above the PCB face (z)
dac_jack_axis     = 3.2;   // barrel AXIS above the PCB face — sets the hole centre
dac_jack_overhang = 2.5;   // how far the socket body sticks past that long edge
dac_jack_depth    = 13.0;  // how far the socket body reaches INBOARD from that edge [MEASURE]
// The socket is NOT centred on its edge — it sits in the board's corner, 3 mm from the
// end. That offset has to be absorbed somewhere, and it is the HOLE that absorbs it:
// dac_jack_y() = dac_pos_y() + dac_jack_off(), so the hole lands 10.5 mm forward of the
// wall's centreline. It used to be the other way round — hole centred, board slid to suit,
// on the grounds that an off-centre hole reads as a mistake while a hidden board does not
// care. That trade is no longer on offer: the board's y is spent clearing the corner
// bosses (see dac_pos_y_set), so there is nothing left to slide.
dac_jack_inset    = 3.0;   // board END edge to the near side of the socket body [measured]
dac_jack_end      = +1;    // which end the socket sits at: -1 = rear (-y), +1 = front
// The derivation is INVERTED from how it started. It used to fix the hole at the middle of
// the wall and move the board to suit; the board's position is set directly now and the
// HOLE follows the socket. The hole therefore lands at the far end of the DAC bed — the
// end away from the vents, at y +10.5 rather than on the wall's centreline.
//
// 0, i.e. CENTRED in y, and that is not cosmetic either: the pocket is 38.2 deep and has
// to pass between the +y and -y corner bosses, so every millimetre of offset costs two of
// `plan` (plan_from_boss_dac). At the old 14.7 it alone demanded 95.6. The ceiling here is
// 6.9; centring spends none of it and leaves the vents a symmetric pair of bays.
dac_pos_y_set     = 0;     // board centre in y, set directly — see plan_from_boss_dac().
dac_socket_setback = 0.5;  // socket face to the thinned panel's inner surface
jack_panel_t = 1.2;        // LOCAL wall thickness at the socket (see above)
// Plug clearance through the thinned panel. Bounded ABOVE by the counterbore behind it: with
// a 6 mm socket that counterbore is only 6.8 wide, so a 7 mm hole plus its 0.6 chamfers (8.2)
// would eat straight through the panel around it. 5 clears a 3.5 mm plug barrel with room.
jack_hole_d  = 5.0;
jack_lead_in = 0.6;        // outer-face chamfer so a plug can't ride the cut edge

// ...and HERE is the devkit's x, now that everything it reads exists. See the note up in the
// plan-placement block for why it hangs off the DAC rather than off the corner bosses.
s3_pos_x = dac_cx() - dac_w/2 - board_clr - shared_wall - s3_cavity_hw();


// ---- button: a scaled TalkingPetDIY dome, in two printed parts ----------------
// The SHAPE is taken from the TalkingPetDIY pet-communication button — a 61.4 mm
// two-part printable button — measured off its meshes and reproduced parametrically at
// this button's OWN size. What was copied is the silhouette and its proportions: a wide
// flange, a straight body stepped in from it, and a top that is one large FILLET rather
// than a spherical dome. Held to the reference's own ratios against the flange:
//
//     feature      reference (Ø57.8)   ratio     here (Ø22)   ratio
//     body         Ø50.0               0.865     Ø19.6        0.891
//     top flat     Ø40.0               0.692     Ø15.6        0.709
//     top fillet   r5.0                0.087     r2.0         0.091
//     height       21.0                0.363     6.5          0.295
//
// THE FLANGE IS Ø22, up from Ø18, and it is the 11 mm switch that did it. An 11 mm square
// body has a 15.6 mm DIAGONAL, and the switch stands up inside the cap's own body bore —
// it has to, because its base sits on the holder's collar floor and its top is therefore
// always above the catch, which is inside the cap. So the cap's bore has to swallow that
// diagonal: Ø17.2 of bore, Ø19.6 of body, Ø22 of flange.
//
// The alternative was to sink the switch BELOW the collar floor, out of the cap's way. That
// keeps the Ø18 button and costs about 5 mm of case height, because the holder then reaches
// 17.5 mm down instead of 11.4 and cavity_depth has to follow. Growing the button costs
// nothing but top-face area, of which there is plenty.
//
// Only `height` drifts far from the reference now: 6.5 mm on a Ø22 flange is a flatter dome
// than 0.363 would give (7.9). Deliberate — the ratio is aesthetic and the 1.4 mm is real
// case height.
//
// The MECHANISM is no longer the reference's. There is NO return spring: the switch is an
// 11 mm tactile with a real spring and real travel of its own, so it does the job the coil
// spring was added to do for a 4x4. What that spring bought was (a) no rattle and (b) a
// stroke you can feel, and both come free here:
//   * no rattle, because the switch's plunger pushes the cap UP against its retention lip
//     and holds it there — btn_preload is how far the post over-travels into the plunger to
//     guarantee that. The cap is preloaded against the lip exactly as before; the spring
//     doing the preloading is just inside the switch now.
//   * a stroke, because an 11 mm tactile travels ~0.7 mm rather than a 4x4's 0.25.
// The switch is still the STOP as well: the plunger bottoms in its own body and the body
// takes the finger load, which is what a tactile switch is built for.
//
// A dome leans more visibly than the flat disc this replaced, and a Ø22 flange leans more
// than a Ø18 one, so the guide matters more: it is the BODY WALL running in a matching bore,
// the shell's own 1.4 mm plus 5 mm inside the holder. See btn_lean() in the asserts.
//
// The two-part split is unchanged and so is the reason for it: the shell keeps only a
// bore, a recess and two blind M2 pilots, so tuning the snap, the travel or the switch
// fit never costs a four-hour shell reprint.

// shell side — a bore, a recess, two blind pilots, nothing else
// Ø19.6, sized so the bore inside it clears the 11 mm switch's 15.6 mm diagonal. Asserted:
// see "cap body must swallow the switch" below. Everything else about the button — the shell
// bore, the holder's guide, the catch, the lip, the collar — chains off this one number.
btn_wall_od      = 19.6;   // cap BODY od
// PER SIDE, body in the shell bore. This is a sliding journal and it is the only thing stopping
// the cap from rocking, so it wants to be tight — but 0.2 was too tight and the printed cap
// seized in its bore. The argument for 0.2 was that both surfaces print as vertical cylinders
// in the same orientation, which is true and still not enough: over a journal this long any
// out-of-roundness in either part binds, and FDM gives you a couple of tenths of that for free.
//
// 0.3 costs lean — btn_lean() goes from 0.69 to 1.03 mm of flange-edge lift against a 1.2 limit
// — and that is the right trade. A cap that leans a millimetre still works; one that seizes does
// not.
btn_guide_clr    = 0.3;
// Deep enough to swallow the whole stroke: the flange is FLUSH with the top face at rest
// (btn_face_gap equals it) and sinks btn_stroke() into the recess when pressed.
btn_recess_depth = 1.6;
btn_pilot_pitch  = 30;     // 2x BLIND M2 pilots, on +-X now: the holder is a Ø21 collar
btn_pilot_depth  = 2.2;    // blind: must not reach the outer face
// No halo groove any more. It existed to make a FLAT 18 mm disc findable by feel on a
// blank face; a dome standing 6.5 mm proud is not something you grope for.

// cap
btn_cap_d    = 22;         // FLANGE od — the diameter you actually see
btn_flange_t = 1.5;
btn_wall_t   = 1.2;        // also the snap: this wall IS the old skirt, and it has to
                           // flex btn_lip_over to get the lip through the shell bore
btn_dome_r   = 2.0;        // the whole top is this one fillet, as on the reference
btn_dome_h   = 6.5;        // apex above the top OUTER face
// No free travel any more, and no btn_travel. With the coil spring gone the post rests ON
// the plunger, so the whole stroke is the switch's own. What replaces btn_travel is a
// PRELOAD: the post is made deliberately LONG, so that with the cap's lip against the catch
// it has pushed the plunger this far past its free position. That is what pins the cap
// against the lip and kills the rattle.
//
// Long, not short, and the direction matters. Print the post short and the cap rests on the
// plunger with its lip floating clear of the catch — it then rattles by exactly that error.
// Print it long and the switch is simply a little pre-depressed, which is harmless right up
// until the preload reaches sw_travel and the switch is permanently closed. So this wants to
// be comfortably under sw_travel, and it is asserted against it.
btn_preload  = 0.25;       // post over-travel into the plunger, cap's lip on the catch
btn_face_gap = 1.6;        // flange to the recess floor at rest. Must clear the whole
                           // stroke, or the flange bottoms before the switch closes.
btn_lip_t    = 1.0;
btn_lip_over = 0.8;        // radial catch beyond the body od
// Spare relief below the lip at full press — and it turns out to be TWO clearances, not one.
// Because bh_relief_h() is lip + stroke + slack and bh_relief_z1() is the catch plus that, this
// single number is simultaneously
//   * the room left under the lip in its relief, and
//   * the gap between the cap body's far edge and the collar floor
// (subtract the chains and both come out as exactly btn_lip_slack). At 0.3 the printed cap
// bottomed out on one or both and had no travel at all. 0.8 costs 0.5 mm of holder depth, which
// cavity_depth 29 still absorbs.
btn_lip_slack = 0.8;
// 8 rather than 6. The lip has to collapse 0.6 mm radially to pass the shell bore, and it does
// that by flexing six 1.2 mm fingers only 5.5 mm long — stiff enough that shoving it in is what
// wedged it. More slits means narrower fingers and the same collapse for much less force.
btn_slits    = 8;          // radial slits so the lip can collapse through the shell bore
btn_slit_w   = 1.0;
btn_slit_z0  = 3.5;        // case z where the slits START — below the top face, so the
                           // only way to see one is to look up under the flange
btn_post_d      = 2.0;     // central post, dome underside down to the plunger. It must not
                           // overhang the plunger — asserted against sw_plunger_d.

// holder — a CUP, not a plate. The guide bore, the catch, the lip relief and the switch all
// live inside one Ø25.2 collar, and it prints FLOOR-DOWN like any cup.
//
// It got SIMPLER when the coil spring went. There is no boss any more: the boss existed only
// to raise a rim for the spring to seat on and to sink a pocket inside that rim, and with no
// spring there is nothing to seat. The switch now stands directly on the collar floor, and
// the only things in the floor are its four pin windows and the two screw holes.
//
// Standing the switch inside the guide rather than below it is still what keeps this shallow.
// Stack guide + relief + aperture + switch body in series below the top face, as the first
// flat-plate holder did, and the module reaches ~17.5 mm down — into the devkit. Side by side
// it is 11.4, which is less than the sprung version managed (12.15).
bh_guide_h   = 5.0;        // guide bore below the top wall — the far half of the journal
bh_floor_t   = 1.6;        // collar floor, under the switch
bh_guide_clr = 0.45;       // PER SIDE, body in the HOLDER's bore. Looser than the shell's
                           // 0.3 on purpose: the holder is located by two M2s in 2.2 mm
                           // clearance holes, so it can sit ~0.1 off axis, and a bore as
                           // tight as the shell's would then pinch. The shell bore is the
                           // precise journal; this one only has to stop the far end.
bh_wall      = 1.6;
bh_ear_d     = 7;          // screw POST od. Full height, not a tab on a gusset: the part
                           // prints floor-down, so a tab standing off the collar is an
                           // overhang and a post is just another vertical wall. It also
                           // leaves the driver a straight shot at the head.
bh_fin_t     = 3;          // web tying each post back into the collar
bh_screw_clear   = 2.2;    // M2 clearance up the posts. Tighter than the usual 2.4 — with
                           // no spigot registering the collar in the shell bore, these two
                           // holes are what bound how far off axis it can sit.
bh_screw_cbore_d = 4.0;    // head counterbore at the floor: an M2 head standing proud
bh_screw_cbore_h = 1.2;    // here would eat the gap to the devkit
// The posts take M2x10: 9.1 mm of collar, less the counterbore, plus btn_pilot_depth.

// ---- 11 x 11 tactile switch, 4 pins [MEASURE — these place the whole mechanism] ----
// An 11 mm square 4-pin tactile with a pin plunger on top — the 12x12 family. It is not a
// drop-in for the 4x4 this case used, and it changed the button in two ways:
//   * it is big enough to have a usable spring and stroke of its own, so the coil spring
//     came out entirely (see btn_preload)
//   * its 15.6 mm DIAGONAL does not fit a Ø13.2 cap bore, so the cap grew to Ø22
//
// The four pins go straight DOWN through the collar floor and are soldered below it, inside
// the case. That is a change of route as well as of count: a 4x4's two legs came out
// SIDEWAYS through the pocket wall and along the floor because there was a boss in the way
// and nowhere else to go. With no boss the floor is the direct route.
//
// The height is given as ONE number, plunger included, because that is the one you can put a
// caliper across and because it is the only thing the cap's post length depends on:
//
//     plunger_z() = bh_relief_z1() - sw_h            <- the split does not appear
//     btn_post_h() = plunger_z() + btn_preload - btn_ceil_z()
//
// The body/plunger split only decides where sw_top_z() falls, and the one thing that cares
// about that is the body staying clear of the cap's dome. So sw_h is measured and sw_body_h()
// is derived from it, rather than the other way round — that way a wrong guess at the plunger
// height cannot quietly change the post.
//
// Only two of these are geometrically fussy. sw_plunger_d must exceed btn_post_d or the post
// overhangs the plunger onto the body and jams; sw_travel must exceed btn_preload with room
// to spare or the switch sits permanently closed. Both are asserted.
sw_body       = 11.0;      // body footprint, square [measured]
sw_h          = 8.0;       // total height above the seating plane, EXCLUDING the pins [measured]
sw_plunger_d  = 3.0;       // the pin on top [MEASURE — must exceed btn_post_d]
sw_plunger_h  = 1.8;       // how far it stands proud of the body [MEASURE — split only]
sw_travel     = 0.7;       // actuation travel [MEASURE — must exceed btn_preload]
// The pin field. Two pins on each of two OPPOSITE SIDES, standing OUTBOARD of the body rather
// than under it — the legs leave the side faces and bend down clear of the outline.
//
// How far out is the number this design kept getting wrong. It has been a square pitch, then a
// [7, 5] rectangular pitch reading "2 mm from the side" as 2 mm INBOARD, then 2 mm OUTBOARD,
// which put the pins 7.5 mm off centre — a 15 mm field on an 11 mm body, and too much.
//
// So it is not a position any more, it is a RANGE. Each window is a radial SLOT running
// sw_pin_slack either side of the nominal, which makes the part tolerant to the one dimension
// nobody has managed to pin down: as drawn it accepts a pin standing anywhere from flush with the
// side face to 2.5 mm out. Getting sw_pin_out exactly right stops mattering, which is the point
// — three wrong readings is enough evidence that it should not have to be exact.
//
// The cost is small: the slots overlap the body's outline by 0.5 mm each, so the floor the switch
// stands on goes from 121 to 115 mm2.
sw_pin_axis   = 0;         // 0 = pins on the +-x sides, 1 = +-y. The body is square, so this is
                           // only which way round you drop it in.
sw_pin_out    = 1.0;       // nominal: how far a pin stands OUT from the body's side face
sw_pin_slack  = 1.5;       // the slot runs this far either side of that, so it need not be exact
sw_pin_gap    = 5.0;       // the two pins on one side, apart [measured]
// 2.2 across, not 2.8. The two dimensions have to share the 5 mm between a side's pins: slot
// width, then the locating rib, then clearance either side of it. 2.8 left only 2.2 mm of gap and
// the rib could not fit in it with any margin. Narrowing to 2.2 is the right side to give on —
// across the pins is the direction we actually know, because sw_pin_gap was measured directly,
// while the outboard direction is the guess and that is where the slot is long.
sw_pin_win    = 2.2;       // window WIDTH, across the pinned axis
sw_pin_len    = 3.5;       // how far the pins reach below the body [MEASURE] — this is what
                           // sets the module's real depth, not bh_z1()
// ---- locating the switch: four ribs, not a pocket -------------------------------------
// The switch had nothing holding it in place. With no boss, no pocket walls and windows sized
// loose enough to accept an unmeasured pin field, the only thing stopping it wandering was its
// own pins touching the sides of their windows — and on the 5 mm axis that let it slide 3.5 mm.
//
// The obvious fix, a pocket sunk into the floor, costs depth: every millimetre of pocket is a
// millimetre of cavity_depth, because the switch's base is what sets where its plunger ends up.
// These ribs cost NONE. They stand BESIDE the body at the midpoint of each edge, in the gap
// between the switch (7.78 mm to its corner) and the cap's own bore (8.6 mm radius) — beside
// the switch rather than under it.
//
// One rib per side rather than four at the corners: a corner rib would have to fit in the
// 0.82 mm between the switch's corner and the cap's bore. At the mid-edge there is 3.1 mm.
// Two lengths, because two of the four sides now have pins standing off them. On the CLEAR pair
// the rib runs the full sw_locate_len. On the PINNED pair it has to sit in the gap between that
// side's two pins, so it is short — asserted against sw_pin_gap - sw_pin_win. Without the split a
// rib would stand over a pin window, printing in mid-air over a hole.
sw_locate_clr     = 0.4;   // per side, switch inside the ribs. Raise if it will not drop in
sw_locate_t       = 1.6;   // rib thickness, radial
sw_locate_len     = 5.0;   // rib length, on the two sides with no pins
sw_locate_len_pin = 1.8;   // rib length, on the two sides that have pins — between them
sw_locate_h       = 2.0;   // how far the ribs stand off the floor

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
mic_clamp_w     = 5;       // narrow bar; the pad does the pressing
mic_clamp_t     = 1.25;    // half the original 2.5 — it only has to hold gasket
                           // compression, and the 10 mm pad does the actual pressing
mic_clamp_pad   = 10;      // central pressing pad (square)
mic_screw_clear = 2.4;     // M2 clearance in the clamp

// ---- base plate: registration lip, vents, feet ----
reg_h = 2.0;               // lip nesting into the shell cavity (alignment + light gap)
reg_t = 1.2;

// The box is otherwise closed and an S3 at 240 MHz with PSRAM is not cold. The vents
// face the desk, so they are invisible, and they sit in whatever the two board pockets
// leave free.
// Slots as [x, y, w, l]. FOUR of them, down from eight, and they moved as well as thinned
// out. The channel between the two pockets used to carry half of them; sharing one wall
// closed it, and that was the right trade — the channel was 3 mm of air paid for in plan_x,
// while the -x strip is dead plate the corner bosses force on us whether it is vented or not.
//
// So both remaining banks sit in space the layout already had to leave empty:
//   * the -x STRIP, 11 mm wide and the full depth, between the devkit pocket and the wall.
//     Two slots, wider than the old ones (4.0) to make up for the channel's, and kept short
//     enough in y to miss the corner counterbores. This runs right along the devkit's -x
//     edge, which is the best venting position in the box — the devkit is the only part in
//     here that gets warm.
//   * two BAYS on the +x side, fore and aft of the DAC pocket, opened up by centring the
//     DAC in y. One slot each.
// Four slots at 4x46 and 10x3 is 428 mm2 of open area against the eight slots' 564 — fewer
// holes, not much less air, and a stiffer plate.
//
// Every slot's clearance to the pockets and the screw counterbores is asserted, so if you
// move a plan dimension or a board, run ./test.sh before assuming this list still fits.
vent_rects = [[-29.0, 0, 4.0, 46], [-22.5, 0, 4.0, 46],
              [ 17, -25, 10, 3.0], [ 17, 25, 10, 3.0]];
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
// Every half-dimension is PER AXIS. They are deliberately not wrapped in a generic version
// that picks an axis for you: the whole reason the case could stop being square is that each
// of these has a different value on each axis, and a call site that does not say which one it
// means is a bug waiting for someone to change plan_x.
function outer_w()     = plan_x;
function outer_h()     = plan_y;
function top_depth()   = wall + cavity_depth;
function outer_d()     = top_depth() + wall;
function inner_half_x()= plan_x/2 - wall;
function inner_half_y()= plan_y/2 - wall;
function flat_half_x() = plan_x/2 - chamfer;         // flat top face after the chamfer
function flat_half_y() = plan_y/2 - chamfer;
function boss_cx()     = plan_x/2 - boss_inset;      // corner boss / screw centres
function boss_cy()     = plan_y/2 - boss_inset;
// inner edge of the base plate's registration lip — the real inboard bound for anything
// standing on the plate — and its outer face, which the devkit pocket's front wall and its
// rear stops run out to.
function lip_inner_half_x() = (plan_x - 2*wall - 2*clr)/2 - reg_t;
function lip_inner_half_y() = (plan_y - 2*wall - 2*clr)/2 - reg_t;
function lip_outer_half_x() = (plan_x - 2*wall - 2*clr)/2;
function lip_outer_half_y() = (plan_y - 2*wall - 2*clr)/2;

// board footprints as placed (x-size, y-size) — the devkit is turned 90 deg, so its
// LENGTH is the y dimension here
function mic_size()     = [mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od)];

// ---- devkit: the y datum moved from the shell wall to the plate ---------------------
// It used to register against the SHELL's rear wall: pocket open at -y, board slid back
// until it touched, receptacles as close to the window as geometry allowed. That was the
// right call while the rear was open, and it is why the plug setback was only 3.3 mm.
//
// With rear stops the datum is the plate instead, and the board sits 2.5 mm further forward.
// The setback would have gone to 5.8 against a 6.5 limit, which is not enough margin on the
// one feature in this case that has already failed twice — so the rear wall is LOCALLY
// THINNED behind the window (usb_panel_t), exactly as the +x wall is behind the 3.5 mm
// socket, and the setback lands at 4.0 instead.
//
// Determinism did not come for free either: a board resting between two stops 1.2 mm apart
// is not located. What locates it is the tab, whose 45 deg ramp pushes it BACK against the
// rear stops — so the rear stop face, not the front wall, is the datum, and the setback
// below is computed from it.
function s3_usb_w()     = s3_usb_ports*s3_usb_port_w + (s3_usb_ports-1)*s3_usb_gap + s3_usb_slop;
// The notch between the two rear stops. Wider than the window by clr each side: anything
// narrower and the stops start doing what the deleted rear wall used to do.
function s3_rear_notch()= s3_usb_w() + 2*clr;
// Board rear edge against the stops (which sit on the lip's footprint, inner face at
// lip_inner_half), and everything else follows from that.
function s3_cy()        = -lip_inner_half_y() + s3_board_clr + s3_w/2;
function s3_pos()       = [s3_pos_x, s3_cy()];
// What is left over at the front. DERIVED, not chosen: it is whatever depth `plan` has that
// the board and its rear clearance did not use. The tab's reach chases it, so it can grow
// without the tab losing contact.
function s3_front_clr() = lip_inner_half_y() - (s3_cy() + s3_w/2);
// pocket block: floor and side walls from the lip at the rear, front wall out to the lip's
// OUTER face — i.e. the front wall is the lip, grown to pocket height.
function s3_pocket_y0() = -lip_inner_half_y();
function s3_pocket_y1() = lip_outer_half_y();
function s3_pocket_c()  = [s3_pos_x, (s3_pocket_y0() + s3_pocket_y1())/2];
function s3_pocket_f()  = [s3_pocket_w(), s3_pocket_y1() - s3_pocket_y0()];
// ---- the tab's z chain, all of it derived from the board's front edge ----
function s3_tab_over()  = s3_front_clr() + s3_tab_cover;         // reach off the wall face
function s3_tab_z0()    = s3_seat_h + pcb_t - s3_front_clr() - s3_tab_preload;
function s3_tab_z1()    = s3_tab_z0() + s3_tab_over();           // ramp top = full reach
function s3_wall_top()  = s3_seat_h + pcb_t + s3_lip;
// how far the receptacle sits in from the outer face — a USB-C plug has only ~6.5 mm of
// shell before its overmold. Measured from the THINNED panel, and from the rear stop face
// the board is preloaded against.
function usb_setback()  = usb_panel_t + (inner_half_y() + s3_cy() - s3_w/2);

// ---- button module: one z chain shared by the cap, the holder and the shell bore ---
// Everything below is in case z (0 = top OUTER face, +z into the box), so the cap and
// the holder are dimensioned against the same numbers the shell is cut to. Diameters
// chain outward from the cap BODY: body -> shell bore -> holder bore -> lip -> relief
// -> collar. Change btn_wall_od and the whole stack follows.
function btn_bore_d()    = btn_wall_od + 2*btn_guide_clr;      // 20.0 shell bore, the journal
function btn_recess_d()  = btn_cap_d + 2*clr;                  // 22.8 flange recess
function btn_wall_id()   = btn_wall_od - 2*btn_wall_t;         // 17.2 — must clear sw_diag()
function btn_lip_od()    = btn_wall_od + 2*btn_lip_over;       // 21.2
function btn_top_d()     = btn_wall_od - 2*btn_dome_r;         // 15.6 flat left on top
// 45 deg by construction, not by choice: the cap prints dome-down, so the step out to
// the flange is the one place it could grow an overhang. Deriving the rise from the step
// means it cannot.
function btn_flare_h()   = (btn_cap_d - btn_wall_od)/2;        // 1.2

function bh_bore_d()     = btn_wall_od + 2*bh_guide_clr;       // 20.3 guide bore in the collar
function bh_relief_d()   = btn_lip_od() + 2*clr;               // 22.0 room for the lip
function bh_collar_od()  = bh_relief_d() + 2*bh_wall;          // 25.2
// The lip TRAVELS down its relief, so the relief is the lip plus the whole stroke. The stroke
// is now just what is left of the switch's own travel after the preload has spent some of it,
// which is why this got shorter when the coil spring came out: 1.75 against 2.55.
function btn_stroke()    = sw_travel - btn_preload;            // 0.45 — the press you feel
function bh_relief_h()   = btn_lip_t + btn_stroke() + btn_lip_slack;     // 1.75

// The switch, standing directly on the collar floor. No boss and no pocket walls: the walls
// would have to fit between the switch's 15.6 mm diagonal and the cap's 17.2 mm bore, which
// is 0.8 mm all round, and they are not needed anyway — four pins in four windows locate the
// body, and the plunger's own reaction holds it down against the floor.
function sw_diag()       = sqrt(2)*sw_body;                    // 15.56 — the binding dimension
function bh_pocket()     = sw_body + 2*clr;                    // 11.8, for the collision checks
// How much of the switch's underside still has floor under it once the four pin windows are
// cut. Windows may run PAST the body's edge — that costs nothing, the body is not there — so
// each one's overlap with the footprint is clipped before it is counted.
// Pin slots. `a` is along the pinned axis, `b` across it; sw_pin_axis just swaps them. The slot
// runs sw_pin_slack either side of the nominal along `a`, and is sw_pin_win wide across `b`.
function sw_pin_a()      = sw_body/2 + sw_pin_out;                        // 6.5 nominal
function sw_pin_b()      = sw_pin_gap/2;                                  // 2.5
function sw_pin_a_lo()   = sw_pin_a() - sw_pin_slack;                     // 5.0
function sw_pin_a_hi()   = sw_pin_a() + sw_pin_slack;                     // 8.0
function sw_pin_slot()   = 2*sw_pin_slack;                                // 3.0 long
function sw_pin_pos()    = [for (sa = [-1,1], sb = [-1,1])
                              sw_pin_axis == 0 ? [sa*sw_pin_a(), sb*sw_pin_b()]
                                               : [sb*sw_pin_b(), sa*sw_pin_a()]];
// ...and the slot's own size, in x/y, whichever way round the switch went in.
function sw_pin_win_xy() = sw_pin_axis == 0 ? [sw_pin_slot(), sw_pin_win]
                                            : [sw_pin_win, sw_pin_slot()];
// How much of the switch's underside a slot eats, per axis. Computed, not assumed: the slot runs
// inboard of the body's edge on purpose, so this is no longer zero.
function sw_win_span_a() = max(0, min(sw_pin_a_hi(),  sw_body/2)
                                - max(sw_pin_a_lo(), -sw_body/2));
function sw_win_span_b() = max(0, min(sw_pin_b() + sw_pin_win/2,  sw_body/2)
                                - max(sw_pin_b() - sw_pin_win/2, -sw_body/2));
function sw_seat_area()  = sw_body*sw_body - 4*sw_win_span_a()*sw_win_span_b();  // 115 of 121
// The ribs' envelope: inner face beside the body, and a rib's furthest point from the axis,
// which is what has to clear the cap's bore.
function sw_locate_r0()  = sw_body/2 + sw_locate_clr;                     // 5.9
function sw_locate_r1()  = sw_locate_r0() + sw_locate_t;                  // 7.5
function sw_locate_max() = norm([sw_locate_r1(), sw_locate_len/2]);       // 7.91

function bh_z0()         = wall;                               // 3.0 collar top on the inner face
function bh_catch_z()    = bh_z0() + bh_guide_h;               // 8.0 cap lip lands HERE
function bh_relief_z1()  = bh_catch_z() + bh_relief_h();       // 9.75 collar FLOOR = switch base
function bh_z1()         = bh_relief_z1() + bh_floor_t;        // 11.35 floor's far face
// ...but bh_z1() is NOT the deepest thing any more: the pins hang through the floor and get
// soldered under it, and that is what cavity_depth has to clear.
function sw_pin_z1()     = bh_relief_z1() + sw_pin_len;        // 13.25 pin tips
function bh_deep_z()     = max(bh_z1(), sw_pin_z1());          // 13.25 deepest point
function sw_body_h()     = sw_h - sw_plunger_h;                // 6.2 body alone
function sw_top_z()      = bh_relief_z1() - sw_body_h();       // 3.55 switch body's top face
function plunger_z()     = bh_relief_z1() - sw_h;              // 1.75 plunger top, free.
                                                               // Straight off sw_h: the split
                                                               // cannot reach the post.
// overall footprint, for the collision asserts: the two posts set x, the collar sets y
function bh_plate_w()    = btn_pilot_pitch + bh_ear_d;         // 37
function bh_plate_l()    = bh_collar_od();                     // 25.2

function btn_face_bot_z()   = btn_recess_depth - btn_face_gap; // 0.0 flange flush at rest
function btn_flange_top_z() = btn_face_bot_z() - btn_flange_t; // -1.5
function btn_flare_top_z()  = btn_flange_top_z() - btn_flare_h(); // -2.7 body starts here
function btn_apex_z()       = -btn_dome_h;                     // -6.5
function btn_ceil_z()       = btn_apex_z() + btn_wall_t;       // -5.3 inner ceiling, post root
function btn_proud()        = btn_dome_h;                      // 6.5 proud of the top face
function btn_wall_z1()      = bh_catch_z() + btn_lip_t;        // 9.0 body's far edge
// The post reaches btn_preload PAST the plunger's free position, so with the cap's lip on the
// catch the switch is holding the cap up there. That is the no-rattle condition, and the
// direction is the whole point — see btn_preload.
function btn_post_tip_z()   = plunger_z() + btn_preload;       // 2.70
function btn_post_h()       = btn_post_tip_z() - btn_ceil_z(); // 8.00 free length

// devkit column, measured down from the top face
function plate_inner_z()= top_depth();                                   // base plate inner face
function s3_pcb_top_z() = plate_inner_z() - s3_seat_h - pcb_t;           // component-side surface
function s3_top_z()     = s3_pcb_top_z() - s3_comp_h;                    // tallest devkit part
function s3_usb_cz()    = s3_pcb_top_z() - usb_recept_h/2;               // nominal centre
// The window's real edges after the trims, and the size/centre the shell cuts from them.
function s3_usb_z0()    = s3_usb_cz() - s3_usb_h/2 + s3_usb_trim_top;     // top edge
function s3_usb_z1()    = s3_usb_cz() + s3_usb_h/2 - s3_usb_trim_bottom;  // bottom edge
function s3_usb_h_eff() = s3_usb_z1() - s3_usb_z0();
function s3_usb_cz_eff()= (s3_usb_z0() + s3_usb_z1())/2;

// DAC. The board's position is derived BACKWARDS from where its socket has to end up:
// face just behind the thinned panel, minus the overhang, gives the PCB edge. So a
// wrong dac_w only slides the FAR edge inward and the socket stays on the hole.
function dac_pcb_edge_x() = outer_w()/2 - jack_panel_t - dac_socket_setback - dac_jack_overhang;
function dac_cx()       = dac_pcb_edge_x() - dac_w/2;
// ...and its y is set directly, because the plate has no room left to shift it. The hole
// follows: dac_jack_y() below IS the hole position.
function dac_pos_y()    = dac_pos_y_set;
function dac_pos()      = [dac_cx(), dac_pos_y()];
// Pocket is OPEN at +x (the socket overhang passes over its end) and stops at the
// register lip, so for collision purposes its footprint runs from its -x wall to there.
function dac_pocket_x0()= dac_cx() - dac_w/2 - board_clr - pocket_wall;
function dac_pocket_x1()= lip_inner_half_x();
function dac_pocket_c() = [(dac_pocket_x0() + dac_pocket_x1())/2, dac_pos_y()];
function dac_pocket_f() = [dac_pocket_x1() - dac_pocket_x0(), dac_l + 2*board_clr + 2*pocket_wall];
// The DAC pocket's x-SIZE is independent of plan_x: both its ends are referenced to the
// +x wall (the socket sets one, the register lip the other), so growing the case slides it
// outward without resizing it. That is what makes plan_x_min() below non-circular, and it is
// also why the DAC is the fixed end of the x chain that s3_pos_x hangs off.
function dac_pocket_w() = dac_w + board_clr + pocket_wall
                        + jack_panel_t + dac_socket_setback + dac_jack_overhang
                        - wall - clr - reg_t;

// ---- how big the case has to be, derived from the boards -------------------------
// `plan` was twice set by eye and twice turned out smaller than the boards. These give
// the floor instead, and an assert holds `plan` to it. Four separate constraints:
//
// X is one chain, read from the +x wall inward and asymmetric all the way: the socket sets
// where the DAC sits, the DAC sets where the devkit sits, and what plan_x has to be big enough
// for is the devkit's outer wall still clearing the -x corner bosses. Nothing in it is
// doubled, because nothing about this axis is symmetric.
//
// Y is the devkit's length between the two register lips, plus the DAC pocket having to pass
// between the +-y bosses. That one IS symmetric.
function plan_x_min()         = boss_inset + boss_od/2 + s3_boss_margin
                                + pocket_wall + s3_l + 2*s3_board_clr   // devkit wall + cavity
                                + shared_wall
                                + board_clr + dac_w                     // DAC cavity
                                + dac_jack_overhang + dac_socket_setback + jack_panel_t;
function plan_y_from_boss_dac() = 2*(abs(dac_pos_y()) + (dac_pocket_f()[1] + boss_od)/2 + boss_inset);
// Depth is the devkit's LENGTH between the two register lips: rear stop face, board, and a
// front clearance at least as big as the rear one. Written out rather than measured off
// s3_pocket_f(), which depends on plan_y and made this circular.
function plan_y_from_depth()  = 2*wall + 2*clr + 2*reg_t + s3_w + 2*s3_board_clr;
function plan_y_min()         = max(plan_y_from_depth(), plan_y_from_boss_dac());

// ---- and how DEEP it has to be, likewise derived ---------------------------------
// Same story as plan_x_min() / plan_y_min(), one axis over. cavity_depth used to be guarded by a
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
// bh_deep_z(), not bh_z1(): the switch's four pins hang through the collar floor and get
// soldered under it, and those solder joints are the lowest thing on the whole top-face
// assembly. Using bh_z1() here would leave the pins hanging in the devkit.
function cavity_from_button() = cavity_for(bh_deep_z() + 2);
function cavity_min()         = max(cavity_from_bare(), cavity_from_mic(), cavity_from_button());
// Board sits component-side UP (toward the top face) on the plate, so the socket
// stands above the PCB, i.e. at LOWER z than it.
// ---- DAC z chain: board sits COMPONENT SIDE DOWN --------------------------------------
// The socket hangs BELOW the PCB into a recess in the pocket floor. Two reasons: it puts the
// jack hole down near the base plate (the point of the exercise), and it leaves the SOLDER
// side facing up so the board can be wired in place. Knock-on: the pin tails now point UP
// into the cavity, so they need headroom rather than floor relief.
function dac_seat_z()    = plate_inner_z() - dac_seat_h;   // PCB seating plane = its LOWER face
function dac_pcb_top_z() = dac_seat_z() - pcb_t;           // solder side, facing UPß
// These four carry jack_z_rise: they are where the socket REALLY sits, and they are what the
// shell's counterbore and plug hole are cut from.
function dac_socket_z0() = dac_seat_z() - jack_z_rise;              // socket top, at the PCB
function dac_socket_z1() = dac_seat_z() + dac_jack_h - jack_z_rise; // socket bottom
function dac_jack_cz()   = dac_seat_z() + dac_jack_h/2 - jack_z_rise;
function dac_axis_z()    = dac_seat_z() + dac_jack_axis - jack_z_rise;
function dac_top_z()     = dac_pcb_top_z() - board_pin_h;  // highest point: the tails, now up
// socket recess in the floor: its footprint on the board, running off the +x end
function dac_recess_x0() = dac_pcb_edge_x() - dac_jack_depth - clr;
// Plate-referenced, deliberately WITHOUT the rise: the recess is as printed.
function dac_recess_z1() = dac_seat_z() + dac_jack_h + clr;
// Socket centre in y, and therefore the HOLE's position. Derived from the board END, not
// from its centre — the socket sits in a corner, so this is the number the cutout follows.
function dac_jack_off() = dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2);
function dac_jack_y()   = dac_pos_y() + dac_jack_off();


// mic clamp: the pad has to bridge from the post tops down to the seated board
function mic_board_top_z() = wall - mic_seat_depth + pcb_t;
function mic_clamp_pad_h() = (wall + mic_post_h) - mic_board_top_z();
function mic_clamp_len()   = mic_post_pitch + mic_post_od;
