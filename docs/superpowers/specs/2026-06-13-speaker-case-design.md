# Speaker case — sealed twin-driver wall enclosure (design)

Date: 2026-06-13
Status: design, pending implementation plan

## Purpose

A dedicated **acoustic** enclosure for two AIYIMA 2"/53 mm full-range drivers,
optimized for "good enough to listen to music" at near-field / desk levels (~3 W
per channel from the MAX98357As). This is a speaker box only — no electronics
module inside (unlike `terrace-case`, which co-houses the VoiceS3R board and amps
in a single shared, foam-lined, non-sealed volume). The drivers are driven by the
terrace device's existing 2× MAX98357A dual-mono amps over a 4-wire run.

**Reality check from the measured driver (see below): Fs ≈ 145 Hz.** This is a
midrange-with-some-upper-bass, not a woofer — there is no usable output below
~120 Hz from any enclosure. The box's job is to load the driver cleanly and seal
well; the *bass* lever is amp-side EQ, and real low end is a subwoofer's job, not
this box's.

## Driver (measured / sourced)

AIYIMA 2", full-range, **4 Ω**, ~12–15 W.

| Dimension | Value |
|---|---|
| Frame OD | 53 mm |
| Cone/grille opening (cutout) | 46 mm |
| Mounting holes | 4 × on a 43 mm square (60 mm diagonal) |
| Seated depth (front→back) | 28 mm |

### Measured T/S (impedance + SPL sweep, LMS)

No published Thiele–Small parameters, so these were measured in-hand from a
free-air impedance sweep and an SPL trace:

| Parameter | Value | Source |
|---|---|---|
| **Fs** (free-air resonance) | **~145 Hz** | Impedance peak (144.65 Hz) |
| **Re** (DC resistance) | ~3.4 Ω | LF impedance asymptote |
| **Qts** | ~0.6 | Derived (Qms ≈ 4.4, Qes ≈ 0.71) |
| **Le** | ~0.13 mH | HF impedance rise |
| Sensitivity | ~83–84 dB | SPL plateau 150 Hz–10 kHz |

**Vas was not measured** (would need a second added-mass sweep) and is not
needed: at Fs = 145 Hz the bass outcome is dominated by the driver, not the box.
SPL trace confirms −3 dB by ~125 Hz, −6 dB by ~100 Hz, then a steep rolloff
(~65 dB @ 50 Hz). A cone-breakup spike sits at ~15 kHz.

**Design consequence:** with Qts ≈ 0.6, *any* sealed box raises the system
resonance Fc **above** 145 Hz and the system Q above 0.6 — so the enclosure
trims the low end rather than extending it. Size for the lowest practical Qtc
(largest volume the form factor allows) and put the bass/warmth lever on the amp,
not the box.

Source: AIYIMA 2"/53 mm listings and review
(https://www.youtube.com/watch?v=taD2VMIUzdo,
https://www.aliexpress.com/s/wiki-ssr/article/mini-subwoofer-speaker-2-inch).
**Implementer must confirm the cutout, screw square, and seated depth against the
drivers in hand before printing** — clone batches vary.

## Acoustic design

- **Sealed, single shared chamber, mono.** Both drivers in one sealed cabinet,
  **no divider**, fed the same (L+R summed) signal. A ~70 mm driver spacing
  cannot image as stereo, so there is nothing to protect with a divider — and at
  Fs = 145 Hz the inter-driver modulation a divider would prevent is negligible.
  Dropping it gives a simpler part, one gasket perimeter, one wire pass, and the
  option of a single larger volume.
- **Size the volume as large as the form factor allows** (target ~0.6 L net,
  shared). With Qts ≈ 0.6 a larger box gives the **lowest practical Qtc** — it
  does *not* extend bass (Fc still sits above 145 Hz), it just avoids piling
  extra system-Q on top. Net = internal gross minus driver displacement
  (~25 cm³ each) and boss/wire-pass solids.
- **Light polyfill stuffing** damps internal standing waves and raises effective
  volume ~5–10%. Loosely fill, do not pack. (Minor at this size — the first
  internal mode is ~2.4 kHz and easily damped.)
- **Sealing is the whole game — including the walls.** FDM PLA leaks through
  layer lines, not just joints. Required:
  1. Print airtight: ≥4 perimeters / high wall count, and a thin **interior seal
     coat** (epoxy or shellac wash) on the shell.
  2. Foam gasket tape (or the printed gasket groove) under each driver flange.
  3. Gasketed rear plate (groove + foam, screwed down).
  4. One sealed wire pass-through (grommet + dab of silicone).

### Bass / EQ — the actual low-end lever (Music Assistant DSP, server-side)

At Fs = 145 Hz no enclosure trick yields bass the driver doesn't have. The amp is
a **MAX98357A** (same as terrace) — digital I²S in, Class-D, no onboard EQ and
only a 5-step gain pin. **The ESPHome firmware can't filter either**: its audio
pipeline only does decode / resample / mix / volume (no EQ component), and the
MAX path is raw I²S into the amp's own DAC with no codec to lean on. Hand-writing
an on-device biquad is not worth it.

The home is **Music Assistant's per-player Audio DSP** (confirmed available and
working), applied server-side before streaming to
`media_player.intercom_s3_player`. Starting values — tune by ear from here:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | 110 Hz | 12 dB/oct (BW Q≈0.7) | — |
| Warmth | Low shelf | 160 Hz | — | +3 to +4 dB |
| Tame breakup (optional) | Peaking notch | 15 kHz | Q≈2 | −3 to −5 dB |

- HPF stops wasting excursion below what the driver can reproduce; cleans midbass.
- Low shelf adds perceived warmth without asking for bass that isn't there.
- The 15 kHz notch only if the cone-breakup spike sounds harsh.
- Real deep bass is out of scope — that's a subwoofer's job.

Caveat: MA DSP only shapes audio routed *through Music Assistant* (i.e. music —
the use case for this box). TTS / wake-word announcements run via HA's voice
pipeline, which has no EQ — fine, those are speech. If music is ever sourced
outside MA, the EQ won't apply and the box plays flat/thin below ~150 Hz.

### Driver orientation — flat front baffle

Drivers sit on a **single flat front face, side by side, no toe-out.** A 2" cone
is near-omnidirectional through its whole usable band, so toe-out buys no real
dispersion and only adds a center baffle ridge (a diffraction source). Instead,
**round the baffle edges** (`rounded_rect`) — that is the diffraction win that
actually exists at this size. Front-firing throws into the room, which suits the
wall mount (back flat to wall).

### Wall mount

- Back flat against the wall → **half-space boundary loading**, ~+3 dB in the
  low end. Welcome for tiny drivers.
- **Keyhole slots molded into the rear plate** (hang on two screws). Rear plate
  does double duty: seals the box and mounts it. Reuse `keyhole()` from lib and
  the terrace `keyhole_*` params.
- **Wire exit at the bottom edge** (one sealed pass), wires routed down the wall.
  Rear exit is rejected — won't seal flush to a wall without a cavity.

## Geometry (all parametric)

Approximate, final values live in `params.scad` as derived functions:

- Single internal chamber ≈ 130 W × 72 H × 68 D mm → ~0.6 L net after driver and
  boss/wire-pass displacement.
- **Walls 4 mm.** Note: 4 mm PLA does *not* push panel resonance out of the music
  band — a panel this size still rings in band. With so little LF energy it is
  unlikely to matter audibly; if insurance is wanted, add a single internal
  brace tying the two largest panels. Do not claim it as a feature.
- Flat front baffle, no toe-out; round the baffle edges for diffraction.
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
    body.scad              # single sealed chamber, flat front baffle (2 drivers),
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
  shell with one flat front baffle carrying both drivers side by side, recessed
  46 mm driver cutouts with locating ring + gasket groove, four screw bosses per
  driver on the 43 mm square, one sealed wire pass at the bottom edge, and corner
  M3 bosses for the rear plate.
- **`rear_plate.scad`** — flat gasketed lid. Inputs: params. Produces the lid
  with a perimeter gasket groove, M3 clearance holes matching the body bosses,
  and two keyhole slots for wall mounting.
- **`grille.scad`** — optional. A snap-on perforated cover per driver using the
  `grille()` field; does not touch the sealed volume.
- **`tests/asserts.scad`** — asserts net chamber volume ≥ target, wall thickness,
  screw square = 43 mm, gasket groove present, and that the wire pass sits on the
  bottom edge.

## Print notes

- Orient **back-down** on the bed: flat front baffle, no overhangs, no supports.
- Rear plate and grilles print flat, no supports.
- Print **airtight**: ≥4 perimeters / high wall count, then an interior seal coat
  (epoxy or shellac wash) on the shell before assembly.
- Fasteners: M2/M2.5 self-tap into printed bosses for the driver flanges (8
  total, 4 per driver); M3 self-tap for the rear plate (match terrace pilots).

## Out of scope (YAGNI)

- Ported / bass-reflex / passive-radiator tuning. With Fs = 145 Hz, ports and
  PRs tune near Fs and cannot manufacture sub-bass — not worth the complexity.
- A divider / per-driver sealed sub-volume (dropped: can't image stereo, mono).
- Two separate boxes (user chose single compact box).
- Housing any electronics — amps and MCU stay in the terrace device.
- Crossover (full-range drivers, none needed).
- Deep bass — that's a subwoofer's job, not this enclosure.

## Open / confirm before print

- Driver cutout, screw square, seated depth vs. drivers in hand.
- Final net volume after the body solid is modeled (assert enforces the floor).
- **EQ confirmed: Music Assistant per-player Audio DSP** works. Apply 110 Hz HPF
  + ~160 Hz low shelf (+ optional 15 kHz notch) on
  `media_player.intercom_s3_player` — values in the Acoustic design table.
  (Neither the MAX98357A nor the ESPHome pipeline can filter; MA DSP is the home.
  Verified: ESPHome path is decode/resample/mix/volume only, MAX path is raw I²S.)
