#!/usr/bin/env python3
"""Analyze saved motion receipts and stopped positions; never send game input."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eql_automation.motion_calibration import (PROBES, Position, StoppedPair, reduce_experiment)
from eql_automation.uinput_watchdog import PulseReceipt

NAVIGATION_SHA256 = "69dbc6472447942cc30dbe592a6e1cf02998c0a0b8811a8bb59672655dc4049e"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe-experiment", action="store_true",
                        help="Print the offline proposal and record schema; this is not a run command")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-sha256")
    parser.add_argument("--navigation", type=Path,
        default=Path.home()/".local/share/eql-automation/owner-assist/0.39.10/navigation.py")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.describe_experiment:
        print(json.dumps(dict(format="eql-motion-experiment-v1", input_authorized=False,
            proposal=[asdict(probe) for probe in PROBES],
            record_fields=["format", "record_id", "horizontal_error", "pairs", "receipts"],
            pair_fields={"first":list(Position.__dataclass_fields__), "second":list(Position.__dataclass_fields__)},
            receipt_fields=list(PulseReceipt.__dataclass_fields__),
            required="Eight stopped pairs and seven complete DOWN/UP receipts; no legacy elapsed substitutions",
            unresolved="Initial travel envelope, current scene, input timing and full-turn ambiguity"), indent=2))
        return
    if not args.input or not args.output or not args.input_sha256:
        parser.error("Need --input, --input-sha256 and a new --output")
    store = (Path.home()/".local/share/eql-automation").resolve()
    protected = (Path.home()/"Games/everquest-legends").resolve()
    if any(not p.resolve().is_relative_to(store) or p.resolve().is_relative_to(protected)
           for p in (args.input, args.navigation, args.output)):
        parser.error("Use copied inputs and a new output under the private eql-automation store")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output already exists")
    try:
        if args.input.stat().st_size > 128*1024 or args.navigation.stat().st_size > 512*1024:
            raise ValueError("Input exceeds analysis size limit")
        raw, source = args.input.read_bytes(), args.navigation.read_bytes()
        if sha256(raw).hexdigest() != args.input_sha256:
            raise ValueError("Experiment hash changed")
        if sha256(source).hexdigest() != NAVIGATION_SHA256:
            raise ValueError("Retained navigation source changed")
        record = json.loads(raw)
        if record["format"] != "eql-motion-experiment-v1":
            raise ValueError("Unknown experiment format")
        module = ModuleType("eql_retained_motion_navigation")
        module.__file__ = str(args.navigation)
        sys.modules[module.__name__] = module
        # Execute the bytes just verified, avoiding a second source read.
        exec(compile(source, str(args.navigation), "exec"), module.__dict__)
        pairs = [StoppedPair(Position(**p["first"]), Position(**p["second"])) for p in record["pairs"]]
        receipts = [PulseReceipt(**r) for r in record["receipts"]]
        result = reduce_experiment(pairs, receipts, legacy=module,
            horizontal_error=record["horizontal_error"], record_id=record["record_id"])
        result.update(input_sha256=args.input_sha256, navigation_sha256=NAVIGATION_SHA256)
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with args.output.open("x") as output:
            json.dump(result, output, indent=2, allow_nan=False)
            output.write("\n")
        args.output.chmod(0o600)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(dict(output=str(args.output), estimate=result["estimate"],
                          input_authorized=False, real_client_accepted=False)))


if __name__ == "__main__":
    main()
