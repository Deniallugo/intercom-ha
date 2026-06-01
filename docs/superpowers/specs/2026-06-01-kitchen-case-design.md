# Kitchen Atom Echo Enclosure — Design

**Date:** 2026-06-01
**Status:** Design — pending implementation
**Device:** Kitchen M5Stack Atom Echo (`devices/atom-echo.yaml`)

A wall-mounted, 3D-printable enclosure for the kitchen intercom: the classic
M5Stack **Atom Echo** module, **one** MAX98357A amp breakout, and **one** 2"
external speaker driver. A faithful fork of the terrace case
([2026-05-31-terrace-case-design.md](2026-05-31-terrace-case-design.md)),
reduced to a single speaker and a single amp and re-cradled for the classic
Atom Echo. Authored as parametric OpenSCAD so the model is version-controlled,
diffable, and re-renderable from source.

## Goal

Produce a serviceable wall enclosure that:

- Mounts **one** 2" (50 mm face, 35 mm deep) full-range driver, centered.
- Houses the classic Atom Echo module (top face forward) and **one** MAX98357A
  amp board in the strip below the driver.
- Exposes the Atom Echo's built-in PTT button through a captive printed plunger
  that presses solidly.
- Gives the module's microphone a clear acoustic path to outside air, isolated
  from internal speaker noise.
- Keeps the USB-C port reachable for power and re-flashing without opening the
  case.
- Splits front/rear so the rear plate stays on the wall and the body lifts off
  for servicing.

## Context

- Device docs: [docs/DEVICES.md](../../DEVICES.md) — kitchen Atom Echo section.
- Amp/wiring: the kitchen louder-amp design
  ([2026-06-01-kitchen-atom-echo-louder-amp-design.md](2026-06-01-kitchen-atom-echo-louder-amp-design.md))
  adds one MAX98357A as a passive parallel I²S listener at the Atom Echo's
  header pads (BCLK G19, LRCLK G33, DIN G22, +5V/GND), GAIN→GND = +12 dB,
  driving one bigger 4 Ω driver. This enclosure houses exactly that combo.
- Prior CAD: `hardware/terrace-case` — the two-speaker/two-amp VoiceS3R case
  this design forks from.

## Why fork (not share a library)

Per the locked decision, the kitchen case is a **new `hardware/kitchen-case`
directory** copied from the terrace structure and adapted. It is independent
and simple to reason about, at the cost of a duplicated `lib.scad`. (Sharing a
common library across both cases was considered and declined — the small
duplication is worth the decoupling.)

## Decisions (locked)

| Topic | Decision |
|---|---|
| Target hardware | Kitchen classic Atom Echo + 1× MAX98357A + 1× 2" driver |
| Deliverable | Parametric OpenSCAD source → STL via CLI |
| Code layout | New `hardware/kitchen-case` (fork of terrace-case); own `lib.scad` |
| Mounting | Wall-mount (keyhole slots on rear plate), same as terrace |
| Speaker driver | 2" — 50 mm face dia, 35 mm deep, ≈44 mm grille field (same as terrace) |
| Speaker layout | **One** driver, centered |
| Amp boards | **One** (MAX98357A) |
| Weather | Indoor (kitchen) — no weatherproofing needed |
| Architecture | Two-part clamshell: front shell + rear wall plate, 4× M3 screws |
| Button | Captive printed plunger cap over the module's top-face button |
| Microphone | Perforation cluster (center + ring) through the front wall |
| Mic placement | Under the button, over the module's top-face mic |
| STL files | Gitignored (regenerable from source) |
| Envelope | ~80 × 95 × 50 mm (narrower than terrace; single driver) |

## Module orientation

The classic Atom Echo carries **both** its PTT button (G39) and its PDM mic on
its **top face**. The module is cradled **top-face-forward** — the same trick
the terrace case uses with the VoiceS3R — so the plunger presses the button and
the mic perforation opens onto the mic right beside it through the front wall.

## Architecture

Two printed parts plus one small printed plunger:

1. **Front shell** — the visible body. Carries one centered speaker recess ring
   + grille + bolt-circle screw bosses + gasket groove, the button well, the
   mic perforation (under the button), the Atom Echo cradle, **one**
   amp-board screw standoff, and the corner screw bosses.
2. **Rear plate** — sits flush on the wall. Carries two keyhole mounting slots,
   the USB-C cable notch at the bottom edge, and the mating screw bosses.
3. **Button cap** — a captive plunger that drops into the front-shell button
   well and presses the module's top-face button.

The two halves join with **4× M3 screws** (corners), self-tapping into printed
bosses by default. Parting line runs around the perimeter; the front shell
holds the deeper (~38 mm) speaker zone, the rear plate is shallow (~12 mm).

### Layout (front view)

```
   ┌────────────────────────┐
   │      ·· ╭─────╮ ··      │
   │     ·   │ spkr │   ·    │   ← one 2" driver, centered
   │      ·· │      │ ··     │
   │         ╰─────╯         │
   │   [AtomEcho▢]  [amp]    │   ← module + single amp board, below the driver
   │      [btn]/(∴)          │   ← button + mic perforation under it
   └───────────┬────────────┘     (both over the module top face)
           USB-C notch (bottom edge)
```

## Components

### Front shell (`modules/front_shell.scad`)
- Rounded rectangular outer wall, 2.4 mm thick, 6 mm corner radius.
- **One** centered speaker recess ring (OD 50 mm seat, 44 mm grille field).
  Driver fastened by `spk_screw_n` (default 4) M2 self-tap screws through the
  driver flange into printed bolt-circle bosses (`spk_bolt_circle`, default
  56 mm — must clear the driver OD), start angle `spk_screw_a0` (45°).
- One circular grille (concentric rings of 3 mm holes) over the cutout.
- A gasket groove in the baffle under the driver flange
  (`gasket_id`..`gasket_od`, `gasket_depth` deep) seats a foam/EVA ring so the
  flange seals the front wave from the back wave.
- Atom Echo cradle: 3-wall pocket sized to the module footprint
  (`mod_w` + `clr`), centered with the single amp board flanking one side;
  module oriented top-face-forward; USB-C edge cutout toward the bottom; a side
  window for header wires to reach the amp.
- Button well guiding the plunger, with a retaining shoulder. The bore goes
  through the front wall **and** the cradle floor behind it, so the plunger nub
  can reach the module's button.
- Mic perforation: a cluster of small holes (one center + a ring of
  `mic_ring_n`, default 6) through the front wall **and** the cradle floor,
  centered `mic_below_btn` from the button so they open into the pocket at the
  module's mic. No boss needed.
- **One** amp-board standoff set with M2 self-tap pilots so the board screws
  down.
- 4× corner screw bosses (front side).

### Rear plate (`modules/rear_plate.scad`)
- Flat plate matching the shell footprint, 2.4 mm thick.
- Two keyhole slots, default 70 mm apart (parametric — scaled to the narrower
  kitchen footprint), sized for common screw heads.
- USB-C cable notch at the bottom edge.
- 4× mating screw bosses (self-tapping or insert-ready).

### Button cap (`modules/button_cap.scad`)
- Captive plunger: face disc (~12 mm dia, slightly proud), skirt with a
  retention lip catching behind the well wall, underside nub landing on the
  module button. ~1.5–2 mm travel; module switch provides return spring.

### Shared library (`modules/lib.scad`)
- Helpers copied from terrace-case: rounded box, grille hole pattern, keyhole
  slot, screw boss.

## Parametric structure

Parameters live in `modules/params.scad`; `kitchen-case.scad` includes them and
exposes a `part` selector (a normal variable overridden by `-D part="..."`):

- `part` ∈ `"front"` | `"rear"` | `"button"` | `"coupon"` (fit-test) |
  `"all"` (assembled preview).
- All dimensions are named variables: outer W/H/D, wall thickness, corner
  radius, speaker OD/cutout, driver retention, grille hole dia/spacing, module
  cradle size + clearance, USB-C notch position/size, button well + cap dims,
  mic perforation offset + hole/ring dims, amp board size + standoff height +
  amp screw pilot, speaker bolt-circle + screw count + start angle + boss dims,
  keyhole spacing, screw boss dia + M3 pilot, global fit clearance
  (default 0.4 mm).
- Single-driver and single-amp counts are baked into the shell geometry; there
  is no `spk_gap` (only one driver) and one amp standoff (not two).

## Build & file layout

```
hardware/kitchen-case/
├── kitchen-case.scad      # includes params + part render selector
├── modules/
│   ├── front_shell.scad
│   ├── rear_plate.scad
│   ├── button_cap.scad
│   └── lib.scad
├── build.sh               # openscad CLI → exports each part to stl/
├── test.sh                # asserts + clean-render check per part
├── tests/
│   └── asserts.scad
├── stl/                   # generated meshes (gitignored)
├── .gitignore             # ignores stl/
└── README.md              # parameters, print settings, BOM, assembly
```

`build.sh` loops the parts and runs, per part:

```
openscad -o stl/<part>.stl -D 'part="<part>"' kitchen-case.scad
```

## Print orientation & settings (documented in README)

- Front shell: grille face down — grille and front surface print without
  supports.
- Rear plate: flat.
- Button cap: face down, small.
- Suggested: 0.2 mm layers, ≥4 perimeters, 20–30 % infill. Indoor location;
  material is the user's choice.

## Verification (physical)

Ship a **fit-test coupon** target (`part="coupon"`) containing just:
- the speaker recess ring,
- the Atom Echo cradle + USB-C notch,
- the button well + a button cap,
- the mic perforation.

Print the coupon first (~10 min) to validate tolerances (cradle fit, button
travel, screw-boss pilot, speaker seat) before printing the full shell. The
README documents which parameters to nudge for a loose/tight fit.

## Out of scope

- The amp wiring itself and disconnecting the internal 0.5 W speaker — covered
  by the louder-amp design
  ([2026-06-01-kitchen-atom-echo-louder-amp-design.md](2026-06-01-kitchen-atom-echo-louder-amp-design.md)).
- Any firmware/YAML change — this is hardware only.
- Music streaming / media-player features (the kitchen device stays
  announcement + PTT only).
- Sharing a CAD library with the terrace case (forked instead).

## Open items requiring physical measurement before final print

These have sensible defaults but must be confirmed against the actual hardware:
- Atom Echo cradle dimensions (`mod_w`/`mod_d`/`mod_h`) and **USB-C port
  position/orientation** — differs from the VoiceS3R.
- Mic offset below the button (`mic_below_btn`) to land on the module mic.
- Exact driver OD, cutout dia, and mounting-hole (bolt-circle) pattern.
- MAX98357A breakout footprint (clone dimensions vary).
- Module button center position relative to the front face.
