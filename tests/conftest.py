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


class FakeStreams:
    """Stand-in for denoise.Stream: records each one made (rate, full mode,
    bytes fed) and returns `out(pcm, full)` from finish()."""

    def __init__(self, out=lambda pcm, full: pcm):
        self.made = []
        self.out = out

    def __call__(self, *, sample_rate, full=True):
        streams = self

        class _Stream:
            def __init__(self):
                self.sample_rate, self.full, self.fed = sample_rate, full, b""

            def feed(self, pcm):
                self.fed += pcm

            def finish(self):
                return streams.out(self.fed, self.full)

        s = _Stream()
        self.made.append(s)
        return s


@pytest.fixture
def fake_streams(monkeypatch):
    """Replace denoise.Stream with FakeStreams; set `.out` to change the output."""
    fakes = FakeStreams()
    monkeypatch.setattr(srv.denoise, "Stream", fakes)
    return fakes
