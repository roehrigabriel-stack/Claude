# Rear end: progress log
Files: src/tb/parts/rear.py (build), rear_lib.py (MB mesh builder, tube, fit_text). Scripts: out/scripts/rear/run.sh OUT "views" [args], probe*.py.
## Done (first full build works, renders in out/renders/rear/a1, a2)
- Light bar: housing (glass_dark), 2 red covers, ~34 emit_tail cells, BUGATTI letters (emit_brake), EB logo (chrome) - path follows tail_edge anchor then rays on Body_*.
- Concave carbon panel + wall (Rear_Panel_Carbon, Rear_Wall), plate bezel/plate/Tourbillon script (sheared text).
- Bumper block (carbon_gloss, boolean cut for exhausts), 2 finishers (rim, tunnel, divider), mesh grilles, reverse strip, reflectors.
- Diffuser: floor L/R (ramp, clamped above chassis by rays), 4 strakes/side, side plates, centre fin.
- Wing: blade aerofoil on rig.wing_hinge(), 2 struts; tail glow area light driven by taillights (30 W).
## Todo
- check wing=1 direction (spec hinge angle is negative: trailing edge may go DOWN), lit/dark renders, floor clipping vs chassis (526 clamped samples), final tri count.
