include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
// Neither plan dimension is a free choice: each is bounded below by the boards, and by a
// DIFFERENT chain, which is why they are no longer the same number. These are the asserts
// that replace guessing at a footprint — they name the value needed rather than letting a
// too-small case fail as a pile of unrelated collisions further down.
assert(plan_x >= plan_x_min(),
       str("plan_x too small for the boards side by side — needs at least ", plan_x_min()));
assert(plan_y >= plan_y_min(),
       str("plan_y too small — needs at least ", plan_y_min(),
           " (devkit length ", plan_y_from_depth(), ", DAC vs bosses ", plan_y_from_boss_dac(), ")"));
// The devkit used to be pinned to x = 0 with a hard assert, on the grounds that a board
// spanning the full depth has no y escape from the corner bosses. True, but the conclusion
// was too strong: what the bosses want is x clearance, and PARKING the pocket against the
// -x pair buys that just as well as centring while giving the DAC the 17.6 mm the -x half
// was wasting. So the rule is now the thing it was standing in for — the pocket sits clear
// of the -x bosses by exactly s3_boss_margin, derived, and this checks the derivation is
// still doing that (clears_bosses below checks the +x pair, which is the end that bites).
// s3_pos_x hangs off the DAC now, one shared wall inboard of its cavity — the DAC is the
// fixed end of the x chain because its socket has to reach the +x wall. This checks the
// derivation still says that, and the boss clearance it leaves is checked separately below.
assert(abs(s3_cavity_x1() - (dac_cavity_x0() - shared_wall)) < 0.001,
       "the two beds no longer share one wall — s3_pos_x has been typed in again");
assert(shared_wall >= pocket_wall,
       "the shared wall is thinner than a normal pocket wall, and it is retaining two boards");
assert(s3_boss_margin > 0, "devkit pocket touches the corner bosses — s3_boss_margin must be positive");
assert(s3_pos_x - s3_pocket_f()[0]/2 >= -boss_cx() + boss_od/2 + s3_boss_margin - 0.001,
       str("devkit pocket eats the -x corner bosses — plan_x must be at least ", plan_x_min()));
// cavity_depth has the same derived floor as `plan`, for the same reason: it is set by
// the devkit's component stack (s3_comp_h) against whatever hangs off the top face. The
// old guard here was a hard-coded `outer_d() == 29`, which stopped meaning anything as
// soon as s3_comp_h became a measured number.
assert(cavity_depth >= cavity_min(),
       str("cavity_depth too shallow for the devkit — needs at least ", cavity_min(),
           " (bare ", cavity_from_bare(), ", mic ", cavity_from_mic(),
           ", button holder ", cavity_from_button(), "), giving outer height ",
           cavity_min() + 2*wall));
assert(outer_d() == top_depth() + wall, "base must be a FLAT plate: outer depth = top_depth + wall");
assert(chamfer < radius, "top chamfer must be smaller than the corner radius");
assert(chamfer > 0 && chamfer < top_depth(), "top chamfer out of range");
assert(flat_half_x() > 0 && flat_half_y() > 0, "top chamfer swallowed the whole top face");
assert(reg_h > 0 && reg_h < cavity_depth, "registration lip out of range");
assert(reg_t > 0 && reg_t < wall, "registration lip must be thinner than the wall");

// ===== corner bosses =====
// They are FULL-DEPTH free-standing pillars, so they are obstacles on every plane in
// the box — that is what forces the two big boards to stack instead of sit side by
// side. Every plan-mounted feature below is checked against them.
assert(boss_od >= insert_m3_d + 3, "corner boss too thin around the heat-set insert");
assert(insert_m3_d > screw_clear, "heat-set bore must be wider than the screw clearance");
assert(screw_cbore_d > screw_clear, "counterbore must be wider than the screw clearance");
assert(screw_cbore_h < wall, "counterbore must not cut through the base plate");
assert(boss_cx() + boss_od/2 <= inner_half_x() && boss_cy() + boss_od/2 <= inner_half_y(),
       "corner bosses run into the side walls");
// The bosses sit well into the rounded corners so the DAC pocket can reach further forward.
// That introduces a bound nothing checked before: pushed too far, a boss breaks out through
// the CURVED part of the wall, which the straight-wall check above cannot see.
//
// It is written PLAN-INDEPENDENT on purpose. A boss offset by boss_inset from each edge sits
// (radius - boss_inset) diagonally off the corner arc's centre whatever the plan is, so this
// bound does not move when the case is resized — which is worth stating, because it is the
// one corner check that survived plan going 96 -> 80 -> 76 -> 72 x 76 untouched.
function boss_corner_reach() = sqrt(2)*(radius - boss_inset) + boss_od/2;
assert(boss_inset < radius,
       "boss_inset past the corner radius — the diagonal corner checks below stop applying");
assert(boss_corner_reach() <= radius - wall,
       str("corner boss breaks out through the rounded corner — boss_inset must be at least ",
           radius - (radius - wall - boss_od/2)/sqrt(2)));
// ...and the tighter bound the wall check misses entirely: the boss must also clear the base
// plate's REGISTER LIP, which passes through the same corner INSIDE the wall. Miss this and
// the boss sits across the lip's annulus and the plate simply will not close — invisible in
// any render of either part alone, because the two parts foul each other, not themselves.
function lip_corner_r_in() = radius - wall - clr - reg_t;
assert(boss_corner_reach() <= lip_corner_r_in(),
       str("corner boss blocks the register lip — the lip cannot slip inside. boss reaches ",
           boss_corner_reach(), " but the lip's inner corner is at ", lip_corner_r_in(),
           ". boss_inset must be at least ", radius - (lip_corner_r_in() - boss_od/2)/sqrt(2)));

boss_cs = [for (sx = [-1,1], sy = [-1,1]) [sx*boss_cx(), sy*boss_cy()]];
module clears_bosses(c, sz, name) {
    for (cb = boss_cs)
        assert(aabb_clear(c, sz, cb, [boss_od, boss_od]), str(name, " clashes a corner boss"));
}
module inside_cavity(c, sz, name) {
    assert(abs(c[0]) + sz[0]/2 <= inner_half_x(), str(name, " off the cavity width"));
    assert(abs(c[1]) + sz[1]/2 <= inner_half_y(), str(name, " off the cavity depth"));
}

// ===== plan layout =====
// Both board pockets live on the BASE PLATE and must not overlap each other; the mic
// seat and the button module hang off the TOP FACE and must not overlap each other. The
// two groups are on opposite parts, so they are checked against each other in z.
// (The button module's own checks live in its section further down.)
inside_cavity(s3_pocket_c(), s3_pocket_f(), "S3 pocket");
inside_cavity(dac_pocket_c(), dac_pocket_f(), "DAC pocket");
inside_cavity(mic_pos,       mic_size(),     "mic seat+posts");
clears_bosses(s3_pocket_c(), s3_pocket_f(), "S3 pocket");
clears_bosses(dac_pocket_c(), dac_pocket_f(), "DAC pocket");
clears_bosses(mic_pos,       mic_size(),     "mic seat+posts");

// The two pocket BLOCKS overlap by design — that is what makes their walls merge into one
// shared rib — so the check is on the CAVITIES, which must stay exactly shared_wall apart.
assert(dac_cavity_x0() - s3_cavity_x1() >= shared_wall - 0.001,
       str("the two board cavities are closer than the wall between them — only ",
           dac_cavity_x0() - s3_cavity_x1(), " mm for a ", shared_wall, " mm wall"));
assert(dac_cavity_x0() - s3_cavity_x1() <= shared_wall + 0.001,
       "the two beds are not sharing a wall any more — there is a gap between the pockets");

// Top-face features must stay on the FLAT face — the chamfer, not the outer edge, is
// the real bound.
assert(abs(btn_pos[0]) + btn_recess_d()/2 <= flat_half_x(), "button recess runs onto the chamfer (x)");
assert(abs(btn_pos[1]) + btn_recess_d()/2 <= flat_half_y(), "button recess runs onto the chamfer (y)");
// ...and the flange is the thing you SEE, so it has to clear the mic port on the same
// face. That was free at Ø18 and is not at Ø38.
assert(norm([btn_pos[0] - mic_pos[0], btn_pos[1] - mic_pos[1]]) >= btn_cap_d/2 + mic_hole_d/2 + 2,
       "button flange runs over the mic port on the top face");
assert(abs(mic_pos[0]) + mic_size()[0]/2 <= flat_half_x(), "mic seat runs onto the chamfer (x)");
assert(abs(mic_pos[1]) + mic_size()[1]/2 <= flat_half_y(), "mic seat runs onto the chamfer (y)");
// ===== plate boards vs top-face features: the vertical checks =====
// The mic and the button module hang down from the top face; the two boards stand up off
// the plate. Where a pair overlaps in PLAN the vertical gap is what keeps the case
// closable, and it is invisible until it isn't. Where they don't overlap the gap is
// irrelevant, so each check is conditional — an unconditional one fires on layouts
// that are perfectly fine, which is exactly what happened when the DAC grew a 6.5 mm
// socket and started standing taller than the devkit.
if (!aabb_clear(dac_pocket_c(), dac_pocket_f(), mic_pos, mic_size()))
    assert(dac_top_z() > wall + mic_post_h + mic_clamp_t + 2, "DAC socket collides with the mic clamp");
assert(dac_top_z() > wall + 2, "DAC socket reaches the top face — deepen cavity_depth");
assert(s3_top_z() > wall + mic_post_h + pcb_t + 2,
       "mic board reaches into the devkit — deepen cavity_depth");
assert(s3_pcb_top_z() > 0 && s3_top_z() > wall, "devkit stack does not fit the cavity at all");

// ===== rear wall: devkit USB-C window + 3.5 mm jack =====
// The window must be a BOUNDED hole: material left above AND below, so the rim that
// meets the base plate stays continuous and the plate still has something to seat on.
assert(s3_usb_z0() >= wall, "USB window runs into the top face — lower the devkit");
assert(s3_usb_z1() <= top_depth() - 1.5,
       "USB window breaks the base rim — raise s3_seat_h or trim more off its bottom");
// The trims must leave a window a USB-C plug can actually pass: the plug is ~2.6 mm thick.
assert(s3_usb_h_eff() >= 2.8,
       str("USB window trimmed to ", s3_usb_h_eff(), " — a USB-C plug is ~2.6 mm thick and will not pass"));
assert(s3_usb_trim_top >= 0 && s3_usb_trim_bottom >= 0, "USB window trims must not be negative");
// The window must expose BOTH receptacles, not straddle the gap between them. This is
// the check that was missing when a 14 mm window left neither port usable: it has to be
// at least as wide as the two ports plus the gap, and it has to stay on the board.
assert(s3_usb_w() >= s3_usb_ports*s3_usb_port_w + (s3_usb_ports-1)*s3_usb_gap,
       "USB window narrower than the ports it serves — no plug would fit either one");
assert(s3_usb_w() <= s3_l + 2*s3_board_clr,
       "USB window wider than the devkit — it would open past the board");
// ...and whatever stands behind the board's rear edge must not stand in front of the PORTS.
// The rule used to be the blunt one — nothing at all behind that edge — because the pocket
// then had a plain rear wall and any notch in it left stubs across the receptacles. Now there
// are rear stops there on purpose, so the rule is the thing it was standing in for: the notch
// between them has to be wider than the window, and nothing else above the seating plane may
// be back there. Below the seating plane does not count; that is floor, under the board.
assert(s3_rear_notch() >= s3_usb_w(),
       str("rear stops narrower apart than the USB window — they would sit across the ports. ",
           "s3_rear_notch() is ", s3_rear_notch(), " and the window is ", s3_usb_w()));
assert(s3_rear_notch() <= s3_l + 2*s3_board_clr - 2,
       str("rear stops have no width left — the notch is ", s3_rear_notch(),
           " in a cavity of ", s3_l + 2*s3_board_clr,
           ". s3_usb_slop() tracks s3_board_clr, so this means the pocket itself is too narrow"));
assert(s3_pocket_y1() > s3_cy() + s3_w/2, "devkit pocket has no +y wall to locate the board");
// Reach check. A USB-C plug has only ~6.5 mm of shell before its overmold. The board no
// longer registers against this wall — it is held 2.2 mm off it by the rear stops — so what
// pays for that is the locally thinned panel, and this is the assert that says whether it
// paid enough.
assert(usb_setback() <= 6.5,
       str("USB receptacle sits too deep for a plug to reach — setback is ", usb_setback(),
           ". Thin usb_panel_t, or move the board back toward the wall"));
// The thinning itself. Thicker and it is not buying anything; thinner and a 23 mm hole in a
// wall a plug gets levered against starts to tear.
assert(usb_panel_t >= 1.5 && usb_panel_t < wall,
       "usb_panel_t out of range — it must actually be thinner than the wall, and at least 1.5 to survive a plug");
// The thinned patch must not eat the bottom rim the base plate seats on, nor run off the flat
// part of the rear wall into the rounded corners or the bosses.
assert(s3_usb_cz_eff() + s3_usb_h_eff()/2 + usb_cb_margin <= top_depth() - 1.5,
       str("thinned USB panel runs into the base rim — it reaches ",
           s3_usb_cz_eff() + s3_usb_h_eff()/2 + usb_cb_margin, " and the rim starts at ", top_depth() - 1.5));
assert(s3_usb_cz_eff() - s3_usb_h_eff()/2 - usb_cb_margin >= wall,
       "thinned USB panel runs into the top face");
assert(abs(s3_pos_x) + s3_usb_w()/2 + usb_cb_margin <= plan_x/2 - radius,
       "thinned USB panel runs off the flat part of the rear wall into a rounded corner");
for (cb = boss_cs)
    assert(abs(s3_pos_x - cb[0]) >= (s3_usb_w() + 2*usb_cb_margin + boss_od)/2,
           "thinned USB panel cuts into a corner boss");

// ===== +x side wall: the DAC's own 3.5 mm socket =====
// The cutout is placed from the BOARD, not set by hand, so it cannot drift away from
// the socket it serves. What can still go wrong is the socket landing off the wall,
// in a corner boss, or past the base rim.
assert(dac_jack_w > 0 && dac_jack_h > 0, "DAC socket body geometry");
assert(abs(dac_jack_end) == 1, "dac_jack_end picks an end: -1 or +1");
assert(dac_jack_inset >= 0 && dac_jack_inset + dac_jack_w <= dac_l,
       "DAC socket does not fit along the board edge — check dac_jack_w/dac_jack_inset vs dac_l");
assert(abs(dac_jack_off()) + dac_jack_w/2 <= dac_l/2,
       "DAC socket falls off the board edge");
// The socket sits in the board's CORNER, so its offset from the board centre is large.
// Guard that it really is out at the end — if this collapses toward zero, the offset has
// stopped being derived from the board and is being typed in again.
assert(abs(dac_jack_off()) >= dac_l/2 - dac_jack_w - 1,
       "DAC socket offset is not at the board end any more — is dac_jack_off() still derived?");
// The hole now FOLLOWS the socket rather than the board following the hole, so alignment is
// structural. What still needs checking is that the hole ends up where it is supposed to:
// at the far end of the DAC bed, the end away from the vents.
assert(dac_jack_end > 0, "socket must sit at the board's FRONT end for the hole to clear the vents");
assert(dac_jack_y() + dac_jack_w/2 <= dac_pos_y() + dac_l/2,
       "socket runs past the board's front edge");
assert(dac_jack_y() - dac_jack_w/2 > dac_pos_y(),
       "socket is not at the far END of the bed — it has drifted back toward the middle");
// the socket must clear the pocket's own end wall, which is just outboard of the board
assert(abs(dac_jack_off()) + dac_jack_w/2 <= dac_l/2 + board_clr,
       "socket body runs into the DAC pocket's end wall");
assert(dac_jack_axis > 0 && dac_jack_axis < dac_jack_h,
       "the barrel axis must lie inside the socket body");

// The local thinning is the whole reason a plug seats. Guard both ends of it: a panel
// thicker than ~1.5 mm eats the plug's insertion depth, and one thinner than 2 layers
// will not survive a plug being levered sideways.
assert(jack_panel_t >= 0.8 && jack_panel_t <= 1.5,
       "jack_panel_t out of range — thicker and a plug will not seat, thinner and the panel tears");
assert(jack_panel_t < wall, "the socket panel must actually be THINNER than the wall");
assert(jack_hole_d > 4.5, "plug hole must clear a 3.5 mm plug and its tolerance");
assert(jack_hole_d + 2*jack_lead_in <= dac_jack_w + 2*clr,
       "plug hole + chamfer is wider than the counterbore behind it — the panel would vanish");
assert(jack_lead_in > 0 && jack_lead_in < jack_panel_t, "socket lead-in chamfer out of range");
// The socket must stay BEHIND the outer skin, or the plate cannot rise into the shell.
assert(dac_socket_setback > 0, "socket face must sit behind the thinned panel, not in it");
assert(dac_pcb_edge_x() + dac_jack_overhang <= outer_w()/2 - jack_panel_t,
       "socket protrudes through the outer skin — the base plate could not be assembled");
// Counterbore bounded within the wall's height. With the board flipped it is the BASE RIM
// that is close, not the top face — and that is exactly what caps how LOW the hole can go,
// so this assert is the one that sets dac_seat_h.
assert(dac_socket_z0() - clr >= wall + 1, "socket counterbore runs into the top face");
assert(dac_socket_z1() + clr <= top_depth() - jack_cb_rim_margin,
       str("socket counterbore runs past the shell's bottom rim — dac_seat_h must be at least ",
           dac_jack_h + clr + jack_cb_rim_margin));

// ---- socket recess in the pocket floor (board is component-side DOWN) ----
// What must hold is MATERIAL UNDER THE SOCKET, and that is the pocket floor PLUS the plate
// beneath it — not the pocket floor alone, which is what this used to measure and why it
// demanded 7.9 when 7 is fine.
assert((plate_inner_z() + wall) - dac_recess_z1() >= 1.5,
       str("too little material under the socket — only ",
           (plate_inner_z() + wall) - dac_recess_z1(), " mm of floor + plate"));
assert(dac_jack_depth > 0 && dac_jack_depth < dac_w,
       "socket body reaches further inboard than the board is wide — check dac_jack_depth");
assert(dac_recess_x0() > dac_cx() - dac_w/2,
       "socket recess undercuts the whole board — nothing left to seat on");
// The limit is the plate's OUTER face, not its inner one — the recess may sink into the plate's
// own 3 mm as long as it does not come out the bottom of the case.
assert(dac_recess_z1() < plate_inner_z() + wall - 0.8,
       str("socket recess breaks through the bottom of the plate — it reaches ", dac_recess_z1(),
           " and the outer face is at ", plate_inner_z() + wall));
// the tails point UP now, so they need headroom rather than floor relief
assert(dac_top_z() > wall + 2, "DAC pin tails reach the top face — deepen cavity_depth");
// side-wall features live in (y, z) and the bosses span every z, so the socket must
// clear them in y alone
for (cb = boss_cs)
    assert(abs(dac_jack_y() - cb[1]) >= (dac_jack_w + 2*clr + boss_od)/2,
           "DAC socket cutout runs into a corner boss");
assert(abs(dac_jack_y()) + dac_jack_w/2 + clr + jack_lead_in <= inner_half_y(),
       "DAC socket cutout runs off the side wall");

// ===== button module: shell bore, cap, holder =====
// The three parts share one z chain and one diameter chain, so these asserts are what
// keep them mating after any single edit. This is the fussiest fit on the case, which
// is exactly why the mechanism is a separate part.

// -- shell side: a bore, a recess, two blind pilots --
assert(btn_cap_d > btn_bore_d(), "cap flange must be wider than the bore or it falls in");
assert(btn_recess_d() >= btn_cap_d + 2*clr, "cap recess must clear the flange");
assert(btn_recess_depth < wall, "cap recess must not cut through the top face");
assert(btn_pilot_depth < wall - 0.6, "holder pilots must stay blind — they would show through the top face");
assert(btn_pilot_depth > 1.5, "holder pilots too shallow for an M2 to hold");
// A pilot is drilled from the inner face and the recess is cut into the outer one. Where
// they overlap in plan the wall between them is all that is left, and at Ø38 the recess
// wall has come out to within a few mm of the pilots.
assert(btn_pilot_pitch/2 - board_screw_pilot/2 >= btn_recess_d()/2 + 1,
       str("holder pilots too close to the recess wall — needs btn_pilot_pitch of at least ",
           btn_recess_d() + board_screw_pilot + 2));

// -- cap: the body is a JOURNAL first and a snap second --
// The whole reason this button is drawn the way it is. A Ø38 flange leans by its own
// radius times the tilt the guide allows, so the guide length is a visible dimension,
// not a detail: 19 mm out, every 0.05 rad is ~1 mm of lean.
function btn_guide_len() = (wall - btn_recess_depth) + bh_guide_h;
function btn_lean()      = btn_cap_d/2 * (2*btn_guide_clr)/btn_guide_len();
assert(btn_guide_len() >= 6,
       str("cap guide is only ", btn_guide_len(), " mm long on a ", btn_cap_d,
           " mm flange — raise bh_guide_h"));
assert(btn_lean() <= 1.2,
       str("cap flange can lean ", btn_lean(),
           " mm — tighten btn_guide_clr or lengthen bh_guide_h"));
assert(btn_wall_t >= 1.2, "cap body too thin to be a bearing surface");
assert(btn_wall_id() > btn_post_d + 2, "cap body bore is barely wider than its own post");
assert(btn_slits >= 4, "too few slits for a body this size to collapse through the bore");
assert(btn_slit_w < btn_wall_od*PI/(2*btn_slits), "slits eat more than half the body");
// Slits may not reach the shell bore, or the journal is cut where it is most accurate —
// and you would see them through the gap under the flange.
assert(btn_slit_z0 > wall, "cap slits cross the shell bore — raise btn_slit_z0 above `wall`");
assert(btn_slit_z0 < bh_catch_z(), "cap slits start below the catch — the lip could not collapse");
assert(btn_post_d < sw_plunger_d, "cap post is wider than the plunger it presses");
assert(btn_post_h() > 0, "cap post has no length — check the z chain");
assert(btn_proud() > 0, "cap sits below the top surface — nothing to press");

// -- travel, and the preload that replaced the return spring --
// The chain that makes this a button rather than a click. With no coil spring the whole stroke
// is the switch's own, and what stops the cap rattling is btn_preload: the post reaches PAST
// the plunger's free position, so the switch holds the cap up against its retention lip.
//
// The direction is the entire point. Preload positive => cap pinned to the lip, switch a
// little pre-depressed, harmless. Preload negative => cap resting on the plunger with the lip
// floating clear, and it rattles by exactly that much.
assert(btn_preload > 0,
       "no preload — the cap would rest on the plunger with its lip clear of the catch, and rattle");
// ...but a preload that reaches sw_travel is a switch that is permanently closed. Half is the
// most that leaves room for print error at both ends.
assert(btn_preload <= sw_travel/2,
       str("preload is ", btn_preload, " of only ", sw_travel,
           " mm of switch travel — it would sit close to permanently pressed. Keep it under ",
           sw_travel/2));
// And what is LEFT has to be a press you can feel.
assert(btn_stroke() >= 0.3,
       str("only ", btn_stroke(), " mm of stroke left after the preload — raise sw_travel or lower btn_preload"));
assert(btn_face_gap > btn_stroke() + 0.5,
       str("flange bottoms on the recess floor before the switch closes — btn_face_gap must exceed the ",
           btn_stroke(), " mm stroke"));
assert(btn_face_gap <= btn_recess_depth,
       "flange stands proud of the top face at rest — raise btn_recess_depth to match btn_face_gap");
assert(btn_recess_depth < wall - 1.0,
       "recess leaves under 1 mm of top face for the flange to land on");
// The lip travels the full stroke down its relief, which is what that relief is FOR.
assert(bh_relief_h() >= btn_lip_t + btn_stroke(),
       "lip relief is shorter than the lip plus its travel — the cap jams before it actuates");
// The cap's far edge must not reach the collar floor before the switch does its work, and the
// lip must not bottom in its own relief. Both of those reduce to btn_lip_slack, and both were at
// 0.3 when a printed cap seized with no travel — so the threshold is 0.6, not the 0.2 that let
// it through. A tenth of print error on a part this size is normal; a tenth of margin is not.
assert(bh_relief_z1() - (btn_wall_z1() + btn_stroke()) >= 0.6,
       str("cap body bottoms on the collar floor mid-stroke — only ",
           bh_relief_z1() - (btn_wall_z1() + btn_stroke()),
           " mm of room. Raise btn_lip_slack"));
assert(bh_relief_h() - btn_lip_t - btn_stroke() >= 0.6,
       str("lip bottoms in its relief before the stroke finishes — only ",
           bh_relief_h() - btn_lip_t - btn_stroke(), " mm of room. Raise btn_lip_slack"));
// -- THE assert of this whole redesign: the cap's bore has to swallow the switch --
// The switch stands on the collar floor and reaches back up past the catch, which is inside
// the cap, so its DIAGONAL — not its width — runs inside the cap's body bore over most of its
// height. 11 mm square is 15.6 mm across the corners, and that is what took the cap from Ø18
// to Ø22. Get this wrong and the cap simply will not go down over the switch.
assert(btn_wall_id() >= sw_diag() + 2*clr,
       str("cap's body bore is ", btn_wall_id(), " and the switch's diagonal is ", sw_diag(),
           " — btn_wall_od must be at least ", sw_diag() + 2*clr + 2*btn_wall_t));
// ...and the same clearance has to hold in the holder's relief bore, which the switch also
// stands inside.
assert(bh_relief_d() >= sw_diag() + 2*clr,
       str("switch's diagonal does not clear the holder's relief bore (", bh_relief_d(), ")"));

// -- printability: the cap goes on the plate apex-down, so every step must be 45 deg or
// tangent. btn_flare_h() is derived to guarantee the one step that could go wrong.
assert(btn_flare_h() >= (btn_cap_d - btn_wall_od)/2 - 0.001,
       "flange flare is steeper than 45 deg — it would print as an overhang");
assert(btn_dome_r > btn_wall_t, "top fillet is thinner than the wall — no inner radius left");
// The inner flat is where the post roots, so the fillet may not eat it.
assert(btn_top_d() > btn_post_d + 4,
       "top fillet has eaten the flat the post roots into");
assert(btn_dome_h > btn_dome_r + btn_flare_h() + btn_flange_t,
       "cap is too short for its own fillet, flare and flange");

// -- the catch: lip vs the holder's bore, and vs the shell bore it passes on the way in
assert(btn_lip_od() > bh_bore_d(), "retention lip does not catch on the holder");
assert((btn_lip_od() - bh_bore_d())/2 >= 0.3,
       str("lip catches on only ", (btn_lip_od() - bh_bore_d())/2,
           " mm of shoulder — raise btn_lip_over"));
assert(btn_lip_od() > btn_bore_d(),
       "lip passes the shell bore freely — the cap would only be held by the holder");
assert(bh_relief_d() > btn_lip_od(), "no radial room for the lip in the holder's relief");
assert(bh_relief_h() >= btn_lip_t + 0.2, "lip relief is shorter than the lip");
// The holder's bore may not be TIGHTER than the shell's: the shell bore is cut in the
// part that defines the axis, the holder only gets there via two M2s in clearance holes.
// Reverse the two and the holder pinches the cap wherever it happens to sit.
assert(bh_guide_clr > btn_guide_clr,
       "holder bore is as tight as the shell's — it would pinch the cap off axis");
assert(bh_guide_clr - btn_guide_clr >= (bh_screw_clear - screw_m2_d)/2,
       str("holder bore does not allow for its own mounting slop — needs bh_guide_clr of at least ",
           btn_guide_clr + (bh_screw_clear - screw_m2_d)/2));

// -- holder: the switch on the floor, and its four pins through it --
// No boss and no pocket walls, so the checks are about the switch standing free inside the
// cap's bore and its pins getting out.
assert(sw_plunger_h > 0 && plunger_z() < sw_top_z(),
       "plunger does not stand proud of the body — the post could never reach it");
// The post reaches PAST the plunger, which is what preloads the cap against the lip.
assert(btn_post_tip_z() > plunger_z(),
       "cap post stops short of the plunger — the cap would rest on it and rattle at the lip");
assert(abs((btn_post_tip_z() - plunger_z()) - btn_preload) < 0.001,
       "post over-travel does not match btn_preload — the z chain has been broken");
// The switch's top must stay clear of the shell's inner face: it reaches a long way up inside
// the cap and there is nothing to stop it except this.
assert(plunger_z() > btn_ceil_z() + btn_wall_t,
       str("switch stands so tall its plunger reaches the cap's own ceiling (", plunger_z(), ")"));
// ...and its body must stay inside the cap's STRAIGHT bore. Above that bore the dome's inner
// fillet closes in on the cap's top flat, which is Ø15.6 against the switch's 15.56 mm
// diagonal — 0.02 mm, i.e. nothing. So the body must not reach the flare, at any point in the
// stroke.
assert(sw_top_z() > btn_flare_top_z() + btn_stroke() + 1,
       str("switch body reaches up into the cap's dome, where the bore narrows to ", btn_top_d(),
           " against a ", sw_diag(), " mm diagonal — its top is at ", sw_top_z()));
assert(sw_body_h() > 0,
       str("sw_plunger_h (", sw_plunger_h, ") is larger than the whole switch height (", sw_h, ")"));
// The pins, and the floor they pass through. They sit OUTBOARD of the body — legs out of the
// side faces, bent down clear of the outline — so the field is described as an outboard distance
// plus a gap, not a pitch.
assert(sw_pin_axis == 0 || sw_pin_axis == 1, "sw_pin_axis picks which pair of sides has the pins");
assert(sw_pin_win > 1.5, "pin windows too small to clear a tactile's legs and their solder");
assert(sw_pin_out >= 0, "sw_pin_out is how far the pins stand OUT from the body — it cannot be negative");
// The slot is a RANGE, and it has to be a useful one: reaching inboard of the body's face so a
// flush pin is caught, and far enough out to cover a splayed one.
assert(sw_pin_slack > 0.5, "pin slots too short to be a range — they are back to guessing a position");
assert(sw_pin_a_lo() <= sw_body/2,
       str("pin slots start ", sw_pin_a_lo() - sw_body/2,
           " mm OUTSIDE the body's face — a pin flush with the side would miss them"));
assert(sw_pin_gap > sw_pin_win,
       "the two pins on one side are closer together than their own windows are wide");
// With the pins outboard this should be the full body area. It is computed rather than assumed,
// because walking sw_pin_out back toward 0 moves the windows under the body again.
assert(sw_seat_area() >= 0.4*sw_body*sw_body,
       str("pin windows have eaten the floor the switch stands on — only ", sw_seat_area(),
           " of ", sw_body*sw_body, " mm2 left"));
// Every slot has to stay on the floor: inside the lip relief's bore, so it does not breach the
// collar wall, and clear of the screw posts' own holes coming up through the same floor.
for (p = sw_pin_pos()) {
    assert(norm([abs(p[0]) + sw_pin_win_xy()[0]/2, abs(p[1]) + sw_pin_win_xy()[1]/2])
             < bh_relief_d()/2,
           str("pin slot at ", p, " reaches the collar wall — it would breach the relief bore"));
    assert(abs(abs(p[0]) - btn_pilot_pitch/2) > (sw_pin_win_xy()[0] + bh_screw_cbore_d)/2,
           str("pin slot at ", p, " runs into the holder's own screw counterbores"));
}
// ---- the four locating ribs ----
// They are the answer to "the switch has nothing holding it in place": the pins alone let it
// slide several millimetres inside their own windows. What they must not do is foul the cap,
// which comes down over them, so their furthest point from the axis is the number that matters.
if (sw_locate_t > 0) {
    assert(sw_locate_max() <= btn_wall_id()/2 - clr,
           str("locating ribs reach ", sw_locate_max(), " from the axis and the cap's bore is ",
               btn_wall_id()/2, " — shorten sw_locate_len or thin sw_locate_t"));
    assert(sw_locate_r0() > sw_body/2,
           "locating ribs are inside the switch's own footprint — it would sit on top of them");
    assert(sw_locate_clr > 0 && sw_locate_clr <= 1.0,
           "sw_locate_clr out of range — the ribs either pinch the switch or do not locate it");
    // ...and they must not sit over a pin window, or they print in mid-air over a hole. Two of
    // the four sides have pins standing off them, and on those the rib lives in the gap BETWEEN
    // that side's pair — which is what sw_locate_len_pin is for. This is the check that the
    // short one is actually short enough.
    assert(sw_locate_len_pin + sw_pin_win + 0.5 <= sw_pin_gap,
           str("rib on a pinned side is ", sw_locate_len_pin,
               " long and only ", sw_pin_gap - sw_pin_win,
               " of gap is clear between that side's two pin slots"));
    assert(sw_locate_len_pin > 1.0, "rib on a pinned side is too short to locate anything");
    // The long ribs are on the clear pair, and they must not reach the pin windows in the OTHER
    // axis either.
    assert(sw_locate_len/2 <= sw_pin_a_lo(),
           str("long rib reaches the pin slots on the neighbouring side — keep sw_locate_len under ",
               2*sw_pin_a_lo()));
    assert(sw_locate_h > pcb_t, "locating ribs too short to catch the switch body's side");
}
assert(sw_pin_len > bh_floor_t,
       "pins do not reach through the floor — nothing to solder to under the holder");
// The floor is what the switch stands on and what its pins pass through, so it has to be
// thick enough to be both. The old "pass the leads out through the rim" requirement is gone
// with the sideways lead channel — the pins go straight down now.
assert(bh_floor_t >= 1.2, "collar floor too thin to stand the switch on");
assert(bh_screw_clear > board_screw_pilot, "holder holes must clear the M2 they pass");
assert(bh_screw_cbore_d > bh_screw_clear && bh_screw_cbore_h < bh_z1() - bh_relief_z1(),
       "screw counterbore must be wider than the hole and stay inside the floor");
assert(bh_ear_d >= bh_screw_cbore_d + 2, "screw post too thin around its own counterbore");
// The posts stand clear of the collar, so the web is the only thing joining them. It has
// to actually span the gap.
assert(btn_pilot_pitch/2 - bh_ear_d/2 < bh_collar_od()/2 + 2,
       "screw posts stand too far off the collar for the web to reach");
assert(btn_pilot_pitch/2 + bh_ear_d/2 > bh_collar_od()/2,
       "screw posts are buried in the collar — they would open into the guide bore");
assert(bh_collar_od() >= bh_relief_d() + 2*bh_wall, "collar wall thinner than bh_wall at the relief");

// -- the assembled module must fit the box and clear what is under it --
// This is the constraint that shaped the holder: series-stacking the switch under the
// guide puts it at ~17.5 and this fires. Measured at bh_deep_z(), the PIN TIPS, not at the
// collar floor — the pins are what actually gets close to the devkit.
assert(bh_deep_z() < top_depth() - 2, "button module reaches the base plate");
if (!aabb_clear(btn_pos, [bh_plate_w(), bh_plate_l()], s3_pocket_c(), s3_pocket_f()))
    assert(s3_top_z() > bh_deep_z() + 2,
           str("button module collides with the devkit — its pins reach ", bh_deep_z(),
               " and the devkit's stack starts at ", s3_top_z()));
if (!aabb_clear(btn_pos, [bh_plate_w(), bh_plate_l()], dac_pocket_c(), dac_pocket_f()))
    assert(dac_top_z() > bh_deep_z() + 2, "button module collides with the DAC");
clears_bosses(btn_pos, [bh_plate_w(), bh_plate_l()], "button holder collar");
inside_cavity(btn_pos, [bh_plate_w(), bh_plate_l()], "button holder collar");
assert(aabb_clear(btn_pos, [bh_plate_w(), bh_plate_l()], mic_pos, mic_size()),
       "button holder collar overlaps the mic seat");
// ...and the bore itself, which is bigger than the old holder PLATE was, must clear the
// mic seat cut into the same inner face.
assert(abs(mic_pos[1]) - mic_size()[1]/2 >= btn_bore_d()/2,
       "shell bore breaks into the mic seat on the inner face");

// ===== microphone =====
assert(mic_seat_depth + mic_gasket_depth < wall, "mic seat + gasket seat cut through the top face");
assert(mic_gasket_d > mic_hole_d, "mic gasket seat must be wider than the port");
assert(mic_gasket_d <= mic_board_l, "mic gasket seat wider than the board it seals against");
assert(mic_post_pitch/2 - mic_post_od/2 >= (mic_board_w + 2*clr)/2,
       "mic posts intrude into the board recess");
// The clamp bar spans both posts and its pad reaches back down to the seated board.
assert(mic_clamp_pad_h() > 0,
       "mic clamp pad has no height — the posts are shorter than the seated board");
assert(mic_clamp_pad < mic_board_w && mic_clamp_pad <= mic_board_l,
       "mic clamp pad overhangs the board it presses");
assert(mic_screw_clear > board_screw_pilot, "clamp holes must clear the M2 they pass");
assert(mic_clamp_len() >= mic_post_pitch + mic_post_od, "clamp bar does not span both posts");
assert(mic_clamp_w <= mic_post_od + 4, "clamp bar wider than the posts can support");
assert(mic_clamp_w >= mic_screw_clear + 1.5,
       str("clamp bar too narrow for the M2 holes it carries — needs at least ", mic_screw_clear + 1.5));
// Thin on purpose (half its first value). It only has to hold gasket compression and
// the pad does the pressing, but below ~1 mm the bar bows instead of clamping and the
// gasket seal goes with it.
assert(mic_clamp_t >= 1.0, "clamp bar too thin to press without bowing");
// the clamp lives inside the box, so it has to clear what is around the mic
assert(wall + mic_post_h + mic_clamp_t < s3_top_z(), "mic clamp collides with the devkit");

// ===== base plate: pockets, vents, feet, screws =====
// Both pockets must nest inside the registration lip, not foul it. The DAC pocket is
// deliberately allowed to run right up to the lip's inner edge (they merge into one
// solid, which prints fine) but may not cross it, or the plate will not drop in.
assert(abs(s3_pos_x) + s3_pocket_f()[0]/2 <= lip_inner_half_x(), "devkit pocket fouls the register lip (x)");
// The devkit pocket is now ALLOWED into the lip's own annulus at both ends — its front wall
// IS the lip, grown to pocket height, and the rear stops stand on the same footprint. What it
// may not do is run past the lip's OUTER face, which is what the shell cavity accepts.
assert(max(abs(s3_pocket_y0()), abs(s3_pocket_y1())) <= lip_outer_half_y(),
       "devkit pocket runs past the register lip's outer face — the plate would not drop in");
assert(s3_front_wall_t() >= reg_t - 0.001,
       str("devkit pocket's front wall is thinner than the register lip it stands on — only ",
           s3_front_wall_t(), " mm"));
assert(dac_pocket_x1() <= lip_inner_half_x(), "DAC pocket crosses the register lip");
assert(abs(dac_pos_y()) + dac_pocket_f()[1]/2 <= lip_inner_half_y(), "DAC pocket fouls the register lip (y)");
assert(dac_pocket_x0() < dac_pocket_x1(), "DAC pocket has no length — the board is too long for the plate");
// the pockets must clear the plate's own screw counterbores
for (cb = boss_cs) {
    assert(aabb_clear(s3_pocket_c(), s3_pocket_f(), cb, [screw_cbore_d, screw_cbore_d]),
           "devkit pocket clashes a base-plate screw");
    assert(aabb_clear(dac_pocket_c(), dac_pocket_f(), cb, [screw_cbore_d, screw_cbore_d]),
           "DAC pocket clashes a base-plate screw");
}
assert(s3_seat_h > 0 && s3_lip > 0, "devkit pocket needs a floor and a retaining lip");
// ---- devkit fit and the retention tab ----
// The devkit's pocket is the one that has to be a SLOT: nothing else locates that board,
// and its slack lands on the USB-C window. So its clearance is its own number, tighter
// than the DAC's, and there is a tab over its front edge to stop it lifting back out.
assert(s3_board_clr > 0, "devkit pocket has no clearance at all — the board would not go in");
assert(s3_board_clr <= board_clr,
       "the devkit pocket is looser than the DAC's, which has its socket to locate it — that is backwards");
// No upper bound tied to a remembered print any more. There WAS one at 1.0, on the grounds that
// the board rattled there — but that was measured when s3_l said 30 against a real 28 mm board, so
// the rattle was 2 mm of wrong board dimension, not clearance. What is worth bounding is the thing
// that actually goes wrong if this grows: the board drifting far enough in x to hide a USB port
// behind the wall. s3_usb_slop() is derived from it, so that is handled by construction — this
// just catches a value big enough to mean something has been mistyped.
assert(s3_board_clr <= 2.0,
       "s3_board_clr is large enough that the board is not in a pocket so much as a tray");
// ---- the front clearance the tab has to reach across ----
// Derived, so it is whatever depth `plan` did not spend on the board. It must be at least the
// pocket clearance (or the board is pinched between the stops and the front wall) and it must
// not run away, because the tab's underside drops 1:1 with it and eventually reaches the
// pocket floor.
// The board's y travel is s3_board_clr, at the rear, between the stops and the front wall — the
// cavity is cut to the board's nominal front edge, so all of the play is behind it.
assert(s3_board_clr > 0.2, "no y travel for the devkit — it would be pinched between the stops and the front wall");
// The front gap is the other half of that travel, and it is what the tab reaches across.
assert(s3_front_gap > 0,
       "the cavity ends at the board's front edge — no y clearance in front of it at all");
// The relief runs the board's whole length now, so what has to hold is that it still stops short
// of the front wall rather than undercutting its base.
assert(s3_relief_front_setback > 0 && s3_relief_front_setback < s3_front_gap + pin_row_w,
       "devkit relief setback does not leave the front wall a base to stand on");
if (s3_tab_cover > 0) {
    // The tab is only printable because its underside is a 45 deg ramp, and the ramp needs
    // room between where it meets the wall and the top of that wall.
    // The tab is a small nib at the top of its own ramp now, not a block running to the top of
    // the pocket wall — but it still has to fit under that top.
    assert(s3_tab_h > 0, "retention tab has no height above its ramp");
    // s3_lip() is derived from the tab, so these two planes coincide by construction. The check
    // is that the derivation still says so — if it drifts, the tab is either poking out of the top
    // of the wall or buried below it.
    assert(abs(s3_wall_top() - s3_tab_top()) < 0.001,
           str("retention tab is no longer flush with the top of the pocket wall — wall top ",
               s3_wall_top(), ", tab top ", s3_tab_top()));
    // ...and the underside must stay clear of the pocket FLOOR. This is what bounds
    // s3_board_clr from above: every millimetre of board travel drops the ramp a millimetre.
    assert(s3_tab_z0() > s3_seat_h + 0.2,
           str("retention tab's ramp reaches the pocket floor — s3_lip is ", s3_lip,
               " and the ramp starts at ", s3_tab_z0(), " against a floor at ", s3_seat_h));
    // The preload is what makes this a hold rather than a cover. Small and self-limiting is
    // the whole idea — the ramp is 45 deg, so a big number here is a press fit, not a
    // slide-in, and the board would seat proud of the floor.
    // The bite is DERIVED now, because the tab is anchored to the top of the wall rather than to
    // the board. All that can be checked is the one thing that would make it meaningless — a tab
    // so low the board cannot be pushed under it at all.
    assert(s3_tab_bite() < pcb_t/2,
           str("tab reaches more than half way down the PCB's edge (bite ", s3_tab_bite(),
               ") — the board would not go under it"));
    // It reaches in over the board, which is the point — but not so far it covers whatever
    // is at the middle of that end, and not so wide it reaches the header rows on the long
    // edges. 4 mm is roughly one header body plus its solder fillet.
    assert(s3_tab_cover > 0.6 && s3_tab_cover < s3_w/8,
           "retention tab covers either too little of the board's front edge to hold it, or too much of that end");
    assert(s3_tab_w > 0 && s3_tab_w <= s3_l - 8,
           str("retention tab is wide enough to reach the devkit's header rows — keep s3_tab_w under ",
               s3_l - 8));
    // ...and the board still has to be able to GET under it. With stops at the rear it can no
    // longer be slid straight in: it goes in tilted rear-up, front edge first, and the rear
    // corners drop behind the stops. That only works while the stops stay at or below the
    // PCB's top face — any taller and the board is captured in z at both ends before it is
    // in, which is a part that cannot be assembled.
    assert(!s3_rear_stops || s3_rear_stop_h <= pcb_t,
           str("rear stops stand ", s3_rear_stop_h - pcb_t,
               " mm above the PCB's top face — the board is then captured in z at both ends and cannot be assembled"));
    assert(!s3_rear_stops || s3_rear_stop_h >= pcb_t/2,
           "rear stops are too short to catch the board's edge — it would ride over them");
}
assert(dac_seat_h > 0 && dac_lip > 0, "DAC pocket needs a floor and a retaining lip");
// ---- how TALL the pocket walls may be ----
// The lip is the wall standing above the seated PCB. Only the part of it level with the
// PCB's own 1.6 mm edge can transfer lateral load; everything above that is shrouding,
// not strength. So a lip is bounded by what it might hit rather than by any mechanical
// need, and these are the two things it can reach: the mic assembly hanging off the top
// face (which overlaps the devkit pocket's +y wall in plan), and the DAC's own socket.
function s3_wall_top_z()  = plate_inner_z() - (s3_seat_h + pcb_t + s3_lip);
function dac_wall_top_z() = plate_inner_z() - (dac_seat_h + pcb_t + dac_lip);
assert(s3_wall_top_z() > wall + mic_post_h + mic_clamp_t + 2,
       "devkit pocket wall is tall enough to hit the mic clamp — reduce s3_lip");
assert(s3_wall_top_z() > bh_deep_z() + 2 || abs(s3_pos_x) + s3_pocket_f()[0]/2 - pocket_wall > bh_plate_w()/2,
       "devkit pocket wall is tall enough to hit the button holder — reduce s3_lip");
assert(dac_wall_top_z() > wall + 2, "DAC pocket wall reaches the top face — reduce dac_lip");
// The DAC lip covers the socket rather than stopping partway up it. It is NOT what resists
// a levered plug: the walls sit ~4 mm clear of the socket in y, so that job belongs to the
// counterbore in the shell wall, which wraps the socket body with 0.4 mm all round.
assert(dac_lip >= pcb_t + 1, "dac_lip does not properly capture the PCB edge");
assert(dac_lip <= pcb_t + board_pin_h + 3,
       str("dac_lip runs far past the pin tails — nothing above ", pcb_t + board_pin_h, " does work"));

// ---- pin relief: the reason the floors are not flat ----
// Without it the board rests on its solder-side pin tails, sits ~2 mm proud, and the lip
// ends up level with the gap UNDER the board instead of its edge — which is what made
// the first walls appear to "cover the pins".
assert(board_pin_h > 0, "no pin relief: the board would seat on its own pin tails");
// The strips must stop SHORT of the cavity face, or they undercut the pocket wall's base and
// its exposed height grows by the relief depth — which is what made the DAC's front wall
// look paper-thin. Still has to reach under the header row, ~2.5 mm in from the board edge.
assert(pin_relief_setback > 0, "pin relief undercuts the pocket wall base");
// Checked against the TIGHTER of the two pockets: the setback is one global number and the
// devkit's clearance is now the smaller, so it is the devkit's header row that the channel
// walks out from under first.
assert(pin_relief_setback + 1 < min(board_clr, s3_board_clr) + 2.5,
       "pin relief setback pushes the channel out from under the header row");
assert(board_pin_h + clr <= s3_seat_h - 0.8,
       str("pin relief would leave too little devkit pocket floor — raise s3_seat_h to at least ",
           board_pin_h + clr + 0.8));
assert(board_pin_h + clr <= dac_seat_h - 0.8,
       str("pin relief would leave too little DAC pocket floor — raise dac_seat_h to at least ",
           board_pin_h + clr + 0.8));
// Devkit: strips on the LONG (+-x) edges, so they must leave a central land in x and an
// end land in y.
assert(2*pin_row_w < s3_l + 2*s3_board_clr - 4, "pin relief strips swallow the devkit's central land");
assert(pin_land > 1 && 2*pin_land < s3_w, "devkit pin relief leaves no end land");
// DAC: strips on the SHORT (+-y) edges instead, because its long +x edge carries the
// socket and needs floor under it. So the lands swap axes.
assert(2*dac_relief_w() < dac_l + 2*board_clr - 4, "DAC relief channel swallows its central land");
// Both cuts in the DAC floor share dac_cut_w, so they match by construction. What still has
// to hold is that this width admits the socket BODY — the recess is what the socket drops
// into, so a width below the socket means the socket fouls the floor beside it.
// The recess must admit the socket BODY, whatever the channel width is. dac_recess_w() takes
// the larger of the two so this holds by construction; the check is that they have not been
// decoupled by hand.
// The recess must at least equal the socket body. It is running at ZERO clearance here by
// choice — noted rather than enforced, because a printed pocket at nominal is an interference
// fit and this is the dimension most likely to need the 0.4/side back.
assert(dac_recess_w() >= dac_jack_w,
       "socket recess is narrower than the socket — the socket would foul the floor beside it");
assert(pin_land > 1 && 2*pin_land < dac_w, "DAC pin relief leaves no end land");
// ...and the point of the swap: the socket's long edge keeps its floor. With short-edge
// strips the +x edge is untouched over its whole length.
assert(dac_w + 2*board_clr - 2*pin_land > 0, "DAC relief strips have no width left");
// The strips run off the RIGHT (+x) end of the floor — the pocket's open side — and are
// landed at the left. Check both ends: the right must actually reach the floor's edge (a
// channel stopping short is a dead end, and that is invisible in a render), and it must not
// run past it into the register lip.
function dac_relief_xhi() = dac_pocket_x1();
function dac_relief_xlo() = dac_cx() - (dac_w/2 + board_clr - pin_land);
// No relief channel may overlap the socket recess in plan. The recess is deeper, so an
// overlap nests one cut inside the other and leaves a stepped pocket rather than a channel.
function dac_relief_y_rear() = dac_pos_y()
                             - ((dac_l + 2*board_clr)/2 - pin_relief_setback - dac_relief_w()/2);
assert(dac_relief_y_rear() + dac_relief_w()/2 < dac_jack_y() - (dac_jack_w/2 + clr),
       "rear relief channel runs into the socket recess — the two would nest");
assert(dac_relief_xhi() >= dac_pocket_x1() - 0.001,
       "DAC relief stops short of the floor's open edge — it would be a dead end");
assert(dac_relief_xhi() <= lip_inner_half_x() + 0.001,
       "DAC relief runs past the floor into the register lip");
assert(dac_relief_xlo() > dac_pocket_x0() + pocket_wall,
       "DAC relief no longer has a land at its left end — it would breach the left wall");

// vents: clear of both pockets, the feet and the screws. A vent opening under a pocket
// floor vents nothing and just weakens the plate.
for (v = vent_rects) {
    vc = [v[0], v[1]];  vs = [v[2], v[3]];
    assert(aabb_clear(vc, vs, s3_pocket_c(), s3_pocket_f()),
           str("vent at ", vc, " opens under the devkit pocket"));
    assert(aabb_clear(vc, vs, dac_pocket_c(), dac_pocket_f()),
           str("vent at ", vc, " opens under the DAC pocket"));
    for (cb = boss_cs)
        assert(aabb_clear(vc, vs, cb, [screw_cbore_d, screw_cbore_d]),
               str("vent at ", vc, " runs into a screw counterbore"));
    for (f = foot_positions)
        assert(aabb_clear(vc, vs, f, [foot_d, foot_d]),
               str("vent at ", vc, " breaks into a foot recess"));
    assert(abs(v[0]) + v[2]/2 <= lip_inner_half_x() && abs(v[1]) + v[3]/2 <= lip_inner_half_y(),
           str("vent at ", vc, " runs into the register lip"));
}
// foot_positions is empty by default — see params. These checks exist for anyone who
// re-populates it. A foot recess is on the OUTER face and a pocket floor on the INNER
// one, and in a 3 mm plate the two together do not fit, so a foot may not sit under a
// pocket at all: that is the check the old "sum of depths" version was too loose to
// catch, and it let a foot land 0.1 mm inside the DAC pocket floor.
for (f = foot_positions) {
    assert(abs(f[0]) + foot_d/2 <= plan_x/2 - 2 && abs(f[1]) + foot_d/2 <= plan_y/2 - 2,
           "foot recess runs off the plate edge");
    assert(foot_depth < wall - 1, "foot recess leaves too little plate under it");
    for (cb = boss_cs)
        assert(norm([f[0]-cb[0], f[1]-cb[1]]) >= (foot_d + screw_cbore_d)/2,
               "foot recess overlaps a screw counterbore");
    assert(foot_depth + s3_seat_h < wall || aabb_clear([f[0],f[1]], [foot_d,foot_d], s3_pocket_c(), s3_pocket_f()),
           "foot recess would break through the devkit pocket floor");
    assert(foot_depth + dac_seat_h < wall || aabb_clear([f[0],f[1]], [foot_d,foot_d], dac_pocket_c(), dac_pocket_f()),
           "foot recess would break through the DAC pocket floor");
}

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) rounded_rect(vent_rects[0][2], vent_rects[0][3], vent_rects[0][2]/2);
screw_boss(8, boss_od, insert_m3_d);

cube(1);  // non-empty render under --hardwarnings
