# FINDINGS

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
