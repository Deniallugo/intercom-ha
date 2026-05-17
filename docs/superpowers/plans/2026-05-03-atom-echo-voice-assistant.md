# Atom Echo Voice Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flash the M5 Atom Echo with a push-to-talk ESPHome voice assistant backed by a fully local HA pipeline (Whisper STT + Piper TTS).

**Architecture:** The Atom Echo streams mic audio to Home Assistant via the ESPHome native API. HA processes it through a Whisper → Assist → Piper pipeline and streams TTS audio back to the device. No cloud services involved.

**Tech Stack:** ESPHome (Arduino framework), Home Assistant Assist, Wyoming Whisper addon (faster-whisper), Wyoming Piper addon, Raspberry Pi 5.

---

## File Map

| File | Purpose |
|------|---------|
| `atom-echo.yaml` | ESPHome device config — audio, button, LED, voice assistant |
| `secrets.yaml` | WiFi credentials, API keys (never committed) |

---

### Task 1: Install the Whisper (STT) addon in Home Assistant

The official HA "Whisper" addon uses faster-whisper under the hood. No custom repository needed.

- [ ] **Step 1: Open the addon store**

  In HA: **Settings → Add-ons → Add-on Store** (button bottom right).

- [ ] **Step 2: Install Whisper**

  Search for **"Whisper"**, click it (published by Home Assistant), click **Install**. Wait for installation to complete (~2-5 min on Pi 5).

- [ ] **Step 3: Configure the model**

  In the Whisper addon → **Configuration** tab, set:
  ```yaml
  language: en
  model: small
  beam_size: 1
  ```
  Save. (Use your actual language code, e.g. `uk` for Ukrainian.)

- [ ] **Step 4: Start the addon and verify**

  Click **Start**. Enable **Start on boot** and **Watchdog**.

  Go to **Log** tab — wait until you see:
  ```
  INFO: Loaded model 'small'
  INFO: Listening for requests
  ```

---

### Task 2: Install the Piper (TTS) addon in Home Assistant

- [ ] **Step 1: Install Piper**

  In the same **Add-on Store**, search **"Piper"**, install it (published by Home Assistant).

- [ ] **Step 2: Configure a voice**

  In Piper addon → **Configuration** tab, set:
  ```yaml
  voice: en_US-lessac-medium
  ```
  Replace with your language's voice if needed. Full voice list: https://rhasspy.github.io/piper-samples/

  Save.

- [ ] **Step 3: Start and verify**

  Click **Start**. Enable **Start on boot** and **Watchdog**.

  In **Log** tab, wait for:
  ```
  INFO: Loaded voice en_US-lessac-medium
  INFO: Listening for requests
  ```

---

### Task 3: Create the voice assistant pipeline in Home Assistant

- [ ] **Step 1: Open Voice Assistants**

  **Settings → Voice Assistants** → click **Add Assistant**.

- [ ] **Step 2: Configure the pipeline**

  | Field | Value |
  |-------|-------|
  | Name | `Local` |
  | Conversation agent | `Home Assistant` |
  | Speech-to-text | `faster-whisper` (small) |
  | Text-to-speech | `piper` (your chosen voice) |
  | Wake word | *(leave blank — using push-to-talk)* |

  Click **Create**.

- [ ] **Step 3: Verify STT works**

  On the same page, click the microphone icon next to your new pipeline → say something → confirm it transcribes correctly.

---

### Task 4: Install the ESPHome addon in Home Assistant

Skip this task if ESPHome is already installed and running.

- [ ] **Step 1: Install ESPHome**

  **Add-on Store → search "ESPHome" → Install** (published by ESPHome).

- [ ] **Step 2: Start it**

  Enable **Start on boot**, click **Start**, open the Web UI.

---

### Task 5: Create the secrets file

- [ ] **Step 1: Create `secrets.yaml` in the project root**

  ```yaml
  # secrets.yaml  — DO NOT COMMIT THIS FILE
  wifi_ssid: "YourNetworkName"
  wifi_password: "YourWifiPassword"
  ap_password: "fallback1234"
  api_encryption_key: ""   # fill in after ESPHome generates it
  ota_password: ""         # fill in after ESPHome generates it
  ```

  Leave `api_encryption_key` and `ota_password` blank for now — ESPHome will generate them in Task 6.

- [ ] **Step 2: Add `.gitignore`**

  Create `.gitignore` in the project root:
  ```
  secrets.yaml
  ```

---

### Task 6: Create the ESPHome YAML config

- [ ] **Step 1: Create `atom-echo.yaml`**

  ```yaml
  substitutions:
    name: atom-echo
    friendly_name: Atom Echo

  esphome:
    name: ${name}
    friendly_name: ${friendly_name}

  esp32:
    board: m5stack-atom
    framework:
      type: arduino

  logger:

  api:
    encryption:
      key: !secret api_encryption_key

  ota:
    - platform: esphome
      password: !secret ota_password

  wifi:
    ssid: !secret wifi_ssid
    password: !secret wifi_password
    ap:
      ssid: "${name} Fallback"
      password: !secret ap_password

  captive_portal:

  # ── Audio hardware ────────────────────────────────────────────────────────────

  i2s_audio:
    i2s_lrclk_pin: GPIO26
    i2s_bclk_pin: GPIO0

  microphone:
    - platform: i2s_audio
      id: atom_mic
      i2s_din_pin: GPIO34
      adc_type: external
      pdm: true

  speaker:
    - platform: i2s_audio
      id: atom_spk
      i2s_dout_pin: GPIO25
      dac_type: external
      mode: mono

  # ── Status LED (single SK6812 on GPIO27) ──────────────────────────────────────

  light:
    - platform: neopixelbus
      type: GRB
      variant: SK6812
      pin: GPIO27
      num_leds: 1
      name: "Status LED"
      id: status_led
      restore_mode: ALWAYS_OFF

  # ── Voice assistant ───────────────────────────────────────────────────────────

  voice_assistant:
    microphone: atom_mic
    speaker: atom_spk
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
      - delay: 2s
      - light.turn_off: status_led

  # ── Push-to-talk button (GPIO39, active LOW) ──────────────────────────────────

  binary_sensor:
    - platform: gpio
      pin:
        number: GPIO39
        inverted: true
      name: "Button"
      on_press:
        - voice_assistant.start: {}
      on_release:
        - voice_assistant.stop: {}
  ```

- [ ] **Step 2: Validate the YAML compiles**

  In the ESPHome Web UI in HA: **+ New Device → Use existing config** (or manually add), paste the YAML, click **Validate**. Fix any reported errors.

---

### Task 7: Flash the Atom Echo (first flash via USB)

The first flash must be done via USB. After that, OTA updates work over WiFi.

- [ ] **Step 1: Generate secrets**

  In the ESPHome Web UI, open the device and click **Install → Manual download → Modern format**. ESPHome will generate `api_encryption_key` and `ota_password` automatically. Copy them into your `secrets.yaml`.

- [ ] **Step 2: Connect the Atom Echo via USB**

  Connect the Atom Echo to the machine running your browser with a USB-C cable.

- [ ] **Step 3: Flash via browser**

  In the ESPHome Web UI, click **Install → Plug into this computer**. The browser will open a serial port picker — select the port for the Atom Echo. Flash proceeds (~2 min).

  Alternative (if browser serial isn't available):
  ```bash
  # Install esphome CLI
  pip install esphome

  # Flash
  esphome run atom-echo.yaml
  ```

- [ ] **Step 4: Watch the boot log**

  In the ESPHome Web UI → **Logs** (or `esphome logs atom-echo.yaml`). Confirm you see:
  ```
  [I] Connected to WiFi: <your SSID>
  [I] Connected to Home Assistant
  [I] voice_assistant: Ready
  ```

---

### Task 8: Add the device to Home Assistant

- [ ] **Step 1: Discover the device**

  HA will auto-discover it. Go to **Settings → Integrations** — you should see a banner: *"ESPHome device discovered: Atom Echo"*. Click **Configure** → enter the API encryption key from `secrets.yaml` → **Submit**.

- [ ] **Step 2: Assign the voice pipeline**

  In HA: **Settings → Voice Assistants**. The Atom Echo should now appear under **Devices**. Click it and assign the `Local` pipeline you created in Task 3.

---

### Task 9: Smoke test

- [ ] **Step 1: Press and hold the button**

  LED should turn **blue**. Speak a test command, e.g. *"What time is it?"*

- [ ] **Step 2: Release the button**

  LED turns **yellow** briefly (thinking), then **green** when TTS plays. You should hear the response from the speaker.

- [ ] **Step 3: Test an error state**

  Hold the button and say nothing, then release. Confirm LED turns **red** for 2 seconds then goes off.

- [ ] **Step 4: Test a HA command**

  Try *"Turn off the lights"* (if you have lights in HA) — confirm it executes.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Device doesn't connect to WiFi | Verify `wifi_ssid` / `wifi_password` in `secrets.yaml`, check 2.4GHz network |
| LED blue but no transcription | Check Whisper addon logs in HA, verify pipeline assignment |
| No audio from speaker | Check ESPHome logs for I2S errors; try increasing `volume_multiplier` to `4.0` |
| Garbled/quiet mic | Try `auto_gain: 31dBFS`, bump `noise_suppression_level` to `3` |
| HA integration not discovered | Ensure the API encryption key in HA matches the one in `secrets.yaml` |
