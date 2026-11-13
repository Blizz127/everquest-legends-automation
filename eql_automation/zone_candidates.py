"""Unverified zone-line candidates from client map labels and zone names.

Exact text matches identify review targets only. They never create a traversable
WorldNav transition, map-stem mapping, or permission to send game input.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
import gzip
import json
import re
import unicodedata

from .nav import MAP_STORE, Point
from .poi_index import build_poi_index, index_path
from .client_ingest import sha256_file


FORMAT = "client-zone-candidates-v2"


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("_", " ").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def token_key(text: str) -> tuple[str, ...]:
    return tuple(sorted(normalize_name(text).split()))


@dataclass(frozen=True)
class ZoneCandidate:
    source_map: str
    label: str
    point: Point
    match_type: str
    client_zone_ids: tuple[int, ...]
    client_zone_names: tuple[str, ...]
    verified: bool = False


class ZoneCandidateIndex:
    def __init__(self, snapshot_id: str, summary_sha256: str,
                 candidates: list[ZoneCandidate]) -> None:
        self.snapshot_id = snapshot_id
        self.summary_sha256 = summary_sha256
        self.candidates = candidates

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.match_type for item in self.candidates).items()))

    def search(self, query: str, *, source_map: str | None = None,
               limit: int = 20) -> list[ZoneCandidate]:
        needle = normalize_name(query)
        if not needle or limit < 1:
            raise ValueError("A nonempty query and positive limit are required")
        return [item for item in self.candidates
                if (source_map is None or item.source_map == source_map) and
                (needle in normalize_name(item.label) or
                 any(needle in normalize_name(name) for name in item.client_zone_names))][:limit]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as stream:
            json.dump({"format": FORMAT, "snapshot_id": self.snapshot_id,
                       "summary_sha256": self.summary_sha256,
                       "candidates": [asdict(item) for item in self.candidates]},
                      stream, separators=(",", ":"))
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> "ZoneCandidateIndex":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
        if payload.get("format") != FORMAT:
            raise ValueError("Unsupported zone-candidate format")
        candidates = [ZoneCandidate(
            item["source_map"], item["label"], Point(**item["point"]),
            item["match_type"], tuple(item["client_zone_ids"]),
            tuple(item["client_zone_names"]), item["verified"])
            for item in payload["candidates"]]
        if any(item.verified for item in candidates):
            raise ValueError("Map labels cannot be marked verified zone transitions")
        return cls(payload["snapshot_id"], payload["summary_sha256"], candidates)


def candidate_path(summary_path: Path, store: Path = MAP_STORE) -> Path:
    poi_path = index_path(summary_path, store)
    return poi_path.with_name(poi_path.name.replace(".json.gz", "-zones-v2.json.gz"))


def build_zone_candidates(summary_path: Path,
                          store: Path = MAP_STORE) -> tuple[ZoneCandidateIndex, Path]:
    summary = json.loads(summary_path.read_text())
    snapshot = summary_path.parent.resolve()
    zone_path = Path(summary["zone_names_store"])
    if not zone_path.resolve().is_relative_to(snapshot):
        raise ValueError("Zone-name path escapes map snapshot")
    output = candidate_path(summary_path, store)
    summary_hash = sha256_file(summary_path)
    if output.is_file():
        existing = ZoneCandidateIndex.load(output)
        if existing.snapshot_id == summary["snapshot_id"] and existing.summary_sha256 == summary_hash:
            return existing, output
    zones = json.loads(zone_path.read_text())
    by_name: dict[str, list[dict]] = defaultdict(list)
    by_tokens: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for zone in zones:
        by_name[normalize_name(zone["name"])].append(zone)
        by_tokens[token_key(zone["name"])].append(zone)
    pois, _ = build_poi_index(summary_path, store)
    candidates = []
    for poi in pois.pois:
        prefixed = poi.text.casefold().startswith("to_")
        target_text = poi.text[3:] if prefixed else poi.text
        matches = by_name.get(normalize_name(target_text), [])
        token_order_only = False
        if not matches:
            matches = by_tokens.get(token_key(target_text), [])
            token_order_only = bool(matches)
        if not prefixed and not matches:
            continue
        if prefixed:
            if token_order_only:
                match_type = "to_prefix_token_order"
            else:
                match_type = "to_prefix_exact" if matches else "to_prefix_unmatched"
        else:
            match_type = "label_token_order" if token_order_only else "label_exact"
        candidates.append(ZoneCandidate(
            poi.map_name, poi.text, poi.point, match_type,
            tuple(zone["id"] for zone in matches),
            tuple(zone["name"] for zone in matches)))
    index = ZoneCandidateIndex(summary["snapshot_id"], summary_hash, candidates)
    index.save(output)
    return index, output
