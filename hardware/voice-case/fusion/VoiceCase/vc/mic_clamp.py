"""Mic clamp bar (port of ``modules/mic_clamp.scad``): spans the two M2 posts, and its
pad presses the INMP441 onto its gasket. Print orientation: bar on the plate, pad up.
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
