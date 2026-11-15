"""Owner-supervised continuation using copied guides and fresh camp probes.

Map ranges rank exploration destinations; they do not prove live suitability.
Arrival bounds remain explicitly historical planning assumptions. Steering is
constructed only from this retained scope's newly reduced seven probes.
"""
from dataclasses import asdict,replace
from hashlib import sha256
import json
from pathlib import Path

from .camp_annotations import read_camp_annotations
from .camp_probe_runtime import CampProbeRuntime
from .camp_session import CampLevelAdvance
from .camp_source_runtime import CampSourcePlan
from .crushbone_assets import DATA_PINS
from .source_destinations import DESTINATIONS,destination_spec,load_source_guide,source_data_name
from .g2_safety_provider import GameWindowIdentity
from .ground_binding import finite
from .motion_calibration import PROBES
from .native_region_policy import encoded
from .owner_camp_probe import CampProbePlan
from .owner_route_assets import checked_bytes
from .route_geometry import RouteMotionBounds
from .supervised_camp_probe import SupervisedCampProbeDeclaration,SupervisedCampProbeScope
from .supervised_route import SupervisedRouteDeclaration,scope_limits
from .supervised_source import SupervisedSourcePolicy


def choose_next_destination(root,current_id,level):
    """Choose only a packaged guide at the copied annotation's exact XY."""
    current=destination_spec(current_id)
    if type(level) is not int or not 1<=level<=50:raise ValueError('Current observed level required')
    if current.arrival_mode!='camp':return None
    map_name=current.zone+'_3.txt'
    pins=DATA_PINS
    if current.zone=='butcher':
        from .butcher_assets import DATA_PINS as pins
    elif current.zone=='gfaydark':
        from .gfay_assets import DATA_PINS as pins
    annotations=read_camp_annotations(checked_bytes(Path(root)/map_name,pins[map_name]))
    def annotation(spec):
        rows=[a for a in annotations if (-a.map_xyz[0],-a.map_xyz[1])==spec.goal]
        if len(rows)!=1:raise ValueError('Packaged guide has no unique copied map annotation')
        return rows[0]
    if annotation(current).hint_includes(level):return None
    eligible=[(spec,annotation(spec)) for spec in DESTINATIONS.values()
        if spec.zone==current.zone and spec.arrival_mode=='camp' and spec.identifier!=current_id and annotation(spec).hint_includes(level)]
    if not eligible:return None
    spec,hint=min(eligible,key=lambda pair:(-pair[1].level_hint[0],pair[0].identifier))
    return spec,encoded(dict(kind='copied_map_next_camp_hint',destination_id=spec.identifier,
        from_destination_id=current_id,observed_level=level,map_sha256=hint.map_sha256,
        map_label=hint.raw_label,level_hint=hint.level_hint,package_goal_xy=spec.goal,
        guide_file_sha256=spec.file_sha256,live_suitability_verified=False,
        label_z_used_for_floor=False,real_client_accepted=False))


def retained_probe_bounds(p):
    """Preserve the old envelope as assumptions, without reusing its heading."""
    monitor=p.monitor;floor=p.floor
    monitor.check_binding(monitor.binding);floor.check()
    if (monitor is not p.journey.camp_motion or monitor.floor is not floor
            or floor is not p.journey.arrival_floor or floor._reader is not p.reader):
        raise ValueError('Arrival basis lost its retained floor or reader')
    return arrival_probe_bounds(monitor,floor,p.result.sha256)


def arrival_probe_bounds(monitor,floor,height_sha256):
    """Shared camp/waypoint hypotheses; this does not reuse old steering."""
    monitor.check_binding(monitor.binding);floor.check()
    if monitor.floor is not floor:raise ValueError('Arrival monitor lost its reached floor')
    raw=monitor.basis;basis=json.loads(raw)
    if (encoded(basis)!=raw or sha256(raw).hexdigest()!=monitor.basis_sha256
            or basis.get('format')!='eql-camp-arrival-motion-v1'
            or any(basis.get(k) is not False for k in
                ('current_heading_verified','current_motion_verified','movement_authorized'))):
        raise ValueError('Canonical historical arrival basis required')
    historical=floor.snapshot(include_evidence=True)['evidence']
    for name in ('itinerary_sha256','floor_proof_sha256','arrival_position',
                 'arrival_log_seq','arrival_received_at'):
        if basis.get(name)!=historical[name]:raise ValueError('Arrival basis differs from retained floor: '+name)
    old=RouteMotionBounds(**basis['bounds'])
    old.validate_values(calibration_record_id=basis['calibration_record_id'],maximum_step_seconds=.2)
    if (old.maximum_requested_hold>.1 or old.maximum_actual_hold<.15
            or old.body_height!=floor._chain.body_height):
        raise ValueError('Arrival hypotheses do not support standard probe holds')
    bounds=replace(old,record_id='camp-probes-'+height_sha256,maximum_requested_hold=.15)
    provenance=encoded(dict(kind='retained_arrival_planning_hypotheses',
        arrival_basis_sha256=monitor.basis_sha256,arrival_floor_sha256=floor.sha256,
        original_bounds=asdict(old),probe_bounds=asdict(bounds),
        historical_assumption_id=old.calibration_record_id,
        current_motion_verified=False,motion_bounds_verified=False))
    return bounds,provenance


def checked_fresh_fit(p,runtime,calibration):
    """Check the producer's seal after planning, without renewing old fixes."""
    if type(runtime) is not CampProbeRuntime:raise ValueError('Exact retained probe runtime required')
    r=runtime;r._check()
    seal=p.calibration_seal
    if (type(r) is not CampProbeRuntime or r is not p.runtime or r.phase!='route_ready'
            or r.probes!=PROBES or r.index!=7 or len(r.transactions)!=7 or len(r.results)!=7
            or type(seal) is not tuple or len(seal)!=5
            or calibration is not seal[0] or encoded(calibration)!=seal[1]
            or r.reference is not seal[2]
            or tuple(map(id,r.transactions))!=tuple(map(id,seal[3]))
            or tuple(map(id,r.results))!=tuple(map(id,seal[4]))
            or r.root.checkpoint is not p.floor
            or r.reference is not r.transactions[-1]._continuation
            or r.route_preparation.checkpoint is not r.reference
            or calibration.get('status')!='conditional'):
        raise ValueError('Current sealed seven-probe calibration required')
    fit=calibration['estimate'];bounds=r.root.bounds
    evidence=fit['retained_evidence']
    if (fit.get('format')!='eql-conditional-camp-motion-estimate-v1'
            or fit['record_id']!='camp-'+r.results[-1].sha256
            or fit['source_floor_sha256']!=p.floor.sha256
            or fit['reached_floor_sha256']!=r.reference.sha256
            or fit['confirmed_at']!=r.results[-1].second.received_monotonic
            or len(evidence)!=7 or sha256(encoded(evidence)).hexdigest()!=fit['retained_evidence_sha256']
            or fit['horizontal_error_assumed']!=bounds.position_error
            or any(fit.get(k) is not False for k in
                ('input_authorized','real_client_accepted','live_calibration_verified','current_heading_verified'))
            or fit.get('verified_speed_upper_bound') is not None):
        raise ValueError('Fresh calibration provenance differs from the retained probes')
    for tx,result,row in zip(r.transactions,r.results,evidence):
        if (tx.phase!='continued' or tx.result is not result
                or row['preparation_sha256']!=tx.preparation.sha256
                or row['result_sha256']!=result.sha256
                or row['floor_sha256']!=tx._continuation.sha256):
            raise ValueError('Fresh calibration sequence differs from its result records')
    speed=fit['conditional_intervals']['speed'];estimate=fit['estimate']
    error=fit['forward_legs'][-1]['heading_error_degrees']
    if (len(speed)!=2 or not all(finite(v) for v in speed)
            or not 0<speed[0]<=estimate['run_speed']<=speed[1]<=bounds.forward_speed_upper_bound
            or not finite(error) or not 0<=error<=bounds.heading_error_degrees
            or not all(finite(estimate[k]) for k in ('run_speed','turn_rate','turn_latency','final_heading'))
            or estimate['turn_rate']<=0 or not 0<=estimate['turn_latency']<=.2
            or type(estimate['right_sign']) is not int or estimate['right_sign'] not in (-1,1)
            or not 0<=estimate['final_heading']<360):
        raise ValueError('Fresh fit exceeds the preserved camp planning envelope')
    # This is the new current pair. Seventh-probe confirmation is historical
    # evidence by now and must not be required to remain reader.latest.
    r.route_preparation.check_start(r.route_start);r._check()
    if (p.calibration_seal is not seal or encoded(calibration)!=seal[1]
            or r.reference is not seal[2] or r.root.checkpoint is not p.floor
            or tuple(map(id,r.transactions))!=tuple(map(id,seal[3]))
            or tuple(map(id,r.results))!=tuple(map(id,seal[4])) or r.phase!='route_ready'):
        raise ValueError('Calibration changed during route adoption')
    return fit


def owner_camp_probe_plan(engine,p,*,root=None):
    """Optional owner-started continuation; no implicit intent or movement."""
    e=engine;e._camp_position_current(p)
    if p.journey.continue_camps is not True:return None
    advance=p.level_advance;camp=p.camp
    if (type(advance) is not CampLevelAdvance or camp.last_level_advance is not advance
            or camp.level_source!='client_log' or advance.level!=camp.level
            or advance.level!=e.settings.level or advance.generation!=p.generation):
        e.trace('camp_continuation_wait',reason='current observed level increase required')
        return None
    root=(Path.home()/'.local/share/eql-automation/owner-route-data'/source_data_name(p.journey.destination_id)
          if root is None else Path(root))
    selected=choose_next_destination(root,p.journey.destination_id,camp.level)
    if selected is None:
        e.trace('camp_continuation_wait',reason='no new packaged map hint at this level',level=camp.level)
        return None
    spec,evidence=selected
    guide=load_source_guide(root,spec.identifier)
    sections=(e._load_camp_sections(spec.identifier,guide,root=root)
              if hasattr(e,'_load_camp_sections') else None)
    bounds,basis=retained_probe_bounds(p)
    if (guide.radius!=bounds.body_radius or guide.body_height!=bounds.body_height
            or guide.wld_sha256!=p.floor._terrain.wld_sha256
            or guide.static_inventory_sha256!=p.floor._static.inventory_sha256):
        raise ValueError('Next guide differs from retained camp source or dimensions')
    e._camp_position_current(p)
    scope=None;maximum_seconds=scope_limits('destination_travel')[0]
    def policy(tx):
        nonlocal scope
        e._camp_position_current(p)
        if scope is None:
            declaration=SupervisedCampProbeDeclaration(bounds.record_id,bounds.record_id,True,
                len(PROBES)*bounds.maximum_actual_hold)
            scope=SupervisedCampProbeScope(p.runtime,declaration=declaration,monitor=p.monitor,
                gate=p.gate,expected_window=GameWindowIdentity(*p.window),log_veto=p.probe_log_veto,
                check_current=lambda:e._camp_position_current(p),started_at=p.probe_started,
                expires_at=p.probe_started+maximum_seconds,
                journey_budget=None if sections is None else e._camp_sections_budget(p))
        return scope.policy(tx)
    def execution(runtime,calibration):
        from eqnav import steer
        e._camp_position_current(p)
        if scope is None or not scope.valid or scope.runtime is not runtime:
            raise ValueError('Original supervised probe scope must still be active')
        scope._check();fit=checked_fresh_fit(p,runtime,calibration)
        estimate=fit['estimate']
        onward=replace(bounds,record_id='camp-route-'+runtime.route_preparation.itinerary.sha256,
            maximum_requested_hold=.1)
        def source_policy(ledger,current):
            scope._check();current()
            seconds,steps,distance,hold=scope_limits('destination_travel')
            remaining=scope.expires_at-runtime.clock()
            if not 0<remaining<=maximum_seconds:raise ValueError('Original camp continuation deadline expired')
            declaration=SupervisedRouteDeclaration('camp-route-'+fit['record_id'],
                ledger.observer.itinerary.sha256,onward.calibration_record_id,onward.record_id,
                False,min(seconds,remaining),steps,distance,min(hold,remaining),'camp_continuation',True)
            return SupervisedSourcePolicy(ledger,declaration=declaration,gate=p.gate,
                owner_input=p.monitor.observer,log_veto=p.probe_log_veto,
                expected_window=GameWindowIdentity(*p.window),topology_generation=p.monitor.topology,
                check_current=current,
                journey_budget=None if sections is None else e._camp_sections_budget(p))
        result=CampSourcePlan(onward,steer,steer.Motion(run_speed=estimate['run_speed'],
            turn_rate=estimate['turn_rate'],right_sign=estimate['right_sign'],
            turn_latency=estimate['turn_latency'],back_speed=0.),estimate['final_heading'],.25,source_policy)
        e._camp_position_current(p);scope._check()
        return result
    result=CampProbePlan(bounds,basis,policy,PROBES,maximum_seconds,guide,execution,
        spec.identifier,evidence,sections)
    result.state();e._camp_position_current(p)
    e.trace('camp_continuation_selected',**json.loads(evidence),motion_bounds_verified=False)
    e._camp_position_current(p)
    return result
