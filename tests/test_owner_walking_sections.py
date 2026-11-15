"""Whole retained owner journey; actual pipe receipts, synthetic world only."""
from dataclasses import replace
from hashlib import sha256
import time

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceWalkHint
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from test_owner_journey_runtime import h,start
from test_motion_collection import retained
from test_owner_source_travel import configure
from test_route_step_sender import after_down


def configure_sections(h,monkeypatch,*,destination='goblin-camp-stop',count=2,dense=False):
    a=configure(h,monkeypatch,destination_id=destination);p=a.planner
    waypoints=(200.,230.,240.) if count==2 else (200.,230.,260.,270.)
    if dense:
        # A full-size current section, rather than a single operation, exercises
        # the cost of guide checks inside the unchanged DOWN deadline.
        waypoints=tuple(200.+i*.25 for i in range(241))
    guide=replace(a.guide,goal=(400.,waypoints[-1]),operations=tuple(
        SourceWalkHint((400.,a),(400.,b)) for a,b in zip(waypoints,waypoints[1:])))
    assets=SourceDestinationAssets(p,guide,'Synthetic two-section destination',encoded(dict(synthetic=True,
        destination_id=destination,guide_sha256=sha256(encoded(guide.record())).hexdigest())),destination)
    prefix=SourceFloorChain(inventory_sha256=p.source.wld_sha256,seed_evidence_sha256='b'*64,
        seed_ids=((10,1),),body_height=6.)
    footprint=swept_square((400.,200.),(400.,200.),1.2)
    assert prefix.advance(footprint,p.source.source_faces_for_footprint(footprint)).candidate
    bounds=RouteMotionBounds('synthetic-section-reserve','synthetic-motion',.01,.15,.2,60.,.3,.1,10.,.2,1.2,6.)
    record=plan_walk_sections(prefix,guide,p,bounds=bounds,maximum_length=30.,minimum_length=20.,
        candidate_spacing=1.,check_context=lambda:None)
    sections=parse_walking_sections(guide,record);assert len(sections.guides)==count
    h.source_loading[0]=lambda:assets
    h.engine._test_walking_partition=lambda d:sections if d is assets else None
    import eql_automation.camp_probe_runtime as probes
    import eql_automation.camp_source_runtime as route
    old_probe=probes.send_camp_probe;old_route=route.run_checked_source_step
    def probe(*a,**kw):
        value=old_probe(*a,**kw);h.apply(value.seal.receipt.key_code,value.seal.receipt);return value
    def step(*a,**kw):
        value=old_route(*a,**kw);h.apply(value.receipt.key_code,value.receipt);return value
    monkeypatch.setattr(probes,'send_camp_probe',probe);monkeypatch.setattr(route,'run_checked_source_step',step)
    def reply():
        c=h.engine.section_run
        if c is not None and c.current_input_key()==62:
            h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,reply)
    return sections


def finish_sections(h,timeout=240.):
    deadline=time.monotonic()+timeout;e=h.engine
    while time.monotonic()<deadline:
        h.tick();h.drain()
        if not e._navigation_busy():return e.journey_last_result
        time.sleep(.01)
    raise AssertionError(('Owner sections timed out',e.autopilot_payload(),h.notices[-5:]))


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
def test_owner_travel_automatically_measures_and_walks_next_section_without_camp(h,monkeypatch):
    sections=configure_sections(h,monkeypatch,count=3);e=h.engine;seen=[]
    advance=e._advance_walking_section
    def capture(w,arrival):
        seen.append((w,w.index,arrival,w.budget.expires_at,e.section_run))
        return advance(w,arrival)
    monkeypatch.setattr(e,'_advance_walking_section',capture)
    start(h,'goblin-camp-stop');h.due_trial();result=finish_sections(h)
    assert result and result['phase']=='arrived','\n'.join(map(str,h.notices))+'\n'+str(result)
    assert len(seen)==3 and [r[1] for r in seen]==[0,1,2]
    w=seen[0][0];c=seen[-1][4]
    assert all(r[0] is w and r[3]==seen[0][3] for r in seen)
    middle=seen[1][4]
    assert middle.closed and middle.monitor.closed and not middle.monitor.floor.valid
    assert seen[0][2].runtime.policy.journey_budget is c.budget is w.budget
    assert c.owner_input is w.observer and c.sender is h.sender and c.veto is w.veto
    assert c.reader is w.reader and c.lease._tracker is w.tracker
    assert len(c.runtime.results)==7 and c.route_runtime.ledger.steps>0
    assert c.completed_arrival is seen[-1][2] and c.closed
    assert not e.journey and e.section_run is None and e.camp_session is None
    assert not h.sender.held and h.observer_closed and w.tracker.lease is None
    assert not h.commands and not result['real_client_accepted']
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
def test_full_size_walking_sections_reach_destination_with_unchanged_permit(h,monkeypatch):
    sections=configure_sections(h,monkeypatch,dense=True)
    assert all(len(g.operations)==120 for g in sections.guides)
    start(h,'goblin-camp-stop');h.due_trial();result=finish_sections(h)
    assert result and result['phase']=='arrived','\n'.join(map(str,h.notices))+'\n'+str(result)
    assert h.engine.section_run is None and not h.sender.held and h.observer_closed


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
@pytest.mark.parametrize('phase,action',(('probe','stop'),('route','stop'),('probe','arm')))
def test_owner_stop_and_assist_during_section_down_release_every_key(h,monkeypatch,phase,action):
    configure_sections(h,monkeypatch);e=h.engine;seen=[]
    e.prepared=True;e.prepared_level=7
    def stop():
        c=e.section_run
        if not seen and c is not None and c.phase==phase and c.current_input_key() in (103,105,106):
            seen.append(c)
            if action=='arm':e.handle_job('arm',e.cancel_generation)
            else:e.stop_action('F9 during next section DOWN')
    after_down(monkeypatch,stop)
    start(h,'goblin-camp-stop');h.due_trial();finish_sections(h)
    assert seen,'\n'.join(map(str,h.notices))
    c=seen[0];assert c.closed and not c.budget.valid and c.monitor.closed
    assert e.journey is None and e.section_run is None and not h.sender.held and h.observer_closed
    assert e.live_zone_tracker.lease is None and e.camp_session is None
    h.tick();h.drain();assert e.active is (action=='arm')
    assert not h.commands


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
@pytest.mark.parametrize('fault',('F8','refused_after_release'))
def test_final_section_release_gap_preserves_owner_assist_and_discards_checkpoint(h,monkeypatch,fault):
    configure_sections(h,monkeypatch);e=h.engine;seen=[]
    e.prepared=True;e.prepared_level=7
    original=e._check_section_arrival
    def check(w,arrival):
        if (not seen and w.index==1 and e.section_run is None
                and arrival.runtime.probe.closed):
            seen.append(arrival)
            if fault=='F8':e.handle_job('arm',e.cancel_generation)
            else:raise ValueError('Synthetic refusal after completed section release')
        return original(w,arrival)
    monkeypatch.setattr(e,'_check_section_arrival',check)
    start(h,'goblin-camp-stop');h.due_trial();finish_sections(h)
    assert seen,'\n'.join(map(str,h.notices))
    assert not seen[0].checkpoint.valid and not seen[0].budget.valid
    assert not h.sender.held and h.observer_closed and e.live_zone_tracker.lease is None
    assert e.journey is None and e.section_run is None and e.camp_session is None
    h.tick();h.drain();assert e.active is (fault=='F8')


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
def test_only_final_section_starts_camp_and_transfers_original_input_observer(h,monkeypatch):
    configure_sections(h,monkeypatch,destination='goblin-camp');e=h.engine;seen=[]
    original=e._advance_walking_section
    def capture(w,arrival):
        assert e.camp_session is None
        seen.append((w,arrival,e.section_run))
        return original(w,arrival)
    monkeypatch.setattr(e,'_advance_walking_section',capture)
    start(h,'goblin-camp');h.due_trial();result=finish_sections(h)
    assert result and result.get('camp_started'),'\n'.join(map(str,h.notices))+'\n'+str(result)
    assert len(seen)==2 and e.journey.phase=='camp' and e.section_run is None
    w,arrival,c=seen[-1]
    assert c.closed and c.monitor.closed and not c.monitor.floor.valid
    assert e.journey.arrival_floor is arrival.checkpoint and arrival.checkpoint.valid
    assert e.journey.camp_motion.observer is w.observer and not h.observer_closed
    assert not w.budget.valid and e.live_zone_tracker.lease is None
    e.stop_action('F9 after final camp');assert h.observer_closed and not arrival.checkpoint.valid


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
@pytest.mark.parametrize('at',('lease_acquired','successor_constructed','final_camp'))
def test_partition_callbacks_cannot_publish_mutated_future_sections_or_camp(h,monkeypatch,at):
    sections=configure_sections(h,monkeypatch,destination='goblin-camp',count=3)
    e=h.engine;seen=[];constructed=[]
    def mutate():
        if not seen:
            seen.append(True)
            object.__setattr__(sections.guides[-1].operations[-1],'end',(999.,999.))
    import eql_automation.owner_walking_sections as module
    constructor=module.SectionContinuation
    def create(*a,**kw):
        c=constructor(*a,**kw);constructed.append(c)
        if at=='successor_constructed':mutate()
        return c
    monkeypatch.setattr(module,'SectionContinuation',create)
    tracker=e.live_zone_tracker;acquire=tracker.acquire
    def lease():
        result=acquire()
        w=None if e.journey is None else e.journey.walking
        if at=='lease_acquired' and w is not None and w.index==1:mutate()
        return result
    monkeypatch.setattr(tracker,'acquire',lease)
    continuation=e._continue_source_journey
    def camp(*a,**kw):
        result=continuation(*a,**kw)
        if at=='final_camp':mutate()
        return result
    monkeypatch.setattr(e,'_continue_source_journey',camp)
    start(h,'goblin-camp');h.due_trial();finish_sections(h)
    assert seen,'\n'.join(map(str,h.notices))
    assert e.journey is None and e.section_run is None and e.camp_session is None
    assert not h.sender.held and h.observer_closed and tracker.lease is None
    assert not h.commands
    if at=='lease_acquired':assert not constructed
    elif at=='successor_constructed':
        assert len(constructed)==1 and constructed[0].runtime is None
        assert constructed[0].closed and constructed[0].monitor.closed


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
@pytest.mark.parametrize('phase',('probe','route'))
def test_section_policy_still_observes_manual_activity_during_down(h,monkeypatch,phase):
    configure_sections(h,monkeypatch);e=h.engine;seen=[]
    def disturb():
        c=e.section_run
        if not seen and c is not None and c.phase==phase and c.current_input_key() in (103,105,106):
            seen.append(c);sample=c.owner_input.sample
            monkeypatch.setattr(c.owner_input,'sample',lambda:replace(sample(),activity=True))
    after_down(monkeypatch,disturb)
    start(h,'goblin-camp-stop');h.due_trial();finish_sections(h)
    assert seen,'\n'.join(map(str,h.notices))
    c=seen[0]
    assert c.closed and c.monitor.closed and not c.budget.valid
    assert e.journey is None and e.section_run is None and e.camp_session is None
    assert not h.sender.held and h.observer_closed and e.live_zone_tracker.lease is None


@pytest.mark.parametrize('h',['walking_sections'],indirect=True)
@pytest.mark.parametrize('phase',('probe','route'))
@pytest.mark.parametrize('fault',('focus','attack'))
def test_child_location_key_refreshes_full_scene_after_outer_tick(h,monkeypatch,phase,fault):
    configure_sections(h,monkeypatch);e=h.engine;seen=[]
    import eql_automation.camp_probe_runtime as probe
    import eql_automation.camp_source_runtime as route
    module=probe if phase=='probe' else route
    send=module.send_location_hotkey
    def guarded(*a,**kw):
        c=e.section_run
        if not seen and c is not None and c.phase==phase:
            h.drain();seen.append(len(h.events))
            if fault=='focus':
                session=e.gate.game_session
                monkeypatch.setattr(e.gate,'game_session',lambda:dict(session(),pid=999))
            else:h.append('a decaying skeleton hits YOU for 1 point of damage.')
        return send(*a,**kw)
    monkeypatch.setattr(module,'send_location_hotkey',guarded)
    start(h,'goblin-camp-stop');h.due_trial();finish_sections(h)
    assert seen,'\n'.join(map(str,h.notices))
    h.drain();assert all(not (kind==1 and value==1) for kind,_,value in h.events[seen[0]:])
    assert e.journey is None and e.section_run is None and not h.sender.held
    assert h.observer_closed and e.live_zone_tracker.lease is None
