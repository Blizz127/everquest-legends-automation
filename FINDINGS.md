# FINDINGS

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
