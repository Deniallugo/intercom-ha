"""The mic clamp — the one small printed part left from the old button module.

The dome button (dome + plunger + holder cup + 2 screws) is gone: the button is now a flexure
cut into the front panel (``case.button_slots``), with the switch on a screwed bridge
(``case.bridge``). The clamp is voice-case's, drawn in its PRINT orientation: bar on the bed,
pad up; the assembly turns it onto the mic posts.
"""

from . import params as P
from .build import box_z, cyl

CLAMP = 'mic clamp'


def clamp(part):
    box_z(part, 0, P.mic_clamp_t, (0, 0), (P.mic_clamp_len(), P.mic_clamp_w), name=CLAMP)
    pad = box_z(part, P.mic_clamp_t, P.mic_clamp_pad_h(), (0, 0),
                (P.mic_clamp_pad, min(P.mic_clamp_pad, P.mic_clamp_w)), name='pad')
    part.union(CLAMP, [pad])
    return part.cut(CLAMP, [cyl(part, -0.1, P.mic_clamp_t + 0.2, P.mic_screw_clear,
                                (sx*P.mic_post_pitch/2, 0), name='clamp screw') for sx in (-1, 1)])
