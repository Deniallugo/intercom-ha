#pragma once
#include <cstdint>
#include <cstring>
#include "esp_log.h"
#include "esp_partition.h"

static const char*  REC_TAG    = "recorder";
static const size_t REC_MAX    = 512 * 1024;  // 5.3 s at 48 kHz
static const size_t REC_SECTOR = 4096;

static const esp_partition_t* _part       = nullptr;
static size_t                 _rec_len    = 0;
static size_t                 _erased_to  = 0;
static bool                   _rec_active = false;

void recorder_init() {
  _part = esp_partition_find_first(
      ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, nullptr);
  if (!_part) {
    ESP_LOGE(REC_TAG, "no spiffs partition found");
    return;
  }
  size_t cap = (_part->size < REC_MAX) ? _part->size : REC_MAX;
  ESP_LOGI(REC_TAG, "flash ready: %zu KB = %.1f s at 48 kHz",
           cap / 1024, (float)cap / (48000 * 2));
}

void recorder_start() {
  if (!_part) { ESP_LOGE(REC_TAG, "no partition, cannot record"); return; }
  _rec_len    = 0;
  _erased_to  = 0;
  _rec_active = true;
  // Erase first sector so the first write is ready immediately
  esp_partition_erase_range(_part, 0, REC_SECTOR);
  _erased_to = REC_SECTOR;
  ESP_LOGI(REC_TAG, "recording started");
}

// Called from I2S task at 48 kHz.  Erases the next flash sector just before
// the write pointer crosses into it — the I2S DMA buffer (~85 ms) absorbs the
// ~10 ms sector-erase pause without dropping samples.
void recorder_on_data(const uint8_t* data, size_t len) {
  if (!_rec_active || !_part) return;
  len &= ~3u;  // flash writes must be 4-byte aligned
  if (len == 0) return;
  size_t cap = (_part->size < REC_MAX) ? _part->size : REC_MAX;
  size_t space = cap - _rec_len;
  if (len > space) { len = space & ~3u; _rec_active = false; }
  if (len == 0) return;
  size_t end = _rec_len + len;
  while (_erased_to < end) {
    esp_partition_erase_range(_part, _erased_to, REC_SECTOR);
    _erased_to += REC_SECTOR;
  }
  esp_partition_write(_part, _rec_len, data, len);
  _rec_len += len;
}

void recorder_stop() {
  _rec_active = false;
  ESP_LOGI(REC_TAG, "recorded %zu bytes (%.2f s at 48 kHz)",
           _rec_len, (float)_rec_len / (48000 * 2));
}

size_t recorder_get_len() { return _rec_len; }

void recorder_read(uint8_t* dst, size_t offset, size_t len) {
  if (_part) esp_partition_read(_part, offset, dst, len);
}
