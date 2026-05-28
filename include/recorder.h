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

void recorder_init() {
  _sbuf = xStreamBufferCreate(RBUF_SIZE, 1);
  if (!_sbuf) ESP_LOGE(REC_TAG, "stream buffer alloc failed");
  else        ESP_LOGI(REC_TAG, "ready (%u KB ring buffer)", (unsigned)(RBUF_SIZE / 1024));
}

void recorder_start() {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started");
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;
  size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
  if (sent < len)
    ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(len - sent));
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
