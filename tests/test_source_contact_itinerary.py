"""Mixed terminal contact planning and real retained pipes; synthetic game."""
from dataclasses import replace
import time

import pytest

from eql_automation.camp_contact_checkpoint import CampContactCheckpoint
from eql_automation.source_contact_controller import SourceContactArrival,SourceContactController
from eql_automation.source_contact_hint import SourceContactHint
from eql_automation.source_guide_compaction import compact_source_guide
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from eql_automation.source_walk_driver import SourceContactBoundary,SourceWalkDriver
from test_source_motion import f,legacy
from test_owner_source_runtime import setup,finish


def simulated_transport(f,r,state,feedback,monkeypatch):
    """Virtual-time receipts/logs for composition; deliberately no pipe writes.

    The real-time sender/cancellation tests above remain separate. This fixture
    exercises the unchanged ledger, geometry, reader and complete execution loop.
    """
    from eql_automation.motion_collection import CommandReceipt
    from eql_automation.uinput_watchdog import PulseReceipt
    f.now=f.clock();f.real=False;positions=iter(feedback)
    def movement(action):
        ledger=r.active
        ticket=ledger.stage(ledger.prepare(action.kind),requested_seconds=action.requested_seconds)
        at=ticket.proposed_at
        receipt=PulseReceipt(ticket.movement_key,ticket.requested_seconds,
            at+.001,at+.002,at+.04,at+.041,'elapsed')
        f.now=at+.042
        seal=ledger.seal_release(ticket,receipt)
        state.y,state.z=next(positions);state.pulses+=1
        return seal
    def location(request):
        r.check_current();at=f.now;f.now+=.002
        f.append(f'Your Location is {state.y}, 4, {state.z}')
        return CommandReceipt(at,f.now)
    monkeypatch.setattr(r,'_send_movement',movement)
    monkeypatch.setattr(r,'_request_location',location)


def simulated_finish(f,r,*,until=None):
    for _ in range(10000):
        r.tick()
        if r.phase=='complete' or until is not None and until():return
        f.now+=.01
    raise AssertionError(r.snapshot())


def guide(contact):
    return SourceItineraryGuide('crushbone','a'*64,'b'*64,'c'*64,.1,6.,contact.end,(contact,))


def test_long_contact_keeps_bends_and_roundtrips_without_becoming_walks():
    contact=SourceContactHint(((0.,0.),(40.,0.),(40.,40.),(80.,40.),(100.,100.)),((20,0),(20,1)),.2)
    g=guide(contact)
    assert SourceItineraryGuide.from_record(g.record())==g
    assert compact_source_guide(g).operations==(contact,)
    assert compact_source_guide(g).operations[0] is contact


@pytest.mark.parametrize('fault',['empty','long_leg','after','goal','radius','gap'])
def test_contact_cannot_hide_an_unbounded_leg_or_ordinary_suffix(fault):
    contact=SourceContactHint(((0.,0.),(2.,0.)),((20,0),(20,1)),.2);g=guide(contact)
    if fault=='empty':g=replace(g,operations=(replace(contact,waypoints=()),))
    elif fault=='long_leg':g=guide(replace(contact,waypoints=((0.,0.),(100.,0.))))
    elif fault=='after':g=replace(g,operations=(contact,SourceWalkHint(contact.end,(3.,0.))))
    elif fault=='goal':g=replace(g,goal=(3.,0.))
    elif fault=='radius':g=replace(g,radius=.3)
    else:g=replace(g,operations=(SourceWalkHint((-2.,0.),(-1.,0.)),contact))
    with pytest.raises(ValueError):g.validate()


@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_plan_finishes_as_contact_without_ordinary_goal_floor(f):
    data=f.plan.itinerary.record();row=data['cells'][-1]
    assert row['kind']=='contact' and row['end']==data['goal']==[4.,3.8]
    assert not data['ordinary_goal_floor_available']
    assert data['goal_floor_height'] is None and data['final_proof_sha256'] is None
    assert data['goal_source_ids']==[]
    assert row['reference_floor_height']==.2 and not row['ordinary_goal_floor_available']
    assert data['terminal_contact_plan_sha256']==row['contact_plan_sha256']
    assert not any(v['origin']=='exact_destination_cap' for v in data['cells'])
    driver=SourceWalkDriver(f.ledger);boundary=driver.next_action()
    assert type(boundary) is SourceContactBoundary and boundary.start[:2]==(4.,2.)
    assert boundary.planned_start[:2]==(4.,2.4)
    hint=driver.contact_hint(boundary)
    assert hint.waypoints==((4.,2.),(4.,2.4),(4.,3.8))
    assert f.ledger.reference.package_xyz==(4.,2.,.2) and f.ledger.steps==0


@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_runtime_travels_to_contact_and_stops_with_distinct_actual_arrival(f,tmp_path,monkeypatch):
    r,e,state=setup(f,tmp_path,monkeypatch,scope='destination_travel',
        feedback=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79)))
    ordinary=f.ledger._state();r.tick()
    assert r.phase=='contact_start' and state.pulses==0 and r.seal is None
    assert r.contact_preflight.hint.waypoints==((4.,2.),(4.,2.4),(4.,3.8))
    finish(f,r)
    assert type(r.completed_arrival) is SourceContactArrival
    assert type(r.transfer) is SourceContactController and r.transfer.phase=='arrived'
    assert r.collector is None and r.seal is None and r.contact_preflight is None
    assert r.completed_arrival.second.package_xyz[1]==3.6 and r.ledger.reference.package_xyz[1]==2.
    assert f.ledger.pose.y==2. and f.ledger.steps==0
    assert state.pulses==4 and r.policy.ledger is r.transfer
    assert [v['outcome'] for v in r.events if v['kind']=='source_acknowledgment']==['in_contact']*3+['arrived']
    checkpoint=CampContactCheckpoint(r.transfer,r.completed_arrival)
    assert checkpoint._reference is r.completed_arrival.second
    before=len(f.drain_events());r.tick();assert len(f.drain_events())==before
    assert not f.sender.held and f.sender._eql_route_operation is None


@pytest.mark.parametrize('stop',['movement','location'])
@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_contact_runtime_stop_during_down_releases_without_arrival(f,tmp_path,monkeypatch,stop):
    r,e,state=setup(f,tmp_path,monkeypatch,stop=stop)
    with pytest.raises((ValueError,RuntimeError)):finish(f,r)
    assert r.phase=='stopped' and state.stopped and r.completed_arrival is None
    assert not f.sender.held and f.sender._eql_route_operation is None
    assert f.ledger.reference.package_xyz[1]==2. and f.ledger.steps==0


@pytest.mark.parametrize('fault',['boundary','hint','cursor','connector'])
@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_contact_preflight_cannot_continue_after_driver_boundary_changes(f,tmp_path,monkeypatch,fault):
    r,e,_=setup(f,tmp_path,monkeypatch);r.tick();before=len(f.drain_events())
    if fault=='boundary':r.driver._boundary=replace(r.contact_boundary)
    elif fault=='hint':object.__setattr__(r.driver._contacts[r.contact_boundary.cell_index],'face_ids',((20,0),))
    elif fault=='cursor':r.driver.index+=1
    else:r.driver._stair_connector=r.driver.targets[0]
    with pytest.raises((ValueError,RuntimeError)):r.tick()
    assert len(f.drain_events())==before and not f.sender.held and r.completed_arrival is None


@pytest.mark.parametrize('f',['stair_contact_route'],indirect=True)
def test_contact_rebuild_includes_the_actual_stair_landing_and_pending_connector(f,tmp_path,monkeypatch):
    feedback=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.7),(3.98,3.2),
        (4.38,3.7),(4.78,3.7),(5.18,3.7),(5.58,3.7),(5.98,4.2),
        (6.38,4.7),(6.78,4.7),(7.18,4.7),(7.58,4.7),(7.98,5.2),
        (8.38,5.7),(8.78,5.7),(9.18,5.7),(9.58,5.7),(9.98,5.7),
        (10.38,5.7),(10.78,5.7),(11.18,5.7),(11.58,5.7),(11.98,5.7),
        (12.38,5.7),(12.78,5.7),(13.18,5.79),(13.58,5.79),(13.98,5.79),(14.38,5.79),(14.78,5.79))
    r,e,state=setup(f,tmp_path,monkeypatch,scope='destination_travel',feedback=feedback)
    simulated_transport(f,r,state,feedback,monkeypatch)
    simulated_finish(f,r,until=lambda:r.phase=='contact_start')
    assert r.driver._stair_connector is not None
    start=r.contact_boundary.start[:2]
    assert start[1]<10. and r.contact_preflight.hint.waypoints==(start,(4.,10.),(4.,15.))
    original=f.ledger._state();reference=f.ledger.reference
    simulated_finish(f,r)
    assert type(r.completed_arrival) is SourceContactArrival and state.pulses==len(feedback)
    assert f.ledger._state()!=original  # Start refresh changes only the ordinary reference.
    assert f.ledger.chain.previous.proof_sha256==reference.floor_proof_sha256
    assert f.ledger.reference.package_xyz==reference.package_xyz
    assert r.completed_arrival.second.package_xyz[1]==14.78
    assert r.snapshot()['completed_movements']==state.pulses and r.snapshot()['partial_movements']==0
    assert any(v['kind']=='source_stair_start' for v in r.events)
    assert any(v['kind']=='source_contact_start' for v in r.events)
    assert not f.sender.held and not f.drain_events()


@pytest.mark.parametrize('where',['completion','handoff'])
@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_final_arrival_callback_cannot_replace_the_itinerary_boundary(f,tmp_path,monkeypatch,where):
    from eql_automation.source_arrival import validate_contact_completion
    feedback=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79))
    r,_,state=setup(f,tmp_path,monkeypatch,scope='destination_travel',feedback=feedback)
    simulated_transport(f,r,state,feedback,monkeypatch)
    validate=SourceContactController.validate_arrival;fired=[]
    def changed(controller,arrival):
        result=validate(controller,arrival)
        if not fired:
            fired.append(True);r.driver.index+=1
        return result
    if where=='handoff':simulated_finish(f,r)
    monkeypatch.setattr(SourceContactController,'validate_arrival',changed)
    with pytest.raises(ValueError,match='boundary changed'):
        if where=='completion':simulated_finish(f,r)
        else:validate_contact_completion(r)
    assert fired and not f.drain_events()
    if where=='completion':assert r.completed_arrival is None and r.phase=='stopped'


@pytest.mark.parametrize('f',['contact_route'],indirect=True)
def test_contact_handoff_keeps_first_sample_deadline_even_with_fresh_second(f,tmp_path,monkeypatch):
    from eql_automation.source_arrival import assert_retained_arrival
    feedback=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79))
    r,_,state=setup(f,tmp_path,monkeypatch,scope='destination_travel',feedback=feedback)
    simulated_transport(f,r,state,feedback,monkeypatch)
    simulated_finish(f,r,until=lambda:state.pulses==4 and r.collector.first is not None)
    f.now=r.collector.first.received_monotonic+2.44
    simulated_finish(f,r)
    receipt=r.completed_arrival;checkpoint=CampContactCheckpoint(r.transfer,receipt)
    assert receipt.expires_at==receipt.first.raw_fix.received_monotonic+2.5
    assert_retained_arrival(r,receipt,checkpoint,f.now)
    f.now=receipt.expires_at+.001
    assert f.now-receipt.second.raw_fix.received_monotonic<.5
    with pytest.raises(ValueError,match='original stopped-pair deadline'):
        assert_retained_arrival(r,receipt,checkpoint,f.now)
