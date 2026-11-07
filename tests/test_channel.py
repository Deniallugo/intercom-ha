import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intercom-addon"))
import channel  # noqa: E402
import players  # noqa: E402


def dev(dev_id, name, entry=None, name_by_user=None, disabled=None):
    return {"id": dev_id, "name": name, "name_by_user": name_by_user,
            "config_entries": [entry or f"e-{dev_id}"], "disabled_by": disabled}


def ent(entity_id, dev_id, platform="esphome", disabled=None):
    return {"entity_id": entity_id, "device_id": dev_id,
            "platform": platform, "disabled_by": disabled}


def reg(devices, entities, names=None):
    return {"devices": devices, "entities": entities, "esphome_names": names or {}}


def state(**kw):
    return players.normalize(kw)


def test_members_are_esphome_devices_with_a_media_player():
    members = channel.build_members(reg(
        [dev("d1", "Atom Echo"), dev("d2", "Sonos"), dev("d3", "Plug")],
        [ent("media_player.atom_echo_player", "d1"),
         ent("media_player.sonos", "d2", platform="sonos"),
         ent("switch.plug", "d3")],
    ))
    assert [m.media_player for m in members] == ["media_player.atom_echo_player"]


def test_disabled_entities_and_devices_are_skipped():
    members = channel.build_members(reg(
        [dev("d1", "A"), dev("d2", "B", disabled="user")],
        [ent("media_player.a", "d1", disabled="user"), ent("media_player.b", "d2")],
    ))
    assert members == []


def test_satellite_marks_mic():
    members = channel.build_members(reg(
        [dev("d1", "Voice S3")],
        [ent("media_player.voice_s3_player", "d1"),
         ent("assist_satellite.voice_s3", "d1")],
    ))
    assert members[0].satellite is True


def test_match_by_slug_of_friendly_name_and_user_name():
    members = channel.build_members(reg(
        [dev("d1", "Atom Echo"), dev("d2", "Voice S3", name_by_user="Kitchen")],
        [ent("media_player.a", "d1"), ent("media_player.b", "d2")],
    ))
    assert channel.match_source("atom-echo", members).device_id == "d1"
    assert channel.match_source("voice-s3", members).device_id == "d2"
    assert channel.match_source("kitchen", members).device_id == "d2"
    assert channel.match_source("garage", members) is None


def test_node_name_from_config_entry_wins_and_ambiguity_is_no_match():
    members = channel.build_members(reg(
        [dev("d1", "Intercom S3", entry="e1"), dev("d2", "Intercom S3", entry="e2")],
        [ent("media_player.a", "d1"), ent("media_player.b", "d2")],
        names={"e1": "esphome-web-0f4600"},
    ))
    assert channel.match_source("esphome-web-0f4600", members).device_id == "d1"
    # Two devices slug to "intercom_s3": refuse to guess.
    assert channel.match_source("intercom-s3", members) is None


def test_plan_channel_minus_self_and_dedup():
    members = channel.build_members(reg(
        [dev("d1", "A"), dev("d2", "B"), dev("d3", "C")],
        [ent("media_player.a", "d1"), ent("media_player.b", "d2"),
         ent("media_player.c", "d3")],
    ))
    p = channel.plan("a", state(), members)
    assert (p.mode, p.targets, p.self_player) == (
        "channel", ["media_player.b", "media_player.c"], "media_player.a")
    p = channel.plan("a", state(routes={"a": ["media_player.b", "media_player.b"]}), members)
    assert (p.mode, p.targets) == ("override", ["media_player.b"])


def test_plan_fallback_and_muted():
    s = state(default=["media_player.x", "media_player.y"],
              selves={"a": "media_player.x"}, muted=["m"])
    assert channel.plan("a", s, []).targets == ["media_player.y"]
    assert channel.plan("a", s, []).mode == "fallback"
    p = channel.plan("m", s, [])
    assert (p.mode, p.targets) == ("muted", [])


def test_plan_reply_excludes_nobody_but_self():
    p = channel.plan("a", state(), [], reply_to="media_player.b")
    assert (p.mode, p.targets) == ("reply", ["media_player.b"])
