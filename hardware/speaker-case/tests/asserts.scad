include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
assert(outer_w() == 86,  "outer width drifted from 86");
assert(outer_h() == 194, "outer height drifted from 194");
assert(outer_d() == 88,  "outer depth drifted from 88");
assert(chamfer < radius, "front chamfer must be smaller than the corner radius");
assert(chamfer > 0 && chamfer < front_depth, "front chamfer out of range");
assert(flat_w() > 0 && flat_h() > 0, "front chamfer swallowed the whole front face");

// ===== drivers (vertical pair, upper sealed zone) =====
assert(spk_n == 2, "this shell is drawn for a vertical PAIR");
assert(spk_cut < spk_od, "cone cutout must be smaller than the driver frame");
assert(spk_recess_depth < wall, "driver recess must not cut through the baffle");
// The pilot is drilled from the RECESS FLOOR into wall + pad, so the depth that
// matters is the sum. (wall alone let recess 1.0 + pilot 3.0 reach exactly 4.0 and
// vent all eight pilots into the chamber.) Keep >= 1 mm of solid floor.
assert(spk_recess_depth + spk_pilot_depth <= wall + spk_pad_t - 1,
       "driver pilots break through the baffle — deepen spk_pad_t or shorten spk_pilot_depth");
assert(spk_pad_d > spk_bolt_circle + spk_screw_pilot, "baffle pad does not reach the bolt circle");
assert(spk_pad_d < spk_pitch, "baffle pads collide — reduce spk_pad_d or raise spk_pitch");
assert(spk_pad_d > spk_cut, "baffle pad must be wider than the cone cutout");
assert(wall + spk_pad_t + spk_depth <= front_depth, "driver + baffle pad deeper than the cavity");
assert(cavity_depth >= spk_depth, "cavity must clear the driver seated depth");
assert(net_vol() >= vol_target, "net chamber volume below target — grow spk_zone_h / cavity_depth / inner_w");
// the bolt circle must land on the flange land: outside the cutout, inside the frame.
// The published "43 mm square (60 mm diagonal)" satisfies neither — see params.
assert(spk_bolt_circle > spk_cut, "driver screws fall inside the cone cutout");
assert(spk_bolt_circle < spk_od,  "driver screws fall outside the driver frame");
// drivers do not collide with each other
assert(spk_pitch > spk_recess_d, "driver recesses overlap — raise spk_pitch");
// each driver clears the chamber top, the divider, and the front chamfer
for (i = [0 : spk_n - 1]) {
    assert(spk_cy(i) + spk_recess_d/2 <= outer_h()/2 - wall,
           "driver recess runs off the chamber top — raise spk_zone_h or lower spk_pitch");
    assert(spk_cy(i) - spk_recess_d/2 >= divider_cy() + divider_t/2,
           "driver recess overlaps the divider — raise spk_zone_h or lower spk_pitch");
    assert(abs(spk_cy(i)) + spk_recess_d/2 <= flat_h()/2,
           "driver recess runs onto the front chamfer — reduce chamfer or spk_pitch");
}
assert(spk_recess_d <= flat_w(), "driver recess wider than the flat front face — reduce chamfer or grow inner_w");

// ===== tuned port (+x side wall) =====
assert(port_id > 0 && port_wall > 0, "port geometry");
assert(port_flange_od > port_od(), "port flange must be wider than the barrel");
assert(port_flange_t < wall, "port flange register must not cut through the side wall");
assert(port_len > wall, "port must be longer than the wall it passes through");
// port area >= 10% of total cone area (Sd ~1450 mm^2 each), or it chuffs
assert(PI/4*pow(port_id,2) >= 0.1 * spk_n * 1450, "port too narrow for two 53 mm cones");
// the tube fits the chamber in y and z, clears the baskets, and never reaches the far wall
assert(port_cz - port_od()/2 >= wall, "port runs into the front face — raise port_cz");
assert(port_cz + port_od()/2 <= front_depth, "port runs off the back edge — lower port_cz");
assert(port_cz - port_od()/2 >= wall + spk_depth, "port tube fouls the driver baskets — raise port_cz");
assert(port_len - wall < inner_w, "port tube hits the far side wall — shorten it");
assert(spk_zone_cy() + port_od()/2 <= outer_h()/2 - wall, "port runs off the chamber top");
assert(spk_zone_cy() - port_od()/2 >= divider_cy() + divider_t/2, "port dips below the divider");

// ===== divider: sealed terminal bolts =====
assert(divider_cy() < spk_zone_cy() && divider_cy() > board_cy(), "divider must sit between the zones");
assert(term_n >= 2*spk_n, "dual mono on a BTL amp needs 2 conductors PER driver");
assert(term_oring_od > term_d, "O-ring seat must be wider than the bolt bore");
assert(term_oring_depth < divider_t/2, "O-ring seat must not halve the divider");
assert(term_cz - term_oring_od/2 >= wall, "terminal row runs into the front face");
assert(term_cz + term_oring_od/2 <= front_depth, "terminal row runs off the back edge");
assert(term_cz >= wall + spk_depth, "terminals sit under a driver basket — raise term_cz");
assert((term_n-1)*term_pitch/2 + term_oring_od/2 <= inner_w/2, "terminal row wider than the divider");

// ===== electronics bay =====
function bpos(p) = [p[0], board_cy() + p[1]];
bay_xmin = -(outer_w()/2 - wall); bay_xmax = outer_w()/2 - wall;
bay_ymin = board_cy() - board_zone_h/2; bay_ymax = divider_cy() - divider_t/2;

module in_bay(p, w, l, name) {
    c = bpos(p);
    assert(c[0]-w/2 >= bay_xmin && c[0]+w/2 <= bay_xmax, str(name, " off bay width"));
    assert(c[1]-l/2 >= bay_ymin && c[1]+l/2 <= bay_ymax, str(name, " off bay height"));
}
// front wall: the S3 pocket, at its OUTER size (walls included), must clear the divider
in_bay(s3_pos, s3_w, s3_l, "S3");
assert(bpos(s3_pos)[1] + s3_l/2 + pocket_wall <= bay_ymax, "S3 pocket runs into the divider — lower s3_pos");
assert(abs(s3_pos[0]) + s3_w/2 + pocket_wall <= bay_xmax, "S3 pocket wider than the bay");
// rear lid: DAC + amp share the inner face
in_bay(dac_pos, dac_w, dac_l, "DAC");
in_bay(amp_pos, amp_w, amp_l, "amp");
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(amp_pos),[amp_w,amp_l]), "DAC overlaps the amp on the lid");
// the lid boards must clear the lid's own corner screw holes
for (sx = [-1, 1], sy = [-1, 1]) {
    cb = [sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset)];
    assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], cb,[boss_od,boss_od]), "DAC clashes a corner boss");
    assert(aabb_clear(bpos(amp_pos),[amp_w,amp_l], cb,[boss_od,boss_od]), "amp clashes a corner boss");
}
// front standoff + board + lid standoff + board must fit the cavity depth
assert(cavity_depth >= 2*(board_standoff_h + 1.6) + 12, "cavity too shallow for the front + lid board stack");

// ===== front-panel breaches (bay only — chamber stays sealed) =====
btn_c = bpos(btn_pos);
btn_sq = [btn_pocket_d, btn_pocket_d];
s3_pocket_sz = [s3_w + 2*pocket_wall, s3_l + 2*pocket_wall];
// the switch must clamp on flats: a thinned-but-solid panel, nut seat wider than the nut
assert(btn_bore_d > btn_thread_d, "PTT bore must clear the switch thread");
assert(btn_panel_t > 0 && btn_panel_t < wall, "PTT panel thinning must leave a solid, thinner panel");
assert(btn_pocket_d > btn_bore_d, "PTT counterbore must be wider than the thread bore");
assert(btn_pocket_d > btn_nut_ac(), "PTT counterbore won't clear the nut across corners — widen btn_pocket_d");
assert(btn_halo_id >= btn_pocket_d, "PTT halo groove overlaps the counterbore — it would thin the nut seat");
assert(btn_halo_od > btn_halo_id && btn_halo_depth < wall - btn_panel_t, "PTT halo groove geometry");
// the counterbore sits in the bay, below the divider, within width
in_bay(btn_pos, btn_pocket_d, btn_pocket_d, "PTT counterbore");
assert(aabb_clear(btn_c, btn_sq, bpos(s3_pos), s3_pocket_sz), "PTT counterbore clashes the S3 pocket");
for (sx = [-1, 1])
    assert(aabb_clear(btn_c, btn_sq, [sx*(outer_w()/2 - boss_inset), -(outer_h()/2 - boss_inset)], [boss_od, boss_od]),
           "PTT counterbore clashes a corner lid boss");
// the halo ring must stay on the FLAT front face — the chamfer, not the outer edge,
// is the real bound now
assert(abs(btn_pos[0]) + btn_halo_od/2 <= flat_w()/2, "PTT halo runs onto the front chamfer (width)");
assert(board_cy() + btn_pos[1] - btn_halo_od/2 >= -flat_h()/2, "PTT halo runs onto the front chamfer (bottom)");
// the switch body behind the panel must clear the lid-mounted board stack
assert(btn_panel_t + btn_body_l + board_standoff_h + 1.6 <= front_depth,
       "switch body + lid board stack deeper than the cavity");

// ===== bottom-wall features (mic / USB-C / sub jack). Placements are (x, z) =====
assert(mic_seat_depth + mic_gasket_depth < wall, "mic seat + gasket seat cut through the bottom wall");
assert(mic_gasket_d > mic_hole_d, "mic gasket seat must be wider than the port");
assert(mic_gasket_d <= mic_board_l, "mic gasket seat wider than the board it seals against");
assert(mic_post_pitch/2 - mic_post_od/2 >= (mic_board_w + 2*clr)/2, "mic posts intrude into the board recess");
// the mic entry uses the COMBINED seat + flanking-post footprint, so the pairwise
// check below covers the posts too (they are what actually reach toward the jack)
bw = [[mic_pos,  mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od), "mic seat+posts"],
      [usbc_pos, usbc_w,                       usbc_l,                                "USB-C board"],
      [jack_pos, jack_nut_d,                   jack_nut_d,                            "sub jack"]];
for (f = bw) {
    p = f[0];
    assert(p[0] - f[1]/2 >= bay_xmin && p[0] + f[1]/2 <= bay_xmax, str(f[3], " off bay width"));
    assert(p[1] - f[2]/2 >= wall && p[1] + f[2]/2 <= front_depth, str(f[3], " off cavity depth"));
}
// ...and they clear each other (they share one wall)
for (a = [0 : len(bw)-2]) for (b = [a+1 : len(bw)-1])
    assert(aabb_clear([bw[a][0][0], bw[a][0][1]], [bw[a][1], bw[a][2]],
                      [bw[b][0][0], bw[b][0][1]], [bw[b][1], bw[b][2]]),
           str(bw[a][3], " overlaps ", bw[b][3], " on the bottom wall"));
// the mic posts must also clear their neighbours
assert(abs(mic_pos[0]) + mic_post_pitch/2 + mic_post_od/2 <= bay_xmax, "mic posts off bay width");
// the sub jack's barrel reaches up past the bottom corner bosses
for (sx = [-1, 1])
    assert(abs(jack_pos[0] - sx*(outer_w()/2 - boss_inset)) >= (jack_nut_d + boss_od)/2,
           "sub jack barrel clashes a bottom corner boss");
// USB-C exit slot: bounded, in the -x side wall, inside the bay
assert(usb_slot_y - usb_slot_h/2 >= 0, "USB exit slot dips below the bay floor");
assert(usb_slot_y + usb_slot_h/2 <= board_zone_h, "USB exit slot runs above the bay");
assert(usbc_pos[1] - usb_slot_w/2 >= wall && usbc_pos[1] + usb_slot_w/2 <= front_depth,
       "USB exit slot off the cavity depth");
// S3 service slot: in the BAY only, never the chamber, and at the devkit's port height
assert(board_cy() + s3_pos[1] + s3_usb_w/2 <= bay_ymax, "S3 service slot breaches the chamber");
assert(board_cy() + s3_pos[1] - s3_usb_w/2 >= bay_ymin, "S3 service slot off the bay floor");
assert(s3_usb_z() - s3_usb_h/2 >= wall && s3_usb_z() + s3_usb_h/2 <= front_depth,
       "S3 service slot off the cavity depth");
// the two side-wall breaches are on OPPOSITE walls, but the port shares +x with the
// service slot — they must not meet
assert(abs((board_cy() + s3_pos[1]) - spk_zone_cy()) >= (s3_usb_w + port_flange_od)/2,
       "S3 service slot collides with the port flange on the +x wall");

// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0, "lid gasket inset too large");
assert(boss_od >= insert_m3_d + 3, "corner boss too thin around the heat-set insert");
assert(insert_m3_d > screw_clear, "heat-set bore must be wider than the screw clearance");
// keyhole bosses fit the narrow lid, are vertically separated, and bear over the chamber
assert(len(keyhole_ys) >= 2, "need at least two keyhole bosses");
assert(keyhole_head_d/2 + kb_pad <= outer_w()/2 - wall, "keyhole boss runs off the plate width");
assert(kb_lip < kb_h, "keyhole retaining plate thicker than the boss");
for (ky = keyhole_ys) {
    assert(ky + keyhole_head_d/2 + kb_pad <= outer_h()/2 - wall, "keyhole boss runs off the plate top");
    assert(ky - keyhole_drop - keyhole_slot_w/2 - kb_pad >= divider_cy() + divider_t/2,
           "keyhole boss reaches below the chamber — the load should bear over the chamber");
}
for (a = [0 : len(keyhole_ys)-2])
    assert(keyhole_ys[a+1] - keyhole_ys[a] >= keyhole_head_d + keyhole_drop + 2*kb_pad,
           "keyhole bosses overlap vertically — spread keyhole_ys");

// helper render smoke
linear_extrude(1) rounded_rect(20, 10, 2);
screw_boss(8, boss_od, insert_m3_d);
on_bolt_circle(spk_screw_n, spk_bolt_circle) cylinder(h = 2, d = spk_screw_pilot);

cube(1);  // non-empty render under --hardwarnings
