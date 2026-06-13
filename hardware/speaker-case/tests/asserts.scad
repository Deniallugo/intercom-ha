include <../modules/params.scad>
include <../modules/lib.scad>

// ---- body: driver layout ----
// Two drivers symmetric about X with exactly spk_gap between their frame edges.
assert(2*spk_cx() - spk_od == spk_gap, "driver edge gap should equal spk_gap");
// Open cone cutout stays inside the driver frame.
assert(spk_cut < spk_od, "cone cutout must be smaller than the driver frame");

// ---- body: gasket groove sits on the flange land, doesn't pierce the baffle ----
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");

// ---- body: depth clears the driver, sealed volume meets the floor ----
assert(cavity_depth >= spk_depth, "cavity must clear the driver seated depth");
assert(net_vol() >= vol_target, "net sealed volume below target — grow cavity_depth or margins");

// ---- body: driver screw square clears the cone cutout and the side walls ----
spk_screw_r = spk_screw_square/2 * sqrt(2);   // boss radius from the driver center
assert(spk_screw_r - spk_boss_od/2 > spk_cut/2, "driver screw bosses overlap the cone cutout");
assert(spk_cx() + spk_screw_square/2 + spk_boss_od/2 <= outer_w()/2 - wall, "driver screw boss hits the side wall");

// ---- body: bottom wire pass is a BOUNDED (sealed) hole, not a slot to the back edge ----
assert(wire_pass_z - wire_pass_d/2 >= wall, "wire pass runs into the front face — raise wire_pass_z");
assert(wire_pass_z + wire_pass_d/2 <= front_depth, "wire pass runs off the back edge (not sealed) — lower wire_pass_z");

// ---- body: assembled depth is front shell + flat lid (rear plate is a flat lid) ----
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// ---- rear plate: gasket groove sits inside the perimeter, doesn't pierce the lid ----
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(lid_gasket_inset + lid_gasket_w/2 < radius + wall || lid_gasket_inset > radius,
       "lid gasket groove should sit on a flat perimeter band");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0,
       "lid gasket groove inset too large for the plate");

// ---- rear plate: keyholes fit within the plate width and clear the corner bosses ----
assert(keyhole_spacing/2 + keyhole_head_d/2 <= outer_w()/2 - wall, "keyholes run off the plate width");
assert(keyhole_spacing/2 - keyhole_head_d/2 > 0, "keyholes overlap at center — widen keyhole_spacing");

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
