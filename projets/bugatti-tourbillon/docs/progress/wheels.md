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

## Follow-up (v5 to v16)
- window_outlines() rewritten: stems at 90+72k forking at rhoF 0.48 into arms to rim pads at +-36 deg; 5 big windows closed by rim arc (pad_deg 26), 5 small gaps between stems. Params in D dict.
- final spokes get a real bevel (chamfer); preview relies on the bevel shader node.
- caliper phi 18 deg at both axles so BUGATTI reads inside the window at 18 deg.
- disc: bigger holes (4.6 mm), satin grey #5A5D63.
- tread seam crack fixed by tucking a 6 mm sidewall overlap under the tread band.
- tris per wheel (FL): final 148k, preview 53k (budget 150k / 45k).
- right wheels checked (fr_closeup_v12.png, chk12.png): lettering reads correctly.
- rear wheel final quality checked (rl_closeup_v12final.png).
- still differs: spoke arms straight and thick vs the real curved, faceted arms; tread pattern generic; preview checker band is coarse.
