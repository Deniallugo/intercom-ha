"""The headline numbers, written into the design as REFERENCE user parameters.

They drive nothing. The geometry comes from `params.py`, exactly as it did from
`params.scad`, and these are copies deposited in the Parameters dialog so that a sketch you
draw by hand can be dimensioned against the case — `ref_plan_x/2`, `ref_boss_cx`,
`ref_dac_axis_z` — instead of you looking each one up in the Python.

Two consequences worth being clear about, because a parameter that looks live and is not is
worse than no parameter at all:

  * Editing one changes NOTHING. The features were built from computed coordinates, with no
    dimensional constraints tied to these, so the model will not move. Change the value in
    `params.py` and re-run.
  * They are all prefixed `ref_`, which keeps them out of the way of any parameter you
    create yourself (the script would otherwise overwrite a same-named one of yours), sorts
    them together in the dialog, and says what they are at a glance.

Derived entries are marked "(derived)" in their comment: those have no equivalent line in
`params.py` to edit — they fall out of the chain, and the comment says what from.
"""

import adsk.core

from . import params as P

PREFIX = 'ref_'


def table():
    """[(name, mm, comment)] — what is worth having on hand when sketching by hand."""
    return [
        # ---- envelope ----
        ('plan_x', P.plan_x, 'case across x (+x is the audio side)'),
        ('plan_y', P.plan_y, 'case along y (+y is the front)'),
        ('cavity_depth', P.cavity_depth, 'interior height under the top face'),
        ('wall', P.wall, 'walls, top face and base plate'),
        ('radius', P.radius, 'rounded vertical corners'),
        ('chamfer', P.chamfer, '45 deg top-edge chamfer'),
        ('outer_d', P.outer_d(), '(derived) overall height, shell + plate'),
        ('top_depth', P.top_depth(), '(derived) top outer face to the plate inner face'),
        ('flat_half_x', P.flat_half_x(),
         '(derived) half the FLAT top face after the chamfer — the real bound for anything '
         'on it'),
        ('flat_half_y', P.flat_half_y(), '(derived) the same along y'),
        # ---- corners ----
        ('boss_cx', P.boss_cx(), '(derived) corner boss / M3 screw centre, x'),
        ('boss_cy', P.boss_cy(), '(derived) corner boss / M3 screw centre, y'),
        ('boss_od', P.boss_od, 'corner boss od, full depth of the cavity'),
        # ---- boards on the plate ----
        ('s3_pos_x', P.s3_pos_x(),
         '(derived) devkit pocket centre in x — hangs off the DAC, one shared wall inboard'),
        ('s3_cy', P.s3_cy(),
         '(derived) devkit centre in y — its rear edge is against the plate\'s stops'),
        ('dac_cx', P.dac_cx(),
         '(derived) DAC centre in x — set backwards from where its socket must land'),
        ('dac_jack_y', P.dac_jack_y(),
         '(derived) 3.5 mm hole centre in y; the socket sits in the board\'s front corner'),
        ('dac_axis_z', P.dac_axis_z(),
         '(derived) 3.5 mm barrel axis in case z (0 = top outer face, +z into the box)'),
        # ---- top face ----
        ('btn_bore_d', P.btn_bore_d(), '(derived) shell bore the cap body runs in'),
        ('btn_recess_d', P.btn_recess_d(), '(derived) cap flange recess'),
        ('btn_cap_d', P.btn_cap_d, 'cap flange od — the diameter you actually see'),
        ('btn_pilot_pitch', P.btn_pilot_pitch, 'the holder\'s two blind M2 pilots, on +-x'),
        ('bh_deep_z', P.bh_deep_z(),
         '(derived) deepest point of the button module below the top face — the switch pins'),
        ('mic_pos_y', P.mic_pos[1], 'mic seat centre in y, on the button\'s axis'),
        ('mic_post_pitch', P.mic_post_pitch, 'the two M2 posts flanking the mic board'),
        ('mic_hole_d', P.mic_hole_d, 'the single mic port'),
        # ---- fit ----
        ('clr', P.clr, 'global clearance for inserted parts'),
    ]


def _expr(value):
    return '%g mm' % round(value, 4)


def write(design):
    """(added, updated, failed) — create or refresh every ref_ parameter."""
    ups = design.userParameters
    added = updated = 0
    failed = []
    for name, value, comment in table():
        full = PREFIX + name
        try:
            existing = ups.itemByName(full)
            if existing:
                existing.expression = _expr(value)
                existing.comment = comment
                updated += 1
            else:
                ups.add(full, adsk.core.ValueInput.createByString(_expr(value)),
                        'mm', comment)
                added += 1
        except Exception as exc:                # a name Fusion will not take, say
            failed.append('%s (%s)' % (full, exc))
    return added, updated, failed
