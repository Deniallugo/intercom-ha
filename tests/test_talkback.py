import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
from talkback import TalkbackWindows  # noqa: E402


def make(now=0.0):
    """Build a TalkbackWindows with a controllable clock."""
    tw = TalkbackWindows(now_func=lambda: tw.t)
    tw.t = now
    return tw


def test_no_window_active_initially():
    tw = make()
    assert tw.reply_target("A") is None


def test_record_then_reply_within_window():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.a"


def test_no_window_when_target_has_no_selves_entry():
    tw = make(now=0)
    selves = {"A": "media_player.a"}  # no B
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") is None


def test_window_not_consumed_on_use():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.a"
    assert tw.reply_target("B") == "media_player.a"


def test_window_expires_after_30s():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    tw.t = 31
    assert tw.reply_target("B") is None


def test_new_broadcast_resets_window_to_latest_sender():
    tw = make(now=0)
    selves = {
        "A": "media_player.a",
        "B": "media_player.b",
        "C": "media_player.c",
    }
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    tw.t = 10
    tw.record_broadcast(source="C", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.c"


def test_no_window_when_sender_has_no_selves_entry():
    tw = make(now=0)
    selves_no_a = {"B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves_no_a)
    assert tw.reply_target("B") is None


def test_pingpong_A_to_B_then_B_to_A():
    tw = make(now=0)
    selves = {"A": "media_player.a", "B": "media_player.b"}
    tw.record_broadcast(source="A", targets=["media_player.b"], selves=selves)
    assert tw.reply_target("B") == "media_player.a"
    tw.t = 5
    tw.record_broadcast(source="B", targets=["media_player.a"], selves=selves)
    assert tw.reply_target("A") == "media_player.b"
