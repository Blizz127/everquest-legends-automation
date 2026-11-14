# STATUS

Updated 2026-11-14 02:59 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No real-client 1–20 route or automated level gain
  is accepted. Fresh-character hands-off 1–50 and strict assist remain required.
- Current level, XP, XP/hour, deaths and camp: **unknown**. Last read-only log
  snapshot remains stale: historical level 7, Greater Faydark, six historical
  deaths, last award 2.574%. These do not establish current run metrics.
- Owner G0 visible stop is confirmed; no repeat requested. Runnable assist
  remains 0.39.6, reusing the existing rotation bot: F8 rotation, F9 stop,
  F10 heal; manual movement/target/loot/vendor/camp and native melee.
  F11/F12 are disabled. Live HP and target/chat identity remain unverified.
- Source **0.41.59** is privately staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.59/source`, commit
  `c783b99`. Archive SHA
  `7e0ec71d7dd30128f466f782692aa60621e71ab46308c4645184e09856edaa16`
  matched, and six no-input remote checks passed. **VERIFIED:** 64 focused
  checks pass. The copied GFay follower reaches segment 125 of 155/step 1,820,
  after fixing a ground-support comparison against a platform 74 units overhead.
  Terrain occupancy still includes all heights. It now refuses baked face 166882
  at grade 2.08764 against limit 1.0, even at the minimum hypothetical pulse.
  Artifact SHA `0a551dc6fa248ea7c118e2da7ece168c3150ab92f520460eb3f0aff6f8f5add0`.
- New source reader counts exact logged gross XP-percentage awards, resets
  its window on level/death/zone/log changes and never fabricates raw/net XP.
  It is not yet connected to the assist GUI or camp ranking; no current rate
  is inferred from the stale owner log.
- **Next:** repair or avoid the segment 125 baked slope, add correctly transformed
  static-placement occupancy, then continue the checked owner-preview route
  integration. Same-zone GFay is prioritized for Legira; Butcherblock then
  Crushbone for a fresh run, later camps by actual level, XP rate and safety.
- **Real-client gate:** fresh independent scene, position/height and speed
  calibration, full collision/hazards and checked sender integration.
  Current-zone/UI readiness remains pending; no capture is retried. Retail
  install points to Daybreak; intended private endpoint is unidentified.
  Owner drives live sessions; the lead does not log in or mutate characters.
- HOWTO and LEVEL_1_20 record current availability and limitations. No git push,
  input/device use, access change or game-install modification occurred.
