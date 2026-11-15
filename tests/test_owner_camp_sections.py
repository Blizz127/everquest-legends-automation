"""Camp-origin sections use actual pipe receipts; the game/geometry is synthetic."""
from dataclasses import replace
import time

import pytest

import eql_automation.owner_camp_plan_provider as provider
from eql_automation.native_region_policy import encoded
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from test_owner_camp_plan_provider import install_historical_basis
from test_owner_camp_level_recheck import ding
from test_owner_camp_standard_route import standard_execution
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


def configure(h,monkeypatch,legacy,*,dense=False):
    e=h.engine;standard_execution(h,monkeypatch,legacy)
    bounds=install_historical_basis(h)
    ding(h,13);e.camp_session.preparation_due=False
    floor=e.journey.arrival_floor
    guide=SourceItineraryGuide('crushbone',floor._terrain.wld_sha256,
        floor._static.inventory_sha256,'f'*64,.1,6.,(4.,18.),
        (SourceWalkHint((4.,2.),(4.,10.)),SourceWalkHint((4.,10.),(4.,18.))))
    if dense:
        points=tuple((4.,2.+16.*i/1057) for i in range(1058))
        guide=replace(guide,operations=tuple(SourceWalkHint(a,b) for a,b in zip(points,points[1:])))
    planning=replace(bounds,maximum_requested_hold=.15,maximum_actual_hold=.2,
        forward_speed_upper_bound=.2,pivot_displacement_upper_bound=.001,post_release_drift=.001)
    from types import SimpleNamespace
    source=SimpleNamespace(source=floor._terrain,static=floor._static,bsp=floor._bsp,
                           region_policy=floor._policy)
    partition=plan_walk_sections(floor.fork(),guide,source,bounds=planning,
        maximum_length=8.1,minimum_length=7.,candidate_spacing=.2,check_context=lambda:None)
    sections=parse_walking_sections(guide,partition);assert len(sections.guides)==2
    monkeypatch.setattr(provider,'choose_next_destination',lambda *a:
        (provider.destination_spec('north-wall'),encoded({'kind':'synthetic-camp-destination'})))
    monkeypatch.setattr(provider,'load_source_guide',lambda *a:guide)
    e._test_camp_sections=lambda destination,actual:sections if actual is guide else None
    e._camp_probe_plan=lambda p:provider.owner_camp_probe_plan(e,p)
    def reply():
        child=e.camp_section_run
        if child is not None and child.current_input_key()==62:
            h.position_reply(x=round(h.game_x,2),y=round(h.game_y,2))
    after_down(monkeypatch,reply)
    return sections


def finish(h,timeout=210.):
    deadline=time.monotonic()+timeout;e=h.engine
    while time.monotonic()<deadline:
        h.tick();h.drain()
        if not e._navigation_busy():return e.journey_last_result
        time.sleep(.01)
    raise AssertionError(('Camp sections timed out',e.autopilot_payload(),h.notices[-8:]))


@pytest.mark.parametrize('h',['camp_sections'],indirect=True)
@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_camp_level_move_uses_one_budget_and_only_final_section_starts_camp(camp,monkeypatch,legacy):
    h=camp;e=h.engine;sections=configure(h,monkeypatch,legacy);seen=[];initial=[]
    begun=e._camp_probe_started;advance=e._advance_camp_section
    def begin(p):
        begun(p);initial.append(e.camp_walking)
        assert initial[-1].budget.snapshot()['reserved_pulses']==0
    def completed(w,arrival):
        seen.append((w,w.index,arrival,w.budget.expires_at,e.camp_section_run,len(h.receipts)))
        assert e.camp_session is None and not w.camp.running
        return advance(w,arrival)
    monkeypatch.setattr(e,'_camp_probe_started',begin);monkeypatch.setattr(e,'_advance_camp_section',completed)
    generation=e.cancel_generation;old=e.camp_session
    h.recovered();result=finish(h)
    assert result and result.get('camp_started'), '\n'.join(map(str,h.notices))+str(
        None if not result else {k:result.get(k) for k in ('phase','reason','camp_started')})
    assert [v[1] for v in seen]==[0,1] and len(initial)==1
    w=initial[0];child=seen[-1][4]
    assert all(v[0] is w and v[3]==seen[0][3] for v in seen)
    assert seen[0][2].runtime.policy.journey_budget is child.budget is w.budget
    assert len(w.pending.runtime.results)==len(child.runtime.results)==7
    assert w.budget.snapshot()['reserved_pulses']==len(h.receipts)>14
    assert e.camp_session is not old and not old.running and e.camp_session.preparation_due
    assert e.cancel_generation==generation+1 and e.journey.phase=='camp'
    assert e.camp_walking is None and e.camp_section_run is None and e.camp_position is None
    assert w.pending.monitor.closed and child.monitor.closed and not child.monitor.floor.valid
    assert e.journey.camp_motion.observer is w.observer and not h.observer_closed
    assert e.journey.arrival_floor is seen[-1][2].checkpoint and e.journey.arrival_floor.valid
    assert e.camp_session.progress.snapshot()['arrival_destination']['destination_id']=='north-wall'
    assert not e.sender.held and not h.commands and e.live_zone_tracker.lease is None
    assert not w.budget.valid and not result['real_client_accepted']


@pytest.mark.parametrize('h',['camp_sections'],indirect=True)
@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
@pytest.mark.parametrize('where,action',(('initial','stop'),('probe','stop'),('probe','arm')))
def test_stop_and_assist_release_camp_section_before_reader(camp,monkeypatch,legacy,where,action):
    h=camp;e=h.engine;configure(h,monkeypatch,legacy);seen=[]
    e.prepared=True;e.prepared_level=13
    def stop():
        w=e.camp_walking;c=e.camp_section_run;p=e.camp_position
        active=(p.runtime if where=='initial' and p is not None else
                c if c is not None and c.phase==where else None)
        if not seen and active is not None and active.current_input_key() in (103,105,106):
            seen.append((w,c))
            if action=='arm':e.handle_job('arm',e.cancel_generation)
            else:e.stop_action('F9 during camp section DOWN')
    after_down(monkeypatch,stop)
    h.recovered();finish(h)
    assert seen,'\n'.join(map(str,h.notices))
    w,c=seen[0]
    assert not w.budget.valid and e.journey is None and e.camp_session is None
    assert e.camp_walking is None and e.camp_section_run is None and e.camp_position is None
    assert not e.sender.held and e.live_zone_tracker.lease is None and h.observer_closed
    if c is not None:assert c.closed and c.monitor.closed
    h.tick();h.drain();assert e.active is (action=='arm')
    assert not h.commands


@pytest.mark.parametrize('h',['camp_sections'],indirect=True)
@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_f8_in_final_section_release_gap_keeps_assist_request(camp,monkeypatch,legacy):
    h=camp;e=h.engine;configure(h,monkeypatch,legacy);seen=[]
    e.prepared=True;e.prepared_level=13
    check=e._check_camp_section_arrival
    def stop_after_release(w,arrival):
        check(w,arrival)
        if w.index==len(w.sections.guides)-1 and not arrival.runtime.lease.active and not seen:
            seen.append((w,arrival))
            e.handle_job('arm',e.cancel_generation)
            raise ValueError('Owner selected assist after final reader release')
    monkeypatch.setattr(e,'_check_camp_section_arrival',stop_after_release)
    h.recovered();finish(h)
    assert seen,'\n'.join(map(str,h.notices))
    w,arrival=seen[0]
    assert not arrival.checkpoint.valid and not w.budget.valid
    assert e.journey is None and e.camp_section_run is None and e.camp_walking is None
    assert e.camp_session is None and e.live_zone_tracker.lease is None and not e.sender.held
    h.tick();h.drain();assert e.active and not h.commands


@pytest.mark.parametrize('h',['camp_sections'],indirect=True)
@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_full_size_camp_plan_keeps_original_down_deadline(camp,monkeypatch,legacy):
    h=camp;e=h.engine;sections=configure(h,monkeypatch,legacy,dense=True);seen=[]
    assert len(sections.original.operations)==1057
    def stop_after_admission():
        p=e.camp_position
        if not seen and p is not None and p.runtime is not None and p.runtime.current_input_key()==103:
            seen.append(e.camp_walking);e.stop_action('Stop after full-size first probe admission')
    after_down(monkeypatch,stop_after_admission)
    h.recovered();finish(h)
    assert seen,'\n'.join(map(str,h.notices))
    assert not seen[0].budget.valid and not e.sender.held and e.live_zone_tracker.lease is None
    assert e.journey is None and e.camp_walking is None and not h.commands
