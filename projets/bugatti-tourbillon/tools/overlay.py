"""Overlay the reference blueprint linework on the orthographic renders.

Usage (plain python3, needs Pillow + numpy; NOT run inside Blender):
    python3 tools/overlay.py <dir with ortho_side.png / ortho_front.png / ortho_rear.png / ortho_top.png> [suffix]

For every ortho_* render found it writes <name>_overlay.png next to it: the
render (dimmed) with the blueprint lines drawn in magenta at the same scale,
plus a metric grid (thin line every 0.5 m, labelled). Where the magenta lines
and the model silhouette disagree, the model is wrong.

The orthographic renders come from tb.studio.render_views (fixed 320 px/m).
Blueprint calibration (pixels in refs/A3_blueprint.png, 199.5 px/m) was
measured from the linework; adjust CAL below if you find a better fit.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BLUEPRINT = os.path.join(HERE, '..', 'refs', 'A3_blueprint.png')
BP_PX_PER_M = 199.5
R_PX_PER_M = 320.0          # tb.studio.ORTHO_PX_PER_M
Y_NOSE = -2.400             # spec.Y_NOSE
Y_CENTER = -0.0645          # ortho view centre (middle of the car length)
Z_CENTER = 0.75

# blueprint regions (x0, y0, x1, y1) and anchor pixel of a known car point
CAL = {
    # anchor = pixel of (nose tip, ground)
    'ortho_side':  dict(box=(80, 100, 1040, 380), anchor=(1023.0, 361.5)),
    # anchor = pixel of (centreline, ground)
    'ortho_front': dict(box=(1090, 100, 1545, 380), anchor=(1314.5, 362.0)),
    'ortho_rear':  dict(box=(1090, 495, 1545, 760), anchor=(1314.5, 745.0)),
    # anchor = pixel of (nose tip, centreline)
    'ortho_top':   dict(box=(80, 485, 1040, 945), anchor=(1025.0, 713.5)),
}


def pink_mask(im):
    a = np.asarray(im.convert('RGB')).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return ((r > 150) & (b > 170) & (g < 195) & ((r - g) > 30) & ((b - g) > 30))


def render_anchor(view, w, h):
    """Pixel in the ortho render of the same car point as CAL[view]['anchor']."""
    if view == 'ortho_side':
        return (w / 2.0 - (Y_NOSE - Y_CENTER) * R_PX_PER_M, h / 2.0 + Z_CENTER * R_PX_PER_M)
    if view in ('ortho_front', 'ortho_rear'):
        return (w / 2.0, h / 2.0 + Z_CENTER * R_PX_PER_M)
    return (w / 2.0 - (Y_NOSE - Y_CENTER) * R_PX_PER_M, h / 2.0)


def grid(draw, view, w, h):
    col = (90, 200, 255)
    if view in ('ortho_side', 'ortho_top'):
        y = -3.0
        while y <= 3.0:
            u = w / 2.0 - (y - Y_CENTER) * R_PX_PER_M
            draw.line([(u, 0), (u, h)], fill=col, width=1)
            draw.text((u + 3, 4), 'y=%.1f' % y, fill=col)
            y += 0.5
    else:
        x = -1.5
        while x <= 1.5:
            u = w / 2.0 + x * R_PX_PER_M
            draw.line([(u, 0), (u, h)], fill=col, width=1)
            draw.text((u + 3, 4), 'x=%.1f' % x, fill=col)
            x += 0.5
    if view == 'ortho_top':
        x = -1.0
        while x <= 1.0:
            v = h / 2.0 - x * R_PX_PER_M
            draw.line([(0, v), (w, v)], fill=col, width=1)
            draw.text((4, v + 2), 'x=%.1f' % x, fill=col)
            x += 0.5
    else:
        z = 0.0
        while z <= 1.5:
            v = h / 2.0 - (z - Z_CENTER) * R_PX_PER_M
            draw.line([(0, v), (w, v)], fill=col, width=1)
            draw.text((4, v + 2), 'z=%.2f' % z, fill=col)
            z += 0.25


def overlay(render_path, view, out_path):
    bp = Image.open(BLUEPRINT)
    cal = CAL[view]
    x0, y0, x1, y1 = cal['box']
    mask = pink_mask(bp.crop(cal['box']))
    k = R_PX_PER_M / BP_PX_PER_M
    m = Image.fromarray((mask * 255).astype('uint8')).resize(
        (int(round((x1 - x0) * k)), int(round((y1 - y0) * k))), Image.LANCZOS)
    ren = Image.open(render_path).convert('RGB')
    w, h = ren.size
    ax, ay = render_anchor(view, w, h)
    bx, by = (cal['anchor'][0] - x0) * k, (cal['anchor'][1] - y0) * k
    ox, oy = int(round(ax - bx)), int(round(ay - by))
    base = Image.blend(ren, Image.new('RGB', ren.size, (30, 30, 30)), 0.35)
    d = ImageDraw.Draw(base)
    grid(d, view, w, h)
    layer = Image.new('RGB', ren.size, (255, 0, 220))
    full = Image.new('L', ren.size, 0)
    full.paste(m, (ox, oy))
    base.paste(layer, (0, 0), full)
    base.save(out_path)
    return out_path


def main():
    d = sys.argv[1]
    suffix = sys.argv[2] if len(sys.argv) > 2 else ''
    for view in CAL:
        p = os.path.join(d, view + suffix + '.png')
        if os.path.exists(p):
            print(overlay(p, view, os.path.join(d, view + suffix + '_overlay.png')))


if __name__ == '__main__':
    main()
