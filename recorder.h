#pragma once
#include "SPIFFS.h"

static File _rec_file;
static bool _rec_active = false;

// Call once at boot to mount SPIFFS.
void recorder_init() {
  SPIFFS.begin(true);
}

// Open /rec.pcm for writing. Overwrites any previous recording.
void recorder_start() {
  SPIFFS.remove("/rec.pcm");
  _rec_file = SPIFFS.open("/rec.pcm", "w");
  _rec_active = _rec_file ? true : false;
}

// Called from the microphone data callback — writes raw PCM bytes.
void recorder_on_data(const uint8_t* data, size_t len) {
  if (_rec_active && _rec_file) {
    _rec_file.write(data, len);
  }
}

// Flush and close the file. Call before uploader_send().
void recorder_stop() {
  _rec_active = false;
  if (_rec_file) {
    _rec_file.flush();
    _rec_file.close();
  }
}
