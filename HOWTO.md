# EverQuest Legends automation — current build 0.17.0

## Current availability

This build is an **offline simulator and planning library**. It does not launch
EverQuest Legends, log in, control a character, or send game input. The owner's
installed client points to Daybreak's live service. Its published
[Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct),
[EULA](https://www.daybreakgames.com/eula?locale=en_US), and
[Terms of Service](https://www.daybreakgames.com/terms-of-service?locale=en_us)
prohibit the requested unattended bot and appear to prohibit a rotation assist
on the live service without Daybreak authorization. The owner says the target
is a private server, but its endpoint has not been found; the installed retail
client still points to Daybreak. No live mode is enabled.

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

`--synthetic-1-50` runs a closed-loop **fabricated** world. It exercises the
planner and stops at synthetic level 50 or fails if progress stalls. The output
prints `simulation_only: true` and `real_client_level_verified: false`.
Trace, summary and a synthetic status file go under
`~/.local/share/eql-automation/runs/synthetic-1-50-<UTC timestamp>/`.
Use `--output DIRECTORY` to choose a different trace directory. These files
are test evidence only; they do not show an EverQuest Legends character at 50.

`--demo-navigation` shows a synthetic blocked edge being quarantined and a
route changing to a safe alternate. The pure navigation controller waits for
an observed start position, uses only explicitly verified graph edges, and
pauses on uncertain movement or zoning. It does not press movement keys.

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
the corrected profile. It requires the same character/class/level, a verified
current target, focused game with chat closed, health and mana readings less
than one second old, and observed gem IDs matching the profile. It only
proposes abilities observed as available. The proposal keeps a cancellable
mode permit; focus, target, observations and permit must be checked again
before each future key. This is a code-level contract with synthetic tests,
not a running in-game rotation. There is no live observer or input sender.
`--demo-assist` prints a synthetic proposal and shows that OFF invalidates it.
`--demo-gauges` uses Pillow to read fabricated red HP and blue mana bars. It
does not capture the game.

The offline `GaugeReader` accepts only explicitly calibrated inner bars from
a focused game-window image at the same window size and active layout. Its
calibration requires both bars to appear at least 85% full. A changed layout,
unfocused window, unreadable fill or empty-looking bar yields **unknown**;
it never treats an unreadable bar as zero HP or mana. Default client XML uses
red for both player and target HP, so color alone cannot identify the player
bar. Live crop coordinates and the active skin have not been verified.

`--index-ui-widgets` reads copied default client UI XML and stores a searchable
widget index outside git. `--query-ui-widgets TEXT` searches names and EQType
codes. The index includes player health/mana/XP and level labels, target
gauges, spell gems, chat input and keyboard assignment widgets. It describes
the **default static UI only**: the active skin, screen positions, live values,
character identity, chat focus and working hotkeys have not been verified.

| Simulated mode | Actions permitted by the planner |
| --- | --- |
| Off | None |
| Assist | Casts, abilities, heals, buffs on the current target only; never movement, target changes, autoattack, loot, vendors, camps, zones, or login |
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

The prior October Paladin/Cleric prototype remains at
`/home/blizz/Projects/everquest-legends-rotation/`. Its historical controls
were F6 prepare, F8 assist toggle, F9 stop, and F10 heal. They have not been
live-verified and are **not** controls for this build. Its prepare action also
changes spell gems, and its combat action can toggle autoattack, so that code
cannot be used unchanged for strict ASSIST. Do not run its installer:
it writes character INIs in the protected Alienware prefix.

## Verification

```bash
python3 -m pytest -q tests/test_offline.py
python3 -m pytest -q tests/test_control.py
python3 -m pytest -q tests/test_spell_catalog.py tests/test_assist.py
python3 -m pytest -q tests/test_ui_schema.py
python3 -m pytest -q tests/test_screen_observer.py
python3 -m pytest -q tests/test_nav_evidence.py
python3 -m compileall -q eql_automation
```

The **real-client** level 50 run, in-game mode switching,
automated spell acquisition, camps, death recovery, and relogin are not
implemented or verified. `FINDINGS.md` records the exact client/server
evidence and blocker.
