"""Bind a conservative BSP prism to an accepted copied terrain cell."""
from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
import json
import math

from .bsp_volume import BspVolumeResult, BspVolumeView
from .floor_replay import FloorTrial
from .ground_sweep import area, clip, hull
from .source_floor_chain import FloorChainStep, exact_plane, rational


def outward_float(value, *, lower):
    result = float(value)
    if (Fraction(result) > value if lower else Fraction(result) < value):
        result = math.nextafter(result, -math.inf if lower else math.inf)
    return result


@dataclass(frozen=True)
class BspFloorCheck:
    candidate: bool
    reason: str
    geometry_sha256: str | None = None
    floor_proof_sha256: str | None = None
    bsp_inventory_sha256: str | None = None
    wld_sha256: str | None = None
    prism_sha256: str | None = None
    selected_ids: tuple[tuple[int, int], ...] = ()
    floor_z_bounds: tuple[float, float] | None = None
    prism_z_bounds: tuple[float, float] | None = None
    hypothetical_body_height: float | None = None
    traversal: BspVolumeResult | None = None
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_bsp_floor(floor_trial, footprint, terrain_sources, bsp_view, *, expected_zone_line=None):
    """Test the full expanded footprint from lowest floor to highest head.

The Z band deliberately overestimates a sloping/multi-patch floor. Exact
rationals drive traversal; outward rounded floats are only report summaries.
The .1 below-floor and .01 numeric margins match the occupancy guard defaults.
"""
    if (not isinstance(floor_trial, FloorTrial) or not floor_trial.candidate
            or floor_trial.floor_step is None or not floor_trial.floor_step.candidate
            or floor_trial.floor_step.occupancy is None
            or not floor_trial.floor_step.occupancy.candidate):
        return BspFloorCheck(False, 'accepted_terrain_trial_required')
    return check_source_bsp_floor(floor_trial.floor_step, footprint, terrain_sources, bsp_view,
                                   expected_zone_line=expected_zone_line)


def check_source_bsp_floor(step, footprint, terrain_sources, bsp_view, *, expected_zone_line=None):
    """Classify the full prism of a source cell; makes no baked-mesh claim."""
    if (not isinstance(step, FloorChainStep) or not step.candidate
            or step.occupancy is None or not step.occupancy.candidate):
        return BspFloorCheck(False, 'accepted_source_floor_step_required')
    if (step.selected_ids != step.occupancy.selected_ids
            or type(step.occupancy.hypothetical_body_height) not in (int, float)
            or not math.isfinite(step.occupancy.hypothetical_body_height)
            or not 0 < step.occupancy.hypothetical_body_height <= 100):
        return BspFloorCheck(False, 'terrain_selection_or_body_changed')
    try:
        geometry = sha256(json.dumps({'footprint': footprint,
            'sources': [asdict(s) for s in terrain_sources]},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError):
        return BspFloorCheck(False, 'invalid_terrain_cell')
    if geometry != step.geometry_sha256:
        return BspFloorCheck(False, 'terrain_cell_changed_since_floor_trial')
    if not isinstance(bsp_view, BspVolumeView):
        return BspFloorCheck(False, 'audited_bsp_inventory_required')
    inventory = {(s.fragment, s.face): s for s in terrain_sources}
    if len(inventory) != len(terrain_sources) or not set(step.selected_ids) <= inventory.keys():
        return BspFloorCheck(False, 'selected_floor_inventory_changed')
    # Reproduce the exact float expansion used by the accepted occupancy test,
    # then preserve those values as rationals for all further geometry.
    boundary = hull(footprint)
    expanded = hull((x+dx, y+dy) for x, y in boundary
                    for dx in (-.002, .002) for dy in (-.002, .002))
    exact_boundary = rational(expanded)
    heights = []
    try:
        for key in step.selected_ids:
            source = inventory[key]
            vertices = tuple((y, x, z) for x, y, z in source.vertices_wld)
            patch = clip(exact_boundary, hull(tuple(p[:2] for p in rational(vertices))))
            dx, dy, offset = exact_plane(vertices)
            heights.extend(dx*x + dy*y + offset for x, y in patch)
        if not heights:
            return BspFloorCheck(False, 'selected_floor_has_no_prism_support')
        floor_low, floor_high = min(heights), max(heights)
        body = step.occupancy.hypothetical_body_height
        low = floor_low - Fraction(.1) - Fraction(.01)
        high = floor_high + Fraction(body) + Fraction(.01)
        # The source/helper package swaps XY relative to raw WLD BSP planes.
        xy_wld = hull(tuple((y, x) for x, y in exact_boundary))
        prism = {'xy_wld': [[str(n) for n in p] for p in xy_wld],
                 'z_bounds': [str(low), str(high)]}
        prism_sha = sha256(json.dumps(prism, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        traversal = bsp_view.check_prism(xy_wld, (low, high),expected_zone_line=expected_zone_line)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return BspFloorCheck(False, 'invalid_selected_floor_prism')
    return BspFloorCheck(traversal.candidate, traversal.reason, geometry,
        step.proof_sha256, bsp_view.inventory_sha256, bsp_view.wld_sha256, prism_sha,
        step.selected_ids, (outward_float(floor_low, lower=True), outward_float(floor_high, lower=False)),
        (outward_float(low, lower=True), outward_float(high, lower=False)), body, traversal)


@dataclass(frozen=True)
class SourceBodyBspCheck:
    candidate: bool
    reason: str
    floor_proof_sha256: str | None = None
    bsp_inventory_sha256: str | None = None
    pieces: tuple = ()
    geometry_sha256: str | None = None
    bsp_wld_sha256: str | None = None
    selected_ids: tuple = ()
    grounded_body_assumed: bool = True
    volume_scope: str = 'above_each_verified_source_floor_patch'
    below_floor_bsp_classified: bool = False
    terrain_collision_margins_unchanged: bool = True
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_source_body_bsp(step, footprint, terrain_sources, bsp_view, *, clip_branches=False,
                          expected_zone_line=None):
    """Classify occupied space above a complete, collision-checked source floor.

    The original occupancy check retains below-floor and numeric margins.
    BSP hazard classification instead checks each supporting patch's exact
    vertical body wedge, from its floor to body_height+.01. Space beneath
    verified support is not claimed dry or otherwise classified by this result.
    Every selected patch must pass; no failed old prism result is overwritten.
    """
    def result(ok, reason, pieces=()):
        return SourceBodyBspCheck(ok, reason,
            getattr(step, 'proof_sha256', None), getattr(bsp_view, 'inventory_sha256', None), tuple(pieces),
            geometry_sha256=getattr(step, 'geometry_sha256', None),
            bsp_wld_sha256=getattr(bsp_view, 'wld_sha256', None),
            selected_ids=getattr(step, 'selected_ids', ()))
    if (not isinstance(step, FloorChainStep) or not step.candidate
            or step.occupancy is None or not step.occupancy.candidate
            or step.selected_ids != step.occupancy.selected_ids):
        return result(False, 'accepted_source_floor_step_required')
    body = step.occupancy.hypothetical_body_height
    if type(body) not in (int, float) or not math.isfinite(body) or not 0 < body <= 100:
        return result(False, 'valid_body_height_required')
    try:
        geometry = sha256(json.dumps({'footprint': footprint,
            'sources': [asdict(s) for s in terrain_sources]},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError):
        return result(False, 'invalid_terrain_cell')
    if geometry != step.geometry_sha256:
        return result(False, 'terrain_cell_changed_since_floor_trial')
    if not isinstance(bsp_view, BspVolumeView):
        return result(False, 'audited_bsp_inventory_required')
    inventory = {(s.fragment, s.face): s for s in terrain_sources}
    if len(inventory) != len(terrain_sources) or not set(step.selected_ids) <= inventory.keys():
        return result(False, 'selected_floor_inventory_changed')
    boundary = hull(footprint)
    expanded = hull((x+dx,y+dy) for x,y in boundary for dx in (-.002,.002) for dy in (-.002,.002))
    exact_boundary = rational(expanded)
    pieces = []
    try:
        for key in step.selected_ids:
            source = inventory[key]
            vertices = tuple((y,x,z) for x,y,z in source.vertices_wld)
            patch = clip(exact_boundary, hull(tuple(p[:2] for p in rational(vertices))))
            # Closed clipping can repeat a corner that lies exactly on a
            # source edge. Canonicalize the convex patch without changing
            # its exact area or dropping the closed edge/point boundary.
            canonical = hull(patch)
            if area(canonical) != area(patch):
                return result(False, 'selected_floor_patch_not_convex', pieces)
            patch = canonical
            if area(patch) <= 0:
                # SourceFloorChain selected only positive-area patches. A
                # changed/degenerate one cannot silently lose its boundary.
                return result(False, 'selected_floor_patch_has_no_area', pieces)
            dx,dy,offset = exact_plane(vertices)
            body_vertices = tuple((y,x,dx*x+dy*y+offset+height)
                for x,y in patch for height in (Fraction(0), Fraction(body)+Fraction(.01)))
            if clip_branches:
                from .bsp_clip import check_bsp_wedge
                # The floor plane is in helper XY; swap its coefficients and
                # polygon into raw WLD together, retaining exact arithmetic.
                traversal = check_bsp_wedge(bsp_view,tuple((y,x) for x,y in patch),
                    (dy,dx,offset),(dy,dx,offset+Fraction(body)+Fraction(.01)),
                    expected_zone_line=expected_zone_line)
            else:
                traversal = bsp_view.check_convex_volume(body_vertices,
                    expected_zone_line=expected_zone_line)
            digest = sha256(json.dumps([[str(n) for n in p] for p in body_vertices],
                separators=(',', ':')).encode()).hexdigest()
            pieces.append(dict(selected_id=key, volume_sha256=digest,
                vertex_count=len(body_vertices), traversal=asdict(traversal)))
            if not traversal.candidate:
                return result(False, traversal.reason, pieces)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return result(False, 'invalid_selected_floor_body_volume', pieces)
    if not pieces:
        return result(False, 'selected_floor_has_no_body_volume')
    return result(True, 'conditional_source_body_bsp_only', pieces)
