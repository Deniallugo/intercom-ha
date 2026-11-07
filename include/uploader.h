#pragma once
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_random.h"
#include <cstdio>
#include <cerrno>
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

static const int UPL_TIMEOUT_S = 8;   // per send()/recv()/connect()

// send() until all `len` bytes are out; false on error or timeout.
static bool _send_all(int sock, const void* buf, size_t len) {
  const uint8_t* p = static_cast<const uint8_t*>(buf);
  while (len > 0) {
    int n = ::send(sock, p, len, 0);
    if (n <= 0) return false;
    p += n; len -= (size_t) n;
  }
  return true;
}

// Every exit path of the task ends here, so _uploading always clears. With
// `discard`, the recording the upload abandoned is drained to nowhere until it
// ends — leaving it would hand its stale tail to the next upload, and a full
// buffer would drop the next recording's start. Bounded, so a recorder nobody
// stops cannot pin this task.
static void _upl_finish(int sock, bool discard) {
  if (sock >= 0) ::close(sock);
  if (discard) {
    const TickType_t give_up = xTaskGetTickCount() + pdMS_TO_TICKS(120000);
    while (!recorder_is_done() && xTaskGetTickCount() < give_up)
      recorder_drain(_upl_buf, sizeof(_upl_buf), 20);
    recorder_discard();
  }
  _uploading = false;
  vTaskDelete(nullptr);
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
    _upl_finish(-1, false);
    return;
  }
  int sock = ::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
  if (sock < 0) {
    ESP_LOGE(UPL_TAG, "socket() failed: errno %d", errno);
    ::freeaddrinfo(res);
    _upl_finish(-1, false);
    return;
  }
  // Without these a Wi-Fi drop mid-request blocks send()/recv() forever, and
  // since _uploading never clears, every later PTT is refused until a reboot.
  // SO_SNDTIMEO also bounds lwIP's connect().
  struct timeval tv;
  tv.tv_sec = UPL_TIMEOUT_S; tv.tv_usec = 0;
  ::setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  ::setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  if (::connect(sock, res->ai_addr, res->ai_addrlen) != 0) {
    ESP_LOGE(UPL_TAG, "connect to %s:%d failed: errno %d", host, port, errno);
    ::freeaddrinfo(res);
    _upl_finish(sock, false);
    return;
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
  if (hlen < 0 || hlen >= (int)sizeof(hdr)) {
    ESP_LOGE(UPL_TAG, "header too large (need %d, max %u) — aborting",
             hlen, (unsigned)sizeof(hdr));
    _upl_finish(sock, false);
    return;
  }
  bool ok = _send_all(sock, hdr, hlen);
  if (ok) ESP_LOGI(UPL_TAG, "streaming  session=%s device=%s", sid.c_str(), device ? device : "");

  size_t total = 0;
  while (ok && !recorder_is_done()) {
    size_t n = recorder_drain(_upl_buf, sizeof(_upl_buf), 20);
    if (n == 0) continue;
    char szl[12]; int sl = snprintf(szl, sizeof(szl), "%x\r\n", (unsigned)n);
    ok = _send_all(sock, szl, sl) && _send_all(sock, _upl_buf, n) &&
         _send_all(sock, "\r\n", 2);
    if (ok) total += n;
  }
  if (!ok) {
    ESP_LOGE(UPL_TAG, "send failed after %u bytes: errno %d — upload abandoned",
             (unsigned)total, errno);
    _upl_finish(sock, true);
    return;
  }

  // Terminating chunk
  if (!_send_all(sock, "0\r\n\r\n", 5)) {
    ESP_LOGE(UPL_TAG, "send of final chunk failed: errno %d", errno);
    _upl_finish(sock, false);
    return;
  }
  ESP_LOGI(UPL_TAG, "sent %u bytes, awaiting response", (unsigned)total);

  char resp[256] = {};
  if (::recv(sock, resp, sizeof(resp) - 1, 0) < 0)
    ESP_LOGW(UPL_TAG, "no response within %d s: errno %d", UPL_TIMEOUT_S, errno);
  else
    ESP_LOGI(UPL_TAG, "done");
  _upl_finish(sock, false);
}

void uploader_start(const char* url, const char* device) {
  if (_uploading) { ESP_LOGW(UPL_TAG, "already uploading, ignoring"); return; }
  _uploading = true;
  _upl_args.url    = url;
  _upl_args.device = device;
  if (xTaskCreate(_stream_task, "uploader", 4096, &_upl_args, 5, nullptr) != pdPASS) {
    ESP_LOGE(UPL_TAG, "could not start upload task");
    _uploading = false;
  }
}

bool uploader_is_uploading() { return _uploading; }
