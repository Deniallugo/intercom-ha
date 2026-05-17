#pragma once
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#include "esp_random.h"
#include <cstdio>
#include <cstring>
#include <string>

// recorder_get_len() and recorder_read() are defined in recorder.h,
// which is included before this file.

static uint8_t _send_buf[16384];  // read buffer: flash → network

static std::string _make_session_id() {
  uint8_t rnd[8];
  esp_fill_random(rnd, sizeof(rnd));
  char buf[17];
  for (int i = 0; i < 8; i++) sprintf(buf + i * 2, "%02x", rnd[i]);
  buf[16] = '\0';
  return std::string(buf);
}

static void _post_chunk(const char* host, int port, const char* path,
                        const char* session_id, int chunk_index, bool is_final,
                        const uint8_t* data, size_t len) {
  char port_str[8];
  snprintf(port_str, sizeof(port_str), "%d", port);

  struct addrinfo hints = {};
  hints.ai_family   = AF_INET;
  hints.ai_socktype = SOCK_STREAM;
  struct addrinfo* res = nullptr;
  if (::getaddrinfo(host, port_str, &hints, &res) != 0 || !res) return;

  int sock = ::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
  if (sock < 0) { ::freeaddrinfo(res); return; }
  if (::connect(sock, res->ai_addr, res->ai_addrlen) != 0) {
    ::close(sock); ::freeaddrinfo(res); return;
  }
  ::freeaddrinfo(res);

  char hdr[512];
  int hlen = snprintf(hdr, sizeof(hdr),
    "POST %s HTTP/1.0\r\n"
    "Host: %s:%d\r\n"
    "Content-Type: audio/pcm\r\n"
    "Content-Length: %zu\r\n"
    "X-Session-ID: %s\r\n"
    "X-Chunk-Index: %d\r\n"
    "%s"
    "\r\n",
    path, host, port, len, session_id, chunk_index,
    is_final ? "X-Final: 1\r\n" : "");

  ::send(sock, hdr, hlen, 0);
  ::send(sock, data, len, 0);

  char resp[64];
  ::recv(sock, resp, sizeof(resp), 0);
  ::close(sock);
}

void uploader_send(const char* url) {
  size_t total = recorder_get_len();
  if (total == 0) return;

  // Parse "http://host:port/path"
  char host[64] = {};
  int  port     = 80;
  char path[64] = "/";

  const char* p = (strncmp(url, "http://", 7) == 0) ? url + 7 : url;
  const char* colon = strchr(p, ':');
  const char* slash = strchr(p, '/');

  if (colon && (!slash || colon < slash)) {
    size_t n = colon - p;
    memcpy(host, p, n);
    port = atoi(colon + 1);
  } else if (slash) {
    size_t n = slash - p;
    memcpy(host, p, n);
  } else {
    strncpy(host, p, sizeof(host) - 1);
  }
  if (slash) strncpy(path, slash, sizeof(path) - 1);

  const size_t CHUNK = sizeof(_send_buf);
  std::string  sid   = _make_session_id();
  size_t offset = 0;
  int    idx    = 0;

  while (offset < total) {
    size_t bytes = total - offset;
    if (bytes > CHUNK) bytes = CHUNK;
    recorder_read(_send_buf, offset, bytes);
    bool is_final = (offset + bytes >= total);
    _post_chunk(host, port, path, sid.c_str(), idx, is_final, _send_buf, bytes);
    offset += bytes;
    idx++;
  }
}
