# STATUS

Updated 2026-11-13 ~12:40 AM CST. Lane handed from the Claude lead to the Codex lead
(coordinator task 28e5398a1701, Blizz 12:31 AM CST Nov 13).

- Level: n/a. No character, no client run, nothing launched.
- XP / XP per hour: n/a. Deaths: 0. Camp: none.
- Code: none written yet. Repo holds only AGENTS.md, FINDINGS.md, STATUS.md.
- Current blocker: the EverQuest Legends client and server have **not been located** (search was
  only partly done; see FINDINGS.md "Not searched").

## Exact next steps for the Codex lead

1. Read `~/Projects/everquest-legends-rotation/HANDOFF.md`, `README.md`, `CODEX_PROMPT.txt`,
   `remote-runtime-check.json` (unread; best lead on where the client runs and what it connects to).
2. Finish the FIRST STEP search: `/data`, deeper `~/dev`, Wine/Proton prefixes, `docker ps -a`,
   listening ports, Banshee (`banshee-ax41`), then the Alienware (light, read-only). Record paths
   and sha256 hashes in FINDINGS.md.
3. Decide and state plainly whether the target is a live commercial/public service; if a ToS or
   no-botting rule conflicts with the goal, send the coordinator one clear note.
4. Send the FIRST STEP findings report to the coordinator (not yet sent).
5. Start client-independent work: map-file to nav-graph tooling (store under
   `~/.local/share/eql-automation/`), spell/class data model, log-tail state reader, bot core with
   a simulated test harness.
