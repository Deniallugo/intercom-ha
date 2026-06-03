# Wake Chime + Music Ducking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the wake word is recognized, duck the music ~20 dB and play a short on-device acknowledgment chime, restoring the music when the voice interaction ends.

**Architecture:** Pure ESPHome-config change in one file. Ducking uses the existing mixer's `mixer_speaker.apply_ducking` action on the music source `s3_media_src`. The chime is a sine-sweep PCM buffer generated in a lambda and played through the announcement mixer source `s3_announcement_src` via `speaker.play`. Trigger points already exist: `micro_wake_word.on_wake_word_detected` (duck + chime + start) and `voice_assistant` `on_end` / `on_error` (restore).

**Tech Stack:** ESPHome (esp-idf framework), C++ lambdas, the `mixer`/`speaker` ESPHome components.

---

## File Structure

- **Modify:** `devices/intercom-s3.yaml`
  - `voice_assistant:` block (currently lines ~281-287) — add `on_end` and `on_error` handlers that restore ducking.
  - `micro_wake_word:` `on_wake_word_detected:` block (currently lines ~301-303) — prepend ducking + chime before the existing `voice_assistant.start`.

No other files change. No new files.

### Notes for the engineer (zero-context assumptions)

- `s3_media_src` and `s3_announcement_src` are the two **mixer source speakers** defined under `speaker:` → `platform: mixer` (`s3_mixer`). The mixer output is `s3_speaker_ext` at **48000 Hz / 16-bit / mono** — the chime PCM must match that format.
- `mixer_speaker.apply_ducking` reduces a source speaker's level by `decibel_reduction` dB over an optional `duration` ramp. Reduction `0` = full volume (restore).
- `speaker.play` plays a raw PCM byte vector on a speaker. Returning the bytes from a `!lambda` lets us synthesize the tone in C++.
- Lambdas compile inside ESPHome's generated C++. Keep them dependency-light: avoid `std::max`/`M_PI` (may not be in scope) — use plain arithmetic and a numeric `2*pi` literal. `sinf` from `<math.h>` is available.

---

## Task 1: Restore ducking when the voice interaction ends

**Files:**
- Modify: `devices/intercom-s3.yaml` (the `voice_assistant:` block)

- [ ] **Step 1: Add `on_end` and `on_error` handlers to `voice_assistant`**

Find this block:

```yaml
voice_assistant:
  id: va
  microphone: s3_mic
  media_player: s3_player
  noise_suppression_level: 2
  auto_gain: 31dBFS
  volume_multiplier: 2.0       # was 2.0 — boost TTS playback for external amp
```

Replace it with (append the two handlers — everything above is unchanged):

```yaml
voice_assistant:
  id: va
  microphone: s3_mic
  media_player: s3_player
  noise_suppression_level: 2
  auto_gain: 31dBFS
  volume_multiplier: 2.0       # was 2.0 — boost TTS playback for external amp
  # Restore the music we ducked on wake-word detection. Both handlers fire so
  # the music never stays stuck quiet if the pipeline errors out partway.
  on_end:
    - mixer_speaker.apply_ducking:
        id: s3_media_src
        decibel_reduction: 0
        duration: 0.5s
  on_error:
    - mixer_speaker.apply_ducking:
        id: s3_media_src
        decibel_reduction: 0
        duration: 0.5s
```

- [ ] **Step 2: Validate the config parses**

Run: `esphome config devices/intercom-s3.yaml`
Expected: exits 0 and prints the fully-rendered config with no schema errors. Confirm the `on_end` / `on_error` keys are accepted under `voice_assistant` (no "[on_end] is an invalid option" error).

- [ ] **Step 3: Commit**

```bash
git add devices/intercom-s3.yaml
git commit -m "feat(s3): restore music ducking on voice_assistant end/error"
```

---

## Task 2: Duck music + play chime on wake-word detection

**Files:**
- Modify: `devices/intercom-s3.yaml` (the `micro_wake_word:` → `on_wake_word_detected:` block)

- [ ] **Step 1: Replace the `on_wake_word_detected` handler**

Find this block:

```yaml
  on_wake_word_detected:
    - voice_assistant.start:
        wake_word: !lambda return wake_word;
```

Replace it with:

```yaml
  on_wake_word_detected:
    # 1. Duck music hard (~20 dB) with a short ramp so the drop isn't jarring.
    - mixer_speaker.apply_ducking:
        id: s3_media_src
        decibel_reduction: 20
        duration: 0.3s
    # 2. Acknowledgment chime: 120 ms 800->1200 Hz sine sweep, 5 ms fades,
    #    48 kHz / 16-bit / mono (matches s3_speaker_ext). Generated once into a
    #    function-static buffer and replayed on each wake. Plays on the external
    #    bus (i2s_bus_ext), which does NOT share the mic's mutex, so it sounds
    #    immediately and mixes over any music. Matches intercom-addon/chimes.py.
    - speaker.play:
        id: s3_announcement_src
        data: !lambda |-
          static std::vector<uint8_t> chime;
          if (chime.empty()) {
            const int sr = 48000;
            const int n = sr * 120 / 1000;        // 120 ms
            int nf = sr * 5 / 1000;               // 5 ms fade
            if (nf < 1) nf = 1;
            const float f0 = 800.0f, f1 = 1200.0f, amp = 16000.0f;
            const float two_pi = 6.28318530718f;
            chime.reserve(n * 2);
            for (int i = 0; i < n; i++) {
              float t = (float) i / sr;
              float freq = f0 + (f1 - f0) * ((float) i / n);
              float env = 1.0f;
              if (i < nf) env = (float) i / nf;
              else if (i > n - nf) env = (float) (n - i) / nf;
              int16_t s = (int16_t) (sinf(two_pi * freq * t) * env * amp);
              chime.push_back((uint8_t) (s & 0xFF));
              chime.push_back((uint8_t) ((s >> 8) & 0xFF));
            }
          }
          return chime;
    # 3. Hand off to the HA Assist pipeline (unchanged behavior).
    - voice_assistant.start:
        wake_word: !lambda return wake_word;
```

- [ ] **Step 2: Validate the config and lambda compile**

Run: `esphome config devices/intercom-s3.yaml`
Expected: exits 0, no schema errors. This catches YAML/action-name mistakes (e.g. wrong `mixer_speaker.apply_ducking` / `speaker.play` keys).

- [ ] **Step 3: Compile to confirm the lambda builds**

Run: `esphome compile devices/intercom-s3.yaml`
Expected: build succeeds (the C++ lambda compiles — catches `sinf`/type errors). This is slower (full firmware build); allow several minutes.

- [ ] **Step 4: Commit**

```bash
git add devices/intercom-s3.yaml
git commit -m "feat(s3): duck music and chime on wake-word detection"
```

---

## Task 3: Verify on hardware

**Files:** none (manual verification on the device).

- [ ] **Step 1: Flash the device**

Run: `./flash.sh intercom-s3`
Expected: upload completes (OTA or USB) and the device reboots and reconnects to HA.

- [ ] **Step 2: Verify with no music playing**

Say "okay nabu". Expected: a short rising chime plays immediately, then the normal Assist listening behavior. Watch the USB-CDC logs (`logger` is VERBOSE) for the `speaker.play` activity and no "Parent bus is busy" errors.

- [ ] **Step 3: Verify with music playing**

Start music (Music Assistant / Spotify) on the `${friendly_name} Player`. Say "okay nabu". Expected:
  - Music volume drops sharply (~20 dB) within ~0.3 s.
  - The chime plays over the ducked music.
  - After the interaction ends (or TTS reply finishes), music ramps back to full over ~0.5 s.

- [ ] **Step 4: Verify error-path restore**

Trigger a pipeline error if convenient (e.g. wake then stay silent until timeout). Expected: music still ramps back to full — `on_error` (or `on_end`) restores ducking; music is never left stuck quiet.

### If on-device playback fails (fallback)

If Step 2/3 shows the chime not playing, audio glitching, or media_player contention on `s3_announcement_src`, fall back to the spec's HTTP-served chime: serve a small WAV from `intercom-addon` and play it via `media_player.play_announcement` instead of `speaker.play`. Keep the ducking (Tasks 1-2 ducking parts) as-is; only the chime delivery changes. Re-open the spec at `docs/superpowers/specs/2026-06-01-wake-chime-and-ducking-design.md` before implementing the fallback.
