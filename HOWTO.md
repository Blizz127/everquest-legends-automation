# EverQuest Legends automation — project 0.41.60 / assist 0.39.6 / G0 candidate 0.39.7

## Current availability

This project's full-auto bot remains an **offline simulator and planning
library**. An isolated, owner-run rotation preview 0.39.6 is staged on the
Alienware outside the game install. Blizz runs the game and helper himself;
the lead has not logged in or sent game input. The installed client points to
Daybreak's live service. Its published
[Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct),
[EULA](https://www.daybreakgames.com/eula?locale=en_US), and
[Terms of Service](https://www.daybreakgames.com/terms-of-service?locale=en_us)
prohibit the requested unattended bot and appear to prohibit a rotation assist
on the live service without Daybreak authorization. The owner says the target
is a private server, but its endpoint has not been found; the installed retail
client still points to Daybreak. Strict live ASSIST and FULL AUTO are not yet
validated. The owner chose to test rotation himself on live.

The prioritized [level 1–20 route record](LEVEL_1_20.md) starts with
Butcherblock, then Crushbone and Unrest as the character's observed level
allows. These are planned camps; no leg is accepted for F11 yet.
Source tools 0.41.60 use the private Alienware path
`~/.local/share/eql-automation/owner-tools/0.41.60/source`; the runnable
rotation helper is separately staged under `owner-assist/0.39.6`.

Source 0.41.60 completes the revised copied GFay terrain replay: all 155
segments arrive in 2,191 idealized steps. Four relocated crossings avoid narrow
steep baked triangles, and exact tile-gap correction preserves the ground and
source-height checks. This is an offline result under hypothetical movement
and body bounds. The new static-instance adapter reproduces all 57,751 solid
object triangles used by the retained bake; its separate occupancy guard is
prepared but has not yet been connected to the full follower replay. Dynamics,
fresh scene/position/speed and real movement remain unverified. 88 focused
checks pass. F11 stays unavailable; no live 1–20 leveling is claimed.
Your G0 stop remains passed. Assist 0.39.6 is unchanged and no new owner command
is requested. The source XP-gain metric is still separate from the assist GUI.

Detailed source-release history and hashes are in [FINDINGS.md](FINDINGS.md).
The current playable-route status is in [LEVEL_1_20.md](LEVEL_1_20.md).

## Owner-run rotation test on Alienware today: preview 0.39.6

Close any already running Solo Assist window. Blizz starts the game through
Lutris and logs in himself. In an Alienware terminal, start the isolated
preview:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.6
EQL_ROTATION_TRACE="$HOME/eql-assist-trace.jsonl" ./launch.sh
```

The GUI starts disarmed. Blizz chooses his character and current level there.
At full HP, click **Find / calibrate HP**. The saved client layout proposes
the inner red gauge. Check the captured character and highlighted rectangle;
click **Save** only if it covers that full red gauge. If needed, drag a new
rectangle from left to right, 5–24 pixels tall, excluding frame, text and mana.
Missing, hidden, minimized or offscreen layouts fall back to manual selection.
An unreadable preview or one below 85% cannot be saved; confirm actual full
HP before pressing Save. The suggested layout
is re-read at Save; a changed rectangle cancels that save.
The older 51-pixel-tall saved HP crop is rejected in this preview. Check that
the Combat tab shows a plausible full HP reading before combat. If HP remains
unknown or falls below 10%, heal manually; the preview treats those readings
as unknown rather than guessing. The trace is saved in
`~/eql-assist-trace.jsonl` for owner feedback.
If HP remains unknown, the gauge now says whether to select the 5–24px
inner red bar, restore the calibrated window size, or recalibrate because
the red fill was not recognized. It never fills in a missing HP value.
**F6** explicitly refreshes and memorizes the spell bar while out of combat.
He selects and moves to the target himself. **F8** arms the spell and ability
rotation on that target; **F9** stops it; **F7** toggles; **F10** requests a heal.
F8 does not prepare gems or select a target. The helper's STOP button or
closing its window ends the test. The preview suppresses all helper `/attack`
commands: **Blizz controls melee himself, and F9 does not turn off native
melee.** Use the game's own attack control to stop it and verify it is off.
If an interrupted command prevents F8/F6 from working, press F9 and close
its chat draft in EverQuest yourself. In the helper, click **Chat recovery…**
and confirm that the chat entry is closed. It sends no game input, discards
old queued starts, and stays OFF until your next F8. Cancel does nothing.
F11 movement and F12 route recording are disabled in this preview. The helper
does not move, retarget, loot, vendor or camp. Do not run two helpers at once.

The preview's HP reader checks a narrow colored band and rejects short red
accents, broad saved crops and readings below 10%. These checks and its source
guard passed a no-input Alienware smoke, but live HP reading and smart healing
remain **unverified**. The preview still uses `/consider` to review the
owner-selected target and inherits unverified chat-draft/target-identity
behavior; it is a supervised test, not accepted strict ASSIST. F9 displays
that rotation is off and melee is manual.

**OBSERVED owner test of the original November helper:** F8 cast armor,
Yaulp, Bash, stun and four nukes; gem preparation and focus checks worked.
Early HP readings were null, then later readings appeared. Two invalid-command
replies were attributed to `/attack off`, but the trace cannot prove the exact
text EverQuest received. Native melee stop was not confirmed. F11 halted
because its default navmesh store was missing. Keep the original helper at
`~/Projects/everquest-legends-rotation` unchanged for comparison; do not use
its F11 until the route and stop gates pass.

The 0.37.0 attack-free wrapper was staged outside the game install, but its
source hash guard **refused** the changed November helper. It was moved to
`~/.local/share/eql-automation/owner-assist/0.37.0-source-mismatch` and is
not a runnable owner test. The active legacy helper source was not changed.

## Completed G0 movement-stop check

Your G0 visible stop is confirmed; no repeat is currently requested. The
following is the retained reproduction procedure. Preview 0.39.4 allows the
**Check movement stop** button in measurement mode. This is the first supervised movement gate, not a route or F11 grind.
Blizz first stops native melee with the game's own control, stands on open,
flat, dry ground with full HP and no target, and enables `/log on`. Close any
other helper, then launch:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.4
EQL_ROTATION_TRACE="$HOME/eql-g0-trace.jsonl" ./launch.sh --measure-navigation
```

Click **Check movement stop** in the helper and focus EverQuest within four
seconds. The source requests one 0.15-second forward pulse, then checks four
`/location` fixes; it sends no combat or target command in this preview.
**F11** cancels the check; watch the character and use the game's own controls
if movement persists. G0 passes only when the helper reports **observed stop
after release**, the trace contains `ap_stop_check_result` with
`outcome=observed_stop`, and Blizz sees the character stop. A dry-run or log
line alone does not pass G0. On 2026-11-13, Blizz confirmed he saw the
character stop and the 0.39.4 trace showed `observed_stop` after a 0.151-second
hold, 4.64-unit displacement and zero measured post-release drift. This
passed the short G0 check; speed, G2 and route following remain unverified.
The four G0 log positions also matched area-63 ground in the copied GFay mesh
at exact XY, with a roughly 2.07-unit character-to-ground height offset.
That is a same-session alignment observation, not a current G2 start permit.
F11 travel/grinding remains disabled. The
copied GFay and Crushbone mesh paths are connected offline but include narrow
clearance and steep polygons, so they are not accepted movement routes.

## Separate G0 watchdog candidate: 0.39.7

This build is staged for a later supervised release check; it does not replace
the current 0.39.6 HP-test instructions or enable G2/F11. No repeat is requested
until that test is scheduled. To run that candidate on open, flat, dry ground,
with melee/autorun off, no target and the same G0 precautions above:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.7
EQL_ROTATION_TRACE="$HOME/eql-g0-watchdog-trace.jsonl" ./launch.sh --measure-navigation
```

**Check movement stop** requests the same one forward pulse and four location
fixes. A separate child uses the helper's existing input-device descriptor
and attempts key-up even if its parent stalls. F9/F11 cancel future work;
the stop and GO paths share a lock. Once GO is queued, the short DOWN
acknowledgment wait finishes or aborts before a stop returns, so a delayed
child cannot press after OFF has returned. OS scheduling and actual game
release still need owner observation. The trace adds `g0_watchdog_start`,
`g0_watchdog_failed` on error, and `release=same_device_watchdog` on a measured
hold. An over-0.20-second reported hold or cancellation is not a pass.
Assist's movement path refuses immediately; this adds no turn, targeting,
combat, camp or route action. The candidate keeps the same assist controls
and HP calibration, but its movement implementation is not client-accepted.

## Read-only UI observation for the next movement gate

Project 0.41.35 and later include an optional owner-run screenshot crop tool. It reads
one focused EverQuest window without sending any input, saves only the player,
target, chat and map window crops under
`~/.local/share/eql-automation/g2-ui-observations/`, and marks every G2 safety
flag **unknown**. The saved client UI layout places Legira's HP gauge at
`(1966, 693, 330, 17)` on the 2560×1600 layout; the old HP calibration
`[1963,661,2301,712]` starts above that gauge and is too tall. These file
coordinates need a live screenshot before they can be used for calibration.
To collect an idle observation when needed, close any helper, stand still in
the game, run the command below from a terminal, and return focus to EverQuest
within five seconds:

```bash
cd ~/.local/share/eql-automation/owner-tools/0.41.58/source
python3 tools/capture_owner_ui.py --label idle
```

After the tool prints its observation directory, the read-only HP analyzer
can check that capture without opening chat or sending game input:

```bash
cd ~/.local/share/eql-automation/owner-tools/0.41.58/source
python3 tools/analyze_owner_hp_capture.py --capture-dir /path/printed/by/capture
```

Its numeric result remains unverified until the owner confirms the live
screen state at full HP and a second known HP state. The earlier 0.39.4
preview still requires manual **Calibrate HP** on the inner red band at full
health for its own smart-heal setting; do not use the old 51-pixel saved crop.

For an explicitly requested map observation, select **Current Zone** in the
map first and use `--label current-zone` instead of `--label idle`. The tool
never opens the map or clicks its controls. The saved map may be hidden or
have stale geometry, and all zone/scene flags remain unverified until the
image is reviewed. The current-zone button rectangle does not resolve through
the old layout parser, so this release does not attempt an automatic click.

The tool prints its private output directory. It requires the reviewed 0.39.4
preview files and exactly one focused game process. It does not turn on F11 or
prove chat, target, melee or combat state. Leave any screenshot files private;
their chat crop may contain messages. Paired owner-controlled visible states
are needed before the UI indicators can become safety checks. The captured
image time is separate from later metadata writing, and the saved UI layout
is still not verified as the active live arrangement. No extra owner test is
required until we request those pairs.

After the check, the owner can send `~/eql-g0-trace.jsonl` or summarize it
without printing the `/location` coordinates from the trace:

```bash
cd ~/.local/share/eql-automation/owner-tools/0.41.25
python3 tools/summarize_owner_nov12_trace.py "$HOME/eql-g0-trace.jsonl"
```

`g0_last_trace_result` includes the hold, displacement and post-release
drift. A trace result alone does not verify the character visibly stopped;
the owner's observation is still required.

## Owner-run GFay→Crushbone zone observation (during normal play)

Optional watcher, staged on Alienware outside the game install:

```bash
cd ~/.local/share/eql-automation/owner-tools/0.41.20
python3 -m eql_automation.watch_destination --character Legira --server freeport
```

Start it before crossing. It watches for up to 15 minutes and can be stopped
with Ctrl-C. Its terminal output names a private JSON file under
`~/.local/share/eql-automation/owner-traces/` if it captures one timely
destination reading. No file is written on timeout. It reads only Legira's
specified client log and the installed `Resources/ZoneNames.txt`; it never
sends `/location` or other input.

When Blizz is already near the Crushbone entrance in Greater Faydark, leave
F11 off and enable `/log on`. While standing near the zone line, type
`/location`, then walk across himself within 30 seconds. After Clan Crushbone
loads, stop moving and type `/location` within 30 seconds. Tell the
coordinator the approximate crossing time or the watcher output path; the lead
can read those new log lines without touching the character. This is a short
before/after observation, not a hand-recorded route. The destination fix may
be after some movement, and the log alone cannot prove the crossing method.
The watcher also records the optional preloading `/location` if it was printed
within 30 seconds of the loading line. That point has no confirmed source-zone
identity or exact zone-line position. Neither reading certifies the spawn or
enables F11.

## Start the offline prototype

From this project directory:

```bash
python3 -m eql_automation --demo
python3 -m eql_automation --shell
python3 -m eql_automation --synthetic-1-50
python3 -m eql_automation --demo-navigation
python3 -m eql_automation --demo-assist
python3 -m eql_automation --demo-gauges
python3 -m eql_automation --inspect-target --source /path/to/copied/eqhost.txt
python3 -m eql_automation --ingest-retail-copy --source /path/to/copied/client-text
python3 -m eql_automation --index-pois
python3 -m eql_automation --query-pois Merchant --map fieldofbone --limit 5
python3 -m eql_automation --index-zone-candidates
python3 -m eql_automation --query-zone-candidates East_Cabilis --map fieldofbone
python3 -m eql_automation --audit-butcherblock
python3 -m eql_automation --inspect-s3d --source ~/.local/share/eql-automation/client-data/retail-full/assets/butcher.s3d
python3 -m eql_automation --inspect-wld --source ~/.local/share/eql-automation/client-data/retail-full/assets/butcher.s3d --member objects.wld
python3 -m eql_automation --audit-butcher-placements
python3 -m eql_automation --audit-butcher-meshes
python3 -m eql_automation --audit-butcher-model-links
python3 -m eql_automation --audit-butcher-instances
python3 -m eql_automation --build-butcher-candidate-scene
python3 -m eql_automation --build-butcher-candidate-scene --exclude-boundary
python3 -m eql_automation --audit-butcher-materials
python3 -m eql_automation --audit-crushbone
python3 -m eql_automation --build-crushbone-candidate-scene
python3 -m eql_automation --build-crushbone-candidate-scene --exclude-boundary
python3 -m eql_automation --audit-zone-regions butcher
python3 -m eql_automation --audit-zone-regions crushbone
python3 -m eql_automation --audit-zone-regions gfaydark
python3 -m eql_automation --audit-map-alignment gfaydark
python3 -m eql_automation --probe-zone-labels butcher
python3 -m eql_automation --probe-zone-labels crushbone
python3 -m eql_automation --probe-zone-labels gfaydark
python3 tools/query_offline_nav.py butcher ~/.local/share/eql-automation/nav-candidates/butcher-fayhouse-128.nav ~/.local/share/eql-automation/nav-candidates/butcher.sample-query-with-points.json 1405.765747 2757.740967 -3.65255 1405.765747 2797.740967 -3.65255
python3 -m eql_automation --audit-path-hazards butcher --source ~/.local/share/eql-automation/nav-candidates/butcher.sample-query-with-points.json
python3 -m eql_automation --index-spell-levels
python3 -m eql_automation --query-spell-levels Yaulp --class-name Paladin --level 9
python3 -m eql_automation --index-ui-widgets
python3 -m eql_automation --query-ui-widgets Target_Level
```

The demo prints a synthetic route and mode-permission results. The shell stays
running while you switch simulated modes:

```text
mode assist
action cast
action move
queue heal
drain
mode full
route
key F8
key F9
status
quit
```

`mode assist`, `mode full`, and `mode off` take effect in the running simulator
without a restart. `stop` is another way to select OFF. Simulated `key F7`
selects FULL, `key F8` selects ASSIST, and `key F9` selects OFF. Each switch
prints an on-screen indicator with mode, generation, and transition reason.
`queue KIND` holds a synthetic action until `drain`; switching modes cancels
queued or already drained intents through their original permits.
`action KIND` checks an intent immediately. `safety REASON` latches OFF and requires
`reset safety` while OFF before reactivation. `quit` stops the shell. These are
**terminal commands and simulated key events**, not in-game commands, grabbed
hotkeys, or a live overlay. No keys reach the EverQuest Legends client.

The older October rotation tool uses F8 for its own fight toggle and F9 for
stop. Do not run both listeners. A real in-game key mapping requires verified
game bindings, a single keyboard owner, a focus-gated grab, release of held
keys on OFF, and a sender that rechecks the mode permit before each key. None
of that live input path has been verified in this build.

`--demo-assist` now also records a symbolic `/cast 3` key sequence. Its
recording-only bridge uses the October bot's command-typing pattern, checks
the original ASSIST permit and a newer matching target/scene observation
before each key, and never records attack, movement or target commands.
OFF cancels the permit before transition bookkeeping waits. One shared
control plane permits only one command at a time, even across bridge
instances. If stopped mid-command, an uncertain draft blocks later sends
until an explicit clear while OFF and a fresh focused, chat-closed observation.
These are offline checks: there is no game keyboard sender, grab, live chat
detector or verified instant-OFF path. A future native sender must have a
bounded nonblocking key-down operation, release held keys on every failure,
and prove that the bot owns any command draft before more keys are typed.
The copied chat UI defines an edit box but offers no verified runtime focus,
text, or owner signal. If chat opens after the first slash, the recording
bridge stops OFF with an uncertain draft. The installed `eqclient.ini` has no
stored custom cast-spell or ability key binding; a direct shortcut has not
been verified either.

The same demo also records a **synthetic** two-event spell-gem mouse click at
a fabricated hitbox. `RecordingGemClickBridge` accepts only a current-target
rotation `/cast 1`–`/cast 8` proposal, a strictly newer matching scene, and
fresh evidence that the expected gem and spell ID are visible and unobstructed
within the focused game window at the expected layout. It shares the input
channel with the command bridge, releases the symbolic button after OFF, and
records no movement, targeting or attack. The copied static UI identifies
gem widgets but gives no active screen position. A private-client screenshot,
layout calibration, unique target-selection signal, and a bounded real mouse
sender are still needed; the bridge cannot click the game in this build.

`--synthetic-1-50` runs a closed-loop **fabricated** world. It exercises the
planner and stops at synthetic level 50 or fails if progress stalls. The output
prints `simulation_only: true` and `real_client_level_verified: false`.
Trace, summary and a synthetic status file go under
`~/.local/share/eql-automation/runs/synthetic-1-50-<UTC timestamp>/`.
Use `--output DIRECTORY` to choose a different trace directory. These files
are test evidence only; they do not show an EverQuest Legends character at 50.
Every synthetic action now passes through a recording-only dispatcher that
binds the original mode permit and an immutable world snapshot. A newer
matching synthetic observation is required before the sink records the action;
OFF, ASSIST movement limits, changed target/zone/state, stale or unknown
readings, and GM presence can cancel it. This validates the dispatch seam
offline. Each fabricated camp trip now feeds a start position, waypoint
arrival, and zone-entry observation through `WorldNavigator`. The camp is
assigned only after the navigator confirms arrival. A stalled waypoint or
incorrect zone entry stops the synthetic route with OFF latched. The default
observation adapter fabricates immediate arrival at each destination; this
does not verify real movement, zoning, or a client position reader.
Repeated observations of one pending transition do not issue another ZONE
action. A missing or stale observation also latches OFF.

`--demo-navigation` shows a synthetic blocked edge being quarantined and a
route changing to a safe alternate. The pure navigation controller waits for
an observed start position, uses only explicitly verified graph edges, and
pauses on uncertain movement or zoning. It does not press movement keys.

The read-only `LocationLogReader` library can tail a specified fresh test
character log and a copied client `Resources/ZoneNames.txt`. It skips existing
log history, resolves only exact unambiguous zone display names, clears the
position during loading, and records later `Your Location is ...` lines as
**raw, unaligned coordinates**. File replacement, truncation, excessive
backlog, malformed lines, and older log timestamps cannot bootstrap a position.
This is a library seam, not a running observer or a navigation input. It does
not request `/loc`, convert log axes to WLD axes, verify log-to-client latency,
or move the character. The installed client currently has no verified private
target; do not use its owner-character log for a bot run.

The separate `G2ReadOnlySceneObserver` can turn a **single** newly logged
`/location` line into a short-lived measurement scene only when the expected
zone ID/name, zone generation, local timestamp and independently supplied
focus, owner-key, chat, target and combat observations all agree. It treats
multiple location lines in one poll as ambiguous. The client does not echo a
`/location` request ID, so the scene cannot prove which command produced the
line. Existing log history cannot establish the starting zone. This library
does not run in preview 0.39.4, send input, prove a log-to-mesh coordinate
transform or authorize G2 movement. No new owner launch step is available.

The offline `check_g2_start()` gate also requires a separately verified
ground-position transform bound to the same new log fix and mesh hash.
`AlignedWldFix` now contains a `SourceFloorObservation`, `MeshProjection` and
the exact current `HeightCalibration` object. Callers separately supply that
calibration and `GroundGeometryEvidence`. Source XY must equal raw XY; mesh
XY must be the exact helper-frame swap. Raw height is checked against the
source floor, while G2 snap and route endpoints use baked height. Calibration
is bound to zone, log generation, newer sequence numbers and a validity window.
The fixed-route controller also checks raw/source/baked Z stability separately
and permits only the selected polygon or its verified immediate neighbor at
the shared endpoint disk. These are evidence consistency checks: a trusted
live producer of these records is still required. Synthetic test/replay flags
are not a live permit. Its
default 18-unit radial check needs 684 samples at 36 directions and 1-unit
spacing; a smaller radius or sample budget can fail before any geometry query.
The reported radius is reduced by any tiny mesh-start snap and rejects larger
snaps or the wrong copied-client zone.
A pass means sampled copied-mesh geometry only. It does not observe dynamic
obstacles or grant a movement permit. No live alignment record has been made.

The separate `ClientLogReader` for level/death status now uses the same
non-replaying file-tail protection. An existing log is skipped at startup;
replacement, truncation and oversized backlog skip old lines and invalidate
the run's level, XP, death count, camp and zone until character/session
identity is re-established. Only a log path known to be absent for a **fresh
test character** should opt in with `fresh_test_character=True` to retain its
first newly written event. This is a read-only library, not a client login or
live telemetry feed.

The read-only `TargetLogMonitor` can record **newly logged target hints** from
a specified character/server log. It skips existing history and clears its
last hint on zoning, death, targetless messages, log reset, malformed lines or
time regression. Two logged selections with the same display name get
different explicit event counts. The client can also retarget without a
`Targeted` line, and the log gives no entity ID; the monitor never claims a
verified current target or supplies an ASSIST target token. It sends no game
input. It is not a reason to turn on strict live ASSIST.

For a **read-only historical geometry audit**, a filtered file containing only
the owner's own timestamped zone, loading and `/loc` system lines can be kept
under `~/.local/share/eql-automation/client-data/` and scored with:

```bash
python3 tools/audit_location_alignment.py gfaydark 'The Greater Faydark' ~/.local/share/eql-automation/client-data/retail-full/log-evidence/historical-system-location-lines.txt
```

The tool compares eight sign/axis candidates against copied flag-zero WLD
terrain, prints source hashes and per-candidate coverage/vertical-offset
scores, and always reports `accepted_log_to_wld_transform: null`. The current
historical Greater Faydark sample favors direct `(x,y)` at 47 of 48 distinct
positions (56 raw log lines);
Crushbone's flat sample is ambiguous. No live coordinate calibration,
clearance, walkability, or movement follows from these scores.

`--inspect-target` reads a copied `eqhost.txt` and reports its host, port,
hash, and whether it is a Daybreak official domain. It does not connect.
`--ingest-retail-copy` reads copied map, zone-name and spell text files and
writes parsed geometry and Paladin/Cleric spell metadata beneath
`~/.local/share/eql-automation/map-store/`. It does not change the client.
Map drawing lines are **not** automatically treated as walkable routes;
navigation still needs observed traversable paths. The retail sample copy is
at `~/.local/share/eql-automation/client-data/retail-sample/` and is kept out
of git.

The complete top-level retail map copy is at
`~/.local/share/eql-automation/client-data/retail-full/`. Run the same import
command with that directory to build a snapshot of all 224 client maps. The
active snapshot is named in `~/.local/share/eql-automation/map-store/current.json`.
Nested `Solo_Leveling` custom/backup maps are ignored. A failed import leaves
the active snapshot in place.

`--index-pois` builds a search index of map labels from the active snapshot.
`--query-pois TEXT` searches it; `--map NAME` narrows to a map file stem.
Results include coordinates and an **unverified text hint** such as
`zone_exit_hint`, `merchant_hint`, `spell_hint` or `portal_hint`. A label is
not evidence that the location is reachable, a zone line functions, or a
merchant stocks a spell. The index is stored outside git under
`~/.local/share/eql-automation/map-store/indices/`.

`--index-zone-candidates` compares map labels with client zone display names;
`--query-zone-candidates TEXT` searches that review list. Exact text and
reordered-word matches are distinguished. Matches are **unverified** and do
not add a transition to the navigation graph. A missing match does not prove
that no zone line exists.

`--index-spell-levels` reads the copied `spells_us.txt` and `dbstr_us.txt`
from the active retail snapshot's source directory. It indexes client spell
and skill rows with a class level from 1–50 under
`~/.local/share/eql-automation/map-store/indices/`. Use `--source DIRECTORY`
to select another copied client directory. `--query-spell-levels TEXT` searches
the index; `--class-name` and `--level` filter it. These are **client level
candidates**. They do not prove a private server grants a spell, that a vendor
stocks it, or that it can be scribed or memorized. The planner requires
separate observed spellbook and vendor facts before proposing an acquisition.
The old Paladin/Cleric rotation profile now checks each class's own level;
it will not offer Paladin Yaulp at level 1 when the client requires level 9.

The offline `AssistAdvisor` can propose a Paladin/Cleric combat action using
the corrected profile. It requires the same character/class/level, a unique
token for the **current target selection**, a verified target relationship,
a focused game with chat closed, health and mana readings at most one second
old, and the selected spell in its observed gem. The token must change on
every target selection, including same-name switches and away/back switches.
It only proposes abilities observed as available. A proposal needs a **newer**
observation with the same token, relationship and target kind immediately
before each future key; the mode permit is checked again too. This is a
code-level contract with synthetic tests, not a running in-game rotation.
There is no live target observer or input sender.

Assist permits damage and stun spells only when the current target is observed
as a hostile NPC and the copied spell has target type 5. Undead spells also
require an observed undead target and target type 10. Bash and Smite require a
hostile NPC. The copied client lists selected heals and HoTs as target type
51, whose behavior is unverified here; self heals and Lay Hands stay disabled
until a private-client test confirms their self-target behavior. Self buffs
with type 6 also need explicit per-spell confirmation. The current verified
self-heal, self-buff and Lay Hands lists are empty. Assist pauses when self HP
is at or below 65% while another target is selected. It never changes target
to heal. The default UI XML and existing log reader do not provide a unique
target token or reliable hostile/friendly relation, so **no live assist action
is ready**.
`--demo-assist` prints a synthetic proposal and shows that OFF invalidates it.
`--demo-gauges` uses Pillow to read fabricated red HP, blue mana, and orange
current-level XP bars. It does not capture the game or supply raw XP.

The offline `GaugeReader` accepts only explicitly calibrated inner bars from
a focused game-window image at the same window size and active layout. Its
calibration requires both bars to appear at least 85% full. A changed layout,
unfocused window, unreadable fill or empty-looking bar yields **unknown**;
it never treats an unreadable bar as zero HP or mana. Default client XML uses
red for both player and target HP, so color alone cannot identify the player
bar. Live crop coordinates and the active skin have not been verified.

The copied default UI defines `PW_ExpGauge` (EQType 4, orange) and a separate
green AA gauge (EQType 5). The offline `XpGaugeReader` requires an active-skin
crop calibrated against a **same-frame verified numeric XP label**, then
checks focus, layout and window size on every read. An empty bar or label/bar
disagreement yields unknown. No active-skin crop, live label reader or normal
XP allocation check has been verified, so no real XP fraction is reported.
`RunState` can track that fraction as current-level progress and percentage
points per hour only while the confirmed level stays the same and normal XP
allocation is verified. A level change, fraction drop or uncertain allocation
resets the rate. This fraction is never fed into raw cumulative XP/hour or
camp scoring, which still need a separate verified absolute XP source.

`--index-ui-widgets` reads copied default client UI XML and stores a searchable
widget index outside git. `--query-ui-widgets TEXT` searches names and EQType
codes. The index includes player health/mana/XP and level labels, target
gauges, spell gems, chat input and keyboard assignment widgets. It describes
the **default static UI only**: the active skin, screen positions, live values,
character identity, chat focus and working hotkeys have not been verified.

| Simulated mode | Actions permitted by the planner |
| --- | --- |
| Off | None |
| Assist | Eligible rotation casts and abilities under the target checks above; verified self heals/buffs can be added after private-client confirmation. It never moves, changes targets, toggles autoattack, loots, vendors, camps, zones, or logs in. |
| Full | All action categories in the simulator; there is no live input transport |

The map graph currently contains **synthetic coordinates only**. It is not an
EverQuest Legends navigation map. `NavGraph.save()` stores supplied graphs under
`~/.local/share/eql-automation/map-store/` by default. No client map, spell,
log, or asset is committed to this repository.

The library also accepts externally supplied class-level spell facts and plans
buy, scribe, and memorize tasks. It does not buy anything. A campaign planner
uses supplied camp scores and observations to suggest rest, recovery, selling,
target selection, or a camp change. These are unexecuted intents, not verified
game behavior.

The zone planner accepts verified zone graphs and zone-line endpoints and can
route across zones while respecting water, aggro and level limits. This build
contains only synthetic zones. The campaign planner pauses on unknown health,
mana or bag state, GM presence, or an attack with no verified current target.
No live pause hotkey or in-game indicator is available yet.

Butcherblock is the first planned navigation and camp review target;
Crushbone follows through Greater Faydark only after real zone transitions
and suitable character levels are observed. The copied client maps contain
drawing lines and unverified exit labels, not walkable collision data. A
historical Butcherblock Recast/Detour proof was reported, but its mesh and bake
recipe are absent from this project's retained store. Greater Faydark height
alignment, conservative collision clearance, doors, water and real movement
remain unverified. No route from that historical proof is active in this build.
`--audit-butcherblock` prints current map hashes and missing collision/client
evidence with `actual_client_acceptance_ready: false`. Optional `--mesh PATH`
checks a retained artifact only inside `~/.local/share/eql-automation/`.
A hash match alone cannot accept a route; the audit creates no graph edges.
`--inspect-s3d` inventories one copied client PFS/S3D archive inside the
approved local data store. It bounds decompression, reports member names and
SHA-256 hashes, and writes no member content to git. Three read-only copied
Butcherblock archives now have untracked manifests under
`~/.local/share/eql-automation/client-data/retail-full/assets/manifests/`.
Their WLD files are candidate terrain, placement and object inputs; archive
inspection alone does not decode geometry or verify a collision route.
`--inspect-wld` counts WLD fragment types, inventories copied client name
references, and records archive/member hashes. `--audit-butcher-placements`
checks exact placement-to-model names and reports the 22 dropped-tree Z
sentinels among 1,884 copied Butcherblock locations. Both are read-only.
The audit does not compose collision geometry, create a navmesh, accept a
route, or send game input. Its derived JSON files stay outside git in the
untracked `assets/manifests/` directory described above.
`--audit-butcher-meshes` decodes copied old-format terrain and object mesh
vertex/triangle arrays, checks indices, and counts solid and pass-through
polygon flags. It does not apply object placements or validate movement.
`--audit-butcher-model-links` traces exact actor definitions to object meshes.
`--audit-butcher-instances` reports model geometry weighted by the copied
placements. `--build-butcher-candidate-scene` writes a provisional OBJ in
`~/.local/share/eql-automation/nav-candidates/` using flag-zero, nondegenerate
terrain and static-object triangles. Client-derived geometry stays outside git.
This OBJ is an input for later collision review. Material/shader collision,
water, dynamic doors, clearance, navmesh routes and actual movement have not
been accepted.
`--audit-butcher-materials` traces mesh polygon groups through the copied
client's material fragments. It identifies 6,443 terrain Boundary faces in
the current OBJ. The current winding-corrected OBJ has SHA-256
`1ec7706037c35c06205c026c4ed56c1b4032fd2fb7a8e2dbe0cf2490d18a1bc3`.
Boundary handling and water need real-client validation before a route is
usable. A pinned Recast/Detour library build is local under
`~/.local/share/eql-automation/toolchains/`.
The `--exclude-boundary` variant omits faces with the copied client's
Boundary material label; it does not assert that the client ignores those
faces. Its Butcherblock FAYHOUSE sample baked to the same 156-polygon nav
tile as the included variant, while the sampled Crushbone tile changed from
269 to 270 polygons. Neither is a verified traversal route.

`--audit-crushbone` reads the two copied Crushbone archives from the same
approved untracked asset store and prints placement, mesh, instance, and
material counts. `--build-crushbone-candidate-scene` writes a provisional
WLD-XYZ OBJ outside git; `--exclude-boundary` produces a second variant.
The copied-data audit found 178 exact-name-matched object placements and
4,057 Boundary terrain faces. The two candidate scenes contain 26,570 and
22,513 faces respectively. Offline bakes and one sampled query per variant
are recorded in `FINDINGS.md`. Water, dynamic doors, terrain clearance,
actual client movement, and the private server target remain unverified.

The copied Cauldron and Unrest archives have a reproducible scene command.
Run on the devbox with the approved private client copies already present:

```bash
python3 -m eql_automation --build-later-zone-candidate-scene cauldron --exclude-boundary
python3 -m eql_automation --build-later-zone-candidate-scene unrest
```

The copied South and North Kaladim archives now have the same hash-pinned
offline command. Run it on the devbox with the approved private client copies:

```bash
python3 -m eql_automation --build-copied-zone-candidate-scene kaladima
python3 -m eql_automation --build-copied-zone-candidate-scene kaladimb
python3 -m eql_automation --audit-map-alignment kaladima
python3 -m eql_automation --probe-zone-labels kaladima
```

`kaladima` is South Kaladim and has a copied map label for Butcherblock.
`kaladimb` is North Kaladim and has labels for South Kaladim. These commands
only produce private static evidence. The character's actual fresh spawn,
walkable route, zone trigger and arrival still need real-client checks.

Both emit provisional WLD-XYZ OBJs under
`~/.local/share/eql-automation/nav-candidates/`, alongside archive/member
hashes and `real_client_accepted: false`. Omit `--exclude-boundary` to retain
Cauldron's copied Boundary faces for a sensitivity comparison. Unrest has no
Boundary faces; its unclassified material modes and the zones' water and
door behavior remain unresolved. These are offline geometry commands, not
an Alienware launch step or an F11 travel command.

`--audit-zone-regions ZONE` checks copied WLD BSP tree and region-label
references for `butcher`, `crushbone`, `gfaydark`, `kaladima`, or `kaladimb`.
It reports water and
zoneline **region ID candidates**. It does not decode region shapes, accept
water-free paths, or turn zoneline labels into graph edges.
`--audit-map-alignment ZONE` compares map drawing endpoints with copied WLD
terrain vertices under eight XY transforms. In all three copied zones the
best transform is `map → WLD = (-map_y, -map_x, map_z)`. It also probes
label XY positions against flag-zero terrain triangles; multiple surfaces
can overlap there. Four Greater Faydark exit labels are about 0.8013–0.8014
units below the nearest candidate surface, not evidence of a general height
correction or a working zone transition. Neither audit sends game input.
`--probe-zone-labels ZONE` applies the supported copied-map frame, checks
each label against the copied WLD BSP tree, then searches a 5-unit XY grid
within 100 units at three candidate heights for nearby tagged zoneline
regions. It reports unknown when a BSP branch is missing or ambiguous.
Results are sampled review hints only: no transition, route edge, or safe
water-free path is accepted. The Greater Faydark labels do not themselves
fall in tagged zoneline regions in this copied client.
`tools/query_offline_nav.py` runs the local Detour query and writes JSON
bound to a zone-named nav file and its before/after checked SHA-256 in the approved untracked
store. `--audit-path-hazards ZONE --source QUERY.json` rehashes that nav
file, rejects incomplete or mismatched query points, then samples the
provisional straight path and both requested-to-snap
endpoint gaps against copied BSP labels. A filename/hash match does not
prove the nav mesh is correct for the real zone. A zero-label result means
only that the sampled points had no labelled region; unknown samples and
narrow missed regions remain possible. The audit always keeps route and
movement acceptance false. Its output now separates sample, unknown, and
label counts for the start connector, Detour corridor, and end connector.
The sampled Crushbone path has one unknown BSP result in each connector;
the corridor itself has none. Both gaps require review before movement.
The audit now also partitions each straight WLD segment at copied BSP planes
and reports every labelled or unknown **centerline interval**, including a
narrow interval between sample points. This checks the copied region tree more
fully than sparse sampling, but still does not verify character width, doors,
aggro, real collision or zone transitions. Plane endpoints, missing children,
cycles and traversal limits remain unknown. The route acceptance flag stays
false even when no label or unknown interval appears.

For bounded **offline** navmesh experiments, place the upstream
[RecastNavigation source](https://github.com/recastnavigation/recastnavigation)
at `~/.local/share/eql-automation/toolchains/recastnavigation`, check out
commit `9f4ce64458dfae86e1239c525ddc219c4e9e06f1`, then run
`tools/build_local_nav_tools.sh`. The script verifies that pin and compiles
`eql-bake-local` and `eql-query-local` outside git. The baker takes a copied
candidate OBJ, an output `.nav` path, WLD center X/Y, half-extent, min/max Z
and label. It uses the offline height/radius/climb/slope profile `(8,5,2,45)`.
Four optional final numbers override that profile in the same order for
bounded sensitivity checks, for example `6 3 3 50`. The query tool now
reports each endpoint's distance to its nearest nav polygon; a complete
Detour corridor can still start several units from the requested point.
One local Butcherblock FAYHOUSE 256×256 bake produced 156 provisional nav
polygons and a 24-polygon offline Detour query path. Its data stays under
`~/.local/share/eql-automation/nav-candidates/`. No query is an accepted bot
route or proof of game movement; the active bot still has no verified nav edge.

The owner-run 0.39.6 preview above is built from a pinned copy of the November
helper plus the source patch in `patches/`. Its original working tree at
`~/Projects/everquest-legends-rotation` was not edited. Do not run the old
tool's installer: it writes character INIs in the protected Alienware prefix.

## Verification

```bash
python3 -m pytest -q tests/test_offline.py
python3 -m pytest -q tests/test_dispatch.py
python3 -m pytest -q tests/test_control.py
python3 -m pytest -q tests/test_spell_catalog.py tests/test_assist.py
python3 -m pytest -q tests/test_ui_schema.py
python3 -m pytest -q tests/test_screen_observer.py
python3 -m pytest -q tests/test_target_log.py
python3 -m pytest -q tests/test_owner_nov12_adapter.py tests/test_owner_nov12_recovery.py tests/test_owner_nov12_entry.py
python3 -m pytest -q tests/test_nav_evidence.py
python3 -m pytest -q tests/test_melee_stop.py
python3 -m pytest -q tests/test_nov12_path_quality.py
python3 -m pytest -q tests/test_g2_probe_geometry.py tests/test_g2_pulse_budget.py
python3 -m pytest -q tests/test_g2_input_bridge.py tests/test_uinput_watchdog.py tests/test_location_log.py
python3 tools/summarize_owner_nov12_trace.py /path/to/copied/owner-trace.jsonl
python3 -m compileall -q eql_automation
```

The staged owner preview also supports a no-input Alienware check:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.6
/usr/bin/python3 -B owner_nov12_smoke.py
./launch.sh --dry-run --level 7
```

The **real-client** level 50 run, in-game mode switching,
automated spell acquisition, camps, death recovery, and relogin are not
implemented or verified. `FINDINGS.md` records the exact client/server
evidence and blocker.
