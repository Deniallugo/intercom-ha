include <../modules/params.scad>

// Envelope must match the approved spec (~123 x 98 x 42 mm).
assert(outer_w() == 123, "outer width should be 123");
assert(outer_h() == 98,  "outer height should be 98");
assert(outer_d() == 42,  "outer depth should be 42");

// Speakers sit symmetric about X, near-touching.
assert(spk_cx() == 28, "speaker center |x| should be 28");          // 53/2 + 3/2
assert(2*spk_cx() - spk_od == spk_gap, "driver edge gap should equal spk_gap");

// Board row sits in the lower strip.
assert(board_cy() < 0, "board row should be below center");

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
