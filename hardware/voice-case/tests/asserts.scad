include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
// `plan` is not a free choice: it is bounded below by the two measured boards. This is
// the assert that replaces guessing at a footprint — it names the number needed rather
// than letting a too-small case fail as a pile of unrelated collisions further down.
assert(plan >= plan_min(),
       str("plan too small for the boards — needs at least ", plan_min(),
           " (width ", plan_from_width(), ", boss/s3 ", plan_from_boss_s3(),
           ", boss/dac ", plan_from_boss_dac(), ", depth ", plan_from_depth(), ")"));
assert(s3_pos_x == 0,
       "the devkit must be centred in x: with four corner bosses, a board this deep has no y escape");
assert(outer_w() == plan && outer_h() == plan, "the puck is square");
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
assert(flat_half() > 0, "top chamfer swallowed the whole top face");
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
assert(boss_c() + boss_od/2 <= inner_half(), "corner bosses run into the side walls");

boss_cs = [for (sx = [-1,1], sy = [-1,1]) [sx*boss_c(), sy*boss_c()]];
module clears_bosses(c, sz, name) {
    for (cb = boss_cs)
        assert(aabb_clear(c, sz, cb, [boss_od, boss_od]), str(name, " clashes a corner boss"));
}
module inside_cavity(c, sz, name) {
    assert(abs(c[0]) + sz[0]/2 <= inner_half(), str(name, " off the cavity width"));
    assert(abs(c[1]) + sz[1]/2 <= inner_half(), str(name, " off the cavity depth"));
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

assert(aabb_clear(dac_pocket_c(), dac_pocket_f(), s3_pocket_c(), s3_pocket_f()),
       "the two board pockets overlap on the base plate — move s3_pos_x or shrink the DAC");

// Top-face features must stay on the FLAT face — the chamfer, not the outer edge, is
// the real bound.
assert(abs(btn_pos[0]) + btn_halo_od/2 <= flat_half(), "button halo runs onto the chamfer (x)");
assert(abs(btn_pos[1]) + btn_halo_od/2 <= flat_half(), "button halo runs onto the chamfer (y)");
assert(abs(mic_pos[0]) + mic_size()[0]/2 <= flat_half(), "mic seat runs onto the chamfer (x)");
assert(abs(mic_pos[1]) + mic_size()[1]/2 <= flat_half(), "mic seat runs onto the chamfer (y)");
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
assert(s3_usb_cz() - s3_usb_h/2 >= wall, "USB window runs into the top face — lower the devkit");
assert(s3_usb_cz() + s3_usb_h/2 <= top_depth() - 1.5,
       "USB window breaks the base rim — raise s3_seat_h or shrink s3_usb_h");
// The window must expose BOTH receptacles, not straddle the gap between them. This is
// the check that was missing when a 14 mm window left neither port usable: it has to be
// at least as wide as the two ports plus the gap, and it has to stay on the board.
assert(s3_usb_w() >= s3_usb_ports*s3_usb_port_w + (s3_usb_ports-1)*s3_usb_gap,
       "USB window narrower than the ports it serves — no plug would fit either one");
assert(s3_usb_w() <= s3_l + 2*board_clr,
       "USB window wider than the devkit — it would open past the board");
// ...and the pocket must have NO rear wall, or its stubs sit in front of the ports. So
// the pocket has to STOP AT OR IN FRONT OF the board's own rear edge: any pocket material
// behind that edge is, by definition, between the receptacles and the window. Here the
// pocket ends ~1 mm in front of it, so the board's last millimetre overhangs the floor —
// harmless on a 69 mm board, and it guarantees nothing at all sits under the ports.
assert(s3_pocket_y0() >= s3_cy() - s3_w/2 - 0.001,
       "devkit pocket reaches behind the board's rear edge — that material would block the USB ports");
assert(s3_pocket_y1() > s3_cy() + s3_w/2, "devkit pocket has no +y wall to locate the board");
// Reach check. A USB-C plug has only ~6.5 mm of shell before its overmold, and with the
// rear open the board registers against the shell wall, so the setback is just the wall
// plus the sliding clearance.
assert(usb_setback() <= 6.5,
       "USB receptacle sits too deep for a plug to reach — the board is not registering on the rear wall");

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
// ...and the whole point of that offset going into the BOARD's position: the hole itself
// must land exactly where jack_hole_y says, which is the middle of the wall. This is the
// assert that would have caught the hole sitting 10 mm away from its socket.
assert(abs(dac_jack_y() - jack_hole_y) < 0.001,
       "socket does not line up with the hole — dac_pos_y() must absorb dac_jack_off()");
// the socket must clear the pocket's own end wall, which is just outboard of the board
assert(abs(dac_jack_off()) + dac_jack_w/2 <= dac_l/2 + board_clr,
       "socket body runs into the DAC pocket's end wall");
assert(dac_jack_axis > 0 && dac_jack_axis < dac_jack_h,
       "the barrel axis must lie inside the socket body");

// -- pull-out stop: the rib that keeps plug-removal load off the thinned panel --
// It only exists if the socket overhangs the PCB by more than the wall's unthinned
// remainder. Below that there is no gap between the board's edge and the wall to put a
// rib in, and the socket goes back to being the backstop.
assert(jack_stop_proj() > 0.4,
       str("no room for a DAC pull-out stop — needs dac_jack_overhang > ",
           wall - jack_panel_t - dac_socket_setback + 0.4,
           "; below that the socket lands on the thinned panel instead"));
assert(jack_stop_proj() < wall - 0.8, "pull-out stop projects further than the wall can carry");
// z: between the socket above and the register lip below, and it must actually overlap the
// PCB's thickness or it catches nothing.
assert(jack_stop_z1() > jack_stop_z0() + 0.8, "pull-out stop has no bearing height");
assert(jack_stop_z0() >= dac_pcb_top_z(), "pull-out stop rises into the socket body");
assert(jack_stop_z0() < dac_pcb_top_z() + pcb_t,
       "pull-out stop sits below the PCB edge — it would catch nothing");
assert(jack_stop_z1() <= top_depth() - reg_h, "pull-out stop collides with the register lip");
// y: entirely clear of the socket, or the base plate cannot rise into the shell
assert(jack_stop_y1() > jack_stop_y0() + 5, "pull-out stop too short to bear on");
assert(jack_stop_y0() >= dac_jack_y() + dac_jack_w/2,
       "pull-out stop crosses the socket's path — the case could not be assembled");
assert(jack_stop_y1() <= dac_pos_y() + dac_l/2, "pull-out stop overhangs the board's end");
for (cb = boss_cs)
    assert(abs(jack_stop_y1() - cb[1]) >= 4 || abs(inner_half() - cb[0]) >= boss_od,
           "pull-out stop runs into a corner boss");
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
// counterbore bounded top and bottom within the wall's height
assert(dac_top_z() - clr >= wall + 1, "socket counterbore runs into the top face");
assert(dac_pcb_top_z() + clr <= top_depth() - 1.5,
       "socket counterbore breaks the base rim — raise dac_seat_h or deepen cavity_depth");
// side-wall features live in (y, z) and the bosses span every z, so the socket must
// clear them in y alone
for (cb = boss_cs)
    assert(abs(dac_jack_y() - cb[1]) >= (dac_jack_w + 2*clr + boss_od)/2,
           "DAC socket cutout runs into a corner boss");
assert(abs(dac_jack_y()) + dac_jack_w/2 + clr + jack_lead_in <= inner_half(),
       "DAC socket cutout runs off the side wall");

// ===== button module: shell bore, cap, holder =====
// The three parts share one z chain and one diameter chain, so these asserts are what
// keep them mating after any single edit. This is the fussiest fit on the case, which
// is exactly why the mechanism is a separate part.

// -- shell side: a bore, a recess, a halo, two blind pilots --
assert(btn_cap_d > btn_bore_d, "cap face must be wider than the bore or it falls in");
assert(btn_recess_d >= btn_cap_d + 2*clr, "cap recess must clear the cap face");
assert(btn_recess_depth < wall, "cap recess must not cut through the top face");
assert(btn_halo_id >= btn_recess_d, "halo groove overlaps the cap recess");
assert(btn_halo_od > btn_halo_id && btn_halo_depth < btn_recess_depth, "halo groove geometry");
assert(btn_pilot_depth < wall - 0.6, "holder pilots must stay blind — they would show through the top face");
assert(btn_pilot_depth > 1.5, "holder pilots too shallow for an M2 to hold");
// pilots must clear the halo groove, or a pilot opens into it
assert(btn_pilot_pitch/2 - board_screw_pilot/2 > btn_halo_od/2,
       "holder pilots run into the halo groove — widen btn_pilot_pitch");

// -- cap: snaps through the shell bore, catches inside the holder --
assert(btn_skirt_t > 0 && btn_slits >= 3, "the skirt must be a slit annulus, or it cannot snap in");
assert(btn_slit_w < btn_skirt_od()*PI/(2*btn_slits), "slits eat more than half the skirt");
assert(btn_skirt_id() > btn_post_d, "cap skirt bore is narrower than its own centre post");
assert(btn_post_d < sw_plunger_d, "cap post is wider than the plunger it presses");
assert(btn_post_d < bh_apert_d(), "cap post cannot enter the holder's plunger aperture");
assert(btn_skirt_h() > 0, "cap skirt has no length — check btn_recess_depth against the wall");
assert(btn_post_h() > btn_skirt_h() + btn_lip_t, "cap post is shorter than its own skirt");
assert(btn_proud() > 0, "cap face sits below the top surface — nothing to press");
// The cap must have travel LEFT when the switch actuates, or the face bottoms on the
// recess floor and the switch never closes.
assert(btn_face_gap > sw_travel, "cap bottoms on the recess floor before the switch actuates");

// -- the catch: lip vs the holder's bore, and vs the shell bore it passes on the way in
assert(btn_lip_od() > bh_bore_d(), "retention lip does not catch on the holder");
assert((btn_lip_od() - bh_bore_d())/2 >= 0.3,
       "lip catches on less than 0.3 mm of shoulder — raise btn_lip_over");
assert(btn_lip_od() > btn_bore_d,
       "lip passes the shell bore freely — the cap would only be held by the holder");
assert(bh_relief_d() > btn_lip_od(), "no radial room for the lip in the holder's relief");
assert(bh_relief_h >= btn_lip_t + 0.2, "lip relief is shorter than the lip");

// -- holder: switch capture and printability --
assert(bh_apert_d() < sw_body, "plunger aperture is wider than the switch body — it would fall through");
assert(bh_apert_d() > sw_plunger_d, "plunger aperture is narrower than the plunger");
assert(bh_gap_h > sw_plunger_h + sw_travel,
       "aperture too short for the plunger plus its travel");
assert(bh_z1() > bh_apert_z1(), "no switch pocket");
assert(bh_block >= sw_body + 2*clr + 2*bh_wall, "switch pocket walls thinner than bh_wall");
// the block has to be wide enough to LAND on the plate: the lip relief is cut through
// the plate's lower face, so a block narrower than that relief would float unsupported
assert(bh_block >= bh_relief_d() + 2*bh_wall,
       "holder block is narrower than the lip relief — it would print unsupported");
assert(bh_plate_w >= bh_relief_d() + 2*2, "holder plate too narrow around the lip relief");
assert(bh_plate_l >= btn_pilot_pitch + 2*(bh_screw_clear + 1.5),
       "holder plate too short to carry both screws");
assert(bh_plate_w >= bh_block && bh_plate_l >= bh_block, "holder plate narrower than its own block");
assert(bh_screw_clear > board_screw_pilot, "holder holes must clear the M2 they pass");
assert(sw_leg_slot_w < sw_body + 2*clr + 2*bh_wall, "leg slots wider than the block");
assert(bh_plate_r > 0 && bh_plate_r < min(bh_plate_w, bh_plate_l)/2, "holder plate corner radius");

// -- the assembled module must fit the box and clear what is under it --
assert(bh_z1() < top_depth() - 2, "button module reaches the base plate");
if (!aabb_clear(btn_pos, [bh_plate_w, bh_plate_l], s3_pocket_c(), s3_pocket_f()))
    assert(s3_top_z() > bh_z1() + 2, "button module collides with the devkit");
if (!aabb_clear(btn_pos, [bh_plate_w, bh_plate_l], dac_pocket_c(), dac_pocket_f()))
    assert(dac_top_z() > bh_z1() + 2, "button module collides with the DAC");
clears_bosses(btn_pos, [bh_plate_w, bh_plate_l], "button holder plate");
assert(aabb_clear(btn_pos, [bh_plate_w, bh_plate_l], mic_pos, mic_size()),
       "button holder plate overlaps the mic seat");

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
assert(abs(s3_pos_x) + s3_pocket_f()[0]/2 <= lip_inner_half(), "devkit pocket fouls the register lip (x)");
assert(max(abs(s3_pocket_y0()), abs(s3_pocket_y1())) <= lip_inner_half(), "devkit pocket fouls the register lip (y)");
assert(dac_pocket_x1() <= lip_inner_half(), "DAC pocket crosses the register lip");
assert(abs(dac_pos_y()) + dac_pocket_f()[1]/2 <= lip_inner_half(), "DAC pocket fouls the register lip (y)");
assert(dac_pocket_x0() < dac_pocket_x1(), "DAC pocket has no length — the board is too long for the plate");
// the pockets must clear the plate's own screw counterbores
for (cb = boss_cs) {
    assert(aabb_clear(s3_pocket_c(), s3_pocket_f(), cb, [screw_cbore_d, screw_cbore_d]),
           "devkit pocket clashes a base-plate screw");
    assert(aabb_clear(dac_pocket_c(), dac_pocket_f(), cb, [screw_cbore_d, screw_cbore_d]),
           "DAC pocket clashes a base-plate screw");
}
assert(s3_seat_h > 0 && s3_lip > 0, "devkit pocket needs a floor and a retaining lip");
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
assert(s3_wall_top_z() > bh_z1() + 2 || abs(s3_pos_x) + s3_pocket_f()[0]/2 - pocket_wall > bh_plate_w/2,
       "devkit pocket wall is tall enough to hit the button holder — reduce s3_lip");
assert(dac_wall_top_z() > wall + 2, "DAC pocket wall reaches the top face — reduce dac_lip");
// The DAC lip covers the socket rather than stopping partway up it. It is NOT what resists
// a levered plug: the walls sit ~4 mm clear of the socket in y, so that job belongs to the
// counterbore in the shell wall, which wraps the socket body with 0.4 mm all round.
assert(dac_lip >= dac_jack_h,
       str("dac_lip does not cover the 3.5 mm socket — needs at least ", dac_jack_h));
assert(dac_lip <= dac_jack_h + 2, "dac_lip now stands proud of the socket — it adds nothing");

// ---- pin relief: the reason the floors are not flat ----
// Without it the board rests on its solder-side pin tails, sits ~2 mm proud, and the lip
// ends up level with the gap UNDER the board instead of its edge — which is what made
// the first walls appear to "cover the pins".
assert(board_pin_h > 0, "no pin relief: the board would seat on its own pin tails");
// The strips must stop SHORT of the cavity face, or they undercut the pocket wall's base and
// its exposed height grows by the relief depth — which is what made the DAC's front wall
// look paper-thin. Still has to reach under the header row, ~2.5 mm in from the board edge.
assert(pin_relief_setback > 0, "pin relief undercuts the pocket wall base");
assert(pin_relief_setback + 1 < board_clr + 2.5,
       "pin relief setback pushes the channel out from under the header row");
assert(board_pin_h + clr <= s3_seat_h - 0.8,
       str("pin relief would leave too little devkit pocket floor — raise s3_seat_h to at least ",
           board_pin_h + clr + 0.8));
assert(board_pin_h + clr <= dac_seat_h - 0.8,
       str("pin relief would leave too little DAC pocket floor — raise dac_seat_h to at least ",
           board_pin_h + clr + 0.8));
// Devkit: strips on the LONG (+-x) edges, so they must leave a central land in x and an
// end land in y.
assert(2*pin_row_w < s3_l + 2*board_clr - 4, "pin relief strips swallow the devkit's central land");
assert(pin_land > 1 && 2*pin_land < s3_w, "devkit pin relief leaves no end land");
// DAC: strips on the SHORT (+-y) edges instead, because its long +x edge carries the
// socket and needs floor under it. So the lands swap axes.
assert(2*pin_row_w < dac_l + 2*board_clr - 4, "pin relief strips swallow the DAC's central land");
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
assert(dac_relief_xhi() >= dac_pocket_x1() - 0.001,
       "DAC relief stops short of the floor's open edge — it would be a dead end");
assert(dac_relief_xhi() <= lip_inner_half() + 0.001,
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
    assert(abs(v[0]) + v[2]/2 <= lip_inner_half() && abs(v[1]) + v[3]/2 <= lip_inner_half(),
           str("vent at ", vc, " runs into the register lip"));
}
// foot_positions is empty by default — see params. These checks exist for anyone who
// re-populates it. A foot recess is on the OUTER face and a pocket floor on the INNER
// one, and in a 3 mm plate the two together do not fit, so a foot may not sit under a
// pocket at all: that is the check the old "sum of depths" version was too loose to
// catch, and it let a foot land 0.1 mm inside the DAC pocket floor.
for (f = foot_positions) {
    assert(abs(f[0]) + foot_d/2 <= plan/2 - 2 && abs(f[1]) + foot_d/2 <= plan/2 - 2,
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
