"""Copied BSP hazard checks for an already checked source step transfer.

Lift and settle cover each supported body's conservative raised wedge; the
transfer covers the original complete clearance band. Existing terrain/static
collision margins are unchanged. This adds no client-step or input authority.
"""
from dataclasses import asdict,dataclass
from fractions import Fraction

from .bsp_clip import check_bsp_wedge
from .bsp_volume import BspVolumeView
from .ground_sweep import finite
from .source_detour import swept_square
from .source_floor_chain import exact_plane
from .source_step import StepTransfer,digest,expanded,patches


@dataclass(frozen=True)
class StepBspCheck:
    candidate: bool
    reason: str
    transition_sha256: str | None
    bsp_inventory_sha256: str | None
    pieces: tuple = ()
    grounded_endpoint_body_assumed: bool = True
    below_endpoint_floor_classified: bool = False
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_source_step_bsp(transition,terrain_view,static_view,bsp_view):
    def result(ok,reason,pieces=()):
        return StepBspCheck(ok,reason,getattr(transition,'transition_sha256',None),
            getattr(bsp_view,'inventory_sha256',None),tuple(pieces))
    if not isinstance(transition,StepTransfer) or not transition.candidate:
        return result(False,'accepted_source_step_required')
    if not isinstance(bsp_view,BspVolumeView):
        return result(False,'audited_bsp_inventory_required')
    e = transition.evidence
    try:
        if digest(e)!=transition.transition_sha256:
            return result(False,'source_step_evidence_changed')
        if (e['source_wld_sha256']!=getattr(terrain_view,'wld_sha256',None)
                or e['source_wld_sha256']!=bsp_view.wld_sha256
                or e['static_inventory_sha256']!=getattr(static_view,'inventory_sha256',None)):
            return result(False,'source_step_inventory_changed')
        sweep = tuple(tuple(p) for p in e['footprint'])
        terrain = terrain_view.source_faces_for_footprint(sweep)
        static = static_view.faces_for_footprint(sweep)
        if digest({'footprint':sweep,'terrain':[asdict(s) for s in terrain],
                   'static':[asdict(s) for s in static]})!=e['geometry_sha256']:
            return result(False,'source_step_geometry_changed')
        inventory = {(s.fragment,s.face):s for s in terrain}
        pieces = []; refusal = None
        for name,position,endpoint in (('lift',e['start'],e['lower_endpoint']),
                                       ('settle',e['end'],e['landing_endpoint'])):
            footprint = swept_square(tuple(position),tuple(position),e['radius'])
            local_sources = terrain_view.source_faces_for_footprint(footprint)
            endpoint_geometry = digest({'footprint':footprint,'sources':[asdict(s) for s in local_sources]})
            if endpoint_geometry!=endpoint['geometry_sha256']:
                return result(False,'source_step_endpoint_geometry_changed',pieces)
            ids = tuple(tuple(k) for k in endpoint['selected_ids'])
            height = e[name]['hypothetical_body_height']
            if not finite(height) or not 0<height<=108:
                return result(False,'invalid_source_step_phase_height',pieces)
            selected = patches(ids,inventory,expanded(footprint))
            if len(selected)!=len(ids):
                return result(False,'source_step_endpoint_patch_missing',pieces)
            for identity,points,polygon,_ in selected:
                dx,dy,offset = exact_plane(points)
                lower = (dy,dx,offset)
                upper = (dy,dx,offset+Fraction(height)+Fraction(.01))
                xy = tuple((y,x) for x,y in polygon)
                checked = check_bsp_wedge(bsp_view,xy,lower,upper)
                pieces.append(dict(phase=name,selected_id=identity,
                    endpoint_geometry_sha256=endpoint_geometry,endpoint_proof_sha256=endpoint['proof_sha256'],
                    volume_sha256=digest({'xy':[[str(v) for v in p] for p in xy],
                        'lower':[str(v) for v in lower],'upper':[str(v) for v in upper]}),
                    traversal=asdict(checked)))
                if not checked.candidate and refusal is None:
                    refusal = name+'_'+checked.reason
        low,high = (Fraction(v) for v in e['transfer_band_exact'])
        xy = tuple((y,x) for x,y in expanded(sweep))
        checked = check_bsp_wedge(bsp_view,xy,(0,0,low),(0,0,high))
        pieces.append(dict(phase='transfer',selected_id=None,
            volume_sha256=digest({'xy':[[str(v) for v in p] for p in xy],
                                 'band':[str(low),str(high)]}),traversal=asdict(checked)))
        if not checked.candidate and refusal is None:
            refusal = 'transfer_'+checked.reason
        if refusal is not None:
            return result(False,refusal,pieces)
        return result(True,'conditional_source_step_bsp_only',pieces)
    except (KeyError,TypeError,ValueError,ZeroDivisionError,OverflowError):
        return result(False,'invalid_source_step_bsp_request')
