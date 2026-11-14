# STATUS

Updated 2026-11-14 02:44 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No real-client 1–20 route or automated level gain
  is accepted. Fresh-character hands-off 1–50 and strict assist remain required.
- Current level, XP, XP/hour, deaths and camp: **unknown**. Read-only owner
  snapshot at 02:41 UTC found the last log write at Nov13 22:10 UTC, historical
  level7 and latest zone Greater Faydark. Six deaths are historical, latest
  Oct20. Last logged XP gain was Nov13 09:27:56 (log time), 2.574%. These do
  not establish current run metrics. No game input or screenshot was sent.
- Owner G0 visible stop is confirmed; no repeat requested. Runnable preview
  remains **assist 0.39.6**, reusing the existing rotation bot. F8 rotation,
  F9 stop, F10 heal; movement/target/loot/vendor/camp stay manual. F11/F12 are
  disabled. Separate G0 candidate 0.39.7 is unchanged. Live HP, target/chat
  identity and native melee stop remain unverified.
- Source **0.41.58** is prepared for private staging. **VERIFIED:** 27 focused
  floor-chain/occupancy tests pass. The complete copied GFay source chain
  passes all 2,399 cells, tracking 266 faces through 268 exact-edge join
  events. All source layers remain in each occupancy check. Body height8 is
  hypothetical; placed objects/dynamics and live start identity are unverified.
  Artifact SHA `06c0a1d0818826ca0913e94a05b26912f9be05b994fa328230857b42dd04a497`.
- The first exact implementation reached 1,147 passing cells before its time
  budget. Exact-arithmetic optimizations completed all 2,399 in 141.55 seconds;
  no tolerance was relaxed. This is a conditional terrain result, not full
  collision or route acceptance. Existing replay still stops at segment87
  until the new selection is bound into its source observations.
- **Next unblocked work:** bind the floor chain into offline replay, measure
  source/baked differences and address remaining baked slope failures; add
  static placements with correct transforms and unique face identity. Add a
  gross client-reported XP-percentage gain reader using the observed log format.
  Prioritize same-zone GFay for Legira; Butcherblock then Crushbone for a fresh
  run, later camps by actual level, XP rate and safety.
- **Real-client gate:** fresh independent scene, position/height and speed
  calibration, complete collision/hazards and checked sender integration.
  Current-zone/UI readiness remains pending; no capture is retried. The retail
  install points to Daybreak and the intended private endpoint is unidentified.
  Owner drives his live session; the lead does not log in or mutate characters.
- HOWTO has the current assist launch and controls. Full evidence and private
  artifact hashes are in FINDINGS.md. No git push, access or game-install change.
