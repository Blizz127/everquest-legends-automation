"""Transfer a completed, stopped same-zone route into a fresh camp session.

The token exists only in memory. Cleanup releases navigation before camp setup;
it cannot renew a location timestamp or resume the camp left behind.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

from .camp_motion_continuity import CampInputContinuity,camp_route_motion_basis
from .camp_source_runtime import CampSourceRuntime
from .source_destinations import destination_spec
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity,window_identity
from .owner_route_trial import zone_binding
from .source_walk_driver import SourceWalkFinished
from .source_contact_controller import SourceContactArrival
from .source_arrival import arrival_reference,arrival_itinerary,validate_contact_completion,assert_retained_arrival


@dataclass(frozen=True)
class CampDestination:
    destination_id: str
    source_evidence: bytes


@dataclass(frozen=True)
class CampArrival:
    pending: object
    runtime: CampSourceRuntime
    receipt: object
    checkpoint: object
    destination: CampDestination
    basis: bytes
    settings: tuple
    zone: tuple
    candidates: tuple


def capture_camp_arrival(engine,p,checkpoint):
    e=engine;r=p.route_runtime;j=p.journey
    e._camp_position_current(p)
    if type(r) is not CampSourceRuntime or r.phase!='complete':
        raise ValueError('Actual completed camp source runtime required')
    r.check_current();receipt=r.completed_arrival
    contact=type(receipt) is SourceContactArrival
    if contact:validate_contact_completion(r)
    final=receipt if contact else r.driver.next_action()
    if ((not contact and (type(receipt) is not SourceWalkFinished or type(final) is not SourceWalkFinished
            or final.reference is not receipt.reference or receipt.reference is not r.ledger.reference
            or receipt.itinerary_sha256!=r.driver.plan.sha256
            or r.transfer is not None)) or r.collector is not None or r.seal is not None
            or r.busy or p.sender.held or p.sender.unfinished
            or getattr(p.sender,'_eql_route_operation',None) is not None
            or checkpoint._reference is not arrival_reference(receipt) or checkpoint._reader is not p.reader
            or not j.continue_camps or j.continue_camps is not j._continue_camps):
        raise ValueError('New camp requires an unchanged stopped route and explicit continuation')
    plan=p.probe_plan;spec=destination_spec(plan.destination_id)
    calibration=p.probe_record['calibration'];seal=p.calibration_seal
    if (seal is None or calibration is not seal[0] or encoded(calibration)!=seal[1]
            or plan.route_guide is not p.runtime.route_guide or plan.state()!=p.probe_plan_state):
        raise ValueError('Camp destination or sealed movement fit changed')
    basis=camp_route_motion_basis(r,calibration,checkpoint)
    destination=CampDestination(spec.identifier,encoded(dict(destination_id=spec.identifier,
        label=spec.label,guide_sha256=sha256(encoded(plan.route_guide.record())).hexdigest(),
        selection=json.loads(plan.destination_evidence),real_client_accepted=False)))
    # Candidate names are historical suggestions; fresh /consider is mandatory
    # in the new camp. Loading while the old scope still owns input is read-only.
    candidates=tuple(e._load_camp_candidates(spec.zone))
    if not candidates:raise ValueError('No observed NPC candidates for the newly reached camp')
    checkpoint.check();e._camp_position_current(p)
    now=r.clock()
    assert_retained_arrival(r,receipt,checkpoint,now)
    if (p.cancelled
            or e.journey is not j or e.cancel_generation!=p.generation
            or plan.state()!=p.probe_plan_state or r.plan.state()!=r.plan_state
            or p.calibration_seal is not seal or encoded(calibration)!=seal[1]):
        raise ValueError('Camp arrival changed during capture')
    token=CampArrival(p,r,receipt,checkpoint,destination,basis,p.settings,
        zone_binding(p.reader),candidates)
    if token.zone[0]!=spec.zone_id:raise ValueError('Current selected-zone arrival required')
    # Deliberate transition. The parent runtime is retired next, never rearmed.
    j.phase='handoff';j.settings=p.settings;j.destination_id=spec.identifier
    j.destination_assets=destination;j.arrival_floor=checkpoint;j.candidates=candidates
    return token


def check_camp_arrival(engine,token,clock,*,new_camp=None):
    e=engine;p=token.pending;j=p.journey;r=token.runtime
    p.tracker.poll()
    token.checkpoint.check()
    p.monitor.check_binding(p.monitor.binding)
    veto=p.probe_log_veto.poll()
    window=window_identity(e.gate,require_focus=True)
    sample=p.monitor.observer.sample();now=clock()
    p.monitor.check_binding(p.monitor.binding)
    assert_retained_arrival(r,token.receipt,token.checkpoint,now)
    if (e.journey is not j or j.phase!='handoff' or p.cancelled
            or j.generation!=e.cancel_generation or j.generation not in (p.generation,p.generation+1)
            or j.settings!=token.settings or settings_identity(e.settings)!=token.settings
            or j.continue_camps is not True or j._continue_camps is not True
            or j.destination_assets is not token.destination
            or j.destination_id!=token.destination.destination_id or j.candidates is not token.candidates
            or j.arrival_floor is not token.checkpoint or j.camp_motion is not p.monitor
            or j.location_binding is not p.hotkey or not token.checkpoint.valid
            or e.camp_position is not None or e._navigation_busy() or not e.jobs.empty()
            or e.stopping or e.active or e.target_ready or e.preparing
            or (e.camp_session is not p.camp and e.camp_session is not None
                if new_camp is None else e.camp_session is not new_camp)
            or e.sender is not p.sender or e.sender.ui is not p.ui or e.gate is not p.gate
            or p.sender.held or p.sender.unfinished or p.sender.dismissed
            or getattr(p.sender,'_eql_route_operation',None) is not None
            or window!=p.window or e.live_zone_tracker is not p.tracker
            or p.tracker.reader is not p.reader or p.tracker.lease is not None or p.lease.active
            or zone_binding(p.reader)!=token.zone or not p.runtime.closed
            or r is not p._route_runtime or r is not p.route_runtime
            or not sample.clear_at(now) or sample.topology_generation!=p.monitor.topology
            or p.monitor.last_observed_at is not None and sample.started_at<p.monitor.last_observed_at
            or not veto.continuity_available or veto.reason is not None):
        raise ValueError('New camp lost fresh arrival, released navigation or owner continuity')
    p.monitor.last_observed_at=sample.finished_at;p.monitor.samples+=1


def continue_camp_arrival(engine,token,clock):
    e=engine;p=token.pending;j=p.journey
    check=lambda:check_camp_arrival(e,token,clock)
    check()
    e.zone=destination_spec(token.destination.destination_id).zone
    started=e.start_stationary_camp(arrival_check=check,replacing_camp=p.camp)
    if e.journey is not j:return dict(camp_started=False,reason='Owner changed the handoff')
    if not started or e.camp_session is None:
        e.stop_action('Arrived at next camp; fresh camp did not start')
        return dict(camp_started=False)
    # start_stationary_camp may run trace callbacks after its final check.
    new_camp=e.camp_session
    check_camp_arrival(e,token,clock,new_camp=new_camp)
    if (p.cancelled or e.cancel_generation!=j.generation or j.phase!='handoff'
            or j.destination_assets is not token.destination or j.arrival_floor is not token.checkpoint
            or j.camp_motion is not p.monitor or e.sender.held or e.sender.unfinished):
        raise ValueError('New camp changed before input ownership transfer')
    j.phase='camp'
    binding=e._camp_motion_binding()
    successor=CampInputContinuity(p.monitor.observer,topology=p.monitor.topology,basis=token.basis,
        binding=binding,clock=clock,floor=token.checkpoint)
    successor.last_observed_at=p.monitor.last_observed_at
    if e.journey is not j or j.camp_motion is not p.monitor:
        raise ValueError('Owner cancelled new-camp input transfer')
    successor.check(binding)
    if e.journey is not j or j.camp_motion is not p.monitor or e.camp_session is not binding[5]:
        raise ValueError('Owner changed during new-camp input observation')
    p.monitor.transfer_to(successor);j.camp_motion=successor
    j.height_check_done=False;j.last_considered_level_advance=None
    if not e._camp_current() or e.journey is not j:
        raise ValueError('New camp input continuity changed')
    spec=destination_spec(token.destination.destination_id)
    new_camp.progress.bind_arrival(destination_id=spec.identifier,name=spec.label,
        zone=spec.zone,itinerary_sha256=arrival_itinerary(token.receipt),
        stopped_log_seq=arrival_reference(token.receipt).raw_fix.log_line_seq)
    result=dict(phase='camp',itinerary_sha256=arrival_itinerary(token.receipt),
        destination_id=token.destination.destination_id,destination=json.loads(token.destination.source_evidence),
        stopped_log_seq=arrival_reference(token.receipt).raw_fix.log_line_seq,camp_started=True,
        fresh_preparation_due=e.camp_session.preparation_due,safe_camp_verified=False,
        real_client_accepted=False,camp_input_continuity=successor.snapshot(include_basis=True))
    e.journey_last_result=result
    e.trace('journey_next_camp_handoff',**result)
    if (e.journey is not j or j.camp_motion is not successor
            or e.camp_session is not new_camp or e.cancel_generation!=j.generation):
        return dict(result,camp_started=False,reason='Owner changed the completed handoff')
    return result
