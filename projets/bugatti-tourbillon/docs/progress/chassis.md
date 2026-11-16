# Progress: chassis + engine (agent: chassis/powertrain)

Files: src/tb/parts/chassis.py, engine.py, chassis_lib.py (helpers: MeshBuilder, sweeps, emit).

## Plan
1. chassis_lib.py: MeshBuilder + primitives (chamfer box, cylinder, sweep/tube, helix) + emit()
2. chassis.py: tub, underfloor, front structure/e-axle/radiators, 4 corners suspension, rear subframe, plumbing
3. engine.py: V16 block/heads/intake/accessories, exhaust, gearbox + rear motor, lighting
4. checks: packaging bbox script (out/scripts/chassis/check_pack.py), renders, final-quality stats

## Status
- [ ] started: lib (in progress)

## Decisions
- Own tube/sweep code in chassis_lib (no depsgraph per call, radii variation); geo.* used where it fits.
- Geometry accumulated per material in MeshBuilders and emitted as few objects per sub-assembly.
- Engine crank axis z=0.30, banks at +-45 deg, block y 0.70..1.50; gearbox/rear motor y 1.52..1.95.
