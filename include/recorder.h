#pragma once
#include <cstdint>
#include <climits>
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

void recorder_start() {
  if (!_sbuf) return;
  xStreamBufferReset(_sbuf);
  _rec_done   = false;
  _rec_active = true;
  ESP_LOGI(REC_TAG, "recording started");
}

void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_sbuf) return;

  // Fast path: no gain — straight passthrough.
  if (_gain_num == _gain_den) {
    size_t sent = xStreamBufferSend(_sbuf, data, len, 0);
    if (sent < len)
      ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(len - sent));
    return;
  }

  // Slow path: apply gain with saturation. Process in stack-resident chunks
  // so we don't allocate per callback. Only one callback runs at a time.
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
    for (size_t i = 0; i < n; i++) {
      int32_t s = (int32_t)in[i] * _gain_num / _gain_den;
      if (s > INT16_MAX)      s = INT16_MAX;
      else if (s < INT16_MIN) s = INT16_MIN;
      out[i] = (int16_t)s;
    }

    size_t sent = xStreamBufferSend(_sbuf, scaled, chunk, 0);
    if (sent < chunk)
      ESP_LOGW(REC_TAG, "buffer full, dropped %u bytes", (unsigned)(chunk - sent));
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
