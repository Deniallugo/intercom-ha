# Remote STT / TTS — Whisper + Piper on a Mac

Home Assistant stays on the Raspberry Pi; **Whisper (STT)** and **Piper (TTS)**
move to an M1 Max MacBook Pro on the same LAN and register back over the
[Wyoming protocol](https://www.home-assistant.io/integrations/wyoming/). The Pi
is fine as a coordinator — it is the speech models that were starving it.

Nothing in `devices/` changes. All three satellites detect their wake word
**on-device** with `micro_wake_word`, so no openWakeWord server is involved; the
only things crossing the network are the STT and TTS legs of the Assist pipeline.

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

Piper synthesised the same sentence in 1.09 s cold (model load included);
steady-state in the daemon is well under real time.

`small.en` is the default in the shipped plist. `base.en` is 2.6× faster but
misheard *terrace* — one of this house's two device names — and a wrong entity
is worse than 0.4 s of extra latency. `--initial-prompt` with the device names
does fix `base.en` on this sentence, so it is a reasonable trade if you want the
speed; the prompt is in the plist either way.

> Neither Whisper nor Piper uses the GPU here. `faster-whisper` runs on
> CTranslate2, which has no Metal backend, and Piper is a small ONNX VITS model
> that gains nothing from one. The win over the Pi is entirely the eight
> performance cores — which is already the whole problem solved.

---

## Before you build this

**The M1 Max is a laptop, and this one is the daily driver.** An always-on voice
backend on a machine that closes, sleeps, and leaves the house means Assist
fails whenever it is away — and the failure mode is a satellite that lights up,
listens, and then times out with no useful error. The keep-awake and daemon
steps below make it survive lid-close and reboot, but they cannot make a laptop
stationary.

If Assist needs to work when you are out, this is the wrong host and a cheap
always-on box is the right one. If it is fine for voice to work only when you
are home with the laptop on the desk, carry on — the performance is genuinely
good.

---

## Install

Docker is **not** an option for the STT service on macOS in general (no GPU
passthrough), and is pointless here anyway since both services are CPU-bound.
Everything runs natively out of one root-owned venv, so the daemons have no
dependency on a user home directory or a login session.

Verified against Homebrew Python 3.14.6 on macOS 26.5 / arm64 —
`wyoming-faster-whisper` 3.5.0, `wyoming-piper`, `ctranslate2` 4.8.1.

```bash
sudo mkdir -p /usr/local/opt/wyoming /usr/local/var/wyoming/{whisper,piper} /usr/local/var/log
sudo /opt/homebrew/bin/python3 -m venv /usr/local/opt/wyoming/venv
sudo /usr/local/opt/wyoming/venv/bin/pip install wyoming-faster-whisper wyoming-piper
```

Pre-download both models. The daemons do not fetch voices on demand, and you do
not want a first-boot model download racing the network coming up:

```bash
sudo HOME=/usr/local/var/wyoming /usr/local/opt/wyoming/venv/bin/python -c \
  'from faster_whisper import WhisperModel; WhisperModel("small.en", device="cpu", compute_type="int8")'
sudo /usr/local/opt/wyoming/venv/bin/python -m piper.download_voices \
  en_US-lessac-medium --data-dir /usr/local/var/wyoming/piper
```

## Daemons

`LaunchDaemons` (not `LaunchAgents`) so both start at boot with nobody logged
in — `brew services` and login items both need a user session and will silently
leave you with no STT after an unattended reboot.

```bash
sudo install -m 0644 -o root -g wheel \
  tools/wyoming-macos/local.wyoming-whisper.plist \
  tools/wyoming-macos/local.wyoming-piper.plist /Library/LaunchDaemons/
sudo launchctl bootstrap system /Library/LaunchDaemons/local.wyoming-whisper.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/local.wyoming-piper.plist
```

Confirm both are listening — this is the check that actually matters:

```bash
lsof -nP -iTCP:10300 -sTCP:LISTEN
lsof -nP -iTCP:10200 -sTCP:LISTEN
tail -f /usr/local/var/log/wyoming-whisper.log   # expect: INFO:__main__:Ready
```

To reload after editing a plist: `sudo launchctl bootout system/local.wyoming-whisper`
then `bootstrap` again.

> **`ProcessType` is load-bearing.** Both plists set `Interactive`. A daemon
> left at the default gets a low QoS class, and on Apple Silicon the scheduler
> confines low-QoS work to the two efficiency cores — which would throw away
> the entire reason for moving off the Pi.

## Keep it reachable

```bash
sudo pmset -a sleep 0            # never idle-sleep
sudo pmset -a disablesleep 1     # stay awake lid-closed (needs AC; no external display required)
```

- **DHCP reservation** for the Mac. Wyoming is plaintext TCP with no auth, so
  keep it on the LAN — and a changed IP breaks the integration with no clear error.
- **Firewall**: allow `/usr/local/opt/wyoming/venv/bin/python` for incoming
  connections, or macOS drops them silently.
- Permanently on AC at 100 % is not kind to the battery; optimized charging
  softens it but expect some long-term wear.

## Wire it into Home Assistant

1. *Settings → Devices & Services → Add Integration → **Wyoming Protocol***.
   Enter the Mac's IP and `10300`. Repeat for `10200`.
2. **Remove the Pi's Whisper and Piper add-ons first** — see below.
3. *Settings → Voice assistants* → point the pipeline's STT and TTS at the new
   `stt.faster_whisper` / `tts.piper` entities.

> **The `tts_engine` trap.** `intercom-addon/config.yaml` hardcodes
> `tts_engine: "tts.piper"`, read at `intercom.py:186`. If the remote Piper is
> added while the local add-on still exists, the new entity registers as
> `tts.piper_2` and every announcement keeps quietly using the slow local one.
> Remove the add-on first, or set the add-on option to the new entity id.

## Tuning

| Want | Change |
|---|---|
| Lower latency | `--model base.en` (keep `--initial-prompt`) or `distil-small.en` |
| Better accuracy | `--model medium.en`, or add `--beam-size 5` |
| Less contention with your own work | `--cpu-threads 6` — leaves two P-cores free |
| No network at startup | add `--local-files-only` once models are cached |
| Different voice | `piper.download_voices <name>`, then edit `--voice` |

`--cpu-threads 8` saturates all eight performance cores for the ~0.6 s of each
transcribe. On a machine you are also working on, that is briefly noticeable;
drop to 6 if it bothers you.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Satellite listens, then times out | Mac asleep or off-LAN — `pmset -g` and `lsof` on 10300 |
| Works logged in, dead after reboot | Installed as a LaunchAgent, not a LaunchDaemon |
| Transcribes but far slower than the table | `ProcessType` not `Interactive` → parked on E-cores |
| `Unable to find voice` in the Piper log | Voice never downloaded, or `--data-dir` mismatch |
| Announcements still slow | Still hitting `tts.piper` on the Pi — check the add-on's `tts_engine` |
