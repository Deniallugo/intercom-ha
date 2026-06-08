# Terrace VoiceS3R Enclosure — Depth Spacer Ring

A drop-in spacer ring that adds internal air volume behind the two 2" drivers
in the terrace case, **without reprinting the front shell or rear plate**.

## Problem

The assembled case sounds constrained/boxy with the bottom (rear) closed, and
opens up when left ajar. Root cause: the drivers are starved for air. Each
driver is 35 mm deep in a `front_depth = 38 + 5 = 43 mm` cavity, leaving only
**~8 mm of clear air behind each cone**. Two drivers share that small sealed
volume, so the air spring is extremely stiff — high effective Qtc, a boomy/honky
midbass hump, suppressed output. Opening the rear relieves that air spring,
which is why it sounds better ajar.

Leaving the rear open is not a real fix: an untuned opening makes it a
leaky/dipole box (back wave partially cancels the front wave, response becomes
uncontrolled and position-dependent). The correct fix is **more sealed volume —
specifically more depth behind the cones.**

## Goal

Add a parametric spacer part to the existing OpenSCAD project that:

- Inserts at the existing front-shell ↔ rear-plate parting line.
- Adds **20 mm** of depth (default), taking the air behind each cone from
  ~8 → ~28 mm (~4× the sealed volume, still well under the driver's Vas).
- Requires **no change to the front shell or rear plate geometry** — only a new
  part, a few params, longer screws, and foam tape on the new seams.
- Leaves the USB-C exit (front shell bottom wall) and keyhole wall-mount (rear
  plate) functionally unchanged; the case simply stands 20 mm further off the
  wall.

## Decisions (locked)

| Topic | Decision |
|---|---|
| Added depth | `spacer_t = 20 mm` (parametric; reprint at any value) |
| Form | Rounded-rect picture-frame: `outer_w × outer_h`, `radius`, perimeter wall = `wall` (2.4 mm), hollow center = added air |
| Mounting | Pass-through: 4× longer M3 self-tap screws span rear plate → spacer corner pillars → into the **existing** front-shell corner bosses |
| Registration | Short spigot lip (~4 mm) on the spacer's front face nests inside the front shell's rear opening, along the four straight edges (corners left open for the front bosses) |
| Sealing | Thin foam/EVA tape on both new seams (front↔spacer, spacer↔rear) — plastic faces are not airtight, and this is a sealed box |
| Front shell / rear plate | Unchanged |
| Screws | 4× M3 self-tapping, ~35 mm (≥ 33 mm) replacing the current short ones |

## Architecture

The clamshell becomes a three-part stack at the same parting line:

```
front shell (cup, drivers)  →  SPACER (frame, +20 mm air)  →  rear plate (lid)
        z=0 .. front_depth        front_depth .. +spacer_t       flat wall lid
```

New part `part="spacer"`, rendered by a new `modules/spacer.scad`, wired into
`terrace-case.scad` and `build.sh` alongside `front`/`rear`/`button`.

### Spacer geometry (`modules/spacer.scad`)

In spacer-local coordinates (base at z = 0, growing +z toward the rear plate):

1. **Perimeter frame** — `rounded_rect(outer_w(), outer_h(), radius)` extruded
   `spacer_t`, minus the inner `rounded_rect(outer_w()-2*wall, outer_h()-2*wall,
   max(0.5, radius-wall))` through its full height. Same wall profile as
   `shell_body`, open on both faces. This hollow is the added air volume.
2. **Registration spigot** — a lip protruding from the front face (-z) by
   `spigot_h` (~4 mm), sized to slide inside the front shell's rear cavity
   (`outer_w()-2*wall-2*clr` across, `spigot_wall` ≈ 1.6 mm thick). Runs only
   along the four **straight edge segments**; the four corners are left open so
   the lip never collides with the front shell's corner bosses. Positive XY
   registration on all four sides + a longer leak path at the front seam.
3. **Corner pillars** — 4 columns (`boss_od`) at the same XY as the front
   bosses (`±(outer_w()/2 - boss_inset)`, `±(outer_h()/2 - boss_inset)`), full
   `spacer_t` tall, each with a `screw_clear` (3.4 mm) through-hole. Their bottom
   faces land flat on top of the existing front bosses (which top out at
   `z = front_depth`), transmitting clamp load. Small gussets/webs tie each
   pillar into the perimeter frame.

The rear plate is unchanged: its clearance holes already align to the same
corner XY, so screws drop rear plate → pillar → front boss in one line.

### Screw path & length

`wall` (rear plate, 2.4) + `spacer_t` (pillar, 20) = 22.4 mm consumed before the
screw reaches the front boss top. An **M3×35** self-tapper then engages ~12 mm
into the front boss (40 mm of full-depth `screw_pilot` available) — ample.
M3×30 (~7 mm engagement) also works. BOM/README specify M3×35.

## Parameters (new, in `modules/params.scad`)

| Param | Default | Meaning |
|---|---|---|
| `spacer_t` | 20 | Added depth = extra air behind the cones |
| `spigot_h` | 4 | Registration lip height into the front cavity |
| `spigot_wall` | 1.6 | Registration lip thickness |

All other dimensions reuse existing params (`outer_w()`, `outer_h()`, `radius`,
`wall`, `clr`, `boss_inset`, `boss_od`, `screw_clear`).

## Wiring into the project

- `terrace-case.scad` — `include <modules/spacer.scad>`; add
  `else if (part == "spacer") spacer();`; in the `"all"` preview insert the
  spacer between front and rear and push the rear plate back by `spacer_t`
  (`translate([0,0,front_depth]) spacer();` then
  `translate([0,0,front_depth+spacer_t]) rear_plate();`).
- `build.sh` — add `spacer` to the render loop.
- `README.md` — new spacer section: purpose, print flat (no supports), BOM note
  (4× M3×35 self-tap replacing the short screws), and the foam-tape seal note on
  both seams. Note the case now stands `spacer_t` further off the wall.

## Print orientation & settings

- Spacer: print flat (frame face down). No supports. Same profile as the rest:
  0.2 mm layers, ≥4 perimeters, 20–30 % infill.

## Verification (physical)

- Test-fit the spacer between the printed front shell and rear plate: spigot
  nests, corner pillars land on the front bosses, M3×35 screws bite.
- Apply foam tape to both seams, reassemble, and confirm sealed playback no
  longer sounds constrained vs. the previous ajar test.

## Out of scope

- Any change to the front shell or rear plate geometry.
- A tuned port / vented alignment (this keeps the box **sealed**, just larger).
- Internal damping liner changes (`sound_iso` already allows for a liner;
  unchanged here).
- Firmware/YAML — hardware only.

## Open items (confirm against hardware)

- Final foam-tape thickness vs. seam clearance (affects total screw length by a
  hair).
- Whether a single +20 mm reprint is enough by ear, or `spacer_t` wants a tweak
  (it's parametric for exactly this reason).
