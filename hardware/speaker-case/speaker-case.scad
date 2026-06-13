// ===== Speaker case — render entry point =====
// Render a single part:  openscad -D 'part="body"' -o out.stl speaker-case.scad
// Parts: "body" | "rear" | "grille" | "all" (assembled preview)
include <modules/params.scad>
include <modules/lib.scad>
include <modules/body.scad>
include <modules/rear_plate.scad>
include <modules/grille.scad>

part = "all";   // override on the CLI: -D 'part="body"'

if (part == "body")        body();
else if (part == "rear")   rear_plate();
else if (part == "grille") grille_cover();
else {  // assembled preview
    body();
    color("gray") translate([0, 0, front_depth]) rear_plate();
}
