# FINDINGS

## Bounded strip-failure portal repair — 2026-11-13 14:35 CST

**VERIFIED offline, no game input, project 0.41.21:** The copied-mesh portal
selector now tries an alternate at a portal adjacent to the first failed
polygon strip, reruns the layered route search, and keeps one shared time,
turn-check, strip-check, sample and repair-round budget. It tries each newly
passing alternative before testing another and retains the final whole-route
strip audit. Fifteen focused selector, strip and turn tests passed; synthetic
cases recovered a corridor where both initial midpoint turn disks passed but
the midpoint strip failed. The selector still returns
`route_accepted=false` and `real_client_accepted=false`.

**VERIFIED copied Crushbone mesh, not client movement:** Against the saved
80-polygon Slaver corridor and `crushbone.npz` SHA-256
`bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`,
the selector stopped before strip search at polygon 3248 with
`no_sampled_turn_disk_candidate` after 42 turn checks and 0 strip checks.
The bounded probe took 1.117 seconds. Its outside-git artifact is
`~/.local/share/eql-automation/nav-candidates/crushbone-strip-repair-probe-20261113T2034Z.json`
SHA-256 `14743f2ed8c5fa39fe3c24be942962f23adf920bfb2eb2863bc8997316465360`.
The source corridor artifact SHA-256 is
`8a4a659cc0effd3bf2c93afe47660f07e7fd6a077`. This repair does not solve
the Crushbone route; no F11 edge was accepted. NumPy was installed in an
isolated devbox environment under the private EQL data store for this offline
probe; no client data or binaries were added to git.


## Optional preloading location in owner watcher — 2026-11-13 14:30 CST

**VERIFIED offline, no game input, project 0.41.20:** The destination watcher
now retains the last new `/location` line no more than 30 seconds before the
loading line, when Blizz chooses to print one. It serializes that raw point,
log time and line ID alongside the first timely Clan Crushbone destination
reading. A stale preloading fix is omitted while a valid destination reading
can still be saved. Twelve focused destination/transition tests passed,
including CLI JSON output on temporary files. The source zone and exact
zone-line position remain unverified; no owner crossing has been captured.


## Owner-run destination capture seam — 2026-11-13 14:27 CST

**VERIFIED offline, no game input, project 0.41.19:** A read-only
`DestinationLogReader` now skips Legira's existing log history and can capture
a newly appended exact `LOADING, PLEASE WAIT...` → `You have entered Clan
Crushbone.` sequence within 60 seconds, followed by the **first** valid
`Your Location is ...` within 30 seconds. It works even when launched while
Legira is already standing in GFay, because it does not require an earlier
source-zone entry. It invalidates on log replacement, malformed/other entry,
location during loading, late first fix and timestamp regression. The owner
CLI additionally refuses a destination log timestamp more than 45 seconds
from the Alienware local clock or multiple arrivals in one poll; output is a
0600 JSON file under the private data store, outside the game install. The
copied client `ZoneNames.txt` resolves Clan Crushbone uniquely to ID 58; the
installed file was observed at SHA-256
`0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d`.
Eleven focused destination/transition tests passed, including the owner CLI
on temporary files. The CLI has not been run against Blizz's logged-in
character. It records raw destination coordinates and explicitly sets source
zone, crossing method, spawn, route and real movement acceptance false.


## G2 start-area provenance and radius gate — 2026-11-13 14:20 CST

**VERIFIED offline, no game input, project 0.41.18:** `check_g2_start()`
requires one `AlignedWldFix` bound by object identity to a fresh raw log fix,
matching scene line/epoch/zone generation, current safety flags, exact copied
zone ID/display name and zone short name, and a declared copied-mesh SHA-256.
The caller must supply a live
calibration record; none exists for Legira or a fresh test character. Raw log
coordinates cannot be passed directly. At the budget's minimum 60-unit/s
upper speed bound and 0.20-second maximum hold, an 8-unit radius fails before
the mesh is queried. An 18-unit, 36-direction, 1-unit-spaced disk requires
684 samples; a 512-sample limit fails, while an explicit 1,024-sample limit
produced only a synthetic sampled candidate. The result always has
`real_client_accepted=false` and `budget_authorized=false`. Twelve focused
start-gate, radial and scene tests passed. Zone mapping and mesh provenance are
caller-supplied contracts, not independently checked files in this function. The
underlying radial sampler may snap points or miss gaps between rays. This gate
rejects a start snap above 0.0005 units and subtracts any remaining snap from
the usable radius before comparing it to the pulse bound. Dynamic
obstacles and a true client-aligned ground point remain unverified.


## Read-only G2 location scene boundary — 2026-11-13 14:15 CST

**VERIFIED offline, no game input, project 0.41.17:**
`G2ReadOnlySceneObserver` converts exactly one new client `/location` log line
into a short-lived `G2Scene` only when an exact zone ID and display name,
stable log epoch and zone generation, local log timestamp within two seconds,
0.50-second monotonic fix age, and separately supplied 0.10-second focus,
owner-key, chat, target and combat safety checks all pass. Batched lines are
rejected until a later single line. A same-zone reentry invalidates the old
fix. Thirty-three focused tests across the observer, log reader, G2 budget and
input bridge passed; they used only temporary files and fake scenes.

**OBSERVED integration gates:** `LocationLogReader` skips existing log bytes,
so starting G2 while already standing in GFay has no trusted zone until a new
zone-entry message is seen. The log does not echo `/location` request IDs;
fix sequence identifies a line, not its issuing command. `G2Scene.at` must be
the current observation time while fix age is checked separately, because
hold reporting occurs before the next fix. The default 8-unit radial geometry
check is insufficient for the budget's minimum 12-unit first-pulse radius at
its 60-unit/s speed upper bound; a larger radial check also needs an explicit
sample budget. Raw log coordinates have no accepted WLD transform. No owner
G0 result, speed bound, independent live scene observer, real key release or
dynamic-obstacle check exists. This adapter is not in owner preview 0.39.4,
does not send game input and does not enable G2 or F11.

## Read-only zone transition evidence boundary — 2026-11-13 14:10 CST

**VERIFIED copied client data:** The GFay manifest
`~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store/gfaydark.json`
(SHA-256 `ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82`)
marks area 4 as `DRNTP00255000004_ZONE` and resolves the destination name
`crushbone` from a guide hint. Its `target`, destination zone ID and heading
are null. The reciprocal Crushbone manifest
`~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store/crushbone.json`
(SHA-256 `dd15b27c8acb221987780b013e9f0c4a9a14f4df389414a33b9ecf6fcc94979d`)
has a GFay reference at area 2, also with no arrival target. The pinned
November parser identifies zone ID 255 as a server zone-point-table reference;
the approved copied client files did not reveal that table. A light read-only
search of the installed Alienware prefix timed out, so its full contents were
not ruled out. The exact missing piece is the server's zone-point-4 arrival
row or a fresh owner-run crossing with immediate destination `/location`.
Neither a reciprocal marker nor a guide exit hint proves spawn XYZ.

**VERIFIED copied owner log:** Legira's Nov 5 GFay→Clan Crushbone entry was
logged at 20:02:02 after loading at 20:01:56. The preceding `/location` was
232 seconds before loading; the next was 92 seconds after entry. Those fixes
cannot establish the crossing or arrival point. `TransitionLogReader` now
tails only new lines of one expected character/server log and can pair a
log-confirmed source zone, a source fix within 30 seconds, exact loading and
different-zone entry messages, and the first destination fix within 30
seconds. It clears pending evidence on replacement, reset, malformed events,
clock rollback and stale windows. The output always says
`route_accepted=false`, `spawn_coordinate_verified=false`, and
`real_client_movement_accepted=false`; the log sequence alone cannot
distinguish walking from a teleport or relog. It sends no input. Scanning the
historical copied log produced zero qualified transition pairs under these
windows. Twenty focused location/transition tests passed. No owner-run
fresh transition has been captured.

## Bounded automatic GFay portal selection — 2026-11-13 14:05 CST

**VERIFIED offline, no game input, project 0.41.15:** A new layered selector
tests shared-portal turn disks, expands fractions only at failed midpoints,
connects surviving choices through audited polygon strips, and rechecks the
chosen whole ground route. Missing/ambiguous portals, unsupported surfaces,
failed final checks and exhausted work budgets fail closed. It returns
`route_accepted=false` and `real_client_accepted=false` even on a sampled
geometry candidate. This avoids hand-picked route points in the offline
pipeline; it has no owner-client input path.

Against the hash-matched copied GFay mesh and the saved 216-polygon graph
corridor, the final source run passed in 92.162 seconds with 243 turn-disk
checks and 270 candidate strip checks, then passed its final whole-strip
recheck to the same 2-unit pre-trigger standoff. It chose portal fractions
`{170: 0.75, 171: 0.70, 187: 0.60}`; the other 211 links remained at 0.50.
The result, including all 216 mesh-frame points, is outside git at
`~/.local/share/eql-automation/nav-candidates/gfay-auto-portal-selection-final-20261113T2004Z.json`
(SHA-256 `5a29d3ddc9a70c5d1cb6e7746c884fc2800394f96e97e5a53cf9d3834696ef82`).
Five focused selector tests passed, including adjacent candidate conflict,
missing link, sample exhaustion and final-audit refusal. The selector does
not repair a strip failure bounded by two disk-passing midpoints and can
reject a traversable turn because its disk is conservative. The copied area-4
zone transition has no verified arrival point; current position, dynamic
obstacles, follower error, G0/G2 and real client movement remain unverified.
F11 is still disabled and no actual level gain has been accepted.

## GFay ground-strip candidate and turn review — 2026-11-13 13:52 CST

**VERIFIED offline, no game input, project 0.41.14:** `audit_route_strips()` now accepts
caller-bounded per-segment spacing, sample and time limits, while keeping its
previous defaults. A one-call audit of all 215 ground polygons in the saved
GFay corridor, using 1.0-unit spacing, 1.2-unit half-width and a point 2 units
before the old terminal ground exit, passed 215/215 strip segments, 214/214
internal seams and 17,772 strip samples in 48.01 seconds. The result at
`~/.local/share/eql-automation/nav-candidates/gfay-high-clearance-whole-strip-audit-20261113T1947Z.json`
has SHA-256 `1f95b6bbe3e4d63dbf4089a8a5f1a614e4cd7c2ada3ee0229495cdbcc221cab7`.
At the old exit point, one final side sample overlaps area 4; the 2-unit
standoff avoids that overlap. Area 4 is the copied manifest's
`DRNTP00255000004_ZONE` Crushbone reference, but its `target` and
`to_zone_id` fields are both null. The actual transition and arrival are
unknown. The strip pass samples straight segments; it does not validate
turning, thin detail transitions, dynamic objects, measured follower error,
current character position or real client motion.

**VERIFIED copied-mesh turn warning:** A conservative 32-direction check at
the midpoint of GFay portal 22391→22406 found a 0.622271-unit drop over a
0.6-unit radial step, grade 1.037118 above the current 1.0 limit. Moving
that crossing from portal fraction 0.50 to 0.60 makes its local full-disk
check and both adjoining 1.0-unit-spaced strips pass. The next portal
22406→22403 fails a conservative full-disk angular-grade check at its
midpoint; moving it to fraction 0.70 passes its local disk and adjoining
strips. Source audits found a third midpoint warning at portal
19145→19119; its fraction 0.60 passes the local disk and adjoining strips.
With portal fractions `{170: 0.60, 171: 0.70, 187: 0.60}` and the same
2-unit standoff, a single route-wide run passed all **214/214** 32-direction,
two-radius turn disks (13,696 samples), and a separate single route-wide run
passed all **215/215** ground strips plus **214/214** seams (17,799 samples).
The hash-bound turn result is
`~/.local/share/eql-automation/nav-candidates/gfay-high-clearance-adjusted-turn-audit-20261113T1954Z.json`
(SHA-256 `12011abe2ca2c7793ba8110c33138115afc3facf5c54dad792670b5d1c51d0ad`);
the strip result is
`~/.local/share/eql-automation/nav-candidates/gfay-high-clearance-adjusted-strip-audit-20261113T1956Z.json`
(SHA-256 `0c4285f15f15f9ef793f097a0c081454c35706c459bf74566e6bca4f2fe8ac80`).
These are only sampled ground geometry: the zone trigger/arrival, thin detail
transitions, dynamic obstacles, follower error and real movement remain
unverified. Twenty-nine focused portal/strip/turn tests and a startup demo
passed. F11 stays disabled.

## GFay corridor edge quantization and owner supply signals — 2026-11-13 13:39 CST

**VERIFIED offline, no game input:** The copied owner GFay mesh at
`~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store/gfaydark.npz`
has SHA-256 `5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9`.
The saved 216-polygon candidate in
`~/.local/share/eql-automation/nav-candidates/gfay-high-clearance-graph-20261113T1931Z.json`
has SHA-256 `41b01005b619c37a1170bc657af2ef829031d584978fe28bae98953193d98477`.
It starts from the owner's historical `/loc (-1807.35, 1786.14, 66.45)`
and ends at the GFay side of the copied Crushbone trigger. The first rejected
portal needed at most 0.000324 world units of inward detail-edge projection;
heights across that seam matched within about 0.00013. Increasing the
physical detail-edge tolerance from 0.0001 to 0.0005 units, still below
0.001-unit missing-detail rejection, yielded 214/214 ground portal midpoint
seam candidates. All 215 ground polygon midpoint centerlines passed a
0.5-unit-spaced detail-surface audit, with maximum sampled local grade 0.906
and queried clearance reaching the 4-unit cap. Sampled 1.2-unit lateral strips
passed segments 0–36; segment 37 exhausted a 10-second work budget without
an observed geometry rejection. The later 13:52 audit above supersedes that
partial strip result. At this point, the remaining strip, zone transition,
dynamic obstacles, follower error, current position and actual movement are
**NOT RUN**. The corridor is not an accepted F11 route. The polygon-wide
maximum slope is 83.764 degrees, which does not describe the checked midline.
The hash-bound centerline result is stored outside git at
`~/.local/share/eql-automation/nav-candidates/gfay-high-clearance-midline-audit-20261113T1938Z.json`
(SHA-256 `dca4f8a095b7c45834c93c7772256b84e892c2b379bf4d326b052f6a4f7f6215`).

**VERIFIED copied owner log:** The read-only log at
`~/.local/share/eql-automation/owner-traces/eqlog-Legira-20261113.txt`
(SHA-256 `d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`)
records at 09:27:57 an item that did not fit and at 09:28:14 no food and
drink. It later records a belt looted and sold, so the failed item does not
prove all bag slots full. The same exact messages are parsed by the pinned
November rotation tool. The offline `RunState` now retains these warnings
across unrelated log lines and clears them only through an explicit verified
inventory/consumable observation. A `WorldSnapshot` carrying the warning
causes full-auto planning to pause; the recording-only dispatcher rejects
LOOT with unknown capacity or a newer warning. No live adapter connects
these two stages yet. Parsing the copied owner log reported level 7, a loot fit warning,
and both food and drink out. Forty-eight focused tests and the simulator
startup check passed. These checks send no game input and buy nothing.

## Offline G2 reentry guard and camp reachability filter — 2026-11-13 13:11 CST

**VERIFIED offline, no game input:** G2 scenes now require the copied log
reader's `zone_generation` and halt when it changes, including a loading and
reentry into the same displayed zone. A queued pulse with the old generation
is rejected before key-down. The campaign planner now ranks only camps in an
explicit caller-supplied verified reachable set. It switches away from an
excluded current camp and pauses if the set is absent or contains no suitable
camp. The synthetic environment supplies fabricated route evidence and still
reaches synthetic level 50; that does not verify any real-client route or XP.
Twenty-nine focused G2/location tests, 26 offline planner tests and the
synthetic 1–50 CLI passed. There is no live G2 scene adapter or real verified
camp set, so F11 remains disabled.

## G2 location-line identity, not command identity — 2026-11-13 12:37 CST

**VERIFIED offline, no game input:** `LocationLogReader` now assigns a
monotonic number to each newly read `/location` line and increments a separate
zone generation when zone state becomes invalid. A same-zone reentry cannot
silently reuse a previous generation. Twenty-three focused location/G2 budget
tests and the simulator startup check pass. Repeated identical location lines
receive different line numbers because they are distinct appended log lines.
The client does not echo a request ID for `/location`, so neither this number
nor temporal arrival proves which command caused a reply. There is still no
live `G2Scene` provider or owner-confirmed G0/fresh speed bound. G2 and F11
remain disabled; no route or level gain has been accepted.

## Hybrid rotation and owner HP diagnostic — 2026-11-13 12:34 CST

**VERIFIED copied client data:** The retained `spells_us.txt` at
`~/.local/share/eql-automation/client-data/retail-full/spells_us.txt`
(SHA-256 `8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de`)
lists Furor ID 560 at Cleric level 5 / Paladin level 8,
Light Healing ID 17 at Cleric level 4 / Paladin level 10,
and Yaulp ID 210 at Cleric level 1 / Paladin level 9.
The copied owner log records Legira casting Furor during the level-7 owner
test; the owner also reported Yaulp firing. The single-class offline profile
would omit both from a level-7 Paladin selection. `Catalog.profile()` now
accepts an explicit Cleric+Paladin class set, checks the spell's unlock level
in each active class, and filters to the verified known spellbook. The strict
`AssistAdvisor` requires that same class set in a fresh observation before
proposing a cast. Eleven focused spell/assist tests passed. A direct
profile query using the copied catalog and known IDs `{14,17,200,210,560}`
selected Strike/Minor Healing for Paladin alone and
Furor/Yaulp/Light Healing for Paladin+Cleric at level 7. The synthetic fixture
now uses those copied client IDs and unlock levels. This offline advisor is
not connected to live input.

**VERIFIED no-device owner preview:** Isolated preview 0.39.4 was built from
the pinned November source and staged under Alienware
`~/.local/share/eql-automation/owner-assist/0.39.4`, outside the game install.
It forwards the HP gauge rejection reason to the GUI and displays actionable
text for an oversized crop, changed window size, or unrecognized red fill;
the HP value stays unknown. Patched `rotation_engine.py` SHA-256 is
`d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f`;
patched `eql_rotation.py` SHA-256 is
`7e4fbfc9af11e5090cac9a43f6538551cfc8b359b1140e8ea223075f7749948b`.
Its pinned-source/no-device smoke, level-7 dry run, and offscreen GUI startup
passed on Alienware. It changes no input policy. Owner live HP and F9
latency remain **NOT RUN** on this build. F11 remains disabled, and G0 has
no observed stop result.

## Crushbone bypass graph cut and bounded portal clearance — 2026-11-13 12:02 CST

**VERIFIED offline, no game input:** `eql_automation/graph_cut_audit.py` adds
bounded ground-graph reachability and a sampled upper bound for maximum wall
clearance along one portal at a fixed height. The upper bound adds half the
sample spacing because distance to the same set of walls is 1-Lipschitz in
the plane. Thirty focused portal, strip and graph tests pass. This is
only copied-mesh evidence, never client acceptance. The staged source outside
the Alienware client at
`~/.local/share/eql-automation/nav-work/0.41.8/eql_automation/graph_cut_audit.py`
matches devbox SHA-256
`1f5dac4fc2855d08efb9e68a0718ca8527a98bda0cf7557822d050e376e4a365`.

On the hash-matched Crushbone mesh, blocking the short-route step polygon
3248 still leaves a 176-polygon ground-graph path from historical arrival
2249 to Slaver goal 3805. Blocking both 3248 and 1170 disconnects that graph
(1,406 polygons visited), so 1170 is required by any ground-graph bypass
that avoids 3248. Polygon 1170 has links only to 637 and 1169. A 1,001-point
scan at the portal's flat detail height Z=0.162506 gives maximum sampled
clearance 2.632477 and a between-sample upper bound 2.635160, both below the
current 3.0-unit diagnostic requirement. Both adjacent polygons' detail
triangles are flat at that height. Thus that copied-mesh bypass cannot
meet the current threshold at this fixed-height portal. The longer penalized
route has 199 polygons and also reaches this gate.

**CORRECTION to sparse sampling:** The preceding 637→1170 portal **does**
have a narrow interval near fraction 0.47 with clearance 3.089791; its
1,001-sample upper bound is 3.093691. The earlier five/few-fraction rejection
there was a grid miss. A targeted sample at 0.47 lets the fixed-corridor
preflight reach the next 1170→1169 portal, where the bounded clearance result
above applies. The 3.0-unit requirement is a conservative diagnostic budget;
the actual follower error is unmeasured. No live route has been accepted,
and F11 stays disabled.

## Route-wide strip scan and second bottleneck — 2026-11-13 11:56 CST

**VERIFIED offline, no game input:** `eql_automation/strip_route_audit.py`
applies the bounded lateral strip check in order to a specified polygon and
portal-point sequence. It also checks each seam and connected component,
returns the first failure, and enforces segment/sample/time caps. Even an
all-segments pass would be a sampled geometry candidate only: turn fans,
follower error, dynamic obstacles, zone transitions, current position and
actual movement would remain unverified. Twenty-five focused
portal/corridor/strip tests pass. The staged source outside the Alienware
client at `~/.local/share/eql-automation/nav-work/0.41.7/eql_automation/strip_route_audit.py`
matches devbox SHA-256
`face6e5be2edda493fa586a125d146456071353fcaa2466a7ef16c3d6d9e0dbf`.

On the hash-matched Crushbone route artifact, the route scanner rejects at
segment 10/poly3146 after 1,281 samples. A bounded local search found a
small portal adjustment: changing the 3181→3146 crossing from source-link
fraction 0.1 to 0.2 lets segments 9–11 pass their sampled strips. The same
80-polygon route then rejects at segment 29/poly3248 after 2,667 samples.
A bounded 12×12 pair of portal fractions across 3248, requiring its two
adjacent strips as well, found zero local passing triplets. Polygon 3248
has only neighbors 3250 and 3247; a dry graph search avoiding it remains
connected but takes a 176-polygon path instead of the 80-polygon path.
That bypass has not passed centerline or strip checks. No route is accepted,
and F11 remains disabled.

## Lateral strip rejects Crushbone candidate — 2026-11-13 11:52 CST

**VERIFIED offline, no game input:** `eql_automation/lateral_strip_audit.py`
checks one straight segment's centerline and two 1.2-unit lateral offsets at
no more than 0.5-unit spacing. It queries nearby copied-mesh polygons
directly, requiring supported detail height, ground area, same connected
component, unambiguous surface, bounded cross-grade and side clearance.
Unsupported overlapping water/other-component surfaces reject; sampled
clearance includes a half-spacing margin. Segment turns and the entire route
remain outside its scope. Twenty-two focused portal/corridor/strip tests and
the simulator startup check pass. The staged module outside the Alienware
client at `~/.local/share/eql-automation/nav-work/0.41.6/eql_automation/lateral_strip_audit.py`
matches devbox SHA-256
`d744eeb1b7f6dbc6c30661c4486146c6f7d893bbab65bb705b60d848794609e2`.

**VERIFIED copied-mesh route check:** The first ten segments of the 0.41.5
Crushbone centerline artifact passed this sampled strip check. Segment 10,
polygon 3146, rejects at sample index 18: center detail Z=0.710 and the
positive-side 1.2-unit offset Z=1.943, a rise/run of about 1.028 above the
1.0 limit. A separate bounded source OBJ check found overlapping Z=0 and
Z=2 faces near this segment. Comparing all 81 portal points with the nearest
source OBJ face at the same XY gave nav-minus-source height differences of
0.062–1.633 units (median 0.263; four above 1.0); overlapping surfaces make
this a diagnostic, not a calibrated client-height transform. The centerline
candidate is therefore **rejected for travel**. No safe full strip, current
player location, movement stop, follower error or real-client route trial has
been verified. F11 stays disabled.

## Full fixed-corridor geometry candidate — 2026-11-13 11:45 CST

**VERIFIED offline, no game input:** A bounded override added one portal
sample at fraction 0.7 on the 4197→4322 link of the historical Crushbone
route. With the five default fractions elsewhere, the copied, hash-matched
80-polygon arrival-to-Slaver path now has an 81-point sampled centerline and
seam chain. `audit_fixed_corridor` checked 1,484 local segments within a
40-second work limit and returned
`fixed_corridor_geometry_candidate_only`; its `real_client_accepted` flag is
false. The reproducible route points, polygon IDs, raw and snapped endpoints,
mesh/manifest hashes and audit parameters are stored **outside git** at
`~/.local/share/eql-automation/nav-candidates/crushbone-slaver-offline-candidate-20261113T1745Z.json`,
SHA-256 `8a4a659cc0effd3bf2c93afe476bf3360d8b303c384997c47660f07e7fd6a077`.
Devbox and Alienware copies match, and a second run after rejecting unused
portal overrides reproduced the same 81 points and 1,484 segment checks.
The source-only auditor staged outside the client at
`~/.local/share/eql-automation/nav-work/0.41.5/eql_automation/portal_corridor_audit.py`
matches SHA-256 `7c54be40b573804542193c3a87c900c4c4fff00b9395a5e12efbef4aeefa170d`.
Seventeen focused portal/corridor tests pass, including the override's
fail-closed bounds. This supersedes only the five-fraction negative result
below: the candidate remains an offline centerline diagnostic. The travel
strip, complete geometry provenance, source-to-bake height offset, dynamic
doors, water, aggro, current position, cross-zone arrival, measured follower
error and actual client movement are unverified. F11 remains disabled.

## Fixed-corridor Crushbone audit — 2026-11-13 11:40 CST

**VERIFIED offline, no game input:** The source-only
`eql_automation/portal_corridor_audit.py` now applies the local detail-surface
and shared-portal checks to a specified polygon sequence with sample-count,
polygon-count and elapsed-time bounds. A portal boundary mismatch of
0.000061 WLD units at 3272→4108 exposed an unnormalized cross-product slack
in the copied mesh's `contains()` method. The local audit now checks a
physical 0.0001-unit distance from each polygon edge; a synthetic
0.001-unit gap still rejects. Review also changed seam endpoint tolerance to
physical distance and rejects conflicting overlapping detail heights.
Sixteen focused portal/corridor tests pass. The offline modules staged under
`~/.local/share/eql-automation/nav-work/0.41.4/eql_automation/` match devbox
SHA-256 `2a9adce2878f9c7bfcfe81f7ecbb1e7867e252e97f7f5badf966885363c1d949`
for `portal_surface_audit.py` and
`9d24df4cfce7af4fb282b25a8cbba7852dd84b69611c3be3eef56b57129f9814`
for `portal_corridor_audit.py`.

**VERIFIED hash-matched copied-mesh query:** The historical Crushbone
arrival-to-Slaver query snaps to polygons 2249→3805 and its existing mesh
path has 80 polygons, 1,049.819 units and 21 funnel points. It goes through
4197→4322→4321→4319; polygon 4320 is a side branch, so the earlier
4322→4320 local candidate is not on this route. The historical raw arrival
Z=2.56 snaps to mesh Z=0.163, and the guide goal Z=-14.678 snaps to mesh
Z=-16.878; these offsets have not been reconciled with real-client position.
With five sampled fractions per portal, the bounded audit made 940 segment
checks and stopped at polygon 4322 after processing 47 polygons. The
upstream chain reached 4322 at incoming 4197-portal fractions 0.3 and 0.9;
the only sampled 4322→4321 exit passed the seam check at fraction 0.75, but
neither local connecting segment met clearance. A separately sampled 4322
segment can pass when entered at its own portal fraction 0.3; that entry was
not reachable from the earlier sampled corridor. This is a **grid-limited
negative result** for one fixed 80-polygon path, not proof no safe route
exists. The full travel strip, source-to-bake height alignment, dynamic
collision, zone arrival, measured follower error and actual game movement
remain unverified. F11 stays disabled.

## Detail-edge quantization correction — 2026-11-13 11:33 CST

**VERIFIED offline correction to 0.41.2:** The prior `unsupported_detail_surface`
result at the Crushbone 4322→4320 portal was caused by a too-strict
barycentric tolerance, not proof of missing terrain. Copied polygon 4320's
detail edge lies within 0.0000049 WLD units of the portal. The new checker
projects only up to 0.0001 WLD units onto a detail edge; a synthetic
0.001-unit gap still rejects. Nine focused tests pass. On the same hash-matched
copied mesh, the 4322 local centerline from portal 4197 parameter 0.1 to
portal 4320 parameter 0.5 and both seams now return **geometry candidate
only**: seven local samples, capped minimum clearance 4.0 units, maximum
sampled rise/run 0.474, and exit heights -5.323203037/-5.323203021. The
direct portal-midpoint line still fails at 1.800-unit clearance.

**OBSERVED alternate local lead:** The 4322 line from 4197 parameter 0.3 to
4321 parameter 0.75, its two seams, and the next 4321 line to 4319 parameter
0.5 and seams also pass these local checks. This is not a complete corridor
or accepted route. The retained, project-generated Crushbone WLD-XYZ OBJ
`~/.local/share/eql-automation/nav-candidates/crushbone-solid-candidate-806b40d87e1810bc.obj`
(SHA-256 `806b40d87e1810bc1bba549fc4468fd585e7402a1e812a1be0a8d67ae7793e3d`)
contains source terrain at the 4322→4320 portal after swapping nav and OBJ
XY. Its sampled source Z differs from baked detail Z by about 0.60–0.64 units;
the origin and real-client collision implications remain unverified. No
follower error, current player position, water/door/aggro state, zone arrival
or actual movement is verified. F11 remains disabled. The corrected module
is staged outside the client at
`~/.local/share/eql-automation/nav-work/0.41.3/eql_automation/portal_surface_audit.py`.
Devbox and Alienware module SHA-256 match
`e1559f5cb88eb34eb9a504d6e26b9c9183532fe78cbbad3aa6121df276d47ba0`.

## Portal-local true-surface and seam audit — 2026-11-13 11:30 CST

**VERIFIED offline, no game input:** `eql_automation/portal_surface_audit.py`
now samples a single polygon's centerline against actual copied Recast detail
triangles, allowed area, local grade and wall clearance. It refuses the
`NavMesh.height()` corner-interpolation/extrapolation fallback when a point
has no containing detail triangle. A separate seam check requires the
crossing to lie on a real shared portal, have supported detail heights on both
sides, satisfy a bounded step height, and clear the wall-distance budget.
Eight focused synthetic checks passed. A positive result is only a local
geometry candidate: no travel strip, full route, dynamic obstruction, water,
zone transition, follower error or real-client movement has been accepted.

**VERIFIED copied-mesh query:** The November `crushbone.npz` remains SHA-256
`bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`.
At polygon 4322, a line between the midpoints of portals to 4197 and 4320
fails immediately at 1.800-unit clearance, below the 3.25-unit sampled floor.
A bounded 5×5 portal-parameter grid produced five local centerline candidates,
all entering the 4197 portal at parameter 0.1 and leaving the 4320 portal at
0.25, 0.4, 0.5, 0.6 or 0.75. Rechecking the 0.1→0.5 line gave seven detail
samples, capped minimum clearance 4.0 units and maximum sampled rise/run
0.474. Its entry seam agrees at height -6.523 on both polygons. The first
checker rejected its exit seam as unsupported; the 11:33 CST correction above
shows this was a quantization-tolerance false rejection. This still is not an
accepted Crushbone passage, and F11 stays disabled. The historical
Crushbone starting point is also not verified as the actual GFay arrival.
The module was staged outside the Alienware client at
`~/.local/share/eql-automation/nav-work/0.41.2/eql_automation/portal_surface_audit.py`;
devbox and Alienware module SHA-256 match
`1735dfebc8148c5c8efd1a21b6d68baa37085c3bc0f8302d9bb24676277d3448`.

## Isolated G2 input bridge and portal-local route lead — 2026-11-13 11:23 CST

**VERIFIED pipe-only:** `eql_automation/g2_input_bridge.py` binds one G2
budget permit to the November helper's existing `evdev.UInput.fileno()` and
its `KEY_UP` forward key. On Alienware, installed evdev source exposes that
same descriptor through `fileno()`; no input device was opened for this
inspection. The bridge arms a child before reserving a permit, checks the
scene just before GO, and the child refuses an expired key-down deadline.
The shared stop/GO lock remains held until the child acknowledges DOWN; if
that acknowledgment fails, the child is killed and UP is written before OFF
can acquire the lock. An OFF waiting for that acknowledgment could take up to
the 0.30-second acknowledgment window plus failure cleanup in this prototype.
During a pulse, the helper's input check and scene
guard are polled; final release uses `KeySender.release()` so failed key-up
retains the held-key record. Pipe-only tests cover changed target before
DOWN, OFF before GO, stop during pulse, caller stall/kill, stale deadline and
failed final release. A no-input Alienware pipe smoke reported a 0.150-second
pulse with the expected DOWN/UP events. This code is not connected to the
owner preview or to live scene observation; G0 is still unconfirmed and G2
and F11 remain disabled.
The isolated Alienware staging path is
`~/.local/share/eql-automation/nav-work/0.41.1/eql_automation/`. Its staged
bridge, budget and watchdog match devbox SHA-256 values
`c7e0313e31a9a7e9a751ed6bb87d768bbe0c6c4e2772313ec97df4481cf8dc73`,
`1547788a3df63d0e559696b5b4e7b9b637b550209e7c9f04877d3d9030077acc`,
and `932452feeb07da362b33b8228be23aa8ebc43641a2cc3730fbbb3587f3cc71ff`,
respectively. The game install and original November helper were not changed.

**OBSERVED copied-mesh analysis:** November Recast inputs use 0.6/0.3 cells,
agent radius 1.2, slope limit 75 and detail sample distance/error 6/1. The
GFay mesh's 89.19-degree `slope[poly]` is the steepest detail triangle
anywhere in that polygon; the 188-polygon candidate line sampled a maximum
rise/run of 0.702 (about 35 degrees). Its 55 standard locator failures
occurred where linearly interpolated Z differed from the actual surface by
up to 9.8 units. This suggests a bounded true-surface, path-local slope
audit before rebaking; it does not accept the route. In Crushbone, the
3-unit/6-unit centroid filter disconnects Slaver west, while a 2-unit/4-unit
filter connects via polygon 4322 (centroid clearance 2.129 units). Its
portal toward polygon 4320 has sampled clearance up to 8.54 units, so the
centroid filter may overreject. A 109-polygon centroid line still failed
local checks (0.366-unit minimum clearance, two blocked rays, 83.32-degree
polygon slope). Next offline query: bounded portal-to-portal, true-surface
samples with clearance and slope in the travel strip. The historical
Crushbone start has not been verified as the GFay arrival point.

## Revocable G2 permit and slope-filtered route result — 2026-11-13 10:59 CST

**VERIFIED offline:** The G2 pulse policy now returns a generation-bound permit
instead of a bare duration. A caller must confirm it against a current scene
within 0.05 seconds before key-down; cancelling the check invalidates queued
permits. Nine focused budget checks pass. This is a pure model: it does not
serialize the eventual input thread or send input. The owner-run sender must
recheck immediately before and during the same-device pulse. G0 remains
unconfirmed and G2 is not in the owner preview.

**VERIFIED copied-mesh query, read-only:** In GFay, requiring ground/trigger
areas, polygon slope at most 45 degrees, centroid clearance at least 3 units
and portal width at least 6 units disconnects Legira's historical start from
the Crushbone trigger. The bounded search visited 16,132 of 38,587 polygons
and scanned 39,503 links. The wider high-clearance corridor below therefore
does not resolve the slope gate. No route or client movement was accepted.

## Bounded G2 pulse policy and wider GFay route audit — 2026-11-13 10:57 CST

**VERIFIED offline:** `eql_automation/g2_pulse_budget.py` is a recording-only
policy for a future supervised movement check. It requires explicit current
geometry and owner-confirmed G0 gates, two stationary fixes, safe scene flags,
a measured speed, a freshly verified conservative speed upper bound of at
least 60 units/s, and a clear-radius budget. It permits at most three
0.15-second forward requests, checks each reported hold and new fix, requires
a delayed stillness fix before every subsequent pulse, then two delayed
still fixes at the end. Each new position fix must advance a log-epoch-bound
sequence, and delayed hold reports or final fixes are rejected. Any unsafe
scene, exceeded time/radius, implausible displacement or drift latches halt.
Eight focused checks passed. A code review reproduced and then resolved the
missing inter-pulse stillness, underestimated-speed and stale-timing permits.
The earlier 8-unit GFay geometry preflight is
too small for this conservative bound; it does not authorize even one pulse.
It neither reads the game nor sends input; callers cannot treat its result as
real-client acceptance. The required scene signals and same-device sender are
not yet integrated, so G2 is not offered to Blizz and F11 stays disabled.
The policy now exposes a generation-bound confirm/cancel interface, but it is
not bound to the helper's input thread. Integration must serialize OFF with
the sender and recheck immediately before and during key-down.

**OBSERVED bounded copied-mesh search:** A GFay polygon-center corridor from
Legira's last logged location toward the Crushbone trigger has 188 polygons,
6,864.7 units of length and 3.47 units minimum clearance across 3,715
surface-height samples, all on allowed ground/trigger areas. Its maximum
polygon slope is 89.19 degrees; 55 samples disagree with the standard
interpolated-Z locator by up to 9.8 units. The current path-quality gate
rejects it. The ordinary funnel path remains narrower/blocked. In the copied
Crushbone mesh, a 3-unit clearance and 6-unit portal-width filter visits 550
of 5,150 polygons before disconnecting the arrival from Slaver Caves west;
the default centroid line narrows to 0.2 units. These are offline query
observations, not a runnable route or client movement result. No game input
was sent.

## Location poll clock rollback — 2026-11-13 10:49 CST

**VERIFIED offline:** The location reader already dropped same-poll fixes
after loading, zone entry and log reset; that earlier review concern was
already resolved. It now also clears the zone and latest fix if its caller
supplies a poll time earlier than the previous observation. The pending log
fix stays unbound until a new zone entry. A focused rollback regression and
the location-reader checks passed (13 tests). This does not establish live
log-to-mesh alignment or a safe current player position.

## Same-device pulse release timer — 2026-11-13 10:46 CST

**VERIFIED offline:** `eql_automation/uinput_watchdog.py` is an optional
building block for a later owner-run G2 check. A separate process inherits the
caller's existing input descriptor and writes one timed key DOWN/UP pair to
that same descriptor. It releases on its own deadline, STOP or parent-pipe
closure; the parent sends an additional UP after child exit. Five focused
pipe-only checks passed, including a stalled caller and a killed caller.
An Alienware pipe-only smoke reported a 0.100-second hold and the expected
DOWN/SYN/UP/SYN sequence. The staged module outside the game install and
devbox source both hash to SHA-256
`f19248cffe3d37f70de20fe1a6503c0b205ab2fff3e3c811e9f068f097c51cb7`.
It has not been tried with EverQuest or a real uinput descriptor, and a
stalled/killed watchdog child itself would still need the parent to release.
The release deadline is best effort under OS scheduling; integration must
exclude concurrent pulses for the same key and descriptor.
It is not wired into the owner preview; G0/G2 and F11 remain unverified/off.

## GFay G2 geometry preflight — 2026-11-13 10:42 CST

**VERIFIED offline:** `eql_automation/g2_probe_geometry.py` performs a bounded,
read-only check of every tested direction around a proposed short movement
probe: dry ground, walkable ray, sampled mesh membership, slope, height change
and at least 3 units of local clearance. Four focused synthetic checks passed.
The staged copy outside the Alienware game install has the same SHA-256 as the
devbox source: `f2debaeaa7f44d060e0ac264735ea16edc4c11cd006262042a1e5568e4299c09`.
Against the copied November GFay mesh at the historical owner `/loc`
`(-1807.35, 1786.14, 66.45)`, the 8-unit, 36-direction check returned
`offline_open_area_candidate`, 324 samples, with a clearance lower bound of
4 units (the query caps its measurement at 4). This is a candidate around an
old position, not a current-position or real-client acceptance. Dynamic
obstacles, facing, movement-stop behavior, G0 and G2 are unobserved. No game
input was sent. F11 stays disabled.

## Isolated November follower clearance guard — 2026-11-13 10:20 CST

**VERIFIED offline:** `patches/nov12-7e3cd28-follower-clearance-guard.patch`
applies cleanly to the pinned November source and adds the bounded corridor
audit to `Navigator._plan()`, so every mesh replan must pass before a new
`PathFollower` is made. The `Navigator` defaults to an unmeasured follower
error and therefore refuses travel. It clears any stale path, follower and
held-control intent when planning fails. Two no-input source smokes passed:
one refuses unmeasured error, the other refuses a synthetic mid-segment pinch
and clears a stale follower. The isolated combined source is under
`~/.local/share/eql-automation/nav-work/0.40.5` on devbox, not in the
owner-run preview or game install. Patched `eqnav/steer.py` SHA-256 is
`fa4ec5fbd4a725a4e0e2ab1ac1c871d508464cb23314d7db5cff640802fdb05a`;
`eqnav/pathguard.py` matches the project module SHA-256
`c161ddf99ad3746efe58ce256f79760adb3e43b44ac488e18984cf563c1c24eb`.
Recorded routes and cross-zone arrival still lack accepted guards; G0/G2
and a measured follower error are missing. F11 stays disabled.

## Bounded corridor audit model and local-camp evidence — 2026-11-13 10:16 CST

**VERIFIED offline:** `audit_path` now checks a mesh path with a capped
sample count, allowed corridor areas, a raycast for each funnel segment,
path-local allowed-mesh membership, slope review and clearance at no more
than two units between samples. The clearance budget includes the baked
agent radius, measured follower error and half the sample spacing. Missing
follower error rejects by default; even a geometric pass remains explicitly
unaccepted in the real client. Four focused corridor checks and five melee
stop checks passed. This audit is not yet wired into the November follower,
so F11 remains disabled; every runtime replan and recorded route still needs
a real guard. A no-input Alienware check against the copied route artifact
returned `sample_off_allowed_mesh` for GFay and `segment_not_walkable` for
Crushbone even with slope review disabled. Both are conservative rejections;
the separate dense clearance audit below independently found sub-radius
chokes. The reproducible offline GFay/Crushbone route artifact is held
outside git at
`~/.local/share/eql-automation/nav-candidates/legira-gfay-crushbone-candidate-20261113.json`,
SHA-256
`4156dc438757689a8f3b9ca3ff20a1d1b946158f43e41aa9adf30016cda3b88d`.

**OBSERVED owner log, read-only:** A level-8 Orc centurion in GFay awarded
Legira 2.574% current-level XP at 09:27:56, but the first `/loc` fix was
44 seconds later, so the fight's exact position is unknown. The guide's
only GFay Orc Camps anchor is about 4,104 dry-mesh units from that fix and
its candidate route includes a steep polygon; it is not an accepted short local
route. The same log repeatedly reports no food or drink from 09:09:50 through
09:31:18, and no inventory room for loot at 09:27:57. Copied owner log
SHA-256:
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`.
One kill cannot establish XP/hour or level-11 camp suitability. No character
input was sent by the lead.

## Native melee stop acknowledgment model — 2026-11-13 10:10 CST

**VERIFIED offline:** A recording-only `NativeMeleeStopGate` now accepts only
exact `Auto attack is on.` / `Auto attack is off.` system-message bodies. It
starts unknown, reserves at most one toggle intent only when its client
command has separately been verified, and requires a later OFF message to
confirm stop. An unknown state, log gap, timeout, wrong acknowledgment or
clock rollback requires manual review; it never retries a toggle. Four
focused safety checks passed. This module is not connected to the live
helper, sends no input, and cannot prove that `/attack` or `/attack off` was
accepted in Blizz's actual client. The owner-supervised command check and
G0/G2 movement checks remain required before full auto.

## Read-only GFay→Crushbone route audit — 2026-11-13 10:07 CST

**VERIFIED copied-store provenance:** The 69-MB November mesh store was copied
from the old helper to
`~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store` on Alienware,
outside its client and original helper. `diff -qr` found no difference across
the 116 copied files. The isolated preview's `MeshStore` loaded GFay and
Crushbone from this copy with 38,587 and 5,150 area entries. Their `.npz`
SHA-256 hashes are
`5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9`
and `bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`;
manifest hashes are
`ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82`
and `dd15b27c8acb221987780b013e9f0c4a9a14f4df389414a33b9ecf6fcc94979d`.
The old helper's three pinned source hashes were rechecked unchanged after
staging. No game data was committed to git.

**VERIFIED offline path query, not live acceptance:** From Legira's last
logged GFay position to the Crushbone trigger, the default dry mesh path is
4,927.779 units, 200 polygons and 31 waypoints. Its minimum waypoint wall
clearance is 0.932, below the baked 1.2-unit agent radius; it includes
two corridor polygons with centroid clearance below 2 and one with 81.78°
slope, above the 75° bake limit. From a historical Crushbone arrival fix to
Slaver Caves west, the dry mesh path is 1,049.819 units, 80 polygons and 21
waypoints; one corridor polygon has only 0.2-unit centroid clearance and a
polygon reaches 83.79° slope. A later full-path sample at no more than two
planar units per point **superseded** the earlier sparse minima: the GFay path
reaches only 0.122-unit wall clearance (2,510–2,529 samples across margin
variants), and the Crushbone path reaches only 0.528 (556–571 samples). Wider
funnel margins of 4 and 6 still leave minima of 0.175/0.249 in GFay and
0.966/0.978 in Crushbone, all below the 1.2-unit baked agent radius. A nearby
Crushbone mesh surface also differs from interpolated path Z by about 1.4 units.
The zone trigger has no encoded
arrival point. The route therefore remains a candidate; no F11 live travel is
accepted. Aggro, water, dynamic obstacles, transition and movement-stop
behavior remain unverified. A light trace summarizer reproduced the owner
trace SHA and 13 unknown versus 5 known HP gauge samples without printing
character data; it does not certify in-game actions.

## Narrow HP owner preview 0.39.3 and G2 preflight design — 2026-11-13 10:02 CST

**VERIFIED no-input owner preview:** Review found that the 0.39.2 band reader
would classify an unrelated 12×3 red patch at the crop's left edge as 3.6%
HP, which could feed the smart-heal decision. Preview 0.39.3 supersedes it.
It rejects the old 338×51 HP crop, requires a fresh 5–24-pixel-tall inner
red-bar calibration, rejects small red accents and returns unknown below
10% rather than treating an isolated red patch as critical HP. The user must
heal manually while HP is unknown. On Alienware, its pinned-source smoke,
level-7 dry-run and offscreen measurement GUI smoke passed without opening
game input devices; the GUI image was 85,715 bytes. Five focused local
adapter/guard tests passed. The devbox runtime smoke could not import numpy;
the Alienware smoke with its installed numpy passed. The isolated owner-run
build is `~/.local/share/eql-automation/owner-assist/0.39.3`; the private
archive SHA-256 is
`78c547a0a0cdde6418a93de32bb50de6f46bd2e14872725a97f44eb894655c6e`.
No 0.39.3 live HP or healing behavior has been reported. G0 remains NOT_RUN.

**OBSERVED offline route gate:** The November helper defaults to
`~/.local/share/eql-rotation/navmesh`, whereas its existing 37-zone,
69-MB hashed mesh store is under its `artifacts/navmesh/store`. A future
isolated launcher can point `EQL_NAVMESH_DIR` at an approved copy outside
the client install. The documented G2 fallback `eqnav.livecheck.py` is absent;
the alternative F11 starts the full grinder. G2 needs a separate short,
owner-supervised travel job with a hard input budget and verified stop before
any F11 release. Read-only Crushbone pathing connects Slaver Caves to Slaver
Pits, but one waypoint has only 0.9 units of wall clearance and the owner's
log records dangerous adds there. That does not establish a safe level-11
camp. A finer one-zone rebake was deferred because devbox load was about
275 on 48 cores with CPU pressure near 68%; no rebake or client movement ran.

## G0 owner preview and level-aware mesh camp filter — 2026-11-13 09:56 CST

**VERIFIED no-input owner preview 0.39.2:** A versioned copy is staged at
`~/.local/share/eql-automation/owner-assist/0.39.2` on Alienware. Its
attack-free adapter now permits only `/stand` and `/location` in measurement
mode and only the existing **Check movement stop** job; F11 travel/grinding,
F12 recording, targeting and other movement jobs remain blocked. F9 does not
send the helper's unconfirmed `/attack off`. The pinned source guard, thin HP
band and F11 block passed `owner_nov12_smoke.py`; `./launch.sh --dry-run
--level 7` passed; an offscreen measurement-mode GUI smoke rendered an
85,715-byte image without opening input devices. Five focused adapter/guard
tests passed on devbox. The private archive
`~/.local/share/eql-automation/releases/eql-owner-assist-preview-0.39.2.tar.gz`
has SHA-256
`b4eccbb786dd55fdc891338e89496ab04b13c543407363d6dd134b5c84a2552f`.
Blizz has not yet reported a 0.39.2 live test. G0 is still **NOT_RUN**:
the observed stop trace and Blizz's visual confirmation are both required.

**VERIFIED offline camp filter:** A separate pinned-source patch under
`patches/nov12-7e3cd28-reachable-camps.patch` adds an eligibility predicate
to the November guide and a copied-mesh dry-component/zone-entry check to
the November `World`. The autopilot now obtains a position fix before camp
choice, keeps an owner-recorded path or a camp already occupied by the owner,
and rejects disconnected mesh camps. The patch applied cleanly to the
0.39.1 runtime copy; 19 focused camp/travel checks passed in an isolated
Alienware source copy. Against the original helper's hashed mesh store, a
read-only query returned Slaver Caves mesh-connected from Legira's last GFay fix,
Trainer Hill disconnected from Slaver, and GFay Orc Camps reachable from
Slaver. A synthetic guide/mesh progression chooses Slaver at levels 7–8,
GFay Orc Camps at 9–10, then stops at 11 with **no verified camp route**.
This patch is not in the owner-run preview; G0/G2 and a level-11 camp remain
open before F11 can be offered. No game movement was performed by the lead.

## Owner live test and isolated assist preview — 2026-11-13 09:43 CST

**OBSERVED owner test, read-only trace review:** Blizz ran the November Solo
Assist on Legira, reported level 7 in Greater Faydark. Trace
`/tmp/eql-trace.jsonl` on Alienware, SHA-256
`c24a83e8f42a246e7e3f87f30d5f04285a24bf5e058147198d1381a3c8024c26`,
shows F8 casting armor, Yaulp, Bash, stun and four nukes; gem preparation
and focus checks worked. HP was `null` for 13 early combat gauge reads, then
read 0.7988 and later 0.93–1.0. The saved HP rectangle
`[1963,661,2301,712]` is 338×51 at 2560×1600 and overlaps the mana crop.
The copied default player UI describes a 14-pixel HP gauge. A six-to-ten-pixel
red fill inside the 51-pixel crop reproduced `bar_fraction=None`; the old
test painted almost the entire crop red. The actual rejected live pixels were
not saved, so this is a supported cause, not confirmed pixel-level diagnosis.

**OBSERVED stop limit:** The trace attributes two invalid-command replies to
`/attack off`, but it records intended command text rather than the exact
chat draft EverQuest received. Helper hotkeys F7/F11 occurred during those
drafts. The trace does not prove whether the literal command is unsupported
or mistyped. The bounded owner log has `Auto attack is on.` and no later
`Auto attack is off.` through 09:31. The installed client describes `/attack`
as a toggle and defines exact on/off messages. The November helper clears
its internal attack flag on send without waiting for an off acknowledgment;
native melee stop therefore remains unverified. Blizz must control and
confirm melee himself in the isolated assist preview.

**VERIFIED offline route evidence:** F11 halted on a missing recorded route
because the default runtime mesh store was absent. A 37-zone mesh store
already exists under the original helper's `artifacts/navmesh/store`, outside
the game install. GFay mesh SHA-256
`5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9`
and Crushbone mesh SHA-256
`bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`
load with their installed-client source hashes. The owner's last logged GFay
position and the Crushbone trigger share a dry component; the Crushbone
entrance and Slaver Caves camp share one there. This supports an automatic
route without hand recording, but no live follower/zone/stop acceptance.
The level-9 primary Trainer Hill camp is disconnected in the current mesh;
later guide camps also have disconnected/manual gaps. A mesh path alone does
not prove hands-off level 50.

**VERIFIED no-input build:** An isolated 0.39.1 preview was built from a
read-only copy of the dirty November source at base revision `7e3cd28`.
The original Alienware working tree and client install were not modified.
The preview's HP reader selects a thin red inner band from the calibrated
crop and rejects ambiguous bands. Its adapter suppresses every helper
`/attack on/off`, blocks F11/F12 movement and route jobs, and labels melee
manual when rotation stops. The direct `eql_rotation.py` entry refuses
startup; `./launch.sh` applies a source hash guard and adapter. The preview
is staged at `~/.local/share/eql-automation/owner-assist/0.39.1` on Alienware.
The private preview archive is
`~/.local/share/eql-automation/releases/eql-owner-assist-preview-0.39.1.tar.gz`
on the devbox, SHA-256
`513172e4c7152952b1f749d0f4d904b6f76a65c70b7f4113db813792808376fe`.
Its no-device smoke passed source pin, thin-band HP, melee suppression and
F11 block; `./launch.sh --dry-run --level 7` passed. Four focused adapter/guard
tests passed on devbox. This is ready for owner-supervised HP/assist feedback,
but **not** live accepted, strict target/chat verified, or full-auto ready.

## November helper target evidence and read-only hint reader — 2026-11-13 09:25 CST

**OBSERVED source:** The current Alienware November 12 engine, SHA-256
`1e1e6e3e021619471f9d954e86c9af81363315a66a7b8771b766acea53ea4731`,
parses `Targeted (kind): name` and `/consider` faction reactions. Neither
contains a unique entity ID. Its own comment says the client can auto-select
an add without a `Targeted` line. Same-name target changes can therefore
carry prior approval in the legacy helper. Its input sender infers chat draft
ownership from sent keys and physical Enter/Escape, without a verified game
chat-focus or draft-content signal. F9 disarms and releases held keys, but
native `/attack off` can be deferred when focus or input is unavailable.
These are source observations, not a lead-run live test.

**VERIFIED offline:** `TargetLogMonitor` now uses the non-replaying log tail
to emit only newly logged selection hints. It invalidates on zoning, death,
targetless lines, unsupported/malformed selections, unparsed lines, log
replacement and time rollback. It never mints a unique target token or marks
a selection verified; its explicit event count cannot cover unlogged
retargets. Six focused synthetic tests passed. No owner-character log was
read and no game input was sent. Strict ASSIST remains disarmed until a live
observer can distinguish every selection, including same-name targets, and
verify chat state before each input event.

## Alienware source switched; owner F8 path rechecked — 2026-11-13 09:17 CST

**VERIFIED read-only:** The Alienware rotation folder currently contains a
large, dirty November 12 working tree, not the reviewed October 17 mirror.
At 2026-11-13 15:15:41 UTC, its `rotation_core.py` SHA-256 was
`5632dbef84ae93b5ec3ec70d516cbc53c4b26593d78d99b55e1f7856bbdbd83a`,
`rotation_engine.py` was
`1e1e6e3e021619471f9d954e86c9af81363315a66a7b8771b766acea53ea4731`,
and `eql_rotation.py` was
`c4fd21f59d0e6cfa2321f0c64826d8402d566a2ac0bde14b4614db4d5a49ac8e`.
Their sizes are 23,178, 138,022 and 56,647 bytes. The earlier 15:08 UTC
recheck found the October hashes; the folder's visible contents changed
between checks. The cause is unknown. The changed source is preserved and
was not overwritten.

**VERIFIED startup and refusal:** The 0.37.0 owner wrapper archive, SHA-256
`afebbc527bf72824cf7ca02f6719ef85071611d766659b158ddac301b416c0e9`,
was staged outside the game install. Its Alienware dry-run refused before GUI
or input because the source hash changed. Its extracted directory was renamed
to `~/.local/share/eql-automation/owner-assist/0.37.0-source-mismatch` so the
old HOWTO command cannot start it. The current Alienware legacy helper's
`./launch.sh --dry-run --level 4` then exited 0 without opening input.
No lead-controlled game login, key press, movement or character progress
occurred.

**OBSERVED current source:** F8 arms persistent combat without selecting a
target or moving, and F9 disarms it; F7 toggles. F8 performs `/consider`
target review and sends `/attack` for approved NPCs, so it is not strict
rotation-only ASSIST. F10 sends `/attack off` before `/cast 1`. F9's native
`/attack off` can be deferred until focus/input is safe; a prompt helper stop
does not prove melee immediately stopped in the client. F11 can start
unattended targeting and movement even though all new movement gates in
`LIVE_GATES.md` are marked NOT_RUN and the November 6 continued-walking
incident remains unresolved. F12 records route points. HOWTO therefore
limits Blizz's current supervised test to F8/F9 and says not to use F11/F12.
The current README claims historical live F8 validation but points to an
unresolved evidence file. No fresh-character 1→50 run has been verified.

## Owner-run attack-free rotation preview — 2026-11-13 09:14 CST

**VERIFIED offline:** `owner_live_entry.py` checks SHA-256 of the three
reviewed October source files before importing their GUI, engine and spell
catalog; changed or missing source refuses to start. Its adapted engine
suppresses `/attack on` and `/attack off`, leaves autoattack manual, and
requires explicit F6 gem preparation before F8 can arm. F8/F9 stop only the
helper's rotation; the status line says Rotation ON/OFF. Only rotation
`/cast`, `Bash`/`Smite` ability and Lay on Hands commands can reach the
inherited sender in combat. The inherited physical Escape/Enter handling
no longer clears an uncertain command draft during the same process. No
targeting, movement, loot, vendor, camp or login command is added.

The focused adapter/assist/mode set passed 39 tests. A no-device invocation
of the adapted real October `Engine` blocked an unprepared F8 and did not
create a sender. The entry's `--dry-run --level 1` passed against the copied
client spell sample, with no game input. This does **not** verify live combat,
target relation, chat-draft ownership, implied healing, input latency or
level 50. The owner will drive any live test; the lead has not entered a
character. The owner-run command is in HOWTO.md.

## Owner-run live rotation handoff — 2026-11-13 09:10 CST

**VERIFIED read-only:** Alienware currently has the October
`/home/blizz/Projects/everquest-legends-rotation/launch.sh` (SHA-256
`c692b528fe86af7e0bef7c341cfc37144d8549c29c1723a99fad94d9d01f3a2c`)
and `rotation_engine.py` (SHA-256
`8e32a72eb7f87dae9901f84841679fdb628c46fab7458de216bfdff9fe567683`).
The desktop **EQ Legends Solo Assist** shortcut is present (SHA-256
`a2dbafb1bad33e93962fa9cfb7c066c57b51de78d74d637b3f24d258f2952cbd`).
One earlier bounded inventory saw placeholder files; a direct recheck at
2026-11-13 15:08:58 UTC and a second agent at 15:09 UTC saw the actual files.
The earlier absence finding is superseded; the cause of the differing reads
is unknown. `./launch.sh --dry-run --level 1` ran on Alienware and exited 0
after reading the installed spell catalog, without opening input devices.
It reported an unconfirmed spellbook and a prospective level-1 gem plan.
No lead-controlled login, game input or character progress occurred.

**OBSERVED tool behavior:** October F6 exports the learned spellbook and
memorizes gems, sending `/attack off` first; F8 starts/stops and sends
`/attack on` when arming, while F8/F9 stop can send `/attack off`; F10 casts
`/cast 1`. It does not choose targets, move, loot, vendor or camp. It clears
an uncertain command draft when physical Escape/Enter is seen without a
verified focused-chat-clear signal, and live combat/implied healing remain
untested. The owner-run command and these limits are in HOWTO.md. This is a
legacy live test path, not proof of strict rotation-only ASSIST or level 50.

**VERIFIED current service rule, non-blocking owner notice:** The installed
retail `eqhost.txt` still points to Daybreak's live login host. Daybreak's
[Terms of Service, section 10](https://www.daybreakgames.com/terms-of-service?locale=en_us)
currently forbids unapproved gameplay-modifying software, macros and bots;
its [Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct)
also restrict unauthorized servers. The owner explicitly chose to test the
legacy rotation himself on live; the lead will not access his account or
character. A private endpoint is still needed for full-auto acceptance.

## Non-replaying run telemetry — 2026-11-13 09:04 CST

**OBSERVED source risk:** The October `LogTail` reset its byte offset to
zero after inode replacement or truncation. In `ClientLogReader`, that could
replay historical level/death lines, double-count deaths or restore stale
zone state. Its separate `stat()` and `open()` could also race a rotation.

**VERIFIED offline:** Run telemetry now uses the already bounded,
file-descriptor-based `NonReplayingLogTail`. Existing file contents are
skipped; replacement, truncation and oversized backlog are skipped and
invalidate level, raw XP, level-progress rate, camp and zone. Because the
same character/run is not independently proven after a reset, the death
count becomes `n/a`. Reading the first bytes of a newly created log is an
explicit `fresh_test_character=True` opt-in, armed only when that path was
absent at startup. The default still skips first-created content. Focused
tests cover existing history, first creation, replacement, truncation,
partial lines and backlog. Raw XP rate samples now discard nonmonotonic
timestamps rather than combining incompatible windows. No real character
log or client input was used.

## Spell-gem click seam and bounded target recheck — 2026-11-13 08:43 CST

**VERIFIED copied-client sources, read-only:** The copied default
`EQUI_CastSpellWnd.xml` defines `CSPW_Spell0` through `CSPW_Spell13`, but no
active on-screen coordinates or key bindings (SHA-256
`840a7b76ce76f6435c1e597ea8a44e57511415ff74a5a2fc3cb6c961fe09eb05`).
The copied default `EQUI_ChatWindow.xml` defines `CW_ChatInput` but no
runtime focused/text/owner signal (SHA-256
`5662c3b77a36d1ad19ca6b83ff254409b4e7ac7ea2910a9f3baa815be214cd83`).
The installed Alienware `eqclient.ini` is 12,706 bytes, SHA-256
`a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc`.
Its `[KeyMaps]` section has five custom entries and none for casting or
abilities. This does not rule out built-in default shortcuts. The October
`rotation_engine.py`, SHA-256
`8e32a72eb7f87dae9901f84841679fdb628c46fab7458de216bfdff9fe567683`,
types slash commands and does not verify chat-draft ownership.

**VERIFIED synthetic only:** `RecordingGemClickBridge` records one mouse
down/up pair for an approved rotation spell gem, with a newer matching
current-target observation and externally supplied visible, unobstructed
hitbox evidence. It shares the exclusive input channel and original permit
with the recording key bridge. A changed target, chat-open observation,
missing gem, changed layout, stale hitbox or OFF prevents the click. A focused
46-test set and `--demo-assist` passed; the demo's hitbox is fabricated.
The key bridge also now has a focused test showing that chat opening after
the first slash stops OFF and keeps the command draft uncertain. No capture,
mouse/keyboard input, login, level or XP was produced. The installed client
has no verified active hitbox or target-selection signal, so neither bridge
is ready for live input.

**VERIFIED bounded private-target recheck:** Devbox process, container,
TCP/UDP listener and named directory checks found no EQEmu/EverQuest server
candidate. The authorized Banshee peer had no matching process, service,
container, image, listener or bounded `/home/blizz/dev` candidate; its
unrelated Sandalcore `worldd` was excluded. `banshee-ax41` was offline at
the time of the check. These negative checks do not prove there is no server
elsewhere. The missing private login endpoint/separate client configuration
remains the exact gate for any real-client automation test. The only located
Alienware client still points to Daybreak's live host; no connection or
input was sent.

## Recording-only assist key bridge — 2026-11-13 08:18 CST

**OBSERVED prior tool:** The October `rotation_engine.py` uses an Xlib
`WindowGate` and evdev `KeySender`; it checks allowed/focus before every
key down, types slash commands character by character, releases a held key
in `finally`, and tracks unfinished drafts. Its F8 arming path sends
`/attack on` and stop can send `/attack off`. Those attack actions are outside
the requested rotation-only ASSIST mode, so the old live sender has not been
launched or copied into the active runtime.

**VERIFIED synthetic only:** `RecordingAssistKeyBridge` now records symbolic
key down/up pairs for an `AssistAdvisor` proposal while checking its original
permit and a strictly newer matching observation before each key. Its
allowlist excludes attack, movement, targeting, spell preparation and login.
The shared `ControlPlane` owns one key-channel lock and the uncertain-draft
flag across bridge instances. A stopped or failed partial command leaves
that flag set until explicit clear while OFF with a fresh focused,
chat-closed observation. A stop request signals permit cancellation before
waiting for transition bookkeeping; a key already in a bounded recorder
call is released, and later key downs are denied. Foreign permits and
advisors from another control plane are rejected. The offline assist demo
records eight symbolic key downs for `/cast 3`, then OFF invalidates the old
proposal. Focused tests cover mode stop, target swap, stale observations,
multiple bridge instances, notifier failure and a stalled recorder.

**Limit:** No game key sender, in-game hotkey grab, real chat-draft ownership
signal or native input latency bound is implemented. A blocking native key
callback could delay the OFF command's return even though its permit is
cancelled immediately. Live immediate-stop acceptance remains unverified;
no client input was sent.

## Historical /loc-to-WLD candidate audit — 2026-11-13 07:41 CST

**VERIFIED read-only/offline:** A filtered copy of only 122 system location,
loading and entered-zone lines from the historical Alienware log resides
outside git at
`~/.local/share/eql-automation/client-data/retail-full/log-evidence/historical-system-location-lines.txt`,
SHA-256 `ba772066f5c24f4f01bcd55afcd7cddd7eb454b27d1116e47200dc1aa2aaeb01`.
It contains 66 location, 22 loading and 34 entered-zone lines; no chat lines
were retained. The owner log remains unchanged. The new bounded
`audit_location_alignment.py` compares exact-zone historical triples to
flag-zero copied WLD terrain for all eight XY sign/axis transforms. It keeps
the printed Z coordinate raw and scores consistency of the vertical offset.

Greater Faydark used 56 historical `/loc` lines, 48 distinct raw positions,
raw Z −6.98 to 67.8, and 72,694 copied flag-zero terrain triangles. The
scorer removes eight repeated positions. Direct log `(x,y)` to WLD `(x,y)`
covered all 48 distinct positions and had 47 offsets within 0.5 units of
median 2.5638; the next candidate `(-y,-x)` had 13 coherent offsets. One direct-mapping
outlier at 2026-11-05 19:17:37 had offset 35.6939. Its untracked audit JSON
has SHA-256 `8e7e8c1afde97f09d84d96b2d9dea2a28a88211ee36c5275eb19a06faaec77e9`.
Four Crushbone points on broad flat terrain tied direct `(x,y)` and
`(-y,-x)` at 4/4 coherent offsets of 2.56; its JSON SHA-256 is
`7bf6288ae2fcef405574220f62196a74fe455b4ddfd1d50a947f6bf70af1faa2`.
The result strongly favors direct logged XY in historical Greater Faydark,
but the tool reports `accepted_log_to_wld_transform=null`,
`live_alignment_verified=false`, and `navigation_edge_accepted=false`.
Five focused alignment tests and both copied-data CLI audits passed; the
combined location/navigation/dispatch focused set passed 46 tests. The
synthetic 1–50 rerun reached only fabricated level 50 with 1,446 trace events.
It does not establish a private-client position source, current character
height, collision clearance, walkability, or actual movement. The implied
log-to-map candidate is `(-log_y,-log_x)` given the separately observed
client map-to-WLD `(-map_y,-map_x)` transform; that also remains provisional.

## Client log position format and read-only tail — 2026-11-13 07:18 CST

**VERIFIED read-only client evidence:** The Alienware retail client has a
historical owner-character log at `<game root>/Logs/eqlog_Legira_freeport.txt`,
SHA-256 `ab782e0d9fec079d2e6d6d74b8c6206c5da96d3811af87f20103c8dfcd99be73`
when inspected. It contains timestamped `Your Location is <number>,
<number>, <number>` messages, `LOADING, PLEASE WAIT...`, and `You have entered
<display name>.` messages. A historical line from that real file parsed with
the new exact-format parser. The log was read only; no character was launched
or commanded. The printed triple's WLD axis order and capture latency remain
unverified.

**VERIFIED copied client data:** The copied `Resources/ZoneNames.txt`, SHA-256
`840b61b01deb4dfb8f49cf13e007364a629ce380c165aad5bb37adba6e52cd39`,
yielded 504 unique display-name-to-ID mappings and 74 ambiguous names.
Exact names in the historical log resolve to Clan Crushbone ID 58, The Greater
Faydark ID 54, Northern Felwithe ID 61, and Southern Felwithe ID 62. These
IDs do not establish walkable routes or coordinate alignment.

**VERIFIED offline:** `LocationLogReader` now requires an expected character
and server filename, skips preexisting log bytes, binds raw location triples
only after an unambiguous entered-zone line, and invalidates them during
loading or on log reset. Its dedicated tail drops replacement/truncation
history, changed continuity anchors, excessive backlog, and oversized partial
lines. A regression in the log's local timestamp clears the zone and requires
a later entered-zone line. A later loading/zone event in the same poll drops
earlier position fixes; malformed position or transition lines also invalidate
them. Twelve focused tests cover these conditions. The reader does not send `/loc`, feed
`WorldNavigator`, or treat a poll timestamp as verified capture freshness.
No fresh test character or real client run has occurred.

## Synthetic camp travel waits for navigator observations — 2026-11-13 07:11 CST

**VERIFIED synthetic only:** The closed-loop `--synthetic-1-50` campaign now
passes each camp trip through `WorldNavigator` using explicitly listed
synthetic move edges and zone transitions. A fabricated start position must
match the current node. The simulated environment records a MOVE or ZONE
action through `DryRunDispatcher`, then supplies a separate arrival
observation. Zone/node and camp state advance only after the navigator
confirms the waypoint or zone entry. A stalled waypoint or wrong zone-entry
position pauses navigation, latches OFF, and leaves the camp unset. A pending
zone transition issues one ZONE action while later observations wait for
entry. Dispatch and navigation observations use one monotonic synthetic
clock; stale observations and adapter exceptions latch OFF. The start position
is supplied by an overridable observation adapter rather than copied directly
into the navigator.

`python3 -m pytest -q tests/test_offline.py tests/test_navigator.py
tests/test_dispatch.py` passed 29 focused tests. `--synthetic-1-50` reached
only fabricated level 50 with 1,446 trace events, including 12 route-step
events marked `arrival_observed=true`; no game/account input was sent.
Trace: `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T131106Z/`.
The default observation adapter returns each requested destination immediately
as fabricated data. **Limit:** no real client position observer, movement key
sender, private endpoint, or actual navigation acceptance exists.

## Recording-only runtime dispatch seam — 2026-11-13 07:06 CST

**VERIFIED synthetic only:** `DryRunDispatcher` now binds each planned action
to its original mode permit, immutable `WorldSnapshot`, target-selection
token, zone and node. Before the recording sink accepts it, a newer focused
observation must match, with chat closed, finite HP/mana/bag state, no GM, and
action-specific conditions such as a present target for a cast and an
available corpse for loot. OFF invalidates the old permit; ASSIST denies
movement, zone, target and other nonrotation actions through `ControlPlane`.
The synthetic 1–50 run now uses this dispatcher for every accepted action and
for its final mode-safety probes. Emergency PAUSE uses `ControlPlane` directly
so unknown observations can still stop the run immediately.

`python3 -m pytest -q tests/test_dispatch.py tests/test_offline.py` passed 18
focused tests. `--synthetic-1-50` still reached only fabricated level 50 with
1,439 trace events and `real_client_level_verified=false`; no game input was
sent. The later synthetic camp-travel change above replaced the immediate
`WorldNav.route()` step application. The dispatcher checks per synthetic action,
not per emitted key; there is no
client sender, hotkey hook, real login or real XP observation.

## Offline current-level XP observation — 2026-11-13 07:03 CST

**VERIFIED copied client UI:** `uifiles/default/EQUI_PlayerWindow.xml`,
SHA-256 `2ebd1af9bb330606c4b604c02b78c6f40fab39f316b1bc7edd839c1568125869`,
defines `PW_ExpGauge` as EQType 4 with orange fill `(220,150,0)` and blue
line fill, plus `PW_ExpLabel` EQType 26. It separately defines a green
`PW_AltAdvGauge` EQType 5. Copied `EQUI_InventoryWindow.xml`, SHA-256
`a1f61d925e4254bcbe35729d8dc2a009a26a9810d7ef702c90ad3a3304bc35f1`,
also has distinct XP and AA gauges and an adjacent percent label. These are
static default-skin definitions, not proof of the active skin, runtime label
format, screen crop, normal XP allocation or cumulative XP.

**VERIFIED synthetic only:** A separate amber `XpGaugeReader` requires a
nonempty reference crop matching a verified same-frame XP percentage, then
checks focus, layout, dimensions and optional later label agreement. Empty
or ambiguous bars remain unknown. `RunState` tracks current-level fraction
and percentage points per hour only for the same confirmed level, resetting
on a level change, fraction drop, stale/nonmonotonic sample or unverified normal
XP allocation. Raw `observe_xp` now requires an integer cumulative value;
the gauge fraction cannot enter raw XP/hour or absolute camp scoring.
`python3 -m pytest -q tests/test_screen_observer.py tests/test_offline.py`
passed 20 focused tests. `--demo-gauges` read fabricated HP 0.5, mana 1.0,
current-level XP fraction 0.25 and explicitly left raw XP unknown. No live
client screenshot, account or server was used. The real XP/hour remains n/a.

## Full copied-BSP centerline intervals — 2026-11-13 06:29 CST

**VERIFIED offline:** `BspPointLookup.trace_segment` now partitions a finite
WLD-XYZ line at every crossed copied BSP plane and returns region/label
intervals. It fails closed on a plane endpoint, missing child, cycle,
nonfinite split, depth or work limit. A synthetic 0.1-unit water-labelled
strip between two point samples was detected by the segment traversal while
the five-unit point sampler reported no water. Six focused region-audit tests
passed. This is an exact classification of the **copied BSP centerline**
within its numeric tolerance, not proof of game collision or character
clearance.

The current Butcherblock FAYHOUSE path has zero labelled and zero unknown BSP
intervals across its start connector, corridor and end connector. The
Crushbone TIKIBAM path has no labelled interval and two unknown intervals:
0.026010 WLD units in the start connector and 0.002449 in the end connector,
both due to copied BSP uncertainty. No route or movement was accepted. New
untracked audit JSON SHA-256 hashes under
`~/.local/share/eql-automation/nav-candidates/` are
`b6fa48b38ec789d413c6b548a77b7ef33daf4c40f6a5ae6518c06d273f797b19`
(Butcherblock) and
`829cd3e63af69b788d99b7a98aec7adf3e954723e6b830fa9831edceeab47637`
(Crushbone). Real client alignment, dynamic doors, aggro, water effects and
zone transitions remain untested. No client/server input occurred.

## Copied client executable and segmented path audit — 2026-11-13 06:25 CST

**VERIFIED read-only source copy:** The Alienware retail client executable at
`/home/blizz/Games/everquest-legends/drive_c/users/Public/Daybreak Game Company/Installed Games/EverQuest Legends/eqgame.exe`
is 15,676,536 bytes, SHA-256
`65b8a28b2df70a256746567c4203c47f91696813865cba97f7151a5f4952503a`.
It was copied with a matching hash to the untracked
`~/.local/share/eql-automation/client-data/retail-full/bin/eqgame.exe`.
The PE32+ x86-64 executable was never launched or changed. A bounded static
string/reference search found target command and UI names (`TARGETNPC`,
`CLEAR_TARGET`, `GAUGETYPE_TARGET_OF_TARGET`) but **no verified unique target
ID, selection epoch, or target relationship signal**. A missing string or
reference in that search does not prove no runtime signal exists. REA's deep
analysis providers were unavailable here; Ghidra needs JDK 21, and Java is
absent. Its portable PE import inspection succeeded, but imports alone do not
answer the target question. The retained REA evidence bundle is outside git at
`~/.local/share/eql-automation/evidence/eqgame-pe-imports-65b8a28b.json`,
SHA-256 `50f6b9a78f1f2eaaefeedb358f132094d6d2afb238bc2cd2be57d446ac0779f3`.

**VERIFIED offline path audit:** The BSP sampler now attributes every sample
to `start_connector`, `corridor`, or `end_connector`. A focused synthetic test
checks both connector directions. The copied Butcherblock FAYHOUSE path still
has 27 samples: 2 start, 24 corridor, 1 end, with no copied labels or unknowns.
The copied Crushbone TIKIBAM path still has 10 samples: 3 start, 6 corridor,
1 end. Its two unknown BSP results are **one on the 5.407412-unit start
connector and one on the 0.49-unit end connector**; the corridor has none.
The earlier shorthand attributing both unknowns to the start gap was wrong.
The first unknown is a missing BSP child at WLD XYZ
`(-90.2200012, 691.169983, -30.9899998)`. Neither path is accepted for
movement. Untracked audit JSON SHA-256 hashes are
`5ad31164d0e1e6dbb897398dc62a7cc0808dd5df8d4cdd1185dc07d12a137850`
(Butcherblock) and
`c4e2745c8a3230a325f4d8adb63787cc942dde51eb30eb33459004994a90dde9`
(Crushbone), under `~/.local/share/eql-automation/nav-candidates/`.
`python3 -m pytest -q tests/test_region_audit.py` passed 4 focused tests;
the two copied-zone CLI audits and `compileall` passed. No client or server
input occurred.

## Assist target continuity and spell targeting — 2026-11-13 06:19 CST

**VERIFIED synthetic only:** Assist proposals now bind a unique target-selection
token, target relation (`self`, `friendly`, `hostile_npc`, or `hostile_player`),
and observed undead status. A newer observation with the same values and the
same memorized spell or available ability is required before a proposed key.
OFF, a target swap, relation/kind change, or gem change cancels the proposal
without advancing its cooldown. A forged queued action inconsistent with the
source role is rejected. No key sender exists in this build.

**VERIFIED copied client data:** `spells_us.txt`, SHA-256
`8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de`,
lists the selected Paladin/Cleric direct heals and HoTs with target type 51,
damage/stun with 5, undead damage with 10, and selected Yaulp/proc buffs with
6. [EQEmu's target type enum](https://raw.githubusercontent.com/EQEmu/EQEmu/master/common/spdat.h)
does not define 51. Its EverQuest Legends behavior is **unverified**. The
advisor therefore permits type-5 attack/stun only for an observed hostile NPC,
type-10 damage only when that NPC is also observed undead, and blocks self
heals, buffs, and Lay Hands until each is explicitly confirmed on the intended
private client. At self HP ≤65% with another target selected, assist pauses.

**VERIFIED static UI audit:** Copied `EQUI_TargetWindow.xml`, SHA-256
`d556f3a9cfe85301f4e4309012ce940f60ebb3f5c3ef2f88098d27cebaea0385`,
defines target HP/class/level widgets but no unique target ID or selection
epoch. Its con-color fill animation is commented out. The current gauge reader
reads player HP/mana only; the log reader tracks level, death and zone.
No supported static signal found here can prove same-name target switches or
hostile/friendly relation. **No live assist acceptance is ready.**

`python3 -m pytest -q tests/test_assist.py tests/test_screen_observer.py`
passed 9 focused tests; `--demo-assist` produced one synthetic `/cast 3` and
rejected it after OFF; `compileall` and `git diff --check` passed. No client,
server, account, or character was contacted.

## Provisional Detour path sampling against copied BSP labels — 2026-11-13 06:06 CST

**VERIFIED offline query and sampling:** The pinned Detour query tool now
emits its requested, snapped, and straight path points back in WLD XYZ;
checks both corridor and straight-path status for partial, truncated, or
out-of-nodes results; and reports endpoint snap distances. A local wrapper
checks the nav SHA-256 before and after querying, then binds the JSON to a
zone-named nav file and that hash. The audit accepts only complete queries,
rehashes that nav file, checks point counts and snapped endpoints, and samples
the straight segments **and the requested
endpoint-to-snap connectors** at intervals no longer than five WLD units.
It looks up copied WLD BSP labels at each sample. The filename/hash check
does not verify that the nav geometry matches the real zone. Missing or
ambiguous BSP regions remain unknown; no negative result establishes a
safe route.

The existing 24-polygon Butcherblock FAYHOUSE corridor yielded 8 straight
points and 27 connector-inclusive samples with no labelled or unknown BSP
regions. Its query JSON SHA-256 is
`5c28b2bb90d6b62b046247330971ff9fcaeaee35f4da9137b92bf901227c028e`;
the hazard audit JSON is
`40772f58ccb06016d49692c47879769a9222cdcca36810209796d27faa199a97`.
The 7-polygon Crushbone TIKIBAM corridor yielded 3 straight points and 10
connector-inclusive samples: no copied labels, but **two unknown BSP
samples**. Its requested start was 5.41 units from the snapped start.
Its query and audit hashes are
`c94fb013a3a823c2de5f396183f14b01dc6794b4c2255a993e948b5a2414621e`
and `9056e51e0e79f1e505674f6c824ff13aec6e029a25a6d3344ee8cc8c0e795cb9`.
These are **sampled label absences only**: narrow volumes, vertical levels,
doors, collision, aggro and live server behavior can invalidate either
corridor. No nav edge was promoted or moved in the client.

**VERIFIED positive detection control:** A fabricated WLD line at Z −50
across two copied Butcherblock water-labelled regions produced 41/41
water-labelled samples and still reported `route_accepted=false`. This
checks the new sampler's ability to flag a copied water label, not an
actual path the character could follow. All query and audit JSON stays
under `~/.local/share/eql-automation/nav-candidates/`, outside git.

## Offline BSP point and zone-label probes — 2026-11-13 06:03 CST

**VERIFIED copied-data algorithm and CLI:** A bounded WLD-XYZ point lookup
uses the 0x21 BSP plane test, one-based child/leaf references, and positive
left/negative right branch from [EQEmu's water-map implementation](https://github.com/EQEmu/EQEmu/blob/master/zone/water_map_v1.cpp#L493-L537).
The API takes raw WLD XYZ; map labels first use the copied-data XY frame
verified above. On a plane, a missing child, a cycle, excessive depth, or a
nonfinite distance it returns unknown. This matters in Crushbone, where the
copied tree has missing-child branches. Synthetic branch/unknown tests and
copied-data CLI probes passed. A lookup only reports the copied WLD's region
label; it does not establish client collision or a server transition.

**VERIFIED sampled label review:** None of the four Greater Faydark exit
labels falls inside a tagged zoneline region at its exact transformed point.
A bounded 5-unit XY grid within 100 units, sampled at label Z, nearest
flag-zero terrain Z and that surface plus 1, found a tagged candidate
40 units from the Butcherblock label, 30 from Crushbone, and 45 each from
Lesser Faydark and Northern Felwithe. The Butcherblock labels for Greater
Faydark, Dagnor's Cauldron and South Kaladim had sampled candidates 30, 20
and 20 units away; its Ocean of Tears boat/translocator label had none in
that search. Crushbone's Greater Faydark label landed in a missing BSP
branch and had a sampled tagged candidate 25 units away. These are nearest
**on the sampled grid and Z levels only**, and no candidate is an accepted
graph edge or actionable crossing. The untracked probe manifests under
`~/.local/share/eql-automation/nav-candidates/` have SHA-256
`7e7eec1a04a3cbbdc80e336524222b02bf0d4b80ec771f5782318c0bade3c9c9`
(Butcherblock), `0a0dd76cf3efa43ddbfbbab3a1fc99fa9f1af310218f1e9e72cc2f2ba9435235`
(Crushbone), and `141cd82a03648d7929a8a9e46a78a21d11cc651e99bdafe14d19a466011898ff`
(Greater Faydark). No movement, zone change, or client acceptance was run.

## Copied-client map frame, BSP labels and profile sensitivity — 2026-11-13 05:55 CST

**VERIFIED read-only GFay source:** Alienware's `gfaydark.s3d` and
`gfaydark_obj.s3d` were copied to the approved untracked client-data store
with source/local SHA-256 matches
`ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f`
and `3439c59e9c6c1623e85b29694d6a6161b924b0a9ece39751b0234ab5c6f71892`.
The copied `gfaydark.wld` is SHA-256
`3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138`.
No Alienware install or prefix write, login, or game input occurred.

**VERIFIED offline map frame:** A bounded audit compared unique top-level
client map-line endpoints with decoded WLD terrain vertices, rounded to
0.1 unit, across all eight XY sign/swap transforms. `map → WLD = (-map_y,
-map_x, map_z)` matched 1,557 Butcherblock, 3,787 Crushbone and 8,163
Greater Faydark vertices. The next-best transform matched 0, 49 and 2,
respectively; raw map XY matched 0, 8 and 0. This strongly supports the
frame transform for these copied assets, **not** a walkable map edge. Label
surface probing requires at least 5% of unique map points (minimum three)
to match and a threefold margin over the next transform, so one coincidental
vertex cannot establish a frame. The map audit manifests under
`~/.local/share/eql-automation/nav-candidates/`
have SHA-256 `f96642d193df59984c158167c67d8213f8acb11bbfab1e5f23dd1e3a5d1c25ba`
(Butcherblock), `2847766145022db7405acfebe5c0a4c5b1cb55845cbaf17a4d5011a8b7a8645d`
(Crushbone), and `c3f9fb5ffdf8dc740d145c119b2c3522e22cb5f36617e575417176932620901f`
(Greater Faydark).

**VERIFIED offline GFay label surface probe:** After that XY transform,
all four client exit labels intersect nearby flag-zero terrain triangles.
Their nearest surface Z minus label Z is about 0.8014, 0.8014, 0.8014 and
0.8013 units for Butcherblock, Crushbone, Lesser Faydark and Northern
Felwithe exits. Some XY points intersect multiple surface levels, so the
nearest height is only a candidate. The historical ~236.82-unit vertical
mismatch is **not reproduced at these four exits**; no global Z correction
has been applied. Actual player coordinates, collision surfaces and zone-line
transitions remain unobserved.

**VERIFIED copied BSP label audit:** Using [Lantern's 0x29 region parser](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/BspRegionType.cs)
and [0x21 BSP tree parser](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/BspTree.cs),
the bounded read-only audit validated all region IDs and tree references.
Butcherblock has 163 water-labelled and 5 zoneline-labelled region IDs;
Crushbone has 263 water-labelled and 3 zoneline-labelled IDs; Greater
Faydark has 9 zoneline-labelled IDs and no water-labelled IDs in these
records. Manifests under the untracked client-data store have SHA-256
`586f8b0aa230a9a574c53968889d40dbd20ecf0a88b74d74972c891b64a0594e`,
`7f172ebf532746483fb3618583759d5943d20b1c84a5ec3ad097ff5ff35c884f`,
and `bcf320e410ae558bb21e639ab45ee54650a5825a550f5a17b2afa99067f35acb`.
The region shapes/PVS are not decoded, and labels do not prove where the
client allows swimming or a transition.

**VERIFIED offline profile sensitivity:** The local baker now accepts
explicit height/radius/climb/slope after its original arguments. In the
same bounded Crushbone tile, compact `(6,3,3,50)` baked 290 polygons with
Boundary included or 289 excluded; conservative `(8,5,2,45)` baked 269 or
270. All four sampled Detour corridors completed, but the query now reports
start-to-nearest-polygon snap distances of about 3.04 units for compact and
5.41 for conservative (end snap 0.49). The comparison manifest SHA-256 is
`c11a97fc9045d531293a751c96a63b4300da01e6d8a723c7b04f79d6379a8031`.
The existing Butcherblock FAYHOUSE complete sample snapped by 0.65/0.30
units; a different sample stayed partial despite 1.53/0.65-unit snaps.
These different samples do **not** resolve the historical conservative
profile disconnect. No profile or corridor is real-client accepted.

## Crushbone copied-client audit and Boundary variants — 2026-11-13 05:47 CST

**VERIFIED copied data, read-only:** Alienware client archives in
`/home/blizz/Games/everquest-legends/drive_c/users/Public/Daybreak Game Company/Installed Games/EverQuest Legends/`:
`crushbone.s3d`
(SHA-256 `a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f`)
and `crushbone_obj.s3d`
(SHA-256 `d80521fdb69c53497d3070b4869dd33ecbdeafdca9ee5f6a3010a93e228f14a5`)
were copied into `~/.local/share/eql-automation/client-data/retail-full/assets/`;
remote and local hashes matched. The install and prefix were not changed.
The copied `crushbone.wld`, `objects.wld`, and `crushbone_obj.wld` hashes are
`ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1`,
`fc7535a0c3ade7a4e3e76733d301acee697dddbf0d2db9ae41718009a29bb8c8`,
and `efe378db3c69b1f2d8b362bc3c32b997bf0d8cec9eac418f893c1ec897b3be95`.
The offline audit found 178 placements, all exact-name matched to copied
actor models; 44 model definitions exist, with two door definitions unused
by static placements. It decoded 2,694 terrain meshes and 44 object meshes.
All 2,738 mesh material chains resolved, including 4,057 flag-zero terrain
faces labelled Boundary. Some raw material types remain unknown; their
collision meaning has not been inferred.

**VERIFIED provisional scene and bake:** The included-Boundary Crushbone OBJ
has 47,268 vertices and 26,570 faces, SHA-256
`806b40d87e1810bc1bba549fc4468fd585e7402a1e812a1be0a8d67ae7793e3d`.
The excluded variant has 39,405 vertices and 22,513 faces, SHA-256
`8dd77042278bd9821d3d95ed2cefd4440070e4617201d5eb9cba1818794d372b`.
The difference is the 4,057 Boundary faces. An independent OBJ scan checked
finite coordinates, face indices, counts, and hashes. A bounded 256×256
offline tile near the copied `TIKIBAM_ACTORDEF` placement baked with the
candidate `(8,5,2,45)` profile to 269 polygons with Boundary included
(nav SHA-256 `364a0f9cc85bf23cb11609c1f40fe7511884821b955be67a473ee572511371b4`)
and 270 polygons when excluded
(nav SHA-256 `3c6ca8e4d2345e7ee2a40ec7d3083eaaef6513fee80feb30550e50417f36548b`).
Both sampled offline Detour queries completed through seven corridor polygons
and three straight points. Artifacts and JSON provenance stay under
`~/.local/share/eql-automation/`, outside git.

**VERIFIED Butcherblock comparison:** Excluding its 6,443 Boundary faces
produced a 105,860-vertex, 98,233-face OBJ, SHA-256
`553b7b61ab09c784484d04b3f8de522e95eab9bbe50c890d21ba417e4359f0d1`.
The two sampled FAYHOUSE tile bakes were byte-identical, SHA-256
`6347c67693d782d4643b5a45c15b13c9415606aecd678cf6e50b1df1e4db3863`.
This local equality does not establish Boundary behavior elsewhere;
Crushbone's differing polygons show that filtering can matter. **No actual
client acceptance is ready.** Neither zone has a verified movement edge,
water/door rule, zone transition, suitable camp, or XP measurement. The
private server endpoint/separate client config is still missing, and the
only located login target is Daybreak live. No real login/input was attempted.

## Bounded provisional Recast/Detour bake — 2026-11-13 05:39 CST

**VERIFIED offline toolchain and synthetic smoke:** `tools/build_local_nav_tools.sh`
rebuilds two local C++ tools against pinned Recast/Detour
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`. A fabricated 64×64 flat
WLD-XYZ plane baked to a 17-polygon Detour mesh; an offline query from
`(10,10,0)` to `(50,50,0)` completed through 6 corridor polygons and 2
straight points. The tools convert WLD XYZ/Z-up to Recast `(-X,Z,Y)`/Y-up and
use a bounded grid. No game or account input was sent.

**VERIFIED copied-scene local bake:** Around the copied
`FAYHOUSE_ACTORDEF` location `(1425.765747, 2737.740967, -3.652549)`, a
256×256-unit region of the winding-corrected provisional OBJ selected 885
triangles, 160 of which Recast marked walkable by slope. With an **offline
candidate** agent profile height 8, radius 5, climb 2, slope 45°, the bake
produced 323 nav vertices, 156 nav polygons, and 25,484 Detour data bytes.
The untracked data is
`~/.local/share/eql-automation/nav-candidates/butcher-fayhouse-128.nav`
(SHA-256 `6347c67693d782d4643b5a45c15b13c9415606aecd678cf6e50b1df1e4db3863`).
The offline bake/query manifest SHA-256 is
`a2a77cfbad2f05af4cc9ad737c7592632c3a10e2f869271c91c0e3231d561991`.
An offline Detour query from WLD `(1405.765747,2757.740967,-3.65255)` to
`(1405.765747,2797.740967,-3.65255)` completed through 24 corridor polygons
and 8 straight points. A different sampled query from the house location to
`(+50,+50)` found both nearest polygons but returned a partial corridor.
This is **not** the historical Nov 6 mesh or route; its earlier clearance
failure is not resolved by these different local samples.

**Acceptance remains closed:** The candidate OBJ contains uncertain Boundary
faces and lacks verified water/door handling. Recast's route is an offline
geometry query, not observed game movement. No waypoint or zone edge has been
promoted into the active bot graph; actual client acceptance remains false.
The intended private server endpoint or separate login config remains missing.

## Butcherblock material chains and OBJ winding — 2026-11-13 05:34 CST

**VERIFIED copied-client material audit:** All 1,925 `0x36` meshes have valid
`0x36 → 0x31 → 0x30` material references; their polygon texture groups cover
every triangle exactly. Of the terrain's flag-zero faces, 45,384 use Diffuse
material parameters and **6,443 use Boundary** parameters. Its 868 flag-`0x10`
faces use Diffuse. Across the 1,862 non-sentinel object instances, all 53,028
flag-zero faces use Diffuse or Diffuse6, and all 28,655 flag-`0x10` faces use
Diffuse or transparent classes. The bounded audit manifest SHA-256 is
`79884f2e18dd69178b500a87a85ecf283177e6a4b41b390febd308779eef33e3`.
The current provisional OBJ includes the 6,443 Boundary faces as candidate
obstacles. The [Lantern OBJ writer](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Exporters/MeshObjWriter.cs)
has an option that excludes Boundary/Invisible geometry; no live evidence yet
establishes which choice matches this client's movement. Water regions and
door state are likewise unverified. Two focused synthetic material tests and
the copied-data audit passed.

**VERIFIED OBJ orientation correction:** A normal check found that 41,501
flag-zero terrain faces in the copied WLD's original index order point in
negative Z, versus 1,561 positive and 8,765 zero projected Z normals.
Following the Lantern writer, the provisional OBJ now writes each face in
reverse index order. An independent scan of the regenerated 115,411-vertex,
104,676-face OBJ found 41,501 terrain faces with positive projected Z normals,
1,561 negative, and 8,765 zero. Its current SHA-256 is
`1ec7706037c35c06205c026c4ed56c1b4032fd2fb7a8e2dbe0cf2490d18a1bc3`;
the manifest SHA-256 is
`aebc4fd5866ac890c30278b9e1eca2567de68ccb99f2075b96f904fdfe5a73f9`.
The previous `c4faf0...` OBJ remains as a historical local artifact and is
superseded for future bakes. **Neither orientation nor material inspection
establishes a walkable route.**

**VERIFIED local toolchain:** The upstream RecastNavigation source was cloned
outside git to `~/.local/share/eql-automation/toolchains/recastnavigation`,
checked out at the historical pin
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`, and built with CMake/Ninja
into local Recast and Detour static libraries. Demo, examples and upstream
tests were disabled. No navmesh bake or Detour query has yet run. The full
Butcherblock scene spans thousands of coordinate units, so a bounded local
bake is the next offline check; its output will remain provisional.

## Butcherblock provisional composed scene — 2026-11-13 05:29 CST

**VERIFIED copied-client model links:** All 75 type `0x14` actor definitions
resolve through one-based `0x2D` references to 75 distinct type `0x36`
meshes; each mesh has the exact corresponding `_DMSPRITEDEF` name. All 1,884
locations refer to one of these models by exact actor name. Across the 1,862
non-sentinel instances, the object meshes contribute 83,125 encoded vertices
and 81,683 triangles: 53,028 flag-zero, 28,655 pass-through `0x10`, and
**179 exact zero-area triangles**. This independently reproduces the
historical 179-face cleanup count, while the old navmesh artifact remains
absent.

**VERIFIED provisional geometry output:** `--build-butcher-candidate-scene`
streamed copied terrain and static-object meshes into
`~/.local/share/eql-automation/nav-candidates/butcher-solid-candidate-c4faf053a4e006c6.obj`
(SHA-256 `c4faf053a4e006c68cbb115b58cccfe293c219a24a10d39f2a73fdd3d1889624`)
in WLD XYZ with Z up. It contains 115,411 used vertices and 104,676
flag-zero, nondegenerate triangles, of which 51,827 are terrain and 52,849
are static-object instances. It excludes 29,523 pass-through triangles, 179
zero-area instance triangles, and 22 dropped-tree instances. A separate
read-only OBJ scan confirmed its hash, all face indices, finite coordinates,
counts and bounds. The untracked provenance manifest SHA-256 is
`1f6f07433e07b9368c06fbfdf39d4e41b144785340386936a387695fce61865c`.
This was the initial 0.19.0 artifact; the 0.20.0 winding-corrected artifact
and manifest above supersede it for future bakes.
The output and source client data are outside git and outside the release
archive. Focused synthetic tests checked exact model linking, uniform scale,
rotation axis/order and face filtering.

**INFERRED transform, still gated:** Projection follows the owner-data-compatible
[LanternExtractor object parser](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/ObjectInstance.cs)
and [OBJ writer](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Exporters/MeshObjWriter.cs):
uniform scale, rotations from raw WLD units, then mesh center and instance
position. All copied scale fields used here agree, and no copied instance has
raw X rotation. This reproduces an exporter candidate, **not verified game
collision**. Shader/material filtering, water, doors, object state, conservative
agent clearance, navmesh routing and actual client movement remain unverified.
The historical 18,292-vertex/10,694-polygon mesh was a different reported
composition; its hash was not reproduced. No route was accepted.

## Butcherblock old-format mesh arrays — 2026-11-13 05:24 CST

**VERIFIED copied-client decoding:** A read-only `0x36` decoder for the
client's WLD version `0x00015500` parsed all 1,925 Butcherblock terrain and
object mesh records with bounded arrays and valid polygon indices. The terrain
`butcher.wld` contains 1,850 meshes, 64,230 encoded vertices and 52,695
triangles. Its polygon flags are 51,827 `0` and 868 `0x10`; no exact
zero-area triangles were found in the raw terrain mesh coordinates.
`butcher_obj.wld` contains 73 meshes, 7,092 vertices and 5,615 triangles
(4,682 flag `0`, 933 flag `0x10`, 65 exact zero-area triangles).
`butcher_2_obj.wld` contains 2 meshes, 1,011 vertices and 1,248 triangles
(1,224 flag `0`, 24 flag `0x10`, no exact zero-area triangles). The decoder
uses the [EQEmu WLD mesh format](https://docs.eqemu.dev/client/guides/file-formats/wld-by-windcatcher/),
where flag `0x10` denotes pass-through surfaces, and verifies the actual
copied files. Two synthetic mesh checks and the copied-data CLI audit passed.
The untracked `butcher-meshes.audit.json` manifest SHA-256 is
`043e827eafb1760c632ae43dc678b109666b9a5836ac44cf779abdd1899a4f21`.
Mesh centers, raw vertices and polygon flags are now decoded in memory;
actor-to-mesh references and placement transforms have not been composed.
**No collision mesh, navmesh, conservative clearance, or real-client movement
is yet verified.** The historical 18,292-vertex/10,694-polygon mesh was a
different reported composition and has not been reproduced.

## Butcherblock WLD fragment and placement provenance — 2026-11-13 05:21 CST

**VERIFIED copied-client structure:** A bounded read-only WLD inventory of the
four WLD members in the copied Butcherblock S3D files parsed their exact header
fragment counts. `butcher.wld` has 5,738 fragments, including 3,653 type `0x22`
regions and 1,850 type `0x36` mesh candidates. `objects.wld` has 5,652
fragments, exactly 1,884 each of types `0x32`, `0x33`, and `0x15`.
`butcher_obj.wld` has 1,149 fragments and 73 type `0x36` mesh candidates;
`butcher_2_obj.wld` has 38 fragments and 2 type `0x36` candidates. All four
parse through the declared fragment count with a four-byte `ffffffff` trailer.
The single out-of-range negative fragment-name reference is the first `0x35`
fragment in `butcher.wld`; it is reported as unresolved, not mistaken for an
object name. The parser follows the published
[VisualEQ WLD loader](https://github.com/alimalkhalifa/VisualEQ/blob/master/src/server/loaders/s3d.js)
and checks bounds against these copied files. No geometry has been composed.

**VERIFIED placement audit:** The 1,884 `0x15` locations in `objects.wld`
resolve to 69 distinct `_ACTORDEF` names. Every name matches one of the 75
distinct type `0x14` definitions in the two copied object-library WLDs by
**exact name**; similar names such as `BTENT`/`BTENT1` are kept distinct.
Twenty-two tree locations have the exact float32 Z value
`-32767.998046875` (10 `DPINE1`, 5 `DCEDAR1`, 5 `RPINE1`, 2 `BPINE`), leaving
1,862 non-sentinel locations. This independently reproduces the historical
1,884/1,862/22 count; it does not reproduce the historical navmesh hash or
validate any route. The six unused actor definitions include four door names
and two models in `butcher_2_obj.wld`. The audit records `collision_composed:
false` and `navigability_verified: false`. Four WLD inventories and the
placement audit are retained only in the untracked
`~/.local/share/eql-automation/client-data/retail-full/assets/manifests/`.
The placement audit manifest SHA-256 is
`42954af5065d6b5d1098a7b39b036e46e5229d1a7778dc27fc3ef55aa8e1a0f2`.
Four focused synthetic WLD/placement tests and the real copied-data CLI audit
passed. No Alienware install/prefix changes or live game input occurred.

## Butcherblock client archive inventory — 2026-11-13 05:15 CST

**VERIFIED read-only source/copy:** The Alienware game root contains
`butcher.s3d` (2,742,696 bytes, SHA-256
`af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839`),
`butcher_obj.s3d` (3,394,472 bytes, SHA-256
`ad4c886395c9af7f3de17be1c1a24785e295f892097b8e5785eec670a089c047`),
and `butcher_2_obj.s3d` (113,036 bytes, SHA-256
`cb5cabede79b53f9b884c15712ec07225f5ca81e1093be36f7d3d12b8ea03ece`).
These plus `butcher_assets.txt` were copied by read-only SSH into the
untracked `~/.local/share/eql-automation/client-data/retail-full/assets/`;
local hashes match Alienware. The install/prefix was not modified. The archives
have `PFS ` at offset 4. REA `open_binary` reported this custom container as
unsupported, so a bounded read-only PFS inventory was implemented from the
[PFS format description](https://github.com/martinlindhe/eqformat_pfs/blob/master/format_pfs.md)
and cross-checked against the owner's bytes.

**VERIFIED local member inventory:** `butcher.s3d` has 62 members, including
`butcher.wld` (2,645,544 bytes, SHA-256
`d4c8db248f4b7d23fe714ff3dceedaf0c83696b178327efcf88d6091e35c722c`)
and `objects.wld` (584,504 bytes, SHA-256
`605bc3b571a8779e62f09481c860b227024b0a97bd5877f4932517335682707b`).
`butcher_obj.s3d` has 149 members, including `butcher_obj.wld` (225,292
bytes, SHA-256 `06d6757279a3803a5c2b908b7f8bbce3c414bc802bd8271cb8558ac85acccc00`).
`butcher_2_obj.s3d` has 9 members, including `butcher_2_obj.wld` (82,812
bytes, SHA-256 `36598801bbe072e6ac72c6b4e368a14eeecebb478da35f9a004e7352705f54df`).
Full member manifests are outside git under `assets/manifests/` in that store.
Two synthetic PFS parser tests and three real copied-archive CLI smokes passed.
At this archive-inventory stage, no WLD mesh, static-object placement,
coordinate transform, collision clearance, or route had been decoded or
accepted. The later WLD audit above has since decoded placement provenance;
the historical Nov 6 serialized mesh remains absent.

## Butcherblock collision-evidence reconciliation — 2026-11-13 04:53 CST

**OBSERVED coordinator report, historical and not independently reproduced:**
The Nov 6 desktop task reported a Butcherblock terrain-plus-static-object
Recast/Detour bake with 1,884 instance records, 1,862 applicable placements,
22 rejected dropped-tree sentinels, corrected exact-name matching for duplicate
`btent`/`orctent`/`hgflag` placements, and 179 removed zero-area faces. The
reported composed mesh had 18,292 vertices and 10,694 polygons, serialized
SHA-256 `d1b57d2dab7b975e8d62821725bf992634136774720707fa103af10e238aad85`.
The reported closed-fayhouse ray hit a barrier at `t=0.1888`, while a
Yard↔South Kaladim route remained. Historical pinned sources were Lantern
`bb4cdba64c1f0453568f3a11f158a38ee1659d0c` and Recast
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`; a later local `bnav_query`
report described a complete 24-polygon/10-point path. The later overlay review
and classification of 23 detail-cleanup warnings is likewise historical.
These reports are **not** current retained navmesh proof or real-client acceptance.

**VERIFIED scoped reconciliation:** No Recast/Detour navmesh, placement table,
bake recipe, `bnav_query`, overlay audit or matching historical hash was found
in this project or `~/.local/share/eql-automation/`. A SHA-256 scan of 559
current code/store/release/run files (26,463,952 bytes, excluding copied client
data) found no serialized mesh hash; local release archives contain no
navmesh-named members. The removed historical working copy was not accessed,
recreated or touched. Thus the historical mesh **cannot be reused from
retained inputs in this project/store**. At the time of that reconciliation,
the only retained Butcherblock/Crushbone map artifacts were client drawing
geometry and labels, explicitly marked `navigability_verified=false`. The
copied S3D/WLD inputs documented above were added afterward and support a
new bake once their geometry and transforms are verified.

**VERIFIED client-map provenance:** Active snapshot `e36ee7fd32a5c4b42f45`
contains `butcher.txt` (24,225 drawing lines, 0 labels, source SHA-256
`04db2b25ebc89a44aaf685899cdb781da68fe3106b09c445bcc526c261d4029c`)
and `crushbone.txt` (5,469 lines, 0 labels, source SHA-256
`e22f714cbd7733918b7f0fd0c6a9b0592974ff9b5e497841e9dc69202396b313`).
The thin label layers are `butcher_1.txt` (1 line, 4 labels, SHA-256
`a1cea4378673518b5d3d63fa43bfa42d62bbbbec2a58d15fe7e3ad907b60bcb0`)
and `crushbone_1.txt` (0 lines, 1 label, SHA-256
`43704aa2af7de192cdbd7b61920278bdc7fe88bd80b1e603eac9c95aa450c87c`).
Client zone IDs are 68 Butcherblock Mountains, 54 Greater Faydark, 58 Clan
Crushbone. Labels suggest **review only** Butcherblock→Greater Faydark→Crushbone;
no zone transition has been traversed or accepted as a graph edge. The
reported Greater Faydark label vertical mismatch of about 236.82 units is
unresolved. Reported agent dimensions `(6,3,3,50)` routed while conservative
`(8,5,2,45)` disconnected; current clearance acceptance is absent. Dynamic
doors, water, zone transitions, mob levels, camp safety, XP/hour, and actual
movement are unverified.

**Result:** Butcherblock is the first navigation/camp review target and
Crushbone the next, followed by camps chosen from a character's observed
level and suitability. The current bot has no accepted real-client route.
Actual client acceptance is **not ready**: the private endpoint/separate login
config remains unknown; a fresh test character has not logged in; and no
retained collision mesh/recipe plus clearance and live movement evidence is
available. ASSIST remains movement-free.

**VERIFIED offline audit tool:** `python3 -m eql_automation --audit-butcherblock`
reads the active snapshot, rehashes the four copied client maps, and reports
their verified source hashes, historical
mesh absent, all collision/live acceptance flags false, and six missing
evidence classes. An optional artifact can be hashed only inside
`~/.local/share/eql-automation/`; a matching hash is provenance only and
never creates graph edges. Eleven focused navigation/evidence tests passed,
including refusal of artifact and copied-map symlinks outside that store and
detection of a changed copied map.

## Offline player gauge reader — 2026-11-13 04:22 CST

**VERIFIED copied client XML:** Default PlayerHP has red FillTint
`(150,0,0)` with EQType 1; PlayerMana has blue FillTint `(0,100,200)` with
EQType 2. TargetHP is also red `(150,0,0)`, so color alone cannot identify
the player gauge. The copied XML hashes are recorded below. **VERIFIED
synthetic only:** The inherited flat-bar algorithm now runs in pure Python
without NumPy. A `GaugeReader` accepts a calibrated full-frame player HP/mana
crop only when the game window is reported focused, its size and active layout
fingerprint match, and both colored fills remain readable. Calibration
requires bars at least 85% full. In a fabricated 120×30 image it returned
HP 0.5 and mana 1.0; an unfocused frame returned unknown. The reading can be
passed to `AssistObservation`, which still requires target, character, gems
and chat state. No actual game screenshot, active skin, calibration or
character state was observed.

## Default client UI widget inventory — 2026-11-13 04:04 CST

**VERIFIED read-only client data:** The Alienware's `eqclient.ini` has `Log=1`
and `UIScale=1` (SHA-256
`a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc`).
Seven default `uifiles/default/EQUI*.xml` definitions were copied read-only
to the untracked local client-data store and their source hashes checked.
`EQUI.xml` includes the player, target, spell gem, chat, inventory and options
windows. A validated index contains 557 static widget IDs. Representative
widgets are PlayerHP EQType 1, PlayerMana 2, ExpGauge 4, LevelLabel 2,
TargetHP 6, Target_Class 1000, Target_Level 1001, spell gems
`CSPW_Spell0`–`CSPW_Spell13`, and editable `CW_ChatInput`. The keyboard
assignment list is present in OptionsWindow. The derived index is
`~/.local/share/eql-automation/map-store/indices/ui-widgets-446c8657ad6284caf128.json`.

**LIMIT:** Static XML does not identify the active skin, runtime positions or
values, current target, character identity, gem IDs, chat focus, XP/hour, or
valid hotkey bindings. The client was not launched and no character/log was
read. The offline assist demo proposed `/cast 3` for a synthetic level-1
Paladin and rejected the proposal after OFF. Concurrent emergency stop and
mode-indicator failure tests leave the controller latched OFF. No game input.

## Strict offline assist proposal — 2026-11-13 04:00 CST

**VERIFIED synthetic only:** `AssistAdvisor` wraps the inherited Paladin/Cleric
rotation without calling its preparation, autoattack or input path. It
requires an explicit character/class/level, currently verified target,
focused game with chat closed, health/mana and gem observations at most one
second old, and an observed available ability before proposing that ability.
It emits only a typed action with a cancellable ASSIST permit. The proposal
becomes invalid when mode is OFF, focus/target/observations change, or a
required ability disappears; cooldowns advance only after a confirmed send.
The rotation's hardcoded Bash/Smite/Lay Hands choices are now filtered by an
explicit observed ability set. 39 focused tests passed. **No live observer,
sender, in-game hotkey, character login or combat run was performed.**

## Client class levels and rotation eligibility — 2026-11-13 03:56 CST

**VERIFIED read-only client data:** Alienware `<game root>/dbstr_us.txt`
(SHA-256 `fd0508baa7151cc7575198860394967a40d72aeecc2db02a2c3024ea1ffbcefe`)
contains class IDs 1–16 in `class_id^45^name` rows. A copy is under the
untracked `~/.local/share/eql-automation/client-data/retail-full/` directory.
The paired `spells_us.txt` (SHA-256
`8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de`)
has 74,021 unique-ID, 174-field rows. Its fields 36–51 form the 16 class
level columns. **INFERRED from client IDs and corroborated by known Cleric and
Paladin rows:** field index `35 + class ID` is that class's level. `Strike`
and `Minor Healing` have Cleric/Paladin level 1; `Yaulp` has Cleric level 1
and Paladin level 9. The new index parses 1,450 rows with at least one class
level 1–50, stores only derived metadata outside git, and exposes class/level
queries. These rows include skills/discipline-like entries and **do not prove
server availability, vendor stock or scribing**.

**VERIFIED bug fix:** The copied October rotation planner previously filtered
spells by the lower of Cleric and Paladin levels. It could therefore offer
`Yaulp` to a level-1 Paladin. Profiles now require an explicit character
class and check its own level. Real copied client data produced no
class-invalid profiles at levels 1–50 for Cleric or Paladin; Paladin Yaulp is
absent at level 1 and present at level 9. This validates client catalog
eligibility only. It does not verify any live rotation or character spellbook.
The full 224-map retail text import was rerun into atomic snapshot
`e36ee7fd32a5c4b42f45` so its profile-validity flag reflects the corrected
class-specific check. The geometry totals remain 1,057,974 lines and 1,445
labels. 37 focused tests passed.

## Offline mode control — 2026-11-13 03:50 CST

**VERIFIED synthetic only:** A running CLI now accepts `mode full|assist|off`
and simulated `key F7|F8|F9` events, reports mode/generation/reason on screen,
and cancels queued intents when the mode changes. Already drained intents keep
their original permit so a sender can reject them after a switch. `safety
REASON` latches OFF until explicit reset. ASSIST denies movement, target,
autoattack, loot, vendor, camp, zone, login, recovery, scribe and memorize
intents. A focused CLI smoke queued MOVE in FULL, switched to ASSIST and
dropped it, then queued HEAL in ASSIST, switched OFF and dropped it. 31 focused
tests passed. **No keyboard grab, game overlay, input sender or live client
test exists.** The October tool already uses F8 and F9 and its prepare/combat
path changes spell gems and autoattack, so it cannot be reused unchanged for
strict ASSIST. The target remains unverified private; no character progress.

## Offline navigation controller — 2026-11-13 03:21 CST

**VERIFIED synthetic only:** A `WorldNavigator` now requires an observed start
position, explicit allowlists of traversed movement edges and zone lines, and
observed waypoint/zone arrivals. A stall at the confirmed source quarantines
both directions of that edge and replans; a mid-edge stall, unknown start,
unexpected zone, failed zone transition, missing verified route or exhausted
retry budget pauses. It emits intents only and has no game input transport.
The retail map drawing lines and POI candidates remain outside the verified
edge allowlists. A CLI synthetic demo replanned from `short` to `alternate`
and arrived; 29 focused tests passed. No real-client path was traversed.

## Zone-line review candidates — 2026-11-13 02:53 CST

**VERIFIED offline:** Cross-referencing the 1,445 map labels with the client's
701 zone names produced 351 unverified transition review candidates:
224 `to_` labels exactly match a client zone display name, 4 match after
reordering the same words, 48 unprefixed labels exactly match, and 75 `to_`
labels do not match a zone display name. For example, `to_East_Cabilis`
matches client zone ID 106, `Cabilis East`, by word order only. This is a
name association, **not** a working zone line or a destination map-stem
mapping. No transition was inserted into the navigable `WorldNav` graph.

A targeted read-only search of the Devbox Coordinator workspace and prior
rotation project found no separate private endpoint or login configuration.
The intended private server remains unidentified. 23 focused tests passed;
no client/server or character action occurred.

## Searchable map labels — 2026-11-13 02:25 CST

**VERIFIED offline:** The active 224-map snapshot has 1,445 labels. An untracked
POI index at
`~/.local/share/eql-automation/map-store/indices/e0aa3e31762d31fd4c1e.json.gz`
preserves each label, map name, coordinates, size and RGB. Text-only hints are
303 `to_` zone-exit candidates, 60 portal candidates, 109 merchant labels,
84 spell labels, 3 combined merchant/spell labels and 886 other landmarks.
The CLI can search labels by text/map and find nearby labels. No color is used
to infer type: blue labels also mark unrelated places, and labels may repeat.
**No label is verified as an actual zone transition, vendor inventory or safe
route.** 21 focused tests passed. The private server endpoint remains unknown.

## Full retail text-map snapshot — 2026-11-13 02:01 CST

**VERIFIED read-only transfer:** The Alienware's top-level `maps/` contains
224 `.txt` files totaling 78,918,163 bytes. The paired `.txt:crc` sidecars
were excluded. A rate-limited `rsync` also copied text maps in three nested
`Solo_Leveling`/backup directories (923 text files, 306,720,534 bytes total),
but the importer deliberately selected **only the 224 top-level client maps**;
no nested custom/backup map was imported. No remote file was modified.

**VERIFIED local import:** snapshot
`~/.local/share/eql-automation/map-store/snapshots/e0aa3e31762d31fd4c1e/`
holds 224 compressed geometry files (about 13 MB total), 1,057,974 drawing
lines, 1,445 labels, 0 unrecognized records, 701 zone names and 198
Paladin/Cleric spell records. All 50 prior rotation profiles passed validation.
`map-store/current.json` points to this snapshot. Import uses a temporary
directory and atomically promotes a complete snapshot, so a failed parse
cannot replace the active one. **Navigability remains unverified:** map lines
are rendered geometry, and labels only indicate candidate places. No client
map line has been treated as a traversable route.

**VERIFIED code checks:** 19 focused tests passed, including duplicate/nonfinite
point rejection and snapshot promotion after a source change. No private server
endpoint has been found; no character or service was contacted.

## Private-target clarification and retail data check — 2026-11-13 01:39 CST

**USER-STATED:** The intended automation target is a private EverQuest Legends
server, location unknown; use the retail client for now. **VERIFIED:** The sole
EverQuest Legends Lutris client found in likely Alienware locations still has
`eqhost.txt` pointing to Daybreak's official
`lvseqns-livl01.everquestlegends.com:15900`. No separate private client/login
configuration was found in bounded Alienware Lutris, Games, Projects or Desktop
checks. Bounded devbox `~/dev`, `~/gbsw`, Docker and listener checks found no
private EQ/EQEmu candidate. `banshee-ax41` was offline; the reachable Tailscale
peer `Banshee` had no candidate in its likely project paths, Docker containers,
services or common EQ listeners. These are bounded negative searches, not proof
that no private server exists elsewhere. **Exact missing piece:** the private
server endpoint or a separate client/login configuration that points to it.
No official service was contacted and no character was used.

**VERIFIED retail read-only copy:** From the Alienware client, two map text
files, `Resources/ZoneNames.txt`, `spells_us.txt`, and `eqhost.txt` were copied
to `/home/blizz/.local/share/eql-automation/client-data/retail-sample/`.
Their SHA-256 hashes match the source values already recorded below; the
`eqhost.txt` copy hashes to
`e8682ae8189d2082de41e87ce6fe82a9e055e6fe16c12ffa1a09bb84127395d8`.
No remote install/prefix file was modified. Import results in the untracked
`~/.local/share/eql-automation/map-store/`:

- `fieldofbone.txt`: 5,238 drawing lines, 11 labels, 0 skipped records.
- `freeportwest.txt`: 16,992 drawing lines, 8 labels, 0 skipped records.
- Zone-name list: 701 entries.
- October Paladin/Cleric parser: 198 spells, all level 1–50 profiles valid.
- **Navigability is unverified:** map `L` records are drawing geometry, not
  proven walkable edges; `P` labels are candidate places, not confirmed zone
  transitions/vendors. No nav graph is generated automatically from them.
- A read-only target inspector classifies this copied `eqhost.txt` as official
  and rejects it as a private target. Future input must match a separately
  reviewed private host, port and `eqhost.txt` hash.

## First-step result — 2026-11-13 00:38 CST (current)

**VERIFIED:** The owner's installed EverQuest Legends client is on the Alienware
(`alienware-bazzite`, host `bazzite`) and points to Daybreak's official, live,
commercial service. It is not an EQEmu/private-server setup. No client was
launched, no character was logged in, and no existing character log was read.
The older material below is retained as handover history; its statements that
the client/server were not found are superseded by this section.

### Alienware install and service evidence

Read-only checks over the `alienware-bazzite` SSH alias found:

| Item | Alienware path or value | SHA-256 |
| --- | --- | --- |
| Lutris configuration | `/home/blizz/.local/share/lutris/games/everquest-legends-1782570403.yml` | `d7a430f39a38b1d088e56ada053b0c454a08a5cb1490418cca4a66b1a6dfb481` |
| Desktop shortcut | `/home/blizz/Games/everquest-legends/drive_c/users/blizz/Desktop/EverQuest Legends.lnk` | `b6c054bcf8043f57e2a60635e7931bf59c3929a97d6e3d4327480b05c50c7259` |
| Login host | `<game root>/eqhost.txt` | `e8682ae8189d2082de41e87ce6fe82a9e055e6fe16c12ffa1a09bb84127395d8` |
| Login client configuration | `<game root>/eqlsClient.ini` | `83c1bd98a27cdc4355d479e59070e6ef9de862388279571d50afee64a2482446` |
| LaunchPad configuration | `<game root>/LaunchPad.ini` | `e727a7e04a0f1f86247461f1490c11a5abb68ca5019dc5ed2252fbc01eda6743` |
| Zone names | `<game root>/Resources/ZoneNames.txt` | `840b61b01deb4dfb8f49cf13e007364a629ce380c165aad5bb37adba6e52cd39` |
| Spell catalog | `<game root>/spells_us.txt` | `8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de` |
| Spell strings | `<game root>/spells_us_str.txt` | `9ce629ec15a7625ff1156256e71a3c954a1cb2fa9bf701692a7529e9b3bf3dab` |
| Example map | `<game root>/maps/fieldofbone.txt` | `5e475aa926ab0eb176e04ebaa9f5264cacc02848e294f7b2ad402f6d5aaf1d85` |
| Example map | `<game root>/maps/freeportwest.txt` | `4e1fdfc54a99f5a9b5cb8903fb08430ea9752b2645ad58809f7c4299b80e0706` |

`<game root>` is
`/home/blizz/Games/everquest-legends/drive_c/users/Public/Daybreak Game Company/Installed Games/EverQuest Legends`.
The Lutris prefix is `/home/blizz/Games/everquest-legends` (about 13 GB).
The shortcut targets `C:\\users\\Public\\Daybreak Game Company\\Installed Games\\EverQuest Legends\\LaunchPad.exe`.
`eqhost.txt` says `[LoginServer] Host=lvseqns-livl01.everquestlegends.com:15900`;
that name resolved to `69.174.201.2` at the check. `eqlsClient.ini` refers to
`https://account.daybreakgames.com` and `http://www.everquestlegends.com`.
There are 448 `maps/` files and 701 zone-name lines. The map example uses
`L x,y,z,x,y,z,R,G,B` records. These observations establish the installed
client's configuration, not a witnessed connection: the client was not run.

**VERIFIED policy conflict:** [Daybreak's EverQuest Legends Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct)
prohibit unauthorized servers/emulators in rules 13–14, and their play-nice
policy prohibits AFK/unattended gameplay. [Daybreak EULA §4.6](https://www.daybreakgames.com/eula?locale=en_US)
bars bots or macros that allow unattended play or otherwise affect gameplay;
[Daybreak Terms of Service §10](https://www.daybreakgames.com/terms-of-service?locale=en_us)
also forbids unauthorized software or macros that modify gameplay or give an
advantage. **INFERRED:** The requested full-auto level 50 run and rotation-only
assist on this live service fall within these prohibitions absent Daybreak's
express written authorization. A private/EQEmu EQL server is also not a clear
fallback under rules 13–14. This conflict was reported to the coordinator for
task `829a00229b29`. Live automation and private-server testing are held;
offline simulation and read-only analysis can continue.

### Earlier October rotation tool

**VERIFIED read-only review:** `/home/blizz/Projects/everquest-legends-rotation/`
is a Paladin/Cleric assist prototype. `rotation_core.py` parses the client's
spell catalog, filters a fresh `/outputfile spellbook` export, chooses 1–50
spell profiles, tails logs, and chooses healing, buff, ability and damage
actions. `rotation_engine.py` gates XWayland/uinput commands on game focus and
uses F6 to prepare, F8 to toggle combat, F9 to stop and F10 to heal.
`eql_rotation.py` supplies a PySide6 GUI. The tool has no pathing, camps,
vendor, looting, death recovery or unattended login. Its `server="freeport"`
setting names a log file and is not evidence of a private server.

| Prior file | SHA-256 |
| --- | --- |
| `HANDOFF.md` | `af18a1d72b5414564a76803fce73b13dc8c70efe2bf560cfe26815bc17bfd5fa` |
| `README.md` | `9fd2f3c8741e16ddf9087f146d62a7789417316ab57fe9afafc0b89b276135aa` |
| `CODEX_PROMPT.txt` | `26e274960b2483f71211822dfba1a5eb67901ac542604f8c4ecaee32e0f0f244` |
| `remote-runtime-check.json` | `347b4b481aa3451c105a9b5417346c87f0751463bab7fa8c0b3dcf7752206249` |
| `eql_rotation.py` | `95b4251558ecd1a5c31d9e12f2d71c2a0492de1e3df52592745fa7e8fc517adc` |
| `rotation_core.py` | `bdd5203bbf87563039799f7dd228480a517fca8dd4550d53b6559506a56875fa` |
| `rotation_engine.py` | `8e32a72eb7f87dae9901f84841679fdb628c46fab7458de216bfdff9fe567683` |
| `test_rotation.py` | `cfb79d8e661ad67d55623ba6888a604708197289b2a8e723a7debeffded72c99` |

The devbox mirror has no `artifacts/` evidence. `HANDOFF.md` reports 17 tests
passed on Alienware historically, but live spell preparation and combat were
never verified; the tests were not rerun in this first-step review.
`install_launchers.py` writes character INIs and must not be run against the
protected Alienware prefix. Missing pieces for the level 50 proof are a
Daybreak-authorized test path, a fresh test character, and an end-to-end run.
Devbox/Banshee server searches were skipped because the installed client points
to an official service and unauthorized EQL servers are prohibited.

## Superseded handover notes

Written 2026-11-13 ~12:40 AM CST by the Claude lead (claude-everquest-legends, Fable 5.2) at handover
to the Codex lead (coordinator task 28e5398a1701). The Claude lead ran for only a few minutes; the
FIRST STEP search is **incomplete**. Labels: VERIFIED = ran it and saw it, INFERRED = guess from evidence.

## Bottom line

- **Client install: NOT FOUND on the devbox so far** (partial search only, see "Not searched").
- **Server: NOT FOUND on the devbox so far.** No EverQuest-compatible server stack seen in running
  docker containers or in top-level `~/dev` directory names.
- **One real lead, unread:** `~/Projects/everquest-legends-rotation/` (an earlier EverQuest Legends
  rotation tool, Oct 17 2026). Its `HANDOFF.md` / `README.md` very likely say where the client runs
  and what it connects to. **Read this first.**
- No hashes recorded: no client or server binary was located to hash.
- Nothing was built, launched, logged in or changed. No game service was contacted.

## What was run and seen (all VERIFIED unless marked)

1. `~/Projects/everquest-legends-rotation/` exists, 332K, files dated Oct 17 2026, no `.git` dir:
   `CODEX_PROMPT.txt`, `HANDOFF.md` (8413 B), `README.md` (4086 B), `eql_rotation.py` (26700 B),
   `rotation_core.py`, `rotation_engine.py`, `test_rotation.py`, `install_launchers.py`, `launch.sh`,
   `eql-solo-assist.desktop`, `remote-runtime-check.json`, `.gitignore`.
   **Contents were not read** (stopped by handover before opening them).
   INFERRED from file names only: `remote-runtime-check.json` and the `.desktop` launcher suggest
   the game client may run on another machine (e.g. the Alienware) rather than this devbox.
2. Name search with `find -maxdepth 7` over `~/Games ~/Steam ~/.local/share/Steam ~/.wine
   ~/Applications ~/.local/share/lutris ~/.var ~/.local/share` for
   `*everquest*  eqgame*  eqlog*  eqhost*  eqclient.ini  spells_us*  *legends*  *daybreak*  LaunchPad*`
   returned exactly one hit: `~/.local/share/devbox-failover/claude-everquest-legends.json`
   (devbox failover metadata for this lane, not game data; not opened).
   Caveats: ran under `timeout 90` with errors hidden, and I did not capture the exit code, so I
   cannot rule out that it was cut off; depth was limited to 7.
3. Steam: no output from `~/.local/share/Steam/steamapps/libraryfolders.vdf`, and no `*.acf` app
   manifests in `~/.local/share/Steam/steamapps/` or `~/Steam/steamapps/` (no installed Steam apps seen).
4. `~/Games/` holds `banshee-library/` (empty) and `dreadnought-server/`. `~/Applications/` holds only
   `BansheeRealm.AppImage` (+ one `.before-0.9.176` backup). `~/Projects/` holds
   `everquest-legends-rotation/` and `xenogears-decomp/`.
5. `~/dev/*` top-level names matching `eq|everquest|quarm|legend|akka|norrath`: only this project
   (`everquest-legends-automation`). No EQEmu / Project Quarm / Akka-named directory at that level.
6. `~/gbsw/` contains only small Python scripts (`chk.py cst.py last.py lm.py send.py st.py sw*.py
   swc0745.py dummy.txt`), no server stack.
7. `docker ps` showed 4 containers, none EverQuest-related: `vana-navw2-28313`, `vanilla-smoke-db-1`,
   `enb-rust-mvas-20261103-server`, `enb-rust-mvas-20261103-db`.
8. Disks: `/` 489G (23G used), `/data` 30T (9.6T used). `locate` is not installed (exit 127), so
   there is no file index to query.
9. Box at the time: 48 CPUs, 187 GiB RAM, ~98 GiB available.

## Not searched / not done (still open)

- `/data` (30T volume) — not searched at all. Most likely place for a large client install if one
  is on this box.
- `~/dev` below the top level, and `~/.wine` / other Wine or Proton prefixes beyond a depth-7 name match.
- Stopped docker containers (`docker ps -a`), systemd services, listening ports.
- Banshee (`banshee-ax41`) — not contacted.
- The Alienware — not contacted.
- Whether "EverQuest Legends" is a live commercial/public service — **unknown**. If it is, the
  no-botting / ToS question in AGENTS.md CONSTRAINTS must be answered and reported to the coordinator
  before any automation touches it.
- The FIRST STEP report to the coordinator was not sent as a findings report; only this handover
  note was sent.

## What I was about to do next

1. Read `~/Projects/everquest-legends-rotation/HANDOFF.md`, `README.md`, `CODEX_PROMPT.txt` and
   `remote-runtime-check.json` to learn where the client lives, how the earlier tool read game state
   and sent input, and which service it logs into.
2. Search `/data` and deeper `~/dev` for `eqgame.exe`, `eqclient.ini`, `spells_us.txt`, `eqhost.txt`,
   `Logs/eqlog_*`, `maps/*.txt`, `*.s3d`, `*.eqg`; hash whatever is found (sha256) and record paths here.
3. Check `docker ps -a`, listening ports and Banshee for an EverQuest-compatible server.
4. Send the coordinator one clear note naming the exact missing piece (client and/or server) and the
   live-service/ToS answer.
5. In parallel, start the parts that need no client: nav-graph tooling for EQ map files, spell/class
   data model from `spells_us.txt`, log-tail state reader, and a bot core with a simulated harness.

## Coordinator channel note

The coordinator did not appear in `ListAgents` (8 peer sessions listed, none of them the coordinator),
though tmux session `claude-devbox-coordinator` exists. The CLI
`python3 ~/.local/share/devbox-coordinator/coordinator.py report --task <id> --status <s> --summary "..."`
is present and accepts `report`.

## Addendum 2026-11-13 12:40 AM CST (coordinator, from Blizz 12:33 AM CST and a read-only check on the Alienware)

- Blizz: "i have a game and client onmy laptop alienware if it neesd it under lutris". Stop searching the devbox.
- **Client install: Alienware (Bazzite, Tailscale 100.111.220.11)**, Lutris config
  `/home/blizz/.local/share/lutris/games/everquest-legends-1782570403.yml`; Wine prefix and game dir
  `/home/blizz/Games/everquest-legends` (13G); launched via umu-run; exe `drive_c/users/blizz/Desktop/EverQuest Legends.lnk`;
  prelaunch script `fix-eq-music.sh`. (VERIFIED read-only by the coordinator.)
- Read-only for you: do not modify or delete the install or prefix; copy anything to analyse to the devbox; do not touch his character progress.
- Server: **still to find and record** (official vs private/EQEmu).
- Earlier devbox tool to read first: `~/Projects/everquest-legends-rotation/` (Oct 17 2026).
