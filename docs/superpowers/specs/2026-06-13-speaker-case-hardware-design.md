# Speaker case — hardware revision: one great driver + smart amp (design)

Date: 2026-06-13
Status: design (approved approach A), pending implementation plan
Supersedes the driver / amp / EQ choices in
`2026-06-13-speaker-case-design.md` (that doc's geometry & structure stand; this
doc replaces its electronics stack and forces a single-cutout baffle).

## Purpose

Pick the best audio hardware that fits the existing combined-device envelope
(**~146 × 118 × 83 mm**, wall-mounted, USB-C), for a **balanced voice + music**
intercom / Home Assistant voice satellite. One hard constraint: the brain stays an
**ESP32-S3**. Drivers and everything else were re-spec'd from scratch.

This is a quality-first revision. The old stack (two 2″ AIYIMA drivers + 2×
MAX98357A + server-side EQ) is replaced.

## Why the old acoustic design was wrong (rationale)

1. **Dual 2″ side-by-side mono comb-filters.** Two identical sources ~70 mm apart
   playing the same signal cancel off-axis — first null ~29° off-axis at 5 kHz,
   worsening to 15 kHz. The 5–15 kHz band (speech crispness, music "air") becomes
   position-dependent. It's an SPL trick that trades away off-axis quality — the
   wrong trade for a wall device heard from the side.
2. **One 3.5″ beats two 2″ on every axis that matters.** Cone area: one Dayton
   PS95 ≈ 35 cm² vs two AIYIMA ≈ 24 cm² — ~50% more air moved (more output and
   midbass) **and** a coherent point source with smooth polar response. Geometry
   agrees: two 3.5″ won't fit the 138 mm inner width, so single is also the fit.
3. **Server-side EQ is a protection hole.** The old spec's 110 Hz excursion
   high-pass lived in Music Assistant DSP, which TTS and wake-word **bypass** —
   the most frequent audio hit a tiny driver full-range with no protection.
4. **MAX98357A caps quality** at 3.2 W, fixed gain, no DSP.
5. **Honest limit:** ~0.6 L sealed will *never* produce deep bass — that's
   geometry, not parts. The wins here are clarity, smooth off-axis response,
   clean loudness, and driver protection. Real bass stays a subwoofer's job.

## Bill of materials (per unit, ~$70 — mid budget)

| Block | Part | Role / why | ~$ |
|---|---|---|---|
| **Driver** | **1× Dayton Audio PS95-4** — 3.5″ point-source full-range, 4 Ω, Fs ≈ 87 Hz | Coherent point source → best voice intelligibility *and* smooth music; built for small sealed satellites | 22 |
| **Amp** | **1× TAS5805M I²S amp board** (PBTL mono, on 12 V) | On-chip **15-band biquad EQ + high-pass** on the I²S stream → EQ/protection for **all** audio incl. TTS/wake; ~15 W clean headroom; ESPHome-native (`audio_dac` platform `tas58xx`) | 18 |
| **Brain** | **M5Stack VoiceS3R** (ESP32-S3, 8 MB PSRAM) | Satisfies the ESP32-S3 requirement; reuses proven Terrace firmware; I²S out → amp, I²C → amp config. Onboard codec mic kept; its speaker codec path unused | 15 |
| **Power** | **USB-C PD trigger → 12 V** (e.g. CH224K) + **12 V→5 V buck** for the S3 | Real amp rail = clean transients, no TTS clipping; S3 regulates 3.3 V from 5 V | 7 |
| **Misc** | mic gasket, hookup wire, foam, fasteners | — | 5 |

Total ≈ **$67–72/unit.** PS95-4 (4 Ω) chosen over PS95-8 so the TAS5805M makes
full power at a modest 12 V rail.

## Audio architecture

```
USB-C ──PD trigger──► 12 V ─┬─────────────► TAS5805M (PVDD) ──► PS95-4 (PBTL, 4 Ω)
                            └─ buck ─► 5 V ─► VoiceS3R (ESP32-S3)
                                              │  I²S (audio out) ─────► TAS5805M
                                              │  I²C (config/EQ) ─────► TAS5805M
                                              └─ codec mic (I²S in) ◄── front MEMS
```

- **Two I²S buses** (as the project already does): one mic-in (codec), one
  audio-out (S3 → TAS5805M). The TAS5805M is configured over I²C.
- **EQ moves on-device** into the TAS5805M biquads, so it applies to TTS,
  wake-word, intercom, and music alike — fixing the old bypass hole. Music
  Assistant DSP becomes optional/cosmetic, not load-bearing for protection.

### On-device EQ / protection (TAS5805M biquads) — replaces the MA-DSP table

| Stage | Type | Freq | Q / slope | Gain | Applies to |
|---|---|---|---|---|---|
| Protect excursion | High-pass | ~90 Hz | 12 dB/oct (Q≈0.7) | — | all audio |
| Tame sealed hump | Peaking | ~Fc (≈140–150 Hz) | Q≈1.5 | −2 to −4 dB | all audio |
| Warmth (optional) | Low shelf | ~200 Hz | — | +2 to +3 dB | all audio |
| Breakup (only if needed) | Peaking notch | per measured breakup | Q≈2 | −3 dB | all audio |

The PS95 is smooth on top, so the breakup notch is likely unnecessary — measure
before adding. Final coefficients tuned against the assembled box.

## Acoustic notes (sealed box)

- Keep **sealed** (the old spec's call is right for predictability). Single driver
  reclaims one basket of volume — maximize the sealed chamber within the envelope.
- With PS95 (Vas ≈ 1.1 L, Qts ≈ 0.69) in ~0.6 L: Qtc ≈ 1.1, Fc ≈ 146 Hz — a mild
  midbass hump then rolloff. The "tame sealed hump" biquad flattens it; net result
  is warm-but-controlled. Target a larger Vb / lower Qtc if the geometry allows.
- Light polyfill in the chamber (effective volume bump, tames the hump slightly).

## Case implications (feeds the geometry spec / `params.scad`)

- **One driver cutout**, centered on the baffle, sized to the PS95-4 (cutout/screw
  pattern/seated depth **[confirm vs hardware]**), replacing the two 46 mm cutouts.
- **Electronics bay** now holds: VoiceS3R cradle, **one** TAS5805M amp mount (not
  two), **PD-trigger + buck** mounts, PTT button well, mic perforation, USB-C exit.
  Net parts count is similar; the second amp mount is freed for the PD/buck boards.
- **Divider**: one sealed wire pass (single driver → single 2-conductor pass)
  instead of two.
- Mic: gasket-isolated, front baffle, as far from the driver/port as the layout
  allows, to limit mechanical feedback. (Reversible: a discrete I²S MEMS on a bare
  S3 would allow freer placement — deferred for fleet/firmware consistency.)

## Out of scope (YAGNI)

- Stereo (mono shared chamber; can't image at this size anyway).
- Deep-bass tuning / ported box (geometry-limited; subwoofer's job).
- Passive radiator (Approach C — declined; keeps sealed predictability).
- Dual-mic array + AEC (would help far-field wake-while-playing, but out of
  envelope/budget; PTT is primary).
- Replacing the brain (ESP32-S3 / VoiceS3R retained by requirement).

## Open / confirm before build

- PS95-4 cutout diameter, screw pattern, seated depth vs the baffle and chamber
  depth (the limiting fit — confirm it clears the 75 mm cavity).
- USB-C source can supply **12 V** at the needed current (PD profile / wall PSU).
- TAS5805M board footprint + PVDD wiring vs the electronics-bay layout.
- VoiceS3R I²S-out routing to the TAS5805M alongside the existing mic I²S bus.
- Final sealed volume / Qtc after the single-driver baffle rework.
