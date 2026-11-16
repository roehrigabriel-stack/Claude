"""Assemble frame_XXXX.png files of a folder into one labelled contact sheet.

python3 tools/contact_sheet.py <frames dir> <out.png> [--cols 4] [--width 480] [--fps 24]
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('out')
ap.add_argument('--cols', type=int, default=4)
ap.add_argument('--width', type=int, default=480)
ap.add_argument('--fps', type=float, default=24.0)
a = ap.parse_args()
files = sorted(glob.glob(os.path.join(a.src, 'frame_*.png')))
if not files:
    raise SystemExit('no frames in ' + a.src)
ims = []
for p in files:
    im = Image.open(p).convert('RGB')
    h = int(round(im.height * a.width / im.width))
    im = im.resize((a.width, h), Image.LANCZOS)
    n = int(os.path.basename(p)[6:10])
    d = ImageDraw.Draw(im)
    label = 'f%d  %.2fs' % (n, (n - 1) / a.fps)
    d.rectangle([0, 0, 8 + 7 * len(label), 16], fill=(0, 0, 0))
    d.text((4, 2), label, fill=(255, 230, 80))
    ims.append(im)
rows = (len(ims) + a.cols - 1) // a.cols
w, h = ims[0].size
sheet = Image.new('RGB', (a.cols * w, rows * h), (20, 20, 20))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % a.cols) * w, (i // a.cols) * h))
sheet.save(a.out)
print(a.out, sheet.size, len(ims), 'frames')
