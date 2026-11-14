# EverQuest Legends automation — current owner guide

Source **0.41.98** · rotation preview **0.39.6** · observation **0.39.10** · hotbutton + motion measurement **0.39.12**.

**The 1–20 autopilot is not ready. F11 and F12 are disabled.** No real route,
automated level gain or fresh-character hands-off 1–50 run has been accepted.
The client installed on Alienware connects to Daybreak. Blizz runs live tests
himself; the lead does not log in or control his character. Service-rule findings
and verification evidence are in [FINDINGS.md](FINDINGS.md).

| Mode | What is available today | Controls |
| --- | --- | --- |
| Assist / rotation | Supervised preview using the existing rotation bot. Blizz moves, chooses his target and controls melee. | F8 arm, F7 toggle, F9 stop, F10 request heal. |
| Full auto | In development; no accepted 1–20 or 1–50 run. | F11 is disabled. There is no live switch to full auto yet. |
| Read-only position observation | One owner-triggered capture; no commands, keys or clicks sent. | **Observe current position**, F9/Stop to cancel. |
| Stationary location-hotbutton test | Sends one explicitly configured key, then checks the log for one fresh position reply. No route movement or combat. | **Test /location hotbutton…**, F9/F11/Stop to cancel. |
| Supervised motion measurement | Four short forward presses and three turns on owner-confirmed open ground; saves relative observations and stops. | **Supervised motion measurement…**, F9/F11/Stop to cancel. |

Run only one helper at a time. **G0 passed; do not repeat the movement-stop
pulse.** The next owner check is the combined hotbutton + motion measurement
below. The manual position observation remains available separately.

Source 0.41.98 adds offline Crushbone crossing diagnostics. Four short local
crossings pass the copied-source checks, but the complete route remains
unaccepted. This does not change your helper, hotkeys or the next test below.

## Next owner test on Alienware: 0.39.12

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
result or route has been accepted yet. Assist stays the separate 0.39.6 preview.
If the helper was restarted, run its hotbutton check again before measurement.

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

Assist 0.39.6 remains the current rotation test; run it separately.

## Source builds and offline tools

The latest private source is staged on Alienware at:

```text
~/.local/share/eql-automation/owner-tools/0.41.97/source
```

Source builds are development tools, not replacements for the owner launchers
above. Source 0.41.97 additionally wires a finite, owner-supervised relative
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
