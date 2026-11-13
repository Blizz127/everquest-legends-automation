# STATUS

Updated 2026-11-13 05:21 CST for coordinator task `829a00229b29`.

- Real-client level: n/a. No automated character login or live run.
- Real-client XP / XP per hour: n/a. Deaths: 0. Camp: none.
- Build: offline prototype 0.17.0. Mode boundary, prior rotation planner reuse,
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
  their WLD members and hashes. Collision geometry remains undecoded.
  A bounded WLD inventory now reads all four copied Butcherblock WLDs and a
  placement audit resolves all 1,884 object locations to exact model names;
  22 tree locations have the documented Z sentinel, leaving 1,862
  non-sentinel locations. This reproduces the historical placement counts but
  neither composes collision geometry nor accepts a route.
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
- Current blocker: owner says the target is private, but its endpoint/client
  configuration is missing. The only located Alienware EQL client still points
  to Daybreak's official live login host. No automated connection or input will
  be sent to that host. Daybreak rules prohibit unattended play and unauthorized
  servers; no Daybreak-authorized live test route is documented. The historical
  Butcherblock mesh/recipe is also absent from the approved retained store,
  and the reported GFay vertical mismatch and conservative clearance failure
  remain unresolved. No actual client acceptance is ready. No private
  launcher/server publication destination is configured; this build is local.
- Next step: obtain the intended private endpoint or separate client config,
  then verify target identity before any live test. Decode the copied
  Butcherblock `0x36` terrain and object meshes, compose them with the now
  decoded static placements and build a new collision bake in this project's
  approved data store;
  check conservative clearance, GFay height alignment, dynamic doors, water,
  zone transitions and actual movement before accepting a route. Review
  Crushbone next, then select camps from observed level and safety. Build a
  read-only runtime UI observer on an isolated client view. ASSIST keeps
  movement manual. The October assist tool's live preparation/combat remain
  unverified.
