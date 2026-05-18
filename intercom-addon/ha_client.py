import os
from typing import Optional

from aiohttp import ClientSession

HA_API = "http://supervisor/core/api"


class HAClient:
    """Thin wrapper over the HA Supervisor REST API.

    Holds a single aiohttp.ClientSession across the addon's lifetime so we
    don't open a new TCP connection per request.
    """

    def __init__(self, session: Optional[ClientSession] = None):
        self._session = session

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

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
