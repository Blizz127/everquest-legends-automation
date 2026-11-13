# STATUS

Updated 2026-11-13 09:04 CST for coordinator task `829a00229b29`.

- Real-client level: n/a. No automated character login or live run.
- Real-client XP / XP per hour: n/a. Current-level XP fraction / percentage points per hour: n/a. Deaths: 0. Camp: none.
- Build: offline prototype 0.36.0. Mode boundary, prior rotation planner reuse,
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
- Current blocker: owner says the target is private, but its endpoint/client
  configuration is missing. The only located Alienware EQL client still points
  to Daybreak's official live login host. No automated connection or input will
  be sent to that host. Bounded devbox/Banshee process, listener, container and
  directory checks found no private EQEmu/EQL candidate; this does not rule
  out another machine or path. Daybreak rules prohibit unattended play and unauthorized
  servers; no Daybreak-authorized live test route is documented. The historical
  Butcherblock navmesh/recipe is absent from the approved retained store, and
  the reported GFay vertical mismatch on its historical route and
  conservative clearance failure remain unresolved. No actual client
  acceptance is ready. No private
  launcher/server publication destination is configured; this build is local.
- Next step: obtain the intended private endpoint or separate client config,
  then verify target identity before any live test. Review copied client
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
  movement manual. The October assist tool's live preparation/combat remain
  unverified.
