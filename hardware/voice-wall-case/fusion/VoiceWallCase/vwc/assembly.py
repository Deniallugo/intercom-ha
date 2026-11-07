"""What each part selector builds, and where everything goes in the assembled unit.

Every printed part is built in its PRINT frame (so a component exports print-ready) and every
electronic part in its box's LOCAL frame; the transforms below put each one in place. The tree
in Fusion's browser is:

    amp electronics     (sub-assembly, placed where the amp box is)
        ZK-502MT, knobs, MP1584, power switch, DC plug, AUX plug (amp), amp wiring
    voice electronics   (sub-assembly, placed where the voice box is)
        ESP32-S3 devkit, PCM5102A, AUX plug (DAC), INMP441, tactile switch, voice wiring
    amp shell, amp lid, amp sled, voice shell, voice lid, voice tray, sleeve,
    plunger, dome, button holder, mic clamp, wall plate, lock bracket

Inside each electronics group every part sits at the IDENTITY, in box-local coordinates — so a
part you drag shows its move directly as box-local x / y / z, which is what `sync` reads.
"""

import json

from . import appearance, button, case, elec, electronics, plate, xf
from . import params as P
from .build import Group, Part


AMP_GROUP, VOICE_GROUP = 'amp electronics', 'voice electronics'


def place_box(z0):
    """box-local -> world: OpenSCAD's translate([0, front_y, z0]) rotate([90, 0, 0])"""
    return xf.mul(xf.T(0, P.front_y(), z0), xf.Rx(90))


def box_xf(where):
    return elec.box_xf(where)


# plate frame (x, y up, z out of the wall) -> world (-x, z, y). A rotation, not the OpenSCAD's
# mirror (Fusion takes rigid transforms only); identical because the plate is x-symmetric.
PLATE_XF = xf.M(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
FLAT_INV = xf.inverse(case.FLAT)


def box_parts():
    """[(name, builder, transform within the box)] for both boxes"""
    bx, by = P.btn_pos
    mx, my = P.mic_pos
    amp = [(case.AMP_SHELL, case.amp_shell, xf.IDENTITY),
           (case.AMP_LID, case.amp_lid, xf.T(0, 0, P.box_d())),
           (case.AMP_SLED, case.amp_sled, FLAT_INV)]
    voice = [(case.VOICE_SHELL, case.voice_shell, xf.IDENTITY),
             (case.VOICE_LID, case.voice_lid, xf.T(0, 0, P.box_d())),
             (case.VOICE_TRAY, case.voice_tray, FLAT_INV),
             (case.SLEEVE, case.sleeve, xf.mul(xf.T(P.sleeve_x, P.tray_top() + 1.6, P.sleeve_zc()),
                                               xf.Rx(90))),
             (button.PLUNGER, button.plunger, xf.T(bx, by, P.btn_flange_top_z())),
             (button.DOME, button.dome, xf.mul(xf.T(bx, by, P.btn_dome_base_z()), xf.Rx(180))),
             (button.HOLDER, button.holder, xf.mul(xf.T(bx, by, P.bh_z1()), xf.Rx(180))),
             # the bar rests ON the post tops, so its outer face is clamp_t beyond them
             (button.CLAMP, button.clamp, xf.chain(P.top_face(P.voice_h),
                                                   xf.T(mx, my, P.wall + P.mic_post_h + P.mic_clamp_t),
                                                   xf.Rx(180)))]
    return amp, voice


SINGLE = {
    'amp-shell': (case.AMP_SHELL, case.amp_shell), 'amp-lid': (case.AMP_LID, case.amp_lid),
    'amp-sled': (case.AMP_SLED, case.amp_sled), 'voice-shell': (case.VOICE_SHELL, case.voice_shell),
    'voice-lid': (case.VOICE_LID, case.voice_lid), 'voice-tray': (case.VOICE_TRAY, case.voice_tray),
    'sleeve': (case.SLEEVE, case.sleeve), 'plunger': (button.PLUNGER, button.plunger),
    'dome': (button.DOME, button.dome), 'holder': (button.HOLDER, button.holder),
    'clamp': (button.CLAMP, button.clamp), 'plate': (plate.PLATE, plate.plate),
    'lock': (plate.LOCK, plate.lock),
    'coupon-amp': ('coupon amp', lambda p: case.coupon(p, 'amp')),
    'coupon-voice': ('coupon voice', lambda p: case.coupon(p, 'voice')),
}
PARTS = ('all', 'electronics') + tuple(SINGLE) + ('sync',)
SHELLS = (case.AMP_SHELL, case.VOICE_SHELL, case.AMP_LID, case.VOICE_LID, plate.PLATE)


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
    printed, items = [], []
    # The groups hold the ELECTRONICS only, each part at the group's identity. Printed parts
    # are top-level components placed in root coordinates: Fusion misplaced printed parts
    # positioned INSIDE a group (the amp shell landed rotated off its box, first real run), and
    # a root-level placement is the one form that came out right every time.
    groups = {'amp': Group(design, AMP_GROUP), 'voice': Group(design, VOICE_GROUP)}
    # the groups are never moved — see electronics.build()
    items += groups.values()
    if which == 'all':
        amp, voice = box_parts()
        for where, plist in (('amp', amp), ('voice', voice)):
            bx = box_xf(where)
            for name, builder, x in plist:
                printed.append(_make(design, name, builder, None, xf.mul(bx, x)))
        printed.append(_make(design, plate.PLATE, plate.plate, None, PLATE_XF))
        printed.append(_make(design, plate.LOCK, plate.lock, None, xf.T(0, 0, P.plate_h())))
    start = _timeline_mark(design)
    elec_parts = electronics.build(design, groups)
    _timeline_group(design, 'electronics', start)
    items += printed + elec_parts
    if ghost is not None:
        for p in printed:
            if p.comp.name in SHELLS:
                appearance.ghost(p.occ, ghost)
    remember_placement(design)
    return printed, items


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
