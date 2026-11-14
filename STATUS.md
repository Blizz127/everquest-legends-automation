# STATUS

Updated 2026-11-14 03:58 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No real-client 1–20 route, automated level gain
  or fresh-character hands-off 1–50 run is accepted.
- Current level, XP, XP/hour, deaths and camp: **unknown**. The last read-only
  log snapshot is stale (historical level 7/Greater Faydark, six historical
  deaths, last award 2.574%); it cannot establish current run metrics.
- G0 visible stop is owner-confirmed; no repeat requested. Assist remains
  **0.39.6**, reusing the existing rotation bot: F8 rotation, F9 stop, F10 heal.
  Movement/target/loot/vendor/camp and native melee remain manual. F11/F12
  are disabled. Live HP and target/chat identity remain unverified.
- Source **0.41.63** / isolated candidate **0.39.8**: **VERIFIED** read-only
  input observation is wired into the existing helper job/tick/cancellation
  lifecycle. 83 local focused checks pass; synthetic actual-engine and
  offscreen GUI smokes also pass on Alienware. Candidate privately staged at
  `~/.local/share/eql-automation/owner-assist/0.39.8`; archive SHA
  `9516de9e4423c91599938db72ed685df8c155ee7d7840127d22de6f992144ba5`.
  It sends no game input and always reports movement unavailable; live
  observation through this new integration is not yet accepted. Source commit
  `6cc87d1` is also staged under `owner-tools/0.41.63/source` with three no-input
  startup checks; archive SHA
  `e9e152b191882309f6fd4a7f8552cd069225e534bde26ce91371b898b27f093a` matched.
- Source **0.41.62**: **VERIFIED** conditional GFay terrain, static-object and
  whole-prism BSP replay arrives through all 155 segments in 2,191 steps.
  All 2,191 BSP checks pass (28,837 node visits, max 27 per prism). Both terrain
  and static trials match the prior run; all 44 pins rechecked. Elapsed 440.80
  wall/117.85 CPU seconds, no refusal or budget exhaustion. Artifact SHA
  `ff21dfa92e8dbd391002512ed7d5950280655ac066b3967b0e0d8b9ee4af6319`.
  This is copied geometry under hypothetical movement/body bounds, not live
  dryness, dynamic obstacles or movement acceptance. 50 focused tests and
  11 local and remote no-input startup/guard checks pass. Source commit
  `8ddde9b` is privately staged at Alienware
  `~/.local/share/eql-automation/owner-tools/0.41.62/source`; archive SHA
  `e6fb63e2d9a417bc3d5f51276b0133f53e308f45e8eca4a8e65e40b9656e8ebd`
  matched.
- The owner-run location/map collector remains at source **0.41.61** on
  Alienware. It sends no input and records explicitly unknown zone/alignment/
  character identity. The pending command in HOWTO is unchanged. A read-only
  directory check found no paired record at 03:37 UTC; no capture was retried.
- **Next / real-client gate:** fresh scene/position evidence; integrate the existing
  owner-run location/UI collector into helper ticks, then stationary-zone/ground
  and UI providers, bounded speed/drift and checked movement. Those providers
  remain unwired; the completed offline geometry cannot enable F11 by itself.
- Same-zone GFay remains the practical Legira candidate; Butcherblock then
  Crushbone for a fresh run, later camps by observed level, XP rate and safety.
  Owner drives live sessions; the lead does not log in or mutate characters.
  Retail points to Daybreak; private endpoint unidentified.
- Gross XP-gain telemetry remains separate from the assist GUI and camp ranking.
  HOWTO/LEVEL_1_20/FINDINGS are current. No git push, game input, access or
  game-install change occurred.
