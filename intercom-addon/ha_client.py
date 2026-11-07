import asyncio
import json
import logging
import os
import time
from typing import Optional

from aiohttp import ClientSession

log = logging.getLogger(__name__)

SUPERVISOR_CORE = "http://supervisor/core"
HA_API = f"{SUPERVISOR_CORE}/api"
# REST has no device/entity registry; only the WebSocket API does.
SUPERVISOR_WS = "ws://supervisor/core/websocket"
WS_TIMEOUT = 10.0

# The ESPHome node name (what devices send as X-Device-Name) is not in the
# device registry: HA keeps it only in the config entry's data
# (data.device_name), which no API returns. The add-on maps /config.
CONFIG_ENTRIES_FILE = "/config/.storage/core.config_entries"

# Devices are added rarely; an unknown X-Device-Name forces an early refresh.
REGISTRY_TTL = 300.0
# After a failed refresh with a cached copy, retry no sooner than this.
REGISTRY_RETRY = 30.0


class HAClient:
    """Thin wrapper over the HA Supervisor REST and WebSocket APIs.

    Holds a single aiohttp.ClientSession across the addon's lifetime so we
    don't open a new TCP connection per request.
    """

    def __init__(self, session: Optional[ClientSession] = None):
        self._session = session
        self._registry: Optional[dict] = None
        self._registry_at: Optional[float] = None  # monotonic
        self._registry_lock: Optional[asyncio.Lock] = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession()
        return self._session

    def _auth_headers(self) -> dict:
        token = os.environ["SUPERVISOR_TOKEN"]
        return {"Authorization": f"Bearer {token}"}

    async def get_states(self) -> list:
        resp = await self.session.get(
            f"{HA_API}/states", headers=self._auth_headers()
        )
        if resp.status != 200:
            raise RuntimeError(f"supervisor /states returned {resp.status}")
        return await resp.json()

    async def get_state(self, entity_id: str) -> dict:
        resp = await self.session.get(
            f"{HA_API}/states/{entity_id}", headers=self._auth_headers()
        )
        if resp.status != 200:
            raise RuntimeError(
                f"supervisor /states/{entity_id} returned {resp.status}"
            )
        return await resp.json()

    async def play_media(self, entity_id: str, media_url: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/play_media",
            headers=self._auth_headers(),
            json={
                "entity_id": entity_id,
                "media_content_id": media_url,
                "media_content_type": "music",
            },
        )
        return resp.status

    async def pause(self, entity_id: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/media_pause",
            headers=self._auth_headers(),
            json={"entity_id": entity_id},
        )
        return resp.status

    async def play(self, entity_id: str) -> int:
        resp = await self.session.post(
            f"{HA_API}/services/media_player/media_play",
            headers=self._auth_headers(),
            json={"entity_id": entity_id},
        )
        return resp.status

    async def tts_get_audio(self, engine_id: str, message: str) -> bytes:
        """Generate TTS via HA and return the raw audio bytes.

        POSTs /api/tts_get_url to make HA render the speech, then GETs the
        returned proxy path (kept on the internal supervisor proxy).
        """
        resp = await self.session.post(
            f"{HA_API}/tts_get_url",
            headers=self._auth_headers(),
            json={"engine_id": engine_id, "message": message},
        )
        if resp.status != 200:
            raise RuntimeError(f"tts_get_url returned {resp.status}")
        data = await resp.json()
        path = data.get("path")
        if not path:
            raise RuntimeError("tts_get_url response missing 'path'")
        audio_resp = await self.session.get(
            f"{SUPERVISOR_CORE}{path}", headers=self._auth_headers()
        )
        if audio_resp.status != 200:
            raise RuntimeError(f"tts audio fetch returned {audio_resp.status}")
        return await audio_resp.read()

    async def ws_commands(self, *types: str) -> list:
        """Run argument-less WebSocket commands on one connection and return
        their results in order. Raises RuntimeError on auth/command failure."""
        token = os.environ["SUPERVISOR_TOKEN"]
        async with self.session.ws_connect(SUPERVISOR_WS, heartbeat=30) as ws:
            msg = await ws.receive_json(timeout=WS_TIMEOUT)
            if msg.get("type") != "auth_required":
                raise RuntimeError(
                    f"websocket: unexpected greeting {msg.get('type')!r}")
            await ws.send_json({"type": "auth", "access_token": token})
            msg = await ws.receive_json(timeout=WS_TIMEOUT)
            if msg.get("type") != "auth_ok":
                raise RuntimeError(
                    f"websocket auth failed: {msg.get('message') or msg.get('type')}")
            results = []
            for msg_id, cmd in enumerate(types, start=1):
                await ws.send_json({"id": msg_id, "type": cmd})
                while True:
                    msg = await ws.receive_json(timeout=WS_TIMEOUT)
                    if msg.get("id") == msg_id and msg.get("type") == "result":
                        break
                if not msg.get("success"):
                    err = (msg.get("error") or {}).get("message", "unknown error")
                    raise RuntimeError(f"websocket {cmd} failed: {err}")
                results.append(msg.get("result"))
            return results

    async def get_registry(self, *, force: bool = False) -> dict:
        """Device and entity registries plus ESPHome node names, cached for
        REGISTRY_TTL:

            {"devices": [...], "entities": [...],
             "esphome_names": {config_entry_id: node_name}, "fetched_at": unix_ts}

        A failed refresh keeps serving the previous copy; raises only when
        there is none yet."""
        if self._registry_lock is None:
            self._registry_lock = asyncio.Lock()
        async with self._registry_lock:
            now = time.monotonic()
            if (not force and self._registry is not None
                    and self._registry_at is not None
                    and now - self._registry_at < REGISTRY_TTL):
                return self._registry
            try:
                devices, entities = await self.ws_commands(
                    "config/device_registry/list", "config/entity_registry/list")
            except Exception as e:
                if self._registry is None:
                    raise
                log.warning("registry refresh failed (%s); using cached copy", e)
                self._registry_at = now - REGISTRY_TTL + REGISTRY_RETRY
                return self._registry
            self._registry = {
                "devices": devices if isinstance(devices, list) else [],
                "entities": entities if isinstance(entities, list) else [],
                "esphome_names": read_esphome_node_names(),
                "fetched_at": time.time(),
            }
            self._registry_at = now
            return self._registry

    @property
    def registry_fetched_at(self) -> Optional[float]:
        """Unix time of the cached registry copy, or None."""
        return (self._registry or {}).get("fetched_at")

    def invalidate_registry(self) -> None:
        """Make the next get_registry() refetch."""
        self._registry_at = None

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def read_esphome_node_names(path: Optional[str] = None) -> dict:
    """{config_entry_id: ESPHome node name} from HA's config-entry store.

    Best effort: {} if unreadable or if this HA predates data.device_name;
    matching then falls back to the device's (friendly) name."""
    try:
        with open(path or CONFIG_ENTRIES_FILE) as f:
            entries = json.load(f)["data"]["entries"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.info("ESPHome node names unavailable (%s); matching by device name", e)
        return {}
    out = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or entry.get("domain") != "esphome":
            continue
        name = (entry.get("data") or {}).get("device_name")
        if isinstance(name, str) and name and entry.get("entry_id"):
            out[entry["entry_id"]] = name
    return out
