# Speaker case — hardware revision: sound-first, PR-loaded, intercom-capable (design)

Date: 2026-06-13
Status: design (approved — sound-first, ~1.5 L passive-radiator box), pending plan
**Supersedes most of `2026-06-13-speaker-case-design.md`:** that doc's two-driver,
sealed, 146×118×83 mm box is replaced by a single-driver, **passive-radiator,
~158×159×118 mm** enclosure. Its structure/print conventions still inform the
build, but the geometry must be re-derived (new envelope, single cutout, PR cutout,
no longer a simple sealed box). The geometry spec should be regenerated in the plan.

## Purpose

Best-sounding wall speaker that fits a still-reasonable envelope, with intercom +
voice provisioned as a second priority. Constraints: a **bare ESP32-S3** brain;
mid budget (~$50–90/unit).

## Why the old acoustic design was wrong (still applies)

1. **Dual 2″ side-by-side mono comb-filters** off-axis (first null ~29° at 5 kHz,
   worsening to 15 kHz) — an SPL trick that wrecks the speech/"air" band.
2. **One 3.5″ beats two 2″:** ~35 cm² vs ~24 cm² cone area, coherent point source,
   smooth polar response. Two 3.5″ wouldn't fit anyway.
3. **MAX98357A is too weak for 8 Ω** (~2 W ≈ 86 dB/1 m) — fine for voice, quiet for
   music. A sound-first device needs a real rail + amp.
4. **0.6 L sealed chokes the driver** (Vas ≈ 1.1 L): Qtc ≈ 1.1, Fc ≈ 146 Hz —
   boomy and no low end. More volume + a PR is the fix (below).

## Chosen architecture — bare S3 → I²S DAC → class-D amp, PR-loaded box

Standalone on-amp DSP (TAS5805M) only ships bundled with an ESP32 and is out of
stock, so EQ is server-side. Clean split: good I²S DAC for fidelity, powerful
analog class-D amp for output, into a single full-range in a passive-radiator box.

```
 USB-C PD charger (15 V, 30 W+)
   └─► CH224K (set 15 V) ─┬─► TPA3116 mono amp (VCC 15 V) ─► PS95-8 (8 Ω)
                          │        ▲ IN+  ◄── PCM5102 L-out (analog)   ║ side panel
                          └─► MP1584 buck → 5 V ─► ESP32-S3            ╚═► PR (tuned ~75 Hz)
 ESP32-S3 ── I²S out ─► PCM5102A DAC ── analog L ─► TPA3116
          ── I²S in  ◄─ ICS-43434 mic            (intercom — secondary)
          ── GPIO ────► PTT button → GND          (intercom — secondary)
 COMMON STAR GROUND: CH224K / TPA / buck / S3 / DAC / mic grounds all tied.
```

## Bill of materials (per unit, ~$83 — mid budget)

| Block | Part | Role / why | ~$ |
|---|---|---|---|
| **Driver** | **1× Dayton Audio PS95-8** — 3.5″ point-source full-range, 8 Ω, Fs ≈ 87 Hz | Coherent, smooth, more cone area than dual-2″. (TB W3-1364SA = fidelity alt.) | 22 |
| **Passive radiator** | **1× 3–4″ PR, Sd ≥ driver (~35–50 cm²), adjustable tuning mass** — side-mounted | Extends usable output to ~75–80 Hz in ~1.5 L; the only in-box bass lever | 15 |
| **Brain** | **bare ESP32-S3** (DevKitC-1 / WROOM-1 **N16R8**, octal PSRAM) | Hard requirement; PSRAM for audio buffers (`speaker-s3.yaml`) | 16 |
| **DAC** | **GY-PCM5102 (PCM5102A) I²S DAC** | Cleaner SNR/THD; self-generates MCLK (SCK→GND) | 6 |
| **Amp** | **TPA3116 mono class-D board** (12–24 V) | ~20 W into 8 Ω at 15 V; run gently (see notes) | 10 |
| **Power** | **CH224K PD trigger (15 V)** + **MP1584 buck (15→5 V)** | One USB-C in → 15 V amp rail + 5 V logic | 5 |
| **Mic** (2nd) | **ICS-43434 I²S MEMS**, gasket-isolated, front baffle, SEL→GND | Intercom / voice | 6 |
| **Misc** | PTT button, foam gaskets (driver, PR, lid), wire, M2–M3 screws | — | 6 |

Total ≈ **$83/unit**, excluding a 15 V-capable PD wall charger.

## Geometry (sound-first, ~1.5 L PR box)

- **External ≈ 158 W × 159 H × 118 D mm** (balanced growth from 146×118×83).
- Inner chamber ≈ **150 W × 103 H × 110 D = 1.70 L gross → ~1.5 L net** (after the
  PS95 basket, the PR, and polyfill). Assert `vol_target` ≈ **1.4 L** net floor.
- Vertical stack (inner): top wall 4 + **speaker/PR zone 103** + divider 4 + **board
  zone 44** + bottom wall 4 = 159.
- Sealed-equivalent at 1.5 L: Qtc ≈ 0.9, Fc ≈ 114 Hz; **PR tuned ~75 Hz** drops
  system F3 to ~75–80 Hz with a damped roll-off. Past ~2.5 L is diminishing returns.
- The PS95's 92 mm frame fills the front baffle → the **PR mounts on a side panel**
  (omnidirectional at LF; fixed panel, not the removable lid).

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

Pins 5/6/7 = existing DAC bus; 15/16/18/40 free, non-strapping, clear of octal-PSRAM
pins (avoid GPIO 26–37, 0/3/45/46, USB 19/20).

## Wiring notes that bite if skipped

- **PCM5102 jumpers:** SCK→GND, FMT→GND (I²S), XSMT→3V3 (un-mute). No MCLK pin.
- **Mono to the amp:** ESPHome `channel: mono`; wire **only L-out** → TPA3116 IN+.
- **TPA3116 gain:** lowest (~20 dB) jumper; ~20 W at 15 V is already more than the
  PS95 wants. **Hard volume ceiling** in firmware/MA (see EQ).
- **One common star ground** at the CH224K output, or expect hum.
- **PR tuning is empirical:** add/remove mass, measure, target Fb ~75 Hz; the PR's
  excursion limit, not the driver's, often sets max clean SPL — check both.

## EQ / driver protection — server-side (Music Assistant)

No on-amp DSP; EQ + protection live in MA per-player Audio DSP:

| Stage | Type | Freq | Q / slope | Gain |
|---|---|---|---|---|
| Protect excursion | High-pass | ~Fb (≈75–80 Hz) | 12–24 dB/oct | — |
| Gentle shape (if needed) | Peaking | ~110–120 Hz | Q≈1 | −1 to −2 dB |

The 1.5 L + PR alignment is fairly flat, so little corrective EQ is needed (vs the
boomy 0.6 L sealed box). **Caveat:** TTS/wake **bypass** MA DSP and there's no
hardware high-pass — below Fb a PR lets cone excursion run away, so the **HPF at Fb
+ a conservative max-volume ceiling are mandatory**, not optional.

## Case implications (feeds the regenerated geometry spec)

- **New external envelope ~158 × 159 × 118 mm**; re-derive all `params.scad`.
- **One driver cutout** (PS95-8: cutout / screw pattern / seated depth **[confirm]**),
  centered, taller speaker zone (103 mm) for the 92 mm frame.
- **PR cutout + gasket + screw bosses on one side panel.**
- **Electronics bay** mounts five small boards (S3, DAC, TPA3116, buck, PD trigger)
  + button + mic + USB-C exit — plan a sled/standoffs.
- **Divider:** one sealed wire pass (single driver). Box airtight except through the
  PR; PR perimeter gasketed.
- **Heavier, deeper box → stronger wall mount** (keyhole/bracket sized for the mass
  and tip-out moment).

## Out of scope (YAGNI)

- On-amp DSP (no in-stock standalone TAS5805M).
- Stereo (mono shared chamber).
- Active 2-way / in-box woofer (no volume for it — a separate sub is the answer for
  deeper bass).
- Far-field dual-mic array + AEC (intercom secondary; single mic + PTT).

## Open / confirm before build

- PS95-8 cutout / screw pattern / seated depth vs the baffle.
- PR part choice + side-panel location + tuning mass for Fb ~75 Hz.
- USB-C source exposes a **15 V** PD profile.
- Electronics-bay layout fits five boards + button + mic + USB-C exit.
- Final net volume / Qtc / Fb after the rework; set `vol_target`.
- Wall-mount rating for the larger/heavier box.
