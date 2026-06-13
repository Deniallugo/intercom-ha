include <../modules/params.scad>
include <../modules/lib.scad>

// ===== speaker zone (upper, sealed) =====

// Two drivers symmetric about X with exactly spk_gap between their frame edges.
assert(2*spk_cx() - spk_od == spk_gap, "driver edge gap should equal spk_gap");
// Open cone cutout stays inside the driver frame.
assert(spk_cut < spk_od, "cone cutout must be smaller than the driver frame");

// Gasket groove sits on the flange land, doesn't pierce the baffle.
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");

// Chamber clears the driver; sealed volume meets the floor.
assert(cavity_depth >= spk_depth, "cavity must clear the driver seated depth");
assert(net_vol() >= vol_target, "net sealed chamber volume below target — grow spk_zone_h / cavity_depth");

// Driver screw square clears the cone cutout and the side walls.
spk_screw_r = spk_screw_square/2 * sqrt(2);   // boss radius from the driver center
assert(spk_screw_r - spk_boss_od/2 > spk_cut/2, "driver screw bosses overlap the cone cutout");
assert(spk_cx() + spk_screw_square/2 + spk_boss_od/2 <= outer_w()/2 - wall, "driver screw boss hits the side wall");
// Drivers (and their lowest screw bosses) stay above the divider.
assert(spk_cy() - spk_od/2 > divider_cy() + divider_t/2, "driver overlaps the divider — raise spk_zone_h");
assert(spk_cy() - spk_screw_square/2 > divider_cy() + divider_t/2, "driver screw bosses overlap the divider");

// ===== divider (sealing floor) =====

// Divider sits between the two zones.
assert(divider_cy() < spk_cy() && divider_cy() > board_cy(), "divider must sit between speaker and board zones");
// Wire pass is a BOUNDED (sealed) hole within the cavity depth.
assert(divider_wire_z - divider_wire_d/2 >= wall, "divider wire pass runs into the front face — raise divider_wire_z");
assert(divider_wire_z + divider_wire_d/2 <= front_depth, "divider wire pass runs off the back edge — lower divider_wire_z");

// ===== electronics bay (lower, vented) =====

// Board zone is tall enough for the module footprint.
assert(board_zone_h >= mod_w + 2*mod_clr, "board zone too short for the module");
// Amps flank the module without hitting the side walls or crossing the divider.
assert(amp_off() + amp_w/2 <= outer_w()/2 - wall, "amp board hits the side wall");
assert(board_cy() + amp_l/2 < divider_cy() - divider_t/2, "amp board overlaps the divider");
assert(amp_off() - amp_w/2 > (mod_w + 2*mod_clr)/2 + cradle_wall, "amp board overlaps the module cradle");

// Mic cluster lands below the button, still within the module footprint.
assert(mic_y() < board_cy(), "mic cluster should be below the module center");
assert(board_cy() - mic_y() <= mod_w/2, "mic cluster should stay over the module");

// Button offset nub stays fully under the cap skirt; bottom slice is valid.
assert(btn_above_center >= 0, "btn_above_center must be non-negative");
assert(btn_above_center + btn_nub_d/2 <= (btn_well_d - 2*clr)/2, "offset nub must stay under the cap skirt");
assert(btn_slice > 0 && btn_slice < btn_cap_d/2 - btn_nub_d/2, "btn_slice must be a positive bottom flat clear of the nub");

// USB-C bottom exit is a BOUNDED (sealed) hole at the port depth, leaving wall
// material front AND back, with the cradle slot inside the module depth.
usb_z_half = (usb_conn_t + usb_clr)/2;
assert(usb_z - usb_z_half >= wall, "USB bottom hole runs into the front face — increase usb_z");
assert(usb_z + usb_z_half <= front_depth - wall, "USB bottom hole runs to the back edge (not sealed) — decrease usb_z");
assert(usb_z - wall - usb_z_half >= 0 && usb_z - wall + usb_z_half <= mod_d, "cradle USB slot falls outside the module depth");
assert((usb_conn_w + usb_clr)/2 + boss_od/2 <= (outer_w()/2 - boss_inset), "USB bottom hole overlaps a corner lid boss");

// Module retention clamp: positive reach, fits the pocket, open center.
assert(mod_clamp_h() > 0, "module clamp must have positive reach — front_depth too shallow vs the module depth");
assert(mod_clamp_foot <= mod_w + 2*mod_clr, "module clamp must fit inside the cradle pocket opening");
assert(mod_clamp_foot - 2*mod_clamp_wall > 0, "module clamp wall too thick — collar has no open center");

// ===== rear lid / shell =====

// Assembled depth is front shell + flat lid.
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// Lid gasket groove sits inside the perimeter, doesn't pierce the lid.
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(lid_gasket_inset + lid_gasket_w/2 < radius + wall || lid_gasket_inset > radius,
       "lid gasket groove should sit on a flat perimeter band");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0,
       "lid gasket groove inset too large for the plate");

// BLIND keyhole bosses: fit within the plate width and the cut stays in the boss
// (never through the lid panel, so the chamber behind stays sealed).
assert(keyhole_spacing/2 + keyhole_head_d/2 + kb_pad <= outer_w()/2 - wall, "keyhole bosses run off the plate width");
assert(keyhole_spacing/2 - keyhole_head_d/2 - kb_pad > 0, "keyhole bosses overlap at center — widen keyhole_spacing");
assert(kb_h > 0 && kb_h <= keyhole_head_d, "keyhole boss height should be a shallow counterbore");

// Grille perforation field stays within the driver frame.
assert(spk_cut <= spk_od, "grille field must stay within the driver frame");

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
