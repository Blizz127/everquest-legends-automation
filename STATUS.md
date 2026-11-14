# STATUS

Updated 2026-11-14 02:16 UTC for coordinator task `829a00229b29`.

- Private source **0.41.56**, commit `4dcdd1d`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.56/source`. Archive SHA
  `59678e99e6a3467b9be7c6d83f7c21d7a7af7b8a177f7e1b53dbe2fc28e93a0c`
  matched remotely. Five pure precision smokes, three CLI startup checks and
  invalid-option refusal passed. No input device or game input; owner assist
  and G0 packages unchanged. Remote evidence: `../smoke.json`.
- Source **0.41.56** adds explicit overlap attribution and two-ULP portal
  diagnostics. **VERIFIED:** 43 precision tests and seven source-query tests
  pass. The segment-38 overlap and segment-52 two-ULP gap both reproduce from
  pinned data and pass source-supported local corrections; stored data stays
  unchanged. Defaults remain one-ULP/gap-only with the 0.6 diagnostic Z limit.
- **VERIFIED replay:** explicit overlap/two-ULP and 2.0-height sensitivity
  reaches segment 65, step 773, then refuses another overlap. No game input.
  Artifact SHA `65b7560c62b41ae6af69dc9d95138ff275fc8e7ce9acd35e4300a6ed800f29f7`.
- **VERIFIED whole-corridor scan:** all 2,399 radius-1.2 cells checked; 2,155
  pass and 244 refuse (45 portal precision; 154 source reference/layering;
  18 source overlaps; 16 source flag/material; one missing/over-budget source;
  three source slopes; seven baked slopes). Max measured difference on
  passing cells: 1.123134. No complete-region bound is accepted. Artifact SHA
  `be99450b900f29f736185a21204a4889af78cefe5abf7cb7b73c63a5e68a3be8`.
- Next: derive portal rounding from retained bake provenance, then classify
  source layers/materials and route around genuine geometry problems using
  the complete profile. Real movement still needs fresh scene/calibration,
  full body/hazard checks and sender integration. Level, XP, XP/hour, deaths
  and camp remain unknown beyond Legira 7 GFay; G0 visible stop passed, no
  accepted 1–20 route or automated XP. Assist 0.39.6/G0 0.39.7 are unchanged.
- Private source **0.41.55**, commit `2d94ede`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.55/source`. Archive SHA
  `9955a1493c1413317d370fb97ab618f7d60322c37290dc710b7643f4140460e7`
  matched remotely. Eight pure G2/ground binding smokes and CLI startup passed;
  no input device or client was opened. Staging evidence is `../smoke.json`.
- Source **0.41.55** separates physical source floor, baked projection and
  calibrated character height. G2/follower now require independent expected
  geometry evidence and current height calibration; endpoint 0.25 and G2 snap
  0.0005 are unchanged. **VERIFIED:** 34 pure checks, 24 retained follower/pipe
  integrations and five source-lookup checks pass. No input devices or game.
- **VERIFIED copied-data diagnostics:** Sampling source at every stop exposes
  0.759658 and 0.925760 bake differences at segment 5, refusing the default
  0.6 and separate 0.9 limits respectively. A separate 2.0 sensitivity reaches
  segment 38/step 458, then refuses the existing detail overlap. It samples
  459 stopped positions; source/bake differences range 0.121987–0.925760.
  Default limits are unchanged. Historical/fixture data does not grant input.
- Current level, XP, XP/hour, deaths and camp remain unknown beyond Legira 7
  in GFay. Owner-confirmed G0 visible stop passed; no accepted 1–20 route or
  automated XP. Next: source-supported regional height bounds and the exact
  reciprocal overlap correction. Fresh live scene/calibration, remaining
  route/hazard checks and sender integration still gate real movement.
  Owner assist 0.39.6 and separate G0 candidate 0.39.7 remain unchanged.
- Private source **0.41.54**, commit `96f472c`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.54/source`. Archive SHA
  `018a488f50db896a9f1fe93587f7f91d20a1d208ebd2f0f022b2ba409b3fcf65`
  matched. Remote pure-geometry/CLI smokes passed, including rejection of a
  competing source floor. No input device or game input was used.
- Source **0.41.54** adds bounded reciprocal one-ULP precision retries with
  full copied-source ground support. Twenty-six focused tests passed. Source
  triangles must cover the expanded footprint continuously and without other
  floors; the full source/baked height difference is checked. No mesh writes.
- **VERIFIED:** Default 0.6 diagnostic Z limit reaches segment 20, step 239,
  then refuses a 0.600690 source/bake difference. A separate 0.9 sensitivity
  reaches segment 38, step 458, then refuses overlapping detail faces. The
  default remains 0.6; neither replay completes the route or sends input.
- The pinned G0/source comparison confirms source-relative character height
  varies only 0.000788 across its two positions; raw-to-baked offset varies
  0.01939. Next: split source-floor and mesh-projection observations in the
  future G2/follower binding, preserving strict endpoint and raw-height checks.
  Historical offsets do not establish fresh live calibration.
- Current level, XP, XP/hour, deaths and camp remain unknown beyond Legira 7
  in GFay. G0 stop passed; no accepted 1–20 route or automated XP. Live scene,
  calibration, full collision/hazard checks and sender integration remain
  unaccepted. Owner assist 0.39.6 and G0 candidate 0.39.7 are unchanged.
- Private source **0.41.53**, commit `fb0733f`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.53/source`. Archive SHA
  `efb26be50ce614ad7b0791efe44496c9e2957eaf35537e19d72256cdf173f2bb`
  matched. Both CLI startup checks and missing-hash/out-of-range-portal
  refusals passed remotely. No input device or game input was used.
- Source **0.41.53** repairs the GFay steep-section route by moving two
  portal crossings west. The same 155-polygon corridor is retained; all three
  changed segments pass continuous radius-1.2 ground tubes and existing
  strip/turn clearance checks. Full centerline BSP: 376 clear spans.
- **VERIFIED:** A midpoint control still fails and exports no plan. The
  guarded follower clears the repaired section and reaches segment 11,
  step 143, before a second one-ULP tile gap stops it. Replay SHA
  `26c21993ea75bbf0dcfd6c893adacd2f58737e42031de2bdee2d94041e7f3113`.
  Wrong/missing plan pins are refused; no source mesh is changed.
- Next: generalize the bounded reciprocal-portal precision correction with
  source support and replay the remaining route. Live scene, calibration,
  complete collision/hazard checks and input integration remain unaccepted.
  Current level/XP/XP-hour/deaths/camp are unknown beyond owner-reported
  Legira 7 in GFay. G0 visible stop passed; no accepted 1–20 leg or automated
  XP. Assist 0.39.6 and separate G0 candidate 0.39.7 remain unchanged.
- Private source **0.41.52**, commit `96f9576`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.52/source`. Archive SHA
  `f356e21c212df80339cfc400ebf114c7ed362abb4f0917f17082ba239eed270f`
  matched. Four focused diagnostic tests and CLI/invalid-option startup
  smokes passed remotely. No input device or game input was used.
- Source **0.41.52** reconciles the GFay one-ULP detail seam against all
  copied terrain faces. Exactly one flag-zero Diffuse source face contains
  the entire failed footprint; source Z is 0.3713 below the baked reference.
  A local virtual XY correction shifts endpoints only 0.0000610352 unit,
  leaves Z unchanged and passes three affected replay footprints. Original
  client data, navmesh and route artifacts are untouched.
- **VERIFIED:** Four focused scope tests passed. The guarded replay now
  stops at segment 6, detail face 248932, grade 1.3266 against limit 1.0.
  Rechecking shorter holds permits two additional steps, then refuses even
  the hypothetical 0.02-second minimum. Final replay SHA
  `4fc154ee94226560abccf08c848cdfa214105fc35562b18e6c8834a0909ab2a0`.
- Current level, XP, XP/hour, deaths and camp remain unobserved beyond the
  owner-reported Legira 7 in GFay. Owner G0 visible stop is confirmed; no
  accepted 1–20 leg or automated XP. Next: compare face 248932 with source
  terrain and adjust the route if needed; live scene/alignment/speed and
  timed sender integration remain open. Assist 0.39.6/G0 0.39.7 unchanged.
- Private source **0.41.51**, commit `bfc9d7e`, is staged on Alienware at
  `~/.local/share/eql-automation/owner-tools/0.41.51/source`. Archive SHA
  `35893d8b96ac0c73e8340bdb8c2577af836910423054d72c4309fc8ce4ce7d01`
  matched. Remote ground-footprint smoke, two CLI startup checks and offline
  navigation smoke passed; no input device or game input was used.
- Source **0.41.51** adds continuous detail-ground footprint checks with
  explicit numerical tolerances. Twenty-three focused tests passed, including
  holes hidden from endpoint/rail samples, overlapping floors, cumulative
  tiny overlaps, height steps and uncertain forward/pivot footprints.
- Six hypothetical copied-GFay footprint checks pass. The guarded full replay
  stops after three segments (19th check): a 0.0001220703125-unit discrepancy
  between reciprocal32479↔31668 portal edges leaves0.00011066 square units
  uncovered. This is observed in the copied navmesh, not proof of a client
  terrain hole. No automatic stitching or tolerance widening was applied.
  Final replay SHA `77b97911957c32a6d1c0ef8a3b1fec365ce61934ed0755cfc61b71f96eeb0d8a`.
- One read-only UI capture attempt refused without exactly one focused game
  window/process; no focus change, screenshot or game input followed.
  Next: compare original copied terrain at the seam, then combine ground,
  wall/headroom/BSP and scene checks for the timed route bridge. Current live
  level/XP-hour/deaths/camp remain unknown beyond Legira7 GFay; G0 stop passed,
  no accepted1–20 leg or automated XP. Assist0.39.6/G0candidate0.39.7 unchanged.
- Private source **0.41.50**, commit `4b34c6a`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.50/source`. Archive SHA
  `2ff19d67457aa4632704ffe68c99d68c114d24f8b38241dd2e68ead9a5c9b09e`
  matched; remote startup, three actual-child pipe receipt checks, and
  offline navigation smoke passed. No input device or game input.
- Source **0.41.50** adds child DOWN/UP timestamp receipts and late key/
  duration selection after READY under the existing stop/GO lock. The old
  G0 float API is preserved. Interrupted, stale, mismatched or cancelled
  receipts cannot report success; zero-key selection emits no events.
- **VERIFIED pipe checks:** 58 focused watchdog/G0/G2 cases passed, plus two
  fixed-route/actual-child integrations. The controller used child write
  bounds and waited for new synthetic stopped fixes before advancing.
  Assist switched after selection emitted no DOWN. No input device or game
  was used. Existing owner packages remain unchanged.
- Current level/XP/XP-hour/deaths/camp still unobserved beyond Legira7 GFay;
  old G0 stop passed, no accepted 1–20 leg or automated level gain. Next:
  swept-motion check and owner-preview bridge using fresh scene/calibration;
  pending owner-ready map/UI capture remains open. Assist stays0.39.6,
  separate G0 candidate0.39.7; no extra owner command requested.
- Private source **0.41.49**, commit `f80c069`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.49/source`. Archive SHA
  `fa7b46a73a717903c134b0e322d3681531dd8c6797bc9f61a7dca939d289c056`
  matched; remote API/CLI startup and offline navigation smoke passed.
  No device access or game input. F11 remains unavailable.
- Next unblocked sender work: add child key-down/up timestamp receipts to
  the existing watchdog, preserving G0's float API. Its current duration-only
  API cannot satisfy the route controller's timing contract; subprocess
  startup also needs a freshly bound proposal after readiness. No route
  sender is connected yet, and assist movement remains refused.
- Source **0.41.49** adds the fixed-route controller using the retained
  rotation bot's steering classes. Eighteen focused checks passed: actual
  completed holds only, fresh stopped raw endpoint pairs, no short-segment
  skips, mode/cancel refusal, and narrow/long-segment steering corrections.
- **VERIFIED idealized replay:** all 155 copied GFay segments completed in
  2,147 steps (1,384 simulated seconds; 11.10 seconds of offline execution).
  This is synthetic motion and endpoint terrain sampling, not real movement
  or a swept-volume check. Final artifact SHA
  `b468b2be658f21f3dbeac3197d89bbf82627460d8a8ab59b91eaec1eab27d99e`.
- Live status unchanged: old G0 visible stop passed; no accepted 1–20 leg,
  automated XP or level gain. Current level, XP/hour, deaths and camp remain
  unobserved beyond Legira7 GFay. Next: pending owner-ready Current Zone/UI
  capture, live alignment/speed and a checked timed-sender connection.
  The new controller produces proposals only and does not enable F11.
  Recommended assist remains 0.39.6; separate G0 candidate remains 0.39.7.
- Private source **0.41.48**, commit `b671d2d`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.48/source`. Archive SHA
  `2cbc8b52a66849121480ae686fd2f1fe5c00634686a9c01ea03783647a99cb05`
  matched; remote API/CLI startup and offline navigation smoke passed after
  correcting the smoke wrapper's JSON-key assumption. No client input.

- Source **0.41.48** adds a G2 safety-provider boundary using fresh input
  scans around independent UI evidence, bound to window/process, calibration,
  mode and cancel generation. Twenty-seven focused tests passed, including
  the existing location-log scene observer. UI evidence was simulated; the
  live classifier and owner-helper integration are still missing.
- The copied GFay route now exports **155 fixed 3D segments**, retaining the
  audited portals and terrain heights. Offline artifact SHA
  `145679ec15111cf2d319ca630c66da693cc69863bdef594f67a46989c18592a4`.
  No route is accepted and the historic G0 start is not a current position.
- The actual retained helper reproduces a corner shortcut outside the
  checked strip and predicted arrival before its raw fix reaches the portal.
  One-segment following avoids the shortcut fixture; the production adapter,
  bounded movement and stopped raw-fix advancement remain to implement.
  Probe SHA `c22363c8f0aa12731434b45c124181b6366bbd62d4967c92eac19c99c2e8a013`.
- Current level/XP/XP-hour/deaths/camp remain unobserved beyond Legira7 GFay.
  G0's owner-confirmed visible stop remains passed; no playable 1–20 leg or
  automated level gain. Next: current-zone/idle UI capture when owner-ready,
  live alignment/speed and the fixed-segment controller. Assist remains
  0.39.6, separate G0 candidate 0.39.7. No new owner test is requested.
- Private source **0.41.47**, commit `b6df01d`, is staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.47/source`. Archive SHA
  `a6a079824b57520f8564f58bfd194707cfc0e603d0656166cb111eaf02b11aa2`
  matched locally/remotely; remote API/closed-observer, input/capture CLI
  startup and offline navigation demo passed. No game input was sent.
  Owner was asked to open map → Current Zone and leave the game focused;
  the lead can capture it read-only without another terminal command.
- Source **0.41.47** corrects the observer's same-descriptor event loss:
  EVIOCGKEY can flush pending key events. Two independent read-only opens now
  separate current-state queries from event history; the new regression
  reproduces that kernel behavior. Touchpad slots and volume-only absolute
  controls are handled explicitly. Thirty-two focused tests passed.
- A bounded read-only Alienware probe exercised all 26 actual devices after
  the fix: profiles 24 without absolute axes, one type-B touchpad and one
  absolute-volume device; two complete observations after startup, zero
  unsupported axes, contacts or held keys. It sent no game input. This quiet
  probe does not verify a deliberate quick-key or held-finger transition.
  Report SHA `5c8faa35c9bb9684a79f1a6a5af21cce5154a59f717448540820f21b411dde0a`.
- A focused UI capture still refused without a unique focused game/session.
  Client XML defines map label MRA_ZoneLabel/EQType1020, but maps may browse
  other zones. The capture now includes that label; current zone needs the
  owner-selected Current Zone view. Map label, chat, target and combat pixels
  remain unobserved. No lead character input or accepted 1–20 movement leg.
- Current level, XP/hour, deaths and camp remain unobserved beyond the older
  Legira7 GFay report. G0's old visible stop remains passed. Next: owner-ready
  current-zone/idle UI observation, then independent scene integration and
  fresh position/alignment/speed for the first short GFay leg. Assist 0.39.6
  remains the owner recommendation; 0.39.7 is the separate G0 candidate.
- Private source build **0.41.46**, commit `a920826`, is staged on Alienware
  at `~/.local/share/eql-automation/owner-tools/0.41.46/source`. Archive
  SHA-256 matched locally/remotely:
  `bffe9db1da810fa6b6d2e65b673fb3fc038075341a74eda614dbdca1ac90c1dc`.
  Remote observer API import/closed-state refusal, both new CLI startup
  checks and the navigation demo passed. The demo is simulated; no live
  device was opened or client input sent. No new owner test is requested.
- Project **0.41.46** adds a read-only owner-input observer, a production
  dependency for future G2. Thirteen focused tests passed, covering startup
  held keys/buttons, brief activity, unreadable devices, hotplug/path reuse,
  overflow through SYN_REPORT, stale/slow clocks and read-only open cleanup.
  No live device observation or movement wiring has run. Absolute axes remain
  unsafe pending contact/neutral interpretation; independent chat, target,
  combat, fresh zone, alignment and speed evidence are still missing.
- Crushbone source-span probe reproduced the west coarse corner Z1.9625:
  raw rasterization merges nearby wall into walkable floor; subsequent filters
  leave it unchanged and connected corner selection inherits the height.
  Source-only reproduction is not exact custom-baker equivalence. Lowering
  permitted bake step height 3.5→1.0 disconnects the actual retained arrival
  and Slaver guide points. Baseline still finds 80 polygons and rejects turn
  3244 after 41 turn checks. Neither mesh is a playable route.
- Real-client progress is unchanged: owner-confirmed old G0 stop passed;
  no accepted 1–20 leg, automated XP or level gain. Current level/XP/hour,
  deaths and camp remain unavailable beyond the earlier Legira level-7 GFay
  report. Next: complete independent live observations for the same-zone GFay
  route. Recommended assist stays 0.39.6; G0 candidate 0.39.7 is separate.
- Last owner-reported real-client level: 7 for Legira in Greater Faydark; no lead-controlled login or automated level gain verified. A later level has not been observed by the lead.
- Separate **0.39.7 G0 watchdog candidate** is staged on Alienware. It
  connects the existing one-pulse G0 intent to the same-device independent
  release child; assist hold refuses. Stop/GO share a reentrant lock and a
  stopped result cannot pass. Twenty-eight focused pipe checks passed;
  Alienware original-engine dispatch smoke used a pipe, created no input
  device and sent no game input. Archive SHA-256 matched
  `4c917a63f755e9ea3982a5939d5c9c7d3c35d9c7ffd0026c80680631df9d492b`.
  Actual watchdog client release remains unverified; keep owner HP testing
  on 0.39.6. The earlier G0 pass is preserved, with no immediate repeat asked.
- The bounded Crushbone detail-distance comparison completed: baseline
  reproduced exactly; distance 6→3 worsened outer-ring maximum angular grade
  from 1.801 to 2.706 and raised warnings 21→439. Reject this candidate.
  Report SHA-256 `b0e7307e43d1b212ce8d5a973c3290014fb9f8eee862e2855de5a4bfa9246780`.
  Coarse polygon 623 corners are identical in both bakes; the bump predates
  detail sampling. Next: inspect compact spans/contour corner height, keeping
  same-zone GFay as the first route candidate. No live movement or XP gain.
- A read-only screen capture attempt refused because there was not exactly
  one focused game window/process. No focus change, input, capture or game
  mutation followed. G2 still needs independent scene observations, a fresh
  zone/location binding, live alignment and a preceding speed calibration;
  the existing budget cannot manufacture its own prerequisite speed bound.
- Owner assist **0.39.6** is privately staged on Alienware. F9 now invalidates
  a queued GUI preparation; explicit **Chat recovery** clears only local
  draft bookkeeping while stopped, sends no keys, and requires a fresh F8.
  Travel is visibly unavailable; measurement mode shows only G0. Twenty-five
  focused adapter/recovery tests passed, plus original-engine and offscreen
  GUI smokes on Alienware with no worker, game input or settings save.
  Final archive SHA-256 `7e750589a9f4c83e875e8a9a982be062e538ad78c54e635acb2494ad853f727c`
  matched locally/remotely. The inherited 0.39.5 HP proposal remains present;
  live HP/healing and recovery behavior still need owner feedback.
- G0 remains passed by the owner's visible-stop confirmation and retained
  trace. No playable 1–20 leg or F11 route is accepted. Current live level,
  XP/hour, deaths and camp activity have not been observed since the last
  owner report (Legira level 7, GFay). Next real-client step is owner-run
  HP/current-scene observation before bounded G2/follower validation.
- Read-only Crushbone source probe found flat Z=0 ground beneath all 65
  sample points at cut 658→623, where the original baked surface reaches
  Z=1.70. A wall begins nearby, so this is not a clearance waiver. Following
  the initial CPU-pressure hold, one low-priority worker completed the
  baseline/detail comparison within the outer 120-second bound. Both tested
  mesh variations still fail the local grade criteria; neither replaces the
  copied baseline or authorizes F11.
- Controlled Crushbone full-zone bake comparison completed: identical
  copied source/baker reproduced all 65 baseline ground heights exactly.
  Halving horizontal cell size reduced the inner-ring error at 658→623,
  but the outer ring still exceeds grade 1.2 and warnings rose from 21 to
  128. Neither mesh gains movement acceptance. The private report SHA-256
  is `9af647dce65f4ebb2907e7008e22db2adf33a5451d98633d8e4361adce9b1fba`.
  Next: examine the source/detail footprint and warning locations before
  adopting any mesh; prioritize same-zone GFay for the first owner-run leg.
  No owner UI capture was found at this turn's check; live HP/scene/speed
  remain unverified, XP/hour and deaths unavailable, F11 disabled.
- Future G2 start-area preflight now converts the calibrated raw-WLD point
  to the retained helper navmesh's swapped XY frame before querying ground.
  A focused asymmetric frame test and all four G2-start tests passed. The
  preflight has no production caller; G2/F11 remain disabled. Its owner-run
  UI capture has not arrived, and live HP/current-position/scene/speed gates
  remain open.
- Corrected copied BSP frame: retained helper navmesh XY is the reverse of
  raw client WLD XY. Helper-mesh BSP route/ring artifacts through 0.41.39
  used the wrong frame and are superseded. Fixed 0.41.40 scans, with a
  pinned helper source and positive copied zone-line frame control, again
  found no labelled/unknown/unsupported spans on the GFay 155-segment
  approach (376 spans) and Butcherblock 249-segment approach (566 spans).
  Their SHA-256 evidence is in FINDINGS.md. Corrected frame checks also keep
  five of six GFay and 12 of 12 Butcher local spokes as static candidates;
  seven Butcher spokes exceed the diagnostic six-unit height band.
  Mesh-native turn/strip checks, the owner G0 stop and raw-WLD
  Kaladim local tile were unaffected. No live movement or F11 permit exists.
- Corrected Cauldron and Unrest helper-funnel BSP evidence: v2 hash-pinned
  scans found 224 plain spans over 81 Cauldron segments and 116 plain spans
  over 30 Unrest segments, with zero water/unknown. The prior Unrest water
  claim was a frame error and is retracted. These are straight funnels only;
  the Unrest turn/strip selector still lacks a complete route. A v2
  corrected-frame GFay→Butcher ground-prefix scan checked 52 segments and
  116 spans with no labelled/unknown/unsupported interval; its start is
  historical and it ends before the zone trigger.
- Level-7 Crushbone route blocker: the finer copied 0.25-detail mesh has an
  80-ground-polygon graph alternative avoiding suspect edge 658↔623, but
  its width-1.2/grade-1.2 selector rejects portal 3244→3242 after 41 turns
  and before full-strip checks. A bounded junction probe found fraction 0.20
  passes the seam and adjacent travel strips, but fails the conservative
  all-direction turn disk near a raised rock. A diagnostic bypass reached
  another failed turn at polygon 4316; it did not yield an accepted route.
  A larger candidate budget gave the original failure. A read-only directed-cut check shows that excluding both
  3244→3242 and 658→623 disconnects arrival from the Slaver goal; either
  edge alone leaves graph connectivity. Next: audit directed walking footprints
  through both cuts and prioritize the same-zone GFay camp; no F11
  route is ready. Current XP/hour remains
  unavailable, so the GFay orc camp remains a planning fallback only.
- Fresh level-1 source progress: South and North Kaladim zone/object archives
  and maps were copied read-only from the owner's client to the private store
  with matching SHA-256. Pinned offline scene composition produced South
  Kaladim OBJ `c9e0a3c9…` (23,854 faces) and North OBJ `ea49e4f4…`
  (30,591 faces). Copied maps and WLD terrain agree on the `-y,-x` frame;
  a South Kaladim BSP zone-line candidate is 30 units from its Butcherblock
  label. A 128-unit exit tile baked 50 provisional polygons; an offline
  six-polygon Detour query links the sampled zone-line point and map label in
  both directions, and copied BSP scans place the zone-line at one end. Exact trigger
  direction, fresh spawn, full route and real transition remain unverified.
  Next: derive a bounded South Kaladim corridor from an observed fresh spawn
  to that exit; retain F11 off. XP/hour and deaths
  remain unavailable; current camp is last reported GFay, unverified now.
- Low-level route progress: a bounded select-only run saved the 249-ground-
  polygon Butcherblock camp→GFay portal sequence; a separate hash-bound
  whole-strip audit passed all 249 copied segments. A separate copied-client
  BSP scan passed all 249 ground and ground+1 segments with 566 corrected-frame spans and no
  labelled, unknown or unsupported spans. Client traversal remains unverified.
  The default Butcher camp roam ring has four >6-unit height changes; a
  smaller 12-unit ring offers 12 one-polygon points that passed copied
  lateral strip and BSP checks, though seven exceed that height band. A
  smaller GFay orc ring keeps all six proposed points within about 2 units
  of its copied anchor; five one-polygon spokes passed strip/BSP checks and
  the sixth still needs a portal choice. Their live camps remain unaccepted. The
  guide markers are not client-certified positions. Current level remains
  last observed 7; XP/hour and deaths remain unavailable, and F11 is off.
- Private publish: source-only project **0.41.45**, commit `0503d58`, is
  staged under Alienware `~/.local/share/eql-automation/owner-tools/0.41.45`.
  Local/remote source archive SHA-256 matched
  `4e10cab4502313f3e1769af7699705188d0b4a9e8e51bab159946bf47b4e3d1e`.
  Remote builder startup passed; the offline navigation demo returned ARRIVED
  with `no_game_input=true`. Recommended assist remains **0.39.6**; separate
  G0 measurement candidate **0.39.7** adds the watchdog. No live character
  input was sent. The old G0 pass remains recorded, and G2/F11 stay off.
- Read-only UI progress: the installed Legira layout puts the HP gauge at
  `(1966,693,330,17)` at 2560×1600; the saved HP crop starts 32 pixels too
  high and spans 51 pixels. The 0.39.4 reader explicitly rejects its height
  before reading pixels; that explains `hp=None` but is not a live HP fix.
  Source 0.41.35 adds a pinned, owner-run, focused-window crop tool that
  saves private player/target/chat images with all G2 safety flags unknown.
  Source 0.41.38 adds a hash-pinned, read-only HP-crop analyzer that never
  enables healing or movement. Its local metadata/traversal tests passed;
  no live observation has been captured.
  The older Unrest entrance BSP water claim used the wrong frame and is
  retracted by the corrected scan. No connected safe continuation from its
  locally passable 3083 crossing is established by the turn/strip audits.
- Level-13–20 source dependency: the owner's Cauldron and Unrest zone/object
  archives were copied read-only to the approved private store, with all four
  remote/local hashes matching. Both zone WLDs passed bounded BSP region and
  raw terrain mesh inventories. All Cauldron 211 and Unrest 164 placements
  resolve to exact model definitions; provisional solid-face scenes were
  composed outside git. A material audit identified 2,442 Cauldron
  `Boundary` terrain faces and unclassified Unrest material modes; a second
  Cauldron scene excludes only those Boundary faces for later sensitivity
  comparison. Project 0.41.31 now reproduces all three copied-source scene
  variants through a hash-pinned offline CLI; each matches the previously
  recorded scene hash. Separate retained owner-helper Cauldron and Unrest
  navmeshes were then copied read-only; their manifest source hashes match
  the four copied archives, and each mesh hash matches its manifest. Cauldron
  has 14,832 polygons and 275 unclassified Recast warnings; Unrest has 3,254
  polygons and zero reported warnings. A dry Cauldron Butcher→Unrest graph
  corridor has 364 polygons, but 10 exceed 75° slope and two have <3 units
  center clearance. At least four threshold violations are unavoidable in
  this copied ground graph. Unrest entrance→yard has a 120-polygon dry graph
  corridor, but its sampled selector rejects narrow polygon 3083 under the
  default repair limits; a local shifted strip there passes. An expanded
  selector first stopped on a timed turn check under devbox load; with a
  larger bounded turn limit it passed 3083 and stopped at polygon 1605.
  The new bounded backtrack option fixes a synthetic connected-choice case;
  a copied Unrest retry with 32 repair rounds still stopped at polygon 1605.
  No complete selected sequence exists. The corrected copied funnel BSP
  scan is plain at both sampled heights, but checks no full strip. An
  Unrest yard→first-floor dry path has 59 polygons but steep/narrow sections.
  No water-safe crossing, client arrival, collision behavior or movement is
  accepted. Next: reconcile source/bake geometry and BSP at these failures,
  then run a bounded tile comparison when CPU pressure eases.
- Level-7 route focus: the existing guide's GFay orc camps are a same-zone
  fallback while the Crushbone Slaver corridor remains unaccepted. From the
  owner-run G0 spot, a copied-mesh dry route around two steep polygons has
  155 ground polygons, maximum copied detail-triangle slope 74.74° and
  minimum center clearance 7.64 units. A bounded lateral selector passed 169 turns, 175
  unique strips and the final whole-route check. A copied BSP scan found no
  labelled, unknown or unsupported spans across 155 segments at two heights.
  The guide marker, live camp, movement and current position remain unverified.
  The Butcher camp→GFay selector reached its final whole-route audit but
  exhausted one segment's time limit at polygon 49153; it did not pass.
  A rerun hit a local turn-audit work limit at the same polygon. A new
  249-ground-polygon dry detour avoids that polygon and prior steep/narrow
  polygons. Its first 420-second selector pass completed portal search after
  320 turns and 355 unique strips, but had no time for the final whole-route
  check. A diagnostic rerun hit its external 460-second timeout before writing
  an artifact. With devbox load above 240, another heavy run is deferred;
  the new fail-closed select-only phase will preserve unverified points before
  a later separate full-strip audit.
  Butcher mesh warning types/locations are absent from retained artifacts.
  Source inspection found the 0.39.4 owner preview lacks independent
  chat-closed, target-absent, combat-clear and incoming-attack-clear signals;
  G0 also does not establish a speed upper bound. Next: finish the lightweight
  source safeguards and private staging; when measured devbox load permits,
  use select-only then the separate final strip audit on Butcherblock.
  Implement and verify the missing owner-run safety/position measurements
  before a supervised short GFay movement test or any F11 route.
- Owner feedback check: the G0 trace appeared and is summarized below. A
  read-only 16:35 CST full scan of Legira's Alienware game log found mtime
  16:10:46 CST; its latest exact level-up message is the historical
  Oct 18 level-7 line. No later level-up message was found. The recent log
  excerpt did not supply a measurable XP/hour or current XP fraction.
- Owner-run 0.39.4 G0 **passed the short stop observation**: trace SHA-256
  `ec233e53ab37ef0245d78f98529ea264055c9c75b5a916f4d36a8c6171e3d7b1`
  records a 0.1508-second hold, 4.6407-unit displacement and zero
  post-release XY/Z drift across four location fixes; Blizz confirmed he saw
  the character stop. The first focus attempt did not start; the second
  succeeded. G2 speed, scene and route gates remain unverified.
  A read-only later snapshot of that trace is stored privately at SHA-256
  `f5d07cd4d424bad8b0f494a85cbf389823ee2c3445e497165a20aad9aca1ecc8`.
  Its four fresh GFay fixes locate on area-63 copied mesh at exact XY, with
  2.065–2.085-unit raw-character-Z to ground offsets. This is local alignment
  evidence, not a fresh G2 start or speed upper bound.
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
- VERIFIED copied artifact: the current Alienware helper's retained
  Butcherblock mesh SHA-256
  `4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde`
  was copied read-only into the private devbox store; its manifest source
  hashes match copied client archives. A 239-polygon dry camp→GFay route
  avoids seven steep/narrow polygons; its 236 ground segments have no copied
  BSP labelled/unknown spans at two heights. The lateral selector stops at
  polygon 37736 after 92 turn checks with no sampled turn candidate. The
  mesh reports 1,180 Recast warnings; no client route is accepted.
- VERIFIED offline: penalizing that failed directed turn and the seven prior
  steep/narrow polygons found a different 237-polygon Butcher camp→GFay
  dry path with no ground center slope above 75 degrees or center clearance
  below 3 units. Its first uncached lateral selector run exhausted the
  180-second global work limit at polygon 38947 after 240 turns/358 strips,
  before a route result. The selector now caches identical strip checks;
  a same-window run reached polygon 14525 (index 155/234) after only 182
  unique strips and then exhausted the 180-second limit. A 360-second
  bounded rerun completed portal search with 260 unique strips but its final
  whole-route audit hit a per-segment time limit at polygon 49153. No F11
  route is accepted.
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
- Private publish: source-only project 0.41.27 commit `145ca43` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.27`.
  Local and remote archive SHA-256 matched
  `ac794491e379dc89afd2b112200be2f60a6bcf652a5de55c23752f738cf40e81`.
  Its remote `--demo-navigation` and trace summarizer `--help` startup
  smoke passed with no game input. The local 0.41.26 archive was superseded
  before staging. Owner-run assist/G0 remains 0.39.4; F11 remains disabled.
- Private publish: source-only project 0.41.28 commit `a89c8a5` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.28`, outside
  the game install. Local and remote archive SHA-256 matched
  `3bd296f75247ca7e6ac4486063b96c2fabfba9566ccee8e7e68c29c30d39be83`.
  Remote `--demo-navigation` and copied-route CLI `--help` passed with no
  game input. The runnable owner assist preview remains 0.39.4; F11 remains
  disabled.
- Superseded before staging: local source-only 0.41.29 commit `fbde3ca`
  archived at SHA-256
  `88e15c983dae61efaa801c60a0cc90f49377d4ff18e81184614d78c7f43aa72c`.
  An Alienware SSH attempt to create its private staging directory timed out
  on port 22; remote transfer and smoke were not run for that version.
- Private publish: source-only project 0.41.30 commit `205ac2f` was staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.30`, outside
  the game install. Local and remote archive SHA-256 matched
  `1af2f47b38301495f4088cabd8f8ced6be128aaf9f3f7262a2cd00298fa03638`.
  Its remote `--demo-navigation` and both copied-route CLI `--help` startup
  checks passed with no game input. It supersedes the unstaged 0.41.29
  archive. The runnable owner assist preview remains 0.39.4; F11 stays off.
- Private publish: source-only project 0.41.31 commit `b8ddbe4` is staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.31`, outside
  the game install. Local and remote archive SHA-256 matched
  `852dd756c6e655ccf550f7894c7afdfd4f0a43a53f12f917bc65969604b6a96f`.
  Remote `--demo-navigation` returned `simulation_only=true` and
  `no_game_input=true`; the new scene CLI appeared in remote `--help`.
  The owner-run assist preview remains 0.39.4; F11 stays disabled.
- Private publish: source-only project 0.41.32 commit `002e7ad` is staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.32`.
  Local and remote archive SHA-256 matched
  `1f28f20664b696c32318e9c5bfa8d9a5083f5697e16aa7eb247553f8fe243577`.
  Remote offline navigation startup and extended route-CLI help passed with
  no game input. The runnable owner assist remains 0.39.4; F11 is disabled.
- Private publish: source-only project 0.41.33 commit `5507bd1` is staged
  under Alienware `~/.local/share/eql-automation/owner-tools/0.41.33`.
  Local and remote archive SHA-256 matched
  `68dc233a698905844f02f782fd048da79430f10682476f05731d3a44cb5bd3e0`.
  Remote offline navigation startup and backtrack CLI help passed with no
  game input. It supersedes 0.41.32 as the current source build; owner assist
  preview 0.39.4 and disabled F11 are unchanged.
- Real-client XP / XP per hour: n/a. Current-level XP fraction / percentage points per hour: n/a. Deaths: n/a (no observed full run). Camp: not observed; Greater Faydark is the last reported zone. GFay orc camps are the nearest level-7 route candidate, not an accepted active camp. The copied owner log reports one item did not fit and food/drink out; a later belt sale does not prove bag capacity was restored.
- Build: local source 0.41.38 (pinned low-level camp-ring diagnostics and private HP capture analysis, plus the earlier UI capture) and isolated owner-run assist/G0 preview 0.39.4 staged outside the Alienware game install. Earlier source releases and historical build details are recorded above. Mode boundary, prior rotation planner reuse,
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
  F8/F9 owner test. F11/F12 are excluded because movement gates were unrun
  and a prior continued-walking report remained unresolved at that time.
  The later 0.39.4 G0 short stop passed; full route gates remain open.
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
  passed; no owner G0 result had been observed then. The later 0.39.4 G0
  result is recorded at the top of this file. A separate offline
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
- Current blocker: the owner-observed F8 rotation fired, but HP remained null
  and `/attack off` was rejected. A new owner-run UI crop has not arrived.
  Strict current ASSIST still lacks a unique target and
  verified chat-draft observation. Full-auto F11 needs confirmed native melee
  stop, G2 speed/scene/follower acceptance after the passed G0 short stop check,
  validated runtime mesh-store binding,
  integration of the offline reachable-camp patch and a level-11 camp; real-client acceptance also lacks the intended
  private endpoint/client configuration. Owner says the target is private, but its endpoint/client
  configuration is missing. The only located Alienware EQL client still points
  to Daybreak's official live login host. The lead will not send automated
  connection or character input to that host. Bounded devbox/Banshee process, listener, container and
  directory checks found no private EQEmu/EQL candidate; this does not rule
  out another machine or path. Daybreak rules prohibit unattended play and unauthorized
  servers; no Daybreak-authorized live test route is documented. The historical
  Butcherblock navmesh/recipe with the historical serialized hash is absent
  from the approved retained store; a distinct current-helper mesh is copied
  and under review. The reported GFay vertical mismatch on its historical route and
  conservative clearance failure remain unresolved. No actual client
  acceptance is ready. The 0.39.4 assist/G0 preview is privately staged on
  Alienware outside the game install; full auto has no playable release yet.
- Next step: prioritize a playable level 1–20 leg. The later Butcherblock
  249-polygon detour passes offline strip and BSP checks; evaluate the
  retained mesh's 1,180 warnings and live terrain before accepting movement. Build the
  owner-run G2 measurement with independently verified current position,
  speed and scene guards, using the passed G0 short stop result as one input.
  First obtain the pending read-only owner UI capture to calibrate HP and
  independent scene indicators. When he next crosses
  GFay→Crushbone manually, obtain a
  fresh `/location` on each side and compare the destination observation to
  the copied mesh without calling it a verified spawn. Keep F11 off until
  G2, current-position observation, transition and follower evidence pass.
  A bounded owner-run G2 straight-motion measurement must use the isolated
  pulse bridge, fresh client scene observer and stop guards; the geometry
  preflight alone does not permit it.
  Build an observed autoattack state/stop acknowledgment gate for
  full auto, then bind the copied mesh store in a separate owner-run route
  trial after G2 checks and resolve the narrow GFay/Crushbone corridors.
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
