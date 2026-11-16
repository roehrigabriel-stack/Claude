"""CLI: build (or open) the car and render standard views for review.

Fresh build of some parts:
  blender -b --factory-startup -P src/render_views.py -- --parts wheels --views f34,left \
      --out out/renders/wheels [--res 1280x720] [--samples 32] [--style light|dark]
      [--set door_L=1 --set headlights=1] [--hide TB_Glass,TB_Body] [--cabin-light 40]
      [--cam "ex,ey,ez,tx,ty,tz,lens" --name closeup]   (repeatable custom camera)

Open an existing file instead of building:
  blender -b out/tourbillon.blend -P src/render_views.py -- --no-build --views f34 --out out/renders/full

Views: front rear left right top f34 f34r r34 r34r low_f34 low_r34 high_f34 high_r34
       ortho_side ortho_front ortho_rear ortho_top   (fixed-scale blueprint views)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from tb import build as tb_build, studio, rig, geo  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts', default='')
    ap.add_argument('--quality', default='preview')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--views', default='f34')
    ap.add_argument('--out', required=True)
    ap.add_argument('--res', default='1280x720')
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--style', default='light')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--hide', default='')
    ap.add_argument('--cabin-light', type=float, default=0.0)
    ap.add_argument('--cam', action='append', default=[])
    ap.add_argument('--name', action='append', default=[])
    ap.add_argument('--suffix', default='')
    ap.add_argument('--transparent', action='store_true')
    ap.add_argument('--no-floor', action='store_true')
    a = ap.parse_args(argv)

    if not a.no_build:
        tb_build.build(parts=[p for p in a.parts.split(',') if p] or None, quality=a.quality)
    res = tuple(int(v) for v in a.res.lower().split('x'))
    studio.setup_render(res=res, samples=a.samples, transparent=a.transparent)
    car = [o for o in rig.all_car_objects() if o.type == 'MESH']
    if not geo.collection(studio.STUDIO_COLL).objects:
        c, r = studio.frame_bounds(car) if car else ((0, 0, 0), 3.0)
        scale = max(0.25, min(1.0, r / 2.6))
        studio.preview_studio(style=a.style, floor=not a.no_floor,
                              center=(c[0], c[1], 0.0) if scale < 0.99 else (0, 0, 0), scale=scale)
    if a.cabin_light > 0:
        studio.interior_light(a.cabin_light)
    for kv in a.set:
        k, v = kv.split('=')
        rig.set_prop(k, float(v))
    for cname in [c for c in a.hide.split(',') if c]:
        coll = bpy.data.collections.get(cname)
        if coll:
            for ob in coll.all_objects:
                ob.hide_render = True
    bpy.context.view_layer.update()
    views = [v for v in a.views.split(',') if v]
    if views:
        studio.render_views(a.out, views, objs=car or None, suffix=a.suffix)
    for i, spec_str in enumerate(a.cam):
        v = [float(x) for x in spec_str.split(',')]
        name = a.name[i] if i < len(a.name) else 'cam%d' % i
        studio.shot(os.path.join(a.out, name + a.suffix + '.png'), v[0:3], v[3:6],
                    lens=v[6] if len(v) > 6 else 50.0, res=res, samples=a.samples)
    print('[render_views] done ->', a.out)


main()
