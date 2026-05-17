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
      ESP_LOGI(REC_TAG, "buffer: %zu KB = %.1f s at 48 kHz",
               s / 1024, (float)s / (48000 * 2));
      return;
    }
  }
  ESP_LOGE(REC_TAG, "buffer allocation failed");
}

void recorder_start() {
  _rec_len    = 0;
  _rec_active = (_rec_buf != nullptr);
  ESP_LOGI(REC_TAG, "recording started  buf_cap=%zu KB", _rec_buf_cap / 1024);
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_rec_buf) return;
  size_t space = _rec_buf_cap - _rec_len;
  size_t copy  = (len < space) ? len : space;
  memcpy(_rec_buf + _rec_len, data, copy);
  _rec_len += copy;
  if (_rec_len >= _rec_buf_cap)
    _rec_active = false;
}

void recorder_stop() {
  _rec_active = false;
  ESP_LOGI(REC_TAG, "recorded %zu bytes (%.2f s at 48 kHz)",
           _rec_len, (float)_rec_len / (48000 * 2));
}
