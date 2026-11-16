"""CLI: build the Tourbillon and save a .blend.

blender -b --factory-startup -P src/build.py -- [--parts a,b,c] [--quality preview|final]
        [--out out/tourbillon.blend] [--strict]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tb import build as tb_build  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts', default='')
    ap.add_argument('--quality', default='preview')
    ap.add_argument('--out', default='')
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args(argv)
    parts = [p for p in a.parts.split(',') if p] or None
    ctx = tb_build.build(parts=parts, quality=a.quality, strict=a.strict)
    for name, n, tris in tb_build.stats():
        print('[stats] %-28s %4d objects %9d tris' % (name, n, tris))
    if a.out:
        tb_build.save(a.out)
        print('[tb.build] saved', a.out)
    print('[tb.build] built modules:', ', '.join(ctx.built))


main()
