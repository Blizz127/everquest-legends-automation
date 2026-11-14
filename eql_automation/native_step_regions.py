"""Native metadata for all phases of an already checked source step."""
from dataclasses import asdict, dataclass
from fractions import Fraction

from .client_region_classification import ClientBspClassificationView
from .ground_sweep import finite
from .source_detour import swept_square
from .source_floor_chain import exact_plane
from .source_step import StepTransfer, digest, expanded, patches


@dataclass(frozen=True)
class NativeStepClassification:
    complete: bool
    reason: str
    transition_sha256: str | None
    classification_inventory_sha256: str | None
    possible_flags: tuple = ()
    pieces: tuple = ()
    grounded_endpoint_body_assumed: bool = True
    below_endpoint_floor_classified: bool = False
    native_bounds_checked: bool = False
    collision_behavior_verified: bool = False
    input_authorized: bool = False
    real_client_accepted: bool = False


def classify_source_step_regions(transition, terrain_view, static_view, classifier):
    """Recheck source identity, then classify lift/transfer/settle separately."""
    def result(complete, reason, pieces=()):
        flags = tuple(sorted({c['flags'] for p in pieces for c in p['classification']['possible_classes']}))
        return NativeStepClassification(complete, reason, getattr(transition, 'transition_sha256', None),
            getattr(classifier, 'inventory_sha256', None), flags, tuple(pieces))
    if not isinstance(transition, StepTransfer) or not transition.candidate:
        return result(False, 'accepted_source_step_required')
    if not isinstance(classifier, ClientBspClassificationView):
        return result(False, 'audited_native_classification_required')
    e = transition.evidence
    try:
        if digest(e) != transition.transition_sha256:
            return result(False, 'source_step_evidence_changed')
        if (e['source_wld_sha256'] != getattr(terrain_view, 'wld_sha256', None)
                or e['source_wld_sha256'] != classifier.wld_sha256
                or e['static_inventory_sha256'] != getattr(static_view, 'inventory_sha256', None)):
            return result(False, 'source_step_inventory_changed')
        sweep = tuple(tuple(p) for p in e['footprint'])
        terrain = terrain_view.source_faces_for_footprint(sweep)
        static = static_view.faces_for_footprint(sweep)
        if digest({'footprint':sweep, 'terrain':[asdict(s) for s in terrain],
                   'static':[asdict(s) for s in static]}) != e['geometry_sha256']:
            return result(False, 'source_step_geometry_changed')
        inventory = {(s.fragment, s.face):s for s in terrain}
        pieces = []; failure = None
        for name, position, endpoint in (('lift', e['start'], e['lower_endpoint']),
                                         ('settle', e['end'], e['landing_endpoint'])):
            footprint = swept_square(tuple(position), tuple(position), e['radius'])
            local = terrain_view.source_faces_for_footprint(footprint)
            geometry = digest({'footprint':footprint, 'sources':[asdict(s) for s in local]})
            if geometry != endpoint['geometry_sha256']:
                return result(False, 'source_step_endpoint_geometry_changed', pieces)
            ids = tuple(tuple(k) for k in endpoint['selected_ids'])
            height = e[name]['hypothetical_body_height']
            if not finite(height) or not 0 < height <= 108:
                return result(False, 'invalid_source_step_phase_height', pieces)
            selected = patches(ids, inventory, expanded(footprint))
            if len(selected) != len(ids):
                return result(False, 'source_step_endpoint_patch_missing', pieces)
            for identity, points, polygon, _ in selected:
                dx,dy,offset = exact_plane(points)
                vertices = tuple((y,x,dx*x+dy*y+offset+z) for x,y in polygon
                    for z in (Fraction(0), Fraction(height)+Fraction(.01)))
                classified = classifier.classify_convex_enclosure_after_bounds(vertices)
                pieces.append(dict(phase=name, selected_id=identity,
                    endpoint_geometry_sha256=geometry, endpoint_proof_sha256=endpoint['proof_sha256'],
                    classification=asdict(classified)))
                if not classified.complete and failure is None: failure = name+'_'+classified.reason
        low, high = (Fraction(v) for v in e['transfer_band_exact'])
        vertices = tuple((y,x,z) for x,y in expanded(sweep) for z in (low,high))
        classified = classifier.classify_convex_enclosure_after_bounds(vertices)
        pieces.append(dict(phase='transfer', selected_id=None, classification=asdict(classified)))
        if not classified.complete and failure is None: failure = 'transfer_'+classified.reason
        return result(failure is None, failure or 'native_step_metadata_only', pieces)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return result(False, 'invalid_source_step_classification_request')
