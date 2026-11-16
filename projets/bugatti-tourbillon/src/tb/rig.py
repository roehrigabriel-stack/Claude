"""tb.rig: control object, drivers and hierarchy conventions.

Everything the user can operate is a custom property of ONE Empty named
spec.ROOT_NAME ('TOURBILLON'): doors, wing, steering, wheel spin, all lights.
Drivers use non-scripted SUM drivers with a Generator F-modifier, so they keep
working when Blender's "auto-run Python scripts" is disabled.

Hierarchy
  TOURBILLON                      root Empty with the custom properties
    MOD_<Module>                  one Empty per module (body, interior, ...);
                                  the assembly animation moves these
      objects ...
    HINGE_Door_L / HINGE_Door_R   driven pivots; door parts are parented to them
    HINGE_Wing
    Wheel_<FL|FR|RL|RR>_Steer -> Wheel_<..>_Spin
"""
import math
import bpy
from mathutils import Vector

from . import spec, geo


# ----------------------------------------------------------------- root / control
def ctrl():
    """Return the root control Empty, creating it (and its properties) on first use."""
    ob = bpy.data.objects.get(spec.ROOT_NAME)
    if ob is None:
        ob = geo.empty(spec.ROOT_NAME, (0, 0, 0), geo.collection('TB_Rig'), size=0.6, display='ARROWS')
        for name, (default, lo, hi, desc) in spec.CTRL_PROPS.items():
            ob[name] = float(default)
            ui = ob.id_properties_ui(name)
            ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=desc, default=float(default))
            ob.property_overridable_library_set('["%s"]' % name, True)
    return ob


def set_prop(name, value):
    """Set a control property now (use for test renders)."""
    c = ctrl()
    c[name] = float(value)
    c.update_tag()
    return c


def key_prop(name, value, frame, interpolation='BEZIER'):
    """Keyframe a control property (used by the animation)."""
    c = ctrl()
    c[name] = float(value)
    c.keyframe_insert(data_path='["%s"]' % name, frame=frame)
    if c.animation_data and c.animation_data.action:
        for fc in c.animation_data.action.fcurves:
            if fc.data_path == '["%s"]' % name:
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - frame) < 0.5:
                        kp.interpolation = interpolation
    return c


def module_root(name, location=(0.0, 0.0, 0.0)):
    """Empty that owns one module, child of the root. Get-or-create."""
    full = 'MOD_' + name
    ob = bpy.data.objects.get(full)
    if ob is None:
        ob = geo.empty(full, location, geo.collection('TB_Rig'), size=0.25, display='CUBE')
        geo.parent(ob, ctrl())
    return ob


def adopt(objs, parent_obj):
    """Parent objects (keeping world transforms) to a module root / hinge."""
    for ob in objs:
        if ob is not None and ob is not parent_obj and ob.parent is None:
            geo.parent(ob, parent_obj)
    return parent_obj


# ----------------------------------------------------------------- drivers
def drive(id_block, data_path, prop, scale=1.0, offset=0.0, index=-1):
    """Drive `id_block.data_path[index]` = offset + scale * TOURBILLON[prop].

    id_block may be an Object, Light, Material node tree owner, etc.
    Non-scripted (always evaluated, no auto-run permission needed)."""
    c = ctrl()
    try:
        id_block.driver_remove(data_path, index) if index >= 0 else id_block.driver_remove(data_path)
    except (TypeError, RuntimeError):
        pass
    fc = id_block.driver_add(data_path, index) if index >= 0 else id_block.driver_add(data_path)
    drv = fc.driver
    drv.type = 'SUM'
    for v in list(drv.variables):
        drv.variables.remove(v)
    var = drv.variables.new()
    var.name = 'var'
    var.type = 'SINGLE_PROP'
    var.targets[0].id = c
    var.targets[0].data_path = '["%s"]' % prop
    for m in list(fc.modifiers):
        fc.modifiers.remove(m)
    mod = fc.modifiers.new('GENERATOR')
    mod.mode = 'POLYNOMIAL'
    mod.poly_order = 1
    mod.coefficients = (offset, scale)
    return fc


def drive_node_value(material, node_name, prop, scale=1.0, offset=0.0):
    """Drive the output of a Value node inside a material by a control property."""
    path = 'nodes["%s"].outputs[0].default_value' % node_name
    return drive(material.node_tree, path, prop, scale, offset)


def drive_light(light_obj, prop, watts):
    """Drive a lamp's power (energy) by a control property: energy = watts * prop."""
    return drive(light_obj.data, 'energy', prop, scale=watts)


# ----------------------------------------------------------------- hinges
def hinge(name, pivot, axis, prop, max_angle_deg, parent_obj=None, translate=None):
    """Driven pivot Empty. Get-or-create by name ('HINGE_<name>').

    Rotates about `axis` (world direction at build time) through `pivot` by
    max_angle_deg * TOURBILLON[prop]. Optional `translate` = (dx, dy, dz) adds a
    linear motion at prop = 1 (sliding / rising parts). Parent parts to the
    returned Empty with geo.parent(part, hinge) or rig.adopt([...], hinge)."""
    full = 'HINGE_' + name
    ob = bpy.data.objects.get(full)
    if ob is not None:
        return ob
    ob = geo.empty(full, pivot, geo.collection('TB_Rig'), size=0.12, display='SPHERE')
    geo.parent(ob, parent_obj or ctrl())
    a = Vector(axis).normalized()
    ob.rotation_mode = 'AXIS_ANGLE'
    ob.rotation_axis_angle = (0.0, a.x, a.y, a.z)
    if abs(max_angle_deg) > 1e-9:
        drive(ob, 'rotation_axis_angle', prop, scale=math.radians(max_angle_deg), index=0)
    if translate is not None:
        base = Vector(ob.location)
        for i in range(3):
            if abs(translate[i]) > 1e-9:
                drive(ob, 'location', prop, scale=translate[i], offset=base[i], index=i)
    return ob


def door_hinge(side):
    """Hinge Empty of the left ('L') or right ('R') door (from spec.DOOR_HINGE_L)."""
    h = spec.DOOR_HINGE_L
    pivot, axis = h['pivot'], h['axis']
    if side == 'R':
        pivot = spec.mirror_x(pivot)
        # mirrored axis direction flips sign so that a positive angle still opens the door
        axis = (axis[0], -axis[1], -axis[2])
    return hinge('Door_' + side, pivot, axis, 'door_' + side, spec.DOOR_OPEN_DEG)


def wing_hinge():
    w = spec.WING
    return hinge('Wing', w['pivot'], (1.0, 0.0, 0.0), 'wing', -w['max_angle'], translate=(0.0, 0.0, w['lift']))


def wheel_pivots(key):
    """(steer_empty, spin_empty) for wheel 'FL' | 'FR' | 'RL' | 'RR'. Get-or-create.

    steer: rotates about world Z (front wheels only, driven by 'steer')
    spin : child of steer, rotates about the axle (local X, driven by 'wheel_spin').
    Parent rotating parts (tyre, rim, disc) to spin; calipers / uprights to steer."""
    sname, pname = 'Wheel_%s_Steer' % key, 'Wheel_%s_Spin' % key
    steer = bpy.data.objects.get(sname)
    spin = bpy.data.objects.get(pname)
    if steer is None:
        pos = spec.WHEELS[key]
        steer = geo.empty(sname, pos, geo.collection('TB_Rig'), size=0.2, display='CIRCLE')
        geo.parent(steer, ctrl())
        if key[0] == 'F':
            drive(steer, 'rotation_euler', 'steer', scale=math.radians(spec.MAX_STEER_DEG), index=2)
        spin = geo.empty(pname, pos, geo.collection('TB_Rig'), size=0.15, display='SINGLE_ARROW')
        geo.parent(spin, steer)
        # forward travel (-Y) = positive rotation about +X for every wheel
        ratio = spec.TIRE_F['radius'] / spec.wheel_radius(key)
        drive(spin, 'rotation_euler', 'wheel_spin', scale=ratio, index=0)
    return steer, spin


def all_car_objects():
    """Every object below the root (recursive)."""
    out = []

    def walk(ob):
        for ch in ob.children:
            out.append(ch)
            walk(ch)
    walk(ctrl())
    return out
