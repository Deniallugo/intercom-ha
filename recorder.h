#pragma once
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include "esp_log.h"

static const char* REC_TAG = "recorder";

static uint8_t* _rec_buf     = nullptr;
static size_t   _rec_buf_cap = 0;
static size_t   _rec_len     = 0;
static bool     _rec_active  = false;

// Decimation state: average 3 input samples (48 kHz) → 1 output sample (16 kHz).
static int32_t _dec_accum = 0;
static int     _dec_count = 0;

void recorder_init() {
  const size_t sizes[] = {
    384 * 1024,
    320 * 1024,
    256 * 1024,
    192 * 1024,
    128 * 1024,
     96 * 1024,
  };
  for (size_t s : sizes) {
    _rec_buf = (uint8_t*) malloc(s);
    if (_rec_buf) {
      _rec_buf_cap = s;
      ESP_LOGI(REC_TAG, "buffer: %zu KB = %.1f s at 16 kHz",
               s / 1024, (float)s / (16000 * 2));
      return;
    }
  }
  ESP_LOGE(REC_TAG, "buffer allocation failed");
}

void recorder_start() {
  _rec_len    = 0;
  _rec_active = (_rec_buf != nullptr);
  _dec_accum  = 0;
  _dec_count  = 0;
}

// Input: raw 48 kHz 16-bit PCM bytes from ESPHome callback.
// Output: decimated to 16 kHz via 3-tap box filter (averages 3 samples → 1).
void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_rec_buf) return;
  for (size_t i = 0; i + 1 < len; i += 2) {
    int16_t s;
    memcpy(&s, data + i, 2);
    _dec_accum += s;
    if (++_dec_count == 3) {
      int16_t out = (int16_t)(_dec_accum / 3);
      if (_rec_len + 2 <= _rec_buf_cap) {
        memcpy(_rec_buf + _rec_len, &out, 2);
        _rec_len += 2;
      } else {
        _rec_active = false;  // buffer full
      }
      _dec_accum = 0;
      _dec_count = 0;
    }
  }
}

void recorder_stop() {
  _rec_active = false;
  ESP_LOGI(REC_TAG, "recorded %zu bytes (%.1f s at 16 kHz)",
           _rec_len, (float)_rec_len / (16000 * 2));
}
