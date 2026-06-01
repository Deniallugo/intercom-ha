# Terrace VoiceS3R Enclosure — Design

A wall-mounted, 3D-printable enclosure for the terrace intercom combo: the
M5Stack ATOM Echo S3R (VoiceS3R) module, two MAX98357A amp breakouts, and
two 2" external speaker drivers. Authored as parametric OpenSCAD so the model
is version-controlled, diffable, and re-renderable from source.

## Goal

Produce a serviceable, sheltered-outdoor wall enclosure that:

- Mounts two 2" (50 mm face, 35 mm deep) full-range drivers side by side as a horizontal
  pair, near-touching (driven dual mono — both play the same mix).
- Houses the VoiceS3R module (button facing forward) and two MAX98357A amp
  boards in the strip below the drivers.
- Exposes the VoiceS3R's built-in PTT button through a captive printed plunger
  that presses solidly.
- Gives the module's microphone a clear acoustic path to outside air, isolated
  from internal speaker noise.
- Keeps the USB-C port reachable for power and re-flashing without opening the
  case.
- Splits front/rear so the rear plate stays on the wall and the body lifts off
  for servicing.

## Context

- Device docs: [docs/DEVICES.md](../../DEVICES.md) — terrace VoiceS3R section.
- Firmware: [devices/intercom-s3.yaml](../../../devices/intercom-s3.yaml).
  The speaker block drives `2× MAX98357A` as dual mono (`channel: mono`, both
  amps in the same slot), which this two-driver enclosure matches.
- The kitchen Atom Echo already has a working case and is out of scope.
- No prior CAD exists in the repo; this is a clean start.

## Decisions (locked)

| Topic | Decision |
|---|---|
| Target hardware | Terrace VoiceS3R + 2× MAX98357A + 2× 2" drivers |
| Deliverable | Parametric OpenSCAD source → STL via CLI |
| Mounting | Wall-mount (keyhole slots on rear plate) |
| Speaker driver | 2" — 50 mm face dia, 35 mm deep, ≈44 mm grille field |
| Speaker layout | Side by side (horizontal pair, dual mono), ~3 mm center gap |
| Amp boards | Two (one per speaker) |
| Weather | Covered/sheltered — no gland/gasket weatherproofing; just avoid upward openings |
| Architecture | Two-part clamshell: front shell + rear wall plate, 4× M3 screws |
| Button | Captive printed plunger cap over module's PTT button |
| Microphone | Perforation cluster (7 small holes) through the front wall |
| Mic placement | Directly under the button, over the module's own mic |
| STL files | Gitignored (regenerable from source) |
| Envelope | ~117 × 95 × 50 mm |

## Architecture

Two printed parts plus one small printed plunger:

1. **Front shell** — the visible body. Carries the two speaker recess rings +
   grilles + per-driver bolt-circle screw bosses, the button well, the mic
   perforation (under the button), the VoiceS3R cradle, amp-board screw
   standoffs, and the corner screw bosses.
2. **Rear plate** — sits flush on the wall. Carries two keyhole mounting slots,
   the USB-C cable notch at the bottom edge, and the mating screw bosses.
3. **Button cap** — a captive plunger that drops into the front-shell button
   well and presses the module's tactile switch.

The two halves join with **4× M3 screws** (corners), self-tapping into printed
bosses by default. Parting line runs around the perimeter; the front shell
holds the deeper (~38 mm) speaker zone, the rear plate is shallow (~12 mm).

### Layout (front view, landscape)

```
   ┌──────────────────────────────────┐
   │  ·· ╭─────╮ ··  ·· ╭─────╮ ··      │
   │ ·  │ spkr │  · gap · │ spkr │  ·    │   ← two 2" drivers, ~3 mm apart
   │  ·· │  L  │ ··    ·· │  R  │ ··     │
   │     ╰─────╯         ╰─────╯        │
   │   [amp1]  [VoiceS3R▢]  [amp2]      │   ← boards row, module centered
   │            [btn]/(∴)               │   ← button + mic perforation under it
   └────────────────────┬──────────────┘     (both over the VoiceS3R)
                     USB-C notch (bottom edge)
```

## Components

### Front shell (`modules/front_shell.scad`)
- Rounded rectangular outer wall, 2.4 mm thick, 6 mm corner radius.
- Two speaker recess rings (OD 50 mm seat, 44 mm grille field), 3 mm center
  gap. Each driver fastened by `spk_screw_n` (default 4) M2 self-tap screws
  through the driver flange into printed bolt-circle bosses (`spk_bolt_circle`,
  default 56 mm — must clear the driver OD). Start angle `spk_screw_a0` (45°)
  keeps the inner bosses out of the center gap.
- Two circular grilles (concentric rings of 3 mm holes) over the cutouts.
- A gasket groove in the baffle under each driver flange (`gasket_id`..`gasket_od`,
  `gasket_depth` deep) seats a foam/EVA ring so the flange seals the front
  wave from the back wave — the key small-driver sound-quality fix.
- VoiceS3R cradle: 3-wall pocket sized 24.4 mm (0.4 mm clearance), centered
  horizontally with an amp board flanking each side; module oriented
  button-forward; USB-C edge cutout toward the bottom; side windows on both
  sides for header wires to reach the amps.
- Button well guiding the plunger, with a retaining shoulder. The bore goes
  through the front wall **and** the cradle floor behind it, so the plunger
  nub can reach the module's switch.
- Mic perforation: a cluster of small holes (one center + a ring of
  `mic_ring_n`, default 6) through the front wall **and** the cradle floor,
  centered `mic_below_btn` below the button so they open into the pocket right
  at the module's own microphone. No boss needed.
- Amp-board standoffs with M2 self-tap pilots so each board screws down (×2).
- 4× corner screw bosses (front side).

### Rear plate (`modules/rear_plate.scad`)
- Flat plate matching the shell footprint, 2.4 mm thick.
- Two keyhole slots, default 90 mm apart (parametric), sized for common screw
  heads.
- USB-C cable notch at the bottom edge.
- 4× mating screw bosses (self-tapping or insert-ready).

### Button cap (`modules/button_cap.scad`)
- Captive plunger: face disc (~12 mm dia, slightly proud), skirt with a
  retention lip catching behind the well wall, underside nub landing on the
  module button center. ~1.5–2 mm travel; module switch provides return spring.

### Shared library (`modules/lib.scad`)
- Helpers: rounded box, grille hole pattern, keyhole slot, screw boss.

## Parametric structure

Parameters live in `modules/params.scad`; `terrace-case.scad` includes them and
exposes a `part` selector (a normal variable overridden by `-D part="..."`):

- `part` ∈ `"front"` | `"rear"` | `"button"` | `"coupon"` (fit-test) | `"all"` (assembled preview).
- All dimensions are named variables: outer W/H/D, wall thickness, corner
  radius, speaker OD/cutout/center-gap, driver retention mode, grille hole
  dia/spacing, module cradle size + clearance, USB-C notch position/size,
  button well + cap dims, mic perforation offset + hole/ring dims, amp
  board size + standoff height + amp screw pilot, speaker bolt-circle + screw
  count + start angle + boss dims, keyhole spacing, screw boss dia + M3 pilot,
  global fit clearance (default 0.4 mm).

## Build & file layout

```
hardware/terrace-case/
├── terrace-case.scad      # includes params + part render selector
├── modules/
│   ├── front_shell.scad
│   ├── rear_plate.scad
│   ├── button_cap.scad
│   └── lib.scad
├── build.sh               # openscad CLI → exports each part to stl/
├── stl/                   # generated meshes (gitignored)
├── .gitignore             # ignores stl/
└── README.md              # parameters, print settings, BOM, assembly
```

`build.sh` loops the parts and runs, per part:

```
openscad -o stl/<part>.stl -D 'part="<part>"' terrace-case.scad
```

## Print orientation & settings (documented in README)

- Front shell: grille face down — grilles and front surface print without
  supports.
- Rear plate: flat.
- Button cap: face down, small.
- Suggested: 0.2 mm layers, ≥4 perimeters, 20–30 % infill. Material is the
  user's choice (sheltered location relaxes the UV constraint).

## Verification (physical)

Because a full case is a multi-hour print, ship a **fit-test coupon** target
(`$part="coupon"`) containing just:
- one speaker recess ring,
- the VoiceS3R cradle + USB-C notch,
- the button well + a button cap,
- the mic perforation.

Print the coupon first (~10 min) to validate tolerances (cradle fit, button
travel, screw-boss pilot, speaker seat) before printing the full shell. The
README documents which parameters to nudge for a loose/tight fit.

## Out of scope

- Kitchen Atom Echo enclosure (already cased).
- Weatherproofing beyond "no upward openings" (location is sheltered).
- Any firmware/YAML changes — this is hardware only.
- **3.5 mm line-out jack** (optional PCM5100 DAC add-on) — deferred. The
  PCM5100 would sit as a parallel I²S listener on the same G5/G6/G7 bus and
  drive a panel-mount 3.5 mm jack; adding it later would need a small board
  standoff + a jack cutout (likely a side or bottom wall). See
  [docs/DEVICES.md](../../DEVICES.md) "Optional: PCM5100 3.5 mm line-out".

## Open items requiring physical measurement before final print

These are parameters with sensible defaults but should be confirmed against the
actual hardware:
- Mic offset below the button (`mic_below_btn`) to land on the module mic.
- Exact driver OD, cutout dia, and mounting-hole pattern.
- MAX98357A breakout footprint (clone dimensions vary).
- Module button center position relative to the front face.
