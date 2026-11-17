#pragma once
// Talker feedback tones, synthesised on the device and fed into a mixer source
// speaker, so they play over music and over an incoming message instead of
// replacing them.
//
// Designed to be told apart from the add-on's chime (one 120 ms sine sweep
// 800↔1200 Hz around every broadcast) and from the wake chime (A5→E6 bell):
// these are either very short, much higher, or low and buzzy (odd harmonics).
//
//   tick       2.6 kHz, 25 ms              "on air" — hold threshold passed
//   delivered  G6 then C7, 60 + 90 ms      rising blip-blip, the add-on has it
//   error      B3 then G3 buzz, 2 × 160 ms descending "bonk-bonk"
//   busy       480+620 Hz, 3 × 90 ms       telephone busy tone, short
//   limit      2.1 kHz, 3 × 50 ms fast     recording limit reached
//
// Mono 16-bit at the mixer's rate (48 kHz on every device here), peaks around
// 0.25 FS: feedback, not an announcement.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

enum FbSound : int { FB_TICK = 0, FB_DELIVERED, FB_ERROR, FB_BUSY, FB_LIMIT };

struct _fb_note_t {
  float f1, f2;      // Hz; f2 > 0 adds a second tone (dual-tone busy)
  float start, dur;  // s
  float buzz;        // 0 = sine, 1 = strong odd harmonics (square-ish)
};

static const _fb_note_t _FB_TICK[]  = {{2637.0f, 0, 0.000f, 0.025f, 0.0f}};
static const _fb_note_t _FB_OK[]    = {{1568.0f, 0, 0.000f, 0.060f, 0.2f},
                                       {2093.0f, 0, 0.080f, 0.090f, 0.2f}};
static const _fb_note_t _FB_ERR[]   = {{247.0f, 0, 0.000f, 0.160f, 1.0f},
                                       {196.0f, 0, 0.200f, 0.160f, 1.0f}};
static const _fb_note_t _FB_BUSY[]  = {{480.0f, 620.0f, 0.000f, 0.090f, 0.0f},
                                       {480.0f, 620.0f, 0.180f, 0.090f, 0.0f},
                                       {480.0f, 620.0f, 0.360f, 0.090f, 0.0f}};
static const _fb_note_t _FB_LIMIT[] = {{2093.0f, 0, 0.000f, 0.050f, 0.3f},
                                       {2093.0f, 0, 0.090f, 0.050f, 0.3f},
                                       {2093.0f, 0, 0.180f, 0.050f, 0.3f}};

// Lost while the I²S driver spins up; see tools/make-chime.py.
static const float FB_LEAD_S = 0.030f;
static const float FB_RAMP_S = 0.004f;   // no clicks
static const float FB_LEVEL  = 0.25f;

static std::vector<uint8_t> fb_render(int which, uint32_t rate) {
  const _fb_note_t* notes; size_t n;
  switch (which) {
    case FB_TICK:      notes = _FB_TICK;  n = 1; break;
    case FB_DELIVERED: notes = _FB_OK;    n = 2; break;
    case FB_BUSY:      notes = _FB_BUSY;  n = 3; break;
    case FB_LIMIT:     notes = _FB_LIMIT; n = 3; break;
    default:           notes = _FB_ERR;   n = 2; break;
  }
  float end = 0;
  for (size_t i = 0; i < n; i++) end = fmaxf(end, notes[i].start + notes[i].dur);
  const size_t lead = (size_t) (FB_LEAD_S * rate);
  const size_t total = lead + (size_t) (end * rate) + 1;
  std::vector<uint8_t> out(total * 2, 0);
  int16_t* pcm = reinterpret_cast<int16_t*>(out.data());
  const float two_pi = 6.2831853f;
  for (size_t k = 0; k < n; k++) {
    const _fb_note_t& nt = notes[k];
    const size_t i0 = lead + (size_t) (nt.start * rate);
    const size_t len = (size_t) (nt.dur * rate);
    const size_t ramp = (size_t) (FB_RAMP_S * rate);
    for (size_t i = 0; i < len && i0 + i < total; i++) {
      const float t = (float) i / rate;
      float env = 1.0f;
      if (i < ramp) env = (float) i / ramp;
      else if (i + ramp > len) env = (float) (len - i) / ramp;
      float s = sinf(two_pi * nt.f1 * t);
      if (nt.buzz > 0) s += nt.buzz * (sinf(3 * two_pi * nt.f1 * t) / 3 +
                                       sinf(5 * two_pi * nt.f1 * t) / 5);
      if (nt.f2 > 0) s = 0.5f * (s + sinf(two_pi * nt.f2 * t));
      float v = s * env * FB_LEVEL * 32767.0f;
      int32_t acc = pcm[i0 + i] + (int32_t) v;
      if (acc > 32767) acc = 32767; else if (acc < -32768) acc = -32768;
      pcm[i0 + i] = (int16_t) acc;
    }
  }
  return out;
}

// One sound at a time; a new one replaces what is left of the last.
static std::vector<uint8_t> _fb_pcm;
static size_t _fb_pos = 0;

// Queue a sound on `spk` (a mixer source speaker). fb_pump() feeds it.
static void fb_play(esphome::speaker::Speaker* spk, int which, uint32_t rate) {
  _fb_pcm = fb_render(which, rate);
  _fb_pos = 0;
  if (spk->is_stopped()) {
    spk->set_audio_stream_info(esphome::audio::AudioStreamInfo(16, 1, rate));
    spk->start();
  }
}

// From an interval: the source speaker's ring buffer only exists once it has
// started, and holds 100 ms, so the sound goes in as space frees up.
static void fb_pump(esphome::speaker::Speaker* spk) {
  if (_fb_pcm.empty()) return;
  if (_fb_pos < _fb_pcm.size()) {
    _fb_pos += spk->play(_fb_pcm.data() + _fb_pos, _fb_pcm.size() - _fb_pos, 0);
    return;
  }
  spk->finish();
  std::vector<uint8_t>().swap(_fb_pcm);
  _fb_pos = 0;
}

// ── Direct playback (a speaker with no mixer in front: Atom Echo) ─────────────
// Rendered in small pieces as the speaker takes them, so the only allocation is
// the speaker's own buffer, the same one an incoming message makes. Callers
// must not start it while the mic runs (the Atom's mic and speaker share their
// I²S clock pins).

static const _fb_note_t* _fbd_notes = nullptr;
static size_t   _fbd_n = 0, _fbd_lead = 0, _fbd_idx = 0, _fbd_total = 0;
static uint32_t _fbd_rate = 16000;
static bool     _fbd_active = false;
static int16_t  _fbd_buf[256];
static size_t   _fbd_len = 0, _fbd_pos = 0;   // bytes in _fbd_buf / sent

static int16_t _fbd_sample(size_t idx) {
  const float two_pi = 6.2831853f;
  int32_t acc = 0;
  for (size_t k = 0; k < _fbd_n; k++) {
    const _fb_note_t& nt = _fbd_notes[k];
    const size_t i0 = _fbd_lead + (size_t) (nt.start * _fbd_rate);
    const size_t len = (size_t) (nt.dur * _fbd_rate);
    if (idx < i0 || idx >= i0 + len) continue;
    const size_t i = idx - i0;
    const size_t ramp = (size_t) (FB_RAMP_S * _fbd_rate);
    const float t = (float) i / _fbd_rate;
    float env = 1.0f;
    if (i < ramp) env = (float) i / ramp;
    else if (i + ramp > len) env = (float) (len - i) / ramp;
    float s = sinf(two_pi * nt.f1 * t);
    if (nt.buzz > 0) s += nt.buzz * (sinf(3 * two_pi * nt.f1 * t) / 3 +
                                     sinf(5 * two_pi * nt.f1 * t) / 5);
    if (nt.f2 > 0) s = 0.5f * (s + sinf(two_pi * nt.f2 * t));
    acc += (int32_t) (s * env * FB_LEVEL * 32767.0f);
  }
  if (acc > 32767) acc = 32767; else if (acc < -32768) acc = -32768;
  return (int16_t) acc;
}

// Start a sound on `spk`. False if the speaker is busy (a message is playing).
static bool fb_direct_play(esphome::speaker::Speaker* spk, int which, uint32_t rate) {
  if (_fbd_active || !spk->is_stopped()) return false;
  switch (which) {
    case FB_TICK:      _fbd_notes = _FB_TICK;  _fbd_n = 1; break;
    case FB_DELIVERED: _fbd_notes = _FB_OK;    _fbd_n = 2; break;
    case FB_BUSY:      _fbd_notes = _FB_BUSY;  _fbd_n = 3; break;
    case FB_LIMIT:     _fbd_notes = _FB_LIMIT; _fbd_n = 3; break;
    default:           _fbd_notes = _FB_ERR;   _fbd_n = 2; break;
  }
  float end = 0;
  for (size_t i = 0; i < _fbd_n; i++)
    end = fmaxf(end, _fbd_notes[i].start + _fbd_notes[i].dur);
  _fbd_rate = rate;
  _fbd_lead = (size_t) (FB_LEAD_S * rate);
  _fbd_total = _fbd_lead + (size_t) (end * rate) + 1;
  _fbd_idx = 0; _fbd_len = 0; _fbd_pos = 0;
  _fbd_active = true;
  spk->set_audio_stream_info(esphome::audio::AudioStreamInfo(16, 1, rate));
  spk->start();
  return true;
}

// The mic is about to start: stop the sound and free the I²S pins.
static void fb_direct_cancel(esphome::speaker::Speaker* spk) {
  if (!_fbd_active) return;
  _fbd_active = false;
  spk->stop();
}

// A message took the speaker: let it have it, without stopping it.
static void fb_direct_drop() { _fbd_active = false; }

// From an interval.
static void fb_direct_pump(esphome::speaker::Speaker* spk) {
  if (!_fbd_active) return;
  for (;;) {
    if (_fbd_pos >= _fbd_len) {
      if (_fbd_idx >= _fbd_total) {
        spk->finish();
        _fbd_active = false;
        return;
      }
      size_t n = 0;
      while (n < sizeof(_fbd_buf) / 2 && _fbd_idx < _fbd_total)
        _fbd_buf[n++] = _fbd_sample(_fbd_idx++);
      _fbd_len = n * 2;
      _fbd_pos = 0;
    }
    size_t w = spk->play(reinterpret_cast<uint8_t*>(_fbd_buf) + _fbd_pos,
                         _fbd_len - _fbd_pos, 0);
    if (w == 0) return;   // ring buffer full, or not started yet
    _fbd_pos += w;
  }
}
