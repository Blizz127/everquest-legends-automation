# FINDINGS

## Butcherblock material chains and OBJ winding — 2026-11-13 05:34 CST

**VERIFIED copied-client material audit:** All 1,925 `0x36` meshes have valid
`0x36 → 0x31 → 0x30` material references; their polygon texture groups cover
every triangle exactly. Of the terrain's flag-zero faces, 45,384 use Diffuse
material parameters and **6,443 use Boundary** parameters. Its 868 flag-`0x10`
faces use Diffuse. Across the 1,862 non-sentinel object instances, all 53,028
flag-zero faces use Diffuse or Diffuse6, and all 28,655 flag-`0x10` faces use
Diffuse or transparent classes. The bounded audit manifest SHA-256 is
`79884f2e18dd69178b500a87a85ecf283177e6a4b41b390febd308779eef33e3`.
The current provisional OBJ includes the 6,443 Boundary faces as candidate
obstacles. The [Lantern OBJ writer](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Exporters/MeshObjWriter.cs)
has an option that excludes Boundary/Invisible geometry; no live evidence yet
establishes which choice matches this client's movement. Water regions and
door state are likewise unverified. Two focused synthetic material tests and
the copied-data audit passed.

**VERIFIED OBJ orientation correction:** A normal check found that 41,501
flag-zero terrain faces in the copied WLD's original index order point in
negative Z, versus 1,561 positive and 8,765 zero projected Z normals.
Following the Lantern writer, the provisional OBJ now writes each face in
reverse index order. An independent scan of the regenerated 115,411-vertex,
104,676-face OBJ found 41,501 terrain faces with positive projected Z normals,
1,561 negative, and 8,765 zero. Its current SHA-256 is
`1ec7706037c35c06205c026c4ed56c1b4032fd2fb7a8e2dbe0cf2490d18a1bc3`;
the manifest SHA-256 is
`aebc4fd5866ac890c30278b9e1eca2567de68ccb99f2075b96f904fdfe5a73f9`.
The previous `c4faf0...` OBJ remains as a historical local artifact and is
superseded for future bakes. **Neither orientation nor material inspection
establishes a walkable route.**

**VERIFIED local toolchain:** The upstream RecastNavigation source was cloned
outside git to `~/.local/share/eql-automation/toolchains/recastnavigation`,
checked out at the historical pin
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`, and built with CMake/Ninja
into local Recast and Detour static libraries. Demo, examples and upstream
tests were disabled. No navmesh bake or Detour query has yet run. The full
Butcherblock scene spans thousands of coordinate units, so a bounded local
bake is the next offline check; its output will remain provisional.

## Butcherblock provisional composed scene — 2026-11-13 05:29 CST

**VERIFIED copied-client model links:** All 75 type `0x14` actor definitions
resolve through one-based `0x2D` references to 75 distinct type `0x36`
meshes; each mesh has the exact corresponding `_DMSPRITEDEF` name. All 1,884
locations refer to one of these models by exact actor name. Across the 1,862
non-sentinel instances, the object meshes contribute 83,125 encoded vertices
and 81,683 triangles: 53,028 flag-zero, 28,655 pass-through `0x10`, and
**179 exact zero-area triangles**. This independently reproduces the
historical 179-face cleanup count, while the old navmesh artifact remains
absent.

**VERIFIED provisional geometry output:** `--build-butcher-candidate-scene`
streamed copied terrain and static-object meshes into
`~/.local/share/eql-automation/nav-candidates/butcher-solid-candidate-c4faf053a4e006c6.obj`
(SHA-256 `c4faf053a4e006c68cbb115b58cccfe293c219a24a10d39f2a73fdd3d1889624`)
in WLD XYZ with Z up. It contains 115,411 used vertices and 104,676
flag-zero, nondegenerate triangles, of which 51,827 are terrain and 52,849
are static-object instances. It excludes 29,523 pass-through triangles, 179
zero-area instance triangles, and 22 dropped-tree instances. A separate
read-only OBJ scan confirmed its hash, all face indices, finite coordinates,
counts and bounds. The untracked provenance manifest SHA-256 is
`1f6f07433e07b9368c06fbfdf39d4e41b144785340386936a387695fce61865c`.
This was the initial 0.19.0 artifact; the 0.20.0 winding-corrected artifact
and manifest above supersede it for future bakes.
The output and source client data are outside git and outside the release
archive. Focused synthetic tests checked exact model linking, uniform scale,
rotation axis/order and face filtering.

**INFERRED transform, still gated:** Projection follows the owner-data-compatible
[LanternExtractor object parser](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/ObjectInstance.cs)
and [OBJ writer](https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Exporters/MeshObjWriter.cs):
uniform scale, rotations from raw WLD units, then mesh center and instance
position. All copied scale fields used here agree, and no copied instance has
raw X rotation. This reproduces an exporter candidate, **not verified game
collision**. Shader/material filtering, water, doors, object state, conservative
agent clearance, navmesh routing and actual client movement remain unverified.
The historical 18,292-vertex/10,694-polygon mesh was a different reported
composition; its hash was not reproduced. No route was accepted.

## Butcherblock old-format mesh arrays — 2026-11-13 05:24 CST

**VERIFIED copied-client decoding:** A read-only `0x36` decoder for the
client's WLD version `0x00015500` parsed all 1,925 Butcherblock terrain and
object mesh records with bounded arrays and valid polygon indices. The terrain
`butcher.wld` contains 1,850 meshes, 64,230 encoded vertices and 52,695
triangles. Its polygon flags are 51,827 `0` and 868 `0x10`; no exact
zero-area triangles were found in the raw terrain mesh coordinates.
`butcher_obj.wld` contains 73 meshes, 7,092 vertices and 5,615 triangles
(4,682 flag `0`, 933 flag `0x10`, 65 exact zero-area triangles).
`butcher_2_obj.wld` contains 2 meshes, 1,011 vertices and 1,248 triangles
(1,224 flag `0`, 24 flag `0x10`, no exact zero-area triangles). The decoder
uses the [EQEmu WLD mesh format](https://docs.eqemu.dev/client/guides/file-formats/wld-by-windcatcher/),
where flag `0x10` denotes pass-through surfaces, and verifies the actual
copied files. Two synthetic mesh checks and the copied-data CLI audit passed.
The untracked `butcher-meshes.audit.json` manifest SHA-256 is
`043e827eafb1760c632ae43dc678b109666b9a5836ac44cf779abdd1899a4f21`.
Mesh centers, raw vertices and polygon flags are now decoded in memory;
actor-to-mesh references and placement transforms have not been composed.
**No collision mesh, navmesh, conservative clearance, or real-client movement
is yet verified.** The historical 18,292-vertex/10,694-polygon mesh was a
different reported composition and has not been reproduced.

## Butcherblock WLD fragment and placement provenance — 2026-11-13 05:21 CST

**VERIFIED copied-client structure:** A bounded read-only WLD inventory of the
four WLD members in the copied Butcherblock S3D files parsed their exact header
fragment counts. `butcher.wld` has 5,738 fragments, including 3,653 type `0x22`
regions and 1,850 type `0x36` mesh candidates. `objects.wld` has 5,652
fragments, exactly 1,884 each of types `0x32`, `0x33`, and `0x15`.
`butcher_obj.wld` has 1,149 fragments and 73 type `0x36` mesh candidates;
`butcher_2_obj.wld` has 38 fragments and 2 type `0x36` candidates. All four
parse through the declared fragment count with a four-byte `ffffffff` trailer.
The single out-of-range negative fragment-name reference is the first `0x35`
fragment in `butcher.wld`; it is reported as unresolved, not mistaken for an
object name. The parser follows the published
[VisualEQ WLD loader](https://github.com/alimalkhalifa/VisualEQ/blob/master/src/server/loaders/s3d.js)
and checks bounds against these copied files. No geometry has been composed.

**VERIFIED placement audit:** The 1,884 `0x15` locations in `objects.wld`
resolve to 69 distinct `_ACTORDEF` names. Every name matches one of the 75
distinct type `0x14` definitions in the two copied object-library WLDs by
**exact name**; similar names such as `BTENT`/`BTENT1` are kept distinct.
Twenty-two tree locations have the exact float32 Z value
`-32767.998046875` (10 `DPINE1`, 5 `DCEDAR1`, 5 `RPINE1`, 2 `BPINE`), leaving
1,862 non-sentinel locations. This independently reproduces the historical
1,884/1,862/22 count; it does not reproduce the historical navmesh hash or
validate any route. The six unused actor definitions include four door names
and two models in `butcher_2_obj.wld`. The audit records `collision_composed:
false` and `navigability_verified: false`. Four WLD inventories and the
placement audit are retained only in the untracked
`~/.local/share/eql-automation/client-data/retail-full/assets/manifests/`.
The placement audit manifest SHA-256 is
`42954af5065d6b5d1098a7b39b036e46e5229d1a7778dc27fc3ef55aa8e1a0f2`.
Four focused synthetic WLD/placement tests and the real copied-data CLI audit
passed. No Alienware install/prefix changes or live game input occurred.

## Butcherblock client archive inventory — 2026-11-13 05:15 CST

**VERIFIED read-only source/copy:** The Alienware game root contains
`butcher.s3d` (2,742,696 bytes, SHA-256
`af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839`),
`butcher_obj.s3d` (3,394,472 bytes, SHA-256
`ad4c886395c9af7f3de17be1c1a24785e295f892097b8e5785eec670a089c047`),
and `butcher_2_obj.s3d` (113,036 bytes, SHA-256
`cb5cabede79b53f9b884c15712ec07225f5ca81e1093be36f7d3d12b8ea03ece`).
These plus `butcher_assets.txt` were copied by read-only SSH into the
untracked `~/.local/share/eql-automation/client-data/retail-full/assets/`;
local hashes match Alienware. The install/prefix was not modified. The archives
have `PFS ` at offset 4. REA `open_binary` reported this custom container as
unsupported, so a bounded read-only PFS inventory was implemented from the
[PFS format description](https://github.com/martinlindhe/eqformat_pfs/blob/master/format_pfs.md)
and cross-checked against the owner's bytes.

**VERIFIED local member inventory:** `butcher.s3d` has 62 members, including
`butcher.wld` (2,645,544 bytes, SHA-256
`d4c8db248f4b7d23fe714ff3dceedaf0c83696b178327efcf88d6091e35c722c`)
and `objects.wld` (584,504 bytes, SHA-256
`605bc3b571a8779e62f09481c860b227024b0a97bd5877f4932517335682707b`).
`butcher_obj.s3d` has 149 members, including `butcher_obj.wld` (225,292
bytes, SHA-256 `06d6757279a3803a5c2b908b7f8bbce3c414bc802bd8271cb8558ac85acccc00`).
`butcher_2_obj.s3d` has 9 members, including `butcher_2_obj.wld` (82,812
bytes, SHA-256 `36598801bbe072e6ac72c6b4e368a14eeecebb478da35f9a004e7352705f54df`).
Full member manifests are outside git under `assets/manifests/` in that store.
Two synthetic PFS parser tests and three real copied-archive CLI smokes passed.
At this archive-inventory stage, no WLD mesh, static-object placement,
coordinate transform, collision clearance, or route had been decoded or
accepted. The later WLD audit above has since decoded placement provenance;
the historical Nov 6 serialized mesh remains absent.

## Butcherblock collision-evidence reconciliation — 2026-11-13 04:53 CST

**OBSERVED coordinator report, historical and not independently reproduced:**
The Nov 6 desktop task reported a Butcherblock terrain-plus-static-object
Recast/Detour bake with 1,884 instance records, 1,862 applicable placements,
22 rejected dropped-tree sentinels, corrected exact-name matching for duplicate
`btent`/`orctent`/`hgflag` placements, and 179 removed zero-area faces. The
reported composed mesh had 18,292 vertices and 10,694 polygons, serialized
SHA-256 `d1b57d2dab7b975e8d62821725bf992634136774720707fa103af10e238aad85`.
The reported closed-fayhouse ray hit a barrier at `t=0.1888`, while a
Yard↔South Kaladim route remained. Historical pinned sources were Lantern
`bb4cdba64c1f0453568f3a11f158a38ee1659d0c` and Recast
`9f4ce64458dfae86e1239c525ddc219c4e9e06f1`; a later local `bnav_query`
report described a complete 24-polygon/10-point path. The later overlay review
and classification of 23 detail-cleanup warnings is likewise historical.
These reports are **not** current retained navmesh proof or real-client acceptance.

**VERIFIED scoped reconciliation:** No Recast/Detour navmesh, placement table,
bake recipe, `bnav_query`, overlay audit or matching historical hash was found
in this project or `~/.local/share/eql-automation/`. A SHA-256 scan of 559
current code/store/release/run files (26,463,952 bytes, excluding copied client
data) found no serialized mesh hash; local release archives contain no
navmesh-named members. The removed historical working copy was not accessed,
recreated or touched. Thus the historical mesh **cannot be reused from
retained inputs in this project/store**. At the time of that reconciliation,
the only retained Butcherblock/Crushbone map artifacts were client drawing
geometry and labels, explicitly marked `navigability_verified=false`. The
copied S3D/WLD inputs documented above were added afterward and support a
new bake once their geometry and transforms are verified.

**VERIFIED client-map provenance:** Active snapshot `e36ee7fd32a5c4b42f45`
contains `butcher.txt` (24,225 drawing lines, 0 labels, source SHA-256
`04db2b25ebc89a44aaf685899cdb781da68fe3106b09c445bcc526c261d4029c`)
and `crushbone.txt` (5,469 lines, 0 labels, source SHA-256
`e22f714cbd7733918b7f0fd0c6a9b0592974ff9b5e497841e9dc69202396b313`).
The thin label layers are `butcher_1.txt` (1 line, 4 labels, SHA-256
`a1cea4378673518b5d3d63fa43bfa42d62bbbbec2a58d15fe7e3ad907b60bcb0`)
and `crushbone_1.txt` (0 lines, 1 label, SHA-256
`43704aa2af7de192cdbd7b61920278bdc7fe88bd80b1e603eac9c95aa450c87c`).
Client zone IDs are 68 Butcherblock Mountains, 54 Greater Faydark, 58 Clan
Crushbone. Labels suggest **review only** Butcherblock→Greater Faydark→Crushbone;
no zone transition has been traversed or accepted as a graph edge. The
reported Greater Faydark label vertical mismatch of about 236.82 units is
unresolved. Reported agent dimensions `(6,3,3,50)` routed while conservative
`(8,5,2,45)` disconnected; current clearance acceptance is absent. Dynamic
doors, water, zone transitions, mob levels, camp safety, XP/hour, and actual
movement are unverified.

**Result:** Butcherblock is the first navigation/camp review target and
Crushbone the next, followed by camps chosen from a character's observed
level and suitability. The current bot has no accepted real-client route.
Actual client acceptance is **not ready**: the private endpoint/separate login
config remains unknown; a fresh test character has not logged in; and no
retained collision mesh/recipe plus clearance and live movement evidence is
available. ASSIST remains movement-free.

**VERIFIED offline audit tool:** `python3 -m eql_automation --audit-butcherblock`
reads the active snapshot, rehashes the four copied client maps, and reports
their verified source hashes, historical
mesh absent, all collision/live acceptance flags false, and six missing
evidence classes. An optional artifact can be hashed only inside
`~/.local/share/eql-automation/`; a matching hash is provenance only and
never creates graph edges. Eleven focused navigation/evidence tests passed,
including refusal of artifact and copied-map symlinks outside that store and
detection of a changed copied map.

## Offline player gauge reader — 2026-11-13 04:22 CST

**VERIFIED copied client XML:** Default PlayerHP has red FillTint
`(150,0,0)` with EQType 1; PlayerMana has blue FillTint `(0,100,200)` with
EQType 2. TargetHP is also red `(150,0,0)`, so color alone cannot identify
the player gauge. The copied XML hashes are recorded below. **VERIFIED
synthetic only:** The inherited flat-bar algorithm now runs in pure Python
without NumPy. A `GaugeReader` accepts a calibrated full-frame player HP/mana
crop only when the game window is reported focused, its size and active layout
fingerprint match, and both colored fills remain readable. Calibration
requires bars at least 85% full. In a fabricated 120×30 image it returned
HP 0.5 and mana 1.0; an unfocused frame returned unknown. The reading can be
passed to `AssistObservation`, which still requires target, character, gems
and chat state. No actual game screenshot, active skin, calibration or
character state was observed.

## Default client UI widget inventory — 2026-11-13 04:04 CST

**VERIFIED read-only client data:** The Alienware's `eqclient.ini` has `Log=1`
and `UIScale=1` (SHA-256
`a10560ba3301c411f1b9eb05b5ad2627b4577222b430a7acf59687341356c7fc`).
Seven default `uifiles/default/EQUI*.xml` definitions were copied read-only
to the untracked local client-data store and their source hashes checked.
`EQUI.xml` includes the player, target, spell gem, chat, inventory and options
windows. A validated index contains 557 static widget IDs. Representative
widgets are PlayerHP EQType 1, PlayerMana 2, ExpGauge 4, LevelLabel 2,
TargetHP 6, Target_Class 1000, Target_Level 1001, spell gems
`CSPW_Spell0`–`CSPW_Spell13`, and editable `CW_ChatInput`. The keyboard
assignment list is present in OptionsWindow. The derived index is
`~/.local/share/eql-automation/map-store/indices/ui-widgets-446c8657ad6284caf128.json`.

**LIMIT:** Static XML does not identify the active skin, runtime positions or
values, current target, character identity, gem IDs, chat focus, XP/hour, or
valid hotkey bindings. The client was not launched and no character/log was
read. The offline assist demo proposed `/cast 3` for a synthetic level-1
Paladin and rejected the proposal after OFF. Concurrent emergency stop and
mode-indicator failure tests leave the controller latched OFF. No game input.

## Strict offline assist proposal — 2026-11-13 04:00 CST

**VERIFIED synthetic only:** `AssistAdvisor` wraps the inherited Paladin/Cleric
rotation without calling its preparation, autoattack or input path. It
requires an explicit character/class/level, currently verified target,
focused game with chat closed, health/mana and gem observations at most one
second old, and an observed available ability before proposing that ability.
It emits only a typed action with a cancellable ASSIST permit. The proposal
becomes invalid when mode is OFF, focus/target/observations change, or a
required ability disappears; cooldowns advance only after a confirmed send.
The rotation's hardcoded Bash/Smite/Lay Hands choices are now filtered by an
explicit observed ability set. 39 focused tests passed. **No live observer,
sender, in-game hotkey, character login or combat run was performed.**

## Client class levels and rotation eligibility — 2026-11-13 03:56 CST

**VERIFIED read-only client data:** Alienware `<game root>/dbstr_us.txt`
(SHA-256 `fd0508baa7151cc7575198860394967a40d72aeecc2db02a2c3024ea1ffbcefe`)
contains class IDs 1–16 in `class_id^45^name` rows. A copy is under the
untracked `~/.local/share/eql-automation/client-data/retail-full/` directory.
The paired `spells_us.txt` (SHA-256
`8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de`)
has 74,021 unique-ID, 174-field rows. Its fields 36–51 form the 16 class
level columns. **INFERRED from client IDs and corroborated by known Cleric and
Paladin rows:** field index `35 + class ID` is that class's level. `Strike`
and `Minor Healing` have Cleric/Paladin level 1; `Yaulp` has Cleric level 1
and Paladin level 9. The new index parses 1,450 rows with at least one class
level 1–50, stores only derived metadata outside git, and exposes class/level
queries. These rows include skills/discipline-like entries and **do not prove
server availability, vendor stock or scribing**.

**VERIFIED bug fix:** The copied October rotation planner previously filtered
spells by the lower of Cleric and Paladin levels. It could therefore offer
`Yaulp` to a level-1 Paladin. Profiles now require an explicit character
class and check its own level. Real copied client data produced no
class-invalid profiles at levels 1–50 for Cleric or Paladin; Paladin Yaulp is
absent at level 1 and present at level 9. This validates client catalog
eligibility only. It does not verify any live rotation or character spellbook.
The full 224-map retail text import was rerun into atomic snapshot
`e36ee7fd32a5c4b42f45` so its profile-validity flag reflects the corrected
class-specific check. The geometry totals remain 1,057,974 lines and 1,445
labels. 37 focused tests passed.

## Offline mode control — 2026-11-13 03:50 CST

**VERIFIED synthetic only:** A running CLI now accepts `mode full|assist|off`
and simulated `key F7|F8|F9` events, reports mode/generation/reason on screen,
and cancels queued intents when the mode changes. Already drained intents keep
their original permit so a sender can reject them after a switch. `safety
REASON` latches OFF until explicit reset. ASSIST denies movement, target,
autoattack, loot, vendor, camp, zone, login, recovery, scribe and memorize
intents. A focused CLI smoke queued MOVE in FULL, switched to ASSIST and
dropped it, then queued HEAL in ASSIST, switched OFF and dropped it. 31 focused
tests passed. **No keyboard grab, game overlay, input sender or live client
test exists.** The October tool already uses F8 and F9 and its prepare/combat
path changes spell gems and autoattack, so it cannot be reused unchanged for
strict ASSIST. The target remains unverified private; no character progress.

## Offline navigation controller — 2026-11-13 03:21 CST

**VERIFIED synthetic only:** A `WorldNavigator` now requires an observed start
position, explicit allowlists of traversed movement edges and zone lines, and
observed waypoint/zone arrivals. A stall at the confirmed source quarantines
both directions of that edge and replans; a mid-edge stall, unknown start,
unexpected zone, failed zone transition, missing verified route or exhausted
retry budget pauses. It emits intents only and has no game input transport.
The retail map drawing lines and POI candidates remain outside the verified
edge allowlists. A CLI synthetic demo replanned from `short` to `alternate`
and arrived; 29 focused tests passed. No real-client path was traversed.

## Zone-line review candidates — 2026-11-13 02:53 CST

**VERIFIED offline:** Cross-referencing the 1,445 map labels with the client's
701 zone names produced 351 unverified transition review candidates:
224 `to_` labels exactly match a client zone display name, 4 match after
reordering the same words, 48 unprefixed labels exactly match, and 75 `to_`
labels do not match a zone display name. For example, `to_East_Cabilis`
matches client zone ID 106, `Cabilis East`, by word order only. This is a
name association, **not** a working zone line or a destination map-stem
mapping. No transition was inserted into the navigable `WorldNav` graph.

A targeted read-only search of the Devbox Coordinator workspace and prior
rotation project found no separate private endpoint or login configuration.
The intended private server remains unidentified. 23 focused tests passed;
no client/server or character action occurred.

## Searchable map labels — 2026-11-13 02:25 CST

**VERIFIED offline:** The active 224-map snapshot has 1,445 labels. An untracked
POI index at
`~/.local/share/eql-automation/map-store/indices/e0aa3e31762d31fd4c1e.json.gz`
preserves each label, map name, coordinates, size and RGB. Text-only hints are
303 `to_` zone-exit candidates, 60 portal candidates, 109 merchant labels,
84 spell labels, 3 combined merchant/spell labels and 886 other landmarks.
The CLI can search labels by text/map and find nearby labels. No color is used
to infer type: blue labels also mark unrelated places, and labels may repeat.
**No label is verified as an actual zone transition, vendor inventory or safe
route.** 21 focused tests passed. The private server endpoint remains unknown.

## Full retail text-map snapshot — 2026-11-13 02:01 CST

**VERIFIED read-only transfer:** The Alienware's top-level `maps/` contains
224 `.txt` files totaling 78,918,163 bytes. The paired `.txt:crc` sidecars
were excluded. A rate-limited `rsync` also copied text maps in three nested
`Solo_Leveling`/backup directories (923 text files, 306,720,534 bytes total),
but the importer deliberately selected **only the 224 top-level client maps**;
no nested custom/backup map was imported. No remote file was modified.

**VERIFIED local import:** snapshot
`~/.local/share/eql-automation/map-store/snapshots/e0aa3e31762d31fd4c1e/`
holds 224 compressed geometry files (about 13 MB total), 1,057,974 drawing
lines, 1,445 labels, 0 unrecognized records, 701 zone names and 198
Paladin/Cleric spell records. All 50 prior rotation profiles passed validation.
`map-store/current.json` points to this snapshot. Import uses a temporary
directory and atomically promotes a complete snapshot, so a failed parse
cannot replace the active one. **Navigability remains unverified:** map lines
are rendered geometry, and labels only indicate candidate places. No client
map line has been treated as a traversable route.

**VERIFIED code checks:** 19 focused tests passed, including duplicate/nonfinite
point rejection and snapshot promotion after a source change. No private server
endpoint has been found; no character or service was contacted.

## Private-target clarification and retail data check — 2026-11-13 01:39 CST

**USER-STATED:** The intended automation target is a private EverQuest Legends
server, location unknown; use the retail client for now. **VERIFIED:** The sole
EverQuest Legends Lutris client found in likely Alienware locations still has
`eqhost.txt` pointing to Daybreak's official
`lvseqns-livl01.everquestlegends.com:15900`. No separate private client/login
configuration was found in bounded Alienware Lutris, Games, Projects or Desktop
checks. Bounded devbox `~/dev`, `~/gbsw`, Docker and listener checks found no
private EQ/EQEmu candidate. `banshee-ax41` was offline; the reachable Tailscale
peer `Banshee` had no candidate in its likely project paths, Docker containers,
services or common EQ listeners. These are bounded negative searches, not proof
that no private server exists elsewhere. **Exact missing piece:** the private
server endpoint or a separate client/login configuration that points to it.
No official service was contacted and no character was used.

**VERIFIED retail read-only copy:** From the Alienware client, two map text
files, `Resources/ZoneNames.txt`, `spells_us.txt`, and `eqhost.txt` were copied
to `/home/blizz/.local/share/eql-automation/client-data/retail-sample/`.
Their SHA-256 hashes match the source values already recorded below; the
`eqhost.txt` copy hashes to
`e8682ae8189d2082de41e87ce6fe82a9e055e6fe16c12ffa1a09bb84127395d8`.
No remote install/prefix file was modified. Import results in the untracked
`~/.local/share/eql-automation/map-store/`:

- `fieldofbone.txt`: 5,238 drawing lines, 11 labels, 0 skipped records.
- `freeportwest.txt`: 16,992 drawing lines, 8 labels, 0 skipped records.
- Zone-name list: 701 entries.
- October Paladin/Cleric parser: 198 spells, all level 1–50 profiles valid.
- **Navigability is unverified:** map `L` records are drawing geometry, not
  proven walkable edges; `P` labels are candidate places, not confirmed zone
  transitions/vendors. No nav graph is generated automatically from them.
- A read-only target inspector classifies this copied `eqhost.txt` as official
  and rejects it as a private target. Future input must match a separately
  reviewed private host, port and `eqhost.txt` hash.

## First-step result — 2026-11-13 00:38 CST (current)

**VERIFIED:** The owner's installed EverQuest Legends client is on the Alienware
(`alienware-bazzite`, host `bazzite`) and points to Daybreak's official, live,
commercial service. It is not an EQEmu/private-server setup. No client was
launched, no character was logged in, and no existing character log was read.
The older material below is retained as handover history; its statements that
the client/server were not found are superseded by this section.

### Alienware install and service evidence

Read-only checks over the `alienware-bazzite` SSH alias found:

| Item | Alienware path or value | SHA-256 |
| --- | --- | --- |
| Lutris configuration | `/home/blizz/.local/share/lutris/games/everquest-legends-1782570403.yml` | `d7a430f39a38b1d088e56ada053b0c454a08a5cb1490418cca4a66b1a6dfb481` |
| Desktop shortcut | `/home/blizz/Games/everquest-legends/drive_c/users/blizz/Desktop/EverQuest Legends.lnk` | `b6c054bcf8043f57e2a60635e7931bf59c3929a97d6e3d4327480b05c50c7259` |
| Login host | `<game root>/eqhost.txt` | `e8682ae8189d2082de41e87ce6fe82a9e055e6fe16c12ffa1a09bb84127395d8` |
| Login client configuration | `<game root>/eqlsClient.ini` | `83c1bd98a27cdc4355d479e59070e6ef9de862388279571d50afee64a2482446` |
| LaunchPad configuration | `<game root>/LaunchPad.ini` | `e727a7e04a0f1f86247461f1490c11a5abb68ca5019dc5ed2252fbc01eda6743` |
| Zone names | `<game root>/Resources/ZoneNames.txt` | `840b61b01deb4dfb8f49cf13e007364a629ce380c165aad5bb37adba6e52cd39` |
| Spell catalog | `<game root>/spells_us.txt` | `8db5548696635075f982a20a8afae13b57346637f5edae3c8d93432c848524de` |
| Spell strings | `<game root>/spells_us_str.txt` | `9ce629ec15a7625ff1156256e71a3c954a1cb2fa9bf701692a7529e9b3bf3dab` |
| Example map | `<game root>/maps/fieldofbone.txt` | `5e475aa926ab0eb176e04ebaa9f5264cacc02848e294f7b2ad402f6d5aaf1d85` |
| Example map | `<game root>/maps/freeportwest.txt` | `4e1fdfc54a99f5a9b5cb8903fb08430ea9752b2645ad58809f7c4299b80e0706` |

`<game root>` is
`/home/blizz/Games/everquest-legends/drive_c/users/Public/Daybreak Game Company/Installed Games/EverQuest Legends`.
The Lutris prefix is `/home/blizz/Games/everquest-legends` (about 13 GB).
The shortcut targets `C:\\users\\Public\\Daybreak Game Company\\Installed Games\\EverQuest Legends\\LaunchPad.exe`.
`eqhost.txt` says `[LoginServer] Host=lvseqns-livl01.everquestlegends.com:15900`;
that name resolved to `69.174.201.2` at the check. `eqlsClient.ini` refers to
`https://account.daybreakgames.com` and `http://www.everquestlegends.com`.
There are 448 `maps/` files and 701 zone-name lines. The map example uses
`L x,y,z,x,y,z,R,G,B` records. These observations establish the installed
client's configuration, not a witnessed connection: the client was not run.

**VERIFIED policy conflict:** [Daybreak's EverQuest Legends Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct)
prohibit unauthorized servers/emulators in rules 13–14, and their play-nice
policy prohibits AFK/unattended gameplay. [Daybreak EULA §4.6](https://www.daybreakgames.com/eula?locale=en_US)
bars bots or macros that allow unattended play or otherwise affect gameplay;
[Daybreak Terms of Service §10](https://www.daybreakgames.com/terms-of-service?locale=en_us)
also forbids unauthorized software or macros that modify gameplay or give an
advantage. **INFERRED:** The requested full-auto level 50 run and rotation-only
assist on this live service fall within these prohibitions absent Daybreak's
express written authorization. A private/EQEmu EQL server is also not a clear
fallback under rules 13–14. This conflict was reported to the coordinator for
task `829a00229b29`. Live automation and private-server testing are held;
offline simulation and read-only analysis can continue.

### Earlier October rotation tool

**VERIFIED read-only review:** `/home/blizz/Projects/everquest-legends-rotation/`
is a Paladin/Cleric assist prototype. `rotation_core.py` parses the client's
spell catalog, filters a fresh `/outputfile spellbook` export, chooses 1–50
spell profiles, tails logs, and chooses healing, buff, ability and damage
actions. `rotation_engine.py` gates XWayland/uinput commands on game focus and
uses F6 to prepare, F8 to toggle combat, F9 to stop and F10 to heal.
`eql_rotation.py` supplies a PySide6 GUI. The tool has no pathing, camps,
vendor, looting, death recovery or unattended login. Its `server="freeport"`
setting names a log file and is not evidence of a private server.

| Prior file | SHA-256 |
| --- | --- |
| `HANDOFF.md` | `af18a1d72b5414564a76803fce73b13dc8c70efe2bf560cfe26815bc17bfd5fa` |
| `README.md` | `9fd2f3c8741e16ddf9087f146d62a7789417316ab57fe9afafc0b89b276135aa` |
| `CODEX_PROMPT.txt` | `26e274960b2483f71211822dfba1a5eb67901ac542604f8c4ecaee32e0f0f244` |
| `remote-runtime-check.json` | `347b4b481aa3451c105a9b5417346c87f0751463bab7fa8c0b3dcf7752206249` |
| `eql_rotation.py` | `95b4251558ecd1a5c31d9e12f2d71c2a0492de1e3df52592745fa7e8fc517adc` |
| `rotation_core.py` | `bdd5203bbf87563039799f7dd228480a517fca8dd4550d53b6559506a56875fa` |
| `rotation_engine.py` | `8e32a72eb7f87dae9901f84841679fdb628c46fab7458de216bfdff9fe567683` |
| `test_rotation.py` | `cfb79d8e661ad67d55623ba6888a604708197289b2a8e723a7debeffded72c99` |

The devbox mirror has no `artifacts/` evidence. `HANDOFF.md` reports 17 tests
passed on Alienware historically, but live spell preparation and combat were
never verified; the tests were not rerun in this first-step review.
`install_launchers.py` writes character INIs and must not be run against the
protected Alienware prefix. Missing pieces for the level 50 proof are a
Daybreak-authorized test path, a fresh test character, and an end-to-end run.
Devbox/Banshee server searches were skipped because the installed client points
to an official service and unauthorized EQL servers are prohibited.

## Superseded handover notes

Written 2026-11-13 ~12:40 AM CST by the Claude lead (claude-everquest-legends, Fable 5.2) at handover
to the Codex lead (coordinator task 28e5398a1701). The Claude lead ran for only a few minutes; the
FIRST STEP search is **incomplete**. Labels: VERIFIED = ran it and saw it, INFERRED = guess from evidence.

## Bottom line

- **Client install: NOT FOUND on the devbox so far** (partial search only, see "Not searched").
- **Server: NOT FOUND on the devbox so far.** No EverQuest-compatible server stack seen in running
  docker containers or in top-level `~/dev` directory names.
- **One real lead, unread:** `~/Projects/everquest-legends-rotation/` (an earlier EverQuest Legends
  rotation tool, Oct 17 2026). Its `HANDOFF.md` / `README.md` very likely say where the client runs
  and what it connects to. **Read this first.**
- No hashes recorded: no client or server binary was located to hash.
- Nothing was built, launched, logged in or changed. No game service was contacted.

## What was run and seen (all VERIFIED unless marked)

1. `~/Projects/everquest-legends-rotation/` exists, 332K, files dated Oct 17 2026, no `.git` dir:
   `CODEX_PROMPT.txt`, `HANDOFF.md` (8413 B), `README.md` (4086 B), `eql_rotation.py` (26700 B),
   `rotation_core.py`, `rotation_engine.py`, `test_rotation.py`, `install_launchers.py`, `launch.sh`,
   `eql-solo-assist.desktop`, `remote-runtime-check.json`, `.gitignore`.
   **Contents were not read** (stopped by handover before opening them).
   INFERRED from file names only: `remote-runtime-check.json` and the `.desktop` launcher suggest
   the game client may run on another machine (e.g. the Alienware) rather than this devbox.
2. Name search with `find -maxdepth 7` over `~/Games ~/Steam ~/.local/share/Steam ~/.wine
   ~/Applications ~/.local/share/lutris ~/.var ~/.local/share` for
   `*everquest*  eqgame*  eqlog*  eqhost*  eqclient.ini  spells_us*  *legends*  *daybreak*  LaunchPad*`
   returned exactly one hit: `~/.local/share/devbox-failover/claude-everquest-legends.json`
   (devbox failover metadata for this lane, not game data; not opened).
   Caveats: ran under `timeout 90` with errors hidden, and I did not capture the exit code, so I
   cannot rule out that it was cut off; depth was limited to 7.
3. Steam: no output from `~/.local/share/Steam/steamapps/libraryfolders.vdf`, and no `*.acf` app
   manifests in `~/.local/share/Steam/steamapps/` or `~/Steam/steamapps/` (no installed Steam apps seen).
4. `~/Games/` holds `banshee-library/` (empty) and `dreadnought-server/`. `~/Applications/` holds only
   `BansheeRealm.AppImage` (+ one `.before-0.9.176` backup). `~/Projects/` holds
   `everquest-legends-rotation/` and `xenogears-decomp/`.
5. `~/dev/*` top-level names matching `eq|everquest|quarm|legend|akka|norrath`: only this project
   (`everquest-legends-automation`). No EQEmu / Project Quarm / Akka-named directory at that level.
6. `~/gbsw/` contains only small Python scripts (`chk.py cst.py last.py lm.py send.py st.py sw*.py
   swc0745.py dummy.txt`), no server stack.
7. `docker ps` showed 4 containers, none EverQuest-related: `vana-navw2-28313`, `vanilla-smoke-db-1`,
   `enb-rust-mvas-20261103-server`, `enb-rust-mvas-20261103-db`.
8. Disks: `/` 489G (23G used), `/data` 30T (9.6T used). `locate` is not installed (exit 127), so
   there is no file index to query.
9. Box at the time: 48 CPUs, 187 GiB RAM, ~98 GiB available.

## Not searched / not done (still open)

- `/data` (30T volume) — not searched at all. Most likely place for a large client install if one
  is on this box.
- `~/dev` below the top level, and `~/.wine` / other Wine or Proton prefixes beyond a depth-7 name match.
- Stopped docker containers (`docker ps -a`), systemd services, listening ports.
- Banshee (`banshee-ax41`) — not contacted.
- The Alienware — not contacted.
- Whether "EverQuest Legends" is a live commercial/public service — **unknown**. If it is, the
  no-botting / ToS question in AGENTS.md CONSTRAINTS must be answered and reported to the coordinator
  before any automation touches it.
- The FIRST STEP report to the coordinator was not sent as a findings report; only this handover
  note was sent.

## What I was about to do next

1. Read `~/Projects/everquest-legends-rotation/HANDOFF.md`, `README.md`, `CODEX_PROMPT.txt` and
   `remote-runtime-check.json` to learn where the client lives, how the earlier tool read game state
   and sent input, and which service it logs into.
2. Search `/data` and deeper `~/dev` for `eqgame.exe`, `eqclient.ini`, `spells_us.txt`, `eqhost.txt`,
   `Logs/eqlog_*`, `maps/*.txt`, `*.s3d`, `*.eqg`; hash whatever is found (sha256) and record paths here.
3. Check `docker ps -a`, listening ports and Banshee for an EverQuest-compatible server.
4. Send the coordinator one clear note naming the exact missing piece (client and/or server) and the
   live-service/ToS answer.
5. In parallel, start the parts that need no client: nav-graph tooling for EQ map files, spell/class
   data model from `spells_us.txt`, log-tail state reader, and a bot core with a simulated harness.

## Coordinator channel note

The coordinator did not appear in `ListAgents` (8 peer sessions listed, none of them the coordinator),
though tmux session `claude-devbox-coordinator` exists. The CLI
`python3 ~/.local/share/devbox-coordinator/coordinator.py report --task <id> --status <s> --summary "..."`
is present and accepts `report`.

## Addendum 2026-11-13 12:40 AM CST (coordinator, from Blizz 12:33 AM CST and a read-only check on the Alienware)

- Blizz: "i have a game and client onmy laptop alienware if it neesd it under lutris". Stop searching the devbox.
- **Client install: Alienware (Bazzite, Tailscale 100.111.220.11)**, Lutris config
  `/home/blizz/.local/share/lutris/games/everquest-legends-1782570403.yml`; Wine prefix and game dir
  `/home/blizz/Games/everquest-legends` (13G); launched via umu-run; exe `drive_c/users/blizz/Desktop/EverQuest Legends.lnk`;
  prelaunch script `fix-eq-music.sh`. (VERIFIED read-only by the coordinator.)
- Read-only for you: do not modify or delete the install or prefix; copy anything to analyse to the devbox; do not touch his character progress.
- Server: **still to find and record** (official vs private/EQEmu).
- Earlier devbox tool to read first: `~/Projects/everquest-legends-rotation/` (Oct 17 2026).
