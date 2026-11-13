"""Search labels from an imported client map snapshot.

Labels are hints on a drawing. They do not establish that an NPC exists, a
zone line works, or a route is traversable. Every returned POI is unverified.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import dist, isfinite
from pathlib import Path
import gzip
import json

from .client_ingest import load_map, sha256_file
from .nav import MAP_STORE, Point


INDEX_FORMAT = "client-map-poi-hints-v1"


@dataclass(frozen=True)
class MapPoi:
    map_name: str
    text: str
    point: Point
    rgb: tuple[int, int, int]
    size: int
    hint: str
    verified: bool = False


def classify_hint(text: str) -> str:
    normalized = text.strip().casefold()
    if normalized.startswith("to_"):
        return "zone_exit_hint"
    if "portal" in normalized:
        return "portal_hint"
    if "merchant" in normalized and "spell" in normalized:
        return "merchant_spell_hint"
    if "merchant" in normalized:
        return "merchant_hint"
    if "spell" in normalized:
        return "spell_hint"
    return "landmark"


class PoiIndex:
    def __init__(self, snapshot_id: str, summary_sha256: str,
                 pois: list[MapPoi]) -> None:
        self.snapshot_id = snapshot_id
        self.summary_sha256 = summary_sha256
        self.pois = pois

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(poi.hint for poi in self.pois).items()))

    def search(self, query: str, *, map_name: str | None = None,
               limit: int = 20) -> list[MapPoi]:
        if not query.strip() or limit < 1:
            raise ValueError("A nonempty query and positive limit are required")
        needle = query.casefold().replace("_", " ")
        return [poi for poi in self.pois
                if (map_name is None or poi.map_name == map_name) and
                needle in poi.text.casefold().replace("_", " ")][:limit]

    def nearest(self, map_name: str, point: Point, *, radius: float,
                limit: int = 20) -> list[MapPoi]:
        if not isfinite(radius) or radius < 0 or limit < 1:
            raise ValueError("Radius must be finite and limit positive")
        origin = (point.x, point.y, point.z)
        pairs = [(dist(origin, (poi.point.x, poi.point.y, poi.point.z)), poi)
                 for poi in self.pois if poi.map_name == map_name]
        return [poi for distance, poi in sorted(pairs, key=lambda pair: pair[0])
                if distance <= radius][:limit]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as stream:
            json.dump({"format": INDEX_FORMAT,
                       "snapshot_id": self.snapshot_id,
                       "summary_sha256": self.summary_sha256,
                       "pois": [asdict(poi) for poi in self.pois]},
                      stream, separators=(",", ":"))
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> "PoiIndex":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
        if payload.get("format") != INDEX_FORMAT:
            raise ValueError("Unsupported POI index format")
        pois = [MapPoi(poi["map_name"], poi["text"], Point(**poi["point"]),
                       tuple(poi["rgb"]), poi["size"], poi["hint"],
                       poi["verified"]) for poi in payload["pois"]]
        if any(poi.verified for poi in pois):
            raise ValueError("Client map labels cannot be marked verified")
        return cls(payload["snapshot_id"], payload["summary_sha256"], pois)


def current_summary(store: Path = MAP_STORE) -> Path:
    pointer = json.loads((store / "current.json").read_text())
    path = Path(pointer["summary_path"])
    if not path.resolve().is_relative_to((store / "snapshots").resolve()):
        raise ValueError("Map snapshot pointer escapes store")
    return path


def index_path(summary_path: Path, store: Path = MAP_STORE) -> Path:
    summary = json.loads(summary_path.read_text())
    snapshot_id = summary["snapshot_id"]
    if not snapshot_id or any(char not in "0123456789abcdef" for char in snapshot_id):
        raise ValueError("Invalid map snapshot ID")
    return store / "indices" / f"{snapshot_id}.json.gz"


def build_poi_index(summary_path: Path, store: Path = MAP_STORE) -> tuple[PoiIndex, Path]:
    summary = json.loads(summary_path.read_text())
    snapshot = summary_path.parent.resolve()
    output = index_path(summary_path, store)
    summary_hash = sha256_file(summary_path)
    if output.is_file():
        existing = PoiIndex.load(output)
        if (existing.snapshot_id == summary["snapshot_id"] and
                existing.summary_sha256 == summary_hash):
            return existing, output
    pois = []
    for item in summary["maps"]:
        geometry = Path(item["geometry_store"])
        if not geometry.resolve().is_relative_to(snapshot):
            raise ValueError("Map geometry path escapes snapshot")
        document = load_map(geometry)
        for label in document.labels:
            pois.append(MapPoi(item["name"], label.text, label.point,
                               label.rgb, label.size, classify_hint(label.text)))
    index = PoiIndex(summary["snapshot_id"], summary_hash, pois)
    index.save(output)
    return index, output
