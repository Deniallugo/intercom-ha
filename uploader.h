#pragma once
#include "SPIFFS.h"
#include <HTTPClient.h>
#include <esp_system.h>

static std::string _make_session_id() {
  uint8_t rnd[8];
  esp_fill_random(rnd, sizeof(rnd));
  char buf[17];
  for (int i = 0; i < 8; i++) sprintf(buf + i * 2, "%02x", rnd[i]);
  buf[16] = '\0';
  return std::string(buf);
}

// Read /rec.pcm from SPIFFS and POST it in CHUNK_SIZE chunks to `url`.
// Headers X-Session-ID, X-Chunk-Index, and X-Final identify the session.
// Deletes /rec.pcm after upload.
void uploader_send(const char* url) {
  File f = SPIFFS.open("/rec.pcm", "r");
  if (!f || f.size() == 0) {
    if (f) f.close();
    return;
  }

  const size_t CHUNK_SIZE = 16384;
  std::string session_id = _make_session_id();
  uint8_t* buf = (uint8_t*) malloc(CHUNK_SIZE);
  if (!buf) { f.close(); return; }

  int chunk_index = 0;
  while (f.available()) {
    size_t bytes_read = f.read(buf, CHUNK_SIZE);
    bool is_final = !f.available();

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "audio/pcm");
    http.addHeader("X-Session-ID", session_id.c_str());
    http.addHeader("X-Chunk-Index", String(chunk_index).c_str());
    if (is_final) http.addHeader("X-Final", "1");
    http.sendRequest("POST", buf, bytes_read);
    http.end();
    chunk_index++;
  }

  free(buf);
  f.close();
  SPIFFS.remove("/rec.pcm");
}
