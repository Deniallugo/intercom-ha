"""Voice S3 wall unit — Fusion script entry point.

Run it from Fusion's Scripts and Add-Ins palette (Shift+S). It asks what to do:

  all          the whole unit on the wall: both boxes with every printed part AND every
               electronic part as its own component, the plate and the lock bracket
  electronics  the electronics alone, in their boxes' positions
  amp-shell  amp-lid  amp-sled  voice-shell  voice-lid  voice-tray  sleeve
  plunger  dome  holder  clamp  plate  lock  coupon-amp  coupon-voice
               one printed part, in its print orientation
  sync         read parts you DRAGGED in the active document back into vwc/placement.py

The adjust-in-place loop:
  1. run `all`
  2. drag a part — the devkit, the DAC, the MP1584, the mic, the switch, the amp board — inside
     its box (Move/Copy, or drag in the canvas). Inspect > Interference shows what it hits.
  3. run `sync` on that document: the move is written to vwc/placement.py and the design checks
     run on the result
  4. run `all` again: pockets, standoffs, windows and holes follow the part

Numbers that are not positions — board sizes, clearances, connector heights — live in
vwc/params.py. A part is never built on a design that fails a check (vwc/checks.py, also
runnable without Fusion: ../test.sh).
"""

import os
import sys
import traceback

import adsk.core
import adsk.fusion

PART = 'all'
ASK = True
# a new document per build, so re-running never touches work you have open (`sync` always works
# on the ACTIVE document — the one you dragged things in)
NEW_DOCUMENT = True
# ref_* reference parameters in the Parameters dialog. They drive nothing — see vwc/parameters.py
USER_PARAMETERS = True
# see-through shells, lids and plate in the assembled views, so the electronics show. None = off
GHOST = 0.35
# one STL per PRINTED component into VoiceWallCase/stl/ (electronics are never exported)
EXPORT_STL = False

TITLE = 'Voice S3 wall unit'


def _reload():
    """Import vwc.* fresh, so an edited parameter or a synced placement takes effect."""
    here = os.path.dirname(os.path.realpath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    for name in [m for m in list(sys.modules) if m == 'vwc' or m.startswith('vwc.')]:
        del sys.modules[name]
    import vwc.assembly
    import vwc.checks
    import vwc.parameters
    import vwc.sync
    return vwc


def _export(parts, folder):
    written = []
    design = adsk.fusion.Design.cast(parts[0].comp.parentDesign)
    mgr = design.exportManager
    if not os.path.isdir(folder):
        os.makedirs(folder)
    for p in parts:
        path = os.path.join(folder, '%s.stl' % p.comp.name.replace(' ', '-'))
        opts = mgr.createSTLExportOptions(p.comp, path)
        opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        mgr.execute(opts)
        written.append(os.path.basename(path))
    return written


def _sync(vwc, app, ui):
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Open the document you moved parts in, then run sync.', TITLE)
        return
    moved, built = vwc.sync.read(design)
    if not moved:
        ui.messageBox('Nothing has moved: every electronic part is where the build put it.\n\n'
                      'Drag a part inside its group ("amp electronics" / "voice electronics" in the browser), then '
                      'run sync again.', TITLE)
        return
    if built is None:
        built_note = ('\n\n(This document carries no record of the placement it was built with, '
                      'so the moves are added to placement.py as it is now.)')
    else:
        built_note = ''
    updates, notes = vwc.sync.plan(moved, built)
    if not updates:
        ui.messageBox('Nothing to write:\n\n  ' + '\n  '.join(notes) + built_note, TITLE)
        return
    path = vwc.sync.write(updates)
    vwc = _reload()                                   # re-read the file just written
    failures = vwc.checks.run_checks()
    verdict = ('All design checks pass — run `all` to rebuild with the new positions.'
               if not failures else
               '%d design check(s) now FAIL — the next build will refuse until they pass:\n  %s'
               % (len(failures), '\n  '.join(failures)))
    ui.messageBox('Wrote %s:\n\n  %s\n\n%s%s' % (os.path.basename(path), '\n  '.join(notes),
                                                 verdict, built_note), TITLE)


def run(_context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        vwc = _reload()
        parts = vwc.assembly.PARTS
        part = PART
        if ASK:
            got, cancelled = ui.inputBox('part to build, or sync:\n' + ' | '.join(parts), TITLE, PART)
            if cancelled:
                return
            part = (got or '').strip() or PART
        if part not in parts:
            ui.messageBox('"%s" is not one of: %s' % (part, ', '.join(parts)), TITLE)
            return
        if part == 'sync':
            _sync(vwc, app, ui)
            return

        failures = vwc.checks.run_checks()
        if failures:
            ui.messageBox('%d design check(s) failed — nothing built:\n\n  %s'
                          % (len(failures), '\n  '.join(failures)), TITLE)
            return

        if NEW_DOCUMENT:
            app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No Fusion design is active — open one, or set NEW_DOCUMENT = True.', TITLE)
            return

        notes = []
        if USER_PARAMETERS:
            added, updated, failed = vwc.parameters.write(design)
            app.log('reference parameters: %d added, %d updated' % (added, updated))
            if failed:
                notes.append('reference parameters Fusion refused: %s' % ', '.join(failed))

        printed, items = vwc.assembly.build(design, part, ghost=GHOST)
        stuck = vwc.build.place_all(design, items)    # positions LAST, read back, re-applied
        if stuck:
            notes.append('Fusion would not keep the position of: %s — they are drawn where '
                         'Fusion left them, not where they belong.' % ', '.join(stuck))
        app.activeViewport.fit()

        for p in items:
            if getattr(p, 'warnings', None):
                notes.append('%s: cut missed the part — %s' % (p.comp.name, ', '.join(p.warnings)))
        for p in printed:
            # a printed part is ONE solid; a second body is a lump a cut split off or a join
            # that did not fuse, and it would print as a loose piece
            n = p.comp.bRepBodies.count
            if n != 1:
                notes.append('%s came out as %d bodies, not 1: %s' % (
                    p.comp.name, n, ', '.join(p.comp.bRepBodies.item(i).name for i in range(n))))
        if EXPORT_STL and printed:
            folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stl')
            notes.append('exported: %s' % ', '.join(_export(printed, folder)))
        if notes:
            ui.messageBox('\n'.join(notes), TITLE)
    except:  # noqa: E722 — Fusion's convention: log, never let a script die silently
        msg = 'Failed (code as of %s):\n%s' % (_code_stamp(), traceback.format_exc())
        app.log(msg)
        if ui:
            ui.messageBox(msg)


def _code_stamp():
    """newest modification time of the script's own code — so a traceback says which version
    actually ran (a stale one shows up immediately)"""
    import time
    here = os.path.dirname(os.path.realpath(__file__))
    files = [os.path.join(here, 'vwc', f) for f in os.listdir(os.path.join(here, 'vwc')) if f.endswith('.py')]
    files.append(os.path.realpath(__file__))
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(max(os.path.getmtime(f) for f in files)))
