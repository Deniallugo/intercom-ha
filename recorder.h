#pragma once
#include <cstdint>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/stream_buffer.h"

static const char*  REC_TAG   = "recorder";
static const size_t RBUF_SIZE = 32 * 1024;  // ~1 s at 16 kHz 16-bit

static StreamBufferHandle_t _sbuf       = nullptr;
static volatile bool        _rec_active = false;
static volatile bool        _rec_done   = false;
static bool                 _logged_fmt = false;
static uint8_t              _pack_buf[2048];

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
}

void recorder_start() {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _rec_done   = false;
  _logged_fmt = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started");
}

// ESP32 I2S PDM RX delivers 32-bit words even when configured for 16-bit.
// The 16-bit sample is in the upper half (bytes [2,3] in little-endian);
// the lower half is zero padding. We pack only the real samples before
// queueing — otherwise playback is 2x slow with a high-frequency buzz.
void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;

  if (!_logged_fmt && len >= 16) {
    _logged_fmt = true;
    ESP_LOGI(REC_TAG, "first 16 raw bytes: %02x %02x %02x %02x  %02x %02x %02x %02x  "
                      "%02x %02x %02x %02x  %02x %02x %02x %02x",
             data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
             data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15]);
  }

  size_t pi = 0;
  for (size_t i = 0; i + 3 < len && pi + 1 < sizeof(_pack_buf); i += 4) {
    _pack_buf[pi++] = data[i + 2];
    _pack_buf[pi++] = data[i + 3];
  }
  if (pi == 0) return;

  size_t sent = xStreamBufferSend(_sbuf, _pack_buf, pi, 0);
  if (sent < pi)
    ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(pi - sent));
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
