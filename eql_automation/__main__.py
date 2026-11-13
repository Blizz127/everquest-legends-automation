"""Offline CLI. It has no live game input or network backend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from dataclasses import asdict

from .control import ControlPlane
from .modes import Action, ActionKind
from .sim import (SimSink, run_assist_demo, run_demo, run_gauge_demo,
                  run_navigation_demo, synthetic_graph)
from .synthetic_run import default_output_dir, run_synthetic_1_50
from .client_ingest import import_retail_copy
from .target import inspect_eqhost
from .poi_index import build_poi_index, current_summary
from .nav import MAP_STORE
from .zone_candidates import build_zone_candidates
from .spell_catalog import build_spell_level_index
from .ui_schema import index_ui_widgets


def shell() -> None:
    control = ControlPlane()
    sink = SimSink(control.controller)
    print("OFFLINE SIMULATOR — no game input. Commands: mode off|assist|full, "
          "key F7|F8|F9, action KIND, queue KIND, drain, stop, safety REASON, "
          "reset safety, route, status, quit")
    print(control.indicator.text)
    while True:
        try:
            raw = input("eql-sim> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return
        normalized = raw.lower()
        if normalized in {"quit", "exit"}:
            return
        if normalized.startswith("mode ") or normalized in {"stop", "reset safety"}:
            try:
                print(control.handle_command(raw).text)
            except (RuntimeError, ValueError) as exc:
                print(exc)
        elif normalized.startswith("key "):
            try:
                print(control.handle_hotkey(raw.split(maxsplit=1)[1]).text)
            except (RuntimeError, ValueError) as exc:
                print(exc)
        elif normalized.startswith("safety "):
            try:
                print(control.emergency_stop(raw.split(maxsplit=1)[1]).text)
            except ValueError as exc:
                print(exc)
        elif normalized.startswith("action ") or normalized.startswith("queue "):
            try:
                kind = ActionKind(normalized.split(maxsplit=1)[1])
                action = Action(kind, "synthetic")
                if normalized.startswith("queue "):
                    print("QUEUED (simulation only)" if control.queue(action) else "DENIED")
                else:
                    print("ALLOWED (simulation only)" if sink.submit(action) else "DENIED")
            except ValueError:
                print("Unknown action kind")
        elif normalized == "drain":
            result = control.drain()
            sent = sum(sink.submit(item.action, item.permit) for item in result.ready)
            print(f"DRAINED {sent} simulated actions; {result.dropped + len(result.ready) - sent} dropped")
        elif normalized == "route":
            print(" -> ".join(synthetic_graph().route("start", "camp")))
        elif normalized == "status":
            print(f"{control.indicator.text} — {len(sink.accepted)} accepted, "
                  f"{len(sink.rejected)} denied")
        elif raw:
            print("Unknown command")


def main() -> None:
    parser = argparse.ArgumentParser(description="EverQuest Legends offline planning prototype")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="run one synthetic scenario")
    group.add_argument("--demo-navigation", action="store_true",
                       help="show offline stuck detection and replanning")
    group.add_argument("--demo-assist", action="store_true",
                       help="show an offline strict current-target rotation proposal")
    group.add_argument("--demo-gauges", action="store_true",
                       help="read fabricated player HP/mana bars; no game capture")
    group.add_argument("--shell", action="store_true", help="switch simulated modes without restarting")
    group.add_argument("--synthetic-1-50", action="store_true",
                       help="run a closed-loop synthetic level 1–50 scenario; not real-client proof")
    group.add_argument("--ingest-retail-copy", action="store_true",
                       help="read copied client text files into the untracked local map store")
    group.add_argument("--inspect-target", action="store_true",
                       help="inspect a copied eqhost.txt without connecting to its server")
    group.add_argument("--index-pois", action="store_true",
                       help="index unverified labels from the active map snapshot")
    group.add_argument("--query-pois", metavar="TEXT",
                       help="search unverified labels in the active map snapshot")
    group.add_argument("--index-zone-candidates", action="store_true",
                       help="cross-reference map labels with client zone names as unverified candidates")
    group.add_argument("--query-zone-candidates", metavar="TEXT",
                       help="search unverified zone-line candidates")
    group.add_argument("--index-spell-levels", action="store_true",
                       help="index client class levels for spells and skills; no server availability claim")
    group.add_argument("--query-spell-levels", metavar="TEXT",
                       help="search client spell/skill level candidates")
    group.add_argument("--index-ui-widgets", action="store_true",
                       help="index static client UI widget names; no live values")
    group.add_argument("--query-ui-widgets", metavar="TEXT",
                       help="search static default UI widget names")
    parser.add_argument("--output", type=Path,
                        help="synthetic trace directory; defaults under ~/.local/share/eql-automation/runs")
    parser.add_argument("--source", type=Path,
                        help="copied retail client text directory for --ingest-retail-copy")
    parser.add_argument("--map", dest="map_name", help="filter POI query by map file stem")
    parser.add_argument("--limit", type=int, default=20, help="maximum POI query results")
    parser.add_argument("--class-name", help="filter client spell candidates by class name")
    parser.add_argument("--level", type=int, help="filter client spell candidates unlocked by this level")
    args = parser.parse_args()
    if args.demo:
        print(json.dumps(run_demo(), indent=2))
    elif args.demo_navigation:
        print(json.dumps(run_navigation_demo(), indent=2))
    elif args.demo_assist:
        print(json.dumps(run_assist_demo(), indent=2))
    elif args.demo_gauges:
        print(json.dumps(run_gauge_demo(), indent=2))
    elif args.synthetic_1_50:
        print(json.dumps(run_synthetic_1_50(args.output or default_output_dir()), indent=2))
    elif args.ingest_retail_copy:
        if args.source is None:
            parser.error("--ingest-retail-copy requires --source")
        print(json.dumps(import_retail_copy(args.source, args.output) if args.output
                         else import_retail_copy(args.source), indent=2))
    elif args.inspect_target:
        if args.source is None:
            parser.error("--inspect-target requires --source pointing to eqhost.txt")
        print(json.dumps(asdict(inspect_eqhost(args.source)), indent=2))
    elif args.index_pois or args.query_pois is not None:
        store = args.output or MAP_STORE
        summary = args.source or current_summary(store)
        index, path = build_poi_index(summary, store)
        if args.index_pois:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "label_count": len(index.pois),
                              "hint_counts": index.counts(),
                              "index_path": str(path),
                              "all_labels_verified": False}, indent=2))
        else:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "query": args.query_pois,
                              "results": [asdict(poi) for poi in index.search(
                                  args.query_pois, map_name=args.map_name,
                                  limit=args.limit)]}, indent=2))
    elif args.index_zone_candidates or args.query_zone_candidates is not None:
        store = args.output or MAP_STORE
        summary = args.source or current_summary(store)
        index, path = build_zone_candidates(summary, store)
        if args.index_zone_candidates:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "candidate_count": len(index.candidates),
                              "match_counts": index.counts(),
                              "index_path": str(path),
                              "transitions_verified": False}, indent=2))
        else:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "query": args.query_zone_candidates,
                              "results": [asdict(item) for item in index.search(
                                  args.query_zone_candidates,
                                  source_map=args.map_name,
                                  limit=args.limit)]}, indent=2))
    elif args.index_spell_levels or args.query_spell_levels is not None:
        store = args.output or MAP_STORE
        source = args.source
        if source is None:
            source = Path(json.loads(current_summary(store).read_text())["source_dir"])
        index, path = build_spell_level_index(source, store)
        if args.index_spell_levels:
            print(json.dumps({"spell_catalog_sha256": index.spell_sha256,
                              "class_names_sha256": index.class_name_sha256,
                              "client_level_candidate_count": len(index.spells),
                              "class_candidate_counts": index.counts(),
                              "index_path": str(path),
                              "server_availability_verified": False,
                              "vendor_stock_verified": False}, indent=2))
        else:
            print(json.dumps({"query": args.query_spell_levels,
                              "class": args.class_name,
                              "level": args.level,
                              "results": [asdict(item) for item in index.search(
                                  args.query_spell_levels,
                                  class_name=args.class_name,
                                  level=args.level,
                                  limit=args.limit)],
                              "server_availability_verified": False}, indent=2))
    elif args.index_ui_widgets or args.query_ui_widgets is not None:
        store = args.output or MAP_STORE
        source = args.source
        if source is None:
            source = Path(json.loads(current_summary(store).read_text())["source_dir"])
        schema, path = index_ui_widgets(source, store)
        if args.index_ui_widgets:
            print(json.dumps({"widget_count": len(schema.widgets),
                              "source_sha256": schema.source_sha256,
                              "index_path": str(path),
                              "active_skin_verified": False,
                              "runtime_values_verified": False,
                              "hotkeys_verified": False}, indent=2))
        else:
            print(json.dumps({"query": args.query_ui_widgets,
                              "results": [asdict(item) for item in schema.search(
                                  args.query_ui_widgets, args.limit)],
                              "runtime_values_verified": False}, indent=2))
    else:
        shell()


if __name__ == "__main__":
    main()
