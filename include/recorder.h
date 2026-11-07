#pragma once
#include <cstdint>
#include <climits>
#include <cmath>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"
#include "freertos/idf_additions.h"
#include "esp_heap_caps.h"

static const char*  REC_TAG   = "recorder";
static const size_t RBUF_SIZE = 32 * 1024;  // ~1 s at 16 kHz 16-bit

static StreamBufferHandle_t _sbuf       = nullptr;
static volatile bool        _rec_active = false;
static volatile bool        _rec_done   = false;
static bool                 _rec_full_logged = false;  // "buffer full" once per take

// Software gain (recorder_set_gain), unity by default. For mics with no PGA.
static int _gain_num = 1;
static int _gain_den = 1;

// High-pass (recorder_set_highpass), off by default. Removes 1-10 Hz drift that
// correct_dc_offset leaves in, louder than speech. Runs before the gain.
// RBJ biquad, Butterworth Q, Direct Form I.
static bool  _hp_on = false;
static float _hp_b0, _hp_b1, _hp_b2, _hp_a1, _hp_a2;
static float _hp_x1, _hp_x2, _hp_y1, _hp_y2;

// Samples to drop at the start of each recording (recorder_set_skip_ms), e.g.
// the Atom's ~50 ms full-scale PDM start-up burst.
static uint32_t _skip_total = 0;
static uint32_t _skip_left  = 0;

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
}

// Buffer in PSRAM, for audio that waits before its upload starts.
void recorder_init_psram(size_t bytes) {
  _sbuf = xStreamBufferCreateWithCaps(bytes, 1, MALLOC_CAP_SPIRAM);
  if (!_sbuf) {
    ESP_LOGE(REC_TAG, "PSRAM stream buffer alloc (%u KB) failed — falling back to "
             "%u KB internal: anything recorded before its upload starts "
             "(PTT pre-roll, mic test) will be truncated to ~1 s",
             (unsigned)(bytes / 1024), (unsigned)(RBUF_SIZE / 1024));
    recorder_init();
    return;
  }
  ESP_LOGI(REC_TAG, "ready (%u KB ring buffer in PSRAM)", (unsigned)(bytes / 1024));
}

void recorder_set_gain(int num, int den) {
  if (den <= 0 || num <= 0) {
    ESP_LOGW(REC_TAG, "invalid gain ratio %d/%d — ignoring", num, den);
    return;
  }
  _gain_num = num;
  _gain_den = den;
  ESP_LOGI(REC_TAG, "software gain set to %d/%d", num, den);
}

// Cutoff in Hz at 16 kHz; 0 turns it off. Call from on_boot.
void recorder_set_highpass(float hz) {
  if (hz <= 0) { _hp_on = false; ESP_LOGI(REC_TAG, "high-pass off"); return; }
  const float fs = 16000.0f, q = 0.7071f;
  const float w0 = 2.0f * (float) M_PI * hz / fs;
  const float c = cosf(w0), alpha = sinf(w0) / (2.0f * q), a0 = 1.0f + alpha;
  _hp_b0 =  (1.0f + c) / 2.0f / a0;
  _hp_b1 = -(1.0f + c) / a0;
  _hp_b2 =  (1.0f + c) / 2.0f / a0;
  _hp_a1 = -2.0f * c / a0;
  _hp_a2 =  (1.0f - alpha) / a0;
  _hp_on = true;
  ESP_LOGI(REC_TAG, "high-pass %.0f Hz", hz);
}

void recorder_set_skip_ms(uint32_t ms) {
  _skip_total = ms * 16;   // 16 samples per ms at 16 kHz
  ESP_LOGI(REC_TAG, "dropping first %u ms of each recording", (unsigned) ms);
}

void recorder_start() {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _hp_x1 = _hp_x2 = _hp_y1 = _hp_y2 = 0.0f;
  _skip_left = _skip_total;
  _rec_full_logged = false;
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started");
}

// Once per recording: a full buffer would log on every callback.
static void _rec_dropped(size_t n) {
  if (_rec_full_logged) return;
  _rec_full_logged = true;
  ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes (further drops in this "
           "recording not logged)", (unsigned) n);
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;

  if (_gain_num == _gain_den && !_hp_on && _skip_left == 0) {
    size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
    if (sent < len) _rec_dropped(len - sent);
    return;
  }

  // Skip, high-pass, gain. Stack chunks, no per-callback allocation; callbacks
  // don't overlap, so the filter state needs no lock.
  const float gain = (float) _gain_num / (float) _gain_den;
  uint8_t scaled[512];
  size_t processed = 0;
  while (processed < len) {
    size_t remaining = len - processed;
    size_t chunk     = remaining > sizeof(scaled) ? sizeof(scaled) : remaining;
    chunk &= ~1u;  // whole 16-bit samples
    if (chunk == 0) break;

    const int16_t* in  = reinterpret_cast<const int16_t*>(data + processed);
    int16_t*       out = reinterpret_cast<int16_t*>(scaled);
    size_t         n   = chunk / 2;
    size_t         m   = 0;
    for (size_t i = 0; i < n; i++) {
      float x = (float) in[i];
      float y = x;
      if (_hp_on) {
        // Filter through the skipped stretch so it has settled.
        y = _hp_b0 * x + _hp_b1 * _hp_x1 + _hp_b2 * _hp_x2
          - _hp_a1 * _hp_y1 - _hp_a2 * _hp_y2;
        _hp_x2 = _hp_x1; _hp_x1 = x;
        _hp_y2 = _hp_y1; _hp_y1 = y;
      }
      if (_skip_left > 0) { _skip_left--; continue; }
      float s = y * gain;
      if (s > INT16_MAX)      s = INT16_MAX;
      else if (s < INT16_MIN) s = INT16_MIN;
      out[m++] = (int16_t) lrintf(s);
    }

    if (m > 0) {
      size_t bytes = m * 2;
      size_t sent  = xStreamBufferSend(_sbuf, scaled, bytes, 0);
      if (sent < bytes) _rec_dropped(bytes - sent);
    }
    processed += chunk;
  }
}

// Discard a recording without marking it done (voice-s3's tap).
void recorder_cancel() {
  _rec_active = false;
  _rec_done   = false;
  if (_sbuf) xStreamBufferReset(_sbuf);
  ESP_LOGI(REC_TAG, "recording cancelled");
}

// Empty the buffer, keep the recording state. For an aborted upload.
void recorder_discard() {
  if (_sbuf) xStreamBufferReset(_sbuf);
}

void recorder_stop() {
  _rec_active = false;
  _rec_done   = true;
  ESP_LOGI(REC_TAG, "recording stopped");
}

// Blocks up to wait_ms; returns bytes read.
size_t recorder_drain(uint8_t* dst, size_t max_len, uint32_t wait_ms) {
  return xStreamBufferReceive(_sbuf, dst, max_len, pdMS_TO_TICKS(wait_ms));
}

bool recorder_is_active() { return _rec_active; }
bool recorder_is_done()   { return _rec_done && xStreamBufferIsEmpty(_sbuf); }
