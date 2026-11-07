"""Voice S3 wall unit — parameters and derived dimensions (no geometry, no adsk).

Ported 1:1 from ``../../../modules/params.scad``: same names, same numbers, mm throughout, and
everything that was an OpenSCAD ``function`` is a function here, so editing a number re-derives
the whole chain instead of leaving a stale copy. The positions of the movable components are
not here — they are in ``placement.py``, the file `sync` rewrites — and are re-exported below so
everything else can keep reading ``P.btn_pos``.

New relative to the OpenSCAD: the ELECTRONICS block at the end — the size of every part that is
modelled as a dummy component (pots, jacks, plugs, the devkit's module and headers, knobs,
cables...). Those numbers place nothing printed; they exist so you can SEE the parts in Fusion,
drag them, and so `checks.py` can tell you when two of them overlap.

TAGS — read them before trusting a number:
  [measured]  caliper value carried over from hardware/voice-case (printed and fitted there)
  [user]      nominal given by the user, not yet checked against a print
  [photo]     estimated from photos (IMG_4057..4062). NOT a measurement — fit-check it
  [assumed]   no evidence at all; a typical value for the part
  [choice]    a design decision, free to change

FRAMES.
  World:      x across (+x right as you face the unit), y OUT of the wall (0 = wall), z up
              (0 = the amp box's bottom face).
  Box-local:  x across, y UP (0 = the box's bottom outer face), z INTO the box from the front
              outer face (z = 0). Every shell, lid, sled, tray and electronic part is authored
              in it; the shells also print in it (front face down).
"""

import math

try:
    from . import placement as _pl
except ImportError:                        # run directly, not as a package
    import placement as _pl

# ---- placement (owned by placement.py) ----
amp_x = _pl.amp_x
amp_lift = _pl.amp_lift
amp_setback = _pl.amp_setback
mp_x = _pl.mp_x
mp_dz = _pl.mp_dz
amp_psw_y = _pl.amp_psw_y
psw_dz = _pl.psw_dz
s3_x = _pl.s3_x
s3_z0 = _pl.s3_z0
dac_dx = _pl.dac_dx
dac_dz = _pl.dac_dz
btn_pos = tuple(_pl.btn_pos)
mic_pos = tuple(_pl.mic_pos)
sleeve_x = _pl.sleeve_x
sleeve_dz = _pl.sleeve_dz
PLACEMENT = ('amp_x', 'amp_lift', 'amp_setback', 'mp_x', 'mp_dz', 'amp_psw_y', 'psw_dz',
             's3_x', 's3_z0', 'dac_dx', 'dac_dz', 'btn_pos', 'mic_pos', 'sleeve_x',
             'sleeve_dz')

# ---- fit ----
clr = 0.4                  # global clearance for parts that locate precisely
wall = 3                   # shell walls

# =====================================================================================
# SHARED ENVELOPE
# =====================================================================================
# Width is set by the VOICE box: the 63 mm devkit lies across x in its tray, which needs
# 63 + 2 x 0.5 + 2 x 1.6 = 67.2 inside. The amp (60) then has 5 mm each side.
box_w = 76                 # [choice] outer width, both boxes
box_r = 4                  # [choice] vertical-edge radius
front_chamfer = 1.5        # [choice] 45 deg front edge; shells print front-face-down
lid_t = 4                  # [choice] rear lid plate

# Lid screws: M3 into heat-set inserts in short bosses on the TOP and BOTTOM walls at the rear
# rim. Bottom pair outboard of the MP1584 pocket, top pair inboard of the panel switch.
insert_m3_d = 4.0          # [measured]
insert_m3_h = 5.0          # [measured]
screw_clear = 3.4
lid_boss_od = 8
lid_boss_len = 10          # [choice]
lid_boss_x_top = 18        # [choice]
lid_boss_x_bot = 27        # [choice]

vent_w = 2.5               # [choice]
vent_pitch = 5.5           # [choice]

# =====================================================================================
# AMPLIFIER — ZK-502MT  (see params.scad for the long story on every number)
# =====================================================================================
# Component side UP, faceplate at the FRONT, connector edge at the REAR. Looking at the front,
# VOL is on the RIGHT (+x). Rear edge from +x to -x: AUX jack, small yellow part, 4-way
# barrier block, DC barrel.
amp_w = 60                 # [user] board width, along the faceplate
amp_l = 73                 # [user] PCB rear edge to the faceplate's FRONT face. CONFIRM
amp_env_h = 18             # [user] PCB underside to the highest point. CONFIRM
amp_tail_h = 2.5           # [assumed] through-hole tails under the PCB
amp_rear_over = 2.0        # [photo] barrel / AUX bodies past the rear edge
amp_face_w = 60            # [assumed] MEASURE
amp_face_h = 18            # [assumed] MEASURE
amp_face_t = 1.6           # [assumed] MEASURE
amp_face_y0 = -1.0         # [photo] faceplate bottom vs the PCB underside. MEASURE
amp_face_x = 0             # [assumed]
# Mounting holes: a RECTANGLE, board frame — x from the board centre (+ = VOL end), depth as
# the distance from the REAR edge. Hole-centre spacing measured on the real board: 52 across,
# 43 front to rear. The front pair is placed just behind the pots (checked against the board
# in Fusion); the rear pair follows from the 43.
amp_hole_dx = 26           # [measured] half the 52 spacing across
amp_hole_front = 57.5      # [fit-checked] front pair, from the rear edge
amp_hole_pitch = 43        # [measured] front pair to rear pair
amp_hole_rear = amp_hole_front - amp_hole_pitch
amp_holes = tuple((sx*amp_hole_dx, r) for r in (amp_hole_rear, amp_hole_front) for sx in (1, -1))
amp_screw_head = (5.5, 2.4)  # M3 pan head d, h — drawn on the board, kept clear of parts
amp_hole_pilot = 2.6
amp_standoff_od = 6.5
amp_standoff_h = 6         # [choice] tails + room for the 24 V tap wires
sled_t = 2                 # [choice]
# Sled hold-down: two M3 countersunk self-tappers up through the shell floor into bosses on the
# sled, in the plug zone either side of the MP1584 pocket (clear of the board, the DC plug and
# the 24 V tap wire). Without them the sled is only captive between the front wall and the lid.
sled_boss_od = 6           # [choice]
sled_boss_h = 4            # [choice] above the sled; its top stays under the plugs
sled_screw_pilot = 2.5     # M3 self-tapping into PLA/PETG
sled_screw_cs_d = 6.5      # M3 flat head (ISO 10642 head is 6.0) + clearance
amp_hs_clr = 8             # [choice] air over the heatsink
amp_hs = (-4, 32, 20, 20)  # [photo] heatsink [x, from rear, size x, size along the board]
# rear connectors, board frame
amp_dc_x = -23             # [photo]
amp_dc_axis = 6.0          # [assumed] above the PCB top. MEASURE
amp_dc_plug_d = 11         # [assumed]
amp_term_x = (-11, 16)     # [photo] barrier block span
amp_term_h = 10            # [assumed]
amp_term_screw_from_rear = 5   # [photo]
amp_aux_x = 22             # [photo]
amp_aux_axis = 3.0         # [assumed] MEASURE
plug_zone = 24             # [choice]

# ---- front ----
ctrl_mode = 'faceplate'    # [choice] 'faceplate' | 'holes'
face_lip = 1.5
face_rebate = 1.0
face_fit = 0.3
ctrl_pitch = 20            # [photo]
ctrl_x0 = 0                # [assumed]
ctrl_axis = 9              # [photo] above the PCB UNDERSIDE. MEASURE
ctrl_bush_d = 7            # [assumed]
ctrl_slack = 1.0
ctrl_led = (27, 5)         # [photo]
ctrl_led_d = 3.5
ctrl_shaft_proj = 15       # [photo]
knob_min_grip = 8          # [choice]

# ---- panel power switch on the +x side wall ----
amp_psw = True             # [choice]
amp_psw_shape = 'rect'     # 'rect' (KCD11-type rocker) | 'round' (toggle)
amp_psw_cut = (15, 10)     # [assumed] along z x along y. Check YOUR switch
amp_psw_round_d = 6.2      # [assumed]
amp_psw_body = (12, 14, 10)    # [assumed] behind the panel: depth in x, z, y

# ---- MP1584 ----
mp_w = 24                  # [user] along x (was 22 — the module is 24 long)
mp_l = 17                  # [user] along z
mp_h = 5                   # [assumed] tallest part above its PCB underside
mp_wall = 1.6
mp_lip = 5                  # [choice] wall above the sled; room over the board for soldered leads (was 2.5)

term_access = True         # [choice]
term_access_d = 6
term_pitch = 9             # [photo]

# =====================================================================================
# VOICE BOX
# =====================================================================================
voice_h = 48               # [choice] the dome alone sets it; the mic is on the TOP face (was 70)
s3_w = 63                  # [measured] ESP32-S3-DevKitC-1 length
s3_l = 28                  # [measured] ... width
s3_comp_h = 11             # [measured] headers + dressed wire above the PCB
s3_board_clr = 0.5         # [measured]
dac_w = 20                 # [measured]
dac_l = 33                 # [measured]
dac_jack_w = 6.0           # [measured]
dac_jack_h = 6.5           # voice-case value — MEASURE
dac_jack_overhang = 2.5
dac_jack_inset = 3.0       # [measured]
board_clr = 1.0            # [measured]
pcb_t = 1.6
pocket_wall = 1.6
board_pin_h = 2.0
tray_t = 2                 # [choice]
tray_seat = 2.5            # [choice]
tray_lip = 3.5             # [measured]
pin_row_w = 6              # [measured]
dac_aux_plug = 12          # [assumed] right-angle plug head past the socket face

# ---- pass-through sleeve ----
sleeve_id = 12             # [assumed] MEASURE your patch cable's plug heads
sleeve_wall = 1.6
sleeve_flange = 3
sleeve_engage = 3          # [choice] < peg_drop

# ---- dome button ----
btn_dome_d = 40            # [choice]
btn_dome_h = 8             # [choice]
btn_rim_lift = 2.0         # [choice]
btn_dome_seat = 1.0
btn_flange_d = 22          # [measured]
btn_flange_t = 3.0         # [choice]
btn_wall_od = 19.6         # [measured]
btn_guide_clr = 0.3        # [measured]
btn_recess_depth = 1.6     # [measured]
btn_face_gap = 1.6         # [measured]
btn_pilot_pitch = 30       # [measured]
btn_pilot_depth = 2.2
btn_wall_t = 1.2           # [measured]
btn_preload = 0.25         # [measured]
btn_lip_t = 1.0
btn_lip_over = 0.8
btn_lip_slack = 0.8
btn_slits = 8
btn_slit_w = 1.0
btn_slit_z0 = 3.5
btn_post_d = 2.0
bh_guide_h = 8.0           # [choice] voice-case had 5
bh_floor_t = 1.6
bh_guide_clr = 0.45
bh_wall = 1.6
bh_ear_d = 7
bh_fin_t = 3
bh_screw_clear = 2.2
bh_screw_cbore_d = 4.0
bh_screw_cbore_h = 1.2
bh_relief_eps = 0.01
bh_rib_embed = 0.3
board_screw_pilot = 1.6
sw_body = 11.0
sw_h = 8.0
sw_plunger_d = 3.0
sw_plunger_h = 1.8
sw_travel = 0.7
sw_pin_axis = 0
sw_pin_out = 1.0
sw_pin_slack = 1.5
sw_pin_gap = 5.0
sw_pin_win = 2.2
sw_pin_len = 3.5
sw_locate_clr = 0.4
sw_locate_t = 1.6
sw_locate_len = 5.0
sw_locate_len_pin = 1.8
sw_locate_h = 2.0

# ---- microphone ----
mic_board_w = 17           # [measured]
mic_board_l = 15           # [measured]
mic_seat_depth = 1.0
mic_gasket_d = 12
mic_gasket_depth = 0.8
mic_hole_d = 2.0
mic_post_pitch = 24
mic_post_od = 5
mic_post_h = 4
mic_clamp_w = 5
mic_clamp_t = 1.25
mic_clamp_pad = 10
mic_screw_clear = 2.4

# =====================================================================================
# WALL PLATE, LEGS, PEGS
# =====================================================================================
chan_d = 30                # [choice]
leg_w = 8
stack_gap = 6              # [choice] < peg_drop
plate_t = 6
plate_margin = 4
peg_neck_d = 4.5
peg_head_d = 8.0
peg_head_h = 1.5
kh_lip = 2.0
kh_clr = 0.4
peg_drop = 8
peg_y_amp = (10, 30)       # [choice]
peg_y_voice = (12, 34)     # [choice]
ws_d = 4.5
ws_head_d = 9
ws_x = 16
lock_gap = 3               # < peg_drop
header_h = 10
# The header block runs FORWARD to just short of the voice box's back (it sits between the legs,
# so nothing else is there), and the lock bracket rests on it over its whole depth. It used to be
# 14 deep, leaving the bracket cantilevered 21 mm over the channel.
header_gap = 0.5           # [choice] header front face to the voice lid's back
lock_t = 4
lock_screw_x = 14

# =====================================================================================
# ELECTRONICS — dummy-component sizes (new in the Fusion port)
# =====================================================================================
# These shape the parts you SEE and drag; the checks use them for overlaps. None of them is
# a measurement unless tagged so. Board-frame numbers for the amp are as above.
amp_pot_body = (10, 10, 11)    # [assumed] pot body behind the faceplate: x, z(depth), y
amp_pot_shaft_d = 6            # [assumed] knurled shaft
knob_d = 15                    # [assumed] the knobs you will fit
knob_h = 14                    # [assumed]
knob_gap = 1.0                 # [choice] knob skirt off the front face
amp_dc_body = (9, 13, 11)      # [assumed] PCB barrel jack: x, z(depth), height — <= 13 or it covers the rear-left screw
amp_aux_body = (6, 12, 5)      # [assumed] PCB 3.5 mm jack: x, z, height
amp_term_depth = 8             # [assumed] barrier block front-to-back
amp_sw_onboard = (8, 7, 6)     # [photo] the yellow part beside the AUX: x, z, height
# Its centre, board frame (x, from the rear edge). The photo estimates leave no room for it ON
# the rear edge — the barrier block ends at x 16 and the AUX body starts at 19 — so it is put
# just inboard of the AUX jack. Where it really is only matters for the switch leads.
amp_sw_onboard_at = (21, 22)   # [photo-guess] moved 4 fwd: the measured rear screw is at 14.5
amp_led_d = 3                  # [assumed]
dc_plug_len = 34               # [assumed] straight barrel plug incl. strain relief
dc_cable_d = 4.5               # [assumed]
aux_plug_d = 6                 # [assumed] right-angle plug head across its cable axis
aux_plug_barrel = 9            # [assumed] head length along the jack axis, past the face
patch_cable_d = 3.5            # [assumed]
lead_d = 2.0                   # [assumed] 5 V / 24 V tap / switch leads (22 AWG pair)
spk_cable_d = 5.0              # [assumed] two speaker pairs, bundled
mp_inductor = (7, 7, 4)        # [assumed] on the MP1584: x, z, height
mp_trim = (4, 4, 4)            # [assumed] the trim pot
psw_flange = (19, 13, 2.5)     # [assumed] rocker bezel outside the wall: z, y, x
s3_module = (25.5, 18, 3.2)    # [datasheet] ESP32-S3-WROOM-1: along x, along z, height
s3_usb = (7.4, 9, 3.3)         # [assumed] USB-C receptacle: along x (depth), z, height
s3_usb_pitch = 13              # [assumed] two USB-C on the end opposite the module
s3_hdr = (2.5, 8.5)            # [assumed] header row width (z) and plastic+pin height
s3_dupont_h = s3_comp_h        # dressed dupont housings + wire, up to the measured 11
dac_hdr_len = 16               # [assumed] 6-pin header along the DAC's front edge
mic_hdr = (8, 2.5, 8.5)        # [assumed] 6-pin header on the mic board: x, y, height (z)


# =====================================================================================
# DERIVED
# =====================================================================================
def inner_w():          return box_w - 2*wall
def amp_front_z():      return (wall - face_rebate if ctrl_mode == 'faceplate' else wall) + amp_setback
def amp_rear_z():       return amp_front_z() + amp_l
def plug_z0():          return amp_rear_z() + amp_rear_over
def box_d():            return plug_z0() + plug_zone
def amp_standoff_len(): return amp_standoff_h + amp_lift
def amp_pcb_y():        return wall + sled_t + amp_standoff_len()
def amp_pcb_top():      return amp_pcb_y() + pcb_t
def amp_env_top():      return amp_pcb_y() + amp_env_h
def amp_h():            return amp_env_top() + amp_hs_clr + wall
def amp_face_y():       return amp_pcb_y() + amp_face_y0
def amp_knob_proj():    return ctrl_shaft_proj - amp_front_z()
def amp_bz(from_rear):  return amp_rear_z() - from_rear
def mp_half_w():        return mp_w/2 + clr + mp_wall
def sled_screw_pts():
    """(x, z) of the two sled hold-down screws: left of the MP1584 pocket in front of the 24 V
    tap's crossing, right of it behind the AUX plug, midway to the lid boss notch"""
    notch_x0 = lid_boss_x_bot - lid_boss_od/2 - 0.6
    return [(mp_x - mp_half_w() - 0.75 - sled_boss_od/2, mp_zc() - 6),
            ((mp_x + mp_half_w() + notch_x0)/2, mp_zc() + 4)]
def plug_zc():          return (plug_z0() + box_d())/2
def mp_zc():            return plug_zc() + mp_dz
def psw_zc():           return plug_zc() + psw_dz
def sleeve_zc():        return plug_zc() + sleeve_dz
# world placement
def lid_back_y():       return plate_t + chan_d
def front_y():          return lid_back_y() + lid_t + box_d()
def voice_z0():         return amp_h() + stack_gap
def voice_top():        return voice_z0() + voice_h
def plate_h():          return voice_top() + lock_gap
def plate_w():          return box_w + 2*plate_margin
def peg_x():            return box_w/2 - leg_w/2


def lid_boss_pts(h):
    return [(-lid_boss_x_bot, wall + lid_boss_od/2 - 1),
            (lid_boss_x_bot, wall + lid_boss_od/2 - 1),
            (-lid_boss_x_top, h - wall - lid_boss_od/2 + 1),
            (lid_boss_x_top, h - wall - lid_boss_od/2 + 1)]


def lid_boss_taper():   return lid_boss_od + 1
def lid_boss_z0():      return box_d() - lid_boss_len - lid_boss_taper()
def amp_win_x0():       return amp_x + amp_dc_x - amp_dc_plug_d/2 - 1
def amp_win_x1():       return amp_x + amp_term_x[1] + 2
def amp_win_y0():       return amp_pcb_y()
def amp_win_y1():       return amp_pcb_top() + amp_term_h + 4
def face_c():           return (amp_x + amp_face_x, amp_face_y() + amp_face_h/2)


def term_xs():
    c = (amp_term_x[0] + amp_term_x[1])/2
    return [amp_x + c + (i - 1.5)*term_pitch for i in range(4)]


# ---- button ----
def btn_bore_d():       return btn_wall_od + 2*btn_guide_clr
def btn_recess_d():     return btn_flange_d + 2*clr
def btn_wall_id():      return btn_wall_od - 2*btn_wall_t
def btn_lip_od():       return btn_wall_od + 2*btn_lip_over
def bh_bore_d():        return btn_wall_od + 2*bh_guide_clr
def bh_relief_d():      return btn_lip_od() + 2*clr
def bh_collar_od():     return bh_relief_d() + 2*bh_wall
def btn_stroke():       return sw_travel - btn_preload
def bh_relief_h():      return btn_lip_t + btn_stroke() + btn_lip_slack
def sw_diag():          return math.sqrt(2)*sw_body
def sw_pin_a():         return sw_body/2 + sw_pin_out
def sw_pin_b():         return sw_pin_gap/2
def sw_pin_slot():      return 2*sw_pin_slack


def sw_pin_pos():
    return [(sa*sw_pin_a(), sb*sw_pin_b()) if sw_pin_axis == 0 else (sb*sw_pin_b(), sa*sw_pin_a())
            for sa in (-1, 1) for sb in (-1, 1)]


def sw_pin_win_xy():
    return (sw_pin_slot(), sw_pin_win) if sw_pin_axis == 0 else (sw_pin_win, sw_pin_slot())


def sw_locate_r0():     return sw_body/2 + sw_locate_clr
def sw_locate_r1():     return sw_locate_r0() + sw_locate_t
def bh_z0():            return wall
def bh_catch_z():       return bh_z0() + bh_guide_h
def bh_relief_z1():     return bh_catch_z() + bh_relief_h()
def bh_z1():            return bh_relief_z1() + bh_floor_t
def sw_pin_z1():        return bh_relief_z1() + sw_pin_len
def bh_deep_z():        return max(bh_z1(), sw_pin_z1())
def sw_body_h():        return sw_h - sw_plunger_h
def sw_top_z():         return bh_relief_z1() - sw_body_h()
def plunger_z():        return bh_relief_z1() - sw_h
def btn_face_bot_z():   return btn_recess_depth - btn_face_gap
def btn_flange_top_z(): return btn_face_bot_z() - btn_flange_t
def btn_ceil_z():       return btn_face_bot_z()
def btn_wall_z1():      return bh_catch_z() + btn_lip_t
def btn_post_h():       return plunger_z() + btn_preload - btn_ceil_z()
def btn_dome_base_z():  return btn_flange_top_z() + btn_dome_seat
def btn_rim_gap():      return -btn_dome_base_z()
def btn_dome_flat_r():  return btn_dome_d/2 - btn_rim_lift
def btn_tilt():         return (2*btn_guide_clr + 2*bh_guide_clr)/2/(wall + bh_guide_h)
def btn_edge_drop():    return btn_dome_flat_r()*btn_tilt() + btn_stroke()
def btn_proud():        return -btn_dome_base_z() + btn_rim_lift + btn_dome_h


def mic_size():         return (mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od))
def mic_board_top_z():  return wall - mic_seat_depth + pcb_t
def mic_clamp_pad_h():  return (wall + mic_post_h) - mic_board_top_z()
def mic_clamp_len():    return mic_post_pitch + mic_post_od


# ---- voice tray layout ----
def tray_top():         return wall + tray_t
def s3_cav():           return (s3_w + 2*s3_board_clr, s3_l + 2*s3_board_clr)
def s3_pocket():        return (s3_cav()[0] + 2*pocket_wall, s3_cav()[1] + 2*pocket_wall)
def s3_zc():            return s3_z0 + s3_pocket()[1]/2
def dac_cav():          return (dac_l + 2*board_clr, dac_w + 2*board_clr)
def dac_z0():           return s3_z0 + s3_pocket()[1] - pocket_wall + dac_dz
def dac_zc():           return dac_z0() + dac_cav()[1]/2 + pocket_wall
def dac_edge_z():       return dac_zc() + dac_w/2
def dac_socket_z():     return dac_edge_z() + dac_jack_overhang
def dac_xc():           return sleeve_x - (dac_l/2 - dac_jack_inset - dac_jack_w/2) + dac_dx
def dac_jack_x():       return dac_xc() + dac_l/2 - dac_jack_inset - dac_jack_w/2
def sleeve_od():        return sleeve_id + 2*sleeve_wall
def sleeve_len():       return tray_t + wall + stack_gap + sleeve_engage
def voice_h_min():      return btn_pos[1] + btn_dome_d/2 + front_chamfer + 2    # the dome, on the face


def top_face(h):
    """The voice box's TOP face as a frame: the front-face frame (x, y along the face, z = depth
    in from the outer face) turned onto the top. (a, b, d) -> (a, h - d, b), so the mic seat,
    posts, clamp and the INMP441 dummy are drawn exactly as they were on the front face and
    turned up there. A quarter turn — axis-aligned stays axis-aligned."""
    try:
        from . import xf
    except ImportError:
        import xf
    return xf.mul(xf.T(0, h, 0), xf.Rx(90))
def board_seat_y():     return tray_top() + tray_seat     # both boards' PCB underside


# ---- wall plate ----
def kh_slot_w():        return peg_neck_d + 2*kh_clr
def kh_head_d():        return peg_head_d + 2*kh_clr
def peg_len():          return kh_lip + kh_clr + (peg_head_d - peg_neck_d)/2 + peg_head_h


def peg_pts():
    return ([(sx*peg_x(), py) for sx in (-1, 1) for py in peg_y_amp]
            + [(sx*peg_x(), voice_z0() + py) for sx in (-1, 1) for py in peg_y_voice])


def header_w():         return 2*(peg_x() - leg_w/2 - 1)
def header_d():         return lid_back_y() - header_gap          # from the wall
def lock_screw_y():     return (plate_t + header_d())/2           # both screws, mid-block


def ws_pts():
    return [(sx*ws_x, y) for sx in (-1, 1) for y in (12, plate_h() - header_h - 12)]


def aabb_clear(p1, s1, p2, s2):
    return (abs(p1[0] - p2[0]) >= (s1[0] + s2[0])/2) or (abs(p1[1] - p2[1]) >= (s1[1] + s2[1])/2)


def scad_overrides():
    """{name: OpenSCAD literal} for every placement value — what the tests pass with -D."""
    out = {}
    for name in PLACEMENT:
        v = globals()[name]
        out[name] = ('[%s]' % ', '.join('%g' % c for c in v)) if isinstance(v, tuple) else '%g' % v
    return out
