"""Voice S3 wall unit — parameters and derived dimensions (no geometry, no adsk).

FLAT: one layer against the wall. Two printed parts make the box:

  tray    back plate + top, bottom and both sides; screwed to the wall. EVERY board is on it:
          the ZK-502MT upright on standoffs in the middle (parts facing the front, knobs up
          through the top); on the viewer's left the ESP32-S3 devkit standing on the plate
          (USB-C down through the bottom); on the right the PCM5102A (top) and the MP1584
          (bottom, next to the DC jack), both flat on the plate. The mic sits in the bottom wall, port facing down.
          Prints back face down.
  panel   the front: a flat plate with the flexure button, its switch bridge and the engraved
          knob names. Two snap hooks into the top wall, two screws up from below. The ONLY wires
          to it are the switch's two, on a small plug: unplug and it comes away.

Positions of movable parts are in ``placement.py`` (the file `sync` rewrites) and re-exported
below. Every derived number is a function, so editing one value re-derives the whole chain.

TAGS — read them before trusting a number:
  [measured]  caliper value (this unit, or carried over from hardware/voice-case where printed)
  [user]      nominal given by the user, not yet checked against a print
  [photo]     estimated from photos. NOT a measurement — fit-check it
  [assumed]   no evidence at all; a typical value for the part
  [choice]    a design decision, free to change

FRAMES.
  Box-local (B): y UP from the box's bottom outer face, z INTO the box from the front outer face,
      x across. Right-handed, so +x is the VIEWER'S LEFT as you face the unit. Every printed part
      and every electronic dummy ends up in it.
  World: the box on the wall — x as box-local, y OUT of the wall (wall at 0), z up.
  Amp frame (A): the ZK-502MT's own numbers, kept as photographed — x from the board centre with
      + = the VOL end, y up from the component side's mounting plane, z from the faceplate's front
      face toward the connector edge. Those x's were taken with "+ = right as you look at the
      faceplate", which in a right-handed frame is a mirror, so `amp_xf()` maps A into B with a
      mirror: harmless, the amp is only dummies and points, never an occurrence transform.
  Tray frame (T): a board lying on a flat tray — x along it, y up off the tray, z across it.
      The devkit, DAC and MP1584 seats are drawn in it (each centred on its board) and put on the
      plate by `plate_xf()`, the tray surface landing on the plate's front face.
"""

import math

try:
    from . import placement as _pl
    from . import xf
except ImportError:                        # run directly, not as a package
    import placement as _pl
    import xf

# ---- placement (owned by placement.py) ----
amp_x = _pl.amp_x
amp_lift = _pl.amp_lift
s3_pos = tuple(_pl.s3_pos)
dac_pos = tuple(_pl.dac_pos)
mp_pos = tuple(_pl.mp_pos)
btn_pos = tuple(_pl.btn_pos)
mic_pos = tuple(_pl.mic_pos)
PLACEMENT = ('amp_x', 'amp_lift', 's3_pos', 'dac_pos', 'mp_pos', 'btn_pos', 'mic_pos')

# ---- fit ----
clr = 0.4                  # global clearance for parts that locate precisely
wall = 3                   # walls, and the front panel

# =====================================================================================
# ENVELOPE
# =====================================================================================
# Width: the devkit column (32.2) + the amp (60) + the DAC column (its seat across, 38.2) + gaps
# + walls, the two columns made equal so the amp — and its knobs — sit exactly in the middle.
box_w = 143                # [choice] outer width
box_r = 4                  # [choice] vertical-edge radius
front_chamfer = 1.5        # [choice] 45 deg front edge; the panel prints front face down
plug_room = 19             # [measured] under the amp's connector edge: the right-angle AUX plug
                           #          (aux_plug_barrel, 15) + 4 mm to the bottom wall. The old box had 0 mm: the plug
                           #          pushed the amp off its mounts
box_d = 37                 # [choice] front face to the wall: 34 mm walls behind the 3 mm panel. The
                           #          button's switch sits over a LOW strip of the amp (just under the
                           #          pots, chips only); the overlap checks prove it against the amp's
                           #          parts rather than stacking the whole 18 mm envelope behind it
plate_t = 5                # [choice] back plate: 3 mm keyhole pocket behind a 2 mm lip

screw_clear = 3.4          # M3 through
m3_pilot = 2.5             # M3 self-tapping into PETG
m3_cs_d = 6.5              # M3 flat head (ISO 10642 head 6.0) + clearance
vent_w = 2.5               # [choice]

# ---- panel fixing ----
lip_t = 1.6                # [choice] locating frame on the panel's back, just inside the walls
lip_d = 2.5                # [choice] ... its depth into the box
hook_w = 8                 # [choice] two snap hooks along the top, into windows in the top wall
hook_len = 3               # [choice] from the panel's back to the barb: short, to clear the faceplate
hook_t = 1.4               # [choice] spring thickness (PETG: ~2% strain at the barb)
hook_barb = 0.9            # [choice] barb height
hook_xs = (-25, 25)        # [choice] mirrored
pboss_od = 7               # [choice] two bosses on the panel's back at the bottom, screws up into them
pboss_len = 8
pboss_xs = (-32, 32)       # [choice]

# =====================================================================================
# AMPLIFIER — ZK-502MT, A frame (see the module docstring)
# =====================================================================================
# Lying flat in A: component side up, faceplate at the front, connector edge at the rear. Rear
# edge from +x to -x: AUX jack, small yellow part, 4-way barrier block, DC barrel.
A_MOUNT = 5.0              # A-frame y of the back plate's front face (the standoffs' feet)
amp_w = 60                 # [user] board width, along the faceplate
amp_l = 73                 # [measured] PCB rear edge to the faceplate's FRONT face
amp_env_h = 20             # [measured] PCB underside to the highest point (the heatsink), the board included
amp_tail_h = 2.5           # [assumed] through-hole tails under the PCB
amp_rear_over = 2.0        # [fit-checked] barrel / AUX bodies past the rear edge
amp_face_w = 60            # [assumed] MEASURE
amp_face_h = 18            # [assumed] MEASURE
amp_face_t = 1.6           # [measured]
amp_face_y0 = -1.0         # [photo] faceplate bottom vs the PCB underside. MEASURE
amp_face_x = 0             # [assumed]
# Mounting holes: a RECTANGLE — x from the board centre (+ = VOL end), depth as the distance from
# the REAR edge. Hole-centre spacing measured on the real board: 52 across, 43 front to rear.
amp_hole_dx = 26           # [measured] half the 52 spacing across
amp_hole_front = 57.5      # [fit-checked] front pair, from the rear edge (just behind the pots)
amp_hole_pitch = 43        # [measured] front pair to rear pair
amp_hole_rear = amp_hole_front - amp_hole_pitch
amp_holes = tuple((sx*amp_hole_dx, r) for r in (amp_hole_rear, amp_hole_front) for sx in (1, -1))
amp_screw_head = (5.5, 2.4)  # M3 pan head d, h — drawn on the board, kept clear of parts
amp_hole_pilot = 2.6
amp_standoff_od = 6.5
amp_standoff_h = 6         # [choice] tails + the 24 V tap wires behind the board
amp_hs = (-4, 32, 20, 20)  # [fit-checked] heatsink [x, from rear, size x, size along the board]
amp_caps = ((-20, 30), (12, 30))   # [fit-checked] the two 470 uF / 35 V caps flanking the heatsink: x, from rear
amp_cap_d = 10.0           # [fit-checked] 470 uF 35 V: 10 x 13 typical. MEASURE the height
amp_cap_h = 13.0
amp_dc_x = -22             # [user] (photo said -23; the hole moved 1 mm toward the middle)
amp_dc_axis = 6.0          # [fit-checked] above the PCB top. MEASURE
amp_dc_plug_d = 10         # [fit-checked] straight barrel plug body. MEASURE yours
amp_dc_plug_len = 34       # [fit-checked] ... jack face to the end of its strain relief
dc_hole_clr = 1.0          # [choice] round the plug body in the bottom (the jack is a [photo] x)
spk_hole_d = 7             # [choice] two holes under the barrier block, one per speaker cable
spk_hole_dx = 7            # [choice] each side of the block's centre
amp_term_x = (-11, 16)     # [fit-checked] barrier block span
amp_term_h = 10            # [fit-checked]
amp_aux_x = 22             # [fit-checked]
amp_aux_axis = 3.0         # [fit-checked]

# ---- controls: the pots come out through the TOP wall ----
face_gap = 1.3             # [choice] faceplate front face to the top wall's inside; the pot nuts
                           #          (~2 mm, left on as shipped) sink into recesses in the top
nut_recess_d = 12.0        # [assumed] across the pot nuts' corners + clearance
nut_recess_depth = 0.8     # [choice] into the 3 mm top wall
ctrl_pitch = 18            # [measured] knob centre to centre
ctrl_x0 = 0                # [assumed]
ctrl_axis = 9              # [photo] above the PCB UNDERSIDE. MEASURE
ctrl_bush_d = 7            # [assumed]
ctrl_slack = 1.0
ctrl_led = (27, 5)         # [photo]
ctrl_shaft_proj = 13       # [measured] shaft past the faceplate's front face
knob_min_grip = 8          # [choice]
# Engraved over each knob along the front face's top edge, 0.6 deep to be filled with paint.
# Keyed by the pot's A-frame position: +1 = the VOL end.
knob_names = {1: 'VOLUME', 0: 'BASS', -1: 'TREBLE'}
label_h = 3.0              # [choice] cap height (4 overlapped: the knobs are 20 apart)
label_depth = 0.6          # [choice]
label_font = 'Arial Black'
label_shift = 0            # [choice] push the two outer names outward if they crowd BASS
# Arial Black advance widths, per 1000 em, and its cap height as a share of the em: the overlap
# check measures the real names rather than guessing (0.8 x height per letter was 30% short).
_ARIAL_BLACK = {'A': 778, 'B': 778, 'E': 722, 'L': 667, 'M': 944, 'O': 833, 'R': 778, 'S': 667,
                'T': 722, 'U': 778, 'V': 778}
label_cap = 0.716

# ---- MP1584 ----
mp_w = 24                  # [user] along tray x (the module's length)
mp_l = 17                  # [user] along tray z
mp_h = 5                   # [assumed] tallest part above its PCB underside
mp_wall = 1.6
mp_bed_extra = 1.0         # [choice] the bed 1 mm longer than the board along its long side
mp_lip = 5                 # [choice] pocket wall height; room over the board for soldered leads


# =====================================================================================
# VOICE BOARDS — either side of the amp
# =====================================================================================
col_gap = 0.5              # [choice] amp board edge to each column
s3_orient = 'plate_down'   # devkit standing on the plate (left), USB-C end DOWN
mp_orient = 'plate_across'
dac_orient = 'socket_down' # across the plate (right), socket edge DOWN

# ---- voice boards ----
s3_w = 70                  # [measured] the new ESP32-S3 devkit: length (was 63)
s3_l = 26                  # [measured] ... width (was 28)
s3_comp_h = 11             # [measured] headers + dressed wire above the PCB
s3_board_clr = 0.5         # [measured]
pcb_t = 1.6
pocket_wall = 1.6
dac_wall = 1.2             # [choice] the DAC seat's walls — it sets the box width
board_pin_h = 2.0
tray_seat = 2.5            # [choice] devkit PCB above the wall (pin tails sink into reliefs)
tray_lip = 3.5             # [measured]
pin_row_w = 6              # [measured]
board_clr = 1.0            # [measured]

dac_w = 20                 # [measured]
dac_l = 33                 # [measured]
dac_jack_w = 6.0           # [measured]
dac_jack_h = 6.5           # voice-case value — MEASURE
dac_jack_overhang = 2.5
dac_jack_inset = 3.0       # [measured]
dac_jack_axis = 3.2        # voice-case: barrel axis from the PCB face
dac_jack_depth = 13.0      # voice-case: how far the socket body reaches inboard of its edge
dac_jack_end = -1          # which end of the board (tray x) the socket sits at
dac_aux_plug = 15          # [measured] the same JZK plug as at the amp (aux_plug_barrel), past the socket face
# DAC seat: voice-case's printed, working DAC pocket. The board sits COMPONENT SIDE DOWN on a
# solid block; the socket hangs into a zero-clearance recess, which is what locates it.
dac_seat_h = 6.0           # [user] PCB above the plate; was 8 (voice-case's 7 + 1 for a sleeve that is gone)
dac_plug_groove = 1.2      # [choice] into the plate under the plug head, which sits that low now
dac_lip = 4.0
dac_cut_w = 6
pin_land = 4
pin_relief_setback = 0.5
dac_relief_edge_gap = 1.8
dac_block_edge_gap = 0.4

# ---- flexure button ----
# A disc cut free of the front wall by three stepped-spiral slots: each slot runs an arc at
# radius btn_r_a, steps out, and runs on at btn_r_b, so between neighbouring slots there is an
# arm ~105 deg long. The ring the arms live in is thinned from the inside to btn_flex_t; the
# disc stays full thickness and carries the nub that presses a tactile switch on a bridge behind.
# Three arms, 120 deg apart: the disc moves straight in wherever it is pressed.
btn_disc_d = 24            # [choice] the part you press
btn_slot_w = 1.2           # [choice]
btn_step = 3.4             # [choice] r_b - r_a: the arm's radial width + one slot
btn_arc_in = 105           # [choice] deg, each slot's inner arc
btn_arc_out = 105          # [choice] deg, each slot's outer arc
btn_flex_t = 1.2           # [choice] arm thickness (PETG; PLA works but creeps)
btn_flex_margin = 0.6      # [choice] thinned rim past the outer slots
btn_nub_d = 3.0
btn_nub_len = 3.0          # [choice] from the disc's inner face
btn_preload = 0.25         # [measured] nub into the switch plunger at rest
petg_e = 2000              # MPa, for the stiffness / stress estimate in the report
petg_allow = 20            # MPa, fatigue-safe bending stress at full travel
btn_travel = 1.0           # [choice] design travel for that estimate

# tactile switch (12 x 12 class, voice-case's) on the bridge behind the disc
sw_body = 11.0
sw_h = 8.0
sw_plunger_d = 3.0
sw_plunger_h = 1.8
sw_travel = 0.7
sw_pin_axis = 0
sw_pin_out = 1.0
sw_pin_gap = 5.0
sw_pin_win = 2.2
sw_pin_len = 3.5
sw_pin_slack = 1.5

bridge_t = 2.5             # [choice]
bridge_w = 8               # [choice] arm width
bridge_pad = 15            # [choice] square pad the switch sits on
bridge_recess = 1.0        # [choice] switch body sunk into the pad
bridge_foot_r = 20         # [choice] feet from the button axis, on a diagonal
bridge_angle = 0          # [choice] deg: feet side by side, clear of the amp's capacitors
bridge_post_od = 5
board_screw_pilot = 1.6    # M2 self-tapping
bh_screw_clear = 2.2
bh_screw_cbore_d = 4.0
bh_screw_cbore_h = 1.2

# ---- microphone: in the TOP wall beside the knobs, port facing up ----
mic_board_w = 17           # [measured] along x
mic_board_l = 15           # [measured] along z
mic_seat_depth = 1.0
mic_gasket_d = 12          # cut the gasket's own centre hole to >= mic_grille_d() so every hole opens
mic_gasket_depth = 0.8
mic_hole_d = 1.5           # [choice] a grille: one hole in the middle, six round it — the one 2 mm
mic_grille_r = 3.0         #          port was a quarter of the open area and muffled the sound
mic_grille_n = 6
mic_post_pitch = 24
mic_post_od = 5
mic_post_h = 4
mic_clamp_w = 5
mic_clamp_t = 1.25
mic_clamp_pad = 10
mic_screw_clear = 2.4

# ---- devkit USB-C window: in the bottom wall, under the devkit's USB end ----
s3_module = (25.5, 18, 3.2)    # [datasheet] ESP32-S3-WROOM-1: along x, along z, height
s3_usb = (7.4, 9, 3.3)         # [fit-checked] USB-C receptacle: along x (depth), z, height
s3_usb_pitch = 13              # [fit-checked] two USB-C on the end opposite the module
s3_usb_h = 10
s3_usb_trim = 2.0
usb_panel_t = 1.8
usb_cb_margin = 2.0
s3_hdr = (2.5, 8.5)
s3_dupont_h = s3_comp_h
dac_hdr_len = 16
mic_hdr = (8, 2.5, 8.5)

# =====================================================================================
# TRAY: back plate
# =====================================================================================
# Hung on TWO wall screws through keyholes, held down by ONE locking screw — so it comes off the
# wall by removing the panel and that one screw, never the amp. The keyholes sit behind the amp
# (nothing to reach: the heads go in from behind), the locking screw low in the middle, under
# the amp's connectors, where a screwdriver reaches it with the panel off.
ws_d = 4.5                 # 4 mm wood screws + plugs
ws_head_d = 9              # countersunk head of the locking screw
kh_head = 9.5              # [choice] keyhole entry: wall-screw heads up to 8.5 mm
kh_shank = 5.0             # [choice] the slot the shank slides up
kh_drop = 9.0              # [choice] how far the box drops once hung
kh_lip = 2.0               # [choice] plastic in front of the screw heads
kh_pts = ((16, 60), (-16, 60))   # [choice] keyhole ENTRY centres (x, y); the slot runs up from it
lock_pt = (2.5, 8)         # [choice] locking screw: between the speaker cables, under the amp
knockout_d = 12            # [choice] break-out discs in the plate for cables from the wall
knockout_skin = 0.6

# =====================================================================================
# ELECTRONICS — dummy-component sizes
# =====================================================================================
amp_pot_body = (10, 10, 11)    # [assumed] pot body behind the faceplate: x, z(depth), y
amp_pot_shaft_d = 6
knob_d = 15                    # [fit-checked] the knobs sat fully down on the printed top
knob_h = 14
knob_gap = 1.0
amp_dc_body = (9, 13, 11)      # [fit-checked] PCB barrel jack: x, z(depth), height
amp_aux_body = (6, 12, 5)
amp_term_depth = 8
amp_sw_onboard = (8, 7, 6)
amp_sw_onboard_at = (21, 22)   # [fit-checked]
amp_led_d = 3
aux_plug_d = 6
aux_plug_past_edge = 17    # [measured] PCB rear edge to the far side of the plugged-in right-angle
                           #          AUX plug, its cable bend included (JZK 90 deg TRS): 73 + 17 = 90
aux_plug_barrel = aux_plug_past_edge - amp_rear_over    # 15: jack face to the plug's far side
patch_cable_d = 3.5
lead_d = 2.0
spk_cable_d = 5.0
dc_cable_d = 4.5
mp_inductor = (7, 7, 4)
mp_trim = (4, 4, 4)


# =====================================================================================
# DERIVED
# =====================================================================================
def inner_w():          return box_w - 2*wall
def ih():               return inner_w()/2

# ---- amp, A frame ----
def amp_front_z():      return 2.0                 # faceplate front face, A frame
def amp_rear_z():       return amp_front_z() + amp_l
def plug_z0():          return amp_rear_z() + amp_rear_over
def amp_standoff_len(): return amp_standoff_h + amp_lift
def amp_pcb_y():        return A_MOUNT + amp_standoff_len()
def amp_pcb_top():      return amp_pcb_y() + pcb_t
def amp_env_top():      return amp_pcb_y() + amp_env_h
def amp_face_y():       return amp_pcb_y() + amp_face_y0
def amp_bz(from_rear):  return amp_rear_z() - from_rear


def term_xs():
    c = (amp_term_x[0] + amp_term_x[1])/2
    return [amp_x + c + (i - 1.5)*9 for i in range(4)]


# ---- the box ----
def box_h():            return wall + plug_room + (plug_z0() - amp_front_z()) + face_gap + wall
def face_top_y():       return box_h() - wall - face_gap      # faceplate front face, B
def plate_z():          return box_d - plate_t                       # plate front face
def cavity():           return ((-ih(), wall, wall), (ih(), box_h() - wall, plate_z()))
def amp_x0():           return amp_x - amp_w/2            # board edges, B x (A x == B x)
def amp_x1():           return amp_x + amp_w/2
def col_x():            return (amp_x1() + col_gap, ih())  # the devkit column (viewer's left)
def col_r_x():          return (-ih(), amp_x0() - col_gap)  # the DAC + MP1584 column (right)


def amp_xf():
    """A -> B: (x, y, z) -> (x, face_top_y + amp_front_z - z, plate_z + A_MOUNT - y).
    Faceplate up, components facing the front, mounting plane on the plate. A mirror — see the
    module docstring."""
    return xf.M(((1, 0, 0), (0, 0, -1), (0, -1, 0)),
                (0, face_top_y() + amp_front_z(), plate_z() + A_MOUNT))


def amp_b(p):
    """one A-frame point in B"""
    return xf.apply(amp_xf(), p)


def knob_xs():
    """[(B x, name)] of the three pots, from the A-frame layout"""
    return [(amp_x + ctrl_x0 + i*ctrl_pitch, knob_names[i]) for i in (1, 0, -1)]


def knob_z():           return amp_b((0, amp_pcb_y() + ctrl_axis, 0))[2]     # shaft axis, B z
def knob_proj():        return ctrl_shaft_proj - face_gap - wall               # above the top
def top_z_a():          return amp_front_z() - (box_h() - face_top_y())        # top outer face, A z


def face_span_z():
    """faceplate depth range in B (it lies under the top wall)"""
    a, b = amp_b((0, amp_face_y(), 0))[2], amp_b((0, amp_face_y() + amp_face_h, 0))[2]
    return min(a, b), max(a, b)


def standoff_pts():
    """[(B x, B y)] of the amp's four standoffs"""
    out = []
    for hx, hr in amp_holes:
        p = amp_b((amp_x + hx, 0, amp_bz(hr)))
        out.append((p[0], p[1]))
    return out


def connector_y():      return amp_b((0, 0, plug_z0()))[1]   # connector faces, B y


# ---- boards on the plate / tower: tray frame -> B ----
_ROT = {
    # standing on the plate: tray x -> B +y, so the USB end (tray -x) points DOWN at its window in
    # the bottom; tray y -> B -z (off the plate, toward the front); tray z -> B -x
    'plate_down': ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
    # lying across the plate: tray x -> B x, tray y -> B -z, tray z -> B y
    'plate_across': ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    # across the plate: tray x -> B -x, tray y -> B -z, tray z (the socket edge) -> B -y (DOWN)
    'socket_down': ((-1, 0, 0), (0, 0, -1), (0, -1, 0)),
}


def plate_xf(pos, orient, z):
    """tray frame (centred on the board, tray surface at y = 0) -> B, the tray surface at B z"""
    return xf.M(_ROT[orient], (pos[0], pos[1], z))


def s3_xf():            return plate_xf(s3_pos, s3_orient, plate_z())
def mp_xf():            return plate_xf(mp_pos, mp_orient, plate_z())
def dac_xf():           return plate_xf(dac_pos, dac_orient, plate_z())


# ---- devkit pocket, tray frame ----
def s3_cav():           return (s3_w + 2*s3_board_clr, s3_l + 2*s3_board_clr)
def s3_pocket():        return (s3_cav()[0] + 2*pocket_wall, s3_cav()[1] + 2*pocket_wall)
def s3_pocket_h():      return tray_seat + pcb_t + tray_lip
def s3_usb_w():         return s3_usb_pitch + s3_usb[1] + 2*s3_board_clr + 1.0
def s3_usb_notch():     return s3_usb_w() + 2*clr


# ---- DAC seat, tray frame (board centre at the origin, socket edge at +z) ----
def dac_block_x():      return dac_l/2 + board_clr + dac_wall
def dac_block_z0():     return -(dac_w/2 + board_clr + dac_wall)
def dac_edge_z():       return dac_w/2
def dac_socket_z():     return dac_edge_z() + dac_jack_overhang
def dac_block_z1():     return dac_edge_z() - dac_block_edge_gap
def dac_seat_y():       return dac_seat_h                     # PCB underside (component side)
def dac_pcb_top_y():    return dac_seat_y() + pcb_t
def dac_block_top():    return dac_pcb_top_y() + dac_lip
def dac_axis_y():       return dac_seat_y() - dac_jack_axis
def dac_jack_off():     return dac_jack_end*(dac_l/2 - dac_jack_inset - dac_jack_w/2)
def dac_recess_w():     return max(dac_cut_w, dac_jack_w)
def dac_recess_z0():    return dac_edge_z() - dac_jack_depth - clr
def dac_recess_y0():    return dac_seat_y() - dac_jack_h - clr
def dac_relief_x():     return -dac_jack_end*((dac_l + 2*board_clr)/2 - pin_relief_setback - dac_cut_w/2)
def dac_relief_z0():    return -(dac_w/2 + board_clr - pin_land)
def dac_relief_z1():    return dac_edge_z() - dac_relief_edge_gap


# ---- MP1584 pocket, tray frame ----
def mp_cav():           return (mp_w + mp_bed_extra + 2*clr, mp_l + 2*clr)
def mp_ring():          return (mp_cav()[0] + 2*mp_wall, mp_cav()[1] + 2*mp_wall)


# ---- flexure button ----
def btn_r_a():          return btn_disc_d/2 + btn_slot_w/2      # inner slot arcs, centreline
def btn_r_b():          return btn_r_a() + btn_step              # outer slot arcs, centreline
def btn_r_out():        return btn_r_b() + btn_slot_w/2 + btn_flex_margin   # thinned ring edge
def btn_arm_w():        return btn_step - btn_slot_w
def btn_arm_len():
    """mean arm length: the overlap of one slot's outer arc and the next one's inner arc"""
    overlap = min(btn_arc_in + btn_arc_out, 120 + btn_arc_in) - max(btn_arc_in, 120)
    return math.radians(max(overlap, 0))*(btn_r_a() + btn_r_b())/2
def btn_junction():
    """disc-to-arm junction: the land between one slot's step and the next slot's start, at r_a"""
    return math.radians(120 - btn_arc_in)*btn_r_a() - btn_slot_w
def btn_stiffness():
    """N/mm, three fixed-guided arms bending out of plane (curved arms are softer: an upper bound)"""
    I = btn_arm_w()*btn_flex_t**3/12
    return 3*12*petg_e*I/btn_arm_len()**3
def btn_stress():       return 3*petg_e*btn_flex_t*btn_travel/btn_arm_len()**2   # MPa at btn_travel
def btn_nub_end():      return wall + btn_nub_len
def sw_body_h():        return sw_h - sw_plunger_h
def bridge_z():         return btn_nub_end() - btn_preload + sw_h - bridge_recess   # pad face, B z
def bridge_back_z():    return bridge_z() + bridge_t
def sw_back_z():        return bridge_z() + bridge_recess
def sw_front_z():       return sw_back_z() - sw_body_h()
def sw_tip_z():         return sw_back_z() - sw_h
def sw_pin_pos():
    a, b = sw_body/2 + sw_pin_out, sw_pin_gap/2
    return [(sa*a, sb*b) if sw_pin_axis == 0 else (sb*b, sa*a) for sa in (-1, 1) for sb in (-1, 1)]
def sw_pin_win_xy():
    s = 2*sw_pin_slack
    return (s, sw_pin_win) if sw_pin_axis == 0 else (sw_pin_win, s)


def bridge_feet():
    a = math.radians(bridge_angle)
    x, y = btn_pos
    return [(x + s*bridge_foot_r*math.cos(a), y + s*bridge_foot_r*math.sin(a)) for s in (1, -1)]


def bridge_xf():
    """bridge print frame (bar along x, pad face on top at z = bridge_t) -> B"""
    x, y = btn_pos
    return xf.chain(xf.T(x, y, bridge_z() + bridge_t), xf.Rz(bridge_angle), xf.Rx(180))


# ---- mic, in the top wall: (x, z) on the top face; depths measured down from the top ----
def mic_size():         return (mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od))
def mic_board_top_y():  return wall - mic_seat_depth + pcb_t     # board's inner face, depth below the top
def mic_clamp_pad_h():  return (wall + mic_post_h) - mic_board_top_y()
def mic_clamp_len():    return mic_post_pitch + mic_post_od
def mic_grille_d():     return 2*mic_grille_r + mic_hole_d
def mic_holes():
    x, z = mic_pos
    out = [(x, z)]
    for i in range(mic_grille_n):
        a = math.radians(i*360.0/mic_grille_n)
        out.append((x + mic_grille_r*math.cos(a), z + mic_grille_r*math.sin(a)))
    return out


# ---- labels ----
def label_y():          return box_h() - front_chamfer - 1 - label_h/2
def label_w(name):
    """width in mm, taking label_h as the CAP height (the larger of Fusion's two readings)"""
    return sum(_ARIAL_BLACK.get(ch, 833) for ch in name)/1000*label_h/label_cap


def label_xs():
    """[(B x, name)]: over each knob, the outer two pushed outward by label_shift"""
    return [(x + (0 if abs(x - amp_x) < 1e-9 else math.copysign(label_shift, x - amp_x)), n)
            for x, n in knob_xs()]


# ---- bottom: the DC plug and the speaker leads go straight out ----
def dc_hole_pt():
    """(B x, B z) of the barrel jack's axis, where the plug comes up through the base"""
    p = amp_b((amp_x + amp_dc_x, amp_pcb_top() + amp_dc_axis, 0))
    return (p[0], p[2])


def dc_hole_d():        return amp_dc_plug_d + 2*dc_hole_clr


def spk_hole_pts():
    xc = amp_x + (amp_term_x[0] + amp_term_x[1])/2
    z = amp_b((0, amp_pcb_top() + amp_term_h/2, 0))[2]
    return [(xc - spk_hole_dx, z), (xc + spk_hole_dx, z)]


bottom_vent_xs = (-13, 2.5, 18, 26)       # [choice] intake slots under the amp, clear of the holes
vent_len = 10.0
def vent_zc():          return dc_hole_pt()[1]                 # in line with the DC plug hole


# ---- devkit USB-C, down through the bottom ----
def s3_usb_z():         return plate_z() - tray_seat - pcb_t - s3_usb[2]/2
def usb_setback():      return s3_pos[1] - s3_w/2       # receptacle faces to the bottom's outer face


# ---- top vents: one row in front of the faceplate, one behind it (the heatsink's chimney) ----
# Mirrored about the middle and as long as the top allows: the front row stops short of the mic
# seat (and the same distance short on the other side), the back row runs nearly wall to wall.
# Short bridges between the slots keep the top wall stiff.
vent_bridge = 2.0          # [choice]
vent_rows = ((2, 'front'), (8, 'back'))   # [choice] slots per row


def _row_span(which):
    """half-width of a row: to 1.5 mm short of the mic seat, or of the side walls"""
    if which == 'front':                   # ...and of the hook windows
        return min(abs(mic_pos[0]) - mic_size()[0]/2, min(abs(x) for x in hook_xs) - hook_w/2 - 0.5) - 1.5
    return ih() - 4


def top_vents():
    """[(x, z, length)] of every top slot"""
    f0, f1 = face_span_z()
    z = {'front': f0 - 1.5, 'back': (f1 + plate_z())/2}
    out = []
    for n, which in vent_rows:
        half = _row_span(which)
        ln = (2*half - (n - 1)*vent_bridge)/n
        for i in range(n):
            out.append((-half + ln/2 + i*(ln + vent_bridge), z[which], ln))
    return out


# ---- panel fixing ----
def pboss_z():          return (wall, wall + pboss_len)
def pboss_screw_pts():  return [(x, wall + pboss_len/2) for x in pboss_xs]


def hook_window():
    """(z0, z1) of the window in the top wall a hook's barb snaps into"""
    z = wall + hook_len
    return (z - 0.5, z + 3)


# ---- wall mounting ----
def kh_hang_pts():
    """where each wall screw ends up once the box has dropped onto it: the top of its slot"""
    return [(x, y + kh_drop) for x, y in kh_pts]


def knockout_pts():
    return [(amp_x - 14, wall + plug_room/2), (amp_x + 14, wall + plug_room/2)]


def aabb_clear(p1, s1, p2, s2):
    return (abs(p1[0] - p2[0]) >= (s1[0] + s2[0])/2) or (abs(p1[1] - p2[1]) >= (s1[1] + s2[1])/2)
