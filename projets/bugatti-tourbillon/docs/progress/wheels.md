# Wheels progress log

## Status
- [x] read brief/spec/refs
- [x] existing code builds and renders (all 4 corners, rig, mirror) ; out/scripts/wheels/r.sh renders the sheet
- [ ] iteration 1: spoke design is a plain 5-star, must become Y-fork with pentagon windows; white artifacts on tyre shoulder; tyre lacks chequered band
- [ ] final quality tri count, dark render, steer/spin checks

## Known defects (v2 render)
- spokes straight, no fork; windows not pentagonal
- small white marks on tyre shoulder

## Iteration 2 (v3)
- added chequered band (tyre_marking material), lighter lettering, chunkier spokes (wA 0.125)
- running checks.sh (steer=1, spin=0.6, tri counts, final dark)
- Differences left: spoke topology (stem/pad), W slot too big vs real; brake disc drilling faint

## Iteration 3 (v4)
- steer=1 and wheel_spin=0.6 verified (out/renders/wheels/f34_steer1.png, f34_spin06.png)
- tri counts (one wheel, FL): final 171k (tyre 117k), preview 117k (tyre 81k). Over budget in both, tread rows dominate.
- dark render: fl_closeup_final_dark.png
- Still differs: Y-spoke topology (real: stem forks, 5 big pentagonal windows, small hub gaps; mine: stem to rim pad with W slot), disc drilling faint, spoke faces lack subtle chamfer highlights, tyre sidewall has no micro-texture.
