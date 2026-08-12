"""Voice S3 desk puck — Fusion 360 script entry point.

Run it from Fusion's Scripts and Add-Ins palette (Shift+S). It asks which part to build,
runs the design checks, and models that part in a NEW document — one component per part,
built from standard sketch + extrude / revolve / loft features and combines, so everything
lands in the timeline and can be inspected, edited or rolled back by hand.

  all      the assembled preview: shell, plate, cap, holder and clamp in position
  shell    the puck body — top face, four walls, every opening
  base     the base plate with both board pockets, the register lip and the vents
  button   the snap-in cap
  holder   the switch carrier that screws inside the top face
  clamp    the mic clamp bar
  coupon   top-face fit coupon + the three parts that mate with it
  fit      a slice off the devkit bed's REAR end — pin relief, width, rear stops
  fit-front  the same off its FRONT end — the retention tab

The numbers all live in `vc/params.py`, and the checks that hold them together in
`vc/checks.py` — which also runs standalone (`./test.sh`), so you can move a board
dimension and see what it costs without opening Fusion at all. A part is never built on a
design that fails a check: that is the same contract the OpenSCAD had, where `assert()`
stopped the render.

Editing a parameter and re-running is the whole workflow, and the module cache is purged
below to make that work — without it Fusion holds the first import of `vc.*` for the rest
of the session and your edit appears to do nothing.
"""

import os
import sys
import traceback

import adsk.core
import adsk.fusion

# The part to build. Set ASK = False to pin it here and skip the prompt.
PART = 'all'
ASK = True
# A new document per run, so re-running never touches work you have open. Turn this off to
# build into the active design instead.
NEW_DOCUMENT = True
# Deposit the headline numbers in the Parameters dialog as `ref_*`, so a sketch you draw by
# hand can be dimensioned against the case. They are REFERENCE ONLY and drive nothing —
# see vc/parameters.py.
USER_PARAMETERS = True
# Write one STL per component next to this script, in stl/ — the equivalent of build.sh.
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
    """[(label, thunk)] — one entry per component, built when its thunk is called.

    Deferred rather than built here so `run` can note where each part's features start in
    the timeline and fold them into a named group as they land.
    """
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
        # The assembled preview, in the shell's frame: z = 0 is the top OUTER face and +z
        # runs down into the box. The holder and the clamp are the two parts drawn in their
        # own print orientation rather than the case's, so they flip into place.
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
        # the COMPONENT, not the occurrence: that exports in the part's own frame, which is
        # the print orientation each part was drawn in
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

        # Checks first, and nothing is modelled if one fails — a case that fails one of
        # these is not a case, it is a pile of collisions waiting to be discovered by hand.
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
        # The root component is NOT renamed: its name follows the document's, and Fusion
        # refuses to set it ("root component name cannot be changed"). The part components
        # inside it carry the names.

        notes = []
        if USER_PARAMETERS:
            added, updated, failed = vc.parameters.write(design)
            # Quiet on success — this is housekeeping, not something to interrupt for. The
            # TEXT COMMANDS window has it if you want the count.
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
