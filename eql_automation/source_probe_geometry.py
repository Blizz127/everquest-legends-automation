"""Source-floor body checks shared by walking and unknown-heading probes.

The floor prefix is supplied by the caller. This never selects a floor from
map-label Z, guesses a heading, sends input or establishes current actor state.
"""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import time

from .bsp_floor_guard import check_source_body_bsp
from .ground_binding import finite, point
from .ground_sweep import motion_footprint
from .native_body_regions import classify_source_body_regions
from .native_region_policy import NativeZeroRegionTrialPolicy, encoded
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_itinerary import _zero_native
from .static_floor_guard import check_source_static_floor


@dataclass(frozen=True)
class CheckedSourceFootprint:
    branch: object
    terrain: object
    static: object
    bsp: object
    native: object


def _source_storage(terrain,static):
    """Pin loaded storage/query identities across caller callbacks."""
    values=[]
    for view,names,query in (
            (terrain,('sources','source_minimum','source_maximum'),'source_faces_for_footprint'),
            (static,('sources','minimum','maximum'),'faces_for_footprint')):
        values.append(getattr(view,query))
        for name in names:
            value=getattr(view,name,None)
            values.append((id(value),getattr(getattr(value,'flags',None),'writeable',None)))
    return tuple(values)


def check_source_footprint(prefix, footprint, *, terrain, static, bsp, region_policy):
    """Fork one checked prefix and check the complete body's source geometry."""
    if type(region_policy) is not NativeZeroRegionTrialPolicy:
        raise ValueError('Explicit source native-region policy required')
    original=_chain_snapshot(prefix)
    classifier=region_policy.classifier
    policy_record=encoded(region_policy.record())
    storage=_source_storage(terrain,static)
    def check():
        region_policy.check_context(zone='crushbone',pins=(region_policy.mesh_sha256,
            terrain.archive_sha256,terrain.wld_sha256,static.inventory_sha256),bsp=bsp)
        if (prefix.inventory_sha256!=terrain.wld_sha256 or _chain_snapshot(prefix)!=original
                or region_policy.classifier is not classifier
                or encoded(region_policy.record())!=policy_record
                or _source_storage(terrain,static)!=storage):
            raise ValueError('Source footprint prefix or policy changed')
    check()
    sources=terrain.source_faces_for_footprint(footprint)
    fork=prefix.fork();floor=fork.advance(footprint,sources)
    if not floor.candidate:raise ValueError('Source motion terrain: '+floor.reason)
    placed=check_source_static_floor(floor,footprint,sources,static)
    if not placed.candidate:raise ValueError('Source motion static: '+placed.reason)
    old_bsp=check_source_body_bsp(floor,footprint,sources,bsp,clip_branches=True)
    if not old_bsp.candidate and old_bsp.reason!='missing_bsp_child':
        raise ValueError('Source motion BSP: '+old_bsp.reason)
    native=classify_source_body_regions(floor,footprint,sources,static,classifier,
        source_wld_sha256=terrain.wld_sha256)
    _zero_native(native)
    check()
    return CheckedSourceFootprint(fork,floor,placed,old_bsp,native)


@dataclass(frozen=True)
class SourceProbeEnvelope:
    """Conditional area evidence; cannot be staged by the movement sender."""
    branch: object
    payload: bytes
    sha256: str
    current_position_verified: bool = field(default=False,init=False)
    current_motion_verified: bool = field(default=False,init=False)
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)

    def record(self):
        import json
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Source probe evidence changed')
        value=json.loads(self.payload)
        if encoded(value)!=self.payload:raise ValueError('Source probe evidence is not canonical')
        return value


def check_source_probe(prefix, reference, *, probe_kind, bounds, terrain, static,
                       bsp, region_policy, check_context, clock=time.monotonic,
                       maximum_seconds=30.):
    """Check every possible heading on an existing source-floor branch.

    Reference Z must come from that exact branch, not a raw eye height or map
    label. This does not read the client. A future owner executor needs its own
    fresh stopped observations and live scope before any measurement pulse.
    """
    if (probe_kind not in ('forward','left','right') or not point(reference)
            or type(reference) is not tuple or type(bounds) is not RouteMotionBounds
            or not callable(check_context) or not callable(clock)
            or not finite(maximum_seconds) or not 0<maximum_seconds<=30):
        raise ValueError('Explicit source probe context and motion hypotheses required')
    bounds.validate_values(calibration_record_id=bounds.calibration_record_id,maximum_step_seconds=.2)
    if type(region_policy) is not NativeZeroRegionTrialPolicy:
        raise ValueError('Explicit source native-region policy required')
    state=_chain_snapshot(prefix)
    if bounds.body_height!=prefix.body_height or prefix.floor_at(reference[:2])[0]!=reference[2]:
        raise ValueError('Source probe reference differs from the retained floor')
    classifier=region_policy.classifier;policy_record=encoded(region_policy.record())
    storage=_source_storage(terrain,static)
    began=last=clock()
    def check():
        nonlocal last
        check_context()
        now=clock()
        region_policy.check_context(zone='crushbone',pins=(region_policy.mesh_sha256,
            terrain.archive_sha256,terrain.wld_sha256,static.inventory_sha256),bsp=bsp)
        if (not finite(now) or not finite(began) or not began<=last<=now<=began+maximum_seconds
                or _chain_snapshot(prefix)!=state or region_policy.classifier is not classifier
                or encoded(region_policy.record())!=policy_record
                or _source_storage(terrain,static)!=storage):
            raise ValueError('Source probe prefix changed or work budget expired')
        last=now
        return now
    check()
    travel=(bounds.forward_speed_upper_bound*bounds.maximum_actual_hold if probe_kind=='forward'
            else bounds.pivot_displacement_upper_bound)
    footprint=motion_footprint(reference[:2],0.,0.,position_error=bounds.position_error,
        heading_error_degrees=0.,post_release_drift=bounds.post_release_drift,
        extra_radius=bounds.body_radius+travel)
    checked=check_source_footprint(prefix,footprint,terrain=terrain,static=static,bsp=bsp,
                                   region_policy=region_policy)
    finished=check()
    payload=encoded(dict(format='eql-source-probe-envelope-v1',reference=reference,
        probe_kind=probe_kind,footprint=footprint,all_headings=True,heading=None,
        maximum_center_travel=travel,bounds=asdict(bounds),
        previous_floor_proof_sha256=prefix.previous.proof_sha256,
        terrain=asdict(checked.terrain),static=asdict(checked.static),bsp=asdict(checked.bsp),
        native=asdict(checked.native),policy=region_policy.record(),
        started=began,finished=finished,requires_fresh_start_pair=True,
        current_position_verified=False,motion_bounds_verified=False,independent_scene_verified=False,
        baked_mesh_coverage_claimed=False,input_authorized=False,real_client_accepted=False))
    return SourceProbeEnvelope(checked.branch,payload,sha256(payload).hexdigest())
