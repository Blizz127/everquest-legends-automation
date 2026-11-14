# Level 1–20 route work

Updated 2026-11-14 01:25 UTC. This is the prioritized route and acceptance
record for the owner's requested playable 1–20 path. **F11 is disabled:** none
of these legs has been driven and accepted in the real client. The owner can
use the rotation-only preview described in [HOWTO.md](HOWTO.md) while he plays.

| Levels | Planned camp | Route needed | Current evidence |
| --- | --- | --- | --- |
| 1–5 | Butcherblock Kaladim gate yards | South Kaladim → Butcherblock, then local camp | The copied South Kaladim map and geometry share the `-y,-x` frame. A 128-unit exit tile yields a six-polygon offline path in both directions between a sampled zone-line point and the Butcherblock map label; copied BSP marks the zone-line at one end. It has no fresh-spawn start. Both Kaladim scenes are pinned to copied owner-client archives. The copied helper's default 54-unit roam ring proposes four points, all with >6 units height change. A 12-unit ring proposes 12 one-polygon points that passed copied strip and BSP checks; seven still have >6 units height change. Fresh spawn, full walkable route, zone trigger, camp mobs and movement remain unverified. |
| 5–8 | Crushbone Slaver Caves (west) | Butcherblock → GFay → Crushbone → safe spot | Copied GFay ground approaches toward Butcherblock and Crushbone pass separate offline strip checks. On the finer copied Crushbone mesh, an 80-polygon graph alternative avoids suspect portal 658↔623, but its width-1.2/grade-1.2 turn audit rejects portal 3244→3242 before any strip check. One directed crossing passes its adjacent strips but fails the conservative turn disk; bypassing that diagnostic reaches another failed turn at polygon 4316. Excluding both suspect directed edges disconnects the graph. Crushbone arrival and the full Slaver route remain unaccepted. |
| 6–10 | GFay orc camps, alternate for Legira | Current GFay position → guide marker, then observed pull area | The existing guide lists this outdoor camp and the owner's log confirms relevant `/con` mobs. A copied dry path from the G0 test position avoids water and two steep polygons; its 155 ground segments passed sampled turns, walking-width strips, whole-route and static BSP checks. Five of six 12-unit local spokes pass copied strip/BSP checks; the sixth needs a portal choice. The actual camp, current position and live movement are unverified. |
| 8–13 | Crushbone Trainer Hill | Slaver Caves → Trainer Hill | The prior guide lists this range; no camp route, con sample or real movement has been accepted. |
| 12–16 | Crushbone Slaver Pits, alternate to delay the Unrest trip | Trainer Hill → Slaver Pits | The prior guide lists this level band but warns of protected slave/NPC targets and a stronger named mob. Actual target selection, pull safety and live XP remain unverified. |
| 13–17 | Unrest yard | Crushbone → GFay → Butcherblock → Dagnor's Cauldron → Unrest | Owner-helper Cauldron and Unrest meshes match the copied archive hashes. A dry Cauldron graph corridor has 364 polygons but steep/narrow sections. The Unrest entrance-to-yard corridor fails its sampled selector near the entrance. A corrected-frame scan of its straight funnel has no copied water/unknown labels, but no full walking strip passes. No walkable leg or arrival is accepted. |
| 14–18 | Crushbone North Wall, danger-limited alternate | Slaver Pits → North Wall | The guide rates this camp poor for automation because a Royal Guard may attack unseen. The bot must reject it until current target identity, danger and XP can be measured. |
| 17–20 | Unrest first floor, subject to observed difficulty and XP | Yard → first floor | A 59-polygon dry graph path exists, but its copied polygon-wide slope reaches 89.01° and minimum center clearance is 1.57 units. Dynamic doors, pull safety and live XP remain unverified; the prior guide marks this indoor camp poor for automation. |
| 17–20 | Crushbone Throne Room, danger-limited alternate | North Wall → Throne Room | The guide rates this camp poor because of clustered legionnaires/oracles and an invisible Royal Guard. It is a planning fallback only; no safe route or camp has been accepted. |

The level bands are **candidate priorities from the existing Alienware
`leveling_guide.json`**, SHA-256
`bfe936da1aec38b37a683af51f0ee4189cd86bcb4a1680deee613c4dfeba77b9`.
They are not validated as current server spawn levels. For Legira's last
owner-reported level 7 in GFay, the immediate candidate is GFay → Crushbone
Slaver Caves, with same-zone GFay orc camps as a fallback candidate. Starting a fresh character at level 1 would instead begin at
the Butcherblock camp if its spawn and safe route are observed. For Legira's
current level band, the same-zone GFay orc route is the first practical
movement-test candidate while the two Crushbone cuts remain unresolved. Camp changes
must use measured XP, con, crowd and danger rather than the table alone.
A controlled full-zone Crushbone bake with half-size horizontal cells reduced
the inner-ring height error at the second cut, but its outer footprint still
fails grade 1.2 and warnings increased from 21 to 128. That mesh is not a
replacement route and does not enable F11.
A read-only source probe then found flat Z=0 terrain under all 65 points at
cut 658→623, where the baked surface reaches Z=1.70. Nearby raised source
geometry still matters to clearance. A completed detail-sampling-only bake comparison
kept the same polygon graph but worsened the outer-ring maximum angular
grade from 1.801 to 2.706 and raised warnings from 21 to 439. That candidate
is rejected; no movement acceptance changed. Both bakes retain the same
elevated coarse polygon corners, so the next attribution is in voxel/contour
construction, before detail sampling. The owner assist 0.39.6 release fixes stopped-state
recovery and queued preparation cancellation while this route work continues.
The 0.41.46 source-span probe now reproduces the raised corner from merged
floor/wall raster spans before detail sampling. A conservative step-height
reduction (3.5→1.0) disconnects arrival from Slaver Caves; it is not adopted.
The baseline control still finds 80 polygons and fails turn polygon 3244.
A new read-only input observer passes 13 focused tests, but its live device
coverage, axis/contact interpretation and integration remain unverified.
Independent scene, current position, alignment and speed observations still
precede the first short GFay leg. The old G0 visible stop remains recorded.
The 0.41.47 input observer now reads the Alienware touchpad's actual contact
slots and separates held-key queries from queued events. Thirty-two focused
checks and a brief read-only 26-device probe passed their stated scope.
The first probe exposed same-descriptor EVIOCGKEY event loss; it is superseded
for event-history claims. No intentional held-finger/quick-key acceptance was
run, and the observer is not connected to movement. The current-zone map label
is now included in read-only capture, pending an owner-selected Current Zone
view. UI scene checks, fresh live alignment/speed and a follower remain open.
Source 0.41.48 adds the input/UI safety-provider integration boundary: 27
focused tests passed with simulated UI evidence, but no calibrated live UI
classifier or owner-helper wiring exists yet. The copied GFay corridor is
exported as 155 fixed 3D segments, preserving the selected portal coordinates
and each polygon's terrain height. The largest adjacent height discrepancy
is under 0.0001 unit. An offline probe of the actual retained helper confirms
its whole-route lookahead can shortcut beyond the audited walking strip, and
its predicted pose can report arrival before the raw location reaches a
portal. The future controller must feed one segment at a time, guard every
motion pulse, and advance only on a fresh stopped raw fix. Exporting the plan
does not implement those runtime constraints or accept the historic start
as the character's current position.
Source 0.41.49 implements the fixed-segment decision layer with the existing
helper's steering classes. It integrates actual completed holds and uses
two fresh stopped raw fixes for endpoint advancement. Rejected commands
cannot become predicted movement, and assist/cancellation invalidates queued
proposals. Eighteen focused checks passed. The copied GFay replay completed
all 155 segments in 2,147 idealized steps; 29 endpoint samples used only an
adjacent selected polygon within the portal acceptance disk. This replay
samples endpoint terrain, not the full swept movement footprint; it does
not verify real pulse precision, live alignment, collision or safe mobs.
Next: independent scene/calibration and the checked timed input connection.
No playable 1–20 leg or automated XP gain is accepted.
Source 0.41.50 resolves the watchdog/controller timing API mismatch. The
child reports timestamps around DOWN/UP writes, and a selector creates the
proposal only after the watchdog is ready. Fifty-eight pipe-based watchdog
checks and two controller integrations passed; the latter used synthetic
alignment/positions and actual child write receipts. No game movement or
live alignment is established by a pipe test. The scene/geometry-checked
owner-preview connection remains to implement.
Source 0.41.51 checks complete convex step footprints against copied detail
triangles within explicit numerical tolerances. The 1.2-unit strip samples
and portal rings alone do not prove a filled walking area. Six hypothetical
footprints pass, but applying the check throughout the replay halts after
three segments: reciprocal portal edges32479↔31668 have a 0.0001220703125-unit
XY mismatch, leaving 0.00011066 square units uncovered in that footprint.
The guard does not bridge it automatically. Compare original copied client
terrain before deciding whether/how to repair the derived navigation view.
No live route acceptance changes; source-wall/headroom/BSP/dynamic checks
and current motion/UI observations remain outstanding.
The Crushbone alternatives let the planner compare same-zone options before
committing to the unresolved Cauldron→Unrest crossing; they do not authorize
F11 or a pull. The helper's protected-target rules must still exclude
noncombat NPCs and stronger named mobs.

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
has been accepted. Project 0.41.31 reproduces those scenes from pinned
copied archives with an offline command; see [HOWTO.md](HOWTO.md) and
[FINDINGS.md](FINDINGS.md) for usage and exact source hashes.
The retained owner-helper meshes for both zones now load from the private
store with matching source and mesh hashes. Their dry graph connectivity does
not clear steep/narrow geometry, corrected-frame copied BSP hazards, dynamic doors
or actual client traversal. The exact diagnostic artifacts are in FINDINGS.md.
The older Unrest funnel BSP scan used the wrong helper-mesh frame;
its water/unknown claims were retracted after a corrected-frame scan found
only unlabelled copied BSP regions at the two sampled heights. A locally passable
crossing at polygon 3083 has no proved connected continuation toward the yard.
This leg remains a planning candidate.

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

The copied GFay → Butcherblock **ground** approach currently has 52 polygons
and 53 selected points. Its corrected-frame v2 BSP scan checks 116 spans at
two heights with no copied label/unknown interval. It stops before the
trigger and starts at a historical position. The route and BSP artifacts
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
portal points for a separate full-strip pass once load permits; neither of
those two early runs accepted the Butcher route.
The later 249-polygon detour did complete its select-only phase after 320
turns and 355 unique strip checks. A separate hash-bound full-strip audit
passed all 249 copied polygons. This is static geometry evidence only; the
selected route still needs verified zone arrival and a live follower trial
before F11 can use it. A later copied-client BSP scan passed all 249 ground
and ground+1 segments with no labelled, unknown or unsupported intervals. It
remains static evidence, not an F11 route.

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

Source 0.41.52 verifies source terrain under the one-ULP GFay detail seam.
An explicit local correction is used only by the offline experiment, with
unchanged baked heights and no mesh writes. Three footprint checks pass;
the guarded route then stops at segment 6 because detail face 248932 has
plane grade 1.3266 against limit 1.0. Adaptive shorter holds allow two extra
steps but the minimum hypothetical hold still fails. The next correction
must resolve the source/route geometry at that face. No G2/F11 leg or level
progress is accepted by these copied-data runs.

Source 0.41.53 relocates the two crossings around GFay segment 6 westward,
keeping the same 155-polygon corridor. The three changed segments pass filled
radius-1.2 ground tubes, legacy strips/turns and the complete centerline BSP
audit. The guarded follower now reaches segment 11, where another reciprocal
one-ULP tile gap refuses coverage. The original meshes and client data remain
unchanged. These conditional copied-data results still do not enable F11.

Source 0.41.54 applies a source-supported, ephemeral precision correction only
to proven reciprocal one-ULP coverage gaps. The repaired GFay plan reaches
segment 20 with the default 0.6-unit diagnostic source/bake Z limit; a separate
0.9-unit sensitivity run reaches segment 38 and stops on overlapping detail
faces. The default is unchanged. No entire route or input path is accepted.
Historical G0 fixes show raw-to-source height offset changes by only 0.000788,
while raw-to-baked offset changes by 0.01939. The next runtime binding must
carry physical source ground and baked mesh projection separately, with fresh
live calibration; a constant raw-to-baked correction is unsuitable.
