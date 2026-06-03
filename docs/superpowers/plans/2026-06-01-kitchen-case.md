# Kitchen Atom Echo Enclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parametric OpenSCAD wall-mount enclosure for the kitchen intercom — classic M5Stack Atom Echo + one MAX98357A + one 2" driver — as a fork of `hardware/terrace-case` reduced to a single speaker and single amp.

**Architecture:** Two-part clamshell (front shell + rear wall plate) joined by 4× M3 screws, plus a captive button plunger. One centered speaker recess ring with grille/gasket/bolt-bosses; an Atom Echo cradle (top-face-forward) with one amp board mounted to its right; a button well + mic perforation over the module's top face. Same OpenSCAD module structure and test harness (parameter asserts + render smoke) as the terrace case.

**Tech Stack:** OpenSCAD (2021.01+), parametric `.scad` modules, bash build/test scripts driving the OpenSCAD CLI.

---

## File Structure

New directory `hardware/kitchen-case/`, mirroring `hardware/terrace-case/`:

```
hardware/kitchen-case/
├── kitchen-case.scad        # render entry point + part selector
├── modules/
│   ├── params.scad          # all parameters + derived dimension functions (no geometry)
│   ├── lib.scad             # shared helpers: rounded_rect, shell_body, grille, keyhole, screw_boss
│   ├── front_shell.scad     # front shell + sub-modules (speaker seat, cradle, amp mount, button well, mic perf, coupon)
│   ├── rear_plate.scad      # rear wall plate: keyholes, USB-C notch, mating bosses
│   └── button_cap.scad      # captive plunger
├── tests/
│   └── asserts.scad         # parameter relationship asserts + helper render smoke
├── build.sh                 # render front/rear/button to stl/
├── test.sh                  # asserts + clean-render check per part
├── .gitignore               # ignores stl/
└── README.md                # parameters, print settings, BOM, assembly
```

Each file has one responsibility: `params.scad` owns all dimensions and derived geometry functions; `lib.scad` owns reusable primitives; the three shell modules own their respective printed parts; the scripts own build/verify.

**The whole diff from terrace-case:** single centered driver (was two side-by-side), single amp to the right of the module (was two flanking), Atom Echo cradle naming, narrower derived width, narrower keyhole spacing. Everything else is carried over verbatim.

---

## Task 1: Scaffold — parameters, helpers, tests, scripts, stub modules

Create every non-geometry file plus **stub** shell modules, so the test harness runs and fails on the (empty) renders. This is the red state: asserts pass, part renders are too small.

**Files:**
- Create: `hardware/kitchen-case/modules/params.scad`
- Create: `hardware/kitchen-case/modules/lib.scad`
- Create: `hardware/kitchen-case/tests/asserts.scad`
- Create: `hardware/kitchen-case/kitchen-case.scad`
- Create: `hardware/kitchen-case/build.sh`
- Create: `hardware/kitchen-case/test.sh`
- Create: `hardware/kitchen-case/.gitignore`
- Create (stubs): `hardware/kitchen-case/modules/front_shell.scad`, `modules/rear_plate.scad`, `modules/button_cap.scad`

- [ ] **Step 1: Write `modules/params.scad`**

```openscad
// ===== Kitchen Atom Echo enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
front_depth = 38;          // inner depth of the front shell — clears the 35 mm-deep driver
rear_depth  = 12;          // depth of the rear plate body

// ---- speaker (one 2" full-range, centered) ----
spk_od         = 53;       // driver face diameter (locating ring ID) — 2" driver
spk_cut        = 44;       // grille perforation field diameter
spk_seat_depth = 4;        // height of the inner locating ring
spk_depth      = 35;       // driver depth front-to-back (sets front_depth clearance)

// ---- driver gasket groove (foam ring seals the flange to the baffle) ----
gasket_od    = spk_od - 1;   // groove outer diameter (just inside the locating ring)
gasket_id    = spk_cut + 1;  // groove inner diameter (just outside the grille field)
gasket_depth = 1.0;          // groove depth cut into the baffle inner face

// ---- speaker frame-hole screw bosses (fasten the driver flange) ----
spk_screw_n     = 4;       // mounting holes on the driver flange
spk_bolt_circle = 56;      // bolt-circle diameter; MUST clear the driver OD
spk_screw_pilot = 1.6;     // M2 self-tap pilot
spk_boss_od     = 5;       // mounting boss outer diameter
spk_boss_h      = spk_seat_depth + 1;  // boss height on the inner baffle
spk_screw_a0    = 45;      // start angle (deg)

// ---- margins / board zone ----
side_margin   = 6;
top_margin    = 7;
board_zone_h  = 30;
bottom_margin = 8;

// ---- grille ----
grille_hole_d    = 3;
grille_ring_step = 6;      // radial spacing between hole rings

// ---- Atom Echo module (24x24 footprint, top-face forward) ----
mod_w   = 24;              // module footprint (square)            [confirm vs hardware]
mod_d   = 17;              // module depth front-to-back in the case [confirm vs hardware]
mod_clr = clr;
mod_usb_w = 10;            // USB-C cutout width                   [confirm position vs hardware]
mod_usb_h = 4;             // USB-C cutout height
cradle_wall = 1.6;

// ---- button ----
btn_well_d = 12.5;         // well bore (cap skirt rides in this)
btn_cap_d  = 12;           // cap face diameter (slightly proud)
btn_travel = 2;
btn_nub_d  = 4;            // nub that contacts the module switch

// ---- microphone (perforation under the button, over the module's mic) ----
mic_below_btn = 8;         // cluster center, this far below the button center
mic_hole_d    = 1.5;       // perforation hole diameter
mic_ring_r    = 2.6;       // radius of the surrounding ring of holes
mic_ring_n    = 6;         // holes in the ring (plus one in the center)

// ---- amp board (one MAX98357A breakout, right of the module) ----
amp_w = 18;
amp_l = 16;
amp_gap = 4;               // gap between the cradle wall and the amp board
amp_standoff_h = 3;
amp_standoff_od = 4.5;     // post OD (wide enough to take a pilot)
amp_screw_pilot = 1.6;     // M2 self-tap pilot in each amp standoff

// ---- wall mount ----
keyhole_spacing = 60;      // narrower than terrace (single-driver footprint)
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;

// ---- screws (M3) ----
boss_od     = 7;
screw_pilot = 2.6;         // self-tap pilot in the front bosses
screw_clear = 3.4;         // clearance hole in the rear plate
boss_inset  = radius + 2;  // corner inset for the 4 screw bosses

// ---- derived dimensions (functions so tests can assert them) ----
function amp_cx()      = (mod_w + 2*mod_clr)/2 + cradle_wall + amp_gap + amp_w/2; // amp center x (right of module)
function board_reach() = amp_cx() + amp_w/2;                  // right-most board extent from center
function outer_w()     = max(spk_od, 2*board_reach()) + side_margin*2;
function outer_h()     = top_margin + spk_od + board_zone_h + bottom_margin;
function outer_d()     = front_depth + rear_depth;
function spk_cx()      = 0;                                   // single driver, centered
function spk_cy()      = outer_h()/2 - top_margin - spk_od/2;
function board_cy()    = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()   = 0;                                   // module centered; amp to the right
function mic_x()       = cradle_cx();                         // centered on the module / button
function mic_y()       = board_cy() - mic_below_btn;          // just below the button
```

- [ ] **Step 2: Write `modules/lib.scad`** (verbatim copy of the terrace helpers)

```openscad
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

- [ ] **Step 3: Write `tests/asserts.scad`**

```openscad
include <../modules/params.scad>
include <../modules/lib.scad>

// Relationship checks — robust to tuning spk_od / depths / amp position in params.scad.

// One driver, centered on X.
assert(spk_cx() == 0, "single driver must be centered on X");

// Front shell must be deep enough to clear the driver front-to-back.
assert(front_depth >= spk_depth, "front_depth must clear the driver depth");

// Grille opening stays inside the driver; bolt circle clears the driver OD.
assert(spk_cut < spk_od, "grille field must be smaller than the driver");
assert(spk_bolt_circle > spk_od, "bolt circle must clear the driver OD");

// Gasket groove sits on the flange land and doesn't cut through the baffle.
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");

// The single amp board, to the right of the module, stays inside the shell wall.
assert(amp_cx() + amp_w/2 <= outer_w()/2 - wall, "amp board must fit inside the shell");

// Board row (cradle + amp) sits in the lower strip, below center.
assert(board_cy() < 0, "board row should be below center");

// Mic perforation lands below the button, still within the module footprint.
assert(mic_y() < board_cy(), "mic cluster should be below the button");
assert(board_cy() - mic_y() <= mod_w/2, "mic cluster should stay over the module");

// Keyhole slots fit within the (narrower) rear plate.
assert(keyhole_spacing/2 + keyhole_head_d/2 <= outer_w()/2 - wall, "keyholes must fit within the plate");

// helper render smoke — these must produce geometry without warnings
linear_extrude(1) rounded_rect(20, 10, 2);
linear_extrude(1) grille(spk_cut);
linear_extrude(1) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);

// sentinel geometry so the render is non-empty under --hardwarnings
cube(1);
```

- [ ] **Step 4: Write `kitchen-case.scad`** (render entry point)

```openscad
// ===== Kitchen Atom Echo enclosure — render entry point =====
// Render a single part:  openscad -D 'part="front"' -o out.stl kitchen-case.scad
// Parts: "front" | "rear" | "button" | "coupon" | "all" (assembled preview)
// NOTE: use a normal variable `part` (overridable by -D), NOT a special
// $-variable — OpenSCAD's -D does not reliably set $-prefixed variables.
include <modules/params.scad>
include <modules/lib.scad>
include <modules/front_shell.scad>
include <modules/rear_plate.scad>
include <modules/button_cap.scad>

part = "all";   // override on the CLI: -D 'part="front"'

if (part == "front")       front_shell();
else if (part == "rear")   rear_plate();
else if (part == "button") button_cap();
else if (part == "coupon") coupon_render();
else {  // assembled preview
    front_shell();
    color("gray")  translate([0, 0, front_depth]) rear_plate();
    color("red")   translate([cradle_cx(), board_cy(), -3]) button_cap();
}
```

- [ ] **Step 5: Write stub `modules/front_shell.scad`** (empty modules so the entry resolves but renders empty)

```openscad
// ===== front shell — STUB (filled in Task 2) =====
module front_shell() { }
module coupon_render() { }
```

- [ ] **Step 6: Write stub `modules/rear_plate.scad`**

```openscad
// ===== rear plate — STUB (filled in Task 3) =====
module rear_plate() { }
```

- [ ] **Step 7: Write stub `modules/button_cap.scad`**

```openscad
// ===== button cap — STUB (filled in Task 4) =====
module button_cap() { }
```

- [ ] **Step 8: Write `build.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
for part in front rear button; do
    echo "rendering $part ..."
    "$OPENSCAD" -D "part=\"$part\"" -o "stl/$part.stl" kitchen-case.scad
done
echo "done -> stl/"
```

- [ ] **Step 9: Write `test.sh`**

```bash
#!/usr/bin/env bash
set -uo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
fail=0

echo "== parameter asserts =="
"$OPENSCAD" --hardwarnings -o /tmp/kc_asserts.stl tests/asserts.scad >/dev/null 2>&1 \
    && echo "OK asserts" || { echo "FAIL asserts"; fail=1; }

for part in front rear button coupon; do
    if "$OPENSCAD" --hardwarnings -D "part=\"$part\"" -o "stl/$part.stl" kitchen-case.scad 2>/tmp/kc_err; then
        sz=$(wc -c < "stl/$part.stl")
        if [ "$sz" -lt 1000 ]; then echo "FAIL $part: STL too small ($sz B)"; fail=1
        else echo "OK $part ($sz B)"; fi
    else
        echo "FAIL $part render:"; cat /tmp/kc_err; fail=1
    fi
done
exit $fail
```

- [ ] **Step 10: Write `.gitignore`**

```
stl/
```

- [ ] **Step 11: Make scripts executable and run the test (expect RED on parts)**

Run:
```bash
chmod +x hardware/kitchen-case/build.sh hardware/kitchen-case/test.sh
hardware/kitchen-case/test.sh; echo "exit=$?"
```
Expected: `OK asserts`, then `FAIL front: STL too small`, `FAIL rear: STL too small`, `FAIL button: STL too small`, `FAIL coupon: STL too small`, and `exit=1`. (Asserts pass; the stub modules render empty, so every part is below the 1000 B floor. This is the intended failing state.)

- [ ] **Step 12: Commit**

```bash
git add hardware/kitchen-case
git commit -m "scaffold(kitchen-case): params, helpers, tests, scripts, stub modules"
```

---

## Task 2: Front shell geometry (+ coupon)

Replace the stub with the real front shell: one centered driver seat/grille/gasket/bolt-bosses, the Atom Echo cradle, one amp mount to its right, the button well, the mic perforation, corner bosses, and the fit-test coupon.

**Files:**
- Modify: `hardware/kitchen-case/modules/front_shell.scad` (replace stub with full content)

- [ ] **Step 1: Run the test to confirm `front` and `coupon` are currently RED**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK asserts`, `FAIL front: STL too small`, `FAIL coupon: STL too small` (rear/button also still FAIL), `exit=1`.

- [ ] **Step 2: Write the full `modules/front_shell.scad`**

```openscad
// ===== front shell + sub-modules (no top-level geometry) =====

// raised locating ring on the inside of the front wall (driver drops in)
module speaker_seats() {
    translate([spk_cx(), spk_cy(), wall])
        difference() {
            cylinder(h = spk_seat_depth, d = spk_od + 2*cradle_wall);
            translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
        }
}

// perforations through the front wall over the speaker
module grille_cut() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        translate([spk_cx(), spk_cy()]) grille(spk_cut);
}

// annular groove in the baffle inner face under the driver flange — seats a
// foam/EVA gasket ring so the flange seals the front wave from the back wave.
module gasket_grooves() {
    translate([spk_cx(), spk_cy(), wall - gasket_depth])
        difference() {
            cylinder(h = gasket_depth + 0.1, d = gasket_od);
            translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
        }
}

// 3-wall pocket holding the Atom Echo top-face-forward; open at the back (+z),
// USB-C slot toward the bottom edge, wire window toward the amp (+x).
module atom_cradle() {
    cw = mod_w + 2*mod_clr;                 // inner pocket size
    translate([cradle_cx(), board_cy(), wall]) difference() {
        translate([0, 0, mod_d/2]) cube([cw + 2*cradle_wall, cw + 2*cradle_wall, mod_d], center = true);
        // pocket, open at back
        translate([0, 0, mod_d/2 + cradle_wall]) cube([cw, cw, mod_d], center = true);
        // USB-C slot through the bottom wall (toward -y)
        translate([0, -(cw/2 + cradle_wall), mod_usb_h/2 + 1])
            cube([mod_usb_w, cradle_wall*3, mod_usb_h], center = true);
        // wire window toward the amp on the +x side
        translate([(cw/2 + cradle_wall), 0, mod_d*0.55])
            cube([cradle_wall*3, mod_w*0.6, mod_d*0.6], center = true);
    }
}

// well bored through the front wall AND the cradle floor behind it, so the
// plunger nub can reach the module's switch. A retaining shoulder the cap's
// lip catches behind sits at the front-wall inner face.
module button_well() {
    translate([cradle_cx(), board_cy(), -0.1]) {
        cylinder(h = wall + cradle_wall + 0.2, d = btn_well_d);          // bore through wall + cradle floor
        translate([0, 0, wall]) cylinder(h = 1.2, d = btn_well_d + 1.6); // shoulder pocket
    }
}

// mic perforation: a small cluster of holes through the front wall AND the
// cradle floor, so the holes open into the pocket right at the module's mic.
module mic_perf() {
    translate([mic_x(), mic_y(), -0.1]) linear_extrude(wall + cradle_wall + 0.2) {
        circle(d = mic_hole_d);
        for (i = [0 : mic_ring_n - 1])
            rotate(i*360/mic_ring_n) translate([mic_ring_r, 0]) circle(d = mic_hole_d);
    }
}

// frame-hole screw bosses around the driver: the flange screws down into these
// from inside the case (bolt circle clears the driver OD).
module speaker_screw_bosses() {
    translate([spk_cx(), spk_cy(), wall])
        for (i = [0 : spk_screw_n - 1])
            rotate(spk_screw_a0 + i*360/spk_screw_n)
                translate([spk_bolt_circle/2, 0, 0])
                    screw_boss(spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// one amp board to the right of the centered module, on standoff posts with M2
// self-tap pilots so the board screws down.
module amp_mounts() {
    translate([amp_cx(), board_cy(), wall])
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(amp_w/2 - 2), sy*(amp_l/2 - 2), 0])
                screw_boss(amp_standoff_h, amp_standoff_od, amp_screw_pilot);
}

// 4 corner screw bosses (front side), self-tap pilots
module front_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

module front_shell() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
            speaker_screw_bosses();
            atom_cradle();
            amp_mounts();
            front_bosses();
        }
        grille_cut();
        gasket_grooves();
        button_well();
        mic_perf();
    }
}

// fit-test coupon: the lower band of the front shell — the bottom arc of the
// speaker seat, the cradle, button well, mic, and amp standoffs — plus a button
// cap printed alongside it (placed in the empty top area).
module coupon_render() {
    intersection() {
        front_shell();
        translate([-outer_w()/2 - 1, -outer_h()/2 - 1, -5])
            cube([outer_w() + 2, board_zone_h + bottom_margin + 18, front_depth + 10]);
    }
    translate([0, outer_h()/2 - 8, 0]) button_cap();
}
```

- [ ] **Step 3: Run the test to verify `front` and `coupon` are GREEN**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK asserts`, `OK front (… B)`, `OK coupon (… B)`. `rear` and `button` still `FAIL … STL too small`, so `exit=1` overall (expected until Tasks 3–4).

- [ ] **Step 4: Commit**

```bash
git add hardware/kitchen-case/modules/front_shell.scad
git commit -m "feat(kitchen-case): front shell — centered driver, atom cradle, single amp"
```

---

## Task 3: Rear wall plate

**Files:**
- Modify: `hardware/kitchen-case/modules/rear_plate.scad` (replace stub with full content)

- [ ] **Step 1: Confirm `rear` is currently RED**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK front`, `OK coupon`, `FAIL rear: STL too small`, `FAIL button: STL too small`.

- [ ] **Step 2: Write the full `modules/rear_plate.scad`** (carried over from terrace; uses the narrower `keyhole_spacing` and `outer_w()` from params)

```openscad
// ===== rear wall plate (no top-level geometry) =====
module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);   // plate
            for (sx = [-1, 1], sy = [-1, 1])                                    // mating bosses
                translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
                    cylinder(h = rear_depth - wall, d = boss_od);
        }
        // screw clearance holes (rear -> into front bosses)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = rear_depth + 0.2, d = screw_clear);
        // keyhole wall-mount slots
        for (sx = [-1, 1])
            translate([sx*keyhole_spacing/2, 0, -0.1])
                linear_extrude(wall + 0.2) keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
        // USB-C cable notch in the bottom edge, aligned under the cradle
        translate([cradle_cx(), -outer_h()/2, rear_depth/2])
            cube([mod_usb_w + 2, wall*4, rear_depth + 0.2], center = true);
    }
}
```

- [ ] **Step 3: Run the test to verify `rear` is GREEN**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK rear (… B)`. `button` still `FAIL … STL too small`, so `exit=1` overall (expected until Task 4).

- [ ] **Step 4: Commit**

```bash
git add hardware/kitchen-case/modules/rear_plate.scad
git commit -m "feat(kitchen-case): rear plate — keyholes, USB-C notch, mating bosses"
```

---

## Task 4: Button cap plunger

**Files:**
- Modify: `hardware/kitchen-case/modules/button_cap.scad` (replace stub with full content)

- [ ] **Step 1: Confirm `button` is currently RED**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK front`, `OK coupon`, `OK rear`, `FAIL button: STL too small`.

- [ ] **Step 2: Write the full `modules/button_cap.scad`** (carried over from terrace)

```openscad
// ===== captive button plunger (no top-level geometry) =====
module button_cap() {
    face_t  = 1.6;
    skirt_h = wall + 1.0;
    union() {
        cylinder(h = face_t, d = btn_cap_d);                                  // proud face
        translate([0, 0, -skirt_h]) cylinder(h = skirt_h, d = btn_well_d - 2*clr); // skirt in well
        translate([0, 0, -skirt_h]) cylinder(h = 1.0, d = btn_well_d - 2*clr + 1.4); // retention lip
        translate([0, 0, -skirt_h - btn_travel]) cylinder(h = btn_travel + 0.5, d = btn_nub_d); // contact nub
    }
}
```

- [ ] **Step 3: Run the test to verify ALL parts are GREEN**

Run: `hardware/kitchen-case/test.sh; echo "exit=$?"`
Expected: `OK asserts`, `OK front`, `OK rear`, `OK button`, `OK coupon`, and `exit=0`.

- [ ] **Step 4: Commit**

```bash
git add hardware/kitchen-case/modules/button_cap.scad
git commit -m "feat(kitchen-case): captive button plunger"
```

---

## Task 5: README, build verification, final commit

**Files:**
- Create: `hardware/kitchen-case/README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Kitchen Atom Echo Enclosure

Parametric OpenSCAD wall-mount case for the kitchen intercom: classic M5Stack
Atom Echo + 1× MAX98357A + 1× 2" driver. Design spec:
[../../docs/superpowers/specs/2026-06-01-kitchen-case-design.md](../../docs/superpowers/specs/2026-06-01-kitchen-case-design.md).
Forked from `hardware/terrace-case` (two speakers/two amps) down to a single
speaker and a single amp.

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # front.stl, rear.stl, button.stl into stl/
./test.sh         # asserts + clean-render check for every part
```

Render one part manually:
```bash
"$OPENSCAD" -D 'part="front"' -o stl/front.stl kitchen-case.scad
```
Parts: `front`, `rear`, `button`, `coupon` (fit test), `all` (assembled preview). Select with the normal variable flag `-D part="..."` (a `$`-prefixed variable would be ignored by `-D`).

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `spk_od`, `spk_cut` | driver outer dia / grille field dia |
| `mod_w`, `mod_d` | Atom Echo footprint / depth |
| `amp_gap` | space between the module cradle and the amp board |
| `mic_below_btn` | mic perforation offset below the button — tune to the module mic |
| `clr` | global fit clearance (raise if parts are tight) |
| `keyhole_spacing` | wall-screw spacing |

The case is centered on the driver; the module sits centered below it with the
single amp board to its right. Outer width is derived (`outer_w()`) from
whichever is wider — the driver or the module+amp row.

## Print before you commit to the full case

Print the **coupon** first (~10 min) and dry-fit the module, a driver, and the
button cap:
```bash
"$OPENSCAD" -D 'part="coupon"' -o stl/coupon.stl kitchen-case.scad
```
- Cradle too tight/loose → adjust `clr` / `mod_clr`.
- Button binds or has no travel → adjust `btn_well_d` / `btn_travel`.
- Driver doesn't seat → adjust `spk_od` / `spk_seat_depth`.
- Driver screw holes don't line up → adjust `spk_bolt_circle` / `spk_screw_n` / `spk_screw_a0` to match your driver's flange.

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice (indoor location).

## BOM

- 1× M5Stack Atom Echo (classic)
- 1× MAX98357A breakout
- 1× 2" full-range driver (~53 mm OD)
- 4× M3 screws (self-tap into the corner front/rear bosses)
- 4× M2 self-tap screws for the driver (into the bolt-circle bosses)
- 4× M2 self-tap screws for the amp board (into the standoffs)
- 1× foam/EVA gasket ring for the driver (~45–52 mm, seats in the baffle groove)
- 2× wall screws for the keyhole slots

## Assembly

1. Drop a foam/EVA gasket ring into the baffle groove around the driver, then seat the driver into the front-shell ring; fasten with 4× M2 through the flange into the bolt-circle bosses (compressing the gasket); solder driver leads to the amp `+/−`.
2. Drop the Atom Echo into the cradle top-face-forward (its button + mic end up behind the well and the perforation in the front wall); route header wires through the side window to the amp.
3. Seat the amp board on its standoffs; fasten with 4× M2 into the standoff pilots.
4. Drop the button cap into its well from the front (snaps captive).
5. Hang the rear plate on two wall screws via the keyholes.
6. Mate front to rear; drive 4× M3 from the back.

Wiring (amp taps + internal-speaker handling) is covered by the louder-amp
design: [../../docs/superpowers/specs/2026-06-01-kitchen-atom-echo-louder-amp-design.md](../../docs/superpowers/specs/2026-06-01-kitchen-atom-echo-louder-amp-design.md).

Then run the full suite + build and confirm STLs are produced:
```bash
hardware/kitchen-case/test.sh && hardware/kitchen-case/build.sh && ls -l hardware/kitchen-case/stl
```
````

- [ ] **Step 2: Run the full test + build and confirm all STLs are produced**

Run:
```bash
hardware/kitchen-case/test.sh && hardware/kitchen-case/build.sh && ls -l hardware/kitchen-case/stl; echo "exit=$?"
```
Expected: every part `OK` from `test.sh`, `done -> stl/` from `build.sh`, and `stl/` listing `front.stl`, `rear.stl`, `button.stl` (plus `coupon.stl` from the test run), each well over 1000 B. `exit=0`.

- [ ] **Step 3: Commit**

```bash
git add hardware/kitchen-case/README.md
git commit -m "docs(kitchen-case): README — render, params, coupon, BOM, assembly"
```

---

## Self-Review notes (verification of this plan against the spec)

- **Spec coverage:** front shell with one centered driver (Task 2), Atom Echo cradle top-face-forward (Task 2), one amp mount (Task 2), button well + mic perforation under button (Task 2), gasket groove + grille + bolt bosses (Task 2), rear plate keyholes + USB-C notch + mating bosses (Task 3), button cap (Task 4), parametric `params.scad` + `part` selector (Task 1), coupon fit-test (Task 2), build/test scripts (Task 1), gitignored `stl/` (Task 1), README with print settings/BOM/assembly (Task 5). New `hardware/kitchen-case` fork with own `lib.scad` (Tasks 1–5). All spec sections map to a task.
- **Type/name consistency:** `outer_w/outer_h/spk_cx/spk_cy/board_cy/cradle_cx/mic_x/mic_y/amp_cx/board_reach` defined in `params.scad` (Task 1) are the exact names used in `front_shell.scad`/`rear_plate.scad` (Tasks 2–3). Module renamed `voicesr_cradle` → `atom_cradle` consistently (defined and called in Task 2). `coupon_render` defined in `front_shell.scad` (Task 2), referenced by the entry (Task 1) and stubbed in Task 1.
- **Out of scope (per spec):** no firmware/YAML changes; amp wiring + internal-speaker disconnect live in the louder-amp design (README links to it); no shared CAD library (deliberate fork).
- **Open items for physical confirmation (carried from spec, noted in `params.scad`):** Atom Echo cradle dims + USB-C port position, mic offset, driver OD/cutout/bolt pattern, MAX98357A footprint. Defaults are sensible; the coupon (Task 2) validates them before a full print.
```
