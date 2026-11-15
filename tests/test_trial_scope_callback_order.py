"""Final owner-scope checks survive read-only provider callback changes.

These isolate the actual trial and runtime binding methods. Synthetic owner,
window and model providers send no input and do not claim route acceptance.
"""
import os
from queue import Queue
from types import SimpleNamespace

import pytest

from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_route_trial import make_owner_route_trial_engine
from eql_automation.owner_source_runtime import OwnerSourceRuntime
from eql_automation.route_step_sender import _fd_identity


@pytest.fixture
def scope(tmp_path):
    s = SimpleNamespace(now=10., focused=True, window=71, pid=83, ticks='97',
                        callback=lambda:None, poll_callback=lambda:None,
                        active=False, veto_reason=None, veto_continuity=True, events=[])
    engine_type = make_owner_route_trial_engine(object, planner_loader=lambda _:None,
                                                clock=lambda:s.now)
    e = object.__new__(engine_type)
    s.engine = e
    e.settings = SimpleNamespace(game_dir=str(tmp_path), character='Probe', server='private', level=1)
    e.supervised_epoch = e.cancel_generation = e.route_session_epoch = 1
    e.cancelled = False
    e.supervised_motion = e.motion_collection_driver = e.route_session_driver = None
    e.jobs = Queue()
    e._route_idle = lambda:True
    def windows():
        s.events.append('window')
        return [SimpleNamespace(id=s.window)]
    e.gate = SimpleNamespace(windows=windows, focused_window=lambda:
        SimpleNamespace(id=s.window) if s.focused else None,
        game_session=lambda:dict(pid=s.pid, start_ticks=s.ticks), controls_ready=lambda:s.focused)
    rd, wr = os.pipe()
    ui = os.fdopen(wr, 'wb', buffering=0)
    e.sender = SimpleNamespace(ui=ui)
    reader = SimpleNamespace(zone_id=68, zone_display_name='Butcherblock Mountains',
        tail=SimpleNamespace(identity=(1,2), epoch=0), zone_generation=1)
    e.live_zone_tracker = SimpleNamespace(reader=reader)
    owner = ('synthetic-owner',)
    def lease_check():
        s.events.append('lease')
        s.callback()
        return owner
    lease = SimpleNamespace(reader=reader, check=lease_check)
    policy = object()
    def model_check(candidate):
        s.events.append('model')
        if candidate is not policy:
            raise ValueError('Synthetic model policy changed')
    model = SimpleNamespace(game_dir=str(tmp_path.resolve()), check_policy=model_check)
    planner = SimpleNamespace(region_policy=policy, installed_region_model=model)
    def sample():
        s.events.append('sample')
        return OwnerInputObservation(s.now,s.now,1,True,1,0,s.active,0,'synthetic')
    p = dict(cancelled=None, epoch=1, generation=1, settings=settings_identity(e.settings),
        sender=e.sender, gate=e.gate, window=(71,83,97), expires=30., lease=lease,
        observer=SimpleNamespace(sample=sample), topology=1, binding=SimpleNamespace(check=lambda:None),
        continuation=dict(started=0., route_epoch=1, tracker=e.live_zone_tracker,
            planner=planner, region_policy=policy, region_model=model,
            destination=SimpleNamespace(check=lambda:None)), driver=None, corridor_runtime=None)
    e.route_trial = p
    r = object.__new__(OwnerSourceRuntime)
    r.engine, r.pending, r.phase = e, p, 'ready'
    r.sender, r.ui, r.fd = e.sender, ui, ui.fileno()
    r.fd_identity = _fd_identity(r.fd)
    r.lease, r.reader = lease, reader
    r.zone = r._zone()
    r.owner_input, r.hotkey = p['observer'], p['binding']
    def poll():
        s.events.append('veto')
        s.poll_callback()
        return SimpleNamespace(continuity_available=s.veto_continuity, reason=s.veto_reason)
    r.veto = p['veto'] = SimpleNamespace(poll=poll)
    r._contact_driver_state = None
    p['source_runtime'] = r
    s.pending, s.runtime, s.model, s.planner = p, r, model, planner
    s.owner = owner
    yield s
    ui.close()
    os.close(rd)


def revoke(s, fault):
    e, p = s.engine, s.pending
    if fault == 'f8':
        e.cancel_generation += 1
        e.cancelled = True
        p['cancelled'] = 'Synthetic F8 owner takeover'
    elif fault == 'f9':
        e.cancel_generation += 1
        p['cancelled'] = 'Synthetic F9 stop'
    elif fault == 'focus': s.focused = False
    elif fault == 'window': s.window += 1
    elif fault == 'process': s.ticks = '98'
    elif fault == 'job': e.jobs.put(('another-job', None))
    elif fault == 'model': s.planner.installed_region_model = object()
    elif fault == 'input': s.active = True
    elif fault == 'deadline': s.now = 31.
    else: raise AssertionError(fault)


def test_binding_publishes_only_after_the_exclusive_reader_and_final_window(scope):
    s = scope
    assert s.engine._trial_binding(s.pending) == s.owner
    assert s.events == ['lease', 'window']


@pytest.mark.parametrize('fault', ('f8', 'f9', 'focus', 'window', 'process', 'job'))
def test_binding_refuses_owner_changes_from_the_lease_callback(scope, fault):
    s = scope
    s.callback = lambda:revoke(s, fault)
    with pytest.raises(ValueError):
        s.engine._trial_binding(s.pending)
    assert s.events[0] == 'lease'


def test_common_scope_keeps_model_checks_on_both_sides_of_read_only_callbacks(scope):
    s = scope
    s.engine._trial_common_current(s.pending)
    assert s.events == ['model', 'sample', 'lease', 'model', 'window']


@pytest.mark.parametrize('fault', ('f8', 'f9', 'focus', 'window', 'process', 'job', 'model'))
@pytest.mark.parametrize('boundary', ('destination', 'hotkey', 'lease'))
def test_common_scope_refuses_late_owner_or_model_changes(scope, fault, boundary):
    s = scope
    callback = lambda:revoke(s, fault)
    if boundary == 'destination': s.pending['continuation']['destination'].check = callback
    elif boundary == 'hotkey': s.pending['binding'].check = callback
    else: s.callback = callback
    with pytest.raises(ValueError):
        s.engine._trial_common_current(s.pending)


def test_runtime_checks_full_scope_after_lease_and_log_callbacks(scope):
    s = scope
    s.runtime.check_current()
    assert s.events == ['lease', 'veto', 'model', 'sample', 'lease', 'model', 'window']


@pytest.mark.parametrize('fault', ('f8', 'f9', 'focus', 'window', 'process', 'job',
                                 'model', 'input', 'deadline'))
@pytest.mark.parametrize('boundary', ('lease', 'veto'))
def test_runtime_refuses_changes_before_its_final_scene(scope, fault, boundary):
    s = scope
    def callback():
        # One mutation at the specified early read; the later lease read must
        # not be necessary to produce or repeat the owner change.
        s.callback = s.poll_callback = lambda:None
        revoke(s, fault)
    if boundary == 'lease': s.callback = callback
    else: s.poll_callback = callback
    with pytest.raises(ValueError):
        s.runtime.check_current()
    assert s.events[:2] == ['lease', 'veto']


@pytest.mark.parametrize('fault', ('hazard', 'coverage'))
def test_runtime_refuses_log_veto_before_publishing_current_scope(scope, fault):
    s = scope
    if fault == 'hazard': s.veto_reason = 'Synthetic incoming attack'
    else: s.veto_continuity = False
    with pytest.raises(ValueError, match='log hazard or coverage'):
        s.runtime.check_current()
    assert s.events == ['lease', 'veto']


@pytest.mark.parametrize('fault', ('source_runtime', 'veto', 'contact_boundary'))
def test_runtime_keeps_final_exclusivity_and_contact_checks(scope, fault):
    s = scope
    def callback():
        if fault == 'contact_boundary':
            s.runtime._contact_driver_state = ('old-contact',)
            s.runtime._contact_boundary_snapshot = lambda:('changed-contact',)
        else:
            s.pending[fault] = object()
    s.poll_callback = callback
    with pytest.raises(ValueError):
        s.runtime.check_current()
    assert s.events == ['lease', 'veto', 'model', 'sample', 'lease', 'model', 'window']
