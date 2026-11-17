"""Headline numbers written into the design as REFERENCE user parameters (`ref_*`).

They drive nothing — the geometry comes from params.py and placement.py — and exist so a sketch
you draw by hand can be dimensioned against the unit (`ref_box_d`, `ref_amp_pcb_y`, ...) instead
of you looking each one up. Editing one changes NOTHING; change the Python and re-run, or drag
a part and `sync`. Same contract as hardware/voice-case/fusion.
"""

import adsk.core

from . import params as P

PREFIX = 'ref_'


def table():
    return [
        ('box_w', P.box_w, 'outer width'),
        ('box_h', P.box_h(), '(derived) outer height'),
        ('box_d', P.box_d, '(derived) depth, front face to the wall'),
        ('wall', P.wall, 'walls and panel'),
        ('plate_z', P.plate_z(), '(derived) back plate front face, box-local z'),
        ('face_top_y', P.face_top_y(), '(derived) amp faceplate front face, box-local y'),
        ('knob_z', P.knob_z(), '(derived) knob shafts, box-local z'),
        ('connector_y', P.connector_y(), '(derived) amp connector faces, box-local y'),
        ('btn_x', P.btn_pos[0], 'button axis on the front face, x (+ = viewer left)'),
        ('btn_y', P.btn_pos[1], 'button axis on the front face, y'),
        ('mic_x', P.mic_pos[0], 'mic port on the front face, x'),
        ('mic_y', P.mic_pos[1], 'mic port on the front face, y'),
        ('clr', P.clr, 'global clearance'),
    ]


def _expr(v):
    return '%g mm' % round(v, 4)


def write(design):
    """(added, updated, failed) — create or refresh every ref_ parameter; safe to re-run."""
    ups = design.userParameters
    added = updated = 0
    failed = []
    for name, value, comment in table():
        full = PREFIX + name
        try:
            p = ups.itemByName(full)
            if p:
                p.expression = _expr(value)
                p.comment = comment
                updated += 1
            else:
                ups.add(full, adsk.core.ValueInput.createByString(_expr(value)), 'mm', comment)
                added += 1
        except Exception as exc:
            failed.append('%s (%s)' % (full, exc))
    return added, updated, failed
