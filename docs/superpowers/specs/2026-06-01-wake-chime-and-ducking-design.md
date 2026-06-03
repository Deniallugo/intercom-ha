# Wake acknowledgment chime + music ducking — design

**Date:** 2026-06-01
**Device:** `devices/intercom-s3.yaml` (Intercom S3 / VoiceS3R)
**Status:** approved, pending implementation plan

## Goal

When the wake word ("okay nabu") is recognized, the satellite should:

1. **Lower the music** so the voice exchange is clearly audible.
2. **Play a short acknowledgment sound** so the user knows the command was heard.

Both behaviors should begin the instant the command is recognized and end when the
voice interaction is over.

## Decisions

- **Sound source:** on-device generated tone (offline, instant, no extra infra).
- **Ducking:** heavy (~20 dB reduction, music nearly silent), restored when the
  interaction ends.

## Where it hooks in

The voice flow already exposes the trigger points we need:

- `micro_wake_word.on_wake_word_detected` — fires the moment the wake word is
  recognized. Today it only calls `voice_assistant.start`.
- `voice_assistant` triggers — we add `on_end` and `on_error` to know when the
  exchange has finished (or failed).

## Component 1 — Acknowledgment chime (on-device tone)

On wake detection, generate a short sine-sweep chime in a lambda and play it through
the mixer's announcement source (`s3_announcement_src`) via the `speaker.play` action.

- **Shape:** ~120 ms, 800 → 1200 Hz rising sweep, 5 ms linear fade in/out — matching
  the "chime-in" aesthetic already used server-side in `intercom-addon/chimes.py`.
- **Format:** 48000 Hz / 16-bit signed / mono — matches `s3_speaker_ext`, the mixer's
  output speaker.
- **Generation:** built once into a function-static `std::vector<uint8_t>` and replayed
  on each wake. The buffer is ~11 KB (5760 samples), so cost is negligible.

### Why this doesn't fight the mic

The chime plays on `i2s_bus_ext` (the external MAX98357A bus). The mic captures on
`i2s_bus` (the internal ES8311 bus). These are two separate I²S peripherals with
separate mutexes, so the chime can sound immediately while the wake-word engine / STT
keeps using the mic. The chime also mixes *over* any playing music via the mixer rather
than interrupting the media pipeline.

The 120 ms chime plays at wake detection, before the user begins speaking, so feedback
into the STT mic is minimal and acceptable.

## Component 2 — Music ducking (heavy, restore on end)

Use the mixer's `mixer_speaker.apply_ducking` action on the music source
`s3_media_src`:

- **On wake detection:** `decibel_reduction: 20` with a short ramp (~0.3 s) so the drop
  is smooth rather than abrupt.
- **On `voice_assistant.on_end` and `on_error`:** `decibel_reduction: 0` with a ~0.5 s
  ramp to bring the music back. Restoring in **both** handlers guarantees the music
  never stays stuck quiet if a pipeline errors out partway through.

## Order of actions at wake

Inside the existing `on_wake_word_detected` block:

1. Duck `s3_media_src` (apply 20 dB reduction).
2. Play the chime into `s3_announcement_src`.
3. `voice_assistant.start` (unchanged).

## Out of scope / unchanged

- The existing `media_player` `on_announcement` / `on_idle` mic-mutex coordination.
- `volume_min` / `volume_max`, `volume_multiplier`, gain settings.
- The push-to-talk button recording/upload path.

## Risk to verify on hardware

`speaker.play` writing raw PCM directly into a mixer source speaker (bypassing the
`media_player`) is the standard ESPHome pattern for on-device sound effects, but it
cannot be confirmed without flashing the device. If it misbehaves (e.g. contention with
the media_player's announcement pipeline, or wrong audio format on the mixer source),
the fallback is to serve the chime as a small WAV from `intercom-addon` and play it via
`media_player.play_announcement`. This fallback is noted but not implemented unless the
on-device path fails verification.
