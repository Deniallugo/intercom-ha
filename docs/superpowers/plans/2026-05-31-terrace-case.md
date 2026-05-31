# Terrace VoiceS3R Enclosure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parametric OpenSCAD wall-mount enclosure for the terrace combo (M5Stack VoiceS3R + 2× MAX98357A + 2× 2" drivers), rendering to STL from source.

**Architecture:** Two-part clamshell (front shell + rear wall plate) plus a captive button plunger, all driven by one shared parameters file. Geometry is split into small composable modules so each feature renders and verifies independently. A `coupon` render slices out just the fit-critical features for a fast test print.

**Tech Stack:** OpenSCAD (CSG modeling language), bash build/test scripts driving the `openscad` CLI in headless mode.

---

## Toolchain note (read first)

OpenSCAD 2021.01 is installed at `/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD` (the user's `osc` wrapper points at it). It is **not** on `PATH` as `openscad`, so export the binary once per shell:

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
```

The core verification primitive throughout: render a part with `--hardwarnings` (exits non-zero on any CAD warning, including non-manifold geometry) and confirm the output STL is non-trivial (> 1000 bytes). Geometry math is verified separately via `assert()` in `tests/asserts.scad`.

## File Structure

```
hardware/terrace-case/
├── terrace-case.scad        # includes everything; $part selector + render
├── modules/
│   ├── params.scad          # ALL variables + derived-dimension functions. No geometry.
│   ├── lib.scad             # rounded_rect, grille, keyhole, screw_boss. No top-level geometry.
│   ├── front_shell.scad     # front_shell() + sub-modules + coupon_render(). No top-level geometry.
│   ├── rear_plate.scad      # rear_plate(). No top-level geometry.
│   └── button_cap.scad      # button_cap(). No top-level geometry.
├── tests/
│   └── asserts.scad         # assert() checks on derived dimensions
├── build.sh                 # render front/rear/button → stl/ (binary)
├── test.sh                  # asserts + render every part with --hardwarnings, size-check
├── stl/                     # generated (gitignored)
├── .gitignore               # ignores stl/
└── README.md                # params, print settings, BOM, assembly
```

**Key scoping rule:** module files contain *only* module/function definitions (no top-level geometry) and do **not** `include params.scad` themselves. `terrace-case.scad` and `tests/asserts.scad` `include` `params.scad` first, then the other files, so all parameters are global and in scope. This avoids OpenSCAD's `use`-vs-`include` variable-scope pitfalls and duplicate-include warnings.

---

## Task 0: Toolchain + scaffold

**Files:**
- Create: `hardware/terrace-case/.gitignore`
- Create: `hardware/terrace-case/modules/` (dir), `hardware/terrace-case/tests/` (dir), `hardware/terrace-case/stl/` (dir)

- [ ] **Step 1: Locate OpenSCAD (already installed)**

Run:
```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
"$OPENSCAD" --version
```
Expected: `OpenSCAD version 2021.01`. If it errors, locate the binary and set `OPENSCAD` accordingly.

- [ ] **Step 2: Create directories and .gitignore**

Run:
```bash
mkdir -p hardware/terrace-case/modules hardware/terrace-case/tests hardware/terrace-case/stl
```

`hardware/terrace-case/.gitignore`:
```gitignore
stl/
*.stl
```

- [ ] **Step 3: Commit**

```bash
git add hardware/terrace-case/.gitignore
git commit -m "chore: scaffold terrace-case hardware dir"
```

---

## Task 1: Parameters + derived-dimension functions

**Files:**
- Create: `hardware/terrace-case/modules/params.scad`
- Create: `hardware/terrace-case/tests/asserts.scad`

- [ ] **Step 1: Write the failing test**

`hardware/terrace-case/tests/asserts.scad`:
```openscad
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"$OPENSCAD" --hardwarnings -o /tmp/asserts.stl hardware/terrace-case/tests/asserts.scad
```
Expected: FAIL — `Can't open include file '../modules/params.scad'` (params not created yet).

- [ ] **Step 3: Write params.scad**

`hardware/terrace-case/modules/params.scad`:
```openscad
// ===== Terrace VoiceS3R enclosure — parameters (no geometry) =====
$fn = 64;

// ---- fit ----
clr = 0.4;                 // global clearance for inserted parts

// ---- shell envelope ----
wall        = 2.4;
radius      = 6;
front_depth = 30;          // inner depth of the front shell (speaker zone)
rear_depth  = 12;          // depth of the rear plate body

// ---- speakers (2" full-range) ----
spk_od         = 53;       // driver outer diameter (locating ring ID)
spk_cut        = 46;       // grille perforation field diameter
spk_gap        = 3;        // gap between the two drivers
spk_seat_depth = 4;        // height of the inner locating ring

// ---- margins / board zone ----
side_margin   = 7;
top_margin    = 7;
board_zone_h  = 30;
bottom_margin = 8;

// ---- grille ----
grille_hole_d    = 3;
grille_ring_step = 6;      // radial spacing between hole rings

// ---- VoiceS3R module (24x24 footprint, button-forward) ----
mod_w   = 24;              // module footprint (square)
mod_d   = 17;              // module depth front-to-back inside the case
mod_clr = clr;
mod_usb_w = 10;            // USB-C cutout width
mod_usb_h = 4;            // USB-C cutout height
cradle_wall = 1.6;

// ---- button ----
btn_well_d = 12.5;         // well bore (cap skirt rides in this)
btn_cap_d  = 12;           // cap face diameter (slightly proud)
btn_travel = 2;
btn_nub_d  = 4;            // nub that contacts the module switch

// ---- microphone ----
mic_port_d  = 2;           // acoustic hole through front wall
mic_boss_od = 8;           // sealing collar OD (gasket seat)
mic_boss_h  = 3;

// ---- amp boards (MAX98357A breakout, generic clone) ----
amp_w = 18;
amp_l = 16;
amp_standoff_h = 3;

// ---- wall mount ----
keyhole_spacing = 90;
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;

// ---- screws (M3) ----
boss_od     = 7;
screw_pilot = 2.6;         // self-tap pilot in the front bosses
screw_clear = 3.4;         // clearance hole in the rear plate
boss_inset  = radius + 2;  // corner inset for the 4 screw bosses

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()  = spk_od*2 + spk_gap + side_margin*2;            // 123
function outer_h()  = top_margin + spk_od + board_zone_h + bottom_margin; // 98
function outer_d()  = front_depth + rear_depth;                      // 42
function spk_cx()   = spk_od/2 + spk_gap/2;                          // 28
function spk_cy()   = outer_h()/2 - top_margin - spk_od/2;
function board_cy() = -outer_h()/2 + bottom_margin + board_zone_h/2;
function cradle_cx()= -outer_w()/2 + side_margin + cradle_wall + (mod_w+2*mod_clr)/2;
function mic_x()    = outer_w()/2 - 10;     // bottom-right, away from drivers
function mic_y()    = -outer_h()/2 + 6;
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"$OPENSCAD" --hardwarnings -o /tmp/asserts.stl hardware/terrace-case/tests/asserts.scad && echo PASS
```
Expected: PASS (no assert failures, STL written).

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/params.scad hardware/terrace-case/tests/asserts.scad
git commit -m "feat(case): parameters + derived-dimension asserts"
```

---

## Task 2: Shared library helpers

**Files:**
- Create: `hardware/terrace-case/modules/lib.scad`
- Modify: `hardware/terrace-case/tests/asserts.scad` (add a render-smoke of each helper)

- [ ] **Step 1: Write the failing test** (append to `tests/asserts.scad`, before the `cube(1);` sentinel)

```openscad
// helper render smoke — these must produce geometry without warnings
rounded_rect(20, 10, 2);
grille(spk_cut);
keyhole(keyhole_slot_w, keyhole_head_d, keyhole_drop);
screw_boss(8, boss_od, screw_pilot);
```
And add at the very top of `tests/asserts.scad`, right after the existing include line:
```openscad
include <../modules/lib.scad>
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
"$OPENSCAD" --hardwarnings -o /tmp/asserts.stl hardware/terrace-case/tests/asserts.scad
```
Expected: FAIL — `Can't open include file '../modules/lib.scad'`.

- [ ] **Step 3: Write lib.scad**

`hardware/terrace-case/modules/lib.scad`:
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

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
"$OPENSCAD" --hardwarnings -o /tmp/asserts.stl hardware/terrace-case/tests/asserts.scad && echo PASS
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/lib.scad hardware/terrace-case/tests/asserts.scad
git commit -m "feat(case): shared geometry helpers"
```

---

## Task 3: Front shell — body, speaker seats, grilles + selector

**Files:**
- Create: `hardware/terrace-case/modules/front_shell.scad`
- Create: `hardware/terrace-case/terrace-case.scad`

- [ ] **Step 1: Write front_shell.scad (body + speakers only for now)**

`hardware/terrace-case/modules/front_shell.scad`:
```openscad
// ===== front shell + sub-modules (no top-level geometry) =====

// raised locating rings on the inside of the front wall (driver drops in)
module speaker_seats() {
    for (sx = [-1, 1])
        translate([sx*spk_cx(), spk_cy(), wall])
            difference() {
                cylinder(h = spk_seat_depth, d = spk_od + 2*cradle_wall);
                translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
            }
}

// perforations through the front wall over each speaker
module grille_cut() {
    translate([0, 0, -0.1]) linear_extrude(wall + 0.2)
        for (sx = [-1, 1]) translate([sx*spk_cx(), spk_cy()]) grille(spk_cut);
}

module front_shell() {
    difference() {
        union() {
            shell_body(front_depth);
            speaker_seats();
        }
        grille_cut();
    }
}
```

- [ ] **Step 2: Write the selector**

`hardware/terrace-case/terrace-case.scad`:
```openscad
// ===== Terrace VoiceS3R enclosure — render entry point =====
// Render a single part:  openscad -D '$part="front"' -o out.stl terrace-case.scad
// Parts: "front" | "rear" | "button" | "coupon" | "all" (assembled preview)
include <modules/params.scad>
include <modules/lib.scad>
include <modules/front_shell.scad>
include <modules/rear_plate.scad>
include <modules/button_cap.scad>

part = is_undef($part) ? "all" : $part;

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

**Note:** this includes `rear_plate.scad` and `button_cap.scad`, which don't exist yet — create empty placeholder files so `front` renders now:
```bash
printf '// placeholder\nmodule rear_plate(){}\nmodule coupon_render(){}\n' > hardware/terrace-case/modules/rear_plate.scad
printf '// placeholder\nmodule button_cap(){}\n' > hardware/terrace-case/modules/button_cap.scad
```

- [ ] **Step 3: Render the front part**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="front"' -o /tmp/front.stl hardware/terrace-case/terrace-case.scad && wc -c /tmp/front.stl
```
Expected: PASS, STL well over 1000 bytes. (If `--hardwarnings` trips on a CGAL note, read it — a real non-manifold means two solids share a face; nudge overlaps by 0.1.)

- [ ] **Step 4: Visual check (manual)**

Run:
```bash
"$OPENSCAD" -D '$part="front"' --camera=0,0,0,55,0,25,260 --imgsize=900,700 -o /tmp/front.png hardware/terrace-case/terrace-case.scad
```
Open `/tmp/front.png`: confirm a landscape box with two perforated circular grilles side by side near the top.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad hardware/terrace-case/modules/rear_plate.scad hardware/terrace-case/modules/button_cap.scad hardware/terrace-case/terrace-case.scad
git commit -m "feat(case): front shell body + speaker seats + grilles + part selector"
```

---

## Task 4: Front shell — VoiceS3R cradle (button-forward, USB notch, wire window)

**Files:**
- Modify: `hardware/terrace-case/modules/front_shell.scad`

- [ ] **Step 1: Add the cradle module** (insert before `module front_shell()`)

```openscad
// 3-wall pocket holding the module button-forward; open at the back (+z),
// USB-C slot toward the bottom edge, wire window toward the amps (+x).
module voicesr_cradle() {
    cw = mod_w + 2*mod_clr;                 // inner pocket size
    translate([cradle_cx(), board_cy(), wall]) difference() {
        translate([0, 0, mod_d/2]) cube([cw + 2*cradle_wall, cw + 2*cradle_wall, mod_d], center = true);
        // pocket, open at back
        translate([0, 0, mod_d/2 + cradle_wall]) cube([cw, cw, mod_d], center = true);
        // USB-C slot through the bottom wall (toward -y)
        translate([0, -(cw/2 + cradle_wall), mod_usb_h/2 + 1])
            cube([mod_usb_w, cradle_wall*3, mod_usb_h], center = true);
        // wire window toward the amps (+x)
        translate([cw/2 + cradle_wall, 0, mod_d*0.55])
            cube([cradle_wall*3, mod_w*0.6, mod_d*0.6], center = true);
    }
}
```

- [ ] **Step 2: Add cradle to the union in `front_shell()`**

Change the `union()` block inside `front_shell()` to:
```openscad
        union() {
            shell_body(front_depth);
            speaker_seats();
            voicesr_cradle();
        }
```

- [ ] **Step 3: Render and size-check**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="front"' -o /tmp/front.stl hardware/terrace-case/terrace-case.scad && wc -c /tmp/front.stl
```
Expected: PASS, STL larger than before.

- [ ] **Step 4: Visual check (manual)**

Re-render the PNG from Task 3 Step 4. Confirm a square pocket sits in the lower-left of the inner cavity with a notch on its bottom wall.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad
git commit -m "feat(case): VoiceS3R cradle with USB notch and wire window"
```

---

## Task 5: Front shell — button well + captive button cap

**Files:**
- Modify: `hardware/terrace-case/modules/front_shell.scad`
- Create: `hardware/terrace-case/modules/button_cap.scad` (replace placeholder)

- [ ] **Step 1: Add the button well module** (insert before `module front_shell()`)

```openscad
// well bored through the front wall, centered over the module button,
// with an internal retaining shoulder the cap's lip catches behind.
module button_well() {
    translate([cradle_cx(), board_cy(), -0.1]) {
        cylinder(h = wall + 0.2, d = btn_well_d);                       // bore
        translate([0, 0, wall]) cylinder(h = 1.2, d = btn_well_d + 1.6); // shoulder pocket
    }
}
```

- [ ] **Step 2: Subtract the well in `front_shell()`**

Change the `difference()` body of `front_shell()` so the cuts read:
```openscad
        grille_cut();
        button_well();
```

- [ ] **Step 3: Write button_cap.scad** (replace the placeholder file)

`hardware/terrace-case/modules/button_cap.scad`:
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

- [ ] **Step 4: Render both parts**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="front"'  -o /tmp/front.stl  hardware/terrace-case/terrace-case.scad && \
"$OPENSCAD" --hardwarnings -D '$part="button"' -o /tmp/button.stl hardware/terrace-case/terrace-case.scad && \
wc -c /tmp/front.stl /tmp/button.stl
```
Expected: PASS for both; both STLs > 1000 bytes.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad hardware/terrace-case/modules/button_cap.scad
git commit -m "feat(case): button well + captive plunger cap"
```

---

## Task 6: Front shell — mic port + sealing boss

**Files:**
- Modify: `hardware/terrace-case/modules/front_shell.scad`

- [ ] **Step 1: Add mic modules** (insert before `module front_shell()`)

```openscad
// acoustic hole through the front wall (subtracted)
module mic_port() {
    translate([mic_x(), mic_y(), -0.1]) cylinder(h = wall + 0.2, d = mic_port_d);
}
// sealing collar on the inside, gasket seats on its top face (added)
module mic_boss() {
    translate([mic_x(), mic_y(), wall]) difference() {
        cylinder(h = mic_boss_h, d = mic_boss_od);
        translate([0, 0, -0.1]) cylinder(h = mic_boss_h + 0.2, d = mic_port_d + 0.6);
    }
}
```

- [ ] **Step 2: Wire into `front_shell()`** — add `mic_boss();` to the union and `mic_port();` to the difference cuts:
```openscad
        union() {
            shell_body(front_depth);
            speaker_seats();
            voicesr_cradle();
            mic_boss();
        }
        grille_cut();
        button_well();
        mic_port();
```

- [ ] **Step 3: Render and size-check**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="front"' -o /tmp/front.stl hardware/terrace-case/terrace-case.scad && wc -c /tmp/front.stl
```
Expected: PASS.

- [ ] **Step 4: Visual check (manual)** — re-render the PNG; confirm a small collar with a through-hole in the bottom-right of the cavity, clear of both grilles.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad
git commit -m "feat(case): isolated mic port + sealing boss"
```

---

## Task 7: Front shell — amp standoffs + corner screw bosses

**Files:**
- Modify: `hardware/terrace-case/modules/front_shell.scad`

- [ ] **Step 1: Add amp + boss modules** (insert before `module front_shell()`)

```openscad
// two amp boards in a row, right of the cradle, on short standoff posts
module amp_mounts() {
    base_x = cradle_cx() + (mod_w/2) + cradle_wall + 6 + amp_w/2;
    for (i = [0 : 1]) {
        bx = base_x + i*(amp_w + 6);
        translate([bx, board_cy(), wall])
            for (sx = [-1, 1], sy = [-1, 1])
                translate([sx*(amp_w/2 - 2), sy*(amp_l/2 - 2), 0])
                    cylinder(h = amp_standoff_h, d = 3);
    }
}
// 4 corner screw bosses (front side), self-tap pilots
module front_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}
```

- [ ] **Step 2: Add both to the union in `front_shell()`**
```openscad
        union() {
            shell_body(front_depth);
            speaker_seats();
            voicesr_cradle();
            mic_boss();
            amp_mounts();
            front_bosses();
        }
```

- [ ] **Step 3: Render and size-check**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="front"' -o /tmp/front.stl hardware/terrace-case/terrace-case.scad && wc -c /tmp/front.stl
```
Expected: PASS. The front shell is now feature-complete.

- [ ] **Step 4: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad
git commit -m "feat(case): amp standoffs + corner screw bosses"
```

---

## Task 8: Rear wall plate

**Files:**
- Modify: `hardware/terrace-case/modules/rear_plate.scad` (replace placeholder)

- [ ] **Step 1: Write rear_plate.scad**

`hardware/terrace-case/modules/rear_plate.scad`:
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
        // screw clearance holes (rear → into front bosses)
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
Remove the placeholder `coupon_render(){}` line if it's still in this file — `coupon_render` moves to `front_shell.scad` in Task 9. (If you leave it, delete it now to avoid a duplicate definition.)

- [ ] **Step 2: Render and size-check**

Run:
```bash
"$OPENSCAD" --hardwarnings -D '$part="rear"' -o /tmp/rear.stl hardware/terrace-case/terrace-case.scad && wc -c /tmp/rear.stl
```
Expected: PASS, STL > 1000 bytes.

- [ ] **Step 3: Visual check (manual)**

Run:
```bash
"$OPENSCAD" -D '$part="rear"' --camera=0,0,0,55,0,0,260 --imgsize=900,700 -o /tmp/rear.png hardware/terrace-case/terrace-case.scad
```
Confirm a plate with two keyhole slots (head + slot) and four corner bosses; a notch in the bottom edge.

- [ ] **Step 4: Commit**

```bash
git add hardware/terrace-case/modules/rear_plate.scad
git commit -m "feat(case): rear wall plate with keyholes + cable notch"
```

---

## Task 9: Coupon render + build/test scripts

**Files:**
- Modify: `hardware/terrace-case/modules/front_shell.scad` (add `coupon_render()`)
- Create: `hardware/terrace-case/build.sh`
- Create: `hardware/terrace-case/test.sh`

- [ ] **Step 1: Add coupon_render() to front_shell.scad** (append at end)

```openscad
// fit-test coupon: the left slice of the front shell — one speaker seat,
// the cradle, button well, and mic features — plus a button cap to test.
module coupon_render() {
    intersection() {
        front_shell();
        translate([-outer_w()/2 - 1, board_cy() - 28, -5])
            cube([outer_w()/2 + 12, 70, front_depth + 10]);
    }
    translate([-outer_w()/2 + 6, board_cy() + 40, 0]) button_cap();
}
```

- [ ] **Step 2: Write test.sh**

`hardware/terrace-case/test.sh`:
```bash
#!/usr/bin/env bash
set -uo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
fail=0

echo "== parameter asserts =="
"$OPENSCAD" --hardwarnings -o /tmp/tc_asserts.stl tests/asserts.scad >/dev/null 2>&1 \
    && echo "OK asserts" || { echo "FAIL asserts"; fail=1; }

for part in front rear button coupon; do
    if "$OPENSCAD" --hardwarnings -D "\$part=\"$part\"" -o "stl/$part.stl" terrace-case.scad 2>/tmp/tc_err; then
        sz=$(wc -c < "stl/$part.stl")
        if [ "$sz" -lt 1000 ]; then echo "FAIL $part: STL too small ($sz B)"; fail=1
        else echo "OK $part ($sz B)"; fi
    else
        echo "FAIL $part render:"; cat /tmp/tc_err; fail=1
    fi
done
exit $fail
```

- [ ] **Step 3: Write build.sh**

`hardware/terrace-case/build.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail
OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
[ -x "$OPENSCAD" ] || { echo "OpenSCAD not found (set \$OPENSCAD)"; exit 1; }
cd "$(dirname "$0")"
mkdir -p stl
for part in front rear button; do
    echo "rendering $part ..."
    "$OPENSCAD" -D "\$part=\"$part\"" -o "stl/$part.stl" terrace-case.scad
done
echo "done -> stl/"
```

- [ ] **Step 4: Make executable and run the test suite**

Run:
```bash
chmod +x hardware/terrace-case/test.sh hardware/terrace-case/build.sh
hardware/terrace-case/test.sh
```
Expected: `OK asserts`, `OK front`, `OK rear`, `OK button`, `OK coupon`; exit 0.

- [ ] **Step 5: Commit**

```bash
git add hardware/terrace-case/modules/front_shell.scad hardware/terrace-case/test.sh hardware/terrace-case/build.sh
git commit -m "feat(case): coupon render + build/test scripts"
```

---

## Task 10: README + final build

**Files:**
- Create: `hardware/terrace-case/README.md`

- [ ] **Step 1: Write README.md**

`hardware/terrace-case/README.md`:
````markdown
# Terrace VoiceS3R Enclosure

Parametric OpenSCAD wall-mount case for the terrace intercom combo: M5Stack
VoiceS3R + 2× MAX98357A + 2× 2" drivers. Design spec:
[../../docs/superpowers/specs/2026-05-31-terrace-case-design.md](../../docs/superpowers/specs/2026-05-31-terrace-case-design.md).

## Render

```bash
export OPENSCAD="${OPENSCAD:-$(command -v openscad || echo /Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD)}"
./build.sh        # front.stl, rear.stl, button.stl into stl/
./test.sh         # asserts + clean-render check for every part
```

Render one part manually:
```bash
"$OPENSCAD" -D '$part="front"' -o stl/front.stl terrace-case.scad
```
Parts: `front`, `rear`, `button`, `coupon` (fit test), `all` (assembled preview).

## Parameters

All in [modules/params.scad](modules/params.scad). Common edits:

| Param | Meaning |
|---|---|
| `spk_od`, `spk_cut` | driver outer dia / grille field dia |
| `spk_gap` | gap between the two drivers (lower = tighter) |
| `mod_w`, `mod_d` | VoiceS3R footprint / depth |
| `mic_x()`, `mic_y()` | mic port position — set after measuring the module |
| `clr` | global fit clearance (raise if parts are tight) |
| `keyhole_spacing` | wall-screw spacing |

## Print before you commit to the full case

Print the **coupon** first (~10 min) and dry-fit the module, a driver, and the
button cap:
```bash
"$OPENSCAD" -D '$part="coupon"' -o stl/coupon.stl terrace-case.scad
```
- Cradle too tight/loose → adjust `clr` / `mod_clr`.
- Button binds or has no travel → adjust `btn_well_d` / `btn_travel`.
- Driver doesn't seat → adjust `spk_od` / `spk_seat_depth`.

## Print settings

- Front shell: grille face **down** (no supports needed). 0.2 mm layers, ≥4 perimeters, 20–30% infill.
- Rear plate: flat.
- Button cap: face down.
- Material: your choice; location is sheltered.

## BOM

- 1× M5Stack ATOM Echo S3R (VoiceS3R)
- 2× MAX98357A breakout
- 2× 2" full-range driver (~53 mm OD)
- 4× M3 screws (self-tap into front bosses)
- Thin EVA/foam ring for the mic boss gasket
- 2× wall screws for the keyhole slots

## Assembly

1. Press the EVA ring onto the mic boss.
2. Seat the two drivers into the front-shell rings; secure with M2 screws or printed tabs; solder driver leads to the amp `+/−`.
3. Drop the VoiceS3R into the cradle button-forward; route header wires through the side window to the amps.
4. Seat the amp boards on their standoffs.
5. Drop the button cap into its well from the front (snaps captive).
6. Hang the rear plate on two wall screws via the keyholes.
7. Mate front to rear; drive 4× M3 from the back.
````

- [ ] **Step 2: Run the full test suite + build**

Run:
```bash
hardware/terrace-case/test.sh && hardware/terrace-case/build.sh && ls -l hardware/terrace-case/stl
```
Expected: all `OK`, then `front.stl`, `rear.stl`, `button.stl` listed.

- [ ] **Step 3: Commit**

```bash
git add hardware/terrace-case/README.md
git commit -m "docs(case): README with params, print settings, BOM, assembly"
```

---

## Final verification

- [ ] `hardware/terrace-case/test.sh` exits 0 with all parts `OK`.
- [ ] PNG previews of `front`, `rear`, and `all` look like the spec's layout.
- [ ] STLs are gitignored (not committed); only source + scripts + README are tracked.
- [ ] The coupon has been (or can be) printed to validate fit before the full case.
