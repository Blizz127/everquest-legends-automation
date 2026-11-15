"""Final actual camp-section receipt into a fresh stationary camp.

Retired child callbacks are never revived. This token checks the preserved
receipt and owner identities while the existing camp-start stop adopts exactly
one new generation. Intermediate sections cannot enter this function.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

from .camp_motion_continuity import CampInputContinuity
from .native_region_policy import encoded
from .owner_camp_arrival import CampDestination
from .owner_navigation_preflight import settings_identity,window_identity
from .owner_route_trial import zone_binding
from .source_arrival import assert_retained_arrival,arrival_reference,arrival_itinerary
from .source_destinations import destination_spec


@dataclass(frozen=True)
class CampSectionArrival:
    trip: object
    arrival: object
    monitor: CampInputContinuity
    destination: CampDestination
    candidates: tuple


def check_camp_section_handoff(e,token,clock,*,new_camp=None):
    w=token.trip;j=w.journey;a=token.arrival;m=token.monitor
    w.check();w.sections.check();w.tracker.poll()
    m.check_binding(m.binding);a.checkpoint.check()
    veto=w.veto.poll();window=window_identity(e.gate,require_focus=True)
    sample=m.observer.sample();now=clock()
    m.check_binding(m.binding)
    assert_retained_arrival(a.runtime,a.receipt,a.checkpoint,now)
    if (e.journey is not j or j.phase!='handoff' or w.stage!='finished'
            or e.camp_walking is not None or e.camp_section_run is not None
            or e.camp_position is not None or e._navigation_busy() or not e.jobs.empty()
            or e.cancel_generation!=j.generation or j.generation not in (w.generation,w.generation+1)
            or j.settings!=w.settings or settings_identity(e.settings)!=w.settings
            or j.continue_camps is not True or j._continue_camps is not True
            or j.destination_assets is not token.destination
            or j.destination_id!=w.destination_id or j.candidates is not token.candidates
            or j.arrival_floor is not a.checkpoint or j.camp_motion is not m
            or j.location_binding is not w.hotkey or w.pending.cancelled
            or e.camp_session is not new_camp or e.autopilot is not new_camp
            or new_camp is not None and j.generation!=w.generation+1
            or w.camp.running or not w.pending.runtime.closed or w.pending.lease.active
            or e.stopping or e.active or e.target_ready or e.preparing
            or e.sender is not w.sender or e.sender.ui is not w.ui or e.gate is not w.gate
            or w.sender.held or w.sender.unfinished or w.sender.dismissed
            or getattr(w.sender,'_eql_route_operation',None) is not None
            or e.live_zone_tracker is not w.tracker or w.tracker.reader is not w.reader
            or w.tracker.lease is not None or a.runtime.lease.active
            or zone_binding(w.reader)!=w.zone or window!=w.window
            or a._claim!=[True] or getattr(a.runtime,'_section_arrival',None) is not a
            or a.budget is not w.budget or w.budget.valid
            or not sample.clear_at(now) or sample.topology_generation!=m.topology
            or m.last_observed_at is not None and sample.started_at<m.last_observed_at
            or not veto.continuity_available or veto.reason is not None):
        raise ValueError('Final camp section lost its fresh receipt or released owner scope')
    m.last_observed_at=sample.finished_at;m.samples+=1


def finish_camp_sections(e,w,arrival,clock):
    e._check_camp_section_arrival(w,arrival)
    if (w.index!=len(w.sections.guides)-1 or w.runtime is not None
            or e.camp_section_run is not None or w.tracker.lease is not None
            or arrival.runtime.lease.active or e.camp_session is not None):
        raise ValueError('Only the released final camp section can start a new camp')
    spec=destination_spec(w.destination_id)
    if spec.arrival_mode!='camp' or spec.zone_id!=w.zone[0]:
        raise ValueError('Current same-zone camp destination required')
    candidates=tuple(e._load_camp_candidates(spec.zone))
    if not candidates:raise ValueError('No observed search names at the final camp')
    e._check_camp_section_arrival(w,arrival)
    destination=CampDestination(w.destination_id,encoded(dict(destination_id=w.destination_id,
        label=spec.label,guide_sha256=sha256(encoded(w.sections.original.record())).hexdigest(),
        section_manifest_sha256=w.sections.record_sha256,
        selection=json.loads(w.plan.destination_evidence),real_client_accepted=False)))
    token=CampSectionArrival(w,arrival,w.monitor,destination,candidates)
    j=w.journey
    arrival._claim[0]=True
    w.budget.cancel('Final camp section reached; original navigation budget retired')
    w.set_stage('finished');e.camp_walking=None
    j.phase='handoff';j.settings=w.settings;j.destination_id=w.destination_id;j.destination_assets=destination
    j.arrival_floor=arrival.checkpoint;j.candidates=candidates
    check=lambda:check_camp_section_handoff(e,token,clock)
    check();e.zone=spec.zone
    started=e.start_stationary_camp(arrival_check=check)
    if e.journey is not j:return dict(camp_started=False,reason='Owner changed the handoff')
    if not started or e.camp_session is None:
        e.stop_action('Next camp reached; fresh camp did not start')
        return dict(camp_started=False)
    new_camp=e.camp_session
    check_camp_section_handoff(e,token,clock,new_camp=new_camp)
    j.phase='camp';binding=e._camp_motion_binding()
    successor=CampInputContinuity(w.monitor.observer,topology=w.monitor.topology,
        basis=arrival.motion_basis,binding=binding,clock=clock,floor=arrival.checkpoint)
    successor.last_observed_at=w.monitor.last_observed_at
    successor.check(binding)
    if (e.journey is not j or e.camp_session is not new_camp or j.camp_motion is not w.monitor
            or e.cancel_generation!=j.generation or j.generation!=w.generation+1):
        raise ValueError('Owner changed final camp input transfer')
    w.monitor.transfer_to(successor);j.camp_motion=successor
    j.height_check_done=False;j.last_considered_level_advance=None
    if not e._camp_current() or e.journey is not j:
        raise ValueError('Final camp input continuity changed')
    new_camp.progress.bind_arrival(destination_id=spec.identifier,name=spec.label,zone=spec.zone,
        itinerary_sha256=arrival_itinerary(arrival.receipt),
        stopped_log_seq=arrival_reference(arrival.receipt).raw_fix.log_line_seq)
    result=dict(phase='camp',destination_id=spec.identifier,destination=json.loads(destination.source_evidence),
        itinerary_sha256=arrival_itinerary(arrival.receipt),
        stopped_log_seq=arrival_reference(arrival.receipt).raw_fix.log_line_seq,
        camp_started=True,fresh_preparation_due=new_camp.preparation_due,
        section_count=len(w.sections.guides),budget=w.budget.snapshot(),
        safe_camp_verified=False,real_client_accepted=False,
        camp_input_continuity=successor.snapshot(include_basis=True))
    e.journey_last_result=result;e.trace('journey_next_camp_handoff',**result)
    if e.journey is not j or e.camp_session is not new_camp or e.cancel_generation!=j.generation:
        return dict(result,camp_started=False,reason='Owner changed the completed handoff')
    return result
