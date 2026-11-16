"""Combine several PNG renders into ONE labelled contact sheet (one image to look at).

python3 tools/sheet.py <out.png> <img1.png> <img2.png> ... [--cols N] [--cell 800]
Labels are the file names without extension.
"""
import argparse
import os

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('images', nargs='+')
ap.add_argument('--cols', type=int, default=0)
ap.add_argument('--cell', type=int, default=0)
a = ap.parse_args()
n = len(a.images)
cols = a.cols or (1 if n == 1 else 2 if n <= 4 else 3)
cell = a.cell or (1280 if cols == 1 else 900 if cols == 2 else 640)
ims = []
for p in a.images:
    im = Image.open(p).convert('RGB')
    h = int(round(im.height * cell / im.width))
    im = im.resize((cell, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    label = os.path.splitext(os.path.basename(p))[0]
    d.rectangle([0, 0, 10 + 7 * len(label), 16], fill=(0, 0, 0))
    d.text((5, 2), label, fill=(255, 230, 80))
    ims.append(im)
rows = (n + cols - 1) // cols
ch = max(im.height for im in ims)
sheet = Image.new('RGB', (cols * cell, rows * ch), (25, 25, 25))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * cell, (i // cols) * ch))
sheet.save(a.out)
print('[sheet]', a.out, sheet.size)
