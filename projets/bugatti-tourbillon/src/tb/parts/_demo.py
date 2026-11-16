"""Demo / smoke-test part (ignored by the normal build because of the leading underscore)."""
import math
from tb import geo, mats, rig, spec


def build(ctx):
    coll = ctx.collection('Demo')
    root = ctx.module_root('Demo')
    body = geo.box('Demo_Body', (1.6, 4.2, 0.5), (0, 0, 0.55), coll)
    geo.mod_bevel(body, 0.06, 4)
    mats.assign(body, 'paint_primary')
    top = geo.uv_sphere('Demo_Top', 0.7, (0, 0.1, 0.8), coll=coll, scale=(1.0, 1.6, 0.6))
    mats.assign(top, 'paint_secondary')
    cf = geo.box('Demo_Carbon', (1.9, 0.5, 0.05), (0, 2.0, 0.85), coll)
    mats.assign(cf, 'carbon_gloss')
    rig.adopt([body, top], root)
    geo.parent(cf, rig.wing_hinge())
    # door panel on the hinge
    door = geo.box('Demo_Door_L', (0.04, 1.4, 0.5), (0.82, -0.2, 0.6), coll)
    mats.assign(door, 'aluminum_brushed')
    geo.parent(door, rig.door_hinge('L'))
    door_r = geo.mirror_copy(door, 'Demo_Door_R', coll)
    geo.parent(door_r, rig.door_hinge('R'))
    # lights
    hl = geo.uv_sphere('Demo_Headlight', 0.08, (0.6, -2.1, 0.6), coll=coll)
    mats.assign(hl, 'emit_headlight')
    tl = geo.box('Demo_Tail', (1.6, 0.03, 0.04), (0, 2.11, 0.7), coll)
    mats.assign(tl, 'emit_tail')
    rig.adopt([hl, tl], root)
    # wheels
    for key, pos in spec.WHEELS.items():
        steer, spin = rig.wheel_pivots(key)
        t = spec.TIRE_F if key[0] == 'F' else spec.TIRE_R
        w = geo.cylinder('Demo_Wheel_' + key, t['radius'], t['width'], 'X', pos, coll=coll)
        mats.assign(w, 'rubber_tire')
        geo.parent(w, spin)
    g = geo.box('Demo_Glass', (1.2, 0.02, 0.5), (0, -1.0, 1.0), coll)
    mats.assign(g, 'glass')
    t = geo.curve_tube('Demo_Tube', [(0.9, -1, 0.3), (1.1, 0, 0.5), (0.9, 1, 0.3)], 0.02, coll=coll)
    mats.assign(t, 'chrome')
    tx = geo.text_mesh('Demo_Text', 'BUGATTI', 0.12, 0.004, coll=coll)
    geo.place(tx, (0, 2.13, 0.5), (90, 0, 180))
    mats.assign(tx, 'chrome')
    rig.adopt([g, t, tx], root)
