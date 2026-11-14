"""Conservative copied-BSP classification of closed convex body volumes.

Plane arithmetic is exact for the supplied binary floats/rational bounds.
The volume is not clipped as branches are traversed: this can visit extra
leaves and refuse unnecessarily, but cannot discard a possible occupied leaf.
Unlabelled copied regions do not establish live dryness or collision safety.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import math
import re

from .ground_sweep import area, hull


def rational_number(value):
    if isinstance(value, Fraction):
        return value
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Prism coordinates must be finite real numbers")
    return Fraction(value)


@dataclass(frozen=True)
class BspVolumeResult:
    candidate: bool
    reason: str
    visits: int
    region_ids: tuple[int, ...] = ()
    labelled_regions: tuple[tuple[int, tuple[str, ...]], ...] = ()
    conservative_unclipped_traversal: bool = True
    input_authorized: bool = False
    real_client_accepted: bool = False


class BspVolumeView:
    """Immutable-value snapshot of an audited WLD tree and its label sets."""

    def __init__(self, lookup, *, region_count, wld_sha256):
        if (type(region_count) is not int or not 1 <= region_count <= 1_000_000
                or not isinstance(wld_sha256, str)
                or re.fullmatch('[0-9a-f]{64}', wld_sha256) is None):
            raise ValueError("Audited region count and WLD identity are required")
        nodes = tuple(tuple(node) for node in lookup.nodes)
        if not 1 <= len(nodes) <= 2_000_000:
            raise ValueError("BSP node inventory is empty or exceeds budget")
        for node in nodes:
            if (len(node) != 7 or any(type(n) not in (int, float) or not math.isfinite(n)
                                      for n in node[:4])
                    or any(type(n) is not int for n in node[4:])
                    or not 0 <= node[4] <= region_count
                    or any(not 0 <= n <= len(nodes) for n in node[5:])):
                raise ValueError("Invalid BSP plane or region/child reference")
        labels = [() for _ in range(region_count)]
        for region, names in lookup.labels_by_region.items():
            if (type(region) is not int or not 0 <= region < region_count
                    or not isinstance(names, (tuple, list, set, frozenset))
                    or any(not isinstance(name, str) or not name or len(name) > 256
                           for name in names)):
                raise ValueError("Invalid copied BSP region labels")
            labels[region] = tuple(sorted(set(names)))
        self.labels = tuple(labels)
        self.nodes = tuple(tuple(Fraction(n) for n in node[:4]) + node[4:] for node in nodes)
        self.region_count = region_count
        self.wld_sha256 = wld_sha256
        self.inventory_sha256 = sha256(json.dumps(
            {'nodes': nodes, 'labels': self.labels, 'regions': region_count, 'wld_sha256': wld_sha256},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

    @classmethod
    def from_wld(cls, wld):
        from .bsp_probe import BspPointLookup
        return cls(BspPointLookup(wld), region_count=wld.bsp_region_count, wld_sha256=wld.sha256)

    def check_prism(self, xy_wld, z_bounds, *, max_visits=4096, max_depth=256, expected_zone_line=None):
        if (not isinstance(xy_wld, tuple) or not 3 <= len(xy_wld) <= 128
                or any(not isinstance(p, tuple) or len(p) != 2 for p in xy_wld)
                or not isinstance(z_bounds, tuple) or len(z_bounds) != 2
                or type(max_visits) is not int or not 1 <= max_visits <= 4096
                or type(max_depth) is not int or not 1 <= max_depth <= 256):
            raise ValueError("Invalid BSP prism or traversal budget")
        xy = tuple(tuple(rational_number(n) for n in p) for p in xy_wld)
        low, high = map(rational_number, z_bounds)
        boundary = hull(xy)
        if len(boundary) != len(xy) or area(boundary) <= 0 or low >= high:
            raise ValueError("BSP prism must have a convex nonzero footprint and height")
        vertices = tuple((x, y, z) for x, y in boundary for z in (low, high))
        return self.check_convex_volume(vertices, max_visits=max_visits, max_depth=max_depth,
                                        expected_zone_line=expected_zone_line)

    def check_convex_volume(self, vertices_wld, *, max_visits=4096, max_depth=256, expected_zone_line=None):
        """Conservatively classify the closed convex hull of exact 3D vertices.

        Affine extrema occur at vertices. Every branch still sees the entire
        hull, so this can refuse unnecessarily; it cannot discard an occupied
        leaf. This supports source-floor wedges without inventing below-floor
        volume. It does not claim to classify a union's convex hull as dry.
        """
        if (not isinstance(vertices_wld, tuple) or not 4 <= len(vertices_wld) <= 256
                or any(not isinstance(p, tuple) or len(p) != 3 for p in vertices_wld)
                or type(max_visits) is not int or not 1 <= max_visits <= 4096
                or type(max_depth) is not int or not 1 <= max_depth <= 256):
            raise ValueError('Invalid convex BSP volume or traversal budget')
        if expected_zone_line is not None:
            from .zone_line import ExpectedZoneLine
            if not isinstance(expected_zone_line,ExpectedZoneLine):
                raise ValueError('Typed expected zone-line geometry required')
            expected_zone_line.check_bsp(self)
        vertices = tuple(tuple(rational_number(v) for v in p) for p in vertices_wld)
        # Exact rank check: a point/line/plane is not a body volume.
        basis = {}
        origin = vertices[0]
        for point in vertices[1:]:
            row = [point[k]-origin[k] for k in range(3)]
            for pivot, existing in sorted(basis.items()):
                factor = row[pivot]
                row = [a-factor*b for a,b in zip(row, existing)]
            pivot = next((i for i,v in enumerate(row) if v), None)
            if pivot is not None:
                scale = row[pivot]
                basis[pivot] = tuple(v/scale for v in row)
            if len(basis) == 3:
                break
        if len(basis) != 3:
            raise ValueError('BSP body volume must have nonzero 3D extent')
        stack = [(1, frozenset())]
        visits = 0
        regions = set()
        labelled = []

        def result(ok, reason):
            return BspVolumeResult(ok, reason, visits, tuple(sorted(regions)), tuple(labelled))

        while stack:
            if visits >= max_visits:
                return result(False, 'bsp_volume_visit_budget_exceeded')
            number, ancestry = stack.pop()
            visits += 1
            if number == 0:
                return result(False, 'missing_bsp_child')
            if number in ancestry:
                return result(False, 'bsp_volume_cycle')
            if len(ancestry) >= max_depth:
                return result(False, 'bsp_volume_depth_budget_exceeded')
            nx, ny, nz, split, region, left, right = self.nodes[number - 1]
            if left == 0 and right == 0:
                if region == 0:
                    return result(False, 'bsp_leaf_has_no_region')
                region -= 1
                regions.add(region)
                if self.labels[region]:
                    labelled.append((region, self.labels[region]))
                    if expected_zone_line is None or not expected_zone_line.allows_region(region,self.labels[region]):
                        return result(False, 'labelled_bsp_volume')
                continue
            values = tuple(nx*x + ny*y + nz*z + split for x,y,z in vertices)
            minimum, maximum = min(values), max(values)
            next_ancestry = ancestry | {number}
            if minimum > 0:
                stack.append((left, next_ancestry))
            elif maximum < 0:
                stack.append((right, next_ancestry))
            else:
                # Touching is deliberately inclusive on both sides.
                stack.append((right, next_ancestry))
                stack.append((left, next_ancestry))
        return result(True, 'conditional_expected_zone_line_volume' if labelled
                      else 'copied_bsp_prism_candidate_only')
