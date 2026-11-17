"""What each part selector builds, and where everything goes in the assembled unit.

Every printed part is built in its PRINT frame (so a component exports print-ready) and placed
at the end; every electronic part is drawn straight in world coordinates inside one group,
"electronics", which is never moved. The browser:

    electronics      ZK-502MT, knobs, DC plug, AUX plug (amp), amp wiring, ESP32-S3 devkit,
                     PCM5102A, AUX plug (DAC), MP1584, INMP441, tactile switch, voice wiring
    tray, panel, switch bridge, mic clamp
"""

import json

from . import appearance, button, case, elec, electronics, xf
from . import params as P
from .build import Group, Part

ELEC_GROUP = 'electronics'


def placements():
    """[(name, builder, print frame -> world)] for every printed part of the unit"""
    W = elec.box_world()
    mx, mz = P.mic_pos
    return [(case.TRAY, case.tray, xf.mul(W, xf.inverse(case.tray_print()))),
            (case.PANEL, case.panel, W),
            (case.BRIDGE, case.bridge, xf.mul(W, P.bridge_xf())),
            # bar under the post tips, pad pressing UP onto the mic board
            (button.CLAMP, button.clamp, xf.chain(W, xf.T(mx, P.box_h() - P.wall - P.mic_post_h - P.mic_clamp_t, mz),
                                                  xf.Rx(-90)))]


SINGLE = {
    'tray': (case.TRAY, case.tray), 'panel': (case.PANEL, case.panel),
    'bridge': (case.BRIDGE, case.bridge), 'clamp': (button.CLAMP, button.clamp),
    'coupon-button': ('coupon button', lambda p: case.coupon(p, 'button')),
    'coupon-top': ('coupon top', lambda p: case.coupon(p, 'top')),
}
# `small`: the small printed parts on one bed, each in its print orientation
SMALL = ('bridge', 'clamp')
BED_W = 220         # mm, rows wrap at this width
BED_GAP = 6         # mm between parts
PARTS = ('all', 'electronics', 'small') + tuple(SINGLE) + ('sync',)
SHELLS = (case.TRAY, case.PANEL)


def _timeline_mark(design):
    try:
        return design.timeline.count
    except Exception:
        return None


def _timeline_group(design, name, start):
    try:
        tl = design.timeline
        if start is not None and tl.count - 1 > start:
            tl.timelineGroups.add(start, tl.count - 1).name = name
    except Exception:
        pass        # cosmetic only


def _make(design, name, builder, parent=None, where=None):
    start = _timeline_mark(design)
    p = Part(design, name, parent)
    builder(p)
    if where is not None:
        p.place(where)
    _timeline_group(design, name, start)
    return p


def build(design, which, ghost=None):
    """-> (printed, everything). `printed` are the components to export; `everything` is every
    Part and Group, whose recorded positions place_all() applies at the very end."""
    if which in SINGLE:
        name, builder = SINGLE[which]
        p = _make(design, name, builder)
        return [p], [p]
    if which == 'small':
        # Fusion grounds the FIRST component of a design, and a grounded one would not take its
        # bed position. A group that is never moved goes first.
        Group(design, 'print bed')
        parts = [_make(design, *SINGLE[k]) for k in SMALL]
        lay_out(parts)
        return parts, parts
    printed, items = [], []
    # The group holds the ELECTRONICS only, each part at its identity, and is never moved — it is
    # also the design's first component, so Fusion grounding it costs nothing.
    group = Group(design, ELEC_GROUP)
    items.append(group)
    if which == 'all':
        for name, builder, x in placements():
            printed.append(_make(design, name, builder, None, x))
    start = _timeline_mark(design)
    elec_parts = electronics.build(design, {'amp': group, 'unit': group})
    _timeline_group(design, 'electronics', start)
    items += printed + elec_parts
    if ghost is not None:
        for p in printed:
            if p.comp.name in SHELLS:
                appearance.ghost(p.occ, ghost)
    remember_placement(design)
    return printed, items


def footprint(p):
    """(min, max) corners in mm of a built part, in its own (print) frame"""
    bb = p.comp.bRepBodies.item(0).boundingBox
    lo, hi = bb.minPoint, bb.maxPoint
    return (lo.x*10, lo.y*10, lo.z*10), (hi.x*10, hi.y*10, hi.z*10)


def pack(sizes, bed_w=BED_W, gap=BED_GAP):
    """shelf packing: [(w, d)] -> [(x, y)] lower-left corners. Tallest-first rows, wrapping at
    bed_w; a part wider than the bed gets a row of its own."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])
    out = [None]*len(sizes)
    x = y = row_d = 0.0
    for i in order:
        w, d = sizes[i]
        if x > 0 and x + w > bed_w:
            x, y, row_d = 0.0, y + row_d + gap, 0.0
        out[i] = (x, y)
        x += w + gap
        row_d = max(row_d, d)
    return out


def lay_out(parts):
    """every part's print frame put on one bed: bottom on z = 0, no two footprints touching"""
    boxes = [footprint(p) for p in parts]
    spots = pack([(hi[0] - lo[0], hi[1] - lo[1]) for lo, hi in boxes])
    for p, (lo, _), (x, y) in zip(parts, boxes, spots):
        p.place(xf.T(x - lo[0], y - lo[1], -lo[2]))


ATTR_GROUP, ATTR_NAME = 'voice-wall-case', 'placement'


def placement_values():
    return {n: (list(v) if isinstance(v, tuple) else v)
            for n, v in ((n, getattr(P, n)) for n in P.PLACEMENT)}


def remember_placement(design):
    """Stamp the placement this document was BUILT with into the design, so `sync` adds a drag
    to the number the geometry actually came from — not to whatever placement.py says now. That
    is what makes a second sync without a rebuild safe instead of a double count."""
    try:
        design.attributes.add(ATTR_GROUP, ATTR_NAME, json.dumps(placement_values()))
    except Exception:
        pass
