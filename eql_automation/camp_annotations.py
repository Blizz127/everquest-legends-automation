"""Copied map annotations are destination hints, not verified camp data."""
from dataclasses import dataclass
from hashlib import sha256
import re

from .client_ingest import parse_map


@dataclass(frozen=True)
class CampAnnotation:
    raw_label: str
    name: str
    level_hint: tuple[int, int]
    map_xyz: tuple[float, float, float]
    map_sha256: str

    def hint_includes(self, level):
        if type(level) is not int or not 1 <= level <= 50:
            raise ValueError('A current level from 1 through 50 is required')
        return self.level_hint[0] <= level <= self.level_hint[1]


def read_camp_annotations(data):
    """Keep source text and coordinates; do not infer map/zone alignment here."""
    if not isinstance(data, bytes) or not 0 < len(data) <= 1024*1024:
        raise ValueError('A bounded copied map document is required')
    document = parse_map(data.decode('latin-1'))
    pin = sha256(data).hexdigest()
    result = []
    for label in document.labels:
        match = re.fullmatch(r'L(\d{2})-(\d{2})_(\S.*)', label.text)
        if match is None:
            continue
        low, high = map(int, match.group(1, 2))
        if not 1 <= low <= high <= 50:
            raise ValueError('Camp annotation has an unsupported level hint')
        result.append(CampAnnotation(label.text, match[3].replace('_', ' '),
            (low, high), (label.point.x, label.point.y, label.point.z), pin))
    if not 1 <= len(result) <= 128 or len({r.raw_label for r in result}) != len(result):
        raise ValueError('A bounded, unique camp annotation inventory is required')
    return tuple(result)
