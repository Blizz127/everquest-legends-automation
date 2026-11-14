"""Local complete XY candidate lookup over a copied navmesh's detail faces."""
from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import numpy as np

from .ground_sweep import GroundFace, GroundCoverage, check_ground_coverage


class GroundSweepView:
    def __init__(self, triangles, polys, areas, components):
        self.triangles, self.polys = triangles, polys
        self.areas, self.components = areas, components
        self.minimum, self.maximum = triangles.min(axis=1), triangles.max(axis=1)

    @classmethod
    def load(cls, path: Path, *, zone):
        raw = path.read_bytes()
        with np.load(BytesIO(raw), allow_pickle=False) as data:
            meta = json.loads(str(data['meta']))
            triangles = np.asarray(data['detail_tris'], dtype=np.float64).reshape(-1, 3, 3)
            polys = np.asarray(data['detail_poly'], dtype=np.int64).reshape(-1)
            areas = np.asarray(data['poly_area'], dtype=np.int64).reshape(-1)
            components = np.asarray(data['component'], dtype=np.int64).reshape(-1)
        if (meta.get('zone') != zone or meta.get('format') != 1
                or not 1 <= len(areas) <= 200000 or len(components) != len(areas)
                or not 1 <= len(triangles) <= 2000000 or len(polys) != len(triangles)
                or polys.min() < 0 or polys.max() >= len(areas) or not np.isfinite(triangles).all()):
            raise ValueError('Invalid copied ground-sweep arrays')
        view = cls(triangles, polys, areas, components)
        view.mesh_sha256 = sha256(raw).hexdigest()
        return view

    def polygons_for_area(self, area_id):
        """Read the complete current inventory without a Python per-face loop."""
        return tuple(int(i) for i in np.flatnonzero(self.areas==area_id))

    def check(self, footprint, *, reference, component, vertical_window, max_faces=96, expected_zone_line=None):
        if expected_zone_line is not None and expected_zone_line.mesh_sha256!=self.mesh_sha256:
            raise ValueError('Zone-line footprint belongs to another mesh')
        left, right = np.min(footprint, axis=0), np.max(footprint, axis=0)
        local = np.flatnonzero((self.minimum[:, 0] <= right[0]) & (self.maximum[:, 0] >= left[0])
                              & (self.minimum[:, 1] <= right[1]) & (self.maximum[:, 1] >= left[1]))
        # Do not truncate: every intersecting XY bounding box must be checked.
        if len(local) > max_faces:
            return GroundCoverage(False, 'local_detail_face_budget_exceeded'), tuple(int(i) for i in local)
        faces = tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in self.triangles[i]),
                                int(self.areas[self.polys[i]]), int(self.components[self.polys[i]])) for i in local)
        result = check_ground_coverage(footprint, faces, reference=reference,
            component=component, vertical_window=vertical_window, max_faces=max_faces,
            expected_zone_line=expected_zone_line,polygon_ids=tuple(int(self.polys[i]) for i in local))
        return result, tuple(int(i) for i in local)
