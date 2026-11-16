"""tb.film: the showcase film. Timing comes from anim/timeline.json (shared with
the soundtrack generator); this module turns it into keyframes.

    from tb import build, showroom, film
    build.build(quality='final')
    film.make()                     # showroom + assembly + cameras + controls
    build.save('out/blend/tourbillon_film.blend')

Design
  * Parts fly in with keyframes on delta_location / delta_rotation_euler, so the
    rest transforms created by the part modules are never touched.
  * A part is invisible (hide_render / hide_viewport keyframes) until its
    fly-in starts.
  * One camera per shot, bound to timeline markers (Blender switches camera at
    each marker when rendering the animation).
"""
import fnmatch
import json
import math
import os

import bpy
from mathutils import Vector

from . import geo, rig, spec, studio, showroom

TIMELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'anim', 'timeline.json')
FILM_COLL = 'TB_Film'


# ----------------------------------------------------------------- timeline
class Timeline:
    def __init__(self, path=None):
        with open(path or TIMELINE) as fh:
            d = json.load(fh)
        self.fps = d['fps']
        self.duration = d['duration']
        self.sections = {s['name']: s for s in d['sections']}
        self.events = d['events']
        self.raw = d

    def f(self, t):
        """seconds -> frame number (frame 1 = t 0)."""
        return int(round(t * self.fps)) + 1

    def sec(self, name):
        s = self.sections[name]
        return s['t0'], s['t1']

    def event(self, label=None, type=None):
        for e in self.events:
            if (label is None or e.get('label') == label) and (type is None or e['type'] == type):
                return e['t']
        raise KeyError((label, type))

    def land(self, label):
        return self.event(label=label, type='land')

    @property
    def last_frame(self):
        return int(round(self.duration * self.fps))


# ----------------------------------------------------------------- keyframe helpers
def _set_interp(id_block, data_path, frames, interpolation='BEZIER', easing='AUTO', index=None):
    ad = id_block.animation_data
    if not ad or not ad.action:
        return
    for fc in ad.action.fcurves:
        if fc.data_path != data_path:
            continue
        if index is not None and fc.array_index != index:
            continue
        for kp in fc.keyframe_points:
            if frames is None or any(abs(kp.co.x - fr) < 0.5 for fr in frames):
                kp.interpolation = interpolation
                kp.easing = easing
                if interpolation == 'BEZIER':
                    kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.update()


def key(id_block, data_path, value, frame, interpolation='BEZIER', easing='AUTO'):
    setattr_path(id_block, data_path, value)
    id_block.keyframe_insert(data_path=data_path, frame=frame)
    _set_interp(id_block, data_path, [frame], interpolation, easing)


def setattr_path(id_block, data_path, value):
    if data_path.startswith('["'):
        id_block[data_path[2:-2]] = value
    else:
        setattr(id_block, data_path, value)


def descendants(ob):
    out = []
    for ch in ob.children:
        out.append(ch)
        out.extend(descendants(ch))
    return out


def select(patterns):
    """Objects whose name matches any of the fnmatch patterns (case sensitive)."""
    if isinstance(patterns, str):
        patterns = [patterns]
    out = []
    for ob in bpy.data.objects:
        if any(fnmatch.fnmatchcase(ob.name, p) for p in patterns):
            out.append(ob)
    return out


def set_visible_from(objs, frame):
    """Hide objects (render + viewport) before `frame`, show them from `frame` on."""
    for ob in objs:
        for path in ('hide_render', 'hide_viewport'):
            setattr(ob, path, True)
            ob.keyframe_insert(path, frame=max(frame - 1, 0))
            setattr(ob, path, False)
            ob.keyframe_insert(path, frame=frame)
            _set_interp(ob, path, None, 'CONSTANT')


def fly_in(units, f0, f1, offset=(0, 0, 0), rot_deg=(0, 0, 0), easing='EXPO', settle=True):
    """Animate `units` (objects or pivots) from an offset pose into their rest pose.

    f0 = first visible frame (start of the move), f1 = landing frame.
    offset: world-axis translation at f0; rot_deg: extra XYZ euler rotation at f0.
    Descendants of every unit follow (parenting) and share the visibility switch.
    settle adds a tiny overshoot so the part visibly 'clicks' into place."""
    done = []
    for ob in units:
        vis = [ob] + descendants(ob)
        set_visible_from(vis, f0)
        ob.delta_location = Vector(offset)
        ob.keyframe_insert('delta_location', frame=f0)
        if settle:
            ob.delta_location = Vector(offset) * -0.012
            ob.keyframe_insert('delta_location', frame=f1)
            ob.delta_location = (0, 0, 0)
            ob.keyframe_insert('delta_location', frame=f1 + 3)
        else:
            ob.delta_location = (0, 0, 0)
            ob.keyframe_insert('delta_location', frame=f1)
        _set_interp(ob, 'delta_location', [f0], easing, 'EASE_OUT')
        _set_interp(ob, 'delta_location', [f1, f1 + 3], 'SINE', 'EASE_IN_OUT')
        if any(abs(a) > 1e-6 for a in rot_deg) and ob.rotation_mode not in ('AXIS_ANGLE', 'QUATERNION'):
            ob.delta_rotation_euler = [math.radians(a) for a in rot_deg]
            ob.keyframe_insert('delta_rotation_euler', frame=f0)
            ob.delta_rotation_euler = (0, 0, 0)
            ob.keyframe_insert('delta_rotation_euler', frame=f1)
            _set_interp(ob, 'delta_rotation_euler', [f0], easing, 'EASE_OUT')
        done.append(ob)
    return done


# ----------------------------------------------------------------- cameras
class Shots:
    def __init__(self, tl):
        self.tl = tl
        self.coll = geo.collection(FILM_COLL)
        self.cams = []

    def add(self, name, t0, t1, keys, lens=50.0, fstop=None, interpolation='LINEAR', focus=None, roll=0.0):
        """One shot = one camera. keys: [(t, eye, target), ...] or [(t, eye, target, lens), ...].
        focus: None -> focus on the look-at target; or a fixed point (x, y, z)."""
        s = bpy.context.scene
        cd = bpy.data.cameras.new('CAM_' + name)
        cd.lens = lens
        cd.sensor_width = 36.0
        cd.clip_start, cd.clip_end = 0.03, 400.0
        cam = bpy.data.objects.new('CAM_' + name, cd)
        geo.link(cam, self.coll)
        tgt = geo.empty('CAMTGT_' + name, (0, 0, 0), self.coll, size=0.1, display='SPHERE')
        con = cam.constraints.new('TRACK_TO')
        con.target = tgt
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'
        for k in keys:
            fr = self.tl.f(k[0])
            cam.location = k[1]
            cam.keyframe_insert('location', frame=fr)
            tgt.location = k[2]
            tgt.keyframe_insert('location', frame=fr)
            if len(k) > 3:
                cd.lens = k[3]
                cd.keyframe_insert('lens', frame=fr)
        for idb, path in ((cam, 'location'), (tgt, 'location'), (cd, 'lens')):
            _set_interp(idb, path, None, interpolation, 'EASE_IN_OUT' if interpolation != 'LINEAR' else 'AUTO')
        if fstop:
            cd.dof.use_dof = True
            cd.dof.aperture_fstop = fstop
            if focus is None:
                cd.dof.focus_object = tgt
            else:
                fo = geo.empty('CAMFOCUS_' + name, focus, self.coll, size=0.05)
                cd.dof.focus_object = fo
        m = s.timeline_markers.new(name, frame=self.tl.f(t0))
        m.camera = cam
        self.cams.append((name, cam, tgt, t0, t1))
        return cam, tgt


# ----------------------------------------------------------------- the film
# Assembly rules: (timeline 'land' label, object name patterns, start offset, start rotation, lead time s)
# Patterns are matched against the direct movable units of the car (see _units()).
ASSEMBLY = [
    ('front subframe', ['MOD_Chassis_Front'],                              (0.0, -7.0, 0.0),  (0, 0, 0),    0.75),
    ('rear subframe',  ['MOD_Chassis_Rear'],                               (0.0, 7.0, 0.0),   (0, 0, 0),    0.75),
    ('engine',         ['MOD_Engine'],                                     (0.0, 0.6, 3.6),   (-12, 0, 0),  0.95),
    ('gearbox',        ['MOD_Engine_Gearbox'],                             (0.0, 6.0, 0.5),   (0, 0, 0),    0.80),
    ('exhaust',        ['MOD_Engine_Exhaust'],                             (0.0, 6.5, 1.2),   (10, 0, 0),   0.65),
    ('wheel FL',       ['Wheel_FL_Steer'],                                 (4.5, 0.0, 0.0),   (0, 0, 0),    0.60),
    ('wheel FR',       ['Wheel_FR_Steer'],                                 (-4.5, 0.0, 0.0),  (0, 0, 0),    0.60),
    ('wheel RL',       ['Wheel_RL_Steer'],                                 (4.5, 0.0, 0.0),   (0, 0, 0),    0.60),
    ('wheel RR',       ['Wheel_RR_Steer'],                                 (-4.5, 0.0, 0.0),  (0, 0, 0),    0.60),
    ('interior',       ['MOD_Interior*'],                                  (0.0, 0.0, 3.4),   (0, 0, 0),    0.75),
    ('sills',          ['Body_Sill_L*'],                                   (3.5, 0.0, 0.0),   (0, 0, 0),    0.60),
    ('sills',          ['Body_Sill_R*'],                                   (-3.5, 0.0, 0.0),  (0, 0, 0),    0.60),
    ('rear haunches',  ['Body_Rear_L*', 'Body_Liner_RL*'],                 (3.2, 2.2, 0.8),   (0, 0, -18),  0.70),
    ('rear haunches',  ['Body_Rear_R*', 'Body_Liner_RR*'],                 (-3.2, 2.2, 0.8),  (0, 0, 18),   0.70),
    ('engine deck',    ['Body_Deck*', 'Glass_Engine*'],                    (0.0, 3.0, 2.6),   (-20, 0, 0),  0.70),
    ('roof and glass', ['Body_Roof*', 'Glass_Windshield*', 'Glass_Roof*'], (0.0, -0.5, 3.2),  (8, 0, 0),    0.75),
    ('front fenders',  ['Body_Fender_F_L*', 'Body_Liner_FL*'],             (3.2, -2.2, 0.6),  (0, 0, 16),   0.70),
    ('front fenders',  ['Body_Fender_F_R*', 'Body_Liner_FR*'],             (-3.2, -2.2, 0.6), (0, 0, -16),  0.70),
    ('bonnet',         ['Body_Bonnet*'],                                   (0.0, -2.0, 2.8),  (18, 0, 0),   0.70),
    ('front fascia',   ['Body_Bumper_F*', 'MOD_Front*', 'MOD_Lights*'],    (0.0, -6.5, 0.3),  (0, 0, 0),    0.70),
    ('rear fascia',    ['Body_Tail*', 'MOD_Rear*', 'MOD_Aero*', 'HINGE_Wing'], (0.0, 6.5, 0.4), (0, 0, 0),  0.70),
    ('doors close',    ['HINGE_Door_L'],                                   (3.6, 0.0, 0.5),   (0, 0, 0),    0.95),
    ('doors close',    ['HINGE_Door_R'],                                   (-3.6, 0.0, 0.5),  (0, 0, 0),    0.95),
]
# units that are on stage from the first frame
STATIC_UNITS = ['MOD_Chassis', 'MOD_Chassis_Tub']
# anything else lands with this label (from above)
DEFAULT_LABEL = 'roof and glass'


def _units():
    """Movable units = direct children of the root, except MOD_Body / MOD_Glass which
    are expanded into their own children (individual panels)."""
    root = rig.ctrl()
    out = []
    for ch in root.children:
        if ch.name in ('MOD_Body', 'MOD_Glass'):
            out.extend(ch.children)
        else:
            out.append(ch)
    return out


def assemble(tl, verbose=True):
    units = _units()
    used = set()
    for label, patterns, offset, rot, lead in ASSEMBLY:
        try:
            t1 = tl.land(label)
        except KeyError:
            continue
        sel = [u for u in units if u.name not in used and any(fnmatch.fnmatchcase(u.name, p) for p in patterns)]
        if not sel:
            if verbose:
                print('[film] no unit for', label, patterns)
            continue
        # doors land a little before their 'close' cue: they arrive open, then swing shut
        t_land = t1 - 0.45 if label == 'doors close' else t1
        fly_in(sel, tl.f(t_land - lead), tl.f(t_land), offset, rot)
        used.update(u.name for u in sel)
    rest = [u for u in units if u.name not in used and u.name not in STATIC_UNITS]
    if rest:
        t1 = tl.land(DEFAULT_LABEL)
        if verbose:
            print('[film] default fly-in for:', ', '.join(u.name for u in rest))
        fly_in(rest, tl.f(t1 - 0.7), tl.f(t1), (0.0, 0.0, 3.2))
    return used


def controls(tl):
    """Keyframes of the control properties (doors, lights, wing, screen, wheels)."""
    f = tl.f
    K = rig.key_prop
    # doors: arrive open during assembly, close on the cue
    t_close = tl.land('doors close')
    for d in ('door_L', 'door_R'):
        K(d, 1.0, f(0.0))
        K(d, 1.0, f(t_close - 0.45))
        K(d, 0.0, f(t_close))
    # wheels spin down as they are fitted
    t_w0, t_w1 = tl.land('wheel FL') - 0.6, tl.land('wheel RR') + 0.25
    K('wheel_spin', -14.0, f(t_w0))
    K('wheel_spin', 0.0, f(t_w1))
    # ignition: lights come on in a short staggered sequence
    t_ig = tl.event(type='ignition')
    for prop, dt, val in (('drl', 0.00, 1.0), ('taillights', 0.06, 1.0), ('headlights', 0.22, 1.0),
                          ('cluster_glow', 0.30, 1.0), ('engine_glow', 0.10, 1.0)):
        K(prop, 0.0, f(t_ig + dt) - 1)
        K(prop, val, f(t_ig + dt) + 2)
    # tiny flicker on the headlights right at ignition
    K('headlights', 0.0, f(t_ig + 0.22) - 1)
    K('headlights', 1.0, f(t_ig + 0.22) + 1)
    K('headlights', 0.35, f(t_ig + 0.22) + 3)
    K('headlights', 1.0, f(t_ig + 0.22) + 5)
    # active wing
    t_up, t_dn = tl.event(type='wing_up'), tl.event(type='wing_down')
    K('wing', 0.0, f(t_up))
    K('wing', 1.0, f(t_up + 0.55))
    K('wing', 1.0, f(t_dn))
    K('wing', 0.0, f(t_dn + 0.6))
    K('brake_lights', 0.0, f(t_up))
    K('brake_lights', 1.0, f(t_up + 0.2))
    K('brake_lights', 1.0, f(t_dn))
    K('brake_lights', 0.0, f(t_dn + 0.3))
    # doors open for the interior, then close for the finale
    t_do, t_dc = tl.event(type='door_open'), tl.event(type='door_close')
    t_shut = tl.land('doors shut')
    for d in ('door_L', 'door_R'):
        K(d, 0.0, f(t_do))
        K(d, 1.0, f(t_do + 1.3))
        K(d, 1.0, f(t_dc))
        K(d, 0.0, f(t_shut))
    K('interior_lights', 0.0, f(t_do))
    K('interior_lights', 1.0, f(t_do + 0.8))
    K('interior_lights', 1.0, f(t_shut))
    K('interior_lights', 0.3, f(t_shut + 0.5))
    t_sc = tl.event(type='screen')
    K('screen', 0.0, f(t_sc))
    K('screen', 1.0, f(t_sc + 0.9))
    K('screen', 1.0, f(t_dc))
    K('screen', 0.0, f(t_dc + 0.8))


def lighting(tl, show):
    """Showroom light choreography: sweep in the dark, slow build, full at ignition."""
    f = tl.f
    base = showroom.base_energies(show)
    t_ig = tl.event(type='ignition')
    a0, a1 = tl.sec('assembly')
    levels = {  # (time, fraction of base energy)
        'key':     [(0.0, 0.0), (a0, 0.10), (a1, 0.45), (t_ig, 0.55), (t_ig + 0.5, 1.0)],
        'strip_l': [(0.0, 0.0), (a0, 0.15), (a1, 0.55), (t_ig + 0.5, 1.0)],
        'strip_r': [(0.0, 0.0), (a0, 0.10), (a1, 0.50), (t_ig + 0.5, 1.0)],
        'rim_f':   [(0.0, 0.0), (a0 + 1.0, 0.0), (a1, 0.5), (t_ig + 0.5, 1.0)],
        'rim_b':   [(0.0, 0.05), (a0, 0.35), (a1, 0.7), (t_ig + 0.5, 1.0)],
    }
    for k, keys in levels.items():
        ld = show[k].data
        for t, frac in keys:
            ld.energy = base[k] * frac
            ld.keyframe_insert('energy', frame=f(t))
        _set_interp(ld, 'energy', None, 'BEZIER')
    # intro sweep: a narrow strip of light travels from nose to tail
    sw = show['sweep']
    t_sw = tl.event(type='light_sweep')
    sw.location = (0.0, -4.6, 2.6)
    sw.keyframe_insert('location', frame=f(t_sw))
    sw.location = (0.0, 4.6, 2.6)
    sw.keyframe_insert('location', frame=f(t_sw + 2.4))
    _set_interp(sw, 'location', None, 'SINE', 'EASE_IN_OUT')
    for t, frac in ((0.0, 0.0), (t_sw, 0.0), (t_sw + 0.5, 1.0), (t_sw + 1.9, 1.0), (t_sw + 2.6, 0.0)):
        sw.data.energy = base['sweep'] * frac
        sw.data.keyframe_insert('energy', frame=f(t))
    # slats and LED ring fade up with the room
    for name, peak in (('Showroom_Slat', 5.0), ('Showroom_LED_Ring', 6.0)):
        m = bpy.data.materials.get(name)
        if not m:
            continue
        sock = m.node_tree.nodes['Emission'].inputs['Strength']
        for t, frac in ((0.0, 0.02), (a0, 0.15), (a1, 0.5), (t_ig + 0.5, 1.0)):
            sock.default_value = peak * frac
            sock.keyframe_insert('default_value', frame=f(t))


def turntable(tl, show, degrees=24.0):
    """Slow rotation of car + turntable during the finale."""
    t0, t1 = tl.sec('finale')
    root = rig.ctrl()
    for ob in (root, show.get('turntable'), show.get('ring')):
        if ob is None:
            continue
        ob.rotation_mode = 'XYZ'
        ob.rotation_euler = (0, 0, 0)
        ob.keyframe_insert('rotation_euler', frame=tl.f(t0))
        ob.rotation_euler = (0, 0, math.radians(degrees))
        ob.keyframe_insert('rotation_euler', frame=tl.f(t1))
        _set_interp(ob, 'rotation_euler', None, 'LINEAR')


def cameras(tl):
    """Shot list. All positions in metres, world space (car nose towards -Y, driver side +X)."""
    S = Shots(tl)
    sx = spec.CABIN['x_seat']
    sc = spec.CABIN['steering_center']
    i0, i1 = tl.sec('intro')
    a0, a1 = tl.sec('assembly')
    g0, g1 = tl.sec('ignition')
    h0, h1 = tl.sec('hero_front')
    p0, p1 = tl.sec('profile')
    r0, r1 = tl.sec('rear')
    d0, d1 = tl.sec('doors')
    n0, n1 = tl.sec('interior')
    e0, e1 = tl.sec('finale')
    t_eng = tl.land('engine')
    t_int = tl.land('interior')
    # 1. intro + first assembly beats: high wide front-left, slow push
    S.add('01_wide_open', i0, t_eng - 0.5,
          [(i0, (6.4, -7.4, 3.3), (0.0, 0.1, 0.35)), (t_eng - 0.5, (5.3, -6.3, 2.7), (0.0, 0.2, 0.40))], lens=40)
    # 2. engine drop and wheels: low rear-left, close to the mechanicals
    S.add('02_engine_low', t_eng - 0.5, t_int - 0.4,
          [(t_eng - 0.5, (3.9, 4.6, 1.55), (0.0, 0.9, 0.55)), (t_int - 0.4, (4.6, 3.2, 1.25), (0.0, 0.5, 0.50))], lens=40)
    # 3. body panels: front-left three-quarter, orbiting
    S.add('03_body_panels', t_int - 0.4, a1,
          [(t_int - 0.4, (5.6, -4.6, 2.3), (0.0, 0.0, 0.55)), (a1, (4.3, -5.9, 1.55), (0.0, -0.1, 0.55))], lens=42)
    # 4. ignition: low dead-ahead, headlights fire into the lens
    S.add('04_ignition', g0, g1,
          [(g0, (0.0, -7.6, 0.62), (0.0, 0.0, 0.60)), (g1, (0.0, -7.0, 0.60), (0.0, 0.0, 0.60))], lens=75)
    # 5. hero: low front three-quarter arc
    S.add('05_hero_front', h0, h1,
          [(h0, (2.5, -5.6, 0.48), (0.0, -0.6, 0.55)), (h1, (4.3, -4.3, 0.70), (0.0, -0.4, 0.55))], lens=50, fstop=5.6)
    # 6. profile: long-lens slide along the flank, front wheel to rear haunch
    S.add('06_profile', p0, p1,
          [(p0, (7.5, -1.9, 0.95), (0.0, -1.2, 0.60)), (p1, (7.5, 1.5, 0.95), (0.0, 0.9, 0.62))], lens=105, fstop=5.6)
    # 7. rear: light bar, diffuser, wing rising
    S.add('07_rear', r0, r1,
          [(r0, (-3.4, 5.4, 1.05), (0.0, 1.5, 0.62)), (r1, (-1.1, 6.3, 0.80), (0.0, 1.6, 0.62))], lens=50, fstop=5.6)
    # 8. doors rise: from front-left, gliding towards the driver door opening
    S.add('08_doors', d0, d1,
          [(d0, (4.9, -3.2, 1.75), (0.2, -0.3, 0.80)), (d1, (2.5, -1.2, 1.30), (0.25, -0.35, 0.75))], lens=35, fstop=4.0)
    # 9. interior A: over the driver's shoulder onto wheel and cluster
    nm = (n0 + n1) / 2.0
    S.add('09_interior_cluster', n0, nm,
          [(n0, (sx + 0.10, 0.36, 1.00), (sc[0], sc[1], sc[2] + 0.02)), (nm, (sx + 0.02, 0.10, 0.93), (sc[0], sc[1], sc[2] + 0.02))],
          lens=30, fstop=2.8)
    # 10. interior B: glide over the crystal console towards the dashboard
    S.add('10_interior_console', nm, n1,
          [(nm, (-0.20, 0.32, 0.86), (0.0, -0.35, 0.52)), (n1, (-0.06, 0.12, 0.82), (0.0, -0.50, 0.56))],
          lens=32, fstop=2.8)
    # 11. finale: wide, rising, turntable turning
    S.add('11_finale', e0, e1,
          [(e0, (5.0, -6.0, 1.45), (0.0, 0.0, 0.55)), (e1, (5.9, -7.2, 2.3), (0.0, 0.0, 0.55))], lens=45)
    return S


def make(timeline_path=None, res=(1280, 720), samples=28):
    """Build the showroom and apply the whole film animation to the current scene."""
    tl = Timeline(timeline_path)
    s = bpy.context.scene
    s.render.fps = tl.fps
    s.frame_start = 1
    s.frame_end = tl.last_frame
    show = showroom.build()
    assemble(tl)
    controls(tl)
    lighting(tl, show)
    turntable(tl, show)
    shots = cameras(tl)
    studio.setup_render(res=res, samples=samples)
    s.render.use_persistent_data = True
    s.camera = shots.cams[0][1]
    s.frame_set(1)
    return tl, show, shots
