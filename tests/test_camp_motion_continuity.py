"""Read-only fake device events plus actual retained camp/pipe lifecycle."""
import json
import time
from types import SimpleNamespace

import pytest

from eql_automation.camp_motion_continuity import CampInputContinuity, arrival_motion_basis
from eql_automation.navigation_phase import navigation_active
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_input_observer import OwnerInputObserver, DeviceIdentity
from test_owner_input_observer import Backend, Device, setup
from test_owner_journey_runtime import h
from test_motion_collection import retained


def monitor_fixture():
    observer,backend,device,clock=setup();observer.sample()
    monitor=CampInputContinuity(observer,topology=1,basis=b'{}',
        binding=tuple(object() for _ in range(6))+(1,),clock=lambda:clock[0])
    return monitor,backend,device,clock


@pytest.mark.parametrize('fault',('brief_turn','mouse','dropped','topology','unreadable','clock'))
def test_input_continuity_cannot_recover_after_a_gap(fault):
    m,backend,device,clock=monitor_fixture();m.check(m.binding)
    if fault=='brief_turn':device.pending=[(1,106,1),(1,106,0)]
    elif fault=='mouse':device.pending=[(2,0,1)]
    elif fault=='dropped':device.pending=[(0,3,0),(0,0,0)]
    elif fault=='topology':backend.nodes[DeviceIdentity('/dev/input/event2',2,2,2)]=Device()
    elif fault=='unreadable':device.fail=True
    else:clock[0]-=1.
    with pytest.raises(ValueError):m.check(m.binding)
    device.fail=False;clock[0]+=2
    with pytest.raises(ValueError):m.check(m.binding)
    assert not m.valid and not m.snapshot()['movement_authorized']
    m.close('stop');m.close('again');assert m.closed


def test_helper_input_is_excluded_but_owner_input_is_not():
    m,backend,device,_=monitor_fixture()
    helper=DeviceIdentity('/dev/input/event9',9,9,9)
    backend.nodes[helper]=Device();backend.exclude=helper
    # Topology must be established before arrival ownership is transferred.
    m.observer.sample()
    m=CampInputContinuity(m.observer,topology=m.observer.generation,basis=m.basis,
        binding=m.binding,clock=m.clock)
    backend.nodes[helper].pending=[(1,30,1),(1,30,0)]
    m.check(m.binding);assert m.valid
    device.pending=[(1,30,1),(1,30,0)]
    with pytest.raises(ValueError):m.check(m.binding)


def test_changed_object_binding_or_basis_does_not_resume():
    m,_,_,_=monitor_fixture();m.check(m.binding)
    with pytest.raises(ValueError):m.check((object(),*m.binding[1:]))
    with pytest.raises(ValueError):m.check(m.binding)
    m,_,_,_=monitor_fixture();m.basis=b'{"changed":true}'
    with pytest.raises(ValueError):m.check(m.binding)


@pytest.mark.parametrize('attribute',('observer','clock','binding','topology'))
def test_monitor_cannot_replace_its_arrival_context(attribute):
    m,_,_,_=monitor_fixture()
    if attribute=='observer':m.observer=SimpleNamespace(sample=lambda:pytest.fail('New observer used'))
    elif attribute=='clock':m.clock=lambda:100.
    elif attribute=='binding':m.binding=tuple([*m.binding])
    else:m.topology+=1
    with pytest.raises(ValueError):m.check(m.binding)


def test_direct_sample_cannot_return_success_after_reentrant_close():
    m,_,_,_=monitor_fixture();sample=m.observer.sample()
    def callback():
        m.close('F9');return sample
    m.observer.sample=callback
    with pytest.raises(ValueError):m.check(m.binding)
    assert not m.valid and m.closed and m.samples==0


@pytest.fixture
def arrived(h):
    """Synthetic handoff scope; full actual route is covered in Journey tests."""
    e=h.engine;assert e.start_stationary_camp(),h.notices
    backend=Backend();observer=OwnerInputObserver(backend=backend,helper_ui=h.sender.ui,clock=time.monotonic)
    observer.sample()
    j=e.journey=Journey(e.cancel_generation,settings_identity(e.settings),'camp')
    j.camp_motion=CampInputContinuity(observer,topology=observer.generation,
        basis=b'{"synthetic_arrival":true,"movement_authorized":false}',
        binding=e._camp_motion_binding(),clock=time.monotonic)
    assert e._camp_current()
    return h,j.camp_motion,next(iter(backend.nodes.values()))


@pytest.mark.parametrize('fault',('released_turn','mouse','device','focus','sender_ui','tracker','level_edit'))
def test_camp_stops_before_command_after_continuity_loss(arrived,fault):
    h,m,device=arrived;e=h.engine
    if fault=='released_turn':device.pending=[(1,106,1),(1,106,0)]
    elif fault=='mouse':device.pending=[(2,0,1)]
    elif fault=='device':device.fail=True
    elif fault=='focus':h.focused=False
    elif fault=='sender_ui':e.sender.ui=SimpleNamespace()
    elif fault=='tracker':e.live_zone_tracker=None
    else:e.settings.level+=1
    before=list(h.commands);e.autopilot_tick(time.monotonic())
    assert e.camp_session is None and e.journey is None and m.closed
    assert h.commands==before and not navigation_active(e) and not e.sender.held
    assert not e.journey_last_result['camp_input_continuity']['movement_authorized']


@pytest.mark.parametrize('stop',('F8','F9','F11','quit'))
def test_camp_exit_closes_monitor_before_assist_or_restart(arrived,stop):
    h,m,device=arrived;e=h.engine
    if stop=='F8':e.handle_job('arm',e.cancel_generation)
    elif stop=='F11':e.autopilot_hotkey_released()
    elif stop=='quit':e.handle_job('quit',None)
    else:e.stop_action('F9')
    assert e.journey is None and e.camp_session is None and m.closed and not m.valid
    assert m.observer.closed and device.closed==1 and not h.commands and not e.sender.held
    if stop=='F8':assert e._journey_assist is not None


def test_observed_camp_level_up_keeps_passive_monitor_without_rearming_navigation(arrived):
    h,m,_=arrived;e=h.engine
    h.append('You have gained a level! Welcome to level 8!')
    e.read_log()
    assert e.settings.level==e.camp_session.level==8
    assert e._camp_current() and m.valid and not navigation_active(e)
    assert not m.snapshot()['current_heading_verified'] and not h.commands


def test_f9_inside_observer_callback_cannot_send_after_scope_change(arrived):
    h,m,device=arrived;e=h.engine
    device.on_events=lambda:e.stop_action('F9 during observer')
    assert not e._camp_current()
    assert e.journey is None and e.camp_session is None and m.closed and not h.commands
