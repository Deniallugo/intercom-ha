# Speaker case — combined device: sealed speaker chamber + electronics bay (design)

Date: 2026-06-13
Status: design (revised — combined device), pending implementation plan

## Purpose

A wall-mounted enclosure that is **both** the acoustic box for two AIYIMA 2"/53 mm
full-range drivers **and** the housing for the full terrace electronics stack
(M5Stack VoiceS3R module + 2× MAX98357A amps + PTT button + mic). It supersedes
the earlier passive-speaker-only design: that box is now the **upper sealed
speaker chamber** of this part, with a **separate vented electronics bay** added
below it.

In short: terrace-case's electronics stack, dropped into the better sealed shell,
with an internal divider keeping the drivers' air away from the boards.

## Driver (measured / sourced)

AIYIMA 2", full-range, **4 Ω**, ~12–15 W. **The box holds TWO identical drivers**
(two cone cutouts, side by side, in one shared sealed chamber). The Thiele–Small
parameters below are a *per-driver* property; because both drivers are the same
part, one measurement characterizes each of them — it does not imply a one-driver
box.

| Dimension | Value |
|---|---|
| Frame OD | 53 mm |
| Cone/grille opening (cutout) | 46 mm |
| Mounting holes | 4 × on a 43 mm square (60 mm diagonal) |
| Seated depth (front→back) | 28 mm |

### Measured T/S (per driver; both drivers identical)

| Parameter | Value | Source |
|---|---|---|
| **Fs** (free-air resonance) | **~145 Hz** | Impedance peak (144.65 Hz) |
| **Re** (DC resistance) | ~3.4 Ω | LF impedance asymptote |
| **Qts** | ~0.6 | Derived (Qms ≈ 4.4, Qes ≈ 0.71) |
| **Le** | ~0.13 mH | HF impedance rise |
| Sensitivity | ~83–84 dB | SPL plateau 150 Hz–10 kHz |

With Fs = 145 Hz and Qts ≈ 0.6, *any* sealed box raises system Fc above 145 Hz —
the enclosure trims rather than extends bass. Size the speaker chamber as large as
the form factor reasonably allows for the lowest practical Qtc, and put the
bass/warmth lever on the amp side (Music Assistant DSP, below). SPL trace: −3 dB
by ~125 Hz, −6 dB by ~100 Hz, breakup spike ~15 kHz. Real deep bass is a
subwoofer's job.

Source: AIYIMA 2"/53 mm listings and review
(https://www.youtube.com/watch?v=taD2VMIUzdo,
https://www.aliexpress.com/s/wiki-ssr/article/mini-subwoofer-speaker-2-inch).
**Confirm cutout, screw square, and seated depth against the drivers in hand.**

## Architecture — two stacked zones, one divider

A vertical stack inside one cabinet (the terrace layout), split by a horizontal
internal divider:

```
            +---------------------------+   <- rounded top
            |   SEALED SPEAKER CHAMBER   |
            |    ( O )         ( O )     |   two drivers, side by side, mono
            |     shared sealed volume   |
            +---------------------------+   <- horizontal divider (sealing floor)
            |      ELECTRONICS BAY       |   vented
            | [amp]  [module+btn]  [amp] |   VoiceS3R + 2x MAX98357A
            |           (mic)            |
            +------------[USB-C]---------+   <- bottom edge
```

- **Top — sealed speaker chamber.** Both drivers on the flat front baffle, firing
  into the room. One shared sealed sub-volume (mono; ~70 mm spacing can't image).
  Sealed by: driver flange gaskets, the rear-plate perimeter gasket, the divider
  seam, and a sealed wire pass through the divider.
- **Divider.** A horizontal slab (`wall` thick) spanning the full inner width and
  full cavity depth, forming the chamber floor. It butts against the rear lid
  (apply foam tape on its back edge for the seam). **Two sealed wire passes — one
  directly under each driver** (grommet each, 2 conductors per pass) go up through
  it from the amps to the drivers. Multiple sealed passes don't harm the chamber —
  each only leaks if not sealed — and they keep the two pairs from crossing.
- **Bottom — electronics bay (vented).** Ported from terrace-case:
  - VoiceS3R module cradle (24×24, button-forward, open at the back)
  - 2× MAX98357A amp mounts flanking the module
  - PTT button well + captive button cap through the front
  - mic perforation cluster below the button
  - USB-C bottom exit (power/data; the device's external connection)
  - module-retention clamp on the rear lid's inner face
  The button well, mic holes, and USB cutout deliberately breach this bay — it is
  **not** sealed, by design. The divider keeps those breaches out of the chamber.

### Wiring
- **External:** a single USB-C exits the bottom (power + data), exactly as terrace.
- **Internal:** amp speaker outputs run up through the divider's two sealed grommet
  passes (one per driver) into the speaker chamber. Feed L → one driver, R → other.

## Geometry (all parametric)

Approximate; final values in `params.scad` as derived functions.

- **External ≈ 146 W × 118 H × 83 D mm.** Sized for wire room: a tall electronics
  bay and a deep cavity give clearance around the module/amps and front-to-back
  for connectors.
- Vertical stack (inner): top wall 4 + **speaker zone 62** + divider 4 + **board
  zone 44** + bottom wall 4 = 118. The 44 mm bay leaves ~10 mm above and below the
  24.8 mm module for wire routing.
- Speaker chamber net volume ≈ **0.59 L** (inner width 138 × zone 62 × cavity 75,
  minus two driver baskets). Floor enforced by assert `vol_target` (≈0.45 L).
  At Fs = 145 Hz the exact volume is acoustically near-irrelevant; the deep cavity
  is chosen for wire room as much as volume.
- **Walls/divider 4 mm.** Rounded vertical edges (`radius`) for baffle diffraction.
- Drivers vertically centered in the speaker zone; module + amps + button + mic
  centered in the board zone (terrace coordinates, re-derived for the new height).

## Structure — extends `hardware/speaker-case/`, ports from `terrace-case`

Keep the existing package; grow it into the combined device.

```
hardware/speaker-case/
  speaker-case.scad        # dispatcher: "body" | "rear" | "button" | "grille" | "all"
  modules/
    params.scad            # + board-zone, module, amp, button, mic, USB, clamp, divider params
    lib.scad               # unchanged helpers
    body.scad              # + divider, cradle, amp mounts, button well, mic perf, USB exit,
                           #   divider wire pass; drivers move into the upper speaker zone
    rear_plate.scad        # + module-retention clamp on the inner face
    button_cap.scad        # NEW — captive button plunger (ported from terrace)
    grille.scad            # unchanged (optional snap-on)
  tests/asserts.scad       # + board-zone / divider / module / seal asserts
  build.sh / test.sh       # + "button" part
```

Ported (adapted to the new layout coordinates) from `terrace-case`:
`voicesr_cradle`, `amp_mounts`, `button_well`, `mic_perf`, `usb_floor_cut`,
`module_clamp`, `button_cap`, and their params (module footprint, amp, button,
mic, USB, clamp, keyhole). The depth **spacer** is NOT ported (chamber depth is
set directly). The old single bottom `wire_pass_cut` is replaced: external exit is
USB-C, internal speaker wiring uses the divider wire pass.

### Components and responsibilities

- **`body.scad`** — the cabinet. Open-back shell; a horizontal **divider** sealing
  the speaker chamber floor with a sealed wire pass through it; in the **speaker
  zone** the two cone cutouts + locating rings + gasket grooves + 43 mm-square
  screw bosses; in the **board zone** the module cradle, two amp mounts, button
  well, mic perforation, USB-C bottom exit; four corner M3 bosses for the lid.
- **`rear_plate.scad`** — flat gasketed lid: perimeter gasket groove, corner M3
  clearance holes, two keyhole slots, and the **module-retention clamp** collar on
  the inner face (lands behind the module).
- **`button_cap.scad`** — captive button plunger (ported from terrace).
- **`grille.scad`** — optional snap-on perforated cover per driver.
- **`tests/asserts.scad`** — speaker-chamber net volume ≥ `vol_target`; driver
  layout/gasket/screw-square checks; **board-zone fits the module + flanking
  amps**; divider sits between the zones and its wire pass is bounded; button/mic
  land within the module footprint; USB-C bottom exit is a bounded sealed hole;
  module clamp reaches and fits.

## Print & assembly

- Orient **back-down**: flat baffle + open back, no supports.
- Print the **speaker chamber airtight** (≥4 perimeters + interior seal coat); the
  electronics bay needn't be airtight.
- Foam gasket under each driver flange; foam in the lid perimeter groove; foam tape
  on the divider's back edge for the chamber-to-lid seam; grommet + silicone on the
  divider wire pass.
- Module drops into the cradle, clamped by the rear-lid collar; amps screw to their
  standoffs; button cap is captive in its well; USB-C exits the bottom.
- Light polyfill in the speaker chamber only.
- Fasteners: M2 self-tap for driver flanges (8) and amp standoffs; M3 self-tap for
  the rear lid (match terrace pilots).

## Bass / EQ — server-side in Music Assistant

The MAX98357A and the ESPHome pipeline can't filter; apply EQ in **Music Assistant
per-player Audio DSP** on `media_player.intercom_s3_player`:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | 110 Hz | 12 dB/oct (Q≈0.7) | — |
| Warmth | Low shelf | 160 Hz | — | +3 to +4 dB |
| Tame breakup (optional) | Peaking notch | 15 kHz | Q≈2 | −3 to −5 dB |

MA DSP shapes music routed through Music Assistant; TTS / wake-word bypass it (fine).

## Out of scope (YAGNI)

- Ported / bass-reflex tuning (Fs = 145 Hz — can't manufacture sub-bass).
- Per-driver sealed sub-volumes (mono shared chamber; can't image stereo anyway).
- Two separate boxes.
- Sealing the electronics bay (it must breach for button/mic/USB).
- Depth spacer (chamber depth set directly).
- Crossover (full-range drivers).

## Open / confirm before print

- Driver cutout (46), screw square (43), seated depth (28) vs units in hand.
- VoiceS3R module footprint, USB-C port depth, amp board size vs hardware
  (carried over from terrace's `[confirm vs hardware]` notes).
- Speaker-chamber net volume floor (assert `vol_target`).
- Box size (~146 × 118 × 83 mm) acceptable for the wall location.
