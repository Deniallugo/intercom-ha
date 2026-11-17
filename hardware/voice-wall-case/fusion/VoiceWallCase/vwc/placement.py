"""Where the movable components sit — the file `sync` rewrites.

FRAME. Box-local mm: y up from the box's bottom face, x across with +x to the VIEWER'S LEFT.
That is not a typo: box-local is a real, right-handed frame with z running INTO the box from the
front face, and with y up that puts +x on your left as you face the unit.

Each value is read by the electronics model AND by every printed feature built for that part, so
moving one moves the board and its seat, posts or holes together.

Two ways to change one:
  * edit it here and re-run the script, or
  * drag the component in Fusion (inside the "electronics" group), run the script with
    part = `sync`, and it writes the move back here — only the number on the `name = value`
    line changes; comments and layout are left alone. Then re-run `all`.
"""

# ---- amplifier (ZK-502MT), upright on the back plate, knobs up through the top ----
amp_x = 0             # board centre, x: in the middle, so the knobs are centred
amp_lift = 0          # (off) taller standoffs: the board comes forward and the box gets deeper

# ---- voice boards on the back plate (x, y of each board's centre) ----
s3_pos = (49.5, 40.6)     # ESP32-S3 devkit, viewer's LEFT, standing, USB-C down through the bottom
dac_pos = (-49.5, 79.7)  # PCM5102A, viewer's RIGHT, top of the column, socket edge facing down
mp_pos = (-49.5, 30.5)    # MP1584, viewer's RIGHT, bottom of the column, next to the DC jack

# ---- front panel ----
btn_pos = (0, 75)         # flexure button disc, above the amp's heatsink (its switch sits behind)

# ---- bottom wall ----
mic_pos = (49.5, 14)      # INMP441 grille in the TOP, beside the knobs, over the devkit: (x, z = depth from the front), port facing up
