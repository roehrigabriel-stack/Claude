"""Master dimensional spec of the Bugatti Tourbillon model. SINGLE SOURCE OF TRUTH.

Units: metres. Angles: degrees unless stated.

COORDINATE FRAME (world space, never changes):
  * origin  : on the ground (z = 0), on the car centreline (x = 0),
              at the middle of the wheelbase (y = 0)
  * FRONT of the car points to -Y   (nose at y = Y_NOSE < 0, tail at y = Y_TAIL > 0)
  * +X is the car's LEFT side (driver side, the model is left-hand drive)
  * +Z is up

Values marked (official) come from Bugatti's published data, the others are
estimates taken from the blueprint / photos and may be refined. Parts must
READ these values instead of hard-coding their own copies.
"""
import math

# ----------------------------------------------------------------- overall
LENGTH = 4.671          # (official)
WIDTH = 2.051           # (official, without mirrors)
HEIGHT = 1.189          # (official)
WHEELBASE = 2.740       # (official)
FRONT_OVERHANG = 1.030  # blueprint estimate
REAR_OVERHANG = LENGTH - WHEELBASE - FRONT_OVERHANG   # 0.901

Y_FRONT_AXLE = -WHEELBASE / 2.0          # -1.370
Y_REAR_AXLE = WHEELBASE / 2.0            # +1.370
Y_NOSE = Y_FRONT_AXLE - FRONT_OVERHANG   # -2.400  foremost point of the body
Y_TAIL = Y_REAR_AXLE + REAR_OVERHANG     # +2.271  rearmost point of the body
HALF_WIDTH = WIDTH / 2.0                 # 1.0255  (reached at the rear haunches)
GROUND_CLEARANCE = 0.105                 # underfloor height (estimate)

# ----------------------------------------------------------------- wheels
def _tire(width, aspect, rim_in):
    rim_d = rim_in * 0.0254
    return dict(width=width, aspect=aspect, rim_in=rim_in, rim_d=rim_d,
                radius=rim_d / 2.0 + width * aspect, sidewall=width * aspect)

TIRE_F = _tire(0.285, 0.35, 20)   # 285/35 R20 (official)  radius ~0.3538
TIRE_R = _tire(0.345, 0.30, 21)   # 345/30 R21 (official)  radius ~0.3702
TRACK_F = 1.720                   # estimate (centre of tyre to centre of tyre)
TRACK_R = 1.660                   # estimate

# wheel centres (x, y, z).  L = +X, R = -X
WHEELS = {
    'FL': (+TRACK_F / 2.0, Y_FRONT_AXLE, TIRE_F['radius']),
    'FR': (-TRACK_F / 2.0, Y_FRONT_AXLE, TIRE_F['radius']),
    'RL': (+TRACK_R / 2.0, Y_REAR_AXLE, TIRE_R['radius']),
    'RR': (-TRACK_R / 2.0, Y_REAR_AXLE, TIRE_R['radius']),
}
# wheel-arch openings in the body side (centre on the axle, radius in the YZ plane)
ARCH_GAP = 0.045                        # tyre-to-arch gap
ARCH_R_F = TIRE_F['radius'] + ARCH_GAP  # ~0.399
ARCH_R_R = TIRE_R['radius'] + ARCH_GAP  # ~0.415
MAX_STEER_DEG = 28.0
BRAKE_DISC_F = dict(d=0.420, t=0.040)   # carbon-ceramic (estimate)
BRAKE_DISC_R = dict(d=0.400, t=0.036)

# ----------------------------------------------------------------- key side-profile stations
# (y, z) of the centreline / greenhouse, blueprint estimates. The body module owns
# the real surfaces; these are the shared anchors other parts may rely on.
Y_COWL = -1.200        # base of the windshield on the centreline
Z_COWL = 0.800
Y_HEADER = -0.520      # top of the windshield (roof header)
Z_HEADER = 1.140
Y_ROOF_PEAK = -0.050   # highest point of the roof
Z_ROOF_PEAK = HEIGHT
Y_BULKHEAD = 0.580     # rear cabin bulkhead / firewall (interior ends here)
Z_TAIL_TOP = 0.800     # top of the tail (light bar level ~0.72..0.80)
Z_NOSE_TIP = 0.560     # leading edge of the bonnet above the horseshoe

# ----------------------------------------------------------------- cabin envelope (shared by body + interior)
# The body greenhouse must ENCLOSE this envelope, the interior must stay INSIDE it.
CABIN = dict(
    z_floor=0.135,              # top face of the cabin floor
    y_footwell=-1.150,          # front end of the footwell (pedal box)
    y_dash_rear=-0.560,         # rear (occupant-side) face of the dashboard top roll
    z_dash_top=0.800,           # height of the dashboard top
    y_bulkhead=Y_BULKHEAD,      # rear wall behind the seats
    x_seat=0.335,               # lateral offset of each seat centreline
    h_point=(0.335, 0.020, 0.265),   # driver hip point (x, y, z)
    seat_back_angle=26.0,       # recline from vertical
    x_tunnel=0.140,             # half width of the centre console / tunnel
    z_tunnel=0.400,             # top of the centre tunnel between the seats
    x_inner_sill=0.640,         # inner face of the door sill (tub side wall)
    z_sill=0.340,               # top of the door sill
    x_inner_belt=0.700,         # interior half width at belt (window sill) height
    z_belt=0.820,               # window sill height at mid door
    x_inner_roof=0.470,         # interior half width at the roof rail
    z_headliner=1.130,          # inner roof height above the occupants
    steering_center=(0.335, -0.440, 0.700),   # centre of the steering wheel rim
    steering_tilt=22.0,         # column tilt from horizontal (wheel plane leans back)
    steering_diameter=0.360,
)

# ----------------------------------------------------------------- doors (dihedral / butterfly)
# Each door is hinged near the base of the A-pillar and swings up, forward and out.
# pivot = a point on the hinge axis, axis = unit direction (for the LEFT door;
# the right door is the mirror image in X). Positive angle opens the door.
#
# Right-hand rule check for the LEFT door (+X side, door body extends to +Y behind
# the pivot): a pure +X axis lifts the rear of the door (scissor door), a -Z
# component swings it outwards (conventional door). Butterfly = mostly +X with
# some -Z. With the values below the rear-bottom corner of the door ends about
# 0.65 m further out and 1.7 m above the ground when fully open.
DOOR_OPEN_DEG = 68.0
DOOR_HINGE_L = dict(
    pivot=(0.800, -0.930, 0.760),
    axis=(0.906, 0.000, -0.423),
)
DOOR_Y_FRONT = -0.955   # front shut line of the door (behind the front wheel arch)
DOOR_Y_REAR = 0.560     # rear shut line at mid height (it then follows the C-line)

# ----------------------------------------------------------------- active rear wing
WING = dict(
    pivot=(0.0, 1.900, 0.800),   # hinge line (across the car) under the wing leading edge
    max_angle=32.0,              # air-brake pitch
    lift=0.085,                  # how far the wing rises when deployed
)

# ----------------------------------------------------------------- control properties on the root object
# name: (default, min, max, description)
CTRL_PROPS = {
    'door_L':          (0.0, 0.0, 1.0, 'Left (driver) door: 0 closed, 1 fully open'),
    'door_R':          (0.0, 0.0, 1.0, 'Right door: 0 closed, 1 fully open'),
    'wing':            (0.0, 0.0, 1.0, 'Active rear wing / air brake: 0 flush, 1 deployed'),
    'steer':           (0.0, -1.0, 1.0, 'Front wheel steering, -1 right .. +1 left'),
    'wheel_spin':      (0.0, -1.0e6, 1.0e6, 'Wheel rotation in radians (front wheels; rears scaled by radius)'),
    'headlights':      (0.0, 0.0, 1.0, 'Main LED headlights'),
    'drl':             (0.0, 0.0, 1.0, 'Daytime running lights'),
    'taillights':      (0.0, 0.0, 1.0, 'Rear light bar'),
    'brake_lights':    (0.0, 0.0, 1.0, 'Brake light boost of the rear light bar'),
    'indicators':      (0.0, 0.0, 1.0, 'Turn indicators (all four)'),
    'interior_lights': (0.0, 0.0, 1.0, 'Cabin ambient lighting'),
    'cluster_glow':    (0.0, 0.0, 1.0, 'Instrument cluster and switch illumination'),
    'screen':          (0.0, 0.0, 1.0, 'Centre console pop-up screen: 0 hidden, 1 deployed'),
    'engine_glow':     (0.0, 0.0, 1.0, 'Engine bay accent lighting'),
}

ROOT_NAME = 'TOURBILLON'

# ----------------------------------------------------------------- colour scheme (reference: light blue + black two-tone)
# sRGB hex values; tb.mats converts to linear.
COLORS = dict(
    paint_primary='#9DBFD6',     # pale glacier blue (fenders, doors, bonnet flanks)
    paint_secondary='#0A0E14',   # blue-black (centre spine, roof, rear, lower body)
    leather_light='#B4C3CE',     # pale blue-grey leather
    leather_dark='#1B2733',      # deep navy
    caliper='#1E4C7A',
)


def mirror_x(p):
    """Mirror a point / axis from the left side to the right side."""
    return (-p[0], p[1], p[2])


def wheel_radius(key):
    return (TIRE_F if key[0] == 'F' else TIRE_R)['radius']
