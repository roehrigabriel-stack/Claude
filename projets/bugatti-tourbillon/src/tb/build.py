"""tb.build: assemble the car from its part modules.

Each part module lives in tb/parts/<name>.py and exposes

    def build(ctx) -> None

It creates its objects in world coordinates, puts them in a collection
'TB_<Name>', and parents them to rig.module_root('<Name>') or to hinges /
wheel pivots (tb.rig). `ctx` is a BuildContext (see below).

Command line (from anywhere):
    blender -b --factory-startup -P /home/user/Claude/projets/bugatti-tourbillon/src/build.py -- \
        --parts wheels,body --out /path/to/file.blend
"""
import importlib
import os
import time
import traceback
import bpy

from . import spec, geo, mats, rig, studio

# build order: later modules may look up objects created by earlier ones
ORDER = ['chassis', 'engine', 'body', 'glass', 'doors', 'front', 'rear', 'aero', 'lights',
         'wheels', 'interior']


class BuildContext:
    """Shared state handed to every part module."""

    def __init__(self, quality='preview'):
        self.spec = spec
        self.geo = geo
        self.mats = mats
        self.rig = rig
        self.quality = quality            # 'preview' (fast test builds) or 'final'
        self.root = rig.ctrl()
        self.built = []                   # names of modules built so far
        self.data = {}                    # free-form: modules may publish info for later ones

    def final(self):
        return self.quality == 'final'

    def collection(self, name):
        return geo.collection('TB_' + name, geo.collection('TOURBILLON_Model'))

    def module_root(self, name):
        return rig.module_root(name)

    def objects(self, prefix):
        """All objects whose name starts with prefix."""
        return [o for o in bpy.data.objects if o.name.startswith(prefix)]


def available_parts():
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parts')
    names = [f[:-3] for f in os.listdir(here) if f.endswith('.py') and not f.startswith('_')]
    ordered = [n for n in ORDER if n in names]
    return ordered + sorted(n for n in names if n not in ORDER and not n.endswith('_lib'))


def build(parts=None, quality='preview', reset=True, strict=False):
    """Build the requested part modules (default: all available) into a fresh scene.
    Returns the BuildContext."""
    if reset:
        studio.reset_scene()
    ctx = BuildContext(quality)
    names = available_parts() if not parts else [p for p in ORDER + sorted(parts) if p in parts]
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        t0 = time.time()
        try:
            mod = importlib.import_module('tb.parts.' + name)
            mod = importlib.reload(mod)
            mod.build(ctx)
            ctx.built.append(name)
            print('[tb.build] %-10s ok   %.1fs' % (name, time.time() - t0))
        except Exception:
            print('[tb.build] %-10s FAILED' % name)
            traceback.print_exc()
            if strict:
                raise
    bpy.context.view_layer.update()
    return ctx


def save(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), compress=True)
    return path


def stats():
    """Small summary of the scene (object and triangle counts per collection)."""
    dg = bpy.context.evaluated_depsgraph_get()
    rows = []
    for coll in bpy.data.collections:
        tris = 0
        n = 0
        for ob in coll.objects:
            if ob.type == 'MESH':
                me = ob.evaluated_get(dg).to_mesh()
                tris += sum(len(p.vertices) - 2 for p in me.polygons)
                ob.evaluated_get(dg).to_mesh_clear()
                n += 1
        if n:
            rows.append((coll.name, n, tris))
    return rows
