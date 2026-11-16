# Rear end: progress log (state: complete, polish remaining)
Files: src/tb/parts/rear.py (build), rear_lib.py (MB mesh builder, tube, fit_text). Scripts: out/scripts/rear/run.sh OUT "views" [args], multi.py (wing0/wing1 + close-ups, one build), probe*.py.
Renders: out/renders/rear/a3 (dark, lights+brake on), a4 (light), m4 (wing 0 / 1).
## Done
- Light bar (housing glass_dark, 2 glass_red covers, ~34 emit_tail cells, BUGATTI emit_brake letters, EB chrome), path = tail_edge anchor then rays on Body_*.
- Concave carbon panel + wall, plate bezel/plate, sheared "Tourbillon" nameplate, bumper block (boolean-cut), 2 finishers (rim/tunnel/divider), grilles, reverse strip, reflectors.
- Diffuser: floor L/R (ramp, clamped + smoothed above chassis/engine by rays), 4 strakes + side plate per side, centre fin.
- Wing: aerofoil blade + 2 struts on own hinge HINGE_Wing_Rear (rig.wing_hinge() has negative angle: TE dives into deck). Tail glow area light 30 W on 'taillights'.
- Tris: preview 36k, final 61.5k.
## Known defects / ideas
- Floor lowered around gearbox gives a smooth blob seen from low rear; floor/chassis still touches (463 clamped samples).
- Wing flush within ~5 mm only; follows body undulations. Cells are plain slabs (no stagger).
- Side flaps at lower corners belong to Body_Lower_R.
