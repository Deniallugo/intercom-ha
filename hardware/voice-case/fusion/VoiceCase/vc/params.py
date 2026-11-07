"""Voice S3 desk puck — parameters and derived dimensions (mm). No adsk imports, so
``checks.py`` runs in plain Python.

Same names and numbers as ``modules/params.scad``.

Axes: +y front, -y rear (USB), +x the audio side, z from the top face (0) down into
the box — the shell's print orientation.
"""

import math

# ---- fit ----
clr = 0.4                  # global clearance for inserted parts

# ---- shell envelope ----
wall = 3                   # walls, top face and base plate
radius = 12                # vertical corner radius; ~12.4 max before the register lip hits the bosses
chamfer = 5                # 45 deg top-edge chamfer (prints support-free top-down)
plan_x = 73                # floor: plan_x_min()
plan_y = 74                # floor: plan_y_min()
cavity_depth = 29          # floor: cavity_min(), set by the switch pins (13.75 mm down)

# ---- corner screws (M3 heat-set inserts: the plate is opened often) ----
boss_od = 8
insert_m3_d = 4.0          # heat-set insert bore
screw_clear = 3.4
screw_cbore_d = 6.2        # counterbore in the plate's outer face, so heads sit flush
screw_cbore_h = 1.6
boss_inset = 10            # sets s3_pos_x and so plan_x; min 9.6 (corner + register lip)

# ---- boards [measured] ----
s3_w = 63                  # devkit, long axis along y, USB-C at the rear
s3_l = 28                  # devkit across x
shared_wall = 2.0          # single wall between the devkit and DAC beds
# PCM5102A "LINE" board, long axis along y, socket edge facing +x. No mounting holes.
dac_w = 20                 # across x  [measured]
dac_l = 33                 # along y   [measured]
jack_cb_rim_margin = 0.1   # how far the socket counterbore may eat into the shell's bottom rim
# Measured on a printed plate: the socket sits 2 mm higher than the chain predicts.
# Applies to the shell's counterbore and plug hole only; 0 once dac_jack_h/axis are measured.
jack_z_rise = 2.0
# DAC sits component-side down, socket in a floor recess. Max 8.4 before the counterbore
# breaks the shell rim.
dac_seat_h = 7.0           # PCB seating plane above the plate
dac_lip = 4.0              # retains the PCB edge, shrouds the pin tails
mic_board_w = 17           # INMP441 breakout [measured]
mic_board_l = 15
pcb_t = 1.6
pocket_wall = 1.6          # friction-pocket wall
board_screw_pilot = 1.6    # M2 self-tap
screw_m2_d = 2.0           # for how far a part can float in its clearance holes
board_clr = 1.0            # DAC pocket, per side — loose, the socket locates the board
# Devkit slot, per side. Nothing else locates the devkit; slack moves the USB off its window.
#   won't go in -> +0.1     rocks side to side -> -0.1
s3_board_clr = 0.5

# ---- devkit retention: front tab preloads the board back against two rear stops ----
# Tab on the short edge (long edges carry headers). Assembly: tilt, front edge under the
# tab, rear drops behind the stops.
s3_rear_stops = True
s3_rear_stop_h = pcb_t     # max pcb_t, or the board is captured at both ends and can't go in
s3_front_gap = 1.0         # board front edge to cavity front face
s3_tab_cover = 0.8         # how much of the board's front edge the tab sits over
s3_tab_h = 1.0             # tab nib above its ramp
s3_tab_w = 10              # across x, narrow to stay between the header rows
# The tab's top is flush with s3_wall_top(); s3_tab_bite() reports where its ramp lands on
# the laminate (positive = preload). Move it with s3_lip or s3_tab_h.

# ---- pin relief: channels under the header rows so the board seats on its laminate ----
board_pin_h = 2.0          # solder-side pin tail protrusion [MEASURE]
pin_row_w = 6              # width of the relief strip along each long edge
pin_land = 4               # supported land left at each short end (DAC)
pin_relief_setback = 0.5   # floor land kept at the wall base
s3_relief_front_setback = pin_relief_setback   # devkit channels run the full board length
dac_relief_wall_gap = 3.0  # DAC channel stops short of the +x wall
# Width of both DAC floor cuts (relief and socket recess). Zero clearance on a 6 mm socket;
# 6.8 if it won't drop in.
dac_cut_w = 6
s3_seat_h = 3.5            # devkit pocket floor — sets the USB-C window height
s3_lip = 3.5               # pocket wall above the seated board
s3_comp_h = 11             # tallest devkit part: headers (~8.5) + wire [measured]

# ---- plan placements (x, y); DAC x derived in dac_cx(), devkit x in s3_pos_x() ----
s3_boss_margin = 0.8       # devkit pocket wall to -x boss
mic_pos = (0, 23)          # top face, front; 25.1 is the limit before the chamfer
btn_pos = (0, 0)           # top face, centred

# ---- rear wall (-y): one window over both devkit USB-C ports ----
usb_recept_h = 3.2         # receptacle height above the PCB [confirm]
s3_usb_ports = 2
s3_usb_port_w = 9.0        # one receptacle across [confirm]
s3_usb_gap = 2.0           # between the two
s3_usb_h = 10              # nominal window height before trims
s3_usb_trim_bottom = 2.0   # trims from the printed part; "bottom" = plate side (larger z)
s3_usb_trim_top = 2.0
usb_panel_t = 1.8          # thinned wall behind the window, so a USB-C plug reaches
usb_cb_margin = 2.0        # thinned patch beyond the window, each side

# ---- 3.5 mm line-out: the DAC's own socket, through a thinned +x wall ----
# The socket stays behind the outer skin so the plate can rise straight into the shell.
dac_jack_w = 6.0           # socket body width along its edge (y)  [measured]
dac_jack_h = 6.5           # socket body height above the PCB (z)
dac_jack_axis = 3.2        # barrel axis above the PCB — hole centre
dac_jack_overhang = 2.5    # socket body past the board edge
dac_jack_depth = 13.0      # socket reach inboard from that edge [MEASURE]
dac_jack_inset = 3.0       # board end edge to the socket [measured]; the hole follows it
dac_jack_end = +1          # socket end: -1 rear, +1 front
dac_pos_y_set = 0          # keep 0: each mm of offset costs 2 mm of plan_y
dac_socket_setback = 0.5   # socket face to the thinned panel
jack_panel_t = 1.2         # local wall thickness at the socket, so the plug seats
jack_hole_d = 5.0          # 5 + 2*jack_lead_in must stay inside the 6.8 counterbore
jack_lead_in = 0.6         # outer-face chamfer

# ---- button: TalkingPetDIY-style dome cap + holder, no return spring ----
# Cap is Ø22 because the switch's 15.6 mm diagonal stands inside the cap's bore.
btn_wall_od = 19.6         # cap body od; the rest chains off it
btn_guide_clr = 0.3        # per side, body in shell bore. 0.2 seized; more costs lean
btn_recess_depth = 1.6     # swallows the stroke, flange flush at rest
btn_pilot_pitch = 30       # 2x blind M2 pilots on ±x (+y is the mic)
btn_pilot_depth = 2.2      # must not break through the outer face

btn_cap_d = 22             # flange od
btn_flange_t = 1.5
btn_wall_t = 1.2           # also the snap skirt
btn_dome_r = 2.0           # top fillet
btn_dome_h = 6.5           # apex above the top face
btn_preload = 0.25         # post over-travel into the plunger: no rattle. < sw_travel/2
btn_face_gap = 1.6         # flange to recess floor at rest — must clear the stroke
btn_lip_t = 1.0
btn_lip_over = 0.8         # radial catch beyond the body od
btn_lip_slack = 0.8        # lip room in its relief AND body-to-collar-floor gap. 0.3 bottomed out
btn_slits = 8              # slits that let the lip collapse through the bore
btn_slit_w = 1.0
btn_slit_z0 = 3.5          # slits start below the top face, hidden under the flange
btn_post_d = 2.0           # central post, dome underside to plunger

# holder: a cup printed floor-down, switch standing inside the guide (keeps it 11.4 deep, not ~17.5)
bh_guide_h = 5.0           # guide bore below the top wall
bh_floor_t = 1.6           # collar floor under the switch
bh_guide_clr = 0.45        # per side; looser than the shell's (holder floats on two M2s)
bh_wall = 1.6
bh_ear_d = 7               # screw post od
bh_fin_t = 3               # web tying each post to the collar
bh_screw_clear = 2.2       # M2 clearance; tight, it bounds how far off axis the holder sits
bh_screw_cbore_d = 4.0     # head counterbore at the floor (M2x10)
bh_screw_cbore_h = 1.2
# The lip relief oversteps the floor by bh_relief_eps, so the ribs are sunk bh_rib_embed
# into it — otherwise they float and export as separate bodies. Checked.
bh_relief_eps = 0.01
bh_rib_embed = 0.3

# ---- 11 x 11 tactile switch, 4 pins [MEASURE] ----
sw_body = 11.0             # body footprint [measured]
sw_h = 8.0                 # height above the seat, pins excluded [measured]; sets the post length
sw_plunger_d = 3.0         # must exceed btn_post_d [MEASURE]
sw_plunger_h = 1.8         # only splits sw_h [MEASURE]
sw_travel = 0.7            # must exceed 2 * btn_preload [MEASURE]
# Two pins on each of two opposite sides. Windows are radial slots accepting a pin from
# flush with the body to 2.5 mm out.
sw_pin_axis = 0            # 0 = pins on ±x sides, 1 = ±y
sw_pin_out = 1.0           # nominal pin distance out from the side face
sw_pin_slack = 1.5         # slot length either side of that
sw_pin_gap = 5.0           # pin spacing on one side [measured]
sw_pin_win = 2.2           # slot width; shares 5 mm with a rib and clearance
sw_pin_len = 3.5           # pin length below the body [MEASURE]; sets the module's depth
# Four ribs beside the switch locate it at no cost in depth.
sw_locate_clr = 0.4        # per side. Raise if it won't drop in
sw_locate_t = 1.6          # rib thickness, radial
sw_locate_len = 5.0        # rib length, sides without pins
sw_locate_len_pin = 1.8    # rib length between a side's two pins
sw_locate_h = 2.0          # rib height off the floor

# ---- microphone: one short port, MEMS pressed onto a gasket ----
mic_seat_depth = 1.0       # board-locating recess
mic_gasket_d = 12
mic_gasket_depth = 0.8
mic_hole_d = 2.0
mic_post_pitch = 24        # 2x M2 posts flanking the seat
mic_post_od = 5
mic_post_h = 4
mic_clamp_w = 5            # clamp bar across the posts; its pad presses the board
mic_clamp_t = 1.25
mic_clamp_pad = 10         # pad, square
mic_screw_clear = 2.4      # M2 clearance in the clamp

# ---- base plate ----
reg_h = 2.0                # register lip into the shell cavity
reg_t = 1.2
# Vent slots (x, y, w, l) in otherwise-empty plate: beside the devkit and around the DAC.
vent_rects = [(-29.7, 0, 3.5, 46), (-23.7, 0, 3.5, 46),
              (17, -25, 10, 3.0), (17, 25, 10, 3.0)]
foot_positions = []        # no foot recesses: no room in a 3 mm plate. Checks validate any added
foot_d = 10
foot_depth = 0.6

# ---- devkit fit coupon: a slice of the bed's rear end (pin relief + width) ----
s3_fit_len = 25            # length of bed taken
s3_fit_skirt = 2           # plate beyond the bed, y only
s3_fit_base = 1.2          # thin plate under it


# ===== derived dimensions =====
# Half-dimensions are per axis on purpose: the case isn't square.

def outer_w():        return plan_x
def outer_h():        return plan_y
def top_depth():      return wall + cavity_depth
def outer_d():        return top_depth() + wall
def inner_half_x():   return plan_x/2 - wall
def inner_half_y():   return plan_y/2 - wall
def flat_half_x():    return plan_x/2 - chamfer     # flat top face after the chamfer
def flat_half_y():    return plan_y/2 - chamfer
def boss_cx():        return plan_x/2 - boss_inset  # corner boss / screw centres
def boss_cy():        return plan_y/2 - boss_inset

# register lip, inner and outer faces
def lip_inner_half_x(): return (plan_x - 2*wall - 2*clr)/2 - reg_t
def lip_inner_half_y(): return (plan_y - 2*wall - 2*clr)/2 - reg_t
def lip_outer_half_x(): return (plan_x - 2*wall - 2*clr)/2
def lip_outer_half_y(): return (plan_y - 2*wall - 2*clr)/2

def mic_size():
    return (mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od))

def boss_centres():
    return [(sx*boss_cx(), sy*boss_cy()) for sx in (-1, 1) for sy in (-1, 1)]

# ---- DAC x: back from where its socket must end up ----
def dac_pcb_edge_x():
    return outer_w()/2 - jack_panel_t - dac_socket_setback - dac_jack_overhang
def dac_cx():         return dac_pcb_edge_x() - dac_w/2
def dac_pos_y():      return dac_pos_y_set
def dac_pos():        return (dac_cx(), dac_pos_y())

# ---- devkit x: one shared wall inboard of the DAC ----
def s3_pocket_w():    return s3_l + 2*s3_board_clr + 2*pocket_wall
def s3_cavity_hw():   return s3_l/2 + s3_board_clr      # board cavity half-width
def s3_pos_x():       return dac_cx() - dac_w/2 - board_clr - shared_wall - s3_cavity_hw()

# Cavity faces either side of the shared wall (the pocket blocks overlap inside it).
def s3_cavity_x1():   return s3_pos_x() + s3_cavity_hw()
def dac_cavity_x0():  return dac_cx() - dac_w/2 - board_clr

def dac_pocket_x0():  return dac_cx() - dac_w/2 - board_clr - pocket_wall
def dac_pocket_x1():  return lip_inner_half_x()   # stops at the lip
def dac_pocket_c():   return ((dac_pocket_x0() + dac_pocket_x1())/2, dac_pos_y())
def dac_pocket_f():
    return (dac_pocket_x1() - dac_pocket_x0(), dac_l + 2*board_clr + 2*pocket_wall)
# Independent of plan_x (both ends reference the +x wall), so plan_x_min() isn't circular.
def dac_pocket_w():
    return (dac_w + board_clr + pocket_wall
            + jack_panel_t + dac_socket_setback + dac_jack_overhang
            - wall - clr - reg_t)

def dac_relief_w():   return dac_cut_w
def dac_recess_w():   return max(dac_cut_w, dac_jack_w)

# ---- devkit y: datum is the rear stops ----
def s3_usb_slop():    return 2*s3_board_clr + 1.0   # board play both ways + margin
def s3_usb_w():
    return s3_usb_ports*s3_usb_port_w + (s3_usb_ports - 1)*s3_usb_gap + s3_usb_slop()
def s3_rear_notch():  return s3_usb_w() + 2*clr     # gap between the rear stops
def s3_cy():          return -lip_inner_half_y() + s3_board_clr + s3_w/2
def s3_pos():         return (s3_pos_x(), s3_cy())
def s3_front_wall_t(): return lip_outer_half_y() - s3_cavity_y1()   # absorbs spare plan_y
def s3_pocket_y0():   return -lip_inner_half_y()
def s3_pocket_y1():   return lip_outer_half_y()
def s3_pocket_c():    return (s3_pos_x(), (s3_pocket_y0() + s3_pocket_y1())/2)
def s3_pocket_f():    return (s3_pocket_w(), s3_pocket_y1() - s3_pocket_y0())
# ---- tab z chain: from the cavity's front face, independent of plan_y ----
def s3_cavity_y1():   return s3_cy() + s3_w/2 + s3_front_gap
def s3_tab_over():    return s3_front_gap + s3_tab_cover
def s3_tab_top():     return s3_wall_top()
def s3_tab_z1():      return s3_tab_top() - s3_tab_h
def s3_tab_z0():      return s3_tab_z1() - s3_tab_over()
def s3_tab_bite():    return (s3_seat_h + pcb_t) - (s3_tab_z0() + s3_front_gap)   # <0 = clearance
def s3_wall_top():    return s3_seat_h + pcb_t + s3_lip
# USB receptacle setback from the outer face; a USB-C plug has ~6.5 mm of shell.
def usb_setback():    return usb_panel_t + (inner_half_y() + s3_cy() - s3_w/2)

# ---- button module z chain (case z) and diameters, outward from the cap body ----
def btn_bore_d():     return btn_wall_od + 2*btn_guide_clr    # 20.2 shell bore
def btn_recess_d():   return btn_cap_d + 2*clr                # 22.8 flange recess
def btn_wall_id():    return btn_wall_od - 2*btn_wall_t       # 17.2, must clear sw_diag()
def btn_lip_od():     return btn_wall_od + 2*btn_lip_over     # 21.2
def btn_top_d():      return btn_wall_od - 2*btn_dome_r       # 15.6 flat on top
def btn_flare_h():    return (btn_cap_d - btn_wall_od)/2      # 1.2, 45 deg so it prints dome-down

def bh_bore_d():      return btn_wall_od + 2*bh_guide_clr     # 20.5 guide bore
def bh_relief_d():    return btn_lip_od() + 2*clr             # 22.0 room for the lip
def bh_collar_od():   return bh_relief_d() + 2*bh_wall        # 25.2
def btn_stroke():     return sw_travel - btn_preload          # 0.45 felt press
def bh_relief_h():    return btn_lip_t + btn_stroke() + btn_lip_slack   # 2.25

def sw_diag():        return math.sqrt(2)*sw_body             # 15.56
def bh_pocket():      return sw_body + 2*clr                  # for collision checks
# Pin slots: `a` along the pinned axis, `b` across it.
def sw_pin_a():       return sw_body/2 + sw_pin_out           # 6.5
def sw_pin_b():       return sw_pin_gap/2                     # 2.5
def sw_pin_a_lo():    return sw_pin_a() - sw_pin_slack        # 5.0
def sw_pin_a_hi():    return sw_pin_a() + sw_pin_slack        # 8.0
def sw_pin_slot():    return 2*sw_pin_slack                   # 3.0

def sw_pin_pos():
    out = []
    for sa in (-1, 1):
        for sb in (-1, 1):
            out.append((sa*sw_pin_a(), sb*sw_pin_b()) if sw_pin_axis == 0
                       else (sb*sw_pin_b(), sa*sw_pin_a()))
    return out

def sw_pin_win_xy():
    return (sw_pin_slot(), sw_pin_win) if sw_pin_axis == 0 else (sw_pin_win, sw_pin_slot())

# Switch underside eaten by the slots, per axis.
def sw_win_span_a():
    return max(0.0, min(sw_pin_a_hi(), sw_body/2) - max(sw_pin_a_lo(), -sw_body/2))
def sw_win_span_b():
    return max(0.0, min(sw_pin_b() + sw_pin_win/2, sw_body/2)
                  - max(sw_pin_b() - sw_pin_win/2, -sw_body/2))
def sw_seat_area():
    return sw_body*sw_body - 4*sw_win_span_a()*sw_win_span_b()   # 115 of 121

# Rib envelope; sw_locate_max must clear the cap bore.
def sw_locate_r0():   return sw_body/2 + sw_locate_clr         # 5.9
def sw_locate_r1():   return sw_locate_r0() + sw_locate_t      # 7.5
def sw_locate_max():  return math.hypot(sw_locate_r1(), sw_locate_len/2)   # 7.91

def bh_z0():          return wall                              # collar top
def bh_catch_z():     return bh_z0() + bh_guide_h              # 8.0 cap lip lands here
def bh_relief_z1():   return bh_catch_z() + bh_relief_h()      # collar floor = switch base
def bh_z1():          return bh_relief_z1() + bh_floor_t       # floor's far face
def sw_pin_z1():      return bh_relief_z1() + sw_pin_len       # 13.75 pin tips
def bh_deep_z():      return max(bh_z1(), sw_pin_z1())         # 13.75 deepest point
def sw_body_h():      return sw_h - sw_plunger_h               # 6.2
def sw_top_z():       return bh_relief_z1() - sw_body_h()      # switch body top
def plunger_z():      return bh_relief_z1() - sw_h             # plunger top, free
# footprint for collision checks: posts set x, collar sets y
def bh_plate_w():     return btn_pilot_pitch + bh_ear_d        # 37
def bh_plate_l():     return bh_collar_od()                    # 25.2

def btn_face_bot_z():   return btn_recess_depth - btn_face_gap    # 0.0 flange flush at rest
def btn_flange_top_z(): return btn_face_bot_z() - btn_flange_t    # -1.5
def btn_flare_top_z():  return btn_flange_top_z() - btn_flare_h() # -2.7 body starts here
def btn_apex_z():       return -btn_dome_h                        # -6.5
def btn_ceil_z():       return btn_apex_z() + btn_wall_t          # -5.3 post root
def btn_proud():        return btn_dome_h                         # 6.5
def btn_wall_z1():      return bh_catch_z() + btn_lip_t           # 9.0 body far edge
def btn_post_tip_z():   return plunger_z() + btn_preload          # preloaded: no rattle
def btn_post_h():       return btn_post_tip_z() - btn_ceil_z()

# devkit column, down from the top face
def plate_inner_z():  return top_depth()
def s3_pcb_top_z():   return plate_inner_z() - s3_seat_h - pcb_t  # component side
def s3_top_z():       return s3_pcb_top_z() - s3_comp_h           # tallest devkit part
def s3_usb_cz():      return s3_pcb_top_z() - usb_recept_h/2
def s3_usb_z0():      return s3_usb_cz() - s3_usb_h/2 + s3_usb_trim_top      # top edge
def s3_usb_z1():      return s3_usb_cz() + s3_usb_h/2 - s3_usb_trim_bottom   # bottom edge
def s3_usb_h_eff():   return s3_usb_z1() - s3_usb_z0()
def s3_usb_cz_eff():  return (s3_usb_z0() + s3_usb_z1())/2

# ---- DAC z chain: component side down, socket in a floor recess ----
def dac_seat_z():     return plate_inner_z() - dac_seat_h    # PCB lower face
def dac_pcb_top_z():  return dac_seat_z() - pcb_t            # solder side, up
# Where the socket really sits (with jack_z_rise); the shell's cuts use these.
def dac_socket_z0():  return dac_seat_z() - jack_z_rise                # socket top
def dac_socket_z1():  return dac_seat_z() + dac_jack_h - jack_z_rise   # socket bottom
def dac_jack_cz():    return dac_seat_z() + dac_jack_h/2 - jack_z_rise
def dac_axis_z():     return dac_seat_z() + dac_jack_axis - jack_z_rise
def dac_top_z():      return dac_pcb_top_z() - board_pin_h   # pin tails
def dac_recess_x0():  return dac_pcb_edge_x() - dac_jack_depth - clr
def dac_recess_z1():  return dac_seat_z() + dac_jack_h + clr   # as printed, no rise
# Socket y = hole y; the socket sits in the board's corner.
def dac_jack_off():   return dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2)
def dac_jack_y():     return dac_pos_y() + dac_jack_off()

# mic clamp pad bridges from the post tops down to the board
def mic_board_top_z():  return wall - mic_seat_depth + pcb_t
def mic_clamp_pad_h():  return (wall + mic_post_h) - mic_board_top_z()
def mic_clamp_len():    return mic_post_pitch + mic_post_od

# ---- minimum case size ----
def plan_x_min():
    return (boss_inset + boss_od/2 + s3_boss_margin
            + pocket_wall + s3_l + 2*s3_board_clr      # devkit wall + cavity
            + shared_wall
            + board_clr + dac_w                        # DAC cavity
            + dac_jack_overhang + dac_socket_setback + jack_panel_t)

def plan_y_from_boss_dac():
    return 2*(abs(dac_pos_y()) + (dac_pocket_f()[1] + boss_od)/2 + boss_inset)
def plan_y_from_depth():   # written out: s3_pocket_f() depends on plan_y
    return 2*wall + 2*clr + 2*reg_t + s3_w + s3_board_clr + s3_front_gap
def plan_y_min():
    return max(plan_y_from_depth(), plan_y_from_boss_dac())

# Depth: the devkit's tallest part must clear the top face, the mic and the button pins.
def cavity_for(clearance_z):
    return clearance_z + s3_seat_h + pcb_t + s3_comp_h - wall
def cavity_from_bare():   return cavity_for(wall)
def cavity_from_mic():    return cavity_for(wall + mic_post_h + pcb_t + 2)
def cavity_from_button(): return cavity_for(bh_deep_z() + 2)
def cavity_min():
    return max(cavity_from_bare(), cavity_from_mic(), cavity_from_button())

# ---- button/mic coupon extents, derived from the features it contains ----
def coupon_w():
    return min(2*(max(abs(btn_pos[0]) + bh_plate_w()/2,
                      abs(mic_pos[0]) + mic_size()[0]/2) + 4), 2*flat_half_x())
def coupon_y0():  return max(btn_pos[1] - bh_plate_l()/2 - 4, -flat_half_y())
def coupon_y1():  return min(mic_pos[1] + mic_size()[1]/2 + 3, inner_half_y())


def aabb_clear(p1, s1, p2, s2):
    """do two centred AABBs (at p1/p2, sizes s1/s2) clear each other?"""
    return (abs(p1[0] - p2[0]) >= (s1[0] + s2[0])/2
            or abs(p1[1] - p2[1]) >= (s1[1] + s2[1])/2)
