"""Offline CLI. It has no live game input or network backend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from dataclasses import asdict

from .modes import Action, ActionKind, Mode, ModeController
from .sim import SimSink, run_demo, synthetic_graph
from .synthetic_run import default_output_dir, run_synthetic_1_50
from .client_ingest import import_retail_copy
from .target import inspect_eqhost
from .poi_index import build_poi_index, current_summary
from .nav import MAP_STORE


def shell() -> None:
    controller = ModeController()
    sink = SimSink(controller)
    print("OFFLINE SIMULATOR — mode off. Commands: mode off|assist|full, action KIND, route, status, quit")
    while True:
        try:
            raw = input("eql-sim> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return
        if raw in {"quit", "exit"}:
            return
        if raw.startswith("mode "):
            try:
                permit = controller.switch(Mode(raw.split(maxsplit=1)[1]))
                print(f"MODE {permit.mode.value.upper()} — generation {permit.generation}")
            except ValueError:
                print("Use mode off, mode assist, or mode full")
        elif raw.startswith("action "):
            try:
                kind = ActionKind(raw.split(maxsplit=1)[1])
                print("ALLOWED (simulation only)" if sink.submit(Action(kind, "synthetic")) else "DENIED")
            except ValueError:
                print("Unknown action kind")
        elif raw == "route":
            print(" -> ".join(synthetic_graph().route("start", "camp")))
        elif raw == "status":
            print(f"MODE {controller.mode.value.upper()} — {len(sink.accepted)} accepted, {len(sink.rejected)} denied")
        elif raw:
            print("Unknown command")


def main() -> None:
    parser = argparse.ArgumentParser(description="EverQuest Legends offline planning prototype")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="run one synthetic scenario")
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
    parser.add_argument("--output", type=Path,
                        help="synthetic trace directory; defaults under ~/.local/share/eql-automation/runs")
    parser.add_argument("--source", type=Path,
                        help="copied retail client text directory for --ingest-retail-copy")
    parser.add_argument("--map", dest="map_name", help="filter POI query by map file stem")
    parser.add_argument("--limit", type=int, default=20, help="maximum POI query results")
    args = parser.parse_args()
    if args.demo:
        print(json.dumps(run_demo(), indent=2))
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
    else:
        shell()


if __name__ == "__main__":
    main()
