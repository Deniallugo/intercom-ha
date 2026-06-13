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

// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// helper render smoke
linear_extrude(1) rounded_rect(20, 10, 2);
screw_boss(8, boss_od, screw_pilot);
screw_circle(4, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);

cube(1);  // non-empty render under --hardwarnings
