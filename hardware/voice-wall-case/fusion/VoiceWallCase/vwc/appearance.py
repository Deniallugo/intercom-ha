"""Colours for the dummy electronics and see-through shells — cosmetic, never fatal.

Fusion's appearance libraries are named differently across versions ("Fusion 360 Appearance
Library", "Fusion Appearance Library") and so are their entries, so this looks for a plain
plastic or paint to copy, recolours the copy, and caches it in the design by name. Any failure
anywhere just leaves the body in the default grey: a build is never lost over a colour.
"""

import adsk.core

RGB = {
    'pcb_dark': (25, 70, 35), 'pcb_blue': (25, 55, 150), 'pcb_purple': (95, 45, 125),
    'black': (30, 30, 32), 'metal': (185, 188, 192), 'alu': (140, 146, 158),
    'green': (35, 140, 65), 'yellow': (235, 200, 35), 'red': (210, 35, 35),
    'blue': (45, 95, 210), 'knob': (70, 70, 76), 'cable': (55, 55, 58),
}
_BASES = ('Plastic - Matte (Yellow)', 'Plastic - Glossy (Yellow)', 'Paint - Enamel Glossy (Yellow)',
          'Plastic - Matte (Black)', 'Plastic - Glossy (Black)')


def _base(app):
    for i in range(app.materialLibraries.count):
        lib = app.materialLibraries.item(i)
        if 'ppearance' not in lib.name:
            continue
        for n in _BASES:
            a = lib.appearances.itemByName(n)
            if a:
                return a
        for j in range(min(lib.appearances.count, 400)):
            a = lib.appearances.item(j)
            if a.name.startswith('Plastic'):
                return a
    return None


def _colour_prop(a):
    props = a.appearanceProperties
    for getter, key in ((props.itemByName, 'Color'), (props.itemById, 'opaque_albedo'),
                        (props.itemById, 'generic_diffuse')):
        try:
            p = adsk.core.ColorProperty.cast(getter(key))
            if p:
                return p
        except Exception:
            pass
    for i in range(props.count):
        p = adsk.core.ColorProperty.cast(props.item(i))
        if p:
            return p
    return None


def get(design, key):
    try:
        name = 'vwc ' + key
        a = design.appearances.itemByName(name)
        if a:
            return a
        base = _base(adsk.core.Application.get())
        if base is None:
            return None
        a = design.appearances.addByCopy(base, name)
        p = _colour_prop(a)
        if p:
            r, g, b = RGB.get(key, (128, 128, 128))
            p.value = adsk.core.Color.create(r, g, b, 0)
        return a
    except Exception:
        return None


def paint(design, body, key):
    try:
        a = get(design, key)
        if a:
            body.appearance = a
    except Exception:
        pass


def ghost(occ, opacity):
    """see-through override on a whole component, so the parts inside show"""
    try:
        occ.opacity = opacity
    except Exception:
        pass
