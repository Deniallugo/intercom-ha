"""The default channel: whoever talks is heard on every other intercom device.

Intercom devices are ESPHome devices with a media_player, taken from HA's
device and entity registries (see HAClient.get_registry). A source
(X-Device-Name = ESPHome node name) is matched to its device by:

1. selves[source] in players.json (manual), unless it names a speaker that
   is not an intercom device while the registry does place the source: an
   old manual entry for a renamed or removed entity must not win,
2. the config entry's data.device_name == node name (exact),
3. slug(node name) == slug(device name / name_by_user) — ESPHome registers
   the device under friendly_name, and "Atom Echo" ~ "atom-echo".

Everything here is pure: no I/O, so it is tested without HA.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Member:
    device_id: str
    friendly_name: str
    media_player: Optional[str]
    node_name: Optional[str] = None      # from the config entry, if known
    satellite: bool = False              # has an assist_satellite (=> mic)
    keys: set = field(default_factory=set)


@dataclass
class Plan:
    targets: list
    mode: str                 # channel | override | reply | muted | fallback
    self_player: Optional[str]


def slug(text) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")


def build_members(registry: Optional[dict]) -> list[Member]:
    """ESPHome devices that own an enabled media_player entity."""
    if not registry:
        return []
    players: dict[str, list[str]] = {}
    satellites: set[str] = set()
    for e in registry.get("entities", []):
        if not isinstance(e, dict) or e.get("platform") != "esphome":
            continue
        device_id, entity_id = e.get("device_id"), e.get("entity_id") or ""
        if not device_id or e.get("disabled_by"):
            continue
        if entity_id.startswith("media_player."):
            players.setdefault(device_id, []).append(entity_id)
        elif entity_id.startswith("assist_satellite."):
            satellites.add(device_id)

    names = registry.get("esphome_names", {}) or {}
    members = []
    for d in registry.get("devices", []):
        if not isinstance(d, dict) or d.get("id") not in players or d.get("disabled_by"):
            continue
        node = next((names[c] for c in d.get("config_entries") or [] if c in names), None)
        friendly = d.get("name_by_user") or d.get("name") or node or d["id"]
        keys = {slug(k) for k in (node, d.get("name"), d.get("name_by_user")) if k}
        members.append(Member(
            device_id=d["id"],
            friendly_name=friendly,
            media_player=sorted(players[d["id"]])[0],
            node_name=node,
            satellite=d["id"] in satellites,
            keys=keys - {""},
        ))
    members.sort(key=lambda m: (m.friendly_name.lower(), m.device_id))
    return members


def match_source(source: str, members: list[Member]) -> Optional[Member]:
    """The registry device a X-Device-Name belongs to, or None."""
    if not source:
        return None
    for m in members:
        if m.node_name and m.node_name.lower() == source.lower():
            return m
    key = slug(source)
    hits = [m for m in members if key and key in m.keys]
    return hits[0] if len(hits) == 1 else None


def self_member(source: str, state: dict, members: list[Member]) -> Optional[Member]:
    """The registry device for `source`, honouring a manual selves entry when
    it names an intercom speaker."""
    manual = state["selves"].get(source)
    if manual:
        hit = next((m for m in members if m.media_player == manual), None)
        if hit:
            return hit
    return match_source(source, members)


def self_player(source: str, state: dict, members: list[Member]) -> Optional[str]:
    """`source`'s own speaker. A manual selves entry wins unless it names a
    non-intercom speaker and the registry has a match (stale entry)."""
    manual = state["selves"].get(source)
    m = self_member(source, state, members)
    if manual and (m is None or m.media_player == manual):
        return manual
    return m.media_player if m else None


def channel_players(state: dict, members: list[Member]) -> list[str]:
    excluded = set(state["excluded"])
    out = []
    for m in members:
        if m.media_player and m.media_player not in excluded and m.media_player not in out:
            out.append(m.media_player)
    return out


def plan(source: str, state: dict, members: list[Member],
         reply_to: Optional[str] = None) -> Plan:
    """Who hears `source`. The talker's own speaker never does."""
    me = self_player(source, state, members)
    if source in state["muted"]:
        return Plan([], "muted", me)
    if reply_to:
        targets, mode = [reply_to], "reply"
    elif state["routes"].get(source):
        targets, mode = state["routes"][source], "override"
    else:
        targets, mode = channel_players(state, members), "channel"
        if not targets:
            targets, mode = state["default"], "fallback"
    seen, out = set(), []
    for t in targets:
        if t != me and t not in seen:
            seen.add(t)
            out.append(t)
    return Plan(out, mode, me)


def known_sources(state: dict, activity: dict) -> list[str]:
    names = set(state["routes"]) | set(state["aliases"]) | set(state["selves"])
    names |= set(state["muted"]) | set(activity)
    return sorted(n for n in names if isinstance(n, str) and n)


def describe(state: dict, members: list[Member], activity: dict,
             entity_states: Optional[dict]) -> list[dict]:
    """Rows for GET /api/devices: registry members plus every source we know
    of that the registry could not place."""
    sources = known_sources(state, activity)
    claimed: dict[str, str] = {}   # source -> device_id
    for s in sources:
        hit = self_member(s, state, members)
        if hit and hit.device_id not in claimed.values():
            claimed[s] = hit.device_id
    by_device = {d: s for s, d in claimed.items()}
    channel = set(channel_players(state, members))

    def row(name, member):
        mp = (self_player(name, state, members) if name else None) or (member.media_player if member else None)
        act = activity.get(name, {}) if name else {}
        st = (entity_states or {}).get(mp) if mp else None
        if act.get("last_seen") or (name and name in state["routes"]):
            has_mic = True       # it has uploaded audio (routes enrolls senders)
        elif member and member.satellite:
            has_mic = True
        else:
            has_mic = None       # unknown: speaker-only or never pressed
        override = state["routes"].get(name) if name else None
        return {
            "name": name,
            "device_id": member.device_id if member else None,
            "friendly_name": member.friendly_name if member else None,
            "alias": state["aliases"].get(name) if name else None,
            "media_player": mp,
            "has_mic": has_mic,
            "state": st.get("state") if st else None,
            "online": (st.get("state") not in ("unavailable", "unknown")) if st else None,
            "listening": bool(mp and mp in channel),
            "muted": bool(name and name in state["muted"]),
            "override": list(override) if override else None,
            "last_seen": act.get("last_seen"),
            "last_broadcast": act.get("last_broadcast"),
        }

    rows = []
    for m in members:
        name = by_device.get(m.device_id) or m.node_name
        rows.append(row(name, m))
    for s in sources:
        if s not in claimed:
            rows.append(row(s, None))
    return rows
