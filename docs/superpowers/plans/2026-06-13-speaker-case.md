# Speaker Case Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parametric OpenSCAD enclosure — `hardware/speaker-case/` — for two AIYIMA 2"/53 mm full-range drivers: a single sealed, mono, wall-mounted box optimized to load the drivers cleanly and seal well.

**Architecture:** Mirror the existing `hardware/terrace-case/` structure exactly (params/lib/modules split, `build.sh`/`test.sh`, `tests/asserts.scad`). A `body.scad` produces the open-back sealed shell with a flat front baffle carrying both drivers; `rear_plate.scad` is a flat gasketed lid with keyhole wall-mount slots; `grille.scad` is an optional snap-on cover. The acoustic "tests" are geometric `assert()`s (net volume floor, seal integrity, screw geometry) rendered under `--hardwarnings`, plus STL render smoke-checks.

**Tech Stack:** OpenSCAD (2021.01), bash harness. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-13-speaker-case-design.md`

---

## File Structure

```
hardware/speaker-case/
  speaker-case.scad        # part dispatcher: "body" | "rear" | "grille" | "all"
  build.sh                 # render STLs (adapted from terrace build.sh)
  test.sh                  # asserts + render smoke (adapted from terrace test.sh)
  modules/
    params.scad            # all dimensions + derived functions (no geometry)
    lib.scad               # shared helpers (copied from terrace lib.scad)
    body.scad              # sealed shell, flat baffle, cutouts, gasket grooves,
                           # driver screw bosses, bottom wire pass, corner bosses
    rear_plate.scad        # flat gasketed lid, keyhole slots, screw clearance holes
    grille.scad            # OPTIONAL snap-on perforated cover, one per driver
  tests/
    asserts.scad           # geometry/acoustic asserts + helper smoke renders
```

---

## Task 1: Scaffold directory, params, lib, and green harness

**Files:**
- Create: `hardware/speaker-case/modules/params.scad`
- Create: `hardware/speaker-case/modules/lib.scad`
- Create: `hardware/speaker-case/modules/body.scad` (stub)
- Create: `hardware/speaker-case/modules/rear_plate.scad` (stub)
- Create: `hardware/speaker-case/modules/grille.scad` (stub)
- Create: `hardware/speaker-case/speaker-case.scad`
- Create: `hardware/speaker-case/tests/asserts.scad`
- Create: `hardware/speaker-case/build.sh`
- Create: `hardware/speaker-case/test.sh`

- [ ] **Step 1: Write `modules/params.scad`** (data only — all dimensions and derived functions)

```scad
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
function spk_cx()    = spk_od/2 + spk_gap/2;                  // 36.5
function spk_cy()    = 0;                                     // drivers vertically centered
function gross_vol() = (outer_w()-2*wall) * (outer_h()-2*wall) * cavity_depth;
function net_vol()   = gross_vol() - 2*driver_disp;
```

- [ ] **Step 2: Write `modules/lib.scad`** (copy helpers from terrace; these are reused verbatim)

```scad
// ===== shared helpers (no top-level geometry) =====

// 2D rounded rectangle centered at origin
module rounded_rect(w, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - r), sy*(h/2 - r)]) circle(r);
}

// hollow shell body: outer rounded box, open at the +z (back) face,
// leaving a `wall`-thick front face at z in [0, wall].
module shell_body(depth) {
    difference() {
        linear_extrude(depth) rounded_rect(outer_w(), outer_h(), radius);
        translate([0, 0, wall])
            linear_extrude(depth)
                rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
    }
}

// 2D concentric-ring perforation field within diameter `cut_d`
module grille(cut_d) {
    grille_hole_d = 3;
    grille_ring_step = 6;
    for (r = [0 : grille_ring_step : cut_d/2 - grille_hole_d]) {
        if (r == 0) circle(d = grille_hole_d);
        else {
            n = max(1, floor(2*PI*r / (grille_hole_d*1.8)));
            for (i = [0 : n-1]) rotate(i*360/n) translate([r, 0]) circle(d = grille_hole_d);
        }
    }
}

// 2D keyhole: head circle on top, slot dropping down by `drop`
module keyhole(slot_w, head_d, drop) {
    union() {
        circle(d = head_d);
        translate([0, -drop/2]) square([slot_w, drop], center = true);
        translate([0, -drop]) circle(d = slot_w);
    }
}

// screw boss with self-tap pilot, base at z=0
module screw_boss(h, od, pilot) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1]) cylinder(h = h + 0.2, d = pilot);
    }
}
```

- [ ] **Step 3: Write the three module stubs** so the dispatcher renders before geometry exists

`modules/body.scad`:
```scad
// ===== sealed shell body (no top-level geometry) =====
module body() { cube(1); }   // STUB — replaced in Task 2
```

`modules/rear_plate.scad`:
```scad
// ===== rear lid (no top-level geometry) =====
module rear_plate() { cube(1); }   // STUB — replaced in Task 3
```

`modules/grille.scad`:
```scad
// ===== optional snap-on grille (no top-level geometry) =====
module grille_cover() { cube(1); }   // STUB — replaced in Task 4
```

- [ ] **Step 4: Write `speaker-case.scad`** (part dispatcher)

```scad
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
```

- [ ] **Step 5: Write `tests/asserts.scad`** (includes + helper smoke only, for now)

```scad
include <../modules/params.scad>
include <../modules/lib.scad>

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
```

- [ ] **Step 6: Write `build.sh`** (adapted from terrace; parts = body/rear/grille)

```bash
#!/usr/bin/env bash
set -euo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
for part in body rear grille; do
    echo "rendering $part ..."
    "$OPENSCAD" -D "part=\"$part\"" -o "stl/$part.stl" speaker-case.scad
done
echo "done -> stl/"
```

- [ ] **Step 7: Write `test.sh`** (adapted from terrace; parts = body/rear/grille)

```bash
#!/usr/bin/env bash
set -uo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
fail=0

echo "== parameter asserts =="
"$OPENSCAD" --hardwarnings -o /tmp/sc_asserts.stl tests/asserts.scad >/dev/null 2>&1 \
    && echo "OK asserts" || { echo "FAIL asserts"; fail=1; }

for part in body rear grille; do
    if "$OPENSCAD" --hardwarnings -D "part=\"$part\"" -o "stl/$part.stl" speaker-case.scad 2>/tmp/sc_err; then
        sz=$(wc -c < "stl/$part.stl")
        if [ "$sz" -lt 1000 ]; then echo "FAIL $part: STL too small ($sz B)"; fail=1
        else echo "OK $part ($sz B)"; fi
    else
        echo "FAIL $part render:"; cat /tmp/sc_err; fail=1
    fi
done
exit $fail
```

- [ ] **Step 8: Make scripts executable and run the harness**

Run:
```bash
chmod +x hardware/speaker-case/build.sh hardware/speaker-case/test.sh
hardware/speaker-case/test.sh
```
Expected: `OK asserts`, and `FAIL` lines for `body`/`rear`/`grille` STL-too-small (stubs render a 1 mm cube < 1000 B). That is the expected red state — stubs exist, geometry doesn't.

- [ ] **Step 9: Commit**

```bash
git add hardware/speaker-case
git commit -m "feat(speaker-case): scaffold params, lib, harness, stubs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Sealed body — shell, baffle cutouts, gasket grooves, driver bosses, wire pass, corner bosses

**Files:**
- Modify: `hardware/speaker-case/tests/asserts.scad` (add body asserts)
- Modify: `hardware/speaker-case/modules/body.scad` (replace stub with full geometry)

- [ ] **Step 1: Add the body asserts to `tests/asserts.scad`** (insert ABOVE the `// helper render smoke` line)

```scad
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
```

- [ ] **Step 2: Run the asserts — verify they FAIL**

Run: `hardware/speaker-case/test.sh`
Expected: `FAIL asserts` — `spk_screw_r` is fine, but the asserts reference only params/functions that already exist, so they should actually PASS. **If `OK asserts`, that is correct here** (these asserts validate params defined in Task 1). The body PART still FAILs (stub). Confirm body still reports STL-too-small.

> Note: in this CAD harness, param-relationship asserts pass as soon as the params are consistent; the red→green signal for geometry is the *part render* smoke-check (STL size). Treat the body part FAIL as the failing test for this task.

- [ ] **Step 3: Replace `modules/body.scad` with the full sealed body**

```scad
// ===== sealed shell body (no top-level geometry) =====
// Open-back box with a flat front baffle carrying both drivers. Drivers drop in
// from the back against the baffle inner face, seal on a foam gasket ring, and
// screw to bosses on the 43 mm square. One sealed wire pass exits the bottom.

// raised locating rings on the inner front face (each driver centers in one)
module speaker_seats() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            difference() {
                cylinder(h = spk_seat_depth, d = spk_od + 2*seat_wall);
                translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
            }
}

// open cone cutouts through the front wall (the cone radiates through these)
module cone_cuts() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy()]) circle(d = spk_cut);
}

// annular groove in the baffle inner face under each driver flange (foam ring)
module gasket_grooves() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall - gasket_depth])
            difference() {
                cylinder(h = gasket_depth + 0.1, d = gasket_od);
                translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
            }
}

// 4 bosses per driver on the 43 mm square; the flange screws into them from the back
module speaker_screw_bosses() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            for (cx = [-1, 1], cy = [-1, 1])
                translate([cx*spk_screw_square/2, cy*spk_screw_square/2, 0])
                    screw_boss(spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// 4 corner M3 bosses (front side), full internal depth — the rear lid screws into these
module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

// single sealed wire pass: a bounded hole through the bottom (-y) perimeter wall,
// centered on X at depth wire_pass_z, so the cable leaves out the bottom while the
// rest of the bottom wall stays solid (does NOT run to the back edge).
module wire_pass_cut() {
    translate([0, -outer_h()/2, wire_pass_z])
        rotate([90, 0, 0])
            cylinder(h = wall*3, d = wire_pass_d, center = true);
}

// optional internal brace: a thin rib spanning top<->bottom behind the divider line
module brace_rib() {
    if (brace)
        translate([0, 0, wall])
            linear_extrude(cavity_depth)
                translate([-brace_w/2, -(outer_h()/2 - wall)])
                    square([brace_w, outer_h() - 2*wall]);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
            speaker_screw_bosses();
            corner_bosses();
            brace_rib();
        }
        cone_cuts();
        gasket_grooves();
        wire_pass_cut();
    }
}
```

- [ ] **Step 4: Run the harness — verify body renders**

Run: `hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body (...B)` (well over 1000 B). `rear`/`grille` still FAIL (stubs). That is correct.

- [ ] **Step 5: Commit**

```bash
git add hardware/speaker-case/modules/body.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): sealed body — baffle cutouts, gasket grooves, bosses, wire pass

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Rear plate — flat gasketed lid with keyhole wall mount

**Files:**
- Modify: `hardware/speaker-case/tests/asserts.scad` (add rear-plate asserts)
- Modify: `hardware/speaker-case/modules/rear_plate.scad` (replace stub)

- [ ] **Step 1: Add rear-plate asserts to `tests/asserts.scad`** (insert ABOVE the `// helper render smoke` line)

```scad
// ---- rear plate: gasket groove sits inside the perimeter, doesn't pierce the lid ----
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(lid_gasket_inset + lid_gasket_w/2 < radius + wall || lid_gasket_inset > radius,
       "lid gasket groove should sit on a flat perimeter band");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0,
       "lid gasket groove inset too large for the plate");

// ---- rear plate: keyholes fit within the plate width and clear the corner bosses ----
assert(keyhole_spacing/2 + keyhole_head_d/2 <= outer_w()/2 - wall, "keyholes run off the plate width");
assert(keyhole_spacing/2 - keyhole_head_d/2 > 0, "keyholes overlap at center — widen keyhole_spacing");
```

- [ ] **Step 2: Run the asserts — verify state**

Run: `hardware/speaker-case/test.sh`
Expected: `OK asserts` (params consistent). `rear` PART still FAILs (stub). The rear part FAIL is the failing test for this task.

- [ ] **Step 3: Replace `modules/rear_plate.scad` with the full lid**

```scad
// ===== rear lid (no top-level geometry) =====
// A FLAT lid `wall` thick. The 4 corner M3 bosses live on the BODY at full depth;
// screws drop through these clearance holes from the back and self-tap into them.
// A perimeter gasket groove on the inner face seals the lid to the body rim.
// Two keyhole slots hang the box on two wall screws.
module rear_plate() {
    difference() {
        linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
        // perimeter gasket groove on the inner (-z assembled) face, cut from z=0 up
        translate([0, 0, -0.1])
            linear_extrude(lid_gasket_depth + 0.1)
                difference() {
                    rounded_rect(outer_w() - 2*lid_gasket_inset + lid_gasket_w,
                                 outer_h() - 2*lid_gasket_inset + lid_gasket_w,
                                 max(0.5, radius - lid_gasket_inset));
                    rounded_rect(outer_w() - 2*lid_gasket_inset - lid_gasket_w,
                                 outer_h() - 2*lid_gasket_inset - lid_gasket_w,
                                 max(0.5, radius - lid_gasket_inset - lid_gasket_w));
                }
        // screw clearance holes (rear -> into the body corner bosses)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = wall + 0.2, d = screw_clear);
        // keyhole wall-mount slots
        for (sx = [-1, 1])
            translate([sx*keyhole_spacing/2, 0, -0.1])
                linear_extrude(wall + 0.2) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
    }
}
```

- [ ] **Step 4: Run the harness — verify rear renders**

Run: `hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`, `OK rear`. `grille` still FAIL (stub).

- [ ] **Step 5: Commit**

```bash
git add hardware/speaker-case/modules/rear_plate.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): gasketed rear lid with keyhole wall mount

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Optional snap-on grille cover

**Files:**
- Modify: `hardware/speaker-case/tests/asserts.scad` (add grille assert)
- Modify: `hardware/speaker-case/modules/grille.scad` (replace stub)

- [ ] **Step 1: Add grille assert to `tests/asserts.scad`** (insert ABOVE the `// helper render smoke` line)

```scad
// ---- grille: perforation field stays within the driver frame ----
assert(spk_cut <= spk_od, "grille field must stay within the driver frame");
```

- [ ] **Step 2: Run the asserts**

Run: `hardware/speaker-case/test.sh`
Expected: `OK asserts`; `grille` PART still FAILs (stub) — the failing test for this task.

- [ ] **Step 3: Replace `modules/grille.scad` with a snap-on cover**

```scad
// ===== optional snap-on grille (no top-level geometry) =====
// A perforated disc per driver with a short skirt that snaps over the driver
// seat ring. Purely protective; never touches the sealed volume.
grille_face_t  = 1.6;          // perforated face thickness
grille_skirt_h = 5;            // skirt depth gripping the seat ring
grille_skirt_t = 1.6;          // skirt wall

module grille_cover() {
    for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy(), 0]) {
        // perforated face
        difference() {
            cylinder(h = grille_face_t, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
            translate([0, 0, -0.1]) linear_extrude(grille_face_t + 0.2) grille(spk_cut);
        }
        // grip skirt (snaps over the seat ring OD with clearance)
        translate([0, 0, -grille_skirt_h])
            difference() {
                cylinder(h = grille_skirt_h, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
                translate([0, 0, -0.1])
                    cylinder(h = grille_skirt_h + 0.2, d = spk_od + 2*seat_wall + 2*clr);
            }
    }
}
```

- [ ] **Step 4: Run the harness — full green**

Run: `hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`, `OK rear`, `OK grille`. Exit 0.

- [ ] **Step 5: Commit**

```bash
git add hardware/speaker-case/modules/grille.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): optional snap-on protective grille

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Assembled preview, README, and EQ documentation

**Files:**
- Create: `hardware/speaker-case/README.md`
- Verify: `hardware/speaker-case/speaker-case.scad` assembled preview renders

- [ ] **Step 1: Render the assembled preview to confirm parts fit**

Run:
```bash
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
"$OPENSCAD" --hardwarnings -D 'part="all"' -o /tmp/sc_all.stl hardware/speaker-case/speaker-case.scad && echo "OK all"
```
Expected: `OK all`, no warnings.

- [ ] **Step 2: Write `hardware/speaker-case/README.md`**

````markdown
# Speaker case — sealed twin-driver wall enclosure

Sealed, mono, wall-mounted enclosure for **two AIYIMA 2"/53 mm full-range drivers
(4 Ω)**, driven by the terrace device's 2× MAX98357A amps. Design rationale and
measured driver T/S: `docs/superpowers/specs/2026-06-13-speaker-case-design.md`.

## Parts
- `body` — sealed shell + flat baffle (both drivers), bottom wire pass
- `rear` — flat gasketed lid + keyhole wall mount
- `grille` — optional snap-on protective covers

## Build
```bash
./build.sh          # renders stl/body.stl, stl/rear.stl, stl/grille.stl
./test.sh           # asserts + render smoke checks
```

## Print & assembly
- Orient **back-down**: flat baffle, no overhangs, no supports.
- Print **airtight**: ≥4 perimeters / high wall count, then a thin interior seal
  coat (epoxy or shellac wash) on the shell before assembly. FDM PLA leaks through
  layer lines, not just joints — sealing is the whole game for a sealed box.
- Foam gasket ring under each driver flange (groove provided); M2 self-tap the
  flanges to the 4 bosses (43 mm square) per driver.
- Foam strip in the rear-plate perimeter groove; M3 self-tap the lid to the 4
  corner bosses.
- Single wire bundle (4 conductors, 2 per driver) exits the bottom through a
  grommet — seal with a dab of silicone. Feed L → one driver, R → the other.
- Loosely add polyfill; do not pack.

## Bass / EQ — apply server-side in Music Assistant
This driver's free-air resonance is **Fs ≈ 145 Hz**: there is no usable output
below ~120 Hz from any enclosure, and a sealed box trims rather than extends the
low end. The bass/warmth lever is **Music Assistant's per-player Audio DSP**
(the MAX98357A and the ESPHome pipeline cannot filter). On
`media_player.intercom_s3_player`, start from — then tune by ear:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | 110 Hz | 12 dB/oct (Q≈0.7) | — |
| Warmth | Low shelf | 160 Hz | — | +3 to +4 dB |
| Tame breakup (optional) | Peaking notch | 15 kHz | Q≈2 | −3 to −5 dB |

MA DSP only shapes audio routed through Music Assistant (music). TTS / wake-word
announcements bypass it — fine, those are speech.

## Confirm before printing
- Driver cutout (46 mm), screw square (43 mm), seated depth (28 mm) vs your units.
- Net sealed volume floor is enforced by `tests/asserts.scad` (`vol_target`).
````

- [ ] **Step 3: Final full test run**

Run: `hardware/speaker-case/test.sh && echo ALL-GREEN`
Expected: `OK asserts`, `OK body`, `OK rear`, `OK grille`, `ALL-GREEN`.

- [ ] **Step 4: Commit**

```bash
git add hardware/speaker-case/README.md
git commit -m "docs(speaker-case): build/print/assembly guide + Music Assistant EQ settings

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review notes (for the implementer)

- **Spec coverage:** sealed single mono chamber (Task 2 body, no divider) ✓; ~0.6 L net + floor assert (`vol_target`, Task 2) ✓; flat baffle, no toe-out, rounded edges (`radius`, body) ✓; airtight-print + seal-coat + gaskets + single wire pass (README + body + rear) ✓; wall mount keyholes + bottom wire exit (rear + body) ✓; optional brace (`brace` param, Task 2) ✓; structure mirrors terrace (Task 1) ✓; EQ moved server-side to Music Assistant DSP (README, Task 5) ✓.
- **Acoustic asserts encode the spec's intent:** `net_vol() >= vol_target` (size for low Qtc), `cavity_depth >= spk_depth` (clearance), seal/bounded-hole checks (no leaks).
- If `openscad` is not on PATH, set `OPENSCAD=/path/to/OpenSCAD` before running the scripts (same convention as terrace-case).
