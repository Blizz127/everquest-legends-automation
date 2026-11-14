# STATUS

Updated 2026-11-14 03:33 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No real-client 1–20 route, automated level gain
  or fresh-character hands-off 1–50 run is accepted.
- Current level, XP, XP/hour, deaths and camp: **unknown**. The last read-only
  log snapshot is stale (historical level 7/Greater Faydark, six historical
  deaths, last award 2.574%); it cannot establish current run metrics.
- G0 visible stop is owner-confirmed; no repeat requested. Assist remains
  **0.39.6**, reusing the existing rotation bot: F8 rotation, F9 stop, F10 heal.
  Movement/target/loot/vendor/camp and native melee remain manual. F11/F12
  are disabled. Live HP and target/chat identity remain unverified.
- Source **0.41.61**: **VERIFIED** conditional GFay terrain plus static-object
  replay arrives through all 155 segments in 2,191 steps. Every motion
  footprint passes; 1,014 queries contain static faces. All 39 pins rechecked.
  Elapsed 477.44 wall/103.18 CPU seconds, no refusal or budget exhaustion.
  Artifact SHA `359a0caf5257c0eb96669a7a59bad4fbba4de7e580b93601f8b49ac69183c5ef`.
  This is simulated copied geometry, not accepted live movement or dynamics.
- A new owner-run location/map collector sends no input, skips old log bytes,
  omits the chat crop and preserves unknown zone/alignment/character identity.
  It pairs a manual fresh `/location` with UI crop timing without another G0
  pulse or zone transition. 48 focused tests and 14 local smoke checks pass.
  Actual paired capture has not been run. Source commit `b5cd4a5` is staged at
  Alienware `~/.local/share/eql-automation/owner-tools/0.41.61/source`; archive
  SHA `06896aff0ba6794a9ee394906171de5e4e9c685021e81fa1aded7c48298baf15`
  matched and all 14 no-input remote startup/guard checks passed.
- **Next:** whole-footprint BSP hazard checks, owner-run fresh scene/position
  observation, bounded speed/drift measurement and checked sender integration.
  Same-zone GFay remains the practical Legira candidate; Butcherblock then
  Crushbone for a fresh run, later camps by observed level, XP rate and safety.
- **Real-client gate:** fresh current-zone/UI readiness remains pending; the
  lead has not retried capture. Owner drives live sessions; the lead does not
  log in or mutate characters. Retail points to Daybreak; private endpoint
  unidentified. Publishing this diagnostic does not authorize movement.
- The exact gross XP-gain reader remains separate from the assist GUI and camp
  ranking. No rate is inferred from stale logs. No git push, game input, access
  or game-install change occurred. HOWTO/LEVEL_1_20/FINDINGS are current.
