# Terrace VoiceS3R — Dual-Amp Audio Output Design

**Date:** 2026-06-01
**Status:** Implemented (wiring + config)
**Device:** `devices/intercom-s3.yaml` (M5Stack ATOM Echo S3R / VoiceS3R)

## Goal

Drive two external speakers from the terrace VoiceS3R at the loudest *clean*
output the hardware allows, with the wiring kept as simple as possible.

## Decision

Two MAX98357A amps as **passive parallel listeners** on the second I²S bus,
both playing the **same mono mix** (dual mono, not stereo).

- **I²S (BCLK/LRC/DIN) → G5/G6/G7**, shared by both boards. I²S out is a
  broadcast: any number of sinks can listen to the same three wires, so adding
  the second amp is **wiring-only** — no ESPHome change. ESPHome sees one
  speaker (`s3_speaker_ext`, `channel: mono`).
- **GAIN → GND (direct) on both = 12 dB.** This is the simplest solder bridge,
  +3 dB over the 9 dB float. (15 dB would need a 100 kΩ resistor to GND, not a
  bare wire — a bare wire to GND is 12 dB.)
- **SD left floating (not connected).** These boards have a working SD pull-up
  (verified: they run with SD unwired), so SD defaults to enabled/left and the
  amps are always on. No GPIO, no software mute — G8 stays free. (A G8-driven
  `gpio` switch was prototyped and removed; if HA on/off is wanted later, wire
  both SD pins to a spare GPIO and add the switch back.)

## Why not stereo / per-amp channel resistors

The audio sources (intercom PTT, TTS, and mono-configured music pipeline) are
mono, so true L/R stereo buys nothing. Dual mono lets both amps share the same
left/mono slot with no channel-select resistors.

## What is NOT in software

- **GAIN stays hardware.** It is a 5-state analog comparator pin (3/6/9/12/15
  dB via VDD/GND/float/100 kΩ), not a logic input. A 3.3 V GPIO can only reach
  the extremes, the thresholds are referenced to the amp's 5 V VDD (so 3.3 V is
  ambiguous), and GAIN is sampled at power-up (GPIO floats at boot). Set it once
  in hardware; trim loudness in software instead.

## Findings from bring-up (lessons, so we don't relearn them)

- **These boards have a working SD pull-up.** They run with SD unwired
  (default enabled, left slot). The earlier doc claim that "clones lack the
  pull-up, so floating SD = shutdown" did **not** match this hardware — so SD is
  left floating and the amps are always on. (A G8-driven enable switch was
  prototyped, then removed once leaving SD bare proved reliable.)
- **GAIN→GND killing all sound was a faulty board.** A healthy GAIN pin is
  per-amp and high-impedance; it cannot silence the other amp. When one amp's
  GAIN→GND took out all output, the unit was bad — not the wiring or config.
- **"Raising GAIN does nothing" at max volume = already at the ceiling.** The
  amp's max output is supply-limited (~3.2 W/4 Ω at 5 V); once the digital path
  rails it, GAIN has no headroom to add. GAIN differences show only below the
  ceiling. (Also: GAIN is read at power-up — power-cycle the amp after rewiring.)

## Loudness ceiling and tuning follow-up

Maximum *clean* output is bounded by amp power (supply-limited), the 5 V supply
current (two amps can sag a weak USB feed → brownout/reboot — watch the
USB-CDC log), and the speaker drivers. Digital over-drive past 0 dBFS only adds
distortion, not loudness.

`voice_assistant.volume_multiplier` was dialed back from 4.0 to **2.0** — once
GAIN was set to +12 dB at the amp, the 4× digital boost clipped TTS. 2.0 is a
starting point; tune by ear (clean, not louder, is the win).

## ESPHome impact

None to the audio graph. The second amp is hardware fan-out, and SD is left
floating, so there's no extra GPIO. Doc/comment changes only.
