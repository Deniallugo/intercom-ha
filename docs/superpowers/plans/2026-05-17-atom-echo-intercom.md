# Atom Echo Intercom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Press-and-hold the Atom Echo button to record voice, release to broadcast the recording to configured HA media players via a local HA addon.

**Architecture:** ESPHome records PCM mic data to SPIFFS flash during button hold. On release it uploads the recording in 16 KB chunks (with a session ID) to a local aiohttp relay server running as a HA addon. The server reassembles the chunks, wraps them in a WAV header, writes a temp file to `/config/www/`, calls the HA REST API to play the URL on configured media players, then deletes the file after playback duration + 5 s.

**Tech Stack:** ESPHome (Arduino/ESP32), Python 3 + aiohttp, Home Assistant addon supervisor, pytest + pytest-asyncio.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `atom-echo.yaml` | Modify | Replace voice_assistant with SPIFFS recorder + HTTP uploader |
| `recorder.h` | Create | SPIFFS-backed mic data capture (C++ helper) |
| `uploader.h` | Create | Chunked HTTP POST upload after recording (C++ helper) |
| `intercom-addon/config.yaml` | Create | HA addon metadata, options schema, port declaration |
| `intercom-addon/Dockerfile` | Create | Container image for the relay server |
| `intercom-addon/run.sh` | Create | Addon entry point |
| `intercom-addon/intercom.py` | Create | aiohttp relay server — chunk buffering, WAV assembly, HA API call, temp file cleanup |
| `tests/requirements.txt` | Create | pytest + pytest-asyncio + pytest-aiohttp + aiohttp |
| `tests/pytest.ini` | Create | asyncio_mode = auto |
| `tests/test_intercom.py` | Create | Unit tests for relay server |

---

### Task 1: Relay server — WAV header utility + tests

**Files:**
- Create: `intercom-addon/intercom.py`
- Create: `tests/requirements.txt`
- Create: `tests/test_intercom.py`

- [ ] **Step 1: Create `tests/requirements.txt`**

  ```
  pytest
  pytest-asyncio==0.23.*
  pytest-aiohttp
  aiohttp
  ```

- [ ] **Step 1b: Create `tests/pytest.ini`**

  ```ini
  [pytest]
  asyncio_mode = auto
  ```

- [ ] **Step 2: Create `intercom-addon/intercom.py` with just the WAV header function**

  ```python
  import asyncio
  import json
  import os
  import struct
  import uuid
  from pathlib import Path

  from aiohttp import web, ClientSession

  OPTIONS_FILE = "/data/options.json"
  CONFIG_WWW = "/config/www"
  HA_API = "http://supervisor/core/api"
  SAMPLE_RATE = 16000
  SAMPLE_WIDTH = 2   # bytes, 16-bit
  CHANNELS = 1

  sessions: dict[str, list[tuple[int, bytes]]] = {}


  def load_options() -> dict:
      with open(OPTIONS_FILE) as f:
          return json.load(f)


  def wav_header(pcm_len: int) -> bytes:
      return struct.pack(
          "<4sI4s4sIHHIIHH4sI",
          b"RIFF",
          36 + pcm_len,
          b"WAVE",
          b"fmt ",
          16,
          1,                                          # PCM
          CHANNELS,
          SAMPLE_RATE,
          SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH,      # byte rate
          CHANNELS * SAMPLE_WIDTH,                    # block align
          SAMPLE_WIDTH * 8,                           # bits per sample
          b"data",
          pcm_len,
      )
  ```

- [ ] **Step 3: Write failing WAV header tests in `tests/test_intercom.py`**

  ```python
  import struct
  import sys
  from pathlib import Path

  import pytest

  sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
  import intercom as srv


  def test_wav_header_is_44_bytes():
      assert len(srv.wav_header(0)) == 44


  def test_wav_header_riff_tag():
      assert srv.wav_header(100)[:4] == b"RIFF"


  def test_wav_header_wave_tag():
      assert srv.wav_header(100)[8:12] == b"WAVE"


  def test_wav_header_total_size():
      h = srv.wav_header(100)
      total = struct.unpack_from("<I", h, 4)[0]
      assert total == 136   # 36 + 100


  def test_wav_header_sample_rate_is_16000():
      h = srv.wav_header(0)
      assert struct.unpack_from("<I", h, 24)[0] == 16000


  def test_wav_header_16bit():
      h = srv.wav_header(0)
      assert struct.unpack_from("<H", h, 34)[0] == 16


  def test_wav_header_data_size():
      h = srv.wav_header(200)
      assert struct.unpack_from("<I", h, 40)[0] == 200
  ```

- [ ] **Step 4: Run tests — expect FAIL (function not yet imported)**

  ```bash
  cd /Users/danillugovskoy/own/intercom
  pip install -r tests/requirements.txt
  pytest tests/test_intercom.py -v
  ```

  Expected: all 7 tests PASS (the function exists already).

- [ ] **Step 5: Commit**

  ```bash
  git add intercom-addon/intercom.py tests/
  git commit -m "feat: relay server WAV header + tests"
  ```

---

### Task 2: Relay server — chunk handler, WAV assembly, HA API call, cleanup

**Files:**
- Modify: `intercom-addon/intercom.py` (add `handle_intercom` + `main`)

- [ ] **Step 1: Add `handle_intercom` and `main` to `intercom-addon/intercom.py`**

  Append after `wav_header`:

  ```python
  async def handle_intercom(request: web.Request) -> web.Response:
      session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
      chunk_index = int(request.headers.get("X-Chunk-Index", "0"))
      is_final = request.headers.get("X-Final") == "1"
      data = await request.read()

      sessions.setdefault(session_id, []).append((chunk_index, data))

      if not is_final:
          return web.Response(status=204)

      # Assemble chunks in order
      chunks = sorted(sessions.pop(session_id), key=lambda x: x[0])
      pcm = b"".join(d for _, d in chunks)

      opts = load_options()
      ha_url = opts.get("ha_url", "http://homeassistant.local:8123")
      filename = f"intercom-{session_id}.wav"
      filepath = Path(CONFIG_WWW) / filename
      filepath.parent.mkdir(parents=True, exist_ok=True)

      with open(filepath, "wb") as f:
          f.write(wav_header(len(pcm)))
          f.write(pcm)

      token = os.environ["SUPERVISOR_TOKEN"]
      media_url = f"{ha_url}/local/{filename}"
      duration = len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)

      async with ClientSession() as session:
          for player in opts.get("media_players", []):
              await session.post(
                  f"{HA_API}/services/media_player/play_media",
                  headers={"Authorization": f"Bearer {token}"},
                  json={
                      "entity_id": player,
                      "media_content_id": media_url,
                      "media_content_type": "music",
                  },
              )

      loop = asyncio.get_running_loop()
      loop.call_later(duration + 5, lambda: filepath.unlink(missing_ok=True))

      return web.Response(status=204)


  def main() -> None:
      opts = load_options()
      app = web.Application()
      app.router.add_post("/intercom", handle_intercom)
      web.run_app(app, host="0.0.0.0", port=opts.get("port", 9999))


  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2: Add handler tests to `tests/test_intercom.py`**

  ```python
  import os
  import uuid
  from unittest.mock import patch

  import pytest
  from aiohttp import web


  FAKE_OPTIONS = {
      "ha_url": "http://ha.test:8123",
      "port": 9999,
      "media_players": ["media_player.sonos_test"],
  }


  class _FakeResponse:
      status = 204


  class _FakeSession:
      def __init__(self):
          self.calls: list = []

      async def __aenter__(self):
          return self

      async def __aexit__(self, *_):
          pass

      async def post(self, url, **kwargs):
          self.calls.append((url, kwargs))
          return _FakeResponse()


  @pytest.fixture(autouse=True)
  def _clear_sessions():
      srv.sessions.clear()
      yield
      srv.sessions.clear()


  @pytest.fixture
  def fake_env(monkeypatch, tmp_path):
      monkeypatch.setitem(os.environ, "SUPERVISOR_TOKEN", "tok")
      monkeypatch.setattr(srv, "CONFIG_WWW", str(tmp_path))
      monkeypatch.setattr(srv, "load_options", lambda: FAKE_OPTIONS)


  @pytest.fixture
  def app():
      application = web.Application()
      application.router.add_post("/intercom", srv.handle_intercom)
      return application


  async def test_single_chunk_creates_wav(aiohttp_client, app, fake_env, tmp_path):
      client = await aiohttp_client(app)
      pcm = b"\x10\x20" * 100
      sid = str(uuid.uuid4())

      with patch("intercom.ClientSession", return_value=_FakeSession()):
          resp = await client.post(
              "/intercom", data=pcm,
              headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
          )

      assert resp.status == 204
      wav = (tmp_path / f"intercom-{sid}.wav").read_bytes()
      assert wav[:4] == b"RIFF"
      assert wav[44:] == pcm


  async def test_intermediate_chunk_no_file(aiohttp_client, app, fake_env, tmp_path):
      client = await aiohttp_client(app)
      sid = str(uuid.uuid4())
      resp = await client.post(
          "/intercom", data=b"\x00" * 64,
          headers={"X-Session-ID": sid, "X-Chunk-Index": "0"},
      )
      assert resp.status == 204
      assert not list(tmp_path.glob("*.wav"))


  async def test_chunks_reassembled_in_order(aiohttp_client, app, fake_env, tmp_path):
      client = await aiohttp_client(app)
      sid = str(uuid.uuid4())
      chunk0, chunk1 = b"\x01" * 50, b"\x02" * 50
      fake_session = _FakeSession()

      with patch("intercom.ClientSession", return_value=fake_session):
          # Send chunk 1 first (out of order)
          await client.post(
              "/intercom", data=chunk1,
              headers={"X-Session-ID": sid, "X-Chunk-Index": "1"},
          )
          await client.post(
              "/intercom", data=chunk0,
              headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
          )

      wav = (tmp_path / f"intercom-{sid}.wav").read_bytes()
      assert wav[44:] == chunk0 + chunk1


  async def test_ha_api_called_with_correct_url(aiohttp_client, app, fake_env, tmp_path):
      client = await aiohttp_client(app)
      sid = str(uuid.uuid4())
      fake_session = _FakeSession()

      with patch("intercom.ClientSession", return_value=fake_session):
          await client.post(
              "/intercom", data=b"\x00" * 64,
              headers={"X-Session-ID": sid, "X-Chunk-Index": "0", "X-Final": "1"},
          )

      assert len(fake_session.calls) == 1
      _url, kwargs = fake_session.calls[0]
      body = kwargs["json"]
      assert body["entity_id"] == "media_player.sonos_test"
      assert f"intercom-{sid}.wav" in body["media_content_id"]
      assert body["media_content_id"].startswith("http://ha.test:8123/local/")
  ```

- [ ] **Step 3: Run tests — all must pass**

  ```bash
  pytest tests/test_intercom.py -v
  ```

  Expected: 11 tests PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add intercom-addon/intercom.py tests/test_intercom.py
  git commit -m "feat: relay server handler with chunked reassembly and HA API call"
  ```

---

### Task 3: HA addon scaffold

**Files:**
- Create: `intercom-addon/config.yaml`
- Create: `intercom-addon/Dockerfile`
- Create: `intercom-addon/run.sh`

- [ ] **Step 1: Create `intercom-addon/config.yaml`**

  ```yaml
  name: Intercom Relay
  description: Receives audio from Atom Echo and plays it on HA media players.
  version: "1.0.0"
  slug: intercom_relay
  init: false
  arch:
    - aarch64
    - amd64
  homeassistant: "2023.0"
  options:
    ha_url: "http://homeassistant.local:8123"
    port: 9999
    media_players: []
  schema:
    ha_url: str
    port: int
    media_players:
      - str
  map:
    - config:rw
  ports:
    9999/tcp: Intercom audio endpoint
  ports_description:
    9999/tcp: ESPHome audio relay
  ```

- [ ] **Step 2: Create `intercom-addon/Dockerfile`**

  ```dockerfile
  ARG BUILD_FROM
  FROM $BUILD_FROM

  RUN apk add --no-cache python3 py3-pip \
   && pip3 install --no-cache-dir aiohttp

  COPY run.sh /run.sh
  COPY intercom.py /intercom.py
  RUN chmod a+x /run.sh

  CMD ["/run.sh"]
  ```

- [ ] **Step 3: Create `intercom-addon/run.sh`**

  ```bash
  #!/usr/bin/with-contenv bashio
  exec python3 /intercom.py
  ```

- [ ] **Step 4: Verify the addon directory looks correct**

  ```bash
  find intercom-addon -type f | sort
  ```

  Expected output:
  ```
  intercom-addon/Dockerfile
  intercom-addon/config.yaml
  intercom-addon/intercom.py
  intercom-addon/run.sh
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add intercom-addon/
  git commit -m "feat: HA addon scaffold for intercom relay"
  ```

---

### Task 4: ESPHome SPIFFS recorder helper (`recorder.h`)

**Files:**
- Create: `recorder.h`

- [ ] **Step 1: Create `recorder.h`**

  ```cpp
  #pragma once
  #include "SPIFFS.h"

  static File _rec_file;
  static bool _rec_active = false;

  // Call once at boot to mount SPIFFS.
  void recorder_init() {
    SPIFFS.begin(true);
  }

  // Open /rec.pcm for writing. Overwrites any previous recording.
  void recorder_start() {
    SPIFFS.remove("/rec.pcm");
    _rec_file = SPIFFS.open("/rec.pcm", "w");
    _rec_active = true;
  }

  // Called from the microphone data callback — writes raw PCM bytes.
  void recorder_on_data(const uint8_t* data, size_t len) {
    if (_rec_active && _rec_file) {
      _rec_file.write(data, len);
    }
  }

  // Flush and close the file. Call before uploader_send().
  void recorder_stop() {
    _rec_active = false;
    if (_rec_file) {
      _rec_file.flush();
      _rec_file.close();
    }
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add recorder.h
  git commit -m "feat: SPIFFS recorder helper for ESPHome"
  ```

---

### Task 5: ESPHome chunked HTTP uploader helper (`uploader.h`)

**Files:**
- Create: `uploader.h`

- [ ] **Step 1: Create `uploader.h`**

  ```cpp
  #pragma once
  #include "SPIFFS.h"
  #include <HTTPClient.h>
  #include <esp_system.h>

  static std::string _make_session_id() {
    uint8_t rnd[8];
    esp_fill_random(rnd, sizeof(rnd));
    char buf[17];
    for (int i = 0; i < 8; i++) sprintf(buf + i * 2, "%02x", rnd[i]);
    buf[16] = '\0';
    return std::string(buf);
  }

  // Read /rec.pcm from SPIFFS and POST it in CHUNK_SIZE chunks to `url`.
  // Headers X-Session-ID, X-Chunk-Index, and X-Final identify the session.
  // Deletes /rec.pcm after upload.
  void uploader_send(const char* url) {
    File f = SPIFFS.open("/rec.pcm", "r");
    if (!f || f.size() == 0) {
      if (f) f.close();
      return;
    }

    const size_t CHUNK_SIZE = 16384;
    std::string session_id = _make_session_id();
    uint8_t* buf = (uint8_t*) malloc(CHUNK_SIZE);
    if (!buf) { f.close(); return; }

    int chunk_index = 0;
    while (f.available()) {
      size_t bytes_read = f.read(buf, CHUNK_SIZE);
      bool is_final = !f.available();

      HTTPClient http;
      http.begin(url);
      http.addHeader("Content-Type", "audio/pcm");
      http.addHeader("X-Session-ID", session_id.c_str());
      http.addHeader("X-Chunk-Index", String(chunk_index).c_str());
      if (is_final) http.addHeader("X-Final", "1");
      http.sendRequest("POST", buf, bytes_read);
      http.end();
      chunk_index++;
    }

    free(buf);
    f.close();
    SPIFFS.remove("/rec.pcm");
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add uploader.h
  git commit -m "feat: chunked HTTP uploader helper for ESPHome"
  ```

---

### Task 6: Update `atom-echo.yaml` for intercom mode

**Files:**
- Modify: `atom-echo.yaml`

- [ ] **Step 1: Replace the contents of `atom-echo.yaml`**

  ```yaml
  substitutions:
    name: atom-echo
    friendly_name: Atom Echo

  esphome:
    name: ${name}
    friendly_name: ${friendly_name}
    includes:
      - recorder.h
      - uploader.h
    on_boot:
      priority: 200.0
      then:
        - lambda: |-
            recorder_init();
            id(atom_mic).add_data_callback([](std::vector<int16_t> data) {
              recorder_on_data(
                reinterpret_cast<const uint8_t*>(data.data()),
                data.size() * sizeof(int16_t)
              );
            });

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

  wifi:
    ssid: !secret wifi_ssid
    password: !secret wifi_password
    ap:
      ssid: "${name} Fallback"
      password: !secret ap_password

  captive_portal:

  # ── Audio hardware ─────────────────────────────────────────────────────────────

  i2s_audio:
    i2s_lrclk_pin: GPIO33
    i2s_bclk_pin: GPIO19

  microphone:
    - platform: i2s_audio
      id: atom_mic
      i2s_din_pin: GPIO23
      adc_type: external
      pdm: true
      sample_rate: 16000
      correct_dc_offset: true

  # ── Status LED (single SK6812 on GPIO27) ───────────────────────────────────────

  light:
    - platform: neopixelbus
      type: GRB
      variant: SK6812
      pin: GPIO27
      num_leds: 1
      name: "Status LED"
      id: status_led
      restore_mode: ALWAYS_OFF

  # ── HTTP client ────────────────────────────────────────────────────────────────

  http_request:
    useragent: esphome/intercom
    timeout: 30s

  # ── Upload script ──────────────────────────────────────────────────────────────

  script:
    - id: upload_recording
      then:
        - light.turn_on:
            id: status_led
            red: 100%
            green: 100%
            blue: 0%
        - lambda: |-
            uploader_send("http://homeassistant.local:9999/intercom");
        - light.turn_off: status_led

  # ── Push-to-talk button (GPIO39, active LOW) ───────────────────────────────────

  binary_sensor:
    - platform: gpio
      pin:
        number: GPIO39
        inverted: true
      name: "Button"
      on_press:
        - light.turn_on:
            id: status_led
            red: 0%
            green: 0%
            blue: 100%
        - lambda: |-
            recorder_start();
            id(atom_mic).start();
      on_release:
        - lambda: |-
            id(atom_mic).stop();
            recorder_stop();
        - script.execute: upload_recording
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add atom-echo.yaml
  git commit -m "feat: atom-echo intercom mode — SPIFFS record + chunked upload"
  ```

---

### Task 7: Install the addon in Home Assistant

These steps are performed in the HA UI and on the Pi filesystem.

- [ ] **Step 1: Copy the addon folder to the Pi**

  From your Mac (or via Samba/SSH), copy `intercom-addon/` to `/addons/intercom_relay/` on the Pi.

  Via scp (adjust the Pi address):
  ```bash
  scp -r intercom-addon/ homeassistant@raspberrypi.local:/addons/intercom_relay/
  ```

  Alternatively drag the folder into the HA file system via the **File Editor** or **Samba** addons if installed.

- [ ] **Step 2: Install from local addon store**

  In HA: **Settings → Add-ons → Add-on Store** → three-dot menu (top right) → **Check for updates**.

  The **Intercom Relay** addon should appear under **Local add-ons**. Click **Install**.

- [ ] **Step 3: Configure the addon**

  In the addon **Configuration** tab, set:
  ```yaml
  ha_url: "http://<your-ha-ip>:8123"
  port: 9999
  media_players:
    - media_player.your_sonos_entity
    - media_player.your_alexa_entity
  ```

  Replace entity IDs with the actual ones from **Settings → Devices & Services → Entities**.

- [ ] **Step 4: Start the addon**

  Click **Start**. Enable **Start on boot** and **Watchdog**.

  Check the **Log** tab — you should see:
  ```
  ======== Running on http://0.0.0.0:9999 ========
  ```

- [ ] **Step 5: Verify the `/config/www` folder exists**

  In the HA **File Editor** (or SSH): confirm `/config/www/` exists. If not, create it:
  ```bash
  mkdir -p /config/www
  ```

---

### Task 8: Flash ESPHome and smoke test

- [ ] **Step 1: Validate the ESPHome config**

  In the ESPHome Web UI in HA: open **atom-echo** device → **Validate**. Fix any compilation errors before flashing.

- [ ] **Step 2: Flash via OTA**

  Click **Install → Wirelessly**. Wait for the flash to complete (~2 min).

  Watch the **Log** tab. You should see on boot:
  ```
  [I] Mounted SPIFFS
  [I] Connected to WiFi
  [I] Connected to Home Assistant
  ```

- [ ] **Step 3: Test — short message**

  - Press and hold the button. LED turns **blue**.
  - Say *"Testing one two three"* (~3 seconds).
  - Release. LED turns **yellow** briefly while uploading, then **off**.
  - The message should play on the configured media players within 2–3 seconds.

- [ ] **Step 4: Test — longer message (~20 seconds)**

  Press and hold for ~20 seconds, speaking continuously. Verify the full message plays on the media players without truncation.

- [ ] **Step 5: Verify temp file is cleaned up**

  In the HA **File Editor**, check `/config/www/`. Any `intercom-*.wav` files should disappear within ~30 seconds of playback ending.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| LED goes blue but no playback | Check addon log for HTTP errors; verify `ha_url` and player entity IDs in addon config |
| "SPIFFS mount failed" in ESPHome log | Add `SPIFFS.begin(true)` (the `true` flag formats SPIFFS on first use) — already in `recorder_init()` |
| Upload takes very long | Reduce recording time; check WiFi signal strength |
| Playback starts but cuts off early | The temp file was deleted too soon — `duration + 5` should be sufficient; increase the buffer if needed |
| Media player not found | Confirm entity ID in **Settings → Entities**; Sonos entities are usually `media_player.<room_name>` |
| Alexa doesn't play | Alexa media player requires the `alexa_media_player` HACS integration and cloud connectivity |
| `homeassistant.local` not resolving | Use the Pi's IP address directly in `uploader_send()` and addon `ha_url` |
