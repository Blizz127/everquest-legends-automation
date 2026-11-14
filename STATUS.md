# STATUS

Updated 2026-11-14 02:30 UTC for coordinator task `829a00229b29`.

- **Working; goal not met.** No accepted real-client 1–20 route or automated
  XP gain. Fresh-character hands-off 1–50 and strict assist are still required.
- Current level, XP, XP/hour, deaths and camp: **unknown** beyond the owner's
  last report, Legira level 7 in Greater Faydark. No current live session was
  read or driven during this source work. Owner confirmed the short G0 visible
  stop; its retained trace agrees. No repeat is requested.
- Current runnable owner preview: **assist 0.39.6**, reusing the existing
  rotation bot. F8 rotation, F9 stop, F10 heal; movement/target/loot/vendor/camp
  remain manual. F11/F12 are disabled. Separate G0 candidate 0.39.7 is unchanged.
  Live HP, target/chat identity and native melee stop remain unverified.
- Source **0.41.57** is prepared for private staging. **VERIFIED:** 67 focused
  tile/precision/occupancy tests pass. An exact manifest-bound float32 model
  matches all 2,771 examined reciprocal tile discrepancies. It does not widen
  an arbitrary ULP tolerance. No client assets or existing mesh are changed.
- **VERIFIED copied-data replay:** explicit tile/overlap/source-height-2.0
  diagnostic reaches segment 87 of 155, step 1,151, then stops on layered
  source floors. Replay SHA
  `c6234c0df3c94b906e150a9c0940857328b325364f24f6eade8b9b12db6486ff`.
- **VERIFIED conditional geometry:** three copied cells pass explicit body
  hypotheses 6 and 8 when the supporting grass is selected. Vertical walls
  and all supplied source layers remain in the occupancy check; exact floor
  coverage rejects even tiny gaps. Actual floor-chain/body/full-inventory
  verification remains false. This is separate from existing refusal rules.
- **VERIFIED full-width profile:** all 2,399 cells checked; 2,195 pass,
  204 refuse (177 source layers, 16 materials, one missing/over-budget source,
  three source slopes, seven baked slopes). First failure: 87/49. No whole
  region height bound is accepted. Profile SHA
  `e5dd717c1bd93770d3ec8419dc948efe0c1ebf3f789297533520bdeae0ed4fbd`.
- **Next unblocked step:** propagate an explicit source-floor identity through
  ordered route cells using shared 3D edges and complete occupancy checks.
  Measure the full corridor after tile classification; route around actual
  obstructions. Butcherblock first, Crushbone next, later camps by observed
  level/safety; the same-zone GFay orc route is the immediate Legira candidate.
- **Real-client gate:** fresh independently identified scene, position/height
  and speed calibration, complete collision/hazard checks, plus checked sender
  integration. The current-zone/UI readiness request remains pending; no
  capture is retried without readiness. The installed retail client points to
  Daybreak; the private endpoint is still unidentified. Owner drives his live
  rotation session; the lead does not log in or mutate his character.
- HOWTO contains the current launch and controls. Historical collision,
  release and verification evidence is retained in FINDINGS.md and git.
  No remote git push, device input, account or game-install change occurred.
