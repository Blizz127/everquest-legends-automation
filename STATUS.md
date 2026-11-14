# STATUS

Updated 2026-11-14 03:21 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No real-client 1–20 route, automated level gain
  or fresh-character hands-off 1–50 run is accepted.
- Current level, XP, XP/hour, deaths and camp: **unknown**. The last read-only
  log snapshot is stale (historical level 7/Greater Faydark, six historical
  deaths, last award 2.574%); it cannot establish current run metrics.
- G0 visible stop is owner-confirmed; no repeat requested. Assist remains
  **0.39.6**, reusing the existing rotation bot: F8 rotation, F9 stop, F10 heal.
  Movement/target/loot/vendor/camp and native melee remain manual. F11/F12
  are disabled. Live HP and target/chat identity remain unverified.
- Source **0.41.60** is privately staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.60/source`, commit
  `d8f8f41`. Archive SHA
  `6e04dd724a7d79f142e4da55a4c386bfd659072081dafbbf5c5d115eb7c0f948`
  matched; nine startup/guard checks plus eight synthetic static tests passed
  remotely without client/input access. **VERIFIED:** repaired GFay
  terrain replay arrives through all 155 segments in 2,191 steps, with no
  geometry refusal or budget exhaustion. It took 356.25 wall/86.31 CPU seconds.
  Artifact SHA `87457cb38f7474c54afccdcda186266153d2f10179cc50f39dc3c3d35669da84`.
  These are conditional simulated terrain checks, not accepted live movement.
- **VERIFIED:** 2,799 copied static placements produce 109,932 all-flag faces.
  Their 57,751 nondegenerate solid triangles match the retained bake exactly.
  The cell-bound static guard is prepared but not yet in follower replay.
  88 focused checks pass; dynamic objects and actual collision remain unverified.
- **Next:** integrate static occupancy per replay trial, then complete hazard,
  independent live scene/position/height/speed and checked sender checks.
  Same-zone GFay remains the practical Legira candidate; Butcherblock then
  Crushbone for a fresh run, later camps by observed level, XP rate and safety.
- **Real-client gate:** fresh current-zone/UI readiness remains pending; no
  capture is retried. Owner drives live sessions; the lead does not log in
  or mutate characters. Retail points to Daybreak; private endpoint unidentified.
- The exact gross XP-gain reader remains separate from the assist GUI and camp
  ranking. No rate is inferred from stale logs. HOWTO/LEVEL_1_20/FINDINGS are
  current. No git push, game input, access or game-install change occurred.
