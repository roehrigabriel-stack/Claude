"""Wheels, tyres and brakes of the Bugatti Tourbillon (four corners).

Per corner K in FL, FR, RL, RR (objects named Wheel_<Thing>_<K>):
  rotating (parented to Wheel_<K>_Spin):  Wheel_Tyre, Wheel_Barrel, Wheel_Spokes, Wheel_Cap,
                                          Wheel_Bolts, Wheel_Disc, Wheel_Bell, Wheel_Bobbins
  steering only (parented to Wheel_<K>_Steer): Wheel_Caliper, Wheel_CaliperText, Wheel_Pads,
                                          Wheel_Carrier
Left wheels are built, right wheels are true mirror copies (geo.mirror_copy), except the
tyre and the lettering, which are rebuilt for the right side so the text reads correctly.
"""
from tb import geo, mats, rig, spec
from tb.parts import wheels_lib as wl


def _corner(ctx, coll, key_l, key_r):
    q = ctx.quality
    out = {}
    # ---------------- left side, local frame, then baked to world
    barrel, spokes, cap, bolts = wl.build_rim('Wheel_Rim_' + key_l, key_l, q, coll)
    disc, bell, bob = wl.build_disc('Wheel_Brake_' + key_l, key_l, q, coll)
    cal, pads = wl.build_caliper('Wheel_Caliper_' + key_l, key_l, q, coll)
    carrier = wl.build_carrier('Wheel_Carrier_' + key_l, key_l, q, coll)
    spin_l = dict(Barrel=barrel, Spokes=spokes, Cap=cap, Bolts=bolts, Disc=disc, Bell=bell, Bobbins=bob)
    steer_l = dict(Caliper=cal, Pads=pads, Carrier=carrier)
    for d in (spin_l, steer_l):
        for thing, ob in d.items():
            wl.bake(ob, key_l, 1)
            ob.name = 'Wheel_%s_%s' % (thing, key_l)
            ob.data.name = ob.name
    tyre_l = wl.build_tyre('Wheel_Tyre_' + key_l, key_l, 1, q, coll)
    ctext_l = wl.build_caliper_text('Wheel_CaliperText_' + key_l, key_l, 1, coll)
    wl.bake(ctext_l, key_l, 1)
    spin_l['Tyre'] = tyre_l
    steer_l['CaliperText'] = ctext_l

    # ---------------- right side: mirrored copies (+ rebuilt tyre / lettering)
    spin_r, steer_r = {}, {}
    for thing, ob in spin_l.items():
        if thing == 'Tyre':
            continue
        spin_r[thing] = geo.mirror_copy(ob, 'Wheel_%s_%s' % (thing, key_r), coll)
    for thing, ob in steer_l.items():
        if thing == 'CaliperText':
            continue
        steer_r[thing] = geo.mirror_copy(ob, 'Wheel_%s_%s' % (thing, key_r), coll)
    spin_r['Tyre'] = wl.build_tyre('Wheel_Tyre_' + key_r, key_r, -1, q, coll)
    ct = wl.build_caliper_text('Wheel_CaliperText_' + key_r, key_r, -1, coll)
    wl.bake(ct, key_r, -1)
    steer_r['CaliperText'] = ct

    # ---------------- rig
    for key, sp, st in ((key_l, spin_l, steer_l), (key_r, spin_r, steer_r)):
        steer, spin = rig.wheel_pivots(key)
        for ob in sp.values():
            geo.parent(ob, spin)
        for ob in st.values():
            geo.parent(ob, steer)
        out[key] = (sp, st)
    return out


def build(ctx):
    coll = ctx.collection('Wheels')
    info = {}
    info.update(_corner(ctx, coll, 'FL', 'FR'))
    info.update(_corner(ctx, coll, 'RL', 'RR'))
    # clean up helper objects that may linger (array pivots etc.)
    ctx.data['wheels'] = {k: dict(tyre='Wheel_Tyre_' + k, spokes='Wheel_Spokes_' + k,
                                  caliper='Wheel_Caliper_' + k, disc='Wheel_Disc_' + k)
                          for k in spec.WHEELS}
