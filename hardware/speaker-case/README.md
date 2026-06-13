# Speaker case — sealed twin-driver wall enclosure

Sealed, mono, wall-mounted enclosure for **two AIYIMA 2"/53 mm full-range drivers
(4 Ω)**, driven by the terrace device's 2× MAX98357A amps. Design rationale and
measured driver T/S: `docs/superpowers/specs/2026-06-13-speaker-case-design.md`.

## Parts
- `body` — sealed shell + flat baffle (both drivers), bottom wire pass
- `rear` — flat gasketed lid + keyhole wall mount
- `grille` — optional snap-on protective covers

## Build
```bash
./build.sh          # renders stl/body.stl, stl/rear.stl, stl/grille.stl
./test.sh           # asserts + render smoke checks
```

## Print & assembly
- Orient **back-down**: flat baffle, no overhangs, no supports.
- Print **airtight**: ≥4 perimeters / high wall count, then a thin interior seal
  coat (epoxy or shellac wash) on the shell before assembly. FDM PLA leaks through
  layer lines, not just joints — sealing is the whole game for a sealed box.
- Foam gasket ring under each driver flange (groove provided); M2 self-tap the
  flanges to the 4 bosses (43 mm square) per driver.
- Foam strip in the rear-plate perimeter groove; M3 self-tap the lid to the 4
  corner bosses.
- Single wire bundle (4 conductors, 2 per driver) exits the bottom through a
  grommet — seal with a dab of silicone. Feed L → one driver, R → the other.
- Loosely add polyfill; do not pack.

## Bass / EQ — apply server-side in Music Assistant
This driver's free-air resonance is **Fs ≈ 145 Hz**: there is no usable output
below ~120 Hz from any enclosure, and a sealed box trims rather than extends the
low end. The bass/warmth lever is **Music Assistant's per-player Audio DSP**
(the MAX98357A and the ESPHome pipeline cannot filter). On
`media_player.intercom_s3_player`, start from — then tune by ear:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | 110 Hz | 12 dB/oct (Q≈0.7) | — |
| Warmth | Low shelf | 160 Hz | — | +3 to +4 dB |
| Tame breakup (optional) | Peaking notch | 15 kHz | Q≈2 | −3 to −5 dB |

MA DSP only shapes audio routed through Music Assistant (music). TTS / wake-word
announcements bypass it — fine, those are speech.

## Confirm before printing
- Driver cutout (46 mm), screw square (43 mm), seated depth (28 mm) vs your units.
- Net sealed volume floor is enforced by `tests/asserts.scad` (`vol_target`).
