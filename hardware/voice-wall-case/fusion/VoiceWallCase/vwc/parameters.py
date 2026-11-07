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
        ('box_w', P.box_w, 'both boxes, outer width'),
        ('box_d', P.box_d(), '(derived) shell depth, front face to rear rim'),
        ('amp_h', P.amp_h(), '(derived) amp box height'),
        ('voice_h', P.voice_h, 'voice box height'),
        ('wall', P.wall, 'shell walls'),
        ('front_y', P.front_y(), '(derived) front faces, distance from the wall'),
        ('voice_z0', P.voice_z0(), '(derived) voice box bottom above the amp box bottom'),
        ('amp_pcb_y', P.amp_pcb_y(), '(derived) amp PCB underside, box-local y'),
        ('amp_front_z', P.amp_front_z(), '(derived) faceplate front face, box-local z'),
        ('amp_rear_z', P.amp_rear_z(), '(derived) amp PCB rear edge, box-local z'),
        ('plug_zc', P.plug_zc(), '(derived) middle of the plug zone, box-local z'),
        ('sleeve_x', P.sleeve_x, 'sleeve axis, x'),
        ('sleeve_zc', P.sleeve_zc(), '(derived) sleeve axis, box-local z'),
        ('board_seat_y', P.board_seat_y(), '(derived) voice boards PCB underside, box-local y'),
        ('s3_zc', P.s3_zc(), '(derived) devkit centre, box-local z'),
        ('dac_xc', P.dac_xc(), '(derived) DAC centre, x'),
        ('dac_zc', P.dac_zc(), '(derived) DAC centre, box-local z'),
        ('btn_x', P.btn_pos[0], 'button axis on the voice face, x'),
        ('btn_y', P.btn_pos[1], 'button axis on the voice face, y'),
        ('mic_x', P.mic_pos[0], 'mic port on the voice TOP face, x'),
        ('mic_z', P.mic_pos[1], 'mic port on the voice TOP face, depth from the front'),
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
