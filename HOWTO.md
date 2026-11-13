# EverQuest Legends automation — current build 0.27.0

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

`--audit-zone-regions ZONE` checks copied WLD BSP tree and region-label
references for `butcher`, `crushbone`, or `gfaydark`. It reports water and
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
