# Level 1–20 route work

Updated 2026-11-13 15:35 CST. This is the prioritized route and acceptance
record for the owner's requested playable 1–20 path. **F11 is disabled:** none
of these legs has been driven and accepted in the real client. The owner can
use the rotation-only preview described in [HOWTO.md](HOWTO.md) while he plays.

| Levels | Planned camp | Route needed | Current evidence |
| --- | --- | --- | --- |
| 1–5 | Butcherblock Kaladim gate yards | South Kaladim → Butcherblock, then local camp | The prior Alienware guide cites Legira's `/con` log for the low-level mobs. A retained current-helper Butcherblock mesh now loads with source hashes checked; the camp position, source arrival and movement remain unverified. |
| 5–8 | Crushbone Slaver Caves (west) | Butcherblock → GFay → Crushbone → safe spot | Copied GFay ground approaches toward Butcherblock and Crushbone pass separate offline strip checks. Crushbone arrival and its Slaver route are unaccepted; two copied-mesh crossings fail the current grade-1.2 turn audit. |
| 6–10 | GFay orc camps, alternate for Legira | Current GFay position → guide marker, then observed pull area | The existing guide lists this outdoor camp and the owner's log confirms relevant `/con` mobs. A copied dry path from the G0 test position avoids water and two steep polygons; its 155 ground segments passed sampled turns, walking-width strips, whole-route and static BSP checks. The actual camp, current position and live movement are unverified. |
| 8–13 | Crushbone Trainer Hill | Slaver Caves → Trainer Hill | The prior guide lists this range; no camp route, con sample or real movement has been accepted. |
| 13–17 | Unrest yard | Crushbone → GFay → Butcherblock → Dagnor's Cauldron → Unrest | Copied client map labels name these zone lines. The owner's Cauldron and Unrest archives are hash-matched in the private store; raw terrain and exact-name placed objects now compose provisional static scenes. Collision behavior, navmesh, water, arrival and movement are unverified. |
| 17–20 | Unrest first floor, subject to observed difficulty and XP | Yard → first floor | The prior guide marks this indoor camp as poor for automation; no safe pull route or live XP rate is observed. |

The level bands are **candidate priorities from the existing Alienware
`leveling_guide.json`**, SHA-256
`bfe936da1aec38b37a683af51f0ee4189cd86bcb4a1680deee613c4dfeba77b9`.
They are not validated as current server spawn levels. For Legira's last
owner-reported level 7 in GFay, the immediate candidate is GFay → Crushbone
Slaver Caves, with same-zone GFay orc camps as a fallback candidate. Starting a fresh character at level 1 would instead begin at
the Butcherblock camp if its spawn and safe route are observed. Camp changes
must use measured XP, con, crowd and danger rather than the table alone.

The copied client's zone-label maps independently name GFay → Butcherblock,
GFay → Crushbone, Butcherblock → Dagnor's Cauldron and Dagnor's Cauldron →
Unrest. The copied map-file SHA-256 hashes, in that order, are
`84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882`,
`84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882`,
`a1cea4378673518b5d3d63fa43bfa42d62bbbbec2a58d15fe7e3ad907b60bcb0`
and `2afc6ef37116bf69d5fed39cb1f4b126cc0648214ea01750947b9adaf0c7e383`.
Labels identify possible exits, not traversable routes or arrival points.
The owner's Cauldron and Unrest zone/object archives have now been copied
read-only into the private data store with remote/local hash matches. Their
BSP, raw terrain meshes and static object placements parse and compose
provisional solid-face scenes, but no collision-verified navmesh or route
has been accepted. See [FINDINGS.md](FINDINGS.md) for exact source hashes.

## What unlocks the first playable leg

1. **G0 passed on 2026-11-13:** the owner saw the character stop, and the
   helper trace shows `observed_stop`, 0.151-second hold, 4.64-unit movement
   and zero post-release drift. This verifies the short stop check only.
2. A fresh same-session `/location` and independently observed client scene
   must bind the current character to the copied mesh. The historical Legira
   location used for offline queries cannot serve as a current start.
3. A bounded owner-run G2 motion measurement must establish speed and drift,
   with F9/F11 cancellation and independent focus, chat, target, combat and
   zone checks. It has not been shipped.
4. A supervised short route must measure follower error and confirm a real
   zone crossing and arrival. Only then may a specific leg enter the full-auto
   graph. Subsequent camps and errands need their own observations.

The copied GFay → Butcherblock **ground** approach currently has 52 polygons,
53 selected points and no copied BSP water/zoneline/unknown spans at ground
or ground+1 height. It stops before the trigger. The route and BSP artifacts
and their hashes are in [FINDINGS.md](FINDINGS.md). There is no accepted
1–20 grind run, current XP/hour, or evidence of level gain under automation.

The copied Butcherblock camp → GFay dry query now has a 239-polygon
alternative after steering around seven steep/narrow polygons. Its 236 ground
segments have no copied BSP labelled or unknown intervals at two heights.
The bounded lateral selector stops at polygon 37736 after 92 turn checks,
before any strip check. A second 237-polygon dry corridor avoids that edge
and has no polygon-center slope above 75 degrees or clearance below 3 units.
Its uncached selector ran out of its 180-second work window at polygon 38947
after 240 turns and 358 strips; this is a work limit, not a geometry pass.
Caching identical strips cut that to 182 unique strip checks and advanced
to polygon 14525 (index 155 of 234) in the same 180-second window. A larger,
still bounded recheck completed its portal search after 240 turns and 260
unique strips, but its final whole-route pass hit the per-segment time limit
at polygon 49153. This is a work limit, not a geometry pass. None of these
results is an F11 route. A second selector run on the same corridor stopped
at that polygon during an individual turn check under the loaded devbox. A
new 249-ground-polygon dry detour avoids it and the prior penalized polygons;
one 420-second selector pass completed its portal search but had no time for
the mandatory final whole-route audit. Its sampled candidate remains
unaccepted. A second bounded run was externally timed out under heavy devbox
load before recording a result. A new select-only phase can retain unverified
portal points for a separate full-strip pass once load permits; neither phase
has accepted this Butcher route.

The same-zone GFay orc-camp fallback uses the existing guide's approximate
marker. The first dry route from the G0 test position had two polygons over
75° slope. Penalizing those two found a 155-ground-polygon alternative with
no polygon detail-triangle slope over 75° or center clearance under 3 units.
Its bounded selector passed 169 sampled turns, 175 unique strips and the
whole-route recheck; a copied BSP scan at two heights found no labelled or
unknown spans across 155 segments. This is copied static evidence only. The
guide marker, actual mob/pull site, current position and live path remain
unverified. Artifacts and hashes are in [FINDINGS.md](FINDINGS.md).

At the G0 test spot in GFay, all four fresh `/location` XY points landed on
copied ground with zero XY snap distance and consistent 2.065–2.085-unit
character-to-mesh height offsets. This supports the coordinate transform at
that spot. A new fix and independent scene checks are still needed before
any G2 motion test.
