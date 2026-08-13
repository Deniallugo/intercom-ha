"""Voice S3 desk puck — parameters and derived dimensions (no geometry, no adsk).

A 1:1 port of ``modules/params.scad``. Same names, same numbers, same units (mm).
Everything that was a ``function`` in OpenSCAD is a function here too, so editing a
parameter and re-running re-derives the whole chain instead of leaving a stale copy.

This module imports nothing from Fusion on purpose: ``checks.py`` runs against it with
plain CPython (``./test.sh``), which is how the design asserts stay runnable without
either OpenSCAD or Fusion open.

The full design archaeology — WHY each number is what it is, and what it used to be —
lives in ``../../../modules/params.scad`` and ``../../../README.md``. Kept here: the
operative constraint for each parameter, i.e. what breaks if you move it.

Axes. +y is the FRONT (toward you), -y the REAR (the USB cable leaves there), +x the
side the audio leaves, and z runs from the TOP face (z = 0) DOWN into the box. That is
the OpenSCAD frame, kept unchanged so every number below reads the same as it did — it
also means the shell is modelled in its print orientation, top face on the XY plane.
"""

import math

# ---- fit ----
clr = 0.4                  # global clearance for inserted parts

# ---- shell envelope ----
wall = 3                   # walls, top face and base plate
# Capped at ~12.4 by the base plate's REGISTER LIP, not by the wall: boss and lip share
# the corner arc's centre, so growing this walks the lip inward past a fixed boss.
radius = 12                # rounded vertical corners
chamfer = 5                # 45 deg top-edge chamfer (prints support-free top-down)
# Not square, and not a style choice: each axis has its own floor. plan_x is one chain
# read inward from the +x wall (socket -> DAC -> shared wall -> devkit -> corner bosses);
# plan_y is the 65 mm devkit between two register lips. See plan_x_min() / plan_y_min().
plan_x = 73                # across x — the two beds side by side, sharing one wall
plan_y = 74                # along y — the devkit's length, and nothing else
# Floored by cavity_min(). What sets it is not the devkit (16.1) but the four SWITCH PINS
# hanging through the button holder's floor, whose tips reach 13.75 mm down.
cavity_depth = 29

# ---- corner screws (M3 heat-set inserts) ----
# Inserts, not self-tap: the base plate is the only access to every solder joint in the
# box, so this joint gets opened repeatedly.
boss_od = 8
insert_m3_d = 4.0          # heat-set insert bore
screw_clear = 3.4
screw_cbore_d = 6.2        # counterbore in the base plate's OUTER face, so no screw
screw_cbore_h = 1.6        # head stands proud to scratch the desk
# THIS NUMBER SETS s3_pos_x, and through it the whole footprint: the devkit pocket is
# parked against the -x pair. Floor is 9.6 (boss inside both the rounded corner and the
# register lip passing through it) — 10 leaves 0.4 mm.
boss_inset = 10

# ---- boards [measured off the actual boards] ----
# MEASURED, both of them, and it took several goes at each — every wrong value was a number
# DERIVED from something rather than put a caliper across. s3_l went 30 -> 26 (back-solved from
# "the pocket can be 4 mm narrower", which does not imply an equally narrower board) -> 25 ("a mm
# narrower than it should be", read as the board when it meant the SPACE) -> 28. s3_w went
# 67 -> 65 -> 63. Each axis of this case is one of these plus fixed overheads, so an error in
# either goes straight into the footprint with nowhere to hide.
s3_w = 63                  # ESP32-S3 devkit, LONG AXIS ALONG Y, USB-C end at the rear
s3_l = 28                  # ...and across x
# ONE wall between the two beds. Each pocket still draws its own pocket_wall on that side
# and the two overlap, so the union comes out as a single rib of exactly this thickness.
# It replaced 1.6 + 3 + 1.6 and that 4.2 mm is what took plan_x from 76 to 72.
shared_wall = 2.0
# PCM5102A "LINE" breakout. Turned 90 deg: LONG AXIS ALONG Y, socket edge facing +x. No
# mounting holes anywhere on it, so it sits in a friction pocket like the devkit.
dac_w = 20                 # board size across x (its SHORT dimension)  [measured]
dac_l = 33                 # board size along y (its LONG dimension)    [measured]
# How much of the shell's bottom RIM the socket counterbore may eat into. Spending it is
# what lets the DAC pocket floor come down to 7.
jack_cb_rim_margin = 0.1
# MEASURED CORRECTION from the printed plate: the derived chain puts the socket 3 mm
# lower than where the board actually ends up. Applied to the SHELL's counterbore and
# plug hole only. If dac_jack_h / dac_jack_axis ever get measured properly, this is 0.
jack_z_rise = 2.0
# The board sits component-side DOWN, so the socket hangs BELOW the PCB into a recess in
# this floor — the only way to get the jack hole near the base plate. What binds is the
# counterbore not breaking the base rim; 8.4 is the limit, this is frozen as printed.
dac_seat_h = 7.0           # PCB seating plane above the plate
dac_lip = 4.0              # retains the PCB edge and shrouds the pin tails (pointing UP)
mic_board_w = 17           # INMP441 breakout [measured]
mic_board_l = 15
pcb_t = 1.6
pocket_wall = 1.6          # friction-pocket wall (boards without usable mount holes)
board_screw_pilot = 1.6    # M2 self-tap
screw_m2_d = 2.0           # the screw itself — only used to work out how far a part can
                           # float in its own clearance holes
# PER-SIDE pocket clearance, deliberately looser than `clr`. The DAC keeps it: it is
# located by its socket sitting in a zero-clearance floor recess, so slack never shows.
board_clr = 1.0
# The DEVKIT does not, because nothing else locates that board and its slack lands on the
# USB-C window.
#
# 0.5 per side. Every printed data point behind the earlier values turned out to be measuring
# s3_l rather than this: 0.4 "came out smaller than the board" and 1.0 "rattled" were taken when
# s3_l said 30 against a real 28 mm board, and "almost impossible to fit" at 0.6 was taken when it
# said 26 — a 27.2 mm cavity on a 28 mm board, i.e. 0.8 mm of interference. None of them says
# anything about this number.
#
# With s3_l measured, 1.0 was simply generous and 1 mm came back out of the total. Nothing is lost
# to what is left: the board's y is set by the rear stops and the tab, and its x play feeds
# s3_usb_slop(), which is derived from this.
#   will not go in -> raise 0.1     rocks side to side -> lower 0.1
s3_board_clr = 0.5

# ---- devkit retention: the pocket is a SLOT, not a tray ----
# Front wall = the register lip grown to pocket height; rear stops on the lip's own
# footprint flanking a USB notch; a tab over the front edge preloading the board BACK
# against those stops. The tab is on the SHORT edge because the long edges carry header
# rows. Assembly is a tilt: front edge under the tab, rear drops behind the stops.
s3_rear_stops = True
# Capped at the PCB's own thickness, and that cap is the assembly story: taller and the
# board is captured in z at both ends before it is in.
s3_rear_stop_h = pcb_t
# The board's y clearance at the FRONT, between its nominal front edge and the cavity's front
# face. Explicit now: the cavity used to be cut to exactly the board's edge, so all of the y play
# was the s3_board_clr behind it — 0.5 mm total against 1.0 in x, and the printed pocket came out
# too short. 1.0 here makes it 1.5 total, and being its own number means the tab's reach and ramp
# track it instead of quietly assuming the cavity ends at the board.
s3_front_gap = 1.0
s3_tab_cover = 0.8         # how much of the board's front edge the tab sits over
# How far the tab continues above its ramp. It used to run all the way to the top of the pocket
# wall, which made it a 4 mm block hanging over the board for no reason — the ramp is the part
# that does the work and the rest was material. 1.0 leaves a small nib at the ramp's top.
s3_tab_h = 1.0
s3_tab_w = 10              # across x, centred — narrow, to stay between the header rows
# How far the tab's ramp reaches BELOW the board's top face, at the board's own edge. SIGNED:
# positive bites into the laminate and preloads the board, negative leaves a clearance above it.
#
# The tab's z is anchored to the TOP OF THE WALL, not to the board: its top face is flush with
# s3_wall_top() and the ramp hangs below from there. So there is no bite input any more —
# s3_tab_bite() is derived, and reports how the tab happens to fall relative to the laminate.
# Raise or lower it by moving s3_lip or s3_tab_h, which is what it is anchored to.

# ---- pin relief: why the pocket floors are not flat ----
# Soldered headers leave pin TAILS through the solder side. On a flat floor the board
# rests on those tails ~2 mm proud, and a lip sized for a flat-seated board then grips
# the gap UNDER the board. Two strips sunk under the header rows fix it.
board_pin_h = 2.0          # solder-side pin tail protrusion [MEASURE]
pin_row_w = 6              # width of the relief strip along each long edge
pin_land = 4               # supported land left at each short end
# Keeps a land of full-height floor at the wall base — flush strips undercut the pocket wall and
# its exposed height grows by the relief depth.
#
# 0.5, down from 1.2, because at 1.2 the relief was missing the pins it exists for. The claim that
# a header row sits ~2.5 mm in from the board edge was too generous for this devkit. At 0.5, with
# s3_board_clr at 1.0, the strip's outer edge runs 0.5 mm PAST the board's edge, so the whole
# outer 5.5 mm of the underside is relieved and no tail can find floor.
pin_relief_setback = 0.5
# The devkit's channels run the board's WHOLE length: off the open rear end, and up to
# pin_relief_setback short of the front wall. They were pinned to 57 of the 63 mm board with a
# pin_land at each end, which left the board's tails landing on floor at both ends — the exact
# failure the relief exists to prevent. There is no need for end lands: the strips are along the
# +-x edges, so the board still seats on a 16 mm central land running the full length.
s3_relief_front_setback = pin_relief_setback
# The DAC channel stops SHORT of the +x wall: it is the jack's access and wants a land
# there, not an open end.
dac_relief_wall_gap = 3.0
# ONE width for both cuts in the DAC floor (relief channel and socket recess). With a
# 6 mm socket the recess is ZERO clearance — if the socket will not seat, 6.8 is the
# number that makes it drop in freely.
dac_cut_w = 6
s3_seat_h = 3.5            # pocket floor under the devkit — sets the USB-C window height
s3_lip = 3.5               # pocket wall standing above the seated board
s3_comp_h = 11             # tallest thing on the devkit's component side: soldered 2.54
                           # headers (~8.5) plus dressed wire [measured]

# plan placements (x, y). The DAC's x is DERIVED — see dac_cx(); the devkit's hangs off
# it one shared wall inboard, see s3_pos_x().
s3_boss_margin = 0.8       # pocket wall to boss, in x — the slack end of the chain
mic_pos = (0, 23)          # top face, front edge — centred in x, on the button's axis.
                           # 25.1 is the hard limit before it runs onto the chamfer.
btn_pos = (0, 0)           # top face, centred

# ---- rear wall (-y): devkit USB-C ----
# ONE window over the devkit's own two USB-C receptacles — power AND flashing AND the
# serial log. Derived from the port count, because a narrow window straddles the gap
# between the two and fully exposes NEITHER.
usb_recept_h = 3.2         # receptacle height above the PCB [confirm]
s3_usb_ports = 2           # the DevKitC-1 has two
s3_usb_port_w = 9.0        # one USB-C receptacle across [confirm]
s3_usb_gap = 2.0           # between the two
# Extra window width, to absorb the board's play in its pocket — DERIVED from that play, down in
# the derived section, rather than a constant that has to be remembered separately every time
# s3_board_clr moves. Too small and the board drifts until a port hides behind the wall; too large
# and it eats the notch the rear stops need.
s3_usb_h = 10              # nominal window height (z) before the trims below
# Trimmed ASYMMETRICALLY from the printed part. z runs down from the top face, so
# "bottom" (the base plate side) is the LARGER z edge.
s3_usb_trim_bottom = 2.0
s3_usb_trim_top = 2.0
# LOCAL wall thickness behind the window, same trick as the jack's panel: a plug has a
# fixed amount of shell before its overmold. Without it the setback is 5.8 of a 6.5 limit.
usb_panel_t = 1.8
usb_cb_margin = 2.0        # how far the thinned patch extends past the window each side

# ---- 3.5 mm line-out: the DAC's OWN socket, through the +x side wall ----
# No panel-mount jack and no flying analog pair. It exits the +x SIDE wall because
# reaching the rear wall would need |x| <= 12.5, which is spent on the USB cutout.
# The wall is locally THINNED behind it (a 3.5 mm plug needs nearly all of ~14 mm of
# barrel in), and the socket stays entirely BEHIND the outer skin so the plate can rise
# straight up into the shell at assembly.
dac_jack_w = 6.0           # socket body width along its edge (y)  [measured]
dac_jack_h = 6.5           # socket body height above the PCB face (z)
dac_jack_axis = 3.2        # barrel AXIS above the PCB face — sets the hole centre
dac_jack_overhang = 2.5    # how far the socket body sticks past that long edge
dac_jack_depth = 13.0      # how far the socket reaches INBOARD from that edge [MEASURE]
# The socket is NOT centred on its edge — it sits in the board's corner. The HOLE absorbs
# that offset (dac_jack_y()), because the board's y is spent clearing the corner bosses.
dac_jack_inset = 3.0       # board END edge to the near side of the socket [measured]
dac_jack_end = +1          # which end the socket sits at: -1 = rear (-y), +1 = front
# CENTRED in y, and not cosmetically: the pocket is 38.2 deep and has to pass between the
# +-y bosses, so every millimetre of offset costs two of plan_y.
dac_pos_y_set = 0
dac_socket_setback = 0.5   # socket face to the thinned panel's inner surface
jack_panel_t = 1.2         # LOCAL wall thickness at the socket
# Bounded ABOVE by the counterbore behind it: 5 + 2*0.6 of chamfer must stay inside a
# 6.8 wide counterbore, or the panel around the hole vanishes.
jack_hole_d = 5.0
jack_lead_in = 0.6         # outer-face chamfer so a plug can't ride the cut edge

# ---- button: a scaled TalkingPetDIY dome, in two printed parts ----
# Shape taken from the 61.4 mm TalkingPetDIY pet button and held to its ratios: wide
# flange, straight body stepped in from it, and a top that is one large FILLET.
# THE FLANGE IS 22, and the 11 mm switch did it: an 11 mm square body has a 15.6 mm
# DIAGONAL and it stands up INSIDE the cap's own bore, so the bore has to swallow it.
# There is NO return spring — the switch has real travel of its own, and btn_preload
# is what replaces the coil spring's anti-rattle job.
# shell side — a bore, a recess, two blind pilots, nothing else
btn_wall_od = 19.6         # cap BODY od. Everything else chains off this one number.
# PER SIDE, body in the shell bore — a sliding journal, and the only thing stopping the
# cap rocking. 0.2 seized the printed cap; 0.3 costs lean (0.69 -> 1.03 of a 1.2 limit).
btn_guide_clr = 0.3
btn_recess_depth = 1.6     # deep enough to swallow the whole stroke, flange flush at rest
btn_pilot_pitch = 30       # 2x BLIND M2 pilots, on +-x: +y belongs to the mic
btn_pilot_depth = 2.2      # blind: must not reach the outer face

# cap
btn_cap_d = 22             # FLANGE od — the diameter you actually see
btn_flange_t = 1.5
btn_wall_t = 1.2           # also the snap: this wall IS the skirt, and it flexes
                           # btn_lip_over to get the lip through the shell bore
btn_dome_r = 2.0           # the whole top is this one fillet, as on the reference
btn_dome_h = 6.5           # apex above the top OUTER face
# PRELOAD: the post is deliberately LONG, so with the cap's lip against the catch the
# switch has been pushed this far past its free position. That is what pins the cap to
# the lip and kills the rattle. Comfortably under sw_travel, or the switch sits closed.
btn_preload = 0.25
btn_face_gap = 1.6         # flange to the recess floor at rest — must clear the stroke
btn_lip_t = 1.0
btn_lip_over = 0.8         # radial catch beyond the body od
# Simultaneously the room under the lip in its relief AND the gap between the cap body's
# far edge and the collar floor. At 0.3 the printed cap bottomed out with no travel.
btn_lip_slack = 0.8
btn_slits = 8              # radial slits so the lip can collapse through the shell bore
btn_slit_w = 1.0
btn_slit_z0 = 3.5          # case z where the slits START — below the top face, so the
                           # only way to see one is to look up under the flange
btn_post_d = 2.0           # central post, dome underside down to the plunger

# holder — a CUP, not a plate: guide bore, catch, lip relief and switch all inside one
# collar, printing FLOOR-DOWN. Standing the switch inside the guide rather than below it
# is what keeps the module 11.4 mm deep instead of ~17.5 (which reaches into the devkit).
bh_guide_h = 5.0           # guide bore below the top wall — the far half of the journal
bh_floor_t = 1.6           # collar floor, under the switch
bh_guide_clr = 0.45        # PER SIDE in the HOLDER's bore. Looser than the shell's 0.3 on
                           # purpose: the holder is located by two M2s in clearance holes,
                           # so a bore as tight as the shell's would pinch off axis.
bh_wall = 1.6
bh_ear_d = 7               # screw POST od. Full height, not a tab on a gusset — the part
                           # prints floor-down, so a post is just another vertical wall.
bh_fin_t = 3               # web tying each post back into the collar
bh_screw_clear = 2.2       # M2 clearance up the posts. Tighter than usual — with no
                           # spigot these two holes bound how far off axis it can sit.
bh_screw_cbore_d = 4.0     # head counterbore at the floor: a proud M2 head here would
bh_screw_cbore_h = 1.2     # eat the gap to the devkit. Takes M2x10.

# ---- 11 x 11 tactile switch, 4 pins [MEASURE — these place the whole mechanism] ----
# Big enough to have a usable spring and stroke of its own (so the coil spring came out)
# and its 15.6 mm diagonal is what took the cap to 22. The four pins go straight DOWN
# through the collar floor and are soldered below it, inside the case.
sw_body = 11.0             # body footprint, square [measured]
sw_h = 8.0                 # total height above the seat, EXCLUDING pins [measured].
                           # ONE number on purpose: it is the only thing the cap's post
                           # length depends on, so a wrong plunger guess cannot reach it.
sw_plunger_d = 3.0         # the pin on top [MEASURE — must exceed btn_post_d]
sw_plunger_h = 1.8         # how far it stands proud of the body [MEASURE — split only]
sw_travel = 0.7            # actuation travel [MEASURE — must exceed btn_preload]
# The pin field. Two pins on each of two OPPOSITE SIDES, standing OUTBOARD of the body.
# How far out is the dimension this design kept getting wrong, so each window is a radial
# SLOT covering a RANGE of it rather than a position: as drawn it accepts a pin anywhere
# from flush with the side face to 2.5 mm out.
sw_pin_axis = 0            # 0 = pins on the +-x sides, 1 = +-y (the body is square)
sw_pin_out = 1.0           # nominal: how far a pin stands OUT from the side face
sw_pin_slack = 1.5         # the slot runs this far either side of that
sw_pin_gap = 5.0           # the two pins on one side, apart [measured]
# 2.2, not 2.8: slot + locating rib + clearance have to share the 5 mm between a side's
# two pins. Across the pins is the direction we actually measured.
sw_pin_win = 2.2           # window WIDTH, across the pinned axis
sw_pin_len = 3.5           # how far the pins reach below the body [MEASURE] — this, not
                           # bh_z1(), is what sets the module's real depth
# ---- locating the switch: four ribs, not a pocket ----
# A pocket costs depth 1:1 (the switch's base sets where its plunger ends up); these cost
# NONE, standing BESIDE the body at the midpoint of each edge, in the 3.1 mm between the
# switch and the cap's bore. Two lengths: on the two sides that have pins the rib has to
# fit BETWEEN that side's pair, or it prints in mid-air over a window.
sw_locate_clr = 0.4        # per side, switch inside the ribs. Raise if it will not drop in
sw_locate_t = 1.6          # rib thickness, radial
sw_locate_len = 5.0        # rib length, on the two sides with no pins
sw_locate_len_pin = 1.8    # rib length, on the two sides that have pins — between them
sw_locate_h = 2.0          # how far the ribs stand off the floor

# ---- microphone (INMP441, top face, gasket-sealed single port) ----
# ONE short hole with the MEMS port pressed to a gasket. A multi-hole cluster through a
# 3 mm wall is a Helmholtz resonator sitting on top of speech.
mic_seat_depth = 1.0       # board-locating recess in the inner face
mic_gasket_d = 12
mic_gasket_depth = 0.8
mic_hole_d = 2.0           # single port, as short as the wall allows
mic_post_pitch = 24        # 2x M2 posts FLANKING the seat — the board lies on its own
mic_post_od = 5            # gasket, so nothing can be underneath it
mic_post_h = 4
# ...so the board is not screwed down, it is CLAMPED: a bar spans both posts and a pad in
# its middle presses the board's centre, right opposite the MEMS port.
mic_clamp_w = 5            # narrow bar; the pad does the pressing
mic_clamp_t = 1.25         # only has to hold gasket compression
mic_clamp_pad = 10         # central pressing pad (square)
mic_screw_clear = 2.4      # M2 clearance in the clamp

# ---- base plate: registration lip, vents, feet ----
reg_h = 2.0                # lip nesting into the shell cavity (alignment + light gap)
reg_t = 1.2

# The box is otherwise closed and an S3 at 240 MHz with PSRAM is not cold. The vents face
# the desk, so they are invisible, and they sit in space the layout already had to leave
# empty: the -x strip beside the devkit (the only part in here that gets warm), and two
# bays fore and aft of the DAC pocket. Slots as (x, y, w, l).
vent_rects = [(-29.7, 0, 3.5, 46), (-23.7, 0, 3.5, 46),
              (17, -25, 10, 3.0), (17, 25, 10, 3.0)]
# NO foot recesses: there is no clean set of four positions left, and a 0.6 recess on the
# outer face under a 2.5 pocket floor on the inner one does not fit in a 3 mm plate.
# Populate this to bring them back; the checks will tell you if the positions collide.
foot_positions = []
foot_d = 10
foot_depth = 0.6

# ---- fit-test coupons (were in voice-case.scad) ----
# A slice off the devkit bed's REAR end. It has been all three sizes: a front slice (width and the
# tab), then the WHOLE bed once the rear stops went in, on the argument that the board now goes in
# tilted between two features 63 mm apart. True, but that made it 10 cm3 — a third of the plate —
# to answer questions that mostly live at one end. The rear is where the two things in doubt are:
# the PIN RELIEF channels and the pocket WIDTH. Raise s3_fit_len to get the tilt rehearsal back.
#
# x is the pocket exactly, with no skirt (the vent slots run within half a millimetre of the
# pocket walls, so a skirt would slice a channel down the coupon's own edges); y takes a small
# skirt at the rear, where the nearest thing outboard is plain plate.
s3_fit_len = 25            # how much of the bed to take, at whichever end
s3_fit_skirt = 2           # plate left beyond the bed, y only
s3_fit_base = 1.2          # plate thickness kept under it — the bed is what is on test


# ===== derived dimensions =====
# Every half-dimension is PER AXIS and deliberately not wrapped in something that picks an
# axis for you: the reason the case could stop being square is that each has a different
# value on each axis, and a call site that does not say which one it means is a bug.

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

# inner edge of the base plate's registration lip — the real inboard bound for anything
# standing on the plate — and its outer face, which the devkit pocket's front wall and
# its rear stops run out to.
def lip_inner_half_x(): return (plan_x - 2*wall - 2*clr)/2 - reg_t
def lip_inner_half_y(): return (plan_y - 2*wall - 2*clr)/2 - reg_t
def lip_outer_half_x(): return (plan_x - 2*wall - 2*clr)/2
def lip_outer_half_y(): return (plan_y - 2*wall - 2*clr)/2

def mic_size():
    return (mic_post_pitch + mic_post_od, max(mic_board_l + 2*clr, mic_post_od))

def boss_centres():
    return [(sx*boss_cx(), sy*boss_cy()) for sx in (-1, 1) for sy in (-1, 1)]

# ---- DAC: position derived BACKWARDS from where its socket has to end up ----
def dac_pcb_edge_x():
    return outer_w()/2 - jack_panel_t - dac_socket_setback - dac_jack_overhang
def dac_cx():         return dac_pcb_edge_x() - dac_w/2
def dac_pos_y():      return dac_pos_y_set
def dac_pos():        return (dac_cx(), dac_pos_y())

# ---- devkit x: hangs off the DAC, one shared wall inboard of its cavity ----
# The DAC is the fixed end of the chain because its socket has to reach the +x wall, so
# plan_x is whatever leaves the devkit's outer wall clear of the -x bosses (plan_x_min).
def s3_pocket_w():    return s3_l + 2*s3_board_clr + 2*pocket_wall
def s3_cavity_hw():   return s3_l/2 + s3_board_clr      # board cavity half-width
def s3_pos_x():       return dac_cx() - dac_w/2 - board_clr - shared_wall - s3_cavity_hw()

# The two CAVITY faces the shared wall stands between. Collision checks between the
# pockets have to use these rather than the pocket blocks: the blocks deliberately
# overlap inside the shared wall.
def s3_cavity_x1():   return s3_pos_x() + s3_cavity_hw()
def dac_cavity_x0():  return dac_cx() - dac_w/2 - board_clr

def dac_pocket_x0():  return dac_cx() - dac_w/2 - board_clr - pocket_wall
def dac_pocket_x1():  return lip_inner_half_x()   # stops at the lip, not the shell wall
def dac_pocket_c():   return ((dac_pocket_x0() + dac_pocket_x1())/2, dac_pos_y())
def dac_pocket_f():
    return (dac_pocket_x1() - dac_pocket_x0(), dac_l + 2*board_clr + 2*pocket_wall)
# The DAC pocket's x-SIZE is independent of plan_x — both ends are referenced to the +x
# wall — which is what makes plan_x_min() non-circular.
def dac_pocket_w():
    return (dac_w + board_clr + pocket_wall
            + jack_panel_t + dac_socket_setback + dac_jack_overhang
            - wall - clr - reg_t)

def dac_relief_w():   return dac_cut_w
def dac_recess_w():   return max(dac_cut_w, dac_jack_w)

# ---- devkit: the y datum is the plate's rear stops, not the shell wall ----
# The board can shift s3_board_clr either way, so the window needs twice that plus a margin.
def s3_usb_slop():    return 2*s3_board_clr + 1.0
def s3_usb_w():
    return s3_usb_ports*s3_usb_port_w + (s3_usb_ports - 1)*s3_usb_gap + s3_usb_slop()
# The notch between the two rear stops. Wider than the window by clr each side: anything
# narrower and the stops do what the deleted rear wall used to do.
def s3_rear_notch():  return s3_usb_w() + 2*clr
# Board rear edge against the stops (which sit on the lip's footprint).
def s3_cy():          return -lip_inner_half_y() + s3_board_clr + s3_w/2
def s3_pos():         return (s3_pos_x(), s3_cy())
# The FRONT WALL's thickness: whatever depth plan_y has that the board and its rear clearance did
# not use, all of it landing here. It grows with plan_y and nothing downstream cares — which used
# to be untrue. This fed the tab's z chain, so spare depth in plan_y pushed the ramp down until it
# reached the pocket floor and the part stopped being buildable.
def s3_front_wall_t(): return lip_outer_half_y() - s3_cavity_y1()
def s3_pocket_y0():   return -lip_inner_half_y()
def s3_pocket_y1():   return lip_outer_half_y()
def s3_pocket_c():    return (s3_pos_x(), (s3_pocket_y0() + s3_pocket_y1())/2)
def s3_pocket_f():    return (s3_pocket_w(), s3_pocket_y1() - s3_pocket_y0())
# ---- the tab's z chain ----
# Off the cavity's front face (= the board's nominal front edge), and dimensioned against the
# board's own TRAVEL toward the rear stops — not against how much spare depth plan_y has. Taking
# it off the front WALL was the bug: the wall absorbs plan_y's slack, so the ramp sank a
# millimetre for every millimetre of spare depth. Nothing about the tab should know plan_y.
# The cavity's front face, and the board's front edge it stands clear of.
def s3_cavity_y1():   return s3_cy() + s3_w/2 + s3_front_gap
def s3_tab_over():    return s3_front_gap + s3_tab_cover
# Top face flush with the wall's, then work downward: the nib, then the 45 deg ramp.
def s3_tab_top():     return s3_wall_top()
def s3_tab_z1():      return s3_tab_top() - s3_tab_h
def s3_tab_z0():      return s3_tab_z1() - s3_tab_over()
# ...and what that leaves at the board's own edge. Negative is clearance above the laminate.
def s3_tab_bite():    return (s3_seat_h + pcb_t) - (s3_tab_z0() + s3_front_gap)
def s3_wall_top():    return s3_seat_h + pcb_t + s3_lip
# How far the receptacle sits in from the outer face — a USB-C plug has only ~6.5 mm of
# shell before its overmold. Measured from the THINNED panel and the rear stop face.
def usb_setback():    return usb_panel_t + (inner_half_y() + s3_cy() - s3_w/2)

# ---- button module: one z chain shared by the cap, the holder and the shell bore ----
# All in case z (0 = top OUTER face, +z into the box). Diameters chain outward from the
# cap BODY: body -> shell bore -> holder bore -> lip -> relief -> collar.
def btn_bore_d():     return btn_wall_od + 2*btn_guide_clr    # 20.2 shell bore, the journal
def btn_recess_d():   return btn_cap_d + 2*clr                # 22.8 flange recess
def btn_wall_id():    return btn_wall_od - 2*btn_wall_t       # 17.2 — must clear sw_diag()
def btn_lip_od():     return btn_wall_od + 2*btn_lip_over     # 21.2
def btn_top_d():      return btn_wall_od - 2*btn_dome_r       # 15.6 flat left on top
# 45 deg by construction, not by choice: the cap prints dome-down, so deriving the rise
# from the step means the flare cannot become an overhang.
def btn_flare_h():    return (btn_cap_d - btn_wall_od)/2      # 1.2

def bh_bore_d():      return btn_wall_od + 2*bh_guide_clr     # 20.5 guide bore
def bh_relief_d():    return btn_lip_od() + 2*clr             # 22.0 room for the lip
def bh_collar_od():   return bh_relief_d() + 2*bh_wall        # 25.2
# The lip TRAVELS down its relief, so the relief is the lip plus the whole stroke.
def btn_stroke():     return sw_travel - btn_preload          # 0.45 — the press you feel
def bh_relief_h():    return btn_lip_t + btn_stroke() + btn_lip_slack   # 2.25

# The switch, standing directly on the collar floor.
def sw_diag():        return math.sqrt(2)*sw_body             # 15.56 — the binding dimension
def bh_pocket():      return sw_body + 2*clr                  # for the collision checks
# Pin slots. `a` is along the pinned axis, `b` across it; sw_pin_axis just swaps them.
def sw_pin_a():       return sw_body/2 + sw_pin_out           # 6.5 nominal
def sw_pin_b():       return sw_pin_gap/2                     # 2.5
def sw_pin_a_lo():    return sw_pin_a() - sw_pin_slack        # 5.0
def sw_pin_a_hi():    return sw_pin_a() + sw_pin_slack        # 8.0
def sw_pin_slot():    return 2*sw_pin_slack                   # 3.0 long

def sw_pin_pos():
    out = []
    for sa in (-1, 1):
        for sb in (-1, 1):
            out.append((sa*sw_pin_a(), sb*sw_pin_b()) if sw_pin_axis == 0
                       else (sb*sw_pin_b(), sa*sw_pin_a()))
    return out

def sw_pin_win_xy():
    return (sw_pin_slot(), sw_pin_win) if sw_pin_axis == 0 else (sw_pin_win, sw_pin_slot())

# How much of the switch's underside a slot eats, per axis. Computed, not assumed: the
# slot runs inboard of the body's edge on purpose.
def sw_win_span_a():
    return max(0.0, min(sw_pin_a_hi(), sw_body/2) - max(sw_pin_a_lo(), -sw_body/2))
def sw_win_span_b():
    return max(0.0, min(sw_pin_b() + sw_pin_win/2, sw_body/2)
                  - max(sw_pin_b() - sw_pin_win/2, -sw_body/2))
def sw_seat_area():
    return sw_body*sw_body - 4*sw_win_span_a()*sw_win_span_b()   # 115 of 121

# The ribs' envelope: inner face beside the body, and a rib's furthest point from the
# axis, which is what has to clear the cap's bore.
def sw_locate_r0():   return sw_body/2 + sw_locate_clr         # 5.9
def sw_locate_r1():   return sw_locate_r0() + sw_locate_t      # 7.5
def sw_locate_max():  return math.hypot(sw_locate_r1(), sw_locate_len/2)   # 7.91

def bh_z0():          return wall                              # collar top, on the inner face
def bh_catch_z():     return bh_z0() + bh_guide_h              # 8.0 cap lip lands HERE
def bh_relief_z1():   return bh_catch_z() + bh_relief_h()      # collar FLOOR = switch base
def bh_z1():          return bh_relief_z1() + bh_floor_t       # floor's far face
# ...but bh_z1() is NOT the deepest thing: the pins hang through the floor and get
# soldered under it, and that is what cavity_depth has to clear.
def sw_pin_z1():      return bh_relief_z1() + sw_pin_len       # 13.75 pin tips
def bh_deep_z():      return max(bh_z1(), sw_pin_z1())         # 13.75 deepest point
def sw_body_h():      return sw_h - sw_plunger_h               # 6.2 body alone
def sw_top_z():       return bh_relief_z1() - sw_body_h()      # switch body's top face
def plunger_z():      return bh_relief_z1() - sw_h             # plunger top, free. Straight
                                                               # off sw_h: the body/plunger
                                                               # split cannot reach the post.
# overall footprint, for the collision checks: the two posts set x, the collar sets y
def bh_plate_w():     return btn_pilot_pitch + bh_ear_d        # 37
def bh_plate_l():     return bh_collar_od()                    # 25.2

def btn_face_bot_z():   return btn_recess_depth - btn_face_gap    # 0.0 flange flush at rest
def btn_flange_top_z(): return btn_face_bot_z() - btn_flange_t    # -1.5
def btn_flare_top_z():  return btn_flange_top_z() - btn_flare_h() # -2.7 body starts here
def btn_apex_z():       return -btn_dome_h                        # -6.5
def btn_ceil_z():       return btn_apex_z() + btn_wall_t          # -5.3 ceiling, post root
def btn_proud():        return btn_dome_h                         # 6.5 proud of the top face
def btn_wall_z1():      return bh_catch_z() + btn_lip_t           # 9.0 body's far edge
# The post reaches btn_preload PAST the plunger's free position, so with the cap's lip on
# the catch the switch is holding the cap up there. That is the no-rattle condition.
def btn_post_tip_z():   return plunger_z() + btn_preload
def btn_post_h():       return btn_post_tip_z() - btn_ceil_z()    # free length

# devkit column, measured down from the top face
def plate_inner_z():  return top_depth()                          # plate's inner face
def s3_pcb_top_z():   return plate_inner_z() - s3_seat_h - pcb_t  # component-side surface
def s3_top_z():       return s3_pcb_top_z() - s3_comp_h           # tallest devkit part
def s3_usb_cz():      return s3_pcb_top_z() - usb_recept_h/2      # nominal centre
def s3_usb_z0():      return s3_usb_cz() - s3_usb_h/2 + s3_usb_trim_top      # top edge
def s3_usb_z1():      return s3_usb_cz() + s3_usb_h/2 - s3_usb_trim_bottom   # bottom edge
def s3_usb_h_eff():   return s3_usb_z1() - s3_usb_z0()
def s3_usb_cz_eff():  return (s3_usb_z0() + s3_usb_z1())/2

# ---- DAC z chain: board sits COMPONENT SIDE DOWN ----
# The socket hangs BELOW the PCB into a recess in the pocket floor: it puts the jack hole
# down near the base plate and leaves the SOLDER side facing up to be wired in place.
def dac_seat_z():     return plate_inner_z() - dac_seat_h    # PCB seating plane, LOWER face
def dac_pcb_top_z():  return dac_seat_z() - pcb_t            # solder side, facing UP
# These four carry jack_z_rise: they are where the socket REALLY sits, and they are what
# the shell's counterbore and plug hole are cut from.
def dac_socket_z0():  return dac_seat_z() - jack_z_rise                # socket top
def dac_socket_z1():  return dac_seat_z() + dac_jack_h - jack_z_rise   # socket bottom
def dac_jack_cz():    return dac_seat_z() + dac_jack_h/2 - jack_z_rise
def dac_axis_z():     return dac_seat_z() + dac_jack_axis - jack_z_rise
def dac_top_z():      return dac_pcb_top_z() - board_pin_h   # highest point: the tails
# socket recess in the floor: its footprint on the board, running off the +x end
def dac_recess_x0():  return dac_pcb_edge_x() - dac_jack_depth - clr
# Plate-referenced, deliberately WITHOUT the rise: the recess is as printed.
def dac_recess_z1():  return dac_seat_z() + dac_jack_h + clr
# Socket centre in y, and therefore the HOLE's position. Derived from the board END, not
# its centre — the socket sits in a corner.
def dac_jack_off():   return dac_jack_end * (dac_l/2 - dac_jack_inset - dac_jack_w/2)
def dac_jack_y():     return dac_pos_y() + dac_jack_off()

# mic clamp: the pad has to bridge from the post tops down to the seated board
def mic_board_top_z():  return wall - mic_seat_depth + pcb_t
def mic_clamp_pad_h():  return (wall + mic_post_h) - mic_board_top_z()
def mic_clamp_len():    return mic_post_pitch + mic_post_od

# ---- how big the case has to be, derived from the boards ----
# plan_x is one chain read from the +x wall inward, asymmetric all the way. plan_y is the
# devkit's length between the two lips, plus the DAC pocket passing between the +-y
# bosses — that one IS symmetric.
def plan_x_min():
    return (boss_inset + boss_od/2 + s3_boss_margin
            + pocket_wall + s3_l + 2*s3_board_clr      # devkit wall + cavity
            + shared_wall
            + board_clr + dac_w                        # DAC cavity
            + dac_jack_overhang + dac_socket_setback + jack_panel_t)

def plan_y_from_boss_dac():
    return 2*(abs(dac_pos_y()) + (dac_pocket_f()[1] + boss_od)/2 + boss_inset)
# Written out rather than measured off s3_pocket_f(), which depends on plan_y and made
# this circular.
def plan_y_from_depth():
    # rear clearance behind the board, the board, and the front gap in front of it
    return 2*wall + 2*clr + 2*reg_t + s3_w + s3_board_clr + s3_front_gap
def plan_y_min():
    return max(plan_y_from_depth(), plan_y_from_boss_dac())

# ---- and how DEEP it has to be ----
#   bare   — the devkit's tallest part just misses the top face
#   mic    — it also clears the mic board on its posts
#   button — it also clears the button holder, which reaches deepest of all
def cavity_for(clearance_z):
    return clearance_z + s3_seat_h + pcb_t + s3_comp_h - wall
def cavity_from_bare():   return cavity_for(wall)
def cavity_from_mic():    return cavity_for(wall + mic_post_h + pcb_t + 2)
# bh_deep_z(), not bh_z1(): the switch's four pins hang through the collar floor and get
# soldered under it, and those joints are the lowest thing on the top-face assembly.
def cavity_from_button(): return cavity_for(bh_deep_z() + 2)
def cavity_min():
    return max(cavity_from_bare(), cavity_from_mic(), cavity_from_button())

# ---- fit-test coupon extents (were functions in voice-case.scad) ----
# DERIVED from the two features the coupon has to contain, not typed in: it used to be a
# hard-coded 62 x 64 cube sized for a 96 mm plan, which quietly starts hanging off the
# part the moment plan_x changes.
def coupon_w():
    return min(2*(max(abs(btn_pos[0]) + bh_plate_w()/2,
                      abs(mic_pos[0]) + mic_size()[0]/2) + 4), 2*flat_half_x())
def coupon_y0():  return max(btn_pos[1] - bh_plate_l()/2 - 4, -flat_half_y())
def coupon_y1():  return min(mic_pos[1] + mic_size()[1]/2 + 3, inner_half_y())


def aabb_clear(p1, s1, p2, s2):
    """do two centred AABBs (at p1/p2, sizes s1/s2) clear each other?"""
    return (abs(p1[0] - p2[0]) >= (s1[0] + s2[0])/2
            or abs(p1[1] - p2[1]) >= (s1[1] + s2[1])/2)
