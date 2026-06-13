// ===== Speaker case — render entry point =====
// Render a single part:  openscad -D 'part="body"' -o out.stl speaker-case.scad
// Parts: "body" | "rear" | "button" | "grille" | "all" (assembled preview)
include <modules/params.scad>
include <modules/lib.scad>
include <modules/body.scad>
include <modules/rear_plate.scad>
include <modules/button_cap.scad>
include <modules/grille.scad>

part = "all";   // override on the CLI: -D 'part="body"'

if (part == "body")        body();
else if (part == "rear")   rear_plate();
else if (part == "button") button_cap();
else if (part == "grille") grille_cover();
else {  // assembled preview
    body();
    color("red")  translate([cradle_cx(), board_cy(), -3]) button_cap();
    color("gray") translate([0, 0, front_depth]) rear_plate();
}
