"""mic clamp bar.

Port of ``modules/mic_clamp.scad``. The two M2 posts flank the INMP441 board rather than
sit under it — they have to, because the board lies directly on its own gasket and nothing
can be underneath it. So this bar spans both posts and its central pad reaches back down to
press the board's centre, opposite the MEMS port. Tightening the two M2s is what compresses
the gasket, and the gasket is what keeps the port volume near zero.

Drawn in PRINTING orientation: bar flat on the plate at z = 0, pad growing +z. No supports.
"""

from . import params as P
from .build import box_z, cyl

NAME = 'mic clamp'


def build(part):
    box_z(part, 0, P.mic_clamp_t, (0, 0), (P.mic_clamp_len(), P.mic_clamp_w), name=NAME)
    pad = box_z(part, P.mic_clamp_t, P.mic_clamp_pad_h(), (0, 0),
                (P.mic_clamp_pad, min(P.mic_clamp_pad, P.mic_clamp_w)), name='pad')
    part.union(NAME, [pad])
    return part.cut(NAME, [cyl(part, -0.1, P.mic_clamp_t + 0.2, P.mic_screw_clear,
                               (sx*P.mic_post_pitch/2, 0), name='clamp screw')
                           for sx in (-1, 1)])
