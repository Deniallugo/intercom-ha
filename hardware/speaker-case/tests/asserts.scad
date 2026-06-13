include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
assert(outer_w() == 158, "outer width drifted from 158");
assert(outer_h() == 159, "outer height drifted from 159");
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
// PR disc fits the side panel's chamber region in y (height) and z (depth)
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
// DAC–mic is the tightest pair (~0.5 mm bare-footprint margin); nudge with care
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "DAC overlaps mic");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(trig_pos),[trig_w,trig_l]), "buck overlaps trigger");
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(trig_pos),[trig_w,trig_l]), "DAC overlaps trigger");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "buck overlaps mic");
// TPA mounts on the rear lid; cavity must clear front standoff + board + TPA stack
assert(cavity_depth >= board_standoff_h + 2 + 16, "cavity too shallow for front + rear board stack");

// ===== front-panel breaches (bay only — chamber stays sealed) =====
btn_c = bpos(btn_pos);
// PTT bore (incl. its nut relief) sits in the bay, below the divider, within width
assert(btn_c[1] + btn_nut_d/2 < divider_cy() - divider_t/2, "PTT bore breaches the chamber");
assert(btn_c[0] - btn_nut_d/2 > bay_xmin && btn_c[0] + btn_nut_d/2 < bay_xmax, "PTT bore off bay width");
// CONTROLLER ENHANCEMENT: the nut relief must clear the S3 pocket and trigger standoffs
assert(aabb_clear(btn_c,[btn_nut_d,btn_nut_d], bpos(s3_pos),[s3_w,s3_l]), "PTT bore clashes the S3 pocket");
assert(aabb_clear(btn_c,[btn_nut_d,btn_nut_d], bpos(trig_pos),[trig_w,trig_l]), "PTT bore clashes the trigger board");
// mic perforation lands over the mic board, in the bay
assert(board_cy()+mic_pos[1] < divider_cy() - divider_t/2, "mic perforation breaches the chamber");
// USB-C bottom exit is a bounded hole at the receptacle depth
usb_z_half = (usb_conn_t + usb_clr)/2;
assert(usb_z - usb_z_half >= wall, "USB hole runs into the front face — increase usb_z");
assert(usb_z + usb_z_half <= front_depth - wall, "USB hole runs to the back edge — decrease usb_z");
assert((usb_conn_w + usb_clr)/2 + boss_od/2 <= (outer_w()/2 - boss_inset), "USB hole overlaps a corner lid boss");

// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// helper render smoke
linear_extrude(1) rounded_rect(20, 10, 2);
screw_boss(8, boss_od, screw_pilot);
screw_circle(4, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);

cube(1);  // non-empty render under --hardwarnings
