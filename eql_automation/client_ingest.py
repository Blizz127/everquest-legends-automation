"""Read-only import of copied client text data into the local, untracked store.

Map L records are drawing geometry, not proof that an edge is walkable. P
records are labels, not verified vendors or zone lines. This importer never
creates traversable NavGraph edges from either record type.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import gzip
import json
import math
import re
import tempfile

from .nav import MAP_STORE, Point
from .prior_rotation_core import Catalog


@dataclass(frozen=True)
class MapLine:
    start: Point
    end: Point
    rgb: tuple[int, int, int]


@dataclass(frozen=True)
class MapLabel:
    point: Point
    rgb: tuple[int, int, int]
    size: int
    text: str


@dataclass
class MapDocument:
    lines: list[MapLine]
    labels: list[MapLabel]
    skipped_records: int = 0

    def bounds(self) -> dict[str, tuple[float, float]] | None:
        points = [line.start for line in self.lines] + [line.end for line in self.lines]
        points.extend(label.point for label in self.labels)
        if not points:
            return None
        return {axis: (min(getattr(point, axis) for point in points),
                       max(getattr(point, axis) for point in points))
                for axis in ("x", "y", "z")}

    def find_labels(self, fragment: str) -> list[MapLabel]:
        fragment = fragment.casefold()
        return [label for label in self.labels if fragment in label.text.casefold()]


def _number(text: str) -> float:
    value = float(text.strip())
    if not math.isfinite(value):
        raise ValueError("Nonfinite map coordinate")
    return value


def _rgb(fields: list[str]) -> tuple[int, int, int]:
    values = tuple(int(field.strip()) for field in fields)
    if len(values) != 3 or any(not 0 <= value <= 255 for value in values):
        raise ValueError("Invalid map color")
    return values


def parse_map(text: str) -> MapDocument:
    lines: list[MapLine] = []
    labels: list[MapLabel] = []
    skipped = 0
    for number, raw in enumerate(text.splitlines(), 1):
        record = raw.strip()
        if not record:
            continue
        parts = record.split(None, 1)
        prefix, body = parts[0], parts[1] if len(parts) > 1 else ""
        try:
            if prefix == "L":
                fields = body.split(",")
                if len(fields) != 9:
                    raise ValueError("Expected 9 fields in L record")
                coords = [_number(field) for field in fields[:6]]
                lines.append(MapLine(Point(*coords[:3]), Point(*coords[3:]),
                                     _rgb(fields[6:])))
            elif prefix == "P":
                fields = body.split(",", 7)
                if len(fields) != 8:
                    raise ValueError("Expected 8 fields in P record")
                point = Point(*(_number(field) for field in fields[:3]))
                size = int(fields[6].strip())
                if not 0 <= size <= 99:
                    raise ValueError("Invalid label size")
                labels.append(MapLabel(point, _rgb(fields[3:6]), size,
                                       fields[7].strip()))
            else:
                raise ValueError(f"Unknown record type {prefix!r}")
        except ValueError as exc:
            raise ValueError(f"Invalid map record at line {number}: {exc}") from exc
    return MapDocument(lines, labels, skipped)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_map(document: MapDocument, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = {
        "format": "client-map-geometry-v1",
        "navigability_verified": False,
        "lines": [asdict(line) for line in document.lines],
        "labels": [asdict(label) for label in document.labels],
        "skipped_records": document.skipped_records,
    }
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        json.dump(payload, stream, separators=(",", ":"))
    temporary.replace(path)


def load_map(path: Path) -> MapDocument:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("format") != "client-map-geometry-v1":
        raise ValueError("Unsupported map store format")
    return MapDocument(
        [MapLine(Point(**line["start"]), Point(**line["end"]),
                 tuple(line["rgb"])) for line in payload["lines"]],
        [MapLabel(Point(**label["point"]), tuple(label["rgb"]),
                  label["size"], label["text"]) for label in payload["labels"]],
        payload["skipped_records"])


def parse_zone_names(text: str) -> list[dict]:
    zones = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split("^")
        if len(fields) < 2 or not fields[0].isdigit() or not fields[1]:
            raise ValueError(f"Invalid zone-name record at line {number}")
        zones.append({"id": int(fields[0]), "name": fields[1],
                      "client_fields": fields[2:]})
    return zones


def import_retail_copy(source: Path, store: Path = MAP_STORE) -> dict:
    """Import top-level client maps into one atomic, versioned snapshot."""

    maps = sorted((source / "maps").glob("*.txt"))
    if not maps:
        raise FileNotFoundError("No copied map text files")
    spell_path = source / "spells_us.txt"
    zone_path = source / "Resources/ZoneNames.txt"
    if not spell_path.is_file() or not zone_path.is_file():
        raise FileNotFoundError("Copied spell catalog or zone-name file missing")
    for source_path in maps:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source_path.stem):
            raise ValueError("Unsafe map file name")
    hashes = {str(path.relative_to(source)): sha256_file(path)
              for path in [*maps, zone_path, spell_path]}
    digest = sha256(json.dumps({"schema": 3, "hashes": hashes},
                               sort_keys=True).encode()).hexdigest()[:20]
    snapshot_root = store / "snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    snapshot = snapshot_root / digest
    summary_path = snapshot / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text())
    else:
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=snapshot_root) as temp:
            staging = Path(temp)
            imported_maps = []
            for source_path in maps:
                document = parse_map(source_path.read_text(encoding="latin-1"))
                relative = Path("geometry") / f"{source_path.stem}.json.gz"
                save_map(document, staging / relative)
                imported_maps.append({
                    "name": source_path.stem,
                    "source_sha256": hashes[str(source_path.relative_to(source))],
                    "geometry_store": str(snapshot / relative),
                    "line_count": len(document.lines),
                    "label_count": len(document.labels),
                    "skipped_records": document.skipped_records,
                    "bounds": document.bounds(),
                    "navigability_verified": False,
                })
            zones = parse_zone_names(zone_path.read_text(encoding="latin-1"))
            catalog = Catalog.load(source)
            zone_relative = Path("zone-names.json")
            (staging / zone_relative).write_text(
                json.dumps(zones, separators=(",", ":")) + "\n")
            spell_relative = Path("paladin-cleric-spells.json.gz")
            with gzip.open(staging / spell_relative, "wt", encoding="utf-8") as stream:
                json.dump({"format": "prior-paladin-cleric-catalog-v1",
                           "source_sha256": hashes[str(spell_path.relative_to(source))],
                           "spells": [asdict(spell) for spell in catalog.spells.values()]},
                          stream, separators=(",", ":"))
            profiles_valid = True
            for class_name in ("cleric", "paladin"):
                for level in range(1, 51):
                    profile = catalog.profile(level, class_name=class_name)
                    ids = [spell.id for spell in profile.values()]
                    if (len(ids) != len(set(ids)) or
                            any(spell.level_for(class_name) > level
                                for spell in profile.values())):
                        profiles_valid = False
                        break
            summary = {
                "source_kind": "copied-retail-client-text",
                "source_dir": str(source),
                "snapshot_id": digest,
                "maps": imported_maps,
                "zone_names_sha256": hashes[str(zone_path.relative_to(source))],
                "zone_name_count": len(zones),
                "zone_names_store": str(snapshot / zone_relative),
                "spell_catalog_sha256": hashes[str(spell_path.relative_to(source))],
                "paladin_cleric_spell_count": len(catalog.spells),
                "paladin_cleric_spell_store": str(snapshot / spell_relative),
                "prior_rotation_profiles_1_to_50_valid": profiles_valid,
                "profile_classes_validated": ["cleric", "paladin"],
                "navigability_verified": False,
                "private_server_identified": False,
                "summary_path": str(summary_path),
            }
            (staging / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            staging.replace(snapshot)
    current = store / "current.json"
    current_temporary = store / "current.json.tmp"
    current_temporary.write_text(json.dumps({"snapshot_id": digest,
                                             "summary_path": str(summary_path)}) + "\n")
    current_temporary.replace(current)
    return summary
