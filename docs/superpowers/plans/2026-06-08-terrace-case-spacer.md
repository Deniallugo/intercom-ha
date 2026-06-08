# Terrace Case Depth-Spacer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a parametric, drop-in OpenSCAD spacer ring that inserts at the terrace case's front-shell ↔ rear-plate parting line and adds 20 mm of air volume behind the drivers, with no change to the existing parts.

**Architecture:** New `modules/spacer.scad` part renders a rounded-rect picture-frame (hollow center = added air) with a registration spigot that nests in the front shell's rear opening and 4 corner pads that pass longer M3 screws through to the existing front bosses. New params live in `params.scad`; relationship checks go in `tests/asserts.scad`; render smoke goes through `test.sh` like every other part.

**Tech Stack:** OpenSCAD (parametric SCAD modules), bash render/test scripts. No runtime code — "tests" are `assert()` relationship checks + STL render-size smoke checks.

---

## File Structure

- `hardware/terrace-case/modules/params.scad` — add `spacer_t`, `spigot_h`, `spigot_wall` (Task 1).
- `hardware/terrace-case/tests/asserts.scad` — add spacer relationship asserts (Task 1).
- `hardware/terrace-case/modules/spacer.scad` — **new**, the `spacer()` module + sub-modules (Task 2).
- `hardware/terrace-case/terrace-case.scad` — include spacer, add `part="spacer"`, insert into the `"all"` preview (Task 2).
- `hardware/terrace-case/build.sh` — add `spacer` to the render loop (Task 2).
- `hardware/terrace-case/test.sh` — add `spacer` to the render loop (Task 2).
- `hardware/terrace-case/README.md` — spacer section: purpose, print, BOM, foam-tape seal (Task 3).
- `docs/DEVICES.md` — one-line note that the terrace case takes an optional +20 mm spacer + longer screws (Task 3).

All commands below assume the working directory `hardware/terrace-case/` unless an absolute path is shown. The test runner is `./test.sh` (set `$OPENSCAD` if OpenSCAD isn't on `PATH`).

---

## Task 1: Spacer parameters

**Files:**
- Modify: `hardware/terrace-case/tests/asserts.scad` (append before the smoke-render block)
- Modify: `hardware/terrace-case/modules/params.scad` (append a new section)

- [ ] **Step 1: Write the failing asserts**

In `tests/asserts.scad`, insert this block immediately **before** the
`// helper render smoke` comment line:

```scad
// ---- depth spacer ----
assert(spacer_t > 0, "spacer_t must be positive");
assert(spigot_h > 0 && spigot_h < spacer_t, "spigot must be positive and shorter than the spacer body");
assert(spigot_wall > 0 && spigot_wall <= wall, "spigot wall must be positive and not exceed the shell wall");
// spigot lip nests inside the front shell's rear opening (with clearance both sides)
assert(outer_w() - 2*wall - 2*clr - 2*spigot_wall > 0, "spigot lip must fit inside the front cavity");
// spacer body must be shorter than the front boss depth so the existing screws still reach a boss to bite
assert(spacer_t < front_depth - wall, "spacer_t must be less than the front boss depth (front_depth - wall) so screws still engage");
```

- [ ] **Step 2: Run the asserts to verify they fail**

Run: `./test.sh`
Expected: `FAIL asserts` (OpenSCAD errors with `WARNING: Ignoring unknown variable 'spacer_t'` / unknown-variable hard-warning), and the script exits non-zero.

- [ ] **Step 3: Add the params**

Append to `modules/params.scad` (after the `// ---- screws (M3) ----` block, before the `// ---- derived ----`/`function` lines if present; otherwise at the end of the parameter section):

```scad
// ---- depth spacer (optional insert at the front<->rear parting line) ----
// A picture-frame ring that adds air behind the drivers without reprinting the
// front shell or rear plate. See docs/superpowers/specs/2026-06-08-terrace-case-spacer-design.md
spacer_t    = 20;          // added depth = extra clear air behind the cones
spigot_h    = 4;           // registration lip height nesting into the front cavity
spigot_wall = 1.6;         // registration lip thickness
```

- [ ] **Step 4: Run the asserts to verify they pass**

Run: `./test.sh`
Expected: `OK asserts` line present. (Other parts still render `OK`.)

- [ ] **Step 5: Commit**

```bash
cd /Users/danillugovskoy/own/intercom
git add hardware/terrace-case/modules/params.scad hardware/terrace-case/tests/asserts.scad
git commit -m "feat(terrace-case): add depth-spacer parameters + asserts"
```

---

## Task 2: Spacer geometry + wiring

**Files:**
- Create: `hardware/terrace-case/modules/spacer.scad`
- Modify: `hardware/terrace-case/terrace-case.scad`
- Modify: `hardware/terrace-case/build.sh:7` (the `for part in ...` loop)
- Modify: `hardware/terrace-case/test.sh:14` (the `for part in ...` loop)

- [ ] **Step 1: Add `spacer` to the test render loop (failing render)**

In `test.sh`, change the render loop line:

```bash
for part in front rear button coupon; do
```

to:

```bash
for part in front rear button coupon spacer; do
```

- [ ] **Step 2: Run to verify the spacer render fails**

Run: `./test.sh`
Expected: `FAIL spacer render:` — terrace-case.scad does not yet handle `part="spacer"` (renders empty / errors), so the STL is missing or under 1000 B.

- [ ] **Step 3: Create the spacer module**

Create `hardware/terrace-case/modules/spacer.scad` with exactly:

```scad
// ===== depth spacer ring (no top-level geometry) =====
// A picture-frame inserted at the front-shell <-> rear-plate parting line to
// add `spacer_t` of air behind the drivers. No change to the front shell or
// rear plate: 4 corner pads pass the (longer) M3 screws straight through to the
// existing front bosses, and a registration spigot nests in the front shell's
// rear opening. Local coords: frame body z in [0, spacer_t]; spigot in
// [-spigot_h, 0] (points toward the front shell).

// hollow perimeter frame — the added air volume
module spacer_frame() {
    linear_extrude(spacer_t)
        difference() {
            rounded_rect(outer_w(), outer_h(), radius);
            rounded_rect(outer_w() - 2*wall, outer_h() - 2*wall, max(0.5, radius - wall));
        }
}

// solid corner pad merging into the frame, sized to contain the boss XY; the
// screw clearance hole is drilled later. Clamps onto the front boss top.
module spacer_corner_pad(sx, sy) {
    pad = 2*boss_inset + boss_od;   // square pad spanning the corner inward past the boss
    intersection() {
        linear_extrude(spacer_t) rounded_rect(outer_w(), outer_h(), radius);
        translate([sx*(outer_w()/2 - pad/2), sy*(outer_h()/2 - pad/2), 0])
            linear_extrude(spacer_t) square(pad, center = true);
    }
}

// registration lip nesting inside the front shell's rear opening, along all
// four edges; the four corners are relieved so the lip clears the front bosses.
module spacer_spigot() {
    lip_ow = outer_w() - 2*wall - 2*clr;
    lip_oh = outer_h() - 2*wall - 2*clr;
    ir     = max(0.5, radius - wall - clr);
    difference() {
        translate([0, 0, -spigot_h]) linear_extrude(spigot_h)
            difference() {
                rounded_rect(lip_ow, lip_oh, ir);
                rounded_rect(lip_ow - 2*spigot_wall, lip_oh - 2*spigot_wall, max(0.5, ir - spigot_wall));
            }
        // corner relief: clear the front shell's corner bosses
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -spigot_h - 0.1])
                cylinder(h = spigot_h + 0.2, d = boss_od + 2*clr);
    }
}

module spacer() {
    difference() {
        union() {
            spacer_frame();
            for (sx = [-1, 1], sy = [-1, 1]) spacer_corner_pad(sx, sy);
            spacer_spigot();
        }
        // M3 clearance holes through the corner pads (and the full spigot range)
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx*(outer_w()/2 - boss_inset), sy*(outer_h()/2 - boss_inset), -spigot_h - 0.1])
                cylinder(h = spacer_t + spigot_h + 0.2, d = screw_clear);
    }
}
```

- [ ] **Step 4: Wire the spacer into the render entry point**

In `terrace-case.scad`, add the include alongside the others (after the
`include <modules/rear_plate.scad>` line):

```scad
include <modules/spacer.scad>
```

Add the part branch — insert after the `else if (part == "button") ...` line and
before the `else if (part == "coupon") ...` line:

```scad
else if (part == "spacer") spacer();
```

Replace the assembled-preview `else { ... }` block with one that includes the
spacer and pushes the rear plate back by `spacer_t`:

```scad
else {  // assembled preview
    front_shell();
    color("lightblue") translate([0, 0, front_depth]) spacer();
    color("gray")      translate([0, 0, front_depth + spacer_t]) rear_plate();
    color("red")       translate([cradle_cx(), board_cy(), -3]) button_cap();
}
```

- [ ] **Step 5: Add `spacer` to the build render loop**

In `build.sh`, change:

```bash
for part in front rear button; do
```

to:

```bash
for part in front rear button spacer; do
```

- [ ] **Step 6: Run the full test suite to verify the spacer renders**

Run: `./test.sh`
Expected: `OK asserts`, `OK front`, `OK rear`, `OK button`, `OK coupon`, and
`OK spacer (<N> B)` with N ≥ 1000. Script exits 0.

- [ ] **Step 7: Eyeball the assembled preview (optional but recommended)**

Run: `${OPENSCAD:-openscad} -D 'part="all"' -o /tmp/tc_all.stl terrace-case.scad`
Expected: renders without warnings; opening it shows the spacer (light blue)
seated between the front shell and the rear plate, with the rear plate stood off
by 20 mm and the 4 screw columns lining up at the corners.

- [ ] **Step 8: Commit**

```bash
cd /Users/danillugovskoy/own/intercom
git add hardware/terrace-case/modules/spacer.scad hardware/terrace-case/terrace-case.scad hardware/terrace-case/build.sh hardware/terrace-case/test.sh
git commit -m "feat(terrace-case): depth-spacer ring part (+20mm air behind drivers)"
```

---

## Task 3: Docs

**Files:**
- Modify: `hardware/terrace-case/README.md` (add a spacer section)
- Modify: `docs/DEVICES.md` (one-line note)

- [ ] **Step 1: Add the README spacer section**

Append to `hardware/terrace-case/README.md`:

```markdown
## Optional depth spacer

If the assembled case sounds constrained/boxy with the rear closed, the drivers
are starved for air (~8 mm behind each cone). The **spacer** part is a drop-in
picture-frame ring that inserts at the front-shell ↔ rear-plate parting line and
adds `spacer_t` (default **20 mm**) of sealed air volume behind the drivers — no
reprint of the front shell or rear plate.

Render/print it like any other part:

    openscad -o stl/spacer.stl -D 'part="spacer"' terrace-case.scad

Print flat (frame face down), no supports, same settings as the shell (0.2 mm
layers, ≥4 perimeters, 20–30 % infill).

**Assembly (front shell → spacer → rear plate):**

1. Seat the spacer on the front shell — its spigot lip nests into the shell's
   rear opening; the 4 corner pads land on the existing front bosses.
2. Foam/EVA tape on **both** seams (front↔spacer and spacer↔rear). Plastic faces
   are not airtight and this is a sealed box — skipping this re-introduces leaks.
3. Fit the rear plate and fasten with **4× M3×35 self-tapping screws** (replacing
   the short ones) — they span the rear plate + spacer and bite into the front
   bosses. M3×30 also works (~7 mm engagement).

The USB-C exit (front shell bottom wall) and keyhole wall-mount (rear plate) are
unchanged; the case simply stands `spacer_t` further off the wall. Tune
`spacer_t` in `modules/params.scad` and reprint just the spacer to taste.
```

- [ ] **Step 2: Add the DEVICES.md note**

In `docs/DEVICES.md`, in the Terrace device section, add a one-line note under
the External speakers row context (after the table is fine). Add this line at
the end of the Terrace subsection's prose, before the `---`:

```markdown
> The terrace 3D-printed case accepts an optional **+20 mm depth spacer**
> (`part="spacer"`) at the rear parting line to give the drivers more sealed air
> volume; it needs 4× M3×35 screws and foam tape on the two new seams. See
> `hardware/terrace-case/README.md`.
```

- [ ] **Step 3: Commit**

```bash
cd /Users/danillugovskoy/own/intercom
git add hardware/terrace-case/README.md docs/DEVICES.md
git commit -m "docs(terrace-case): document the optional depth spacer"
```

---

## Self-Review notes

- **Spec coverage:** spacer_t=20 default (Task 1) ✓; picture-frame + hollow center (Task 2 `spacer_frame`) ✓; registration spigot along edges with corner relief (Task 2 `spacer_spigot`) ✓; 4 corner pads passing screws to existing front bosses (Task 2 `spacer_corner_pad` + hole) ✓; no front/rear geometry change (only `terrace-case.scad` selector + preview touched) ✓; longer M3×35 screws + foam-tape seal (Task 3 README/BOM) ✓; USB/keyhole unaffected (no edits to those modules) ✓; wired into build.sh + test.sh + part selector (Task 2) ✓.
- **Placeholder scan:** none — all SCAD and bash edits are shown in full.
- **Type/name consistency:** `spacer_t`, `spigot_h`, `spigot_wall` defined in Task 1 and used identically in Task 2; module names `spacer()`, `spacer_frame()`, `spacer_corner_pad()`, `spacer_spigot()` consistent; reuses existing `outer_w()/outer_h()/radius/wall/clr/boss_inset/boss_od/screw_clear` verbatim from params.
