include <../modules/params.scad>
include <../modules/lib.scad>

// Relationship checks — robust to tuning spk_od / spk_gap / depths in params.scad.

// Two drivers sit symmetric about X with exactly spk_gap between their edges.
assert(2*spk_cx() - spk_od == spk_gap, "driver edge gap should equal spk_gap");

// Front shell must be deep enough to clear the driver front-to-back.
assert(front_depth >= spk_depth, "front_depth must clear the driver depth");

// Grille opening stays inside the driver; bolt circle clears the driver OD.
assert(spk_cut < spk_od, "grille field must be smaller than the driver");
assert(spk_bolt_circle > spk_od, "bolt circle must clear the driver OD");

// Gasket groove sits on the flange land and doesn't cut through the baffle.
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");

// Board row (cradle + amps) sits in the lower strip, below center.
assert(board_cy() < 0, "board row should be below center");

// Mic perforation lands below the button, still within the module footprint.
assert(mic_y() < board_cy(), "mic cluster should be below the button");
assert(board_cy() - mic_y() <= mod_w/2, "mic cluster should stay over the module");

// USB-C bottom exit is a BOUNDED (sealed) hole at the port depth usb_z, sized to
// the connector cross-section + clearance. It must leave bottom-wall material
// front AND back (not run off to the back edge), and the matching cradle slot
// must sit within the module depth.
usb_z_half = (usb_conn_t + usb_clr)/2;
assert(usb_z - usb_z_half >= wall, "USB bottom hole runs into the front face — increase usb_z");
assert(usb_z + usb_z_half <= front_depth - wall, "USB bottom hole runs to the back edge (not sealed) — decrease usb_z or deepen the shell");
assert(usb_z - wall - usb_z_half >= 0 && usb_z - wall + usb_z_half <= mod_d, "cradle USB slot falls outside the module depth — adjust usb_z");
assert((usb_conn_w + usb_clr)/2 + boss_od/2 <= (outer_w()/2 - boss_inset), "USB bottom hole overlaps a corner lid boss");

// The rear plate is a FLAT lid. The 4 corner M3 bosses live entirely on the
// front shell and span the full internal depth to the rear plate's inner face;
// the screws self-tap from the back straight into them. So the assembled depth
// is just the front shell plus the rear lid's wall — NOT an extra rear_depth of
// proud "mating bosses" standing off the plate (which would either poke out the
// back, fouling the flush keyhole wall-mount, or collide with the front bosses).
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// ---- depth spacer ----
assert(spacer_t > 0, "spacer_t must be positive");
assert(spigot_h > 0 && spigot_h < spacer_t, "spigot must be positive and shorter than the spacer body");
assert(spigot_wall > 0 && spigot_wall <= wall, "spigot wall must be positive and not exceed the shell wall");
// spigot lip nests inside the front shell's rear opening (with clearance both sides)
assert(outer_w() - 2*wall - 2*clr - 2*spigot_wall > 0, "spigot lip must fit inside the front cavity");
// spacer body must be shorter than the front boss depth so the existing screws still reach a boss to bite
assert(spacer_t < front_depth - wall, "spacer_t must be less than the front boss depth (front_depth - wall) so screws still engage");

// ---- button offset (toward the top, over the real dome switch) ----
assert(btn_above_center >= 0, "btn_above_center must be non-negative");
assert(btn_above_center + btn_nub_d/2 <= (btn_well_d - 2*clr)/2, "offset nub must stay fully under the cap skirt — reduce btn_above_center (or shrink btn_nub_d / widen btn_well_d)");
assert(btn_slice > 0 && btn_slice < btn_cap_d/2 - btn_nub_d/2, "btn_slice must be a positive bottom flat that doesn't reach the offset nub side");

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
