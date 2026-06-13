# Speaker case — combined device (sealed speaker chamber + electronics bay)

Wall-mounted enclosure that is **both** the acoustic box for **two AIYIMA 2"/53 mm
full-range drivers (4 Ω)** and the housing for the full terrace electronics stack
(M5Stack VoiceS3R + 2× MAX98357A amps + PTT button + mic). A vertical stack: a
**sealed speaker chamber** on top, a **vented electronics bay** below, split by an
internal divider. Design rationale, measured driver T/S, and layout:
`docs/superpowers/specs/2026-06-13-speaker-case-design.md`.

## Parts
- `body` — shell with the sealed speaker chamber (two drivers on a flat baffle), the
  sealing divider + wire pass, and the electronics bay (module cradle, 2 amp mounts,
  button well, mic perf, USB-C exit)
- `rear` — flat gasketed lid with blind keyhole wall-mount bosses + module clamp
- `button` — captive PTT button cap
- `grille` — optional snap-on protective covers

## Build
```bash
./build.sh          # renders stl/{body,rear,button,grille}.stl
./test.sh           # asserts + render smoke checks
```

## Print & assembly
- Orient **back-down**: flat baffle + open back, no supports.
- Print the **speaker chamber airtight** (≥4 perimeters + a thin interior seal coat
  of epoxy/shellac); the electronics bay needn't be airtight.
- Foam gasket ring under each driver flange (groove provided); M2 self-tap each
  flange to its 4 bosses (43 mm square).
- Foam strip in the lid perimeter groove; **foam tape on the divider's back edge**
  for the chamber-to-lid seam; M3 self-tap the lid to the 4 corner bosses.
- Module drops into the cradle (clamped by the rear-lid collar); amps screw to
  their standoffs; button cap is captive in its well.
- **Wiring:** USB-C exits the bottom (power/data). Speaker wires run from the amps
  up through **two divider grommet passes — one per driver** (seal each with
  silicone), each carrying that driver's 2-wire pair. Feed L → one driver, R → the
  other.
- Loosely add polyfill in the **speaker chamber only**.

## Wall mount
Two blind keyhole bosses on the lid's outer face (near the top, over the speaker
zone) hang the box on two screws. They are cut through the boss only — the lid
panel behind stays solid, so the speaker chamber stays sealed.

## Bass / EQ — apply server-side in Music Assistant
Driver Fs ≈ 145 Hz: no usable output below ~120 Hz from any enclosure, and a sealed
box trims rather than extends the low end. The bass/warmth lever is **Music
Assistant's per-player Audio DSP** (the MAX98357A and the ESPHome pipeline cannot
filter). On `media_player.intercom_s3_player`, start from — then tune by ear:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | 110 Hz | 12 dB/oct (Q≈0.7) | — |
| Warmth | Low shelf | 160 Hz | — | +3 to +4 dB |
| Tame breakup (optional) | Peaking notch | 15 kHz | Q≈2 | −3 to −5 dB |

MA DSP only shapes audio routed through Music Assistant (music). TTS / wake-word
announcements bypass it — fine, those are speech.

## Confirm before printing
- Driver cutout (46 mm), screw square (43 mm), seated depth (28 mm) vs your units.
- VoiceS3R footprint, USB-C port depth, amp board size vs hardware (carried from
  terrace's `[confirm vs hardware]` notes).
- Speaker-chamber net volume floor enforced by `tests/asserts.scad` (`vol_target`).
- Box size (~146 × 118 × 83 mm) acceptable for the wall location.
