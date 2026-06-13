# Speaker case — hardware revision: sound-first, intercom-capable (design)

Date: 2026-06-13
Status: design (approved — Option 2, sound-first), pending implementation plan
Supersedes the driver / amp / EQ choices in
`2026-06-13-speaker-case-design.md` (that doc's geometry & structure stand; this
doc replaces its electronics stack and forces a single-cutout baffle).

## Purpose

Pick the best audio hardware that fits the existing combined-device envelope
(**~146 × 118 × 83 mm**, wall-mounted, USB-C). Priority order, per the latest
call: **sound quality / playback first, intercom + voice a provisioned second.**
One hard constraint: a **bare ESP32-S3** brain (no VoiceS3R "smart-speaker"
module, no integrated-amp board — those are out of stock / too abstracted).

## Why the old acoustic design was wrong (still applies)

1. **Dual 2″ side-by-side mono comb-filters.** Two identical sources ~70 mm apart
   on the same signal cancel off-axis — first null ~29° off-axis at 5 kHz,
   worsening to 15 kHz. The speech/"air" band becomes position-dependent. An SPL
   trick that trades away off-axis quality — wrong for a wall device.
2. **One 3.5″ beats two 2″ on every axis that matters.** Cone area: one Dayton
   PS95 ≈ 35 cm² vs two AIYIMA ≈ 24 cm² — ~50 % more air moved, *and* a coherent
   point source with smooth polar response. Geometry agrees: two 3.5″ won't fit
   the 138 mm inner width, so single is also the fit.
3. **MAX98357A is too weak for an 8 Ω driver** (~2 W into 8 Ω at 5 V ≈ 86 dB/1 m)
   — fine for voice, quiet for music. A sound-first device needs a real rail and a
   real amp.

## Chosen architecture — bare S3 → I²S DAC → class-D amp

The standalone TAS5805M (on-amp DSP) only ships bundled with an ESP32 (Louder /
SmartAmp), and those are out of stock — so on-amp DSP is off the table. Instead,
a clean split: a good I²S DAC for fidelity, a powerful analog class-D amp for
output. EQ moves to Music Assistant (server-side); see the EQ section.

```
 USB-C PD charger (15 V, 30 W+)
   └─► CH224K (set 15 V) ─┬─► TPA3116 mono amp (VCC 15 V) ─► PS95-8 (8 Ω)
                          │        ▲ IN+  ◄── PCM5102 L-out (analog)
                          └─► MP1584 buck → 5 V ─► ESP32-S3 (onboard LDO → 3V3)
 ESP32-S3 ── I²S out ─► PCM5102A DAC ── analog L ─► TPA3116
          ── I²S in  ◄─ ICS-43434 mic            (intercom — secondary)
          ── GPIO ────► PTT button → GND          (intercom — secondary)
 COMMON STAR GROUND: CH224K / TPA / buck / S3 / DAC / mic grounds all tied.
```

## Bill of materials (per unit, ~$68 — mid budget)

| Block | Part | Role / why | ~$ |
|---|---|---|---|
| **Driver** | **1× Dayton Audio PS95-8** — 3.5″ point-source full-range, 8 Ω, Fs ≈ 87 Hz | Coherent point source, smooth response, more cone area than dual-2″; built for small sealed satellites. (TB W3-1364SA is a fidelity alternative.) | 22 |
| **Brain** | **bare ESP32-S3** (DevKitC-1 / WROOM-1 **N16R8**, octal PSRAM) | Hard requirement; PSRAM needed for the audio buffers (see `speaker-s3.yaml`). I²S out → DAC, second I²S in ← mic. | 16 |
| **DAC** | **GY-PCM5102 (PCM5102A) I²S DAC** | Cleaner SNR/THD than an integrated-DAC amp; self-generates MCLK (SCK→GND). | 6 |
| **Amp** | **TPA3116 mono class-D board** (12–24 V) | Real power headroom (~20 W into 8 Ω at 15 V) for music. Run gently — see notes. | 10 |
| **Power** | **CH224K USB-C PD trigger (15 V)** + **MP1584 buck (15→5 V)** | Single USB-C in: CH224K makes the 15 V amp rail, MP1584 drops it to 5 V for the S3. | 5 |
| **Mic** (secondary) | **ICS-43434 I²S MEMS**, gasket-isolated, front baffle | Intercom / voice capability; SEL→GND (left). | 6 |
| **Misc** | PTT button, foam gasket, wire, M2–M3 self-tap screws | — | 5 |

Total ≈ **$66–70/unit**, excluding a PD wall charger (reuse one that exposes a
15 V PDO; 12 V is not a guaranteed PD voltage, 15 V is).

## Pin map (ESP32-S3 — aligns with `devices/speaker-s3.yaml`)

| S3 pin | Dir | Net | Notes |
|---|---|---|---|
| GPIO5 | → | PCM5102 BCK | `i2s_bclk_pin` (existing) |
| GPIO6 | → | PCM5102 LCK | `i2s_lrclk_pin` (existing) |
| GPIO7 | → | PCM5102 DIN | `i2s_dout_pin` (existing) |
| GPIO15 | → | ICS-43434 SCK/BCLK | new mic I²S bus |
| GPIO16 | → | ICS-43434 WS/LRCL | new mic I²S bus |
| GPIO18 | ← | ICS-43434 SD (data) | `i2s_din_pin` |
| GPIO40 | ← | PTT button → GND | active-low, internal pull-up |
| 3V3 | → | PCM5102 VIN, ICS-43434 VDD | logic power |
| 5V | ← | MP1584 5.0 V out | board power |
| GND | — | common star ground | all grounds tie here |

Pins 5/6/7 are the existing DAC bus; 15/16/18/40 are free, non-strapping, and
clear of the octal-PSRAM pins (avoid GPIO 26–37, 0/3/45/46, USB 19/20).

## Wiring notes that bite if skipped

- **PCM5102 jumpers:** SCK→GND (PLL-generated MCLK), FMT→GND (I²S), XSMT→3V3
  (un-mute). No MCLK pin declared — correct.
- **Mono to the amp:** PCM5102 is a stereo DAC; set ESPHome `channel: mono`, wire
  **only L-out** to the TPA3116 IN+, leave R unconnected. No summing resistors.
- **TPA3116 gain:** set the **lowest gain (~20 dB)** jumper; the 100 W rating is
  far beyond a PS95-8. At 15 V you still have ~20 W — more than the driver wants.
- **One common star ground** at the CH224K output, or expect hum.
- **ICS-43434 SEL → GND** so it lands on the channel ESPHome reads.

## EQ / driver protection — server-side (Music Assistant)

No on-amp DSP in this build, so EQ and excursion protection live in **Music
Assistant per-player Audio DSP** on the speaker's media player:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | ~90 Hz | 12 dB/oct (Q≈0.7) | — |
| Tame sealed hump | Peaking | ~Fc (≈140–150 Hz) | Q≈1.5 | −2 to −4 dB |
| Warmth (optional) | Low shelf | ~200 Hz | — | +2 to +3 dB |

**Caveat — TTS/wake bypass MA DSP.** With ~20 W on tap and no hardware high-pass,
set a **conservative max-volume ceiling** in firmware/MA so bypassed TTS can't
over-excurse the driver. The sealed box itself limits sub-Fc excursion, which
helps. (This bypass hole is the one real cost of losing on-amp DSP.)

## Acoustic notes (sealed box)

- Keep **sealed** (predictable). Single driver reclaims one basket of volume —
  maximize the sealed chamber within the envelope.
- PS95 (Vas ≈ 1.1 L, Qts ≈ 0.69) in ~0.6 L → Qtc ≈ 1.1, Fc ≈ 146 Hz: a mild
  midbass hump then rolloff, flattened by the "tame sealed hump" biquad.
- **Optional bass extension (sound-first stretch):** a 3″ passive radiator tuned
  ~75 Hz adds real perceived midbass — the only way to buy low end in this volume.
  Costs sealed-box predictability; decide at build time.
- Light polyfill in the chamber.

## Case implications (feeds the geometry spec / `params.scad`)

- **One driver cutout**, centered, sized to the PS95-8 (cutout / screw pattern /
  seated depth **[confirm vs hardware]**), replacing the two 46 mm cutouts.
- **Electronics bay** now mounts more, smaller boards: S3, PCM5102 DAC, TPA3116,
  MP1584 buck, CH224K trigger. Plan standoffs / a sled; it's the densest zone.
  The freed second-driver baffle area helps the bay breathe.
- **Divider:** one sealed wire pass (single driver → single 2-conductor pass).
- **Mic** (secondary): gasket-isolated, front baffle, far from the driver to limit
  mechanical feedback. **PTT button** through the front. **USB-C** bottom exit.

## Out of scope (YAGNI)

- On-amp DSP (no in-stock standalone TAS5805M; EQ is server-side).
- Stereo (mono shared chamber; can't image at this size).
- Ported box (geometry-limited; passive radiator is the only bass lever).
- Far-field dual-mic array + AEC (intercom is secondary; single mic + PTT).

## Open / confirm before build

- PS95-8 cutout diameter / screw pattern / seated depth vs the baffle and 75 mm
  cavity (the limiting fit).
- USB-C source exposes a **15 V** PD profile (charger choice).
- Electronics-bay layout fits five small boards + button + mic + USB-C exit.
- Final sealed volume / Qtc after the single-driver baffle rework.
- Whether to add the optional passive radiator now or leave it sealed.
