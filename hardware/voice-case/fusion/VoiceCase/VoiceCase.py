"""Voice S3 desk puck — Fusion 360 entry point (Scripts and Add-Ins, Shift+S).

Asks for a part, runs the design checks (nothing is built if one fails), and models it in
a new document:

  all        assembled preview
  shell      body: top face, walls, openings
  base       base plate: board pockets, register lip, vents
  button     snap-in cap
  holder     switch carrier, screws inside the top face
  clamp      mic clamp bar
  coupon     top-face fit coupon + its mating parts
  fit        devkit bed, rear end: pin relief, width, rear stops
  fit-front  devkit bed, front end: retention tab

Numbers live in `vc/params.py`; edit and re-run.
"""

import os
import sys
import traceback

import adsk.core
import adsk.fusion

# The part to build. Set ASK = False to pin it here and skip the prompt.
PART = 'all'
ASK = True
# Build into a new document each run; False builds into the active design.
NEW_DOCUMENT = True
# Add read-only `ref_*` user parameters for dimensioning hand sketches (vc/parameters.py).
USER_PARAMETERS = True
# Write one STL per component to stl/, in print orientation.
EXPORT_STL = True

PARTS = ('all', 'shell', 'base', 'button', 'holder', 'clamp', 'coupon', 'fit',
         'fit-front')


def _reload():
    """Import vc.* fresh, so an edited parameter takes effect on the next run."""
    here = os.path.dirname(os.path.realpath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    for name in [m for m in list(sys.modules) if m == 'vc' or m.startswith('vc.')]:
        del sys.modules[name]
    import vc.base_plate
    import vc.build
    import vc.button_cap
    import vc.button_holder
    import vc.checks
    import vc.coupons
    import vc.mic_clamp
    import vc.parameters
    import vc.params
    import vc.shell
    return vc


def _part(vc, design, module, transform=None):
    p = vc.build.Part(design, module.NAME, transform)
    module.build(p)
    return p


def _builders(vc, design, part):
    """[(label, thunk)] per component; deferred so `run` can group each part's timeline features."""
    P = vc.params
    t = vc.build.transform

    def one(module, transform=None):
        return lambda: [_part(vc, design, module, transform)]

    singles = {'shell': vc.shell, 'base': vc.base_plate, 'button': vc.button_cap,
               'holder': vc.button_holder, 'clamp': vc.mic_clamp}
    if part in singles:
        return [(singles[part].NAME, one(singles[part]))]
    if part == 'coupon':
        return [('coupon', lambda: vc.coupons.coupon(design))]
    if part == 'fit':
        return [(vc.coupons.FIT, lambda: vc.coupons.fit(design, end=-1))]
    if part == 'fit-front':
        return [(vc.coupons.FIT_FRONT, lambda: vc.coupons.fit(design, end=+1))]
    if part == 'all':
        # Shell frame: z = 0 is the top face, +z into the box. Holder and clamp are drawn
        # in print orientation, so they are flipped into place.
        placed = [
            (vc.shell, None),
            (vc.base_plate, t((0, 0, P.top_depth()))),
            (vc.button_cap, t((P.btn_pos[0], P.btn_pos[1], -P.btn_proud()))),
            (vc.button_holder, t((P.btn_pos[0], P.btn_pos[1], P.bh_z1()), rot_x_deg=180)),
            (vc.mic_clamp, t((P.mic_pos[0], P.mic_pos[1], P.wall + P.mic_post_h),
                             rot_x_deg=180)),
        ]
        return [(module.NAME, one(module, transform)) for module, transform in placed]
    raise ValueError('unknown part "%s" — one of: %s' % (part, ', '.join(PARTS)))


def _group_timeline(design, name, start):
    """Fold one part's features into a named timeline group, so the tree stays readable."""
    try:
        tl = design.timeline
        if tl and tl.count - 1 > start:
            tl.timelineGroups.add(start, tl.count - 1).name = name
    except Exception:
        pass            # cosmetic only — never lose a build over the timeline tree


def _export(parts, folder):
    written = []
    design = adsk.fusion.Design.cast(parts[0].comp.parentDesign)
    mgr = design.exportManager
    if not os.path.isdir(folder):
        os.makedirs(folder)
    for p in parts:
        # Export the component, not the occurrence: that keeps the print orientation.
        path = os.path.join(folder, '%s.stl' % p.comp.name.replace(' ', '-'))
        opts = mgr.createSTLExportOptions(p.comp, path)
        opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        mgr.execute(opts)
        written.append(os.path.basename(path))
    return written


def run(_context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        vc = _reload()

        part = PART
        if ASK:
            got, cancelled = ui.inputBox('part to build:\n' + ' | '.join(PARTS),
                                         'Voice S3 desk puck', PART)
            if cancelled:
                return
            part = (got or '').strip() or PART
        if part not in PARTS:
            ui.messageBox('"%s" is not one of: %s' % (part, ', '.join(PARTS)))
            return

        failures = vc.checks.run_checks()
        if failures:
            ui.messageBox('%d design check(s) failed — nothing built:\n\n  %s'
                          % (len(failures), '\n  '.join(failures)),
                          'Voice S3 desk puck')
            return

        if NEW_DOCUMENT:
            app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No Fusion design is active — open one, or set '
                          'NEW_DOCUMENT = True.')
            return

        notes = []
        if USER_PARAMETERS:
            added, updated, failed = vc.parameters.write(design)
            app.log('reference parameters: %d added, %d updated' % (added, updated))
            if failed:
                notes.append('reference parameters Fusion refused: %s' % ', '.join(failed))

        parts = []
        for label, thunk in _builders(vc, design, part):
            start = design.timeline.count if design.timeline else 0
            parts.extend(thunk())
            _group_timeline(design, label, start)

        app.activeViewport.fit()

        for p in parts:
            if p.warnings:
                notes.append('%s: cut missed the part — %s'
                             % (p.comp.name, ', '.join(p.warnings)))
        if EXPORT_STL:
            folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stl')
            notes.append('exported: %s' % ', '.join(_export(parts, folder)))
        if notes:
            ui.messageBox('\n'.join(notes), 'Voice S3 desk puck')
    except:  # noqa: E722 — Fusion's own convention: log, never let a script die silently
        app.log('Failed:\n%s' % traceback.format_exc())
        if ui:
            ui.messageBox('Failed:\n%s' % traceback.format_exc())
