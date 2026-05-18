#pragma once
#include <cstdint>
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"

static const char*  REC_TAG   = "recorder";
static const size_t RBUF_SIZE = 16 * 1024;  // ~500 ms at 16 kHz 16-bit

// VAD tuning (compile-time constants in v1)
static const uint32_t VAD_MIN_MS         = 1000;
static const uint32_t VAD_SILENCE_MS     = 1200;
static const uint32_t VAD_MAX_MS         = 15000;
static const uint32_t VAD_RMS_THRESHOLD  = 600;

enum rec_mode_t { REC_HOLD, REC_VAD };

static StreamBufferHandle_t _sbuf       = nullptr;
static volatile bool        _rec_active = false;
static volatile bool        _rec_done   = false;
static rec_mode_t           _mode       = REC_HOLD;
static uint64_t             _start_us     = 0;
static uint64_t             _last_loud_us = 0;

static inline uint64_t _now_us() { return esp_timer_get_time(); }

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
}

static void _start_common(rec_mode_t mode) {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _mode = mode;
  _start_us = _now_us();
  _last_loud_us = _start_us;
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started (mode=%s)",
           mode == REC_HOLD ? "HOLD" : "VAD");
}

void recorder_start() {
  _start_common(REC_HOLD);
}

void recorder_start_vad() {
  _start_common(REC_VAD);
}

static uint16_t _rms_int16(const uint8_t* data, size_t len) {
  if (len < 2) return 0;
  uint64_t sumsq = 0;
  size_t   n     = len / 2;
  const int16_t* s = reinterpret_cast<const int16_t*>(data);
  for (size_t i = 0; i < n; i++) {
    int32_t v = s[i];
    sumsq += static_cast<uint64_t>(v * v);
  }
  uint64_t mean = sumsq / n;
  // Integer sqrt (Newton)
  uint64_t r = mean;
  for (int j = 0; j < 8 && r > 0; j++) r = (r + mean / r) / 2;
  return static_cast<uint16_t>(r > 0xFFFF ? 0xFFFF : r);
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;
  size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
  if (sent < len)
    ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(len - sent));

  if (_mode == REC_VAD) {
    uint64_t now = _now_us();
    uint64_t elapsed_ms = (now - _start_us) / 1000;
    if (_rms_int16(data, len) >= VAD_RMS_THRESHOLD) {
      _last_loud_us = now;
    }
    uint64_t silence_ms = (now - _last_loud_us) / 1000;
    if (elapsed_ms >= VAD_MIN_MS && silence_ms >= VAD_SILENCE_MS) {
      _rec_active = false;
      _rec_done   = true;
      ESP_LOGI(REC_TAG, "VAD stop (silence %llums)",
               (unsigned long long)silence_ms);
    } else if (elapsed_ms >= VAD_MAX_MS) {
      _rec_active = false;
      _rec_done   = true;
      ESP_LOGI(REC_TAG, "VAD hard cap (%llums)",
               (unsigned long long)elapsed_ms);
    }
  }
}

void recorder_stop() {
  _rec_active = false;
  _rec_done   = true;
  ESP_LOGI(REC_TAG, "recording stopped");
}

size_t recorder_drain(uint8_t* dst, size_t max_len, uint32_t wait_ms) {
  return xStreamBufferReceive(_sbuf, dst, max_len, pdMS_TO_TICKS(wait_ms));
}

bool recorder_is_active() { return _rec_active; }
bool recorder_is_done()   { return _rec_done && xStreamBufferIsEmpty(_sbuf); }
