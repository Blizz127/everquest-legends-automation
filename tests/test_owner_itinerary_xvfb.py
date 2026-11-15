"""Opt-in retained owner path on a new private Xvfb and anonymous input pipe.

Run with EQL_TEST_PRIVATE_XVFB=1. This starts only its own X server, never a
client/helper application or device. Window/PID/focus/grabs are real Xlib calls;
terrain, game logs, physical feedback, owner input and gauges remain synthetic.
The F8 case calls the actual handler, not the X hotkey event dispatcher.
"""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest

from test_motion_collection import retained


@pytest.fixture
def private_xvfb(tmp_path, monkeypatch):
    if os.environ.get('EQL_TEST_PRIVATE_XVFB') != '1':
        pytest.skip('explicit private-Xvfb opt-in required')
    pytest.importorskip('Xlib')
    executable = shutil.which('Xvfb')
    if executable is None:
        pytest.skip('Xvfb unavailable')
    from Xlib import X, Xatom, display

    # Never connect to the owner's existing display, even during fixture setup.
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
        monkeypatch.delenv(name, raising=False)
    read_fd, write_fd = os.pipe()
    server = connection = gate = None
    windows = []
    report = dict(synthetic=True, real_client_accepted=False, real_input_device=False,
                  gate_backend='retained WindowGate / private Xvfb',
                  gauges='synthetic', owner_input='synthetic clear samples')
    started = time.monotonic()
    log = (tmp_path/'xvfb.log').open('wb')
    try:
        server = subprocess.Popen(
            [executable, '-displayfd', str(write_fd), '-screen', '0', '320x240x24',
             '-nolisten', 'tcp', '-noreset'],
            pass_fds=(write_fd,), stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        # An external runner can reap this exact process after a hard timeout
        # or CPU-limit kill, when pytest's finally blocks cannot execute.
        if os.environ.get('EQL_XVFB_PID_FILE'):
            start_ticks = Path('/proc', str(server.pid), 'stat').read_text().rpartition(') ')[2].split()[19]
            with Path(os.environ['EQL_XVFB_PID_FILE']).open('a') as markers:
                markers.write(json.dumps(dict(pid=server.pid, start_ticks=start_ticks))+'\n')
                markers.flush()
                os.fsync(markers.fileno())
        os.close(write_fd)
        write_fd = None
        assert select.select([read_fd], [], [], 5.)[0], 'private Xvfb did not publish a display'
        number = os.read(read_fd, 64).decode().strip()
        assert number.isascii() and number.isdigit(), 'invalid private display number'
        monkeypatch.setenv('DISPLAY', ':'+number)
        monkeypatch.setenv('XAUTHORITY', '/dev/null')
        connection = display.Display()
        root = connection.screen().root
        for name in ('eqgame', 'synthetic-neutral'):
            window = root.create_window(0, 0, 100, 80, 0,
                connection.screen().root_depth, X.InputOutput, X.CopyFromParent,
                background_pixel=connection.screen().black_pixel)
            window.set_wm_class(name, name)
            window.set_wm_name('Private synthetic '+name)
            window.change_property(connection.get_atom('_NET_WM_PID'),
                                   Xatom.CARDINAL, 32, [os.getpid()])
            window.map()
            windows.append(window)
        root.change_property(connection.get_atom('_NET_CLIENT_LIST'), Xatom.WINDOW,
                             32, [window.id for window in windows])

        def focus(window):
            root.change_property(connection.get_atom('_NET_ACTIVE_WINDOW'),
                                 Xatom.WINDOW, 32, [window.id])
            window.set_input_focus(X.RevertToParent, X.CurrentTime)
            connection.sync()

        focus(windows[0])
        from rotation_engine import WindowGate
        gate = WindowGate()
        gate.refresh_grabs()
        assert not gate.grab_errors and gate.controls_ready()
        gate.read_gauges = lambda *args: (1., 1.)
        report.update(display=':'+number, xvfb_pid=server.pid,
                      synthetic_window=windows[0].id, synthetic_pid=os.getpid(),
                      actual_passive_grabs=True)
        yield SimpleNamespace(gate=gate, lose_focus=lambda: focus(windows[1]), report=report)
    finally:
        cleanup_errors = []
        if gate is not None:
            try:
                gate.display.close()
            except Exception as error:
                cleanup_errors.append(str(error))
        if connection is not None:
            try:
                for window in windows:
                    window.destroy()
                connection.sync()
                connection.close()
            except Exception as error:
                cleanup_errors.append(str(error))
        if write_fd is not None:
            os.close(write_fd)
        os.close(read_fd)
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=3.)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3.)
            report.update(xvfb_reaped=server.poll() is not None, xvfb_exit=server.returncode)
        log.close()
        report['cleanup_errors'] = cleanup_errors
        report['wall_seconds'] = time.monotonic()-started
        output = Path(os.environ.get('EQL_XVFB_REPORT_DIR', str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        name = report.get('case', 'setup')
        (output/('owner-itinerary-xvfb-'+name+'.json')).write_text(
            json.dumps(report, indent=2, sort_keys=True)+'\n')


@pytest.fixture
def actual_owner(tmp_path, retained, monkeypatch, private_xvfb):
    from test_owner_zone_itinerary import real_owner
    generator = real_owner.__wrapped__(tmp_path, retained, monkeypatch)
    h = next(generator)
    from eql_automation.owner_navigation_preflight import window_identity
    h.gate = h.engine.gate = h.sender.gate = private_xvfb.gate
    identity = window_identity(h.gate, require_focus=True)
    h.engine.last_hotkey_test['window_identity'] = identity
    private_xvfb.report['window_identity'] = identity
    try:
        yield h
    finally:
        generator.close()


def _instrument(h, monkeypatch, scene, *, lose_focus):
    """Inclusive callback totals and child timestamps, without replacing guards."""
    from eql_automation.owner_zone_itinerary import _ItineraryOwner
    from eql_automation.source_motion import SourceReceiptLedger
    from eql_automation.supervised_source import SupervisedSourcePolicy
    import eql_automation.uinput_watchdog as watchdog
    counts, totals, maxima = Counter(), Counter(), Counter()
    pulses = []
    active = []
    focused_lost = []
    e = h.engine

    def counted(target, name, label):
        original = getattr(target, name)
        def wrapper(*args, **kwargs):
            begin = time.monotonic()
            counts[label] += 1
            try:
                return original(*args, **kwargs)
            finally:
                elapsed = time.monotonic()-begin
                totals[label] += elapsed
                maxima[label] = max(maxima[label], elapsed)
        monkeypatch.setattr(target, name, wrapper)

    for name in ('windows', 'identity', 'game_session', 'focused_window',
                 'focused', 'controls_ready'):
        counted(h.gate, name, 'gate.'+name)
    counted(_ItineraryOwner, 'binding', 'owner.binding')
    counted(_ItineraryOwner, 'check', 'owner.check')
    counted(e, '_itinerary_current', 'engine._itinerary_current')
    counted(h.sender, 'check', 'sender.check')
    cancellations = []
    cancel = SourceReceiptLedger.cancel
    def observed_cancel(ledger, reason='Source movement cancelled'):
        reference = ledger.reference
        now = time.monotonic()
        cancellations.append(dict(at=now, reason=str(reason), phase=ledger.phase,
            reference_age=None if reference is None else now-reference.raw_fix.received_monotonic))
        return cancel(ledger, reason)
    monkeypatch.setattr(SourceReceiptLedger, 'cancel', observed_cancel)
    boundaries = []
    for name in ('observe', 'validate_scene', 'authorize', 'still_authorized'):
        original = getattr(SupervisedSourcePolicy, name)
        def boundary(policy, *args, _original=original, _name=name, **kwargs):
            start_counts = counts.copy()
            reference = policy.ledger.reference
            item = dict(method=_name, started_at=time.monotonic())
            if reference is not None:
                item['reference_received_at'] = reference.raw_fix.received_monotonic
            boundaries.append(item)
            try:
                return _original(policy, *args, **kwargs)
            except BaseException as error:
                item['error'] = type(error).__name__+': '+str(error)
                raise
            finally:
                item['finished_at'] = time.monotonic()
                item['callback_counts'] = dict(counts-start_counts)
        monkeypatch.setattr(SupervisedSourcePolicy, name, boundary)

    def phase():
        if e.supervised_motion is not None:
            return 'initial_calibration'
        if e.source_crossing_run is not None:
            return 'source_crossing'
        if e.section_run is not None:
            return 'walking_section'
        if e.route_trial is not None:
            return 'initial_source_route'
        return 'other'

    read_status = watchdog._read_status
    def observed_status(*args, **kwargs):
        value = read_status(*args, **kwargs)
        if active:
            record = active[-1]
            record['statuses'].append(dict(status=value.split(' ', 1)[0], at=time.monotonic()))
            if value.startswith('UP '):
                record['raw_receipt'] = json.loads(value[3:])
            if value == 'DOWN':
                record['down_callback_counts'] = dict(counts)
            if (value == 'DOWN' and lose_focus and not focused_lost
                    and record.get('key_code') in (103, 105, 106)):
                scene.lose_focus()
                focused_lost.append(time.monotonic())
                record['focus_lost_at'] = focused_lost[-1]
                assert not h.gate.focused() and not h.gate.controls_ready()
        return value
    monkeypatch.setattr(watchdog, '_read_status', observed_status)

    run = watchdog._run_pulse
    def observed_pulse(fd, key, seconds, **kwargs):
        record = dict(phase=phase(), key_code=key, requested_seconds=seconds,
                      started_at=time.monotonic(), statuses=[])
        initial_counts = counts.copy()
        initial_totals = totals.copy()
        pulses.append(record)
        active.append(record)
        for name in ('before_down', 'select_after_ready'):
            callback = kwargs.get(name)
            if callback is None:
                continue
            def selection(*args, _callback=callback, _name=name, **options):
                record[_name+'_started_at'] = time.monotonic()
                try:
                    result = _callback(*args, **options)
                    if _name == 'select_after_ready' and result is not None:
                        record.update(key_code=result.key_code, requested_seconds=result.seconds,
                                      expires_at=result.expires_at)
                    elif result is not None:
                        record['expires_at'] = result
                    return result
                finally:
                    record[_name+'_finished_at'] = time.monotonic()
            kwargs[name] = selection
        stop = kwargs.get('should_stop')
        if stop is not None:
            record['stop_checks'] = []
            def observed_stop():
                check = dict(started_at=time.monotonic())
                record['stop_checks'].append(check)
                try:
                    result = stop()
                    check['stopped'] = result
                    return result
                finally:
                    check['finished_at'] = time.monotonic()
            kwargs['should_stop'] = observed_stop
        try:
            receipt = run(fd, key, seconds, **kwargs)
            if receipt is not None:
                record['receipt'] = asdict(receipt)
            return receipt
        except BaseException as error:
            record['error'] = type(error).__name__+': '+str(error)
            if hasattr(error, 'timing'):
                record['permit_timing'] = error.timing
            if hasattr(error, 'receipt'):
                record['receipt'] = asdict(error.receipt)
            raise
        finally:
            record['finished_at'] = time.monotonic()
            record['callback_counts'] = dict(counts-initial_counts)
            if 'down_callback_counts' in record:
                at_down = Counter(record.pop('down_callback_counts'))
                record['pre_down_callback_counts'] = dict(at_down-initial_counts)
                record['after_down_callback_counts'] = dict(counts-at_down)
            record['callback_inclusive_seconds'] = dict(totals-initial_totals)
            active.pop()
    monkeypatch.setattr(watchdog, '_run_pulse', observed_pulse)
    scene.report.update(pulses=pulses, callback_counts=counts,
                        callback_inclusive_seconds=totals, callback_max_seconds=maxima,
                        inclusive_times_overlap=True, focus_lost_at=focused_lost,
                        source_cancellations=cancellations, source_boundaries=boundaries)
    return pulses, focused_lost


@pytest.mark.parametrize('case', ('focus_loss', 'first_crossing_f8', 'ordinary_source'))
def test_retained_owner_with_private_x_gate(actual_owner, private_xvfb, monkeypatch, case):
    from eql_automation.native_region_policy import encoded
    from eql_automation.owner_zone_itinerary import ITINERARY_JOB
    from eql_automation.owner_route_trial import SOURCE_JOB
    from eql_automation.route_geometry import RouteMotionBounds
    from eql_automation.zone_itinerary_budget import ZoneItineraryDeclaration
    from eql_automation.zone_itinerary_runtime import ZoneItineraryPlan
    from test_owner_source_crossing import _configure_sectioned_crossing
    from test_owner_zone_itinerary import synthetic_legs
    h, scene = actual_owner, private_xvfb
    e = h.engine
    scene.report['case'] = case
    scene.report['test_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    crossing = _configure_sectioned_crossing(h, monkeypatch)
    assert e.live_zone_tracker.owner_binding[-3:] == tuple(scene.report['window_identity'])
    assets = h.source_loading[0]()
    legs, crossings = synthetic_legs(
        {'Fixture': 68, 'The Greater Faydark': 54, 'Clan Crushbone': 58}, crossing)
    bounds = RouteMotionBounds('synthetic-independent-itinerary', 'synthetic-bounds-only',
        .01, .15, .2, 60., .3, .1, 10., .2, 1.2, 6.)
    plan = ZoneItineraryPlan(
        ZoneItineraryDeclaration('synthetic-retained-owner', legs, 120., 1000, 100., 10000.),
        bounds, encoded(dict(kind='synthetic-independent-owner-bounds')),
        lambda identifier: assets, lambda _: None, crossings.__getitem__)
    h.itinerary_selection[0] = plan
    e.read_log()
    handoffs, completed, source_steps = [], [], []
    handoff = e._handoff_completed_motion
    def observed_handoff(pending, session, record):
        owner = e.zone_itinerary_owner
        handoffs.append(dict(at=time.monotonic(), initial_receipts=len(session.receipts),
                             root_snapshot=None if owner is None else owner.root.snapshot()))
        return handoff(pending, session, record)
    monkeypatch.setattr(e, '_handoff_completed_motion', observed_handoff)
    finish = e._finish_source_crossing
    def observed_finish(current):
        result = finish(current)
        run = e.zone_itinerary_run
        if run is not None and run.phase == 'load_destination':
            completed.append(dict(at=time.monotonic(), phase=run.phase,
                                  root_snapshot=run.root.snapshot()))
            e.handle_job('arm', e.cancel_generation)
        return result
    monkeypatch.setattr(e, '_finish_source_crossing', observed_finish)
    import eql_automation.owner_source_runtime as source_runtime
    step = source_runtime.run_checked_source_step
    def observed_source_step(*args, **kwargs):
        result = step(*args, **kwargs)
        source_steps.append(dict(at=time.monotonic(), receipt=asdict(result.receipt)))
        return result
    monkeypatch.setattr(source_runtime, 'run_checked_source_step', observed_source_step)
    pulses, lost_focus = _instrument(h, monkeypatch, scene, lose_focus=case == 'focus_loss')
    scene.report.update(handoffs=handoffs, completed=completed, source_steps=source_steps)
    begin, cpu = time.monotonic(), time.process_time()
    try:
        if case == 'ordinary_source':
            e.post(SOURCE_JOB, dict(open_flat_clear=True, destination_id='butcher-gfay-crossing'))
        else:
            e.post(ITINERARY_JOB, dict(itinerary_id='synthetic-retained-owner',
                open_flat_clear=True, owner_supervised_continuation=True))
        e.handle_job(*e.jobs.get_nowait())
        assert e.supervised_motion is not None, h.notices
        owner = e.zone_itinerary_owner
        h.due_trial()
        deadline = begin+110.
        while (e.journey is not None or e._navigation_busy()) and time.monotonic() < deadline:
            e.read_log()
            h.tick()
            h.drain()
            if case == 'ordinary_source' and source_steps:
                e.stop_action('Ordinary source comparison complete after first movement receipt')
            time.sleep(.01)
        h.drain()
        scene.report['root_snapshot'] = None if owner is None else owner.root.snapshot()
        scene.report['initial_measurement_receipts'] = (len(owner.initial_account.releases)
            if owner is not None else handoffs[0]['initial_receipts'] if handoffs else 0)
        assert not e._navigation_busy()
        assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None
        assert e.source_crossing_run is None and e.journey is None and e.camp_session is None
        assert (owner is None or not owner.root.valid) and not h.sender.held and h.observer_closed
        assert e.live_zone_tracker.lease is None
        held = set()
        for kind, code, value in h.events:
            if kind == 1 and value == 1:
                held.add(code)
            elif kind == 1 and value == 0:
                held.discard(code)
        assert not held, 'a pipe DOWN lacks a later matching UP'
        scene.report['cleanup_verified'] = True
        if case == 'focus_loss':
            assert lost_focus, h.notices
            assert not handoffs and not completed
        elif case == 'ordinary_source':
            assert owner is None and source_steps, h.notices
            assert handoffs and handoffs[0]['initial_receipts'] == 7, h.notices
        else:
            assert handoffs and handoffs[0]['initial_receipts'] == 7, h.notices
            assert completed, h.notices
            assert completed[0]['phase'] == 'load_destination'
            assert e._journey_assist is not None
        scene.report['assertions_passed'] = True
    finally:
        scene.report.update(experiment_wall_seconds=time.monotonic()-begin,
            experiment_cpu_seconds=time.process_time()-cpu, notices=h.notices,
            pipe_events=h.events, sender_held=sorted(h.sender.held),
            observer_closed=h.observer_closed, owner_active=e.zone_itinerary_owner is not None,
            tracker_lease_active=e.live_zone_tracker.lease is not None)
        e.stop_action('private-Xvfb test teardown')
        h.drain()
