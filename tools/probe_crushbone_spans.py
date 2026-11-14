#!/usr/bin/env python3
"""Run one pinned source-only Crushbone span diagnostic; never accept a route."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path.home() / ".local/share/eql-automation"
PROJECT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "toolchains/recastnavigation"
LIBRARY = ROOT / "toolchains/recast-build/Recast/libRecast.a"
EQTR = ROOT / "nav-candidates/crushbone-detail-distance-0.41.45/crushbone.eqtr"
REFERENCE = ROOT / "nav-candidates/crushbone-detail-distance-0.41.45/baseline.eqnm"
COMMIT = "9f4ce64458dfae86e1239c525ddc219c4e9e06f1"
PINS = {
    LIBRARY: "261a3e9ee6fb3b1fe52d00a095fa0f24ca48f6d3790ecb17066fe633bc07a43f",
    EQTR: "ad521d7df14c0d4a578923595316794cb06181672bb8f22b21f0925ec43e9da5",
    REFERENCE: "e798100211c36cbb86f54f8445d0dec1422b77242cfeab49f95999987f7380b0",
    UPSTREAM / "Recast/Source/RecastContour.cpp": "a9282897a5a5cb56cf8bbab97e0fd5edc3cd394ae8fe5266a28ce4199a4f3bfa",
    UPSTREAM / "Recast/Source/Recast.cpp": "865595763451cde0aad5b99088bfab48d4ea35050fefd67f3d4f95885ba38d66",
    UPSTREAM / "Recast/Source/RecastFilter.cpp": "0d133cdce1446babbf01bf47dc152c843e9cb2ee5dbb537c2e0ae566b6c95b9d",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def check_sources() -> None:
    for path, expected in PINS.items():
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"retained source pin mismatch: {path}")
    revision = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    if revision != COMMIT:
        raise ValueError("retained Recast revision changed")
    subprocess.run(["git", "-C", str(UPSTREAM), "diff", "--quiet", "HEAD", "--", "Recast"], check=True)


def run(output: Path) -> dict:
    check_sources()
    output.mkdir(mode=0o700)
    source = PROJECT / "tools/probe_crushbone_spans.cpp"
    saved_source = output / source.name
    saved_source.write_bytes(source.read_bytes())
    saved_wrapper = output / Path(__file__).name
    saved_wrapper.write_bytes(Path(__file__).read_bytes())
    binary = output / "span_probe"
    commands = [
        ["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-I" + str(UPSTREAM / "Recast/Include"), "-I" + str(UPSTREAM / "Recast/Source"),
         str(saved_source), str(LIBRARY), "-o", str(binary)],
        [str(binary), str(EQTR)],
    ]
    report = {"format": "eql-source-span-run-v1", "offline_only": True,
              "game_input_sent": False, "route_accepted": False,
              "exact_custom_baker_equivalence": False, "completed": False,
              "pins": {str(p): h for p, h in PINS.items()},
              "upstream_commit": COMMIT, "source_sha256": digest(saved_source),
              "wrapper_sha256": digest(saved_wrapper), "commands": commands,
              "steps": []}
    report_path = output / "report.json"

    def save():
        temporary = output / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        temporary.replace(report_path)

    save()
    for name, command, timeout in zip(("compile", "probe"), commands, (60, 15)):
        began = time.monotonic()
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            (output / f"{name}.stdout").write_bytes(error.stdout or b"")
            (output / f"{name}.stderr").write_bytes(error.stderr or b"")
            report["steps"].append({"step": name, "status": "timeout", "limit_seconds": timeout})
            save()
            raise RuntimeError(f"{name} timed out; partial evidence retained") from error
        (output / f"{name}.stdout").write_bytes(result.stdout)
        (output / f"{name}.stderr").write_bytes(result.stderr)
        report["steps"].append({"step": name, "returncode": result.returncode,
                                "seconds": time.monotonic() - began,
                                "stdout_sha256": digest(output / f"{name}.stdout"),
                                "stderr_sha256": digest(output / f"{name}.stderr")})
        save()
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect retained stderr")
    probe = json.loads((output / "probe.stdout").read_text())
    check_sources()
    if digest(source) != report["source_sha256"] or digest(Path(__file__)) != report["wrapper_sha256"]:
        raise ValueError("probe source changed during execution")
    report.update(completed=True, binary_sha256=digest(binary),
                  config=probe["config"], probes=probe["probes"],
                  contributing_triangles=len(probe["raw_contributors"]),
                  compact_samples=len(probe["compact"]))
    save()
    return {"report": str(report_path), "sha256": digest(report_path),
            "completed": True, "game_input_sent": False, "route_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.exists() or output.is_symlink() or
            output.parent.resolve() != (ROOT / "nav-candidates").resolve()):
        parser.error("output must be new and directly under the private nav-candidates store")
    os.umask(0o077)
    os.nice(15)
    try:
        print(json.dumps(run(output), sort_keys=True))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Source span diagnostic refused: {error}\n")


if __name__ == "__main__":
    main()
