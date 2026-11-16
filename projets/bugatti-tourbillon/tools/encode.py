"""Encode the rendered frames + soundtrack into the final MP4.

python3 tools/encode.py --frames out/film/frames --audio out/audio/soundtrack.wav \
        --out out/film/tourbillon_showcase.mp4 [--timeline anim/timeline.json] [--title TOURBILLON]
        [--scale 1920x1080] [--crf 16]

Adds a fade from black at the start, a fade to black on the timeline's
fade_out event and a letter-spaced title card over the final seconds.
"""
import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']


def title_png(path, size, text, sub):
    w, h = size
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    font_path = next((f for f in FONTS if os.path.exists(f)), None)

    def spaced(txt, px, y, tracking, fill):
        font = ImageFont.truetype(font_path, px) if font_path else ImageFont.load_default()
        widths = [d.textlength(c, font=font) for c in txt]
        total = sum(widths) + tracking * (len(txt) - 1)
        x = (w - total) / 2.0
        for c, cw in zip(txt, widths):
            d.text((x, y), c, font=font, fill=fill)
            x += cw + tracking
    spaced(text, int(h * 0.060), int(h * 0.845), int(h * 0.030), (255, 255, 255, 235))
    if sub:
        spaced(sub, int(h * 0.020), int(h * 0.925), int(h * 0.010), (200, 215, 230, 200))
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', required=True)
    ap.add_argument('--audio', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeline', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'anim', 'timeline.json'))
    ap.add_argument('--title', default='TOURBILLON')
    ap.add_argument('--subtitle', default='BUGATTI')
    ap.add_argument('--scale', default='')
    ap.add_argument('--crf', type=int, default=16)
    ap.add_argument('--start', type=int, default=1)
    a = ap.parse_args()
    tl = json.load(open(a.timeline))
    fps, dur = tl['fps'], tl['duration']
    t_fade = next((e['t'] for e in tl['events'] if e['type'] == 'fade_out'), dur - 1.0)
    first = os.path.join(a.frames, 'frame_%04d.png' % a.start)
    w, h = Image.open(first).size
    if a.scale:
        w, h = (int(v) for v in a.scale.lower().split('x'))
    tpath = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'title_overlay.png')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    title_png(tpath, (w, h), a.title, a.subtitle)
    t_title = max(0.0, t_fade - 1.6)
    vf = ('[0:v]scale=%d:%d:flags=lanczos,format=yuv420p[base];'
          '[1:v]format=rgba,fade=t=in:st=%.3f:d=0.8:alpha=1[ttl];'
          '[base][ttl]overlay=0:0:enable=\'gte(t,%.3f)\'[ov];'
          '[ov]fade=t=in:st=0:d=0.7,fade=t=out:st=%.3f:d=%.3f[v]') % (w, h, t_title, t_title, t_fade, max(dur - t_fade, 0.1))
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-framerate', str(fps), '-start_number', str(a.start),
           '-i', os.path.join(a.frames, 'frame_%04d.png'), '-loop', '1', '-framerate', str(fps), '-i', tpath]
    if a.audio:
        cmd += ['-i', a.audio]
    cmd += ['-filter_complex', vf, '-map', '[v]']
    if a.audio:
        cmd += ['-map', '2:a', '-c:a', 'aac', '-b:a', '256k']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
            '-t', '%.3f' % dur, a.out]
    subprocess.run(cmd, check=True)
    print('encoded', a.out, os.path.getsize(a.out) // 1024, 'kB')


if __name__ == '__main__':
    main()
