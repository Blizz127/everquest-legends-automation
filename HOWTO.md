# EverQuest Legends automation — current owner guide

Source **0.42.46** · travel/camp test **0.39.30** · stationary preview **0.39.24** · retained assist **0.39.13** · movement preview **0.39.21**.

**The complete 1–20 autopilot is not ready. Preview 0.39.30 offers supervised travel to Slave Mines or North Wall and Castle, followed by repeated camp combat. F12 is disabled.** No real route,
automated level gain or fresh-character hands-off 1–50 run has been accepted.
The client installed on Alienware connects to Daybreak. Blizz runs live tests
himself; the lead does not log in or control his character. Service-rule findings
and verification evidence are in [FINDINGS.md](FINDINGS.md).

| Mode | What is available today | Controls |
| --- | --- | --- |
| Assist / rotation | Supervised preview using the existing rotation bot. Blizz moves, chooses his target and controls melee. | F8 arm, F7 toggle, F9 stop, F10 request heal. |
| Full auto | In development; no accepted 1–20 or 1–50 run. | No complete leveling mode yet. |
| Stationary camp test | In 0.39.24, prepares learned spells automatically, searches observed NPC names, checks fresh considerations, fights and recovers between fights. Stops at observed level 20 or a failed check. | F11 starts/stops; F8 switches to assist; F9 stops all helper input. |
| Read-only position observation | One owner-triggered capture; no commands, keys or clicks sent. | **Observe current position**, F9/Stop to cancel. |
| Stationary location-hotbutton test | Sends one explicitly configured key, then checks the log for one fresh position reply. No route movement or combat. | **Test /location hotbutton…**, F9/F11/Stop to cancel. |
| Supervised motion measurement | Four short forward presses and three turns on owner-confirmed open ground; saves relative observations and stops. | **Supervised motion measurement…**, F9/F11/Stop to cancel. |
| Supervised destination travel | In 0.39.18, measures motion, plans from current GFay coordinates toward Crushbone, checks each movement and stops. No zone crossing or leveling. | **Travel toward Crushbone…**, F9/F11/Stop to cancel. |
| Supervised zone crossing | In 0.39.19, a separate action measures motion, follows the GFay route into the expected Crushbone zone line, then stops after fresh arrival positions. No combat or leveling. | **Travel into Crushbone…**, F9/F11/Stop to cancel. |
| Supervised source route | In 0.39.21, measures motion and plans from the current Crushbone position toward Slave Mines, with fresh stopped observations after each pulse and explicit step handling. No combat or leveling. | **Travel to Slave Mines…**, F9/F11/Stop to cancel. |
| Supervised short route trial | In 0.39.20, measures motion, creates a two-unit GFay or Crushbone path from fresh current positions, checks terrain/objects/region evidence, follows it if checks pass, then stops. No combat or leveling. | **Supervised short route trial…**, F9/F11/Stop to cancel. |

Run only one helper at a time. **G0 passed; do not repeat the movement-stop
pulse.** Assist still uses the existing rotation bot. Preview 0.39.21 adds a
separate finite movement test; it cannot switch into assist or full auto.
Preview 0.39.24 switches between assist and the repeated stationary camp test without a
restart. Preview 0.39.30 includes the destination selector, same-process Crushbone travel→camp and F8 assist switching; complete full-auto remains unfinished.

## Choose a travel/camp destination — preview 0.39.30

Close your old helper yourself; run only one. On Alienware:

```bash
EQL_ROTATION_TRACE="$HOME/eql-journey-trace.jsonl" ~/.local/share/eql-automation/owner-assist/0.39.30/launch.sh
```

This includes the existing rotation: **F8 assist**, **F9 stop**, **F10 heal**.
Assist leaves movement and targets to you. **F11** starts/stops the stationary
camp where you stand. The first F11 after travel/setup remains OFF.

In **Travel and camp test**, select the destination:

- **Slave Mines**: the original route. The copied map suggests levels 7–10.
- **North Wall and Castle**: start near Slave Mines. The route retraces the
  corridor to reach this combined map destination. The copied map suggests
  levels 13–17; this does not establish live camp suitability.

Start inside Clan Crushbone. Open the map and run **Test /location hotbutton…**
using your configured `/location` key. Then close map/chat, clear your target,
turn native melee off and stand on clear, flat ground. Click **Travel to selected
camp…**, confirm the open starting area and focus EverQuest during the countdown.
The helper measures motion, checks a route from your current floor and travels
if those checks pass. A fresh stopped arrival hands over to automatic learned
spell preparation in gems **1–8**, then repeated stationary fights and recovery.

Stay present for this test. **F8** switches to assist after movement releases;
**F9** stops. The selected destination stays fixed throughout that trip and is
shown in the travel/camp status. Stop before choosing another. There is no
restart or re-login between these activities. G0 passed; do not repeat it.

In 0.39.28, after travel hands over to camp, manual keyboard/mouse activity,
lost focus or lost input-device coverage stops the camp. Brief movement followed
by releasing the key also stops it. **F8 switches to assist and gives movement
back to you**; F9/F11 stops and closing the helper releases the monitor.
This monitor is read-only and sends no keys. It applies to a camp reached by
the Travel button; standalone F11 camp behavior is unchanged.

Preview 0.39.30 also remembers the floor reached by travel while you camp.
Stop, assist, manual input or a changed game/log binding discards that record.
It does not yet move you to another camp automatically. The next trip still
needs fresh position and motion observations; old calibration is not renewed.

In **0.39.30**, after the first kill and completed rest at a camp reached by
travel, the helper automatically requests two new positions with the same
location hotbutton you tested before travel. It checks that you remain on the
reached floor, then resumes the same camp. The status reads **Checking stopped
position after recovery**. It performs this check once per reached camp;
standalone F11 camping is unchanged. Missing replies, a changed height/floor,
manual input or changed focus stop the camp. F9 cancels; F8 waits for the
hotbutton release, then switches to assist. No movement or target command is
sent by this check, and it does not enable automatic camp relocation.

The North Wall path passed copied terrain/object/region checks and a bounded
long-leg fixture. It has **not been traversed or accepted in the real client**.
A start without a checked connection is refused. Later-camp relocation is still
an explicit selection; it is not automatically triggered by a level-up. GFay
entry, Trainer Hill, the full 1–20/1–50 route, buying/scribing, active looting,
vendors and death recovery remain unfinished.

In 0.39.27, an empty combat history can use NPC names from your retained
observations on **Freeport**, in GFay or Crushbone. Your character's own
NPC/consider/kill history takes precedence. No other character logs are scanned.
Only reduced name evidence is staged; the source log and chat are not copied
into the release. The helper still needs a current zone, readable log, correct
configured level, learned spells and readable resources. Historical levels do
not set your current level or authorize combat: each attempted fight needs a
fresh matching consideration inside the current level window. A PC selection
or mismatched target is rejected. The inherited matching-consideration path
does not require an NPC-selection receipt when none is logged.

The 0.39.27 fix is retained for a camp bookkeeping error that could block casting after
a normal NPC-selection message. It sends no native melee command. Fresh-character
login, new NPC discovery outside the retained names, automatic camp relocation
and complete 1–20 remain unfinished. G0 is passed; no repeat is needed.
Preview 0.39.25 remains available below.

## Travel to Slave Mines, then camp — preview 0.39.25

Close your old helper yourself; run only one. On Alienware:

```bash
EQL_ROTATION_TRACE="$HOME/eql-journey-trace.jsonl" ~/.local/share/eql-automation/owner-assist/0.39.25/launch.sh
```

The existing rotation is included: **F8 assist**, **F9 stop**, **F10 heal**.
Assist never moves or chooses targets. **F11** starts the stationary camp
when idle, or stops it. The first F11 after navigation/setup is always OFF,
including if its key press caused movement to stop before its release.

For travel, start **inside Clan Crushbone**. In **Travel and camp test**:

1. Open the game map and use **Test /location hotbutton…** with your already
   configured, manually checked `/location` hotbutton. This obtains a current
   zone/position observation in this helper; it does not repeat G0.
2. Close the map/chat, turn native melee off, clear your target and stand on
   clear flat ground. Select **Travel to Slave Mines, then camp…**. Confirm
   the starting area and return focus to EverQuest during the four-second countdown.
3. Stay present. The helper measures motion with seven short presses, plans
   from your current position and follows the source route. After a fresh
   stopped arrival, it releases navigation, prepares learned spells in gems
   **1–8**, and begins the repeated stationary camp described below.

**F8 cancels travel and switches to assist after movement releases; F9 stops
all helper input.** No restart or re-login is needed between these activities.
The screen/log shows travel or camp state. Saved arrival reports cannot start
camp; F9 during arrival or preparation defeats the continuation.

This increment covers one Crushbone destination. The copied client map labels
Slave Mines **7–10**, an unverified suitability hint. It does not provide the
whole level 1–20 route, automatic GFay entry or later camp relocation. Fresh
NPC/consider/kill evidence in your own Crushbone log is required for candidate
names; no candidates means no trip. The camp then rechecks every target live.
Real traversal, camp safety, movement-to-combat handoff and spell preparation
still need owner acceptance. Death, hazards or changed input/zone stop the
trip; there is no automatic death recovery. Standalone movement 0.39.21 and
stationary camp 0.39.24 remain available.

## Assist and repeated stationary fights — preview 0.39.24

Close the older helper first, then run on Alienware:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.24
EQL_ROTATION_TRACE="$HOME/eql-camp-trace.jsonl" ./launch.sh
```

**F8 runs the existing assist rotation on your target.** Movement, target
selection, posture, looting, camps and native melee remain yours in assist.
F9 stops; F10 requests a heal. F6 prepares the spell bar as before.

For the repeated camp test, stand at your chosen camp, turn native melee off,
close chat. F11 now prepares the spell bar automatically; no initial F6 is needed
for the camp. Set the helper's correct character
level (1–19); HP must read at least 70% and mana at least 50%. Focus EverQuest
and press **F11**, or click **Repeat stationary camp** and return to the game
during the four-second countdown. Supervise this first test.

The helper searches up to eight NPC names backed by paired NPC-selection and
consideration messages plus kills in your own log history. The historical zone
is only a name-selection hint. Each attempt requires a new, exact-name
consideration reply with a level between your configured level minus three
and your level. History is never used as current-target permission. If the log
has no such candidates, it stops with that reason; there is no guessed fallback.

After a matching kill, it observes loot messages for two seconds, then recovers
resources before selecting again. It requests standing before sending **one**
sit toggle, waits for fresh HP ≥95% and mana ≥90%, requests standing, and waits
for two fresh settled readings before another fight. When resources are already
full, it skips the sit toggle. These are posture requests; the preview cannot
confirm sitting/standing visually. No input is sent to open or complete looting.

At startup, F11 exports your learned spellbook through the client, clears helper
gem slots **1–8**, and loads the selected heal/damage/buff spells. Each spell
requires a fresh matching begin-and-finish acknowledgment; silence never counts
as a correct gem. Automatic preparation changes your bar. In F8 assist, preparation remains an
explicit F6 action and target selection stays manual.

Fresh level-up messages update the camp's level. After the current fight and
resource recovery, it repeats preparation to use available learned upgrades.
It does **not** buy or scribe spells. A failed/partial preparation stops with the
bar marked unprepared; it never resumes the old rotation on a mixed bar. F9
stops preparation too, including before the next command's Enter. Observed level
20 stops further pulls. An empty candidate sweep waits 30 seconds before retrying
and stops after 15 minutes without an eligible target. A fight stops after four
minutes or 30 seconds without matching damage; recovery stops after five minutes
or 90 seconds without sufficient progress. The entire session is capped at four
hours. These limits do not prove the camp is safe or productive.

It stops on focus/input interruption, changed target/log/client, zoning, an
additional attacker, encounter lock, missing gauges, inventory/supply warning,
death or a failed check; it does not resume by itself. **F9 stops further helper
input immediately; F11 stops the camp; F8 replaces it with owner-targeted assist.**
Stopping leaves posture and native melee under your control and does not cancel a
spell already submitted. Switching between assist and camp needs no re-login.

This is a supervised combat increment, not the hands-off 1–20 path. No movement,
camp relocation, vendor/supply service, death recovery or spell buying/scribing
is included. Loot messages do not prove complete looting. Current HP calibration,
actual targeting/kill, rest and automatic preparation behavior still need owner acceptance. Same-name
log messages cannot establish a unique entity ID. Use 0.39.21 separately for the
movement test below; **do not repeat G0**. Previous one-kill preview 0.39.22 remains
available if you want the shorter test.

Source 0.42.31 adds the step controller to the movement core. It uses the same
sender and stop lock, keeps the confirmed floor during a partial step, waits
without movement when height is ambiguous, and resumes ordinary walking only
after fresh stopped readings confirm a complete landing. Steps up and down,
stop during input and late callbacks pass focused synthetic/OS-pipe checks.
The controller retains the existing time and movement budgets. Source 0.42.32
connects it to the separate owner action described below.

Source 0.42.30 rebuilds a height-step approach from the actual stopped floor,
including the full possible movement area and an exit beyond the landing.
If a direct transfer cannot cover the approach, it checks a compound approach
first. A second riser, missing terrain, obstacle, region hazard or uncovered
corner stops preparation. Point-support queries preserve multiple heights at
riser edges; they do not label an uncertain or partial step as grounded.

The copied Slave Mines guide is now a pinned private data file on Alienware,
so the future owner runtime will not need Devbox's old recipe files. This is
used by the owner source-route action in 0.39.21. Actual traversal and camp
safety remain unverified. G0 remains passed; do not repeat that pulse.

Source 0.42.29 adds a source-floor movement core for the Slave Mines itinerary.
Every ordinary move retains the old floor and position until two fresh stopped
readings confirm the result; stop/mode changes cancel pending work. The walk
driver approaches explicit height steps and returns a separate planning handoff
before a normal forward press can reach the riser. Remaining approach cells and
the actual stopped position stay attached to that handoff. No step or landing
is accepted merely because its copied geometry passes.

This source core passes synthetic route and OS-pipe checks. The 0.39.21
movement preview uses it through a separate owner action. Use 0.39.13 for
assist, as documented below. Both use the existing helper;
assist continues to leave movement and target selection to Blizz.

Source 0.42.19 can plan from dry ground into the exact copied Crushbone zone-line
region and retain its actual area in position observations. The copied-data
probe produces 200 segments; this is not a traversed route. Ordinary routes
still refuse zone-line geometry. Starting a new plan inside the zone-line
region remains unsupported. Copied geometry and pipe tests are not live crossing
acceptance.
Source 0.42.21 connects repeated checked moves, provisional movement receipts,
fresh stopped source positions and expected-zone arrival through one log reader
and one shared time/movement budget. Loading releases movement and discards the
source transaction; only fresh destination positions can complete the handoff.
Source 0.42.22 connects that core to a separate owner action in preview 0.39.19.
The existing **Travel toward Crushbone…** action still stops at the approach.
Crushbone camp execution and level 1–20 automation remain unfinished.

Source 0.42.23 adds a reusable Crushbone geometry/camp loader and exact terrain
diagnostics. Copied level-range labels remain hints: the entrance label lacks
terrain support, Slave Mines/Throne Room have multiple terrain levels, and
Trainer Hill/North Wall have distant overhead Boundary sheets. These are not
accepted camp destinations. This source update sends no game input and does not
change the 0.39.19 crossing or 0.39.13 assist controls. G0 remains passed.
Source 0.42.24 can explicitly propose a single Diffuse floor beneath distant
Boundary sheets, then apply the complete movement-area checks. Stacked floors,
unknown materials and surfaces touching the body still refuse. Fresh height
readings can use the exact checked initial floor and stop if that plan changes.
The copied Crushbone entrance now reaches the separate region-tree refusal;
this is not yet a traversable camp route. No new owner test is requested.
Source 0.42.25 adds a separate model of the client's native region metadata,
including missing-branch default class0, float32 arithmetic and full transition
flags. It checks body and step volumes alongside the existing terrain/static
checks. Its results are still offline evidence; they are not connected to the
owner movement permission yet. The current launchers and controls are unchanged.

Source 0.42.26 connects the native region model to copied Crushbone initial
planning and fresh stopped-height observations through an explicit opt-in.
Terrain/static checks remain required, and the original BSP refusal stays in
the evidence. This is a development-only step: destination movement and the
owner driver refuse these new plans until per-move integration is complete.
The 0.39.19 crossing and 0.39.13 assist launch commands are unchanged. G0 is
passed; no repeat or additional owner test is requested by this source update.

## Source travel in Crushbone on Alienware: 0.39.21

This is a supervised movement preview toward **Slave Mines**, not the requested
1–20 leveling bot. It uses the existing rotation helper, but combat and leveling
stay disabled during this finite test. No hand-recorded route is needed.

Stop and close the older measurement helper yourself so only one helper runs.
On Alienware:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.21
./launch.sh --measure-navigation
```

Start inside Clan Crushbone on clear, flat, open ground. Open the map and use
**Test /location hotbutton…** in this same helper session. Then close the map
and chat, clear your target and turn melee off. Choose **Travel to Slave Mines…**.
It gives a four-second focus countdown, measures motion with seven short
presses, collects fresh positions and plans the route before starting travel.

Stay present for this test. **F9, F11 or Stop measurement cancels.** The route
stops at the destination or at a failed check, observed attack or zone change.
It does not fight, loot, recover from death or restart itself. The 25-minute
travel limit and movement budgets are shared across ordinary walking and steps.
An ambiguous step waits without movement and then stops if it cannot resolve.

Results are saved under `~/.local/share/eql-automation/route-trials/`; the GUI
shows planning, position collection, travel and the final stopped result.
Real traversal, dynamic clearance, camp safety and leveling remain unverified.
**G0 already passed. Do not repeat G0.**

## Short movement in Crushbone on Alienware: 0.39.20

The existing **Supervised short route trial…** action now supports both
Greater Faydark and Clan Crushbone. It measures movement, checks a new two-unit
path from your current position, follows it if checks pass, then stops.
This is not a camp route or the 1–20 autopilot. Actual client traversal remains
unverified; combat, looting and leveling stay manual. Assist stays on 0.39.13.
G0 is passed and does not need repeating.

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.20
EQL_ROTATION_TRACE="$HOME/eql-crushbone-trial-trace.jsonl" ./launch.sh --measure-navigation
```

Close the other helper first. Select the correct character. Open the in-game
map and run **Test /location hotbutton…** in this helper to recognize the current
zone and verify the configured location key. A new zone entry observed by this
helper also supplies zone identity. Close the map and chat, clear your target
and turn melee off. On clear, flat, open ground, choose **Supervised short route
trial…** and focus the game during its countdown. Stay present through the
seven calibration presses and short route. **F9, F11 or Stop measurement stops
it.** Failed checks stop the action; it does not retry automatically.

The Crushbone loader reads the installed executables, zone archives and catalog
to ensure they match the copied model. A changed file stops the job. It never
writes the game installation. Results are saved under
`~/.local/share/eql-automation/route-trials/`; keep the trace above if it stops.
The two GFay travel actions remain available and still stop after their stated
approach/crossing destination. Crushbone camp selection and onward leveling are
not included in this preview.

## Travel into Crushbone on Alienware: 0.39.19

This is a supervised crossing preview, not unattended leveling. It starts in
Greater Faydark, plans from fresh current positions using copied client geometry,
and stops after observing the expected Crushbone entry and two new positions.
It does not move around Crushbone, fight, loot, sell or choose a camp. Actual
client crossing is unverified. G0 remains passed; do not repeat it.

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.19
EQL_ROTATION_TRACE="$HOME/eql-crossing-trace.jsonl" ./launch.sh --measure-navigation
```

Close the other helper first. Select the correct character, open the in-game
map and use **Test /location hotbutton…** to recognize your current GFay zone.
The helper needs that successful hotbutton setup in the same session. Close
the map and chat, clear your target and turn melee off. On clear, flat, open
ground, choose **Travel into Crushbone…** and focus the game during its countdown.
It performs seven short calibration presses, then plans and follows the route.
You do not need to record a route by hand.

Stay present. **F9, F11 or Stop measurement cancels.** Owner input, lost focus,
combat hazards, unexpected zoning and failed checks stop the action. It does
not restart itself. The source route has a 25-minute/3,000-move limit, with at
most 90 additional seconds to observe arrival. Known loading prevents location
hotbutton input; loading during an active location request may stop the preview
rather than continue. The result is experimental until you observe it in game.

The result is saved under `~/.local/share/eql-automation/route-trials/` as
`owner-crossing-*.json`. Keep `~/eql-crossing-trace.jsonl`; the displayed result
and the saved record identify where it stopped. **Travel toward Crushbone…**
remains the approach-only option. Assist remains the separate 0.39.13 launcher.

## Travel toward Crushbone on Alienware: 0.39.18

This new preview adds **Travel toward Crushbone…**. It uses the installed
client's map label, the copied navmesh and your current position. It measures
motion, plans a full Greater Faydark approach, follows individually checked
moves and stops. It does not cross into Crushbone, fight, loot or level for you.
Real-client traversal has not been verified. This update can recognize your
current zone from the open map during the stationary hotbutton test. It checks
the exact zone name against the installed catalog and compares all three map
coordinates with the new `/location` reply. Live map placement and recognition
still need owner testing. Keep logging enabled; logging changes and zoning
clear the observation. The preceding destination flow passed simulated arrival
and F9 release checks.

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.18
EQL_ROTATION_TRACE="$HOME/eql-destination-trace.jsonl" ./launch.sh --measure-navigation
```

Use one helper at a time. Select the correct character. In the game, open the
map so its zone name and three coordinate labels are visible. Run **Test
/location hotbutton…** in this helper and focus the game during its countdown.
Look for **Current zone recognized from map: The Greater Faydark**. You can
start while already in GFay; a fresh zone entry is an alternative if map
recognition is unavailable. Unreadable or mismatched labels leave the zone
unknown and travel refuses before moving. The test sends the configured
hotbutton only once and does not start travel. After it stops, close the map
before choosing travel.
Start on clear, flat, open ground; close chat, clear your target and turn melee
off. Choose **Travel toward Crushbone…**, then focus the game during the
four-second countdown. The seven calibration presses and route belong to this
one action. The short two-unit trial remains optional; G0 is passed and does
not need repeating.

Stay present. **F9, F11 or Stop measurement stops the action.** Physical input,
focus loss, combat/log hazards, zoning or a failed geometry/position check also
stop it. No automatic restart occurs. Travel is limited to 25 minutes, 3,000
moves/turns and 10,000 planned units; those ceilings do not guarantee arrival.
The initial clear-ground statement covers calibration, not every part of the
route. Watch for moving obstacles and enemies. Route status shows the current
segment, and the stop message preserves the specific failure reason.

Results are saved under `~/.local/share/eql-automation/route-trials/` with an
`owner-destination-` filename, plus route-session records in its `routes/`
subdirectory. Keep `~/eql-destination-trace.jsonl` for diagnosis. Assist remains
the separate 0.39.13 launcher; this travel preview cannot run combat rotation.
The requested seamless assist/full-auto switch and hands-off 1–20 remain
unfinished.

## Short route test on Alienware: 0.39.15

This is the next traversal check, **not a usable 1–20 leveling route**.
Preview 0.39.15 is staged on Alienware. Its no-input GUI startup and installed
data checks pass; actual route traversal is unverified. Do not reuse a saved
motion result as heading.
This action measures and follows the new path in the same uninterrupted session.

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.15
EQL_ROTATION_TRACE="$HOME/eql-route-trial-trace.jsonl" ./launch.sh --measure-navigation
```

1. Close the other helper before launching. Choose the correct character.
   **The new helper must observe a Greater Faydark zone entry while it is
   running.** Starting it while already in GFay cannot establish the zone from
   old log history. If no new entry is seen, the trial refuses before moving;
   this older preview does not include the map recognition in 0.39.18. Any zoning is yours
   to perform, and is not part of this test's movement.
2. Configure/test a hotbutton containing only `/location` in this same helper,
   using the stationary hotbutton steps below. A prior helper's result is not
   reused. An unused F1–F5 or F13–F24 key is required; F6–F12 remain reserved.
3. On wide, clear, flat GFay ground, close chat, clear the target and turn
   native melee off. Click **Supervised short route trial…** and confirm the
   setup. Loading verifies the copied data against the installed archives and
   catalog before any movement. Focus EverQuest during the four-second countdown
   and release all keyboard/mouse input. Stay present.
4. It makes four short forward presses and three turns, then collects new
   stopped positions, checks a new two-unit path from there, obtains fresh
   height observations and follows that path if all checks pass. It ends
   stopped. **F9/F11 or Stop measurement cancels throughout.** A failed check
   stops the action; there is no automatic retry or fallback typing.
5. Report the displayed **Route trial arrived/stopped** result or its refusal
   reason. Evidence is under `~/.local/share/eql-automation/route-trials/` and
   the trace is `~/eql-route-trial-trace.jsonl`.

The GUI shows countdown, startup, route and stopped stages. The ordinary
**Supervised motion measurement…** button still finishes after measurement;
only the distinct route-trial button can continue into a short path.
The initial path stays inside one navigation polygon. Body dimensions, motion
bounds and open-ground conditions remain conditional observations/assumptions.
The owner supervises current obstacles and chat/target state. This test does
not fight, select targets, loot, choose camps, cross zones or level unattended.
Pipe completion/cancellation checks and copied geometry loading do not prove
that real-client traversal works. Current level, XP/hour, deaths and camp are
unknown; no automated level gain has been verified.

The development backend can plan a complete path from
fresh current coordinates to the copied client map's Crushbone approach marker.
A copied-data probe produced 197 segments. It retains the starting floor and
checks each later movement through the existing collision guards; it does not
claim the entire path is clear. This backend change does not extend the owner
trial's distance or enable full auto. Keep using 0.39.15 for the pending short
traversal check; no new G0 or separate test is requested.

Source 0.42.12 additionally carries the pinned tile-seam model into each
movement check, retaining terrain, object, BSP and release requirements.
Copied-data checks pass at two real map overlaps. Synthetic pipe tests have
also crossed seams, but strict timing checks still stop runs under heavy
CPU pressure. This is development evidence, not real-client route acceptance.
The full approach still needs its own bounded owner travel action; the short
trial limits have not changed.

## Motion-only option on Alienware: 0.39.12


This supersedes the stationary-only 0.39.11 test. Run the hotbutton check and
then the short motion measurement in the **same helper session**. It does not
start leveling or follow a route.

1. In EverQuest, make a hotbutton containing **only `/location`**. Bind it to
   an unused function key among F1–F5 or F13–F24; remove any other action on that
   key. F6–F12 are reserved for the helper. Manually verify that your selected
   key prints your position and does nothing else. The helper does not edit
   your game configuration or choose a key for you.
2. Close other helpers. Start the new candidate on Alienware:

   ```bash
   cd ~/.local/share/eql-automation/owner-assist/0.39.12
   EQL_ROTATION_TRACE="$HOME/eql-motion-trace.jsonl" ./launch.sh --measure-navigation
   ```

3. Choose the correct character and level. In **Movement measurement**, click
   **Test /location hotbutton…**, select the key you configured, and confirm
   that you verified its single-command binding. Click **Test once**.
4. Within four seconds, focus EverQuest, close chat, stand still and release
   the keyboard/mouse. The helper sends one 20 ms key press. F9, F11 or
   **Stop measurement** cancels. Do not click **Check movement stop**; G0 is done.
5. The result should say **One fresh location reply observed** and give a
   report path under `~/.local/share/eql-automation/location-hotkey-tests/`.
   A missing or duplicate reply,
   focus loss or activity during the query stops the test. It does not retry
   or type a fallback command.

6. After a successful reply, stay in this helper. Move yourself onto **wide,
   open, flat ground**, away from edges, water, obstacles and enemies. Close
   chat, clear your target and turn native melee off. Keep the tested hotbar/page.
7. Click **Supervised motion measurement…**, read the short sequence, confirm
   the ground/setup and start. You have four seconds to focus EverQuest and
   release your keyboard/mouse. Stay present. It makes four 0.10-second forward
   presses and three turns (0.05, 0.15 and 0.15 seconds), with stopped position
   checks between them. **F9/F11 or Stop measurement cancels.**
8. It finishes stopped and saves a complete or partial result under
   `~/.local/share/eql-automation/motion-measurements/`. Send the displayed
   result/refusal reason or `~/eql-motion-trace.jsonl`. No repeat is automatic.

The open-ground/setup declarations are yours; the helper does not independently
verify obstacle clearance, chat closure or the hotbutton's current contents.
Physical input, focus/session/settings changes, recognized combat/transition
log messages and invalid/missing position replies stop the measurement. The
relative result needs no new zone-entry event and does **not** establish a zone,
a route or a guaranteed maximum speed. It is not installed as autopilot data.

The actual staged helper passed Alienware pipe-only completion and cancellation
smokes plus offscreen GUI/dialog checks; no game input was sent. No live motion
result or route has been accepted yet. Assist uses the separate 0.39.13 preview.
If the helper was restarted, run its hotbutton check again before measurement.

## Owner-run rotation test on Alienware today: preview 0.39.13

Close any already running Solo Assist window. Blizz starts the game through
Lutris and logs in himself. In an Alienware terminal, start the isolated
preview:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.13
EQL_ROTATION_TRACE="$HOME/eql-assist-trace.jsonl" ./launch.sh
```

Preview 0.39.13 fixes stale HP/mana surviving OFF → F8 or settings changes.
Automatic healing waits for a new reading; explicit F10 remains available
without HP. The actual engine regression and offscreen startup passed on
Alienware without game input. Live HP calibration still needs owner feedback.

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

## Observe current position from the helper: candidate 0.39.10

This is the pending stationary observation. No repeat of the completed
G0 movement pulse is needed.
Close other helpers, then launch on Alienware:

```bash
cd ~/.local/share/eql-automation/owner-assist/0.39.10
EQL_ROTATION_TRACE="$HOME/eql-position-observation.jsonl" ./launch.sh --measure-navigation
```

Choose the correct character and level in the helper. Stand still in the game
with logging enabled and the map set to **Current Zone**. Click **Observe
current position first**, then focus EverQuest and type `/location` **once**
within 60 seconds. Press Enter, close chat and leave the game focused and map
visible. The helper waits two seconds after the new log line, then saves
player/target/map crops and `unbound-location.json` to its private observation
store. Candidate 0.39.10 then runs the icon diagnostic automatically, saving
`combat-diagnostic-assets/` and `combat-analysis.json` beside the pair. The
measurement tab reports whether analysis was saved or unavailable; an analysis
failure preserves the raw capture. The tab displays the saved directory or
refusal reason.
Report that path when available. It saves no chat crop and sends no commands,
keys or clicks. Ordinary chat entry keeps rotation stopped while this explicitly
requested diagnostic waits; F9, F11, **Stop measurement**, settings changes or
closing the helper cancel it. Start a fresh measurement helper for collection
if it has previously created an input sender for another test.

The record remains unbound: it does not verify character/zone identity, map
alignment, standing still, log flush latency or movement safety. It cannot
enable G2, F11 or leveling. **Check movement stop** is a separate pulse button;
do not click it for this observation. The path has been checked with synthetic
events and frames; actual game capture still needs owner-run evidence.

Assist 0.39.13 remains the current rotation test; run it separately.

## Source builds and offline tools

Source 0.42.46 is privately published on Alienware at:

```text
~/.local/share/eql-automation/owner-tools/0.42.46/source
```

Source builds are development tools, not replacements for the owner launchers
above. Source 0.42.46 adds a developer-only static movement audit:
`python3 -B tools/audit_client_motion_update.py --help`. It reads only the
pinned owner executable and writes evidence under the private client-data
store. The client has additional movement terms beyond forward speed; this
audit does not certify a speed cap, enable movement or require an owner test.

Source 0.42.45 adds `CampProbePreparation` for a future camp heading
measurement. It checks an all-heading source envelope from a fresh stopped
height and explicit motion hypotheses. It requires another newly collected pair
at the exact checked position afterward, retains both original timestamps and
rejects changed or expired state. It grants no movement authority and is not
enabled in the owner controls. Current scene and independently supported motion
bounds are still required before automatic measurement. Owner preview remains
**0.39.30**; there is no new owner check for this source-only increment.

Source 0.42.44 connects a fresh post-recovery position collection to the
existing helper, retaining the actual configured hotbutton and acquiring its
own reader lease. Collection starts once after the first kill/recovery, records
both request receipts and fresh height correspondence, and resumes the same
camp after release. Cancellations also retain diagnostic receipts. These
records do not become lasting movement authority; a future relocation must
collect new observations. No automatic relocation is enabled.

Source 0.42.43 captures the actual arrived floor before travel gives
up its log reader, then retains it through camp without rearming the travel
observer. It also adds a pure validator for two newly collected stopped replies
on that floor. The new height correspondence must match the arrival offset;
an expired old calibration cannot supply it. Source 0.42.44 now supplies the
automatic collection above; camp relocation remains unfinished.

Source 0.42.42 shares the existing route driver's original-terrain,
object and body-region checks with an unknown-heading probe checker. It can
use a retained source floor where a baked-mesh start cannot establish support.
The copied-data diagnostic `tools/audit_camp_source_probes.py --help` replays
the historical Slave Mines floor and checks explicit hypothetical probe sizes.
It sends no input; successful geometry is not fresh character state, measured
speed, or permission to move. Live floor capture, fresh height/heading collection
and automatic relocation are still unfinished. That source increment left preview 0.39.28 unchanged; the current preview is
0.39.30 above.

Source 0.42.41 adds a continuous area check for a possible short pulse
when heading is unknown. It requires fresh stopped observations and checks all
possible directions against copied terrain, objects and region data. It does
not send input or enable automatic camp relocation. The diagnostic
`tools/audit_camp_probe_envelopes.py --help` describes its explicit hypothetical
motion/body parameters; results stay in the private data store. That baked-mesh
probe refuses both copied points: Slave Mines needs retained floor provenance
and North Wall has incomplete baked coverage. The source-floor checker in
0.42.42 above supports five tested hypothetical areas; it does not waive
those mesh refusals or enable movement. G0 stays passed.
Use preview **0.39.30** above for owner-run assist/travel/camp tests.

Source 0.42.38 adds bounded near-straight proposal compaction and the
pinned North Wall/Castle guide. Its complete copied-data check passes; the
owner preview still rebuilds a fresh route before any travel. The diagnostic
accepts `--compact`; its longer offline audit budget does not change runtime
movement, observation or travel limits.

Source 0.42.37 added long source-face route proposals, reversed itinerary
guides and the copied-data diagnostic `tools/audit_crushbone_camp_transit.py`.
Its `--strategy graph|reverse` options never send input. The initial North Wall
graph failed ground coverage; the original reverse-corridor check exhausted
its work budget. Those attempts remain refused; the compacted 0.42.38 check
supersedes them for North Wall. That source increment shipped with preview 0.39.26; the current preview is
0.39.30 above. G0 remains passed. Use the owner launch commands above for game testing.

Source 0.41.97 additionally wires a finite, owner-supervised relative
motion experiment into candidate 0.39.12; it preserves the stationary setup
and strict assist behavior. No full-auto route is enabled.

Previously, source 0.41.96 shares the same bounded hotbutton sender between route
acquisition and the new 0.39.11 stationary setup test. The explicit owner job
handles sender initialization, a four-second focus countdown, one key cycle,
fresh-log response checks and a saved result. F9/F11, settings/jobs, focus loss,
duplicate replies and timeouts stop it; there is no automatic retry or typing.
The previous manual observation and assist controls are unchanged.

Source 0.41.95 adds a route-position option that presses a single
owner-configured `/location` hotbutton instead of typing into chat. It uses
the existing sender, stop/focus checks, input observation and release watchdog;
the route still requires a fresh, single location reply. It never assumes a
default key. Route use still needs same-session owner setup/test evidence and
route launcher integration; 0.39.11 now provides the stationary setup test.
The current Alienware files contain no `/location` hotbutton. Per-character
font/caret classification belongs to the optional typed-command approach; it
is not an owner requirement or a prerequisite for the hotbutton alternative.
The existing G0 result remains passed, and no repeat is requested.

Source 0.41.94 connects corrected glyph/caret geometry to conditional
pixel sampling. Unknown atlas-edge pixels have explicit masks. The matcher
compares every prefix on the same known pixels and cannot promote a partial
comparison to a complete-field match. The offline font importer now offers
`--sample-pixels` with explicit geometry, projection, tint and pipeline evidence;
see `python3 tools/analyze_font_gdi.py --help`. It saves separate sampled PNGs
and known-pixel masks below the private font-probe store. These are rendering
hypotheses, not live chat focus/closure/selection classifications. No owner
launcher, control or pending observation changes.

Source 0.41.93 adds the checked `/location` observation provider. It
brackets each independent UI classification with owner-input, focus and log
checks. Start/end require observed closed chat; intermediate keys require
the exact complete focused draft, with the insertion point at its end and
no selection. The calibrated pixel classifier is still missing: raw frame
candidates cannot authorize typing. No owner command or hotkey changes.

Source 0.41.92 connects terrain, static-object and BSP volume checks to
the checked route sender. It prepares both possible control footprints while
stopped, then binds the selected result to the exact fresh proposal and receipt.
Body size, speed, pivot drift and timing bounds must be supplied independently;
there are no assumed live defaults. OFF can interrupt preparation. The 50 ms
proposal limit and 0.5 s position lifetime are unchanged. A copied GFay first
cell and a synthetic pipe pulse passed; this does not enable F11 or accept a
live route. The current stationary observation remains the next owner check.

Source 0.41.91 supplies the route loop's concrete `/location` executor.
It reuses the existing bot's command/key code and the same checked command
implementation as motion measurement. Every key needs a current independent
chat/scene observation bound to the exact submitted prefix. Route commands
retain their input-attempt records in the saved session report; failed drafts
remain uncertain after keys are released. This executor has no movement method,
and assist cannot attach it. Current scene/zone/height/motion providers still
need live evidence. No new owner command, hotkey or observation is enabled.

Source 0.41.90 connects the fixed-route follower, ground reader and
checked sender into an engine-tick loop. It collects two fresh stopped
positions before each step, preserves the exact reference during the pulse,
then continues from the committed floor state. The retained helper adapter
handles stop/settings/close cancellation and saves partial or arrived records
under `~/.local/share/eql-automation/route-sessions/`. Assist helpers reject
this attachment. No owner job or hotkey creates a route session: current
scene/zone/height/motion inputs and a guarded route-location command executor
are required before it can be enabled. The completed route test used synthetic
feedback and a pipe, not the game. Existing owner launchers and pending
observation instructions are unchanged.

Source 0.41.89 adds a saved-position diagnostic. After the existing
observation helper reports a saved directory, the lead can analyze it without
opening a display or sending game input:

```bash
python3 tools/analyze_owner_position_pair.py \
  --capture-dir /path/reported/by/helper \
  --pair-sha256 SHA256_OF_UNBOUND_LOCATION_JSON
```

The tool checks saved file hashes, capture-record timing and overlapping crop
pixels. Optional `--zone-names`/`--zone-names-sha256` and `--map-label-text`
look up an explicitly supplied label hypothesis; they do not perform OCR.
Optional `--route`/`--route-sha256`/`--mesh`/`--mesh-sha256` summarize a pinned
offline route, with the mesh tied to that route's named zone. Recorded process
IDs are not current identity evidence, and raw `/location` coordinates remain
unbound to WLD. The tool does not enable F11 or accept a live route. There is
no new owner check: the pending 0.39.10 stationary observation is unchanged.

Source 0.41.88 corrects the isolated font probe's DC setup and records
its mapping mode, background mode and bitmap reuse policy. The native helper
defaults to `reuse`; `clear-each` supplies a comparison baseline and
`white-reuse` exposes pixels that GDI leaves untouched. Run it only in its
separate development Wine prefix. Import reused results with
`--diagnostic-only`; `--compare-baseline PATH --baseline-sha256 SHA` adds a
pinned comparison. Reused results cannot supply an independent glyph bank.
The earlier transparent-background claim was an import-labeling error:
the client calls `SetMapMode(MM_TEXT)` and reuses its bitmap. Corrected probes
observe an opaque default background and history-dependent pixels outside
glyph extents. These are development diagnostics, not live-client acceptance.
Source 0.41.87 models the input font's separate integer advances,
fractional glyph rectangles, vertical centering and independently rounded caret.
The font importer accepts optional `--base-height`, `--ui-scale` and
`--client-box-ui LEFT TOP RIGHT BOTTOM` together to record those geometry
hypotheses. Its PNGs remain the raw GDI model; geometry is a separate manifest
diagnostic, with GPU projection/sampling and live equivalence explicitly false.
Only fitting, left-aligned single-line prefixes are supported. This adds no
owner check or game control. Source 0.41.86 adds an offscreen GDI font probe and a pinned importer for
its glyph data. The probe belongs in a separate development Wine prefix; it
must not run in the owner's protected game prefix. The importer verifies the
actual selected font bytes and reproduces the inspected 4-bit alpha conversion.
Copied-font rendering hypotheses are available. Source scale compensation is
now modelled; current font overrides, selected shader state, bitmap/atlas
history, final texture sampling and live equivalence still need checks.
These tools add no owner test or game controls. Source 0.41.85 can compare the exact submitted command prefix with the
same frame's chat input pixels, using an explicitly supplied rendering bank.
It scores the entire field, including extra text, under a declared constant-
background model. No default live font bank is supplied: the input's initial
font slot is now traced separately from saved chat-output style. Pixel candidates never prove
focus, draft ownership or closure. No new owner action or route input is enabled.
Source 0.41.84 records each attempted command write and binds observation
checks to its exact immutable submitted-prefix snapshot. A failed write stays
uncertain after cleanup; completed writes do not prove client delivery, draft
ownership or closed chat. This supports the pending independent scene observer;
it enables no new owner control or measurement. Source 0.41.83 uses a prepared source-check plan; unchanged INI/include
files are hashed without reparsing them on every frame. It connects the optional chat-input diagnostic to the same
frame used for gauge/combat reading. It records crop hashes without saving chat
pixels or interpreting focus. Prepared client layout parsing avoids repeating
XML parsing; full source content and selection checks still bracket the feature
pass. Source changes refuse the prepared layout. Both XML and numerical
preparation costs are retained separately;
each call still captures a new frame and records the complete observation time.
Preparation grants no scene or movement permission. The copied-source route
work and remaining live checks are tracked in [LEVEL_1_20.md](LEVEL_1_20.md).

From the source directory, these examples are offline only:

```bash
python3 -m eql_automation --demo
python3 -m eql_automation --demo-assist
python3 -m eql_automation --shell
python3 tools/reduce_motion_calibration.py --describe-experiment
```

In the simulator shell, `mode assist`, `mode full`, and `mode off` switch modes
without restarting; `status` shows the selected mode, `stop` selects OFF, and
`quit` exits. These are terminal commands, not live game controls.

[STATUS.md](STATUS.md) records the current blocker and next step.
[HOWTO_REFERENCE_04179.md](HOWTO_REFERENCE_04179.md) preserves earlier source
commands and development notes; its old test instructions are historical.
