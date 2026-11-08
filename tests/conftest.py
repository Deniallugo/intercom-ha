import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))


@pytest.fixture(autouse=True)
def _reset_airtime():
    """Speakers start free in every test (srv.airtime is module-level)."""
    import intercom as srv
    srv.airtime.reset()
    yield
    srv.airtime.reset()
