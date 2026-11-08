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
