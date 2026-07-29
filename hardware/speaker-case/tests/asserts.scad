include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
assert(outer_w() == 158, "outer width drifted from 158");
assert(outer_h() == 165, "outer height drifted from 165");
assert(outer_d() == 118, "outer depth drifted from 118");

// ===== speaker zone (upper, sealed) =====
assert(spk_cut < spk_od, "cone cutout must be smaller than the driver frame");
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");
assert(cavity_depth >= spk_depth, "cavity must clear the driver seated depth");
assert(net_vol() >= vol_target, "net chamber volume below target — grow spk_zone_h / cavity_depth / inner_w");

// driver bolt circle clears the cone cutout and the side walls
assert(spk_bolt_circle/2 - spk_boss_od/2 > spk_cut/2, "driver bosses overlap the cone cutout");
assert(spk_cx() + spk_bolt_circle/2 + spk_boss_od/2 <= outer_w()/2 - wall, "driver bosses hit the side wall");
// the LOCATING RING, not the frame, is what actually sets the chamber height
assert(spk_cy() + (spk_od + 2*seat_wall)/2 <= outer_h()/2 - wall, "driver seat ring runs off the chamber top — raise spk_zone_h");
assert(spk_cy() - (spk_od + 2*seat_wall)/2 >= divider_cy() + divider_t/2, "driver seat ring overlaps the divider — raise spk_zone_h");
// driver (and its lowest boss) stays above the divider
assert(spk_cy() - spk_od/2 > divider_cy() + divider_t/2, "driver overlaps the divider — raise spk_zone_h");
assert(spk_cy() - spk_bolt_circle/2 - spk_boss_od/2 > divider_cy() + divider_t/2, "driver bosses overlap the divider");

// ===== divider (single sealed wire pass) =====
assert(divider_cy() < spk_cy() && divider_cy() > board_cy(), "divider must sit between the zones");
assert(divider_wire_z - divider_wire_d/2 >= wall, "wire pass runs into the front face — raise divider_wire_z");
assert(divider_wire_z + divider_wire_d/2 <= front_depth, "wire pass runs off the back edge — lower divider_wire_z");

// ===== passive radiator (side panel, +x) =====
assert(pr_cut < pr_od, "PR cutout must be smaller than the PR frame");
assert(pr_gasket_id < pr_gasket_od, "PR gasket groove must have id < od");
assert(pr_gasket_id >= pr_cut && pr_gasket_od <= pr_od, "PR gasket must sit on the flange land");
assert(pr_gasket_depth < wall, "PR gasket groove must not cut through the side wall");
// PR disc (with its locating ring) fits the side panel's chamber region in y and z
assert(spk_cy() + (pr_od + 2*pr_seat_wall)/2 <= (outer_h()/2 - wall), "PR seat ring runs off the top of the chamber");
assert(spk_cy() - (pr_od + 2*pr_seat_wall)/2 >= divider_cy() + divider_t/2, "PR seat ring dips below the divider");
assert(spk_cy() + pr_od/2 <= (outer_h()/2 - wall), "PR runs off the top of the chamber");
assert(spk_cy() - pr_od/2 >= divider_cy() + divider_t/2, "PR dips below the divider");
assert(pr_cz() - pr_od/2 >= wall, "PR runs into the front face");
assert(pr_cz() + pr_od/2 <= front_depth, "PR runs off the back edge");
// PR intrusion clears the driver basket on the centerline
assert(side_x() - pr_depth > spk_cx() + spk_od/2, "PR intrudes into the driver basket");

// ===== electronics bay (front-baffle boards) =====
// absolute board centers in the bay (board_cy() + per-board offset)
function bpos(p) = [p[0], board_cy() + p[1]];
bay_xmin = -(outer_w()/2 - wall); bay_xmax = outer_w()/2 - wall;
bay_ymin = board_cy() - board_zone_h/2; bay_ymax = divider_cy() - divider_t/2;

// each front-baffle board stays inside the bay rectangle
module in_bay(p, w, l, name) {
    c = bpos(p);
    assert(c[0]-w/2 >= bay_xmin && c[0]+w/2 <= bay_xmax, str(name, " off bay width"));
    assert(c[1]-l/2 >= bay_ymin && c[1]+l/2 <= bay_ymax, str(name, " off bay height"));
}
in_bay(s3_pos,   s3_w,  s3_l,  "S3");
in_bay(dac_pos,  dac_w, dac_l, "DAC");
in_bay(buck_pos, buck_w, buck_l, "buck");
in_bay(trig_pos, trig_w, trig_l, "trigger");
in_bay(mic_pos,  mic_board_w, mic_board_l, "mic");

// front-baffle boards do not overlap each other (pairwise)
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(dac_pos),[dac_w,dac_l]), "S3 overlaps DAC");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(buck_pos),[buck_w,buck_l]), "S3 overlaps buck");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(trig_pos),[trig_w,trig_l]), "S3 overlaps trigger");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "S3 overlaps mic");
// DAC–mic is the tightest pair; compared at the mic POCKET's outer size, since the
// pocket wall (not just the board) is what would foul the DAC's edge
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l],
                  bpos(mic_pos),[mic_board_w + 2*pocket_wall, mic_board_l + 2*pocket_wall]), "DAC overlaps the mic pocket");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(trig_pos),[trig_w,trig_l]), "buck overlaps trigger");
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(trig_pos),[trig_w,trig_l]), "DAC overlaps trigger");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "buck overlaps mic");
// TPA mounts on the rear lid; cavity must clear front standoff + board + TPA stack
assert(cavity_depth >= board_standoff_h + 2 + 16, "cavity too shallow for front + rear board stack");
// the S3 rides high in the bay to free the bottom strip for the PTT nut pocket:
// its POCKET (walls included, not just the footprint) must clear the divider
assert(bpos(s3_pos)[1] + s3_l/2 + pocket_wall <= bay_ymax, "S3 pocket runs into the divider — lower s3_pos");

// ===== front-panel breaches (bay only — chamber stays sealed) =====
btn_c = bpos(btn_pos);
btn_sq = [btn_pocket_d, btn_pocket_d];
s3_pocket_sz  = [s3_w + 2*pocket_wall, s3_l + 2*pocket_wall];
mic_pocket_sz = [mic_board_w + 2*pocket_wall, mic_board_l + 2*pocket_wall];
// the switch must clamp on flats: a thinned-but-solid panel, nut seat wider than the nut
assert(btn_bore_d > btn_thread_d, "PTT bore must clear the switch thread");
assert(btn_panel_t > 0 && btn_panel_t < wall, "PTT panel thinning must leave a solid, thinner panel");
assert(btn_pocket_d > btn_bore_d, "PTT counterbore must be wider than the thread bore");
assert(btn_pocket_d > btn_nut_ac(), "PTT counterbore won't clear the nut across corners — widen btn_pocket_d");
assert(btn_halo_id >= btn_pocket_d, "PTT halo groove overlaps the counterbore — it would thin the nut seat");
assert(btn_halo_od > btn_halo_id && btn_halo_depth < wall - btn_panel_t, "PTT halo groove geometry");
// the counterbore sits in the bay, below the divider, within width
in_bay(btn_pos, btn_pocket_d, btn_pocket_d, "PTT counterbore");
// ...and clears every neighbour it shares the bottom strip with (pockets at their outer size)
assert(aabb_clear(btn_c, btn_sq, bpos(s3_pos), s3_pocket_sz), "PTT counterbore clashes the S3 pocket");
assert(aabb_clear(btn_c, btn_sq, bpos(trig_pos), [trig_w,trig_l]), "PTT counterbore clashes the trigger board");
assert(aabb_clear(btn_c, btn_sq, bpos(mic_pos), mic_pocket_sz), "PTT counterbore clashes the mic pocket");
for (sx = [-1, 1])
    assert(aabb_clear(btn_c, btn_sq, [sx*(outer_w()/2 - boss_inset), -(outer_h()/2 - boss_inset)], [boss_od, boss_od]),
           "PTT counterbore clashes a corner lid boss");
// the halo ring stays on the front face, clear of the bottom edge
assert(abs(btn_pos[0]) + btn_halo_od/2 <= outer_w()/2 - wall, "PTT halo runs off the front face width");
assert(board_cy() + btn_pos[1] - btn_halo_od/2 >= -outer_h()/2 + 2, "PTT halo runs off the bottom edge");
// the switch body behind the panel must clear the lid-mounted TPA stack
assert(btn_panel_t + btn_body_l + 16 <= front_depth, "switch body + rear TPA stack deeper than the cavity");
// mic perforation lands over the mic board, in the bay
assert(board_cy()+mic_pos[1] < divider_cy() - divider_t/2, "mic perforation breaches the chamber");   // perf is concentric within the mic board, which in_bay already bounds
// USB-C bottom exit is a bounded hole at the receptacle depth
usb_z_half = (usb_conn_t + usb_clr)/2;
assert(usb_z - usb_z_half >= wall, "USB hole runs into the front face — increase usb_z");
assert(usb_z + usb_z_half <= front_depth - wall, "USB hole runs to the back edge — decrease usb_z");
assert((usb_conn_w + usb_clr)/2 + boss_od/2 <= (outer_w()/2 - boss_inset), "USB hole overlaps a corner lid boss");

// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0, "lid gasket inset too large");
// keyholes fit the wider plate
assert(keyhole_spacing/2 + keyhole_head_d/2 + kb_pad <= outer_w()/2 - wall, "keyhole bosses run off the plate width");
assert(keyhole_spacing/2 - keyhole_head_d/2 - kb_pad > 0, "keyhole bosses overlap at center");
// TPA on the lid inner face lands inside the bay, doesn't foul the chamber
assert(board_cy()+tpa_pos[1] + tpa_l/2 < divider_cy() - divider_t/2, "TPA on lid breaches the chamber zone");
assert(board_cy()+tpa_pos[1] - tpa_l/2 >= board_cy() - board_zone_h/2, "TPA on lid off the plate height (bottom)");
assert(abs(tpa_pos[0]) + tpa_w/2 <= outer_w()/2 - wall, "TPA on lid off the plate width");

// helper render smoke
linear_extrude(1) rounded_rect(20, 10, 2);
screw_boss(8, boss_od, screw_pilot);
screw_circle(4, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);

cube(1);  // non-empty render under --hardwarnings
