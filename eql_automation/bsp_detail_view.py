"""Small, read-only detail-triangle view for copied BSP route checks.

The owner helper's full NavMesh loader builds walls, links and spatial grids.
The BSP centerline audit needs only polygon areas and sorted detail faces.
Source and mesh hashes are verified by the calling offline tool.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class BspDetailMeshView:
    def __init__(self, area: np.ndarray, detail: np.ndarray,
                 detail_start: np.ndarray) -> None:
        self.area = area
        self._detail = detail
        self._detail_start = detail_start

    @classmethod
    def load(cls, path: Path, *, zone: str, expected_format: int = 1) -> "BspDetailMeshView":
        try:
            with np.load(path, allow_pickle=False) as data:
                meta = json.loads(str(data["meta"]))
                area = np.asarray(data["poly_area"], dtype=np.int64).reshape(-1)
                nv = np.asarray(data["poly_nv"], dtype=np.int64).reshape(-1)
                detail = np.asarray(data["detail_tris"], dtype=np.float64).reshape(-1, 3, 3)
                detail_poly = np.asarray(data["detail_poly"], dtype=np.int64).reshape(-1)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            raise ValueError(f"copied mesh detail view cannot load: {error}") from error
        if (not isinstance(meta, dict) or meta.get("format") != expected_format or
                meta.get("zone") != zone or not 1 <= len(area) <= 200000 or
                len(nv) != len(area) or len(detail_poly) != len(detail) or
                len(detail) > 2000000 or
                (len(detail_poly) and
                 (detail_poly.min() < 0 or detail_poly.max() >= len(area))) or
                not np.isfinite(detail).all()):
            raise ValueError("copied mesh detail view has invalid metadata or arrays")
        order = np.argsort(detail_poly, kind="stable")
        sorted_poly = detail_poly[order]
        return cls(area, detail[order],
                   np.searchsorted(sorted_poly, np.arange(len(area) + 1)))
