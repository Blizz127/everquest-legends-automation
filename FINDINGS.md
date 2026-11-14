# FINDINGS

## 2026-11-14 21:25 UTC — source 0.42.65: distinct thin-contact envelope diagnostics

VERIFIED `tools/source_contact_envelope.py` checks an explicit pinned thin-sheet
hypothesis without changing ordinary terrain/static checks. It retains the full
terrain support and placement/model/transform/raw-face provenance, enforces the
128-face limit before separating hypothesized contacts, and independently checks
static query membership against its complete source list. Contact faces must
be flat, nondegenerate and strictly above the entire flat reference terrain by
at most the declared 0.125 units. No material is rewritten or globally exempted.
Every other face keeps the original lower/numeric margins and an enlarged body
height; complete BSP/native volumes include the added rise. The original static
refusal remains in the result. Terrain query completeness is supplied by the
caller's pinned source view, not independently established by this helper.

This result is deliberately **not** a step/route permit: contact semantics,
transition kinematics, input and real-client acceptance all remain false. The
model proves only that other geometry clears a bounded envelope **if** the exact
sheets can be foot contact or noncolliding. It does not prove entry/exit motion.
No fake riser, nearest-height choice or ordinary floor adoption was introduced.
`audit_contact_walks` keeps its caller's floor unchanged and returns no future
floor object. It rejects step hints, discontinuities and an endpoint different
from the exact destination; the normal guide's optional final connector cannot
be silently omitted.

VERIFIED **12 focused checks pass** in 1.98s. They cover retained contact
hypotheses, height bounds, walls/ceilings, incomplete source queries, changed
placement, total source budget before partition, invalid geometry/seals,
BSP/native hazards, original-floor preservation and exact walk-only endpoints.
Private JUnit `releases/eql-0.42.65-contact-final.xml`, SHA
`68c7f9efc3663515f0da3749e4f81c3509bc53b8b5ae4015a466892b0fa35fea`.

The initial exit-only copied-data diagnostic found two conditional envelopes:
(103.96875,100.96875) → (115.84375,134.01041666666666) → (106,154).
All other terrain/static and BSP/native checks pass under the explicit contact
hypothesis for the four retained rug faces. Artifact
`nav-candidates/crushbone-throne-contact-exit-0.42.65.json`, SHA
`978d64a0a5be740109af19069264ac6e094beac7c560d641b48c71525c9e6e84`,
11.56s wall / 2.94s CPU. It uses a labelled synthetic diagnostic landing/exit
prefix and does not replay the entire approach or flight. The exact endpoint
was independently checked; the extracted helper now requires that equality.

The full composed devbox replay is **incomplete**. It finished the approach,
then exhausted its 180-second wall budget during the staircase: 183.21s total /
10.51s CPU. Artifact `nav-candidates/crushbone-throne-composed-contact-0.42.65.json`,
SHA `4c9947b06b40a4b84ac5c78f1ca17d7e1284e18326d33c948eb961e61de83e23`.
Its terminal handle is closed; it is not a route or full-envelope success.
Read-only Alienware availability: load 3.78 over 24 CPUs, approximately 13.4GiB
available memory, required copied data present. A single bounded low-priority
offline replay is planned there after this private source build is staged;
no lead game input, login or character mutation is involved.

Next runtime slice: distinct stair operation/boundary/controller in the existing
receipt sender and stopped-pair loop. Preserve the ordinary floor until a fresh
final landing; retain all compatible XY tread/phase candidates when straddling
risers, and recheck each actual maximum-hold envelope rather than reusing the
nominal offline corridor. Live stair/contact movement is still unimplemented.
Owner preview/runtime stay 0.39.32/0.42.61. G0 is passed; no repeat. Current level,
XP, XP/hour, deaths and camp remain unknown; full 1–20/1–50 are not accepted.

## 2026-11-14 21:14 UTC — source tools 0.42.64 privately published

VERIFIED installed `~/.local/share/eql-automation/owner-tools/0.42.64/source`
on Alienware from `64e29a9a1688c8de40a22a337edc494a25d9e47e`. All **524** pinned
source/test files match the validated snapshot. The bundle retains all **45**
passing checks with verified JUnit hashes; imports and three auditor startups
pass remotely. Source archive SHA
`33c9f93eb7264be9a546f04c6726a884e0f57ed7a19bb1d38844d40168c632cc`;
startup receipt SHA
`399843f13149ab4cca8383dba70e1ef043a843f820f16a376c4e8455f79a17b3`.
Private receipt: `releases/eql-source-tools-0.42.64-staging.json`.
Owner launcher/runtime remain **0.39.32 / 0.42.61**; its launcher hash is
unchanged. No helper restart, game input, install or character change.

An exact rational point-in-triangle check independently confirms the marker
and old rejoin are strictly inside rug 5782 faces 1 and 0 respectively.
Private artifact `nav-candidates/crushbone-throne-rug-markers-0.42.64.json`,
SHA `f47fe5408ff9881235c16e43275e40934527329746f6d5a13d2947b8ce6276e3`.
This proves copied geometry containment, not the client's collision filter.
The lower bypass is refused, no Throne guide was published, and the live stair
executor remains unfinished. G0 passed; no repeat. Full 1–20/1–50 not accepted.

## 2026-11-14 21:13 UTC — source 0.42.64: selected-floor budget and Throne exit diagnosis

VERIFIED the 32-patch limit now applies to the connected supporting floor,
instead of counting unrelated eligible floors overhead. All source faces still
participate in edge ownership and occupancy. Three-owner edges remain ambiguous;
the selected-floor limit stays 32 and the complete source limit stays 128.
No height filtering, material exemption or collision clearance was introduced.

VERIFIED **45 focused checks pass**: 19 floor-chain checks and 26 detour,
occupancy and static-floor checks. New regressions retain 40 overhead layers,
still reject a wall/low ceiling/ambiguous edge, and reject over-budget connected
floors and complete inventories. Private JUnit hashes:
`3218665407b2da427b3db24bed0100d237d53387a9b253f7227e5f564e36aa79`
and `252eb0714e70f9188e8a9a32f5fc5b274eea997519baa3691f2e3f1a523f049f`.

VERIFIED copied-data gap diagnosis: the original crossing after package
(103.96875,100.96875) hits static fragment 5781, face 1, actor `OGGRUG_ACTORDEF`.
Its surface is 0.09459114074707031 above the selected terrain Z16. The exact
source face is flag 0 / `TransparentMasked`; neither its name nor material
establishes pass-through. Gap artifact `nav-candidates/crushbone-throne-exit-gap-0.42.64.json`
SHA `a4aaa82a93e9bf5454a3f3bb2edf87620b5125e4d7dee57792110233afa2261a`.
The map target (106,154) and old rejoin (115.84375,134.01041666666666)
lie inside the second rug's faces. The original detour cannot reach those
endpoints under the retained static-obstacle model, irrespective of its budget.

A proposed lower bypass toward a nearby stopping-point hypothesis (90,154)
was checked using complete terrain/static queries. Retreat to
(99.63541666666667,86.30208333333333) passes; the next sweep to (100,76)
is refused for uncovered supporting floor. Remaining waypoints were not run.
Artifact `nav-candidates/crushbone-throne-exit-bypass-0.42.64.json`, SHA
`622ffde4f9b8ffdc48d6d6271d931d2c516de3e3bc365ac3eeb03310ce114eb2`,
38.70 seconds wall / 3.00 CPU. This diagnostic replays an explicitly synthetic
landing/exit prefix; it does **not** replay the full approach/flight or check
BSP regions. It is not an executable route or camp-suitability proof.
`tools/audit_crushbone_throne_gap.py` preserves the inventory, obstruction and
ordered waypoint results privately. Its command-line startup passes.

OBSERVED REA session inspection initially timed out during its apktool version
probe; one read-only retry completed with no target open, no retained evidence
and no pending cleanup. Native analysis is unavailable: Ghidra's required full
JDK21 is missing; other providers are unavailable/unconfigured. No configuration,
access or client change was made. Retained actor-down-query evidence does not
connect rug/material flags to collision filtering. Rug pass-through and static
support behavior remain unknown; no such behavior was inferred or enabled.

Next: reconcile explicit placed-surface support or find a completely checked
alternate approach/nearby endpoint; finish the separate stair executor. Owner
preview/runtime remain 0.39.32/0.42.61. Read-only Alienware trace remains 17,821
bytes, modified 2026-11-14 19:31:12.111509 UTC. No new real-client travel/camp
acceptance. G0 is passed and must not repeat. Current level, XP, XP/hour, deaths
and camp remain unknown; full 1–20 and fresh hands-off 1–50 remain unfinished.

## 2026-11-14 21:05 UTC — source tools 0.42.63 privately published

VERIFIED installed `~/.local/share/eql-automation/owner-tools/0.42.63/source`
on Alienware from `f02fa000fdc3bf6600ec07bf7470f21c70b536b0`. All **523** pinned source/test files
match the locally validated snapshot; the bundle includes the **21 passing**
focused tests with verified JUnit hashes. Imports and all three auditor
command-line startup checks pass remotely. Owner preview/runtime remain
**0.39.32 / 0.42.61**; its launcher hash is unchanged. No owner helper was
restarted and no game input was sent.

Bundle SHA `8b4f97325267e87a83f7aec2824058c3ce431401b60d95e660d0528d44c21743`;
startup receipt SHA `baf2e1964600dac85821443aab7935542040d97a52bc2a89d73eceee3798473e`.
Receipt: private `releases/eql-source-tools-0.42.63-staging.json`.
This release contains offline stair-flight planning tools, not a live stair
executor or complete Throne guide. The later exit crossing remains the next
geometry issue. Full 1–20 and fresh hands-off 1–50 remain unfinished.

## 2026-11-14 21:03 UTC — source 0.42.63: checked stair flight and composed route boundary

VERIFIED the copied Crushbone flight now passes **33 complete body/region
phases** across the 16 retained treads and 15 one-unit rises. The new
`tools/source_stair_flight.py` keeps flat parallel risers in exact order and
constructs distinct grounded lift, bounded transfer, raise/lower and grounded
settle phases. Every intermediate tread/riser remains collision geometry.
Only the two full outer floor caps get ground-contact treatment. Local lift is
bounded against the lowest actual support beneath the entire phase footprint;
horizontal transfers are limited to four units. The individual rise, radius
1.2 and body-height-6 hypotheses remain explicit. This is a conditional motion
model, **not evidence that the client follows its vertical phases**.

The exact footprint encloses the old float-expanded endpoint caps. The caller
reselects all-height terrain/static geometry using outward bounds for that exact
corridor. The initial run `f5a2c17167e2faf25887c2cb4bf98021496bce2b6a2081d6b2ee3bef2e191fa5`
used the earlier topology inventory and is **superseded**, not final completeness
evidence. Corrected artifact `nav-candidates/crushbone-throne-stair-flight-0.42.63-enclosed.json`,
SHA `a1cae104121d732cc2fff603287c97e0cc9e53933c52815ddacb9aed8ab6f23c`,
passes all 33 phases in 16.10 seconds. BSP results are retained; only the existing
explicit native-zero policy handles missing children. Nonzero metadata/hazards
remain refused. No input authority or ordinary floor adoption is claimed.

`tools/source_stair_plan.py` now ties the flight to the original checked floor.
It rechecks the full departure cap, independently queries every complete phase,
checks the final cap against the flight's exact identities (including changed
same-ID geometry), and snapshots static sources when available. Only the final
**planning clone** links to the parent proof. The original prefix stays unchanged;
there is no intermediate reseed or live floor commit. The plan has a canonical
byte seal and is a separate type that the owner executor cannot consume yet.

VERIFIED composed approach + flight in
`nav-candidates/crushbone-throne-composed-flight-0.42.63-repair.json`, SHA
`acfc5d9699dafaafc0e986a653225eab746599a6a951254fd267dc5d8df933d1`.
The approach has 16 fully checked cells. The stair plan has all 33 independent
phase queries and reaches the planned floor at Z16. The exit search reaches
(103.96875,100.96875), then refuses. An explicit walk-only repair toward the
retained hint (115.84375,134.01041666666666) exhausted the reachable grid in its
bounded box: **13 states / 102 edges**, with terrain, static and query-budget
refusals. Result: `no_source_detour_in_search_box`, not physical disconnection.
Total 140.40s wall / 19.16s CPU on a heavily loaded devbox (316 runnable processes,
0% idle in the sampled interval). No repeated heavy bake or Alienware load.
The earlier composed artifact `b7cb1dc297815213e0ce20c49a5b1abc173807f9550e50b3ae8ce7185f6c59cd`
preceded the final landing identity guard and is superseded by this run.

The walk helper's optional explicit repair range cannot contain a step, and
its detour always requires the final complete itinerary rebuild. Default
shortcut behavior is unchanged. No Throne guide was added, and the composed
route's overall `source_candidate` remains false.

VERIFIED **21 focused checks pass**:

| Check | Result / private JUnit SHA-256 |
| --- | --- |
| `test_source_stair_flight.py` | 8 passed in 1.64s; `cc9a0501f296d16003a291c53a8b829d2a8d0c490fa4252926fd47c83c14aec4` |
| `test_source_stair_plan.py` | 5 passed in 4.16s; `e0aa3e34a4ee2cca00382951e8467f8d1416c2bc312b737e96a58ba5104a6278` |
| `test_source_walk_shortcuts.py` | 8 passed in 1.65s; `e439fe69497d11aa0e1077a77f963522d6aaaab133edf152d81bb515179a420c` |

Coverage includes ascent/descent, whole-body ceiling/static/BSP/native failures,
missing support/riser, bounded lift/transfer, exact corridor enclosure, upstairs
prefix refusal, missing inventory, changed final geometry, unchanged original
floor and sealed result. The new composed auditor command-line startup passes.

OBSERVED read-only owner trace remains 17,821 bytes, last modified
2026-11-14 19:31:12.111509 UTC. There is no new route/level acceptance. G0 remains
passed and must not repeat. Real level, XP, XP/hour, deaths and camp are unknown.
Existing assist preview remains **0.39.32 / runtime source 0.42.61**. No helper
restart, game input, character mutation or install/prefix write occurred.

Next: inspect the exact terrain/static obstruction at the exit crossing, then
finish the composed route. For execution, add an explicit stair-flight hint,
boundary, support reader and provisional controller; never relabel it as a
walk/single step. Rebuild the actual measured movement envelope, keep ordinary
floor state frozen until a fresh full outer cap, and preserve receipts, original
deadlines, F8/F9, input/focus/hazard stops and assist's manual movement. The
hypothetical vertical phases require owner-run observation, not an acceptance
inference from successful arrival. Full 1–20 and fresh 1–50 remain unfinished.

## 2026-11-14 20:50 UTC — source tools 0.42.62 privately published

VERIFIED installed `~/.local/share/eql-automation/owner-tools/0.42.62/source`
on Alienware from local revision `9e8b57e10479c5f68c8222161ed2ce0ae7520e62`.
All 518 pinned Python source/test files match the validated local snapshot.
The bundle includes the 30 passing focused checks and their hash-verified JUnit
records. Imports and both auditor command-line startup checks pass remotely.
This is an offline tooling release; owner preview/runtime remain **0.39.32 /
0.42.61**, and its launcher hash is unchanged. No helper restart or game input.

Bundle SHA `ee878910ea73d95f5ec76257eef5ce9ef5a36bac923881a51c60f1c938fa5008`;
startup receipt SHA `ac265a722022644589cdf3f9ed1deb9948d63d3a52962bfee60402bb74dda945`.
Local receipt: `releases/eql-source-tools-0.42.62-staging.json` in the private store.
No Throne guide or staircase body-clearance acceptance was published. Next work
is the explicit stair-flight body/region model. G0 remains passed, full 1–20 and
fresh 1–50 remain unfinished, and current real run metrics are unknown.

## 2026-11-14 20:48 UTC — source 0.42.62: underlay repair and explicit staircase gate

VERIFIED offline development, **not real-client acceptance**. Owner preview stays
0.39.32 (runtime source 0.42.61), with the existing rotation. G0 passed by trace
and owner visible-stop confirmation; do not repeat it. Current real level, XP,
XP/hour, deaths and camp remain unknown. No full 1–20 or fresh 1–50 run.

The North Wall→Throne search now retains lower floors under platforms while
proposing their actual steps. `discover_step_links(include_internal_edges=True)`
adds two-owner edge proposals; its default is unchanged. Opposite interiors,
height/width bounds and the complete source-riser/body checker still apply.
A missing riser stays refused. No source geometry is removed from collision checks.

`tools/source_covered_floors.py` checks only proposed lower faces, then retries
the graph. Exact clipped upper patches must partition the entire lower triangle,
with no holes or positive-area overlaps and strictly bounded height gaps at every
patch vertex. This handles opposite triangle diagonals without nearest-Z selection.
Only proven lower-face graph edges are excluded. Other goal layers remain in the
source graph. Pair/patch/round exhaustion never becomes a geometry exclusion.

`tools/source_walk_shortcuts.py` preserves the supplied floor lineage and every
explicit step, and tests proposed walking shortcuts against complete local
terrain/static geometry. The final itinerary still needs the independent full
BSP/native-region rebuild. Walking repairs first passed two earlier route faults:

| Private artifact under `nav-candidates/` | Result / SHA-256 |
| --- | --- |
| `crushbone-throne-transit-0.42.62-rejoin18.json` | First corner repaired; advanced to a static-object fault. `1ddc66dc2e48c6a2a354f8982600d3344efa16a10f7b37167bdabde9534c6469` |
| `crushbone-throne-transit-0.42.62-rejoin31.json` | Static-object zigzag repaired; advanced to raised-platform body collision. `14a327d0e7a229f29396086ee6fd37ac4a5457a5c5263c4bf7e5362edc940695` |
| `crushbone-throne-transit-0.42.62-covered-floors.json` | Identical-triangle filter alone still refused walk 24. `e800927f0b5b703b312858f50d8304a67a847a21421cabd359abf812757296af` |
| `crushbone-throne-transit-0.42.62-covered-unions.json` | Exact upper-patch coverage advances through three checked steps, then refuses operation 64: `landing_selected_floor_uncovered_ground_area`. 32.79s wall / 9.81s CPU. `4f76fd213222cd174aed48e668c9756de2834be2958d8ab37fefccb1aca4339b` |
| `crushbone-throne-stair-topology-0.42.62.json` | Exact projected support plus 15 complete risers across 16 retained treads; topology only. 195 source faces, 5.05s wall. `74e8839773311b88f82e358949dfbaca508efb5dfa549c3d69b1416f86183f00` |

The last audit uses `tools/audit_crushbone_throne_stairs.py` and
`tools/source_stair_topology.py`. It reconstructs the explicitly selected sequence
of source components from the pinned proposal, includes all-height nearby source
faces, and checks the complete projected tread partition, flat monotone heights,
both outer supports and each actual bounded riser. All 15 rises are exactly one
unit; interior tread depths are 2 units except one at 1.96875. The existing
radius-1.2 single-step checker requires a complete approximately 2.4-unit cap on
one level, so those intermediate caps cannot fit. **Do not shrink the body or
weaken the step checker to make this pass.** The topology result explicitly has
no body/static/BSP validation, no executable itinerary and no adopted floor lineage.

Earlier fixed-center exclusions and bounded walking detours did not complete a
route. They are search outcomes, not proof of physical disconnection. The former
Trainer closure also applied to the older boundary-edge discovery model only;
it does not establish closure under this new opt-in internal-edge proposal model.

VERIFIED focused tests (30 total across the affected helpers):

| Check | Result / private JUnit SHA-256 |
| --- | --- |
| `test_source_step_links.py` | 9 passed; `c033a43d71dd0cfcaa52ac7b5b339e9a90fa26f472726c955fb59c69c3bf7a33` |
| `test_source_walk_shortcuts.py` | 6 passed; `ae8c5071cc541ffc32651cf7994c5cba1b1bc98e92e6b6e63514cffa8bcde428` |
| `test_source_underlay_transit.py` | 11 passed in 1.38s; `15281a0720cccc2708e0b03ab3c095bf9d0620d73f57851130d5a408042c55f4` |
| `test_source_stair_topology.py` | 4 passed in 0.38s; `d3dfbaf0a2a5e3a3009b57f00249289c514cc1e71130d74c24cfb2216e503bc6` |

Both audit command-line help/startup checks pass. No game input, owner helper
restart, install/prefix edit or character mutation occurred. All client geometry
and artifacts stay in the private data store. No Throne guide was packaged.

Next implementation: a distinct staircase flight model between full outer caps,
with exact bounded per-riser body phases, all-source/static occupancy and
BSP/native-region checks. Intermediate treads must not masquerade as ordinary
full floor caps. Only a complete checked flight may link the final planning
floor to the original prefix; actual movement remains an owner-run acceptance.

## 2026-11-14 20:21 UTC — source 0.42.61 / preview 0.39.32 privately published

VERIFIED installed outside the game prefix on Alienware:
`~/.local/share/eql-automation/owner-assist/0.39.32/launch.sh` and
`~/.local/share/eql-automation/owner-tools/0.42.61/source`, source revision
`7b463160dcae0ba4f0d9de30df8e9077f95372a7`. The bundle contains the exact 19-check local
validation snapshot and JUnit evidence; its runtime and test hashes match.
All 198 preview runtime modules match source, and the preview manifest passes.
Installed spell/posture pins, both packaged guides and owner NPC history load.
Offscreen GUI startup passes with continuation unchecked, no worker, device,
game input or settings write. The obsolete measurement flag is refused.
No owner helper was restarted and no character was controlled.

Bundle SHA `1429c0ecf4239fd8f292f633df7c774a5a139b550e8a119ba09341c634e408d2`;
startup receipt SHA `325b0c373baec104ab58431b7575cee1efc11fab4ba47e8eecd269ef8faa11fb`.
Local receipt: `releases/eql-owner-journey-0.39.32-staging.json`.

Owner command:
`EQL_ROTATION_TRACE="$HOME/eql-journey-trace.jsonl" ~/.local/share/eql-automation/owner-assist/0.39.32/launch.sh`.
F8 assist / F9 stop / F11 stationary camp remain. Use the separate location-hotbutton
test, focus the game and release controls; G0 already passed and must not repeat.
No Throne destination was added. Actual route acceptance, full 1–20 and fresh
hands-off 1–50 remain open; current real level/XP/hour/deaths/camp unknown.

## 2026-11-14 20:21 UTC — hotbutton input settling and bounded Throne investigation

Source **0.42.61**, owner preview **0.39.32 candidate1** built locally. The
location-hotbutton setup now waits for a later fully clear input scan when a
focus click/release, held key or touch contact remains in the sampled input.
The original eight-second setup deadline is fixed; it is checked after sampling
and also caps sender admission. Coverage, unsupported motion devices and clock
failures still refuse immediately with distinct explanations. Send/reply checks
remain strict. Saved evidence retains aggregate first-wait/last observations,
not key identities. F8 waits for cleanup before assist, and F9 defeats that switch.

VERIFIED **19 focused checks passed in 4.21 seconds**, 42 unrelated cases
not selected. JUnit `releases/eql-0.42.61-hotbutton-final.xml`, SHA
`2c4403c73afce2700ec16fedae23ce922b557b2b83793d89306479d74ac9105b`.
These use the retained engine and real OS-pipe/watchdog writes with synthetic
input/game observations. Offscreen GUI startup and manifest pass; worker,
input, settings-write and continuation-checkbox flags are false. This is not
real-client acceptance. Publication is recorded separately after staging.

OBSERVED read-only owner trace: `owner-observations/journey-20261114T2020Z.jsonl`,
SHA `cfdc097c67bf84a582a266cf1c95d8defd594eb750ef264f4cab95c1d055e9ba`.
Its last modified time is 19:31:12 UTC. A 19:21 location-hotbutton attempt refused
before any game key and the helper later exited. No camp/route or level gain is
recorded. The old release-keys message conflated held input, drained activity,
coverage, unsupported devices and freshness. **The old trace does not establish
which of these caused that refusal**; the earlier shorthand that controls were
held was too specific. New diagnostics resolve that ambiguity on the next run.

VERIFIED copied-data audit `tools/audit_crushbone_throne_transit.py` can start
from an independently labeled synthetic North Wall floor. It does not replay
the Mines prefix or claim a current character position. The complete initial
radius-1.2/body-height-6 cap passes terrain, static, BSP and region checks.
A 16-step, 310-operation proposal retains all three Throne floor layers, but the
full itinerary checker rejects walk 8 for uncovered floor. First artifact
`nav-candidates/crushbone-throne-transit-0.42.61-first.json`, SHA
`5706d6741c33c812f1338e5c2fe840b5f864a5478b30d237e486b1789dbcd336`,
20.22s wall / 5.04s CPU. It has no accepted route or selected final Throne layer.

The tool can replace an explicitly chosen walk-only range by a bounded local
proposal. It fully checks and replays the prefix rather than reseeding the fault,
preserves every step, and requires the entire repaired itinerary to pass again.
Two walk 8–12 attempts expired; the second explored 58 states / 519 edges within
89.30s wall / 11.96s CPU. Artifact
`nav-candidates/crushbone-throne-transit-0.42.61-repair2.json`, SHA
`613dddf2e5da8fb07f5a6d1a41d0009ab45f9f41a6961064d6c2e67591ee6929`.
Timeout is not a geometry disconnection or permission to exclude a component.
CPU/wall process limits bound this single low-priority audit. No bake, game input,
owner-session restart, install change or new destination publication occurred.
Next route work: inspect the narrow rejected crossing and use a suitable bounded
proposal resolution; preserve all goal layers and full geometry checks.

G0 remains passed. Current real level, XP, XP/hour, deaths and camp are unknown.
Full 1–20 and fresh hands-off 1–50 remain unfinished.

## 2026-11-14 20:09 UTC — source0.42.60 / owner preview0.39.31 privately published

VERIFIED install on Alienware outside the protected game prefix:
`~/.local/share/eql-automation/owner-assist/0.39.31/launch.sh` and
`~/.local/share/eql-automation/owner-tools/0.42.60/source`, source revision
`8014bd29dc7c48d930db52fe3c348807b9742fb1`. Runtime/test bytes equal the successful
19-check candidate, and all 198 preview runtime modules equal source. Manifest,
installed spell/posture source hashes, both guide pins and retained NPC history
load successfully. Offscreen GUI startup passed; continuation is unchecked.
The measurement flag is refused. Worker/device/input/install-modification flags
are false. No running helper was restarted and no character was controlled.

Bundle SHA `d9973e229b7ed1cf14759e9f53d0331d0ede37d3991ad4cfc0695ec3858dca20`;
owner startup receipt SHA
`4ab91ab775b6386dddf6f229789afd1411f174eab5ecf3b2d0e4400fc3676d9a`.
Local receipt `releases/eql-owner-journey-0.39.31-staging.json` retains the exact
remote metadata. Owner command:
`EQL_ROTATION_TRACE="$HOME/eql-journey-trace.jsonl" ~/.local/share/eql-automation/owner-assist/0.39.31/launch.sh`.
F8 assist / F9 stop / F11 stationary camp remain. The optional continuation
requires the initial checkbox, a new observed level, fresh probes, a supported
next guide and fresh stopped arrival before new-camp preparation.

This is an owner test build, not accepted real-client travel or leveling. G0
already passed; do not repeat it. Full1–20 and fresh hands-off1–50 remain open.

## 2026-11-14 20:08 UTC — full next-camp continuation passes on Alienware

VERIFIED `owner-tools/0.42.60-validation-2`: **19 passed, 69 deselected in
75.07 seconds**. The production provider completed its seven real watchdog/pipe
probe pulses, sealed current fit, source route, stopped arrival and new camp
startup. The test checks a different camp object, fresh preparation due, old
floor retirement and the same still-open observer with a new valid floor. Game
and geometry observations are synthetic; no game client input or level gain
is established. Output SHA
`97a3d14da0844fa0effef58cee583771c967c092831d48d216ec2cf4afaacba6`;
JUnit SHA `fb859e67612f172386a4a8287e6d011c2d6b9cbb064c23102e2db5f587e45111`.
Archive SHA `6c2a81bae7440e5e81841ddbec75dcdcb1b2acbbe1f13c1c4478a411ba16f92a`.
The local receipt copies are under `releases/eql-0.42.60-validation-2-*`.

The previous message `Release watchdog did not confirm key down` did not
identify a timeout: it also covered the child's explicit `EXPIRED` response.
New `PulsePermitExpired` diagnostics retain selector-return, final-stop-check,
GO-send and reply timestamps. Initial remote candidate1 failed after 23 movement
receipts with selection slack **33.770ms**, final-check slack **-0.693ms**, GO
slack **-0.696ms** and child reply **0.380ms** later. This establishes parent
validation consumed the permit before GO in that run. It does not retrospectively
prove the reason for every older generic error. Candidate1 output SHA
`91229fdce4e8d1af38a2c4f4d447a96491ab86bfb2e71ece33de3c34e1de723c`.

Source sender selection now omits only its duplicate post-authorization full
sender check. The watchdog still invokes the complete final `should_stop`
under the same stop lock before GO, including fresh physical/log sampling,
focus, descriptors, command state and exact authorization. A cheap empty-held-key
check remains before the sender marks its selected key, so a callback cannot
hide an already-held matching key. The 50ms permit, all other deadlines and
independent UP cleanup are unchanged. Focused remote checks include
before/after-DOWN revocation, authorization callback mutation and expiration
without DOWN. Two diagnostic checks also passed locally in 0.64 seconds.

Alienware read-only reconciliation: the retained 0.42.56 candidate3 directory
contains only `source`, with no checks/result artifact; an exact `/proc` scan
found no matching runner/pytest. That old result is unavailable, not passed.
The new checks used a separate versioned directory and a runner that persists
completion/output even on timeout. No old process was restarted or interrupted.

New bounded source-boundary inventory tooling reads the pinned client terrain
without route search or baking. It preserves exact projected overlaps, opposing
floor heights and rejected intervals. Initial Trainer/approach scan: 88 examined
pairs, 19 overlapping pairs; four nonzero step intervals, one narrow interval,
15 over-height intervals. Neighbor scan includes components `(465,0)` and
`(512,35)` and finds eight nonzero intervals. Frontier `(448,2)` / `(516,4)`
connects to `(515,6)`; these are candidate connections inside a possible isolated
group, not a complete camp route. No zero-gap partial joins were found in these
scans, no static-floor support was promoted, and no movement bounds changed.
Artifacts under `nav-candidates/`: initial SHA
`2da89deeff4f00c85c2c6fd45a0c1297d04a6b537ed912c68ab27b5e7dc6f1d2`,
neighbor SHA `c584db2b46b8472c29284e3afbaa1cd7c05d21c6d6cc92707d280dab1700a60d`,
frontier SHA `f012ead2cbabfd0a9d2ad27033be2a636e831a04c817d9403eae62aca5e40ee1`.
The final frontier `(515,6)` has only edges back into the examined set.
A combined exact-predicate recheck establishes a closed seven-component island
under the current full-edge/2-unit-step discovery model; it does not prove
physical disconnection. Closure artifact SHA `62a9023c3a72d3f5eabd0d15f3398ffdd72f7b215f7650397f2afbb1edac6b90`.
Next Trainer work needs a supported alternative (such as verified step/jump
capability or static supporting geometry), not another identical graph search.
All use copied WLD SHA
`ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1`.

Preview0.39.31 candidate5 builds and starts locally with no worker/input/settings
write. Publication receipt follows separately. G0 remains passed. Current
character level, XP/hour, deaths and camp remain unknown. Full real-client
1–20 and fresh hands-off1–50 are still incomplete.

## 2026-11-14 19:58 UTC — stopped next-camp arrival enters fresh combat preparation

Source 0.42.59 adds an in-memory `CampArrival` transition after the optional
next-camp route completes. Capture requires the actual completed source runtime,
its exact stopped receipt, new floor checkpoint, unchanged destination and
sealed fit. The basis retains the original motion-bound assumption ID and
separately records the newly measured steering fit ID/hash; it never claims
current heading or independently verified bounds. No timestamp is renewed.

The old probe/reader lease is released before new-camp startup. A scoped
`replacing_camp` hook verifies the exact old camp/autopilot again after callbacks
and uses the existing one-generation stop transition. A new camp session starts
with spell preparation due, no retained target and new target/consider checks.
The same physical observer transfers to a new monitor/floor while the old
wrapper is retired without closing the device. Input observation time cannot
move backward. F8/F9 interruption wins during gauge reading, controlled stop and
input transfer; cleanup does not consume the deferred F8 request.

VERIFIED focused checks: **37 passed, seven deselected in 5.82 seconds**, JUnit
SHA `5b655a18fa0421b98675d47310fa914699b28a147cf5e6d53fc8bdac0edac98e`.
The new handoff tests use the actual retained engine and genuine source-floor
objects with a synthetic arrival token. They cover stale/changed arrivals,
physical input, reader ownership, generation/settings, callback replacement,
F8/F9 and fresh preparation. They are not route execution acceptance.

The separate complete production-provider/watchdog/pipe attempt **failed after
one movement receipt** with `Release watchdog did not confirm key down`, before
new-camp arrival. JUnit SHA
`ab709e58b26d3362920e3d1f20d0c9acf725630274849c1cd7571daa73feae2e`.
The devbox was heavily loaded (observed load average 167.62 on this turn's first
check); causation is not independently proven. No production deadline was
loosened and this is not counted as passed. The full test now asserts a new camp
and retained observer on successful completion; that end-to-end result remains
unresolved.

VERIFIED local owner candidate `owner-build-drafts/0.39.31-candidate4`: all 198
runtime Python modules equal source; manifest and offscreen GUI startup pass.
Build-info SHA `c3a209bbbb086cdb85c5ec2f715f75c9144ae4161579120e37e8dc8fccc86cb7`;
GUI metadata SHA `69e4c3ecf14800399fb89e7926a2e76bcb06139c634c6e3a05954a521cba8f84`.
Screenshot inspected: assist OFF, continuation unchecked, both packaged choices.
The displayed level 13 is a smoke argument, not observed character progress.
Worker/input/settings-write flags are false. No game client was controlled.

Alienware SSH port 22 timed out again; source0.42.55/preview0.39.30 remain the
last verified publications. The retained0.42.56 candidate3 result still could
not be read; no duplicate remote test was launched. Current character level,
XP/hour, deaths and camp remain unknown. G0 already passed and was not repeated.
Trainer/Throne route gaps and full real 1–20/1–50 acceptance remain unfinished.

## 2026-11-14 19:50 UTC — concrete continuation provider and local preview 0.39.31

Source 0.42.58 wires `owner_camp_probe_plan` into a new owner entrypoint and
preview builder. The GUI captures an initially unchecked continuation choice
with the travel request; queued mutation, non-boolean values and later intent
changes cannot enable it. Ordinary travel without that choice stays unchanged.
The provider requires a fresh camp-log level increase and retains the original
monitor/reader/recovery scope. It checks the canonical arrival basis against the
actual retained floor, copies only its declared bounds as historical hypotheses,
and changes the request cap to .15 seconds for the standard probes. The later
route returns to .10 seconds and takes steering from the exact fresh reducer
output, sealed before planning. Fit edits, changed transaction identities and
stale route-start pairs are refused; old confirmation timestamps are not renewed.

VERIFIED copied map/guide reads: level 7/10 stays at Slave Mines; 11/12 has no new
packaged hint; 13–17 selects North Wall; 18/20 has no new packaged hint. The North
Wall guide has 230 walk hints, 7 step hints and 1307.5937891227334 units of walk
length. INFERRED: the earlier five-minute total budget is too short at the
historically observed roughly 30-unit/second movement with repeated stopped
pairs and turns. Continuation now uses the existing destination travel maximum
of 1500 seconds, anchored once at camp probe start; its probe-measurement window
remains 120 seconds. Per-pulse DOWN/UP, actual-hold and stopped-pair limits are
unchanged. Source height correspondence remains subordinate to that original
absolute job deadline and each fresh location check.

A distinct `camp_continuation` declaration records
`owner_supervised_continuation=True` and `open_flat_clear=False`. It does not
reissue the first starting area's open-ground statement at a later camp.
Independent scene, dynamic clearance and motion bounds remain unverified.
The source policy keeps the exact original veto reader and input observer.

VERIFIED **17 passed in 16.28 seconds**, provider/fit/level scheduling checks,
JUnit SHA `8bb3e492c9a849cb3da06e47fae5173973b159aaa218df13531bfead42e988a3`. VERIFIED additional declaration
checks: **4 passed in 1.91 seconds**, JUnit SHA `e6bb1f2a115a5dc59fac8ab4b295b43294f4da3ffdf7b4f5680376cd21e4ccc9`.
These include genuine source transaction/floor objects with deterministic
synthetic observations and a small retained-engine position test. One separate
full real-watchdog/OS-pipe continuation attempt **failed before its first movement
receipt** with `Release watchdog did not confirm key down` under measured devbox
load above 200 on 48 CPUs. No completed movement receipt was recorded and
production deadlines were not loosened. That end-to-end check is unresolved; do not count the focused runs as a replacement or call it accepted.

VERIFIED local candidate `owner-build-drafts/0.39.31-candidate2`: all 197 runtime
modules match current source bytes; source manifest and offscreen Qt startup
pass. GUI smoke SHA `69e4c3ecf14800399fb89e7926a2e76bcb06139c634c6e3a05954a521cba8f84`. Checkbox is visible, enabled and
unchecked; worker_started/game_input_sent/settings_saved are all false. The
candidate1 screenshot was visually inspected; candidate2 retains the same UI.
The displayed level 13 is a smoke-test argument, **not** Legira's observed level.
A dedicated private devbox `python-ui` environment now supplies Qt for these
no-input startup checks. No client/prefix/character changes or input occurred.

Alienware SSH port 22 still timed out in this turn. Neither source 0.42.58 nor
preview 0.39.31 is published there; source 0.42.55/preview 0.39.30 remain the last
verified publications. Preserve and retrieve the old 0.42.56 candidate3 remote
result when the host returns; its process/result state is unknown. Next: new-camp
combat entry after onward arrival, plus Trainer/Throne coverage and later real
acceptance. G0 remains passed; no repeat requested. Full 1–20 and fresh hands-off
1–50 remain incomplete; actual current level/XP/hour/deaths/camp unknown.

## 2026-11-14 19:39 UTC — observed level-up reconsideration (source 0.42.57)

VERIFIED focused local checks: **15 passed in 5.21 seconds**, JUnit
`releases/eql-0.42.57-level-checks.xml`, SHA `b6f2036b45f53156a1bfc8b18043b7dade003efd757418ed3656dbbc788b0829`.
`StationaryCamp` now records a frozen `CampLevelAdvance` only for a strictly
increasing fresh client-log level event. Duplicate levels retain the same
marker; multiple increases before recovery coalesce to the latest. Reordered,
backward and delayed messages cannot replace it. Camp log sequence numbers
remain distinct from the location reader's sequence.

A Journey with an optional probe-plan provider may reconsider after the next
completed spell preparation/recovery when that exact new event matches its
camp, generation and current level. Successful no-plan collection consumes the
marker once; ordinary camps without a provider keep their first-check-only
behavior. Position collection pins the event identity and values, including
release callbacks. New tests cover repeated recovery, duplicate messages,
deferral for preparation, F8/F9 and changed marker/settings; the existing actual
preparation-after-ding case also passes.

Earlier low-priority local runs had one watchdog fail to confirm DOWN under
measured devbox load around 190 on 48 CPUs. The sender stopped and released the
pipe key. The final small serial batch passed at normal priority with unchanged
deadlines. This is synthetic game/scene evidence, not real-client acceptance.
No game input, device or character action occurred. Source 0.42.56 final remote
result remains unconfirmed after its 510-second SSH timeout; 0.42.56/0.42.57 are
not published on Alienware. Last verified published source is 0.42.55, owner
preview 0.39.30. Next is the concrete continuation plan/provider and new-camp
entry. Actual level/XP/hour/deaths/camp unknown; G0 remains passed.

## 2026-11-14 19:29 UTC — shared supervised camp-probe policy

`SupervisedCampProbeScope` and its per-transaction policy implement the existing
abstract probe admission interface. Explicit continuation supervision remains
an owner choice, not independent clearance or a verified speed bound. One
scope retains the exact physical observer/topology, stop generation, root
bounds and basis, original time limit and aggregate maximum-hold reservations.
Each pulse brackets the same log-veto reader with fresh input observations;
foreign/duplicate tickets or exhausted budgets are refused. DOWN authorization
expires after at most 50 ms, while observation continues through the full
0.15-second turn and unconditional sender UP cleanup.

The recovered-position owner scope now constructs the veto before collecting
its first pair. Both object and tail/path/clock/generation are pinned there,
then passed into the probe runtime. A source child must use that same veto;
it cannot rebaseline between calibration and travel. The new concrete policy
also checks the veto generation against the retained camp monitor binding.
The source launcher still supplies no continuation plan provider, so these
changes do not turn on a new owner movement mode.

VERIFIED initial candidate `0.42.56-validation-1`: 18 passed in 37.07 seconds,
output SHA `5e1e8bfacd84e768bfc3083c89089062b0786c67cc1d0ace61849cc0384b22e8`.
VERIFIED candidate 2: **21 passed in 132.90 seconds**, output SHA
`bfff871870008a43371fcf60095d0fd6f95242297bf9d96006ea95e866007cb5`.
That includes the standard seven probes, fresh fit and source arrival using the
concrete policy, plus a hazard after calibration preventing route movement.
A subsequent read-only review found that tail replacement before runtime
creation could otherwise establish a new baseline; early transport now pins
that state too. Final candidate 3 was launched for these latest changes and integration, but
its SSH transport timed out after 510 seconds without a result. A separate
read-only Alienware connection also timed out on port 22. Its remote process
state and final result are unknown; do not claim a pass or start a duplicate.
Local checks passed both early-veto replacement cases. The early-hazard case
first stopped before policy construction (no movement); after adding diagnostic
assertion text, it passed alone in 8.27 seconds. Current combined verification
and private publication remain pending Alienware availability. All input
uses OS pipes and actual watchdogs; scene/game observations are synthetic.
No game input, device, login, character action or prefix change occurred.

Next: carry an explicit continuation choice through SOURCE_JOB/Journey, build
the plan from retained source hypotheses and a level-appropriate pinned guide,
use the newly measured fit, then add a separately checked new-camp entry.
No new G0 or owner test is requested. Actual level, XP/hour, deaths and camp
remain unknown; the real 1–20 and fresh hands-off 1–50 goals remain incomplete.

## 2026-11-14 19:30 UTC — next provider and route coverage evidence

OBSERVED/read-only helper verification: the retained map
`owner-route-data/crushbone-camps-20261114/crushbone_3.txt` hashes to
`4b1c009838988b13507797afd1ccbce8ba23e1ca99adbafd1065956cfd71bda0`.
Its hints are Entrance 4–7, Slave Mines 7–10, Trainer Hill 10–13,
North Wall/Castle 13–17 and Throne Room 17–22. Only Slave Mines and North Wall
have packaged source guides. Trainer Hill (package XY 119,-212) and Throne Room
(106,154) remain buildable coverage work, not missing owner choices. Map Z
must not select a floor: Trainer approaches still have unconnected tall-wall
boundaries in the current graph and Throne has overlapping diffuse layers.

The retained recipe `tools/audit_crushbone_camp_transit.py` already accepts
`--destination trainer|throne --strategy graph|reverse --compact` and a new
output under `nav-candidates`. It replays parent
`crushbone-source-itinerary-0.42.28-final.json`, SHA
`09c4cf3d6e69245249f8df9ef66a8f1914c7fc5038bb3dd8b5b1c01dee98bb28`,
and fully rebuilds new proposed suffixes. No new bake was launched: VERIFIED
19:29 UTC devbox pressure was load 185.72 on 48 CPUs, with 134,688 MiB swap
used out of 139,263 MiB. Continue light provider/UI work while this pressure
persists; do not use the owner's laptop for a heavy replacement bake. Future
bakes should use an immutable source snapshot because the recipe pins code.

The concrete provider can preserve arrival bounds as explicit historical
planning hypotheses, change only its new record ID and request cap to .15s
for the standard probes, then return to .10s for source travel. Existing actual
hold bound is .20s, so seven probe reservations total 1.4s. Fresh reducer
speed/heading and uncertainty must fit the preserved envelope; old arrival
heading/speed cannot drive the new route. `navigation` supplies the fitter;
`eqnav.steer.Motion` supplies the onward steering model. The source policy
retains the original absolute camp deadline and shared veto/observer.

A level-aware provider also needs scheduling: `Journey.height_check_done`
currently suppresses later recovery collection. Reconsider on a new accepted
`camp.level_source == 'client_log'` event/sequence, not an edited configured
level or historical log. Absence of an appropriate packaged next guide keeps
stationary camping active; it is not permission to send level 7 to North Wall.
Preserve Butcherblock-first fresh-character work alongside this practical
Crushbone branch. No new route or actual level progression is accepted here.

## 2026-11-14 19:19 UTC — source 0.42.55 privately published

VERIFIED Alienware `owner-tools/0.42.55/source`, revision
`cc73151ea368ea02f0392f9c9af7854ae52aaab0`. Runtime/tests/tools byte-match the final
270-pass candidate. Imports, diagnostic CLI startup and copied-data pins pass.
Archive SHA `33f4d5ec3ee916dc5589a2b4ce44dc880fb0af7e9984ce36b261c08a43c8c35b`;
startup SHA `b93940a709f003296f75892a4db8e3d57983ad028e224934eaafcb82913f572a`.
Publication record: `releases/eql-automation-0.42.55-staging.json`.

The full standard seven-probe sequence now feeds its fresh fitted motion into
source travel and stopped arrival in the no-game harness. Shared ancestry and
value checks preserve cancellation and all original deadlines. No device was
created, worker/client started, game input sent, character changed or prefix
edited. Owner preview stays 0.39.30 and assist stays 0.39.13. G0 passed; no new
owner test is requested. Next: concrete shared supervised probe policy and
continuation provider, then new-camp entry. The real 1–20 and fresh hands-off
1–50 goals are not met; current level, XP/hour, deaths and camp remain unknown.

## 2026-11-14 19:19 UTC — standard seven-probe to source-route integration

VERIFIED candidate `0.42.55-validation-7` on Alienware: **1 passed in 70.15
seconds**, output SHA
`92db48c674b8b111c110fa2e5367ace5e29131a1df29c416e6ea1941eb7f11d7`.
The retained engine runs exactly the standard four forward / three turn
probes through the actual watchdog and an OS pipe. A synthetic game updates
from actual receipt intervals and supplies rounded log coordinates. The route
plan uses the resulting fitted speed, turn rate, latency, sign and final
heading, keeps all seven ancestors alive, collects new startup observations,
executes the source itinerary and captures stopped arrival. No game input.

Candidates 1/2 refused source DOWN at its original 50 ms deadline. Diagnostic
candidate 3 found 112 observer checks and 761 owner binding calls in one failed
source attempt. Shared ancestry validation now observes identical provider
scopes once, then checks every ancestor's fields and evidence; distinct scopes
keep recursive validation. In-memory scalar/tuple/type/identity snapshots
replace repeated JSON/deepcopy conversions without changing exported evidence.
Two immediately duplicated sender ledger checks were removed. The 0.5-second
position freshness and 50 ms DOWN deadlines are unchanged. Candidate 4 reached
later travel but still hit the timing limit. Candidate 5 exposed a mixed
snapshot comparison, corrected before candidate 6. Candidate 6 executed 33
source pulses and correctly stopped at the fixture's six-second reserved-hold
allowance; the fixture's reconnect/backtrack guide needed allowance for all
64 declared steps at the unchanged 0.18-second bound. Candidate 7 passes with
that explicit test-only allowance; production budgets were not raised.

VERIFIED **51 local focused checks passed in 75.26 seconds**. New regressions
cancel a middle ancestor or mutate its bounds, clock, receipt or raw reading
from the final shared clock callback; the leaf refuses without input. A
different binding context still takes the recursive path. VERIFIED final
Alienware candidate `0.42.55-validation-8`: **270 passed in 279.56 seconds**,
output SHA `d932716e6adde266b02e618f77642542fe10b6a62e3b9c490b504cc57986f92e`.
It covers standard probes/fit/travel, F8/F9 cleanup, source transfer and
ancestor/stale-observation regressions. Publication is recorded above. Owner preview
remains 0.39.30, G0 passed, and real 1–20/1–50 acceptance
and level/XP/hour/deaths/camp remain unknown.

Next implementation is a shared `SupervisedCampProbeScope` plus per-transaction
`CampProbeInputPolicy`. One retained input monitor and log veto must span all
seven probes and the onward route, with the original owner deadline and one
aggregate hold budget. Policies are constructed during `collect_start`, then
require fresh physical-input/log observations through holding and release;
DOWN expiry must not become a release deadline. The owner launcher still
supplies no `camp_probe_plan_provider`. Wire explicit continuation intent there,
then the fresh fit/source execution and a separately checked new-camp handoff.
This is an implementation plan, not installed owner behavior or a request for
another G0 test.

## 2026-11-14 19:01 UTC — source 0.42.54 privately published

VERIFIED Alienware `owner-tools/0.42.54/source`, revision
`6d817f664690a5b157dee94b45a8163100ee604f`. Runtime/tests/tools byte-match the
final 173-pass candidate. Imports, diagnostic CLI startup and copied-data pins
pass. Archive SHA
`6f093cf29d70eb7dfa974a91abadb4638fb74c672ad3ce56c737a47d9bc79189`;
startup SHA `e0acf6ae87cc42fd6b454a4b15d19164f972fafd42ee03c279d4b4359d50a690`.
Publication record: `releases/eql-automation-0.42.54-staging.json`.

The optional retained-engine camp route now completes startup, movement,
observed acknowledgment and captured arrival in the synthetic harness. F8/F9
cleanup is covered. No default launcher plan/policy is enabled; preview remains
0.39.30. Next is exact standard seven-probe→route integration, then concrete
owner launch wiring and new-camp entry. The launcher hook is
`tools/owner_nov12_entry_03926.py` calling `make_owner_journey_engine`, which
already accepts `camp_probe_plan_provider`; no such provider is supplied today.
No game input, input-device creation, login, character action or prefix edit.
G0 passed; no new owner test. Real level/XP/hour/deaths/camp unknown; no accepted
1–20 or fresh hands-off 1–50 run.

## 2026-11-14 19:00 UTC — source 0.42.54, retained camp route execution

Implemented an optional `CampProbePlan.route_plan_factory` returning explicit
`CampSourcePlan` bounds, current motion/heading and source-policy factory. The
retained engine keeps the original probe runtime alive, adopts its exact route,
collects genuinely new startup replies, and reuses a shared source walk/step
execution loop. Owner travel retains its original admission adapter. No fake
trial plan or default open-ground declaration is created for camp routing.

The child retains sender/descriptor, reader lease, monitor, stop lock and the
original deadline. Constructed components and child ownership are pinned.
F8/F9 cancel the child first; key UP and operation cleanup precede ancestor
release/F8 assist. Successful arrival captures its new floor and stops before
choosing another camp. Failed startup keeps its partial readings and input
receipts in diagnostics. The owner launcher remains 0.39.30.

VERIFIED initial local sample: one pass, two timing refusals under devbox load.
First Alienware candidate: 56 passed, five new-route timing refusals. Isolated
checks traced these to recursive historical-floor/input checks inside every
source binding callback. Optimizations retain full ancestry checks in the
source observer and actual physical sampling in both input senders, with a
final ancestry phase/continuation check after provider callbacks. Immutable
geometry bytes/digests and flat height-value snapshots avoid repeated parsing
and copying while retaining nested mutation detection. Source proposal time is
recorded after preflight when the ticket is created; post-callback state and
fresh scene checks remain. No position, scene, DOWN or release deadline widened.

VERIFIED final candidate `owner-tools/0.42.54-validation-14`: **173 passed in
197.83 seconds**, output SHA
`d4f251ee0749a77ba58a578c7c03c3fc60becddf56798ed18435e828ae20aee6`.
Covers retained camp startup/walk/arrival, F8/F9 during startup/movement/replies,
physical-input refusal, component/lease/deadline/policy changes, late ancestor
cancellation, nested height/envelope mutation, and existing source/step runtime
and camp behavior. Actual watchdog/OS-pipe writes; all game state, source geometry
and scene admission are synthetic. Private source publication pending.

NOT VERIFIED: exact standard seven-probe holds followed by source travel; the
new integrated route test uses one .02s forward probe and explicitly supplied
synthetic motion. The seven-probe tests elsewhere stop before source routing or
use synthetic receipts. This is the next focused integration check, followed
by a concrete owner launch-path provider and new-camp entry. No game input,
input-device creation, character action, login or protected-prefix change.
G0 remains passed; no repeat/new owner test. Current level, XP/hour, deaths and
camp unknown; no accepted real 1–20 or fresh hands-off 1–50 run.

## 2026-11-14 18:40 UTC — source 0.42.53 privately published

VERIFIED Alienware `owner-tools/0.42.53/source`, revision
`b193de1e5f54f7846d9f5a28ad072a77abc9896d`. Runtime/tests/tools match the
83-pass final observer/source-movement/walk/step-transfer candidate. Imports,
diagnostic CLI startup and copied-data pins pass. Archive SHA
`a7d5f224f447ae29edc4d09a5ded68d10ec038542ec476db900743bf9fc02018`;
startup SHA `b31779f6f00b04d47c02848006ada719448782f257d6b37bb11285f06815c31e`.
Publication record: `releases/eql-automation-0.42.53-staging.json`.

The existing movement ledger accepts the distinct fresh camp observer, with an
actual watchdog/OS-pipe roundtrip and subsequent arrival capture verified under
synthetic game feedback. The owner camp runtime still needs explicit observer,
driver and movement-policy wiring; no default path is enabled. Preview remains
0.39.30. No game input, input-device creation, character action or protected-prefix
change. Current independent scene/supported motion producers remain unfinished.
G0 passed, no new owner test. Actual level/XP/hour/deaths/camp unknown; no real
1–20 or fresh hands-off 1–50 acceptance.

## 2026-11-14 18:39 UTC — source 0.42.53, explicit camp observer and existing movement driver

Implemented `CampSourceObserver`, which consumes an exact `CampRouteStart`
once and uses a distinct `CampSourceHeight` correspondence from its newly
measured pair. It does not manufacture an initial travel plan or renew the old
travel calibration. The original reader/owner scope and stop lock remain
required, with explicit deadline and path-deviation tolerance. Construction
checks time after provider callbacks; an expired start cannot be adopted. New
startup replies must follow the measured pair's sequence baseline.

The existing source ledger now accepts this explicit second observer type via
shared floor/bounds/terrain properties. Its original lock is pinned throughout
stage/release/acknowledgment. The walk driver uses an explicit lateral tolerance.
Probe requests of .15s cannot silently enter the ordinary <=.1s route path:
callers supply tighter requested-hold bounds, with all body, speed, error and
actual-hold bounds unchanged. A dedicated height serializer supports subsequent
arrival checkpoint capture without recursive checkpoint objects or unencoded
datetimes. Step-transfer consumers retain the existing `SourceStoppedFix` type.

VERIFIED initial local 14 checks passed in 19.00 seconds. First Alienware
candidate: 82 passed, one wrong test exception expectation (`RouteHalt` is the
correct refusal). The actual watchdog/OS-pipe camp-observer movement/observed
acknowledgment passed. VERIFIED final candidate
`owner-tools/0.42.53-validation-2`: **83 checks passed in 13.62 seconds**, output
SHA `c07fa7ab5d669365f15e3960d0a5dbe0c01c57daa10fa62e94b75dd2e91ada65`.
The checks cover camp observer adoption/height/lock/hold bounds, delayed-provider
refusal, existing source movement/walk/step-transfer behavior, pipe execution
and next arrival capture. Private source publication pending.
All game positions, focus and scene admission are synthetic. No game input,
character action, protected-prefix changes or new owner controls. The owner
camp runtime still needs explicit driver/policy wiring; preview stays 0.39.30.
Current independent scene/supported motion producers remain missing for
unattended input. G0 passed, no new test. Actual level/XP/hour/deaths/camp unknown;
real 1–20 and fresh hands-off 1–50 remain unaccepted.

## 2026-11-14 18:33 UTC — source 0.42.52 privately published

VERIFIED Alienware `owner-tools/0.42.52/source`, revision
`968b4e9e0f51c01a6674a3f5180f6d511972d056`. Runtime/tests/tools match the
45-pass final source-planning/retained-handler/watchdog-pipe candidate. Imports,
diagnostic CLI startup and copied-data pins pass. Archive SHA
`845853fb72edb77ddfbd93f5aed179cda54dc25c579f44f28a8b60057865a529`;
startup SHA `2bbbf1246107d5a92defbd8b9e215565969043b7ade0413ec46e11ea0abb33f4`.
Publication record: `releases/eql-automation-0.42.52-staging.json`.

Optional onward planning now stays on the reached source floor, collects genuinely
new before/after-planning positions, and retains the original scope/deadline.
It finishes stopped before movement execution. The owner launcher has no default
probe plan/guide; preview remains 0.39.30. No game input, input-device creation,
character action or protected-prefix edit. New observer/driver adoption and
current movement admission remain unfinished. G0 passed; no repeat/new owner
test. Actual level, XP/hour, deaths and camp unknown; 1–20/1–50 remain unaccepted.

## 2026-11-14 18:32 UTC — source 0.42.52, onward source-route preparation

Implemented `CampRoutePreparation`: direct `plan_source_itinerary` reuse on a
private fork of the actual retained camp/probe floor, with new stopped-height
observations. It does not call `CurrentStartPlanner.plan`, choose new baked
support, manufacture a `CurrentStartPlan`, or restart an old observer. Guide,
source, body, reader and owner identities remain checked. The future suffix
stays planning evidence; the retained current prefix is unchanged. Another new
matching pair is required after planning, including when geometry outlives the
original half-second observation window.

The optional `CampProbePlan.route_guide` now carries that planning sequence
through the actual retained engine before lease release. It uses the same
configured location key and original runtime deadline. Guide/preparation
replacement is refused. Route-ready completion stops before any onward input;
there is no default provider/guide or new owner control. Traces keep compact
route identity/start evidence rather than embedding an entire long itinerary.
Cancellation diagnostics retain the owned preparation and updated collection
history.

VERIFIED 19 focused local source-planning checks passed in 14.72 seconds.
VERIFIED final Alienware candidate `owner-tools/0.42.52-validation-1`:
**45 checks passed in 72.08 seconds**, output SHA
`b278dd1257e7d9b18957810df161b7af453d37018783d6ec577d6a504ad594ae`.
Coverage includes the new planner, original current-source planner, retained
engine handoff/F8/F9 and actual watchdog/pipe checks. In particular, route-start
key UP/operation cleanup precede lease release and queued F8 assist. Changed
guide/preparation identities stop before the start collection. Private source
publication pending. Synthetic
positions, scenes and admission only; no game input, character action or prefix
changes. Current movement admission and explicit new observer/driver adoption
remain unfinished. Preview stays 0.39.30; G0 passed, no new owner test. Actual
level, XP/hour, deaths and camp remain unknown; 1–20 and hands-off 1–50 are not
accepted.

## 2026-11-14 18:27 UTC — source 0.42.51 privately published

VERIFIED Alienware `owner-tools/0.42.51/source`, revision
`89c2ce08157bf2cae88d7c75f3b2a3b5cbd5b8f7`. Runtime/tests/tools match the
58-pass final calibration/retained-handler candidate. Imports, diagnostic CLI
startup and copied-data pins pass. Archive SHA
`599af8aa8d966231bc4d4b176d75e528930048f5d513f55867566e63de9f0fea`;
startup SHA `a320dd5ee6a16ce8aa609cb8308ac470d7808b3eaf3112b11ccead9864f389cf`.
Publication record: `releases/eql-automation-0.42.51-staging.json`.

The existing rotation tool's fitter now receives actual distinct camp probe
pairs. Completion retains a conditional estimate or explicit refusal; it never
loads a live calibration or authorizes a route. Preview stays 0.39.30 with no
default camp-probe plan/policy. No game input, device creation, character action
or protected-prefix edits. Current movement admission and reached-reference
adoption remain unfinished. G0 passed; no repeat/new owner test. Current level,
XP/hour, deaths and camp unknown; no real 1–20/1–50 acceptance.

## 2026-11-14 18:26 UTC — source 0.42.51, conditional camp calibration

Implemented a separate-leg reducer which retains all 14 actual immediate
before/after pairs rather than inventing an eight-pair chain. Each transaction's
first post-release pair supplies displacement; its later post-geometry pair is
confirmation evidence. Increasing sequence/time, stationary collection gaps,
source-height correspondence and exact continued transaction ownership are
checked. The standard seven keys/durations and the existing retained fitter's
latency/direction/left-turn checks remain required. The original eight-pair
measurement API retains its report format.

The optional retained-engine handoff now records a conditional estimate or an
explicit unavailable reason at completion. Successful or failed fitter callbacks
must leave ownership/evidence intact. No saved live calibration is written and
no next route is started. Future speed bounds, client input-consumption timing,
full-turn ambiguity and current heading remain unverified.

Initial local focused run: VERIFIED 46 passed, one failure from numeric zone IDs
at the generic reducer boundary. The adapter now uses a tagged zone identity,
retaining the actual numeric ID/display in raw evidence. VERIFIED final Alienware candidate
`owner-tools/0.42.51-validation-1`: **58 checks passed in 19.09 seconds**, output
SHA `85b139a2c149785140de2cf08616a0e4034751d9e7e993cb81ba47aa2eb30514`.
Scope: new per-leg/transaction reduction, original calibration behavior and
retained-engine handoff/F8/F9 checks. Private publication pending. All positions/receipts in new ledger tests are synthetic; source
floor transactions and the retained fitter are real code. Existing engine tests
use actual watchdog/OS-pipe writes with synthetic game feedback. No game input,
character action or prefix edits. Preview stays 0.39.30; G0 passed, no repeat.
Current level, XP/hour, deaths and camp unknown. Full 1–20 and hands-off 1–50
remain unaccepted. Next: explicit current movement policy and reached-reference
adoption for onward routing.

## 2026-11-14 18:21 UTC — source 0.42.50 privately published

VERIFIED Alienware `owner-tools/0.42.50/source`, revision
`84164032b5fbb59d8bd4e07cc44f9c31da53f549`. Runtime/tests/tools match the
31-pass final retained-engine/OS-pipe candidate; imports, diagnostic CLI startup
and copied-data pins pass. Archive SHA
`3e8106a1d10dceb87862633fadd1b635205aa3f2425277e4be895e3259ab7890`;
startup SHA `85bbdbdcf04b3eeab11966cc69c500e31465aa233d0e2c9fd9adcaae761e88fd`.
Publication record: `releases/eql-automation-0.42.50-staging.json`.

Optional camp-probe handoff and retained F8/F9 handlers are tested with synthetic
admission/game feedback. The owner launcher has no default probe plan provider;
preview remains 0.39.30. No real client input, input-device creation, login,
character action or protected-prefix edit. Current movement admission, independent
scene/supported motion bounds, calibration reduction and next-route adoption
remain unfinished. G0 passed; no repeat/new owner test. Current level, XP,
XP/hour, deaths and camp remain unknown; no real 1–20/1–50 acceptance.

## 2026-11-14 18:20 UTC — source 0.42.50, retained-engine probe handoff

VERIFIED optional `CampProbePlan` handoff preserves the exact post-recovery
reader lease, sender, hotbutton, monitor, fresh height and original floor.
The completed position collector detaches before the finite runtime starts.
A separate noncombat input branch permits only its exact active location or
movement driver; unrelated commands/input remain refused. Generation, focused
window, settings, recovery, monitor and original floor checks remain active.
There is no default plan provider or permissive movement policy.

VERIFIED retained-engine F8 job handling and F9 `stop_action` during actual
watchdog movement DOWN: movement UP and descriptor-operation cleanup precede
reader release; F8 assist activates only on the following safe tick, with no
new movement or target command. F9 leaves camp and assist off. Cancellation
remains latched through cleanup. A successful two-probe handoff captures full
result/preparation evidence and stops before a next route; it does not resume
the old stationary camp from the changed position. Malformed plans and policy
construction exceptions stop without movement or combat resumption.

VERIFIED five focused local handoff-failure checks passed in 13.87 seconds.
The first Alienware candidate passed 29 checks. After the final malformed-probe
and policy-exception fixes, **31 checks passed in 52.84 seconds** at
`owner-tools/0.42.50-validation-2`, output SHA
`944ba4e77e6245cb7b78ca548d3096288b8365a7544b8c1be6690dda64eecde5`.
Selected checks cover the new retained-engine handoff, ordinary position-only
behavior and actual watchdog/OS-pipe runtime. The unchanged long travel case
was deselected. Scene, bounds, game replies and movement admission are synthetic;
control tests invoke the real engine handlers, not physical F8/F9 events in a
running client. No real client input, character action or live acceptance.

Private source publication pending. Owner preview remains 0.39.30; its launcher
has no probe plan provider. Next: explicit current movement admission, conditional
calibration reduction and next-route adoption from the reached reference.
Independent scene/supported motion bounds remain missing for unattended input.
Current level, XP, XP/hour, deaths and camp remain unknown. G0 passed, no repeat
or new owner test. Full 1–20 and fresh hands-off 1–50 remain unfinished.

## 2026-11-14 18:12 UTC — source 0.42.49 privately published

VERIFIED Alienware `owner-tools/0.42.49/source`, revision
`c2dabe5616535304910524cd7ceb61d099802830`. Runtime/tests/tools match the
11-pass actual-watchdog/OS-pipe candidate. Imports, diagnostic CLI startup and
copied-data pins pass. Archive SHA
`93b75833874860446c0284a573412cd83d3ed2b04d7f69295f3ed6d7c22a4e34`;
startup SHA `ddfc2af8bc8e89abacf3e37ab5aacebd24849850fd681ef4fc11a98f37d25b67`.
Publication record: `releases/eql-automation-0.42.49-staging.json`.

The runtime uses synthetic admission and game feedback in validation. No game
input, helper engine launch, device creation, login, character action or prefix
edit. Owner preview remains 0.39.30. Next: actual camp-position handoff and
retained-engine F8/F9 controls with an explicit current movement policy.
Independent scene/supported motion bounds remain needed for unattended input.
G0 passed; no repeat/new owner test. Current level, XP, XP/hour, deaths and camp
remain unknown. No real 1–20 route or fresh hands-off 1–50 acceptance.

## 2026-11-14 18:12 UTC — source 0.42.49, finite runtime and actual pipe sender

VERIFIED `CampProbeRuntime` now sequences actual source preparation, fresh
start collection, selected watchdog pulse, post-release collection/body check,
fresh confirmation, reached-floor retention and the next preparation. One reader
lease and stop lock span the sequence. Completed collectors are detached before
geometry; reentrant ticks only check current scope and never consume the reader.
A stale start after watchdog READY is refused without renewing its timestamp.
Stop revokes the lease immediately, while actual lease release waits for busy
work, held keys and descriptor-operation cleanup to finish.

VERIFIED `send_camp_probe` pins the retained descriptor, selects after READY,
requires an exact bounded input admission and releases the original descriptor
even if the sender's descriptor changes. It never writes the replacement
object. Interrupted receipts and final release times remain in diagnostics;
cancelled movements cannot commit endpoints. `CampProbeInputPolicy` is a required
abstract dependency with no permissive implementation. It does not infer scene
clearance or speed bounds from geometry, logs or old calibration.

VERIFIED two focused local missing/refused-policy checks pass in 7.64 seconds.
All **11 Alienware checks pass in 33.68 seconds** at
`owner-tools/0.42.49-validation-1`, output SHA
`f285d8ba47dd44c3438d0bbbd00224bae4b1679ef0481c6f16b3d0b4c700df72`.
These use actual watchdog subprocesses and OS-pipe event writes, explicit
synthetic admission/geometry and synthetic replies generated by the configured
location key. The full seven-probe run completes with 27 position pairs and
seven movement receipts. Tests also cover stop requests labelled F8/F9 after
DOWN, missing/refused/oversized admission, command/owner-input veto, expired
start, focus loss and replacement-descriptor isolation. Native F8/F9 engine
integration is not claimed by these cancellation tests. No game input occurred.

The initial local fixture attempt exposed a synthetic log-clock regression;
it was corrected to preserve its existing wall/monotonic mapping. Client
freshness limits were not loosened. Private source publication pending.
Owner preview remains 0.39.30 with the existing rotation bot. Next: transfer the
actual post-recovery camp-position scope into this runtime, test retained-engine
F8/F9 ordering, and supply an explicit current movement policy. Production
independent scene and supported motion-bound producers remain missing for
unattended input. No new owner controls/test or G0 repeat. Current level, XP,
XP/hour, deaths and camp remain unknown; real 1–20 and fresh hands-off 1–50
remain unfinished. No client login, character action or prefix edit.

## 2026-11-14 18:06 UTC — source 0.42.48 privately published

VERIFIED Alienware `owner-tools/0.42.48/source`, revision
`3503f060d0f467a1b19a055b0f4c6eec4366da9f`. Runtime/tests/tools match the
89-pass validation snapshot. Imports, diagnostic CLI startup and copied-data
pins pass. Archive SHA `eae0b93a5abc5603808017efe31e59d5e17e7cdf9aa0ef9c8ec821098af9648f`;
startup SHA `b92660f0dcd12694701b8accf5246b66312c58b3a712caf329315809b39008db`.
Publication record: `releases/eql-automation-0.42.48-staging.json`.

This source increment continues checked probe floors across a synthetic
seven-probe sequence. It does not connect actual movement or new owner controls.
Preview stays 0.39.30. No helper worker, input device, game input, login,
character action or protected-prefix edit. G0 remains passed; no repeat.
Next: finite camp runtime plus sender/collection integration with explicit
current movement policy. No real 1–20/1–50 acceptance; current level, XP,
XP/hour, deaths and camp remain unknown.

## 2026-11-14 18:05 UTC — source 0.42.48, reached-floor probe continuation

VERIFIED a fresh exact confirmed `CampProbeResult` can be consumed once into
`CampProbeFloorReference`, retaining a private checked endpoint floor and the
actual transaction/reader/stop-lock ancestry. The original arrival checkpoint,
travel observer and calibration are not modified or reconstructed. Retention
rechecks freshness and cancellation after callbacks. Continued preparation uses
an actual newly collected `CampStoppedHeight` on the reached floor; the previous
result's pair cannot be relabelled as new evidence. A different stop lock,
released lease, ancestor cancellation or changed source/result invalidates the
continuation. Existing arrival-height/preparation behavior remains covered.

VERIFIED **89 focused local checks passed in 62.33 seconds** and **89 Alienware
checks passed in 4.90 seconds**. This includes an actual seven-transaction
source-floor chain with synthetic forward/right/forward/right/forward/left/forward
receipts and positions outside the original arrival cap. Original expiry and
calibration identity remain unchanged; stopping the first transaction invalidates
the last. These are short explicit motion hypotheses, not the real client's
seven-probe calibration or a heading fit. No game input was sent.
Remote candidate: `owner-tools/0.42.48-validation-1`; output SHA
`3638485e58194b50ab6bcbd2a120e5e835f0bf818b213bf609e8e4c2ae835db9`.

OBSERVED next runtime integration point: `owner_camp_position._camp_position_tick`
must transfer the exact sender/hotkey/monitor/lease before `_release_camp_position`
clears the reader and resumes combat. `StoppedLocationPair` and
`send_location_hotkey` already supply collection. The existing source sender's
exact ledger/policy requirements cannot be bypassed with a fabricated travel
ledger. Next: a finite camp-specific runtime and selected-key sender adapter
requiring an explicit current movement policy, with F8/F9 release behavior
checked in the retained-engine/OS-pipe harness. Production independent scene
and supported motion-bound producers are still missing for unattended input.

Source publication pending. Owner preview remains 0.39.30; no new controls or
owner test. G0 passed, including visible stop. No client login, character action,
input device or protected-prefix edit. Current level, XP, XP/hour, deaths and
camp remain unknown. Automatic camp relocation and full 1–20/1–50 acceptance
remain unfinished; no completion is claimed.

## 2026-11-14 18:01 UTC — source 0.42.47 privately published

VERIFIED Alienware `owner-tools/0.42.47/source`, revision
`226d48105067adadb3c6d1e6f925893ecde37f8d`. Runtime, tests and tools match the
56-pass validation snapshot byte for byte. Imports, diagnostic CLI startup
and copied-data pins pass. Archive SHA
`3168bafc087b81e52081e59fc44023452eb97b1f65f3be09eff8cf10804f8e88`;
startup SHA `ef50a2883a2f091e496853f9168cea68e320960682be0d21f39b1c2be79f9b64`.
Publication record: `releases/eql-automation-0.42.47-staging.json`.

Owner preview remains 0.39.30. No helper worker, input device, game input,
client login, character action or protected-prefix edit. The single-probe
transaction is input-free and not connected to owner controls. Reached-reference
continuation, current scene/motion evidence and actual sender integration remain
next; no automatic relocation or 1–20/1–50 acceptance is claimed. G0 passed;
no repeat. Current level, XP, XP/hour, deaths and camp remain unknown.

## 2026-11-14 18:01 UTC — source 0.42.47, single camp-probe transaction

VERIFIED `CampProbeTransaction` binds an exact consumed `CampProbeStart` to
one movement kind/key and matching receipt. It checks elapsed completion,
positive requested hold, maximum actual hold and fresh release timing. The
post-release pair is resolved on the prepared probe floor, including positions
outside the original camp arrival cap. The entire endpoint body must remain
inside the exact prepared envelope and pass terrain/static/BSP/native checks.
Geometry runs outside the shared stop lock. A new matching stopped pair after
geometry finishes is required; the planning pair's timestamps are never renewed.
Cancellation, stale observations, changed lease/binding or altered retained
records discard the transaction. Original checkpoint and calibration remain
unchanged. A returned floor fork is historical evidence, not a new checkpoint;
it must be obtained while the original reader lease is still active.

VERIFIED final focused checks: **56 passed locally in 29.94 seconds** and
**56 passed on Alienware in 3.40 seconds**, including 39 new transaction cases.
The remote final candidate is `owner-tools/0.42.47-validation-1`; output SHA
`2a70ce27b8e3ae3215a4fb0b7824af734c4f09a35861ea844c334dccf52b688e`.
Cases cover moved endpoints, full-body containment, one-use starts, wrong keys,
interrupted/short/overlong receipts, stale/moving/wrong-floor replies, F9 during
geometry or context callbacks, and retained-evidence changes. Synthetic game
receipts/positions and copied-geometry fixtures only; no game input or device.

No typed receipt authenticates its sender. Input, current motion/heading,
sender origin and real-client acceptance remain false. This is a single-probe
source component, not a measurement executor: next-reference production,
actual sender integration, current independent scene evidence and supported
motion bounds remain necessary. Automatic camp relocation and full 1–20/1–50
remain unfinished. Source publication pending; owner preview stays 0.39.30.
G0 passed, including visible stop; no repeat or new owner check. Current level,
XP, XP/hour, deaths and camp remain unknown. No character, login or prefix
change was attempted.

## 2026-11-14 17:52 UTC — source 0.42.46 privately published

VERIFIED Alienware `owner-tools/0.42.46/source`, revision
`3d53836f2da4e950943a7ab265a2d888b9b45622`. All eight startup checks pass,
including byte identity of the locally checked audit script, matching
static facts against the actual installed executable, changed-source refusal
and diagnostic CLI startup. Eight local audit checks also pass. This reads
the owner's installed binary without executing it or changing the prefix.
Owner preview remains 0.39.30; no new owner test is requested.

- Archive SHA `eec1fdd94bb253f67589309ebce696eae7405aff3b8f7a2b87fb7a6cc4b55b24`.
- Startup SHA `6c9c1774a649f2b4f858599df006565af5cbe3a57e7863a6d7b972aa5ec1e767`.
- Publication record `releases/eql-automation-0.42.46-staging.json`.

No client process, input device, game input, login or character action was
started. G0 remains passed, including visible stop. Current level, XP/hour,
deaths and camp are unknown. Static movement composition does not certify a
speed bound or live route; automatic camp relocation and full 1–20/1–50 remain
unfinished. Next: current scene evidence and bounds on additional motion
contributions/clock before automatic heading probes.

## 2026-11-14 17:51 UTC — source 0.42.46, static movement composition

VERIFIED copied executable SHA `fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`.
The constructor binds actor virtual +f0 to `0x14031ebb0`, which returns the
embedded movement object at actor+21d8. Its virtual +10 is `0x140694a70`.
The inspected update dispatch calls this before collision processing. The
update combines a uint32 tick difference times binary32 0.02, a further clock
callback, forward/input-vector terms, residual velocity and a final position
hook. The clock callback's units/effective bound are not established here.

VERIFIED static contributions: `0x1403314c0` conditionally adds angle-projected
terms derived from actor+484/+488, 0.5 and an optional runtime global.
`0x140331240` can add vertical and horizontal position terms after integration;
its horizontal term has no additional time-factor multiplication within that
function. Angle/phase wrapping does not bound their amplitudes. The inspected
functions have no magnitude clamp for these terms. This is not a claim that
all movement code lacks a cap. Actual state, producer bounds, alternative
vtables, clock callback and other position writers remain unobserved.

INFERRED: a bound on the normal forward scalar alone cannot establish a bound
on the final displacement. Do not promote the prior 40/60/150 hypotheses,
old fitted speed or a heading-wrap constant into current movement authority.

VERIFIED reproducible tool `tools/audit_client_motion_update.py`: pins the exact
file, nine virtual-table slots, six constants and 15 bounded source spans;
writes native evidence only into the private client-data store. Eight focused
checks passed: reproduced facts, all disassembly hashes, two independently
checked spans, false input/live flags, wrong-binary refusal, existing-output
refusal, CLI startup and compilation. Report:
`client-data/native-motion-update-0.42.46/probe.json`, SHA
`6f589331bafb99b3a65c30d5cef577ac0bde69db766f9250d3d01cf230a84a15`.
The report retains `verified_speed_upper_bound=null` and movement authority false.

OBSERVED REA opened/hashed the exact copy, but its native provider is unavailable:
Ghidra requires a full JDK 21 or newer. No configuration/access changes or
installation attempted. The REA target was closed; analysis used bounded
ordinary objdump, not REA decompilation or native execution. Provider status
is retained beside the report. No game input, login, capture, character action
or protected-prefix edit occurred. Owner preview stays 0.39.30; G0 passed,
including the owner's visible-stop confirmation. Source publication pending.
Current level, XP, XP/hour, deaths and camp remain unknown. Automatic camp
remeasurement/relocation, real 1–20 acceptance and fresh hands-off 1–50 remain
unfinished. Next: bound the additional terms/clock or observe them inactive,
and supply independent current scene evidence before a checked probe.

## 2026-11-14 17:45 UTC — source 0.42.45 privately published

VERIFIED Alienware publication at `owner-tools/0.42.45/source`, revision
`f9c40c3ec96c0e899c41f9fdc047b6740afd19c0`. Runtime, tests and tools match the final
53-pass snapshot byte for byte. Imports, diagnostic CLI startup and copied
client-data pins pass. Owner preview remains 0.39.30 with no new controls or
input behavior. Record: `releases/eql-automation-0.42.45-staging.json`.

- Archive SHA: `eabafd96d24d405e17d1def00c0d0f9271b1f59ccb154b03026a921edbea078c`.
- Startup SHA: `a2e18edb401088bb6558aeb171df59962fc3c5a6db71e3449098c69f19292d4a`.
- Focused output SHA: `c5bb60d5caa65d8a9432a8df3ada6a0dbacbc2fb02d1360a330cf3def647710c`.

No worker, device, game input, prefix edit, login or character action. No
real-client route acceptance or current level/XP/hour/deaths/camp metrics.
G0 remains passed. Current scene and supported motion-bound producers, the
checked pulse/post-pair transaction and automatic relocation remain unfinished;
no complete 1–20 or fresh hands-off 1–50 run is claimed.

## 2026-11-14 17:44 UTC — source 0.42.45, fresh source-probe preparation

VERIFIED `CampProbePreparation` consumes an actual `CampStoppedHeight`, the
exact retained floor and active reader lease. It checks an all-heading source
body envelope using explicit caller-supplied planning hypotheses. It does not
construct a walking route, pose, turn calibration or `open_flat_clear` claim.
Slow geometry work may outlive the original pair; those timestamps remain
unchanged. A new consecutive stopped pair must match the exact checked source
position/offset before a start record is issued. That record retains its own
0.5-second expiry. Input and current-motion authority remain false throughout.
Cancellation or changed scope, envelope, bounds, record or reader discards the
preparation without mutating the original camp floor.

VERIFIED 38 focused local checks passed in 9.46 seconds. The final Alienware
snapshot `owner-tools/0.42.45-validation-1` passes all 53 selected preparation,
source-geometry and fresh-height checks in 2.07 seconds, output SHA
`c5bb60d5caa65d8a9432a8df3ada6a0dbacbc2fb02d1360a330cf3def647710c`.
All positions, guards and geometry fixtures are synthetic; no game input.
Private source publication pending. Owner preview remains 0.39.30, and the
new preparation class is not enabled in owner controls.

VERIFIED read-only Alienware process inspection this turn found no process
named `eqgame.exe` or `EverQuest Legends` and no `~/eql-journey-trace.jsonl`.
No client launch, capture, login or character action was attempted. This
provides no current level/XP/death/camp information. G0 remains passed; no repeat.

OBSERVED in source: no production `G2UiObservation` producer or
`G2SafetyProvider` construction exists. The frame reader retains unknown scene
flags. `RouteMotionBounds` checks hypotheses; the motion fitter explicitly
returns `verified_speed_upper_bound=None`. The route's conditional speed upper
interval times 1.25 and finite 150 limit are not independent physical caps.
Neither historical arrival speed nor quiet logs is promoted to current proof.
Current scene/body/speed/drift evidence and a checked pulse/post-pair transaction
remain necessary for automatic remeasurement. No live 1–20 or fresh hands-off
1–50 acceptance, and no automatic relocation is claimed.

## 2026-11-14 17:40 UTC — source 0.42.44 and preview 0.39.30 published

VERIFIED private publication on Alienware at `owner-assist/0.39.30` and
`owner-tools/0.42.44/source`, revision `593d66e65531e6a64b3a3e8da4e4dcc0ba0bf285`.
Runtime and test files are byte-identical to the final 50-pass snapshot.
Existing tools match too; the additional packaging wrapper was exercised by
the successful local preview build. Preview manifest, installed executable/
spell pins, both source guides, reduced NPC history and no-input GUI startup
pass. This supersedes preview 0.39.29 for owner-run travel/camp testing.

- Archive SHA: `dbb9a11dcca82312e98fc1af2dfb6aac70f5d2603c1ec2da9f5d62b526a22364`.
- Startup SHA: `da52755c351fb87704008a76bcc717f0c743aeab3248ce2cc24c51d0f5ccf683`.
- Focused check output SHA: `8e6e5437350b022af9ebebc8086130bfb1ba5acb92a0d7636de65e9e852bb895`.
- Record: `releases/eql-owner-journey-0.39.30-staging.json`.

The new collection runs automatically only after the first kill/recovery at a
camp reached by travel; it requests positions and resumes the same camp.
F8 cancellation preserves the queued switch to assist until original-key
cleanup completes. No automatic relocation is enabled. No lead game input,
input-device creation, settings save, prefix edit, login, character action or
session interruption occurred. G0 remains passed. No actual camp/route
acceptance or current level, XP, XP/hour, death/camp metrics; full 1–20 and
fresh hands-off 1–50 remain incomplete. Next: checked unknown-heading probe
preparation on that actual fresh source floor, then automatic camp relocation.

## 2026-11-14 17:39 UTC — source 0.42.44, automatic post-recovery position collection

Implemented in the same owner helper: after the first matching kill and
completed recovery at a camp reached by travel, acquire an exclusive lease on
the same log reader and collect two new stopped replies through the exact
same-session configured location hotbutton. The pure source-height validator
checks those replies on the retained floor before the lease is released.
Successful collection records evidence and resumes the same camp. Initial
spell-preparation recovery and later ordinary fights do not repeat the check.
Standalone F11 camps and owner-targeted assist retain their existing behavior.
No movement, target change or chat typing is added by position collection.

The final stand-command completion time is now explicitly retained as a
settling reference; it does not prove posture. Stop revokes the lease immediately
but waits for in-flight hotbutton release before returning the reader. F8's
queued assist request survives that same cancellation's cleanup. This avoids
an extra stop generation discarding F8. Failed collections preserve their
request/release diagnostics. The fresh height record keeps its original short
expiry and cannot authorize a later trip.

VERIFIED first Alienware snapshot: 13 focused checks pass in 3.73 seconds,
output SHA `2871d060c92d624d75af98a774e5d1a38fdef8d0a4631846a077f7ed71aae231`.
The next snapshot adds F8 cleanup coverage and passes 14 checks in 4.14 seconds,
SHA `c8ae9a8430f5b5c4a56b747d313052764d5effc4619bb6f200316bea43c54e4a`.
The initial local test fixture lacked a rotation object after skipping synthetic
preparation; fixed the fixture. Its next attempt hit the original watchdog
key-down deadline under Devbox load 218/48 CPUs. No timing limit was relaxed;
Alienware load was 1.98/24 CPUs. VERIFIED final snapshot `owner-tools/0.42.44-validation-3`: all 50 checks
pass in 90.99 seconds, including actual full travel handoff→new collection
and focused existing recovery/continuity cases. Output SHA
`8e6e5437350b022af9ebebc8086130bfb1ba5acb92a0d7636de65e9e852bb895`. All game feedback is synthetic; senders write to OS pipes only.

Preview 0.39.30 builds locally; manifest and every runtime module match source.
Private publication is pending. No device creation, game input, prefix edit,
login or character action. Actual level, XP, XP/hour, deaths and camp unknown;
no accepted full 1–20 or fresh hands-off 1–50. G0 remains passed.

Next implementation detail from read-only source review: the unknown-heading
probe needs a route-independent session over the actual checkpoint, fresh
height, checked source envelope and release receipt. Existing source walking
objects require already measured heading/turn motion and an original route;
recreating those with guesses would be invalid. Post-pulse replies must use the
exact checked envelope branch, not the old arrival cap or an arbitrary supplied
floor. Current scene and supported motion bounds are still required before
movement; neither historical arrival speed nor quiet logs supplies those facts.

## 2026-11-14 17:32 UTC — source 0.42.43 and preview 0.39.29 published

VERIFIED private publication on Alienware: `owner-assist/0.39.29` and
`owner-tools/0.42.43/source`, revision `22c1e47ec48aa66001acedc6aa62cd585b2e829d`.
Runtime, tests and tools match the 71-pass snapshot byte for byte. Preview
manifest, installed executable/spell pins, both source guides, reduced NPC
history and offscreen GUI startup pass. F8/F9/F10 assist controls and the
travel/camp UI remain available; the obsolete G0 launch flag still refuses.

- Archive SHA: `03abd5a38f302eba938bbeb9a64b2d91fa96686d394c3b9f46652890579bbfec`.
- Startup SHA: `aa75d92768dfd2faba16a41586af57cf8269651c91408f4fdd3ed6fe08fcc679`.
- Check output SHA: `deecae856afff85c2afd4e9e2c626ea5828ec48eb001dbcb52a83db5bac96cac`.
- Record: `releases/eql-owner-journey-0.39.29-staging.json`.

No game input, input device, settings save, prefix edit, login, character action
or session interruption. No actual camp/route acceptance or level gain claimed.
G0 remains passed; no repeat. Current level, XP, XP/hour, deaths and camp remain
unknown. The next increment is automatic fresh stopped-position acquisition
after a reached camp's first kill and recovery, followed by same-camp resumption;
automatic relocation and full 1–20/1–50 remain unfinished.

## 2026-11-14 17:32 UTC — source 0.42.43, reached floor retained through camp

VERIFIED local implementation and 67 focused checks: `CampFloorCheckpoint`
captures the exact latest stopped source-ledger reference before navigation
releases its reader. It keeps a private floor-chain fork, source/static/BSP
pins, model/policy identity, immutable arrival and historical-height records.
Camp keeps this historical checkpoint while the original movement observer
expires normally. F9, assist, manual input or changed bindings discard it.
The physical-input monitor performs full floor checks before sampling devices;
its final checks invoke no extra model callback after the freshness boundary.

`measure_camp_stopped_height` is an input-free producer for two new consecutive
stopped replies after a new acquisition baseline. It uses only the retained
checked floor cap, validates the fresh height offset against the actual arrival,
and expires its result at the second reply plus 0.5 seconds. It neither renews
the old calibration nor grants movement authority. Automatic collection is not
yet connected. Local preview 0.39.29 manifest and all runtime bytes match source.

VERIFIED final Alienware snapshot `owner-tools/0.42.43-validation-1` passes
all 71 selected checks in 175.21 seconds. This includes a full actual retained-
engine/OS-pipe handoff and late F9 during floor capture, lease release and input-
monitor transfer. Output SHA
`deecae856afff85c2afd4e9e2c626ea5828ec48eb001dbcb52a83db5bac96cac`.
All game feedback is synthetic. Publication is pending. No game input, device creation, prefix
edit, login or character action. G0 remains passed; no repeated owner check.
No accepted live 1–20 route, automated level gain or fresh hands-off 1–50 run;
actual level, XP, XP/hour, deaths and camp remain unknown.

Read-only integration design for the next increment: reuse `StoppedLocationPair`,
the tracker lease and the exact same-session `OwnerLocationHotkey` after the
first matching kill and recovery. Preserve the final stand-command completion
time as a settling reference, not proof of standing. Release the lease after
hotbutton cleanup on cancellation, before assist may resume. Record a successful
fresh pair and resume the same camp; any later relocation needs another fresh
pair. No extra device, log parser, fabricated open-ground declaration or old
observer restart is needed.

## 2026-11-14 17:19 UTC — source 0.42.42 published, five source probe areas pass

VERIFIED private publication on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.42/source`, revision
`4fab02fb07de228ac4ba851c751759399a65d011`. Source, tools and tests match the final 57-pass
Alienware snapshot byte for byte. Imports, diagnostic CLI startup and copied
client-data pins pass. Publication record:
`releases/eql-automation-0.42.42-staging.json`.

- Archive SHA: `fb8b7edef8c40bd182a7af599ee45c017e82d97837c538aff1879b5282d2e1fe`.
- Startup SHA: `956bd973724d7baa7ebd7f5bd98207bc9bf4e7dd58148f77f4b358f8866cfb08`.
- Focused output SHA: `0f6932d70bbf559ede2bdab7f3dab7353c9ea7a6366c79fef4066b04914991dd`.
- Final copied geometry audit SHA:
  `f3c6ad73badd02d42b6933177adda08973fe85b0e43af23663a77526b1902358`.

Five of six explicit hypothetical source probe sizes pass; the largest North
Wall disk still refuses. The audit completed in 40.33 seconds on Devbox. This
removes the copied-detail start obstruction for the smaller conditional areas,
not the remaining live floor/position/height/heading requirements.

Owner preview remains 0.39.28 using the existing rotation tool. No input
worker/device, game input, settings save, prefix edit, login, character action
or session interruption. G0 passed; no repeat. No accepted automatic camp
relocation, real 1–20 route, automated level gain or fresh hands-off 1–50.
Actual level, XP, XP/hour, deaths and camp remain unknown. Next: capture the
exact reached floor through camp and acquire fresh stopped height/position
evidence before any checked heading pulse.

## 2026-11-14 17:19 UTC — source 0.42.42, source-floor probe geometry

VERIFIED final copied-data audit: `crushbone-source-probes-0.42.42-final.json`, SHA
`f3c6ad73badd02d42b6933177adda08973fe85b0e43af23663a77526b1902358`, completed in 40.33 seconds. The historical Slave Mines
source/static prefix replays exactly: 1,065 cells, seven steps, final proof
`176bbef50fb75c7e1cc635c851cbd7dcac57b7dab27b06d8ed090636ab7ac3fa`.
Parent region checks were not repeated; each new probe independently ran the
full terrain, static-object, body-BSP and native-region checks. The North Wall
start is an explicit synthetic unique source-floor hypothesis, not an arrival.

With hypothetical speed ceiling 40, body radius 1.2, body height 6, position
error .05 and post-release drift .1:

| Copied source point | Maximum actual hold hypothesis | Whole-area geometry |
| --- | --- | --- |
| Slave Mines `(426,74,-17)` | .02, .05, .1 seconds | All three pass |
| North Wall `(-95,-78,0)` | .02, .05 seconds | Both pass |
| North Wall `(-95,-78,0)` | .1 seconds | Refused: selected floor uncovered ground area |

Every possible heading/intermediate position is covered under those supplied
bounds. These are not measured current speeds or live-authorized durations.
The source checker shares the exact existing movement-driver terrain/static/
body-BSP/native sequence. It retains the selected source floor instead of
reselecting by map-label Z or asserting clearance from the baked perimeter.
Baked-detail failures remain recorded; no mesh coverage claim is made. The
original floor stays unchanged and the returned branch carries no input ticket.

VERIFIED focused checks: 22 new cases pass locally in 3.12 seconds. Final
Alienware snapshot `owner-tools/0.42.42-validation-2` passes all 57 selected
probe and existing source movement checks in 2.62 seconds, output SHA
`0f6932d70bbf559ede2bdab7f3dab7353c9ea7a6366c79fef4066b04914991dd`.
The first local attempt exposed an incorrect test seed (fixed), plus an
existing 0.05-second DOWN authorization timeout under Devbox load ~194; no
deadline was relaxed. The complete 55-case initial Alienware run passed in
2.76 seconds, SHA `27e1618523899f18f4c947c2d9b2f06aa5be616946623a1398b50d0dfd55a944`.
Two later tests reproduced acceptance after a final callback replaced source
storage or classifier metadata. Final context rechecks now reject both, and
source storage/query identities are checked around shared geometry too.

The initial copied probe report SHA
`2fa9a879bcdeb2e88d9ae115b825bf18411a2de1a06dfbf3c2753c2803380bbf`
had the same five accepted sizes, before those final callback checks. Final
report code/data hashes match the final source geometry implementation. An
earlier audit invocation refused the 19 MB parent report at the ordinary
16 MB route-data loader; this audit now uses its own explicit 32 MB limit and
the exact historical SHA, checked before/after. Runtime limits are unchanged.

Source publication pending. Owner preview remains 0.39.28 using the existing
rotation. No game input, prefix edit, login or character action. G0 remains
passed. Next: preserve exact arrival-floor lineage through camp and produce
fresh stopped position/height evidence before a checked heading measurement.
No automatic relocation, accepted 1–20/1–50 or current level/XP/hour/deaths/camp.

## 2026-11-14 17:16 UTC — North Wall copied-detail refusal reconciled

VERIFIED by the read-only geometry helper against the pinned current store:
North Wall package XY `(-95,-78)` is on baked polygon 505, component 3,
Z `0.162506103515625`; source WLD 2141 face 0 is at Z 0. Boundary 518 face 5
is overhead at Z 623.75. Mesh SHA
`ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56`;
manifest SHA `3c5701958bead8a9919be4d86db36cef80e57ed32825a4a75543cdac0d121b37`.

The .1 hypothetical hold disk overlaps copied details 4510/5236, polygons
368/505, at Y `-80.65621948242188` / `-80.65625`. Area
`0.00014963621876599282`, zero height delta, four binary32 ULP: the existing
one-ULP classifier correctly refuses. The separately constructed pinned tile
model recognizes that exact pair (axis 1, lower tile 4), with zero orientation
refusals. This does not resolve the whole probe.

The .02 disk misses `1.4197280411564766` units of baked area: details 5235/5236
cover `13.291830650243012` of `14.711558691399489`. The requested radius 2.15
(circumscribed 2.192120990147884) exceeds the 1.5030526029314686 distance to the
nearest western polygon edge. No reciprocal seam covers that exterior edge.
Thus tile correction alone cannot make this probe pass. Neither baked refusal
proves a physical wall; complete original terrain/object/body-region checking
is the next route, using the existing source-motion driver's checks.

A separate read-only capture review confirmed that the old source observer
cannot simply be resumed after camp: camp intentionally changes cancellation
generation and measurement mode, and the original height calibration expires.
Lease release and reacquisition also clear `reader.latest`. Capture a private
snapshot-checked fork of the exact arrival floor before release; keep the old
observer/height evidence historical. A later camp-bound scope must obtain two
new stopped replies and fresh height evidence on that retained checked cap.
Do not extend the old calibration, fabricate heading/open-ground declarations
or choose a floor by nearest Z. None of this capture/relocation is enabled yet.

## 2026-11-14 17:12 UTC — source 0.42.41 privately published

VERIFIED on Alienware: source revision `17d3a344b22226f8ed87ed1618ce7392052df0a7` is published at
`~/.local/share/eql-automation/owner-tools/0.42.41/source`. All 56 focused
probe/current-route checks pass (synthetic feedback), imports and diagnostic
CLI startup pass, and copied client-data pins match. The 122-check local
validation also covered precision/native-region behavior.

- Archive SHA: `6c801445f27c3a1047256e00100a25f3c2831d5c2101e7eef659be63796f69a2`.
- Startup SHA: `9a601aa7d45f023d7ed71b6f9f182cb22824fdc29071dfc509b6fcfaf13c7033`.
- Check output SHA: `aacfea503fe5fe2403a1d7e56062d25fe182d7dec1b382936e22c235c05ee608`.
- Local publication record: `releases/eql-automation-0.42.41-staging.json`.

Owner preview stays **0.39.28**, with the existing rotation bot. This source
increment is not a new owner launcher and enables no game input. Both copied
camp probe refusals remain. G0 stays passed, including the owner's visible-stop
confirmation. No repeat, login, game action, prefix edit, helper interruption
or real-client route acceptance. Actual level, XP, XP/hour, deaths and camp
remain unknown; full 1–20 and fresh hands-off 1–50 remain unfinished.

## 2026-11-14 17:11 UTC — source 0.42.41, unknown-heading probe area

VERIFIED locally: 122 focused checks pass in 16.01 seconds across the new
probe envelope, existing current-position route, precision-seam and native
region checks. The new library validates a fresh stopped location pair, then
checks a circumscribed disk covering every possible forward heading (or pivot
displacement) under explicit motion/body hypotheses. It uses complete local
detail/source/static/BSP inventories and the existing native region policy.
It produces conditional geometry evidence, no movement ticket or route. No
input is sent and no current heading/speed or independent scene is asserted.

Shared current-floor validation preserves the existing route contract. A
read-only review identified an area-tolerance gap: tiny detail strips could
complete exact XY coverage without slope, seam-height or source-height checks.
Three new regression cases reproduced the gap. Every positive patch now gets
those checks; a harmless flat strip still passes. All 122 checks passed after
the fix. These are synthetic fixtures, not client acceptance.

VERIFIED copied-data diagnostics with synthetic observations at map destination
XY, not a character position:

- `nav-candidates/crushbone-probe-envelope-0.42.41.json`, SHA
  `8c5b96b205d18db150dfcc4c420cf9fdd9915ca6a1dbf33e3199b8512118faff`:
  speed ceiling 40, maximum hold .1, body radius 1.2, height 6 were hypotheses.
  Slave Mines refuses its layered Diffuse floor; North Wall refuses
  `overlapping_ground_faces`. This first diagnostic preceded the tiny-strip fix.
- `nav-candidates/crushbone-probe-envelope-0.42.41-short.json`, SHA
  `968198472623e230f59081897dc035c82a726bc95bf164b9d5759f123a8d023d`:
  same hypotheses except maximum hold .02; includes complete code/data hashes
  and motion/body parameters. Slave Mines again refuses layered floors; North
  Wall refuses `no_bounded_reciprocal_seam_set`. This runs the corrected helper.
  Shorter hypothetical duration is diagnostic, not an accepted live pulse.

Both reports are outside git in the private store. Source 0.42.41 publication
is pending; owner preview remains 0.39.28. Next: reuse exact retained arrival
floor provenance with fresh stopped observations rather than selecting a layer
from map Z, and reconcile North Wall detail seams. No automatic relocation,
real route/camp acceptance, level gain or fresh 1–20/1–50 run. G0 stays passed,
including the owner's visible-stop confirmation; no repeat. Actual level, XP,
XP/hour, deaths and camp are unknown. A read-only Alienware check found no
`~/eql-journey-trace.jsonl`; load 2.25/24 CPUs, available memory ~12.4 GiB.

## 2026-11-14 17:11 UTC — installed compass evidence (read-only helper)

VERIFIED read-only against the owner's installed client: default compass XML
defines a 98×32 window, two 180×24 scrolling compass strips and a 98×24 overlay.
The active default_light artwork was visually inspected: E, SE, S, SW, W, NW,
N, NE and a fixed red center marker. Saved `[CompassWindow] Show=0` is saved
layout evidence, not current window visibility. No live frame or input was
captured/sent. No verified compass-toggle key or command was found; do not
assume Alt+D. Client strings mention compass/Sense Heading but do not establish
a usable numeric heading observation. Actor-versus-camera orientation and
angular accuracy are unverified. True North exists in client spell data but
was absent from the retained learned-spell list; no spell was cast.

Paths relative to the protected installed game directory:

- `uifiles/default/EQUI_CompassWindow.xml`: SHA
  `9a216cec7c43387a3dd6ee1a659a8de31e564876f2df1075efe2d89ae0a1b043`.
- `uifiles/default/EQUI_Animations.xml`: SHA
  `c1b787f5b6e5aa6a556c4aa236377494303a96a184b67ffe470c76ade1c3ac35`.
- `uifiles/default_light/window_pieces04.tga`: SHA
  `ca1191753025f8bf11cda7593be2198b13efcc87bef2c51947816af23f76b319`.
- `UI_Legira_freeport_LO1.ini`: SHA
  `5876a4136283b692263bc2826ffc2b12cd7328f4faa320c5f4071f2092fbc76b`.
- `eqclient.ini`: SHA
  `a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc`.
- Retained `eqstr_us.txt`: SHA
  `0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`.
- Retained 18-row spellbook: SHA
  `ee7147598c13c6bcd1d1fa17de8e889d436b53608187ab9ce37d1c097ce8df92`.

A future read-only observer can resolve the compass overlay and match this
artwork, refusing hidden/occluded/ambiguous frames. This is a possible route
to heading observation, not implemented current-state evidence.

## 2026-11-14 17:01 UTC — 0.39.28 published; camp observer remains continuous

VERIFIED: source 0.42.40 revision `ea6d335e9142dffec958619bf8e5acf2f92b1258` and preview 0.39.28
are published on Alienware at `owner-tools/0.42.40/source` and
`owner-assist/0.39.28` under the private store. Runtime/tests match the final
27-pass validation snapshot byte for byte. Manifest, installed executable and
spell pins, both route guides, owner NPC history and GUI/startup checks pass.
GUI bytes match the previously inspected image. No broad repeated suite ran.

- Release SHA: `4a2b6153c9a1dd7d90e7135a3ac9ae8963d6dc4fcb595275ad9c232a92348f0f`.
- Startup SHA: `78a33c1aa5eb47c0ca6d834025e8f8a4757dba260b98605cae05be93784a0223`.
- Final focused checks SHA: `72096bcca85bdcf1872ad76261c23843c716cc71daf190d9a1285a6cd9af0537` (27 passed, 45.08 seconds).
- Local record: `releases/eql-owner-journey-0.39.28-staging.json`.

The original input monitor stays open after travel→camp and closes on stop or
assist. Manual input, focus/coverage loss or binding replacement stops camp.
The final pose/motion basis is historical evidence, never permission to move.
Standalone F11 behavior is unchanged, so an owner F11 test on 0.39.27 remains
useful. HOWTO has the 0.39.28 launch path and current mode behavior.

No worker/device/game input, settings save, prefix edit, login, character action
or owner session interruption during publication. No accepted real-client route,
camp loop, automated level gain or full 1–20/1–50 run. Current level, XP/hour,
deaths and camp remain unknown. G0 is passed; no repeat.

Next relocation work can reuse fresh stopped-pair/current-floor validation and
the full terrain/static/BSP/native sequence in `SourceReceiptLedger._geometry`.
For an unknown heading, `motion_footprint` with zero nominal reach and an explicit
all-heading travel radius can enclose the possible movement disk; sampled rays
are insufficient. Speed bounds would remain assumptions until measured. A
read-only client compass/heading observer is also being investigated. Neither
approach has been implemented or accepted for automatic relocation yet.

## 2026-11-14 16:56 UTC — camp input continuity for later relocation

VERIFIED locally: 26 focused checks pass for source 0.42.40 / preview 0.39.28
candidate. The original read-only physical-input observer is now retained across
successful source-route arrival into camp. The navigation lease is still released
and navigation remains inactive. Failed/cancelled handoffs keep default cleanup.
F8/F9/F11/quit closes the retained monitor; F8 enters assist only after cleanup.

The monitor rejects brief turn press/release, mouse activity, lost coverage,
topology changes and replaced sender/UI/tracker/window/character/log bindings.
Loss is latched; a later clear scan cannot restore it. Synthetic OS-pipe camp
checks confirm no new command after invalidation. Observed camp level changes
are accepted through the existing camp binding; unobserved settings edits stop.
Same-thread helper events remain excluded by the observer's existing exact
uinput-device identity. No permission/access/device changes were made. The final monitor additionally
pins its observer/clock/binding context and rechecks after callbacks, so a direct
sample call cannot return successfully after reentrant cancellation. The first
local fixture for helper exclusion changed topology after capture and correctly
failed; it now establishes topology before the synthetic handoff.

The arrival basis copies the final source ledger's heading, actual motion values,
checked bounds, floor/itinerary hashes and stopped position/sequence into immutable
bytes. It does not reuse the calibration-start heading. Every snapshot explicitly
states movement is unauthorized and current heading/motion are unverified: no
physical input alone cannot rule out forced movement, auto-facing or speed effects
in combat. Automatic relocation still needs fresh stopped positions and a
geometry-checked heading/motion measurement. No route authority is retained in
the monitor. Camp checks, not the old navigation combat veto, govern encounters.

VERIFIED on Alienware: the initial candidate passes all 26 selected checks
in 219.46 seconds, including full travel→camp and late F9 at four handoff stages.
Output SHA `8b8cd2bec94bc82bdef3c42cb9979bdace9f40cef4e2739e6ffb7fee85d2de64`.
That snapshot is retained at `owner-tools/0.42.40-validation-1`. The final monitor
context/callback refinement has 26 local passes in 1.02 seconds; the separate
final snapshot passes all 27 selected checks in 45.08 seconds, including a
complete handoff. Final output SHA
`72096bcca85bdcf1872ad76261c23843c716cc71daf190d9a1285a6cd9af0537`;
retained at `owner-tools/0.42.40-validation-2`. The first local
preview is retained at `owner-build-drafts/0.39.28-first-snapshot`; it was never
published. No running helper was replaced. Alienware aggregate load was 3.70
on 24 CPUs with about 13.6 GiB available memory before the short final check.
Publication is pending. A read-only check
found no `~/eql-journey-trace.jsonl`; the G0 trace remains historical, and the
owner's visible-stop confirmation remains accepted. No repeat G0. Current level,
XP/hour, deaths and camp remain unknown. Complete hands-off 1–20/1–50 is unfinished.

## 2026-11-14 16:51 UTC — 0.39.27 published on Alienware

VERIFIED: source 0.42.39 revision `056a9cb5ab570091ac03565a426c1f28baa8f84b` and owner preview
0.39.27 are published under Alienware `~/.local/share/eql-automation/` at
`owner-tools/0.42.39/source` and `owner-assist/0.39.27`. Runtime and test bytes
match the 84-pass validated candidate. Manifest, installed executable/spell
pins, both route guides, reduced owner NPC history and GUI startup pass.
The GUI image hash is unchanged from the previously inspected 0.39.26 image.

- Archive SHA: `5defdd3054e2f3aa72f4fb22f1b69127f1cb6465cff257d318af7c49819e9f49`.
- Startup SHA: `788a91164797fed01a3da3c93e98e12c4cc8bfaa8c4377dd2e3ba0c418e490cf`.
- Check output SHA: `69b7341fb562869340fb0efeaeccdde094475a9e2f4557c12022c5c4acd22f4c`.
- Publication record: `releases/eql-owner-journey-0.39.27-staging.json`.

Existing rotation/GUI code is retained. No worker, device, game input, settings
write, prefix modification, login, character action or session interruption.
The owner can close the previous helper and launch
`~/.local/share/eql-automation/owner-assist/0.39.27/launch.sh`.
F8 assist, F9 stop, F10 heal and F11 stationary camp/OFF are unchanged.
G0 remains passed, including the owner's visible-stop confirmation; no repeat.

No real-client traversal, camp acceptance or automated level gain was established
by these checks. Full 1–20/1–50 remains unfinished. Actual current level, XP,
XP/hour, deaths and camp remain unknown. Next: owner-run camp acceptance and
preserved motion/heading observations through camp before enabling relocation.

## 2026-11-14 16:50 UTC — fresh-character candidate fallback and NPC-selection fix

VERIFIED: source 0.42.39 derives a 5,370-byte private NPC-name artifact from
retained owner log SHA `d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`.
The artifact is `owner-route-data/owner-npc-candidates-20261113-v1.json`, SHA
`0d43373b543d09a41e43f76aa42bfee9e6d892dda898ea238a4cac2fe8d73676`.
The existing parser finds five GFay names, four Crushbone names and none for
Butcherblock. Only names, historical levels and source line pairs are included;
no raw chat or other-player log content is distributed. Source bytes are checked
before and after extraction, and the builder refuses a changed output hash.

The selected character's log takes precedence. With no candidates there, the
runtime can use that exact artifact only for matching Freeport/zone identity.
It does not scan other logs, invent current level/position, grant target authority
or manufacture absent log continuity. Missing optional data provides no names;
changed, oversized, symlink or nonregular data is refused. The camp's existing
installed-executable check remains. Candidate origin and artifact hash survive
into camp start/final evidence and the existing travel-to-camp handoff.

VERIFIED: an actual retained Engine/KeySender fixture exposed a pre-existing
camp issue: `Targeted (NPC)` sets `native_attack_off_pending`, while the camp's
overridden combat tick omitted the owner's no-command bookkeeping cleanup.
The next `/cast` therefore refused. The camp now runs that inherited adapter
cleanup and waits for the next tick. It sends no `/attack` command, and an
observed native-melee ON message still stops camp. This is a synthetic feedback
reproduction, not a newly observed live-client result.

All 84 focused candidate/camp checks pass locally in 3.44 seconds, with actual
OS-pipe key events and synthetic game feedback. Earlier new-test failures first
used a wrong fixture server/log filename; the corrected fixture then exposed
the NPC-selection issue above. No movement or authority limits were relaxed.
The existing matching-consideration path uses unknown kind if no selection
receipt exists; it does not require an explicit NPC receipt. Bad fresh target,
high level, PC selection and cancellation remain refused.

VERIFIED on Alienware: all 84 selected focused checks pass in 44.36 seconds,
including the full copied-geometry fixture travel→camp handoff carrying fallback
candidate provenance. The raw-log reproduction check ran locally only; it was
excluded remotely so raw chat did not need to be redistributed. Remote output
SHA `69b7341fb562869340fb0efeaeccdde094475a9e2f4557c12022c5c4acd22f4c`.
No game input. Preview 0.39.27 private publication/startup checks are pending.
G0 remains passed including owner confirmation; never repeat it. Actual current
level, XP/hour, deaths and camp remain unknown; full 1–20/1–50 is unfinished.
Automatic relocation still needs preserved motion/heading continuity through
camp, fresh stopped positions/posture and a supported destination choice.
Copied map level labels alone are not evidence of suitable live encounters.

## 2026-11-14 16:43 UTC — 0.39.26 published on Alienware

VERIFIED: source 0.42.38 revision
`33b7fc9e58eeb3d0fd2e2af6137bf3149bd01e1c` and owner preview 0.39.26 are
published at `owner-tools/0.42.38/source` and `owner-assist/0.39.26` under the
Alienware private store. The release's runtime and test files match the
40-pass validated candidate byte for byte. No broad repeated suite was run.
Both guide pins, packaged source manifest, installed executable/spell pins,
GUI startup and obsolete measurement-flag refusal pass. The GUI was visually
inspected: destination selector and travel button are visible and enabled.
Its saved Legira/level-7 settings do not establish the current character state.

- Release archive: `15ee2da1a72ef27c44c79f1f3e276dcd39e23f353540381a0fca1df7a7b3644c`.
- Startup evidence: `75e1980e2bf9f4ccd8825db5cc5b0313e00ff35b7034ee4c1fb7dcf2251d42e0`.
- GUI screenshot: `ccbcc1b39cf3fbd8f4262848df736d8cbe2db64cf58fc75a1c36c173927287ad`.
- Local publication record: `releases/eql-owner-journey-0.39.26-staging.json`.
- Local inspected GUI: `owner-build-drafts/0.39.26/alienware-camp-gui.png`.

No worker/device/game input, settings write, prefix modification or owner
session interruption during staging. Existing native engine hash is unchanged.
No live traversal, camp suitability, automated level gain or complete 1–20/1–50
acceptance. Owner can now explicitly test North Wall/Castle from near Slave
Mines; current-floor rebuilding and all movement limits still apply. Automatic
level-based camp relocation, earlier levels and later destinations remain
unfinished. G0 stays passed; no repeat. Current level/XP/hour/deaths/camp unknown.

## 2026-11-14 16:40 UTC — North Wall copied route checked; owner candidate

VERIFIED: the compacted reverse guide from Slave Mines `(426,74)` to the
combined North Wall/Castle annotation `(-95,-78)` passes the complete copied
terrain/static/BSP/native-region itinerary check. Its 237 operations rebuild
into 247 checked cells with seven explicit steps; destination source height is
0. The retained 1,065-cell/seven-step prefix was replayed again first. This is
conditional geometry evidence, not a current character position or traversal.

- Report `nav-candidates/crushbone-north-wall-transit-0.42.38-compacted.json`:
  `6271afba7548adb9c64dfde89f065aaf28dd3ff2b7f136b0b6ee8e505fc30300`.
- Checked plan: `6c56b689c20fa0cb1af25a681c70a1e8adbb5b12690bbea81e9b68d323d77559`.
- Private `owner-route-data/crushbone-camps-20261114/crushbone-north-wall-source-guide-v1.json`:
  `62f8f50797414ace566d7ec967a5ed61153b15ccdb11efeb4f2ea35f38f67d97`.
- Guide record: `0e3827e24ad599762b1ad75a1669f21d57cadf7d776e61779921332b99ae59a4`.

The 633 original reverse operations compact to 237 using an eight-unit hint
length and an explicit `1e-8` XY rounding tolerance. Every intermediate point
is tested against that tolerance; steps, reversals and larger turns remain.
These are new proposals and proofs, not a claim of exact geometry equivalence.
The diagnostic finished in 126.24 seconds. Its offline total budget is now
600 seconds to include parent replay; the itinerary check still caps at 240.
Owner startup, pulse, observation and travel limits were not increased.

VERIFIED: eight compaction checks, one actual-pipe eight-unit driver check and
15 destination-loader/queue checks pass locally. The driver case confirms
three bounded releases with fresh stopped pairs, then mid-leg OFF without a
new floor or later action. Its initial test failures mixed synthetic and real
clocks/log timestamps; the corrected fixture uses consistent real timing.
No product time or provenance checks were relaxed.

Three local complete-handoff checks stopped before handoff: one release
watchdog refusal and two current-floor connector refusals. Reports and hashes
are retained in `owner-build-drafts/0.39.26/local-handoff-refusals.json`.
Devbox was heavily loaded; timing is a possible cause, not a verified diagnosis.
The isolated Alienware run **passes all 40 focused checks** in 322.79 seconds,
with synthetic geometry, game feedback and OS pipes. It covers both queued
selection and complete handoff, destination mutation at release, existing
F8/F9/F11 cancellation, loader pins, compaction and the long-leg driver.
Output SHA `3d5bc125e878da71b31c5664631daf882ccf20ff5184f962723e5bfba94929f3`,
retained under `owner-tools/0.42.38-validation-1/checks.txt` on Alienware.
No game input or character action. The native runtime limits were unchanged.

Source 0.42.38 / owner preview 0.39.26 is built and validated; publication and
GUI/startup checks are pending.
It pins both destination guides, copies the queued choice, rejects unknown or
mismatched destinations and retains selected-destination evidence through the
fresh arrival/camp handoff. The GUI has an explicit selector and separate
travel/camp indicators. Native engine SHA remains
`d4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e`.
Real traversal/camp suitability and automated relocation after level-ups are
unverified/unfinished. Full 1–20/1–50 remains unfinished; G0 remains passed.

## 2026-11-14 16:25 UTC — source 0.42.37 published

VERIFIED: revision `4cd5c622ad31654aac8e5d49579c22c659b01e97` is staged at
Alienware `~/.local/share/eql-automation/owner-tools/0.42.37/source`.
All 23 selected checks pass there with zero failures, errors or skips; imports,
the diagnostic CLI startup and copied client-data pins also pass. No engine
worker, device, game input, install modification or owner-session interruption.
Owner travel/camp preview remains 0.39.25; standalone assist remains 0.39.13.
No new route, camp or level milestone has been accepted. G0 remains passed.

- Source archive SHA: `59dac50095eff4d5e081941c3bd96a04e53fefd616d550bfc7351b1394d43590`.
- Focused output SHA: `6d586a6e73caf74c007c331a1ee1b9b9c9481bc9a1de6d205c5c7d82c0434a59`.
- Startup SHA: `334d67dfdf1d2a595e5015498e714d6c3e2c6dfe02999bb74fd476eb18a99628`.
- Local publication record: `releases/eql-automation-0.42.37-staging.json`
  under the private data store. No client data/assets were committed or pushed.

## 2026-11-14 16:24 UTC — source 0.42.37, longer camp transit proposals

VERIFIED: 23 focused checks pass for the new source-face transit graph,
reverse-guide builder and existing itinerary validator. Long ordinary paths
are divided into short checked cells; exact 3D edge identities preserve floor
layers and explicit steps keep landing identities. Floating-point subdivision
retains exact final endpoints. Search clocks and adjacency construction are
bounded. Reverse guides retain the previous departure floor as a proposed new
landing; old proofs never become current character observations.

VERIFIED copied-data replay: the retained synthetic itinerary's **1,065 cells
and seven steps** reproduce final floor proof
`176bbef50fb75c7e1cc635c851cbd7dcac57b7dab27b06d8ed090636ab7ac3fa`.
Every walk proof, static check, step transition and landing proof was checked.
The parent's region evidence remains pinned, not replayed in this diagnostic.
Any proposed new suffix is checked against terrain, static objects, BSP and
native region classifications by the complete itinerary planner.

The first North Wall/Castle graph proposal had 129 edges, seven steps and
1,116 guide operations. It **failed** with
`Source itinerary terrain: selected_floor_uncovered_ground_area`; it is not a
usable route. Retained report:
`nav-candidates/crushbone-north-wall-transit-0.42.37-initial.json`, SHA
`c1cbfb0830d47ab618d95076ad054c07ec6e49a6e7ecabfa3cf1c9dbe6e10255`.
The earlier graph inventory has SHA
`c68ad077a864eca7f8d97644a761a227709eb1bc04a95f29dfee779fb74108ef` at
`nav-candidates/crushbone-camp-transit-graph-0.42.37.json`. That inventory used
an endpoint seed hypothesis; the later full replay above supplies the checked
offline lineage. Neither establishes a current avatar floor or input authority.

OBSERVED read-only geometry review: Trainer Hill's 22-face component `(454,2)`
and its 14-face approach component `(937,6)` remain isolated under the current
step proposal model. Two approach boundaries have opposing floor heights
11/0 and 12/0. Individual wall triangles spanning four or one unit are only
parts of those walls, not traversable step heights. Other access, partial-edge
joins and possible static-object support remain unverified; no physical
disconnection or larger client step capability is claimed. Movement bounds
were not increased.

The reversed suffix toward the nearest North Wall point (36.52 units from the
annotation) replayed the same 1,065-cell/seven-step prefix and produced 633
reverse operations. The full check then **exhausted its 300-second work budget**;
this is not a geometry acceptance or proof of a blocked physical route. Report
`nav-candidates/crushbone-north-wall-transit-0.42.37-reverse.json`, SHA
`354a3bb73b6cf418dc8bf7835fcec973c6b50e055c8a984dd246bf1eb8c02a62`,
records 303.40 seconds including cleanup/save. Devbox load reached 283 on 48
CPUs. Only one nice-19 geometry job ran at a time. Proximity alone is not a
connector. Next: compact redundant straight walk hints, retaining explicit
steps and full footprint/region checks, and retry the complete copied route.

Read-only integration review found that the existing source runtime already
consumes a guide's selected goal. A future accepted destination needs a pinned
registry entry, a destination ID captured in the queued Journey request and
matching arrival/report evidence. The original strict motion declaration and
F8/F9/F11 cancellation must remain intact. The copied map has one combined
North Wall/Castle annotation; no separate Castle endpoint is invented. No new
destination is enabled in this release.

No game input, Alienware geometry load or protected-install changes. Preview
0.39.25 remains the owner build; real traversal/camp acceptance and complete
1–20/1–50 remain outstanding. G0 is passed and must not be repeated.

## 2026-11-14 16:07 UTC — 0.39.25 published and next camp evidence

VERIFIED: source 0.42.36 (`f7bed78`, runtime `9d4dd29`) and preview 0.39.25 are
staged on Alienware. **89 distinct checks pass**: the first package run had
88 passes and a test-only missing-`patch` failure; the corrected final check
executes the SHA-pinned packaged native input loop directly and passes. No
utility or access change. Initial validation source/output are retained under
`owner-tools/0.42.36/source-initial-validation-missing-patch` and `checks.txt`;
corrected source is `owner-tools/0.42.36/source`, final check output is
`checks-native-final.txt`. The runtime package is unchanged by that test fix.

- Initial checks SHA: `ac73dc14c90c9a97ca53c8467c1b483c623e03783e324a4380463ec90fc76f06`.
- Final native check SHA: `8138a95fdc8975284122efb252275a3cc37b1549033d7e435d5691f419b53f45`.
- GUI SHA: `64ef2866989f98c905a0100c1896735a5fdd5a1a6b779d5f62b746616998c2fc`.
- Startup SHA: `644c6b75fd535f1e10c36f76cfd7e790eb416096178aaef56cfb2b3d819cd5f9`.
- Packaged native engine SHA: `d4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e`.

Manifest/source equality, installed executable/spell pins, GUI controls and
measurement-flag refusal pass. No worker/device/game input, settings write,
protected-prefix modification or owner-session interruption. These checks do
not establish actual movement, spell preparation, safe camps or leveling.
Current actual level/XP/hour/deaths/camp remain unknown; G0 remains passed.

OBSERVED next routes: copied map annotations place Trainer Hill (10–13) at
package XY `(119,-212)`, North Wall/Castle (13–17) at `(-95,-78)`, Throne Room
(17–22) at `(106,154)`. No retained complete source guide for these destinations
was found in the approved artifact inventory. Trainer has a unique diffuse
point proposal at Z80.1933236/face(460,1), North at Z0/face(2141,0); Throne is
layered. These are point proposals, not traversable routes or suitable camps.
Root rehashed the approved artifacts:

- `nav-candidates/crushbone-floor-seeds-0.42.24.json`: `14c561a20ca70de087008c8dad27a11560dec831c8362a4401123f903a8b458d`.
- `nav-candidates/crushbone-camp-annotations-0.42.23.json`: `7b43a48bd1b6a8307e71bc97fb3e2956086f23e98d8e7484ceeb60f8409e27bc`.
- `owner-route-data/crushbone-camps-20261114/crushbone_3.txt`: `4b1c009838988b13507797afd1ccbce8ba23e1ca99adbafd1065956cfd71bda0`.
- Sole retained source guide, `crushbone-source-guide-v1.json` in that directory:
  `88aecac52585363add569d3f66ed9ba19921725e81e3a1626e96c50cfdc847e7`.

The copied owner log **does exist**, superseding earlier no-copy notes:
`owner-traces/eqlog-Legira-20261113.txt`, rehashed
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`.
The bounded candidate parser finds five GFay names (observed levels1,2,10),
four Crushbone names (levels1–8,10,12,13), no Butcherblock names. This can seed
future fresh-character discovery; it does not authorize a current target or
prove current level. No chat contents were returned. A nearest-NPC action is
present in client strings, but its actual physical binding remains unverified;
no F8/Tab default or new slash syntax is assumed. No new route search or live
client acceptance was performed during this evidence inventory.

## 2026-11-14 16:01 UTC — combined travel and camp candidate

Source 0.42.36 joins the retained movement and stationary-camp engine in one
owner-started helper. Only explicit hotbutton setup/source-travel requests admit
navigation. Same-generation, same-reader source completion retains its actual
stopped receipt; the original raw-receipt 0.5-second deadline is preserved
through reader release and camp admission. Saved reports cannot continue a run.
The input observer remains open through handoff. Camp preparation and rotation
reuse the existing sender and cancel generation. F8 defers assist until movement
cleanup; F9 destroys the continuation. The packaged native F11-release hook
preserves key bookkeeping/debounce and consumes the navigation OFF latch even
if a separate observer or GUI Stop already cancelled the trip. First F11 after
setup/travel is intentionally OFF, documented in HOWTO and the GUI.

VERIFIED so far: 75 retained camp/assist checks and seven new local focused
checks pass. An Alienware synthetic/OS-pipe run reaches the source destination,
releases navigation and starts camp preparation/export. Movement, position-read,
lease-release and gauge-read cancellation cases pass there. Initial expected
export-filename and prefixed-notice test assertions were corrected; final
package checks are pending. Local GUI startup cannot use system Python without
NumPy or the navigation environment without PySide6; Alienware has the retained
runtime for the final smoke. No install/prefix, game input or character action.

Actual movement-to-combat acceptance, route/camp safety, current level/XP/hour,
spell preparation acceptance and a complete 1–20/1–50 run remain unverified.
The only combined destination is Slave Mines; later camps and GFay entry are
not silently enabled by this work. Retained movement 0.39.21 and camp 0.39.24
remain available. G0 passed and is not repeated.

## Automatic learned-spell preparation — 2026-11-14 15:42 UTC

**VERIFIED implementation, source 0.42.35 / preview 0.39.24:** an
explicit camp preparation phase now runs at startup and between fights after a
fresh level-up. It reuses the retained Catalog, profile selection, slot map,
KeySender, rotation builder and prepared-marker storage. The same log reader
checks new hazards before each key/Enter. No nested preparation worker, extra
reader or cancellation reset is introduced. Assist/F6 behavior stays separate.

A fresh filename-specific export acknowledgment and a changed, stable export
file are both required. The installed spell catalog is loaded and bound to its
file identity. Helper slots 1–8 receive one ID-zero clear request each; these
requests are explicitly not treated as verified empty slots. Every intended
gem then requires exact-name begin followed by finish after its sole submitted
command, with fresh sequence/time boundaries and no overlapping request. Wrong,
bare, duplicate, late or backward-time replies and silence fail. Readiness is
published only after settling, a complete log-batch check and current scope
checks. Logs name spells, not gem numbers; slot attribution is from the sole
outstanding command and uninterrupted scope, not an invented slot field.

Before any clear, the old prepared marker is invalidated. After partial failure
or F9, the bar remains unprepared; the old rotation never resumes on mixed gems.
The final marker save is also checked after its callback-bearing session lookup;
a late stop invalidates the saved marker again. Cooldowns for unchanged spells
use the retained rotation builder. After preparation, the ordinary recovery and
stand request precede further targeting. No buying or scribing is implemented.

**VERIFIED 75 focused checks pass** using the actual retained Engine/KeySender,
synthetic game feedback and OS pipes. They include startup without F6, a second
preparation after a ding with the same sender/generation, missing/stale export,
missing begin/finish, wrong spell, duplicate-spell refusal, changed catalog,
attack/zone/ding interruption, backward timestamps, F9 or attack while typing,
last-finish plus attack in one batch, and F9 during marker save. No game input.

**VERIFIED client evidence:** copied `eqstr_us.txt`, SHA
`0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`, documents
`/memspellslot` in resource 10009 and ID 0 forgetting the slot in resource 10010.
Resources 12053/12007/12496 name begin/finish/forget; 12052 is duplicate-spell
refusal. Historical owner log SHA
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e` contains
begin/finish pairs (e.g. Light Healing lines 458–461, Furor 12047–12053,
Center 15860–15863) and duplicate refusals at 2457/2458. Forget lines do not
identify a slot or prove an ID-zero command was used. **No retained real
ID-zero submission or new automatic-preparation acceptance exists.**

**OBSERVED old false-success path:** retained live trace SHA
`c24a83e8f42a246e7e3f87f30d5f04285a24bf5e058147198d1381a3c8024c26` records six
`mem_outcome=already` results after roughly two seconds with no begin/finish.
That establishes the old timeout classification, not correct gem contents.
The new automatic camp path never accepts that classification. Manual F6 still
uses the retained path; its prior success must not be promoted to strict proof.

**VERIFIED read-only Alienware export copy:** the existing client-produced
`eql-rotation-spellbook.txt` is retained at
`client-data/spellbook-observed-20261114T1540Z/eql-rotation-spellbook.txt` in the
private store. It has 235 bytes and 18 tab-separated rows, SHA
`ee7147598c13c6bcd1d1fa17de8e889d436b53608187ab9ce37d1c097ce8df92`.
All 18 names resolve through the retained parser against copied `spells_us.txt`,
SHA `c179a57fe444a65838c3728895e57161912eb527e77d92859ecb007a3236c8e9`.
The catalog check is alongside the export, SHA
`edf3595ab94101af8d592cd7a72dc81db5a67a8c77856796cf7a93be2b5cbf32`.
This proves existing export format compatibility, not current level, current
gems or automated character progress. No game input or prefix modification.

**Still unfinished:** real preparation/targeting/combat/recovery acceptance,
travel→camp handoff, spell acquisition, vendors/supplies, death/relogin recovery,
a fresh-character 1–20 route and hands-off 1–50 proof. G0 remains passed; no repeat.
Current actual metrics remain unknown.

**VERIFIED private publication — 15:44 UTC:** preview **0.39.24** is on Alienware
at `~/.local/share/eql-automation/owner-assist/0.39.24`; source **0.42.35**,
revision `8ab65ffb750bd55ca89469ae65e934d2c94428de`, is at `owner-tools/0.42.35/source`.
All **75 focused checks pass on Alienware**. Packaged runtime modules match that
source; installed executable, `spells_us.txt` and `spells_us_str.txt` are verified.
The actual installed spell-data hash matches the copied catalog above; the
installed fade-string SHA is
`cdbe3d6e02eb0d636ed15a6f9d52fa1af5f82bacbd237a8102b7c23f281e4a32`.
The enabled camp GUI shows automatic preparation and its gem-1–8 change, with
unused inherited controls hidden. Its image was copied back, hash-checked and
visually inspected. Movement-entry refusal passes. No worker, device, game
input, settings write, install/prefix modification or character action occurred.

- Archive SHA: `0b1de2d0438a812610b27ffbba5dd4ce029d8844f3e61d6e9b7558550215101a`.
- Test output SHA: `8f0df46d40dc65102d465d4e7efc63088403bf9da78c54310224aa8d36abadeb`.
- GUI PNG SHA: `28def42eb197eee4b24cee74958af5052ade7058e47417eb34b778aff06cddd1`.
- Startup report SHA: `3494c55be6d8f735a0c8101ebc3dc09979926834625c5eda1099fc119952e2e8`.

Metadata: `releases/eql-owner-camp-0.39.24-staging.json` in the private store.
The initial local unpublished documentation candidate is retained under
`owner-build-drafts`. These checks are not real preparation or leveling acceptance.

## Repeated stationary camp and resource recovery — 2026-11-14 15:33 UTC

**VERIFIED source 0.42.34 / preview 0.39.23:** the existing owner
rotation Engine and KeySender now support repeated stationary encounters with
resource recovery in one cancellation generation. Each round clears previous
target permission, waits for a new exact-name/level consideration, and preserves
cumulative kill/loot/XP evidence. Duplicate kill identities cannot become another
same-name encounter. No-target sweeps wait 30 seconds and stop after 15 minutes;
fight, recovery and overall session budgets remain separate.

Recovery requests standing, submits one sit toggle if resources are low, waits
for HP ≥95% and mana ≥90%, requests standing and requires two fresh samples
captured after settling before another target attempt. Missing/stale gauges,
attack during recovery (including the old mob name), inventory/supply warnings,
client identity changes or OFF stop the session. There is no posture cleanup
command after OFF. The current bar survives a fresh level-up; outstanding old
consideration replies are discarded and rechecked. No automatic spell upgrade
is claimed. Observed level 20 stops further pulls. Assist remains manual for
movement, targeting, posture, camps and native melee.

**VERIFIED 53 focused checks pass** on Devbox against the retained Engine and
KeySender, synthetic feedback and actual OS pipes. These cover two same-name
encounters, duplicate kills, recovery longer than 30 seconds, stale/missing
readings, every recovery command interrupted by F9 (including final Enter),
late permission callbacks, pending level monotonicity, ding/kill in either order,
level-20 termination and bounded empty searches. Six initial assertions expected
InterruptedError to propagate; recovery intentionally handles it as stopped.
Those assertions now check stopped state, released keys, no posture publication
and no further commands. No real game input or client acceptance was performed.

**VERIFIED copied-client static control flow:** command registry `/sit` is at
`0x140deb160` and its handler at `0x140250380`; `/stand` is at `0x140deb180` with
handler `0x1402503f0`. `/sit` compares its argument with resource 12946 (`off`).
Non-off arguments, including `on`, reach posture toggle `0x1402b28d0`.
`/stand` requests state `0x64`. **INFERRED:** `/sit on` is not an idempotent
seated-state request. Preconditions, actual posture and server response remain
unverified. The repeated runtime hashes the installed executable at startup and
checks its file identity during use before permitting these commands.

Private audit: `client-data/posture-commands-20261114T1529Z.json`, SHA
`3d715d71bd85c409ccb7b189cf2f5f652b0de7e335679b186814f12b7eaae265`.
Executable SHA `fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`;
strings SHA `0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`.
Reproduce with `tools/audit_client_posture.py`; client bytes and bounded
disassembly stay in the private store. The REA native provider was unavailable
because its configured Java lacks JDK21, so the existing bounded objdump/PE
approach was used without changing tools or access. No native client execution.
Historical owner traces contain `/stand` submissions but no positive posture
acknowledgment; there is no retained live `/sit on` acceptance.

**NOT VERIFIED / unfinished:** real combat/rest/targeting acceptance, current
metrics, accepted 1–20 route, travel→combat handoff, automatic spell acquisition
and refresh, inventory/supply service, death/relogin recovery and fresh hands-off
1–50. G0 is passed and must not be repeated. **VERIFIED private publication — 15:34 UTC:** preview **0.39.23** is at
`Alienware: ~/.local/share/eql-automation/owner-assist/0.39.23`; source **0.42.34**,
revision `2ff4ec71eaab0e040e154993ffba4c8f04669a45`, is at `owner-tools/0.42.34/source`.
All **53 focused checks pass on Alienware**; packaged modules match that source,
the installed executable matches the posture-analysis pin, and the offscreen
GUI has an enabled **Repeat stationary camp · F11** button. Unused inherited
camp/route configuration is hidden. Movement-entry refusal also passes.
The GUI image was copied back, hash-checked and visually inspected. No worker,
device, game input, settings write or install/prefix modification was performed.

- Archive SHA: `420022f64d758f397ec3b268e83c8ed98c798a58074d563f0066e1ab8421153f`.
- Test output SHA: `41caf0e2f3ddf93f25110eb6240ab1a8716eb3cacbafbbbe8b6218122448527f`.
- GUI PNG SHA: `f902fc257be8326f052c6d0a86c07a61e200b0087ea20514c063aa79c8316640`.
- Startup report SHA: `7641c46b41150426c0e594a8374b90d5ff2b2a02f03d65d45c5f568bf485e220`.

Private metadata: `releases/eql-owner-camp-0.39.23-staging.json`. The initial
local unpublished GUI candidate is retained under `owner-build-drafts`.
There is no new real-client acceptance or automated character-level evidence.

## Stationary camp integration — 2026-11-14 15:17 UTC

**VERIFIED implementation and focused checks:** source 0.42.33 connects a bounded
one-kill camp directly to the retained rotation Engine and KeySender. It shares
the sender/cancellation generation with assist; there is no extra input process.
The engine remains inactive during acquisition, and fresh exact-name/level
consideration is required before casting. A separate camp authorization prevents
the legacy retaliation/previous-target branches from approving another target.
The camp uses the prepared spell rotation, respecting heal priority and mana
reserve, while excluding native melee, stance chords, Bash/Smite, movement,
rest/vendor and loot input. Log replacements skip history and terminate camp.
Completion stops combat too; F8 explicitly replaces camp with assist.

All **29 focused checks passed** on Devbox against the retained Engine/KeySender,
synthetic feedback and actual OS pipes. Initial test setup lacked evdev; the
fixture now reads Linux key constants directly without importing a device API.
An initial fixture expected the wrong nuke slot; the actual retained mapping is
gem 3. Later tests cover F9 during every command type and late providers/startup,
queued starts, replacement logs, other targets/adds, locked encounters, expired
replies, zone/focus loss, low resources and kills during consideration refresh.
No game input, owner login or real kill acceptance was performed.

The first Alienware candidate passed all 29 checks but its GUI smoke caught
the inherited disabled travel tab, which also disabled the new camp button.
That candidate and its failed startup evidence were retained as unpublished
artifacts after verifying no process was using either directory. The tab and
mode indicators are corrected in the replacement candidate; no process was
stopped and no game input was sent by the smoke.

**VERIFIED private publication — 15:21 UTC:** preview **0.39.22** is installed at
`Alienware: ~/.local/share/eql-automation/owner-assist/0.39.22`, and source
**0.42.33**, revision `7b82e2129bcb4049d9fcb056c9561ae40edd7a9d`, is at
`owner-tools/0.42.33/source`. All **29 focused checks pass on Alienware**. The
packaged runtime sources exactly match the checked source snapshot. The final
offscreen GUI shows the enabled **Stationary camp test** tab and **One stationary
kill · F11** button; its startup report confirms no worker, device, game input or
settings write. The movement-mode entry correctly refuses and points to 0.39.21.

- Archive SHA: `aae67ea09535f57ac7f3bbb25cfd1e8eed609121576287af887ff371e61bb40f`.
- Test output SHA: `b6ed5e95c99c83013d013faf04fcb7a89901ad930901e2e54d422c3ca01a8c88`.
- GUI PNG SHA: `0ef648b3ec40fc141824e691c0bb9735742d91358474dcfc6ef3299d1712b511`.
- Startup report SHA: `aaf0b910d115a17f95ca6cf58d85f1892b82a41265e20957addb840f606e9ac6`.

Metadata is retained at `releases/eql-owner-camp-0.39.22-staging.json` in the
private store. This is startup/pipe evidence, not a real kill or route acceptance.

**VERIFIED retained evidence:** `owner-traces/eqlog-Legira-20261113.txt` under the
private data store is 1,858,221 bytes, SHA
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`.
The exact Clan Crushbone intervals contain explicit NPC selections, matching
considerations and kills. For example, lines 7778/7781 and 7817/7819 pair an NPC
selection with the same centurion name's level-3/level-1 consideration. These are
historical candidate names, not nearby spawns, current targets or safe camps.
Protected/slave/pet/service names and legacy explicit avoid entries are excluded.
Runtime candidate collection uses at most the final 4 MiB of the owner's current
log and hashes those exact bytes; pair line numbers are relative to that suffix.

**OBSERVED range discrepancy:** the copied client map `crushbone_3.txt`, SHA
`4b1c009838988b13507797afd1ccbce8ba23e1ca99adbafd1065956cfd71bda0`, labels Slave
Mines 7–10, Trainer Hill 10–13, North Wall/Castle 13–17 and Throne Room 17–22.
The legacy guide uses differing ranges and mixed external/log guidance. Only the
client labels are retained as route hints; neither source establishes camp safety.

**Remaining real-client gates:** owner-run 0.39.21 traversal and owner-run finite
camp targeting/HP/mana/casting/kill observation. Camp repetition, verified rest,
loot, movement-to-combat handoff and hands-off leveling are unfinished. Current
level, XP/hour, deaths and camp remain unknown. G0 passed; no repeat.

## Owner source-route integration and private preview — 2026-11-14 15:05 UTC

**VERIFIED implementation:** source 0.42.32 connects the source itinerary and
transfer controller to a separate owner-started action in the existing rotation
helper. Startup retains its sender, physical-input observer, tested location
hotbutton, cancellation generation, stop lock and exclusive zone-reader lease.
It measures motion, plans from fresh current Crushbone positions using the
private guide, measures height on the selected floor, and consumes each new
startup reply immediately. No second worker, sender or ordinary baked-route
driver runs beside the source runtime.

Ordinary and partial-step pulses use the same supervised policy and aggregate
time/hold budgets. Only the stopped-pair collector polls the leased reader;
nested input pumps recheck scope without consuming it. Settling keeps the same
receipt/deadline and sends no movement. Stop propagates to the active collector,
transfer and ordinary ledger. The parent helper persists the result, returns
the lease and closes its retained physical-input observer. A reproduced final
collector-clock cancellation could overwrite the runtime's stopped phase; local
construction plus final ownership checks now prevents that publication.

**VERIFIED focused checks:** all 14 selected cases pass on Alienware in 86.21s:
nine source-runtime cases, four retained-helper source flows and one existing
native local-trial compatibility flow. They cover approach/partial landing/
ordinary continuation, settling with no extra movement, complete startup and
travel, F9 during movement/location DOWN, changed model rejection, cleanup and
no rearming. Feedback and geometry are synthetic; actual input writes use OS
pipes. Six changed source/test files were rehashed against the checked snapshot
and match. Output SHA
`834aafd5b28dc206d77da657cc45cfe456b0c1fc13cdd62dbb3a242f50751aa9`;
private metadata `releases/eql-source-runtime-0.42.32-checks.json`.

Initial Devbox watchdog checks hit scheduling refusals (sample load 255 on 48
CPUs). Remote full-helper checks then exposed excessive repeated owner checks:
selection took roughly 30–38ms, leaving about 29–33ms before DOWN; the final
stop check took roughly 27–35ms. The active source observation binding now
checks owner/window/generation/lease identity without recursively observing
physical input/model/files. The policy and watchdog still run full checks
immediately before GO under the shared lock, during input and after release.
No deadline or scene requirement was relaxed. The final focused run above
passes; earlier failed outputs and timing measurements remain in private
`owner-tools/source-runtime-check-20261114T1507Z`.

**VERIFIED private owner publication:** preview 0.39.21 is staged at Alienware
`~/.local/share/eql-automation/owner-assist/0.39.21`. Its source manifest,
offscreen GUI and enabled **Travel to Slave Mines…** action pass; copied
GFay/Crushbone geometry, the 1,053-operation private guide and installed
executables/archives/catalog match. Archive SHA
`73b10ff59e9406f7d35487bf9daff0bee2f8d020ca3d7927dd1d7fb64fc0bb7a`;
startup SHA `c328b348309c7a1e7243ba72acf35f04408e9b4e72ba5ad4592405156092aa44`;
GUI SHA `24fa80f0277a01fa90fad30ab75428659ce0a42d3ca725830ebde0aeb58023e6`.
No engine worker, device or game input was started. No install/prefix/character
was changed. The loader test used a synthetic zone identity and proves no live
current-zone observation. Assist 0.39.13 is unchanged.

**Owner action / remaining gate:** close the older helper, then on Alienware run
`cd ~/.local/share/eql-automation/owner-assist/0.39.21 && ./launch.sh --measure-navigation`.
Inside Crushbone, complete the existing location-hotbutton setup, then choose
**Travel to Slave Mines…** on clear starting ground. HOWTO gives the complete
steps and F9/F11 stop controls. G0 remains passed and must not be repeated.
Real traversal, step capability, live scene/position acceptance and camp safety
remain unverified. This preview neither fights nor levels. Current metrics
unknown; no accepted 1–20 or fresh hands-off 1–50 run.

**VERIFIED private source publication:** source commit `7658f33` is staged at
`owner-tools/0.42.32/source`. Seven focused no-input startup checks pass without
failures/errors/skips, plus imports, CLI, copied-data pins and private guide.
Archive SHA `8c0353c9f80cab72559f6ffb3582f0382450ff3b43b8e4e034525b7289896a1f`;
startup SHA `1a4b54535d0b88336d6bae5b95db5742326f10a42841bd93340236bda74e4872`;
test-output SHA `7592dd9382ea668fa3587360143f5cbaf23ee05533ece7b27713f672c627b7a2`.

## Receipt-bound source step progression — 2026-11-14 14:55 UTC

**VERIFIED implementation:** source 0.42.31 connects the conditional approach
planner to a typed transfer controller through the existing source sender and
shared stop lock. Checked branch identities remain private runtime state;
serialized plans cannot create a landing capability. Whole maximum-hold body
and center envelopes are checked independently. Every release remains
provisional until fresh consecutive stopped replies are consumed exactly once.

The ordinary ledger stays leased with its confirmed floor/pose unchanged during
a partial step. Geometry selects possible support before raw-Z comparison;
multiple heights remain ambiguous even if both fit the calibration residual.
Ambiguous or elevated readings enter bounded settling with no new movement.
A complete observed cap can publish an approach or landing; otherwise a partial
cap must overlap both checked riser sides. Downstep landing uses branch lineage,
not a larger height. Actual approach stops preserve the pending step instead of
steering back to an earlier guide cap. Policy time/origin/hold budgets remain
shared across every transition.

**VERIFIED focused checks:** all 18 transfer cases pass, including repeated
approaches, partial/up/down landings, settling/expiry, center-envelope refusal,
mutated branches, copied observations, OFF and stale callbacks. The combined
75-case run initially had 74 passes and one diagnostic-order mismatch: an
attempt to move while settling validated an old reference before reporting the
settling phase. Phase refusal now comes first; all 18 transfer cases pass after
the correction. Actual watchdog OS-pipe checks assert DOWN/SYN/UP/SYN and release
without committing a floor. Game positions, terrain and scenes remain synthetic.

Two material cancellation findings were corrected and covered: a final
observation callback could publish after OFF; a completed controller's late
cancel could stop a newer transfer lease. Final observations now recheck the
exact live receipt/window before consuming a reply, and cancellation propagates
only while the controller still owns the ordinary ledger's exact lease.

**Remaining:** owner-runtime connection and actual client traversal. No game
input, client login or character change occurred. Owner movement 0.39.20 and
assist 0.39.13 are unchanged. G0 is passed and requires no repeat; current
level/XP/hour/deaths/camp unknown. No accepted real 1–20 route, automated XP or
fresh hands-off 1–50 run.

**VERIFIED private source publication:** commit `27ee681` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.31/source`. All 97 selected startup
checks pass without failures/errors/skips; imports, CLI, copied pins and the
private guide match. No worker/device/game input or prefix modification.
Archive SHA `7cea7dd0fe34b0a0f068b16652f806012dab909da318d17e24af353163d429db`;
startup SHA `a8bfaff8ca317adf7fc50e37a5c227fcdd1a90897e80362ab192bee43d71ca2d`;
test-output SHA `8919fea7f2b1b7422c41825afda7bdc2f38ed8283ad704284b513d399b3937bb`.

## Full-envelope source step approach — 2026-11-14 14:43 UTC

**VERIFIED implementation:** source 0.42.30 connects the ordinary driver's
actual stopped step handoff to a separately sealed approach plan. It checks an
expanded actual cap, tries a direct transfer, and falls back to a checked
continuous approach plus explicit step when endpoint-selected faces cannot
cover the direct transfer. It checks the exit for the full supplied motion
reach. Exact rational polygon subtraction proves the union covers the complete
movement footprint; overlapping cells cannot conceal a gap. Every added cell
retains terrain/static, original BSP and full native-zero checks. It refuses an
unsupported following riser instead of shortening the maximum actual hold.

The driver prepares geometry outside the stop lock and rechecks its reference,
committed floor, hint, owner scope and freshness before returning. The immutable
hint map is bound to the issued boundary. Square-cap widening accounts for
diagonal projected width; original proposals are independently rechecked.
These two improvements followed concrete review findings, with regression
checks. No returned plan commits a floor, authorizes a key or claims actual
Forward auto-step capability.

Point-support queries use only the sealed plan's selected source patches and
revalidate their geometry. Selection uses XY geometry before any raw-Z check.
At a shared riser edge both possible heights remain; even two heights fitting
the same residual are not reduced to a nearest-height guess. A point support
is explicitly not a complete body cap or an observed grounded state.

**VERIFIED focused checks:** all 25 changed-feature cases pass across final
focused runs: compound fallback, full-envelope exit/corner/hazard rejection,
small coverage gaps, ambiguous risers, changed support geometry, diagonal cap
widening, immutable hint binding and OFF during preparation. An initial combined
run had 72 passes and three early timing refusals in existing OS-pipe cases.
Those three pass in the focused retry. A simultaneous Devbox sample showed
load ~115 on 48 CPUs and 0.7% idle. No freshness, DOWN, hold or release limit was
relaxed. Fixture issues (out-of-bounds synthetic caps, duplicate keyword options
and a nonintersecting synthetic seed) were corrected before passing checks.

**VERIFIED copied-data probe:** all seven retained steps were tried from
synthetic positions 0.25 and 1 unit before their planned departures, with
explicit unmeasured reach/uncertainty hypotheses. Twelve of fourteen cases pass
full approach/transfer/exit coverage; guide operation 1023 at setback 1 requires
the compound fallback. Both operation 1027 starts refuse the independent
unique-floor proposal because the point is missing/layered; no nearest layer
was substituted. A real continuation must retain its actual preceding floor.
Final repeat pinned all package and probe code; 5.06s, report
`nav-candidates/crushbone-step-approaches-0.42.30-final.json`, SHA
`3e072e934f9ad4acf8e0698cd7db892dd4acb5ceb209478dfeb092060109c731`.
Initial pre-diagonal-fix report SHA
`556f899c9220b499ce8278a27efcb98e5647f5df9af7b37d1f8e29dcedac1aca`.
Neither report represents a live position, movement, landing or accepted camp.

**VERIFIED runtime data dependency:** exported the 1,053-operation/seven-step
Slave Mines guide from the retained hash-pinned recipe and copied annotation.
The private canonical file is 116,296 bytes, SHA
`88aecac52585363add569d3f66ed9ba19921725e81e3a1626e96c50cfdc847e7`, at
`owner-route-data/crushbone-camps-20261114/crushbone-source-guide-v1.json` under
the approved local/Alienware store. It contains copied data and stays out of git.
A source loader checks its digest, client-data pins, guide hash and bounded
operations without requiring Devbox recipe files. Read-only SSH verification
matches the staged file; no prefix write, worker or game input occurred.

**VERIFIED private source publication:** commit `2f9207f` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.30/source`. All 79 selected
startup checks pass without skips; imports, CLI, copied-data pins and private
guide validation pass. No worker/device/game input or install modification.
Archive SHA `8f108fb0620b7deba3377c67768ce01c90dd11206feceb2a6f99018fde35dcf3`;
startup SHA `523d45be9a53193765cb783840b33be3f034a2e47bedd9e6ac6351e4842f260c`;
test output SHA `ebbaed227f7118846ba56b9b037f4d412ab23c336cbb14c5b05ef9f894cc462c`.

**Remaining:** typed fresh transition observations, continued pulses while
astride a riser, bounded settling and actual landing-cap acknowledgment, then
the owner runtime using its existing sender, input observer and log lease.
The new source plan is not executable by the current owner launcher. Owner
movement 0.39.20/assist 0.39.13 and passed G0 are unchanged; no new owner test.
Current metrics unknown; no accepted real 1–20 route, automated XP or fresh
hands-off 1–50 run.

## Source-only walking and stopped acknowledgment — 2026-11-14 14:33 UTC

**VERIFIED implementation:** source 0.42.29 uses a distinct source-floor observer,
ledger, supervised policy and sender. It never invents a baked mesh projection.
The original owner/log/zone/height calibration remains bound to each issued
reading. The ledger checks complete terrain/static/region evidence on the full
maximum-hold footprint outside the stop lock, then stages one measured control
through the retained watchdog and sender. Original file/source/device identities,
focus, physical input, finite budgets and measurement-only scope remain required.
Assist, full-auto and off cannot use this measurement path.

Release receipts do not advance floor or pose. Two new consecutive stopped
replies must match the exact provisional source branch; the actual endpoint cap
is rechecked and the same raw reply is rebound without renewing its timestamp.
Only then is the cap/pose committed. Invalid height, replay, stale position,
changed file/source, owner activity, focus loss or cancellation leaves the old
floor and stops. The ordinary driver aims through walking cells using retained
measured motion, with no backward movement or speculative jumps. Explicit
height steps produce an early planning handoff containing the actual reference,
cap proof and unconsumed approach cells; the driver does not skip that approach
or adopt a conditional landing. Full movement bounds remain unchanged.

**VERIFIED focused checks:** 55 pass across source motion, walk driver, itinerary
and current-log wrapper. Two existing baked-sender compatibility checks pass;
the new source pipe test also passes with explicit forward DOWN/SYN/UP/SYN event
assertions. Watchdog tests use actual OS pipes and synthetic scenes/positions;
the repeated route uses synthetic receipts and stopped replies. No game input.
Review found a receipt-sealing cancellation resurrection and a final-clock scope
change escaping observation validation. Ten regression cases failed before the
fix; all eleven publication/scope cases pass afterward. Fixture errors in the
initial regression hooks and synthetic riser layout were corrected; timing and
hold limits were not relaxed. The new view/pose identity cases also pass.

**OBSERVED development constraint:** an ordinary maximum-hold footprint can
reach a riser before the center reaches its planned departure cap. The driver
therefore hands off early without authorizing motion. A helper's no-write copied
geometry probe reported that retained step 989 accepts a departure 0.25 unit
back but refuses 1 unit back (`step_support_partition_failed`); step 994 accepts
0.25/1/2 units back but refuses 4 (`step_lift_bound_exceeded`). These helper
observations are not retained acceptance artifacts or client traversal proof.
A future executor must handle a checked compound approach where direct rebasing
fails, and cover the entire unchanged motion envelope across the transition.

**VERIFIED private source publication:** commit `06b1cbd` is staged on Alienware
at `~/.local/share/eql-automation/owner-tools/0.42.29/source`. All 57 selected
startup checks pass without skips; imports, CLI startup and copied data pins
match. No worker, device, game input, character action or prefix write.
Archive SHA `7431b4d8b57a981aa5add5515f4b42a0f69d66bbdbafab4bba7aa1a952688a8d`;
startup SHA `d7293b0ba4d55a9a2c3976c22f8c38b7c2da63a492cc263aa9c8a1ab05cfca7d`;
test output SHA `f4a63f7803be81ee561372b16c1b680e1e8595798617acfdf53d969dd502460e`.

**Remaining:** conditional step movement and landing acknowledgment, plus the
owner-runtime connection. Source core development does not enable the owner
1–20 autopilot. Movement preview 0.39.20 and assist 0.39.13 remain current;
G0 passed, no repeat. Current level, XP/hour, deaths and camp unknown. No
accepted camp route, automated XP or fresh-character 1–50 run.

## Mixed source-floor camp itinerary — 2026-11-14 14:14 UTC

**VERIFIED implementation:** source 0.42.28 represents walking and height steps
separately. Retained routes supply only XY/step hints; their old floor seeds,
proofs and acceptance flags do not become current state. Planning forks the
supplied floor, checks a bounded nearby guide connector, rebuilds terrain/static
and native-zero body evidence on every cell, and retains the original BSP
results. Every step rechecks the departure cap, riser, landing and all three
body phases. Conditional landings stay on the planning branch. The final
connector reaches the exact copied annotation, choosing its layer through
continuity rather than map-label Z. Results are sealed bytes and require fresh
observations and per-move checks before any future execution.

`plan_current_source_itinerary` connects this builder to the existing fresh-log
current-start producer, retains its initial source prefix and validates the
owner/log/zone and copied views during planning. Its distinct result type has
`source_execution_wired=False`; the baked route sender cannot consume it.
No assist, movement controls, game installation or character state changed.

**VERIFIED focused checks:** 54 pass, including walk/up-step/walk/down-step/exact
destination composition, a shifted start, same-XY wrong-floor refusal, transfer
hazards, cancellation, expiry, changed live prefix, exact-goal refusal and the
actual log-reader planning wrapper. A code review identified that native refusal
on the first connector discarded other nearby entries. A reproduced test now
passes after typed geometry refusal discards that candidate's cells and tries
the next entry; cancellation/context errors still abort. Two test-fixture errors
(duplicate keyword and wrong synthetic seed triangle) were corrected before the
passing final run. These checks are simulated; no device or game input is used.

**VERIFIED initial copied-data run:** retained 1,053 operations (1,046 ordinary
cells and 7 steps) were extracted with exact footprint comparisons. From the
explicitly synthetic shifted start `(274,-424)`, rebuilding plus connectors
produced 1,058 walking cells and 7 step transfers to exact annotation `(426,74)`
on source floor Z -17. The supplied initial floor stayed unchanged. Runtime
138.15s; report `nav-candidates/crushbone-source-itinerary-0.42.28.json`, SHA
`85d968a2ca9469999130b8e467872247718de86361e5cb55d19687dae83aaa99`.
This initial run preceded the alternative-connector fix and guide-snapshot
optimization. **VERIFIED final repeat:** the same shifted start, 1,058 walking
cells, 7 steps and exact goal pass in 84.25s. All package implementation hashes
and the probe code were pinned before and after the run. Final report
`nav-candidates/crushbone-source-itinerary-0.42.28-final.json`, SHA
`09c4cf3d6e69245249f8df9ef66a8f1914c7fc5038bb3dd8b5b1c01dee98bb28`.

**VERIFIED private source publication:** commit `e28f5f7` staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.28/source`. All 54 focused startup
checks pass there without skips; imports, CLI startup and copied data pins pass.
Archive SHA `c8d4f2414948311f6d3cfdc77815272a8c6b4fa8b21e75e869039a68340e51e0`;
startup SHA `408b4dbfa81e9687ba4f58e4b5756061465844f660045200dc928f17965c009a`;
test output SHA `08cfdbe16a64414eb314f9ec2efaf79a2ccdde836b272283bead8d55cb99dbe7`.
No worker/device, game input, character action or prefix write. The full copied
itinerary run was on Devbox; it was not repeated on the owner's laptop.

**Remaining:** source-only stopped observations, receipt acknowledgment and
conditional step landing must be connected to the owner movement runtime.
Seven source transfers are not verified client auto-steps. Current level,
XP/hour, deaths and camp are unknown; no accepted 1–20/1–50 run or automated XP.
Owner preview 0.39.20 and assist 0.39.13 stay current. G0 passed; no repeat needed.

## Native region evidence through supervised movement — 2026-11-14 14:03 UTC

**VERIFIED implementation:** source 0.42.27 carries the explicit Crushbone
native-zero policy through each maximum-hold forward and pivot footprint.
Terrain/static checks and the original BSP result remain intact. Native
classification runs during stopped precomputation. Cache seals retain original
evidence identity; exact issued records and their sealed terrain/static/BSP
contents are checked at staging, authorization and after callbacks. Replacement
policy/classifier/evidence/record, nonzero flags and stale observations refuse.
The default external-guard path and zone crossings cannot consume this policy;
assist/full-auto cannot use the measurement path. Timing limits are unchanged.

The owner local-trial loader now supports current zone 58, verifies installed
`eqgame.exe`, `EQGraphics.dll`, Crushbone archives and the catalog read-only,
and retains their device/inode/size/mtime/ctime identities. File or owner-session
changes stop the job. This separate installed-file record does not relabel
copied geometry as live verified and does not claim loaded-memory verification.
The owner continuation carries the exact binding through calibration, fresh
planning/height and supervised movement. No client/prefix writes are made.

**VERIFIED focused checks:** the combined run passed 146 cases; one descriptor
reuse fixture stopped before DOWN and therefore did not reach its intended
assertion. Its isolated retry passes. No deadline was relaxed. Coverage includes
native forward/pivot records, missing/nonzero/incomplete regions, changed seals,
policy and classifier replacement, slow classification, mode refusal, installed
binary replacement, actual pipe movement and cancellation during DOWN.
Four actual owner-wrapper checks pass: the new full native local-trial flow,
binary change before calibration, the old local trial and complete GFay crossing.
All client feedback is synthetic and input goes only to OS pipes.

**VERIFIED copied-client movement preparation:** both forward and pivot pass
native metadata checks at the retained historical entrance with radius 1.2 /
height 6 hypotheses; original BSP results remain false. The complete fresh
planning/height/precompute/ticket flow stages a forward move without sending
input or committing its floor. Report
`nav-candidates/crushbone-native-moves-0.42.27.json` SHA
`968b8a8c3aacce449899dff143b824dcebe720672b904f9fed7e59c5f60cebd7`.
This uses a synthetic reader/clock and is not a current character observation.

**Owner preview 0.39.20:** built from retained 0.39.12 through the existing
patch chain, current package and a UI text update for the existing short-trial
button. All 183 packaged manifest files verify and Python sources parse.
Manifest SHA `bc0d92e5dc1548548360d2b7ea6c2f5b120899b2d21e0d15c60aa856424e39b1`.
HOWTO documents GFay/Crushbone short movement, the existing travel actions,
manual combat and stop controls. No new G0 check is needed.

**VERIFIED owner publication:** preview 0.39.20 is staged on Alienware. The
manifest, offscreen GUI and both GFay/Crushbone copied loaders pass. Installed
client `fe41a8db...`, engine `4f5f18ee...`, Crushbone archives and catalog match
the model read-only. The exact file records are in the private startup JSON.
Archive SHA `107a961f9b2d62a849b5be1a7d8def2ce350b047a700be26cf30a396c2eda5a2`;
startup SHA `11d9780b843319980fd7a61c775862935836b86864d125faaf28ad8f18c4c361`.
No worker/device, game input, character action or prefix modification occurred.
The coordinator received the concrete owner launch/test step; no acknowledgement
is needed to continue development. Live traversal remains unverified.

**VERIFIED source publication:** commit `b401d14` staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.27/source`. All 30 selected startup
checks pass without skips, including the complete native owner trial, installed
file-change stop and old crossing. The copied entrance comparison also passes
forward/pivot precomputation and exact forward ticket preparation without input.
Source archive SHA `96d280175a79c62d07f920a92edd3178f8dd2a03a18c3b3c469b564dc7546703`;
source startup SHA `cdb3dfd06a408dee295df3b04bdaf93e9bc1b249cc0c440605f78352fd1dbf15`;
remote copied-move report SHA `dbb9b81d64af20b95f31a43d4491b2e66f2b9b7d4a656c3e245aab99ecb3832d`.

**Next:** source-step execution and fresh Crushbone camp routing, using owner
movement feedback when available. Seven source transfers still need execution
support; destination planning intentionally still refuses the native policy.
No actual crossing/camp traversal, automated XP, accepted 1–20 or fresh hands-off
1–50 run. Current level, XP/hour, deaths and camp unknown. Assist 0.39.13 remains.

## Explicit native-zero planning and fresh height — 2026-11-14 13:54 UTC

**VERIFIED implementation:** source 0.42.26 adds a separate typed Crushbone
planning policy. The default loader and v1 planning behavior remain unchanged.
Opt-in v2 plans retain the original BSP result; only a passing result or exact
`missing_bsp_child` is eligible. Terrain and static geometry still must pass.
Every selected floor patch needs complete, nonempty native metadata with full
integer flags exactly zero. Water, mixed flags, high-bit transitions, empty
pieces and unresolved classification refuse. The policy pins the native
classifier, source/mesh/static/BSP inventories and copied executable model.
Installed binary matching and actual movement remain unverified.

The complete nested policy/classification record is sealed as canonical bytes.
Fresh height requires this exact evidence, the initial floor chain, source,
owner/log/zone identities and newer stopped samples. Snapshot checks include the
policy and classifier. A returned dictionary cannot mutate the sealed record.
Default/assist/full-auto height behavior remains unchanged; native plans are
explicitly refused by destination planning and the owner movement driver until
per-move authorization is connected. Nothing in this increment sends input.

**VERIFIED focused checks:** 145 pass across native policy, current planning,
floor bootstrap, destination planning, copied-data loader and observed height.
A new delayed final native-validation test reproduced a stale-sample bug;
freshness now includes that validation time, and the regression passes.
Ten actual owner-wrapper checks also pass with OS-pipe input and synthetic game
feedback, including local arrival, cancellation and complete expected-zone
crossing. These checks send no input to EverQuest.

**VERIFIED copied-data comparison:** `tools/probe_crushbone_start.py` uses an
explicitly synthetic log and clock, supplied coordinates and body hypotheses.
At retained historical package XY `(274.06,-424.04)`, radius 1.2, height 6 and
heading 0, the default path retains `missing_bsp_child`. Explicit native
planning produces a conditional initial plan and a fresh synthetic height
correspondence, retaining full terrain/static evidence and native flags `[0]`.
These are not the owner's current coordinates or actual motion observations.
Final report `nav-candidates/crushbone-native-start-0.42.26-final.json` SHA
`459978e5a09d1cfd7ee53dfe97c34743793f407afefb922c8d1c9915082f9e7c`.

**VERIFIED private startup:** source commit `502fe13` is staged on Alienware
`~/.local/share/eql-automation/owner-tools/0.42.26/source`. All 102 selected
checks pass without skips, including the actual owner local/crossing wrappers
with OS pipes and synthetic feedback. The copied native-start comparison also
passes on Alienware; the default path refuses and opt-in planning/height pass.
Archive SHA `79ff85be663aadfef55e46d146a2bfa13c629b40e2f8c33fe7dbe56afdd1b8f8`;
startup SHA `f899357e3e4a6f1bacdd5b05cd935c5897cc97fe6056c3b5f8b237285002d480`;
native-start report SHA `1ca6ad5fd50bbd0f01ccfa9002ce8c2f4b1d0745ca859fe4952d31d34b49362f`.
No worker, device, game input, client launch or installed-prefix modification.

**Next:** propagate the explicit model into per-move preparation/cache records
and supervised authorization, checking installed binary identity before any
owner use; then source-step execution and fresh camp routing. Owner crossing
0.39.19 and existing-bot assist 0.39.13 stay current. G0 passed. Current level,
XP/hour, deaths and camp unknown. No live crossing/camp acceptance, automated
XP, accepted 1–20 or fresh hands-off 1–50 run.

## Native region enclosure and complete Crushbone replay — 2026-11-14 13:46 UTC

**VERIFIED implementation:** source 0.42.25 composes the audited native
`ClientBspTreeView` and last-record-wins `ClientRegionMap` into a separate
`ClientBspClassificationView`. Missing children and untyped regions retain
separate origins and fallback flags 0. Typed labels retain the full DWORD,
record/fragment identity and transition metadata; a low byte 0 does not remove
TP/high-bit flags. Cycles, budgets, unsupported arithmetic and the null-root
special return remain unresolved. No `candidate`/dry-space claim is added.

Complete body enclosures use exact rational nearest-even binary32 rounding in
the audited product/add order. Each node receives the original AABB; no exact
mathematical plane clips away a possible native branch. Both subnormal input
and result flush choices are enclosed. RN and masked SIMD exceptions/no handler
intervention remain assumptions; the native bounds gate and alternate-volume
path are not modeled. Complete classification is not collision clearance.
Separate adapters bind complete body and lift/transfer/settle classifications
to freshly rechecked terrain/static and source-step proofs. The copied Crushbone
loader pins this native inventory separately from the legacy BSP inventory.
Final classifier SHA `99197a077bfd709305eeececf77602f5ff3283006cad14da948d960c11b08b0a`.

**VERIFIED arithmetic correction:** a focused test reproduced omission of FTZ
zero when an exact tiny product rounds to minimum-normal under gradual
underflow. The enclosure now includes the pre-round tiny alternative as well.
The independent arithmetic check and root source check used the
[Intel SDM, volume 1 §§4.9.1.5 and 11.5.2.5](https://cdrdv2-public.intel.com/843827/253665-sdm-vol-1-dec-24.pdf).
No client MXCSR state was read or claimed. The first replay and entrance probe
used the earlier enclosure and are superseded by the final replay below.

**VERIFIED final focused checks:** 84 pass, including exact midpoint parity,
float64 double-rounding counterexample, underflow/normal carry, FTZ zero, native
operation ordering, full transition flags, label precedence, unresolved model
states, changed geometry and real copied Crushbone loading.

**VERIFIED full copied-route replay:**
`nav-candidates/crushbone-native-all-phases-0.42.25-ftz.json` SHA
`ce932ff516a5053e2b41bab44d7ba1c3ee77b2e1918b8d8cb4a8f02a2aed9526`.
All **1,046 ordinary cells and seven step transfers** were replayed without
searching for a new route. Every saved terrain proof and transition digest was
asserted; static occupancy was rechecked. Native metadata is complete for every
body/phase and its full possible flag set is exactly `[0]`, with no unresolved
classification. Runtime 97.18 seconds on the devbox. The legacy results are
preserved: 926 ordinary missing-child refusals and all seven step BSP refusals;
`current_path_bsp_candidate` remains false. Route and real-client acceptance
remain false. Final floor proof is
`0a49c84e8be0beafc822fda6dc77cc74bf58dd46092cb2ca0f6d15df0103f521`.
This resolves the copied metadata question; it does not establish live step
capability, body dimensions, actor query offsets, dynamic obstacles or movement.

For traceability, the superseded entrance probe SHA is
`beba9000cd092c75a191cd4b82d5f2ea3036e4d467281be42c7f6dab6f7bfcae` and the
pre-correction full replay SHA is
`a5c55cd931ed4ddc1feedecdf02ec60a789513a2bdd3752980d44b80996a4420`.
They were never used to enable game input.

**VERIFIED private startup:** source commit `30fbca6` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.25/source`. All 84 selected
checks pass there with no skips. Copied camp report and native inventory match.
Archive SHA `a33d5e02e1dcdcf09c465078e8a8921d599aac803247117418996033f97ad5c2`;
startup SHA `4d781d09699610753d2fbcf41a02b27e03669c43e495c2b2ad53201346b0507c`;
test-output SHA `a8948d646826606aefb6b2eb88ebd756e78ffa15197af6bf1094e521fa430196`.
No worker/device, game input, client launch or prefix modification occurred.
Owner's latest reply confirms the G0 visible stop; its passed result is retained.

**Next:** explicit Crushbone measurement policy accepting only complete full
flags 0 metadata alongside unchanged terrain/static proofs, preserving the old
BSP result and refusing other legacy hazards. Bind policy/classifier and nested
evidence hashes into current planning, fresh height, each movement preparation
and supervised authorization. Before owner movement uses this model, verify the
installed eqgame/EQGraphics binary hashes too. Keep ordinary/default/full-auto behavior and
exact zone-line crossing permissions separate. The seven source steps still
need actual driver execution support. Owner crossing 0.39.19 and assist 0.39.13
remain unchanged; G0 passed. Current level, XP/hour, deaths/camp unknown; no live
route, automated XP, accepted 1–20 or fresh hands-off 1–50 run.

## Explicit floor proposal and bound height bootstrap — 2026-11-14 13:33 UTC

**VERIFIED implementation:** source0.42.24 adds an explicit
`propose_unique_diffuse_floor` query. Every Diffuse intersection counts; the
query refuses multiple levels, nonzero flags and unknown materials. Only
flag-zero Boundary sheets strictly above the sole floor plus the explicit body
height and existing .01 margin can be classified overhead. All intersections
remain recorded and all source faces remain in footprint occupancy. The
original strict `source_floor_at` default is unchanged. Current-start planning
must opt in, records the proposal in its seed, and still requires complete
terrain, static-object and BSP checks.

`measure_current_height(..., floor_plan=plan)` can now consume only the exact
plan's already checked initial floor. It checks source/plan hashes, initial
terrain/static/BSP proofs, seed owner/log/zone identity, body hypothesis and a
newer stopped pair. Both local and destination-wrapped plans work. It snapshots
the floor chain and observer identities around callbacks; `floor_at` retains
the exact checked-cell limit. Evidence records floor and seed hashes. The owner
wrapper also requires the active plan and collector to remain identical. No
saved position or label Z selects a supporting floor; measurement-only and
unverified body/live flags remain unchanged.

**VERIFIED tests:** 129 focused geometry/bootstrap/copy checks pass. Tests
include contact/unknown-material/multilevel refusal, sloping Boundary occupancy
inside the swept footprint, static/water/missing-child refusal, fresh direct and
destination height, changed seed/source/body/plan, out-of-cell coordinates and
callback changes. Two actual owner-wrapper OS-pipe tests pass for local arrival
and complete expected-zone crossing, with synthetic game feedback. A new active
plan replacement case initially stopped during calibration (`Pulse cancelled
before key down`) before reaching its intended assertion; focused retry passes.
No timing limit was relaxed. A separate final-binding-delay case **reproduced a
failure**: stale time sampled before callback work could allow expired height.
Freshness is now evaluated after callbacks; it passes in the final129 checks.

**VERIFIED copied-data diagnostic:** with explicit six-unit body-height
hypothesis, Trainer Hill and North Wall produce point seed proposals. Mines and
Throne remain layered and Entrance has no support. None is an accepted camp.
`nav-candidates/crushbone-floor-seeds-0.42.24.json` SHA
`14c561a20ca70de087008c8dad27a11560dec831c8362a4401123f903a8b458d`.
A synthetic-reader comparison at the retained historical entrance XY
`(274.06,-424.04)` changes from point material refusal to
`Current-start BSP refused: missing_bsp_child`: the initial terrain/static
checks now pass with the same radius1.2/height6 hypotheses. This is not a current
character position or live traversal. Report
`nav-candidates/crushbone-start-bootstrap-0.42.24.json` SHA
`50a1bc047f5867cea3824bc3a997ca49678816cfeebb6b4e93246f27ed05b411`.

**VERIFIED final private startup:** commit
`21fcc7660f1841d6df9f9f2a57312ed530e019ab` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.24/source`. All 53 selected
checks pass without skips: copied-data loader, floor bootstrap suite, actual
owner local route, crossing and active-plan replacement stop. This includes the
final freshness fix. The copied floor-proposal report matches the devbox.
Archive SHA `4d827dd8396fba9982970d52e2c7ddc58f0a6c60f6df6888b1f6f573f32dae94`;
startup SHA `4a6efb36ff5b23edff2a64439b8a8a10fca9aed2db9c75698c552711e71f118d`;
test-output SHA `c388125efa5c40532147ffadd6bae387bca2d5607d10bb515166a044dfd37554`.
No worker/device/game input, client launch or installed-prefix modification.

**Next:** compose `ClientBspTreeView` and `ClientRegionMap` into a separate native
classification view. Native classification uses binary32 operation order,
nonzero-region early termination and last-record-wins labels; the old exact
BSP volume/union-label check does not model those semantics. Preserve origin
(missing child versus untyped region), transition flags and classification
uncertainty; do not convert an unresolved query to class0 or infer solid
clearance from metadata. Terrain/static collision checks remain independent.
Owner crossing0.39.19 acceptance is still pending; source integration does not
change its installed bundle. Assist0.39.13 and passed G0 remain. Current level,
XP/hour, deaths and camp unknown; no accepted 1–20 route, automated XP or fresh
hands-off1–50 run.

## Crushbone camp inputs and native region consumers — 2026-11-14 13:25 UTC

**VERIFIED implementation:** source 0.42.23 adds a reusable, pinned Crushbone
loader for complete terrain/detail/static/BSP views and five copied map camp
annotations. Inputs are checked before and after parsing; geometry arrays are
read-only. The private store is
`~/.local/share/eql-automation/owner-route-data/crushbone-camps-20261114`.
`tools/prepare_crushbone_assets.py` assembles only retained approved copies;
`tools/inspect_crushbone_camps.py` prints exact annotation intersections without
client access. No historical position or label Z becomes a current floor seed.
`source_hits_at()` exposes all terrain intersections/materials while preserving
the strict existing `source_floor_at()` decision and all-height footprint query.

**VERIFIED focused checks:** 43 pass, including the actual retained-data loader,
changed/symlinked input refusal, point layers, immutable views and current-start
regressions. The loader has 21,834 terrain faces, 9,576 static faces and 178
placements. Copied source archives remain pinned at `a2591482...` and
`d80521fd...`; full hashes are in `crushbone_assets.py` and the private report.
Report `nav-candidates/crushbone-camp-annotations-0.42.23.json` SHA
`7b43a48bd1b6a8307e71bc97fb3e2956086f23e98d8e7484ceeb60f8409e27bc`:

- Entrance annotation package XY `(150,-520)` has no terrain intersections.
- Slave Mines `(426,74)` has Diffuse Z -17, 0 and 26.0212337, plus Boundary623.75.
- Trainer Hill `(119,-212)` has Diffuse80.1933236 plus Boundary623.75.
- North Wall `(-95,-78)` has Diffuse0 plus Boundary623.75.
- Throne Room `(106,154)` has Diffuse16,46.96875,54.96875 plus Boundary624.75.

These are copied annotations, not verified mob levels or usable destinations.
A separate six-point read-only inspection finds historical entrance
`(274.06,-424.04)` has Diffuse0 plus Boundary624.75. That is not a current
character position. Multiple Diffuse layers remain ambiguous; distant Boundary
sheets explain the generic point-material refusal at the single-floor points.
No material or BSP refusal was waived in this release.

**VERIFIED static evidence, not execution:** a read-only helper using the
reverse-engineer-anything workflow found no available REA native provider
(Ghidra Java runtime unavailable), then used retained evidence plus bounded
objdump/PE byte spans. No environment change or game operation occurred.
The known fallback-0 query result flows through actor `+0xac` into
`0x140332920`, which stores its low byte at `+0xb6` (previous at `+0xb7`).
The clamp getter `0x140277010` tests that byte at `0x140277040`; class0 takes the
same below-5 branch as DR0. Movement consumer `0x1403388f0–0x140338d31` also
tests it at `0x140338b7a` before conditionally zeroing an input scalar used on
actor vectors. Upper sample `+0xa8` flows through `0x140338350` into byte`+0xb4`;
its old/new-medium switches cover classes5..10. Class0 skips new-medium cases,
while old-medium cleanup may still run.

**INFERRED scope:** missing-child and untyped-region metadata can be named
native default class0 for this exact fallback path. This is a classification
result, not solid collision clearance, universal dry volume, live actor state
or route acceptance. Scene predicates can skip classification updates.
Root independently rehashed both binaries and all five exact PE-mapped spans.
Private evidence `client-data/native-region-movement-20261114T1325Z.json` SHA
`3f171fbcd905adbfe2edcc2376dc61bd18b34cbd5ebcc3ab29efd6251056b081` retains full
file/span hashes. No movement policy changed from this static finding.

**VERIFIED private publication:** commit `1324841637894f3b7d05adc2c4130678a62dd99a`
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.42.23/source`.
The seven pinned data files are staged separately under the private data root.
All 43 focused checks pass there, with zero skips. The annotation report matches
the devbox byte-for-byte. Archive SHA
`d37f41c70c433fdcb71239e2285542a9bcd823e0d5999fe5711a23b69731317a`;
startup SHA `73c14d1f66b4aac5b90a911b9aa1e46ad9ce3b9011122b03660fa6b230d73c14`.
No worker/device/game input or installed-prefix modification occurred.

**Next:** an explicit unique-Diffuse floor proposal with overhead Boundary
checks and fresh height continuation; represent the observed native default
classification separately from terrain/static occupancy. Real crossing remains
owner-test gated. G0 passed; assist0.39.13 and crossing0.39.19 are unchanged.
Current level, XP/hour, deaths and camp remain unknown. No automated level gain,
accepted 1–20 route or completed fresh-character 1–50 run.

## Owner crossing action integration — 2026-11-14 13:18 UTC

**VERIFIED implementation:** source 0.42.22 adds a distinct owner crossing job,
preview 0.39.19's **Travel into Crushbone…** action. The original approach-only
job remains separate. The new loader binds copied GFay area 4, polygon 19256,
native region 2884 and `DRNTP00255000004_ZONE` to the manifest endpoint and the
unique catalog destination 58. It does not infer an arrival spawn or a server
trigger from map lines. The original installed archives/catalog are read only.

The same owner action retains motion measurement, then obtains separate plan,
height and initial-ground pairs. Initial movement observations are newer than
height calibration, never reused calibration samples. A provisional ledger,
one aggregate corridor policy and an exclusive arrival reader replace the
ordinary route driver for this job. Owner/settings/process/input/device checks
remain valid across zoning; source-only checks stay with source transactions.
The inherited rotation engine's normal stop-on-zone behavior is overridden only
for exact loading/expected-entry messages during this owned crossing. The
arrival controller still checks their order, freshness and destination.

The location executor uses the tested owner hotbutton, shared stop lock and
existing descriptor. Nested pumps check cancellation without consuming the
arrival reader. Known client loading blocks the location transaction. A loading
event during an active source hotbutton may stop this preview rather than
resume; it cannot authorize another key during known loading. Arrival uses a
new pair after the retained post-entry delay, then closes the lease and observer
and stops. No camp, combat, target selection or automatic restart is added.

**VERIFIED initial harness:** an actual retained owner engine plus OS-pipe
sender completed calibration, source planning, movement, inherited `read_log`
loading/entry dispatch and fresh destination positions, ending released and
stopped. Game feedback/geometry and input observations were synthetic. F9 during
movement, source and destination position requests also passed. A later combined
run had three early timing/refusal failures (watchdog arm, interrupted pulse and
expired stopped geometry) and one stale test expectation for label capitalization.
The expectation was corrected. A focused retry passed movement cancellation,
then stopped early on missing watchdog DOWN acknowledgment. Timing limits remain
unchanged.

**VERIFIED final source startup on Alienware:** all five selected checks pass
without skips: complete owner crossing, wrong-destination stop, no location DOWN
after known loading, original local-route completion and countdown-zone display.
They use synthetic game files/feedback and OS pipes, without a helper worker,
device or game input. This confirms the cases which devbox timing refusals had
prevented from reaching their intended assertions. It does not demonstrate a
real-client route or live timing margin.
Commit `b4415076f22d6a89363c389550cb1775db45f4c3` is staged at
Alienware `~/.local/share/eql-automation/owner-tools/0.42.22/source`.
Archive SHA `48368ce3cc80dd14c591b7a86bdb6463593c1ed55ab02da6cfbbce064ce124fb`;
startup SHA `c26a63d203e652d2e1e38dcee396687a90989bc6eb871d13092c502aed24250e`;
test-output SHA `02799ac6c9506d3e7ebf714322c622358a6274a45c8ebcca6c4cd1a490b3c8db`.

**VERIFIED owner preview publication:** 0.39.19 is staged at Alienware
`~/.local/share/eql-automation/owner-assist/0.39.19`. All 148 package modules
match source 0.42.22. Entry and source-manifest checks pass. Offscreen GUI
startup shows the new crossing button and the retained approach/short-route
buttons; `worker_started`, `game_input_sent` and `settings_saved` are false.
The new loader reads the installed archives/catalog, matches the copied pins,
loads the complete source geometry in 1.99 seconds and selects native polygon
19256 / region 2884 with manifest XY `(-51.0242595, 2618.9152375)`.
Loader identity is synthetic; this is not a live zone or traversal observation.
Launching without explicit `--measure-navigation` refuses. No device creation,
game launch/input, prefix modification or other session interruption occurred.
Preview archive SHA `ab4d1ef1f858584a10e170e7586d78188db05dd1f8e5aaf78555439cd022acb3`;
source-manifest SHA `27d84332e291b19351650585b9284ab2dae516015f8e0b859bc1176f0bd472b2`;
startup SHA `df8cc72be5d18e56c861e8f109d53578fbf32b248c7d9458d2ee7a26d2261c6d`.
HOWTO contains the exact launch command and separate action/stop controls.

**Remaining real-client gate:** owner-run current-map/hotbutton recognition and
actual route/crossing acceptance. Next build fresh Crushbone arrival geometry and
level-suitable camp execution. Current level, XP/hour, deaths and camp are
unknown; no accepted 1–20 route, automated XP or completed fresh 1–50 run.

## Repeated source moves and exclusive arrival corridor — 2026-11-14 13:10 UTC

**VERIFIED implementation:** source 0.42.21 adds `CrossingCorridorHandoff` and
`SupervisedCrossingCorridorPolicy`. One immutable declaration covers the dry
approach, pivots and the exact expected zone-line footprint. Movement slots and
maximum hold are reserved before DOWN, including the final loading pulse whose
source floor never commits. The existing destination ceilings apply only to
this explicit scope. Source and arrival deadlines are separate, bounded by one
outer horizon; the arrival subdeadline remains at most 120 seconds. Ordinary
route policies still refuse crossing scopes.

`ZoneArrivalHandoff` owns the only location-reader poll for both source pairs
and arrival boundaries. Its stopped-source collector borrows that poll, so a
loading event retires the source pair before an old-zone postcheck can consume
or hide it. Complete boundary batches remain ordered; loading followed by an
invalid event refuses. Completed source results are checked again for queued
loading before consumption. Reentry, competing polls, changes of owner/log/zone
and callback cancellation refuse.

The sender seals elapsed receipts after final UP within the original 0.3-second
bound. Fresh replies are observed against that exact provisional floor as each
arrives; a complete stopped pair resolves it before another pulse. Loading
releases controls and cancels the pending source transaction. A footprint must
overlap the exact pinned native line to correlate loading; dry-pivot loading
refuses. Destination arrival uses new positions and does not reuse source pose,
heading or floor. An unsupported or very late inter-pulse loading event can
still stop the corridor rather than automatically continuing; recovery is not
implemented by this primitive.

**VERIFIED focused checks:** the final corridor/one-pulse batch passes 32 tests.
These include real watchdog DOWN/UP writes to OS pipes, two repeated source
resolutions followed by a third loading pulse and fresh destination positions,
dry pivots, one shared budget, unresolved-receipt exclusion and cancellation.
Game positions, log messages and scene observations are synthetic. The preceding
combined batch had 220 passes and two interrupted pipe cases; both are included
in the passing final focused run. A devbox sample showed load averages around
165, 204 runnable processes and zero idle CPU. This supports scheduling pressure
as a possible cause, not a measured diagnosis of each interruption. No deadlines
or freshness checks were relaxed.

Review found that loading followed by a malformed position could return a
successful handoff even though arrival had stopped. A failing test reproduced
it; both crossing wrappers now reject stopped arrival. A second reproduced
failure delayed the final scope callback beyond receipt expiry. The final clock
read now follows scope callbacks, then callback-free binding/cancellation checks
precede phase publication.

**Remaining real-client gate:** the owner travel runtime/GUI still uses ordinary
approach routing. Connect this corridor to its existing stop lock, tested location
key and single reader/input observer without running the old route driver in
parallel. Then establish fresh Crushbone geometry and suitable camps. Owner
travel 0.39.18 and assist 0.39.13 are unchanged. G0 is passed and needs no repeat.
No live login, character input/mutation, client/prefix write or new owner test
occurred. Current level, XP/hour, deaths and camp unknown; no real crossing,
accepted 1–20 route, automated XP or completed fresh 1–50 run.

**VERIFIED private publication:** commit
`d8437e2fb2d1ed4a5bca3dd7fb2c3ba7be07e386` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.21/source`. All five selected
startup checks pass there without skips: two source moves then loading/arrival,
loading during a source pair, malformed-position refusal and both late callback
cases. Movement receipts use OS pipes; game feedback is synthetic. No helper
worker/device, game input or install modification occurred.
Archive SHA `479a4aeb7da59b3388ecc38787ef8d0d3a4fd2c12140881e6a4c534537bdc9bb`;
startup SHA `c4ba83663c78fded82bc578ca0f5c112eace463837223a9c0e7b9d3db777b31b`;
test-output SHA `41e9941d3911d35eb871f829825bc035598bef3109fbbc11ae008878e1ca0b7c`.

## Provisional source-floor receipt transaction — 2026-11-14 12:54 UTC

**VERIFIED implementation:** source 0.42.20 adds `ProvisionalRouteFloorCommit`
as a distinct ledger subclass. Ordinary `RouteFloorCommit` behavior is unchanged.
The new ledger seals one exact elapsed watchdog receipt within the existing
UP+0.3-second limit, including key, duration, stage/DOWN order, maximum hold and
unchanged controller/floor bindings. Sealing changes neither committed source
floor nor predicted pose. Interrupted receipts cannot resolve as source moves.
Ordinary immediate commit and reuse as another movement ticket refuse.

The immutable seal has a fixed expiry, at most ten seconds from UP. Its exact
pending fork can supply observations as each reply arrives, retaining the ground
observer's 0.5-second age limit. Resolution requires a fresh stopped source pair,
the same owner/reader/zone/line context supplied by the exclusive controller,
unchanged base/fork snapshots, exact source-floor support and the original
checked footprint. It integrates the release, accepts the pair, then publishes
the fork under the shared stop lock. Any failure halts the source runner and
discards pending state. No log consumer, movement, input authority or automatic
source-vs-loading decision is introduced by this class.

**VERIFIED focused checks:** 74 transaction cases pass, including actual watchdog
DOWN/UP writes to an OS pipe followed by explicitly synthetic elapsed time and
positions. They cover stale/interrupted/wrong/excessive receipts, source changes,
loading cancellation, assist/mode/generation changes, expiry, unsupported or
moving positions, one-use semantics and stops inside callbacks. An initial test
fixture incorrectly moved its clock backwards while constructing an outside-
footprint observation; correcting the fixture exercises the intended refusal.

Read-only review identified a final-clock race: mode, generation or source context
could change after the last snapshot without clearing the ledger. All three
cases were reproduced as failing tests. Rechecking context after that clock
read prevents publication; callback-free seal/pending/state checks precede the
final swap. The same check covers receipt sealing. Footprint containment now
uses the same convex hull normalization as staging, including clockwise input.
No existing timing limit was increased.

**Remaining runtime work:** the checked sender currently cancels the source fork
for a final crossing pulse; a corridor path must seal it before that cancellation.
Source-position collection and expected arrival must own one reader, processing
loading before any old-zone check. A corridor also needs one aggregate step/time/
hold budget rather than renewed one-pulse declarations. Then bind the owner
action and fresh destination geometry/camps. Owner preview 0.39.18 and assist
0.39.13 are unchanged; G0 remains passed. No new owner test, game login/input,
character mutation or client/prefix write occurred. Current level, XP/hour,
deaths and camp unknown; no accepted route, crossing, automated XP or 1–20/1–50.

**VERIFIED private publication:** commit
`c6b8e721524d83e785c14d9cbbce215962d0581e` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.20/source`. Startup uses the
pinned retained steering implementation, synthetic geometry/receipt/positions
and the actual new ledger: sealing preserves floor/pose, a delayed source pair
resolves, and seal reuse halts. No worker, device, input or install change occurs.
The final 35 provisional tests also pass after the last context rechecks.
Archive SHA `03689a47494db3f4862e5fc7103efedf0a23d2cb3a7e2b51441c66ec3112d183`;
startup SHA `80f339db761fbb1dd687c3c099da3c4245079139aad2af46931ca3904f3f100d`.

## Exact zone-line route and observation context — 2026-11-14 12:51 UTC

**VERIFIED implementation:** source 0.42.19 propagates the immutable expected
zone line into destination planning and ground observations. The producer keeps
the actual area 4 and exact raw XY; the consumer requires the same line hash
and source pins. Named transition polygons cannot be relabelled as area 63.
The movement geometry preparer requires matching observation and swept-footprint
contexts. Ordinary plans/observers retain dry-only defaults. The initial start
capsule is still dry-only: this does not support restarting inside the zone line.

The retained NavMesh search may use only the explicit area after complete
polygon inventory checks against the navigation/detail/ground views. Exact
source pins and native BSP labels are rechecked after callbacks and search.
Read-only review identified that the first implementation checked this context
only before search; a mutation of the expected region to water could leave a
stale planning record. The final implementation refuses that case, extra area
polygons and dry relabeling. Runtime collision checks remain mandatory.

**VERIFIED focused checks:** 72 zone-line/observation/destination/crossing cases
passed before the final inventory rechecks. The broader focused run passed 169
cases with one failing new fixture that attempted to mutate a tuple in place.
After correcting that fixture, all 21 destination cases pass, including changed
BSP labels, expanded area inventory and relabeling after search. No receipt,
position or movement deadline was relaxed.

**VERIFIED copied-client plan:** `tools/probe_destination_route.py` now accepts
`--tile-rounding --expected-crushbone-zone-line`. It resolves the pinned native
label `DRNTP00255000004_ZONE`, area 4, polygon 19256, region 2884, and uses only
the manifest point's XY. Endpoint Z comes from exact mesh detail support; the
manifest's vertical midpoint is not used as a floor. With explicit synthetic
start `(1780.12,-1802.22)` and heading `336.8889866616196`, the planner produces
200 segments / 5,029.060435635146 units in 6.609 seconds. The last point is
`(-51.02425949999999,2618.9152374999994,16.068756103515625)` in actual area 4.
The initial source-floor chain remains at index 1. Untraversed corridor body,
static, terrain and BSP checks remain required before each movement.

Retained private evidence:
`~/.local/share/eql-automation/nav-candidates/gfay-zone-corridor-0.42.19/`.
Probe SHA `8efea68b025c570f25a951e01ccd04ec0c34f6058730206c34fe98dd738eba24`;
plan SHA `b984dd6b2737a7d2cab98467ea804d0b88294bdf0105e7153a0259d586faf842`;
geometry SHA `aecfa6db0f4ac503d0638e20a9f942821eba1ceca9ba152b48e6085ee5bc4a17`.
The destination remains a guide hint until a real expected-zone arrival. This
does not establish server destination/spawn, current character position or
actual traversal. No game input, login or character mutation was performed.

**Remaining integration:** ordinary movement envelopes touch the zone line
before a final pulse necessarily reaches it. Continuing source-side pulses
therefore needs a receipt sealed while fresh, a stopped source/loading decision,
and either a fresh-position source-floor commit or discard on loading. The
existing 0.3-second receipt freshness requirement cannot simply be extended
through the 2.5-second loading observation. Source-position collection and
arrival must share one reader and inspect loading before source-zone checks.
Then carry the lease into fresh Crushbone geometry/camps. Owner preview 0.39.18,
assist 0.39.13 and passed G0 remain unchanged; no new G0 or owner test is requested.
Current level, XP/hour, deaths and camp unknown. Real 1–20/1–50 remain unaccepted.

**VERIFIED private publication:** commit
`259a468029849c1d324d76175ca714d75eb336bb` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.19/source`. Imports and synthetic
exact-area/raw-XY observation pass; ordinary context, area relabeling and missing
line hash refuse. No worker, device, game input or client/prefix change occurs.
Archive SHA `5b04df2d2d3da672ac70b438b215c6307a471f2696a53af8ee53bd019bd65b43`;
startup SHA `54f7852d40d21627b4cd8e03d402d6ac605b93009d15828ae19b535af94191b9`.

## Checked crossing pulse and arrival integration — 2026-11-14 12:39 UTC

**VERIFIED implementation:** source 0.42.18 adds `SupervisedCrossingPolicy`,
`CrossingPulseHandoff` and `run_checked_crossing_step`. The distinct declaration
binds the exact expected zone line and destination and permits at most one
forward pulse. It reuses the existing sender's descriptor pin, shared stop lock,
geometry ticket, watchdog and final-UP cleanup. Ordinary route entry rejects
this policy. Loading is observed before ordinary source-zone checks; source
movement ends immediately and the expected-arrival flow owns the exclusive
reader. The source floor fork and pose are never committed, even for a fully
elapsed pulse. Missing/late loading stops after a 2.5-second observation bound;
there is no retry from an old position. The destination needs a fresh planner.

The watchdog now preserves a validated interrupted child DOWN/UP receipt in a
`PulseInterrupted` exception. Ordinary callers still receive an error and cannot
commit a cancelled pulse. A child already finished at stop may have closed stdin;
the queued UP is still read and validated. The complete sender cleanup remains
mandatory. The receipt proves descriptor write timing, not client consumption.

`ExpectedArrivalLogVeto` accepts only exact loading/expected-entry text and keeps
scanning for every other existing hazard. This fixes a concrete integration
problem: ignoring an ordinary watcher's latched `zone_transition` would hide
attack/death/log-reset messages after it. The independent location reader still
enforces ordering, freshness and exact destination. The two non-replaying tails
start at the same identity/cursor but retain their own epoch counters, avoiding
a false mismatch when the source reader has already observed an earlier reset.

**VERIFIED focused runtime checks:** actual watchdog subprocesses write to OS
pipes only. The complete new sender/policy/controller path handles loading during
DOWN and delayed loading after an elapsed pulse, then two new destination
positions. No loading, late loading, wrong destination, incoming attack, owner/
policy cancellation, assist mode, lease revocation, release failure and loading
before DOWN all stop; no source floor commit or pose advance occurs. Arrival
checks cover hazards in the loading batch, after entry and during the stopped
pair. Position, input/focus observations, terrain and owner scope are synthetic.

232 focused regressions passed in 15.16 seconds before the final review fixes.
Read-only review found a policy-cancel+loading race, cancellation at final receipt
commit and a finished-child BrokenPipe receipt loss. The policy race was
reproduced as a failing test; fixes bind policy cancellation throughout arrival,
serialize final state changes under the shared stop lock, recheck after callbacks
and read queued UP after a closed child stdin. 68 crossing/arrival/watchdog
checks passed afterward (7.31 seconds), then 53 crossing/policy cases passed after
the final lock changes (5.69 seconds). No timing deadline was relaxed. A further
late-loading case checks the receipt time rather than accepting a late message
merely because it changed the phase; all 15 crossing tests pass on that final
change (4.11 seconds).

**VERIFIED private publication:** commit
`bf8e8ea601cdacf42e8b245113d70838586c78d7` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.18/source`. Imports, synthetic
loading→release→fresh destination pairing, hazard scanning across loading and
an actual watchdog interruption on an OS pipe pass. No engine worker, input
device, game input or install change occurs. The first startup attempt ran from
SSH's home directory and its `python -m` child could not import the staged
package; it failed without input. The retry verified every staged file against
the unchanged archive and ran from the source directory, as the helper launcher
does. No installed client or prefix was touched.
Archive SHA `f58abc80b9eb619b5a532215504f6ce8fdf639589e3065d1047cadc0ec4249d0`;
startup SHA `4e526c5e633e399e0e2cc0b1bd7050b7ed90fee749817fb57767b628f216d52f`.

**Remaining owner/runtime work:** the GUI travel action still ends at the
Crushbone approach. It must plan the checked launch-point approach, carry its
source-floor chain through the layered entrance and transfer its lease into the
new crossing controller without ordinary route cleanup revoking it. Fresh
Crushbone geometry/camp execution follows. Owner preview **0.39.18**, assist
**0.39.13** and passed G0 remain unchanged. No new owner test is requested by this
source update. Actual live map recognition, traversal, crossing, automated XP
and 1–20/1–50 completion are unverified. Current level, XP/hour, deaths and camp
remain unknown.

## Exact expected zone-line geometry — 2026-11-14 12:29 UTC

**VERIFIED implementation:** source 0.42.17 introduces immutable
`ExpectedZoneLine`, binding crossing identity, zone, mesh/archive/WLD/BSP and
manifest hashes, the exact native label, actual area and polygon/region IDs.
The source factory resolves effective native region labels, then checks the
conservative BSP classifications. Terrain and precision retries retain actual
area 4; only the named polygon can pass. BSP traversal retains the labelled
region in its result and continues checking every other branch. Water, unknown
labels, other transitions, missing children, source terrain and static collision
still refuse. The same permission enters route records and cache identity.
Ordinary `SupervisedRoutePolicy` rejects any crossing preparer; this update
creates no movement, sender or live crossing action. New area63↔4 precision
seam derivation remains unsupported and refuses; existing explicit retry paths
carry the permission without broadening seam derivation.

**VERIFIED copied source result:** `tools/probe_zone_line_geometry.py` uses the
pinned GFay manifest
`ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82`
and existing complete terrain/static/BSP loader. The exact label
`DRNTP00255000004_ZONE` maps to polygon **19256**, area **4**, native region
**2884** with only `zoneline` classification. At synthetic package XY
`(-51,2612)`, ordinary starting polygon 19254 has baked Z=16.068756103515625.
The probe explicitly hypothesizes source face `(1707,28)`, floor Z=15.84375,
heading 0, body height 6, radius 1.2 and the recorded motion envelope. It does
not infer a current character position or select a live floor from nearest Z.

The earlier all-layer point query correctly refused: source surfaces include
the floor, ceiling at Z=57.84375 and Boundary surface near Z=801.8125. The
conditional chain keeps all layers in occupancy. Ceiling clearance is 42 units;
the forward footprint crosses into source faces `(1708,6)` and `(1708,7)` and
native region 2884. Terrain/static/BSP pass; permission-off returns
`Terrain: forbidden_area_or_other_component`. The original floor chain stays
at index 1; the uncommitted fork reaches 2. No precision correction is needed.
Forward geometry took 0.080632 seconds in this run, outside any live sender.
No timing deadline was changed. Probe artifact:
`~/.local/share/eql-automation/nav-candidates/gfay-zone-line-0.42.17/probe.json`,
SHA `cb0094eb72189b3f4e7172f2eb7993dc01bbb2742791133f88c1bccef311a322`.
The expected destination remains a guide hint until the live arrival log;
no server destination/spawn acceptance follows from this offline result.

**VERIFIED focused checks:** 205 pass across exact-label/source/polygon binding,
default refusal, other labels/missing children, static collisions, precision
retry propagation, route-cache invalidation and ordinary-policy refusal.
An inventory timing probe on the real 38,587-polygon array measured 8.51 ms
per Python enumeration. The complete recheck now uses the existing NumPy
array operation (0.0881 ms in a separate probe), preserving mutation detection
and the original deadlines. 93 focused route/zone-line/policy checks pass after
that change. Read-only review found no concrete correctness defect and recorded
the unsupported new zone-line precision-seam limit above.

**Next and live gate:** wire a distinct checked crossing pulse and the existing
loading/arrival handoff, with the source floor carried continuously through the
layered entrance. Then plan from fresh Crushbone positions. Existing owner
preview **0.39.18** and assist **0.39.13** remain unchanged; pending live map/
travel evidence is still needed. G0 is passed and must not be repeated.
Current level, XP/hour, deaths and camp are unknown. No real route, automated
XP, 1–20 or fresh hands-off 1–50 run is accepted.

**VERIFIED private publication:** commit
`94d4447c223d50eaaf5afb0095c0dfa3c6fab2af` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.17/source`. Its no-input startup
checks exact zone-line BSP/area/polygon selection, strict defaults and rejection
of other water/unknown/zone regions. No worker, device, game input or install
change occurred. Archive SHA
`95f95fe14d6f3775270c0a7f33399791ef135e418c00f53b7fd3d6390b14f8a3`;
startup SHA `1c7f37e7f0880c17349a273e477cb99ecff0fe08eecc4c791f9f46fcb9887c87`.
Owner preview 0.39.18 and assist 0.39.13 are unchanged.

## Expected zone-arrival handoff — 2026-11-14 12:17 UTC

**VERIFIED implementation:** source 0.42.16 adds `ZoneArrivalHandoff` over the
existing exclusive `ZoneReaderLease`. It observes only new loading/entry
boundaries, calls the supplied control-release operation on loading, requires
the exact expected destination and a separate current ready observation, then
uses the existing `StoppedLocationPair` to request two fresh positions. It
never creates a device or crossing movement, carries no source heading/height/
floor chain, and does not treat the first position as an exact spawn. The
caller must still connect a checked crossing move and readiness provider.

The location reader now exposes immutable per-poll boundary records while
preserving its existing non-replay and zone invalidation behavior. A reentrant
empty poll initially erased a loading event before the handoff could release;
review reproduced it. Capturing the owned boundary/cursor result before callback
checks fixes that loss; a changed cursor refuses and releases. Destination
watching also now invalidates loading/entry pairing on logging ON/OFF and on a
reversed receipt clock. Previously, a logging reset could be bridged into a
false arrival. No old zone, position or heading was enabled as a shortcut.

**VERIFIED focused validation:** 91 checks pass across arrival, destination,
location, transition, stopped-pair and owner-zone tracking. New cases cover
release before any location request, no requests while loading/not ready,
expected fresh stopped destination positions, changed owner/log/cursor,
unexpected/missing/duplicate/stale entries, logging reset, malformed/partial
messages, movement during the destination pair, cancellation inside release/
ready/current callbacks, and reentrant empty/mutating polls. The first run's
five failures came from a fixture appending entry before a two-second clock
advance; the corrected fixture records entry after waiting. Freshness was not
relaxed. All handoff positions, time and release callbacks are synthetic; this
is not live input, a zone crossing or character progress.

**VERIFIED retained transition data:** copied GFay manifest
`navmesh/nov12-7e3cd28-store/gfaydark.json`, SHA
`ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82`,
has area 4 / `DRNTP00255000004_ZONE`, zone-point 4. Package bounds are
`(-92.651199,2614.455322,0.000075)` to
`(-9.39732,2623.375278,89.199112)`. Current approach goal Y=2585.165 stops
29.290322 units before the minimum region Y. Its `to_zone=crushbone` mapping
is explicitly a guide hint; destination ID, spawn target and heading are null.
No exact server destination or spawn was invented from this record.

**VERIFIED private publication:** source commit
`340402a6079c653456c21885c9c79581953cb429` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.42.16/source`. Startup exercises
loading→release→ready→two stopped destination positions and logging-reset
rejection using synthetic logs, clocks and release callbacks. No worker,
device, game input or install change occurs. Owner 0.39.18 is unchanged.
Source archive SHA
`0a54115dd34257e98fbddc13de3b208b3fd902b48357df96af6dfab0038f54e3`;
startup SHA `9df757ed74aa57f3c22cda491ca2474a4e9aeaadfc3efd68e6ac9f2611c26cce`.

**Still required:** connect the final checked trigger movement and loading
release to the owner runtime, then load Crushbone geometry and plan from its
fresh positions. Existing ground-only destination routes still reject zone-line
areas. The owner preview stays **0.39.18**, assist **0.39.13**; its pending live
map/travel test is unchanged. No new owner action or G0 repeat. Live map refresh,
actual traversal, crossing, camps and 1–20/1–50 remain unverified/unfinished.
Current level, XP/hour, deaths and camp remain unknown.

## Current-zone recognition at stationary startup — 2026-11-14 12:11 UTC

**VERIFIED implementation:** source 0.42.15 / destination preview 0.39.18
adds visible-map recognition to the existing stationary `/location` hotbutton
test. It reads the pinned client's zone label and all three coordinate labels,
requires a complete exact unique catalog name and confident single-line OCR,
and compares the displayed integers with the same test's fresh raw log reply.
The reader retains its live log cursor; map coordinates never become navigation
positions. A route still obtains its own fresh stopped pair. No extra game key
is sent by recognition. Unknown/clipped labels, changed sources/process/focus,
logging/zone boundaries, duplicate replies and cancellation leave startup stopped.
A final callback-cancellation gap found during review was reproduced and fixed
with a short locked commit and a scalar cancellation recheck after callbacks.

**VERIFIED focused checks:** 100 cases pass in 11.71 seconds, including the
actual Tesseract adapter on synthetic rendered labels, retained-engine hotbutton
integration using a pipe instead of a device, F9 during recognition/final
observation, logging resets and existing hotbutton/UI/tracker regressions.
The initial run found one OCR padding problem and six missing-fixture errors;
those were corrected. Cropping blank padding raised the synthetic `11` reading
from 84.02 to 96.04 confidence without lowering the 85 threshold. These tests
are not real-client acceptance.

**VERIFIED static source evidence:** the pinned native types 1021/1022/1023
read actor fields +0x74/+0x78/+0x7c, in the same order as the three `/location`
values. Their display formatter is `%.0f`; the log formatter is `%1.2f`.
The allowed difference is 0.505 units for formatting, not a movement tolerance.
`tools/audit_current_zone_label.py` now reproduces those spans and formats as
well as the actor-zone dispatch. Private artifact
`client-data/map-zone-0.42.15/probe.json` SHA
`8d8d9f7d06ee0a90778a1404ca1b6b1ae75fa18dd67bfd0b11db45d18a3f5905`.
No game/native client was executed or attached for this audit.

**VERIFIED private publication:** 0.39.18 is staged at Alienware
`~/.local/share/eql-automation/owner-assist/0.39.18`. Its manifest, offscreen GUI,
installed map/catalog/archive and destination-loader startup checks pass. The
GUI image was inspected. Archive SHA
`e173bb56b36a917a3ccdfecba54c0d24bf96cba027e87f1564e92a4c0d3ac45c`;
startup SHA `412c2b8b5a2d181db8293a16c81be4ea7e9c0110e0596d9005b8b57fe9f9c7a0`.
The production OCR adapter reads synthetic “The Greater Faydark” on Alienware
at 91.21 confidence. This startup uses a synthetic zone identity; no engine
worker, device, game input, settings write or install change occurs.

Alienware lacked Tesseract, so its private dependency is staged separately at
`tools/tesseract-5.5.0-linux64` outside the game install. It contains the existing
local 5.5.0 executable, resolved loader/libraries, English model and license
files; all 174 payload file hashes match its manifest. It uses one OCR thread,
not a system installation. Tool archive SHA
`a9dbdae3c1230647fb6e9bd90cd7cd0449fdd8de81170123561d4b9d605898d2`;
manifest SHA `1a12779535242e14bc6883b36dcd1da4e72d1bd7f7ab26ee4034dbb2c8eea462`;
startup SHA `d4a673c23c9a4b0a547ebcdd417e357463ff002102899bbd9fd4eef268673c5c`.
All binaries/model data remain outside git.

Source commit `50bd0003090a5fc06010ad893ff96b10c2572a36` is staged at
Alienware `owner-tools/0.42.15/source`. All 139 package files match preview
0.39.18. Imports, engine composition with map recognition, private OCR presence
and destination loading pass without worker/device/input. Source archive SHA
`1397789a473b215f8812cbce41573fb066b7b5b7da1b9ab067a10b1f6f6cf751`;
source startup SHA `f2398c0f8c9cd944414cc41584aca7ab206477bae7be5d41d78eadfaa0858b41`.

**Remaining real-client gate:** owner runs the existing stationary hotbutton
test with the map visible, then supervises travel. Live crop placement, OCR
accuracy and label refresh are not verified. Starting already in GFay now has
an implemented observation path; old zone history is still not replayed.
Actual traversal, zone crossing, camps/combat and 1–20/1–50 are unfinished.
Level, XP/hour, deaths and camp remain unknown. G0 is passed and owner-confirmed;
no repeat. Assist remains 0.39.13, based on the existing rotation tool.

## Logging continuity and current-zone startup — 2026-11-14 12:01 UTC

**VERIFIED fix:** source 0.42.14 / destination preview 0.39.17 invalidates
the retained zone and position when a client logging ON/OFF notice appears.
The movement log monitor latches a stop, and transition pairing cannot span
that boundary. Incomplete parsed loading/entered messages also clear the old
zone. A subsequent exact zone entry restores observation; old coordinates
are never replayed. Player chat containing the same words does not match.
97 focused location/transition/veto/owner-tracker tests pass in 2.21 seconds.

**VERIFIED source inspection, static only:** the copied `eqstr_us.txt`
contains notices 12096, 13221 and 13222. The pinned executable's command
function at `0x14023ede0` changes logging flag `0x140f43518` and selects the
ON/OFF notice. The chat path tests that flag before calling the log-buffer
routine. The flush span at `0x140120612` supplies mode `a`, calls three
stream routines, then clears buffered data. **INFERRED:** this is an
open/append-write/close cycle, not a persistent writable descriptor. Wine
descriptor lifetime and full logging continuity have not been observed.
Process birth plus an old zone line therefore was not enabled as a startup
shortcut. This also avoids treating a zone retained before disabled logging
as current after logging resumes.

The executable remains SHA
`fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`;
string catalog SHA
`0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`.
`tools/audit_client_logging.py` reproduces the focused spans and stores them
outside git. Private artifact `client-data/logging-0.42.14/probe.json` SHA
`9027bf69e91f11cab48009b982b8af8d5c9d00c9fb1e56d7c4e910825673b8da`.
REA session inspection reported no available native engine (Ghidra lacks its
required JDK). The instructions' read-only fallback was used: these are
ordinary `objdump` observations, not REA decompiler or runtime evidence. No
game was executed or attached, no input sent, and no install changed.

**VERIFIED private publication:** 0.39.17 is staged on Alienware; source
manifest, GUI startup and installed archives/catalog/map checks pass without
starting an engine worker, creating a device or saving settings. The loader
used a synthetic zone identity, not live zone acceptance. Archive SHA
`eda64b469937c051a7f256f4f7dd723651de3c9ef37bc5495f995953b1da7d07`;
startup SHA `057493d27526f5076b6ef0bd9d4ee10e0e1ae5846ff92fc03789a797814c6276`.
The GUI image is byte-identical to 0.39.16's inspected image. HOWTO now uses
0.39.17. Assist stays 0.39.13; prior previews remain intact.

Source commit `dc5e25cec42b3c73d372af7e210b0a05d6b4223a` is staged at
Alienware `owner-tools/0.42.14/source`; all 138 package files match 0.39.17.
Imports, engine composition and destination loading pass there without input.
Source archive SHA `e532f803cd5f388ecb5b36a7f527aeb0263af365faa5a9e44aaf691ac2d96f43`;
source startup SHA `8c16865bc0db25c349e84a0d282a70d6562285ea63de66879525b00ccb12f47d`.

**Remaining:** current-zone recognition without a fresh appended entry needs
an independent current-client observation. The actor-zone UI label remains
the next source to integrate. Actual travel, zone crossing, camp/combat
execution and hands-off 1–20/1–50 are unverified or unfinished. Current level,
XP/hour, deaths and camp remain unknown. G0 is passed; no repeat requested.

## Owner destination travel and pulse steering — 2026-11-14 11:52 UTC

**VERIFIED implementation:** source 0.42.13 / owner preview 0.39.16 adds the
separate `supervised_destination_travel` job and **Travel toward Crushbone…**
button to the existing rotation tool. The action retains the same seven-pulse
calibration, input observer, sender, stop lock and log lease, obtains fresh
positions, invokes the full destination planner, measures current height and
runs the checked route. It does not load saved heading or queue a new action.
Ordinary motion still stops; the two-unit local trial retains its old scope.

The destination comes from the installed client's `maps/gfaydark_1.txt`,
verified read-only SHA `84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882`.
The copied map/alignment bundle is private under
`owner-route-data/gfay-crushbone-approach-20261114`; tile geometry remains in
`gfay-destination-20261114-tiles`. Exact label/alignment hashes and the unique
approach marker bind the endpoint; no manual route recording or guessed game
coordinates. This marker is not a verified zone trigger or a selected camp.

Destination scope is explicitly bounded to 1,500 seconds, 3,000 controls,
10,000 planned units and 600 seconds of reserved maximum hold. Startup has
its own 180-second cap after asset loading, including countdown/calibration.
Height correspondence lasts 1,560 seconds, while every later position keeps
its original freshness and source-floor residual checks. The execution clock
is extended exactly once after valid startup. These limits permit an attempt;
they do not prove that a 4,996-unit route will finish before the cap. Focus,
physical input, jobs, process/settings, log hazards, zone transitions, geometry,
watchdog and release conditions remain active. Assist rejects movement.

**VERIFIED steering defect and fix:** the full owner-path harness exposed a
real controller mismatch: a 0.6-unit lookahead could be followed by 2–3 units
of blind pulse travel, causing corrective steering to overshoot the centerline.
The retained follower's default 20ms continuous-loop tick also widened the
requested 1-degree turn threshold to roughly 3.4 degrees. The wrapper now aims
at least one maximum nominal hold ahead and sets the fresh follower's unused
continuous tick to zero. Input duration, corridor width, collision bounds and
freshness are unchanged. A deterministic 40-unit / 0.3-width regression with
one-degree calibration disagreement and a late but bounded pivot failed at
0.549 units cross-track before the fix; it now arrives inside the strip.

**VERIFIED focused checks:** 42 policy/preflight cases passed before the final
steering correction; all 25 follower cases plus 20 subtests pass with that fix.
The complete retained-engine destination flow passes across two polygons with
actual watchdog pipes and synthetic log/physics feedback (26.69s). The
three destination preflight cases and original local-trial runtime pass; a
calibration timing overrun prevented the first F9 test from reaching its
intended event. The isolated F9 recheck passes (13.74s): it stops during route
DOWN, releases keys, closes the observer/lease and emits no later input.
Earlier pipeline failures were an authorization deadline under CPU contention
and the steering defect above; neither is hidden as a passing run.
Private copied test records are in `releases/eql-destination-0.42.13-evidence`.
Arrival SHA `444a9291bb82db59b2153d81666ef327b076498bb31892a725aa74f78415fdc0`;
F9 SHA `3caf4f10547b0253f413a1286562d2e8a79100e50ccd615016159351d4f61aec`. They are simulation evidence only.

**VERIFIED private publication:** owner preview is on Alienware at
`owner-assist/0.39.16`. GUI startup shows both short-trial and destination
buttons. The screenshot was inspected; controls and stop button are visible.
The complete loader matches installed archives, catalog and destination map,
using a synthetic tracker identity for this read-only startup. No engine worker,
device, game input, settings save or protected-prefix change occurred.
Archive SHA `ca3be29d31a969fe52ae96a3f92917bc1e408146593d7404289a35c53eaff99b`;
startup SHA `7b5c7df74f3e8f93038fce6ec656f4b949e9c7c7a5ccb0a5e0ec504ce1628fb5`;
GUI SHA `a73d8076f2d703a55e736ac5d187ca997e2d46331ce15876714ccfdbe851c3d1`. HOWTO has the command and controls.

Source commit `afcbaa7c9a9fb47fed70aecc5d2da69521a66e6b` is also staged on
Alienware at `owner-tools/0.42.13/source`. Its 138 package files match the
0.39.16 preview manifest. Imports, engine class composition and the destination
loader pass there, with installed archives/catalog/map checked read-only.
This used a synthetic tracker identity; no worker, device or game input.
Source archive SHA `e044f7812b32743094a0508021e107215d52d67790a2be3e9d762b982b692c5f`;
source startup SHA `b66e5f0a71f4269fc1d63cf360969f5d0f1de01daf4ada24a928ad926a888c85`.

**Remaining:** owner-run current-session zone/hotbutton setup and real traversal
are unverified. The approach does not zone, choose camps, fight, loot, buy/sell,
recover death or level. Existing assist 0.39.13 remains separate; seamless mode
switching and unattended 1–20/1–50 remain unfinished. Current level, XP/hour,
deaths and camp remain unknown; saved UI level 7 is not a current observation.
G0 is passed; no repeat requested. Next consume actual owner travel evidence,
continue zone/camp execution and improve current-zone startup independently.

**OBSERVED, 11:56 UTC:** one read-only Alienware `/proc/*/comm` and expected
character-log metadata check found no process named `eqgame.exe`. The selected
Legira/freeport log's most recent complete timestamp was Nov 13 16:10:46 local;
the latest retained zone entry was Nov 13 15:17:07 local. Neither is a current
zone or character-progress observation. Current-process writer-FD ownership
therefore remains unverified; the preview keeps its appended-entry behavior.
Metadata-only evidence is retained privately in
`releases/current-zone-process-probe-20261114-1157.json`. No game launch, input,
protected-file change or repeated polling occurred.

## Pinned tile policy in route geometry — 2026-11-14 11:43 UTC

**VERIFIED implementation:** source 0.42.12 carries an immutable, explicit
`RoutePrecisionPolicy` from the opted-in GFay loader into the current-start and
destination plan, then into `RouteGeometryPreparer`. It binds the exact grid,
manifest/mesh/archive/zone and retained seam tuple. Changing the policy, grid,
manifest or seam inventory invalidates prepared checks. Tile seams cannot be
used by hiding the grid or omitting the policy. Default loading and the staged
owner preview remain unchanged. Actual terrain/source, static objects, BSP,
freshness, watchdog and receipt-bound floor commits remain required.

The private copied bundle `owner-route-data/gfay-destination-20261114-tiles/`
adds the retained `gfaydark.json` manifest SHA
`ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82`
to the same four pinned files used by owner trial 0.39.15. Old bundles were not
modified. The model is numerical provenance, not measured character clearance.

**VERIFIED copied-data probe:** actual per-movement `_trial` geometry passes
terrain/static/BSP at route segments 39 and 58, covering five- and forty-ULP
baked overlaps. Each refuses `overlapping_ground_faces` with overlap permission
off. Original source chains remain index 1; successful results are uncommitted
index-2 forks. Segment 54 retains its unrelated `surface_crosses_height_window`
refusal at the same six-unit envelope. This isolated probe constructs no
sender/ledger and does not assert route traversal. Radius 1.2, height 6 and
motion bounds remain explicit hypotheses. Probe SHA
`5a13fbc1c0127e1b98752299247115186e0e56b88b06e8b67a7ea360b16d2392`
at `nav-candidates/gfay-route-tile-geometry-0.42.12/probe.json`; executed code
and full source hashes are retained beside it. Positive probe wall times were
0.1112s and 0.0804s (CPU 0.1054s and 0.0774s).

The new tile-enabled destination probe still produces 197 segments / 4,995.95
units, retaining the initial chain and all future runtime checks, in 10.80s
after loading. It uses synthetic observations, not current character state.
Private `nav-candidates/gfay-crushbone-destination-tiles-0.42.12/probe.json`
SHA `f615e7676eac49f6b03d2a427188203b67ff76b1ddeae7d2c73ee031100d0b60`.

**VERIFIED validation and limitation:** 94 focused policy/source-floor/geometry/
current-start/destination cases pass; three owner-runtime loading/handoff
regressions pass. The pipe fixtures exercise actual watchdog processes with
synthetic log/motion feedback. The gap, overlap, permission-off and wall cases
have each passed across focused runs, but the combined run remains unstable
under measured devbox CPU pressure (CPU PSI approximately 72%; all allowed
cores approximately 98–100% busy during a bounded sample). The last four-case
run passed overlap traversal and permission-off refusal, while gap and wall
runs stopped on watchdog scheduling deadlines. These failures are recorded,
not counted as passing or waived. Deadlines and observations were not relaxed.
An exact SAT sign test now short-circuits at the first positive vertex instead
of computing an unnecessary maximum; its predicate and boundary behavior are
unchanged. Profiling before this improvement identified rational cross-product
work; later a 60ms CPU check consumed 344ms wall time under contention.

**Remaining real-client gate:** owner-run short traversal remains unaccepted;
0.39.15 still requires current-session GFay and hotbutton setup. The full
destination needs an explicit bounded owner travel scope; short-trial limits
are not silently enlarged. Zone entry, Crushbone source steps, suitable camps,
combat/loot/vendor/recovery integration and 1–20 leveling remain unfinished.
Current level, XP/hour, deaths and camp are unknown. G0 is passed including
owner visible-stop confirmation; no repeat. Assist 0.39.13 and owner trial
0.39.15 stay unchanged, with no new owner action or lead game input.

**VERIFIED private staging (2026-11-14 11:42 UTC):** source `f5037e7546df0360d31a3ae8637e2a386d4dda10` is
available on Alienware at `owner-tools/0.42.12/source`, with the new copied
bundle under `owner-route-data/gfay-destination-20261114-tiles`. The actual
copied five-ULP geometry startup passes terrain/static/BSP, refuses without
overlap permission and rejects a changed grid manifest. The existing 0.39.15
snapshot verifies unchanged before and after. No engine worker, device,
game input or protected-install change. Archive SHA
`f90fb3ff2689a03efd2feedb72576951cf6ac8ed1c76b9a70911dd37c0694f02`;
startup SHA `c70d8b19ac011cd7ab6e0d2b902f7d50fca7a5114f46928880f1490bea1e8043`.
This source staging is not an owner traversal or leveling acceptance.

## Fresh current-position destination corridor — 2026-11-14 11:31 UTC

**VERIFIED copied-data planning:** source 0.42.11 adds `plan_destination`,
composing the existing current-start producer with the retained rotation
helper's NavMesh search. Exact start and destination support are resolved
independently; the search's nearest-point mechanism cannot move either XY or
select another endpoint polygon. Every corridor polygon is dry and in the
current component; every selected crossing lies on both unique directed
portal segments. Chosen segment lengths and height seams satisfy the existing
follower limits. Body/obstacle clearance of the suffix is explicitly unverified.

The initial accepted source-floor chain remains at index 1. Future movement
must still run the existing `RouteGeometryPreparer` terrain/static/BSP checks,
then commit its floor extension only after the matching release receipt.
Runtime observations use that committed chain. Whole-corridor precomputation
is not a movement requirement; the evidence explicitly scopes its proof to
the initial floor/body and reciprocal topology. A first prototype reused the
old whole-route strip selector and exhausted its repair rounds after 44.48s;
it produced no plan. The final producer selects bounded reciprocal portal
targets and leaves each forthcoming body footprint to the mandatory runtime
checks. No collision guard or input policy was disabled.

The source destination is `to_Clan_Crushbone`, line 2 of private
`client-data/retail-full/maps/gfaydark_1.txt`, SHA
`84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882`.
Pinned map-alignment evidence SHA
`c3f9fb5ffdf8dc740d145c119b2c3522e22cb5f36617e575417176932620901f`
supports map-to-WLD `(-y,-x)` via 8,163 vertex matches versus 2 next-best.
The resulting package XY is an approach marker in dry polygon 19255, not
acceptance of the actual zone trigger. Three source terrain heights exist at
that XY; no source floor was chosen by nearest label Z. The connected runtime
floor chain must establish support as the character approaches.

The pinned probe uses synthetic fresh replies at fixture XY
`(1780.12, -1802.22)`, not a claimed current character location. It produces
197 segments, total length 4,995.9465 units, in 10.62 seconds after loading,
retaining initial floor index 1. Code/data hashes and executed probe source
are saved outside git. No game input or client execution occurred.

Private `nav-candidates/gfay-crushbone-destination-pinned-0.42.11/`:

- `probe.json` SHA `dbf36ca66eac3112faf4b48aa7fe9df894b45ac97036f706e2bfa013760fb531`.
- `plan.json` SHA `ebe75cdd071ab04866b79ef559a8b56a702b9dc29988e9fdcd206ad0d90e021b`.
- `geometry.json` SHA `6c8d32df692d74b471867c7b33b8bdeeb907171647a1472748fd800c1e74998a`.

**VERIFIED focused tests:** thirteen final planning cases pass, including
changed source/owner/deadline, displaced reverse portal, duplicate/missing
links, changed endpoint XY/floor and closed/foreign components. Two actual
watchdog-pipe cases pass with synthetic scene/movement feedback: the new
multi-polygon plan reaches its destination, and a wall outside the initial
proof stops the sender before the wall. Every completed DOWN has a matching
receipt/chain extension; rejection adds no extension. Test-harness corrections
were needed for clock rebinding, a serialized receipt property and the
terminal follower index; no runtime bounds were widened. The final planning
plus clear traversal run passed 14 cases; the suffix-wall case passed in its
preceding focused run. These do not establish actual client movement.

**Remaining work:** the current owner policy remains a finite short trial;
this full destination plan cannot silently extend its limits. Copied tile
rounding/overlap handling must be carried consistently into runtime guards;
Crushbone source steps and later camps remain unfinished. Owner trial 0.39.15
and assist 0.39.13 stay unchanged. A single read-only result check found no
route-trial JSON or `~/eql-route-trial-trace.jsonl`; the owner test remains
pending without repeated polling. G0 stays passed. Current level, XP/hour,
deaths and camp remain unknown; no automated XP or real route accepted.

Source `aaa744cbee21d8824c438976ea1d00cf126bee03` is privately staged on
Alienware at `owner-tools/0.42.11/source`. Startup builds a fresh two-polygon
synthetic destination route through the retained NavMesh, verifies the initial
floor chain is not advanced, and rejects a displaced reverse portal. All 134
pre-existing runtime modules match owner preview 0.39.15. No worker, device,
input or install change occurs. Archive SHA
`452b228978b7f1b2647696b4c851286dead6841f24de9d17286cb12d156a457f`;
startup SHA `d496086fb74b5ca323f64316f5b42bcf3424c1665e5f96e03a562e166cfe5cf9`.

## Same-action owner route runtime — 2026-11-14 11:18 UTC

**VERIFIED implementation and pipe tests:** source 0.42.10 composes the retained
rotation engine with the current zone reader, supervised motion, fresh stopped
pair collectors, current-start planner, height producer and checked route
sender. A separate `supervised_local_route_trial` owner job retains the exact
input observer and same-session heading after calibration; it never reloads
saved heading or rearms another queued action. Ordinary motion measurement
still ends stopped. Trial cancellation releases keys and closes the reader
lease/observer; F9 at the completed-motion handoff cannot start a route.

Fifteen focused runtime/collector cases pass, including actual pipe-backed
motion-to-route completion, cancellation during startup and route DOWN,
missing zone/assets before motion, stale/duplicate/unsolicited positions and
ownership changes. The separate 11-case check includes ordinary measurement
completion and cancellation at the handoff boundary. Physical feedback/logs
are synthetic: these are **not real-client movement or level acceptance**.

Preview 0.39.15 is built from verified 0.39.12 and uses the existing rotation
engine, with a separate short-route button and stage indicator. Its entry
requires measurement mode; assist 0.39.13 remains unchanged. The source manifest
pins all packaged runtime modules. Client data stays outside git, in the private
`owner-route-data/gfay-trial-20261114-current/` directory: mesh, terrain/object archives
and zone catalog, 11,396,711 bytes. Loader checks loaded archive/WLD identities,
complete static/BSP inventories, transform source and installed read-only source
hashes. It consumes no historical route/position proof.

**OBSERVED installed-catalog change:** the first unpublished 0.39.14 staging
attempt refused before device/GUI startup because its copied zone catalog no
longer matched the installed file. The current catalog was read from Alienware
without modification: 20,266 bytes, SHA
`0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d`.
It adds unique entries for Tomar's Terrorfields (84) and Firiona Vie (503);
GFay remains uniquely The Greater Faydark (54). The new 0.39.15 bundle pins
this current catalog; old candidate/data are retained and not reused. Both
installed GFay source archive hashes matched before the catalog refusal.
Private retained catalog: `client-data/zone-catalog-20261114T1123Z/ZoneNames.txt`.

**Remaining real-client gate:** this first finite route needs a newly observed
GFay zone entry in the running helper, same-session `/location` hotbutton setup,
owner-supervised open ground and a real execution result. Current-zone label
OCR/bootstrap and multi-polygon paths/camps remain unfinished. The two-unit
one-polygon trial is not the requested 1–20 route. Level, XP/hour, deaths and camp
remain unknown. G0 is passed, including the owner's latest visible-stop answer;
no repeat is needed. No lead-driven character movement or login was performed.

**VERIFIED private 0.39.15 publication/startup:** staged at Alienware
`~/.local/share/eql-automation/owner-assist/0.39.15`. The exact packaged source
manifest passes, complete copied geometry loads, and installed archives/catalog
match. Offscreen GUI smoke shows both the separate route trial and ordinary
motion buttons enabled. No helper worker, input device, game input or settings
write occurred. Entry without measurement mode refuses, leaving assist 0.39.13
separate. The loader smoke uses a synthetic tracker identity; it is not proof
of the current live zone. Four focused followup cases pass for preparation
refusals (including a transition during load) and observed-zone/countdown UI
payload. The new loader consumes the actual current copied data successfully.

- Private archive SHA: `973fdb977d6c693d5bd97d14c7aeeeb7dea4f4f132558ec9dacf07f0e9881f0c`.
- Alienware startup SHA: `bf9be22fe38d2b0e21264ac9551b4ec7beabc77d0b2fe9fb1442fb58dfea8022`.
- GUI image SHA: `657ac604daa81c2b592dfd1695256b7b10bbda7836ac3a0b0a96366b5184bc57`.

Source `5f7c7173ae008ea899c4d5173b3d2bc793438bef` is also privately staged at
Alienware `owner-tools/0.42.10/source`. Its no-input startup imports the runtime,
composes the retained engine, verifies distinct motion/trial jobs and checks
all 135 package files against the verified 0.39.15 owner preview. No worker,
device or game input was started. Source archive SHA
`19934789962e4799474b9c3afcc314d77f092c03ef88bfa69ee050a35f55ebae`;
startup SHA `4642e104d1fc349d224bdc02cc98b6d49604eeb0d1a51c1374dbd9d68e898f8f`.
The offscreen GUI screenshot was visually inspected: the separate route button
and the stop/hotbutton/motion controls are visible without scrolling. Its saved
character/level fields are configuration, not verified current run metrics.

## Current-position route producer — 2026-11-14 11:03 UTC

**VERIFIED implementation:** source 0.42.9 adds `CurrentStartPlanner`. It uses
two fresh consecutive stopped log positions bound to the current owner/log
and expected client-catalog zone. It finds exact baked XY support without
snapping or choosing the floor nearest actor Z, samples all source terrain
layers independently, and preserves every source seed ID. It constructs a
short one-polygon capsule from the second position and supplied same-session
heading. Selected-polygon exact coverage, complete local ground, terrain
occupancy, static-object occupancy and BSP checks all must pass. Body/motion
parameters remain explicit hypotheses; neither live acceptance nor movement
authority is produced.

The output contains new geometry evidence, a hashed fixed-route artifact and
the accepted initial source-floor chain. It does not reuse the historical
route's starting location or coverage proof. A fresh stopped-height startup
remains necessary before movement; planning does not retimestamp its inputs.
The new route still needs owner scene/motion/session assembly. One-polygon
planning is a finite first traversal stage, not completion of camp routing or
the 1–20 goal. Multi-polygon transitions and real movement remain required.

`BspDetailMeshView.load` now binds its exact bytes with SHA-256 and makes its
arrays read-only. The planner checks that identity with ground/source/static
and BSP identities, including after callbacks. Deadline and monotonic time
are checked after binding callbacks; replacing geometry or crossing a deadline
cannot produce a successful final plan. `RouteMotionBounds.validate_values`
allows the same hypothesis validation before a follower/floor chain exists;
the existing body-height match remains in the runtime validator.

**VERIFIED focused checks:** all 29 final producer/detail-loader tests pass.
They cover translated current starts, overlapping baked/source floors,
interior holes/static obstacles/water, stale/moving/unbound positions,
source/owner-binding changes, deadline callback changes and same-count foreign
detail meshes. A plan round trip feeds the existing observed-height producer
and fixed follower with fresh synthetic pairs. A larger focused run had
68 passes and an existing pipe case stop after release on its timing guard;
its isolated recheck passed. No deadline was widened or failure hidden.

**VERIFIED copied GFay probe, synthetic positions:** the first probe used
package XY `(1780.12, -1802.22)`, four units along the retained first leg, only
as a reproducible fixture. A separate polygon-center fixture also refused.
The diagnostic found `invalid_footprint_or_face_budget`: the new selected
polygon query incorrectly charged remote detail triangles against its local
budget. Those early refusals did **not** establish a physical edge/gap. The
fix queries every intersecting XY bounding box and retains the same local
limit, without truncation. An explicit large-polygon regression passes.

After the fix, the original shifted fixture produces a new two-unit plan in
polygon 32475, passes all terrain/static/BSP guards and creates a fresh
height correspondence. Planning/startup took about 0.208 seconds after view
loading. The checked capsule includes four static faces from the complete
109,932-face/2,799-placement inventory. The body radius 1.2, height 6 and motion
envelope remain hypotheses; the synthetic actor-height offset is 2.564.
Measured fixture correspondence is 2.5592270276605618, not a live calibration.

Private artifacts under `nav-candidates/`:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `gfay-current-start-0.42.9/probe.json` | `edd33babeb049d2417762be5e0d19a8168b5891e48978e704f95ae358c50721f` | Initial budget refusal |
| `gfay-current-start-center-0.42.9/probe.json` | `0f3f5dd665ae49dc216b6a978692a77e89734c87a32c493f91d80e20777d2474` | Same budget refusal |
| `gfay-current-start-local-query-0.42.9/probe.json` | `e0fca4fd35c82af948dae32259546908c6f3a30d803fe84296f58c51e0da52e9` | New plan and height produced |
| `gfay-current-start-local-query-0.42.9/plan.json` | `47ce46da4940d116e447c61c18c9ef3dc24df30e8269ffc9b8134c108c01d7f2` | New current-XY fixed plan |
| `gfay-current-start-local-query-0.42.9/geometry.json` | `09850ab55d46d90bcdf060bdf556605b028d0686d53353a050828857dbd80aec` | New capsule/source proof |

**Next:** preserve the completed motion session's observer and current heading
through a single explicitly owner-started trial; connect current-zone lease,
position collection, this producer, height and route driver. No owner control
is enabled yet. Assist 0.39.13 and motion 0.39.12 stay unchanged; G0 passed and
needs no repeat. Current level, XP/hour, deaths and camp remain unknown. No
client input, login, install change or automated XP occurred in this work.

Source `cc2e54f` is privately staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.9/source`. Remote startup
imports the new producer and builds a translated current-position plan over
synthetic complete geometry/logs, verifies its new proof hash and false
acceptance fields, then rejects an expired pair. No helper worker or input
device is started. Archive SHA
`cb885406415014ac024a05781b611e177d821fd4fbed65e8666afa73ad65c55d`;
startup SHA `2aa7c3b6c349496cfa8025774594ac520513a8157320c447d59714399437a328`.
The source build does not replace the owner assist/motion previews.

## Finite supervised route policy and current-zone label correction — 2026-11-14 10:56 UTC

**VERIFIED implementation:** source 0.42.8 adds `SupervisedRoutePolicy` to the
existing checked route sender and session driver. It is an explicit
measurement-only path with an owner open-ground declaration, exact route,
motion and planning-record identities, maximum duration/steps/distance and a
conservatively reserved total key-hold budget. Actual focus/process, physical
input and log-veto observations remain required. Terrain, static-object and
BSP checks, exact pending ticket, watchdog release and receipt-bound floor
commit remain required. Cancellation during observation/geometry callbacks
is rechecked before authority can return; callback time counts toward the
whole-trial deadline.

The policy **does not claim** independently verified chat, target, dynamic
clearance, body dimensions or motion bounds. Its typed scene/authorization
records keep those verification fields false. The default unattended sender
rejects these types, and the policy refuses assist, full-auto and off modes.
Each session attempt records the declaration, planning bounds and reserved
hold, including failures. No source job, GUI button or hotkey constructs this
policy yet, and no saved calibration is accepted as current heading.

**VERIFIED checks:** the focused integration run had 140 passes, one existing
pipe-test watchdog-arm refusal before its intended final-release injection,
and one deliberately excluded older full-route pipe case. The failing case
passed on its isolated recheck; no timeout was relaxed. The final policy-only
non-pipe run passes all 31 cases, including a new slow-callback deadline case.
Both new real-pipe tests passed in the integration run: a conditional pulse
commits only after release, and cancellation during DOWN releases without a
floor commit. These are synthetic observations and pipe writes, not client
acceptance. No real route or automated XP has been observed.

**VERIFIED static source; correction of earlier inference:** the copied
`MRA_ZoneLabel` XML uses EQType 1020. In the pinned executable, the actual
producer dispatch for 1020 is selector 205 to `0x140547e32`. It reads the
current actor at `0x140f3a808`, zone field `+0x1ec`, and resolves its name through
the zone catalog at `0x140f3a7c8` via `0x1406ec290`. It does not read the map
window's selected-zone field `+0x920`. The adjacent dispatches 1018–1023 and
two label-update callers were also checked. Missing actor/catalog yields
empty output; unknown lookup yields `Unknown Zone`; some metadata permits an
instance-number suffix. The earlier claim that this label necessarily
represents the browsed map was incorrect and is superseded here.

`tools/audit_current_zone_label.py` reproduces the XML, adjacent dispatch and
seven bounded native span hashes without native execution. Executable SHA
`fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`;
XML SHA `6bcdcc7b20c6510c5797e044ab3193b8a7fa2386dc87e8d770b5387346fe6419`.
Private artifact `client-data/current-zone-label-0.42.8/probe.json`, SHA
`90adaeac3d89d5fc70e6690ad9fa205abb270b50654f91e2544fc2feb107896a`.
UI capture metadata now distinguishes this static source from unknown live
refresh/recognition. The complete XML-to-runtime adapter binding, visible
fresh label capture and loading behavior remain unverified; this finding does
not establish the owner's current zone or automatically enable route startup.

**Next concrete assembly:** retain the completed motion experiment's observer,
tested hotbutton, sender, log veto and settings/window bindings through one
owner-started measure-then-trial job. Acquire the exclusive current-zone
reader, build a short source-checked plan from current XY rather than the old
GFay start, request fresh stopped positions for height, then attach the route
driver. Default motion completion still stops. One read-only Alienware report
directory check found zero JSON results in `location-hotkey-tests`,
`motion-measurements` and `g2-ui-observations`; no further polling was needed.
G0 remains passed. Owner assist 0.39.13 and pending motion 0.39.12 are unchanged.
Current level, XP/hour, deaths and camp remain unknown. No login, game input,
protected-install change or public/git push occurred.

Source `1d36c0d` is privately staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.8/source`. Remote startup imports,
immutable declaration, false verification-field preservation and refusal of
absent dependencies pass without an engine worker, device or game input.
Archive SHA `5cd565ce3dc1d915072648ef64fa47fa9c118719284d50468eaf9d23a371be94`;
startup SHA `ea1bf83f094adf13afdc7c31b92927040d42629b9ae417adfbef87afa9f0e79e`.
This source publication does not replace the installed owner assist/motion
previews or enable a route control.

**INFERRED next implementation from existing source APIs:** a first local
trial can remain within one uniquely supported dry polygon, starting at the
new stopped pair's exact package XY. `exact_detail_support` and
`PortalPrecisionView.source_floor_at` provide independent baked/source support;
`SourceFloorChain` plus terrain/static/BSP guards can certify an explicit short
capsule. Generate fresh geometry evidence and a one-segment `FixedRoute`
rather than borrowing the historical plan's coverage hash. Keep heading only
through continuous same-session physical-input observation. If planning
outlasts the fix lifetime, acquire a fresh stopped pair at the planned start;
never refresh old timestamps. No current-position plan has been produced yet.

## Live zone tracking and route reader handoff — 2026-11-14 10:41 UTC

**VERIFIED implementation:** source 0.42.7 adds `owner_zone_tracker.py` to the
actual retained-helper route adapter. It creates a `LocationLogReader` lazily
from helper `read_log()` ticks, after the game window exists. It starts at EOF
and accepts newly appended, catalog-resolved zone entries. It never imports the
old helper's historical `self.zone`, guesses GFay, or replays saved positions.
The binding contains canonical game path, character/server, window ID, PID and
process start ticks. Level changes do not destroy zone knowledge; process,
character and path changes do. This is in-memory same-session state, not a
persistent checkpoint or proof of uninterrupted client logging.

`lease_current_zone()` lends the exact reader to height/route startup, discards
passively observed positions, and pauses passive cursor consumption for the
whole lease, including reentrant helper pumps. The inherited rotation log tail
continues independently. Stop/job cancellation revokes the lease immediately;
passive polling resumes only after borrower cleanup releases it. `RouteSession`
checks an optional exact-reader lease on every operation; route attachment
rejects a competing lease. Competing hotbutton/motion/pointer work cannot acquire
it. Missing providers create no sender, command, capture or movement authority.
No source entry point for owner route execution is enabled by this change.

**VERIFIED checks:** 86 focused cases pass, including actual retained-engine
log handling and no-input route-session handoff/revocation. Three existing
wall-clock pipe movement tests were outside this focused run, not claimed as
passed. `tools/probe_observed_height_bootstrap.py` now sends the copied GFay
fixture through passive zone observation, exclusive handoff, new stopped
positions and the real source-floor height producer. All positions remain
synthetic. Artifact `nav-candidates/gfay-observed-height-bootstrap-0.42.7.json`,
SHA `c20daad6fef7a65e8554ec0fd06d573704c4e5a3e9dafe5c18eaa397ec082155`.

**VERIFIED static query investigation; no client commands executed:** retained
executable SHA `fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`
and resource SHA `0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`
were used. `/who` table `0x140de9480` points to `0x14023c800`, then handler
`0x1402b88d0–0x1402b92d8`; no-argument/all modes send a request. Resources
12316/12317/12318 resemble zone footers, but the current-zone argument source
and response/loading semantics were not established. No trusted footer parser
was added. `/pickzone` only prints its current-zone status in a cooldown branch;
the no-argument available branch can issue a zone-selection request. It is not
used as a query-only shortcut. `/charinfo` reports origin/bind point, `/time`
reports clocks, and `/waypoint` requests a path/map marker without establishing
a current-zone output or autonomous movement. Exact command table bindings and
three handler byte hashes were rechecked in
`client-data/native-zone-query-20261114T104025Z/probe.json`, SHA
`edf2da3c52e47dab11fb595d96dd23060fe3992c19f1c616a3c91f00a4d7baf5`.

**Remaining real-client work:** initial current-zone observation when launched
mid-zone, current scene interpretation, measured motion/body bounds and the
owner route entry are still incomplete. The passive handoff helps only after a
new zone entry is observed in that helper/game session. One read-only Alienware
process check found no `eqgame.exe`; it supplied no current logfile-writer
binding or game-scene evidence. The owner motion 0.39.12 result alone cannot
enable the route. Assist 0.39.13 and passed G0 are unchanged; no new test or
G0 repeat was requested. Current level, XP/hour, deaths and camp remain unknown;
no real 1–20 route, automated level gain or fresh hands-off 1–50 run is accepted.

Source `b5d2be3` is privately staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.7/source`. The remote startup
smoke imports the actual retained **0.39.12** engine and verifies live-format
synthetic zone tracking, level stability, inherited log delivery, exclusive
reader handoff, stop revocation and process replacement. No engine worker,
device, game input or client/prefix change occurred. Archive SHA
`a06c9de121add8243adbf94ef9d29cc04c958059170def12f84074f19974f0db`;
startup SHA `fdaf9e5f130863363c1e858de30f9fa03f5e6776b4b9b37abaf53d421cade103`.
The first startup attempt stopped before engine import because the smoke used
the measurement engine hash against the 0.39.13 assist package. Read-only checks
confirmed both packages match their own entry manifests; the corrected smoke
uses 0.39.12, matching the local route-test base. No helper files were replaced.

## Observed ground-height startup — 2026-11-14 10:29 UTC

**VERIFIED implementation:** source 0.42.6 adds `observed_height.py`, which
creates a current stopped-height correspondence before the route follower
exists. This removes the circular requirement to obtain an aligned route fix
before producing its initial height calibration. The producer uses the same
`LocationLogReader` that will enter `RouteSession`, two consecutive post-release
stopped fixes, the owner/window binding, and the pinned source/mesh observer.
It samples all source terrain layers independently at each printed XY; raw Z
never selects a convenient floor. Missing/layered support, changed geometry,
owner/log identity, stale first or second timestamps and inconsistent offsets
refuse the record. It preserves both raw samples, face IDs, each height offset,
residuals, log identity, route hash and observation times.

The new `ObservedHeightCalibration` keeps `live_verified=False` and is accepted
only in measurement mode. Ground observation, follower, floor staging and
route-session startup consume it without changing that scope. Full-auto,
assist and off refuse this evidence; a mode change revokes the follower.
`RouteSession` pins the calibration object for its lifetime and retains its
JSON-compatible evidence in the run snapshot. Body dimensions, motion bounds,
scene checks and sender authorization are still separate; none is fabricated
from the height fit. Printed coordinate centers and copied source geometry do
not establish live collision equivalence or a universal height correction.

**VERIFIED checks:** 146 focused tests plus 20 subtests pass, including 24 new
observed-height cases. Tests exercise the actual log reader, existing observer,
follower, session and receipt-bound floor staging; no device or game input is
used by the new cases. The existing complete pipe route smoke initially hit a
watchdog-arm refusal, then passed in isolation; a later repeat also refused.
No timing limit was widened. A final bounded pipe diagnostic completed both
segments in ten steps, outcome `arrived`, with final UP/SYN events. This is
synthetic physical feedback through a pipe, not game movement.

**VERIFIED copied-data probe, synthetic observations:**
`tools/probe_observed_height_bootstrap.py` loads the pinned GFay route/mesh and
source archive, writes synthetic client-format replies into an isolated log,
produces the new correspondence, and feeds a later sequence through the actual
ground observer. It takes the zone display name from the copied catalog:
`The Greater Faydark` (also present in the retained owner log), not the shortened
name used by older synthetic fixtures. At the retained route start, source Z
is 63.92649730426629 and baked Z is 64.40511617644279. The explicitly synthetic
actor offset 2.564 prints actor Z=66.49; the producer derives
2.5635026957337033 against source terrain. This is not a current owner reading.
Artifact `nav-candidates/gfay-observed-height-bootstrap-0.42.6.json`, SHA
`cf788c43782c5e7382c5dc22352148849a832c4659565a1af1dbf162c4dcee13`.

**Remaining production work:** current zone/session attribution and the owner
route-entry/scene/motion-provider assembly are not connected yet. Motion 0.39.12
produces an unbound relative estimate, not a zone or guaranteed speed/body bound;
its saved JSON alone cannot activate the route. The retained rotation helper
already reverse-scans zone history, but discards entry time/log/session identity
and can overlook a later loading marker. Do not treat its bare `self.zone` as
current verification. Next: connect current-zone observation and the supervised
route startup to existing helper/session evidence. No new owner test is added;
G0 remains passed, measurement 0.39.12 and assist 0.39.13 remain unchanged.
Current level, XP/hour, deaths and camp are unknown; real 1–20 and fresh 1–50
acceptance remain absent.

Source `345f5e9` is privately staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.6/source`. The remote no-input
startup smoke passed observed-height creation, later ground consumption,
stale-first-sample/owner mismatch refusal and full-auto refusal. Observations
were synthetic; no engine or device was opened. Archive SHA
`de04a95ba440b5fedef57502b376bc8aa760dd5fcaf1c92200cda8311003473d`;
startup SHA `2f58596879eef3b0e1a95924084d87fb7ebff618ec3329a11d1fda01b6ec0443`.

## Actor Z, location text and downward collision query — 2026-11-14 10:17 UTC

**VERIFIED static evidence:** the installed `eqstr_us.txt` was read over SSH
without changing the protected install. Its message 13177 prints the three
`/location` substitutions in order. The handler at `0x14024d280–0x14024d3e3`
formats actor `+0x74`, `+0x78`, `+0x7c` directly with `%1.2f`; there is no
height correction in this output path. Handler source-span SHA:
`e519458ba5ac02a907fd13a20ee90f57453fa34fbd041ad0806128026916a7a3`.
Resource copy: `client-data/location-resource-20261114T101437Z/eqstr_us.txt`,
458,530 bytes, SHA
`0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`.
Its manifest records the complete Alienware source path. This resolves the
previously missing rendered coordinate order; it does not measure current Z.

**VERIFIED static chain:** constructors at `0x1403141c0` and `0x140331a60`
install primary vtables `0x1409c4558` and `0x1409cc468`. Both slot `+0x128`
entries point to `0x140277010–0x140277117`, source-span SHA
`2d81fc4d14476b59eaca20e308e22aff615a09eb96f16759291de4e8ac352d5a`.
The movement clamp at `0x140275e2b` compares `actorZ-offset` with actor+0x38;
when below, it stores `actorZ=actor+0x38+offset`. This offset is state-dependent:

- State byte +0x281 in {0x6f,0x78}, byte +0xb6>=5, or virtual +0xa0 true:
  zero. The live meanings of these states remain unnamed.
- Otherwise virtual +0x110 in {2,9,10}: max(float32 1.9, field158*0.5).
  Other kinds yield 1.9 for finite values; the actual negative-field branch
  multiplies by 0.75 before the maximum.
- A present +0x12c8 subobject may raise a positive offset using its virtual
  +0x88 result. This is not a universal height or simply field +0x158/+0x164.

`0x1402762f0–0x140276380` writes the return of `0x140276d80` into actor+0x38.
The latter uses a downward query with identical first two coordinates and
end Z=-32767. Its size input r is float32(field158*0.1), with exact zero
replaced by float32 0.1. The dispatcher `0x140194700` stores r, r² and 1/r.
After the query, the routine computes `outputZ-r+float32(0.062)`, subject to
cache, Scene predicate, global-threshold and failure-sentinel behavior.
The sentinel is approximately -1e27; it must not become a valid support height.

The point-output getter `0x1405c39c0–0x1405c3a86` does **not** simply return a
triangle surface coordinate. It normalizes `t*(end-start)` and, above length
float32 0.002, retracts that displacement by 0.002 before adding start.
At shorter lengths it returns start. The normalization helper is
`0x1400f5460–0x1400f5524`. The separate region probe still uses its independently
computed `inputZ+(0.25-d)` sample. Consequently no universal `source floor+0.25`
or `source floor+0.062` mapping is established by this chain.

**VERIFIED conditional collision distinction:** the solver's timed-face branch
uses start C, direction V and runtime vector U, then D=V-U and S=C±rN.
Its separate output P=(S+tD)+tU differs algebraically from the original
path point C+tV by the radius/normal term. The actual scalar float operations
retain separate rounding; that algebra is not a bit-exact simplification. However, a zero-relative-motion overlap can return P=C,
t=0, mode=1. Thus contact output and path output cannot be interchanged.
Solver `0x1405c5790–0x1405c641a` SHA:
`fc00eb75c831305052282fd5a4bceb15a2f876023b45bc6e0ba6acb1f6b84543`.
U at `0x140fe6c28` is runtime data, not a verified zero; non-face branches
remain outside this interpretation. **INFERRED:** a swept-radius center path
versus a separate contact result. No universal flat-floor correction follows
without its branch, motion and hit conditions.

**VERIFIED tooling:** source 0.42.5 adds `tools/audit_client_actor_vertical.py`.
It checks whole-file identities, constructor-bound slots, the command entry,
format and resource order, and saves 16 bounded native spans plus constants.
Replay artifact `client-data/native-actor-vertical-20261114T101807Z/probe.json`,
SHA `2b597ed18b1f91c96aa8678b73a452a869eeb9c14404a847a6e8d849295aa886`.
Pinned-source replay, changed executable/resource rejection and refusal to
write disassembly outside the private data store passed. Native code was not
executed and no client input was sent. No conservative route check was relaxed.

**Remaining real-client gate:** owner 0.39.12 hotbutton/motion results and a
current scene/position remain pending. A read-only check found no saved JSON
results in either result directory; it was not repeatedly polled. Actual actor
state/dimensions, dynamics and traversal remain unaccepted. Next: correlate the decoded coordinate/collision relations with the current
source floor and use the owner's measured motion for the first supervised GFay
leg. G0 remains passed, assist 0.39.13
unchanged; no new owner test is introduced. Current level, XP/hour, deaths and
camp remain unknown. This is not a level 1–20 or fresh 1–50 completion.

Source `62d8088` is privately staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.5/source`. Read-only startup
checks verified the installed executable/resource identities, both getter
bindings and all 16 span hashes. No engine or input was used. Archive SHA
`b113ed8d9f3db8e0c062da078ea0dc25a7eafe4de98b521a75e7957c8f3680fa`;
startup SHA `e49ca9be658cfa593c3ca4d3dc3d66821ca5613002b52e3c02def0770e4c5add`.

## Native region callback and actor samples — 2026-11-14 10:10 UTC

**VERIFIED static chain:** retained
`client-data/runtime-20261114T0503Z/eqgame.exe`, SHA
`fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`,
registers callback `0x1401c3170` at `0x1401b2056–0x1401b206a` through
Scene-interface global `0x140fe74b8`, vtable slot `+0x60`. The retained
graphics DLL's actual Scene vtable `0x1803713f0` maps that slot to
`0x1800f8e50–0x1800f8e79`, which passes Scene+8 to `0x1802ba360` and stores
the callback at Scene+0x18. This resolves the previously unidentified caller
callback without executing native code.

Callback `0x1401c3170–0x1401c34a2`, source-span SHA
`4cafdcf861ab108da9438404e807dc38d733dffdb6fca3933aa8bf7d842fc1ca`,
uses case-sensitive comparisons and requires at least four bytes before NUL.
Null/short labels preserve the initial DWORD. Prefixes replace only its low
byte: DR=0, WT/AWT=5, SL=6, LA/ALV=7, VW/AVW=8, W2=9, W3=10.
APK/ATP/ASL set bits 30/31/28. A-prefix branches return immediately. Non-A
labels, including unknown prefixes, also test byte 2 for P, bytes 3–4 for TP,
and (when length>32) bytes 31–33 for M/S/P/F. Thus an unknown non-A prefix
need not leave flags unchanged. ATP and TP paths also write a transition
name; the callback is not universally pure. ATP uses the retained format
`DRNTP00255%05d000000000000000` and numeric input beginning at byte 4.

**VERIFIED actor sample provenance:** `0x140277980–0x140277b86` copies actor
fields `+0x74/+0x78/+0x7c` into point components, passes the point through
movement processing, then calls `0x140277e50`. That routine modifies the
third component by `+0.25 - d` before a Scene predicate and slot+0x50 query.
The constant is float32 0.25 at `0x140910d70`. For fields H=`+0x158` and
J=`+0x164`, its instruction branches give d=0 for byte `+0x281==0x6f`,
d=2H for the successful `693ce0/693ad0` branch, otherwise d=J-H when J>0,
else d=H. The field names and their live values remain unverified: this is
**not** permission to replace a source floor with floor+0.25 universally.

The update also queries the current stored point into actor `+0xac`, and
the point shifted vertically by `actor[+0x6dc]-actor[+0x158]` into `+0xa8`.
Both use wrapper `0x1401b0ba0–0x1401b0bd2`, which supplies fallback 0; its
optional status reports a signed-negative classification, not missing BSP.
Other callers sample different offsets (including third component minus 1
and a separate derived coordinate plus 0.01). No universal feet/head height
or live actor dimensions follows from these static fields.

The lower query's low byte reaches `0x140336d30`, which stores state at
actor `+0xb5` and conditionally selects audio IDs 99/100. The bounded downstream
chain reaches Miles audio playback. **INFERRED:** region transition sounds.
Sound assets and numeric enum names remain unverified; this is not a dry-ground
or walkability predicate. The first unwind range is not the complete function.

**VERIFIED implementation:** source 0.42.4 adds `client_region_labels.py` with
the raw flag model and recorded transition-write intent; it performs no global
write or transition. ATP numeric conversion/formatting is explicitly outside
the model. Its copied WLD map preserves later-record precedence, distinguishes
valid untyped regions from missing tree children, and requires contiguous
native 0x29 record indices. Existing structural/empty-label restrictions and
conservative route policy remain unchanged. Fifty-five focused cases pass
across label/map decoding, native-style point lookup and the existing region
audit, including an additional noncontiguous-index refusal check.

**VERIFIED retained evidence:** `tools/audit_client_region_labels.py` reproduces
ten native spans and the three copied flag inventories. Output:
`client-data/native-region-flags-20261114T100825Z/probe.json`, SHA
`4d39a3febb5878b1df2c378ea0f21530a720483fac5ad4c603341d42287add36`.
The flags below start with initial DWORD 0; untyped counts are separate and
do not establish dryness.

| Copied zone | Regions | Flag 0x5 | Flag 0x80000000 | Untyped |
| --- | ---: | ---: | ---: | ---: |
| Butcherblock | 3,653 | 163 | 5 | 3,485 |
| Crushbone | 2,695 | 263 | 3 | 2,429 |
| Greater Faydark | 2,905 | 0 | 9 | 2,896 |

All three have contiguous type records. Client assets, labels, maps and native
disassembly remain outside git. **Next:** bind the actor's physical vertical
offsets to its actual query/collision path, and use pending owner motion/current
scene for the first supervised GFay leg. G0 stays passed; assist 0.39.13 and
measurement 0.39.12 remain unchanged. No live route, XP gain or fresh-character
run is accepted; current level, XP/hour, deaths and camp remain unknown.

**VERIFIED private staging:** source commit
`f0523e94427afe6311a24342b751dae364e20299` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.4/source`. Archive SHA
`979a48d936448a048394876ddc3ef2b08fe474e72e221c9d1eee3edf55caba45`.
Remote no-input startup passes case-sensitive flags, marker positions,
transition-intent recording, copied type precedence, untyped-region handling
and missing-child distinction. Startup SHA
`d4d67ccd5479325a475f8c797d44f571975c71bb82f53654ce025c6692026860`.
No engine was constructed and no native client code was executed.

## Installed-client BSP lookup resolved — 2026-11-14 10:02 UTC

**VERIFIED static evidence, not native execution:** the retained
`client-data/font-runtime-20261114T0706Z/EQGraphics.dll`, SHA
`4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168`,
contains the actual WLD loader and tree conversion/query chain. Source 0.42.3
adds `tools/audit_client_bsp_static.py` to reproduce eleven bounded disassembly
spans without loading the DLL. Evidence is under
`client-data/bsp-native-query-20261114T100048Z/probe.json`, SHA
`725c1e04894c28bd67747245e3f31e1c6209c894adc36bd3b9a70eb154d4953a`.
All client disassembly remains in the private data store.

- WLD reader `0x1802bf3a0` checks magic `0x54503d02`, reads the 28-byte header,
  decodes the existing XOR key and produces 32-byte fragment descriptors.
  The accepted version tests are `(version & 0xffff0000)==0x10000000` or
  `(version & ~1)==0x15500`. Its error `-1` concerns loading, not region lookup.
- Conversion `0x1802c03f0–0x1802c0856` calls the 0x21 tree expander
  `0x1802c0860–0x1802c0b4f`. Each 28-byte source node becomes a 48-byte
  runtime node; source child zero becomes null, otherwise the child pointer
  is `nodes + 48*(reference-1)`. `0x1802bc750` installs tree pointer/count at
  runtime `+0xa8/+0xa0`. The conversion has five chained unwind ranges:
  its first `.pdata` end `0x1802c0408` is **not** the function end.
- Point lookup `0x1802bc5f0–0x1802bc719` first requires strict interior of
  runtime bounds expanded by float32 **2000**. Outside returns `-1`.
  Inside, a null root returns the distinct value `1`. Otherwise a nonzero
  node region reference returns `reference-1` before testing children. Scalar
  `MULSS/ADDSS` evaluates `y*ny + x*nx`, then `z*nz`, then split, with separate
  rounded operations. A nonnegative result, including zero, takes child
  `+0x10`; negative takes `+0x18`. A null child returns **-1** at `0x1802bc6e2`.
  Query source-span SHA:
  `cb27263a07676da173d04e454eae75f84e58dcb235cdd47634ca0fb6fc923c11`.
- `0x1802bcce0` initializes the region-to-type map to `-1`, then applies the
  zero-based IDs listed by 0x29 records; later overlapping records overwrite
  earlier entries. Label consumer `0x1802bc510–0x1802bc5ce` returns null for
  query `-1` or an unassigned type. Null root and missing child are different.
- Scene wrapper `0x1800f78c0` forwards its point unchanged and returns its
  caller's fifth DWORD argument when no label/callback exists. `0x1800f8c40`
  has an unclassified numeric-zero default and separate AFG-volume logic.
  A nine-point caller `0x1802bd290` samples center/eight extent corners and
  skips callbacks for query `-1`; valid untyped regions instead invoke its
  callback with a null label. None of these facts identifies missing space
  as dry. The upstream actor coordinate/height and classification callback
  installed at Scene `+0x18` remain unresolved.

**VERIFIED implementation:** `client_bsp_probe.py` is a separate copied-tree
diagnostic. It models the tree suffix after the native bounds gate, assumes
normal binary32 round-to-nearest/even arithmetic, and explicitly leaves live
MXCSR, bounds and actor position unverified. Subnormal/overflow arithmetic,
cycles and visit limits return model refusals; they do not invent native
results. No route policy or closed-volume test is relaxed. Read-only native
comparison found no concrete mismatch within this declared scope.

**VERIFIED checks:** 60 focused tests pass across the new point model,
conservative volumes, exact clipping and WLD regions. They distinguish null
root/child, zero/negative-zero, region-before-children and intermediate
rounding; a point resolving above the floor still cannot clear a thin unknown
volume below it.

**VERIFIED copied-data comparison:**
`nav-candidates/crushbone-client-bsp-points-0.42.3.json`, SHA
`76612457b311046e2bb964678f818ac8eda844a9549dae535b31e3cf639d260e`.
All **926** centroids of the first-reported ordinary-cell null volumes still
return missing child. Of **9,578** vertex samples, **5,136** return missing
child and **4,442** resolve a region. These finite samples are not exhaustive
volume classifications and resolve none of the route refusals. No height
tolerance or default-dry interpretation was introduced.

**Next:** identify the actor-position/classification caller, and consume the
pending owner 0.39.12 hotbutton/motion/current-scene result for the first GFay
leg. G0 is passed and needs no repeat. Assist 0.39.13 remains based on the
existing rotation bot. Current level, XP/hour, deaths and camp are unknown;
no real route, automated level gain or fresh-character run is accepted.

**VERIFIED private staging:** source commit
`aee7341a0bf5e391e0fd9943df2ce71dc6aa7065` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.3/source`. Archive SHA
`2863ce50a3cd04e51a36640da2f4f8fb706356866242315564c5cc5c880e9e7b`.
Remote no-input startup passes zero-branch selection, null-root/child
distinction, region-before-children, binary32 rounding and unchanged
conservative volume refusal. Startup SHA
`3250015e2b0bb55e3073c376fed38b3c04636271f9333ef00eb8ef631f4c607b`.
No client engine was constructed or native client code executed.

## Clipped BSP audit of complete source path — 2026-11-14 09:50 UTC

**VERIFIED implementation:** source 0.42.2 adds exact rational clipping of a
closed floor/body polyhedron at every BSP branch. Face, edge and point contacts
remain present, including zero-plane branches. The cap polygon is rebuilt
exactly; missing children, empty regions, labels, cycles and budget exhaustion
remain refusals. The original unclipped API remains available for comparison.
Source body checks can request clipping without changing terrain certificates.

A separate source-step BSP checker verifies the accepted transition digest,
full terrain/static sweep identity, each endpoint's geometry, WLD identity and
recorded phase heights. Lift/settle classify separate support wedges using the
conservative raised height; transfer classifies the exact full stored band,
including its lower collision margins. Every phase is inspected even after
another phase's BSP refusal. Results remain separate from the existing step
and landing hashes; endpoint below-floor BSP is explicitly unclassified.

**VERIFIED focused checks:** 57 pass across clipped volumes, original BSP
volumes, floor binding and step phases. Coverage includes an ancestor-impossible
missing branch, water hidden from corners/centerline, thin unknown layers,
closed point contact after successive clips, sloped floor wedges, exact large
coordinates, cycles/budgets, transfer-only hazards, source/zone/endpoint changes,
and downsteps. Clipping removes the synthetic impossible branch while retaining
all actual hazard/contact refusals. Read-only implementation review found no
concrete face clipping defect.

**VERIFIED copied-client complete audit:**
`nav-candidates/crushbone-clipped-bsp-all-phases-0.42.2.json`, SHA
`23e220cf97d72d75c2db39171222941453ecfb1b80ab8903750b1251c082a224`.
All 1,046 terrain/static cells and seven step transition hashes replay exactly
to the prior final proof. Both unclipped and clipped body checks refuse **926**
ordinary cells with `missing_bsp_child`; **120** pass this BSP-only check. Every
step remains refused: the first failing phase is lift for five and settle for
two. All lift/settle/transfer pieces are retained. Runtime 66.61 seconds.
`completed=true` means the audit ran; `current_path_bsp_candidate=false`,
`route_accepted=false` and `real_client_accepted=false` remain explicit.
Historical 866 counts covered an earlier prefix, not this full current path.

The earlier complete-cell/first-failed-step-phase run is retained as
`nav-candidates/crushbone-clipped-bsp-path-v2-0.42.2.json`, SHA
`9974b633fb9937d1c641f4885423fe2fc9c9bc08d301bd66a0b9963005dd3b8c`.
It produced the same cell/first-step refusal counts, but later step phases
were not visited after a failure. The initial partial `...bsp-path-0.42.2.json`
was deliberately interrupted at 400 saved cells to fix the replay's landing
seed: generated steps must use their original seed, not the first selected
floor ID. It is not complete evidence and no input process was affected.

**VERIFIED first-refusal height diagnostic:**
`nav-candidates/crushbone-bsp-null-heights-0.42.2.json`, SHA
`0f871071b7a6ff71dd4ea3c3da57e1d4bc4c9674563b3ed01d32fbc3d32a9001`.
All 926 first-reported cell null volumes touch the selected source floor. Their
maximum height above it is **0.0076641723357943475** units; 66 exceed .001 and
none exceeds .01. The entrance witness is exactly between floor Z=0 and
`3298535/549755813888` (~0.000006000000212) above it. These are first-refusal
witnesses, not exhaustive classifications of all later branches or support
patches. No unknown region was removed and no tolerance was inferred.

**Next:** determine the installed client's actual position/region query and
absent-child handling. Static analysis follows the reverse-engineer-anything
skill using retained authorized copies; no native execution or client access.
A fresh read-only check still found zero saved owner hotbutton/motion results.
G0 remains passed, owner builds 0.39.13/0.39.12 stay unchanged, and current level,
XP/hour, deaths and camp remain unknown. No new owner test was requested.

**VERIFIED private staging:** source commit
`f314f5c6447fdab70642d9b7e4125d5d6498c57e` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.2/source`. Archive SHA
`20863809c01958b45479a7d962b9b86ec2b9a119519fe7fb305b48e06b31d3aa`.
Remote no-input startup passes clipped-branch precision, thin-unknown refusal,
step BSP phases, source discovery/ranking and prefix isolation. Startup SHA
`b71cdcaeefe38afeb3ec53cc2ac3fb4d8dcc6ed0653fd768ac569b022d0fd01d`.
All seven raised transfer bands pass the new BSP check; their supported
endpoint phases retain the refusals described above.

**VERIFIED bounded static follow-up:** retained
`client-data/font-runtime-20261114T0706Z/EQGraphics.dll`, SHA
`4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168`,
contains a Scene property-registration function at `0x1800f5220–0x1800f5b5d`.
It installs vtable `0x1803713f0`, registers `Marked Region Index` from object
`+0x4e0` at `0x1800f555e–0x1800f5576`, then initializes that integer to `-1`
at `0x1800f59d8`. This is **not** a region-query/null-result proof. The earlier
string match only located property setup; neither position selection nor
absent-child handling has been established.

Root reproduced the bounded `objdump -d -M intel` output and matched SHA
`173233fe7d753d453814fe497d93059d5d38a76ecb9a0065fa1547cae5e2b596`.
It is retained privately under `client-data/bsp-region-static-20261114T095149Z/`,
with `probe.json` SHA
`6216bd271f582e0e96f5244c9916a293570f7875d770a37892b0b794cd2cd1ea`.
Portable REA exports/imports were used; no cached deep-analysis session was
available, and no provider was installed/repaired or executable run. Four DLL
exports include `CreateGraphicsEngine`, but none names a region query.
**Next static trace:** WLD-loader candidate `0x1800f2000–0x1800f2f5b`, following
its world/tree handle; RIP references identify `objects.wld` and `lights.wld`.
No runtime or null-region interpretation follows from those strings alone.

## Automatic source-step continuation — 2026-11-14 09:42 UTC

**VERIFIED implementation:** source 0.42.1 indexes full source boundary edges,
groups exact projected lines, requires opposite floor interiors, and clips
affine height gaps at zero and both explicit step bounds. Valid partial edge
intervals survive over-limit endpoints elsewhere. It generates departure and
landing squares using exact diagonal footprint erosion, retaining the original
expanded footprint. The graph keeps all target height layers; arrival-specific
travel-distance ranking prevents fewest-step paths from choosing impractically
long approaches. Discovery and ranking confer no terrain, BSP or input authority.
Every accepted approach and generated transfer still passes the existing source
floor, complete-riser, lift/transfer/settle and static checks on its own branch.
No source grades, numeric margins or occupancy checks were weakened.

**VERIFIED copied-client run:**
`nav-candidates/crushbone-auto-source-steps-ranked-0.42.1.json`, SHA
`fcc23ce2a7f91a2642c7c482307d62d293d8fd33c31b4c15db2154e94fd90a7e`.
The retained 1,006 cells and two prior steps replay with exact matching proof
hashes. Discovery produces 1,276 directed links. The chosen five-step chain is:
`2459/3 → 2468/0 → 2478/5 → 2482/5 → 2484/0 → 2492/0`.
The first crossing has an affine positive rise; subsequent transitions drop 2,
rise 1, rise 2 and drop 1 source units. Generated cap centers and all details
are in the artifact. Forty additional connector/cap cells pass and reach the
final guide goal `(426.5, 73.97)` in the lower source component. Final proof SHA
`0a49c84e8be0beafc822fda6dc77cc74bf58dd46092cb2ca0f6d15df0103f521`.
Runtime 22.61 seconds. No new crossing was positioned by hand.

This uses radius 1.2, body height 6, maximum step 2 and maximum total lift 4 as
explicit, unmeasured kinematic hypotheses. The complete terrain/static chain
is a candidate; `route_accepted`, `real_client_accepted`, `bsp_classified` and
`game_input_sent` remain false. All 866 historical BSP refusals remain in force.
It does not establish actual step capability, doors, water, mobs or transitions.

The initial fewest-step graph run is retained as
`nav-candidates/crushbone-auto-source-steps-0.42.1.json`, SHA
`ad0695dca5410a89205b1ff6c4f4a137ddccd391003e68676cfca8295a25b5b2`.
It passed two westward crossings then refused an over-80-unit approach; it is
not a successful route. Distance ranking fixes that search-choice limitation
without enlarging the continuous-floor search bounds.

**VERIFIED focused tests:** 71 pass across discovery, step, component, detour,
floor-chain and assist adapter/recovery tests. New geometry cases cover exact
affine clipping, zero-gap rejection, reversed winding/direction, diagonal cap
erosion, narrow intervals, same-side rejection, pair budgets, multiple goal
layers and distance ranking. Generated synthetic caps pass the actual step
checker, while a missing riser still refuses. Read-only math review found no
concrete interval or orientation defect. Actual-engine assist regression and
Alienware startup evidence are recorded below.

**Remaining:** consume the existing owner 0.39.12 hotbutton/motion result and
current scene/zone observations for the first supervised GFay leg; finish BSP
classification on the source path. No accepted real route or automated XP.
G0 passed with the owner's visible-stop confirmation and requires no repeat.

**VERIFIED private source staging:** commit
`ac78e8bc878e36f7ee0b4dcf4045097331084daa` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.1/source`. Archive SHA
`50a9f0c4fdfabfe1ce9f590b0d03e45a5ec4d4148afed6050c3babf5981a18dc`.
Imports, automatic discovery, generated caps, distance ranking, both step
directions, component pruning and parent isolation pass without constructing
an engine or sending input. Startup artifact SHA
`29e8aae74b3cda327858d39c32d961056172aaa58bdc3e03585edf61a742e2ba`.

## Assist gauge lifecycle fix — 2026-11-14 09:39 UTC

**VERIFIED:** owner preview 0.39.13 builds on the retained 0.39.6 rotation
engine and command restrictions. The old engine preserved HP/mana after OFF;
its idle loop advanced the sampling timer without reading gauges. An inert
actual-engine fixture reproduced OFF → F8 → `/alt activate 6001` from cached
20% HP, with no intervening gauge sample. The new adapter clears HP/mana before
stop cleanup, before an inactive arm, and on all settings changes, and makes
sampling due. It preserves rotation timers and explicit F10 healing.

The actual-engine regression passed on Devbox and Alienware: old failure
reproduced, stale automatic heal prevented, a synthetic fresh low sample
restored support, inactive calibration/character changes invalidated readings,
stale queued starts remained refused, and F10 sent only `/cast 1` to an inert
recorder with HP unknown. No worker, device, capture or game input was created.
Focused adapter/recovery tests: 31 passed, including release failure.

**VERIFIED private staging:** `owner-assist/0.39.13` is installed separately on
Alienware; archive SHA
`7e4f98f831020d9449ac2a512a4816f4a4cde1b820a0965ad05b0da41eb04209`.
Source guard and offscreen GUI startup pass; the inspected screenshot shows
ASSIST OFF and travel unavailable. Startup record SHA
`2e4a67881a27da46b7c3d2ee274ece94f50e6781075673252b528f33248b35ae`.
HOWTO contains the new assist launch command. Measurement 0.39.12 is unchanged.

**Limits:** this fixes cached observation lifetime, not active-character,
current-layout or frame identity. Live HP calibration and chat/target behavior
still need owner acceptance. No automated XP, real route or level milestone
was produced. G0 remains passed with explicit owner visible-stop confirmation;
no repeat is needed. A 09:36 UTC read-only check found zero saved hotbutton and
motion records; no helper was started or owner session interrupted.

## Explicit source-step transitions — 2026-11-14 09:30 UTC

**VERIFIED implementation:** source 0.42.0 keeps ordinary exact-edge floor
continuity unchanged and adds a separate conditional lift/transfer/settle
checker. It requires committed departure and independently checked landing
caps, exact complete support projection, opposite-side source edges and full
vertical riser coverage. The two source edges may have different lengths.
Ramp endpoints use a conservative sweep height derived from their minimum
support heights. Lift/settle retain the original below-floor/numeric margins.
Transfer classifies every terrain/static face, including both support floors
and the riser, without exemptions. Touching its body band rejects the move.
A passed landing has reason `conditional_step_landing_only`, no invented
ordinary edge joins, and a proof hash bound to the old prefix and step record.
The parent chain remains unchanged. This is a kinematic hypothesis, not verified
client climbing, jumping or input authority; BSP remains separately unclassified.

The new exact-edge component precheck overapproximates ordinary floor
connectivity, including ambiguous edge branches. It retains all goal height
layers and does not select one by nearest Z. Different components prove a limit
of the current continuous-floor model, not physical disconnection. Full swept
terrain/static checks still decide every attempted connection.

**VERIFIED focused checks:** 33 tests pass across step, component, detour and
floor-chain modules. Cases include ramp endpoints, both step directions,
complete riser/support requirements, missing/too-narrow landing, transfer-only
wall, lift-only and settle-only ceiling, source changes, explicit height limits,
branch isolation and linked suffix continuation. Independent read-only review
found no concrete geometry, rejoin or false-disconnection defect.

**VERIFIED copied-client probe:**
`nav-candidates/crushbone-source-steps-and-components-0.42.0.json`, SHA
`2f4c9a42e293ce4ffcf86d2604f6f88dca31ed48fd843de3c92339aa9ce16f49`.
The tool replays all 982 prior terrain/static cells and matches their exact
proof hashes, then checks source-backed approaches and these transitions:

- Up 5/16 unit at the copied 1528/1538 riser. Body radius 1.2/height 6,
  maximum boundary rise .5 and total-lift hypothesis 1.0. Transition SHA
  `79d2b339f514f7757495c4a1844a4e706206862c2414cbdf389ee35d2d1876dd`.
- Down 3/32 unit at the 2489/2485 lip. Same body, rise and clearance settings,
  with an explicit total-lift hypothesis 2.5 because of the sloping endpoint
  footprints. This is not a measured client limit. Transition SHA
  `dcf5d6efdc54118487b1c5e62c9897d58c09072d8b054af7e400283f1a3940b0`.

Both phase checks pass with the actual riser surfaces retained. Six subsequent
connections to guide points 154, 155, 156, 162, 163 and 164 pass; each has a
checked connector and endpoint. Component checking skips 157–161, which return
to the prior western floor. Goal 165 still reaches the bounded search time
limit; that timeout does not prove an obstacle or global disconnection.
The complete source view has 6,549 eligible faces and 576 overapproximated
continuous-floor components. Runtime was 27.46 s. Whole-route and real-client
flags remain false, and the 866 historical BSP refusals remain in force.

The earlier first-step-only probe is retained as
`nav-candidates/crushbone-source-step-0.42.0.json`, SHA
`ec641b5a4819601b283912114f68e728d028cac8bdf698f62ee4d867f32c8d70`;
it passed the first step but timed out trying the next ordinary-floor leg.

**Remaining:** automatic source-step discovery and continuation beyond waypoint
164, plus current real motion/scene/zone binding and client acceptance. No game
input, login, character mutation or automated XP occurred. Level, XP/hour,
deaths and camp remain unknown. Existing assist 0.39.6 and owner measurement
0.39.12 are unchanged; G0 remains passed and requires no repeat.


**VERIFIED private staging:** source commit
`8e916b2e548652729de11808bd9880f3bca340e3` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.42.0/source`. Archive SHA
`a47ffa7b1fdfa1bdf566245db3f7f8191667c42bd9b18897ee51a3f2fda0ffb0`.
Imports, both step directions, component pruning and parent-prefix isolation
pass without creating an engine or sending game input. Startup artifact SHA
`68cff203b87466e8321ab426daada0074f26f64486c4a9b58caa06a02d3d456d`.

## Automatic source-floor detours — 2026-11-14 09:19 UTC

**VERIFIED implementation:** source 0.41.99 introduces a bounded local A*
search using the copied terrain/static views. Every edge checks its complete
swept square and a stationary endpoint square. The source-floor chain forks
from an accepted prefix; failed terrain/static branches never replace it.
Node keys include exact lattice coordinates and selected source identities.
Canonical endpoint footprints preserve that key's geometric meaning; queued
records retain independent proof ancestry when a better visit is found.
An arbitrary downstream guide point is rejoined through the same complete
sweep check, without reseeding. BSP and real movement remain outside this
planner's result. No radius, body height, source grade or clearance was relaxed.

**VERIFIED checks:** 21 focused source-chain/detour tests pass. These cover
thin static-wall bypass, full turn footprints, failed-branch isolation,
blocked/budget-limited search, separate upper/lower floor selection, arbitrary
non-grid rejoin and continued suffix proof ancestry. No partial route is
returned on exhausted budgets. CLI/module compilation and diff whitespace
checks pass. Independent source review found no concrete branch/rejoin defect.

**VERIFIED actual copied-client probe:**
`nav-candidates/crushbone-auto-source-detours-0.41.99.json`, SHA
`94116bdf777333bb875e537e450818950a4683b0ffd4965b002a0607689002c8`.
Run with `tools/audit_crushbone_source_corridor.py --auto-detours` and the pinned
approved inputs. No manual polygon-440 repair flag was used. Three searches
bypassed obstructions at guide segments 70, 72 and 149 and rejoined waypoints
71, 74 and 150. Their successful searches expanded 2, 1 and 2 nodes. The low-deck
midpoint attempt timed out before its next downstream rejoin succeeded.
All 982 retained terrain/static cells pass, their indices run 0–981, and every
stored proof links to the preceding accepted proof. Four rejected guide cells
are retained separately. Full route flags remain false; 866 BSP refusals remain
recorded and are not cleared by detour success. The bounded run took 107.64 s.

**Remaining source-route limit:** the next failure is segment 153/division 16
near polygon 3954. Four downstream rejoin searches hit their eight-second
budgets; those timeouts do not establish global disconnection. Independent
read-only geometry review identifies a separate 0.3125-unit riser: source
1528/4 ends at Z=-0.3125 and the adjacent east floor begins at Z=0, with vertical
riser faces 1528/1–3. The current equal-3D-edge, grade≤1 connectivity model reaches
1,685 faces from 1528/4 but not east floor 1538/3, even before occupancy checks.
This needs an explicit step/ledge-transition model or another supported route;
additional search time alone cannot create the missing connection. The same
component review found none of the four attempted rejoin floors in the carried
component (6,549 total eligible faces), so a future component precheck can avoid
those repeated searches. This is model disconnection, not physical impossibility. Actual
client step capability is unverified, and no stair acceptance was inferred.

**Owner/live state:** the read-only Alienware listing found zero saved location
hotbutton and motion results. Owner candidate 0.39.12 and existing rotation
preview 0.39.6 stay unchanged. G0 is passed and needs no repeat. No game input,
login, character mutation, accepted 1–20 route or automated XP occurred. Current
level, XP/hour, deaths and camp remain unknown. Continue step-aware source
planning and consume the existing owner motion/current-scene test when present.


**VERIFIED private source staging:** commit
`36217ccabdfb9b8ea08c4f67e6006e50bcbe1b49` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.99/source`. Archive SHA
`a456488f04b32faaa1161657e08df05e160837a257fd246d164490c5e1a16e16`.
Imports, checked direct detour, exact-goal suffix continuation and failed-branch
isolation pass there without creating an engine or sending game input.
Startup SHA `2e4e5bd639166e42ee670f49b0597731dd8b957e8ca2989480fa69dc1c8b49b1`.

## Crushbone source corridor diagnostics — 2026-11-14 09:13 UTC

**VERIFIED implementation/tests:** source 0.41.98 adds direct source-step
terrain/static/BSP composition and exact convex-volume BSP traversal. Existing
baked-floor entry points retain their full expanded-prism semantics. The new
`check_source_body_bsp` separately classifies each selected supporting patch's
closed above-floor body wedge; its result explicitly assumes grounding and
leaves below-floor BSP space unclassified. Original terrain/static below-floor
and numerical margins are unchanged. It is not connected to live movement.
Forty-one focused BSP/static/floor tests pass, including changed-cell refusal,
water in the body, missing children, exact floor contact, nonzero volume and
sloped support. Both diagnostic tools compile and `git diff --check` passes.

**VERIFIED copied-source results:** approved client archives and retained helper
geometry only; no removed working copy was accessed. The probes include 21,834
terrain faces, 9,576 static faces and 178 placements. No baked heights were
flattened. Static inventory SHA
`b49d11674658e30a6df8914c4ba2002df6772f093b859647f05ad43c2842647a`;
terrain WLD SHA
`ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1`.
The copied inputs and code hashes are pinned in each artifact under
`~/.local/share/eql-automation/nav-candidates/`:

- `crushbone-source-body-crossings-0.41.98.json`, SHA
  `b14bed5ed58a855e01eba453280660a708759ec2a727353f9d5215ffad5f9435`:
  four local 658→623 crossings at portal fractions .50/.65/.80/.85 pass all
  three full source cells, including static objects and above-support BSP.
  Each crosses six units, with hypothetical body radius 1.2/height 6 and
  source grade ≤1. These do not establish a whole corridor or real movement.
  The original expanded BSP prism still refuses and is retained separately.
  Crossings at 3244 and 4316 still fail source coverage; 3244 includes an
  actual rock, so its failure cannot be corrected by flattening baked heights.
- `crushbone-source-corridor-occupancy-0.41.98.json`, SHA
  `e1c38747e4545bfab6a9eee8cad8da0a55280a6db31e9b626630b307e9c6a3ca`:
  a 174-polygon graph alternative avoids 3244 and 4316. Its continuous source
  audit passes 519 terrain/static cells, then refuses cell 519 at segment 70,
  division 4, polygon 440: `selected_floor_uncovered_ground_area`. It also
  retains 515 BSP refusals. Both complete-route flags remain false. Continuing
  terrain diagnostics after BSP refusal is not route acceptance.
- Initial entrance-only refusal: `crushbone-source-corridor-0.41.98.json`, SHA
  `39c299da1528c99398a149fa7adaf60ee1b37fddcbee89c5bb8eef1c660a48d7`.

**VERIFIED repaired guide retry:** a source-supported waypoint inside polygon
440 clears the raised corner at unchanged body and clearance settings. Tool
option `--repair-raised-corner` rechecks the full prefix rather than trusting
that local result. `crushbone-source-corridor-raised-corner-0.41.98.json`, SHA
`5776160874ed8952d0f6b3d7aeb728c50c6e341c985262b7812519fe064174e1`,
passes 537 terrain/static cells before a separate body-band intersection at
polygon 510. BSP refusals remain recorded from the initial cell and the route
remains unaccepted. This identifies the next actual source obstacle instead
of repeatedly failing the already understood polygon-440 corner.

**OBSERVED in independent read-only source review:** source face 2014/10 has
Z=0, while BSP node 3652 splits at Z=6.000000212225132e−6 with missing right
child. At historical entrance WLD XY (−424.04, 274.06), positive Z=1e−7
still reaches that missing child; Z=1e−5 and greater sampled heights reach
unlabelled region 1795. Thus this particular refusal is a real source/BSP
plane discrepancy, not an impossible traversal branch or exact-contact-only
case. Exact clipping alone would not resolve it. No tolerance or label rule
has been changed to erase it. Client interpretation remains unverified.

**Remaining:** identify the full corridor coverage failure and a supported BSP
interpretation; consume real owner hotbutton/motion/current position/zone
observations for the first supervised route leg. The already staged 0.39.12
helper and HOWTO test are unchanged. G0 is passed and does not need repeating.
No client input, login, current-level observation, automated XP, whole 1–20
route or fresh-character 1–50 acceptance occurred. Level, XP/hour, deaths and
camp remain unknown. Existing assist 0.39.6 still uses the earlier rotation bot.


**VERIFIED private source staging:** commit
`ba64f91c0c6ccd075829fcf5573be7e967678d18` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.98/source`. Archive SHA
`b7718ea37f6cd4cf5dd365a82e3ae8627dac13f4f55ea30b89486b9fbe789f6c`.
Module startup and above-floor volume, missing-child, degenerate-volume and
missing-floor checks pass there. No engine was created or game input sent.
Startup evidence SHA
`3671241bc1cbef5c0cec366abb25231c8138e6a68703adf45a7f646937b60a83`.

## Supervised relative measurement shipped as 0.39.12 — 2026-11-14 08:59 UTC

**VERIFIED implementation:** source 0.41.97 composes the existing helper's
stationary hotbutton test, finite motion collector and actual watchdog sender.
An explicit owner job requires a successful hotbutton result in the same helper
and process/window plus owner confirmation of open flat ground, closed chat,
cleared target and melee off. Four-second focus countdown, seven exact bounded
probes, eight stopped pairs and persistent input/log checks finish with a saved
complete or partial record. F9/F11, queued jobs, focus/settings/session changes,
recognized log hazards and owner activity cancel. There are no retries or typed
fallbacks. Assist still rejects movement. Relative observations use None zone
fields and retain log identity/epoch/sequence/timestamp/transition checks; no
absolute zone is invented. Conditional estimates never authorize a route.

The owner's declaration is **not independently observed collision/chat/macro
clearance**. Read-only review confirmed no owner restriction requires an absolute
zone or per-character pixel recognizer before this explicitly supervised test.
It still does not grant unattended navigation or character control to the lead.

**VERIFIED checks:** collector/reducer checks passed (67 cases). Initial new
wrapper test failures exposed fixture omissions (EV_KEY and require_focus),
which were corrected. The subsequent source wrapper/hotbutton/executor run had
75 passing tests and one complete-run timing refusal. Built candidate imports
passed; its wrapper/manual-observation run had 47 passing tests and two early
timing refusals. At 08:56 UTC the devbox load average was 191.48; load is a
plausible cause, not a proven attribution. All timing limits stayed unchanged.
A standalone pipe smoke initially lacked the preview working directory, so its
watchdog child could not import the package; the smoke now uses the same working
directory as launch.sh. This was a diagnostic invocation issue, not game input.

**VERIFIED on Alienware, no game input:** the actual staged helper/watchdog
completed seven pipe movement pulses and sixteen synthetic position replies;
all keys were released and the engine finished stopped. Two further smokes
cancelled during movement DOWN and before the final stopped pair, preserving
partial evidence and no estimate. Synthetic input/position observations are
explicitly labeled. Artifacts under the approved local data store:

- `evidence/owner-motion-0.41.97-complete.json`: SHA
  `71abacec984b164cd79ea20d14a18f6b578838929fdd6d7de4cf593e64a8c0aa`.
- `evidence/owner-motion-0.41.97-motion-down.json`: SHA
  `ac297ce1697547cdb0830c65cd522c5e36bd17687549968c56d020ecf2099307`.
- `evidence/owner-motion-0.41.97-final-pair.json`: SHA
  `ae5a5373c40368b84509ecf7134a0c77f5a5cc0d1be7ab3ab89ffbe3163f01b2`.

**VERIFIED private staging:** `owner-assist/0.39.12`, archive SHA
`3ca6f6e3ae1891e5a8a72d61c8f1895e595836b37b581afe33c38e0e29cdc27d`.
Pinned imports/reserved-key refusal and actual Qt offscreen GUI/dialog checks
pass. Dialog starts disabled, confirmation enables it, unchecking disables it;
smoke rejects it with no worker. GUI screenshot inspected, both test buttons
visible. PNG SHA `a660b95a39fd774af60b9e1f0c4b51818f8b86781cbf2bdf29d127b6ce1ea301`;
metadata SHA `2dc2fb0c753f3ef123b5214c1cad57570b1b74640243d2e25dcc1c3e68a8cf16`.

**Remaining real-client gate:** owner runs hotbutton then motion measurement
in the same 0.39.12 helper session, per HOWTO. Current scene/zone/height and real
motion feedback still need binding to the first supervised route leg. No real
1–20 leg, automated XP or fresh1–50 run has been accepted. G0 passed from the
trace plus owner's visible-stop confirmation; no repeat. Metrics remain unknown.

**VERIFIED source staging:** commit `a1d53019c6acc45104f825bc86916fd90b18bba8`
is staged at Alienware `owner-tools/0.41.97/source`, archive SHA
`af9ca6832b0a19a574387356ab2a0d22db86d77ae2f5cf762570e21fa537b64b`.
Remote imports, retained-engine composition and reserved-key refusal passed
without constructing an engine or sending input. Startup SHA
`6c1d6b93c8534a7b39c060c866307e3ddd370bfb7d0218ed4965d66f2c1030f8`.

## Stationary hotbutton test shipped as 0.39.11 — 2026-11-14 08:45 UTC

**VERIFIED implementation:** source 0.41.96 extracts the existing hotbutton
transaction into `location_hotkey.py`; the route executor and the new owner
setup test both call it. The owner selects an already configured nonprinting
key and explicitly confirms that it invokes only `/location` in this session.
The measurement GUI has no default key and does not enable Test once until
selection and confirmation are present. The test initializes the sender,
pumps pending stop input, checks the unchanged owner request, then starts a
four-second focus countdown. One 20 ms key cycle is followed by a bounded
single fresh-log-reply check and a short duplicate-observation interval.

F9/F11, queued jobs, settings/session/focus changes, owner input during dispatch
or reply collection, log replacement/transition, timeout and duplicate replies
stop the operation. A busy marker prevents recursive ticks from sending again.
There is no retry, fallback typing, Escape, movement, target change or combat
command. The owner-confirmed macro contents are not mechanically verified;
observing a fresh location is temporal correlation, not a client request ID.
All outcomes finish stopped. JSON records contain the owner declaration,
saved-config hashes, window/process identity, pulse/cleanup record and raw fix,
under `~/.local/share/eql-automation/location-hotkey-tests/`.

**VERIFIED focused checks:** 46 source tests passed for setup and route paths,
including prior-stop rearming, F9 during sender initialization/countdown/DOWN,
reply-before-UP, no retries, device replacement and complete fixture travel.
The first run exposed a stale `self.owner_input` reference during extraction
into the shared function; it failed before DOWN and was corrected. The built
0.39.11 adapter then passed 48 setup/manual-position tests. The first attempt
to run those from the minimal bundle could not import route-only fixture
dependencies; adding the source tree as a test-only package fallback allowed
collection while retaining the bundled adapter/sender. No extra runtime
dependency was added to the owner package.

Saved built-candidate fixture result:
`evidence/owner-location-hotkey-test-0.41.96.json`, SHA-256
`cdd74a72163d5b30964b8084c212429ef0cac365aa91ad3e85528e6a6b05e0af`.
This is synthetic owner setup/input observation and a fixture position reply;
the retained engine and watchdog use pipes, not a game device.

**VERIFIED private staging/startup:** Alienware path
`~/.local/share/eql-automation/owner-assist/0.39.11`. Archive SHA-256
`b4436eaf7c69aec24ff4d40ec4ea9ecc3f4185bb0d8983d3b1d79af483fa4be1`.
Source guard, imports and reserved-key refusal pass. The actual helper GUI
rendered with Qt offscreen and its input worker disabled. The new test button
is visible/enabled; the actual dialog starts without a key and keeps Test once
disabled until explicit selection+confirmation. Removing confirmation disables
it again; F9 is not offered. The smoke rejected the dialog without posting a
test. No game window, account or character was opened or controlled.

GUI PNG SHA `54cbff33213b79fe20fe499e5e8e029041be1963eb4559f30744d4e5f7a001cf`;
GUI metadata SHA `754f77d2966a13e2eae5ff243d2645019bd156d17a6f40962ab85dc8a6d3c3ab`.
The helper screen was visually inspected; the new button is visible, with
horizontal scrolling available for the longer existing measurement row.
These are helper UI checks, not EverQuest screenshots or live acceptance.

**Remaining real-client gate:** the owner configures/verifies the single-command
hotbutton and runs this stationary test himself. HOWTO gives the exact launch
command and controls. No live hotbutton reply has been collected. The subsequent
first route still needs current scene/zone/height/motion bindings and actual
movement/arrival evidence. Assist 0.39.6, manual observation 0.39.10 and G0's
passed result remain available; no G0 repeat. Level, XP/hour, deaths and camp
remain unknown for a real automation run. Task 829a00229b29 is not complete.

**VERIFIED source publication:** commit `57a7f20c7c45d229fff4d49c6cadb4ac8f1bd0f0`
is staged at Alienware `owner-tools/0.41.96/source`, archive SHA-256
`353f1af83d103f28035aca254950aca745afbbbf715f00d2691d92c83a6d23e8`.
Remote source imports and reserved-key refusal pass without constructing an
engine or sending input. Startup artifact SHA-256
`9404a1ee7b4a7f229b97b333f6c73e7c60e8cf4919bc7d3de66d2988b10f5a6c`.
Private staging record: `releases/eql-automation-0.41.96-staging.json`.

## Private source 0.41.95 staged — 2026-11-14 08:37 UTC

**VERIFIED:** source `34cdcd110e8f6cb05aed338aa33c8457ad60e54f` is staged at
Alienware `owner-tools/0.41.95/source`; archive SHA-256
`fe1a5af676699981de33d44dcd64e2f3e9055a67b74696d7550f2699eef8e6b7`.
Remote imports and refusal of a helper-reserved key, absent owner setup and
absent route pass. No engine/device was constructed and no input/capture ran.
Startup artifact SHA-256
`8bd80d09c65aa7fc20443a7acde15165e6ed4786319276dd7fe5650fdcf60fb5`.
Staging record is in the private `releases/eql-automation-0.41.95-staging.json`.
Assist 0.39.6, stationary observation 0.39.10 and F11-off remain unchanged.

## Hotbutton route-position option and access reconciliation — 2026-11-14 08:36 UTC

**VERIFIED implementation:** source 0.41.95 adds
`route_location_hotkey.RouteLocationHotkeyExecutor` to the existing
`RouteSessionDriver.request_location` interface. It uses the existing sender,
reserved operation and duplicated descriptor, a 20 ms watchdog pulse, original
F9/focus checks and the existing complete owner-input observer. Full binding
checks run after callbacks as well as before them. Cleanup releases the pinned
original descriptor even when the current sender/device is replaced. No chat,
Escape, Enter, target, movement or recovery command is part of this query.
The route's existing exclusive log reader accepts or refuses the subsequent
fresh single reply; the key receipt never asserts a client effect.

The owner must supply a configured/tested nonprinting function key and a
same-session setup record. F6–F12 (helper controls), printable keys, arrows,
Enter and Escape are excluded. Saved configuration hashes detect persisted
edits; they do not prove unflushed hotbar/page state or macro contents. Those
remain explicit owner setup assertions, and any owner input stops the route.
No default key is supplied, no client config is written, and no launcher
constructs this executor yet. A stationary owner setup/test is the next
integration step; this release does not claim that path is ready to use.

**VERIFIED tests:** 27 focused cases pass with the actual retained helper and
watchdog, pipe input and fixture logs/scene/geometry. The complete fixture run
finished two segments/nine steps using twenty hotbutton queries and no chat
keys. Missing/duplicate replies stop before movement; a reply printed before
UP remains buffered until the driver installs its receipt. F9 during DOWN and
device replacement release the original pipe; changes during input observation
refuse before DOWN. The initial run had one test expectation error: retained
focus loss raises InterruptedError, not RuntimeError. The assertion was fixed;
the focus-loss behavior already refused input. A post-callback device/focus
binding gap found in review was fixed and covered by two additional regressions.
Private evidence `evidence/route-location-hotkey-0.41.95.json`, SHA-256
`103a42f1f90f1159d242b023b0313c87b00584cdae7ad203561bce1ddf8bb37d`.

**OBSERVED access/current-client evidence:** rereading owner instructions found
no ban on read-only game-window capture. Historical statements that a turn
did not capture were action reports, not permission denials. The explicit
limits remain no lead login/control of the owner's character, no protected
prefix changes and no access/prompt bypass. Read-only SSH/X11 queries found
zero game windows, no process/session through WindowGate, and zero saved
stationary position pairs; no image or input was taken. A game-window absence
is not evidence of a denied permission and does not justify repeatedly asking
for G0. G0's trace and owner's visible-stop confirmation remain accepted.

Current read-only configuration pins, under the installed EverQuest Legends
directory on Alienware:

| File | SHA-256 |
| --- | --- |
| `eqclient.ini` | `a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc` |
| `Legira_freeport_LO1.ini` | `e2d8d449c7d03fb66493e0caf6a49a29c8ae13cdbfdfe3641f6b286e6ba681ab` |
| `UI_Legira_freeport_LO1.ini` | `5876a4136283b692263bc2826ffc2b12cd7328f4faa320c5f4071f2092fbc76b` |

No `/loc` or `/location` entry was present in those files. The unsuffixed
Legira INIs were absent; the `_LO1` files above are the actual matches.
The configured hotbutton option is therefore not ready for real dispatch.
Per-character caret/selection recognition was a chosen typed-input design,
not an owner rule or a necessary dependency for every acquisition mechanism.
Actual current zone/height/motion/scene and route acceptance remain missing.
No level/XP/hour/deaths/camp can be reported for a real automation run.

## Private source 0.41.94 staged — 2026-11-14 08:29 UTC

**VERIFIED:** source `672d8ebfdee81e8aee5f5665840b872666c8cd80`, archive SHA
`984dadad8d5ea9d32f1b039fe4f76e2f9aabe63c7531ac653753a62cecdb7e8d`,
is staged at Alienware `owner-tools/0.41.94/source`. Startup imports and
missing-source/invalid-mask refusal checks pass. No engine, input device,
game capture or native process was started. Remote startup artifact SHA
`0e227c99ea0aa1327bc9a85b52c03f11abf10c011e291606480f70682b0c5825`.
Local staging record: `releases/eql-automation-0.41.94-staging.json` under the
private store. Client assets/derived pixels were not placed in git or this
source archive; owner launcher versions remain unchanged.

## Geometry-to-pixel font sampling 0.41.94 — 2026-11-14 08:28 UTC

**OBSERVED existing source gap:** the geometry module computed compensated
per-glyph rectangles and a separately rounded caret, while the prefix matcher
still received raw GDI concatenations. Retained shader-key/viewport evidence
supports a conditional projection hypothesis. It does not establish active
font, atlas history, inherited blend/color state or live raster equivalence.
The neutral forced edit border has no demonstrated focus-dependent variant;
an absent caret can mean blink-off. Neither can establish closed chat or
selection absence. These missing booleans are not filled by the new sampler.

**VERIFIED implementation:** `font_raster.py` samples each corrected geometry
quad at pixel centers, with explicit projection offset, tint, pipeline-evidence
pin and output rectangle. Its declared model uses bilinear alpha4 samples and
source-alpha ADD composition of a tinted white texture. Float64 reference
interpolation/byte rounding is not claimed identical to GPU rasterization.
The sampler rejects changed geometry and clipped output. It uses known texels
only inside each glyph's cx-by-cy extent; a nonzero contribution from outside
that extent marks the destination pixel unknown. It does not clamp to a glyph
edge, use arbitrary probe padding, or invent transparent neighboring atlas
cells. Reused transparent DIBs refuse because their interiors lack the required
history independence. Unknown pixels stay conservative through overlapping draws.

`PrefixRendering` now carries an optional immutable 0/255 known-pixel mask.
The matcher computes the intersection over every rendering/origin and scores
all candidates, including blank, on that same set. Unknown pixels cannot
improve one candidate selectively. Extra unexplained ink on known pixels still
counts. Shared-known uniqueness is reported separately; any unknown pixel
keeps complete-field and full-model-match claims false. Text, focus, ownership,
delivery and input authority remain unverified.

The offline importer accepts `--sample-pixels` only with the explicit raster
contract. Sampled images/masks are separate from legacy raw PNGs; it records
code hashes and never alters the owner's installation. Missing options refuse
before output creation. A first smoke using a nonexistent input received the
existing file-stat error; the valid retained-input retry specifically verified
the missing-contract refusal and absence of output.

**VERIFIED checks:** 58 initial sampler/matcher checks passed. Focused parser,
geometry, matcher and reader checks then passed 130 tests under system Python;
22 reader tests skipped for missing NumPy and all 22 passed under the existing
private numerical interpreter. Coverage includes exact texel centers, bilinear
weights, alpha4 conversion, unknown right/bottom neighbors, independent caret
rounding, tint, clipping, altered geometry, shared-mask fairness and blank ties.

**VERIFIED copied-font experiment, not live pixels:** the retained corrected
height-19 clear-each probe (`e4458657…`) and copied font (`83b14d85…`) produced
all 18 prefix/caret cases at base height 15 and scale 1.25, with explicit +.5/+.5
projection, white tint, full alpha and the retained shader-key evidence pin.
Unknown output counts range from 23 to 247. Every generated comparison frame
was synthetic, including deliberately different values in unknown pixels.
All 18 comparisons distinguished the expected prefix on 11,045 shared known
pixels, while complete-field comparison and live equivalence remained false.
This is model self-consistency plus independent arithmetic tests, not actual
GPU/client comparison or acceptance.

Private artifacts under `~/.local/share/eql-automation/`:

- `font-probes/sampled-arial-19-0.41.94/manifest.json`, SHA
  `da3d84a9bf006fa241968a8fde2a6db6428e287ba7b8fb703be8386c3e422e0f`.
- `evidence/sampled-font-matcher-0.41.94.json`, SHA
  `8a1744f0cbe9ec54f0909f8f4b7874d19f87d137fa30e16b0de3b38373b907de`.

The prior turn implemented phase-aware command evidence composition; this turn
connects its text-analysis dependency to the corrected source geometry. Current
owner pixels, closed/focused/selected chat discrimination and calibrated target/
combat classification still gate input, alongside zone/height/motion/body bounds.
No game/native process, capture, login or input ran this turn; no prefix or
character changed. G0 remains passed and needs no repeat. Assist 0.39.6 and
observation 0.39.10 are unchanged, with the existing stationary observation
pending. Level/XP/hour/deaths/camp remain unknown; no playable 1–20 or fresh
hands-off 1–50 acceptance exists.


## Private source 0.41.93 staged — 2026-11-14 08:20 UTC

**VERIFIED:** source `67d51602343b6bfd8d773c2b448ba2d0a9c80061`, archive SHA
`33b9be5574ec9491a28a5edd7a740b13dcabde6663da549543d003906fa1b937`,
is staged at Alienware `owner-tools/0.41.93/source`. Startup checks pass for
imports, unknown UI defaults, missing independent dependencies and wrong-phase
refusal. No engine/input device was constructed and no game capture/input ran.
Remote startup artifact SHA
`cec11d717fe0582ee62233cd2cfd3920ea4cbce8534386e256d4398498fc2d8a`.
Local staging record: `releases/eql-automation-0.41.93-staging.json` under the
private store. This is a source build; owner assist/observation helpers are unchanged.

## Phase-aware command observation 0.41.93 — 2026-11-14 08:20 UTC

**VERIFIED implementation:** `CommandInputProvider` supplies the concrete
`check_input(request, phase, submission)` composition for both checked location
executors. It validates the fixed `/location` write history and exact snapshot
identity; observes current focus/process, owner input and a separate non-replaying
log veto around a new independently classified frame; and preserves the oldest
observation timestamp with a maximum 100 ms lifetime. It never polls the route's
exclusive location reader. The existing movement provider still requires closed
chat; only the command provider accepts an independently verified open draft.

Start, first key and end require observed closed chat and an absent draft.
Intermediate keys require the exact complete visible prefix, focus, insertion
point at the end and no selection. Default/unknown fields, ordinary frame
candidate dictionaries, copied snapshots, arbitrary commands, stale captures,
owner activity, changed focus/process/generation and positive log vetoes reject.
The command classifier remains an explicit missing dependency; this code does
not infer it from engine flags, font hypotheses or blank pixels.

**VERIFIED checks:** 98 focused provider and existing safety tests passed;
five cases passed through the actual retained command sender and route executor
on a pipe. A final two-test check covered the shared collection entry and clearing
old evidence on a missing classifier. Two retained evidence cases were then
saved: the complete ten-key command emitted 40 events and left no draft or held
keys; a new native-melee-on log event after three keys stopped after 12 events,
without Enter, with all keys released and the draft explicitly uncertain.

Artifact `evidence/command-input-provider-0.41.93.json` under the private store,
SHA `63643b05d98bcd7c9ef7dfdeebffcd2084fdc5025333c4932cae6bf0d56ec5af`,
retains actual command journals, pipe events, fixture log-veto results and source/
retained-helper hashes. UI/physical-input observations and the scene were
synthetic. No game input, capture, login, character/prefix mutation or owner
helper replacement occurred. This verifies composition and refusal behavior,
not real-client text/focus recognition or acceptance.

The previous turn made concrete progress with receipt-bound source geometry.
This turn replaces the remaining synthetic-only command evidence composition
with its concrete provider. The next implementation gap is calibrated frame
classification for chat focus/closure, target absence and combat state, using
current owner pixels; motion/body and zone/height bindings are also unverified.
The existing stationary observation remains pending. G0 is passed, assist stays
0.39.6 and observation stays 0.39.10. Current level, XP, XP/hour, deaths and camp
remain unknown. Neither the playable 1–20 nor fresh 1–50 objective is met.


## Private source 0.41.92 staged — 2026-11-14 08:15 UTC

**VERIFIED:** source `b9914381b5d233d47dc98cdc806e2b3964cbaf58`, archive SHA
`75a798e9e873daecf7441da0c3873e1e45a1de610089f23d28dcd4fb8c7eb2bf`,
is staged at Alienware `owner-tools/0.41.92/source`. Remote startup imports
pass, external bounds remain mandatory, missing dependencies refuse, and the
route location executor still has no movement method. No engine/device was
constructed and no client capture/input occurred. Startup artifact SHA
`03316f59681d8cac9f3536d24543f7d7591235e83bcaf7ed648c35ade706574a`.
Local staging record: `releases/eql-automation-0.41.92-staging.json` under the
private store. Owner launchers and the existing pending observation are unchanged.

## Route geometry preparation 0.41.92 — 2026-11-14 08:14 UTC

**VERIFIED implementation:** `RouteGeometryPreparer` now supplies the concrete
route callback previously represented by test closures. It uses the copied
mesh/source floor, complete transformed static inventory and BSP volume checks.
Externally supplied speed, maximum actual hold, heading/position error, drift,
pivot displacement and body dimensions bound the swept footprint. Request
sizing never replaces the maximum-hold bound. No live measurements or default
body assumptions are inferred from G0 or the replay.

The first uncached synthetic measurement took 70.4 ms, exceeding the existing
50 ms proposal lifetime. Preparation now computes forward/pivot candidates
while stopped, before watchdog arming. It releases the shared stop lock while
performing exact arithmetic; OFF can revoke immediately. A one-use result is
bound to the exact reference object, floor chain, controller, source identities
and bounds. Only the newly proposed control selects its own successful trial.
The final stage still checks the original 50 ms deadline and the stopped
reference still expires at 0.5 s. No timestamp is renewed. Ticket-bound terrain,
static and BSP records remain available only while that ticket is pending and
its context matches. Neither those records nor the cache authorizes input.

**VERIFIED checks:** 28 final focused checks pass, covering the complete
actual checked sender/watchdog on a pipe, wall and water refusal, pivot drift,
context/source mutation, stale preparation, cross-thread OFF and one candidate's
query refusal without substituting it for another. Scene/motion/body/position
values in those tests are synthetic. An earlier combined run had 54 passes and
one timed sender test refused before DOWN rather than reaching its intended
post-DOWN revocation point; that exact test's focused repeat passed. No timing
limit was relaxed, and the original failed run is not claimed green. Earlier
geometry/underlying coverage checks passed 99 tests before the final cache
binding/cancellation refinements.

**VERIFIED copied-data diagnostic:** the final implementation recomputed the
first GFay route cell using the owner's copied archive, mesh and complete static
inventory. Both preparation and fresh staging succeeded: 52.8 ms for preparation,
2.39 ms for staging. The synthetic body/motion/height assumptions are explicit
in the private artifact. No input descriptor, game capture or live character was
used. This proves one conditional source cell, not route acceptance.

- Evidence: `evidence/route-geometry-source-final-0.41.92.json`, SHA
  `03f4b8c9babd4ea3d9dd0f20a368339e918613f32115ce62877bdc6863813c2d`.
- Reproduction recipe: `evidence/route-geometry-source-final-0.41.92-recipe.py`
  under `~/.local/share/eql-automation/`; generated client geometry stays out of git.
- The old replay recipe refused changed code pins. The new diagnostic verifies
  the retained client/helper files and metadata, records three changed recipe
  module hashes, uses the old evidence only for its hashed seed coordinates/IDs,
  and recomputes the initial floor and new candidate using current code. It does
  not silently adopt the historical whole-route result. Complete static
  inventory identity/face count and BSP coordinate frame were rechecked.

**OBSERVED:** the owner stationary-observation store contained zero pairs at
08:09:32 UTC. G0's trace and owner visible-stop confirmation remain accepted;
no repeat is needed. Assist 0.39.6 and observation 0.39.10 are unchanged.
Current level/XP/XP-per-hour/deaths/camp remain unknown. Live command-chat/scene,
zone/height and measured motion/body bindings are the remaining route input gate;
F11 remains disabled. The playable 1–20 and fresh 1–50 objectives are not met.


## Private source 0.41.91 staged — 2026-11-14 08:04 UTC

**VERIFIED:** source `ca0842a7ef18bd8cfb41a6beb45e60efe9a407a5`, archive SHA
`d5167bf5982e890502b293b5abbb720617d7db44b3744cdcd6928a4220bea663`,
is staged at Alienware `owner-tools/0.41.91/source`. Startup verifies module
imports, shared command-method identity, absence of a route pulse method,
refusal of missing dependencies and class composition with the hash-matching
retained engine. No engine was instantiated or game/display/device input used.
Remote startup artifact SHA
`ddc25020a2a4a56f37a982eb4cee7bd8333a3eee969c79b243841a42e5b765f7`;
local staging record `releases/eql-automation-0.41.91-staging.json`.
Owner helper versions are unchanged. Live route acceptance remains absent.

## Route location-command execution 0.41.91 — 2026-11-14 08:04 UTC

**VERIFIED implementation:** the route loop now has a concrete
`RouteLocationExecutor`. It shares one fixed `/location` implementation with
`MeasurementExecutors`, including the retained bot's actual command/character/
tap methods, pinned descriptor, immutable submission snapshots and unconditional
release. Only the engine/session binding differs. Each operation pins its
exact active driver; changed driver, sender, pending request, mode or recovery
refuses further input. The route executor has no movement method. Current
independent command-start/key/end observations are still mandatory, and no
owner job/hotkey constructs this path. Route session snapshots now retain the
same command journals; trace purpose distinguishes route position requests
from calibration requests.

**VERIFIED route tests:** 17 focused checks pass, including exact ten-key
submission, all four stop boundaries, copied/stale ownership, driver replacement,
failed UP retry on the original descriptor and a complete retained-engine route.
That passing route used actual command code and watchdog subprocesses on a pipe:
nine steps, ten stopped pairs, 20 commands, 800 journaled command events and
872 total pipe events asserted by the test. Scene, geometry, calibration and
location feedback were synthetic. The saved helper result and source hashes
are retained at `evidence/route-location-executor-0.41.91.json`, SHA
`d59f68dfbb7025a8fb61343b118a59ee9453558226e09abd0913ad8e5dbe9c9d`.
The raw pipe event stream from that test was not saved; its command write
journals and movement receipts were. All paths below use the private store.

**VERIFIED mixed calibration results:** 36 existing executor checks passed;
the full real-time calibration test refused after two accepted pulses with
`Release watchdog did not arm`. Its focused retry later refused with
`Invalid release watchdog timing receipt`. Final records in both cases show
no held keys, no pending releases and no cleanup error. The first error can
also mean the stop predicate returned before READY was read; the second
collapses several receipt predicates. Their exact earlier causes are unproven.
CPU pressure was observed around 64%, but causation was not established.

No deadline or release checks were relaxed. One bounded diagnostic on sampled
CPU 41 retained raw child receipts and completed all seven pulses, eight pairs,
16 commands and 696 pipe events with no parse errors. All original full-test
result assertions were checked against that saved record. Evidence:

| Run | SHA-256 |
| --- | --- |
| `evidence/motion-arm-refusal-0.41.91.json` | `5b3e779c436ab3331f13571948d8520ce8e78adb08aede0bfc4d163c4276b35c` |
| `evidence/motion-receipt-refusal-0.41.91.json` | `1eb28745f1a52c289fca91195a32ea68d689a151b64972cc994d52958fdb6ea0` |
| `evidence/motion-timing-0.41.91.json` | `22553cc53d9a47393d9436a79bdcac51915c9bdd2890d4e3a74b3abf7b176e49` |

The previous turn made concrete progress by staging the route-session loop;
this turn replaces its simulated command callback with the actual shared
executor in the pipe harness. Current live scene/zone/height/motion bindings
and owner route controls remain incomplete. No game capture/input/login or
protected-prefix/character change occurred. Owner assist 0.39.6, observation
0.39.10 and the passed G0 result are unchanged. Current level/XP/hour/deaths/
camp remain unknown; neither the playable 1–20 nor fresh 1–50 goal is achieved.

## Private source 0.41.90 staged — 2026-11-14 07:58 UTC

**VERIFIED:** source `4057d766b9e2854fd47a2bf29d10ca2faf006c62`, archive SHA
`716182f30c5fbcb40fcfbf244a011d9b9fda86cdd0529f3d3fa576b06aaed893`,
is staged at Alienware `owner-tools/0.41.90/source`. Route modules import
successfully, and the new adapter composes with the hash-matching retained
0.39.10 engine class. The engine was not instantiated, and no display,
input device, game capture or game input was used for the remote startup check.
Remote artifact SHA
`6105af00fc910548e470ad194668e789651396796c9ecf047833f53f01c9fe01`;
local record `releases/eql-automation-0.41.90-staging.json`.
The owner helper files were unchanged. A read-only listing at 07:58:51 UTC
found zero saved position pairs. No live route acceptance or level gain is
claimed; the existing stationary observation remains pending.

## Consecutive checked route steps 0.41.90 — 2026-11-14 07:58 UTC

**VERIFIED implementation:** `RouteSession` now owns the route's exclusive
`LocationLogReader`, collects two fresh stopped fixes, aligns them through
`RouteGroundObserver` against the committed floor and calls the retained
fixed-route follower. `RouteSessionDriver` runs the existing checked sender,
waits for final release and settling, then repeats through subsequent segments.
The exact aligned reference is retained during each pulse. A matching fresh
zone binding and explicit initial release are required; the saved unbound pair
and old log history cannot start the loop.

The loop defers replies arriving during command cleanup, rejects batched,
unsolicited, partial, stale or changed-zone replies, and polls cancellation
without recursively scheduling another step. It records unsuccessful executor
attempts with unknown input delivery. The owner engine attachment handles
stop/job/close cancellation, retains cleanup order, rejects assist attachment
and saves partial/arrived records outside the game prefix. No job or hotkey
constructs it. The guarded location-command executor and independent current
scene/height/motion providers remain mandatory external dependencies.

**VERIFIED tests:** 27 focused session/actual-helper checks passed, followed
by the cancellation regression after adding unsuccessful-attempt evidence.
The initial system-Python run skipped 16 tests because NumPy was absent;
the successful runs used the existing private numerical interpreter with
the installed pure-Python pytest package. No dependency was installed.

**VERIFIED retained-engine pipe experiment:** two synthetic segments arrived
after nine checked watchdog pulses, ten stopped position pairs, 20 simulated
location commands and 72 actual pipe events. Every new pair used the committed
floor; the initial floor remained unchanged. Actual helper ticks, follower,
ground producer, log reader, transaction and watchdog were used. Scene,
geometry, calibration and position feedback were synthetic. No real command
or movement was sent to the client. Evidence
`evidence/route-session-0.41.90.json`, SHA
`d248bb682531d8b62341b42bee0aeecfd5747f9b335d89522b27a93bba7cbc00`.
Paths are relative to the private `~/.local/share/eql-automation/` store;
source and retained-helper hashes are in that artifact.

The previous goal turn made progress by staging 0.41.89; this turn adds the
missing runtime loop. Neither proves a playable 1–20 path or a fresh 1–50 run.
Current level/XP/hour/deaths/camp remain unknown. Owner assist 0.39.6 and
observation 0.39.10 remain unchanged; G0 passed and needs no repeat. The pending
owner stationary observation remains the next live-data step, followed by
actual scene/zone/ground/motion binding and route executor assembly.

## Private source 0.41.89 staged — 2026-11-14 07:50 UTC

**VERIFIED:** source `79aeeea2aea0e39324d9cc3b500e87835f38ebe9`, archive SHA
`808175304076a030dab4bfb740bb887d1369d283d0a1fa4542ffabe5c0280b87`,
is staged at Alienware `owner-tools/0.41.89/source`. Six startup checks pass:
version/import, CLI help, complete synthetic report matching devbox output
with a relocated byte-identical mesh, wrong-pair-pin refusal, incomplete-route
argument refusal and unchanged saved inputs. Remote pixels, coordinates,
catalog and route/mesh were all synthetic. This does not extend the local
real-source GFay experiment into a live-client result.

Remote `owner-pair-smoke.json` SHA
`35b14bfcf813a6380e51b81c1fe389e9f60383d5b6b3b1e3a699b0f22ecaf134`;
normalized comparison SHA
`a00c08ceddadd6c5e2da32ea6ed268ddb18459856eef8c78784039467505322b`.
Local staging record: `releases/eql-automation-0.41.89-staging.json`.
No game capture, input, device creation, protected-prefix write or owner helper
change occurred. The pending observation and live route bindings are unchanged.

## Saved-position and offline-route diagnostic 0.41.89 — 2026-11-14 07:49 UTC

**VERIFIED:** the new saved-pair reader validates the existing 0.39.10 format,
pinned metadata/PNG bytes, recorded timing/no-chat conditions, bounded RGB
crop dimensions and parent/child pixel agreement. It preserves recorded-only
process/window identifiers and raw unbound coordinates. The capture producer's
independent identity comparison is unchanged; only its shared record checks
were extracted. Exact zone-name lookup uses the existing catalog parser.

The optional route summary reuses `FixedRoute.load` and additionally requires
exactly one named `<zone>.npz` source pin with the supplied mesh's digest.
This prevents another valid input pin from being mistaken for the zone mesh,
while allowing a relocated byte-identical mesh. The report never queries the
route from raw coordinates, selects a scene state or enables F11.

**VERIFIED checks:** 82 focused saved-reader/adapter/catalog checks pass,
followed by all 17 original capture checks. A separate CLI experiment loaded
the retained 0.39.10 capture and pair producers by SHA and used them to save
synthetic pixels/location. The reader checked all ten PNGs and seven overlapping
child crops, then loaded the real copied catalog and existing GFay plan/mesh.
The explicit label hypothesis `The Greater Faydark` resolves to catalog ID 54;
the route has 155 segments. Input files stayed unchanged. Evidence:
`evidence/owner-pair-0.41.89.json`, SHA
`ef0bd3fbfbd29985c094207a9842f5d6baec67be59d3821ba21517fe2965db3c`.
All paths here are relative to the private `~/.local/share/eql-automation/` store.

| Retained input | SHA-256 |
| --- | --- |
| 0.39.10 owner UI producer | `3da44541cc6dee7e55c87a32188512a8ce55681188c4859e5a5d3d5b3161e940` |
| 0.39.10 position producer | `e1cd015858e19c2dd8116d4cb65bda40a3d20d32653da8d14133100502c3ec16` |
| Copied ZoneNames.txt | `840b61b01deb4dfb8f49cf13e007364a629ce380c165aad5bb37adba6e52cd39` |
| GFay fixed plan 0.41.48 | `145679ec15111cf2d319ca630c66da693cc69863bdef594f67a46989c18592a4` |
| Retained gfaydark.npz | `5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9` |

**OBSERVED:** read-only Alienware listing at 07:48 UTC found zero saved
`g2-ui-observations/*/unbound-location.json` pairs. No capture/input/game launch
occurred. The existing stationary observation remains pending; no new test or
G0 repeat is requested. G0 passed with the owner's visible-stop confirmation.
Assist 0.39.6 and observation 0.39.10 are unchanged. Actual current scene,
zone-to-asset/coordinate/height binding and measured travel bounds are still
required for a checked live route step. Current level, XP/hour, deaths and camp
remain unknown; the real 1–20 and fresh 1–50 goals are not met.

## Private source 0.41.88 staged — 2026-11-14 07:38 UTC

**VERIFIED:** source `ad9a9867cbf75441463c122c17f1acfb5ee21bab`, archive SHA
`3762ee15ca2f485876b84ba5326275b369626365baf77a8c999d25ac35b810f8`,
is staged at Alienware `owner-tools/0.41.88/source`. Seven focused checks
pass: import/version, installed font and three version-2 probe pins/DC
metadata, refusal of both reused banks, exact local comparison reproduction,
legacy metadata/pixel compatibility, geometry/false live flags and CLI startup.
Remote `font-dib-smoke.json` SHA
`9a7b8a6a7f047f7ebbbfc9095fec7c2237133c6262859929166b5fa6394ad4ff`;
canonical comparison SHA
`3f8cd9f7f6be8f1e1f63989089d492f888e011235251bc927cc2d924c6a11082`.
Local staging record: `releases/eql-automation-0.41.88-staging.json`.

No native helper or game ran on Alienware; its font was read only. No capture,
input, devices, protected writes or character changes occurred. Owner helpers
and the pending stationary observation remain unchanged. Current run metrics
remain unknown; neither a live route nor a level gain is accepted.

## Corrected DC setup and reusable-bitmap evidence 0.41.88 — 2026-11-14 07:35 UTC

**VERIFIED correction to the earlier trace:** PE import parsing resolves
IAT `0x18035e060` to **SetMapMode**, not SetBkMode. The call at `0x180197dd8`
sets MM_TEXT (1); the DLL imports no SetBkMode. The earlier claim that this
call selected TRANSPARENT was wrong. Complete bounded new-glyph, rerender,
raster and copy paths show no explicit full-bitmap clear. Evidence
`font-dc-correction-native-0.41.88.json` SHA
`f9c34b2034cc820ce809a4f56843e0763857c10a7ea17f058c33a2bee39e307e`.

The own-tool probe now sets MM_TEXT, leaves the background mode at its DC
default, and records both actual modes. Its version-2 format records whether
the bitmap is cleared before every glyph, zeroed once and reused (default),
or initialized white once and reused. Version-1 imports retain their actual
legacy transparent-background/clear-each provenance. Reused diagnostics
cannot be composed into independent glyph rendering banks. The comparison
requires matching font, descriptor, metrics, sequence and DC modes, then
separates changed alpha4 pixels inside and outside each glyph's cx/cy extent.

**VERIFIED execution:** 72 focused parser/geometry checks pass. Zig 0.13.0
built the corrected native helper on one low-priority devbox CPU; source SHA
`1550757f03706a966402a6dddf10bbeb2995bffaac839040cd94b4804eba33ea`,
executable SHA `db9da10858f2f94e798bbbf9792b720bb719fb8120a56af24caba0ea4c643f63`.
Three offscreen runs used the existing dedicated devbox Wine 10.0 prefix,
never the owner's game prefix. All selected the exact copied font and
observed mapping mode 1, background mode **2 (OPAQUE)**. Own-prefix server
exit and existing-output preservation were checked successfully.

| Isolated height-19 probe | SHA-256 |
| --- | --- |
| Clear each glyph | `e4458657f0c351a72aa7a6b349e2944e0202b083496ad7e2ada17c7e82925fac` |
| Zero once, reuse | `0b36f0c4e1c109bd960778d85afcee4054802a1c68a6ffd11cb17bdc0aee6853` |
| White once, reuse | `b43c810e95635252408fe46e3bd174223a47195838d361e6d6f3c8f60703dcd4` |

**OBSERVED isolated behavior:** the 21×19 bitmap retains history beyond the
measured glyph width. The zero-once sequence changes 76 alpha4 pixels across
five glyphs outside their extents; none change inside. White-once runs also
preserve outside pixels, including the column immediately after cx. Corrected
clear-each alpha4 glyphs match the older clear-each results exactly. Thus the
DC labeling error did not change these particular baseline glyphs, but the
baseline cannot represent unknown live bitmap history. Linear sampling may
touch those retained edge pixels. Comparison artifact SHA
`85734b0a5c6f19ac210a982f2e97e1463378135bed8b17b2f348d8b0c92d8994`.

The CLI's `--diagnostic-only` import/comparison succeeded with zero rendering
PNGs, manifest SHA
`dc8d4f7689ed1c28185e07e7db874d8382d28a4e2a672fcfc6312ab3134bbb55`.
Non-diagnostic reused import and incomplete baseline arguments both refused
before creating output; CLI evidence SHA
`e67be5267582da0411d2e914986c2a162e6ccc68ceb72698ea1841bebafa92ad`.

**VERIFIED static shader filenames:** the traced stage/input serialization
and CRC32 reproduce table pipeline 7/8 keys 209776124/750037918 exactly,
matching the retained identical vertex shaders. Evidence
`font-shader-keys-0.41.88.json` SHA
`56330272396face7035bc06394d265a9271eaf23922bafca84b0b41ef44bfa97`.
Font preparation requests source-alpha/inverse-source-alpha blending and
alpha modulation; color stage, blend override and ADD state remain inherited.
This does not prove an active shader, bitmap history or rendered live pixels.

The next direct route integration is a read-only consumer of the existing
stationary pair, reusing saved-pair/crop and GFay route validators. The pending
owner observation remains missing at the last 07:26 UTC check; no new test or
repeat G0 is requested. Owner assist 0.39.6 and observation 0.39.10 are unchanged.
No game execution, live capture/input, login or protected-prefix write occurred.
Current level/XP/hour/deaths/camp remain unknown; no live route or level gain
is accepted. This build corrects a source-model error, not the completion claim.

## Compiled shader candidates — 2026-11-14 07:29 UTC

**VERIFIED static candidate evidence:** the two installed vertex shaders
whose signatures match the font layout, `VertexShader_209776124.cso` and
`VertexShader_750037918.cso`, are byte-identical (3,860 bytes), SHA
`34cca2a5891206066202ab9792f97829b845479fdf1381fed8caeedfaaf42d68`.
Their RDEF declares the native upload's b0, size 0x380, four matrices and
viewport offset 0x100. Thus the earlier text-source/constant-layout mismatch
is resolved for these compiled candidates; the copied General/State.hlsl
is not their constant-buffer contract. Candidate/chunk evidence SHA
`45c26807b5b898cea423afb8da3d51de0a16a59aa2255bdf2cb9afba111a7a22`
(`evidence/font-shader-candidates-0.41.87.json`).

Their manually decoded initial SHEX instructions subtract the original
viewport origin, divide by its size, map to clip coordinates and invert Y.
Together with the API viewport's +0.5 origin, this would cancel the glyph
builder's -0.5 shift. The common SHEX payload SHA is
`980ce04465783a0e3a7f0be12eac27d56ecd4cf05f1a162666e30e9c8013f9db`.
This is conditional on selecting these shader keys; signature correspondence
alone is not proof of active selection. No shader/game code was executed.

**OBSERVED static atlas constraints:** cells use exactly tmMaxCharWidth by
tmHeight, without a gutter. Unused initialized cells are transparent black;
written cells use white RGB even at zero alpha. Linear samples near a cell
edge can therefore depend on adjacent occupancy or texture-format fallback.
The geometry-only build correctly leaves GPU projection/sampling and live
equivalence false. Shader-key selection and final atlas sampling remain next.

## Private source 0.41.87 staged — 2026-11-14 07:28 UTC

**VERIFIED:** source `b8e5c07db40c03543b5feccac2993a3946052925`, archive SHA
`0bc8d770626ec2dcebbe625cc65d295334a35497d0951eeb678cdf3282d28c10`,
is staged at Alienware `owner-tools/0.41.87/source`. Six focused no-input
checks pass: startup/import, retained probe/font pins, exact reproduction of
all 18 devbox geometry reports, false live/input flags, mismatched probe-height
refusal and CLI startup. Remote `font-geometry-smoke.json` SHA
`8e0a7b6c016985c0b985a680e3ff873dec277e206462a2940ba172c97afaa110`.
Canonical geometry digest is
`be8963b1a7dde5f8391f67a76d580120c06c4d3d88ed69fb8a7a9de85985a129`;
local staging record is `releases/eql-automation-0.41.87-staging.json`.
No device, live capture, game input or protected write was used.

Additional bounded static render/metric evidence is retained as
`evidence/font-render-state-native-0.41.87.json`, SHA
`a442cf3d777cede9c68efe8c1a309acd580e646af78ce36a593e7811faf168b5`.
The copied pipeline table contains two entries with the font FVF layout;
neither supplies its compiled shader filename. All 34 small installed
`RenderEffects/TS/*.cso` files (122,880 bytes total) were copied read-only for
static signature/reflection/selection analysis to the private shader store's
`TS/` directory. Its manifest SHA is
`be83e0d4e7591940302af0f6edeb955ef57a3bee546c847d1eef9450a49a7d0c`.
These are retained source artifacts, not proof of an active shader binding.
The owner launchers and pending stationary check are unchanged. G0 remains
passed; no live route/leveling acceptance is added.

## Source font geometry 0.41.87 — 2026-11-14 07:26 UTC

**VERIFIED static linkage:** `CreateGraphicsEngine` constructs the interface
with vtable `0x18036faf8` and places it at returned structure +8, loaded by
eqgame into `0x140fe74a8`. Slots +0x158/+0x160 therefore reach the inspected
face/scale setters. An intermediate concern about vtable `0x18036fae0` was
resolved: that constructor belongs to embedded objects, not this interface.
The saved scale enum's 1.25 multiplication is correctly linked to the font
height/compensation path. Static blocks are retained in
`evidence/font-geometry-native-0.41.87.json`, SHA
`2262716d592d28f2615933bf8144c3dc01db1ed852eaf400ad2a6eb182cd202f`.

**VERIFIED implementation:** `font_geometry.py` models the bounded fitting,
left-aligned single-line path with explicit binary pins and source hypotheses.
Requested LOGFONTA height must equal `ceil(baseHeight * scale)`. Each glyph
advances by `ceil(GDIcx * compensation)`, while its rectangle keeps the
fractional width/height and pre-projection -0.5 shift. Texture extents use
the glyph's cx/cy, not the maximum-width backing bitmap. Single-precision
operation boundaries are preserved. Clipping, wrapping and selection are
outside this model; overflowing hypotheses refuse.

The caret is drawn separately after converting the measured text width back
to UI units with ceil and the resulting origin to graphics units with floor.
Height similarly uses `1 + ceil(ceil(tmHeight * compensation) / scale)`;
single-line vertical centering truncates its half difference. The importer
can now record all 18 prefix/caret geometry cases beside its unchanged raw
GDI PNGs. It never labels those PNGs as transformed GPU output.

**VERIFIED checks:** 57 focused geometry/parser checks pass; the updated
37-case geometry subset also passes after adding a float32 multiply-boundary
case. CLI startup and incomplete-argument refusal pass. All 18 cases with
the copied height-19 probe and retained logical client rectangle resolve;
text origin is (150,1510), font height 17 UI units, compensation
0.9868420958518982. `/l` and `/locatio` place the caret one pixel beyond direct
graphics-space concatenation. These are source-derived model results, not
observed screen coordinates. Manifest SHA
`0da2313f5365b07f4d107f4661935f5ba87e7e01efbfcd96e091c03eaf3877e1`;
validation `evidence/font-geometry-0.41.87.json` SHA
`2155dec6b579789458ed3b22b97aec03311546f1692305661dbb595022278064`.

**VERIFIED static filter; unresolved shader binding:** font state defaults
reach D3D11 `MIN_MAG_LINEAR_MIP_POINT` (0x14). The viewport wrapper adds +0.5
to the actual API viewport origin. A new read-only copy of installed
`RenderEffects/General/State.hlsl` contains the position-conversion function,
but its b7/viewport-offset-0xc0 declaration differs from the inspected native
upload's b0/offset-0x100 layout. The selected shader/include must be reconciled
before combining those facts into a final pixel model. No raster equivalence
or current filter/viewport/font binding is claimed.

Copied shader sources stay outside git at
`client-data/font-shaders-20261114T0723Z` under the private store:
State.hlsl SHA `e4059a3a8ecdea33e28948ff01fd8ba01ffd2404e2f87a30c8c796a26724e171`,
InputLayoutsTable.json SHA `a8fb376bf6c7d2609a4280576e9c134a4f4804fed2d874b3394c797b63941d18`,
TextureStagesTable.json SHA `3e7afbdf1596d073396c1fb8d6bc5cc13477248eaf8a53e2822243226af0cb6c`.
No game executable/DLL was run, no live capture/input occurred, and protected
files were read only. The 07:26 UTC listing found zero stationary observation
pairs. Assist 0.39.6 and observation 0.39.10 remain unchanged; G0 is passed.
Current level, XP/hour, deaths and camp remain unknown. No live route or
automated level gain is accepted.

## Private source 0.41.86 staged — 2026-11-14 07:17 UTC

**VERIFIED:** source `780ba2c83a62471aa0a7c2fd39a1f157ea1ed2a7`, archive SHA
`4fcd1c179b69a553bb773c918b12d8e6003e3e1c15612cd4a3c56025a1c690eb`,
is staged at Alienware `owner-tools/0.41.86/source`. Five focused startup
checks pass. The installed Arial file still matches the font bytes selected
by the isolated devbox GDI probe. Both pinned probe files import correctly,
a wrong selected-font hash refuses, and four complete frame passes compare
height-15/19 models with/without caret against the installed 172-source layout.
All pixels in these frames are synthetic; no GDI/native helper was run on the
Alienware. Its game install/prefix were read only.

**OBSERVED model-frame timing:** first 79.6 ms, median 80.2 ms, maximum 83.1 ms;
four of four meet 100 ms. Real capture/input/log scanning remains excluded.
Remote `../isolated-font-synthetic-frames.json` SHA
`de4d0f23ec831d5186daccc6256671b76068b6675b0e9c49e9589e460dfd1944`;
local staging record `releases/eql-automation-0.41.86-staging.json`.

No real-client command, route or leveling acceptance is implied. Current font
overrides, final texture sampling/compensation and scene/position/motion/height/
envelope binding remain the next integration work. Owner controls are unchanged;
the pending stationary observation remains the only requested owner check.

## Source font and isolated GDI glyph model 0.41.86 — 2026-11-14 07:16 UTC

**VERIFIED static input selection:** `CW_ChatInput` omits `Font`; SIDL's
ScreenPiece default and native constructor set 3. Parser/template/runtime
creation carry that index into widget font field +0x160. Saved
`ChatWindow*_FontStyle` changes output child +0x338 only, not input +0x330.
Evidence `input-font-native-0.41.86.json` SHA
`63d37434fba401a5c30ca5eb4909f77028dfce6c4d349b443f90349767fba710`.
New read-only copied `SIDL.xml` SHA
`ca7d43baa5121c26283fed4a886aa984bd8855a5f83a754418099e8b1ebf1f21`.

**VERIFIED static graphics path:** copied `EQGraphics.dll` SHA
`4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168`
initializes physical slot 3 with Arial, positive height 15, weight 100 and
charset 1. Other LOGFONTA bytes initially zero. Requested font indices pass
through a mutable remap row, initially row 0/identity; later face and scale
overrides exist. Startup reads `[Fonts] Font.us.0` with a graphics-supplied
default face; retained `eqclient.ini` has no `[Fonts]` section. Saved `UIScale=1`
is an enum selecting **1.25×**. Scaling uses `ceil(baseHeight*scale)` and retains
fractional compensation. Thus height 19 is a source-supported initial scaled
hypothesis, not a current live binding. Config evidence SHA
`6cdb4ca1e88c28d5b94e13a68cf5489288a4b8a5111387e27d189892e48fea5f`.

The native raster path uses a memory DC, the unchanged 60-byte LOGFONTA,
MM_TEXT mapping mode, black background, white text and alignment 0.
The original 0.41.86 description mislabeled the mapping-mode import as
SetBkMode(TRANSPARENT); the 0.41.88 section above records that correction.
It creates a top-down 32-bit DIB sized `tmMaxCharWidth × tmHeight`; each UTF-16
unit is measured and rendered separately with `ExtTextOutW` options 2. Texture
copy converts `(pixel & 255) >> 4` to 4-bit alpha with white RGB. This is why
whole-string FreeType or raw 8-bit GDI output was not adopted as equivalent.
Evidence `font-raster-native-0.41.86.json` SHA
`4673a71f6608932402f9f4a1fde2409cd3388b051abcb0b5994775fd83552ff0`.
All binary observations are static; no copied game executable/DLL was run.

**VERIFIED own-tool execution:** `tools/probe_font_gdi.c` compiled with Zig
0.13.0 for Windows, with one low-priority CPU due measured devbox pressure.
The helper ran offscreen under Wine 10.0 in new private devbox prefix
`validation/font-gdi-0.41.86/wine-prefix`, never the Alienware game prefix.
GDI's selected font bytes exactly match the copied owner Arial Regular file,
SHA `83b14d85ab64222f676eba6bcd7187057e4ad9bd46eaa696ae4d545fe3459c7a`.
Native helper source/executable SHAs are retained in `build-v2.json`; executable
SHA `3aeb80090bc8b2f7326fab34d3bead2c90a7f3bee9a796eb047679743c94f4dd`.
An existing output path refused and preserved the original file/hash.

`font_gdi_probe.py` checks complete probe structure, selected-font and descriptor
pins; it reproduces alpha4 coverage and composes individual glyph advances.
`tools/analyze_font_gdi.py` writes only a new private font-model directory.
Sixty focused parser/matcher checks pass. Thirty-six model comparisons cover
all nine prefixes with/without caret at heights 15 and 19. Artifact SHA
`7cf6009a09e46fc9e84d348121b4c7a4bbeca17acd28d4a25b1a0883ff042145`;
maximum local comparison was 41 ms for these model crops, not a live budget.
Native probe SHAs: height 15
`3c90c64b66e8f4dc975a5e599c3072e760ff5ba96fa63427254f42684d8c5415`,
height 19 `5d8496c4e73d9271d1939118cd46fc3bfba4f93155489989415bf33567327c08`.
Private font-model manifests under `font-probes/initial-arial-{15,19}-0.41.86`
have SHAs `eb3458cbfaf7f1dbcbdc3363cffc7e691519a868b099373325ad92d525d09816`
and `6accab2193a141c90650da2bc996803c62cbc874c7414a2691105aee266b9214`.

**Remaining limits:** these glyphs come from an isolated Wine renderer, not game
screenshots. Current remap/face overrides, final texture filtering, fractional
scale compensation, current scene/position and motion/height/envelope checks
remain unresolved. No default live bank or game control is enabled. Assist
0.39.6 and observation 0.39.10 are unchanged; G0 remains passed. The 07:05 UTC
read-only listing found no stationary observation. Current level/XP/hour,
deaths and camp remain unknown; no route or automated gain is accepted.

## Private source 0.41.85 staged — 2026-11-14 07:05 UTC

**VERIFIED:** `cc3c2ca22979ddd86c97b1cfad3010d53bbf4d23`, archive SHA
`cf3c51cc169b236245bcd2b284bb1158e45d7a3f5067a077e84e90fa89617618`,
is staged at Alienware `owner-tools/0.41.85/source`. Four focused remote
startup checks pass, including the complete frame reader against the installed
172-source layout with six synthetic text cases and a seventh call proving that
the previous command snapshot is not retained. Exact, missing, extra, wrong and
caret-suffix cases produce the expected pixel-model results; chat authority
remains unknown/false. Actual client glyphs and screenshots were not used.

**OBSERVED synthetic full-frame timing:** first 66.9 ms, warm median 74.5 ms,
maximum 78.8 ms; all six meet 100 ms. Layout/numerical setup took 134.2/29.7 ms.
This includes the new comparison and existing layout/gauge/combat/chat checks,
but excludes real capture/input/log scans. No full live-budget acceptance is
claimed. Remote `../synthetic-command-frames.json` SHA
`5db90cbd3853959eee45a9a3abe660c04685cb246ac70ade9a27a7fcd37dadec`;
local staging record `releases/eql-automation-0.41.85-staging.json`.

No game capture/input, devices, protected writes, login or character mutation
occurred. Owner assist 0.39.6 and stationary observation 0.39.10 are unchanged.
Actual input font/rendering, current scene/position and motion/height/envelope
binding remain unresolved before route execution. G0 must not be repeated.

## Same-frame submitted-prefix comparison 0.41.85 — 2026-11-14 07:04 UTC

**VERIFIED implementation:** `CommandTextMatcher` consumes an exact submitted
prefix snapshot and the current `ChatInputFrame` before its images are discarded.
`PreparedUiFrameReader` accepts a new snapshot/phase per invocation; no previous
command is retained. The matcher requires a complete non-uncertain drafting
prefix, a capture after its completed writes and a fully fitting rendering bank.
Start/end/blank fields never establish closed chat.

The immutable caller-supplied bank covers all nine prefixes, with at most 32
variants, 25 shared origins, six million template-channel comparisons and a
2048×64 input crop. It has an explicit provenance digest, pixel tolerance and
no default font. One per-channel median background hypothesis is shared by
every candidate. Whole-field residuals include extra suffixes and transparent
glyph padding; caret pixels need an explicit variant. A column suffix table
avoids rescanning the field per candidate. Scores, mismatch counts, expected/
alternate candidates, ambiguity and unexplained-ink counts are diagnostic only.
Uniqueness considers every variant within tolerance, independently of which
has the lowest squared error. No visual result supplies `MeasurementInputEvidence`,
G2 flags, focus, ownership, delivery, healing or movement permission.

**VERIFIED checks:** 76 focused matcher/chat/frame checks passed using the
private interpreter (the initial system run skipped 36 dependency-bound cases;
those skips are not counted). This includes independent full-canvas residual
calculations, all nine prefixes, wrong/extra/missing/caret text, all-white
ambiguity, nonzero-tolerance variants, clipping, immutable banks, old captures,
source/frame changes, one-frame integration and full timing accounting.
Fourteen local synthetic glyph cases are retained in
`evidence/command-text-0.41.85-final.json`, SHA
`b3624150b4644234c2446089f916457889012eca1c65814601bb0b95e42d0e40`;
rendering manifest SHA `b5bf82884336d0c19ee1f36b5e88f729bab485be671e0281b002a227d5028a87`.
Maximum local comparison time was 16 ms for these small synthetic crops;
this is not a live observation-budget result. Earlier diagnostic artifacts
remain retained with their earlier scope.

**OBSERVED source limit:** copied `eqclient.ini` has `ChatFontSize=3`; saved
Legira `[ChatManager]` has `ChatWindow0_FontStyle=3` and
`ChatWindow1_FontStyle=3`, both in container 0. Neither selected/default
ChatWindow nor ChatContainer XML declares a font face/index. Config hashes:
`a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc` and
`5876a4136283b692263bc2826ffc2b12cd7328f4faa320c5f4071f2092fbc76b`;
copy manifest `ed4383e03ca937798a5607b62ae3d606966c6523774d589d4ffb77e802488888`.
A light read-only Alienware listing found 20 font files under the prefix's
`drive_c/windows/Fonts`, but no mapping to the active input field was established.
No font was selected by guess, copied for rendering, or treated as live evidence.
The actual `CW_ChatInput` font selection, fallback, rasterization and background
remain unverified. Synthetic renderings are test data, not client-derived glyphs.

Current assist 0.39.6 and observation 0.39.10 are unchanged. G0 is passed; no
repeat. Stationary owner evidence and current scene/position/motion/height/
envelope binding remain required. No real route or automated gain is accepted.

## Private source 0.41.84 staged — 2026-11-14 06:57 UTC

**VERIFIED:** source `355e938cfa6203fdffdeef78c97e00b58a33a5bb`, archive SHA
`490e2a91917c0347e6b2e9f14de976830448e8f7a330ef1eafe8021dc21aec6f`,
is staged at Alienware `owner-tools/0.41.84/source`. Four focused remote
startup checks pass: version/import, retained source pins, the actual sender's
40-event command against a pipe with exact prefix records, and refusal of an
equal-but-reconstructed snapshot before any write. Chat feedback is synthetic.
Artifact `../synthetic-command-submission.json`, SHA
`5bffd428cb6a6b74310d2f626cdb9985679662337add0d29727f299bf83f7586`.
Local `releases/eql-automation-0.41.84-staging.json` records the result.

The initial remote smoke fixture omitted three constants evaluated by the
retained character method (Space/Minus/Dot); it failed before any DOWN. The
fixture was corrected, the already staged source was verified byte-for-byte
against its archive, and the focused smoke passed without source changes.
The original fixture remains for evidence. No game capture/input, devices,
protected writes, login or character mutation occurred. The read-only listing
still finds zero saved `g2-ui-observations/*/unbound-location.json` records.

**Next:** use current scene evidence to interpret the existing chat/player/
target features, with exact command-prefix records available to the observer.
Candidate text matching alone cannot prove focus or closure. Bind real current
position, motion, height and travel-envelope observations before route input.
G0 remains passed; owner helpers are unchanged. No actual client command, route
or level gain is accepted by these source/pipe checks.

## Immutable command submission records 0.41.84 — 2026-11-14 06:55 UTC

**VERIFIED implementation:** the measurement executor journals every attempted
write to its pinned descriptor before submission, then records byte count,
timestamps and completion/exception/short-write outcome. Immutable snapshots
advance `/location` only after each complete DOWN/SYN/UP/SYN cycle. Failed or
out-of-order writes latch uncertainty; successful cleanup cannot repair that
prefix. Records include attempted key codes, operation identity, revision and
Enter completion. Existing sender/generation/input guards remain required:
other writers, including the original sender's F9 releases, are outside this
scope's journal. Kernel writes do not prove client delivery, ownership or focus.

`check_input(request, phase, submission)` must return evidence referencing that
exact snapshot. The executor rejects copied or stale evidence and revision
changes during observation or before the next DOWN. Observation callbacks do
not newly hold the stop lock. UP/SYN cleanup still runs if observation or its
clock fails; no Escape, command retry or new device is introduced. The actual
retained sender's command/character/tap path remains in use.

**VERIFIED checks:** 43 focused checks passed with the private NumPy interpreter;
both parameterized DOWN-SYN and UP-SYN short-write cases then passed separately
(two passed, 35 deselected). The initial system-Python run skipped 19 tests for
missing NumPy and is not counted as verification of those cases. The complete
retained sender and watchdog collected 16 commands, seven pulses, eight stopped
pairs and 696 events through a pipe. All 16 command journals contain 40 full
writes, unique operation identities, complete Enter cycles and false client-
delivery/focus flags. Scene and position feedback were synthetic. Local private
artifact `evidence/motion-command-submission-0.41.84.json`, SHA
`898e904fc5dcda6803e020e1817eb716d55de6d1f5510396637138c29d58cccc`.

**Unverified:** no default live command-draft observer exists, no actual game
input was sent, and no real route or automated level gain was accepted. Current
owner assist 0.39.6 and observation 0.39.10 remain unchanged. The pending
stationary observation, current scene/player/target/chat interpretation and
motion/height/envelope binding are still needed; G0 passed and needs no repeat.

## Private source 0.41.83 staged — 2026-11-14 06:46 UTC

**VERIFIED:** `029d39fcc29372da5e1b3299733da85b13550841`, archive SHA
`a1d8550f10e0b132f72e9764fe76a8b0106f05e5c8bb2d96ccb04e0c0ce50c73`,
is staged at Alienware `owner-tools/0.41.83/source`. Five focused no-input
remote startup checks pass. All deterministic frame-report fields match
published 0.41.82, excluding observation/preparation timing metadata. This
includes source/crop/frame hashes, gauge values, icon scores/ranking, dynamic
chat geometry and unknown-state flags. The actual installed full layout uses
172 checked source files; no source fingerprint dependency was discarded.

**OBSERVED synthetic timing:** first observation 59.3 ms, warm median 50.9 ms,
maximum 60.1 ms; all ten meet 100 ms. This is about 2.3× faster at the median
than the measured 0.41.82 full-layout pipeline. Layout/numerical preparation
are recorded separately at 120.5/26.9 ms. Real game capture and input/log scans
remain excluded, so this is not proof of the entire live observation budget.
Remote `../synthetic-full-layout-frames.json` SHA
`a7566484ca03569445894b621cc65d6be539ad940539924db24512099f9d7bb3`;
local `releases/eql-automation-0.41.83-staging.json` retains the smoke summary.
No game capture, input, devices, login, protected writes or character changes
occurred. Assist 0.39.6 and stationary observation 0.39.10 remain unchanged.

**Next:** integrate immutable helper-command prefix/write receipts with the
current-scene observer; validate current layout/player/target/chat evidence and
bind motion/height/envelope observations before checked route execution. The
owner stationary capture remains pending (zero pairs at the 06:35 UTC check).
G0 passed and must not be repeated. Current level, XP/hour, deaths and camp
remain unknown; no automated leveling or real 1–20/1–50 acceptance is claimed.

## Compiled layout dependency checks 0.41.83 — 2026-11-14 06:45 UTC

**VERIFIED implementation:** the prepared layout now compiles the exact file/
candidate/directory/INI-selection dependency plan after its bracketed parse.
Each frame still verifies every source file's complete content, existing source
identity and higher-priority candidate presence. It verifies directory fallback
and suffix-INI selection as well. Unchanged INI/include bytes already prove
that their parsed selection rules are unchanged, so those rules are not parsed
again inside the observation. Existing sources are resolved once before their
content is read. Missing candidates cannot replace a selected file while their
`is_file` result remains false; their existence is still checked each time.
The full plan runs before and after the feature pass. No budget was widened,
all source-content/selection dependencies retained, and no modified sources
are silently reloaded.

**VERIFIED focused checks:** 31 prepared-layout/chat-frame checks pass in 1.07
seconds. Added cases forbid INI/manifest parsing during a frame and reject a
same-content source symlink redirected to a different target. Existing cases
still reject all content/selection changes, absent overlays appearing, late
manifest changes and inconsistent input regions. This addresses the measured
0.41.82 snapshot bottleneck; new Alienware timing is still to be measured.
Owner helpers, live-state acceptance and movement controls remain unchanged.
G0 remains passed. No accepted real route or automated XP is claimed.

## Source 0.41.82 staged with full layout measurement — 2026-11-14 06:43 UTC

**VERIFIED:** `a345da0fc748bbb6832039d3b9a079cb6aa23c62`, archive SHA
`0c8ab92d17382abf8879abbd255f65bc7fd6eb2f4210b11e02e4039122c44899`,
is staged at Alienware `owner-tools/0.41.82/source`. Four focused no-input
startup checks pass. Ten synthetic frames use the actual installed full layout,
172 fingerprinted sources, actual retained gauge reader and copied sprites
rendered at source-supported 16×16 inside the real 16×33 combat-widget proposal.
HP/mana and all sprite rankings match; chat crops bind the same frame and retain
unknown focus. Changed resolution refuses without reparsing.

**OBSERVED timing:** layout preparation 282.4 ms; numerical preparation 110.0 ms;
first observation 104.0 ms, warm median 117.2 ms, maximum 142.9 ms. Only three
of ten observations meet 100 ms. This includes complete installed-source layout
verification, geometry and features, but uses synthetic frame copies and excludes
real capture/input/log scans. It is not live acceptance. Remote artifact
`../synthetic-full-layout-frames.json` SHA
`09a4058568a73de14f7595f124db9fc889347b531d1e266d87007a2653b7ec6c`;
local staging record `releases/eql-automation-0.41.82-staging.json`.

**VERIFIED bounded profile:** three complete snapshot checks took 156 ms under
profiling. Repeated path safety/resolution accounts for 90 ms cumulative and
INI parsing 38 ms. The snapshot makes 1,545 path resolutions and 21,594 lstat
calls across those three checks. Median sampling/feature times from the frame
record are 59.3/51.5 ms. The source content/selection plan can be compiled during
preparation: unchanged manifest/INI bytes do not need reparsing in every frame.
That is the next measured optimization; content and overlay verification remain
required. Remote `../layout-snapshot-profile.txt` SHA
`c74215c76ae610b387f4448c5984359a0ffee4afcf4c751474056762a627ddf4`.
No game capture, input, device access, login or protected-install write occurred.
Owner helpers remain unchanged and G0 remains passed, with no repeat.

## Prepared layout and same-frame chat integration 0.41.82 — 2026-11-14 06:41 UTC

**OBSERVED bottleneck:** a read-only Alienware call to the actual retained
`UiLayout.load` on installed sources took 150.386 ms for 168 source files and
7,836 elements. This alone exceeds the 100 ms observation budget. The earlier
frame benchmarks explicitly excluded real layout loading. The real saved
combat-widget rectangle is 16×33 pixels; the HP/mana rectangles are each
330×17 pixels at saved scale 1.25. No game frame or input was used for the probe.

**VERIFIED implementation:** `PreparedUiLayout` brackets the retained parser
with full source fingerprints before an observation. Every use checks file
contents and actual selection rules: exact/suffix character INIs, optional
`eqclient.ini`, skin-directory fallback, first nonempty skin/default include
manifest, variants before normal files, and selected-skin precedence within
each variant. Empty and fully overridden includes remain dependencies, including
subdirectory/non-XML suffix includes. New overlays, manifests, INIs or changed
contents invalidate the cache. Each use returns a new layout/cache and INI copy;
parsed XML remains explicitly borrowed read-only internal data. The frame
sample carries the full fingerprint verifier through the feature pass, so
post-load manifest/overlay changes are also rejected. No source changes or
reparsing are hidden inside an observation.

`PreparedUiFrameReader` can now receive the inspected copied-runtime identity
for optional chat features. `chat_ui_frame` resolves and crops the input outer/
client regions from that same sample, requires source coverage and refuses
missing/offscreen geometry. Reports retain geometry, crop hashes and the parent
frame hash, without saving pixels or recognizing text. Chat focus/draft remain
unknown for both empty and nonempty crops. Both numerical and XML preparation
costs are retained separately; feature/source-check time remains in the full
observation interval. Owner launchers and controls are unchanged.

**VERIFIED focused checks:** 49 cache/chat/frame-reader cases passed in 2.97
seconds; two subsequent whole-fingerprint hook cases passed in 2.92 seconds.
They cover selection/content invalidation, preparation races, independent
per-frame layout caches, same-frame crop binding, changed pixels/sources,
missing crop provenance, delayed work and post-feature manifest/overlay checks.
Compile and whitespace checks pass. No full suite ran. A read-only listing at
06:35 UTC still found zero owner position pairs; no capture was initiated.

**Remaining integration gap found by source review:** the input monitor yields
activity/held/contact counts, not chat focus. Measurement executors currently
pass only request and phase to their independent observer, with no immutable
submitted-prefix receipt. Sender `unfinished` is marked before a DOWN attempt
to preserve uncertainty; that does not prove the client opened an owned draft.
Current client focus/draft transitions and an exact submitted-prefix interface
remain required. No empty crop, absent caret, quiet scan or successful kernel
write is promoted to evidence that chat is closed. G0 remains passed with no
repeat; live scene/motion calibration and route acceptance remain unfinished.

## Chat focus cue — bounded static finding, 2026-11-14 06:34 UTC

**VERIFIED static:** in copied binary `fe41a8db…7146bf36`, Editbox vtable
`0x140b6fa70` slot `+0x40` calls caret renderer `0x1406297e0`. It requires the
caret-enable byte `+0x423`, font pointer `+0x160`, and UI-manager focus pointer
(manager `+0x90`, retrieved at `0x14062984e`) equal to this Editbox. At
`0x14062985c–866`, `GetTickCount` bit 9 gates a nominal 512 ms on/off blink.
It draws literal `|` (VA `0x1408a3ee4`) through font routine `0x140624ed0` at
`0x1406298f2`. ChatWindow sets the caret color to `0xffffffff` at
`0x1403d7cd6`. Chat enable/disable at `0x1403d6b50` reaches input focus-clear
`0x1405e81d0` or focus-set `0x1405eee30`; no direct hide/show or background
replacement was established in these inspected paths.

**INFERRED candidate:** a correctly located blinking pipe could supply a
positive-focus veto after visual validation. A pipe may also be draft text.
Absence cannot establish chat-clear because of blink phase, configuration,
font, clipping, occlusion and alignment. No reliable negative-focus visual
signal was established. No classifier or owner control is enabled from this
finding; current live observation and input-state integration remain required.
This was bounded read-only static analysis, with no execution, attach, capture,
remote operation or game input.

## Private source 0.41.81 staged — 2026-11-14 06:34 UTC

**VERIFIED:** source commit `55b89f86132faaac7d6282e6bc03a1f3b77f3f71`, archive
SHA `e4500669c87df9310900e98d3e827fd1ff67dd1e8eccf6a4c00b7036a349d4a0`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.81/source`.
Three focused no-input startup checks pass: source import/version, current
client-file geometry matching the local proposals, and missing-animation
refusal. The actual installed executable and six layout input files still
match the copied audit's pins. Files were read and copied only into the new
private benchmark directory; the retained loader was imported with bytecode
writes disabled. No client/prefix, settings or character data was modified.

Remote `../chat-geometry.json` SHA
`e5cc949cbe6cd093e002d17c43e1e4c7c7e9a21432a4d76bf59f6a46d58781a8`;
local staging record `releases/eql-automation-0.41.81-staging.json`.
This accepts static source geometry only, not real-client alignment, input
focus or movement. No game capture, device access, input or login ran.
Assist 0.39.6 and observation candidate 0.39.10 remain current. G0 is passed
and must not be repeated. Current level, XP/hour, deaths and camp are unknown;
no automated XP or 1–20/1–50 route acceptance is claimed.

## Dynamic chat input geometry 0.41.81 — 2026-11-14 06:32 UTC

**VERIFIED static reconciliation:** copied `eqgame.exe` SHA
`fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`
constructs a Page under `CCW_ChatWindows`, then a ChatWindow under that Page
(`0x14011c330`, clone/add path `0x140621c30`, ChatWindow ctor `0x1403d7b70`).
The input lookup is at `0x1403d7c3b`. This explains why the retained static
XML-only walker returned no `CW_ChatInput` despite the source element existing.

The page sizing routine `0x140622320` uses `PageBorder.LeftTop.width`,
`RightTop.width` and `Bottom.height`; its top is runtime tab height minus
`TabBorder.LeftBottom.height` plus `PageBorder.Top.height`. Fresh Page/TabBox
constructors do not force a border, matching their omitted/false source border
styles. No extra page-border inset should be applied. Tab height depends on
font/animation state; the old generic 22-unit constant is not established for
these chat tabs. Bottom-anchored input bounds do not need that unknown top.

The common frame transform `0x140628950` uses the maximum of each edge's three
corresponding source pieces, then subtracts that edge's overlap without a
second clamp. Thus selected `default_light/WDT_Chat` has effective insets
L21/T10/R0/B7; its 35-unit right overlap cancels its art width. ChatWindow
construction at `0x1403d7c89` forces input style bits `0xc0`, including border,
despite XML `Style_Border=false`. Input outer and client/text boxes therefore
differ. The full ChatWindow constructor preserves its XML stretch/fill flags;
no outer-size override was found there. Later runtime layout is not proven.
Private bounded disassembly artifact (272 lines, three ranges):
`evidence/chat-layout-native-0.41.81.json`, SHA
`f928a9392c86e4051b16a2429fb1c9438357c374bf08c99b21655d510758afde`.

**VERIFIED implementation:** isolated `chat_ui_layout` resolves that dynamic
hierarchy using the retained UiLayout and the inspected copied-binary pin.
It carries unknown page top through the calculation, requires missing source
references instead of silently using zero-sized art, and distinguishes forced
input border/client bounds. It changes no retained layout or owner control,
and reports chat focus, draft and active tab as unknown. Pixel projection is
explicitly an unverified proposal using the retained rounding model.

**VERIFIED checks:** 17 focused tests pass in 0.24 seconds. Cases cover unequal
page corner/middle dimensions, edge corner maxima, overlaps exceeding width,
forced input border, unknown top propagation, missing/unsupported source data,
no double page border and non-mutating/no-input reports. Compile and whitespace
checks pass. No full suite ran.

**OBSERVED copied-data result:** the retained loader still reports no static
input, while the new resolver returns source-unit outer
`(99,1206,558,1227)` and client `(120,1206,537,1227)` for the copied MainChat
placement. At the saved 1.25 scale its pixel proposals are outer
`(124,1508,698,1534)` and client `(150,1508,671,1534)`. These are not accepted
live crop coordinates. The saved manager has two tabs in one container, not
two independent visible chat windows. Evidence pins 38 parsed elements and
all copied input files in `evidence/chat-layout-0.41.81.json`, SHA
`a10a6b628aa00490b511bfb7f60417861fe062a87e341074415b2bbf6c56a44c`.
The animations supplement is the earlier copied `EQUI_Animations.xml` SHA
`c1b787f5b6e5aa6a556c4aa236377494303a96a184b67ffe470c76ade1c3ac35`.

**Still unverified:** current placement/clipping/active tab, final scaling and
rounding, active runtime binding and chat focus/draft. An empty crop is not
proof of closed chat. No game capture, login, input or character mutation ran.
G0 remains passed; assist 0.39.6, observation 0.39.10 and F11/F12 disabled are
unchanged. No accepted real 1–20 route or automated XP is claimed.

## Private source 0.41.80 staged — 2026-11-14 06:29 UTC

**VERIFIED:** commit `ba00f00a8323a96da2ed4de834521e65d1cd961c`, archive SHA
`38f26a24c9da68f06aecc46375e09fdd53ed1173473934f54d4f4db077fa4403`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.80/source`.
Eleven no-input remote checks pass, including complete deterministic candidate
report equality against published 0.41.79 (timing/preparation fields excluded
and private source path basenames normalized).

**OBSERVED synthetic Alienware timing:** preparation 33.1 ms, first new frame
59.6 ms, subsequent-frame median 56.4 ms, maximum 67.9 ms. All ten synthetic
frames meet 100 ms. This excludes real capture/layout/input/log work and is
not whole-scene live acceptance. The separate preparation record remains in
every report. Existing NumPy 2.5.1 was used without installing dependencies.
Remote detailed artifact `../synthetic-frame-features.json` SHA
`0ecb93c7e7285c8959aae7e0ce55270c659ea0c28c732f08d3eaed49031dc2d1`;
local `releases/eql-automation-0.41.80-staging.json` retains the smoke report.
Only private source/benchmark files were written; no input device, game capture,
login or protected client/prefix modification occurred.

A read-only listing still finds zero paired owner position records. Assist
0.39.6 and observation candidate 0.39.10 remain unchanged. G0 is passed with
no repeat. No 1–20 route, automated level gain or hands-off 1–50 run is accepted.

## Prepared frame reader 0.41.80 — 2026-11-14 06:28 UTC

**VERIFIED implementation:** `PreparedUiFrameReader` compiles the source sprite
bounds and exercises a synthetic numerical batch before the caller starts its
observation. Construction captures no game frame, creates no input device and
sends no input. Each invocation captures a new frame through the existing
reader. Changed skin/scale/template dimensions and pre-preparation timestamps
are refused. Preparation time and backend are retained in separate metadata;
no old frame is refreshed, no observed latency is hidden, and no permission or
latency guarantee is created. The existing live helpers are not wired to it.

**VERIFIED focused checks:** 67 frame-reader/matcher checks pass in 1.75 seconds
under private NumPy/Pillow. New cases cover zero capture during preparation,
new pixels on each invocation, layout/decal changes, later capture latency and
cancellation before capture. No full suite ran. The current owner HOWTO is
shortened to current launchers, controls and limitations; all prior material is
preserved in `HOWTO_REFERENCE_04179.md` as historical development reference.

**OBSERVED local timing:** ten synthetic 2560×1600 frames using copied client
sprites and the actual retained gauge reader preserve the deterministic
0.41.79 candidate reports. Preparation took 1.811 seconds, first observation
369 ms, warm median 310 ms and maximum 524 ms on the loaded devbox. This is
not an overall startup improvement or proof of the 100 ms live budget.
Real capture, layout loading and input/log scans are excluded. Evidence:
`evidence/ui-frame-features-0.41.80.json`, SHA
`71aca508483faa07c3b91eafaf5a4e180092be4bd7c92ab60b544d14cc14966d`.

**OBSERVED tool limitation:** the REA binary-session inventory returned a
provider timeout while probing unrelated apktool: `inspect_apktool_client`,
20,000 ms deadline, stdout `3.0.3`, exit code 0. No retry, tool repair,
settings/session change or attach occurred. Bounded local static disassembly
of the already copied client continues; this tool error is not live evidence.
G0 remains passed, with no repeat. Current scene evidence, motion/height
calibration and live route acceptance remain missing; no automated level gain
or hands-off 1–50 run is claimed.

## Private source 0.41.79 staged — 2026-11-14 06:20 UTC

**VERIFIED:** commit `68844ef020609e962a1daa6184a523d6bbd13baf`, archive SHA
`7dae6f43cbb7fec8ae5329d6fc818ff95ce49581f4fc9468c71ad84dd4aa0237`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.79/source`.
Eleven remote checks pass, including complete deterministic feature-report
equality against the published 0.41.78 benchmark. Time fields and the private
version directory names were normalized; every candidate, score, tie, source
hash, frame hash, gauge value and remaining deterministic field matched.
The existing Alienware NumPy version is 2.5.1; no dependency was installed there.

**OBSERVED timing:** warm median falls from 248.2 ms to 53.9 ms, about 4.6×
faster. Nine of ten synthetic frames meet the 100 ms budget. The cold first
call is 199.3 ms and still fails it; initialization must be accounted for before
arming a future measurement. The benchmark excludes real capture, real layout
loading and input/log scans, so it does not verify the whole live scene budget.
Remote detailed artifact `../synthetic-frame-features.json` SHA:
`cbb662dfce23d0710e0f8d46ccb426019e053a0ce175bd6e87e3aa7005252a04`.
Local staging evidence is `releases/eql-automation-0.41.79-staging.json`;
remote `../smoke.json` retains checks and timings. Three installed UI assets
were read/pinned and copied only into the private benchmark folder. No game
capture, login, input or protected-install mutation occurred.

The read-only listing still found zero saved owner position pairs. Assist
0.39.6 and observation candidate 0.39.10 remain unchanged. G0 is passed with
no repeat. Current live chat/player/target/position evidence, motion/height
calibration, initial spatial envelope and accepted route execution are still
missing. Level, XP/hour, deaths and camp remain unknown; no 1–20 route or
fresh-character hands-off 1–50 run is accepted.

## Exact NumPy matching 0.41.79 — 2026-11-14 06:19 UTC

**VERIFIED implementation:** the existing combat matcher's bounded batches
now use NumPy when installed, retaining the exact Pillow-only fallback.
The same native signed 32-bit channel bounds and residual formula are used;
totals use signed 64-bit reduction before conversion to Python integers.
This matters because the largest supported numerator is 6,379,683,840, beyond
signed 32-bit range. Fresh readonly residual arrays preserve yielded rows
across batches. Traversal order, representative ties, filter choices, scores,
incompatible-channel counts and output schema remain unchanged. No dependency
was installed on Alienware; the retained gauge reader already uses NumPy.

**VERIFIED focused checks:** 61 matcher/frame-reader checks pass in 2.08 seconds
under private NumPy 2.5.4/Pillow 13.0.0. Coverage includes every residual at
random shifted positions, non-square and full-sized templates, alpha edge
values, overflow, retained batches, full ranking equality, ties, transparent
sprites and the shared frame reader. A separate Pillow-only interpreter run
passes 31 checks; its 14 NumPy-specific cases skip as expected. Compile and
whitespace checks pass; no full suite ran.

**OBSERVED synthetic benchmark:** ten 2560×1600 synthetic frames using the five
copied client sprites preserve the complete deterministic 0.41.78 reports.
The loaded devbox's warm median falls from 1.690 seconds to 258.4 ms; cold/max
is 2.359 seconds. The new private record is
`evidence/ui-frame-features-0.41.79.json`, SHA
`5029f0e3bdef2abde532e66b7eb22a530b4695f1d37df45a76205c3c1f750e1b`.
The first comparison harness compared tuples with saved JSON lists and failed;
JSON normalization corrected that representation mismatch before the passing
comparison. No real capture, real layout load, input/log scan or game input is
included. This does not establish the complete live scene budget or authorize
movement. Current owner evidence and live scene/motion integration remain
missing; G0 is passed, with no repeat or additional owner test requested.

## Private source 0.41.78 staged — 2026-11-14 06:16 UTC

**VERIFIED:** commit `9a5ee313c554ecf0f3b8b9138e703563fd2a03bc`, archive SHA
`85733f911c0fd3c2776205b0c03a3d9139f80aa8c080c4a9552524042f8dcfe6`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.78/source`.
Ten remote startup checks pass, including the new single-frame feature path
with the actual retained gauge reader and five copied source sprites.
The benchmark read and pinned the three installed UI asset files, copied them
only to its private benchmark folder, and rendered ten synthetic frames.
It opened no input devices, captured no game frame and sent no game input.

**OBSERVED Alienware timing:** cold/max 403.8 ms and warm median 248.2 ms;
zero of ten synthetic cases meet 100 ms. All ten sprite rankings and gauge
values matched the fabricated frames. No real capture/layout loading or
input/log scans are included. The remote detailed artifact
`../synthetic-frame-features.json` SHA is
`460dcfeafcc767df7cd89bf8462e936c4a439f19170a796537f4e9b2bc1de829`.
Staging evidence is `releases/eql-automation-0.41.78-staging.json` locally and
`../smoke.json` remotely. This timing is not live acceptance; the measured
latency now needs reduction before this path can serve per-input checks.
Reading the retained benchmark's stage timings identifies the feature pass as
the dominant cost: warm median 228.9 ms versus 12.1 ms sampling, with 5,096,440
pixel comparisons per icon search. This identifies matching/feature processing
as the next optimization target without another client run.
Read-only listing still found zero saved owner position pairs. Existing assist
and observation launchers remain unchanged; G0 passed and needs no repeat.

## One-frame feature reading 0.41.78 — 2026-11-14 06:15 UTC

**VERIFIED implementation:** `sample_focused_ui` now separates the existing
borrowed-gate capture/layout path from PNG/JSON persistence. The original
capture writer uses it, preserving its saved metadata/crop contract.
`read_focused_ui_features` consumes that same in-memory frame with the actual
retained `rotation_core.bar_fraction` and client-derived combat matcher.
It returns HP/mana candidates, source/crop identity, combat ranking and timing
through final focus/process checks. It writes no files, creates no gate/device,
changes no Engine state and invokes no input. Source changes, frame mutation,
cancellation and focus/process changes refuse a result. Missing/unrecognized
gauges and combat crops remain unknown rather than implying a dead player or
an absent target. Chat, target and player presence remain unresolved; no
`G2UiObservation` or movement/healing permission is manufactured.

**VERIFIED focused checks:** 72 tests passed in 4.88 seconds under the private
NumPy interpreter with Pillow 13.0.0. The tests exercise the actual retained
gauge reader, in-memory versus saved-PNG ranking equality, existing owner
capture/adapter paths, missing/offscreen regions, interrupted observations and
timing that includes layout work. Pillow was added only to the devbox's
private `python-nav` environment; the owner's client/prefix was unchanged.
No full suite ran. Compile and whitespace checks pass.

**OBSERVED synthetic timing:** ten synthetic 2560×1600 frames used the five
actual copied client combat sprites and retained gauge reader. All ranked
correctly and read the fabricated HP/mana bands as 0.5/1.0. Cold processing was
5.859 seconds; warm median 1.690 seconds; maximum 6.126 seconds on the loaded
devbox (load 220.98/238.84/249.77 at 06:14 UTC). This exceeds the existing
100 ms observation budget. It excludes real capture, real layout loading and
input/log scans; it is not proof of live timing. Private artifact:
`evidence/ui-frame-features-0.41.78.json`, SHA
`1fb997572f4192ae2edad6de9c5c8b81696c9df006b81b103be2ee91b84600a7`.

**VERIFIED source clarification:** selected UI/config files were copied
read-only from Alienware to `client-data/ui-layout-20261114T061034Z`;
manifest SHA `ed4383e03ca937798a5607b62ae3d606966c6523774d589d4ffb77e802488888`.
The saved skin is `default_light`. Its chat XML SHA
`5aae64a0d193acdb664eae0ede4495151a19b39044decb3951e24b0d55ed9abf`
defines a painted, borderless 21-unit input with right offset 35. The default
XML instead defines a transparent 20-unit input; that default geometry must
not be applied to this saved skin. Neither definition proves current focus.
The selected INI describes one container with two runtime chat pages. The
retained layout walker has no runtime page expansion and returns no
`CW_ChatInput` under MainChat; it also ignores template border overlap.
Resolving that parent chain remains concrete chat-reader work. No chat text
or screenshot was read by this audit, and no client config was modified.

**Still unverified:** current owner scene/position pair, live layout alignment,
chat focus/draft ownership, target/player identity, initial travel envelope,
current motion/height calibration and real route acceptance. G0 remains passed
with no repeat; no additional owner test or movement control is enabled.
Assist remains 0.39.6 and observation candidate 0.39.10. Current level, XP/hour,
deaths and camp remain unknown; 1–20 and hands-off 1–50 are not achieved.

## Private source 0.41.77 staged — 2026-11-14 06:08 UTC

**VERIFIED:** commit `97ca10885747b769536a7dd134585b7f9795cb37`, archive SHA
`f272597a6324186d33775844bd4b198a748d36035f33acd8df6e6cfed5aee084`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.77/source`.
Nine remote startup checks pass: the prior synthetic estimator/collector
checks plus concrete-executor import without device creation and refusal of
missing session/provider bindings. Remote checks sent no input, started no
capture and opened no client assets/devices. Evidence is retained locally in
`releases/eql-automation-0.41.77-staging.json` and remotely in `../smoke.json`.
Read-only listing found zero saved owner position pairs. The existing stationary
capture remains pending; no new test or G0 repeat is requested. Assist 0.39.6
and observation candidate 0.39.10 are unchanged.

## Concrete measurement executors 0.41.77 — 2026-11-14 06:07 UTC

**VERIFIED implementation:** the finite collector can now use the retained
`KeySender.command`, `character` and `tap` code for exactly `/location`, plus
the existing selected-pulse watchdog. The command view bypasses the sender
constructor and uses a duplicate of its existing descriptor. Engine sender
identity remains unchanged. A common operation marker and the existing G0
stop lock exclude competing sends; request deadlines are never refreshed to
accommodate delayed child startup.

Command delivery is marked uncertain before the first DOWN attempt, including
the slash. Per-key evidence distinguishes closed chat before the first slash
from the helper draft during later keys. Interrupted commands retain the draft
flag and send neither Escape nor a retry. Cleanup tracks pending releases
independently of the sender's mutable held-key set, so a replacement-device
stop cannot suppress a failed original-descriptor release retry. Final and
per-key callbacks are followed by ownership checks. Child receipts, final
release times, remaining keys and cleanup failures are preserved in the
collector's completed/partial record.

**VERIFIED focused validation:** 56 executor/collector checks passed in
24.73 seconds, composing the actual retained Engine wrappers and constructor-
free retained sender with ordinary pipes. Checks include F9 while a watchdog
pulse is held, shared-lock attachment, cancelled/expired requests, wrong-request
evidence, first-slash delivery failure, device replacement with cleared shared
bookkeeping, interrupted chat and final callback mutation. The complete run
produced 16 commands, seven pulses, eight stopped pairs and 696 input events.
Its private record is `evidence/motion-executors-0.41.77.json`, SHA
`803f19f60bd4c1433ba35ebd7f45f0c768ee1c2b7d8f23500e1c85f6bb127747`.
All scene/position observations were synthetic. No real device, client input,
capture or login was used. Compile and whitespace checks pass; no full suite ran.
The first focused run had one test-fixture field-name error (`index` instead
of `serial`), corrected before the passing run. Its full pipe record also
completed and remains retained. Evidence copying initially found both pytest's
real directory and its alias; resolved-path deduplication preserved the single
record without overwriting anything.

**Still missing:** independent live observations during command drafting and
movement, an initial spatial envelope, current zone/frame/height binding and
real route acceptance. The required provider callback is not a substitute for
these observations; no default live provider or new owner control exists.
G0 is passed, including the owner's visible-stop confirmation, and is never
repeated. Assist stays 0.39.6; the existing stationary capture uses 0.39.10.
No accepted real-client 1–20 route or hands-off 1–50 run exists. Current level,
XP/hour, deaths and camp remain unknown.

## Private source 0.41.76 staged — 2026-11-14 05:56 UTC

**VERIFIED:** commit `cb5dbc49876cb1d9191ae41c0eea2b3205b79b78`, archive SHA
`97a85859153e3ea85998958f90bce1fa20fd625eeae8e069e6ce4dad4bf606e3`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.76/source`.
Seven remote startup checks pass, including a new fixture-log stopped pair
advancing to a motion proposal and then refusing an ASSIST-mode change before
any pulse. The explicit pulse callback was forbidden. Other checks cover
version/schema, pinned retained fitting, output preservation, cancelled receipt
refusal and adapter import. Remote checks used synthetic positions/receipts,
opened no client assets/devices and sent no game input. Local staging evidence
is `releases/eql-automation-0.41.76-staging.json`; remote `../smoke.json` retains
the result. Read-only listing still found zero saved owner position pairs.
Assist 0.39.6 and observation candidate 0.39.10 are unchanged; G0 needs no repeat.

## Finite motion collection 0.41.76 — 2026-11-14 05:55 UTC

**VERIFIED implementation:** `MotionExperimentSession` uses the existing
`LocationLogReader` to collect eight stopped pairs around the seven proposed
pulses. It keeps raw timestamps, sequence numbers, log/zone generations, command
start/completion times, child DOWN/UP receipts and final-release completion.
It requires an already observed matching zone event; historical startup state
and bare legacy `Loc` callbacks cannot bootstrap it. One outstanding command
is tracked, but true client request correlation remains explicitly unverified.

The collector rejects competing reader consumption, batched/unsolicited or
incomplete replies, resets, transitions, stale requests, changing bindings,
unresolved forward displacement and ambiguous short turns. Shared estimation
helpers now enforce the same pair means, uncertainty and direction checks in
the incremental collector and complete reducer. There is no retry. Rejected
release attempts remain in partial evidence even when cancellation arrives
just after final UP. The CLI refuses stopped/incomplete collection records.

`owner_motion_adapter` services the driver from the retained Engine tick chain
and cancels on stop/new jobs/mode changes. It refuses overlapping position or
input diagnostics, legacy travel/recording and recovery work. The adapter keeps
a completed/partial snapshot on the Engine and saves it to an exclusive private
JSON outside the game/prefix; unavailable persistence is reported and memory
is retained. Optional Engine tracing is not the sole copy. A job racing driver
attachment revokes the attempt. No staged owner job/hotkey constructs a driver.
Checked command/pulse executors, current scene and initial spatial envelope
remain external dependencies, not fabricated from this experiment.

**VERIFIED focused validation:** 64 checks passed in 10.66 seconds under the
private NumPy interpreter. Tests compose the actual retained Engine with the
existing position/preflight/watchdog/rotation wrappers and the new adapter.
They cover full finite collection, F9/F11/new jobs, settings/process/mode changes,
reader failures, intermediate movement contradictions, no reply/no retry,
competing diagnostics, disabled tracing and failed-save memory retention.
No full suite ran. Compile and whitespace checks pass.

The final real-watchdog pipe run completed seven accepted pulses, eight stopped
pairs, 16 location requests and 42 input events (including final UP/SYN releases).
All geometry/positions were synthetic, appended in client log format. No real
input device, client capture, login or game input was used. Evidence:
`evidence/motion-collection-0.41.76-release.json`, SHA
`457f809c1baf1b85dcdfda05dc68b65f3dcf07430e5a5e9d09d8a25ed6a23f3e`.

**OBSERVED timing limitation:** an earlier real-pipe attempt under devbox load
produced a requested 0.15-second left hold lasting **0.217554784 seconds**.
The collector refused it against the unchanged 0.20-second limit after five
accepted pulses, with no next pulse and the attempted release retained. The
private rejected record SHA is
`4454dce54c970705c5d004eb2dc3ec1e58e3d6035c40ab877bca346c6b578f61`, under
`validation/motion-collection-0.41.76-composed/test_real_watchdog_pipe_throug0/saved/`.
Measured devbox load was 286.84/253.64/222.78 at 05:53 UTC. A prior private
validation attempt also failed to create its missing parent directory; that
harness setup was corrected. The older duplicate receipt-only pipe test assumed
all requested holds met the limit; it is replaced by the engine/collector pipe
test that verifies either an observed successful collection or a measured
budget rejection with release and no retry. No production limit was widened.
The failed run is not live acceptance or a successful calibration, and the
later passing run does not establish a hard real-time release guarantee.

**Still missing:** pending owner position/UI evidence, current zone/frame/height
binding, independent live scene and initial travel envelope, checked live
executors and real route acceptance. Assist remains 0.39.6, observation candidate
0.39.10; G0 passed and needs no repeat. Current level, XP/hour, deaths and camp
remain unknown. No accepted 1–20 route or hands-off 1–50 run exists.

## Private source 0.41.75 staged — 2026-11-14 05:43 UTC

**VERIFIED:** source commit `6e9139d62782c4b7f9e2af295168045b1fef4cd9`,
archive SHA `3ad452339379a7e8a3d32a6db38f01361562b30f4ae4b92bc93705d776761a33`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.75/source`.
Five remote startup checks pass: source version, finite experiment schema,
synthetic receipt/position reduction with the pinned retained fitter, existing
output preservation and cancelled receipt refusal. These remote receipts and
positions were synthetic; the actual pipe-watchdog test ran on the devbox.
No input devices, display capture, client assets or login were opened by the
remote smoke. Its private `../smoke.json` and local
`releases/eql-automation-0.41.75-staging.json` record the result. Assist 0.39.6
and observation candidate 0.39.10 remain unchanged. No G0 repeat is needed.

## Conditional motion estimation 0.41.75 — 2026-11-14 05:42 UTC

**VERIFIED implementation:** `motion_calibration.py` reduces seven isolated
receipt records and eight stationary position pairs using the retained owner's
`navigation.bearing`, `wrap180` and `fit_calibration`. The private retained
navigation SHA is `69dbc6472447942cc30dbe592a6e1cf02998c0a0b8811a8bb59672655dc4049e`.
The proposed sequence is F .10 / R .05 / F .10 / R .15 / F .10 / L .15 /
F .10 seconds: 0.75 seconds requested total, experimental settings rather
than measured client constants. No sender is implemented or invoked by the
reducer/CLI. The initial spatial envelope and current scene remain separate
missing inputs; this does not bypass G2's unresolved speed-bound prerequisite.

The reducer uses each forward leg's immediate pre/post stopped pair. It retains
all receipt timestamps and position provenance, checks zone/log continuity,
release/settle ordering, translation during pivots, height changes and constant
forward speed. It computes bearing uncertainty from the explicit supplied
horizontal error assumption and propagates descriptor-write timing intervals.
Inactive/ambiguous short turns, overlapping duration/angle intervals and an
invalid **unclamped** latency are rejected before calling the legacy fitter.
The independent left sample must fit both the conditional outer intervals and
the legacy point-residual policy. These are conditional outer bounds with
correlated headings, not confidence intervals or proof of joint feasibility.

Outputs explicitly leave input authorization, live calibration, client input
consumption timing, full-turn ambiguity and live route acceptance unverified;
`verified_speed_upper_bound` is null. The raw report cannot be loaded as a
saved legacy calibration. The forward/pivot-only fixed-route follower now
accepts `back_speed=0` as unused; backward/jump/probe controls remain rejected.
No legacy long movement bursts or new owner measurement controls were enabled.

**VERIFIED focused validation:** 36 estimator/CLI tests pass, including rounded
client-format synthetic coordinates, both turn directions, wraparound, bad
receipts, changing log generations, drift, wrong timing, insufficient resolution,
input hashes, output preservation, and the retained fitter's slow-turn and
left-residual refusal domains. One case ran seven actual watchdog
subprocesses against a pipe and checked DOWN/UP plus final release events;
all position feedback in that case was simulated. Twenty-four retained-follower
tests plus 20 subtests pass under the private NumPy interpreter, including zero
unused backward speed and actual retained forward/pivot behavior. Initial test
expectations exposed rounded-angle error larger than a fixed two-degree guess;
the final check requires the known synthetic rate inside the derived interval.
The pipe test also checks the watchdog's existing extra final UP/SYN release.
No client input, capture or login occurred. No full suite ran.

**OBSERVED G0 limitation:** the retained trace has a parent elapsed hold of
0.1508157029893482 seconds, displacement 4.640700378175716 and visible-stop
confirmation, but no child DOWN/UP receipt. Its historical average 30.770671
units/second is not a current verified upper speed bound. G0 remains passed
and is not repeated. A read-only Alienware listing this turn found zero saved
position pairs. Current level, XP/hour, deaths and camp remain unknown; no
1–20 route or fresh-character 1–50 run is accepted. Assist stays 0.39.6 and
the existing pending observation uses candidate 0.39.10.

## Automatic owner capture analysis: source 0.41.74 / candidate 0.39.10 — 2026-11-14 05:34 UTC

**VERIFIED implementation:** the existing position-observation flow now calls
`owner_combat_diagnostic.analyze_owner_observation()` after the raw metadata and
`unbound-location.json` pair are saved. The capture records the XML selected by
`UiLayout.sources['PW_CombatStateAnim']`, including its post-capture hash. The
analyzer uses that recorded source, checks the pair/metadata and source pins,
and copies XML plus adjacent animation textures into the private observation
folder. It refuses unresolved texture fallback rather than guessing a source.
Neither the game directory nor any other part of the protected prefix can be
an output root. Original install files and raw observations remain unchanged.

A successful analysis writes `combat-analysis.json` and a separate engine
trace outcome. Missing/changed/unsupported source data leaves the raw pair
saved and reports analysis unavailable. F9, settings or process changes suppress
a current analysis result; a late revoked result is retained under a cancelled
filename. No sender or pointer is created. The analysis still chooses no live
state, grants no movement, and does not verify textures at the earlier capture
time. This is the existing owner-invoked observation, not an additional owner
test. Old 0.39.9 pairs remain usable by the manual pinned-atlas analyzer.

**VERIFIED focused validation:** 87 tests passed in 2.11 seconds across the
post-capture analyzer, owner adapter, matcher and existing location collector.
They cover source selection, original-file/raw-pair preservation, unavailable
textures (without invented fallback), changed metadata/XML, protected-prefix
outputs, cancellation and settings/process changes. Compile and whitespace
checks pass. No full suite ran.

**VERIFIED private helper publication:** `owner-assist/0.39.10` was built from
the retained, hash-checked 0.39.9 snapshot. Twenty runtime files are pinned by
the new entry; rotation core/engine/GUI and assist behavior are unchanged.
New builder `tools/build_nov12_preview_03910.py` refuses existing destinations
and protected-prefix outputs. Archive SHA
`e3430fd77c1a55601af338222d0a6ec1f808204964be0fd84b1fc6c52eb8a89d`.
The candidate is staged at Alienware
`~/.local/share/eql-automation/owner-assist/0.39.10`.

The actual retained Engine's synthetic event/log/capture flow saved one pair
and its icon analysis, then preserved a second pair with analysis unavailable
when a synthetic texture was removed. F9/F11 cancellation passed. It created
no real display capture, input device or game input. The offscreen GUI smoke
showed MEASUREMENT ONLY with Observe current position visible/enabled, no
worker, and unchanged existing settings. The first GUI attempt correctly
refused an empty game directory at the spell-data sanity check. The successful
smoke used only the copied ID 14/200 spell rows, SHA
`445bb32f1980715b080e5ed59e21275a726c54049d61d20dd85a5af01daf84ca`,
in a temporary private directory; it did not open the protected install.
GUI PNG SHA `721fb63e825ea22141442c138abc2694be74120a251a344f8d7b060b65679125`.
The saved GUI image was visually inspected; the observation and stop controls
are visible. Local publication evidence is
`releases/owner-assist-0.39.10-staging.json`; remote `staging.json`,
`engine-smoke.txt` and `measurement-smoke.json/png` are beside the candidate.

**Live gate / remaining integration:** one read-only listing this turn still
found zero saved owner position pairs. No live capture/input/login was initiated.
The stationary capture and current UI/zone/motion calibration remain pending;
there is no accepted 1–20 route or fresh-character 1–50 run. Current level,
XP/hour, deaths and camp remain unknown. G0 does not need repeating. Assist
stays 0.39.6. Read-only integration audit also identified the next motion
bootstrap gap: G2 currently requires a measured speed bound before its own
forward measurement and cannot supply the turn-rate/sign/latency/heading inputs
needed by the fixed-route follower. Re-enabling legacy long calibration bursts
would bypass the bounded implementation and was not done. Resolve that assembly
while preserving owner-driven live tests and strict assist isolation.

## Private source 0.41.73 staging and Alienware timing — 2026-11-14 05:25 UTC

**VERIFIED:** Commit `01bc41e4a7a0609f37729c7452025d4b6d3fc510`, archive SHA
`9a384402c17987579306844da88b529eb900e5ed9f44dbfae8796e7f85aa90a2`,
is staged at `~/.local/share/eql-automation/owner-tools/0.41.73/source` on Alienware.
Six remote synthetic/no-input startup checks pass: version, batched ranking/tie
order without permission, every shifted scalar/integer residual, immutable
bound caching, analyzer CLI and location-collector CLI. Remote `../smoke.json`
and local `releases/eql-automation-0.41.73-staging.json` retain the result.
These startup checks opened no client assets, capture, input devices or login.

**VERIFIED separate owner-machine synthetic timing:** at nice=10, using copied
client sprite bytes sent in memory and synthetic backgrounds/placements, the
Alienware (Pillow 12.3.0) measured one cold search at 22.663 ms wall / 22.574 ms
CPU. Twenty warm searches had median 12.688 ms wall / 12.637 ms CPU and maximum
14.035 ms wall / 13.195 ms CPU. Every case had the corresponding source sprite
as unique best with zero residual. The staged matcher file SHA was verified
against the devbox source before running. No installed game files, display,
input devices or login were opened. This is copied-source rendering and search
timing on the owner machine, not timing or classification of a real UI capture.
The complete capture/input/log/scene budget remains unverified.

Remote record: `owner-tools/0.41.73/synthetic-icon-timing.json`.
Local evidence: `evidence/combat-ui-alienware-speed-0.41.73.json`, SHA
`f38be656935f6bfee467e753d56e32bc0e0c4cfb3f42ae193a0657557d4deb1e`.
The previously slow source search is now practical for a calibrated observer
on this machine, but the pending owner capture, live calibration and route
acceptance remain missing. No G0 repeat or new owner test is requested.

## Exact combat-template search optimization — 2026-11-14 05:24 UTC

**VERIFIED source 0.41.73:** combat ranking now packs RGB channels into a signed
32-bit Pillow image and batches up to 16 candidate placements vertically. It
computes the same doubled integer alpha-interval residual in compiled image
operations, then sums native integer buffers without histogram quantization.
The source-byte/size/filter key caches up to 128 immutable template-bound pairs.
Traversal order, representative tied hypothesis and scores are preserved;
zero alpha still contributes no information. No new confidence threshold,
classification, current scene claim or movement permission was introduced.

**VERIFIED focused checks:** 31 matcher tests passed in 0.73 seconds. New tests
compare every residual channel and sum with the direct scalar formula across
shifted random crops, fractional sizes, both filters and alpha boundary values;
other cases prove cache source-byte identity and full output/tie stability across
batch sizes 1/8/16/64. Existing pinning, parent-crop and refusal checks pass.
Compile and whitespace checks pass. No full suite ran.

**VERIFIED copied-source equivalence and timing:** the complete output dictionaries
match source commit `e597f2d819af336c0c366171412cc9f5f9f6eba0` in ten synthetic
renderings of the five actual client sprites. Devbox wall-clock median fell
from 1.219634 to 0.085787 seconds; maximum new time was 0.283251 seconds.
Some warm cases also exceeded 100 ms, so this has not established the live
scene budget. Current capture/input-provider time is not included. Evidence:
`evidence/combat-ui-exact-speed-0.41.73.json`, SHA
`7b366bf8955b28bacb73440dea6bec36f085a2bf388da4a693ce403c1b0b9313`.
An independent read-only probe also matched all 1,050 candidate numerators on
the copied sprites; it identified 16-placement batches as faster under that
probe's load. Its timing is supplementary, not real-client acceptance.

**Live gate unchanged:** the same stationary 0.39.9 capture remains pending;
no additional capture polling or game input was initiated this turn. G0 needs
no repeat. Real icon placement/rendering, current character/zone/motion
calibration and complete scene timing still need evidence before route input.
Assist 0.39.6 stays unchanged; no accepted real-client 1–20 or fresh 1–50 run.
Current level, XP/hour, deaths and camp remain unknown.

## Private source 0.41.72 staging — 2026-11-14 05:20 UTC

**VERIFIED:** Commit `e597f2d819af336c0c366171412cc9f5f9f6eba0`, archive SHA
`3106ff4a7fc75c675895fb1c99f76b1d1462e8bba8ef71db871fddf4d67d45b6`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.72/source`.
Six remote synthetic/no-input startup checks pass: version, decal ranking in a
tall crop without permission, pinned parent/child consistency with texture
identity unknown, changed-crop refusal, analyzer CLI and location-collector CLI.
Remote `../smoke.json` and local `releases/eql-automation-0.41.72-staging.json`
retain the result. No client assets, display capture, input device or login
were opened by these checks. Owner assist/observation controls remain unchanged.

## Source-derived saved combat-icon analysis — 2026-11-14 05:19 UTC

**VERIFIED source 0.41.72:** `combat_ui_match.py` and
`tools/analyze_owner_combat_capture.py` read pinned copied UI metadata, its exact
combat-control PNG and the source-derived atlas. They verify captured XML
against the atlas, saved skin, crop bounds/dimensions/hashes and, when present,
parent-window/child pixel equality. They never open the display, current game
files or input devices. Capture provenance hashes XML/INIs, not textures;
texture identity at capture remains explicitly unverified.

**OBSERVED source/layout detail:** `PW_CombatStateAnim` declares a 13×13 decal,
but its containing widget can be about 13×26 UI units. The matcher derives
floor/ceil decal sizes from that declaration and saved scale, searching within
the crop rather than stretching to the whole control. Nearest/bilinear filters
and straight-alpha 8-bit rendering are explicit diagnostic hypotheses. Per
channel, an unknown background gives the allowed alpha-compositing interval;
the score measures residual outside it with half-unit rounding slack. Fully
transparent pixels convey no identity. Each animation retains a representative
best box and tied-hypothesis count. No confidence threshold, selected state,
active-skin verification or G2 safety flag is generated. Standing may still be
the statically observed null-player fallback; absent attack borders cannot
establish native melee OFF. Attack-border classification is not implemented.

**VERIFIED focused tests:** 23 tests passed in 1.38 seconds, covering tall-control
placement, scaling/alpha, ties, transparent templates, bounded search, source
changes and consistent/inconsistent parent crops. After adding the explicit
texture-at-capture unknown flag, its focused regression passed again. CLI help,
compile and whitespace checks passed. No full suite ran.

**VERIFIED copied-source experiment, not live:** the five real combat sprites,
rendered at a synthetic 16×16 size/offset into a 17×33 control over a fixed fake
background, each ranked correctly under nearest and bilinear rendering: 10/10
unique best matches, zero residual for their corresponding source. Runtime
11.68 seconds for all ten offline searches; this does not establish the 100 ms
live scene budget. Private evidence `evidence/combat-ui-ranking-0.41.72.json`,
SHA `1d341c177e600c0ae31c91bee562d23c389fccd4c119990b8b8cda5d18febcbb`,
pins atlas manifest `7d7a98dd3055c76bac46bdb7adc7b9b34820cd6549e1666c67ead1130a92df21`.
No game pixels/assets were added to git.

**Current live gate:** one read-only Alienware listing this turn found zero
`g2-ui-observations/*/unbound-location.json` pairs. No capture was initiated.
The existing 0.39.9 stationary capture is sufficient input for the first icon
diagnostic; no different owner test or G0 repeat is needed. Current live
calibration, complete scene/motion providers and real route acceptance remain
missing. Assist 0.39.6 is unchanged. Level, XP/hour, deaths and camp remain
unknown; no accepted 1–20 or fresh-character 1–50 run exists.

## Private source 0.41.71 staging — 2026-11-14 05:15 UTC

**VERIFIED:** Commit `a7976735dc7b8dcf5599e3388552c00bf33c6f51`, archive SHA
`1942a0318cd706afe6de17247a70beae95a745f326ecd8bddcc7441531064212`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.71/source`.
Six remote synthetic/no-input startup checks pass: version, history skip without
permission, singular-damage latch surviving OFF, missing-file latch surviving
creation, chat/malformed-transition classification, and required provider
arguments plus location-collector CLI startup. Remote `../smoke.json` and local
`releases/eql-automation-0.41.71-staging.json` retain the result. The smoke opened
no client assets, captures, input devices or login. Owner assist remains 0.39.6;
no real-client route acceptance is claimed.

## Latched movement log veto — 2026-11-14 05:14 UTC

**VERIFIED source 0.41.71:** `scene_log_veto.py` baselines the expected character/
server log once per owner-started measurement generation. New incoming attacks,
native melee ON, death, zoning, target selection and observed player hazards
latch a veto. Missing files, replacement/truncation/backlog/anchor resets,
partial lines, decode/parser errors and backward/invalid clocks lose continuity
and latch refusal. Existing history is never replayed; equal source seconds are
accepted. Neither silence nor OFF clears a latch or supplies a safety flag.

`G2SafetyProvider` now requires this monitor and the caller's expected log path,
checks it before and after UI/input observations, and rechecks cancellation,
mode, focus and process after log I/O. An independent review reproduced a
cancellation during the final poll; the added post-poll binding check and four
regressions address it. Recognized malformed transition/melee prefixes also
veto. Filename binding is not active-character proof: the eventual assembly
must bind the owner-selected character/log to the window. Current UI flags
remain independently required and the provider remains measurement-only.

**VERIFIED focused checks:** 80 reader/provider tests passed in 0.58 seconds;
three real-watchdog pipe cases passed in 1.06 seconds. Those cases inject a
logged attack before DOWN, after DOWN and during final release, confirming
release/no floor commit. Their scene, motion and geometry evidence is synthetic;
no input device or real client was used. Compile and whitespace checks passed;
no full suite ran.

**VERIFIED retained-log audit:** 22,705 parsed lines from owner log SHA
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`.
The corrected classifier finds 4,350 incoming attacks, 67 native melee ON,
214 target selections, six deaths, 57 zone-transition messages and 58 player
hazards, with no chat matches in the checked chat envelopes. All retained
` YOU for ` / ` YOU,` shapes match. Initial audit exposed 1,336 missed singular
`point of damage` lines; the plural-optional pattern and regression fix that.
The first audit remains retained and is superseded by private
`evidence/scene-log-veto-0.41.71-v2.json`, SHA
`d9ee4eaa7f27dead154054f8636cac9e48ed58fc059daf39bc4a76e04b632631`.
These observed formats are a subset, not proof of complete combat logging or
live safety. No client capture/input/login was initiated.

**Live gate unchanged:** G0 visible stop is owner-confirmed and needs no repeat.
Assist 0.39.6 and observation candidate 0.39.9 are unchanged; the source adapter
is not wired into an owner movement control. The pending stationary owner
position/UI pair, current calibration, complete live scene/motion providers
and actual route acceptance are still missing. Level, XP, XP/hour, deaths and
camp remain unknown; there is no accepted 1–20 run or fresh-character 1–50 proof.

## Private source 0.41.70 staging — 2026-11-14 05:07 UTC

**VERIFIED:** Commit `7ff2503642f52bb490cf1b30a607fe63fdcd7965`, archive SHA
`a4b7f3ddcc1bc60724c810bb1c3a24d7b8b5695c19bb169aac6c30a6c3c0827b`,
is staged on Alienware at `~/.local/share/eql-automation/owner-tools/0.41.70/source`.
Six remote startup checks pass: version, synthetic exact-RGBA atlas extraction,
unknown runtime fields preserved, changed texture refusal, extractor CLI and
location collector CLI. These checks use fabricated textures, not game capture
or client assets. No input device/login was opened. Remote `../smoke.json` and
local `releases/eql-automation-0.41.70-staging.json` retain the result. Current
assist and observation candidate are unchanged. Their rotation_core.py files
have the same SHA `9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113`,
so the new-data candidate-profile comparison covers that shared profile code.

## Current client UI templates and patch reconciliation — 2026-11-14 05:06 UTC

**VERIFIED source 0.41.70:** `combat_ui_atlas.py` reads a hash-pinned private
manifest, XML and textures, retaining exact source coordinates, frame ordering,
durations, optional fields and RGBA bytes. It refuses changed inputs, symlinks,
missing textures, ambiguous definitions and invalid bounds. It preserves absent
XML fields as unknown rather than inventing defaults. The extraction CLI writes
only to a new private directory, never the install/prefix. Thirteen focused tests
pass; after replacing a deprecated Pillow test accessor, that specific test also
passes. Actual client extraction and CLI/compile smoke pass. No full suite ran.

**VERIFIED read-only current assets:** saved skin is `default_light`; active
live skin is still unverified. Its `EQUI_PlayerWindow.xml` has SHA
`2ebd1af9bb330606c4b604c02b78c6f40fab39f316b1bc7edd839c1568125869`,
`AttackIndicator.tga` has SHA
`d0bb709872f3c647474ab863008348c03ad47856df37680760d6c071df3ec0b6`,
and `window_pieces06.tga` has SHA
`3fc79c8f70b6195091a54ab29e9380f53133c261f0909db7967f0102e3d164ec`.
Copies and source paths are retained under private
`client-data/ui-combat-assets-20261114T045805Z/`; manifest SHA
`7d7a98dd3055c76bac46bdb7adc7b9b34820cd6549e1666c67ead1130a92df21`.
The extracted 11-frame atlas is
`ui-templates/combat-atlas-0.41.70/atlas.json`, SHA
`b998545568dd7642f647a1b2d435a1d99e0f4c4da0ded88fa0b12d867effc77f`.
Five combat sprites are 40×40 at x=200, y=0/40/80/120/160. Attack indicators
include duplicate source regions; several StaticAnimation controls explicitly
have AutoDraw=false. No live classifier or G2 safety flag is produced. Initial
read-only copies of default EQUI_Animations.xml/MapViewWnd.xml are separately
retained in `client-data/ui-scene-20261114T045729Z/manifest.json`.

**VERIFIED installed executable changed:** at 05:02:40 UTC its SHA was
`fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36`
(15,714,424 bytes), differing from the earlier `65b8a28b…` copy. A matching fresh
copy is `client-data/runtime-20261114T0503Z/eqgame.exe`; the prior copy was kept.
The initial old-binary analysis remains historical, and its current-build
assertion correctly failed. No old addresses were adopted for the new build.

**OBSERVED static mapping on the new copy, not execution:** bounded PE/RIP
reference inspection and GNU objdump show the constructor loading
`PW_CombatStateAnim` at `0x1404dcd50`, storing its lookup at `this+0x430` at
`0x1404dcd70`. Selector `0x1404df5d0` uses that field, caches state at +0x474,
and assigns its animation result to widget+0x368 at `0x1404df861`:

| State | Client animation | Branch | Client tooltip ID |
|---|---|---|---|
| 0 | A_PWCSInCombat | 0x1404df803 | 9172 |
| 1 | A_PWCSDebuff | 0x1404df7c5 | 9173 |
| 2 | A_PWCSTimer | 0x1404df787 | 9177 |
| 3 | A_PWCSStanding | 0x1404df746 | 9175 |
| 4 | A_PWCSRegen | 0x1404df6fb | 9176 |

**Critical limit:** null global `0x140f37db8` also selects Standing. A Standing
match cannot establish a valid in-world player, combat safety or no incoming
attack. The virtual +0x138/+0x140 calls and entry-field semantics remain unknown.
The five names and branch structure persist, but old widget/cache/animation
fields were +0x420/+0x464/+0x358. A separate selector using these same assets
belongs to an unproven widget and was not merged into the player mapping.
Read-only independent review confirmed the new disassembly hashes and mapping.
Current static probe SHA
`98ab0ec9a9061f8f996fa4ab0d09f963e8f1f9615aab4085d1eae0f277ff83bc`,
binding record SHA
`056e9678ec2cf054c853bab7a819169a81cb21b23c4ea730fe0222df3818cddc`,
in `evidence/combat-ui-static-20261114T0503Z/`. Client tooltip strings were read
from installed `eqstr_us.txt`, SHA
`0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`;
selected-string record SHA
`17c395849e936c0039c405ab2dd39aef81eece291fff2b8dc21590b3dc301d20`
is retained in the preceding `…T0500Z/` directory.

The reverse-engineer-anything skill was applied. REA deep providers remain
unavailable (Ghidra JDK missing); no access/configuration changes were made.
Its portable objdump call reached a 10-second provider deadline with a partial
header record `ev_1c4bbd508e72fbe4aaf92370cd2b9932ae1730fb3a01b4c99db72a75617da3c1`.
That was preserved, not retried as completed evidence. The exported/reset bundle
`evidence/combat-ui-rea-20261114T0500Z.json` has SHA
`ff2beb4b9bc05fee3f1fd7f6d72f70a1eb188c6e8ebbadbce2f7587c213f651b`.
Successful bounded shell objdump runs above are labelled shell evidence, not
REA decompilation. No binary was executed or running process attached.

**VERIFIED selected data reconciliation:** all seven checked GFay/Butcherblock/
Crushbone terrain/object archives still match copied inputs. `spells_us.txt`
changed from `8db55486…` to
`c179a57fe444a65838c3728895e57161912eb527e77d92859ecb007a3236c8e9`.
The eight-file read-only comparison took 0.055 seconds remotely; artifact
`evidence/selected-client-data-20261114T0504Z.json`, SHA
`f22877de12a9d095cd141a2fe51e4c20ffb0fc4084977e64fcb5bd298ed7a065`.
Current spells and complete dbstr were copied to the new runtime snapshot;
class-source SHA `5a1a4d496e01c256ab32114b1a6ea5d699fafec08b17cfaa88684dd6746b1e53`.
The 174-field parser and retained helper Catalog both accept the new file:
74,021→74,023 rows, two added, none removed, 18 changed. No changed row is a
Paladin/Cleric level 1–20 spell; candidate helper profiles for all levels 1–20
are identical. This does not establish ownership, scribing, server availability
or live casting. Audit SHA
`28bec61a75828b99883dc100ae2b6cb72aa24d8e68966596f80369af1c3cfdb4`,
`evidence/spell-update-20261114T0505Z.json`. The refreshed 16-class index is
`map-store/indices/spell-levels-c179a57fe444a658-5a1a4d496e01c256.json.gz`, SHA
`61c320963702a41b96d588aca593fae83a76f64a4d49a65f267e3f000b31e4fd`.
An initial 25 MiB transfer bound refused the 38,381,991-byte spell file before
writing; the corrected 64 MiB bounded read completed with the expected hash.

**Live gate unchanged:** one read-only listing this turn found zero paired
position records. No game capture/input/login occurred. Current level, XP,
XP/hour, deaths and camp remain unknown. G0 needs no repeat. Assist 0.39.6,
observation candidate 0.39.9 and F11/F12 disabled state remain unchanged. The
next scene work needs actual current capture/placement/calibration and complete
independent safety evidence; source templates alone do not enable movement.

## Private source 0.41.69 staging — 2026-11-14 04:56 UTC

**VERIFIED:** Commit `e9e687477844906892ffdba12f5438c7ac04cb00`, archive SHA
`68838c535e6b3680b572977a750849deb38d7f3940afd8d3dcb805d1e0dd202b`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.69/source`.
Six no-input startup checks pass: version, route-bridge import/startup, missing
live-provider refusal, missing route-state refusal, replay CLI and location
collector CLI. Remote `../smoke.json` and local private
`releases/eql-automation-0.41.69-staging.json` retain the result. No client data,
input device, capture, login or game input was opened. Source search confirms
no owner runtime imports the new bridge. Assist 0.39.6 and observation candidate
0.39.9 remain unchanged; this is source staging, not playable-route acceptance.

## Checked route sender bridge — 2026-11-14 04:54 UTC

**VERIFIED source 0.41.69:** The new isolated `run_checked_route_step` adapter
joins the real release watchdog and `RouteFloorCommit` through the existing
sender interface. Every provider is mandatory. Scene checks bind the exact
stopped aligned/raw reference, zone/log generation/sequence/coordinates and
freshness; current position while moving is never inferred from that reference.
Proposal creation follows watchdog READY. An explicit external authorization
must bind that staged request; a conditional FloorTrial alone is rejected.
Complete swept-body coverage, measured speed/drift/hold bounds, static/BSP and
dynamic hazards still belong to the external guard, which is not implemented as
a live provider here. Slow checks expire the existing 50 ms deadline rather than
refreshing it. `RouteFloorCommit.check_pending` rechecks snapshots before GO and
throughout the operation without consuming or authorizing the ticket.

The adapter requires the shared reentrant OFF/GO lock, an idle sender with no
command/recovery state, and an exclusive sender operation. It duplicates the
existing descriptor for watchdog lifetime, preventing cleanup from reaching an
unrelated reused descriptor. Final sender UP/SYN and held-key acknowledgement
must succeed before commit. Device changes or final-release failure retain the
held marker, discard the fork and halt. All writers/device lifecycle must obey
the same lock/exclusive-operation contract. Generation changes and reentrant
OFF invalidate the step. A successful receipt still proves device writes only;
the follower requires new stopped fixes before another step.

**VERIFIED:** 67 focused checks passed in 5.44 seconds, using the actual watchdog
subprocess on pipes and the retained follower/ground/floor machinery. Cases cover
successful cleanup-before-commit, drafts/recovery/dismissed/assist refusal,
missing or offline-only authorization, altered scene/reference/floor, slow or
invalid authorization, stop/rearm/unsafe scene after DOWN, failed final release,
reentrant operation, cancellation during cleanup, descriptor reuse, a key
re-added by a post-release callback, and failure to close the pinned descriptor.
The latter two regressions were added after focused read-only source review.
The final 67-check run includes both fixes. The descriptor identity check does
not prove the same open-file description if the same device is reopened; the
explicit lifecycle exclusivity contract remains essential.
No full suite, full copied replay or live input was run this release.

**Not verified / still required:** current owner scene/UI/height/motion bounds,
independently calibrated live safety and complete motion-guard providers, actual
owner helper wiring and client consumption. G2SafetyProvider remains explicitly
measurement-only; no full-auto mode or provider default was silently added.
The adapter is not imported by the owner helper. G0 passed, no repeat needed;
assist 0.39.6 and observation candidate 0.39.9 remain unchanged. Current level,
XP, XP/hour, deaths and camp remain unknown; no live 1–20 or 1–50 run is accepted.

## Private source 0.41.68 staging — 2026-11-14 04:48 UTC

**VERIFIED:** Commit `a3fccf43b330f283a805f7a34352b73ede606107`, archive SHA
`31b344b027f20faa2465219c4b872eba9a32a2ecd122a5bc5c961f10a0550c06`,
is staged on Alienware at `~/.local/share/eql-automation/owner-tools/0.41.68/source`.
Five no-input startup checks pass: version, non-authorizing record construction,
missing route-state refusal, replay CLI and location collector CLI. Remote
`../smoke.json` and local private `releases/eql-automation-0.41.68-staging.json`
retain the result. No client assets, input device, capture, login or game input
were used. Assist 0.39.6 and observation candidate 0.39.9 remain unchanged.

## Receipt-bound floor commits and completed printed-feedback replay — 2026-11-14 04:47 UTC

**VERIFIED source 0.41.68:** `RouteFloorCommit` owns one committed source chain and
one pending update. It gives the geometry callback the exact immutable proposal,
current aligned fix, footprint/source tuple, key, requested/maximum hold and
external motion-bound record ID, plus a shallow chain fork. It checks the
returned floor proof's ancestry, geometry digest, expanded footprint and selected
patches. Deep snapshots catch changed chain contents, pose, motion, calibration,
route, mode and generation. This preserves identity; the external guard must
still prove the supplied footprint covers actual movement with current measured
bounds and complete scene/static/BSP/dynamic checks.

Receipt integration uses the same reentrant OFF/GO lock, matching key/duration,
finite ordered times, a current one-use ticket, DOWN no earlier than completed
staging and no later than the proposal deadline, and UP-complete minus DOWN-start
within the staged bound (at most 0.20 seconds). Only successful
`FixedRouteFollower.record_release()` commits the fork. Failure, stale/repeated
receipt, context change, cancellation, swallowed/no-op integration or reentrant
operation discards pending state and halts. It does not pretend already-simulated
or physical movement was rolled back. No input device is owned or opened, no
key is sent, and preparation/ticket/conditional floor records remain explicitly
non-authorizing. The sender adapter must establish receipt provenance and client
key consumption; constructing a PulseReceipt object cannot prove either.

**VERIFIED:** 39 focused checks pass. The actual separate watchdog writes DOWN/UP
to a pipe; its returned timestamps commit the checked fork, then synthetic
stopped fixes run through the real ground producer and retained follower back
to `ready`. The extended pipe/ground/follower test was also rerun alone after its
last assertion was added. No game/device/live scene was used and no full suite
was run. The initial immutable-Motion fixture error was corrected to replace the
calibration object. Review caught and corrected staging-time ordering and
reentrant-operation gaps before release.

**VERIFIED completed copied replay (source 0.41.67):**
`nav-candidates/gfay-client-observation-replay-0.41.67-budget1200.json`, SHA
`b70de7f0f9bfa193ce83e1b9bcee3d16be63b8920357a9c49e622e8b4de0f603`,
arrived at **155/155 segments in 2,323 steps**. All 2,323 source-floor, static-object
and BSP-volume trials passed, as did 2,324 stopped observation pairs. There were
2,324 committed floor cells; final proof
`c5aff2f9d468fd646b79cf7d44d1007267b4790a65ae9d2c77ce5a7adb2b8431`.
All 48 input pins rechecked. Runtime **508.417698391 wall / 147.502962158 CPU
seconds**, no budget exhaustion, observation failure or sweep failure. Maximum
physical/printed XY difference is 0.006980280448 and raw-height residual
0.007485565464. The first 600-second attempt remains unchanged evidence of its
checked prefix; variable scheduling made elapsed time differ between attempts.

**Not verified:** current live zone/UI/frame/height/speed/drift, sender integration,
real route movement, dynamic hazards, camp combat, XP or level gain. The completed
replay uses simulated physical-pose guards and conditional body/motion bounds.
No owner adapter imports the new commit component. Read-only Alienware listing at
04:46 UTC still found zero paired position records. G0 passed and needs no repeat.

## Private source 0.41.67 staging and longer replay — 2026-11-14 04:37 UTC

**VERIFIED:** Commit `a944b44a5d8ce229f4993fc6530b27ceb3243595`, archive SHA
`52dcb4254b6ec17c8fa709f7fa814c75f1b873d20e9ee82f3488929b220967cf`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.67/source`.
Six no-input startup checks pass: source version, physical/printed-coordinate
separation, paired timing/sequence, producer-refusal evidence, replay CLI and
location collector CLI. These use synthetic records; no client assets, capture,
input device or login was opened. Remote `../smoke.json` and local private
`releases/eql-automation-0.41.67-staging.json` retain the result.

A separate 1,200-second copied replay is **running**, PID 1908498 / tool session
47911, output `nav-candidates/gfay-client-observation-replay-0.41.67-budget1200.json`.
It has not yet produced an outcome; revalidate that handle/process before any
restart. The first 600-second run remains immutable and incomplete at 117/155
segments. Private publication is source tooling only; no live acceptance, F11
enablement or automated character progress is claimed.

## Full follower with client-format feedback — 2026-11-14 04:36 UTC

**VERIFIED source 0.41.67:** Commit `1de3504` adds optional
`--client-observations` to the copied-route replay. Raw coordinates come from the
physical source floor plus the synthetic character offset, printed through
Python's two-decimal model of the retained log examples. Client tie-rounding
semantics have not been separately verified. The production `RouteGroundObserver`
re-samples exact source and baked support at those printed coordinates and feeds
the existing `FixedRouteFollower`. The physical simulated pose/heading are never
replaced by observed/estimated positions. The proposed source-floor fork is
committed after simulated release, before the next observation. Producer refusal
is retained as a route halt with physical and raw coordinates, not lost as an
uncaught exception. Recent/history records retain both coordinate sets.

**VERIFIED:** Four focused tests pass, including unchanged physical pose,
independent source/baked heights, existing adjacent-portal bounds, exact-gap
refusal with diagnostic data, and straight/turning feedback through the actual
retained steering code. No full suite run.

**VERIFIED partial copied run:**
`nav-candidates/gfay-client-observation-replay-0.41.67.json`, SHA
`15a465a312e1981aed16f33d8fab04eae8f09e676b69bf7a36b4317f35505e6f`,
halted solely at the explicit 600-second wall budget: **1,771 steps, 117/155
segments reached, 1,772 observation pairs**, with all 1,771 terrain, static-object
and BSP trials accepted and no observation/sweep failure. Runtime was
600.712159460 wall / 121.103933281 CPU seconds. All 48 input pins were rechecked
before changing the wall-budget CLI bound. Maximum physical/observed XY difference
was 0.006980280448; maximum raw-height residual 0.007485565464.
This establishes a checked prefix only. The attempted path differs from the older
ideal-coordinate replay and cannot inherit its remaining-segment result.

The next run uses an explicit 1,200-second budget; the CLI's maximum is now
1,800 seconds while its default remains 35. Priority remains nice 15. This changes
only offline elapsed-time allowance, not route, pulse or geometry thresholds.
The whole-volume guards still use simulated physical pose/heading and hypothetical
body/speed/drift bounds; no live input permit is created. No account, client,
input device or game capture was used. The read-only Alienware listing at
04:26 UTC still found zero paired position records. G0 remains passed; no repeat.

The next real runtime integration must bind each checked floor fork and permitted
hold bound to the exact current proposal and commit only after a successful
watchdog DOWN-start/UP-complete receipt. Cancellation/overrun must discard the
fork and halt. Current zone/UI/frame/height/speed observations remain external
requirements. Existing G0 and assist entry points are unchanged.

## Private source 0.41.66 staging — 2026-11-14 04:23 UTC

**VERIFIED:** Commit `b48d4b37a18fa7b538ba23d74a76b42b504f8ff0`, source archive SHA
`5e6a93b72dae25b3a60ef1b78f7237a67d5c740481fb0fcef6c560dec27f4e4b`,
is staged on Alienware at `~/.local/share/eql-automation/owner-tools/0.41.66/source`.
Six startup/synthetic checks pass: version, printed-axis/source-height serialization,
format validation, incomplete floor-ledger refusal, probe CLI and location-collector
CLI. Remote `../smoke.json` and local private
`releases/eql-automation-0.41.66-staging.json` record the result. No client assets,
devices, capture, login or game input were used. Assist 0.39.6 and candidate 0.39.9
are unchanged; no live acceptance or level gain is claimed.

## Client-format observations and committed floor context — 2026-11-14 04:21 UTC

**VERIFIED source 0.41.66:** The copied ground probe now optionally reconstructs
committed source-floor cells and models the observed client log representation.
The retained `owner-traces/eqlog-Legira-20261113.txt` (SHA
`d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e`)
has 68 location examples, all with two decimal places on each axis. This is
format evidence from those examples, not a guarantee for every client build.
Synthetic raw Z is the source floor at the physical position plus offset 2.564;
it is then printed and parsed along with XY. The physical pose and production
observer are unchanged. No source height is derived from baked Z or rounded raw Z.

The earlier step-1856 refusal is attributed to a real copied tile gap. The
planned portal `(148.4438018798828, 1343.3875732421875)` has exact support in
polygon 20481. Replay motion displaced it by approximately `(3.24e-11, 2.25e-11)`
into the gap before polygon 20500, whose edge is Y=1343.3876953125. The gap is
0.0001220703125 (one float32 ULP), classified as an exact tile side. The producer
correctly refused that idealized raw point. At the observed log representation,
helper XY `(148.44, 1343.39)` is exactly supported in polygon 20500; source Z is
-8.658088500271823 and baked Z is -8.171095156657957. No edge snap, endpoint
canonicalization or wider production tolerance was introduced.

**VERIFIED copied-data run:**
`nav-candidates/gfay-ground-producer-probe-0.41.66.json`, SHA
`1a1131ce8454daabe4f44a548e9aa3411e3b1d1b2fb6718609c295dd91b8d3ad`,
accepts **211/211 samples across 209 distinct steps**. Reconstructing the initial
cell and all 2,191 committed step cells reproduces every retained floor proof,
including the final `dbc2128db3c931665dc52ce44183258a42cbe7e6b19becc475e8c0f10a9ca4f8`.
Source/static/BSP trial step, segment, duration, acceptance and footprint identity
are checked before reconstruction. Static/BSP traversal is not rerun here.
Sample observations use the postcommit cell; duplicates and original output order
are preserved. Maximum raw-height residual is 0.0070871339, XY displacement
0.0067374863 and baked-height change from the old sample 0.0030731438 units.
Runtime 89.009742378 wall / 62.048562518 CPU seconds; all 25 input pins rechecked.

**VERIFIED:** 14 focused checks pass for serialization, exact gap refusal,
source-versus-baked height, postcommit indexing, proof identity, mismatched or
rejected trial refusal and unchanged chain during sampling. No full suite run.
**Not verified:** complete steering using quantized observations, live calibration,
current zone/UI, speed/drift or route execution. Source-floor reconstruction is
an offline context, not a live bootstrap. No game input, capture or login.
Read-only Alienware listing at 04:17 UTC still found zero paired position records.
G0 remains owner-confirmed passed; no repeat or new test is requested.

## Private source 0.41.65 staging — 2026-11-14 04:14 UTC

**VERIFIED:** Source commit `ae680f284bf44534e4d0158ad0d39ccefa9fbe21`, archive SHA
`2853d27c12ff713227382d8e343a374f389e25b81af0d3c5304a618c71338ab3`, matched on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.65/source`. Six synthetic/startup
checks passed: import/version, exact triangle support, missing edge support,
ambiguous heights, probe CLI and the location collector CLI. No client assets,
devices, real capture or game input were used. Remote `../smoke.json` and local
private `releases/eql-automation-0.41.65-staging.json` retain the scope.
Owner assist 0.39.6 and observation candidate 0.39.9 are unchanged.

## Ground-position producer for the retained route follower — 2026-11-14 04:13 UTC

**VERIFIED source 0.41.65:** `RouteGroundObserver` now produces source-floor,
mesh-projection and aligned-position records from a fresh `RawLocationFix`,
pinned copied geometry and an externally supplied current `HeightCalibration`.
It creates no calibration, never converts an unbound diagnostic, preserves the
same raw object and exact XY, and independently measures source Z and baked Z.
The identity WLD frame and helper XY swap remain explicit. Current selected
polygon support takes precedence; only verified absence allows a selected
adjacent polygon within the existing portal disk. Source/height failure cannot
select a more convenient neighbor. Every result passes the existing binding
validator against the exact supplied calibration object and geometry context.

The new detail query distinguishes absent, supported and ambiguous geometry.
It uses exact rational arithmetic on the stored floats, without the older
replay helper's up-to-0.0005-unit edge projection. Missing/malformed/degenerate
or excessive detail data refuses. Reciprocal dry same-component links and
source/mesh hashes are checked. The file loader rechecks copied inputs after
loading and makes array views read-only. An optional committed source-floor
chain is sampled without `advance()` or state mutation; otherwise the existing
all-layer source query refuses layered/unsupported floors. No raw Z or offset
is used to choose a source layer.

Forty-two focused checks pass, including an integration with the actual pinned
`eqnav.steer` follower: produced observations advance its two synthetic route
segments to arrival. Checks cover unequal raw axes and three different heights,
current-polygon precedence, conflicting detail heights, tiny unsupported gaps,
current height/source/session/age refusal, unbound records and unchanged source
chain state on success/refusal. The private NumPy Python 3.13 environment ran
these tests using the installed pure-Python pytest runner with plugin autoload
disabled. Earlier attempts exposed missing pytest there and a Python 3.12/3.13
NumPy mismatch; neither was a code result. The successful run used matching
Python/NumPy, with no dependency/access changes.

**VERIFIED copied-geometry probe, synthetic calibration only:** 199 of 211
retained replay samples pass the producer. Ten all-layer source queries refuse
missing/layered support and one refuses collision/material flags; this probe
did not reconstruct/use the committed floor chain. One other sample, step 1856
at segment 127, has no exact support on current polygon 20481 or next polygon
20500. Both old edge-projection lookups supplied Z; the new producer refuses.
Its position is approximately 3.94e-11 units from the planned portal. This
needs attribution/correction, not a tolerance increase or an accepted live leg.
The maximum baked-Z difference from prior replay among accepted samples is
3.73e-5 units. Runtime was 23.58 wall/7.83 CPU seconds.

Artifact `nav-candidates/gfay-ground-producer-probe-0.41.65.json`, SHA
`db2d1311f27fbfeb52383ae326048f446c54b2ca9ce9c61f49d37ce8cc8e3ed5`;
probe script SHA `430ddbb92a990bdaed478e047104b0f5c10fa5ad19990dd80741d529e8b83302`.
Its eight code/data pins rechecked. Source query and calibration fixtures are
explicitly offline; no live movement, actual alignment or route acceptance is
claimed. The previous whole-footprint BSP replay remains historical evidence,
not a substitute for these live observation requirements.

**Next:** connect the committed floor context and resolve exact portal support,
then pair current owner position/UI evidence with measured height/frame/speed
and checked movement. Owner assist 0.39.6, observation candidate 0.39.9 and the
0.41.61 standalone command are unchanged. No new owner test or G0 repeat is
requested. Current level/XP/rate/deaths/camp remain unknown, no automated level
gain is accepted, and the full 1–20/1–50 goals remain incomplete.

## Private source 0.41.64 staging — 2026-11-14 04:06 UTC

**VERIFIED:** Source commit `3c9cf0394597cd07153686cc7bbd0ca9264431e7`, archive SHA
`e6832e42c16fa23644846164ea97694c0a80bfc653b11e6c99e06171214a698e`, matched on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.64/source`. Four startup checks
pass: package/position/crop/adapter imports and the builder, location collector
and UI collector help paths. No game assets, capture, devices or input were
used. Remote `../smoke.json` and private local
`releases/eql-automation-0.41.64-staging.json` retain the record. Candidate
0.39.9's actual-engine synthetic event and GUI evidence is recorded below.
Current assist 0.39.6 and the original 0.41.61 collector remain available.

## Position/UI collection in the existing helper — 2026-11-14 04:06 UTC

**VERIFIED source 0.41.64 / candidate 0.39.9:** `Observe current position`
now starts a tick-driven session in the retained November helper. It opens the
exact character log at its end, waits for one newly appended owner-typed
`/location`, settles for two seconds across normal engine ticks, and reuses
the engine's existing gate for one capture. The shared crop writer sends no
input, sleeps nowhere and never closes the borrowed gate. It writes only
player/target/map crops and the existing unbound pair format to private storage.
The standalone 0.41.61 command remains valid and is not replaced.

The pinned helper's Slash/Enter dispatch now uses an explicit chat-open hook.
The inherited rotation-stop chain still runs and increments its generation.
Only an active, disarmed, sender-free diagnostic in its waiting/settling phase
may rebind to that exact synchronous chat stop. F9/F11, other stops/jobs,
settings/session changes and exit still cancel. A matching reason string
alone cannot preserve a session. Ordinary typing is allowed during the wait;
it is not treated as proof that the owner held still. No sender is created.

Ninety-eight local focused checks pass for the collector, unbound reader,
shared crop writer, location log and existing preflight. They cover ambiguous
extra locations, transitions/resets, focus/process changes, cancellation while
capturing, borrowed-gate ownership, chat omission and stopped-state behavior.
An actual retained-engine smoke on Alienware fed synthetic Slash/letter/Enter
and F9/F11 events plus temporary log bytes; collection completed or cancelled
as expected without devices, real capture or input. An offscreen GUI smoke
with an empty game directory shows the new button; worker/input/settings
writes are false. The final rendered instruction was inspected and says to
click the button BEFORE typing the command. The unpublished earlier text
snapshot is preserved under a `before-instruction-fix` suffix.

Candidate `~/.local/share/eql-automation/owner-assist/0.39.9` is privately staged.
Archive SHA `4dc6022f36b0dd434a88335147ccda82b6eb8622d9652b5322d835f9f9c6fbd6`;
engine SHA `48c6dd7cf6676284d8aafc1221a66ad71f1861cca82f6c9af56446504599848b`;
GUI SHA `776fca6816302a97dcdcd7fdf6f0b30f502076fa78c356b1d6f9f37f0c2f930d`;
render SHA `b0413ac5802165d7f9bbf4790a21ea69fcc82150325b3a0a2a3495823719c999`.
Private `releases/owner-assist-0.39.9-staging.json` records the smoke scope.
The pair retains unknown character/zone identity, alignment, log flush delay,
continuous focus and standing-still claims; it carries no movement permit.

**OBSERVED:** A read-only Alienware listing at 04:04 UTC found zero retained
`g2-ui-observations/*/unbound-location.json` records. No actual capture was
initiated by the lead. The next runtime work is source-ground observation
with externally supplied live height calibration, then UI/zone/speed providers
and checked movement. No live 1–20 route, automated XP or level 50 acceptance
is claimed. G0 stays passed; current owner assist stays 0.39.6. HOWTO provides
this GUI alternative to the same pending collection, not another G0 test.
No game input/login, client-install/access change, public release or git push.

## Private source 0.41.63 staging — 2026-11-14 03:58 UTC

**VERIFIED:** Source commit `6cc87d1469c17a3b1eb74e144bf564c4e47042e6`, archive SHA
`e9e152b191882309f6fd4a7f8552cd069225e534bde26ce91371b898b27f093a`, matched on
Alienware at `~/.local/share/eql-automation/owner-tools/0.41.63/source`.
Package/preflight imports, the candidate builder and location collector startup
checks pass there with no assets, captures or input. Remote `../smoke.json` and
private local `releases/eql-automation-0.41.63-staging.json` retain the record.
The separate candidate 0.39.8 engine/GUI smoke scope and hashes are below.
Owner assist 0.39.6 and the pending 0.41.61 collector remain unchanged.

## Existing-helper read-only observation — 2026-11-14 03:58 UTC

**VERIFIED source 0.41.63 / candidate 0.39.8:** The existing November rotation
engine now has a measurement-only `nav_preflight_later` job and GUI button.
It binds one game window/process and settings snapshot, waits across engine
ticks, opens the existing read-only input observer without creating a sender,
and takes baseline/later samples. Results contain counts and the explicit
missing UI, zone/ground, speed and checked-route providers; they never authorize
movement. Raw keys are not persisted. Queued requests retain their original
settings/generation/epoch; GUI posts revoke a pending result immediately.
F9/F11, settings changes, session/focus changes and helper exit close readers.
The inherited stopped state is preserved. This path does not capture the game.

Eighty-three focused tests pass, including cancellation during a scan or close,
queued settings changes, source/window/process identity and actual input-reader
fixtures. The actual retained helper's engine passes a synthetic dispatch/tick
smoke locally and on Alienware without opening devices, capture or sender.
The Alienware offscreen GUI smoke shows the new button and measurement-only
badge with worker/input/settings writes false; its PNG was inspected. The
initial help copy incorrectly said G0 was the only check; it was corrected,
and the final candidate was rebuilt and smoked. The unpublished earlier
snapshot is preserved with a `before-help-text-fix` suffix.

Final candidate archive SHA
`9516de9e4423c91599938db72ed685df8c155ee7d7840127d22de6f992144ba5`
matched on Alienware at `~/.local/share/eql-automation/owner-assist/0.39.8`.
GUI SHA `774f8d41d96ce5cf6e66a6cea1f9dc4a0f428e48523a89fdde40d2dcbe9de3f2`;
preflight source SHA
`4cc33a96723b48973e8237418320ebcd1f6bce948c1b725630d29155f4cea9b0`;
render SHA `4664190bdc36ec28fc5022e186b973608ec93ce9d7d415183c616d69de7a26d7`.
Private `releases/owner-assist-0.39.8-staging.json` records the smoke scope.
No live input/session observation through this integration is accepted.

**OBSERVED remaining gap:** There is still no retained real game UI crop or
paired location/UI record in the local approved store. The then-assumed
browsed-map label semantics were superseded by the source 0.42.8 native audit
above; live label freshness remains unverified. Next implement a tick-driven,
owner-invoked location/UI collection session in the helper using the existing
unbound collector; retain its unknown identity/zone/alignment fields. Then
wire source-ground observation with live height calibration, rather than
reusing synthetic replay calibration. These are actual runtime dependencies.

Assist 0.39.6, the pending owner collector command at 0.41.61 and completed G0
remain unchanged. No new/repeated owner test is requested. Full-auto 1–20,
automated XP and fresh-character level 50 remain unverified. No lead login,
game input, installation/access change, public release or git push occurred.

## Private 0.41.62 staging — 2026-11-14 03:46 UTC

**VERIFIED:** Commit `8ddde9bec83ae906784e0066767f313f074a6738`, archive SHA
`e6fb63e2d9a417bc3d5f51276b0133f53e308f45e8eca4a8e65e40b9656e8ebd`, matched at
Alienware `~/.local/share/eql-automation/owner-tools/0.41.62/source`. Eleven
synthetic/startup checks passed: interior water, upper-body plane contact,
exact arithmetic, cycle/budget refusal, terrain-cell binding, axis swap,
changed-cell refusal, outward report bounds, CLI starts and required flags.
No client assets, game input or UI capture were opened. Remote `../smoke.json`
and local `releases/eql-automation-0.41.62-staging.json` retain the scope.
The owner's pending collector command remains on 0.41.61; assist 0.39.6 and
G0 candidate 0.39.7 remain unchanged. No repeated/new owner test is requested.

## Complete GFay replay with copied BSP volumes — 2026-11-14 03:45 UTC

**VERIFIED source 0.41.62:** All 155 segments and 2,191 simulated steps arrive
with terrain, all-flag static occupancy and full-prism copied BSP checks enabled.
Every one of the 2,191 BSP checks passes: 28,837 total node visits, at most 27
per prism, 35 distinct regions across the run, and at most three regions per
prism. No labelled/unknown region, geometry refusal or budget exhaustion occurs.
Both the terrain and static trial sequences exactly match 0.41.61. All 44
code/data pins rechecked. Elapsed 440.80 wall/117.85 CPU seconds; the faster
wall time than the preceding run is not claimed as a computational speedup.

Artifact `nav-candidates/gfay-bsp-volume-replay-0.41.62.json`, SHA
`ff21dfa92e8dbd391002512ed7d5950280655ac066b3967b0e0d8b9ee4af6319`.
Code baseline `5afeb82`; BSP inventory SHA
`43958a80b7a7c2d7d8768658ba6a909a78030b2ec77b000406815dad5c5c5a9b`;
source WLD SHA `3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138`.
The existing copied frame control still resolves the swapped helper trigger
to region 2859, a Felwithe zone-line hint. It does not prove a live transition.

**Implemented and fixture-verified:** The exact accepted cell digest binds
selected floor patches to the new volume. Its XY expansion matches the terrain
occupancy check; exact rational clipping yields local floor-height bounds.
The prism extends from the lowest floor minus 0.1 below-clearance and 0.01
numeric margin to the highest floor plus hypothetical body height 8 and 0.01.
Exact plane arithmetic retains small offsets; report floats round outward and
do not drive traversal. Both children are visited on contact/straddling. Any
label, missing child/region, cycle, or visit/depth exhaustion refuses before
simulated movement or proposed-floor commit. Keeping the whole prism during
traversal may conservatively visit extra leaves; refusals are not asserted to
be exact intersection witnesses. The initial seed remains terrain-only, with
all actual motion footprints checked anew.

Fifty focused tests pass, including an interior water pocket missed by corners
and centerline, upper-body/side/below-floor hazards, exact plane contact,
rounding-sensitive arithmetic, malformed trees and budgets, clipped sloped
floors, coordinate swapping and refused-state preservation. Eleven local
no-input startup/guard checks pass. This checks copied labels and hypothetical
geometry; it does not establish live dryness, body dimensions, dynamics,
current alignment/speed or real route following.

**OBSERVED remaining live implementation gap:** Current production code has
no caller constructing G2SafetyProvider/G2ReadOnlySceneObserver or producing
live AlignedWldFix/HeightCalibration/MeshProjection; those constructions remain
in the synthetic replay. The owner preview restricts movement to G0. The
current location reader also needs a new zone-entry event; the stationary
collector deliberately cannot bypass that with an unverified map label.
A read-only listing of the latest private capture directories at 03:37 UTC
found no paired location/UI record; no capture/input was performed.

**Next:** owner-controlled fresh scene/position evidence, live zone and ground
providers, calibrated UI/input observations, speed/drift measurement and
checked owner-helper integration. The previously staged collector command
at 0.41.61 is unchanged. G0 remains passed with no repeat. No live 1–20 route,
automated XP gain, fresh-character run or level 50 completion is accepted.

## Private 0.41.61 staging — 2026-11-14 03:33 UTC

**VERIFIED:** Source commit `b5cd4a50eabe2e8d9c719505b283c6e4153c00bc` and
archive SHA `06896aff0ba6794a9ee394906171de5e4e9c685021e81fa1aded7c48298baf15`
matched at Alienware `~/.local/share/eql-automation/owner-tools/0.41.61/source`.
Fourteen synthetic/startup checks passed remotely, including static-wall
refusal, exact terrain-cell binding, fresh unbound log collection, changed
process/transition refusal, timing pairing, three CLI help paths and invalid
static-replay options. No client assets, input devices or actual UI capture
were opened. `../smoke.json` and the private local record
`releases/eql-automation-0.41.61-staging.json` preserve the exact checks.

The owner can run `python3 tools/capture_owner_location.py --character Legira
--server freeport` from that source directory, then manually issue `/location`
once while standing still with the map on Current Zone. HOWTO has the complete
procedure. The lead has not run a live capture; no repeated G0 is requested.
This is an unbound observation collector, not F11 or a movement permit.

## Static-inclusive GFay replay and stationary capture tool — 2026-11-14 03:32 UTC

**VERIFIED source 0.41.61:** The revised GFay route completes all 155 segments
in 2,191 simulated steps with the parity-checked static inventory connected to
every accepted terrain trial. All 2,191 combined occupancy checks pass;
1,014 queries contain static faces, with at most 32 static faces per query.
The combined classifications include 1,781 overhead and 8,907 outside-footprint
face observations. All 109,932 source faces/flags remain in the inventory;
queries are not height-filtered, discarded or truncated to obtain this result.

The full terrain-trial sequence is byte-structure identical to the preceding
terrain-only run. It commits the same 2,192 terrain cells including the seed;
static objects only obstruct and never become a selected terrain floor. A
failed static check discards the proposed floor fork before shortening/rechecking
or halting. The initial seed is terrain-only; all actual motion footprints
are then checked for static occupancy. This is conditional copied-source
occupancy under hypothetical body height 8, speed and drift, not actual client
collision, complete BSP hazards, dynamics or route acceptance.

Artifact `nav-candidates/gfay-static-tracked-replay-0.41.61.json`, SHA
`359a0caf5257c0eb96669a7a59bad4fbba4de7e580b93601f8b49ac69183c5ef`.
Elapsed 477.44 wall/103.18 CPU seconds, no refusal or budget exhaustion.
All 39 code/data pins rechecked after completion. Plan SHA remains
`5ea1024a8196a96f07e6cb73e259bd4e55cdb47e7a982e559a2c5eb60476743b`;
static inventory SHA remains
`dc489aff256243b2a84ad3979c2222d5011bbdc2865afa78534d0d43df99dcd4`.

**VERIFIED fixtures, not live:** A new owner-run collector pairs one newly
appended manually requested `/location` with a timestamped UI capture. It skips
existing log bytes, refuses resets/transitions/process replacement, brackets
sampled focus, and refuses additional locations or stale timing during capture.
It writes an explicitly UNBOUND location record, not a navigation fix. No
current zone, alignment, character identity, command correlation or continuous
focus is inferred. It sends no input and omits the chat crop. Existing trusted
location-reader behavior is unchanged. Capture now includes monotonic start/end
times, validates character/server identifiers and avoids a repeated-focus-call
race. Forty-eight focused fixture/geometry tests and fourteen local startup/
guard smoke checks pass. No actual capture was performed.

**Next:** stage the collector for the owner, then add bounded whole-footprint
BSP hazard checks and integrate independently observed live scene/position/
speed with the checked sender. Existing BSP centerline evidence cannot prove
a filled walking volume. G0 remains owner-confirmed; no repeat is requested.
Assist 0.39.6/G0 candidate 0.39.7 remain separate and unchanged. F11/F12 stay
disabled; no live 1–20 route, automated XP or hands-off level 50 is accepted.

## Private 0.41.60 staging — 2026-11-14 03:21 UTC

**VERIFIED:** Commit `d8f8f41`, archive SHA
`6e04dd724a7d79f142e4da55a4c386bfd659072081dafbbf5c5d115eb7c0f948`, matched at Alienware
`~/.local/share/eql-automation/owner-tools/0.41.60/source`. Nine lightweight
startup/guard checks and eight synthetic static-adapter tests passed remotely.
They covered seed reuse/refusal, exact reference-gap repair, wrong-height
refusal, cell-bound static occupancy, a blocking static wall and three CLI
startup paths. No client assets, input devices or game were opened. Remote
`../smoke.json` records the scope. Assist 0.39.6 and G0 candidate 0.39.7 remain
unchanged; F11 is disabled. The separate private staging record is
`releases/eql-automation-0.41.60-staging.json` under the data store.

## Completed conditional GFay terrain follower — 2026-11-14 03:20 UTC

**VERIFIED source 0.41.60:** The eastern/southern repaired plan completes all
155 segments in 2,191 idealized steps, with 2,191 passing motion-footprint checks
and 2,192 committed terrain-floor cells including the seed. It arrives without
a geometry refusal or exhausted budget. Elapsed time 356.25 seconds, CPU 86.31
seconds; the difference is consistent with measured shared-host scheduling.
The entire 2,138-trial prefix matches the earlier time-limited report exactly.
Only the wall allowance changed; no movement or geometric limit was relaxed.

The three missing-reference tile-gap trials pass their complete corrected
checks. Maximum measured source/baked difference remains 1.174967554 under
the explicit 2.0 diagnostic sensitivity; default 0.6 is unchanged. Body height 8,
speed, latency and drift remain hypotheses. This is a terrain-only simulated
follower result, not full collision, trusted live calibration or route acceptance.

Artifact `gfay-east-tracked-long-replay-0.41.60.json`, SHA
`87457cb38f7474c54afccdcda186266153d2f10179cc50f39dc3c3d35669da84`;
last floor proof `dbc2128db3c931665dc52ce44183258a42cbe7e6b19becc475e8c0f10a9ca4f8`.
All 29 input pins rechecked after completion; source baseline `1e961fc`.
The original complete static scan is explicitly NOT claimed for this repaired
plan: only its unchanged first-leg seed is reused, with every actual footprint
checked again. The final plan SHA is
`5ea1024a8196a96f07e6cb73e259bd4e55cdb47e7a982e559a2c5eb60476743b`.

**VERIFIED static guard preparation:** A separate guard binds static occupancy
to the exact accepted terrain-cell digest, retaining the original selected
floor IDs. Static faces may obstruct that floor but cannot become a new floor.
Changed footprints/terrain, identity collisions, failed terrain and query-budget
refusals remain stopped; no query is truncated. Five focused checks pass.
Together with 65 floor/precision/tile checks, 10 seed checks and 8 static-adapter
checks, 88 focused checks passed. Six pure startup checks and all three source
CLI help commands also pass locally without input or client assets.

**Next:** Connect the parity-checked static inventory and guard to each replay
trial, then evaluate complete occupancy and hazards. Fresh scene, independent
position/height/speed observations and checked sender integration still gate
real-client acceptance. No real 1–20 route, automated level gain, fresh-character
run or level 50 completion is claimed. G0 remains passed; assist 0.39.6 and
G0 candidate 0.39.7 are unchanged. The owner alone drives his live session.

## Eastern GFay crossings and complete replay attempt — 2026-11-14 03:16 UTC

**OBSERVED source attribution:** The remaining late slope cells share detail
157769 in polygon 18957, baked grade 1.53314345, over coplanar original source
1577/16 and 1577/17 at grade 0.28129395. Both late crossings can move toward
their southeast endpoint, away from the narrow steep baked wedge.

**VERIFIED local candidate:** Move portals 150 and 151 to fraction 0.40. Package
crossings become (52.683950806,1814.747509766) and
(53.403952026,1815.467480469). All 12 radius 1.2 ground-tube cells on affected
segments 150–152 pass; maximum grade 0.427195481. Both turn checks, three strip
checks and 376 whole-centerline BSP spans pass. Plan
`gfay-east-tile-portal-plan-0.41.60.json`, SHA
`5ea1024a8196a96f07e6cb73e259bd4e55cdb47e7a982e559a2c5eb60476743b`.
Repair report SHA `43aa14eac101be1ad4d4ca6b1bb10cdc5bf29f7715380addc09a57de8a4f82f7`.

**VERIFIED first replay:** With exact missing-reference gap attribution, the
replay reached segment 149/step 2,138 without another geometry refusal, then
exhausted its 300-second wall budget. This is a passing prefix, not a completed
route. Three reference-gap trials passed their complete corrected checks.
Artifact `gfay-east-tracked-replay-0.41.60.json`, SHA
`43ffacf88272a05c5e9c1e0bc39744df882df0c642f4576631490df182ac64a5`.
The binding correctly reports 125 unchanged initial segments and explicitly
marks the old complete static scan as inapplicable to this changed plan.

The same route was rerun with an explicit 600-second offline wall budget;
no geometry, speed or controller tolerance is increased. Default budget 35
remains unchanged. The report now records CPU seconds separately so shared
host scheduling delays can be distinguished from geometry work. No live
movement or 1–20 acceptance follows from these copied-data checks.

## Static-instance source parity and reference-gap attribution — 2026-11-14 03:10 UTC

**VERIFIED copied static inventory:** The new all-height query transforms
2,799 placements into 109,932 source faces, with unique per-instance identities
above the terrain fragment range. It preserves all flags/materials, vertical
faces and all heights. Thirty parked placements are explicitly recorded using
the retained baker's Z<=-31768 rule. The actual 79 placed model meshes come from
84 exact static actor definitions; no unmatched or partially parsed actor is
silently accepted. Only the observed 40-byte single-component actor layout is
supported, preventing multi-component actors from losing geometry unnoticed.

The adapter passes relative vertices and center separately into the pinned
helper `model` transform and preserves final float32 coordinates. Its 57,751
nondegenerate flag-zero triangles match the retained baker's complete static
triangle multiset **exactly**, with zero missing/extra triangles. For parity
only, 30 zero-area solid faces are omitted, matching the baker; they remain in
the source query. Another 52,151 flag 16 faces also remain in source queries.
The retained whole scene has 130,423 triangles (72,672 terrain +57,751 static),
reproducing the original bake input count. Eight focused adapter checks pass.

Artifact `gfay-static-source-inventory-0.41.60.json`, SHA
`2fe5feee285285c36245d5fe96d4fc9e2e63b7bf25f94aceee71007c9014037a`;
inventory digest `dc489aff256243b2a84ad3979c2222d5011bbdc2865afa78534d0d43df99dcd4`.
All 14 code/data pins rechecked. This adapter is not yet connected to follower
occupancy and does not prove live collision behavior or include dynamics.

**VERIFIED replay diagnosis:** The southern plan passed the former slope and
reached segment 128/step 1,857, then stopped at `reference_ground_not_supported`.
Its reference Y 1343.38757324221 is about 2.25e-11 above the lower tile edge,
inside the exact modeled gap. That origin-support check occurs before the
usual uncovered-area failure, so the prior precision path never ran. Artifact
`gfay-south-tracked-replay-0.41.60.json`, SHA
`7457783698c734b8ac01d137106520afbd523725490470662646ced7cd88dedf`;
source baseline `055a646`, elapsed 198.55 seconds.

The new retry requires the reference strictly inside a positive exact tile gap
and portal span, with no original in-window triangle supplying XY support. It
then runs the same corrected coverage, reference-height, grade, area, component
and source checks. A wrong Z, existing XY support or missing exact-tile evidence
still refuses. Attribution is retained per trial; this is not a general retry
for missing ground. 65 focused floor/precision/tile checks and 10 seed checks
pass. Static and reference-gap code baseline is `041ae28`. No game input,
mesh edits, live route acceptance or new owner test occurred.

## Southern GFay crossings avoid the segment 125 slope — 2026-11-14 03:03 UTC

**OBSERVED copied source attribution:** Bad detail 166882 belongs to the required
next polygon 20488. Segment 125's centerline misses it, but the uncertainty
footprint overlaps its thin tip; the following segment 126 centerline also
crosses that tip. Pulse shortening alone cannot remove the planned crossing.
The original terrain covering the failure footprint is fragment 1576/face 71,
flag 0/Diffuse, grade 0.1724407411. Its height differs by about 0.346 units from
the bad baked patch, whose plane grade is 2.087641816. This is evidence of a
narrow baked-triangle slope problem, not steep underlying source terrain.

**VERIFIED local candidate:** Move portals 125 and 126 to raw endpoint fraction
0.65, giving package XY (194.043804932,1279.817620850) and
(192.483808899,1279.817620850). All 49 radius 1.2 ground-tube cells on affected
segments 125–127 pass; maximum grade 0.273627. Both turn checks, all three strip
checks and 376 full-centerline BSP spans pass. The polygon sequence is unchanged.
A raw tube run failed only the last cell's small tile gap. Explicit exact-tile
precision, backed by source terrain, repairs that cell with source/baked
maximum difference 0.501262. Default tolerances and the stored mesh are unchanged.

Raw report SHA `2ce0f381a678f112d7b8795a14fc05d73861acb57cdfa985c8398703047d6e48`.
Corrected report `gfay-south-tile-portal-repair-0.41.60.json`, SHA
`7daa50b71fd15e0d8ffa37b73ed94d243f224a86d9e0a552238768e230760a5a`.
Plan `gfay-south-tile-portal-plan-0.41.60.json`, SHA
`898cf06b03674656dd5af62a63f8b57329a799ad75ea1378eb1a5d3a4cdca5ac`.
All 25 repair pins rechecked; code baseline `055a646`. Full replay is pending.

The replay now explicitly binds the original conditional floor seed only when
the candidate's first leg, zone, mesh and width are identical. A changed suffix
does not inherit the old complete static-scan claim; every actual footprint
still runs source continuity, occupancy and ground checks. Seventeen focused
seed/trial tests pass, including changed-start/mesh/zone/width refusal and
changed routes falsely claiming the same artifact identity. This remains
copied-data simulation; no live input, current calibration or F11 acceptance.

## Private 0.41.59 staging — 2026-11-14 02:59 UTC

**VERIFIED:** Commit `c783b99`, archive SHA
`7e0ec71d7dd30128f466f782692aa60621e71ab46308c4645184e09856edaa16`, matched at Alienware
`~/.local/share/eql-automation/owner-tools/0.41.59/source`. Six lightweight
remote checks passed: continuous floor beneath an overhead platform,
intersecting-wall refusal without changing prior state, exact new XP awards
and invalid-time byte preservation, level-loss reset, CLI startup and invalid
option refusal. Remote `../smoke.json` records these synthetic checks.
No copied assets, input device or client were opened. Assist 0.39.6 and
G0 candidate 0.39.7 remain unchanged; F11 is not accepted. Local staging
record: `releases/eql-automation-0.41.59-staging.json` in the private data store.

## Conditional floor-aware follower replay — 2026-11-14 02:58 UTC

**VERIFIED source 0.41.59:** Each proposed movement footprint forks the
source-floor tracker, checks all terrain heights for occupancy, then compares
the selected source floor with its baked ground support. Only accepted,
completed idealized actuation commits the fork. Rejected or shortened trials
cannot change the previous floor. The new flag requires the pinned complete
0.41.58 proof and explicit tile-precision diagnostic; defaults are unchanged.

The first run stopped at segment 87/step 1,153: support comparison included a
baked platform 74.13 units above selected grass, although ground coverage had
already excluded that height band. Its artifact is preserved as
`nav-candidates/gfay-tracked-floor-replay-0.41.59.json`, SHA
`e510acad7252cbf021eef545cb7852a261476f5dc41d4a02502cc7688e634f53`,
with source baseline commit `9ec69a8`. Actual detail triangles 202831/202835/
202837/202839/202841 span Z 74.268753–77.568756; reference Z is 4.376260.

The corrected comparison excludes only triangles whose ENTIRE vertex-Z range
lies strictly outside the explicit ground window. Crossing/boundary triangles
remain checked. This exclusion survives XY-only seam correction and does not
remove any source face from the preceding all-height occupancy check. There
is no nearest-height choice, height-limit increase or stored-mesh modification.

**VERIFIED replay:** 150.45 seconds, segment 125 of 155, step 1,820, halted on
`steep_detail_plane`, not the time budget. All 1,821 committed floor cells passed
conditional terrain occupancy. Detail face 166882 (local index 4) has grade
2.08764181598 against limit 1.0 at reference
(202.24202037,1293.73888163,-3.46258753) in package coordinates. Reducing the
hypothetical pulse to 0.02 seconds still refuses. Maximum measured source/baked
Z difference on passing trials is 1.17496755365, under the explicitly requested
2.0 sensitivity setting; default 0.6 remains unchanged. It is not a complete
regional error bound. Artifact `gfay-tracked-floor-window-replay-0.41.59.json`,
SHA `0a551dc6fa248ea7c118e2da7ece168c3150ab92f520460eb3f0aff6f8f5add0`.
All 28 artifact input pins were rechecked after completion.

**VERIFIED focused checks:** 21 floor-trial/chain checks plus 43 telemetry/offline
checks pass. The floor regressions include both continuous and precision-retry
paths under a high platform, intersecting walls, crossing height bands, source
height limits and unchanged prior state after rejection. CLI help and four
stdlib startup checks pass locally, without copied assets or a game/input device.

**Next:** repair or avoid the segment 125 baked slope using copied source
evidence. Add a separate static-placement occupancy query, preserving terrain
floor identity: use the pinned helper's center-before `model` transform and
unique instance IDs; do not mix in the different Lantern transform. The full
live gate remains fresh scene/position/speed observations, full collision and
hazards, plus checked sender integration. G0 is passed, assist 0.39.6 and
G0 candidate 0.39.7 are unchanged, and no 1–20 leg/F11 or automated XP is accepted.

## Gross client-reported XP gain reader — source 0.41.59

**VERIFIED:** 43 focused telemetry/offline checks pass. The source reader now
counts the actual `You gain experience! (<decimal>%)` award format with exact
integer accumulation. Bonus/penalty variants are supported; chat, nonfinite,
negative, trailing-text and overprecision inputs do not count. The separate
status field is gross percentage points per hour since this observed level/log
window began. It does not infer raw XP, current XP fraction or net progress.
Idle polls advance elapsed time; each received batch shares its receipt time
rather than inventing individual event timestamps. Historical bytes are skipped.

Known level/zone/camp changes, death, raw-XP loss, log replacement/truncation,
missing files and clock regression discard the gross-rate window. Invalid
poll times are rejected before consuming bytes; four regression cases confirm
fresh awards remain readable afterwards. The reader does not drive the client
or change the separate owner assist preview. No current owner XP rate is claimed.

**OBSERVED client format:** Read-only `eqstr_us.txt`, SHA
`0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`,
contains award templates 138/14541/14542 and level-loss templates 442/443.
Template 16001 describes per-class levels and a selected-loadout-dependent
character level after 10. Thus an unreported loadout change can leave the
reader's last observed level stale; a fresh UI/direct level observation must
reset the window. This gross award metric is not yet connected to camp ranking
or the owner helper UI and is not a trusted substitute for those observations.

## Private 0.41.58 staging — 2026-11-14 02:45 UTC

**VERIFIED:** Commit `c042a8d`, archive SHA
`f82f22ac87ba20c66520ba43e2534e264029019d76639cc5499b52a093081548`,
matched at Alienware `~/.local/share/eql-automation/owner-tools/0.41.58/source`.
Six lightweight remote checks passed: same-floor travel beneath an overhead
surface, exact-edge continuation with linked proof, shared-edge source sample,
wall refusal with latched stop, CLI startup and invalid-body refusal. Remote
`../smoke.json` records them. No input device or game was opened. Assist0.39.6,
G0candidate0.39.7 and the owner's install remain unchanged. No F11 acceptance.

## Complete conditional GFay source-floor chain — 2026-11-14 02:44 UTC

**VERIFIED source 0.41.58:** The ordered source-floor tracker carries exact
source identity through overlapping full-width route cells. New triangles
must join through exact positive-length 3D edges with opposite XY interiors;
vertex-only links, branches, changed identities and unsupported materials
refuse. Every cell must have an exact floor partition and pass all-height
occupancy. The selected floors must agree as exact affine planes throughout
the entire overlap with the prior cell. Refusal latches the tracker; it cannot
reseed itself. `floor_at` is confined to the accepted cell, preserves the raw
WLD/package XY conversion and requires exact same-height agreement on shared
edges. It never chooses a nearest height. This is an offline source model,
not a trusted live geometry producer or a game input permit.

The seed is fragment698/face65 from the unambiguous first cell of the pinned
0.41.57 source profile. Its hash pins the explicit copied-data hypothesis;
it does not prove the character currently occupies that surface. The body
height is an explicit hypothetical 8 units. Source inventory includes every
local terrain-WLD face at all heights; placed objects/dynamics are still
absent. Both limitations remain explicit in every accepted cell/report.

**VERIFIED complete scan:** All 2,399 cells pass the conditional source-floor
chain in 141.55 seconds: 266 distinct selected source faces, 268 edge-join
events and 1,806 overhead classification events. All prior 204 failed profile
cells have a valid terrain-source chain under this hypothesis; their separate
baked-ground failures are not thereby repaired or accepted. Cell87/49 retains
source1208/9, agreeing with the earlier local diagnostic. No partial-edge
matching or T-junction relaxation was needed. The ordered chain has a hashed
link per cell and samples its source plane at each cell reference.

Artifact `~/.local/share/eql-automation/nav-candidates/gfay-source-floor-chain-fast-0.41.58.json`,
SHA `06c0a1d0818826ca0913e94a05b26912f9be05b994fa328230857b42dd04a497`.
Its source implementation is preserved in commit `01a253d`; all 19 pinned
inputs were rechecked after completion. The earlier exact implementation in
`7cda362` reached 1,147 cells before its 240-second budget, with no geometric
refusal: artifact `gfay-source-floor-chain-0.41.58.json`, SHA
`7cc91bde204f8f8afd6ce3f820af46a16c032f01c1f67e112f9cd69d83d0441f`.
That prefix was not mistaken for a complete chain. The completed run computes
the same exact intersections more cheaply: clip the footprint by source
triangles, use exact separating axes for overlap, and avoid comparing equal
planes or constructing intersections outside common source patches.

**VERIFIED focused checks:** 27 source-chain/occupancy tests passed, including
edge/point-only contact, a tiny positive overlap, crossed convex strips,
identity changes, disconnected cells, three-face branches, unsupported floor
material, low platforms, vertical walls, floor gaps, same-edge point samples
and failure latching. The CLI starts without reading data on `--help`.
No game input/device or client launch occurred.

**Next:** Integrate this pinned conditional source selection into offline
follower replay and measure source/baked differences without dropping other
occupancy faces. Recheck the remaining baked slope refusals. Extend collision
queries with correctly transformed, uniquely identified static placements.
The log also supplies explicit XP-gain percentages for a future gross gain
rate reader. Fresh UI/position/speed observations and sender integration still
gate real route acceptance. G0 remains passed; no repeat is requested. Assist
0.39.6/G0candidate0.39.7 are unchanged, F11 stays disabled, no real level gain
is claimed and the full 1–50 goal remains incomplete.

## Read-only owner progress and static-object coverage — 2026-11-14 02:42 UTC

**VERIFIED read-only log snapshot:** The exact owner file
`<game root>/Logs/eqlog_Legira_freeport.txt` was stable at 1,896,925 bytes,
SHA `974341d7328c77235ca1dc06c0508d3b7d980893f3b95826843970881af90375`.
Its mtime is 2026-11-13 22:10:46 UTC; the last written log timestamp is
Nov13 16:10:46 (log timezone not independently verified). The latest logged
level gain is level7 on Oct18, and latest zone entry is Greater Faydark on
Nov13 15:17:07. Six historical deaths were counted, latest Oct20. These are
historical events, not a current run's level, death total or camp.

The actual log contains `You gain experience! (<decimal>%)`: 174 matching
historical events, most recent Nov13 09:27:56 reporting 2.574%. There are no
such events in the final hour of that stale log. Current XP and XP/hour remain
unknown. This format can support a future explicitly labelled gross logged
percentage-gain rate; it must not be treated as raw XP, current XP fraction,
net XP after losses, or a rate across different levels. The initial narrow
pattern omitted percentage suffixes and found zero; that count is superseded
by `owner-traces/owner-progress-20261114T024123Z.json`, SHA
`dd8ee20410c984585e8e83bb1d19d9733acbc6b3f6ae3e63e298ace3b25cd43d`.
No raw chat was copied or printed, no screenshot was attempted, and no game
input, process focus or install modification occurred.

**OBSERVED read-only static-source investigation:** The retained GFay bake
manifest pins both terrain and object archives and records 130,423 triangles.
Terrain has 72,694 flag-zero triangles. Copied objects metadata has 2,829
placements: 30 parked sentinels and 2,799 eligible placements, with 84 exact
static model links and no unmatched actors. Original bake therefore included
eligible placed-object geometry, while current source-floor checks cover
terrain WLD only. Helper `eqnav.zonegeom.place_vertices(..., convention='model')`
uses center-before rotation/-Y tilt and matches the retained bake path; the
project's Lantern-style `projected_vertex` uses a different transform. Do not
mix them without reconciliation. Static collision faces need identity including
object archive/member, placement fragment, model fragment and face index;
`SourceFace(fragment,face)` alone collides between repeated instances.

Retained member hashes: `objects.wld`
`b15dbe0df01eb2276e70a783ae067f65f5abb4ec18649481f6c1d867c89913e6`;
`gfaydark_obj.wld`
`4e0eef9ccb436c8abc2859aeed6d8e333918f3b814a92bcb2bb5ad1248830735`.
The existing `read_object_locations`, `combine_model_links`, `read_meshes`
and `mesh_face_materials` APIs provide provenance for a future local placed-
face query. No new object geometry scan, bake or client test was run here.

## Private 0.41.57 staging — 2026-11-14 02:31 UTC

**VERIFIED private staging:** Source 0.41.57, commit `c6ac9ee`, is available
at Alienware `~/.local/share/eql-automation/owner-tools/0.41.57/source`.
Archive SHA `d16bce7389f4694b557e7a0b273ff33c017e2e34e0175e6312a36a35b342e444`
matched remotely. Three pure geometry smokes, three CLI startups and an
invalid-option refusal passed; `../smoke.json` records all seven checks.
No input device or game was opened. Existing owner-assist packages and game
install remain unchanged. This source release does not enable F11.

## Exact tile model and conditional source-floor occupancy — 2026-11-14 02:30 UTC

**VERIFIED implementation:** Source 0.41.57 adds an explicit `--tile-rounding`
diagnostic derived from the pinned manifest's float32 origin, cell size,
radius, border and tile dimensions. Only exact predicted adjacent sides can
match. Unique reciprocal links, unchanged other-axis/Z endpoints, dry common
components, whole polygon interiors on the predicted sides, and two distinct
ring boundary contacts are required. The absolute correction remains capped
at 0.0005; source and mesh files remain unchanged. Default one-ULP/gap-only
behavior and source-height limit 0.6 remain unchanged. The native baker
wrapper source was not found; agreement with its output is an empirical
model, not native-code verification or client collision acceptance.

**VERIFIED copied-data evidence:** All 2,771 examined mismatched reciprocal
ground links match the inferred tile model. The segment-65 overlap now passes
the local source-supported correction: six boundary vertices move in XY,
with no Z changes, and overlap falls from 0.0001142676 to zero. Its maximum
source/baked difference is 0.8682792. The model explains a 40-ULP pair near
coordinate -39 and a two-ULP pair of width 0.00048828125 near coordinate 2572;
no arbitrary ULP-count expansion is used. Artifact:
`~/.local/share/eql-automation/nav-candidates/gfay-tile-rounding-model-0.41.57.json`,
SHA `1564253a51f0037e563f64b862d0f1ccd2ceaea6cc1bd05ca5cca85904955792`.
This diagnostic and the occupancy artifact below pin baseline commit
`b4b2c5e`. That earlier seam serialization retained a default
`maximum_ulp_steps=1` field even for tile classification; it was not the
classifier's limit. Current source explicitly records `exact_tile_side`,
actual ULP steps and no ULP cap, and adds the ring-contact check.

**VERIFIED replay after those refinements:** The 155-segment repaired GFay
route reaches segment 87, step 1,151, in the explicit tile/overlap diagnostic
with source-height limit 2.0. It stops on `Copied source floor missing or
layered at exact XY`, rather than continuing under an assumed floor. The
last successful stopped source is fragment1208/face9. This used synthetic
motion/alignment and sends no input. Artifact
`gfay-tile-rounding-replay-0.41.57.json`, SHA
`c6234c0df3c94b906e150a9c0940857328b325364f24f6eade8b9b12db6486ff`.

**VERIFIED separate occupancy diagnostic:** Three cells (87/49, 87/50, 89/0)
conditionally pass explicit body-height hypotheses 6 and 8. All supplied
terrain faces are retained, including vertical walls, masked materials and
opposite winding. Nonselected faces are classified against a selected floor
partition using XYZ clipping; surfaces touching or crossing the body band
refuse. Exact rational partition coverage prevents even a 2e-8-wide floor
gap from hiding an obstacle. The grass under the first two cells is the
same source face as earlier locally passing cell87/48; the third selection
is an explicit hypothesis. This does not yet prove a chain from G0, actual
body size, placed-object inventory, dynamics or a full-route bound. Existing
all-layer source support and input rules are unchanged. Artifact
`gfay-selected-floor-occupancy-0.41.57.json`, SHA
`31494c656ee0560a09f3333a3f4a60ec7eff2b1df0741fb345cb8f1c87b972c7`.

**VERIFIED focused checks:** 67 analytic tests passed across tile rounding,
portal precision and selected-floor occupancy, including wrong tile identity,
unsupported reciprocity, vertical walls, body-band contact and the tiny-gap
regression. No game data is committed. HOWTO now puts the current owner
assist launch near the top and retains older release evidence here.

**VERIFIED complete corridor profile with tile classification:** All 2,399
radius-1.2 cells were checked in 112.63 seconds; 2,195 pass and 204 refuse,
compared with 2,155/244 before the tile model. Every precision retry now has
a supported seam classification; eleven still fail subsequent source-layer
checks. Counting those nested reasons, remaining refusals are 177 source-layer
ambiguities/overlaps, 16 source flag/material, one missing/over-budget source,
three source slopes and seven baked slopes. The first failed cell is 87/49.
The largest difference on passing cells is 1.1231339241; a complete-region
maximum remains unset. Artifact `gfay-tile-source-profile-0.41.57.json`, SHA
`e5dd717c1bd93770d3ec8419dc948efe0c1ebf3f789297533520bdeae0ed4fbd`.

**Next:** Carry an explicitly identified source floor through the ordered
route cells by exact shared 3D edges, complete floor coverage and all-height
occupancy. Do not choose nearest Z. Real motion still requires fresh scene,
height/speed calibration, full body/static/dynamic checks and sender wiring.
Owner G0 visible stop is confirmed; no repeat is requested. Current level,
XP/hour, deaths and camp are unobserved beyond owner-reported Legira7 GFay.
Assist 0.39.6 and G0 candidate 0.39.7 remain unchanged; F11 is disabled.

## Private 0.41.56 staging and classified next issues — 2026-11-14 02:16 UTC

**VERIFIED staging:** Commit `4dcdd1d`, archive SHA
`59678e99e6a3467b9be7c6d83f7c21d7a7af7b8a177f7e1b53dbe2fc28e93a0c`,
matched at Alienware `~/.local/share/eql-automation/owner-tools/0.41.56/source`.
Five pure precision smokes passed (overlap, default refusal, same-polygon
refusal, explicit two-step gap, three-step refusal), along with three CLI
startup checks and an invalid-option refusal. Remote `../smoke.json` records
these results. No input device or game input was used.

**OBSERVED read-only helper investigation, not yet a retained standalone proof:**
The segment65 overlap is five float32 steps, width0.000152587890625, between
detail217422/poly27783 and detail217667/poly27806. Reciprocal links58132/58183
share X/Z endpoints but have package Y -499.8123474121094 versus -499.8125.
Source fragment681/face12 is the sole Diffuse ground over the expanded
footprint. A virtual six-vertex midpoint correction reportedly passes full
coverage and source support (max delta0.868279); root must pin a reproduction.

The pinned manifest and retained helper pipeline suggest a tighter classifier
than increasing the ULP cap. Float32 cell_size0.600000024, tile_size256 and a
five-cell border, applied to source package-Y minimum -2803.8125, reproduce
both sides at tile14/15 through independent local arithmetic. With f32 at
every operation: tile_world=f32(256*cs), cfg_bmin=f32(f32(global_min+
f32(tile_index*tile_world))-f32(5*cs)), inner_min=f32(cfg_bmin+f32(5*cs)),
inner_max=f32(cfg_bmin+f32(261*cs)). The same expression reportedly reproduces
the earlier X25/26 and Y13/14 seams. Across 35 internal boundaries per axis,
predicted errors can be 20–40 ULP near small coordinates but no more than
0.00048828125 absolute distance. This is an empirically supported inference;
the actual baker C++ source was not located in approved stores.

Retained approved provenance: `owner-assist/0.39.4/eqnav/build.py` lines133–155
records filtered source triangle bounds; `eqnav/bake.py` lines99–105 writes
float32 EQTR, lines165–175 passes bake parameters, lines183–185 stores float32
arrays. Mesh meta baker SHA
`072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44`
matches retained private `nav-candidates/trainer-sensitivity-20261113T1557Z/eqlnav_bake`.
WLD→package swaps XY (`eqnav/zonegeom.py` line452); package→Recast is (Y,Z,X)
(`eqnav/bake.py` line49). The seam matches package-Y/Recast-X arithmetic,
so this investigation does not attribute it to a frame swap. No removed old
working copy was accessed, recreated or used.

**OBSERVED source-layer classification from helpers:** Segment87 cells49–50
have continuous supporting grass fragment1208/face9, flag0/Diffuse, grade
0.21765. At cell49 the ground is Z4.26128 vs baked4.92395; it covers the entire
footprint. The additional XY layers are Fay floors at Z71.96875/73.96875 and
planks at76.8125/77.53125 (paired upward/downward surfaces), more than67.4
above the grass within the footprint. Segment89/cell0 has grass1174/face1,
grade0.21132, Z-1.17372 vs baked-0.58124, covering the full footprint. Its
material refusals come from elevated TransparentMasked BRAILING1 faces of
fragment1175 (IDs82/111/115/118), grade5.64–5.66, Z74.20–76.28, more than75
above the ground. These are real distinct source layers, not evidence of
bad grass material. They need an explicit vertical occupancy/headroom proof
or a route change; nearest-height filtering is not accepted. The complete
region bound remains unset. These helper findings are leads for pinned root
diagnostics, not live acceptance or permission to move.

## Source-supported overlaps, explicit two-ULP cases and full corridor profile — 2026-11-14 02:15 UTC

**VERIFIED implementation:** Source 0.41.56 keeps the existing precision defaults
and adds explicit offline overlap attribution and maximum-two-ULP diagnostics.
Every meaningful original overlap must be between uniquely linked reciprocal
polygons, within their exact coordinate strip and span, with triangle interiors
on opposite portal sides and ground heights agreeing within 0.01. Original
steep, forbidden or partial-height-window faces cannot be hidden. Both original
and corrected full ground checks run; source coverage runs over the complete
expanded footprint with all source heights. Same-polygon/extra overlaps,
layers, wider gaps, altered endpoints and other failure kinds refuse.

`--maximum-portal-ulp-steps 2` permits exactly one or two representable float32
steps with unchanged other-axis and Z endpoints, absolute difference at most
0.001. `--precision-overlaps` separately opts into the attributed overlap path.
Both require `--precision-portals`; defaults remain one-ULP/gap-only and the
0.6 source-height diagnostic limit. Forty-three analytic precision tests and
seven source-point/footprint lookup tests pass. The latter include outer-margin
and all-height enumeration without candidate truncation. CLI startup and
invalid combinations refuse as expected. No input device is opened.

**VERIFIED pinned segment-38 overlap:** Reproduced against the copied mesh
and source. Detail232871/poly29697 and detail224903/poly28757 overlap by
0.00010231455221615393 square units. Their maximum height difference across
the sliver is 0.00002369795806. Seven boundary vertices move ephemerally to
the reciprocal midpoint, leaving Z unchanged. Corrected overlap is zero and
full source support passes (max source/baked delta0.3553916111). The default
gap-only control refuses. Private artifact
`~/.local/share/eql-automation/nav-candidates/gfay-source-supported-overlap-0.41.56.json`,
SHA `f1f2ecf4f26c59bba885e8f13f9f55c307c6488a57114cb0f4db97ba3eb15ff2`.
Its exact implementation/pins are retained in local commit `21b4f64`.

The one-ULP overlap replay reaches segment52/step659, then refuses a gap.
Artifact `gfay-overlap-replay-0.41.56.json`, SHA
`91d595ae5307544b24e4265ce8d1636a62f8c988fa913557beaf383e7c753a6a`.

**VERIFIED pinned segment-52 gap:** The two reciprocal Y coordinates are
-653.4124755859375 and -653.412353515625: exactly two float32 steps, with
matching endpoint X/Z and a representable midpoint -653.4124145507812.
Six local boundary vertices shift to that midpoint. The original uncovered
area0.000084311394038 becomes ~1.0e-14 after correction; source support passes
with max source/baked delta0.7006225861. The one-ULP control refuses. Artifact
`gfay-source-supported-two-ulp-gap-0.41.56.json`, SHA
`526a6dfb1682dff4982b05a0f62b15a564fcca696fa9488562cecb3c8adf58b1`.

**VERIFIED replay with explicit two-ULP/overlap and 2.0 height sensitivities:**
28 successful local retries; segment65/step773 then refuses another overlap
with no supported seam classification. Artifact `gfay-two-ulp-replay-0.41.56.json`,
SHA `65b7560c62b41ae6af69dc9d95138ff275fc8e7ce9acd35e4300a6ed800f29f7`.
Defaults are unchanged and no stored source/mesh is modified.
The two-ULP proof/replay and full profile implementations are retained in
local commit `167bcfe`; subsequent wording-only edits clarify their scope.

**VERIFIED complete corridor scan:** `audit_route_source_profile.py` partitions
the repaired route's 4654.7114 XY units into 2,399 convex cells, each covering
at most two units of travel with the full radius1.2 corridor. It checks complete
local baked footprints and all source XY candidates at all heights. A coarse
measurement envelope comes from all source/detail vertex Z extrema, rather
than choosing another arbitrary height acceptance cap. Tight reported maxima
come from source/baked plane differences at all clipped intersection vertices.
This uses float64 clipping, not outward-rounded exact certification, and cannot
issue a live height calibration or input permit.

All 2,399 cells were checked in168.38seconds; 2,155 pass and244 refuse. Reasons:
45 unsupported portal precision;154 source reference missing/layered;
18 overlapping source ground;16 source flag/material;one source missing/over
budget;three source slopes;seven baked slopes. The first refusal is segment65,
partition36. Maximum measured difference on passing cells is1.1231339241 at
segment143/partition13 (source fragment1577 faces13/35). The whole-region value
is null because some cells failed. These classifications do not imply every
refusal is a physical obstacle; source layers need supporting-floor/overhead
classification and slopes/materials need source-aware detours. Private artifact
`gfay-source-profile-0.41.56.json`, SHA
`be99450b900f29f736185a21204a4889af78cefe5abf7cb7b73c63a5e68a3be8`.

Next: explain portal error from retained bake provenance rather than increasing
ULP counts with coordinate magnitude, classify the source layers, and use the
complete failure profile for route repairs. No accepted 1–20 route, real G2/F11
movement or XP gain follows. Assist0.39.6/G0candidate0.39.7 are unchanged.

## Private 0.41.55 staging — 2026-11-14 02:03 UTC

**VERIFIED:** Source commit `2d94ede`, archive SHA
`9955a1493c1413317d370fb97ab618f7d60322c37290dc710b7643f4140460e7`,
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.55/source`.
The remote archive matched its SHA; extraction allowed only regular files and
directories under `source/`. Eight pure checks passed, including G2 package
frame/snap, source-height separation, rejection of a self-reported large bound,
and malformed integer time. Replay CLI startup passed. Evidence is
`~/.local/share/eql-automation/owner-tools/0.41.55/smoke.json` on Alienware.
No device or game input occurred; runnable assist/G0 packages are unchanged.

**OBSERVED helper diagnostic for next work:** A read-only current-store check
reported that the segment-38 overlap is between detail 224903/poly28757 and
232871/poly29697. Their reciprocal link Xs are 1300.4439697265625 and
1300.44384765625, exactly one float32 ULP apart, with shared Y range
[-1114.21240234375,-960.6124267578125], area63/component2. Midpoint X is
1300.4439086914062. Source fragment657/face4, flag0/Diffuse, was the sole
projected source covering the expanded footprint. A virtual midpoint shift
reportedly removed the overlap and passed source coverage with max Z delta
0.355391611. This investigation has no retained standalone proof artifact yet;
root must reproduce and pin it before extending the precision retry. It is
not route acceptance and does not justify raising overlap tolerance.

## Separate ground observation binding — 2026-11-14 02:03 UTC

**VERIFIED implementation:** Source 0.41.55 replaces the ambiguous aligned
ground point with independent `SourceFloorObservation`, `MeshProjection` and
`HeightCalibration`. Both observations bind the exact same raw fix object.
Raw/source XY agree exactly and mesh XY is the helper-frame swap; source and
mesh Z remain distinct. The separately supplied expected calibration pins the
source archive/WLD, zone identity, log epoch/generation, newer log sequence
and monotonic lifetime. Raw minus source Z must match calibrated character
height. Motion/frame calibration remains a separate record.

`GroundGeometryEvidence` is supplied independently of observations and pins
the source/mesh identities, same-floor proof hash, regional height-difference
bound and reciprocal portal pairs. A self-reported huge bound or substituted
proof cannot pass. These records are evidence containers; the trusted live
verifier that computes their evidence still does not exist. Tests/replay use
explicitly synthetic verification flags, not reusable live permissions.

G2 uses the baked package point directly, requires the selected start polygon,
and preserves the 0.0005 snap test. The retained-class follower preserves
0.25 endpoint XY/Z tolerances and adds independent stationary checks for raw
Z and source Z. It accepts support from only the selected polygon or the
immediate selected neighbor within the shared endpoint disk, with independent
reciprocal adjacency evidence. Component changes, stale/session-switched fixes
and source height inconsistencies refuse. No production input path calls it.

**VERIFIED focused checks:** 34 pure binding/G2/radial tests pass; 24 retained
steering/follower and real watchdog-child pipe tests pass; five analytic source
lookup tests pass. They cover raw jumps hidden by a fixed mesh height, source
layers, wrong XY/frame, calibration identity/expiry, independent proof/limit,
neighbor support away from endpoints, changed components, unchanged endpoint
Z tolerance and assist/cancel refusal. The pipe tests open no input device. An oversized integer time is also
refused without raising an overflow exception.

**VERIFIED copied-data replay:** The replay implementation and pinned sources
are retained in local commit `d8587fc`; the later malformed-integer guard does
not change normal float calculations. `PortalPrecisionView.source_floor_at()` now
queries all copied source layers at every stopped XY, allowing shared source
edges only at the same height and refusing missing/unsupported/layered ground.
The raw character Z is then *synthetically* source Z + 2.564, not baked Z.
Reciprocal selected-route adjacency is read from the pinned copied mesh. The
same-floor fixture hash is explicitly simulation-only; point samples and a
chosen bound do not prove an entire regional source/bake relationship.

- Default 0.6 bound: segment 5, step 42, refuses bake/source delta 0.75965824
  at source fragment 698 face 20. Artifact
  `~/.local/share/eql-automation/nav-candidates/gfay-separated-ground-replay-0.41.55.json`,
  SHA `4f86ffad6395f22532b1dd90ff0874fe3363b3c6e9257e81bd5be17d9fd83099`.
- Separate 0.9 sensitivity: segment 5, step 63, refuses delta 0.92576014 at
  source fragment 698 face 21. Artifact `gfay-separated-ground-z09-replay-0.41.55.json`,
  SHA `6dcdc4c3867b129e7fb12867748968a4a98709da04a43be7acf86430edbb8c7a`.
- Separate 2.0 sensitivity: segment 38, step 458, refuses
  `overlapping_ground_faces`. Across 459 observations, baked minus source Z
  ranges 0.12198656–0.92576014. Artifact `gfay-separated-ground-z2-replay-0.41.55.json`,
  SHA `12ebd718d386ed8f7a8df7fdf43054a047b162a74ba73408eb50549e4ccd99a8`.

Default 0.6 remains unchanged. These new checks expose a limitation masked by
the previous replay, which generated raw Z directly from baked ground. No
entire route, fresh live calibration, G2/F11 movement or XP gain is accepted.
The next unblocked work is a source-supported regional bound and the exact
reciprocal overlap diagnostic. Assist 0.39.6/G0 candidate 0.39.7 are unchanged.

## Private 0.41.54 staging — 2026-11-14 01:51 UTC

**VERIFIED:** Commit `96f472c` archive SHA
`018a488f50db896a9f1fe93587f7f91d20a1d208ebd2f0f022b2ba409b3fcf65`
matched at Alienware `~/.local/share/eql-automation/owner-tools/0.41.54/source`.
A synthetic two-source-triangle precision smoke passed; adding a competing
floor refused. CLI startup and mutually incompatible precision flags were
checked (`../smoke.json`). These remote checks used no input devices/client
data; the full copied-data replays ran on the devbox. No game input occurred.

## Source-supported tile precision and separate ground heights — 2026-11-14 01:50 UTC

**VERIFIED implementation:** `portal_precision.py` recognizes only unique,
reciprocal, same-component area-63 links with constant X or Y, identical other
coordinate/Z endpoints and exactly adjacent float32 coordinates (gap no more
than 0.001 unit). Duplicate/nonreciprocal links, other endpoint differences,
forbidden areas and different components cannot supply a repair. Only an
original `uncovered_ground_area` can be retried. Local vertices must lie on
the named portal span; both local boundary edges must be present. Their XY
coordinates move to a float64 midpoint without changing Z, area, component,
source arrays or the stored mesh. The complete corrected footprint must pass
the existing ground/grade/seam/overlap checks again.

`portal_precision_view.py` selects every source triangle whose XY bounds
intersect the footprint plus a 0.002-unit margin, without any height filter.
The copied-source partition must continuously cover that expanded footprint,
with flag 0/Diffuse faces, grade at most 1, no positive-area floor overlap,
no hole and continuous shared-edge height. Competing floors cannot disappear
through a height window. Affine source-versus-baked height differences are
checked at every source/detail intersection vertex, covering the whole area.
The default 0.6-unit difference limit is an explicit diagnostic choice, not
a proved bake error bound or live calibration. Twenty-six analytic tests pass,
including two-face partitions, X/Y/negative coordinate seams, actual midpoint
precision, layers away from the reference, different source height, material,
source holes/steps, portal-span limits and unchanged original arrays.
This remains a ground diagnostic; source object/headroom/BSP volume checks,
actual body dimensions, dynamic obstacles and live input acceptance are separate.

**VERIFIED copied-data replay:** 1,088 eligible reciprocal seam pairs were
found in the pinned mesh; 74,981 source terrain faces were read. The default
run passes six local retries across the first two seams, reaches segment 20,
step 239, and refuses the next seam because max source/baked delta is
0.6006898934 > 0.6. A separately requested offline sensitivity with limit 0.9
passes fifteen retries (largest observed delta 0.6984934), reaches segment 38,
step 458, and stops on `overlapping_ground_faces`. That failure is not retried.
The default limit is unchanged. Both runs use hypothetical motion and neither
completes the route, validates actual movement or enables F11.

**VERIFIED G0 comparison:** The retained owner trace and alignment artifact
were hash-checked, and copied source and baked heights recomputed independently.
Two distinct raw locations land on source fragment 698 face 65. Raw character
Z minus source Z is 2.56429032 and 2.56350270, span 0.0007876231. Raw Z minus
baked Z is 2.06549075 and 2.08488382, span 0.0193930717. Thus a constant historical
raw-to-baked correction would inherit variable bake error. The source values
corroborate earlier historical alignment; they are not fresh live calibration.

**Next interface correction:** `AlignedWldFix.ground_wld_xyz` currently
conflates physical source ground with the baked approximation. No production
G2/follower input caller exists. It should carry two explicitly bound same-XY
observations: a unique source floor with source/character-height calibration,
and selected-polygon mesh ground with mesh provenance and same-floor evidence.
The follower can keep its strict 0.25-unit mesh endpoint tolerance while
checking raw/source vertical movement independently. G2's 0.0005 mesh snap
check must also remain. Synthetic replay currently fabricates raw Z from baked
Z; regression coverage must give raw/source and baked Z independent values.
This is a pending code change, not a claim that the new binding is implemented.

Private `nav-candidates/` evidence:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `gfay-precision-replay-0.41.54-v2.json` | `fd49d84674c500e6f6da8f1e9b56887be1084ab3beca3479c2a6935f28b9b640` | Default 0.6 limit; segment 20 refusal |
| `gfay-precision-z09-replay-0.41.54.json` | `454c8218244e39e152021d7f094d9c2d606d9d7c7f187f9387fe9ca053c26852` | Separate sensitivity; segment 38 overlap refusal |
| `g0-source-mesh-height-comparison-0.41.54.json` | `cc91b3615afb605d3b9b02fa146c38a599fa7c44c1caff326bc341625978dc2b` | Two retained G0 positions, source/baked heights kept separate |

The earlier `gfay-precision-replay-0.41.54.json` is superseded by v2 after
explicit replay wall-budget/sensitivity arguments were added. No timeout is
reported as route success; the final runs completed their diagnostic refusals.


## Private 0.41.53 staging — 2026-11-14 01:41 UTC

**VERIFIED:** Commit `fb0733f` archive SHA
`efb26be50ce614ad7b0791efe44496c9e2957eaf35537e19d72256cdf173f2bb`
matched at Alienware `~/.local/share/eql-automation/owner-tools/0.41.53/source`.
CLI startup for portal repair/replay and invalid hash/portal argument refusals
passed in the remote smoke (`../smoke.json`). This source-only staging did
not open input devices, change the game prefix or operate a character.

## GFay westward portal repair — 2026-11-14 01:40 UTC

**VERIFIED source comparison:** The failed step-63 footprint is wholly inside
copied `gfaydark.wld` fragment 698 face 21, flag 0, Diffuse grass material.
Its source grade is 0.2222886, versus the baked face 248932 grade 1.3265971.
Source reference Z is 0.4118495 below the baked reference. The private source
comparison artifact records exact triangle vertices, containment and hashes;
it does not certify static objects, collision or live movement. A separate
read-only helper probe observed no placed-object triangle near the failed
footprint and normal BSP at its reference. Those observations motivated
routing around the baked face rather than flattening geometry or relaxing
slope limits.

**VERIFIED repair:** `tools/repair_fixed_route_portals.py` accepts a pinned
private plan and explicit raw-endpoint portal fractions. For the retained
GFay route, crossings after segments 5 and 6 moved to fraction 0.6, west of
the steep detail face. It recomputes each side's own detail height and keeps
the full polygon sequence. All three changed segments pass the original
strip/clearance constraints; both relocated portals pass their sampled turn
checks. Their complete radius-1.2 ground tubes are partitioned into overlapping
convex capsules, each of which is checked across its entire area. This
radius is an offline geometric constraint, not a verified body measurement.
The complete 155-segment centerline has 376 clear copied-BSP spans at the two
existing height offsets, with the positive zone-line frame control retained.
These checks do not constitute a continuous body/headroom/BSP sweep.

The tool exports only after these checks pass. A midpoint control fails the
ground tube and exports no plan. Incorrect source SHA is refused without
writing a report/plan; the replay also requires a hash with any supplied plan.
The new plan preserves historical start and unverified camp-marker semantics.
Neither this tool nor replay sends input or modifies any mesh/client data.

**VERIFIED follower replay:** The updated plan gets through the former steep
section and reaches segment 11, step 143. It stops at another precision gap:
reciprocal polygons 30749 and 31681 have X boundaries 1607.6439208984375 and
1607.64404296875. Their other portal endpoint coordinates match. The uncovered
footprint area is about 0.000097938 square units. This second gap remains
refused; the first seam's narrowly scoped experiment cannot apply to it.
Next is a bounded source-supported generalization for reciprocal one-ULP
portal discrepancies, followed by replay of the remaining route.

Private `nav-candidates/` artifacts:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `gfay-steep-source-comparison-0.41.53.json` | `3b434747a12232806f1deeab980bf7763e5bf954a0eb874a72b9b018811a5eec` | Entire failed footprint has gentle copied source terrain |
| `gfay-west-portal-repair-0.41.53.json` | `e7dae014ddea26ef4161cdf31c6581b7dda1b1ecd3cf1f770ab483bee691ae09` | Changed tubes/strips/turns and full centerline BSP pass |
| `gfay-west-portal-plan-0.41.53.json` | `9207b689d3ca462f0eb0b6d45af87deb902662c237dd33f5172ab613021e12f6` | Same 155 polygons, two portal relocations |
| `gfay-midpoint-control-repair-0.41.53.json` | `7c84738b66b82cf06863b72731a26b9a2cc47f985be948fc076f79b74a6b5952` | Refused; no exported plan |
| `gfay-west-portal-replay-0.41.53.json` | `26c21993ea75bbf0dcfd6c893adacd2f58737e42031de2bdee2d94041e7f3113` | Reaches segment 11 then refuses the next precision gap |


## Private 0.41.52 staging — 2026-11-14 01:33 UTC

**VERIFIED:** Commit `96f9576` archive SHA
`f356e21c212df80339cfc400ebf114c7ed362abb4f0917f17082ba239eed270f`
matched on Alienware at `~/.local/share/eql-automation/owner-tools/0.41.52/source`.
Four focused diagnostic tests, two CLI startup checks and missing-ground-option
refusal passed remotely; `../smoke.json` records them. No game input/device
access occurred. The ordinary unpatched ground replay still stops at segment
3, step 18, as expected (control SHA
`158919e75adda325e472f008509d3a14f283240fd47606010921054286506ebf`).
The diagnostic correction is explicitly opt-in and does not enable F11.

## Source-supported GFay seam diagnostic — 2026-11-14 01:32 UTC

**VERIFIED:** `tools/audit_gfay_source_seam.py` reads pinned copied
`client-data/retail-full/assets/gfaydark.s3d`, SHA
`ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f`,
using the existing archive/WLD/mesh/material parsers. WLD SHA is
`3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138`.
All 74,981 faces in 1,597 terrain meshes were checked against the failed
step-18 footprint after helper XY→raw WLD YX conversion. Exactly one source
face overlaps: fragment 698, face 66, flag 0, Diffuse `GFAYDARK_SPATH_MDF`.
Every vertex is strictly inside that convex source triangle (minimum
barycentric 0.22415), so its full 3.47416-square-unit footprint has continuous
source terrain support. Source plane grade is 0.052416 (about 3 degrees).
The baked reference Z is +0.3712978 above the source plane. This is source
terrain evidence, not collision, headroom, dynamic or client acceptance.

**VERIFIED:** The reciprocal portal edges differ by exactly one float32 ULP,
0.0001220703125. The local diagnostic moves only those XY edge coordinates
to their midpoint (maximum shift 0.00006103515625), keeps baked Z, and rechecks
all local clipped detail faces. It closes this footprint's coverage deficit.
The optional replay correction requires every new footprint to be strictly
inside the same pinned source triangle and both reciprocal polygons to be
present. Four synthetic tests cover its scope, source-frame containment,
immutability and rejection of an unrelated hole. This does not implement a
general stitch or edit any mesh/plan/client data.

**VERIFIED replay:** The local correction is used for three footprints at
steps 18–20; then the guarded replay reaches segment 6 and refuses detail
face 248932, grade 1.326597 against limit 1.0. An optional bounded diagnostic
halves rejected forward holds, rechecking every smaller footprint before
integrating any motion. It permits two more steps (61→63) but still refuses
at the hypothetical 0.02-second minimum. The source/route at this steep face
is the next investigation; neither a wider grade limit nor live input is
adopted. All speed, heading, timing and body-radius bounds remain hypothetical.

Retained GFay bake parameters include cell size 0.600000024, height
0.300000012, detail sampling distance 6, detail max error 1 and radius
1.20000005. The pinned baker is SHA
`072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44`.
**INFERRED:** voxel/detail approximation can explain a source/bake height
difference, but no retained intermediate heightfield/contour isolates this
particular +0.3713 offset. No global Z correction is justified by this probe.

Private `nav-candidates/` evidence:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `gfay-source-seam-experiment-0.41.52.json` | `0ca4fa85769c8e94e236ce69f09da180e70597006d2cb4934fc191598d1eb076` | Exact source containment and local virtual coverage |
| `gfay-local-seam-replay-0.41.52.json` | `a747a3a60bd0633ff6bb07d2130c426f9a1684a0af2a897e78caca0adc3e876d` | Segment 6, step 61, steep face refusal |
| `gfay-local-seam-shortened-replay-0.41.52.json` | `4fc154ee94226560abccf08c848cdfa214105fc35562b18e6c8834a0909ab2a0` | Segment 6, step 63, minimum hold still refuses |


## Private 0.41.51 staging — 2026-11-14

**VERIFIED:** Commit `bfc9d7e` archive SHA
`35893d8b96ac0c73e8340bdb8c2577af836910423054d72c4309fc8ce4ce7d01`
is staged at Alienware `~/.local/share/eql-automation/owner-tools/0.41.51/source`.
Remote import, complete flat-ground footprint smoke, both CLI help checks and
offline navigation demo passed. Evidence is `../smoke.json` in that release.
No input device, character or game install was touched.

## Continuous ground footprints and GFay portal discrepancy — 2026-11-14 01:25 UTC

**VERIFIED source semantics:** The existing half_width1.2 is a lateral sample
offset, not a measured character radius or proof of a filled corridor.
Ground/grade/BSP checks are discrete, and portal turn checks sample rings.
Copied-wall clearance margins do not turn those samples into continuous
terrain support. The old 155-segment idealized replay sampled endpoint
height; it did not establish complete swept ground coverage.

**VERIFIED implementation and23 focused checks:** `ground_sweep.py` forms a
circumscribed convex footprint from a nominal forward ray plus bounds for
position error, heading deviation, release drift and an explicit extra
radius. Its angular deviation bound is2*reach*sin(theta/2); a zero-reach pivot
still has a position/drift footprint. These supplied bounds are not live
calibration. Detail triangles are clipped against the entire footprint.
Their disjoint coverage, planar grade, component/area, reference height and
shared-edge heights are checked. Pair-overlap areas are accumulated and
subtracted from the coverage lower bound, so many individually tiny overlaps
cannot hide a missing patch. Tests cover an interior hole, duplicate/stacked
floors, discontinuous seams, bad slope/areas and invalid work/motion bounds.

`GroundSweepView` selects every XY-overlapping detail-face bounding box from
the copied arrays, refusing excess candidates instead of truncating them.
The check uses a bounded vertical window and explicitly does not validate
headroom, collision walls, continuous BSP hazards, dynamic obstacles, body
dimensions or real client motion. Results retain input_authorized=false and
real_client_accepted=false. Source hashes:
`ground_sweep.py` `d82e43920235eb7af0f982357d0f5eace8d997c66de41a9e2409098b116d45b6`;
`ground_sweep_view.py` `a0e6b18f40eb54ef1d8e1ee79a58af79c6dce209681c5aae2fd634d13e3b0860`.

**VERIFIED copied-data checks:** Six forward/pivot footprints at segment
starts0,26,113 pass under explicitly hypothetical speed/timing/error bounds.
The full guarded replay then stops after3 segments and18 completed simulated
steps, at its19th footprint check. Its footprint area3.4741615286 has only
3.4740508670 covered square units: deficit0.00011066155, above1e-7 tolerance.
The check is retained rather than widened to make the old replay pass.

**VERIFIED local detail/portal evidence:** Polygon31668's boundary is at
helper X1761.2440185546875; polygon32479's is at X1761.244140625. Difference:
0.0001220703125 unit. Their reciprocal graph portals have identical Y/Z
endpoints and the same X discrepancy; local detail edges show it too.
**INFERRED:** this is consistent with float quantization of a shared portal.
Original client terrain beneath the gap has not yet been checked, so this
is not evidence of a real client hole and no virtual stitching is adopted.
The next bounded source probe uses the approved copied gfaydark.s3d archive.

Private evidence under `nav-candidates/`:

| Artifact | SHA-256 | Scope |
| --- | --- | --- |
| `gfay-continuous-ground-sweeps-0.41.51-v2.json` | `f96f5e70da52251436218901816d2a02046aa8ad056e2f015e29828140fb8462` | Six conditional ground candidates; no movement permission |
| `gfay-full-ground-sweep-replay-0.41.51-v2.json` | `77b97911957c32a6d1c0ef8a3b1fec365ce61934ed0755cfc61b71f96eeb0d8a` | Full replay halts at segment3; hypothetical motion |
| `gfay-detail-seam-gap-0.41.51.json` | `d938fc7956194d8bf20450fa02699c1c2ee90da03a150acbe439f480e8b25fa6` | Exact local faces and reciprocal portal coordinates |

The earlier six-footprint artifact predates cumulative-overlap accounting;
v2 is the current result. The first full-sweep artifact used an outdated
endpoint-only assumptions label; v2 records its conditional full-ground
scope explicitly. Both earlier files remain private history.

**OBSERVED read-only Alienware capture:** The guessed original helper .venv
path was absent, so no capture ran through it. Using the documented system
python3 with fresh GUI environment then reached the capture gate and refused
without a unique focused game window/process. No focus changed, screenshot
was taken or game input sent. The owner-ready Current Zone observation is
still pending. No new live level/XP/death/camp evidence or accepted route.

## Source 0.41.50 private publication — 2026-11-14 01:17 UTC

**VERIFIED:** Source commit `4b34c6a` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.50/source`. Archive SHA-256
`2ff19d67457aa4632704ffe68c99d68c114d24f8b38241dd2e68ead9a5c9b09e`
matched locally/remotely before extraction. Remote API and CLI startup,
three selected-key pipe receipts (UP/LEFT/RIGHT code values), and the offline
navigation demo passed. Each child wrote its DOWN/UP sequence to an anonymous
pipe, not an input device. Receipt timestamps and event counts are retained
in private `smoke.json`; the simulated demo remains distinct from live travel.
No input device was opened or created, no game input sent and no character/
prefix files changed. Existing owner assist0.39.6 and G0 candidate0.39.7 are
unchanged. Next: scene/swept-motion approval and the owner-preview route
bridge, with live observations still pending. The full goal remains active.

## Timestamped watchdog receipts and post-READY selection — 2026-11-14 01:15 UTC

**VERIFIED implementation:** `timed_key_pulse_receipt` returns four child
monotonic timestamps bracketing complete DOWN/UP writes, key code, requested
duration and completion reason. These bound descriptor writes, not game
consumption. Maximum possible write exposure is UP-complete minus DOWN-start;
the old float API retains DOWN-complete to UP-complete duration semantics.
Parent acknowledgment/return time is never substituted for a key timestamp.
Watchdog source SHA-256: `3ccaf83ca95183ffe918f6fdc9a62a22e1b43c2bf9f5bacd0e0c265620fdef39`.

`selected_key_pulse_receipt` arms the child first, then invokes one selector
inside the shared stop/GO lock. That callback chooses the key, duration and
expiry from fresh proposal/scene/geometry evidence. The child validates the
selection and expiry. A None selection sends no key events. Only one key can
be selected, so forward and turning cannot be combined through this API.
The DOWN-ack wait remains unpumped while holding the lock; READY/UP waits
still process cancellation. The selected key is used for cleanup. STOP,
partial/malformed/mismatched receipts, stale deadlines, and cancellation
before GO or after UP raise rather than reporting successful progress.

**VERIFIED focused execution:** 58 watchdog/G0/G2 tests passed using pipes.
They include parent stall/kill, post-UP cancellation, independent release,
invalid selections, actual child STOP reason, stale post-READY deadlines and
slow child writes. Two additional tests combine the actual retained follower
with the separate watchdog child. One sends a bounded event sequence to a
pipe, applies the child's conservative write-time bounds to the controller,
then advances only after two new synthetic stopped fixes. The second changes
to assist after selection and emits no DOWN event. All character alignment
and location inputs in these integrations are synthetic. No device was
opened and no real client input occurred.

The first compatibility run had55 passing checks and one error-message
assertion: the new cancellation message said "after key release", while G0
expected "after release". The wording was corrected, then all58 focused
checks passed, including two added child-process cases. This was an assertion
compatibility failure, not a key-release failure.

**Remaining integration:** A real owner-preview bridge must supply current
scene/calibration and a complete swept-motion check, derive expiry from
proposal time rather than refreshing it after slow checks, and release/halt
on any sender failure or mode change. This source release supplies the timing
APIs and pipe integration, not that live caller. Existing owner assist0.39.6
and G0 candidate0.39.7 remain unchanged; no F11 or live route acceptance.

## Source 0.41.49 private publication — 2026-11-14 01:11 UTC

**VERIFIED:** Commit `f80c069` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.49/source`. Local/remote archive
SHA-256 matched
`fa7b46a73a717903c134b0e322d3681531dd8c6797bc9f61a7dca939d289c056`.
Remote fixed-route API import, replay CLI startup, and offline navigation
demo passed. The demo is explicitly simulated; the separate 155-segment
copied-data replay ran on the devbox. `smoke.json` and startup outputs remain
beside the private archive. No input device, character or game-prefix action
was taken. Assist remains0.39.6; this source release does not enable F11.

## Timed-sender integration dependency — 2026-11-14 01:11 UTC

**VERIFIED read-only source inspection:** The retained KeySender already
exposes its existing device descriptor, UP/LEFT/RIGHT codes, focus/input/chat
check, held-key bookkeeping and redundant release. A separate measurement/
full-auto bridge can reuse these; the G0 `Engine.hold` admission remains
forward-only and must not become an assist movement path. Zero-key proposals
need observations only, never a device pulse.

The current project `timed_key_pulse` returns a rounded duration, whereas the
new controller needs actual start/release timestamps and rejects a start more
than50ms after proposal. The subprocess starts after the proposal, so merely
wiring these APIs would reject delayed startup or invent timestamps. Next:
add a timestamped child receipt while preserving the old float-return API,
and bind/revalidate the proposal after watchdog readiness. Parent return time
must not substitute for key timing. Fresh scene and full swept-motion checks
remain required; no route sender is connected in0.41.49.

## Fixed-route controller and complete copied GFay replay — 2026-11-14 01:09 UTC

**VERIFIED implementation:** `fixed_route_follower.py` loads an explicitly
hash-pinned segment export and reuses the retained `eqnav.steer` Motion,
PoseEstimator and PathFollower. It creates one follower for each proposal,
with no implicit path search, heading probe, back/jump or recovery. It pivots
separately from forward movement. Only an actual completed hold receipt is
integrated; a rejected proposal halts and cannot be predicted on a later tick.
The controller has no input device or sender. External scene/geometry checks,
release watchdog and cancellation release remain caller responsibilities.

Two new aligned raw fixes after release/settle must agree before endpoint
advancement. The current mesh/calibration, zone/log generation, sequence,
XY and height must match; predicted arrival cannot advance the cursor. The
raw-WLD to helper-frame XY swap is explicit at the observation boundary.
A change to assist/OFF or cancellation invalidates pending proposals.
Eighteen focused integration tests passed using the actual hash-pinned
retained helper classes, with synthetic alignment and location observations.
No device or live game was accessed by these tests.

**VERIFIED defects found and corrected by copied-route replay:**

- Maximum-size pulses could leave a final distance below the chosen minimum
  pulse. Requested holds now partition the remaining distance; a minimum
  hold that overshoots beyond the endpoint radius refuses. This is estimated
  timing, not proof of actual sender precision or bounded displacement.
- A new legacy follower starts its projection at s0 with a 60-unit search
  window. Beyond that window it could steer backward. The new wrapper seeds
  its progress from the observed point on the current fixed segment.
- Default lookahead and turn tolerance let a small heading error drift beyond
  the 1.2-unit strip on a long leg. Lookahead now scales with that strip, with
  smaller turn thresholds. The requested turn targets the same lookahead
  point as the existing follower. A long-corridor regression exercises it.

**VERIFIED idealized execution:** `tools/replay_fixed_route.py` drives the
actual retained steering and new controller over the pinned copied GFay
plan. Version v5 completed 155/155 segments in 2,147 steps, 1,384.17 simulated
seconds and 11.10 seconds of offline computation. Its motion assumes exactly
30.77 units/second and a 0.02-second minimum hold; neither is current live
calibration. Synthetic stopped fixes use copied detail-surface heights.
Twenty-nine endpoint samples fall just across a portal and consult only the
adjacent selected polygon within the 0.25-unit endpoint disk, retaining its
height. Full swept motion, dynamic obstacles, actual timing and client UI
are not checked by this replay. No route or real-client acceptance is gained.

Private artifacts under `nav-candidates/`:

| Artifact | SHA-256 | Result |
| --- | --- | --- |
| `gfay-fixed-controller-replay-0.41.49.json` | `e4bf8c5bb966124ef5c84bbec36f483f149a2c8cc138e76ce2d7e009abfb01d5` | Stops after four segments; final-step sizing defect |
| `gfay-fixed-controller-replay-0.41.49-v2.json` | `dacc683b2d5e8cc2bd28cb3c647f678914992dced4a06febad706221c72250f3` | Stops after five; reseeded progress defect |
| `gfay-fixed-controller-replay-0.41.49-v3.json` | `ee47bc4d68c09adccbd00349b1437e91e7d6bb911b36e1e834fd16fc3e60b7bc` | Stops at26; endpoint sampling lacked adjacent polygon |
| `gfay-fixed-controller-replay-0.41.49-v4.json` | `497daeb80d7b2456dcc0ee4b09f6203d6c2d293cebe8e69d9e415019075d11e3` | Stops at113; narrow-strip drift |
| `gfay-fixed-controller-replay-0.41.49-v5.json` | `b468b2be658f21f3dbeac3197d89bbf82627460d8a8ab59b91eaec1eab27d99e` | All155, idealized only |

The last report pins controller source
`44cf7315fd15e3db296bb4f45f5c06cef25fc1fd413e4cee2788f2606a51be1d`
and replay source
`5a3376e6c85e6f9286c8f0b99d5ea040e14077108c41063d7ef1d45f01b013a9`.
Current live metrics remain unobserved beyond the prior Legira7 GFay report;
old G0 visible stop remains passed. The pending owner-ready map/current-scene
capture, live alignment/speed, swept-control check and owner-preview timed
sender are next. Assist remains0.39.6; no extra owner test is requested.

## Source 0.41.48 private publication — 2026-11-14 01:01 UTC

**VERIFIED:** Source commit `b671d2d` is staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.41.48/source`. Archive SHA-256
`2cbc8b52a66849121480ae686fd2f1fe5c00634686a9c01ea03783647a99cb05`
matched before extraction outside the game install. API import, both new
CLI startup checks, and the offline navigation demo returned zero. The demo
reports `final_directive=ARRIVED`, `simulation_only=true`, `no_game_input=true`.
The initial smoke wrapper expected the wrong JSON key `state`; parsing the
saved output with its actual `final_directive` key resolved that reporting
error without rerunning the demo. Private `smoke.json` retains that note.
No devices were opened, game input sent, or character/prefix changed.

Recommended assist remains 0.39.6 and separate G0 candidate 0.39.7. The owner
has not yet supplied readiness for the pending read-only Current Zone map
capture; that observation, live scene calibration, alignment/speed and a
bounded fixed-route controller remain required. No 1–20 leg, live camp or
automated level gain is accepted. The goal remains active.

## Scene integration and fixed GFay segment export — 2026-11-14 00:59 UTC

**VERIFIED focused tests:** `g2_safety_provider.py` joins the existing
read-only owner-input observer to `G2ReadOnlySceneObserver`. A new UI frame
must be captured between two complete, clear input scans with matching
input topology. Both ends verify the exact focused window/process/start
identity, measurement mode and cancellation generation. The frame must match
the bound calibration, report every independent scene check, and fit the
existing 0.10-second freshness bound. The returned time is the oldest check,
not completion time. Twenty-seven focused tests passed, including connection
to real `LocationLogReader` parsing of new fixture zone/location lines.
Tests cover F9/mode/session/focus changes, input contacts/activity, unknown
or stale frames, slow clocks and failed callbacks. UI/device evidence in
these tests is simulated. The actual calibrated UI classifier and owner
preview caller are not implemented; this library does not send game input.

**VERIFIED copied-data execution:** `tools/prepare_gfay_segment_plan.py`
exports the pinned 155-polygon GFay corridor using the accepted offline
portal selection and corrected-frame BSP evidence. Both endpoints of each
segment get their polygon's detail-surface height; no zero-height default,
new path search, averaged seam or shortcut is substituted. All polygons are
ground, all segments have length, and maximum adjacent height disagreement
is 0.0000993064 unit. Source/input hashes are checked before and after.
Execution took 3.79 seconds. Private artifact:
`nav-candidates/gfay-fixed-segment-plan-0.41.48.json`, SHA-256
`145679ec15111cf2d319ca630c66da693cc69863bdef594f67a46989c18592a4`.
Its origin is the historical G0 position, its goal an unverified guide marker,
and its frame is `(WLD Y, WLD X, Z)`. It is not current route acceptance.

**VERIFIED retained-code behavior:** `tools/probe_legacy_follower.py` uses
hash-pinned `eqnav/steer.py` and `eqnav/mesh.py` from owner-assist/0.39.4,
without input devices. On an L-shaped fixture the whole-route lookahead sends
forward along a shortcut whose midpoint is 2.5 units from the selected path,
outside the audited 1.2-unit half-width. Supplying only the first segment
instead requests a turn with no forward input. A delayed-location fixture
also reports `arrived` at predicted Y10 while the raw fix is still Y9.
Private probe `nav-candidates/legacy-follower-corner-arrival-0.41.48-v3.json`,
SHA-256 `c22363c8f0aa12731434b45c124181b6366bbd62d4967c92eac19c99c2e8a013`.

**VERIFIED additional short-segment defect:** The default three-unit arrival
radius marks a 0.6-unit fixture arrived after an unchanged raw fix, with no
forward request. Radius0.25 requests forward and remains running on that
same unchanged fix. This is an offline tuning example, not calibrated live
precision. The actual 155-segment export has 35 segments no longer than three
units and a minimum of 0.599976 unit. The final v3 probe retains the corner,
delayed-arrival, short-segment and tuned-control cases; v1/v2 remain private
history. Live movement granularity may require separately audited traversal
across several short portals, rather than assuming a stop within 0.25 unit
is achievable. No portal skipping or route acceptance is enabled.

**INFERRED implementation requirement:** Reuse the old helper's pose and
single-segment follower behind a bounded swept-motion guard; do not call its
Navigator, which replans independently of the audited route. Unknown heading,
probe/turn-test/back/jump and rejected controls must terminate that follower;
continuing it would predict unsent controls. Advance only with a new raw fix
after keys are released and motion settled. These runtime constraints are
recorded by the exporter, not implemented by it. Live scene, current start,
alignment/speed, controller and actual camp acceptance remain open. The
owner's old G0 stop confirmation is preserved; no further G0 test is asked.


## Source 0.41.47 private publication — 2026-11-14 00:52 UTC

**VERIFIED:** Source commit `b6df01d` is staged on Alienware at
`~/.local/share/eql-automation/owner-tools/0.41.47/source`. Local/remote archive
SHA-256 matched
`a6a079824b57520f8564f58bfd194707cfc0e603d0656166cb111eaf02b11aa2`.
Remote imports/closed-observer refusal, input-observation and UI-capture CLI
startup passed. The capture declares the actual map zone label. The offline
navigation demo reports ARRIVED with `simulation_only=true`; no actual route
was driven. Private `smoke.json` records results. This final startup smoke
opened no input devices; the separate documented candidate probe did open
read-only descriptors. Neither sent game input or modified characters/prefix.

Owner was asked for map → Current Zone with the game left focused, allowing
the lead to capture read-only without another terminal command. No readiness
reply or new image has been observed at publication. Recommended assist is
still 0.39.6, separate G0 candidate 0.39.7; no route acceptance is claimed.

## Alienware input contacts and event-queue correction — 2026-11-14 00:50 UTC

**VERIFIED read-only installed metadata:** The laptop exposes 26 input event
nodes. The only absolute-axis devices observed are a VEN_06CB:00 06CB:CE26
buttonpad (axes 0,1,47,53,54,55,57; properties POINTER+BUTTONPAD) and the Razer
DeathAdder Elite's ABS_VOLUME axis32. `input_contacts.py` accepts that exact
buttonpad capability shape, queries every bounded type-B tracking slot with
EVIOCGMTSLOTS, and requires unused slots plus clear touch/tool keys. Other
axis layouts remain unsupported. Absolute volume has no neutral-position
requirement, but every ABS event, including value zero, counts as activity.
Contact interpretation follows the [kernel multitouch protocol](https://docs.kernel.org/input/multi-touch-protocol.html)
and the read-only buffer ABI in [Linux input.h](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/input.h).
The ioctl encoding is restricted to the tested x86_64 Linux ABI.

**VERIFIED defect found in the real probe:** The first source candidate saw
held-key counts 0→1→0 but no queued activity. Review of
[evdev_handle_get_val](https://raw.githubusercontent.com/torvalds/linux/master/drivers/input/evdev.c)
shows EVIOCGKEY flushes that client's queued key events. The 0.41.46 observer
used one descriptor for queries and event reads, so its synthetic brief-tap
tests did not model this kernel behavior. Its real event-history completeness
is not accepted. Source-only 0.41.46 was never wired into movement; existing
assist 0.39.6 does not use this new observer.

**VERIFIED fix and focused checks:** Each input node now has two independent
O_RDONLY/nonblocking/no-follow opens, one for event reads and another for
state ioctls. `dup()` would share the evdev client and is deliberately not
used. Both fstats must match, and both descriptors close on failure. A new
regression emulates the state query flushing its own queue while a short
press/release remains on the event reader. Thirty-two focused tests passed,
including contact held before attachment, contact release during scanning,
invalid/changed/oversized/incomplete slot data, unknown axes and ABS-to-zero.
The installed evdev 1.9.3 C wrapper may surface failed EVIOCGKEY as SystemError;
that error also invalidates observation. Its `input.c` SHA-256 is
`c083605053c070502c8e75da4236b73ebff887ebb846c5f67046ff21fcaf39d9`.

**VERIFIED brief read-only laptop execution:** `tools/observe_owner_input.py`
records counts/errors only, never typed keys. Final candidate2 archive SHA
`a22826b0fe374727b97b8d24c410aaecbd44fb29caa4c1c74554180a764eb6cf`
matched before extraction outside the game prefix. Three samples covered all
26 devices: first attach was rejected, then two complete quiet observations
with zero unknown axes, contacts or held keys. Each scan took under one
millisecond. This exercised the actual read-only APIs but did not deliberately
test a held finger or brief key tap. No device was grabbed, no virtual device
created, no permissions changed and no game input sent. The new observer is
still not wired into G2/F11.

Retained locally/remotely under `owner-input-observations/`:

| Evidence | SHA-256 | Scope |
| --- | --- | --- |
| `20261114T004600Z-1794617160427839439.json` | `3f3340b3cc807b03fc31cc576ea209cf620b8cc8039f40a0ad9d561fe0d6ffcf` | Initial device API/contact evidence; superseded for event-history completeness |
| `20261114T004852Z-1794617332296603712.json` | `5c8faa35c9bb9684a79f1a6a5af21cce5154a59f717448540820f21b411dde0a` | Separate-descriptor quiet probe; no movement acceptance |

Final observer source SHA:
`296171170fa9aee7b3b021e00f3fa29103bb822f8f2c0e854c4c28e5f405b4a6`;
contact reader SHA:
`4521dde1d977bf6ea7cc912586fafd0ff73613fd9324f2314bc4bdb5a628a577`.

## Fresh-zone UI source located — 2026-11-14 00:50 UTC

**VERIFIED read-only Alienware source:** Installed
`uifiles/default/EQUI_MapViewWnd.xml`, SHA
`6bcdcc7b20c6510c5797e044ab3193b8a7fa2386dc87e8d770b5387346fe6419`,
defines `MRA_ZoneLabel` with EQType1020 at lines310–327. The Current Zone
button (`MVW_LoadCurrent`) resets a browsed map to the player's zone. The
contemporary inference that the label represents the browsed zone is superseded
by the source 0.42.8 native audit above; live recognition/refresh remains open.
The saved Legira UI INI SHA
`5876a4136283b692263bc2826ffc2b12cd7328f4faa320c5f4071f2092fbc76b`
has the map hidden. The existing pinned layout parser computes a map rectangle
(1288,476,1198,955) and label (1301,1403,250,15) at2560×1600. Its button
rectangle has zero size; no automated click is implemented or inferred.

The read-only capture now includes the map and label and explicitly marks
current-zone verification false. One capture attempt this turn refused
because a unique focused game/session was unavailable; no focus changed,
image captured or game input sent. No new assist trace/UI capture was found;
the old G0 trace is unchanged. Historical zone-entry text is insufficient
for an independent current-zone bootstrap. Owner-selected Current Zone and
idle scene images remain the next observation, followed by production scene
integration, current location/alignment and speed calibration. No accepted
1–20 leg, automated XP or new level observation exists.

## Source 0.41.46 privately staged — 2026-11-14 00:43 UTC

**VERIFIED:** Commit `a920826` is staged on Alienware under
`~/.local/share/eql-automation/owner-tools/0.41.46/source`. Local/remote archive
SHA-256 matched
`bffe9db1da810fa6b6d2e65b673fb3fc038075341a74eda614dbdca1ac90c1dc`.
Remote API imports and closed-observer refusal passed without enumerating or
opening event devices. Both new diagnostic CLIs start, and the offline
navigation demo reports ARRIVED with `simulation_only=true` and
`no_game_input=true`. `smoke.json` and CLI stdout/stderr remain beside the
private archive. The initial extraction guard rejected git archive's root
`source` directory before extracting anything; the corrected guard explicitly
allows that root directory while still rejecting links and other paths.
No game/prefix files or characters were changed. Recommended assist remains
0.39.6; this is a source release, not playable route acceptance.

## Source span attribution and actual route comparison — 2026-11-14 00:40 UTC

**VERIFIED offline:** `tools/probe_crushbone_spans.cpp` compiled with
`-Wall -Wextra -Werror` against retained Recast commit
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`. Its one-tile source diagnostic
preserves the ordered EQTR, original vertical/grid bounds and baseline
raster/filter parameters. It includes the pinned upstream contour routine to
inspect corner selection; it does not bake a replacement mesh. All products
are in the approved private data store, not git.

At the west raised corner, source face 15419 creates floor span 616–617 with
walkable area 63. Vertical face 15424, itself slope-marked area 0, merges into
that raw span and raises its top to 622 while retaining area 63. Face 15427
raises it to 623, world Z1.962509. The low-hanging, ledge and clearance filters
leave it unchanged. Connected compact spans 617 and 623 make the contour
corner inherit 623. The east sample likewise reproduces Z2.262512. This
supports raster span merge and connected corner selection as the local cause,
rather than detail sampling or later low-hanging promotion. The exact custom
baker wrapper source is unavailable; full source/binary equivalence is **not
established**. BSP labels are recorded separately, not applied to these spans.

Final span report:
`nav-candidates/crushbone-span-attribution-final-0.41.46/report.json`, SHA-256
`02a9a785d61a47649846e64b3cd89a916201c97cd07d5d054e2fecac71ade1ef`.
Ordered source EQTR remains
`ad521d7df14c0d4a578923595316794cb06181672bb8f22b21f0925ec43e9da5`.
The preceding detail-distance report (`b0e7307e…`) is a different experiment,
not a revision of this span report. Both remain retained.

**VERIFIED bounded bake and route query:** Changing only maximum climb from
3.5 to 1.0 produced 5,124 polygons/9,920 links/35,200 detail triangles with 26
warnings. Its old fixed ring cannot support one outer sample, so a separate
query checked the actual retained arrival and Slaver guide endpoints. Both
snap to ground with zero XY drift and at most 0.060 vertical drift, but are
in disconnected components. No route exists between them in this candidate.
The baseline control finds 80 polygons, then rejects polygon 3244 after 41
turn checks and no strip checks, reproducing the previous footprint failure.
No checks were waived, no candidate was installed and no game input was sent.

Private artifacts under `~/.local/share/eql-automation/`:

| Artifact | SHA-256 |
| --- | --- |
| `nav-candidates/crushbone-lower-climb-0.41.46/report.json` | `17e2b9fda8d2dc25aa10f78fc51ba5d201e69211fce6fe654f98ba21682ab32d` |
| `nav-candidates/crushbone-lower-climb-0.41.46/lower_climb.eqnm` | `5f2e34f8bd7ad5277028910218ab816389b50c776ee9f419a232758b381062b0` |
| `nav-candidates/crushbone-lower-climb-route-v3-0.41.46/report.json` | `ce38ee19f8c47628b6edab75221686ebe16246a77a9d0d3ae56d799e577f1623` |
| `nav-candidates/crushbone-baseline-route-0.41.46/report.json` | `c457b927e472a87c1d9b209a3514728a5f6eece46660c705dcd0a097d693cd3b` |

Each query retains its executed source and hash. Two initial query attempts
used system Python without NumPy and failed before loading a mesh; their
incomplete checkpoints remain retained. The successful runs used the existing
`python-nav/bin/python`. The final CLI checks imports before creating a report
directory and has a clear missing-runtime error. The endpoints use the helper
Y,X,Z frame despite old artifact keys labelled WLD. They are historical guide
positions, not a current player observation. **No real-client acceptance.**

## Read-only owner-input dependency — 2026-11-14 00:40 UTC

**VERIFIED source and 13 focused tests:** `owner_input_observer.py` inventories
all visible event nodes, uses explicit O_RDONLY/nonblocking/no-follow opens,
and checks descriptor identity and device topology before and after scanning.
It samples active EV_KEY state on both sides of draining events, including
mouse/controller buttons and devices lacking F8. Brief press/release activity
is retained as an unsafe observation. Unreadable devices, replacement,
read errors, empty coverage, slow/rolled-back clocks and stream loss prevent
clear results. SYN_DROPPED remains latched until SYN_REPORT and a fresh key
snapshot. Collection start determines freshness. Counts are returned without
logging typed key codes. EV_ABS remains unsupported rather than assuming zero
means neutral.

Only the exact live helper uinput event node may be excluded: UI_GET_SYSNAME,
sysfs parent/device links, major/minor and read-only node fstat must agree,
and the identity is rechecked each sample. Same device names are irrelevant.
Installed Alienware evdev read API signatures were inspected without opening
input devices; they match this implementation. `InputDevice()` is deliberately
not used because it attempts O_RDWR first. Installed source hashes:
`device.py` = `f2c2871a6661dc3175949a6c232d2917547d2f9a86cdacc51ab7ad6b2b2ed4eb`;
`uinput.py` = `bc96f91344e1a6d0e8e87781d2673be33157921dffa16edae5a9a7fa3856a3d5`.

The observer is not wired into G2/assist and no real devices were observed.
Its fake-device tests establish behavior under the tested failures, not live
input completeness. Scene/UI indicators, current zone, alignment, fresh speed
and a real follower remain missing. GFay is the first same-zone movement
candidate; assist 0.39.6 and separate G0 candidate 0.39.7 remain unchanged.

## Actual G0 dispatch wired to independent release — 2026-11-13 18:24 CST

**VERIFIED source, pipe tests and Alienware engine smoke; no game input:**
New `owner_g0_watchdog.py` wraps the existing 0.39.6 adapter. Its `hold()`
accepts only measurement mode, running `stop_check`, `forward`, exactly 0.15
seconds, and no jump, with combat/preparation off. Assist refuses before
creating a sender. It passes the helper's existing uinput descriptor to
`timed_key_pulse`, checks cancellation/focus/owner input around GO, and keeps
failed-release held-key records for cleanup. A reentrant lock serializes
stop_action/stop_autopilot with GO because sender checks can process F9 on
the same thread. Cancellation after child UP also rejects the result.

READY now pumps owner events; DOWN acknowledgment intentionally does not.
An intermediate review caught why pumping inside that locked wait was wrong:
a same-thread F9 could publish OFF before a queued GO was consumed. The final
code retains the locked acknowledgment-or-kill/UP ordering. UP waits pump
normally. This is not a hard real-time guarantee; OS scheduling and actual
client release remain unverified.

Twenty-eight focused pipe checks passed across adapter/watchdog/G2 bridge
runs. The older G2 bridge fixture sat exactly at a floating-point 0.4-second
subtraction boundary and failed at the current large monotonic uptime; its
fixture now uses an interior 0.5-second interval. Production thresholds were
not relaxed. Tests cover one DOWN/UP, pre-GO F9 reentrancy, F9/F11 after DOWN,
GUI stop after UP, stale states and retained failed-release bookkeeping.

Read-only introspection on Alienware confirms installed `evdev.UInput.fileno`
returns its existing `self.fd`; no device was created. The staged no-device
smoke constructs the actual Engine without running it, substitutes a pipe
sender, dispatches the actual `Hold` intent, sees exactly one DOWN followed
by release, and refuses that same hold after switching to assist. The prior
HP/recovery smoke also passed. No keyboard devices or client input were used.

Separate candidate path: `~/.local/share/eql-automation/owner-assist/0.39.7`.
Local/remote archive SHA-256:
`4c917a63f755e9ea3982a5939d5c9c7d3c35d9c7ffd0026c80680631df9d492b`.
Adapter SHA-256:
`9a905e4477494b944f8cad733b07907a9b7c35177890565f7f9c31c201d93b56`.
Watchdog SHA-256:
`00088c9733034d8aab1c00be65c800bed7deaf5a5a6b59f848c3ba20cf03dc79`.
The 0.39.6 owner HP-test intake is unchanged; no immediate repeat G0 is
requested. The older observed G0 pass does not certify this new sender.

**Real-client gates still open:** a single focused read-only capture attempt
refused because the game window/process condition was not met. No focus was
changed or input sent. G2 lacks a production independent scene provider,
current zone/location bootstrap, live alignment and a preceding fresh speed
calibration. These are implementation/evidence dependencies, not a request
for private-server permission. G2 and F11 remain disabled.

Source project 0.41.45 (`0503d58`) is staged separately under Alienware
`~/.local/share/eql-automation/owner-tools/0.41.45/source`. Local/remote archive
SHA-256 is `4e10cab4502313f3e1769af7699705188d0b4a9e8e51bab159946bf47b4e3d1e`.
Its builder CLI/startup smoke passed; the offline navigation demo returned
ARRIVED with `no_game_input=true`. No client acceptance follows from that demo.

## Crushbone detail-distance experiment rejected — 2026-11-13 18:24 CST

**VERIFIED bounded offline bake:** After the initial CPU-pressure hold, one
low-priority worker completed the pinned full-zone baseline and sample-distance
6→3 comparison within a 120-second outer limit (90-second per-child limit).
Baseline took 15.69 seconds and reproduced the prior EQNM hash and all 65
sample heights exactly. The new variant took 31.44 seconds, kept 5,143
polygons/10,260 links, and increased detail triangles 43,862→96,779. Warnings
rose 21→439. At radius 1.2 the maximum height worsened 1.70053→1.93756 and
maximum angular grade 1.80114→2.70633, still above the 1.2 limit. It is not
adopted. Denser detail alone does not resolve the source-flat/baked-bump issue.

Private directory: `nav-candidates/crushbone-detail-distance-0.41.45/`.
Report SHA-256:
`b0e7307e43d1b212ce8d5a973c3290014fb9f8eee862e2855de5a4bfa9246780`.
Variant EQNM SHA-256:
`549e0ba84bbe73ccb8093d2c842b49d17f864f513c70d7e073675ad547446269`.
Executed probe-source SHA-256:
`a920a11a5f14c0fc707c749c8e1731ecc757498ce7dccb7c0940e56b688981d6`.
The ordered EQTR remains
`ad521d7df14c0d4a578923595316794cb06181672bb8f22b21f0925ec43e9da5`.
No client movement, route acceptance or character progress resulted. Next is
source/voxel attribution; GFay remains the first same-zone route candidate.

## Crushbone bump predates detail sampling — 2026-11-13 18:27 CST

**VERIFIED read-only retained-artifact audit:** Baseline and detail-distance-3
EQNM products have identical coarse polygon 623 vertices (helper XYZ):
`(-172.64374,98.74379,2.26251)`, `(-173.84375,99.94379,0.16251)`,
`(-186.44374,99.94379,1.96251)`, `(-187.64374,98.74379,0.16251)`.
The source beneath the east high corner includes an actual Z=2 platform
(face 15339) and Z=0 floor (15376); the west high corner has Z=0 ground
(15419) and nearby raised wall faces 15424–15427. The 65 center/ring ground
samples remain Z=0. **INFERRED:** Coarse contour/polygon construction connects
raised geometry and floor within this long polygon; detail sampling alone
cannot remove those coarse corner heights.

The retained authorized upstream Recast tree is
`~/.local/share/eql-automation/toolchains/recastnavigation`, commit
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`. Its
`Recast/Source/RecastContour.cpp` SHA-256 is
`a9282897a5a5cb56cf8bbab97e0fd5edc3cd394ae8fe5266a28ce4199a4f3bfa`.
`getCornerHeight` at line 28 takes the maximum Y among up to four connected
compact spans; `walkContour` emits that height. Supporting source hashes:
`Recast.cpp` = `865595763451cde0aad5b99088bfab48d4ea35050fefd67f3d4f95885ba38d66`;
`RecastMesh.cpp` = `9667e69e1886a520fcc84044b2e96154ff75e5c804fa32520b1cc0d991e42fd9`.
The native baker main source was not found in the approved data store, so
source-to-binary equivalence is not established. Next diagnostic: inspect the
local compact spans/contour corner at the two elevated vertices to distinguish
an elevated voxel from a maximum-neighbor corner lift. Do not waive the
footprint check or promote either candidate. No forbidden old worktree was
read or recreated, and no game input was sent.

## Owner assist 0.39.6 stop and draft recovery — 2026-11-13 18:20 CST

**VERIFIED original-engine offline behavior and Alienware GUI, no game
input:** The 0.39.5 adapter retained `sender.unfinished` after owner
Escape/Enter, while the inherited F6/F8/F10 gate kept rejecting it. Its
instruction to clear chat and retry could not recover. Separately, a GUI
`prepare_later` queued before F9 carried no cancellation generation; it could
schedule preparation after that stop. Both cases were reproduced using the
retained engine methods without opening input devices.

New `owner_nov12_recovery.py` layers on the existing restricted adapter,
preserving earlier preview sources. Start jobs receive a generation and
stale/missing generations are rejected, including delayed preparation. An
explicit GUI confirmation captures the current generation before its dialog.
The worker accepts it only while stopped, with no held keys, no movement or
pointer mode and an actual pending draft. It clears local bookkeeping and
old target approval, invalidates queued starts, stays OFF, and sends no keys.
The owner must first close game chat themselves and later press F8. Cancel
and stale confirmations cannot resume assist. Existing F11/F12 blocking and
manual melee remain unchanged; UI labels and guide now accurately say so.
Measurement mode shows only the G0 stop button and its stop control.

Twenty-five focused adapter/recovery tests passed. The final isolated
preview's Alienware no-device smoke ran the original engine post/stop/job/
reset methods: a pre-F9 Prepare was discarded, recovery made no sender call,
old F8/Prepare jobs remained canceled, and a fresh F8 could arm while
unfocused. Offscreen assist and measurement GUI smokes reported
`worker_started=false`, `game_input_sent=false`, `settings_saved=false`.
Their rendered windows were inspected, including the fully visible G0 button.
No live helper was running from this candidate path when the initial cramped
layout candidate was retained separately and replaced before release.

Final private preview: `~/.local/share/eql-automation/owner-assist/0.39.6`
on Alienware. Local/remote archive SHA-256 matched
`7e750589a9f4c83e875e8a9a982be062e538ad78c54e635acb2494ad853f727c`.
Final GUI SHA-256:
`baa9ba1400cd4bbe995b97ecb68d9d1757ab40bcf14d5475d1c03998c09fbff3`.
Recovery module SHA-256:
`efdf13c8b63efc31154be0c889d7be85ea6f8736a340334a99c3486c9a1a5a34`.
The launcher pins both adapter modules as well as engine/UI/HP sources.
**Unverified:** live recovery, live HP/healing, strict target identity and
chat observation, G2, route following and automated leveling. F9 stops further
helper input; native melee and an already-started game cast are owner/client
controlled. The owner-visible G0 stop result remains accepted separately.

Source-only project 0.41.44 (`0cb5167`) is also staged at Alienware
`~/.local/share/eql-automation/owner-tools/0.41.44/source`. Its local/remote
archive SHA-256 is `b6043c05109c8dd6374394052a2414fbf1a0ee39d6b95dc042924171fa2a091f`.
Remote CLI/startup checks passed and the offline navigation demo returned
ARRIVED with `no_game_input=true`. This synthetic result is not movement
acceptance.

## Crushbone detail-sampling next experiment — 2026-11-13 18:20 CST

**VERIFIED read-only source probe by delegated audit:** All 65 existing
center/ring samples around helper-frame `(-180.14373779,98.74378967)` are
covered by EQTR face 15356 at Z=0. Other covering faces are sky at about
Z=625.8. The closest raised wall starts roughly 2.17 units from the center,
so flat source ground does not establish body clearance. The input EQTR
SHA-256 is `ad521d7df14c0d4a578923595316794cb06181672bb8f22b21f0925ec43e9da5`;
its private location is `nav-candidates/crushbone-cell-sensitivity-0.41.42/`.
**INFERRED:** Detail interpolation may explain part of the local baked bump;
this must be tested, not flattened or waived.

`tools/probe_crushbone_bake.py --comparison detail` now reproduces the
baseline and changes only `detail_sample_dist` 6→3, preserving the full
ordered source and 90-second/one-thread limits. The CLI/startup check passed;
the new comparison has **not run**. `vmstat` showed 116 runnable processes,
92% user + 8% system CPU and zero idle, so this bake was held while the small
owner preview shipped. No route or movement acceptance changed.

## Owner assist 0.39.5 proposes HP from client layout — 2026-11-13 18:08 CST

**VERIFIED build and synthetic Alienware GUI, no game input:** The new
preview builds from the pinned 0.39.4 rotation helper. Its existing HP
calibration dialog now proposes `PlayerWindow/Player_HP` using the selected
character/server and captured window dimensions. The owner sees the outline
and explicitly saves it at full HP; manual drag and Cancel remain available.
It rejects the old 51-pixel crop, missing/hidden/minimized/offscreen layouts,
and malformed identities. The saved layout rectangle is re-read before an
auto-proposed calibration is saved. Runtime HP pixel reading and the input
adapter are unchanged. This does not make unsaved UI moves observable.

The 13 focused rectangle tests passed. On Alienware, the existing no-device
rotation smoke passed. Three new offscreen calibration-dialog smokes used
synthetic full-red, half-red and blue bars at the real saved rectangle
`[1966,693,2296,710]`: only full red enabled Save; the other two kept the
region unknown. All three reported no worker, no game input and no settings
save, and the owner settings file remained byte-identical. The synthetic
full-bar dialog was visually inspected; private image SHA-256 is
`c2c09792d6e95b8bacdf3929859ae41141ad9e2851c75d2cf8c4207f8a4a18a1`.
Local no-device smoke attempts were blocked by the devbox environments'
missing Pillow/numpy combinations; the equivalent Alienware run passed.

Preview is staged outside the game install at
`~/.local/share/eql-automation/owner-assist/0.39.5` on Alienware. Local/remote
archive SHA-256 matched
`2161c8996305a4c1620a024074a3194908aaf7a908f2fcca9f124b8605806e2c`.
New GUI SHA-256 is
`cd59576a50ba353c6f47f03f04ebf7b92c4407785e7fdbd3a50e13df4a35ea17`;
the proposal module is
`3866414c8e3dfff41744ff7ba39e4996ae1ac645e2712ecf79a1836dcca1481f`.
Both and the existing UI-layout reader are checked by the launch guard.
**Unverified:** live HP calibration, partial-health reading, automatic
healing and strict assist acceptance. F11 is still disabled. The previous
0.39.4 preview remains available; no helper or game session was launched
for live input. HOWTO contains the owner launch and calibration steps.

## Controlled Crushbone horizontal-grid sensitivity — 2026-11-13 18:02 CST

**VERIFIED offline bake, no game input:** New `tools/probe_crushbone_bake.py`
uses the pinned owner helper, two copied archives and original baker. Both
variants used all 26,570 ordered triangles and 5,586 classifier nodes with
one low-priority thread and a 90-second child timeout. The EQTR SHA-256 is
`ad521d7df14c0d4a578923595316794cb06181672bb8f22b21f0925ec43e9da5`.
A repeated full-zone baseline preserved the grid origin and reproduced all
65 local ground heights at the old 658→623 crossing exactly (maximum
difference 0.0). It produced the retained counts: 5,143 polygons, 55 tiles,
21 Recast warnings, in 12.34 seconds.

Changing only the input `cell_size` from 0.6 to 0.3, with vertical cell height
0.3 and detail error 0.25 unchanged, produced 6,307 polygons, 190 tiles and
128 unclassified warnings in 56.65 seconds. At the fixed helper-frame
point `(-180.14373779296875,98.74378967285156)`, the 0.6-radius ring's
maximum height dropped from 1.29823 to 0.76766; its maximum radial/angular
grades dropped from 1.58037/1.47035 to 0.72182/0.95924. The 1.2-radius ring
still fails grade 1.2: radial 1.39795 and angular 1.33682. The copied source
ground at these samples is flat at Z=0. This is incomplete improvement,
not an accepted turn or route. Cell size also changes derived tile width
and detail sample spacing, so this does not isolate one internal Recast
stage as the cause. No warnings have been waived.

Private evidence: `nav-candidates/crushbone-cell-sensitivity-0.41.42/report.json`
under `~/.local/share/eql-automation/`, SHA-256
`9af647dce65f4ebb2907e7008e22db2adf33a5451d98633d8e4361adce9b1fba`.
Baseline EQNM SHA-256 is
`e798100211c36cbb86f54f8445d0dec1422b77242cfeab49f95999987f7380b0`;
half-cell EQNM SHA-256 is
`c476212e29f32bead6a8c0782d0bf1b700567bc2696318990c49d6d2e4bcc533`.
The exact executed script is retained there as `probe-source.py`, SHA-256
`a4e389f9b3b0dc1a5d6656243ca73e75b349545b722ea1383e85b2d6bd0bb499`.
The released script additionally checkpoints partial results and preserves
timeout/sampling-failure diagnostics. Those error paths were source-reviewed;
both real bakes succeeded, so those errors were not exercised by this run.
F11 remains off. The next live dependency is still the owner's idle UI
capture; the same-zone GFay route remains the practical level-7 candidate.

## Crushbone directed junction probe — 2026-11-13 17:56 CST

**VERIFIED copied-mesh diagnostic by read-only probe, no game input:** On the
retained detail-0.25 Crushbone mesh SHA-256 `ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56`,
the 80-polygon alternate route artifact SHA-256
`5762a13cf23d5b3a957d7e896662ff114700a1711c3d42cbe644f1a4eb15d9ad`
crosses portal 3244→3242. At portal fraction 0.20, its seam and the two
adjacent width-1.2/grade-1.2 travel strips pass separately, while the
360-degree turn disk fails with `angular_grade_too_steep` at radius 0.6.
This supports a bounded directed-turn investigation, not a safety waiver:
the copied source has raised rock close to the crossing. A diagnostic
selector bypass of only that junction then fails another turn at polygon
4316 after 83 turn checks and zero accepted strips. Neither junction nor
the Slaver route is accepted for movement; prioritize the same-zone GFay
orc-camp route while investigating both directed footprints.

## Future G2 start-area mesh frame correction — 2026-11-13 17:55 CST

**VERIFIED source and focused test, no game input:** The future
`check_g2_start` preflight held a calibrated point in raw client WLD XYZ but
queried the retained helper navmesh with that point directly. The helper
navmesh uses `(WLD Y, WLD X, Z)`, so an asymmetric point could check the wrong
ground. Version 0.41.41 swaps XY at this boundary and compares the snapped
point in the same helper frame. An asymmetric `(10,20,30)` raw-WLD test now
requires the first mesh query to be `(20,10,30)`; four focused tests passed.
There is no production caller for `check_g2_start` yet. This fix does not
enable G2, validate a live position, or authorize F11.

## Helper-mesh BSP frame correction — 2026-11-13 17:44 CST

**VERIFIED source and copied-data control:** The retained owner helper stores
navmesh XYZ as `(raw WLD Y, raw WLD X, Z)`; its pinned `eqnav/zonegeom.py`
SHA-256 is `bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60`.
The project's raw copied-WLD `BspPointLookup` expects `(WLD X,WLD Y,Z)`.
Before 0.41.40, `ground_bsp_route.py` passed helper mesh XY to that lookup
without swapping them. The old helper-mesh BSP route and ring artifacts are
**invalid provenance** and must not be used as water/unknown clearance proof.
A positive control from the copied Butcherblock WLD shows why: the helper
Kaladim trigger point `(-180.98,3136.79,8.88)` probes an unlabelled region
without the swap and a zone-line region after the swap. The code now swaps XY
at this boundary, pins the helper frame source and requires one manifest
trigger to resolve as a copied BSP zone line before producing v2 evidence.

**VERIFIED corrected offline approach scans, no game input:** A new
hash-bound v2 GFay G0-position→orc-marker scan checked 155 copied ground
segments at mesh height and height+1: 376 BSP spans, no labelled, unknown or
unsupported intervals. Its private artifact SHA-256 is
`2ed1de243e26aa927ff164677d6251b765e3e3ea468836ea68887298e36a9f33`.
The corrected Butcherblock camp→GFay v2 scan checked 249 segments at both
heights: 566 spans, no labelled, unknown or unsupported intervals; artifact
SHA-256 `ef3239d708dfb1aad6035610e562c7c685e0bdc64da1da6671552a5453189259`.
Both records explicitly report `swap_xy_keep_z` and a positive copied zone-line
frame control. The GFay orc camp's corrected v2 local-ring record has five
of six one-polygon spokes passing copied strip/BSP checks; its sixth needs a
portal sequence. Artifact SHA-256 is
`02c86635a07c10eb856569f702b98ea701ad200e109853144960a771396045ab`.
The corrected Butcherblock Kaladim-yard v2 ring retains 12 of 12 local
strip/BSP candidates, seven with >6-unit height change; artifact SHA-256 is
`48d05c38ae76666d54739e3b7674e623d55297b88fa1ec89d65979c7d338d066`.
Both rings also include a positive copied zone-line frame control. These
static diagnostics do not verify client collision, current position, a zone
crossing or actual movement. The project-built raw-WLD Kaladim Detour query
and its BSP scan were already in the correct frame and are unaffected.

**VERIFIED corrected offline funnel scans:** The old helper-frame Cauldron
and Unrest funnel BSP artifacts also omitted the XY swap. Replaying their
saved points in the old frame reproduced the old span totals and eight false
Unrest water spans. The new hash-pinned v2 Cauldron artifact SHA-256
`0a115cd3a183c43fece695bacbfd28e849b5f71fb2f25acb04428143fd438e4c`
has 224 unlabelled spans across 81 segments. The new Unrest artifact SHA-256
`0815ec90d9ea947dd05ee4e4e6eecd4c3967cc1ebf7f5eec3ac4f9735b434dc6`
has 116 unlabelled spans across 30 segments. Neither corrected scan has
water, unknown or other labelled intervals at the path and path+1 heights.
The older claim that the sampled Unrest entrance route is water at foot
height is **retracted**. These are straight funnel scans only; they do not
clear full ground strips, dynamic doors or the failing Unrest route selector.
The older GFay→Butcher helper-mesh BSP artifact also had the wrong frame.
Its hash-pinned v2 reissue scanned the 52-ground-polygon approach at mesh
height and height+1, found 116 spans with no labelled/unknown/unsupported
intervals, and retained an explicit positive frame control. Artifact SHA-256
is `1c52bf26c45b0f046af54adb4a67967573b1511cbaf55a389fbae71bcd325081`.
This ends before the zone trigger and uses a historical start, so it is not
a current movement route.
The owner-run G0 stop remains observed; its mesh alignment used the helper's
proper `/location` swap. The old G0 field `snapped_wld_xyz` is misnamed and
actually contains helper-frame XYZ. G2 and F11 remain closed.

## Finer Crushbone corridor still fails a copied turn — 2026-11-13 17:34 CST

**VERIFIED offline, no game input:** The retained included Boundary,
detail-error 0.25 Crushbone mesh SHA-256
`ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56`
has an 80-ground-polygon graph path from the copied arrival to the Slaver
goal after excluding the second suspect portal 658↔623. The private
hash-bound corridor JSON is
`crushbone-detail025-avoid-658-623-route-0.41.39.json`, SHA-256
`5762a13cf23d5b3a957d7e896662ff114700a1711c3d42cbe644f1a4eb15d9ad`.
It is a graph result, not a verified walkable path.

The required selector at width 1.2 and grade 1.2 rejected portal
3244→3242 with `no_sampled_turn_disk_candidate` after 41 turn checks and
zero full strips; expanding its candidate budget from 6 to 13 made no
difference. The second selector JSON SHA-256 is
`fa3c69bdcdca9ccf381690e9f3858b396d6b2be149b6584b5063bd57107e8c3a`.
At that edge, 0.2 of the portal fails angular grade and sampled fractions
0.35–0.8 fail radial grade, all at a 0.6-unit check radius. A separate
read-only graph check found that excluding both directed portals 3244→3242
and 658→623 disconnects the saved arrival from the Slaver goal: 1,376
ground polygons are reachable without reaching the goal. Either edge alone
leaves graph connectivity. All 13 sampled fractions at 3244→3242 fail at
grade 1.2, and none passes even at diagnostic grade 2.0. A graph route
avoiding polygon 3244 alone takes 198 polygons via 658→623 and fails its
selector earlier at polygon 55 even at diagnostic grade 1.75. The mesh's
21 Recast warnings remain unclassified, and the route has no full strip/BSP
acceptance or real-client traversal. F11 remains disabled.

## Copied Kaladim starting-zone source — 2026-11-13 17:27 CST

**VERIFIED offline, no game input:** `kaladima` is South Kaladim in the
owner's client map labels; `kaladimb` is North Kaladim. Four zone/object
archives were copied read-only from the Alienware install into the approved
untracked private store; local SHA-256 matched the installed originals:

| Archive | SHA-256 |
| --- | --- |
| `kaladima.s3d` | `4e9dfb073a551f0caaca736286d3b73eaff3bf1cbaef1b143b575ce65d91f8f7` |
| `kaladima_obj.s3d` | `192c44e5e3c6e110d72aff09a6f06d802383b3d7ec019114d78c82894bec4c6e` |
| `kaladimb.s3d` | `605911382c8bc23bd2d735ba2e3eb0e8f7f941f7a260895acc01db87d7a5ba12` |
| `kaladimb_obj.s3d` | `649ddc660e18a997b393e2f7da7fd32e7eb080eb7ef5832b37cba3fc92a3b103` |

The copied map SHA-256 values are `bfcbaed6d2c04b506a82a073b00133f830ad961d59fd2df78598d75a2099f69d`
(`kaladima.txt`), `f6f6d9d30752b7f7d812126af323eac66c558f16641cf4cce0bd561310aea5f7`
(`kaladima_1.txt`), `f83bb7f4e39f937d66ca65088f5bbfc8f8f4827f645cea1ca4e304bf36dcc13b`
(`kaladimb.txt`) and `e4c8c4398c2a987085ca362aee9142a5b14915bda9af67d86a7be02fa0c58656`
(`kaladimb_1.txt`). The private copies are under
`~/.local/share/eql-automation/client-data/retail-full/assets/` and
`~/.local/share/eql-automation/client-data/retail-full/maps/`.

South Kaladim's copied terrain WLD has 5,861 BSP nodes and 1,474 regions;
22 region-type records are water and three are zone-line candidates. North
Kaladim has 7,436 nodes and 2,021 regions; 40 records are water and two are
zone-line candidates. Both map geometries independently select the `-y,-x`
map-to-WLD transform. South Kaladim's `to_Butcherblock_Mountains` label is
near copied surface Z=0; a sampled zone-line region at WLD
`(-87.2702,39.7893,0)` lies 30 units in XY from its label. At the label itself
the BSP lookup returns `missing BSP child`, so its trigger shape and exact
entry direction are unresolved. North Kaladim's second South Kaladim label
has a sampled zone-line region five units away; its first does not have one
within the current search radius. These are static candidates only.

The pinned `--build-copied-zone-candidate-scene` command composed provisional
South Kaladim OBJ SHA-256
`c9e0a3c9d16e278d53fd958f5696e8d88df18be927a76ac0980d4bb9f85f02c8`
(40,707 vertices, 23,854 faces) and North Kaladim OBJ SHA-256
`ea49e4f493dc08b541ddfb247acf612dab5168f3d400cd73b153ebdd98bdc8f5`
(52,743 vertices, 30,591 faces), both under
`~/.local/share/eql-automation/nav-candidates/`. All 266 South and 249 North
object placements found exact model names. Collision materials, doors,
navigability, spawn, a real zone crossing and an automated level gain remain
unverified. F11 remains disabled.

**VERIFIED offline exit diagnostic:** The pinned local Recast baker
(`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`) produced a 128-unit
South Kaladim exit tile with 50 provisional nav polygons using profile
`height=8,radius=5,climb=2,slope=45`. The nav SHA-256 is
`6e3efc8ddd012f7a270980416ef180d30d26a0ca94b5456de09209dd3c67c7f6`.
The hash-bound local Detour query from sampled BSP zone-line point
`(-87.2702,39.7893,0)` toward the map label at `(-57.2702,39.7893,0)`
returned six polygons and five straight points, with start/end snap distances
0.747/0.866 units; query JSON SHA-256 is
`8b975e42785ef693d9af3dfd441e1d83892005e2ed6d991e888eab5d989144d1`.
A separate copied BSP scan of its four straight segments at path and path+1
height found two zone-line spans at the start and four unlabelled spans, with
no water/unknown spans. A reverse Detour query from the map label toward the
sampled zone-line point also completes in six polygons and five points,
SHA-256 `53604bd54be15e55550fd17ce7a61fb2fef425edad954a07859f9c960c3b411c`.
Its copied BSP scan at both heights has four unlabelled spans followed by
two zone-line spans; it has no water or unknown span. This supports an
offline approach into the labelled region, but the actual trigger direction
and transition remain unknown.
The tile covers only the exit vicinity and gives no fresh-character spawn
location or certified route from spawn. No real client movement was run.

## HP crop evidence reader — 2026-11-13 17:20 CST

**VERIFIED source diagnosis, live pixels still missing:** The owner preview
0.39.4 saved HP crop is `[1963,661,2301,712]` at 2560×1600, 51 pixels high.
Its `WindowGate.read_gauges` rejects HP crops taller than 24 pixels before
reading their pixels, producing `hp_recalibrate_inner_bar` and `hp=None`.
The installed UI layout resolves `Player_HP` to `(1966,693,330,17)` and
the client XML defines that control as a red-tinted gauge. This is a
source-backed candidate, not proof of the active live bar.

Project 0.41.38 adds a read-only analyzer for the private owner-created
`PlayerWindow__Player_HP.png` crop. It checks the exact capture metadata,
source/crop hashes, rectangle and current client layout; then uses the
hash-pinned 0.39.4 red-bar reader. Its report never enables healing or G2.
Three focused metadata/hash/traversal checks passed locally. A separate synthetic
check on Alienware's installed Python and pinned reader returned 1.0 for a
full 330×17 red band, 0.5 for a half band and unknown for a tiny, blue or
ambiguous band. The staged end-to-end analyzer also accepted a temporary
synthetic 330×17 full-red crop as an **unverified** 1.0 fraction, with healing
and G2 still false; that temporary synthetic capture was removed. No actual
owner UI capture has arrived, so a live HP reading,
full-health calibration and smart heal are unverified.

## Copied low-level camp spokes — 2026-11-13 17:16 CST

**VERIFIED offline, no game input:** The pinned 12-unit GFay orc-camp ring
has six copied graph points. Five direct spokes stay in ground polygon 18960,
match their requested endpoints in XYZ and pass sampled lateral strips plus
the copied-client BSP at ground and ground+1. The sixth crosses polygons
18960→18959 and remains unselected. Private reviewed artifact SHA-256
`4941f6517d3aec4a0b236779774db89a08d8942c51a748a4699624d6934936eb`.
The pinned 12-unit, 12-angle Butcher Kaladim-yard ring has 12 direct spokes
in polygon 21947; each matches its requested XYZ endpoints and passes the
same copied strip and BSP checks. Seven spokes change anchor height by more
than the six-unit diagnostic band, from about −10.12 to +9.19 units. Their
sampled local grade passed the current diagnostic limit, but no client climb
or camp safety has been observed. Private artifact SHA-256
`b1971335c3591d2600139d480c26edc3dd49e3e3e79f4f357a7a1b7f9d7086b2`.
The new offline tool checks both XY and Z snap drift before a local candidate
can pass, rehashes helper/mesh/archive inputs after the run and keeps the
copied guide marker unverified. Actual mobs, dynamic obstacles, aggro,
incoming attacks, player presence and live movement remain unverified. F11
stays disabled.

## Low-level copied camp rings and staged Butcher route — 2026-11-13 17:07 CST

**VERIFIED offline, no game input:** A 249-ground-polygon Butcherblock
Kaladim-yard→GFay detour selected a complete portal sequence in a bounded
153.29-second select-only run: 320 turn checks, 355 unique strip checks.
Selection artifact SHA-256
`5c7babe22742d9d1c9ae4d293e2f0a9f52ace21bd8687702260f1cedbd70fad8`.
The independent, hash-bound whole-strip recheck passed all 249 segments in
90.57 seconds; artifact SHA-256
`52d9ef886c7df92b6908c94a83439e32edd74757555c27b8fda87c9f6d415592`.
The full copied-client BSP scan then passed 249 segments at detail ground and
ground+1: 560 spans, zero labelled, unknown or unsupported spans. Its private
artifact SHA-256 is
`bace97b411ee5ce5f54f9b38b534b93aacfdc542991500fc57d7a011e6ef3e90`.
The hash-pinned minimal detail view's area, face offsets and face slices
matched the owner's full helper loader on all 249 selected polygons in a
separate read-only comparison. Two earlier full-loader BSP runs timed out
without output under heavy devbox load; the reduced view completed the full
route. These results clear sampled static strip and BSP geometry only.
Dynamic collision, actual camp/zone arrival and client movement remain
separate gates.

**VERIFIED copied helper ring diagnostics:** The default 54-unit GFay orc
ring returned six graph-reachable points, two with >6 units anchor-height
change; artifact SHA-256
`23977ff5f55329364c4e39bdc5390bff54a5b6a4ad320d8f0986bf3c8581fd18`.
A 12-unit GFay ring returned six points with height changes within about
2 units; pinned-source artifact SHA-256
`3dbcae10be19ee142b10e691dc0a54a25bca1a120e747241b75b57cc94babd27`.
The default 54-unit Butcher yard ring returned four points, all with >6 units
height change; artifact SHA-256
`9a2b603a2a38082ac370587cdf672cc7020323869024de2ca7bb60cd6443079e`.
A 12-unit, 12-angle Butcher ring returned 12 graph-reachable points, five
within the same 6-unit diagnostic band; artifact SHA-256
`12c8575ed3f9075ba1518549b44bf2cb0549ccfae7a36fdad9ae29839399cf78`.
Three of those short points (returned indices 2, 7 and 8) lie in one copied
polygon each and passed one-segment lateral strips and client BSP scans at
ground and ground+1; artifact SHA-256
`65fb89f85ded580778f6c56882a8c462fc8b664b3cc525dced8e51a67b9e5458`.
The guide markers are approximate; none of these points has live mob, aggro,
dynamic obstacle or movement acceptance. The 6-unit height band is a
diagnostic threshold, not a proven client climb limit. F11 remains disabled.

**VERIFIED focused source check:** The lateral strip now reuses detail heights
already checked by its centerline auditor. Thirty-nine focused portal,
strip and selector tests passed; 12 saved GFay strip decisions and sample
counts matched the previous implementation. That loaded-machine comparison
did not establish a speed gain. The separate new BSP CLI validates route,
selection, full-strip, archive and mesh hashes before writing only an offline
diagnostic outside git. It uses only the copied polygon areas and detail
faces needed by the BSP check, avoiding the full helper's wall/grid build.

**VERIFIED installed manual only, live stop not tested:** The Alienware
`everquest_manual.txt` SHA-256
`d106f7f7d97093b1ae343ef24f8741ce64c3631981bf17995ca059927caf9290`
describes `/attack` as a toggle, and `eqmanual_supplement.txt` SHA-256
`789cf9c54fdf523be8a865ac020cb97efaf51844b8ad33e3fe0fde2549f74ca0`
describes the Attack action as a toggle. The installed `eqstr_us.txt`
SHA-256 `0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde`
contains exact ON/OFF messages. The owner trace links two rejected replies
to attempts to send `/attack off`, without proving the exact delivered text.
Bare `/attack` and a fresh ON→OFF acknowledgment must be tested by the owner
before any full-auto native-melee stop; never retry an unknown toggle.

## Read-only G2 UI capture and Unrest water check — 2026-11-13 16:44 CST

**VERIFIED static client layout, no game input:** The owner preview 0.39.4
`UiLayout.load` against the Alienware's installed Legira UI INI resolves
`Player_HP` to `(1966,693,330,17)` at 2560×1600, while the previously saved
HP crop `[1963,661,2301,712]` starts 32 pixels higher and spans 51 pixels.
That mismatch plausibly explains `hp=null`; a live crop and HP reading have
not confirmed it. The same layout places `Player_Mana` at
`(1966,713,330,17)`, `PW_CombatStateAnim` at `(2289,665,16,33)`,
`TargetWindow` at `(1668,1256,375,279)` and `MainChat` at
`(91,1269,657,280)`. The client XML defines chat input, attack indicators
and combat state widgets, but the saved INI/XML does not reveal live focus,
target, melee state or incoming attacks. Project 0.41.34 adds an owner-run,
read-only focused-window crop tool pinned to the staged preview's source
hashes. Version 0.41.35 tightens capture timestamps and keeps output under
the private G2 observation store. Its help/import smoke passed; no live
screenshot has been captured by this release and no G2 safety flag is
accepted. Hashes of the client's saved UI layout files are recorded after
capture, not misrepresented as verified active-state evidence.

**VERIFIED copied-source BSP diagnostics, not client movement:** The Unrest
entrance route's second funnel segment is water-labelled from mesh ground
through +1.5 height and clears at +1.75. The WLD's `missing BSP child` is
unclassified, not evidence of dry terrain. Polygon 3083 is a dry-graph cut;
a local upper-edge crossing is dry and passes a copied-mesh strip, but sampled
continuation sections toward the yard are water-labelled at ground height.
There is no accepted dry continuation, actual water behavior or Unrest route.
F11 remains disabled.

## Bounded earlier-portal repair — 2026-11-13 16:37 CST

**VERIFIED offline, no game input:** Version 0.41.33 lets the copied-ground
selector revisit up to eight preceding portal choices when the current
polygon has no connected incoming strip. A synthetic four-polygon case that
cannot pass with only adjacent repair now passes after revisiting one earlier
portal; no result sets `route_accepted` or `real_client_accepted`. The repair
count remains bounded at 32, and the existing wall-time, turn, strip and
sample caps still apply. Fifteen focused selector tests passed.

On the copied Unrest entrance→yard corridor, a depth-4/16-round diagnostic
stopped at polygon 3083 with `strip_repair_round_budget_exceeded`, private
artifact SHA-256
`06a2a46adedecd6d6db50898c1b15c94919be48d528be1065fb0d05431293ff7`.
Depth 2/16 rounds reached polygon 1605 before its repair-round cap, artifact
SHA-256 `c0847a39c4617a22161b7d74859a4b6d3a66060bc541b7bc8aadec71812a00d8`.
Depth 2/32 rounds still stopped at polygon 1605 with
`no_sampled_strip_through_polygon` after 195 turns, 238 strips and 27.23
seconds, artifact SHA-256
`afba521ddbaca9271774583a4e8106e4bf8cd33b2bdd4e9a7915448141261e7d`.
A direct local midpoint strip through polygon 1605 passed, so this failure
may reflect an earlier connected-choice limit rather than impassable terrain.
The separate copied BSP water/unknown spans already block this route.
No complete selected or live path exists; F11 remains disabled.

## Retained Cauldron and Unrest navmeshes, offline route gate — 2026-11-13 16:31 CST

**VERIFIED read-only owner-helper copy, no game input:** The Alienware helper
store `~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store/` already
contained Cauldron and Unrest meshes. Its six manifest, report and mesh files
were copied to the matching approved private devbox store. The Cauldron
manifest SHA-256 is
`7fa85bdeb68e8b1ab66b6cbd30ff53dd2702a1ac15580c4477ea001637f05146`,
report `60296d77ac73393a285aa55ee5935174d5af7562f8a81ce68e4446efee5c88f8`
and mesh `884bb7c888aa25cfce2286053ab437facdd5e979fb5227da6c066208c8b77a29`.
The Unrest manifest SHA-256 is
`8224bd5a1c6dbf721bd801a4310148fc6f472b9ee9cab687078a28f883f31786`,
report `1210dc41f493be0d1862ccfd143de92f5aeb9c513f0fbd34a403c9b692ffecc2`
and mesh `2b8fdb3f54078a3977e04df46e69b53d41a72ab56c4783cfe28334e08d4bdace`.
Each manifest's mesh hash matches its copied mesh; each source archive hash
matches the corresponding copied owner-client archive listed below. The
Cauldron manifest reports 14,832 polygons, 3,099 water-area polygons and
275 Recast warnings whose locations/types are not retained. The Unrest
manifest reports 3,254 polygons, 99 water-area polygons and zero warnings.
These reports are copied bake evidence, not real-client acceptance.

**VERIFIED dry graph queries, not strips:** In Cauldron, the ground polygon
beside the Butcherblock zone line and the one beside Unrest share a dry
component. A water-forbidden query returned a 364-polygon, 6,665.98-unit
graph path with no water or zone-line polygons. Ten of its polygons have
reported slope >75°; two have center clearance <3 units. A bounded graph
search found that every ground-only path between these endpoints crosses at
least four polygons violating those thresholds. These polygon-wide metrics
can overstate the actual crossing difficulty, but no safe strip has passed.
The private dry artifact SHA-256 is
`2b102f439b7cb10029aefc9b06af99d853c44a86f75835f9edd67e1ba3666a5f`.
A BSP scan of only its 81 funnel segments, at copied path height and +1,
found 210 spans with no labelled or unknown intervals; it did **not** scan
every polygon strip. That diagnostic artifact SHA-256 is
`c11d8f54e97927aecf4b804598ebbca63e64a0da0db91f30dfaf28323a68555b`.

In Unrest, a dry ground query from a polygon beside the Cauldron zone line
to the prior guide's yard marker returned 120 polygons, 1,117.93 units,
maximum copied polygon slope 37.43° and minimum center clearance 1.26 units.
Its private dry artifact SHA-256 is
`94d90612bea9906505f99d8628c10c6dba65f0b91666896f85afcfb7b0b0862d`.
The bounded portal selector stopped at polygon 3083 after 145 turn and 49
strip checks with `no_sampled_strip_through_polygon`; it saved no accepted
points. Its artifact SHA-256 is
`c4960c5282f0f5a2ee77f1f9d5eef5bf959192993f021ac23d97572f73f7cb05`.
Polygon 3083 is a flat, narrow ground-graph cut near the entrance; excluding
it disconnects that entrance pocket from the yard in the copied dry graph.
It is **not** proven impassable: a direct local check through 3083 passed
with incoming portal fraction 0.70 and outgoing fraction 0.65 at 1.2-unit
half-width and grade 1.0. The failure is in finding a connected sampled
choice sequence under the selector's default repair limits. Version 0.41.32
exposes bounded candidate (1–13) and repair-round (0–16) limits for offline
diagnosis. One expanded run under heavy devbox load stopped earlier at
polygon 1504 with `selection_work_budget_exceeded` after 72 turn checks and
zero strips, an individual turn-audit time limit rather than a terrain
rejection. Its private artifact SHA-256 is
`395933dd925d263c2a084497744c9cf3f34067fc9b956f0c6ba2399c329d674f`.
Increasing only that per-turn work limit let a second bounded expanded run
pass polygon 3083 and advance to polygon 1605, where it returned
`no_sampled_strip_through_polygon` after 176 turns and 133 strip checks in
7.0 seconds. Its private artifact SHA-256 is
`a229d775e0dd1e10b436dc3732c0edd2a762d0c00021bfd8bae98c05d97ce104`.
This is progress through the copied graph, not a whole-route pass.
The separate final-strip recheck correctly refused this failed selection.
A BSP scan of only the 30 funnel segments found 8 water-labelled and 71
unknown spans (`missing BSP child`) across ground and +1 heights, including
water at segment 2. Its artifact SHA-256 is
`6c82b19afa82592c7618b8c1c4bf20f63d750ebb7db90140846a045f3617801d`.
The mesh's dry-area label and the copied BSP water label disagree there;
at a +2.2-unit height offset, the same segment's water labels disappeared,
but ground-level foot clearance and the real client's water behavior remain
unverified. Their real-client meaning needs review. An Unrest yard→first-floor dry query
returned 59 polygons and 459.46 units, but its polygon slope reaches 89.01°
and center clearance falls to 1.57 units. Its private artifact SHA-256 is
`eb1a52b7808d5394b6947d97f3f8a168beaf555de9db5d5f6a4e500221d6f774`.
No zone transition, camp, live XP, door, water-safe route or movement has
been verified. F11 remains disabled.

## Reproducible later-zone scene command — 2026-11-13 16:23 CST

**VERIFIED offline, no game input:** Project 0.41.31 adds
`--build-later-zone-candidate-scene cauldron|unrest`. It checks all four copied
archive hashes against the owner-client hashes below before composing the
terrain and exact-name placed objects. On the approved private copies, the
Cauldron included and Boundary-excluded commands reproduced the previously
recorded OBJ SHA-256 values `eaa99ae692ce6b1842721ebe774178b4c63b1e9b6b6223f8f0b0e3bbf0d68496`
and `fd88af2865e07a33c057f8cefe729a308b13bcf5b78abbead0d94338d2308bb5`.
Unrest with Boundary included reproduced
`bf136a77bf8df60920ed39991f7edf06cf28efbbc8d1b328902ecd78f40ba64d`.
The Unrest exclude-Boundary option produced identical 32,818-face geometry
with a different comment header and hash
`9572e69924b2e1f3f29571286499a46b6eee03c801c7430e73f3f1e06630260c`.
These commands do not determine collision, water or safe movement. F11 and
the level 13–20 route remain unavailable.

**OBSERVED read-only bake plan, not run:** The retained bounded local baker
`~/.local/share/eql-automation/toolchains/eql-bake-local` has SHA-256
`9e068f54a1a98c0f9ad55b4e2580f811aec581bb6e73022fc57234b27119eb57`.
A 128-unit half-extent (256 × 256 cell) trial around the copied Cauldron map's
Unrest-exit label at WLD XYZ `(-2046.01, -626.98, 89.35)` intersects about
98 provisional OBJ faces. The reciprocal Unrest entrance label near
`(50.16, 325.75, -0.8)` intersects about 159. A future low-load run should
cap one bake at 30 seconds and 1 GiB and compare the Cauldron Boundary
variants before using any tile. The baker lacks BSP water and zoneline area
tagging; its output would still be geometry-only evidence. At 22:23 UTC the
devbox load was 201.94 on 48 CPUs with swap full, so no bake was run.

## Dagnor's Cauldron and Unrest client source — 2026-11-13 16:17 CST

**VERIFIED read-only owner-client copy:** Four archives were copied from the
Alienware's installed EverQuest Legends game root into the approved private
devbox store `~/.local/share/eql-automation/client-data/retail-full/assets/`.
The remote and local SHA-256 values match: `cauldron.s3d`
`a035788d5df592e313d7b2a7998a3ceae300ebe68cf9e837c2509a2cd98b4409`,
`cauldron_obj.s3d`
`b4d59143a630c81b9a9b39156a27854df5c72641e7ad3d93e5fe49ecdc89a686`,
`unrest.s3d`
`e34c4b636d731dbf67dcb5ac028a75ac4e68c9a45a4a6cabd1cdce0f6793df1f`,
and `unrest_obj.s3d`
`5756a96a0c7b4d57f5fac25533871024fdef3eea4eb9ec12b2da655f53f8aaa1`.
Only the approved private copy was written; the Alienware install and prefix
were read only.

**VERIFIED copied WLD inventory:** `cauldron.wld` SHA-256
`031f85a34831af9dc9eddf54e787e8ad07b94945404136271b49ba262adcda33`
has 1,988 BSP regions, 3,975 BSP nodes, 1 water and 3 zoneline type
records. Its 1,043 terrain mesh fragments encode 29,607 vertices and 24,989
triangles, with zero raw degenerate triangles. `unrest.wld` SHA-256
`1516ec497e32e19242a0c89ab4e5ab593e9c2945f4b30637c0c628beb186826c`
has 4,058 BSP regions, 10,585 nodes, 25 water and 1 zoneline type records.
Its 3,198 terrain mesh fragments encode 48,631 vertices and 26,291 triangles,
two raw degenerate. The private region and terrain inventory artifacts have
SHA-256 `9237fcd205058d3ca27b77524182d067efa1ddeb36f010542958d00ce5cafb09`
and `b829198289f7a33ac6e325e9d2bbae0e703c16645cb9a6da5383fb3f402b45c1`.
The copied Cauldron map labels exits to Butcherblock and Unrest; the Unrest
map labels the reciprocal Cauldron exit. These are drawing/label evidence,
not walkable transitions.

**VERIFIED static placement composition, provisional only:** Cauldron's
`objects.wld` has 211 placements, 203 after rejecting 8 dropped-tree Z
sentinels; all 211 exact actor references match 19 model definitions.
Unrest has 164 placements and no sentinels; all 164 match 38 definitions.
Instanced model summaries count 5,035 Cauldron and 9,507 Unrest triangles,
with 4,303 and 7,045 solid-flag faces, respectively. The private placement
and instance audit artifacts have SHA-256
`4cc0d453a79b6b3ad74d3e91bc2e541f806b616f0675b4b8b2b4638efa56e3ef`
and `33b5e60772be481025235c048a09cb4d688b1e9628e75eaa85d94d11519fcb30`.
The provisional Cauldron WLD-XYZ solid-face OBJ has 34,560 used vertices,
28,758 faces and SHA-256
`eaa99ae692ce6b1842721ebe774178b4c63b1e9b6b6223f8f0b0e3bbf0d68496`;
Unrest has 56,951 used vertices, 32,818 faces and SHA-256
`bf136a77bf8df60920ed39991f7edf06cf28efbbc8d1b328902ecd78f40ba64d`.
Both OBJs are outside git under `~/.local/share/eql-automation/nav-candidates/`.
They include Boundary material faces, skip pass-through and zero-area faces,
and have **no verified collision-material behavior**. The separately retained
owner-helper Recast meshes were found and copied later, as recorded above;
they have no accepted water avoidance, dynamic-door behavior, current camp,
transition or actual client movement. No 13–20 route is ready.

**VERIFIED material sensitivity source:** A copied WLD material audit found
2,442 Cauldron terrain solid-flag faces labelled `Boundary`, with no such
placed-object faces. An otherwise identical provisional Cauldron scene that
excludes exactly those labelled terrain faces has 30,396 used vertices,
26,316 faces and SHA-256
`fd88af2865e07a33c057f8cefe729a308b13bcf5b78abbead0d94338d2308bb5`.
Unrest has no `Boundary` faces but has 7,025 solid-flag terrain faces with
unclassified `Unknown:0x80000002` material and 272 solid-flag placed-object
faces with other unknown material values. The private material audit artifact
SHA-256 is `4e48cfeefc3d2d02a99ed22cb3ce5dcd91745f4e7a09e822b92e78a0f9576878`.
The material names and flags do not establish what the real client collides
with. Both Cauldron variants and Unrest remain unaccepted bake inputs, not
walkable routes.

## Butcherblock complex-polygon detour — 2026-11-13 15:58 CST

**VERIFIED copied-data offline, no client input:** Rerunning the 234-ground
camp→GFay bypass through the reusable selector with a 10-second per-turn and
30-second per-segment cap stopped at polygon 49153 after 22 turn checks and
zero strips. Its global 360-second cap was not reached; this was a local
work-limit result, not a terrain rejection. The private artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-bypass-selector-20261113T2156Z.json`
has SHA-256 `6340edceed564ad88f6d631a87856fe255e5b6f4050f0af26037840b0105fe95`.
The earlier final whole-route pass also timed out at the same polygon,
making it an expensive audit location under current devbox load.

**VERIFIED dry detour only:** Penalizing polygon 49153 in addition to the
nine earlier steep/narrow or failed-turn polygons found a 249-ground-polygon
path from the approximate Kaladim-yard guide camp to the GFay ground
standoff. It excludes 49153 and has no copied detail-triangle slope above
75 degrees or polygon-center clearance below 3 units; its maximum slope is
73.92 degrees and minimum center clearance is 3.79 units. The outside-git
artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-complex-bypass-20261113T2157Z.json`
has SHA-256 `4f026d28558afa0f898980d6b30f74decd75f0ceb74ac5c8b937fdbb6602f9a5`.
A bounded selector is running on that detour; no lateral/BSP/live acceptance
follows from the dry path. Its first 420-second pass completed the portal
search after 320 turn and 355 unique strip checks, but had no time left for
the mandatory final whole-route audit. It returned
`selection_work_budget_exceeded`, with no accepted points. The private
artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-complex-bypass-selector-20261113T2158Z.json`
has SHA-256 `dc15a6989b6a04ec253c88a28de99fadfbf8058394e0d291a90108aa0e0cbbc2`.
A bounded diagnostic rerun with source rehash and unverified-point retention
was stopped by its external 460-second timeout (exit 124) before it wrote an
artifact. No result or selected points were retained from that attempt. At
22:14 UTC the devbox reported load averages 243.89, 242.58 and 226.32; a
further heavy rerun is deferred under this measured pressure. The offline
selector now offers a fail-closed `--select-only` phase so a later portal
search can save unverified points before a separate whole-route strip pass.
This code change has a focused synthetic test; no Butcher result from it has
run. F11 remains disabled.

## G2 owner-preview input gate — 2026-11-13 15:53 CST

**OBSERVED source inspection, no game input:** Isolated owner-assist 0.39.4
`rotation_engine.py` already checks focused X11 window identity at lines
224–251 and tracks some evdev keys at lines 708–730 and 832–925. Its input
device discovery only registers devices advertising F8, so it cannot certify
all owner keys or keys held before attachment. Recent chat-key timestamps and
unfinished helper-command state are not an independent chat-closed signal.
Its target/log state cannot prove no current target, and absence of incoming
attack log lines cannot prove combat or incoming attacks are clear within the
G2 observer's 0.1-second bound. `autopilot.py`'s completed G0 measured one
0.15-second pulse, not a speed upper bound. Project
`g2_scene_observer.py` requires a fresh location fix and independent scene
checks; `g2_start_gate.py` additionally requires live alignment and a speed
bound. These pieces are not wired into the owner preview. **G2 and F11 remain
disabled.** A future owner-run test must wait for actual independent UI/device
observations and a bounded measurement release, not inferred clear states.

## Level-7 GFay orc-camp fallback and Butcher route limit — 2026-11-13 15:46 CST

**VERIFIED copied-data offline, no client input:** The existing 0.39.4
`leveling_guide.json` SHA-256
`bfe936da1aec38b37a683af51f0ee4189cd86bcb4a1680deee613c4dfeba77b9`
lists GFay orc camps as a level 6–10 outdoor alternative. Its marker comes
from Brewall-derived map guidance; the owner's earlier `/con` log supports
some listed mob levels, not an exact camp or safe pull location. Starting
from the owner's completed G0 test position, a copied GFay mesh dry query to
that guide marker found 133 ground polygons, length 4,101.80 units, with two
polygons whose steepest copied detail triangles exceed 75 degrees. The private artifact
`~/.local/share/eql-automation/nav-candidates/gfay-g0-to-orc-camp-dry-20261113T2144Z.json`
has SHA-256 `2830b6e3091189a99e67736aa9bc075520851e016e03f1da02007d91365c9bb8`.
Penalizing those two steep polygons found a different 155-ground-polygon
dry path, length 4,095.75 units, with maximum polygon slope 74.74 degrees
and minimum polygon-center clearance 7.64 units. Its private artifact
`~/.local/share/eql-automation/nav-candidates/gfay-g0-to-orc-camp-repair-20261113T2145Z.json`
has SHA-256 `18fdc7d2b051d0920bd25259fea259acf7034816d5547cf2d3dec460ed47e20a`.
**VERIFIED sampled static corridor:** A bounded rerun of the repaired GFay
path passed 169 portal-turn checks, 175 unique polygon-strip checks and its
final whole-route recheck in 224.827 seconds, using a 1.2-unit half-width
and grade limit 1.0. Its private selector artifact
`~/.local/share/eql-automation/nav-candidates/gfay-g0-to-orc-camp-selector-20261113T2150Z.json`
has SHA-256 `ecc62e51b9b16a2fee2e0050bda864e77ab73d74a6bdcd18f347a477c148b36f`.
The earlier 3-second per-turn setting stopped at polygon 28793 on a work
limit, not a terrain rejection; its artifact SHA-256 is
`46c29a3dc80fa19d577620482c7ae1858c93a95ff528f484852c375a1d520901`.
Tracing the 155 selected ground segments at copied mesh height and height+1
through the copied GFay BSP yielded 366 spans and no labelled, unknown or
unsupported-height intervals. The private BSP artifact
`~/.local/share/eql-automation/nav-candidates/gfay-g0-to-orc-camp-bsp-20261113T2154Z.json`
has SHA-256 `7673e2bd887d9997981cb4accb588e8a5c0732fc3e541e5e408d73926dfbd499`.
This is an offline static candidate from the G0 position, not proof of a
current live route. The G0 position is no longer fresh; the actual camp,
dynamic obstacles, aggro, follower error and real movement remain unverified.
F11 remains disabled.

**VERIFIED bounded work limit:** On the earlier 234-ground-polygon Butcherblock
camp→GFay bypass, the cached selector reached its final whole-route pass
after 240 turn and 260 unique strip checks. The complete pass stopped at
polygon 49153 because an individual segment reached its 10-second work
limit; elapsed total was 187.163 seconds within a 360-second global limit.
The private artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-bypass-cache-selector-20261113T2142Z.json`
has SHA-256 `f5b1bb0d67bd047d19bae620163ad6754f8c24e72084dc39efcfcf919cb9d255`.
This is not a whole-route geometry pass or real-client acceptance.

**OBSERVED warning-provenance limit:** The retained Butcherblock mesh,
manifest and report contain only the aggregate 1,180 Recast warning count;
no retained per-warning type, tile, location or baker stderr log was found
in the approved store. The matching retained baker hash is
`072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44`.
Those warnings cannot be classified or mapped to this route from retained
artifacts. They remain an acceptance limitation; no inference is made from
the warning count alone.

## Owner-run G0 and retained Butcherblock mesh — 2026-11-13 15:27 CST

**VERIFIED owner-run observation:** Blizz launched isolated assist preview
0.39.4 in measurement mode on his Alienware and confirmed he saw the
character stop after its short forward pulse. The helper trace
`~/eql-g0-trace.jsonl` SHA-256
`ec233e53ab37ef0245d78f98529ea264055c9c75b5a916f4d36a8c6171e3d7b1`
has one `ap_stop_check_result` with `outcome=observed_stop`, all four
preflight/post-release location fixes, 0.1508157-second hold, 4.6407004
units displacement, and 0.0 XY/Z drift between post-release fixes. One
earlier focus attempt did not start; the successful attempt then ran. This
clears the G0 stop observation only. One pulse does not establish a verified
speed upper bound, live log-to-WLD alignment, G2 scene guards, follower
error or any route. The lead sent no client input.

**OBSERVED same-session log/mesh comparison:** The owner game log records a
fresh `You have entered The Greater Faydark.` at 15:17:07 CST, followed by
four G0 `/location` replies at 15:22:47–15:22:50. A read-only snapshot of
the appended G0 trace is under
`~/.local/share/eql-automation/owner-traces/g0-20261113T2122Z-f5d07cd4.jsonl`,
SHA-256 `f5d07cd4d424bad8b0f494a85cbf389823ee2c3445e497165a20aad9aca1ecc8`;
it retains the same single G0 result as the earlier trace hash. All four
fresh log XY points located directly on area-63 ground in the hash-matched
copied GFay mesh, with 0 XY snap distance and raw-character-Z minus mesh-Z
offsets 2.06549–2.08488 units. The private diagnostic
`~/.local/share/eql-automation/nav-candidates/g0-gfay-mesh-alignment-20261113T2132Z.json`
has SHA-256 `083b8effbef8966877d01e21f68b666c814a81bd706156999a1d8fcf64b3d06e`.
This supports the copied coordinate convention at the measured spot; it is
not a fresh G2 start or independently certified speed upper bound.

**VERIFIED offline fresh-start strip, incomplete turn:** The G0 final XY
remained in GFay ground polygon 32475, the same start polygon as the earlier
selected GFay→Crushbone ground corridor. Replacing only that corridor's
historical first point with the G0 final point passed 388 first-strip sample
locations. The separate first-portal turn recheck exhausted a 5-second work
limit after 44 samples on this loaded devbox. The rest of the corridor was
unchanged from its earlier offline candidate, but no new whole-route recheck
or current-position route acceptance follows. The private artifact
`~/.local/share/eql-automation/nav-candidates/g0-gfay-crushbone-first-strip-20261113T2133Z.json`
has SHA-256 `f2b82c64ac131c29d7f55ea89b66a2ff51efb45a4d57747424f8be372654359b`.

**VERIFIED retained current-tool artifact:** The Alienware's existing
`~/.local/share/eql-automation/navmesh/nov12-7e3cd28-store/butcher.npz`
was copied read-only to the same private devbox store path; both copies have
SHA-256 `4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde`.
Its manifest SHA-256 is
`64f3b3d8673a61424268172b3b9c6989921c77e49d5b0f4d55fa034f2d8ef792`
and its report SHA-256 is
`1ee7d3bfd81ff4e10af638082b9e5c7b46b2b64de99c3f5ca1367915574c82af`.
The manifest's three source archive hashes match the copied client archives:
`butcher.s3d` `af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839`,
`butcher_obj.s3d` `ad4c886395c9af7f3de17be1c1a24785e295f892097b8e5785eec670a089c047`,
and `butcher_2_obj.s3d`
`cb5cabede79b53f9b884c15712ec07225f5ca81e1093be36f7d3d12b8ea03ece`.
The manifest reports 56,785 nav polygons and **1,180 Recast warnings not yet
classified**. This is a different mesh and hash from the November 6
historical Butcherblock proof; it does not retroactively verify that proof.

**VERIFIED offline dry route, no game input:** From the prior guide's
approximate Kaladim gate-yard camp coordinate `(2700,-650,9.8)` to the
copied mesh's GFay trigger, a water-forbidden query found 255 polygons.
Penalizing seven steep or narrow polygons across three bounded retries
produced a 239-polygon alternative with 236 ground polygons, maximum copied
polygon slope 74.24 degrees and minimum polygon-center clearance 3.0 units.
The initial dry-query artifact SHA-256 is
`7e7077c7b8c8c5e7a4bacc3ea2f6c5e07f3ec2a10a56043b23a076abe127d1df`;
its private path is
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-dry-20261113T2123Z.json`.
The final repair artifact SHA-256 is
`57b037d85ef9d5723e0c6179951fbc3a90f5d677b8bcd8060b88aef2e31000d8`.
It is under
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-repair2-20261113T2125Z.json`.
Strict detail heights and copied BSP tracing over the 236 ground segments at
ground and ground+1 height returned 530 spans with no labelled or unknown
ones; the private BSP artifact SHA-256 is
`f6591ed1ab789ca0ea1e7d2342a9abc93eae375b17eeb295ec8d7c9ed928c5d3`.
Its path is
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-bsp-20261113T2127Z.json`.
This checks static labels along a midpoint corridor; the lateral strip,
zone trigger, current character position, dynamic hazards and actual motion
are unverified. The guide camp coordinate is approximate. F11 stays off.

**VERIFIED bounded selector rejection:** The 236-ground-polygon repaired
corridor reached directed edge 37736→37733 at path index 67, then returned
`no_sampled_turn_disk_candidate` after 92 turn checks and zero strip checks.
The private selector artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-selector-20261113T2127Z.json`
has SHA-256 `f90684524bda5906343e102e421ecfd70de35441758af92dd93c6c44122d28c9`.
At the midpoint the copied nav detail drops about 0.628 units over a
0.6-unit radial sample, narrowly above the diagnostic grade-1.0 limit.
This conservative rejection does not prove the client cannot traverse the
edge. Source material remains unresolved; the alternate below avoids it.

**VERIFIED copied-mesh alternate:** With that edge's two polygons and the
seven prior steep/narrow polygons penalized, a water-forbidden dry query
returned 237 polygons, 234 on ground. It excludes both rejected-edge
polygons. No ground polygon has slope above 75 degrees or center clearance
below 3.0 units; observed maxima/minima are 74.09 degrees and 3.7858
units. The outside-git artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-bypass-20261113T2130Z.json`
has SHA-256 `b1da160d7b517cd9d1a54a8243504ad0eabc9fa3085d08d1e3f4cd60fd544afd`.
Its portal turns, lateral strips and client movement still need checks.

**VERIFIED offline selector work accounting:** On that same 234-ground-polygon
bypass, the pre-cache selector spent 180.108 seconds, 240 turns and 358 strip
checks, then exhausted its global time budget at polygon 38947 (route index
66). The private artifact SHA-256 is
`44c4d9277ce85f8599b4b829e77d8a9bb67a18ebe57c90225d48b36189377794`.
With repeated `(polygon, entry, exit)` strip checks cached, the same
180-second bound spent 240 turns and 182 **unique** strip checks and reached
polygon 14525 (index 155) before another global time limit. Its artifact
`~/.local/share/eql-automation/nav-candidates/butcher-kaladim-to-gfay-bypass-cache-selector-20261113T2135Z.json`
has SHA-256 `e72b0ec0ab35aca62c4d04eaf24a2899949d88353f6ae2847e48c611595e57c4`.
The cache preserves the global sample/time caps and the final whole-route
audit. Neither timed-out run is a geometry pass; a longer bounded recheck is
underway. The copied mesh's 1,180 warnings remain unclassified.

**VERIFIED code smoke:** The new `ground_bsp_route` helper rejects missing
detail, non-ground areas, labelled or unknown BSP spans, and incomplete BSP
partitions. Six focused tests pass. Replaying the GFay→Butcherblock selected
ground corridor through it yielded 114 static BSP spans, no labels or unknowns,
and a candidate-only result; its outside-git artifact SHA-256 is
`f7f21ce0fd86a0da77d67dc0c2979e8b8aa7a0ac9fdd0c784d3364c0354e8833`.
No helper result accepts client movement.

## GFay to Butcherblock ground approach — 2026-11-13 15:15 CST

**VERIFIED copied-data offline, no game input:** The copied GFay map label for
Butcherblock and the hash-matched GFay mesh produced a 55-polygon dry query
from Legira's **historical**, not current, `/location` (raw log
`Y=-1807.35, X=1786.14, Z=66.45`) toward a sampled area-5 trigger point.
The first 52 ground polygons end at standoff
`(2669.644124, -1653.812419)` in WLD XY, before the three area-5 polygons.
The dry-query artifact is
`~/.local/share/eql-automation/nav-candidates/gfay-butcher-dry-route-20261113T2108Z.json`
SHA-256 `5761ec6d3a9b8676a6ca676d302276c0c28cff0351c9c7ffe0614727b6466bc0`.
The ground prefix passed 87 sampled turn checks, 103 sampled strip checks and
the final whole-route recheck in 43.42 seconds with 1.2-unit half-width and
grade limit 1.0. Its selector artifact SHA-256 is
`a32246bd1a848e62329fb8372102b638734144094b2893ac5d1eb6fbabfce4b4`.
The earlier 10-second per-segment run stopped on a work limit at polygon
33468; this bounded extended run resolved that limit, not a client traversal.

**VERIFIED copied BSP diagnostic:** Strict detail-triangle heights existed at
both ends of all 52 ground segments. Tracing them through the copied GFay BSP
at ground height and one unit above yielded 57 spans at each height, with no
labelled water/zoneline spans and no unknown spans. The private artifact
`~/.local/share/eql-automation/nav-candidates/gfay-butcher-bsp-audit-20261113T2114Z.json`
is SHA-256 `d073c2e03ee85c1b288b028569c9986e026e7cf462a16d8d526f3ffe76843591`.
It binds the selector, dry route, mesh, archive and WLD hashes. This checks
only copied static BSP labels along the sampled ground path. Current position,
doors, mobs, follower error, motion stop, trigger entry, Butcherblock arrival
and real-client movement are unverified. No F11 edge is accepted.

**VERIFIED bounded bake attempt:** A one-thread, low-priority full
Butcherblock bake from copied archives was stopped by its 120-second timeout
under measured heavy devbox load. It produced no mesh under
`~/.local/share/eql-automation/navmesh/butcher-full-provisional-20261113T2107Z`.
This is a resource/time limit, not evidence that Butcherblock terrain is
unroutable. A small FAYHOUSE tile remains the only retained provisional
Butcherblock navmesh sample. No install or game input was changed.

## Isolated Crushbone Boundary and detail sensitivity — 2026-11-13 15:04 CST

**VERIFIED copied-data offline bakes, no game input:** The retained November
`eqlnav_bake` binary SHA-256
`072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44`
matches the original mesh's embedded baker hash. The copied archives yielded
the original 26,570 triangles and 5,586 BSP classifier nodes. An exact
ordered subset of the Boundary-excluded OBJ's terrain triangles selected
16,863 of the original 20,920 terrain triangles; 4,057 Boundary faces were
removed while all 5,650 original placed-object triangles were retained.
This avoids the provisional OBJ's different object placement convention.
The same original parameters and one low-priority thread produced a
55-tile, 5,142-polygon Boundary-excluded mesh SHA-256
`0602118e61708bfc7312f8f7e82ba908b05f85362b2e5fdf5c830c63b5b1cccf`
with zero Recast warnings. At both cut edges its exact XY detail heights and
all 13 grade-1.2 turn results matched the original included-Boundary mesh.
Boundary sky faces alone did not cause these sampled grade failures.

**VERIFIED sensitivity, not acceptance:** Reducing only
`detail_sample_max_error` from 1.0 to 0.5 with Boundary included left the
first cut's failed offset at Z=0.944 and passed zero of 13 sampled turns;
that mesh SHA-256 is
`f3294a5b2c0c27e7137a34b766aa7f737d53dbd00cea201391626af5fffe0893`
and emitted 13 Recast warnings. At error 0.25, the same offset was Z=0.163
and all 13 sampled turns on 3248→3247 passed with Boundary included and
excluded; those meshes have SHA-256
`ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56`
(21 warnings) and
`a99f2b7c2fd8465cd5f87d70bbd28a4de01b876579cdb43347fb97cb028b4130`
(20 warnings). The 658→623 cut passed zero of 13 turns in all five variants.
The full comparison artifact outside git
`~/.local/share/eql-automation/nav-candidates/crushbone-boundary-detail-sensitivity-20261113T2103Z.json`
has SHA-256 `6f223b5aa21a1f1cf34f27fca9dc521b95ac9b6116bc3e84c0dd2dd0b8c0f4c1`.
The finer bakes' warnings are not yet classified. No variant has accepted
strip/camp travel, dynamic obstacles, client height, zone arrival or real
movement. F11 remains disabled.

## Crushbone cut-edge source and bake height mismatch — 2026-11-13 14:56 CST

**VERIFIED copied data, offline:** At the midpoint and first rejected
0.6-unit turn offset of both cut edges, the included provisional WLD OBJ has
two covering terrain faces: flat Z=0 `Diffuse` / `CLOVEGRASS_MDF` and a
Z≈624–626 `Boundary` / `CRUSHSKY_MDF` face. The two flat faces map to copied
`crushbone.wld` SHA-256
`ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1`.
The Boundary-excluded OBJ SHA-256
`8dd77042278bd9821d3d95ed2cefd4440070e4617201d5eb9cba1818794d372b`
has exactly one covering face, Z=0, at each of those four XY points. The
current included-Boundary navmesh detail rises from 0.163 to 0.944 on
3248→3247 and from 0.350 to 1.117 on 658→623 over the sampled 0.6-unit
offset. The diagnostic artifact outside git
`~/.local/share/eql-automation/nav-candidates/crushbone-cut-source-height-20261113T2055Z.json`
has SHA-256 `587bae81e4bbb6729b975d5714aafd4f328006eed51cbf4143f8d02fb82592d8`.
The source-to-bake discrepancy is a concrete reason to review the bake; the
OBJ remains provisional collision input, and these four samples do not
establish playable grade or client position. F11 remains disabled.

## Crushbone copied-ground two-edge cut — 2026-11-13 14:53 CST

**VERIFIED offline, no game input:** On copied `crushbone.npz` SHA-256
`bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`,
the directed crossings `3248→3247` and `658→623` form a two-edge cut between
arrival polygon 2249 and Slaver goal polygon 3805. Blocking either edge alone
leaves a ground-graph path; blocking both reaches 1,375 polygons from the
start and not the goal. At diagnostic grade 1.2, all 13 portal fractions from
0.20 through 0.80 fail the turn-disk audit on both edges: the first has 13
radial-grade failures; the second has 4 seam-clearance, 7 radial-grade and 2
angular-grade failures. The outside-git evidence artifact
`~/.local/share/eql-automation/nav-candidates/crushbone-two-edge-cut-20261113T2052Z.json`
has SHA-256 `5bce35b185cd6497fb0dbdf55b08691ff6548067ede296855a9d7a0f31f843af`.
This rules out an alternate *sampled graph corridor under the current copied
mesh and conservative audit*; it does not prove live client terrain is
untraversable. Playable grade, WLD-to-bake height, follower error and movement
remain unverified.

**VERIFIED private staging:** Project 0.41.23 source-only archive from commit
`26870d8` has SHA-256
`7d067a46ca5ef429aa26edeb07dafdfdbae61ec612f1bb190c3ed312084977d6`.
It was copied to the Alienware private EQL store at
`~/.local/share/eql-automation/owner-tools/0.41.23`; the remote archive hash
matched, extraction succeeded, and the `--demo-navigation` startup smoke
reported `simulation_only=true` and `no_game_input=true`. No client input or
install changes occurred. Owner preview 0.39.4 remains the assist runnable.

## Final-query deadlines in offline turn and corridor audits — 2026-11-13 14:50 CST

**VERIFIED offline, no game input, project 0.41.23:** The standalone
turn-disk and fixed-corridor samplers now reject a sampled candidate if the
last geometry query runs past their wall-time budget. Deterministic clock
regressions cover both final-query cases. Forty-four focused portal, strip,
turn and corridor tests passed. This changes only offline diagnostics and
accepts no live route.

## Local surface ambiguity and Crushbone grade sensitivity — 2026-11-13 14:40 CST

**VERIFIED offline, no game input, project 0.41.22:** The selector now treats
`spatial_candidate_budget_exceeded` and a seam's local sample limit as
rejected portal fractions rather than global exhaustion. Only the turn's
elapsed-time cap aborts that phase. A segment's local spatial/sample limit
also remains a rejected candidate; the global sample/time/check caps still
fail closed. An explicit `maximum_grade` now reaches the turn-disk check,
candidate polygon strips and final whole-route strip audit. Seventeen focused
selector/strip/turn tests passed, including a synthetic 1.05-grade corridor
that fails at the default 1.0 but passes an explicit 1.2 while remaining
`route_accepted=false` and `real_client_accepted=false`.

**VERIFIED budget correction:** An independent review reproduced a false
sample-cap pass: centerline locations were missing from strip counts, turn
locations were missing from the selector total, and three early surface
failures were off by one. The current code counts all tested centerline,
center/side and turn-disk locations, reserves each turn's 64-point maximum,
and constrains each strip call by its remaining shared budget. Seams are
bounded separately by turn/segment counts. Thirty-five focused portal,
strip, turn and surface tests passed. Earlier GFay artifact sample totals
were computed by the older undercounting code; their sampled geometry
claims required a recheck under this accounting. A hash-matched copied GFay
ground corridor recheck completed in 88.897 seconds with 243 turn checks and
270 candidate strip checks; it again returned a sampled candidate only. Its
outside-git artifact
`~/.local/share/eql-automation/nav-candidates/gfay-selector-sample-accounting-20261113T2044Z.json`
has SHA-256 `9375be63e37a322ade3a3789810682afd82949ca4169a5ae40d970a383512354`.
The source corridor artifact has SHA-256
`41b01005b619c37a1170bc657af2ef829031d584978fe28bae98953193d98477`
and the copied mesh SHA-256 is
`5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9`.
This recheck began before the final pre-call sample-cap guard was added, but
the new guard only constrains work when close to the shared cap. The
GFay→Crushbone trigger, arrival and client movement are still unverified.

**VERIFIED deadline correction:** A read-only review found that standalone
segment and whole-route strip audits could finish their last clearance query
after the time limit and still return a sampled candidate. Both now check
elapsed time immediately before a positive return. Two deterministic
deadline regressions and the other focused geometry checks passed (37 total).

**VERIFIED copied Crushbone mesh:** On the saved 80-polygon corridor, the
selector still finds no sampled turn-disk crossing at polygon 3248 under
maximum grade 1.2 after 42 turn checks. The diagnostic artifact outside git
`~/.local/share/eql-automation/nav-candidates/crushbone-grade-1p2-selector-20261113T2040Z.json`
has SHA-256 `291ed6a6fa9b2281c695650c236727dc2e96be57da02a45cf51201d7fe28ddf5`.
Blocking 3248 leaves a 176-polygon connected ground graph, but the bounded
selector on that bypass stops at polygon 441 with grade 1.2 after 129 turn
checks, then at polygon 468 with grade 2.0 after 142 turn checks. Both stop
before strip search. Their artifacts have SHA-256
`4f1df4a1130ac8d8c391bdc09a794275e3bd90292426153e68381ea919734e2`
and `10c91b323696a59c6bef536cbc59e0aedaa360cfd93115a823f6c60181eb0908`.
The mesh SHA-256 remains
`bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793`.
Grade 2.0 is a sensitivity parameter, not a measured safe player slope.
The actual follower error and current character position remain unknown;
neither route is accepted and F11 stays disabled.


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
