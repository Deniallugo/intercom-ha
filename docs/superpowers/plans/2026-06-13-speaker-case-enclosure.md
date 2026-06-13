# Speaker Case Enclosure (sound-first, PR-loaded) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework `hardware/speaker-case/` from the two-driver sealed box into a single-driver, side-mounted passive-radiator enclosure (~158×159×118 mm, ~1.5 L net) that also mounts and wires the full sound-first electronics stack.

**Architecture:** Parametric OpenSCAD. `params.scad` holds all dimensions as data + derived functions; `lib.scad` holds reusable helpers; `body.scad` builds the shell (single front driver, side PR, sealed divider, vented electronics bay); `rear_plate.scad` is the gasketed lid + wall-mount keyholes; `grille.scad` is an optional snap-on. `tests/asserts.scad` is the test harness — it renders under `--hardwarnings` and every `assert()` must hold. Each task adds asserts (red), then geometry/params (green), then renders parts.

**Tech Stack:** OpenSCAD (2021.01), bash (`build.sh`/`test.sh`). No other toolchain.

**Wiring map this enclosure must serve (the "all wiring" requirement):**
- **USB-C power IN** — bottom edge cutout aligned to the CH224K's USB-C receptacle.
- **15 V rail** CH224K → TPA3116 + → MP1584; **5 V** MP1584 → ESP32-S3 — all free-air jumpers inside the bay (board proximity, no case feature).
- **I²S/analog** S3 → PCM5102 → TPA3116 — free-air jumpers inside the bay.
- **Driver wire** TPA3116 out → up through the **single sealed divider wire pass** → PS95-8 terminals in the sealed chamber.
- **Mic** ICS-43434 on the front baffle of the bay → front **mic perforation**; wires free-air to S3.
- **PTT** panel-mount switch in a front **button bore** → wires free-air to S3.
- **Passive radiator** — no wiring (passive), side-panel mounted.

**Conventions (match the existing package):**
- Run the test harness with `./hardware/speaker-case/test.sh` (asserts + every part renders ≥1000 B).
- `[confirm vs hardware]` marks a default to verify against parts in hand; asserts enforce *fit*, not the absolute value.
- Commit after each green task.
- **Interim-failure expectation:** from Task 1 until Task 6, `test.sh` exits nonzero because the not-yet-reworked `rear` part (fixed in Task 5) and the obsolete `button` part (removed in Task 6) reference retired params. That is expected. **Each task's success gate is `OK asserts` plus `OK` for the part(s) that task touches** (`body`, then `rear`, then `grille`) — not the overall exit code. The whole suite goes green at Task 6.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `modules/params.scad` | All dimensions + derived functions | **Rewrite** — new envelope, single PS95-8, PR, 5 boards |
| `modules/lib.scad` | Shared helpers | **Add** `screw_circle`, `board_standoffs`, `board_pocket` |
| `modules/body.scad` | Shell: driver, PR, divider, bay, front features | **Rewrite** incrementally across tasks 1–5 |
| `modules/rear_plate.scad` | Gasketed lid + keyholes | **Modify** — drop module clamp, resize keyholes |
| `modules/grille.scad` | Optional snap-on grille | **Modify** — single centered disc |
| `modules/button_cap.scad` | Captive plunger (old) | **Delete** — replaced by panel-mount switch bore |
| `tests/asserts.scad` | Assert test harness | **Rewrite** incrementally across tasks 1–6 |
| `speaker-case.scad` | Part dispatcher | **Modify** — drop `"button"` part |
| `build.sh` / `test.sh` | Render + test runners | **Modify** — drop `button` from the part loop |
| `README.md` | Package docs | **Modify** — new design |

---

## Task 1: Rebaseline — new envelope + single PS95-8 driver

**Files:**
- Modify: `hardware/speaker-case/modules/params.scad` (full rewrite)
- Modify: `hardware/speaker-case/modules/lib.scad` (add `screw_circle`)
- Modify: `hardware/speaker-case/modules/body.scad` (full rewrite — driver + shell + divider stub)
- Modify: `hardware/speaker-case/tests/asserts.scad` (rebaseline to driver/shell/volume only)

- [ ] **Step 1: Rewrite `params.scad` with the new design's full parameter set**

Replace the entire file with:

```openscad
// ===== Speaker case — sound-first PR-loaded device — parameters =====
// No geometry here. ONE Dayton PS95-8 3.5" full-range on the front baffle, a
// side-mounted passive radiator, and a vented electronics bay holding the stack:
// ESP32-S3 devkit + PCM5102A DAC + TPA3116 mono amp + MP1584 buck + CH224K PD
// trigger + ICS-43434 mic + PTT switch + USB-C power in.
$fn = 64;

// ---- fit ----
clr = 0.4;                 // clearance for inserted parts

// ---- shell ----
wall   = 4;                // walls + lid + divider thickness (airtight chamber)
radius = 8;                // rounded vertical edges (baffle diffraction)
inner_w = 150;             // interior width set directly -> outer_w 158

// ---- driver: Dayton PS95-8 (single, centered) [confirm vs hardware] ----
spk_od    = 91;            // frame OD — locating-ring ID
spk_cut   = 76;            // OPEN cone cutout through the baffle
spk_depth = 45;            // seated depth front->back [confirm]
seat_wall = 1.6;           // locating-ring wall
spk_seat_depth = 4;        // locating-ring height on the inner baffle
spk_bolt_circle = 83;      // 4 screws on an 83 mm bolt CIRCLE [confirm]
spk_screw_n     = 4;
spk_screw_pilot = 1.6;     // M2 self-tap
spk_boss_od     = 5;
spk_boss_h      = spk_seat_depth + 1;

// ---- driver gasket groove ----
gasket_od    = spk_od - 1;
gasket_id    = spk_cut + 1;
gasket_depth = 1.0;

// ---- passive radiator (side panel, +x) [confirm vs hardware] ----
pr_od    = 80;             // PR frame OD
pr_cut   = 66;             // PR moving-mass cutout through the side wall
pr_depth = 25;            // PR intrusion into the chamber
pr_seat_wall   = 1.6;
pr_seat_depth  = 4;
pr_bolt_circle = 72;       // 4 screws on a bolt circle [confirm]
pr_screw_n     = 4;
pr_screw_pilot = 1.6;
pr_boss_od     = 5;
pr_boss_h      = pr_seat_depth + 1;
pr_gasket_od   = pr_od - 1;
pr_gasket_id   = pr_cut + 1;
pr_gasket_depth = 1.0;

// ---- vertical stack: speaker zone (top) | divider | board zone (bottom) ----
spk_zone_h   = 103;        // sealed chamber interior height (fits the 91 mm driver)
divider_t    = wall;
board_zone_h = 44;         // vented electronics-bay height

// ---- chamber depth (sets the sealed volume + front-to-back board room) ----
cavity_depth = 110;
front_depth  = wall + cavity_depth;   // front wall + cavity = 114

// ---- net-volume target (acoustic floor) ----
driver_disp = 60000;       // mm^3 displaced by the PS95 basket [confirm]
pr_disp     = 40000;       // mm^3 displaced by the PR assembly [confirm]
vol_target  = 1400000;     // 1.4 L net floor

// ---- divider single sealed wire pass (driver pair: 2 conductors) ----
divider_wire_d = 6;
divider_wire_z = wall + 12;

// ---- electronics-bay boards (footprints, [confirm vs hardware]) ----
// Each board placed by (x,y) center on a mounting plane. front-baffle boards
// stand on standoffs/pockets off the front wall (+z); the TPA mounts on the rear
// lid inner face (handled in rear_plate). Coordinates are relative to box center.
s3_w   = 69; s3_l   = 26;          // ESP32-S3-DevKitC-1
dac_w  = 27; dac_l  = 27;          // GY-PCM5102
buck_w = 22; buck_l = 17;          // MP1584
trig_w = 25; trig_l = 15;          // CH224K
tpa_w  = 50; tpa_l  = 30;          // TPA3116 mono (mounts on the rear lid)
board_standoff_h  = 3;
board_standoff_od = 4.5;
board_screw_pilot = 1.6;           // M2 self-tap
pocket_wall = 1.6;                 // friction-pocket wall (boards without holes)

// board placements (x,y centers) — tuned to satisfy the no-overlap asserts
s3_pos   = [0,   8];               // relative to board_cy(): +y toward divider
dac_pos  = [-58, 8];
buck_pos = [58,  8];
trig_pos = [50, -12];              // low, by the USB-C exit
mic_pos  = [-50, -12];             // mic board, front baffle, away from button
tpa_pos  = [0,   0];               // on the rear lid, centered in the bay

// ---- USB-C power IN (CH224K receptacle at the bottom edge) ----
usb_conn_w   = 10;
usb_conn_t   = 10;
usb_clr      = 3;
usb_z        = wall + 8;           // receptacle center depth from the front face [confirm]

// ---- PTT panel-mount momentary switch (front bore) [confirm vs hardware] ----
btn_bore_d   = 12.2;               // 12 mm panel-mount thread + clearance
btn_nut_d    = 14;                 // wrench-flat clearance behind the panel

// ---- microphone (ICS-43434 board + front perforation) ----
mic_board_w  = 17; mic_board_l = 14;
mic_hole_d   = 1.5;
mic_ring_r   = 2.6;
mic_ring_n   = 6;

// ---- wall mount: BLIND keyhole bosses on the lid OUTER face ----
keyhole_spacing = 120;             // wider for the bigger/heavier box
keyhole_slot_w  = 4;
keyhole_head_d  = 9;
keyhole_drop    = 8;
kb_h            = 4;
kb_pad          = 3.5;
function key_cy() = 30;            // keyhole height on the lid (upper, chamber region)

// ---- rear-plate perimeter gasket groove ----
lid_gasket_inset = wall + 3;
lid_gasket_w     = 2.0;
lid_gasket_depth = 1.0;

// ---- corner screws (M3) fastening the rear plate ----
boss_od     = 7;
screw_pilot = 2.6;
screw_clear = 3.4;
boss_inset  = radius + 3;

// ---- derived dimensions (functions so tests can assert them) ----
function outer_w()    = inner_w + 2*wall;                                  // 158
function outer_h()    = 2*wall + spk_zone_h + divider_t + board_zone_h;    // 159
function outer_d()    = front_depth + wall;                                // 118
function spk_cx()     = 0;                                                 // driver centered
function spk_cy()     = (outer_h()/2 - wall) - spk_zone_h/2;               // speaker-zone center
function divider_cy() = (outer_h()/2 - wall) - spk_zone_h - divider_t/2;   // divider center
function board_cy()   = -outer_h()/2 + wall + board_zone_h/2;              // board-zone center
function side_x()     = outer_w()/2 - wall;                                // inner face of the +x side wall
function pr_cz()      = wall + cavity_depth/2;                             // PR center depth
function gross_vol()  = (outer_w()-2*wall) * spk_zone_h * cavity_depth;    // chamber only
function net_vol()    = gross_vol() - driver_disp - pr_disp;
```

- [ ] **Step 2: Add `screw_circle` to `lib.scad`**

Append to `hardware/speaker-case/modules/lib.scad` (before the final line):

```openscad
// N screw bosses on a bolt CIRCLE of diameter `bc`, base at z=0
module screw_circle(n, bc, h, od, pilot) {
    for (i = [0 : n - 1])
        rotate([0, 0, i*360/n + 45]) translate([bc/2, 0, 0])
            screw_boss(h, od, pilot);
}
```

- [ ] **Step 3: Rewrite `body.scad` — single driver + shell + divider stub**

Replace the entire file with:

```openscad
// ===== sound-first PR-loaded shell body (no top-level geometry) =====
// Open-back box. A horizontal divider seals the upper SPEAKER CHAMBER (one
// PS95-8 on the front baffle, a passive radiator on the +x side wall) off from
// the lower vented ELECTRONICS BAY. Driver wires run up through one sealed pass
// in the divider. PR/bay geometry is added in later tasks.

// ---- speaker zone (upper, sealed) -----------------------------------------

module speaker_seat() {
    translate([spk_cx(), spk_cy(), wall])
        difference() {
            cylinder(h = spk_seat_depth, d = spk_od + 2*seat_wall);
            translate([0, 0, -0.1]) cylinder(h = spk_seat_depth + 0.2, d = spk_od + 2*clr);
        }
}

module cone_cut() {
    translate([spk_cx(), spk_cy(), -0.1]) linear_extrude(wall + 0.2) circle(d = spk_cut);
}

module gasket_groove() {
    translate([spk_cx(), spk_cy(), wall - gasket_depth])
        difference() {
            cylinder(h = gasket_depth + 0.1, d = gasket_od);
            translate([0, 0, -0.1]) cylinder(h = gasket_depth + 0.3, d = gasket_id);
        }
}

module speaker_screw_bosses() {
    translate([spk_cx(), spk_cy(), wall])
        screw_circle(spk_screw_n, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);
}

// ---- divider (sealing floor) -----------------------------------------------

// single sealed wire pass, centered under the driver
module divider_wire_cut() {
    translate([spk_cx(), divider_cy(), divider_wire_z])
        rotate([90, 0, 0])
            cylinder(h = divider_t*3, d = divider_wire_d, center = true);
}

module divider() {
    difference() {
        translate([0, divider_cy(), wall + cavity_depth/2])
            cube([outer_w() - 2*wall, divider_t, cavity_depth], center = true);
        divider_wire_cut();
    }
}

// ---- corners --------------------------------------------------------------

module corner_bosses() {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), wall])
            screw_boss(front_depth - wall, boss_od, screw_pilot);
}

module body() {
    difference() {
        union() {
            shell_body(front_depth);
            divider();
            speaker_seat();
            speaker_screw_bosses();
            corner_bosses();
        }
        cone_cut();
        gasket_groove();
    }
}
```

- [ ] **Step 4: Rewrite `tests/asserts.scad` to the rebaselined (driver/shell/volume) set**

Replace the entire file with:

```openscad
include <../modules/params.scad>
include <../modules/lib.scad>

// ===== shell / envelope =====
assert(outer_w() == 158, "outer width drifted from 158");
assert(outer_h() == 159, "outer height drifted from 159");
assert(outer_d() == 118, "outer depth drifted from 118");

// ===== speaker zone (upper, sealed) =====
assert(spk_cut < spk_od, "cone cutout must be smaller than the driver frame");
assert(gasket_id < gasket_od, "gasket groove must have id < od");
assert(gasket_id >= spk_cut && gasket_od <= spk_od, "gasket must sit on the flange land");
assert(gasket_depth < wall, "gasket groove must not cut through the baffle");
assert(cavity_depth >= spk_depth, "cavity must clear the driver seated depth");
assert(net_vol() >= vol_target, "net chamber volume below target — grow spk_zone_h / cavity_depth / inner_w");

// driver bolt circle clears the cone cutout and the side walls
assert(spk_bolt_circle/2 - spk_boss_od/2 > spk_cut/2, "driver bosses overlap the cone cutout");
assert(spk_cx() + spk_bolt_circle/2 + spk_boss_od/2 <= outer_w()/2 - wall, "driver bosses hit the side wall");
// driver (and its lowest boss) stays above the divider
assert(spk_cy() - spk_od/2 > divider_cy() + divider_t/2, "driver overlaps the divider — raise spk_zone_h");
assert(spk_cy() - spk_bolt_circle/2 - spk_boss_od/2 > divider_cy() + divider_t/2, "driver bosses overlap the divider");

// ===== divider (single sealed wire pass) =====
assert(divider_cy() < spk_cy() && divider_cy() > board_cy(), "divider must sit between the zones");
assert(divider_wire_z - divider_wire_d/2 >= wall, "wire pass runs into the front face — raise divider_wire_z");
assert(divider_wire_z + divider_wire_d/2 <= front_depth, "wire pass runs off the back edge — lower divider_wire_z");

// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");

// helper render smoke
linear_extrude(1) rounded_rect(20, 10, 2);
screw_boss(8, boss_od, screw_pilot);
screw_circle(4, spk_bolt_circle, spk_boss_h, spk_boss_od, spk_screw_pilot);

cube(1);  // non-empty render under --hardwarnings
```

- [ ] **Step 5: Run the test harness — expect FAIL first if any value is off, then PASS**

Run: `./hardware/speaker-case/test.sh`
Expected after the edits above: **`OK asserts` and `OK body`** (the gate for this task). `OK grille` should also pass (its old module still resolves). **`FAIL rear` and `FAIL button` are expected here** — `rear` references the retired `mod_clamp*` params (reworked in Task 5) and `button` references retired `btn_*` params (removed in Task 6). If an *assert* fails, read its message and adjust the named param until green.

- [ ] **Step 6: Commit**

```bash
git add hardware/speaker-case/modules/params.scad hardware/speaker-case/modules/lib.scad hardware/speaker-case/modules/body.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): rebaseline shell — single PS95-8, ~1.5L envelope"
```

---

## Task 2: Side-mounted passive radiator

**Files:**
- Modify: `hardware/speaker-case/modules/body.scad` (add PR modules + body() calls)
- Modify: `hardware/speaker-case/tests/asserts.scad` (add PR asserts)

- [ ] **Step 1: Add PR asserts (red) to `tests/asserts.scad`**

Insert before the `// ===== rear lid / shell =====` line:

```openscad
// ===== passive radiator (side panel, +x) =====
assert(pr_cut < pr_od, "PR cutout must be smaller than the PR frame");
assert(pr_gasket_id < pr_gasket_od, "PR gasket groove must have id < od");
assert(pr_gasket_id >= pr_cut && pr_gasket_od <= pr_od, "PR gasket must sit on the flange land");
assert(pr_gasket_depth < wall, "PR gasket groove must not cut through the side wall");
// PR disc fits the side panel's chamber region in y (height) and z (depth)
assert(spk_cy() + pr_od/2 <= (outer_h()/2 - wall), "PR runs off the top of the chamber");
assert(spk_cy() - pr_od/2 >= divider_cy() + divider_t/2, "PR dips below the divider");
assert(pr_cz() - pr_od/2 >= wall, "PR runs into the front face");
assert(pr_cz() + pr_od/2 <= front_depth, "PR runs off the back edge");
// PR intrusion clears the driver basket on the centerline
assert(side_x() - pr_depth > spk_cx() + spk_od/2, "PR intrudes into the driver basket");
```

Run: `./hardware/speaker-case/test.sh` → Expected: still `OK asserts` (these are param-only checks and should hold with the defaults; if one fails, adjust the named PR param).

- [ ] **Step 2: Add PR geometry to `body.scad`**

Add these modules after `gasket_groove()`:

```openscad
// ---- passive radiator (mounted on the +x side wall, fires sideways) --------

// locating ring on the INNER side-wall face
module pr_seat() {
    translate([side_x(), spk_cy(), pr_cz()]) rotate([0, -90, 0])
        difference() {
            cylinder(h = pr_seat_depth, d = pr_od + 2*pr_seat_wall);
            translate([0, 0, -0.1]) cylinder(h = pr_seat_depth + 0.2, d = pr_od + 2*clr);
        }
}

// open cutout through the +x side wall
module pr_cut_hole() {
    translate([outer_w()/2 - wall - 0.1, spk_cy(), pr_cz()]) rotate([0, 90, 0])
        linear_extrude(wall + 0.2) circle(d = pr_cut);
}

module pr_gasket_groove() {
    translate([side_x() - pr_gasket_depth, spk_cy(), pr_cz()]) rotate([0, -90, 0])
        difference() {
            cylinder(h = pr_gasket_depth + 0.1, d = pr_gasket_od);
            translate([0, 0, -0.1]) cylinder(h = pr_gasket_depth + 0.3, d = pr_gasket_id);
        }
}

module pr_screw_bosses() {
    translate([side_x(), spk_cy(), pr_cz()]) rotate([0, -90, 0])
        screw_circle(pr_screw_n, pr_bolt_circle, pr_boss_h, pr_boss_od, pr_screw_pilot);
}
```

Then update `body()` to add `pr_seat(); pr_screw_bosses();` into the `union()` and `pr_cut_hole(); pr_gasket_groove();` into the difference list:

```openscad
module body() {
    difference() {
        union() {
            shell_body(front_depth);
            divider();
            speaker_seat();
            speaker_screw_bosses();
            pr_seat();
            pr_screw_bosses();
            corner_bosses();
        }
        cone_cut();
        gasket_groove();
        pr_cut_hole();
        pr_gasket_groove();
    }
}
```

- [ ] **Step 3: Run the harness — expect PASS + body renders with the PR**

Run: `./hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`. Visually confirm if desired: `openscad -D 'part="body"' -o /tmp/body.stl hardware/speaker-case/speaker-case.scad` and open it — a side-wall PR seat + cutout should appear.

- [ ] **Step 4: Commit**

```bash
git add hardware/speaker-case/modules/body.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): side-mounted passive radiator seat + cutout"
```

---

## Task 3: Electronics-bay board mounts + no-overlap asserts

**Files:**
- Modify: `hardware/speaker-case/modules/lib.scad` (add `board_standoffs`, `board_pocket`, `aabb_clear`)
- Modify: `hardware/speaker-case/modules/body.scad` (add front-baffle board mounts)
- Modify: `hardware/speaker-case/tests/asserts.scad` (add bay-fit + pairwise no-overlap asserts)

- [ ] **Step 1: Add board helpers to `lib.scad`**

Append:

```openscad
// 4 corner standoffs for a board of footprint w x l, centered at origin, base z=0
module board_standoffs(w, l, h, od, pilot) {
    for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - 2), sy*(l/2 - 2), 0]) screw_boss(h, od, pilot);
}

// 3-wall friction pocket (open at +z) for a board w x l, centered at origin
module board_pocket(w, l, h, pw) {
    difference() {
        translate([0, 0, h/2]) cube([w + 2*pw, l + 2*pw, h], center = true);
        translate([0, 0, h/2 + pw]) cube([w, l, h], center = true);
    }
}

// boolean helper: do two centered AABBs (at p1/p2, sizes s1/s2) clear each other?
function aabb_clear(p1, s1, p2, s2) =
    (abs(p1[0]-p2[0]) >= (s1[0]+s2[0])/2) || (abs(p1[1]-p2[1]) >= (s1[1]+s2[1])/2);
```

- [ ] **Step 2: Add bay-fit + no-overlap asserts (red) to `tests/asserts.scad`**

Insert before `// ===== rear lid / shell =====`:

```openscad
// ===== electronics bay (front-baffle boards) =====
// absolute board centers in the bay (board_cy() + per-board offset)
function bpos(p) = [p[0], board_cy() + p[1]];
bay_xmin = -(outer_w()/2 - wall); bay_xmax = outer_w()/2 - wall;
bay_ymin = board_cy() - board_zone_h/2; bay_ymax = divider_cy() - divider_t/2;

// each front-baffle board stays inside the bay rectangle
module in_bay(p, w, l, name) {
    c = bpos(p);
    assert(c[0]-w/2 >= bay_xmin && c[0]+w/2 <= bay_xmax, str(name, " off bay width"));
    assert(c[1]-l/2 >= bay_ymin && c[1]+l/2 <= bay_ymax, str(name, " off bay height"));
}
in_bay(s3_pos,   s3_w,  s3_l,  "S3");
in_bay(dac_pos,  dac_w, dac_l, "DAC");
in_bay(buck_pos, buck_w, buck_l, "buck");
in_bay(trig_pos, trig_w, trig_l, "trigger");
in_bay(mic_pos,  mic_board_w, mic_board_l, "mic");

// front-baffle boards do not overlap each other (pairwise)
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(dac_pos),[dac_w,dac_l]), "S3 overlaps DAC");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(buck_pos),[buck_w,buck_l]), "S3 overlaps buck");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(trig_pos),[trig_w,trig_l]), "S3 overlaps trigger");
assert(aabb_clear(bpos(s3_pos),[s3_w,s3_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "S3 overlaps mic");
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "DAC overlaps mic");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(trig_pos),[trig_w,trig_l]), "buck overlaps trigger");
assert(aabb_clear(bpos(dac_pos),[dac_w,dac_l], bpos(trig_pos),[trig_w,trig_l]), "DAC overlaps trigger");
assert(aabb_clear(bpos(buck_pos),[buck_w,buck_l], bpos(mic_pos),[mic_board_w,mic_board_l]), "buck overlaps mic");
// TPA mounts on the rear lid; cavity must clear front standoff + board + TPA stack
assert(cavity_depth >= board_standoff_h + 2 + 16, "cavity too shallow for front + rear board stack");
```

Run: `./hardware/speaker-case/test.sh` → Expected: an overlap/off-bay FAIL is likely on the first pass. Tune the `*_pos` params in `params.scad` until all pass (this is the packing step — nudge centers; keep S3 centered-ish, smaller boards to the corners).

- [ ] **Step 3: Add front-baffle board mounts to `body.scad`**

Add after `pr_gasket_groove()`:

```openscad
// ---- electronics bay (front-baffle board mounts) ---------------------------
module bay_boards() {
    // S3 devkit: friction pocket (no reliable mount holes)
    translate([s3_pos[0], board_cy()+s3_pos[1], wall]) board_pocket(s3_w, s3_l, board_standoff_h+2, pocket_wall);
    // boards with holes: corner standoffs
    translate([dac_pos[0],  board_cy()+dac_pos[1],  wall]) board_standoffs(dac_w, dac_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    translate([buck_pos[0], board_cy()+buck_pos[1], wall]) board_standoffs(buck_w, buck_l, board_standoff_h, board_standoff_od, board_screw_pilot);
    translate([trig_pos[0], board_cy()+trig_pos[1], wall]) board_standoffs(trig_w, trig_l, board_standoff_h, board_standoff_od, board_screw_pilot);
}
```

Add `bay_boards();` to the `union()` in `body()` (after `corner_bosses();`).

- [ ] **Step 4: Run the harness — expect PASS + body renders the mounts**

Run: `./hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`.

- [ ] **Step 5: Commit**

```bash
git add hardware/speaker-case/modules/lib.scad hardware/speaker-case/modules/body.scad hardware/speaker-case/tests/asserts.scad hardware/speaker-case/modules/params.scad
git commit -m "feat(speaker-case): electronics-bay board mounts + no-overlap asserts"
```

---

## Task 4: Front-panel features — PTT bore, mic mount + perforation, USB-C power exit

**Files:**
- Modify: `hardware/speaker-case/modules/body.scad` (button bore, mic mount + perf, USB exit)
- Modify: `hardware/speaker-case/tests/asserts.scad` (asserts for the three breaches)

- [ ] **Step 1: Add asserts (red) to `tests/asserts.scad`**

Insert before `// ===== rear lid / shell =====`:

```openscad
// ===== front-panel breaches (bay only — chamber stays sealed) =====
// PTT bore is inside the bay, below the divider
btn_c = [trig_pos[0]-30, board_cy()+trig_pos[1]];   // button sits left of the trigger, low
assert(btn_c[1] + btn_nut_d/2 < divider_cy() - divider_t/2, "PTT bore breaches the chamber");
assert(btn_c[0] - btn_nut_d/2 > bay_xmin && btn_c[0] + btn_nut_d/2 < bay_xmax, "PTT bore off bay width");
// mic perforation lands over the mic board, in the bay
assert(board_cy()+mic_pos[1] < divider_cy() - divider_t/2, "mic perforation breaches the chamber");
// USB-C bottom exit is a BOUNDED (sealed) hole at the receptacle depth
usb_z_half = (usb_conn_t + usb_clr)/2;
assert(usb_z - usb_z_half >= wall, "USB hole runs into the front face — increase usb_z");
assert(usb_z + usb_z_half <= front_depth - wall, "USB hole runs to the back edge — decrease usb_z");
assert((usb_conn_w + usb_clr)/2 + boss_od/2 <= (outer_w()/2 - boss_inset), "USB hole overlaps a corner lid boss");
```

Add the matching param near the other placements in `params.scad`:

```openscad
btn_pos = [trig_pos[0]-30, -12];   // PTT panel-mount switch center (bay)
```

And change `btn_c` in the assert to use it:

```openscad
btn_c = bpos(btn_pos);
```

Run: `./hardware/speaker-case/test.sh` → tune `btn_pos` / `usb_z` until green.

- [ ] **Step 2: Add the three breaches to `body.scad`**

Add these modules after `bay_boards()`:

```openscad
// PTT panel-mount momentary switch bore through the front wall
module button_bore() {
    translate([btn_pos[0], board_cy()+btn_pos[1], -0.1]) {
        cylinder(h = wall + 0.2, d = btn_bore_d);                       // thread bore
        translate([0, 0, wall]) cylinder(h = 1.5, d = btn_nut_d);       // nut/flat relief inside
    }
}

// ICS-43434 mic board: friction pocket + a front perforation cluster over its port
module mic_mount() {
    translate([mic_pos[0], board_cy()+mic_pos[1], wall])
        board_pocket(mic_board_w, mic_board_l, board_standoff_h+1, pocket_wall);
}
module mic_perf() {
    translate([mic_pos[0], board_cy()+mic_pos[1], -0.1]) linear_extrude(wall + 0.2) {
        circle(d = mic_hole_d);
        for (i = [0 : mic_ring_n - 1])
            rotate(i*360/mic_ring_n) translate([mic_ring_r, 0]) circle(d = mic_hole_d);
    }
}

// USB-C power IN: bounded (sealed) hole through the bottom (-y) wall at usb_z
module usb_floor_cut() {
    translate([trig_pos[0], -outer_h()/2, usb_z])
        cube([usb_conn_w + usb_clr, wall*3, usb_conn_t + usb_clr], center = true);
}
```

Update `body()`: add `mic_mount();` to the `union()`, and add `button_bore(); mic_perf(); usb_floor_cut();` to the difference list.

- [ ] **Step 3: Run the harness — expect PASS**

Run: `./hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`.

- [ ] **Step 4: Commit**

```bash
git add hardware/speaker-case/modules/body.scad hardware/speaker-case/modules/params.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): PTT bore, mic mount + perforation, USB-C power exit"
```

---

## Task 5: Rear lid — TPA mount, drop module clamp, resize keyholes

**Files:**
- Modify: `hardware/speaker-case/modules/rear_plate.scad` (drop `module_clamp`, add `tpa_mount`, keep keyholes/gasket)
- Modify: `hardware/speaker-case/tests/asserts.scad` (keyhole + TPA-on-lid asserts)

- [ ] **Step 1: Add/adjust asserts (red) to `tests/asserts.scad`**

Replace the `// ===== rear lid / shell =====` block's keyhole asserts with:

```openscad
// ===== rear lid / shell =====
assert(outer_d() == front_depth + wall, "rear plate must be a flat lid: outer depth = front_depth + wall");
assert(lid_gasket_depth < wall, "lid gasket groove must not cut through the lid");
assert(outer_w() - 2*lid_gasket_inset > 0 && outer_h() - 2*lid_gasket_inset > 0, "lid gasket inset too large");
// keyholes fit the wider plate
assert(keyhole_spacing/2 + keyhole_head_d/2 + kb_pad <= outer_w()/2 - wall, "keyhole bosses run off the plate width");
assert(keyhole_spacing/2 - keyhole_head_d/2 - kb_pad > 0, "keyhole bosses overlap at center");
// TPA on the lid inner face lands inside the bay, doesn't foul the chamber
assert(board_cy()+tpa_pos[1] + tpa_l/2 < divider_cy() - divider_t/2, "TPA on lid breaches the chamber zone");
assert(abs(tpa_pos[0]) + tpa_w/2 <= outer_w()/2 - wall, "TPA on lid off the plate width");
```

Run: `./hardware/speaker-case/test.sh` → tune `keyhole_spacing` / `tpa_pos` until green.

- [ ] **Step 2: Edit `rear_plate.scad` — remove `module_clamp`, add `tpa_mount`**

Delete the `module_clamp()` module and its `if (mod_clamp) module_clamp();` call. Add this module:

```openscad
// TPA3116 amp mounts on the lid INNER face (standoffs toward the bay)
module tpa_mount() {
    translate([tpa_pos[0], board_cy()+tpa_pos[1], -board_standoff_h])
        mirror([0,0,1])
            board_standoffs(tpa_w, tpa_l, board_standoff_h, board_standoff_od, board_screw_pilot);
}
```

Change the `rear_plate()` union to call `tpa_mount();` instead of the clamp:

```openscad
module rear_plate() {
    difference() {
        union() {
            linear_extrude(wall) rounded_rect(outer_w(), outer_h(), radius);
            keyhole_bosses();
            tpa_mount();
        }
        // perimeter gasket groove on the inner (z=0) face
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
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -0.1])
                cylinder(h = wall + 0.2, d = screw_clear);
    }
}
```

Remove the now-unused `mod_*` params from `params.scad` (the `// ---- VoiceS3R module ----` and `// ---- module retention clamp ----` blocks and `mod_clamp_h()`), since no module/clamp exists anymore.

- [ ] **Step 3: Run the harness — expect PASS + rear renders**

Run: `./hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK rear`.

- [ ] **Step 4: Commit**

```bash
git add hardware/speaker-case/modules/rear_plate.scad hardware/speaker-case/modules/params.scad hardware/speaker-case/tests/asserts.scad
git commit -m "feat(speaker-case): rear lid — TPA mount, drop module clamp, resize keyholes"
```

---

## Task 6: Single-driver grille + dispatcher/build/test cleanup

**Files:**
- Modify: `hardware/speaker-case/modules/grille.scad` (single centered disc)
- Delete: `hardware/speaker-case/modules/button_cap.scad`
- Modify: `hardware/speaker-case/speaker-case.scad` (drop `"button"`)
- Modify: `hardware/speaker-case/build.sh` and `test.sh` (drop `button` from the loop)

- [ ] **Step 1: Rewrite `grille.scad` for one centered driver**

Replace the `grille_cover()` module body's `for` loop with a single placement:

```openscad
module grille_cover() {
    translate([spk_cx(), spk_cy(), 0]) {
        difference() {
            cylinder(h = grille_face_t, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
            translate([0, 0, -0.1]) linear_extrude(grille_face_t + 0.2) grille(spk_cut);
        }
        translate([0, 0, -grille_skirt_h])
            difference() {
                cylinder(h = grille_skirt_h, d = spk_od + 2*seat_wall + 2*grille_skirt_t);
                translate([0, 0, -0.1])
                    cylinder(h = grille_skirt_h + 0.2, d = spk_od + 2*seat_wall + 2*clr);
            }
    }
}
```

- [ ] **Step 2: Delete the obsolete captive button and drop it from the dispatcher**

Run: `git rm hardware/speaker-case/modules/button_cap.scad`

Edit `speaker-case.scad`: remove the `include <modules/button_cap.scad>` line, remove the `else if (part == "button") button_cap();` line, and remove the `color("red") ... button_cap();` line from the assembled preview.

- [ ] **Step 3: Drop `button` from the part loops**

In both `build.sh` and `test.sh`, change `for part in body rear button grille; do` to `for part in body rear grille; do`.

- [ ] **Step 4: Run the harness — expect PASS with no `button`**

Run: `./hardware/speaker-case/test.sh`
Expected: `OK asserts`, `OK body`, `OK rear`, `OK grille` — and no `button` line.

- [ ] **Step 5: Commit**

```bash
git add -A hardware/speaker-case/
git commit -m "feat(speaker-case): single-driver grille; drop captive button (panel-mount switch)"
```

---

## Task 7: Full render, volume verification, and README

**Files:**
- Modify: `hardware/speaker-case/README.md`
- Generate: `hardware/speaker-case/stl/*.stl`

- [ ] **Step 1: Render all parts and confirm sizes**

Run: `./hardware/speaker-case/build.sh`
Expected: `rendering body ...`, `rear`, `grille`, `done -> stl/`, with each STL well over 1000 B.

- [ ] **Step 2: Verify the net volume meets the floor (echo the value)**

Run:
```bash
/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD -D 'part="body"' \
  --hardwarnings -o /tmp/vol.echo hardware/speaker-case/speaker-case.scad 2>&1 | true
echo 'echo(net_vol_L=( (158-8)*103*110 - 60000 - 40000 )/1e6);' > /tmp/vol.scad
/Applications/OpenSCAD-2021.01.app/Contents/MacOS/OpenSCAD -o /tmp/vol.stl /tmp/vol.scad 2>&1 | grep net_vol_L
```
Expected: `ECHO: net_vol_L = 1.5995` (≥ 1.4 L target). The asserts already guard this; this step is a human-readable confirmation.

- [ ] **Step 3: Rewrite `README.md` to the new design**

Replace the README body with a description matching this plan: single PS95-8 on the front baffle, side-mounted PR, sealed chamber + vented bay split by a divider with one sealed wire pass, the five-board stack (S3 / PCM5102 / TPA3116-on-lid / MP1584 / CH224K), PTT panel-mount switch, ICS-43434 mic + front perforation, USB-C power IN. Document the wiring map (from this plan's header) and the print/assembly notes from `docs/superpowers/specs/2026-06-13-speaker-case-hardware-design.md` (print chamber airtight ≥4 perimeters, foam gaskets under driver/PR/lid, polyfill in the chamber only, side-PR tuning mass for Fb ~75 Hz).

- [ ] **Step 4: Commit the STLs + README**

```bash
git add hardware/speaker-case/stl hardware/speaker-case/README.md
git commit -m "feat(speaker-case): render PR-loaded enclosure STLs; update README"
```

---

## Self-Review Notes (gaps to watch during execution)

- **Board packing (Task 3/4)** is the only step likely to need real iteration — the no-overlap asserts are the guide; nudge `*_pos` until green. If the five front-baffle boards genuinely don't fit, the fallback is moving the DAC or buck onto the lid alongside the TPA (add a second `*_mount` in `rear_plate.scad` and a matching lid-side assert), or growing `board_zone_h` by 6–10 mm (re-confirm `outer_h` and the wall-mount load).
- **`[confirm vs hardware]` dims** (PS95-8 frame/cutout/bolt-circle/depth, PR dims, board footprints, USB-C receptacle depth, switch thread) must be measured against parts in hand before printing; the asserts enforce *fit*, not absolute correctness.
- **Spec coverage:** single driver ✓ (T1), ~1.5 L volume ✓ (T1 + T7), side PR ✓ (T2), five-board bay + wiring passes ✓ (T3/T4), USB-C power in ✓ (T4), mic + PTT ✓ (T4), heavier-box wall mount ✓ (T5 keyholes). The geometry spec regeneration called for in the hardware spec is satisfied by this enclosure plan.
