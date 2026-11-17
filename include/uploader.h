#pragma once
// Chunked HTTP upload of a PTT recording, on one long-lived task.
//
//   uploader_begin()  at the press: resolve + connect while the user decides
//                     whether this is a tap or a hold. Nothing is sent yet.
//   uploader_commit() hold confirmed: send the request (optionally as a reply)
//                     and stream the recorder until recorder_stop().
//   uploader_cancel() tap: close the idle connection; the add-on sees nothing.
//   uploader_start()  begin + commit at once (mic test).
//   uploader_probe()  connect-only reachability check, between uploads.
//
// The task is created once at boot (uploader_init) so a press doesn't allocate
// a 4 KB stack: on the Atom Echo every allocation fragments the DMA heap.
#include "lwip/netdb.h"
#include "lwip/sockets.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_timer.h"
#include <cstdio>
#include <cstdlib>
#include <cerrno>
#include <fcntl.h>
#include <cstring>

static const char* UPL_TAG = "uploader";

static const int UPL_IO_TIMEOUT_S    = 8;   // connect() and each send()
// After the last chunk the add-on denoises and starts playback before it
// answers: seconds on a Pi for a long message.
static const int UPL_REPLY_TIMEOUT_S = 25;
static const int UPL_PROBE_TIMEOUT_S = 5;

enum UplResult : int {
  UPL_NONE = 0,      // nothing run yet
  UPL_PENDING,       // in progress
  UPL_HTTP,          // got an HTTP response: see uploader_http_status()
  UPL_NET_ERROR,     // DNS, connect or send failed
  UPL_TIMEOUT,       // sent everything, no response in UPL_REPLY_TIMEOUT_S
  UPL_CANCELLED,     // tap: dropped before anything was sent
};

enum UplAddon : int { UPL_ADDON_UNKNOWN = 0, UPL_ADDON_UP, UPL_ADDON_DOWN };

static uint8_t       _upl_buf[4096];
static TaskHandle_t  _upl_task = nullptr;

static char          _upl_url[256];
static char          _upl_probe_url[256];
static char          _upl_device[64];

static volatile bool _uploading     = false;   // a PTT job is pending or running
static volatile bool _upl_job       = false;   // job waiting for the task
static volatile bool _upl_commit    = false;
static volatile bool _upl_cancel    = false;
static volatile bool _upl_reply     = false;
static volatile bool _probing       = false;   // probe pending or running
static volatile bool _upl_probe_job = false;

static volatile int  _upl_result = UPL_NONE;
static volatile int  _upl_status = 0;          // HTTP status, 0 if none
// From the add-on's JSON body; -1 when absent (older add-on, cut-off body).
static volatile int  _upl_delivered = -1, _upl_queued = -1, _upl_failed = -1;
static volatile int  _upl_addon = UPL_ADDON_UNKNOWN;

static void _make_sid(char out[17]) {
  uint8_t r[8]; esp_fill_random(r, 8);
  for (int i = 0; i < 8; i++) sprintf(out + i * 2, "%02x", r[i]);
  out[16] = '\0';
}

struct _upl_target_t { char host[64]; char path[192]; int port; };

// "http://host[:port][/path[?query]]". The query (e.g. ?token=…) stays in path.
static bool _parse_url(const char* url, _upl_target_t& t) {
  memset(&t, 0, sizeof(t));
  t.port = 80;
  strcpy(t.path, "/");
  const char* p = strncmp(url, "http://", 7) == 0 ? url + 7 : url;
  const char* slash = strchr(p, '/');
  const char* end_host = slash ? slash : p + strlen(p);
  const char* colon = (const char*) memchr(p, ':', end_host - p);
  const char* host_end = colon ? colon : end_host;
  size_t hlen = host_end - p;
  if (hlen == 0 || hlen >= sizeof(t.host)) return false;
  memcpy(t.host, p, hlen);
  if (colon) t.port = atoi(colon + 1);
  if (t.port <= 0 || t.port > 65535) return false;
  if (slash) {
    if (strlen(slash) >= sizeof(t.path)) return false;
    strcpy(t.path, slash);
  }
  return true;
}

// True if the caller should give up waiting (connect slices check this).
typedef bool (*_upl_abort_fn)();

// connect() bounded by timeout_s and abortable. lwIP's blocking connect()
// ignores SO_SNDTIMEO and waits out the SYN retries (a minute or more), so
// connect non-blocking and wait for writability in short slices.
static bool _connect_timeout(int sock, const struct sockaddr* addr, socklen_t len,
                             int timeout_s, _upl_abort_fn abort_fn) {
  int flags = ::fcntl(sock, F_GETFL, 0);
  if (flags < 0 || ::fcntl(sock, F_SETFL, flags | O_NONBLOCK) < 0) return false;
  int r = ::connect(sock, addr, len);
  if (r != 0 && errno != EINPROGRESS) return false;
  if (r != 0) {
    const int64_t give_up = esp_timer_get_time() + (int64_t) timeout_s * 1000000;
    for (;;) {
      if (abort_fn && abort_fn()) { errno = ECANCELED; return false; }
      fd_set wfds; FD_ZERO(&wfds); FD_SET(sock, &wfds);
      struct timeval tv; tv.tv_sec = 0; tv.tv_usec = 50000;
      int s = ::select(sock + 1, nullptr, &wfds, nullptr, &tv);
      if (s > 0) break;
      if (s < 0 || esp_timer_get_time() > give_up) { errno = ETIMEDOUT; return false; }
    }
    int err = 0; socklen_t elen = sizeof(err);
    if (::getsockopt(sock, SOL_SOCKET, SO_ERROR, &err, &elen) != 0 || err != 0) {
      errno = err ? err : errno;
      return false;
    }
  }
  return ::fcntl(sock, F_SETFL, flags) == 0;   // blocking again for send/recv
}

// Resolve + connect. Returns the socket or -1.
static int _open(const _upl_target_t& t, int timeout_s, _upl_abort_fn abort_fn) {
  char port_s[8]; snprintf(port_s, sizeof(port_s), "%d", t.port);
  struct addrinfo hints = {}, *res = nullptr;
  hints.ai_family = AF_INET; hints.ai_socktype = SOCK_STREAM;
  if (::getaddrinfo(t.host, port_s, &hints, &res) != 0 || !res) {
    ESP_LOGW(UPL_TAG, "DNS failed for %s", t.host);
    return -1;
  }
  int sock = ::socket(res->ai_family, res->ai_socktype, res->ai_protocol);
  if (sock < 0) {
    ESP_LOGE(UPL_TAG, "socket() failed: errno %d", errno);
    ::freeaddrinfo(res);
    return -1;
  }
  // Without timeouts a Wi-Fi drop blocks forever and every later PTT is refused
  // until reboot.
  struct timeval tv; tv.tv_sec = UPL_IO_TIMEOUT_S; tv.tv_usec = 0;
  ::setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  ::setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  bool ok = _connect_timeout(sock, res->ai_addr, res->ai_addrlen, timeout_s, abort_fn);
  ::freeaddrinfo(res);
  if (!ok) {
    if (errno != ECANCELED)
      ESP_LOGW(UPL_TAG, "connect to %s:%d failed: errno %d", t.host, t.port, errno);
    ::close(sock);
    return -1;
  }
  return sock;
}

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

// Last `"key": <int>` in s, or -1. The add-on puts its counts after the
// per-target results, so the last match is the top-level one.
static int _json_last_int(const char* s, const char* key) {
  char pat[24]; snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char* hit = nullptr;
  for (const char* p = strstr(s, pat); p; p = strstr(p + 1, pat)) hit = p;
  if (!hit) return -1;
  hit += strlen(pat);
  while (*hit == ' ') hit++;
  if (*hit != ':') return -1;
  hit++;
  while (*hit == ' ') hit++;
  if (*hit < '0' || *hit > '9') return -1;
  return atoi(hit);
}

// Read the whole response (Connection: close). Keeps the status line and the
// last ~640 bytes of the body, which hold the counts.
static void _read_response(int sock) {
  struct timeval tv; tv.tv_sec = UPL_REPLY_TIMEOUT_S; tv.tv_usec = 0;
  ::setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  static char win[768];
  size_t have = 0;
  bool got_any = false;
  const int64_t give_up = esp_timer_get_time() + (int64_t) (UPL_REPLY_TIMEOUT_S + 5) * 1000000;
  for (;;) {
    if (have > sizeof(win) - 128) {   // keep the tail
      memmove(win, win + have - 384, 384);
      have = 384;
    }
    int n = ::recv(sock, win + have, sizeof(win) - 1 - have, 0);
    if (n <= 0) {
      if (n < 0 && !got_any)
        ESP_LOGW(UPL_TAG, "no response within %d s: errno %d", UPL_REPLY_TIMEOUT_S, errno);
      break;
    }
    if (!got_any) {
      got_any = true;
      win[have + n] = '\0';
      int code = 0;
      if (sscanf(win, "HTTP/%*s %d", &code) == 1) _upl_status = code;
      _upl_addon = UPL_ADDON_UP;
    }
    have += n;
    if (esp_timer_get_time() > give_up) break;
  }
  win[have] = '\0';
  if (!got_any) { _upl_result = UPL_TIMEOUT; return; }
  _upl_delivered = _json_last_int(win, "delivered");
  _upl_queued    = _json_last_int(win, "queued");
  _upl_failed    = _json_last_int(win, "failed");
  _upl_result = UPL_HTTP;
  ESP_LOGI(UPL_TAG, "response %d  delivered=%d queued=%d failed=%d", _upl_status,
           _upl_delivered, _upl_queued, _upl_failed);
}

// Drains an abandoned recording (max 120 s) so its tail can't leak into the next.
static void _drain_recording() {
  const TickType_t give_up = xTaskGetTickCount() + pdMS_TO_TICKS(120000);
  while (!recorder_is_done() && xTaskGetTickCount() < give_up)
    recorder_drain(_upl_buf, sizeof(_upl_buf), 20);
  recorder_discard();
}

static bool _upl_should_abort() { return _upl_cancel; }
static bool _probe_should_abort() { return _upl_job; }   // a press wins

static void _do_upload() {
  _upl_target_t t;
  if (!_parse_url(_upl_url, t)) {
    ESP_LOGE(UPL_TAG, "bad URL '%s'", _upl_url);
    _upl_result = UPL_NET_ERROR;
    return;
  }
  int sock = _open(t, UPL_IO_TIMEOUT_S, _upl_should_abort);
  if (sock < 0) {
    if (_upl_cancel) { _upl_result = UPL_CANCELLED; return; }
    _upl_addon = UPL_ADDON_DOWN;
    _upl_result = UPL_NET_ERROR;
    return;
  }
  _upl_addon = UPL_ADDON_UP;

  // Connected: wait for the gesture to resolve (hold threshold, < 1 s).
  const TickType_t give_up = xTaskGetTickCount() + pdMS_TO_TICKS(30000);
  while (!_upl_commit && !_upl_cancel && xTaskGetTickCount() < give_up)
    vTaskDelay(pdMS_TO_TICKS(10));
  if (!_upl_commit) {
    ::close(sock);
    _upl_result = UPL_CANCELLED;
    ESP_LOGD(UPL_TAG, "cancelled before sending");
    return;
  }

  char sid[17]; _make_sid(sid);
  char hdr[640];
  int hlen = snprintf(hdr, sizeof(hdr),
    "POST %s HTTP/1.1\r\nHost: %s:%d\r\n"
    "Content-Type: audio/pcm\r\nTransfer-Encoding: chunked\r\n"
    "X-Sample-Rate: 16000\r\n%s"
    "X-Session-ID: %s\r\nX-Device-Name: %s\r\nConnection: close\r\n\r\n",
    t.path, t.host, t.port, _upl_reply ? "X-Intercom-Reply: 1\r\n" : "",
    sid, _upl_device);
  if (hlen < 0 || hlen >= (int) sizeof(hdr)) {
    ESP_LOGE(UPL_TAG, "header too large (need %d, max %u) — aborting",
             hlen, (unsigned) sizeof(hdr));
    ::close(sock);
    _upl_result = UPL_NET_ERROR;
    _drain_recording();
    return;
  }
  bool ok = _send_all(sock, hdr, hlen);
  if (ok) ESP_LOGI(UPL_TAG, "streaming  session=%s device=%s%s", sid, _upl_device,
                   _upl_reply ? "  (reply)" : "");

  size_t total = 0;
  while (ok && !recorder_is_done()) {
    size_t n = recorder_drain(_upl_buf, sizeof(_upl_buf), 20);
    if (n == 0) continue;
    char szl[12]; int sl = snprintf(szl, sizeof(szl), "%x\r\n", (unsigned) n);
    ok = _send_all(sock, szl, sl) && _send_all(sock, _upl_buf, n) &&
         _send_all(sock, "\r\n", 2);
    if (ok) total += n;
  }
  if (!ok || !_send_all(sock, "0\r\n\r\n", 5)) {
    ESP_LOGE(UPL_TAG, "send failed after %u bytes: errno %d — upload abandoned",
             (unsigned) total, errno);
    ::close(sock);
    _upl_addon = UPL_ADDON_DOWN;
    _upl_result = UPL_NET_ERROR;   // visible now, so the caller can stop recording
    _drain_recording();
    return;
  }
  ESP_LOGI(UPL_TAG, "sent %u bytes, awaiting response", (unsigned) total);
  _read_response(sock);
  ::close(sock);
}

static void _do_probe() {
  _upl_target_t t;
  if (!_parse_url(_upl_probe_url, t)) { _upl_addon = UPL_ADDON_DOWN; return; }
  int sock = _open(t, UPL_PROBE_TIMEOUT_S, _probe_should_abort);
  if (sock < 0) {
    if (!_upl_job) _upl_addon = UPL_ADDON_DOWN;   // aborted by a press: unknown
    return;
  }
  ::close(sock);   // no request: the add-on logs nothing
  _upl_addon = UPL_ADDON_UP;
}

static void _upl_task_fn(void*) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    while (_upl_job || _upl_probe_job) {
      if (_upl_job) {
        _upl_job = false;
        _do_upload();
        _uploading = false;
      } else {
        _upl_probe_job = false;
        _do_probe();
        _probing = false;
      }
    }
  }
}

// Once, from on_boot, before the heap fragments.
void uploader_init() {
  if (_upl_task) return;
  if (xTaskCreate(_upl_task_fn, "uploader", 4096, nullptr, 5, &_upl_task) != pdPASS) {
    ESP_LOGE(UPL_TAG, "could not start upload task");
    _upl_task = nullptr;
  }
}

// Starts connecting. False if a PTT upload is still running (busy).
bool uploader_begin(const char* url, const char* device) {
  if (!_upl_task) uploader_init();
  if (_uploading || !_upl_task) { ESP_LOGW(UPL_TAG, "busy, ignoring"); return false; }
  strncpy(_upl_url, url, sizeof(_upl_url) - 1);
  _upl_url[sizeof(_upl_url) - 1] = '\0';
  strncpy(_upl_device, device ? device : "", sizeof(_upl_device) - 1);
  _upl_device[sizeof(_upl_device) - 1] = '\0';
  _upl_commit = false;
  _upl_cancel = false;
  _upl_reply = false;
  _upl_status = 0;
  _upl_delivered = _upl_queued = _upl_failed = -1;
  _upl_result = UPL_PENDING;
  _uploading = true;
  _upl_job = true;
  xTaskNotifyGive(_upl_task);
  return true;
}

void uploader_commit(bool reply) {
  _upl_reply = reply;
  _upl_commit = true;
}

void uploader_cancel() { _upl_cancel = true; }

void uploader_start(const char* url, const char* device) {
  if (uploader_begin(url, device)) uploader_commit(false);
}

// Connect-only check of the add-on. Skipped while anything else runs.
bool uploader_probe(const char* url) {
  if (!_upl_task) uploader_init();
  if (!_upl_task || _uploading || _probing) return false;
  strncpy(_upl_probe_url, url, sizeof(_upl_probe_url) - 1);
  _upl_probe_url[sizeof(_upl_probe_url) - 1] = '\0';
  _probing = true;
  _upl_probe_job = true;
  xTaskNotifyGive(_upl_task);
  return true;
}

bool uploader_is_uploading()   { return _uploading; }
bool uploader_is_probing()     { return _probing; }
int  uploader_result()         { return _upl_result; }
int  uploader_http_status()    { return _upl_status; }
int  uploader_delivered()      { return _upl_delivered; }
int  uploader_queued()         { return _upl_queued; }
int  uploader_failed_targets() { return _upl_failed; }
int  uploader_addon_state()    { return _upl_addon; }

// Network failure seen, possibly while the task still drains the recording.
bool uploader_failed() { return _upl_result == UPL_NET_ERROR; }

// The add-on heard it: 2xx and somebody got it (or the body had no counts).
bool uploader_delivered_ok() {
  if (_upl_result != UPL_HTTP || _upl_status < 200 || _upl_status >= 300) return false;
  if (_upl_delivered < 0 && _upl_queued < 0) return true;
  return (_upl_delivered > 0) || (_upl_queued > 0);
}
