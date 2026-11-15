# EverQuest Legends Carbon — Codex Astra handoff

Written 2026-11-15 8:28 AM CST by Devbox. Blizz ordered the Carbon lanes switched to Codex.

## Role
You are the EverQuest Legends automation lead on Codex GPT-6-Astra ultra Fast. Session: `codex-everquest-legends-astra`. Worktree: `/home/blizz/dev/everquest-legends-automation-carbon`. Branch: `carbon/continue`. Starting point: the last commit on this branch at handoff (GFay source assets and crossing wiring, committed as part of this switch if they were still uncommitted).

Do not work in `/home/blizz/dev/everquest-legends-automation`; that tree still has the paused Codex lead's uncommitted work. Leave the paused session `codex-everquest-legends` stopped; do not resume it. Leave the idle Flash session `gemini-everquest-legends` alone.

## Goal and brief (original Carbon order, still in force)
Continue toward the standing 1-50 automation plus assist/rotation-only goal. Continue from the latest handoff and progress docs in this checkout (`FINDINGS.md`, `STATUS.md`, `HOWTO.md`, and this file).

## Progress
Last previously committed work: `9993e33` — Stage Butcherblock-to-GFay crossing assets and wire OwnerSourceCrossingRuntime (0.42.90). At switch time the Carbon lead had uncommitted Greater Faydark source/crossing assets, tests, and audit/prepare tools, plus wiring in `owner_*` and `source_*` modules; that work is committed on `carbon/continue` with this handoff if it was still dirty. The Carbon lead then hit Gemini quota during focused crossing tests. Inspect `git log` and `git status` before acting, then keep going on GFay / 1-50 work.

## Rules
Commit small and often on `carbon/continue` only. No push. Do not touch Blizz's EverQuest Legends characters, Lutris config, or the Wine prefix at `~/Games/everquest-legends`. Do not modify or delete that install. You may read a copy of game data if needed, but never write into the prefix. No credential or access changes. No server restarts. Do not run `rea setup`. Do not edit `~/.codex/config.toml` or `~/.claude.json`. Daybreak is off for this launch. Inspect current work before acting, then keep going.
