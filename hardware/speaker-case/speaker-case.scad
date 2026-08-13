// ===== Speaker case — render entry point =====
// Render a single part:  openscad -D 'part="body"' -o out.stl speaker-case.scad
// Parts: "body" | "rear" | "port" | "all" (assembled preview)
include <modules/params.scad>
include <modules/lib.scad>
include <modules/body.scad>
include <modules/rear_plate.scad>
include <modules/port.scad>

part = "all";   // override on the CLI: -D 'part="body"'

if (part == "body")      body();
else if (part == "rear") rear_plate();
else if (part == "port") port_tube();
else {  // assembled preview
    body();
    color("gray") translate([0, 0, front_depth]) rear_plate();
    // port tube seated in the +x side wall, pointing outward
    color("tan")
        translate([outer_w()/2, spk_zone_cy(), port_cz]) rotate([0, -90, 0]) port_tube();
}
