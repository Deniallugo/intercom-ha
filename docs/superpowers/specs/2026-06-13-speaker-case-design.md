# Speaker case — sealed twin-driver wall enclosure (design)

Date: 2026-06-13
Status: design, pending implementation plan

## Purpose

A dedicated **acoustic** enclosure for two AIYIMA 2"/53 mm full-range drivers,
optimized for "good enough to listen to music." This is a speaker box only — no
electronics module inside (unlike `terrace-case`, which co-houses the VoiceS3R
board and amps in a single shared, foam-lined, non-sealed volume). The drivers
are driven by the terrace device's existing 2× MAX98357A dual-mono amps over a
4-wire run.

## Driver (measured / sourced)

AIYIMA 2", full-range, **4 Ω**, ~12–15 W.

| Dimension | Value |
|---|---|
| Frame OD | 53 mm |
| Cone/grille opening (cutout) | 46 mm |
| Mounting holes | 4 × on a 43 mm square (60 mm diagonal) |
| Seated depth (front→back) | 28 mm |

No published Thiele–Small parameters, so the box is sized by rule of thumb, not
computed alignment.

Source: AIYIMA 2"/53 mm listings and review
(https://www.youtube.com/watch?v=taD2VMIUzdo,
https://www.aliexpress.com/s/wiki-ssr/article/mini-subwoofer-speaker-2-inch).
**Implementer must confirm the cutout, screw square, and seated depth against the
drivers in hand before printing** — clone batches vary.

## Acoustic design

- **Sealed, two-chamber single box.** Both drivers in one cabinet, but an
  **integral divider** down the middle gives each driver its own sealed
  sub-volume. This stops the two cones modulating each other's air, which lowers
  intermodulation distortion on music.
- **Target net volume ≈ 0.30 L per chamber.** Rule-of-thumb sealed sizing for a
  2" full-range: yields a relaxed, non-boxy alignment rather than a peaky small
  box. Net = internal gross minus driver displacement (~25 cm³ each).
- **Light polyfill stuffing** in each chamber damps internal standing waves and
  raises the effective volume ~15%. Loosely fill, do not pack.
- **Sealing is the whole game.** Any leak collapses the low end. Three seals:
  1. Foam gasket tape (or the printed gasket groove) under each driver flange.
  2. Gasketed rear plate (groove + foam, screwed down).
  3. One sealed wire pass-through per chamber (grommet + dab of silicone).

### Driver orientation — front baffle, toed out

Drivers sit on the **front face, split into two facets each toed outward 15°**
(left facet aims left-of-center, right facet right-of-center). Rationale:

- A single box ~70 mm driver spacing cannot image as stereo anyway, so toe-out
  trades nothing and buys **wider dispersion / room fill** — better for casual
  listening off the sweet spot.
- Still throws sound **into the room**, unlike side-firing, which suits the
  wall mount (back flat to wall).

### Wall mount

- Back flat against the wall → **half-space boundary loading**, ~+3–6 dB in the
  low end. Welcome for tiny drivers.
- **Keyhole slots molded into the rear plate** (hang on two screws). Rear plate
  does double duty: seals the box and mounts it. Reuse `keyhole()` from lib and
  the terrace `keyhole_*` params.
- **Wire exit at the bottom edge** (one sealed pass per chamber), wires routed
  down the wall. Rear exit is rejected — won't seal flush to a wall without a
  cavity. Feed L → one driver, R → the other.

## Geometry (all parametric)

Approximate, final values live in `params.scad` as derived functions:

- Internal chamber ≈ 65 W × 72 H × 68 D mm → ~0.30 L net after driver
  displacement.
- **Walls and divider 4 mm** (rigid, pushes panel resonance up out of the
  music band; thin printed walls ring).
- 15° toe-out per facet.
- External ≈ **150 L × 80 H × 80 D mm** (length = left-right driver axis). Fits
  any common print bed.

## Structure — mirrors `terrace-case`

New directory `hardware/speaker-case/`, same layout and conventions as
`hardware/terrace-case/`:

```
hardware/speaker-case/
  speaker-case.scad        # top-level assembly (body + rear plate + optional grille)
  params.scad              # driver dims, chamber volume, walls, toe-out, mount, seals
  build.sh                 # render STLs (copy terrace build.sh pattern)
  test.sh                  # run asserts (copy terrace test.sh pattern)
  modules/
    lib.scad               # local copy of helpers: rounded_rect, keyhole, screw_boss, grille
    body.scad              # twin sealed chambers, toed-out front baffles, divider,
                           # driver recesses + gasket grooves + screw bosses, bottom wire pass
    rear_plate.scad        # gasketed lid, keyhole slots, mating screw bosses
    grille.scad            # OPTIONAL snap-on protective grille, one per driver (separate print)
  tests/
    asserts.scad           # geometry asserts (volume target, wall thickness, screw square, seals)
```

Reused from terrace conventions: `$fn`, `clr`, `wall`/`radius` style,
`spk_od`/`spk_cut`/gasket-groove params, `spk_*` screw-boss params (re-spec'd to
the 43 mm square), `keyhole_*`, M3 `boss_od`/`screw_pilot`/`screw_clear`, and
the `lib.scad` helpers.

### Components and responsibilities

- **`body.scad`** — the sealed cabinet. Inputs: params. Produces the open-back
  shell with two toed-out front baffles, central divider sealing the two
  chambers, recessed 46 mm driver cutouts with locating ring + gasket groove,
  four screw bosses per driver on the 43 mm square, one sealed wire pass per
  chamber at the bottom edge, and corner M3 bosses for the rear plate.
- **`rear_plate.scad`** — flat gasketed lid. Inputs: params. Produces the lid
  with a perimeter gasket groove, M3 clearance holes matching the body bosses,
  and two keyhole slots for wall mounting.
- **`grille.scad`** — optional. A snap-on perforated cover per driver using the
  `grille()` field; does not touch the sealed volume.
- **`tests/asserts.scad`** — asserts net chamber volume ≥ target, wall/divider
  thickness, screw square = 43 mm, gasket groove present, and that the wire pass
  sits on the bottom edge.

## Print notes

- Orient **back-down** on the bed: the two 15° front facets print as mild
  overhangs (~75° from horizontal) — no supports.
- Rear plate and grilles print flat, no supports.
- 4 drivers' worth of fasteners: M2/M2.5 self-tap into printed bosses for the
  driver flanges; M3 self-tap for the rear plate (match terrace pilots).

## Out of scope (YAGNI)

- Ported / bass-reflex tuning (no T/S data to tune against).
- Two separate boxes (user chose single compact box).
- Housing any electronics — amps and MCU stay in the terrace device.
- Crossover (full-range drivers, none needed).

## Open / confirm before print

- Driver cutout, screw square, seated depth vs. drivers in hand.
- Final net volume after the body solid is modeled (assert enforces the floor).
