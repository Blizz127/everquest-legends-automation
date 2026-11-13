# STATUS

Updated 2026-11-13 15:19 CST for coordinator task `829a00229b29`.

- Last owner-reported real-client level: 7 for Legira in Greater Faydark; no lead-controlled login or automated level gain verified. A later level has not been observed by the lead.
- Owner feedback check: at 14:54 CST, neither `~/eql-assist-trace.jsonl` nor `~/eql-g0-trace.jsonl` was found on Alienware. Legira's real-client log was last checked at 14:24 CST and then still had mtime 09:31:50 CST. No 0.39.3/0.39.4 live result is available.
- Owner agreed to run the supervised 0.39.4 G0 movement-stop check; its result
  has not yet arrived; both expected trace paths were absent at 15:19 CST.
  No new character level, XP or death observation was
  received. The new [1–20 route record](LEVEL_1_20.md) prioritizes
  Butcherblock → Crushbone → Unrest by observed level, with all route legs
  still unaccepted for F11.
- VERIFIED offline: a hash-bound GFay → Butcherblock 52-ground-polygon
  standoff approach passed 87 turn checks, 103 strip checks and a whole-route
  recheck. A copied BSP trace at ground and ground+1 height found no labelled
  or unknown spans over its 52 segments. It used a historical Legira start
  and stops before the zone trigger; no game movement or transition is proven.
  Artifacts/hashes are in FINDINGS.md. A bounded full Butcherblock bake timed
  out at 120 seconds under heavy devbox pressure and produced no mesh.
- Private publish: source-only project 0.41.23 commit `26870d8` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.23`
  outside the game install. The local and remote archive SHA-256 matched:
  `7d067a46ca5ef429aa26edeb07dafdfdbae61ec612f1bb190c3ed312084977d6`.
  Its lightweight remote `--demo-navigation` startup smoke passed. This
  archive does not enable F11 or replace owner-run assist preview 0.39.4.
- Private publish: source-only project 0.41.24 commit `2bf41fa` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.24`.
  Remote SHA-256 matched local
  `f588185e3f1760f21c8dfa3c3e6a45ef2cf7bb1778567f6b808a1c6143e8ec5f`;
  the remote `--demo-navigation` smoke passed with no game input. This build
  records offline rebake evidence; no live travel feature was enabled.
- Private publish: source-only project 0.41.25 commit `dc02181` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.25`, outside
  the game install. Local and remote archive SHA-256 matched
  `d131e77caf2dbb2e560eb1f80dc7c47958628205189e1cc911dd3a359ae9a567`.
  The remote `--demo-navigation` startup smoke and trace summarizer `--help`
  passed; neither sent game input. The owner preview remains 0.39.4 and F11
  remains disabled.
- Real-client XP / XP per hour: n/a. Current-level XP fraction / percentage points per hour: n/a. Deaths: n/a (no observed full run). Camp: Greater Faydark current zone; Slaver Caves (west) is a planned level-7 destination, not an accepted active camp. The copied owner log reports one item did not fit and food/drink out; a later belt sale does not prove bag capacity was restored.
- Build: local source 0.41.25 (G0 trace metrics and 1–20 route record) plus an isolated owner-run assist/G0 preview 0.39.4 staged outside the Alienware game install. Source-only 0.41.20 and its owner-run watcher are staged separately on Alienware outside the game install; 0.41.21 route-selector staging failed twice because SSH closed the connection and is superseded by 0.41.22. The 0.41.22 source-only archive from commit `0a5ab05` is ready locally at SHA-256 `7d2b8fe8d726820f1f3ad393d3fb62e8a89398dfaddbd848ac2854ad91765d98`; Alienware staging was attempted but its SSH connection timed out. The 0.41.22 geometry work has no owner-run input command. The 0.37.0 guarded preview remains quarantined after its source-hash refusal. Version 0.41.9 adds an explicit verified Paladin+Cleric profile to the offline assist planner; 0.41.10 corrects its focused fixture to copied client IDs and unlock levels; 0.41.11 adds log-line and zone-generation identity for offline location tracking; 0.41.12 rejects same-zone reentry during G2 and requires verified reachable camps before selecting a full-auto camp; 0.41.13 carries exact supply warnings into sticky offline state and loosens only a measured float32 portal-edge tolerance; 0.41.14 adds explicit bounded long-strip budgets and a conservative turn-disk diagnostic; 0.41.15 adds a bounded offline automatic portal selector; 0.41.16 adds a read-only zone-transition log observer; 0.41.17 adds a read-only fresh location-to-G2 scene adapter; 0.41.18 binds the sampled G2 radius to fresh position provenance and the pulse speed bound; 0.41.19 adds an optional read-only owner-run destination watcher; 0.41.20 retains an optional preloading fix; 0.41.21 adds bounded alternate portal search after a failed strip; 0.41.22 separates local surface uncertainty from global work exhaustion and propagates an offline grade limit, still no bot input; 0.39.4 exposes unknown-HP reasons in the owner UI without changing input policy. Mode boundary, prior rotation planner reuse,
  synthetic nav graph and stall monitor, incremental log-state adapter, hourly
  status writer, spell progression and camp decision models, cross-zone route
  planner, unknown-state safety pause, simulator CLI. Four offline audit defects
  fixed: invalid mode cancellation, spoofed command classification, obsolete
  camp after level-up, first events in a newly created log. Closed-loop
  synthetic 1–50 scenario exercises camp changes, zone routes, spell tasks,
  rotation, rest, loot, vendor, death recovery, relogin and mode safety.
  Read-only importer now preserves copied retail map geometry/labels and
  zone/spell metadata outside git; target inspector rejects the official
  `eqhost.txt` as a private target. Full top-level retail map import uses
  atomic snapshots; routing rejects duplicate/nonfinite points and weights.
  Searchable POI index preserves 1,445 client map labels as unverified hints.
  Zone-name cross-reference builds a review list, never walkable edges.
  Pure WorldNavigator now requires verified traversal edges and start/arrival
  observations, replans from confirmed nodes after stalls, and pauses on
  uncertain mid-edge/zone conditions. The offline shell now switches modes by
  command or simulated F7/F8/F9 events, prints mode/generation/reason, and
  cancels queued or already drained intents after a mode change. The F8/F9
  mapping is not wired to the game; the October tool already uses those keys.
  Read-only client class strings now identify all 16 classes; an untracked
  spell/skill index holds 1,450 client level 1–50 candidates. The inherited
  Paladin/Cleric profile now checks each class's own unlock level. A strict
  offline assist advisor requires verified character, target, focus, gauges,
  gems and abilities before proposing a permitted rotation action; it does
  not send input. Mode transitions are serialized; emergency OFF survives a
  concurrent activation, and indicator failure latches OFF. Seven read-only
  copied client UI XML files yielded 557 static widget IDs in an untracked
  index; live UI values and active skin are unknown. A pure-Python player
  gauge reader now requires full-bar calibration, focus, exact window size and
  matching layout; unreadable values remain unknown. Butcherblock collision
  evidence was reconciled as historical coordinator-reported proof: at that
  point no mesh, bake recipe or placement inputs were retained in this
  project/approved store.
  Butcherblock is the first route/camp review target, Crushbone next; neither
  has a verified nav edge or suitable camp yet. An offline Butcherblock audit
  now rehashes the copied maps and refuses artifacts outside the approved
  store; it never promotes a route from a historical hash alone. Three
  Butcherblock PFS/S3D archives have been copied read-only from Alienware to
  the untracked client-data store; a bounded archive inspector inventories
  their WLD members and hashes.
  A bounded WLD inventory now reads all four copied Butcherblock WLDs and a
  placement audit resolves all 1,884 object locations to exact model names;
  22 tree locations have the documented Z sentinel, leaving 1,862
  non-sentinel locations. This reproduces the historical placement counts;
  the placement audit itself accepts no route.
  The old-format `0x36` mesh decoder now reads 1,925 terrain/object mesh
  records with 72,333 encoded vertices and 59,558 triangles total. It records
  pass-through flags and zero-area raw triangles; this mesh-only audit leaves
  placement composition, clearance and navigability unverified.
  All 75 actor definitions now resolve unambiguously to 75 object meshes;
  1,862 non-sentinel instances weight those meshes to 81,683 triangles and
  reproduce the historical 179 zero-area faces. A provisional composed
  WLD-XYZ OBJ outside git has 115,411 used vertices and 104,676 flag-zero,
  nondegenerate terrain/object faces. Material collision, dynamic obstacles,
  clearance, navmesh routes and client alignment remain unverified.
  Material chains have been checked across all 1,925 meshes; 6,443 terrain
  flag-zero faces are Boundary class and remain separately identified as
  uncertain candidate obstacles. The OBJ face order now matches the Lantern
  exporter and yields predominantly upward terrain normals. Recast/Detour
  source was checked out at historical pin `9f4ce64` and static libraries
  built locally. A bounded provisional FAYHOUSE region now bakes to 323 nav
  vertices and 156 polygons; one 24-polygon offline Detour query completes.
  No route has been accepted into the bot graph or tested in the client.
  A Boundary-excluded Butcherblock OBJ removed 6,443 faces, but the sampled
  FAYHOUSE tile remained byte-identical at 156 polygons. Two copied Crushbone
  archives now support a read-only audit: 178 exact matched placements,
  2,694 terrain meshes, 44 object meshes, and 4,057 Boundary terrain faces.
  Included and excluded provisional Crushbone OBJs have 26,570 and 22,513
  faces; sampled bounded tiles have 269 and 270 nav polygons, respectively.
  Both sampled offline queries completed. No real movement or collision
  acceptance follows from those samples.
  Copied Greater Faydark terrain archives now support a read-only map/WLD
  frame check. Map endpoints align to WLD terrain under XY sign/swap
  `(-map_y,-map_x)` in Butcherblock (1,557 matches), Crushbone (3,787),
  and Greater Faydark (8,163), all at 0.1-unit rounding. Four GFay exit
  labels are about 0.8013–0.8014 below nearby candidate terrain surfaces;
  the historical ~236.82 vertical mismatch was not reproduced there.
  Bounded BSP audits mark 163 Butcherblock and 263 Crushbone water-labelled
  region IDs, plus 5/3/9 zoneline-labelled IDs in Butcherblock/Crushbone/GFay;
  region shapes and live transitions remain unknown. The local baker now
  accepts explicit agent dimensions and the query reports endpoint snap
  distances. Compact and conservative Crushbone samples all produced
  corridors, but conservative start snapped 5.41 units, so this does not
  resolve the historical clearance disconnect or prove movement.
  A fail-closed copied-WLD BSP point lookup now marks candidate water and
  zoneline regions at raw WLD XYZ; missing children, cycles, plane hits,
  depth limits and nonfinite distances return unknown. All four GFay exit
  labels are outside tagged zoneline regions at their exact coordinates;
  a bounded sampled grid found tagged candidates 30–45 XY units away.
  Butcherblock's GFay label has a candidate 30 units away; Crushbone's
  GFay label has a candidate 25 units away but hits a missing BSP child at
  the label itself. These hints add no accepted route or transition.
  Detour queries now export requested, snapped and straight path WLD points.
  A local wrapper binds query JSON to a zone-named nav file and SHA-256;
  an offline sampler includes straight segments and both requested-to-snap
  connectors when checking copied BSP labels. The Butcherblock FAYHOUSE
  sample had 27 sampled positions with no copied labels or unknown BSP results. The
  Crushbone TIKIBAM sample had 10 sampled positions, no labels and two unknown BSP
  results. Segment attribution locates one unknown on its 5.407412-unit start
  connector and one on its 0.49-unit end connector; the six corridor samples
  have no unknowns. Neither result verifies a safe
  route, zone identity, or game movement.
  Strict assist now requires a target-selection token that changes on every
  selection, an observed target relationship, and a newer matching observation
  before any proposed key. Copied-client spell target types gate hostile NPC
  damage/stun and verified-undead damage; unverified self heals, buffs and Lay
  Hands remain disabled. Low self HP with another target selected pauses
  assist. Current UI/log interfaces do not supply the required unique token
  or target relationship, so this is an offline contract only.
  Full copied-BSP centerline traversal now splits provisional path segments
  at plane crossings and catches a synthetic 0.1-unit water region missed by
  sparse sampling. Butcherblock sample has no labelled or unknown spans;
  Crushbone has no labelled spans but unknown intervals of 0.026010 and
  0.002449 WLD units in start/end connectors. Both routes remain unaccepted.
  A read-only copy of the Alienware `eqgame.exe` now resides outside git,
  matching source SHA-256
  `65b8a28b2df70a256746567c4203c47f91696813865cba97f7151a5f4952503a`.
  Bounded static target-command searches found no usable unique target ID;
  this is not proof none exists. REA deep providers are unavailable here
  because Java/JDK 21 and other engines are absent.
  The copied default UI identifies an orange normal-XP gauge and separate
  green AA gauge. A separate offline reader now requires same-frame numeric
  label calibration and rejects uncertain crops. A current-level progress
  tracker can report percentage points/hour within one confirmed level;
  raw XP/hour remains n/a without an absolute cumulative XP source. Neither
  live crop nor runtime label/normal-XP allocation has been verified.
  The synthetic 1–50 harness now passes every action through a recording-only
  dispatcher that rechecks the original mode permit, a newer matching world
  snapshot, focus, target token and safety conditions before accepting it.
  OFF and ASSIST limits are exercised through that dispatcher. Synthetic
  camp travel now uses `WorldNavigator` and separate fabricated start,
  waypoint, and zone-entry observations before changing node or camp state.
  A bad observation latches OFF. The default observation adapter still
  fabricates immediate arrival; no real position or movement is verified.
  Pending zone transitions dispatch once, observation errors latch OFF, and
  dispatch/navigation timestamps share a monotonic synthetic clock.
  A new read-only location log reader parses the real client's exact `/loc`
  output shape and zone-entry messages, but keeps coordinates raw and
  unaligned. It skips existing history and drops positions across loading,
  unknown zones, log resets and timestamp regressions. It sends no input.
  A bounded historical alignment audit now scores the raw `/loc` triples
  against copied WLD terrain under all eight XY sign/axis candidates. It
  never accepts a transform or route.
  The October bot's character-by-character command sender was reviewed.
  A new recording-only assist key bridge checks a fresh matching observation
  and original permit before each symbolic key. The shared control plane
  serializes commands across bridge instances and preserves uncertain drafts
  across mode switches. Attack, movement and targeting stay excluded from
  ASSIST. No game keyboard input is connected.
  A second recording-only assist bridge models one spell-gem mouse click from
  a fresh matching scene and visible, unobstructed gem hitbox. It shares the
  same input channel and permit. A synthetic chat-open-after-slash case stops
  the command bridge with an uncertain draft. The installed `eqclient.ini`
  has no custom cast/ability binding; no active gem hitbox is calibrated.
  No game mouse input is connected.
  Run-level status now uses a non-replaying log tail. Replaced, truncated or
  backlogged logs invalidate level, XP, death count, camp and zone instead
  of replaying old events. First content from a newly created fresh-character
  log requires explicit opt-in. No owner-character log was read for this test.
  The owner says he will test the older October rotation helper himself on
  live. A direct Alienware recheck found that launcher and source present;
  its `--dry-run --level 1` exited 0 without input. HOWTO now gives its
  owner-run command and controls. It is a legacy test path with attack
  toggles and gem preparation, not strict current ASSIST. No lead-controlled
  login, key input or character progress occurred.
  An attack-free owner-run adapter for the reviewed October helper now
  suppresses autoattack commands, requires explicit F6 preparation before
  F8, and preserves uncertain chat drafts after physical Escape/Enter.
  It hash-checks the inherited source before import. This preview is still
  short of strict ASSIST because target relation, chat ownership, implied
  healing and live stop latency are unverified.
  The Alienware source changed from the October hashes to a larger, dirty
  November 12 helper between read-only checks. The 0.37.0 wrapper refused
  startup on its hash guard and its staged directory was renamed with a
  source-mismatch suffix; no input was sent. The current legacy helper's
  `--dry-run --level 4` passed. HOWTO now documents only its supervised
  F8/F9 owner test. F11/F12 are excluded because movement gates are unrun
  and a prior continued-walking report remains unresolved.
  The November helper's `Targeted` and `/consider` lines lack a unique entity
  ID, and its source documents auto-retargets without a `Targeted` line.
  Its sender infers chat ownership rather than observing the game draft.
  A read-only target log monitor now emits only new hints from a specified
  character/server file, revokes them on unsafe state changes, and never
  grants a unique target token or authorizes strict ASSIST.
  Blizz's November helper live test fired armor, Yaulp, Bash, stun and four
  nukes; gem preparation and focus checks worked. HP was null for 13 early
  combat gauge readings, then later resolved. A thin red bar inside the
  saved 51-pixel HP crop reproduces the rejection offline. The 0.39.1
  preview measures a contiguous inner band and leaves ambiguous crops
  unknown. It suppresses helper autoattack, makes native melee manual,
  and blocks F11/F12. Its source guard refuses changed November modules.
  It has not been run against a logged-in character by the lead or owner.
  The original F11 halt is explained by an absent default runtime mesh
  store; an existing 37-zone store has an offline GFay→Crushbone→Slaver
  corridor on the relevant dry components. Live movement/stop/zone gates
  are still unrun; the level-9 Trainer Hill primary camp is disconnected.
  The 0.39.2 preview adds a measurement-only G0 stop check: only `/stand`,
  `/location` and the existing bounded forward pulse are available there;
  F11 travel and F12 remain disabled. Its offscreen GUI and no-device smoke
  passed, but no owner G0 result has been observed. A separate offline
  November source patch now filters camps by dry-mesh reachability and
  recorded-route eligibility, then preserves a clear halt when no reachable
  camp exists. A copied-mesh audit from Legira's last position selects
  Slaver Caves for levels 7–8, GFay Orc Camps for 9–10 and halts at 11;
  this is not real XP or live route acceptance.
- Verification: `python3 -m pytest -q tests/test_screen_observer.py tests/test_ui_schema.py tests/test_assist.py tests/test_spell_catalog.py tests/test_client_ingest.py tests/test_control.py tests/test_offline.py`
  — 47 passed; `--demo-gauges` returned synthetic HP 0.5/mana 1.0
  and unknown values when unfocused; `--demo-assist` proposed a synthetic `/cast 3` and
  rejected it after OFF; CLI
  queue/switch/drain smoke dropped 2 stale synthetic actions;
  complete retail import found 224 maps, 1,057,974 drawing
  lines, 1,445 labels, 701 zone names and 198 Paladin/Cleric spells;
  all 1–50 Cleric and Paladin profiles class-valid after correction. Active
  snapshot: `~/.local/share/eql-automation/map-store/snapshots/e36ee7fd32a5c4b42f45/`.
  Client class-name SHA-256:
  `fd0508baa7151cc7575198860394967a40d72aeecc2db02a2c3024ea1ffbcefe`.
  Client spell-catalog SHA-256:
  `8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de`.
  Paladin Yaulp is absent from the level-1 profile and present at level 9.
  Indexed levels do not establish server spell availability or vendor stock.
  POI and zone-candidate CLI smoke passed. The 351 transition review candidates
  include 224 exact `to_` name matches, 4 reordered-name matches, 48 unprefixed
  exact matches and 75 unmatched `to_` labels. Drawing geometry and labels
  have not been verified as navigable or actionable.
  `python3 -m eql_automation --demo-navigation` replanned a synthetic stalled
  edge and arrived; no input was sent.
  `python3 -m eql_automation --synthetic-1-50` — synthetic level 50 reached,
  1439 trace events, no game/account input. Trace:
  `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T073156Z/`.
  `python3 -m compileall -q eql_automation` — passed.
  `python3 -m pytest -q tests/test_nav_evidence.py tests/test_navigator.py`
  — 11 passed; `--audit-butcherblock` verified the four copied map hashes and
  reported all acceptance flags false.
  `python3 -m pytest -q tests/test_pfs_archive.py` — 2 passed;
  `--inspect-s3d` decoded and inventoried all 3 copied Butcherblock archives
  (62, 149 and 9 members) without client input.
  `python3 -m pytest -q tests/test_wld_inventory.py tests/test_placement_audit.py`
  — 4 passed; `--audit-butcher-placements` matched all 1,884 copied placements
  to 75 exact model definitions and reported 22 dropped-tree sentinels,
  with collision and navigability false. Four copied WLD members were
  structurally inventoried without client input.
  `python3 -m pytest -q tests/test_mesh_geometry.py` — 2 passed;
  `--audit-butcher-meshes` decoded all 1,925 copied mesh records with valid
  triangle indices and reported `collision_composed: false`.
  `python3 -m pytest -q tests/test_model_links.py tests/test_instance_geometry.py tests/test_candidate_scene.py`
  — 6 passed; `--audit-butcher-model-links` resolved 75/75 exact model chains;
  `--audit-butcher-instances` reproduced 179 weighted zero-area triangles;
  `--build-butcher-candidate-scene` wrote an untracked 5,933,075-byte OBJ
  SHA-256 `c4faf053a4e006c68cbb115b58cccfe293c219a24a10d39f2a73fdd3d1889624`.
  An independent scan validated its 115,411 vertices, 104,676 faces,
  finite coordinates and face indices. This initial OBJ was superseded by a
  winding-corrected OBJ of the same counts, SHA-256
  `1ec7706037c35c06205c026c4ed56c1b4032fd2fb7a8e2dbe0cf2490d18a1bc3`;
  an independent scan found 41,501 positive projected Z normals among the
  terrain faces. `python3 -m pytest -q tests/test_material_audit.py` — 2 passed;
  `--audit-butcher-materials` resolved all 1,925 mesh material chains and
  identified 6,443 Boundary faces. CMake/Ninja Recast/Detour build passed.
  This is offline geometry only.
  A synthetic plane baked to 17 nav polygons and a complete 6-polygon query;
  the copied-scene FAYHOUSE region baked to 323 nav vertices/156 polygons,
  Detour data SHA-256
  `6347c67693d782d4643b5a45c15b13c9415606aecd678cf6e50b1df1e4db3863`.
  A sampled 24-polygon query completed offline; another was partial. The
  current active graph still has zero verified Butcherblock edges.
  The Crushbone tile is also offline only, with zero verified live edges.
  Copied archive, scene and tile hashes are in `FINDINGS.md`; copied data
  and candidate nav files remain outside git.
  `python3 -m pytest -q tests/test_candidate_scene.py tests/test_material_audit.py`
  — 5 passed. `python3 -m compileall -q eql_automation` and
  `git diff --check` passed. `--audit-crushbone` CLI smoke confirmed
  178 exact placements, 4,057 Boundary faces, and live acceptance false.
  `python3 -m pytest -q tests/test_map_alignment.py tests/test_region_audit.py
  tests/test_candidate_scene.py tests/test_material_audit.py` — 8 passed;
  three copied-zone region and map-alignment CLI audits passed, with
  manifests and hashes in `FINDINGS.md`. Four bounded Crushbone profile
  bakes and Detour queries ran offline. No real client/account input.
  `python3 -m pytest -q tests/test_region_audit.py tests/test_map_alignment.py`
  — 4 passed after BSP lookup hardening; `--probe-zone-labels` CLI passed
  against all three copied zones. Sample manifests/hashes are in
  `FINDINGS.md`; `python3 -m compileall -q eql_automation` and
  `git diff --check` passed.
  `python3 -m pytest -q tests/test_region_audit.py tests/test_map_alignment.py`
  — 5 passed after connector and malformed-path checks. The local query
  wrapper and `--audit-path-hazards` CLI ran on both copied-zone nav samples;
  hashes are in `FINDINGS.md`. A fabricated Butcherblock water line flagged
  41/41 samples, with route acceptance false. The Detour tool rebuilt and
  emitted WLD straight points; compile and diff checks passed.
  `python3 -m pytest -q tests/test_assist.py tests/test_screen_observer.py`
  — 9 passed for target continuity, spell/ability targeting and OFF cancellation;
  `--demo-assist` proposed synthetic `/cast 3` and rejected it after OFF.
  `python3 -m pytest -q tests/test_region_audit.py` — 4 passed for segmented
  path sampling; Butcherblock and Crushbone copied-zone hazard CLI audits
  passed with counts above. `compileall` and `git diff --check` passed.
  Two added exact-segment checks in `tests/test_region_audit.py` passed;
  both copied-zone span audits ran offline. The synthetic status text now
  names the missing private target rather than suggesting a live Daybreak test.
  `python3 -m pytest -q tests/test_screen_observer.py tests/test_offline.py`
  — 20 passed; `--demo-gauges` returned synthetic HP 0.5, mana 1.0,
  current-level XP fraction 0.25, raw XP unknown. Compile and diff checks passed.
  `python3 -m pytest -q tests/test_dispatch.py tests/test_offline.py` — 18
  passed; synthetic 1–50 rerun reached only fabricated level 50 and 1,439
  trace events, with `real_client_level_verified=false`.
  `python3 -m pytest -q tests/test_offline.py tests/test_navigator.py tests/test_dispatch.py`
  — 29 passed; synthetic 1–50 rerun reached only fabricated level 50 and
  1,446 trace events. All 12 recorded route-step events have
  `arrival_observed=true`; a stalled waypoint and wrong zone entry are
  rejected in focused tests, as are stale start/arrival observations and
  callback errors. Waiting on a zone issues one action. No client input was
  sent. Trace: `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T131106Z/`.
  The historical Alienware log contained exact timestamped location, loading,
  and entered-zone lines; one real historical location line parsed read-only.
  Its SHA-256 was `ab782e0d9fec079d2e6d6d74b8c6206c5da96d3811af87f20103c8dfcd99be73`.
  Copied client zone names resolved 504 unique names and 74 ambiguous ones;
  the four reviewed zone names matched IDs 58, 54, 61 and 62. Twelve focused
  location-log tests passed. No coordinate transform or live freshness check
  has been verified. The full 41-test focused set passed and synthetic 1–50
  reran to only fabricated level 50 with 1,446 events at
  `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T131858Z/`.
  Historical Greater Faydark: 56 raw lines held 48 distinct positions;
  direct log XY covered 48/48 copied-terrain positions with 47/48 vertical
  offsets within 0.5 of median 2.5638; the next candidate scored 13/48.
  Four Crushbone points tied two transforms.
  The filtered system-line and audit JSON hashes are in FINDINGS.md. This is
  copied-geometry evidence only, not live coordinate calibration. Five
  alignment tests and both copied-data CLI audits passed; the combined focused
  set passed 46 tests. Synthetic 1–50 reran to fabricated level 50 with 1,446
  events at `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T134150Z/`.
  `python3 -m pytest -q tests/test_key_bridge.py tests/test_assist.py tests/test_control.py tests/test_dispatch.py`
  — 38 focused checks passed; `--demo-assist` recorded eight symbolic key
  downs for `/cast 3`, no game input, then OFF rejected the old proposal.
  Synthetic 1–50 reran to only fabricated level 50 with 1,446 events at
  `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T141929Z/`.
  `python3 -m pytest -q tests/test_gem_bridge.py tests/test_key_bridge.py tests/test_assist.py tests/test_control.py tests/test_dispatch.py`
  — 46 focused checks passed. `--demo-assist` recorded a fabricated gem
  mouse down/up pair as well as eight symbolic command-key downs. Synthetic
  1–50 reran to fabricated level 50 with 1,446 events at
  `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T144347Z/`.
  `python3 -m pytest -q tests/test_offline.py tests/test_location_log.py`
  — 37 focused checks passed, including replacement, truncate, partial-line,
  backlog and nonmonotonic XP-time regressions. Synthetic 1–50 reran to only
  fabricated level 50 with 1,446 events at
  `/home/blizz/.local/share/eql-automation/runs/synthetic-1-50-20261113T150416Z/`.
  `python3 -m pytest -q tests/test_owner_live_adapter.py tests/test_key_bridge.py tests/test_assist.py tests/test_control.py`
  — 39 focused checks passed; the adapted October engine no-device smoke
  blocked F8 before F6; the owner entry's dry run passed on copied spell data.
  `python3 -m pytest -q tests/test_target_log.py` — 6 focused synthetic
  checks passed; no owner-character log or input was used.
  `python3 -m pytest -q tests/test_owner_nov12_adapter.py tests/test_owner_nov12_entry.py`
  — 4 focused checks passed. The staged Alienware 0.39.1 no-device smoke
  passed its source pin, thin HP band, attack suppression and F11 block;
  `./launch.sh --dry-run --level 7` exited 0. The legacy 0.39.0 working
  preview's packaged test import was incomplete and its staging directory
  was renamed `0.39.0-smoke-incomplete`; it was never handed to the owner.
  The 0.39.2 preview passed five adapter/guard checks, no-device smoke,
  level-7 dry-run and an offscreen measurement GUI smoke on Alienware.
  The isolated reachable-camp patch passed 19 focused camp/travel checks;
  a copied-mesh query found GFay→Slaver and Slaver→GFay Orc connected candidates,
  rejected Slaver→Trainer Hill, and stopped the offline sequence at level 11.
  Preview 0.39.3 rejected the broad saved HP crop and synthetic red accents;
  its pinned-source smoke, level-7 dry-run and offscreen GUI smoke passed on
  Alienware without game input. Five focused local adapter/guard tests passed.
  Its private archive SHA-256 is
  `78c547a0a0cdde6418a93de32bb50de6f46bd2e14872725a97f44eb894655c6e`.
  The original 69-MB, 116-file mesh store was copied outside the game and
  old helper; `diff -qr` matched it and the isolated loader opened GFay and
  Crushbone. The default GFay→Crushbone path is 4,927.779 mesh units; its
  minimum waypoint clearance is 0.932, below the 1.2-unit baked agent radius;
  the Crushbone→Slaver corridor contains a polygon with 0.2-unit centroid
  clearance. A later full-path sample at ≤2-unit spacing supersedes the
  waypoint minima: only 0.122-unit clearance on the GFay leg and 0.528 on the
  Crushbone leg. Wider funnel margins of 4/6 remain below the 1.2-unit baked
  radius on both legs. F11 is withheld.
  These are offline candidates only. A read-only trace summarizer reproduced
  the owner trace SHA and 13 unknown / 5 known HP gauge samples.
  A recording-only native melee stop gate requires exact ON/OFF log messages,
  a separately verified toggle, one attempt and a later OFF acknowledgment;
  five focused safety checks passed. It is not connected to the live helper.
  A bounded offline path-quality audit checks path-local area, raycast,
  clearance, slope and sample budget; four focused checks passed. It requires
  measured follower error and is not wired to F11. A no-input Alienware check
  rejected both copied route legs before clearance sampling: GFay off allowed
  mesh and Crushbone blocked raycast. The owner's log confirms
  one level-8 centurion kill for 2.574% XP but does not locate that fight;
  it also reports no food/drink and full bags. The only GFay guide camp is
  about 4,104 mesh units from the last fix and its route has a steep polygon.
  A separate pinned-source patch now places the bounded corridor audit inside
  November `Navigator._plan()` before each follower/replan and clears stale
  follower state on rejection. Two isolated no-input source smokes passed;
  the patch is not in the owner preview, and recorded routes remain unguarded.
  A bounded, read-only GFay radial geometry check now accepts only a short
  offline open-area candidate at the historical location: 36 rays over eight
  units, 324 samples and at least four units of capped clearance. Four focused
  checks passed. It observes neither the current position nor G0/G2 movement.
  A separate-process same-device key-release timer now passes five pipe-only
  checks, including caller stall/kill, plus an Alienware pipe smoke. It is
  not connected to the owner preview or a real uinput device, so it does not
  establish actual movement-stop behavior.
  The read-only location reader now invalidates its zone and fix on caller
  clock rollback; 13 focused location checks passed. Same-poll loading and
  zone transitions were already handled before this increment.
  A recording-only G2 pulse policy now caps pulse count, hold time, total
  window and observed displacement, requires a fresh verified upper speed
  bound, checks stillness after each pulse, and requires two final still
  fixes; eight focused checks passed. It rejects stale hold reports, final
  fixes and reused log fix sequences. The earlier 8-unit geometry preflight
  cannot authorize a pulse under this bound. It is not connected to game input.
  The offline policy now requires a generation-bound permit rechecked within
  0.05 s before key-down; its cancel method invalidates queued permits. Nine
  focused budget checks pass; the real sender is not integrated.
  A copied-mesh GFay route query with slope<=45°, clearance>=3u and portal
  width>=6u disconnected start and Crushbone trigger after 16,132 polygon
  visits. No GFay or Crushbone path is accepted for client travel.
  An isolated G2 input bridge now uses a same-descriptor child pulse with
  a child-enforced key-down expiry, serialized stop/GO boundary, helper
  release bookkeeping and no-input pipe tests. It is not wired to the owner
  preview or real scene observer. Alienware pipe smoke passed at 0.150 s.
  Copied-mesh review suggests bounded portal-local surface/slope sampling
  before rebaking GFay or Crushbone; centroid/polygon-wide metrics may be
  overconservative, but no candidate passes current route guards.
  An offline true-detail-surface and shared-portal seam audit now rejects
  unsupported height fallback. Nine focused checks pass. On the copied
  Crushbone mesh, polygon 4322's direct portal midpoint fails clearance at
  1.800 units. Its initial exit-seam rejection was a quantization-tolerance
  false negative; a bounded 0.0001-unit detail-edge projection now lets
  selected offset centerlines and seams pass locally, including a lead through
  4322→4321→4319. The retained source terrain is about 0.60–0.64 units below
  the baked detail surface there. No complete corridor or route is accepted
  for live movement.
  The first bounded full-corridor audit uses the historical 80-polygon
  Crushbone path from snapped arrival to Slaver west and a physical
  0.0001-unit polygon-edge tolerance. It checks 940 local segments, then
  rejects the five-fraction sampled chain at polygon 4322; this does not
  establish that no alternate portal positions or route can pass. Polygon
  4320 is off the actual path. Sixteen focused portal/corridor tests pass.
  One bounded extra sample on the 4197→4322 portal yields an 81-point
  offline centerline/seam chain across the historical 80-polygon Crushbone
  path, with 1,484 local checks. Its hash-pinned route artifact is outside git.
  Seventeen focused checks pass; the result expressly excludes travel-strip,
  live-position and real-client movement acceptance, so F11 remains off.
  A bounded lateral strip audit now rejects the 0.41.5 centerline candidate
  at segment 10/poly3146: a 1.2-unit side offset rises about 1.233 units
  (grade 1.028) across copied mesh detail. Nearby source terrain has
  overlapping Z=0/2 faces. Twenty-two focused tests pass; no accepted
  Crushbone travel route or real-client movement result exists.
  A route-wide strip scanner now reproduces the segment-10 rejection, then
  finds segment29/poly3248 after one locally valid portal shift. A bounded
  12×12 portal-pair search at poly3248 finds no local crossing that also
  passes adjacent strips. A graph bypass exists but is 176 polygons and
  remains untested by the strip audit. Twenty-five focused tests pass;
  F11 remains off.
  A bounded graph-cut audit shows that avoiding poly3248 requires poly1170
  on this copied ground graph. Its portal to1169 has maximum clearance at
  most 2.635 units under the fixed-height copied-mesh distance bound, below
  the current 3.0-unit diagnostic budget. A denser check corrected the
  earlier sparse false rejection at the preceding 637→1170 portal: it has
  a narrow 3.09-unit clearance opening near fraction0.47. Thirty
  focused tests pass; these are offline geometry findings only.
  A bounded copied-mesh search found a wider GFay candidate with 3.47-unit
  minimum sampled clearance but an 89.19-degree slope flag and 55 standard
  locator mismatches. The filtered Crushbone arrival-to-Slaver route remains
  disconnected. Neither is accepted for live travel.
  A retained 216-polygon GFay alternative passes all 214 copied-mesh ground
  portal midpoint seams and 215 ground midpoint centerlines at 0.5-unit
  sample spacing after a 0.0005-unit float32 detail-edge correction. Its
  215-segment sampled ground strip passes in one call to a 2-unit standoff
  before the copied Crushbone area-4 trigger. A conservative turn disk flags
  local grade at waypoints 170, 171 and 187. With three adjusted portal
  crossings, separate whole-route runs pass all 214 turn disks and all 215
  ground strips plus 214 seams. The new automatic selector independently
  chose fractions 0.75/0.70/0.60 at those links and passed a whole ground
  strip recheck. The trigger crossing, arrival
  and actual movement are unverified, so no route is accepted into F11.
  The copied GFay marker references server zone-point 4, and the reciprocal
  Crushbone marker does not encode a spawn coordinate. The Nov 5 owner log
  proves a zone entry but has source/destination location fixes 232/92 seconds
  away from it. The new non-replaying observer pairs only fresh log-confirmed
  before/after fixes and never labels the latter an exact spawn or proves
  walking rather than teleport/relog. Twenty
  focused location/transition tests pass; no fresh crossing is captured.
  The copied owner log's
  no-room and food/drink warnings now stay in offline telemetry until a
  verified supply observation. A planner snapshot carrying them pauses, and
  recording-only dispatch refuses loot with unknown capacity or a later
  warning. A live adapter does not connect these stages yet. Twenty-nine
  focused portal/strip/turn tests and the startup demo pass; no game
  input or purchases were performed.
- Verification for 0.41.18: 41 focused G2/start-area/log/bridge tests passed
  after the pipe-based bridge test was corrected to accept a measured hold
  over 0.20 seconds only as a safe halt with key-up. The synthetic 1–50 smoke
  reached only synthetic level 50 and reported `real_client_level_verified=false`.
  No real-client G2 pulse or movement was run.
- Verification for 0.41.21: 15 focused portal/strip/turn tests passed;
  a hash-matched copied Crushbone 80-polygon probe failed at polygon 3248
  before strip search, with no sampled turn-disk candidate. This is an
  offline route rejection, not evidence of client movement.
- Verification for 0.41.22: 37 focused portal, strip, turn and surface tests
  passed after correcting undercounted centerline/turn sample budgets and
  preventing a slow final geometry query from passing the strip time limit.
  The copied GFay 215-ground-polygon corridor again produced an offline
  sampled candidate after 243 turn checks and 270 candidate strip checks
  in 88.897 seconds under corrected accounting; the last pre-call cap guard
  was added after that run. Its destination crossing and client traversal
  remain unverified.
  The copied 80-polygon Crushbone route still fails at polygon 3248 with
  grade 1.2; the 176-polygon bypass fails at polygon 441 with grade 1.2
  and polygon 468 with grade 2.0. None reached strip search.
- Verification for 0.41.23: 44 focused portal, strip, turn and corridor
  tests passed after the final-query deadline checks; offline only.
  The copied Crushbone graph has a two-edge cut at 3248→3247 and 658→623;
  all 13 sampled portal fractions on both edges fail the conservative
  grade-1.2 turn audit. No alternate route is accepted into F11.
  At four rejected cut-edge samples, copied Diffuse grass terrain is flat
  at Z=0 while the included-Boundary navmesh detail rises 0.77–0.78 units
  over a 0.6-unit turn offset. The overlapping high sky faces are Boundary
  material and disappear from the excluded OBJ; the subsequent 0.41.24
  rebake found they did not cause those sampled rises. Live client-height
  calibration is still required.
- Verification for 0.41.24: the same-profile Boundary-excluded full-zone
  rebake finished with zero warnings and left both Crushbone cut-edge
  heights and 13-fraction turn failures unchanged. A detail-error 0.25
  sensitivity bake passed all 13 sampled turns at 3248→3247, but 658→623
  remained zero of 13; the finer variants emitted 20–21 Recast warnings.
  No real-client route or level gain is accepted.
- Current blocker: 0.39.4 owner-supervised F8/F9 HP and attack-free rotation
  feedback is pending. Strict current ASSIST still lacks a unique target and
  verified chat-draft observation. Full-auto F11 needs confirmed native melee
  stop, G0/G2 movement-stop/follower acceptance, validated runtime mesh-store binding,
  integration of the offline reachable-camp patch and a level-11 camp; real-client acceptance also lacks the intended
  private endpoint/client configuration. Owner says the target is private, but its endpoint/client
  configuration is missing. The only located Alienware EQL client still points
  to Daybreak's official live login host. The lead will not send automated
  connection or character input to that host. Bounded devbox/Banshee process, listener, container and
  directory checks found no private EQEmu/EQL candidate; this does not rule
  out another machine or path. Daybreak rules prohibit unattended play and unauthorized
  servers; no Daybreak-authorized live test route is documented. The historical
  Butcherblock navmesh/recipe is absent from the approved retained store, and
  the reported GFay vertical mismatch on its historical route and
  conservative clearance failure remain unresolved. No actual client
  acceptance is ready. The 0.39.4 assist/G0 preview is privately staged on
  Alienware outside the game install; full auto has no playable release yet.
- Next step: collect Blizz's owner-run 0.39.4 F8/F9 HP and supervised G0
  stop observations. When he next crosses GFay→Crushbone manually, obtain a
  fresh `/location` on each side and compare the destination observation to
  the copied mesh without calling it a verified spawn. Keep F11 off until
  G0/G2, current-position observation, transition and follower evidence pass.
  Collect the owner's 0.39.4 HP/F8/F9 observations and supervised
  G0 movement-stop result without touching Legira. Build a bounded owner-run
  G2 straight-motion measurement program using the isolated pulse bridge,
  fresh client scene observer and bounded stop guards; the geometry
  preflight alone does not permit it.
  Build an observed autoattack state/stop acknowledgment gate for
  full auto, then bind the copied mesh store in a separate owner-run route
  trial after G0/G2 checks and resolve the narrow GFay/Crushbone corridors.
  For Crushbone, the 0.41.5 centerline fails the lateral strip at poly3146;
  a local portal shift moves the first failure to poly3248. Evaluate the
  176-polygon bypass only after measured follower error establishes a real
  clearance budget; the current 3.0-unit offline budget fails its mandatory
  1170→1169 portal. Inspect turn fans, variable source-to-bake height offsets
  and alternate camps/routes in parallel. Do not promote the centerline
  artifact to F11.
  Integrate the already tested reachable-camp
  fallback for level 9; resolve the level-11 camp using measured XP and route safety.
  Validate a unique selection signal and chat-open/draft signal on an isolated
  client view; the preview remains supervised. Obtain the intended private endpoint or separate client config,
  then verify target identity before strict live assist input. Review copied client
  Boundary collision, water region shapes and dynamic-door rules; compare
  more offline clearance variants without promoting edges. Trace the
  historical GFay height mismatch. Inspect dynamic doors, water, zone
  transitions and actual movement before accepting a route. Validate a unique
  target-selection epoch, target relationship and type-51 healing behavior
  on the intended private client before wiring assist input. The XP reader
  needs a real active-skin crop and same-frame label confirmation. BSP
  candidates require observed traversal; Crushbone camps
  still require client evidence; select later camps from observed level and
  safety. Verify the historical log-to-WLD candidate against a fresh test
  character on the intended private client, including height and log delay,
  before any position can feed `WorldNavigator`; build a read-only runtime UI observer on an
  isolated client view. Verify target-selection identity, chat-draft ownership,
  a bounded native key sender and immediate OFF before enabling live ASSIST.
  A spell-gem click path would also need a private-client screenshot, active
  hitbox calibration, unique target selection and bounded native mouse sender.
  ASSIST keeps
  movement manual. The new 0.39.3 preview's live HP and stop behavior remain
  unverified.
