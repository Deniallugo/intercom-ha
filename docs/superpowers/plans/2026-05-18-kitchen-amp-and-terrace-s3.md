# Kitchen amp upgrade + terrace ESP32-S3 build implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-route the kitchen Atom Echo's I²S output to an external MAX98357A + 3″ driver via the Grove port (one-line YAML change + hardware assembly), and bring up a new ESP32-S3-based terrace device with stereo PCM5102 DAC + TPA3116D2 amp + 2× Visaton FRS 8 drivers + INMP441 mic + IP54 enclosure, running both intercom (PTT + wake word) and Home Assistant voice-assistant flows.

**Architecture:** Kitchen stays an Atom Echo — only the I²S DOUT pin moves from the internal NS4168 (GPIO22) to the Grove port (GPIO26) where an external Class-D amp drives a real 3″ driver. Terrace is a from-scratch ESPHome device with a stereo audio chain (44.1 kHz I²S → PCM5102 → analog → TPA3116D2 → 2× 3.3″ full-range), mic on a separate I²S bus, and the same recorder.h/uploader.h glue as the kitchen.

**Tech Stack:** ESPHome (esp-idf framework), C++ headers (`recorder.h`, `uploader.h` — already in tree), MAX98357A I²S Class-D amp, PCM5102 I²S DAC, TPA3116D2 analog Class-D amp, Visaton FRS 8 / Dayton DMA70-4 full-range drivers, INMP441 I²S MEMS mic.

**Spec:** [docs/superpowers/specs/2026-05-18-kitchen-amp-and-terrace-s3-design.md](../specs/2026-05-18-kitchen-amp-and-terrace-s3-design.md)

**Prerequisite:** [Intercom features plan](./2026-05-18-intercom-features.md) **must be merged first** — this plan depends on `recorder_start_vad()`, mic-always-on, and the `micro_wake_word` handler that plan introduces to `atom-echo.yaml`.

---

## File map

### Modified files
- `atom-echo.yaml` — one-line change: `i2s_dout_pin: GPIO22` → `GPIO26`

### New files
- `intercom-s3.yaml` — complete ESPHome config for the new terrace device

### Unchanged (but used by the new device)
- `recorder.h`, `uploader.h` — reused as-is; new device's YAML includes them

### Hardware deliverables
- One assembled MAX98357A + DMA70-4 speaker box wired to the Atom Echo's Grove port (kitchen)
- One assembled ESP32-S3 + PCM5102 + TPA3116D2 + 2× FRS 8 cabinets + IP54 box (terrace)

---

## Task 1: Verify prerequisites

**Files:** none — read-only verification.

- [ ] **Step 1: Confirm intercom-features changes are on `main`**

Run:
```bash
git log --oneline main | grep -iE "(wake.?word|recorder.*vad|mic.*always)" | head -5
```
Expected: at least one commit referencing wake-word, VAD, or mic-always-on. If empty, **stop** — pause this plan and finish the intercom-features plan first.

- [ ] **Step 2: Confirm `recorder.h` has VAD mode**

Run:
```bash
grep -nE "(REC_VAD|recorder_start_vad)" /Users/danillugovskoy/own/intercom/recorder.h
```
Expected: at least one match for `REC_VAD` (enum) and one for `recorder_start_vad` (function).

- [ ] **Step 3: Confirm `atom-echo.yaml` has `micro_wake_word`**

Run:
```bash
grep -n "micro_wake_word" /Users/danillugovskoy/own/intercom/atom-echo.yaml
```
Expected: at least one match. If empty, **stop**.

- [ ] **Step 4: Confirm baseline compile is green**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config atom-echo.yaml > /tmp/atom-echo-precheck.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`. If non-zero, fix the baseline before proceeding.

---

## Task 2: Kitchen — procure and assemble external speaker board

**Files:** none — physical build.

**BOM (~$32):**
- 1× MAX98357A breakout (Adafruit or AliExpress clone)
- 1× Dayton Audio DMA70-4 (3″, 4Ω, full-range) — or equivalent 3″ 4Ω full-range driver ≥86 dB sensitivity
- 1× small sealed or ported enclosure, ~0.2 L (3D-printed, cheap project box, or repurposed bookshelf cab)
- 1× 4-pin Grove cable (cut one end for bare wires)
- ~30 cm of speaker wire
- Header pins / Dupont jumpers for the side-pin tap

- [ ] **Step 1: Confirm parts on hand**

Visually verify all parts present. The Grove cable colors are: red=5V, black=GND, yellow=GPIO26, white=GPIO32.

- [ ] **Step 2: Solder MAX98357A header pins (if breakout shipped unpopulated)**

Solder the 7-pin header onto the breakout (VIN, GND, SD, GAIN, DIN, BCLK, LRC).

- [ ] **Step 3: Mount driver in enclosure**

Cut a 65 mm hole in the enclosure baffle (DMA70-4 cutout diameter — verify against driver datasheet before cutting). Mount the driver with 4× M3 screws. Solder ~10 cm leads to the driver's `+` and `-` terminals (red on `+`).

- [ ] **Step 4: Wire MAX98357A to the driver**

| MAX98357A pin | Driver |
|---|---|
| `+` output | Driver `+` |
| `-` output | Driver `-` |

Keep the speaker wire short (<30 cm).

- [ ] **Step 5: Place MAX98357A inside the enclosure, with input header accessible**

Either pass the I²S input wires out through a small hole and seal with hot glue, or mount the MAX98357A on the outside of the box with a short cable to the driver.

---

## Task 3: Kitchen — wire MAX98357A to the Atom Echo

**Files:** none — soldering.

- [ ] **Step 1: Identify Atom Echo pin exposure**

The Atom Echo has:
- Grove port on the side (4 pins: 5V, GND, GPIO26, GPIO32)
- A row of side header pads exposing GPIO19, GPIO21, GPIO22, GPIO23, GPIO25, GPIO33

For this build we need 5V, GND, GPIO19 (BCLK), GPIO33 (LRCLK) from the side header, and GPIO26 (DIN) from the Grove port.

- [ ] **Step 2: Wire from Grove**

Cut one end off the Grove cable. Strip and tin the 4 wires.

| Grove wire | MAX98357A |
|---|---|
| Red (5V) | VIN |
| Black (GND) | GND |
| Yellow (GPIO26) | DIN |
| White (GPIO32) | not used (cut or insulate) |

- [ ] **Step 3: Wire BCLK and LRCLK from the side header**

Solder thin wires (or use Dupont sockets if the side header is populated):

| Atom Echo side pin | MAX98357A |
|---|---|
| GPIO19 | BCLK |
| GPIO33 | LRC |

- [ ] **Step 4: Leave GAIN and SD pins per defaults**

- GAIN: leave floating for default 9 dB. (Optional: tie to GND for +12 dB if final volume is still too low after the YAML/flash step.)
- SD: leave open (always-on).

- [ ] **Step 5: Mechanical assembly**

Plug the Grove cable into the Atom Echo's Grove port. Route the side-header wires neatly. Place the assembled speaker box near the Atom Echo or on a kitchen surface.

---

## Task 4: Kitchen — update atom-echo.yaml

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/atom-echo.yaml` (one line)

- [ ] **Step 1: Change the I²S DOUT pin**

Edit `atom-echo.yaml`. Find:

```yaml
speaker:
  - platform: i2s_audio
    id: atom_speaker
    i2s_audio_id: i2s_out
    i2s_dout_pin: GPIO22
```

Change to:

```yaml
speaker:
  - platform: i2s_audio
    id: atom_speaker
    i2s_audio_id: i2s_out
    i2s_dout_pin: GPIO26
```

(Only `i2s_dout_pin: GPIO22` → `i2s_dout_pin: GPIO26`. Everything else in that block unchanged.)

- [ ] **Step 2: Validate config**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config atom-echo.yaml > /tmp/atom-echo-validate.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`, and the resolved config in the log shows `i2s_dout_pin: 26`.

If a `pin conflict` or similar error appears, double-check that `GPIO26` is not declared anywhere else (e.g. as `allow_other_uses: true` on a separate bus). It should not be in stock `atom-echo.yaml`.

- [ ] **Step 3: Compile**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome compile atom-echo.yaml 2>&1 | tail -15
```
Expected: ends with `INFO Successfully compiled program.` and a `.bin` path.

---

## Task 5: Kitchen — flash and smoke test

**Files:** none — runtime verification.

- [ ] **Step 1: Flash via OTA**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome upload atom-echo.yaml --device atom-echo-<mac-suffix>.local
```
(Substitute the actual hostname — find it via the Atom Echo's existing logs or `dns-sd -B _esphomelib._tcp` on macOS.)

Expected: `INFO OTA successful` and a reboot. Device reconnects to WiFi within ~10 s.

- [ ] **Step 2: Smoke test announcement playback**

In Home Assistant, call:
- Service: `media_player.play_media`
- Target: `media_player.atom_echo_<mac>_player`
- Data: `media_content_type: music`, `media_content_id: https://github.com/anars/blank-audio/raw/master/250-milliseconds-of-silence.mp3` (or any short clip)

Actually use a tone for audibility: `media_content_id: media-source://tts/cloud?message=hello`.

Expected: external speaker emits the TTS clearly. Internal Atom Echo speaker is silent (NS4168 idling with no data).

- [ ] **Step 3: Smoke test intercom button**

Press the Atom Echo button. Watch HA addon logs (`docker logs <addon>`) for an incoming POST to `/intercom`. Expected: a session ID logged, audio streamed, and (if routing is configured) playback on configured target speakers.

- [ ] **Step 4: Verify volume is acceptable**

Subjective check: at 1 m from the speaker, TTS playback should be clearly audible from anywhere in a typical kitchen with background appliance noise.

If still too quiet: tie MAX98357A GAIN pin to GND for +3 dB.

- [ ] **Step 5: Commit kitchen YAML change**

```bash
cd /Users/danillugovskoy/own/intercom
git add atom-echo.yaml
git commit -m "feat(atom-echo): route I2S DOUT to Grove for external amp

Moves the speaker's i2s_dout_pin from GPIO22 (internal NS4168) to GPIO26
(Grove port) so an external MAX98357A + 3-inch driver can be hung off the
Atom Echo without disassembly. The internal amp keeps receiving clocks but
no data, so it sits silent.

Hardware mod side: MAX98357A breakout wired with VIN/GND from Grove 5V/GND,
BCLK from GPIO19 (side header), LRC from GPIO33 (side header), DIN from
GPIO26 (Grove)."
```

---

## Task 6: Terrace — procure parts

**Files:** none — physical procurement.

**BOM (~$136):**

| Part | Qty | Source / model |
|---|---|---|
| ESP32-S3-DevKitC-1 (N8R8 or N16R8) | 1 | M5Stack / Espressif / DevKit-compatible |
| PCM5102 (or PCM5102A) I²S DAC breakout | 1 | AliExpress "PCM5102 stereo DAC" |
| TPA3116D2 stereo amp board, plain analog input, 12–24 V | 1 | AliExpress "TPA3116D2 80W×2 dual channel" — **no Bluetooth / DSP / SD-card variants** |
| Visaton FRS 8 (3.3″, 4Ω, 87 dB) | 2 | Or Dayton DMA70-4 equivalent |
| MDF / 3D-printed enclosure for each driver | 2 | ~0.7 L ported, port tuned ~100 Hz |
| INMP441 I²S MEMS mic breakout | 1 | AliExpress "INMP441 module" |
| Foam windscreen | 1 | Cut from cheap headset cover |
| 12 mm panel-mount momentary tactile button | 1 | Any |
| WS2812 RGB LED (single or short strip) | 1 | Any |
| 12 V 3 A barrel-jack PSU | 1 | Any |
| MP1584EN buck converter module (12 V → 5 V, 2 A) | 1 | AliExpress |
| IP54 plastic enclosure ~150 × 100 × 60 mm | 1 | Any |
| Speaker grille cloth | 1 | Auto-parts store or repair shop |
| Speaker terminals + spade connectors | 2 sets | Any |
| Strain-relief cable gland (12 V mains entry) | 1 | Any |
| Hookup wire, twisted analog cable, foam, hot glue | – | Stock |

- [ ] **Step 1: Confirm all parts present**

Lay out and visually verify each item.

- [ ] **Step 2: Inspect TPA3116D2 board**

Verify: (a) only RCA / analog terminal inputs visible, (b) no Bluetooth antenna or pairing button, (c) no SD card slot. If it has any of those, the input is hijacked — return / replace.

- [ ] **Step 3: Inspect PCM5102 board**

Flip board over. Find the `SCK` pin pad. Verify it's bridged to GND (a solder blob or trace tying SCK to the adjacent GND pad on the back). If not bridged: solder a bridge with iron + solder, otherwise step 12 of Task 8 will need a fourth GPIO.

---

## Task 7: Terrace — build speaker cabinets

**Files:** none — physical build.

Skip this task if you bought pre-built enclosures.

- [ ] **Step 1: Cut MDF (or print) two identical enclosures**

Target: ~0.7 L internal volume per cabinet (e.g. 150 × 100 × 70 mm internal). Use 12 mm MDF or 3 mm walls for PETG print.

- [ ] **Step 2: Cut driver mounting hole**

Diameter: per FRS 8 datasheet cutout (~75 mm). Use a hole saw or router circle jig.

- [ ] **Step 3: Cut port hole**

Port: 30 mm diameter × 60 mm long PVC tube, tuned to ~100 Hz. Mount with hot glue or press-fit.

- [ ] **Step 4: Mount drivers**

Glue grille cloth on the inside of the front baffle behind the driver hole. Mount each FRS 8 with 4× M4 screws. Run a short twisted pair from the driver `+` / `-` terminals to a binding post or speaker terminal on the back panel.

- [ ] **Step 5: Seal cabinet seams with hot glue or silicone**

Air-tight (apart from the port) — leaks reduce bass.

---

## Task 8: Terrace — create intercom-s3.yaml skeleton

**Files:**
- Create: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

- [ ] **Step 1: Write the skeleton (no audio yet)**

Create `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`:

```yaml
substitutions:
  name: intercom-terrace
  friendly_name: Intercom Terrace

esphome:
  name: ${name}
  friendly_name: ${friendly_name}
  name_add_mac_suffix: true
  includes:
    - recorder.h
    - uploader.h
  on_boot:
    - priority: 600.0
      then:
        - lambda: recorder_init();
    - priority: 200.0
      then:
        - lambda: |-
            id(terrace_mic).add_data_callback([](const std::vector<uint8_t>& data) {
              recorder_on_data(data.data(), data.size());
            });

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf

logger:

api:
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "${name} Fallback"
    password: !secret ap_password

captive_portal:
```

- [ ] **Step 2: Validate skeleton compiles**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-skel.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`. (The skeleton references `terrace_mic` which doesn't exist yet — the lambda is text, not validated at this stage. If ESPHome rejects it, comment out the `on_boot priority: 200.0` block until Task 9 adds the mic.)

If commented out, leave a `# TODO: re-enable after Task 9` marker.

---

## Task 9: Terrace — add audio I/O blocks

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

- [ ] **Step 1: Add i2s_audio, microphone, speaker blocks**

Append to `intercom-s3.yaml` (after `captive_portal:`):

```yaml
# ── Audio hardware ────────────────────────────────────────────────────────────

i2s_audio:
  - id: i2s_in
    i2s_lrclk_pin: GPIO16
    i2s_bclk_pin:  GPIO15
  - id: i2s_out
    i2s_lrclk_pin: GPIO6
    i2s_bclk_pin:  GPIO5

microphone:
  - platform: i2s_audio
    id: terrace_mic
    i2s_audio_id: i2s_in
    i2s_din_pin: GPIO17
    adc_type: external
    pdm: false
    sample_rate: 16000
    correct_dc_offset: true

# Speaker: 44.1 kHz stereo for music; ESPHome auto-resamples 16 kHz mono
# announcements / intercom playback through the same pipeline.
speaker:
  - platform: i2s_audio
    id: terrace_speaker
    i2s_audio_id: i2s_out
    i2s_dout_pin: GPIO7
    dac_type: external
    bits_per_sample: 16bit
    sample_rate: 44100
    channel: stereo
```

- [ ] **Step 2: Re-enable the mic callback if commented in Task 8**

If you left the `priority: 200.0` `on_boot` block commented, uncomment now.

- [ ] **Step 3: Validate**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-audio.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`. If `channel: stereo` is rejected by your ESPHome version, see Open Items in the spec — fallback is two separate `speaker` entries, one per channel. For now, leave `stereo` and resolve at flash time.

---

## Task 10: Terrace — add media_player

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

- [ ] **Step 1: Add media_player block**

Append:

```yaml
# ── Media player (HA-controllable playback) ──────────────────────────────────

media_player:
  - platform: speaker
    id: terrace_player
    name: "${friendly_name} Player"
    buffer_size: 65536        # PSRAM-backed; bigger buffer for music streams
    media_pipeline:
      speaker: terrace_speaker
      format: FLAC
    announcement_pipeline:
      speaker: terrace_speaker
      format: WAV
```

- [ ] **Step 2: Validate**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-player.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`.

---

## Task 11: Terrace — add status LED and PTT button

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

- [ ] **Step 1: Add light + binary_sensor blocks**

Append:

```yaml
# ── Status LED (single WS2812 on GPIO8) ──────────────────────────────────────

light:
  - platform: esp32_rmt_led_strip
    rgb_order: GRB
    chipset: WS2812
    pin: GPIO8
    num_leds: 1
    name: "Status LED"
    id: status_led
    restore_mode: ALWAYS_OFF

# ── Push-to-talk button (GPIO9, active LOW with pull-up) ─────────────────────

binary_sensor:
  - platform: gpio
    pin:
      number: GPIO9
      inverted: true
      mode:
        input: true
        pullup: true
    name: "Button"
    on_press:
      - if:
          condition:
            lambda: 'return uploader_is_uploading();'
          then:
            - logger.log: "button ignored — upload in progress"
          else:
            - light.turn_on:
                id: status_led
                red: 0%
                green: 0%
                blue: 100%
            - lambda: |-
                recorder_start();
                id(terrace_mic).start();
                uploader_start("http://homeassistant.local:9999/intercom", App.get_name().c_str());
    on_release:
      - delay: 0.1s
      - lambda: |-
          id(terrace_mic).stop();
          recorder_stop();
      - light.turn_on:
          id: status_led
          red: 100%
          green: 100%
          blue: 0%
      - wait_until:
          condition:
            lambda: 'return !uploader_is_uploading();'
          timeout: 10s
      - light.turn_off: status_led
```

- [ ] **Step 2: Validate**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-button.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`.

---

## Task 12: Terrace — add voice_assistant block

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

- [ ] **Step 1: Add voice_assistant block**

Append (mirrors `listen_and_answer.yaml` indicator behavior, adapted for the new pin/light IDs):

```yaml
# ── HA voice-assistant satellite ─────────────────────────────────────────────

voice_assistant:
  microphone: terrace_mic
  speaker: terrace_speaker
  noise_suppression_level: 2
  auto_gain: 31dBFS
  volume_multiplier: 2.0
  on_listening:
    - light.turn_on:
        id: status_led
        red: 0%
        green: 0%
        blue: 100%
  on_stt_end:
    - light.turn_on:
        id: status_led
        red: 100%
        green: 100%
        blue: 0%
  on_tts_start:
    - light.turn_on:
        id: status_led
        red: 0%
        green: 100%
        blue: 0%
  on_end:
    - light.turn_off: status_led
  on_error:
    - light.turn_on:
        id: status_led
        red: 100%
        green: 0%
        blue: 0%
    - delay: 0.1s
    - light.turn_off: status_led
```

- [ ] **Step 2: Validate**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-va.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`.

---

## Task 13: Terrace — add micro_wake_word with two phrase placeholders

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml`

The wake-word phrases are an open item — for now configure with two **placeholder** prebuilt models so the file compiles. The actual phrase choice happens in Task 17 once we can hear the device on the bench.

- [ ] **Step 1: Add micro_wake_word block**

Append:

```yaml
# ── Wake-word dispatch: phrase A → intercom, phrase B → voice assistant ──────

micro_wake_word:
  models:
    - model: okay_nabu          # ← intercom trigger (placeholder; finalize in Task 17)
    - model: hey_jarvis         # ← voice-assistant trigger (placeholder)
  on_wake_word_detected:
    - if:
        condition:
          # Branch on which model fired. wake_word string matches the model name.
          lambda: 'return wake_word == "okay_nabu";'
        then:
          - if:
              condition:
                lambda: 'return uploader_is_uploading() || recorder_is_active();'
              then:
                - logger.log: "wake word (intercom) ignored — busy"
              else:
                - light.turn_on: { id: status_led, red: 0%, green: 0%, blue: 100% }
                - lambda: |-
                    recorder_start_vad();
                    uploader_start("http://homeassistant.local:9999/intercom",
                                   App.get_name().c_str());
                - wait_until:
                    condition:
                      lambda: 'return !uploader_is_uploading();'
                    timeout: 20s
                - light.turn_off: status_led
        else:
          - voice_assistant.start
```

- [ ] **Step 2: Validate**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome config intercom-s3.yaml > /tmp/s3-mww.log 2>&1; echo "exit=$?"
```
Expected: `exit=0`.

If ESPHome rejects the `wake_word` lambda variable name (it varies by version), check the resolved config for the actual name (`detected_word`, `phrase`, etc.) and update the lambda.

- [ ] **Step 3: Compile the full file**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome compile intercom-s3.yaml 2>&1 | tail -15
```
Expected: `INFO Successfully compiled program.` and a `.bin` path under `.esphome/build/intercom-terrace/`.

- [ ] **Step 4: Commit the YAML**

```bash
cd /Users/danillugovskoy/own/intercom
git add intercom-s3.yaml
git commit -m "feat(intercom-s3): add ESP32-S3 terrace device config

New ESPHome config for the stereo terrace device:
- PCM5102 I2S DAC -> TPA3116D2 analog amp -> 2x FRS 8 stereo
- INMP441 I2S mic on separate bus
- Button (GPIO9) for PTT intercom override
- WS2812 status LED (GPIO8)
- voice_assistant satellite block (mirrors listen_and_answer.yaml)
- micro_wake_word with two placeholder models; phrase finalization
  deferred to bench testing once hardware is built

Reuses recorder.h / uploader.h from the kitchen build. POSTs intercom
audio to the same /intercom endpoint."
```

---

## Task 14: Terrace — bench-wire electronics on breadboard

**Files:** none — physical build.

Pre-enclosure dry-fit. Goal: prove the electronics work before committing to a cabinet layout.

- [ ] **Step 1: Wire ESP32-S3 to PCM5102**

| ESP32-S3 | PCM5102 |
|---|---|
| 3.3 V | VIN |
| GND | GND |
| GPIO5 | BCK |
| GPIO6 | LCK |
| GPIO7 | DIN |

- [ ] **Step 2: Wire PCM5102 to TPA3116D2 input**

Use a short twisted pair (~10 cm). Twist the L and R signal wires with their own ground reference.

| PCM5102 | TPA3116D2 |
|---|---|
| LOUT | L IN (signal) |
| ROUT | R IN (signal) |
| AGND (analog ground) | IN GND |

- [ ] **Step 3: Wire 12 V PSU to TPA3116D2 PVDD**

| PSU | TPA3116D2 |
|---|---|
| 12 V | VCC / V+ |
| GND | GND |

- [ ] **Step 4: Wire buck converter (12 V → 5 V) for the ESP32-S3**

| 12 V rail | MP1584EN | ESP32-S3 |
|---|---|---|
| 12 V | IN+ | – |
| GND | IN− / OUT− | GND |
| – | OUT+ (set to 5 V via on-board pot) | 5V (or VIN) |

**Critical:** before connecting OUT+ to the ESP32-S3, measure with a multimeter to confirm 5.0 ± 0.1 V. The MP1584 ships at whatever the previous user set; many ship at 12 V passthrough.

- [ ] **Step 5: Wire INMP441 mic**

| ESP32-S3 | INMP441 |
|---|---|
| 3.3 V | VDD |
| GND | GND |
| GND | L/R (selects left channel, drops the right slot) |
| GPIO15 | SCK (BCLK) |
| GPIO16 | WS (LRCLK) |
| GPIO17 | SD (DOUT) |

- [ ] **Step 6: Wire button and LED**

| ESP32-S3 | Component |
|---|---|
| GPIO9 | Button signal (other side to GND; internal pull-up enabled in YAML) |
| GPIO8 | WS2812 DIN |
| 5 V (buck output) | WS2812 VIN |
| GND | Button + WS2812 GND |

- [ ] **Step 7: Connect speaker terminals (not yet to cabinets)**

Use temporary clip leads to the FRS 8 drivers (still in cabinets if already built, or on the bench). Confirm L and R wired correctly.

- [ ] **Step 8: First power-on**

Apply 12 V. Expected:
- TPA3116D2 power LED lights
- Buck converter output stays at 5 V (re-measure under load)
- ESP32-S3 boots; status LED on board lights
- WS2812 stays off (correct — `restore_mode: ALWAYS_OFF`)

If anything smells, smokes, or feels hot, kill power and recheck wiring.

---

## Task 15: Terrace — initial flash and bench smoke test

**Files:** none — runtime verification.

- [ ] **Step 1: Flash via USB**

Run:
```bash
cd /Users/danillugovskoy/own/intercom && esphome run intercom-s3.yaml --device /dev/cu.usbserial-<id>
```
(Substitute the actual USB serial path. On macOS: `ls /dev/cu.usb*` after plugging in.)

Expected: build succeeds, upload completes, device reboots, ESPHome live-log stream opens showing WiFi connection + API ready.

- [ ] **Step 2: Verify HA discovery**

In Home Assistant: Settings → Devices & Services. Expected: new ESPHome device "Intercom Terrace" prompts to add. Add it.

Verify new entities appear:
- `media_player.intercom_terrace_player`
- `light.status_led`
- `binary_sensor.button`

- [ ] **Step 3: Smoke test announcement playback (mono TTS)**

Call `media_player.play_media` on `media_player.intercom_terrace_player` with TTS content. Expected: both speakers (L and R) play the same mono TTS clearly.

- [ ] **Step 4: Smoke test stereo music**

If you have Music Assistant or another stereo source: play a stereo track to `media_player.intercom_terrace_player`. Expected: clean stereo separation, no popping, no buffer underruns logged. If you don't have a stereo source, skip and revisit in Task 16.

- [ ] **Step 5: Smoke test button**

Press the button. Expected:
- Status LED turns blue
- HA addon receives POST to `/intercom`
- On release after 2s, status LED turns yellow until upload finishes, then off

- [ ] **Step 6: Smoke test mic capture**

Speak near the INMP441 while holding the button. Expected: the upload's audio (logged by the addon, or played back to its targets) contains your voice clearly.

- [ ] **Step 7: Smoke test wake word (placeholder phrase)**

Say "okay nabu" near the mic. Expected: status LED blue, recorder VAD-recording starts, upload finishes after silence detection. (May not trigger reliably on placeholder phrases — that's expected, Task 17 finalizes.)

- [ ] **Step 8: Verify voice_assistant trigger**

Say "hey jarvis" (or whichever phrase B is set to). Expected: voice_assistant flow starts (HA assist pipeline runs). May require an `assist_pipeline` configured in HA — if absent, the device will log an error harmlessly.

- [ ] **Step 9: Tune TPA3116D2 onboard pot**

While playing a continuous music track, rotate the pot slowly. Find the position where:
- Volume at the user's listening distance is loud enough
- No clipping / distortion is audible
- Onboard amp doesn't get uncomfortably hot

Mark the pot position with a paint pen so it can be restored if knocked. Typically ~70–80% rotation.

---

## Task 16: Terrace — install in IP54 enclosure and mount

**Files:** none — physical build.

- [ ] **Step 1: Plan the IP54 enclosure layout**

Inside the IP54 box, plan placement so:
- 12 V barrel jack on one wall, with strain relief
- USB-C accessible (for future re-flashing) on another wall, with a gasketed plug when not in use
- Button on the front face
- WS2812 LED visible through a small light-pipe or translucent panel on the front
- Internal: ESP32-S3 + PCM5102 + TPA3116D2 + buck converter

- [ ] **Step 2: Drill all panel holes before mounting electronics**

Holes: 12 V jack, USB-C cutout, button, LED light-pipe, two speaker terminal posts on a side wall, mic cutout (small hole behind grille cloth).

- [ ] **Step 3: Mount components inside**

Use M3 standoffs or hot glue for boards. Keep the analog signal wire (PCM5102 LOUT/ROUT → TPA3116 input) as short and as twisted as possible. Route 12 V leads away from analog signal.

- [ ] **Step 4: Install mic with windscreen**

Mount INMP441 just behind a foam windscreen plug in the mic cutout. Glue the foam in place. Verify the mic port hole on the INMP441 board faces outward.

- [ ] **Step 5: Wire speaker terminals to the cabinets**

External speaker wire runs from terminals on the enclosure to the speaker cabinets. Keep runs short (< 2 m each), match L/R polarity.

- [ ] **Step 6: Close and weatherproof**

Tighten all gaskets. Mount the enclosure under cover (eave / overhang) where direct rain and full sun don't hit it. Mount the speaker cabinets with their baffles tilted slightly down to shed water.

- [ ] **Step 7: Powered-up integration test in installed location**

Repeat Task 15 steps 3–6 in the deployed location. Verify WiFi signal strength is acceptable (HA dashboard or `wifi_signal` sensor reading better than −75 dBm).

---

## Task 17: Finalize wake-word phrases

**Files:**
- Modify: `/Users/danillugovskoy/own/intercom/atom-echo.yaml` (kitchen wake-word from intercom-features plan)
- Modify: `/Users/danillugovskoy/own/intercom/intercom-s3.yaml` (terrace)

Now that hardware is up and you can hear false-positive rates in the deployed locations, pick the two final wake-word phrases.

- [ ] **Step 1: Decide phrases**

Pick from ESPHome's prebuilt micro_wake_word models. Common choices: `okay_nabu`, `hey_jarvis`, `alexa`, `hey_mycroft`, `computer`. Constraints:
- Two **distinct** phrases (no shared prefix)
- The intercom one should be short/punchy (yelled across a room)
- The VA one should match your HA Assist setup if you've already named it

Suggested defaults: `okay_nabu` (intercom) + `hey_jarvis` (VA). Update both files to match.

- [ ] **Step 2: Update intercom-s3.yaml model entries**

If the phrases differ from the placeholders, change the `model:` entries and the `wake_word == "..."` lambda string accordingly.

- [ ] **Step 3: Update atom-echo.yaml**

The Atom Echo (classic ESP32) probably can only run **one** wake-word reliably. Confirm with the boot log: after flashing the kitchen device, look for `Free internal heap` near boot. If below ~50 KB after both models load, drop the VA model from `atom-echo.yaml` and document that the kitchen uses the button for VA. Spec calls this out as a fallback.

- [ ] **Step 4: Re-flash both devices**

```bash
cd /Users/danillugovskoy/own/intercom
esphome run atom-echo.yaml --device atom-echo-<mac>.local
esphome run intercom-s3.yaml --device intercom-terrace-<mac>.local
```

- [ ] **Step 5: Verify wake-words trigger reliably**

Test each phrase 10× from 1 m. Acceptable hit rate: ≥ 8/10 with ≤ 1 false-positive per hour of ambient kitchen / terrace noise. If miss rate is too high, try an alternate phrase or tune `micro_wake_word`'s `probability_cutoff`.

- [ ] **Step 6: Commit final wake-word choices**

```bash
git add atom-echo.yaml intercom-s3.yaml
git commit -m "feat(wake-word): finalize phrases — okay_nabu (intercom), hey_jarvis (VA)

Phrase choices made after bench-testing hit/miss rates in the deployed
kitchen and terrace locations. The kitchen Atom Echo runs only the intercom
wake word; running both models exceeded the classic ESP32's RAM budget.
Voice assistant on the kitchen is triggered from HA only (no local wake)."
```

(Adjust phrases and commit body to match what you actually picked.)

---

## Task 18: Final integration test

**Files:** none — full-system verification.

- [ ] **Step 1: Kitchen-to-terrace intercom**

Press the Atom Echo button. Speak. Release. Expected: audio plays on the terrace speakers within ~2 s.

- [ ] **Step 2: Terrace-to-kitchen intercom**

Press the terrace button. Speak. Release. Expected: audio plays on the kitchen speaker within ~2 s.

- [ ] **Step 3: Wake-word intercom from terrace**

Say the intercom wake word from the terrace. Wait for blue LED. Speak. Expected: VAD ends the recording ~1.2 s after you stop. Audio plays on the kitchen speaker.

- [ ] **Step 4: Voice assistant from terrace**

Say the VA wake word. Expected: HA Assist pipeline runs, TTS reply plays on terrace speakers.

- [ ] **Step 5: Music streaming to terrace**

Cast or queue a music track to `media_player.intercom_terrace_player`. Expected: stable stereo playback for ≥ 5 minutes without buffer underruns, with both channels distinct (test with a stereo-test track).

- [ ] **Step 6: Concurrent stress test**

Start music playing on the terrace. Have someone trigger an intercom broadcast from the kitchen. Expected (if the intercom-features ducking is in place): music pauses, broadcast plays, music resumes after the broadcast.

If ducking isn't on, the broadcast may overlap or queue depending on `media_player` behavior — note observed result for follow-up.

- [ ] **Step 7: Final commit (if not yet)**

If any final tweaks were made (LED colors, button debounce, mic gain, volume_multiplier), commit them with a clear message tying back to the integration test findings.

---

## Self-Review

**Spec coverage check:**

| Spec section | Implementing task(s) |
|---|---|
| Kitchen Atom Echo — Grove wiring | Task 3 |
| Kitchen Atom Echo — YAML pin change | Task 4 |
| Kitchen — assemble external amp + driver | Task 2, Task 5 (smoke test) |
| Terrace BOM | Task 6 |
| Terrace speaker cabinets | Task 7 |
| Terrace YAML — full config | Tasks 8–13 |
| Terrace electronics wiring (PCM5102, TPA3116, INMP441, button, LED, buck) | Task 14 |
| Terrace flash + bench test | Task 15 |
| Terrace IP54 install | Task 16 |
| Wake-word phrase finalization | Task 17 |
| Integration test (intercom + VA + music + ducking) | Task 18 |
| Open: PCM5102 SCK jumper verification | Task 6 step 3 |
| Open: TPA3116D2 variant check | Task 6 step 2 |
| Open: ESPHome stereo `channel: stereo` verification | Task 9 step 3 + Task 15 step 4 |
| Open: TPA3116 pot trim | Task 15 step 9 |
| Open: Atom Echo two-wake-word RAM check | Task 17 step 3 |
| Open: Pin remap on chosen S3 board variant | Task 14 (wire as table specifies; revise pins in YAML if a strapping pin conflicts) |
| Dependency: intercom-features merged first | Task 1 (gate) |

All spec requirements have an implementing task. No gaps.

**Placeholder scan:** All "wake-word phrase" placeholders are intentional — Task 13 documents them as such and Task 17 resolves them. No "TODO", "fill in", or "implement later" leftover.

**Type / pin consistency:** Pin assignments referenced consistently across Tasks 9–14: I²S out (GPIO5/6/7), I²S in (GPIO15/16/17), button (GPIO9), LED (GPIO8). Mic ID `terrace_mic`, speaker ID `terrace_speaker`, player ID `terrace_player`, LED ID `status_led` — all match between YAML tasks. Intercom POST URL `http://homeassistant.local:9999/intercom` matches the kitchen Atom Echo's URL exactly.
