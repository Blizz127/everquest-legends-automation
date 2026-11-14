"""Native metadata over independently checked terrain/static body volumes."""
from dataclasses import asdict, dataclass
from fractions import Fraction

from .client_region_classification import ClientBspClassificationView
from .ground_sweep import area, clip, hull
from .source_floor_chain import exact_plane, rational
from .static_floor_guard import check_source_static_floor


@dataclass(frozen=True)
class NativeBodyClassification:
    complete: bool
    reason: str
    floor_proof_sha256: str | None
    geometry_sha256: str | None
    static_inventory_sha256: str | None
    classification_inventory_sha256: str | None
    possible_flags: tuple[int, ...] = ()
    pieces: tuple = ()
    volume_scope: str = 'above_each_checked_source_floor_patch; original_AABB_enclosure'
    grounded_body_assumed: bool = True
    below_floor_classified: bool = False
    native_bounds_checked: bool = False
    terrain_collision_margins_unchanged: bool = True
    collision_behavior_verified: bool = False
    input_authorized: bool = False
    real_client_accepted: bool = False


def classify_source_body_regions(step, footprint, terrain_sources, static_view, classifier, *, source_wld_sha256):
    """Metadata completeness does not mean hazard-free or collision-free."""
    def result(complete, reason, pieces=()):
        flags = tuple(sorted({c['flags'] for p in pieces for c in p['classification']['possible_classes']}))
        return NativeBodyClassification(complete, reason,
            getattr(step, 'proof_sha256', None), getattr(step, 'geometry_sha256', None),
            getattr(static_view, 'inventory_sha256', None), getattr(classifier, 'inventory_sha256', None),
            flags, tuple(pieces))
    checked = check_source_static_floor(step, footprint, terrain_sources, static_view)
    if not checked.candidate:
        return result(False, 'terrain_static_'+checked.reason)
    if not isinstance(classifier, ClientBspClassificationView):
        return result(False, 'audited_native_classification_required')
    if classifier.wld_sha256 != source_wld_sha256:
        return result(False, 'native_classification_source_mismatch')
    inventory = {(s.fragment, s.face):s for s in terrain_sources}
    if len(inventory) != len(terrain_sources) or not set(step.selected_ids) <= inventory.keys():
        return result(False, 'selected_floor_inventory_changed')
    body = step.occupancy.hypothetical_body_height
    boundary = hull(footprint)
    expanded = hull((x+dx, y+dy) for x, y in boundary for dx in (-.002,.002) for dy in (-.002,.002))
    exact_boundary = rational(expanded)
    pieces = []; failure = None
    try:
        for key in step.selected_ids:
            vertices = tuple((y,x,z) for x,y,z in inventory[key].vertices_wld)
            patch = clip(exact_boundary, hull(tuple(p[:2] for p in rational(vertices))))
            if area(patch) <= 0:
                return result(False, 'selected_floor_patch_has_no_area', pieces)
            dx,dy,offset = exact_plane(vertices)
            body_vertices = tuple((y,x,dx*x+dy*y+offset+height) for x,y in patch
                for height in (Fraction(0), Fraction(body)+Fraction(.01)))
            classification = classifier.classify_convex_enclosure_after_bounds(body_vertices)
            pieces.append(dict(selected_id=key, classification=asdict(classification)))
            if not classification.complete and failure is None: failure = classification.reason
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return result(False, 'invalid_checked_floor_body_volume', pieces)
    if not pieces: return result(False, 'selected_floor_has_no_body_volume')
    return result(failure is None, failure or 'native_body_metadata_only', pieces)
