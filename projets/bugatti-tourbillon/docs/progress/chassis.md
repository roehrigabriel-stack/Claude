# Progress: chassis + engine

Files: src/tb/parts/chassis.py, engine.py, chassis_lib.py (MeshBuilder/Parts/emit helpers).
Check script: out/scripts/chassis/check_pack.py (packaging limits, per object; -- --quality final).

## Done (both build cleanly, 0 packaging violations, preview and final)
- Tub (carbon floor, sills, front bulkhead + dash beam, firewall + gold shield, tunnel with HV ends), underfloor panel.
- Front: subframe, towers, crash cans + bumper beam + horseshoe, radiator (leaning), 2 motors + reduction cases + inverter, driveshafts/boots, rack, ARB, rocker/pushrod/coil-over (teal springs), steered uprights on hinges HINGE_Chassis_Steer_L/R.
- Rear: subframe rails, towers, deck beam (y 1.64) with dampers, wishbones, toe links, ARB, shafts, side radiators + hoses.
- Engine: crankcase, blocks, heads, cam covers + plaque (BUGATTI/V16 text), airboxes + silver trumpet rings, runners, throttle bodies, rails, front drive + belt, headers (8/bank, merge in 2 collectors), silencers, 2 tailpipes/side ending y=2.05, DCT + rear e-motor, glow strips + 3 lamps (engine_glow).
- Triangles: preview 126k total, final 195k (chassis 67k, engine 127k).

## Sub-roots
MOD_Chassis_Tub (tub, underfloor), MOD_Chassis_Front (front structure, suspension, steer hinges), MOD_Chassis_Rear (subframe, suspension, side radiators),
MOD_Engine (block, heads, intake, accessories, lights), MOD_Engine_Exhaust, MOD_Engine_Gearbox.

## Left / ideas
- Fuel tanks at the sides, frunk tub, more bolts; equal-length headers only approximate; rear drive shafts angled ~26 deg.
- Wheel-agent hubs should start at x=0.82 (front) / 0.79 (rear).
