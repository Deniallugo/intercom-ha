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

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
