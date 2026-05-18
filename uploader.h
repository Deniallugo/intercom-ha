#pragma once
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_random.h"
#include <cstdio>
#include <cstring>
#include <string>

static const char* UPL_TAG = "uploader";

static uint8_t       _upl_buf[4096];
static volatile bool _uploading = false;

struct _upl_args_t { const char* url; const char* device; };
static _upl_args_t _upl_args;

static std::string _make_sid() {
  uint8_t r[8]; esp_fill_random(r, 8);
  char s[17];
  for (int i = 0; i < 8; i++) sprintf(s + i * 2, "%02x", r[i]);
  s[16] = '\0';
  return std::string(s);
}

static void _stream_task(void* arg) {
  auto* args = static_cast<_upl_args_t*>(arg);
  const char* url    = args->url;
  const char* device = args->device;

  // Parse "http://host:port/path"
  char host[64] = {}, path[64] = "/";
  int  port = 80;
  const char* p     = strncmp(url, "http://", 7) == 0 ? url + 7 : url;
  const char* colon = strchr(p, ':');
  const char* slash = strchr(p, '/');
  if (colon && (!slash || colon < slash)) {
    memcpy(host, p, colon - p);
    port = atoi(colon + 1);
  } else if (slash) {
    memcpy(host, p, slash - p);
  } else {
    strncpy(host, p, sizeof(host) - 1);
  }
  if (slash) strncpy(path, slash, sizeof(path) - 1);

  // Resolve + connect
  char port_s[8]; snprintf(port_s, sizeof(port_s), "%d", port);
  struct addrinfo hints = {}, *res = nullptr;
  hints.ai_family = AF_INET; hints.ai_socktype = SOCK_STREAM;
  if (::getaddrinfo(host, port_s, &hints, &res) != 0 || !res) {
    ESP_LOGE(UPL_TAG, "DNS failed for %s", host);
    _uploading = false; vTaskDelete(nullptr); return;
  }
  int sock = ::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
  if (::connect(sock, res->ai_addr, res->ai_addrlen) != 0) {
    ESP_LOGE(UPL_TAG, "connect failed");
    ::close(sock); ::freeaddrinfo(res); _uploading = false; vTaskDelete(nullptr); return;
  }
  ::freeaddrinfo(res);

  // Send HTTP headers — chunked streaming body
  auto sid = _make_sid();
  char hdr[512];
  int hlen = snprintf(hdr, sizeof(hdr),
    "POST %s HTTP/1.1\r\nHost: %s:%d\r\n"
    "Content-Type: audio/pcm\r\nTransfer-Encoding: chunked\r\n"
    "X-Session-ID: %s\r\nX-Device-Name: %s\r\nConnection: close\r\n\r\n",
    path, host, port, sid.c_str(), device ? device : "");
  ::send(sock, hdr, hlen, 0);
  ESP_LOGI(UPL_TAG, "streaming  session=%s device=%s", sid.c_str(), device ? device : "");

  size_t total = 0;
  while (!recorder_is_done()) {
    size_t n = recorder_drain(_upl_buf, sizeof(_upl_buf), 20);
    if (n == 0) continue;
    char szl[12]; int sl = snprintf(szl, sizeof(szl), "%x\r\n", (unsigned)n);
    ::send(sock, szl, sl, 0);
    ::send(sock, _upl_buf, n, 0);
    ::send(sock, "\r\n", 2, 0);
    total += n;
  }

  // Terminating chunk
  ::send(sock, "0\r\n\r\n", 5, 0);
  ESP_LOGI(UPL_TAG, "sent %u bytes, awaiting response", (unsigned)total);

  char resp[256] = {};
  ::recv(sock, resp, sizeof(resp) - 1, 0);
  ::close(sock);

  ESP_LOGI(UPL_TAG, "done");
  _uploading = false;
  vTaskDelete(nullptr);
}

void uploader_start(const char* url, const char* device) {
  if (_uploading) { ESP_LOGW(UPL_TAG, "already uploading, ignoring"); return; }
  _uploading = true;
  _upl_args.url    = url;
  _upl_args.device = device;
  xTaskCreate(_stream_task, "uploader", 4096, &_upl_args, 5, nullptr);
}

bool uploader_is_uploading() { return _uploading; }
