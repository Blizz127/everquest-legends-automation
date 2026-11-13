"""Offline CLI. It has no live game input or network backend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .modes import Action, ActionKind, Mode, ModeController
from .sim import SimSink, run_demo, synthetic_graph
from .synthetic_run import default_output_dir, run_synthetic_1_50


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
    parser.add_argument("--output", type=Path,
                        help="synthetic trace directory; defaults under ~/.local/share/eql-automation/runs")
    args = parser.parse_args()
    if args.demo:
        print(json.dumps(run_demo(), indent=2))
    elif args.synthetic_1_50:
        print(json.dumps(run_synthetic_1_50(args.output or default_output_dir()), indent=2))
    else:
        shell()


if __name__ == "__main__":
    main()
