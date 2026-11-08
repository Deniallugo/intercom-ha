"""Short-lived broadcast media, served by the add-on itself on its LAN port.

Players fetch GET /media/<name> without credentials: an ESPHome speaker's
play_media URL is fetched by HA's ffmpeg proxy (esphome/media_player.py
swaps it for /api/esphome/ffmpeg_proxy/... when the device reports its
supported formats), Cast and other players fetch it themselves. So the name is
the secret: 192 random bits, one per broadcast, gone after its TTL. Nothing
lands in /config/www, which HA serves to anyone (and to the internet via
Nabu Casa) at /local/.

The URL players get is http://<host IP>:<published port>/media/<name>: the
host's primary IPv4 from the Supervisor (no mDNS needed on the player), else
the host of HA's internal_url. The add-on stays on the hassio bridge network;
the published port is reachable from the LAN and from HA Core (host network).
If the port is not published (Network section emptied) there is no LAN URL,
and the caller falls back to /config/www.
"""
import logging
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

MEDIA_DIR = "/tmp/intercom-media"
ROUTE = "/media/{name}"
# The container port; the host port may be remapped in the Network section.
LAN_PORT = 9999

CONTENT_TYPES = {"wav": "audio/wav", "mp3": "audio/mpeg"}
_NAME = re.compile(r"^[A-Za-z0-9_-]{32}\.(wav|mp3)$")

# How long the address lookup is trusted (DHCP may move the host).
ADDRESS_TTL = 300.0
ADDRESS_RETRY = 30.0
FALLBACK_HOST = "homeassistant.local"
FALLBACK_HA_URL = "http://homeassistant.local:8123"


class MediaStore:
    """Unguessable, expiring names for files under MEDIA_DIR."""

    def __init__(self):
        self._expires: dict[str, float] = {}
        self._labels: dict[str, str] = {}

    @staticmethod
    def directory() -> Path:
        return Path(MEDIA_DIR)

    def put(self, body: bytes, ext: str, ttl: float, *, label: str = "",
            now: Optional[float] = None) -> Path:
        """Store `body` under a fresh random name; return its path."""
        if ext not in CONTENT_TYPES:
            raise ValueError(f"unsupported media type {ext!r}")
        directory = self.directory()
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{secrets.token_urlsafe(24)}.{ext}"
        path = directory / name
        path.write_bytes(body)
        self._expires[name] = (time.monotonic() if now is None else now) + ttl
        self._labels[name] = label
        self._sweep(now)
        return path

    def lookup(self, name: str, *, now: Optional[float] = None) -> Optional[Path]:
        """The file for a live name, or None (unknown, malformed or expired)."""
        if not _NAME.match(name or ""):
            return None
        expires = self._expires.get(name)
        if expires is None:
            return None
        if (time.monotonic() if now is None else now) >= expires:
            self.remove(name)
            return None
        path = self.directory() / name
        return path if path.is_file() else None

    def remove(self, name: str) -> None:
        self._expires.pop(name, None)
        self._labels.pop(name, None)
        try:
            (self.directory() / name).unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            log.warning("could not remove media %s: %s", name[:6], e)

    def items(self) -> list[tuple[str, str]]:
        """(name, label) of live media — for tests and logs."""
        return list(self._labels.items())

    def clear(self) -> None:
        """Drop everything (startup: files from a previous run are orphans)."""
        self._expires.clear()
        self._labels.clear()
        shutil.rmtree(self.directory(), ignore_errors=True)

    def _sweep(self, now: Optional[float]) -> None:
        t = time.monotonic() if now is None else now
        for name, expires in list(self._expires.items()):
            if t >= expires:
                self.remove(name)


def content_type(name: str) -> str:
    return CONTENT_TYPES.get(name.rsplit(".", 1)[-1], "application/octet-stream")


def published_port(addon_info: dict) -> Optional[int]:
    """Host port mapped to LAN_PORT, or None if it is not published."""
    network = addon_info.get("network")
    if not isinstance(network, dict):
        return None
    value = network.get(f"{LAN_PORT}/tcp")
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def primary_ipv4(network_info: dict) -> Optional[str]:
    """First IPv4 of the primary connected interface (Supervisor /network/info)."""
    interfaces = network_info.get("interfaces")
    if not isinstance(interfaces, list):
        return None
    ranked = sorted(
        (i for i in interfaces if isinstance(i, dict)),
        key=lambda i: (not i.get("primary"), not i.get("connected", True)),
    )
    for iface in ranked:
        if iface.get("enabled") is False or iface.get("connected") is False:
            continue
        ipv4 = iface.get("ipv4") or {}
        for addr in ipv4.get("address") or []:
            if isinstance(addr, str) and addr:
                return addr.split("/", 1)[0]
    return None


def host_of(url) -> Optional[str]:
    if not isinstance(url, str) or not url:
        return None
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


def _url_host(host: str) -> str:
    return f"[{host}]" if ":" in host else host


class LanAddress:
    """Where players reach the add-on, and where HA Core is (for /local/)."""

    def __init__(self):
        self._base: Optional[str] = None
        self._published = True
        self._ha_url: str = FALLBACK_HA_URL
        self._valid_until = float("-inf")

    async def resolve(self, ha) -> tuple[Optional[str], str]:
        """(add-on base URL or None if the LAN port is unpublished, HA URL)."""
        now = time.monotonic()
        if now < self._valid_until:
            return (self._base if self._published else None), self._ha_url

        complete = True
        try:
            port = published_port(await ha.supervisor_get("/addons/self/info"))
            published = port is not None
        except Exception as e:
            log.warning("add-on info unavailable (%s); assuming port %d", e, LAN_PORT)
            port, published, complete = LAN_PORT, True, False

        internal_url = None
        try:
            internal_url = (await ha.get_core_config()).get("internal_url")
        except Exception as e:
            log.info("HA config unavailable (%s)", e)
            complete = False

        host = None
        try:
            host = primary_ipv4(await ha.supervisor_get("/network/info"))
        except Exception as e:
            log.info("network info unavailable (%s)", e)
            complete = False
        host = host or host_of(internal_url) or FALLBACK_HOST

        self._published = published
        self._base = f"http://{_url_host(host)}:{port}" if published else None
        self._ha_url = (internal_url.rstrip("/")
                        if isinstance(internal_url, str) and internal_url
                        else FALLBACK_HA_URL)
        self._valid_until = now + (ADDRESS_TTL if complete else ADDRESS_RETRY)
        log.info("media served at %s", self._base or f"{self._ha_url}/local/ "
                 "(LAN port not published)")
        return (self._base if self._published else None), self._ha_url

    def invalidate(self) -> None:
        self._valid_until = float("-inf")
