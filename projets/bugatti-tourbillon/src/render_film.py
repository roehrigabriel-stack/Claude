"""CLI: render frames of the film .blend (resumable: existing frames are skipped).

blender -b out/blend/tourbillon_film.blend -P src/render_film.py -- --out out/film/frames
        [--frames 1-624] [--step 1] [--res 1280x720] [--samples 28] [--list 1,50,100] [--overwrite]
"""
import argparse
import os
import sys
import time

import bpy


def camera_for(scene, frame):
    best = None
    for m in sorted(scene.timeline_markers, key=lambda m: m.frame):
        if m.camera is not None and m.frame <= frame:
            best = m.camera
    return best


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--frames', default='')
    ap.add_argument('--list', default='')
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--res', default='')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args(argv)
    s = bpy.context.scene
    if a.res:
        s.render.resolution_x, s.render.resolution_y = (int(v) for v in a.res.lower().split('x'))
    if a.samples:
        s.cycles.samples = a.samples
        s.cycles.adaptive_min_samples = max(4, a.samples // 4)
    if a.list:
        frames = [int(v) for v in a.list.split(',')]
    else:
        f0, f1 = (int(v) for v in a.frames.split('-')) if a.frames else (s.frame_start, s.frame_end)
        frames = list(range(f0, f1 + 1, a.step))
    os.makedirs(a.out, exist_ok=True)
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.image_settings.compression = 30
    done = 0
    t_start = time.time()
    for f in frames:
        path = os.path.join(a.out, 'frame_%04d.png' % f)
        if os.path.exists(path) and os.path.getsize(path) > 0 and not a.overwrite:
            continue
        s.frame_set(f)
        cam = camera_for(s, f)
        if cam is not None:
            s.camera = cam
        s.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        done += 1
        print('[render_film] frame %d done in %.1fs (%d rendered, %.0fs elapsed)' % (f, time.time() - t0, done, time.time() - t_start), flush=True)
    print('[render_film] finished: %d frames rendered' % done, flush=True)


main()
