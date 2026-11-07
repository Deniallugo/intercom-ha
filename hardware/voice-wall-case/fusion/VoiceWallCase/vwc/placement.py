"""Where the movable components sit — the file `sync` rewrites.

Every value here is a component POSITION in its box's local frame (x across, +x to the right
as you face the unit; y up from the box's bottom outer face; z into the box from its front
outer face). Each one is read by both the electronics model and every case feature that
depends on that component, so moving a value moves the board AND its pocket, standoffs,
window or hole together.

Two ways to change one:
  * edit it here and re-run the script, or
  * drag the component in Fusion (inside its box's sub-assembly), run the script with
    part = `sync`, and it writes the move back into this file — only the number on the
    `name = value` line changes; comments and layout are left alone. Then re-run `all`.

Absolute values are marked (abs); the rest are OFFSETS from a derived position, marked (off),
and 0 means "where the layout puts it". The OpenSCAD reads the same names (tests pass them in
with -D), so after a sync the geometry cross-check still compares like with like.
"""

# ---- amplifier box -------------------------------------------------------------------
amp_x = 0             # (off) ZK-502MT board centre across x
amp_lift = 0          # (off) board raised on taller standoffs; the box grows by the same
amp_setback = 0       # (off) faceplate behind the front wall — "holes" mode only
mp_x = 1              # (abs) MP1584 pocket centre across x
mp_dz = 0             # (off) MP1584 along z, from the middle of the plug zone
amp_psw_y = 28        # (abs) panel switch cut-out centre, height above the box bottom
psw_dz = 0            # (off) panel switch along z, from the middle of the plug zone

# ---- voice box -----------------------------------------------------------------------
s3_x = 0              # (off) ESP32-S3 devkit pocket centre across x
s3_z0 = 19.5          # (abs) devkit pocket's front face, depth from the box front
dac_dx = 0            # (off) PCM5102A from its derived spot (socket over the sleeve), x
dac_dz = 0            # (off) ... and z; >= 0, it shares the devkit pocket's rear wall at 0
btn_pos = (0, 24)     # (abs) dome button axis on the front face, (x, y)
mic_pos = (0, 30)     # (abs) INMP441 port on the TOP face, (x, z = depth from the front)
sleeve_x = 4          # (abs) pass-through sleeve axis across x (both boxes)
sleeve_dz = 0         # (off) ... along z, from the middle of the plug zone
