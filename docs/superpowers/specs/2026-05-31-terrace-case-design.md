# Terrace VoiceS3R Enclosure — Design

A wall-mounted, 3D-printable enclosure for the terrace intercom combo: the
M5Stack ATOM Echo S3R (VoiceS3R) module, two MAX98357A amp breakouts, and
two 2" external speaker drivers. Authored as parametric OpenSCAD so the model
is version-controlled, diffable, and re-renderable from source.

## Goal

Produce a serviceable, sheltered-outdoor wall enclosure that:

- Mounts two ~2" (≈53 mm OD) full-range drivers side by side as a horizontal
  stereo pair, near-touching.
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
  The speaker block describes `2× MAX98357A` in stereo (`channel: stereo`),
  which this two-driver enclosure matches.
- The kitchen Atom Echo already has a working case and is out of scope.
- No prior CAD exists in the repo; this is a clean start.

## Decisions (locked)

| Topic | Decision |
|---|---|
| Target hardware | Terrace VoiceS3R + 2× MAX98357A + 2× 2" drivers |
| Deliverable | Parametric OpenSCAD source → STL via CLI |
| Mounting | Wall-mount (keyhole slots on rear plate) |
| Speaker driver | 2" full-range, ≈53 mm OD, ≈46 mm grille cutout |
| Speaker layout | Side by side (horizontal stereo), ~3 mm center gap |
| Amp boards | Two (one per speaker) |
| Weather | Covered/sheltered — no gland/gasket weatherproofing; just avoid upward openings |
| Architecture | Two-part clamshell: front shell + rear wall plate, 4× M3 screws |
| Button | Captive printed plunger cap over module's PTT button |
| Microphone | Mic port + sealing boss aligned to module mic opening |
| Mic port placement | Front face, low corner, away from speaker grilles |
| STL files | Gitignored (regenerable from source) |
| Envelope | ~123 × 98 × 42 mm |

## Architecture

Two printed parts plus one small printed plunger:

1. **Front shell** — the visible body. Carries the two speaker recess rings +
   grilles, the button well, the mic port + sealing boss, the VoiceS3R cradle,
   amp-board standoffs/clips, and the screw bosses.
2. **Rear plate** — sits flush on the wall. Carries two keyhole mounting slots,
   the USB-C cable notch at the bottom edge, and the mating screw bosses.
3. **Button cap** — a captive plunger that drops into the front-shell button
   well and presses the module's tactile switch.

The two halves join with **4× M3 screws** (corners), self-tapping into printed
bosses by default. Parting line runs around the perimeter; the front shell
holds the deeper (~30 mm) speaker zone, the rear plate is shallow (~12 mm).

### Layout (front view, landscape)

```
   ┌──────────────────────────────────┐
   │  ·· ╭─────╮ ··  ·· ╭─────╮ ··      │
   │ ·  │ spkr │  · gap · │ spkr │  ·    │   ← two 2" drivers, ~3 mm apart
   │  ·· │  L  │ ··    ·· │  R  │ ··     │
   │     ╰─────╯         ╰─────╯        │
   │  (·)                              │   ← mic port (low corner, away from grilles)
   │  [VoiceS3R▢] [amp1] [amp2]   [btn]│   ← boards row; plunger over module button
   └────────────────────┬──────────────┘
                     USB-C notch (bottom edge)
```

## Components

### Front shell (`modules/front_shell.scad`)
- Rounded rectangular outer wall, 2.4 mm thick, 6 mm corner radius.
- Two speaker recess rings (OD 53 mm seat, 46 mm through-cutout), 3 mm center
  gap. Each driver retained by 4 small printed tabs *or* M2 screws through the
  frame holes — selectable via parameter.
- Two circular grilles (concentric rings of 3 mm holes) over the cutouts.
- VoiceS3R cradle: 3-wall pocket sized 24.4 mm (0.4 mm clearance), module
  oriented button-forward; USB-C edge cutout toward the bottom; side window for
  header wires to reach the amps.
- Button well guiding the plunger, with a retaining shoulder.
- Mic port (2 mm hole or 3-hole cluster) + sealing boss collar (foam/EVA gasket
  seat) aligned to module mic opening; position is parametric.
- Amp-board standoffs + printed retention clips (×2).
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

`terrace-case.scad` opens with a single parameters block and a `$part` selector:

- `$part` ∈ `"front"` | `"rear"` | `"button"` | `"coupon"` (fit-test) | `"all"` (assembled preview).
- All dimensions are named variables: outer W/H/D, wall thickness, corner
  radius, speaker OD/cutout/center-gap, driver retention mode, grille hole
  dia/spacing, module cradle size + clearance, USB-C notch position/size,
  button well + cap dims, mic port position/diameter + boss/gasket dims, amp
  board size + standoff height, keyhole spacing, screw boss dia + M3 pilot,
  global fit clearance (default 0.4 mm).

## Build & file layout

```
hardware/terrace-case/
├── terrace-case.scad      # parameters block + $part render selector
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
openscad -o stl/<part>.stl -D '$part="<part>"' terrace-case.scad
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
- the mic port + boss.

Print the coupon first (~10 min) to validate tolerances (cradle fit, button
travel, screw-boss pilot, speaker seat) before printing the full shell. The
README documents which parameters to nudge for a loose/tight fit.

## Out of scope

- Kitchen Atom Echo enclosure (already cased).
- Weatherproofing beyond "no upward openings" (location is sheltered).
- Any firmware/YAML changes — this is hardware only.

## Open items requiring physical measurement before final print

These are parameters with sensible defaults but should be confirmed against the
actual hardware:
- Exact module mic-hole position (sets mic port X/Y).
- Exact driver OD, cutout dia, and mounting-hole pattern.
- MAX98357A breakout footprint (clone dimensions vary).
- Module button center position relative to the front face.
