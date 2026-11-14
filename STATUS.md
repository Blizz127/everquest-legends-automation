# STATUS

Updated 2026-11-14 06:07 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No accepted real-client 1–20 route, automated
  level gain or fresh-character hands-off 1–50 run. Current level, XP,
  XP/hour, deaths and camp remain **unknown**; historical Legira level 7/GFay
  and old log awards/deaths are not current run metrics.
- **G0 passed:** owner-confirmed visible stop plus trace evidence; no repeat.
  Current assist remains **0.39.6**, built on the existing rotation bot:
  F8 rotation, F9 stop, F10 heal. Movement, targeting, native melee, loot,
  vendors and camps remain manual; F11/F12 are disabled. Live HP/chat/target
  identity still need acceptance.
- **Source 0.41.77:** concrete location/pulse executors now reuse the retained
  bot's actual sender and watchdog with shared stop locking and original-device
  cleanup. Fifty-six focused checks pass, including F9 during a pipe pulse and
  failed release after device replacement. The full pipe experiment completed
  16 commands, seven pulses, eight stopped pairs and 696 events. All scene and
  position feedback was synthetic; artifact SHA
  `803f19f60bd4c1433ba35ebd7f45f0c768ee1c2b7d8f23500e1c85f6bb127747`.
  No live provider/control is enabled. Private source staging follows these
  checks; owner assist and observation versions remain unchanged.
- **Source 0.41.76:** finite collection is integrated with the retained helper
  tick chain, with explicit external command/pulse executors and no owner
  control enabled. Sixty-four focused checks pass. A real watchdog pipe run
  with synthetic log feedback completed seven pulses/eight stopped pairs;
  artifact SHA `457f809c1baf1b85dcdfda05dc68b65f3dcf07430e5a5e9d09d8a25ed6a23f3e`.
  An earlier 0.2176-second hold exceeded the 0.20 limit and was rejected; its
  partial receipt evidence is retained. Results save independently of tracing.
  Source `cb5dbc4` is privately staged at `owner-tools/0.41.76/source`; seven
  remote no-input startup checks pass. Archive SHA
  `97a85859153e3ea85998958f90bce1fa20fd625eeae8e069e6ce4dad4bf606e3`.
- **Source 0.41.75:** an offline receipt/stopped-position estimator now reuses
  the existing bot's bearing and turn fitter without prior speed/heading/rate.
  It preserves timing/error assumptions and rejects inactive short turns before
  the legacy latency clamp. Sixty focused tests plus 20 subtests pass,
  including real watchdog pipe writes with simulated positions. The follower
  permits zero backward speed because it never requests backward movement.
  No verified travel ceiling, live calibration or new input is enabled.
  Source `6e9139d` is privately staged at `owner-tools/0.41.75/source`; five
  remote synthetic/no-input startup checks pass. Archive SHA
  `3ad452339379a7e8a3d32a6db38f01361562b30f4ae4b92bc93705d776761a33`.
- **Source 0.41.74 / observation candidate 0.39.10:** automatic icon analysis
  is now connected to the existing owner capture flow. The raw pair is saved
  first and survives analysis failure. Eighty-seven focused checks and actual
  helper synthetic-engine/offscreen-GUI smokes pass. Candidate is staged at
  `owner-assist/0.39.10`; archive SHA
  `e3430fd77c1a55601af338222d0a6ec1f808204964be0fd84b1fc6c52eb8a89d`.
  No real capture/input/login occurred; existing settings were unchanged.
- **Source 0.41.73:** exact batched template scoring preserves complete
  0.41.72 output in ten source-icon synthetic cases. Thirty-one focused tests
  pass. Devbox median search is 86 ms versus 1.22 seconds; maximum is 283 ms,
  so the full live scene budget remains unverified. No new owner test or input.
  Source `01bc41e` is privately staged at `owner-tools/0.41.73/source`; six
  startup checks pass. Alienware synthetic search: 22.7 ms cold, 12.7 ms warm
  median, 14.0 ms warm maximum across 20 cases. No live capture/scene acceptance.
  Archive SHA `9a384402c17987579306844da88b529eb900e5ed9f44dbfae8796e7f85aa90a2`.
- **Source 0.41.72:** saved combat-icon analysis now connects the client atlas
  to the existing observation format. Twenty-three focused tests pass; 10/10
  synthetic renderings of actual source icons rank correctly. Crops and source
  XML are pinned and parent/child pixels checked. Results select no live state;
  active rendering/texture identity and the live scene budget remain unverified.
  Source `e597f2d` is privately staged at `owner-tools/0.41.72/source`; six
  synthetic/no-input Alienware startup checks pass. Archive SHA
  `3106ff4a7fc75c675895fb1c99f76b1d1462e8bba8ef71db871fddf4d67d45b6` matched.
  Assist remains unchanged.
- **Source 0.41.71:** latched positive-hazard log monitoring now brackets
  measurement scene observations. Quiet logs never grant safety. Eighty focused
  reader/provider checks and three actual-watchdog pipe cases pass. The retained
  log audit finds 4,350 incoming attacks, including 1,336 singular-damage lines
  missed in the initial audit and now covered. No owner input/capture occurred.
  Source `a797673` is privately staged at `owner-tools/0.41.71/source`; six
  synthetic/no-input Alienware startup checks pass. Archive SHA
  `1942a0318cd706afe6de17247a70beae95a745f326ecd8bddcc7441531064212` matched.
  Owner assist is unchanged.
- **Source 0.41.70:** **VERIFIED** client-derived combat/attack atlas: 11
  frames extracted from fresh default_light assets; 13 focused tests pass.
  The updated installed executable was copied read-only and its icon selector
  inspected statically. Standing also appears on a null-player fallback;
  that match alone cannot establish scene safety. No live classifier enabled.
  Source `7ff2503` is privately staged at `owner-tools/0.41.70/source`; six
  no-input remote startup checks pass. Archive SHA
  `a4b7f3ddcc1bc60724c810bb1c3a24d7b8b5695c19bb169aac6c30a6c3c0827b` matched.
- **Client update reconciled:** executable is now `fe41a8db…7146bf36` and
  spell file `c179a57f…236c8e9`. Seven checked navigation archives still match.
  The new spell file has two added and 18 changed rows; Paladin/Cleric 1–20
  rows and candidate rotations are unchanged. Refreshed 16-class private
  index built. No owned-spell/server/casting or movement acceptance claimed.
- **Checked sender 0.41.69:** 67 focused checks passed previously. It requires
  current scenes, measured whole-motion authorization and final release before
  committing a step. It remains separate from owner runtime controls.
- **Completed printed-feedback replay:** **VERIFIED** all 155 segments and
  2,323 simulated steps arrive with all terrain/static/BSP trials passing.
  All 2,324 stopped observation pairs pass; 48 pins rechecked. Artifact SHA
  `b70de7f0f9bfa193ce83e1b9bcee3d16be63b8920357a9c49e622e8b4de0f603`.
  Runtime 508.42 wall / 147.50 CPU seconds. The prior 600-second checked prefix
  remains retained. No replay process is still running. Physical pose/heading,
  body, speed and drift are simulation assumptions; no live route is accepted.
- **Observation candidate 0.39.10** uses the same **Observe current position**
  button and manual `/location` flow. It additionally saves private copied
  templates and `combat-analysis.json`; missing sources preserve the raw pair.
  Old 0.39.9 pairs remain valid for separate analysis. Read-only listing this
  turn (2026-11-14 05:56 UTC) found zero paired records. No lead capture was initiated.
- **Next / real-client gate:** validate the source-derived scene templates against the
  pending owner capture; bind the new conditional motion estimator to an independently supported
  initial travel envelope and current scene, then supply the checked sender
  with measured whole-motion bounds; obtain the
  pending owner scene/position evidence and current zone/frame/height/speed
  calibration. Source-ground production, checked-step adapter and receipt bookkeeping exist;
  live providers and owner control wiring remain incomplete. The finite collector
  now runs on helper ticks with concrete checked executors; independent live
  scene/envelope providers are still required and none is enabled by default. No new owner test
  is requested, and the existing stationary capture remains pending.
- Same-zone GFay is the practical Legira candidate; Butcherblock then Crushbone
  for a fresh run, later camps by observed level, XP rate and safety. Owner
  drives live sessions. Retail points to Daybreak; private endpoint unknown.
