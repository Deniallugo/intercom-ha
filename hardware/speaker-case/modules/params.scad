// ===== Speaker case — sealed twin-driver wall enclosure — parameters =====
// No geometry here. AIYIMA 2"/53 mm full-range, 4 ohm. Single sealed mono box.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // clearance for inserted parts

// ---- shell ----
wall   = 4;                // walls + lid thickness (rigid, airtight target)
radius = 8;                // rounded vertical edges (diffraction win at this size)

// ---- drivers (measured in-hand; confirm vs your units) ----
spk_od    = 53;            // frame OD — the locating ring ID
spk_cut   = 46;            // OPEN cone cutout through the baffle (cone fires through)
spk_gap   = 20;            // gap between the two driver frame edges
spk_depth = 28;            // seated depth front->back
seat_wall = 1.6;           // locating ring wall thickness
spk_seat_depth = 4;        // locating ring height on the inner baffle

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1; // groove OD: just inside the locating ring
gasket_id    = spk_cut + 1;// groove ID: just outside the open cutout
gasket_depth = 1.0;        // depth cut into the baffle inner face

// ---- driver mounting screws: 4 on a 43 mm SQUARE (60 mm diagonal) ----
spk_screw_square = 43;     // hole-to-hole along a side of the square
spk_screw_pilot  = 1.6;    // M2 self-tap pilot
spk_boss_od      = 5;
spk_boss_h       = spk_seat_depth + 1;

// ---- interior margins ----
side_margin = 10;          // wall-to-driver, left/right interior
vert_margin = 13;          // wall-to-driver, top/bottom interior

// ---- cavity depth (sets the sealed volume) ----
cavity_depth = 71;         // clear air behind the cones
front_depth  = wall + cavity_depth;   // front-shell extrude = front wall + cavity

// ---- net-volume target (acoustic floor) ----
driver_disp = 25000;       // mm^3 displaced by each driver basket (measured estimate)
vol_target  = 550000;      // mm^3 net floor (~0.55 L); size as large as form allows

// ---- bottom wire pass (single sealed bundle exit, grommet) ----
wire_pass_d = 8;           // bore for the 4-wire bundle + grommet
wire_pass_z = wall + 12;   // hole center depth from the front face

// ---- wall mount (keyhole slots in the rear plate) ----
keyhole_spacing = 100;
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;

// ---- rear-plate perimeter gasket groove (seals the lid) ----
lid_gasket_inset = wall + 3;   // groove centerline inset from the outer edge
lid_gasket_w     = 2.0;        // groove width
lid_gasket_depth = 1.0;        // groove depth into the lid inner face

// ---- corner screws (M3) fastening the rear plate ----
boss_od     = 7;
screw_pilot = 2.6;             // self-tap pilot in the front bosses
screw_clear = 3.4;             // clearance hole in the rear plate
boss_inset  = radius + 3;      // corner inset for the 4 screw bosses

// ---- optional internal brace (insurance only; off by default) ----
brace   = false;
brace_w = 4;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()   = spk_od*2 + spk_gap + side_margin*2;   // 146
function outer_h()   = spk_od + 2*vert_margin;               // 79
function outer_d()   = front_depth + wall;                   // front shell + flat lid
function spk_cx()    = spk_od/2 + spk_gap/2;                 // 36.5
function spk_cy()    = 0;                                     // drivers vertically centered
function gross_vol() = (outer_w()-2*wall) * (outer_h()-2*wall) * cavity_depth;
function net_vol()   = gross_vol() - 2*driver_disp;
