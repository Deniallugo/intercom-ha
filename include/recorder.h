#pragma once
#include <cstdint>
#include <climits>
#include <cmath>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"

static const char*  REC_TAG   = "recorder";
static const size_t RBUF_SIZE = 32 * 1024;  // ~1 s at 16 kHz 16-bit

static StreamBufferHandle_t _sbuf       = nullptr;
static volatile bool        _rec_active = false;
static volatile bool        _rec_done   = false;

// Software gain for the captured 16-bit PCM stream. Defaults to unity (1/1 = no
// change). Devices whose mic chain has no PGA (e.g. Atom Echo PDM) can call
// recorder_set_gain(2, 1) from on_boot to add +6 dB, (4, 1) for +12 dB, etc.
// Devices whose codec already controls gain (e.g. VoiceS3R ES8311) leave this
// at the default.
static int _gain_num = 1;
static int _gain_den = 1;

// High-pass filter, off by default (recorder_set_highpass). Measured on both
// mics: 1-10 Hz drift that correct_dc_offset leaves in, swinging up to ±10000 —
// 2-12 dB LOUDER than the speech itself. With the add-on's cleanup off, that
// went straight to the amplifiers, pumped the speakers and ate the headroom any
// gain needs. It runs BEFORE the gain, so the gain is spent on the voice.
// RBJ biquad, Q = 0.707 (Butterworth, 12 dB/octave), Direct Form I in float.
static bool  _hp_on = false;
static float _hp_b0, _hp_b1, _hp_b2, _hp_a1, _hp_a2;
static float _hp_x1, _hp_x2, _hp_y1, _hp_y2;

// Samples to drop at the start of each recording (recorder_set_skip_ms). The
// Atom's PDM mic is started on the button press and its decimation filter
// spends ~50 ms settling at full scale — a click on every broadcast.
static uint32_t _skip_total = 0;
static uint32_t _skip_left  = 0;

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
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
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started");
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;

  // Fast path: nothing to do to the samples — straight passthrough.
  if (_gain_num == _gain_den && !_hp_on && _skip_left == 0) {
    size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
    if (sent < len)
      ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(len - sent));
    return;
  }

  // Slow path: skip, high-pass, then gain with saturation. Process in
  // stack-resident chunks so we don't allocate per callback. Only one callback
  // runs at a time, so the filter state needs no locking.
  const float gain = (float) _gain_num / (float) _gain_den;
  uint8_t scaled[512];
  size_t processed = 0;
  while (processed < len) {
    size_t remaining = len - processed;
    size_t chunk     = remaining > sizeof(scaled) ? sizeof(scaled) : remaining;
    chunk &= ~1u;  // even count — pairs of bytes are one 16-bit sample
    if (chunk == 0) break;

    const int16_t* in  = reinterpret_cast<const int16_t*>(data + processed);
    int16_t*       out = reinterpret_cast<int16_t*>(scaled);
    size_t         n   = chunk / 2;
    size_t         m   = 0;
    for (size_t i = 0; i < n; i++) {
      float x = (float) in[i];
      float y = x;
      if (_hp_on) {
        // Keep filtering through the skipped stretch, so the filter has
        // settled by the time samples are kept.
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
      if (sent < bytes)
        ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(bytes - sent));
    }
    processed += chunk;
  }
}

void recorder_stop() {
  _rec_active = false;
  _rec_done   = true;
  ESP_LOGI(REC_TAG, "recording stopped");
}

// Called by the uploader task: blocks up to wait_ms for data, returns bytes read
size_t recorder_drain(uint8_t* dst, size_t max_len, uint32_t wait_ms) {
  return xStreamBufferReceive(_sbuf, dst, max_len, pdMS_TO_TICKS(wait_ms));
}

bool recorder_is_active() { return _rec_active; }
bool recorder_is_done()   { return _rec_done && xStreamBufferIsEmpty(_sbuf); }
