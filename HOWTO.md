# EverQuest Legends automation — current build 0.3.0

## Current availability

This build is an **offline simulator and planning library**. It does not launch
EverQuest Legends, log in, control a character, or send game input. The owner's
installed client points to Daybreak's live service. Its published
[Rules of Conduct](https://help.daybreakgames.com/hc/en-us/articles/53818164365843-What-are-the-EverQuest-Legends-Rules-of-Conduct),
[EULA](https://www.daybreakgames.com/eula?locale=en_US), and
[Terms of Service](https://www.daybreakgames.com/terms-of-service?locale=en_us)
prohibit the requested unattended bot and appear to prohibit a rotation assist
on the live service without Daybreak authorization. No live mode is enabled.

## Start the offline prototype

From this project directory:

```bash
python3 -m eql_automation --demo
python3 -m eql_automation --shell
```

The demo prints a synthetic route and mode-permission results. The shell stays
running while you switch simulated modes:

```text
mode assist
action cast
action move
mode full
route
mode off
status
quit
```

`mode assist`, `mode full`, and `mode off` take effect in the running simulator
without a restart. Each switch prints `MODE ...` on screen. `mode off` cancels
the previous action permit immediately; `quit` stops the shell. These are
terminal commands, not in-game commands or hotkeys.

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

The prior October Paladin/Cleric prototype remains at
`/home/blizz/Projects/everquest-legends-rotation/`. Its historical controls
were F6 prepare, F8 assist toggle, F9 stop, and F10 heal. They have not been
live-verified and are **not** controls for this build. Do not run its installer:
it writes character INIs in the protected Alienware prefix.

## Verification

```bash
python3 -m pytest -q tests/test_offline.py
python3 -m compileall -q eql_automation
```

The level 50 run, real-client map ingestion, in-game mode switching, automated
spell acquisition, camps, death recovery, and relogin are not implemented or
verified. `FINDINGS.md` records the exact client/server evidence and blocker.
