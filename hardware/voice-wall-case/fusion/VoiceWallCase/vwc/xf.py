"""Rigid transforms in pure Python — (R, t), R as three rows, mm. No adsk.

Every placement in the assembly is one of these, composed here and handed to Fusion only at
the end (``build.matrix``), so the same arithmetic serves the build, the offline emitter and
`sync` (which has to invert a box's placement to turn a drag back into box-local numbers).

Fusion occurrences only take RIGID transforms — no mirrors. The OpenSCAD placed the wall plate
with mirror([0, 1, 0]) rotate([90, 0, 0]); here it is a proper rotation that also flips x,
which is the same solid because the plate is symmetric in x (checked in `plate`).
"""

import math

I3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
IDENTITY = (I3, (0.0, 0.0, 0.0))


def T(x=0.0, y=0.0, z=0.0):
    return (I3, (float(x), float(y), float(z)))


def _rot(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    c, s = round(c, 15), round(s, 15)
    if axis == 'x':
        R = ((1, 0, 0), (0, c, -s), (0, s, c))
    elif axis == 'y':
        R = ((c, 0, s), (0, 1, 0), (-s, 0, c))
    else:
        R = ((c, -s, 0), (s, c, 0), (0, 0, 1))
    return (tuple(tuple(float(v) for v in r) for r in R), (0.0, 0.0, 0.0))


def Rx(deg): return _rot('x', deg)
def Ry(deg): return _rot('y', deg)
def Rz(deg): return _rot('z', deg)


def M(rows, t=(0, 0, 0)):
    """from explicit rows — for the plate's axis swap"""
    return (tuple(tuple(float(v) for v in r) for r in rows), tuple(float(v) for v in t))


def mul(a, b):
    """a * b: apply b FIRST, then a — OpenSCAD's nesting order, so
    translate(t) rotate(r) child  ==  mul(T(t), R(r))."""
    Ra, ta = a
    Rb, tb = b
    R = tuple(tuple(sum(Ra[i][k]*Rb[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    t = tuple(sum(Ra[i][k]*tb[k] for k in range(3)) + ta[i] for i in range(3))
    return (R, t)


def chain(*xs):
    out = IDENTITY
    for x in xs:
        out = mul(out, x)
    return out


def apply(x, p):
    R, t = x
    return tuple(sum(R[i][k]*p[k] for k in range(3)) + t[i] for i in range(3))


def apply_vec(x, v):
    R, _ = x
    return tuple(sum(R[i][k]*v[k] for k in range(3)) for i in range(3))


def inverse(x):
    R, t = x
    Rt = tuple(tuple(R[j][i] for j in range(3)) for i in range(3))
    return (Rt, tuple(-sum(Rt[i][k]*t[k] for k in range(3)) for i in range(3)))


def det(x):
    (a, b, c), (d, e, f), (g, h, i) = x[0]
    return a*(e*i - f*h) - b*(d*i - f*g) + c*(d*h - e*g)


def same_rotation(a, b, tol=1e-6):
    return all(abs(a[0][i][j] - b[0][i][j]) < tol for i in range(3) for j in range(3))
