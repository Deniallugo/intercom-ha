import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import intercom as srv  # noqa: E402

MEDIA_BASE = "http://192.0.2.10:9999"


@pytest.fixture(autouse=True)
def _reset_airtime():
    """Speakers start free in every test (srv.airtime is module-level)."""
    srv.airtime.reset()
    yield
    srv.airtime.reset()


@pytest.fixture(autouse=True)
def media_server(monkeypatch, tmp_path):
    """Served media goes to a temp dir at MEDIA_BASE; no Supervisor lookup."""
    monkeypatch.setattr(srv.media, "MEDIA_DIR", str(tmp_path / "media"))
    resolve = AsyncMock(return_value=(MEDIA_BASE, "http://ha.test:8123"))
    monkeypatch.setattr(srv.lan_address, "resolve", resolve)
    srv.media_store.clear()
    yield resolve
    srv.media_store.clear()
