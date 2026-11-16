"""CLI: build the car, the showroom and the film animation, then save a .blend.

blender -b --factory-startup -P src/make_film.py -- [--parts a,b] [--quality final|preview]
        [--out out/blend/tourbillon_film.blend] [--res 1280x720] [--samples 28] [--timeline anim/timeline.json]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tb import build as tb_build, film  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts', default='')
    ap.add_argument('--quality', default='final')
    ap.add_argument('--out', default='out/blend/tourbillon_film.blend')
    ap.add_argument('--res', default='1280x720')
    ap.add_argument('--samples', type=int, default=28)
    ap.add_argument('--timeline', default='')
    a = ap.parse_args(argv)
    tb_build.build(parts=[p for p in a.parts.split(',') if p] or None, quality=a.quality)
    res = tuple(int(v) for v in a.res.lower().split('x'))
    tl, show, shots = film.make(a.timeline or None, res=res, samples=a.samples)
    for name, n, tris in tb_build.stats():
        print('[stats] %-28s %4d objects %9d tris' % (name, n, tris))
    tb_build.save(a.out)
    print('[make_film] %d frames at %d fps, %d shots -> %s' % (tl.last_frame, tl.fps, len(shots.cams), a.out))


main()
