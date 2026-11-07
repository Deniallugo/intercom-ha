# Remote STT / TTS — Whisper + Piper on a Mac

Home Assistant stays on the Raspberry Pi; Whisper (STT) and Piper (TTS) run on
an M1 Max MacBook on the LAN and connect over the
[Wyoming protocol](https://www.home-assistant.io/integrations/wyoming/).
Nothing in `devices/` changes: wake words are detected on-device.

| Service | Port | Where | Accelerated |
|---|---|---|---|
| faster-whisper (STT) | 10300 | Mac | No — CPU, 8 performance cores |
| Piper (TTS) | 10200 | Mac | No — small ONNX model, CPU is plenty |
| HA Core + `intercom-addon` | — | Pi | — |

---

## Measured on the target machine

Apple M1 Max (8P + 2E, 32 GB), `int8`, `beam_size=1`, on a 3.47 s utterance —
*"Turn off the kitchen lights and set the terrace speaker to fifty percent."*

| Model | Transcribe | RTF | Result |
|---|---|---|---|
| `tiny.en` | 0.14 s | 0.04× | correct |
| `base.en` | 0.23 s | 0.07× | **"terra speaker"** ✗ |
| `distil-small.en` | 0.47 s | 0.14× | correct |
| `small.en` | 0.61 s | 0.18× | correct |

Piper: 1.09 s cold for the same sentence, well under real time once loaded.

The plist uses `small.en`: `base.en` is faster but misheard a device name.
`--initial-prompt` (already in the plist) fixes that sentence, so `base.en` is
an option if you want the speed. No GPU is used — CTranslate2 has no Metal
backend; the gain is the eight performance cores.

---

## Before you build this

Assist works only while the laptop is on the LAN; when it is away, satellites
listen and then time out with no useful error. If voice must always work, use
an always-on box instead.

---

## Install

Native, in one root-owned venv (no dependency on a login session). Verified with Homebrew Python 3.14.6 on macOS 26.5 / arm64 —
`wyoming-faster-whisper` 3.5.0, `wyoming-piper`, `ctranslate2` 4.8.1.

```bash
sudo mkdir -p /usr/local/opt/wyoming /usr/local/var/wyoming/{whisper,piper} /usr/local/var/log
sudo /opt/homebrew/bin/python3 -m venv /usr/local/opt/wyoming/venv
sudo /usr/local/opt/wyoming/venv/bin/pip install wyoming-faster-whisper wyoming-piper
```

Pre-download both models (the daemons don't fetch them on demand):

```bash
sudo HOME=/usr/local/var/wyoming /usr/local/opt/wyoming/venv/bin/python -c \
  'from faster_whisper import WhisperModel; WhisperModel("small.en", device="cpu", compute_type="int8")'
sudo /usr/local/opt/wyoming/venv/bin/python -m piper.download_voices \
  en_US-lessac-medium --data-dir /usr/local/var/wyoming/piper
```

## Daemons

LaunchDaemons, not LaunchAgents/`brew services`, so they start at boot with nobody logged in.

```bash
sudo install -m 0644 -o root -g wheel \
  tools/wyoming-macos/local.wyoming-whisper.plist \
  tools/wyoming-macos/local.wyoming-piper.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/local.wyoming-whisper.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/local.wyoming-piper.plist
```

Check both are listening:

```bash
lsof -nP -iTCP:10300 -sTCP:LISTEN
lsof -nP -iTCP:10200 -sTCP:LISTEN
tail -f /usr/local/var/log/wyoming-whisper.log   # expect: INFO:__main__:Ready
```

To reload after editing a plist: `sudo launchctl bootout system/local.wyoming-whisper`
then `bootstrap` again.

Both plists set `ProcessType: Interactive`; without it the daemons get a low
QoS class and run on the efficiency cores only.

## Keep it reachable

```bash
sudo pmset -a sleep 0            # never idle-sleep
sudo pmset -a disablesleep 1     # stay awake lid-closed (needs AC; no external display required)
```

- DHCP reservation for the Mac — a changed IP breaks the integration silently.
  Wyoming is unauthenticated plaintext: LAN only.
- Firewall: allow `/usr/local/opt/wyoming/venv/bin/python` incoming.

## Wire it into Home Assistant

1. *Settings → Devices & Services → Add Integration → **Wyoming Protocol***.
   Enter the Mac's IP and `10300`. Repeat for `10200`.
2. **Remove the Pi's Whisper and Piper add-ons first** — see below.
3. *Settings → Voice assistants* → point the pipeline's STT and TTS at the new
   `stt.faster_whisper` / `tts.piper` entities.

If the local Piper add-on still exists, the remote one registers as
`tts.piper_2` and announcements keep using the local one (the add-on's
`tts_engine` defaults to `tts.piper`). Remove the add-on first, or set
`tts_engine` to the new entity.

## Tuning

| Want | Change |
|---|---|
| Lower latency | `--model base.en` (keep `--initial-prompt`) or `distil-small.en` |
| Better accuracy | `--model medium.en`, or add `--beam-size 5` |
| Less contention with your own work | `--cpu-threads 6` — leaves two P-cores free |
| No network at startup | add `--local-files-only` once models are cached |
| Different voice | `piper.download_voices <name>`, then edit `--voice` |

## Troubleshooting

| Symptom | Cause |
|---|---|
| Satellite listens, then times out | Mac asleep or off-LAN — `pmset -g` and `lsof` on 10300 |
| Works logged in, dead after reboot | Installed as a LaunchAgent, not a LaunchDaemon |
| Transcribes but far slower than the table | `ProcessType` not `Interactive` → parked on E-cores |
| `Unable to find voice` in the Piper log | Voice never downloaded, or `--data-dir` mismatch |
| Announcements still slow | Still hitting `tts.piper` on the Pi — check the add-on's `tts_engine` |
