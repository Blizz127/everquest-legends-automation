from types import SimpleNamespace
import os

import pytest

from eql_automation.owner_input_observer import (
    DeviceIdentity, OwnerInputObserver, _ReadOnlyDevice,
)


class Device:
    def __init__(self, types=(1,), held=0):
        self.types = set(types)
        self.held = held
        self.pending = []
        self.closed = 0
        self.fail = False
        self.on_events = lambda: None

    def check_identity(self):
        if self.fail:
            raise OSError("device_removed")

    def held_count(self):
        return self.held

    def events(self):
        self.on_events()
        result, self.pending = self.pending, []
        return result

    def close(self):
        self.closed += 1


class Backend:
    def __init__(self):
        self.nodes = {DeviceIdentity("/dev/input/event1", 1, 1, 1): Device()}
        self.denied = set()
        self.exclude = None

    def enumerate(self):
        return tuple(sorted(self.nodes))

    def excluded_helper(self, ui):
        return self.exclude

    def open(self, node):
        if node in self.denied:
            raise PermissionError("device_unreadable")
        return self.nodes[node]


def setup():
    backend = Backend()
    clock = [100.0]
    observer = OwnerInputObserver(backend=backend, clock=lambda: clock[0])
    device = next(iter(backend.nodes.values()))
    return observer, backend, device, clock


def test_initial_attach_needs_stable_scan_and_held_keys_are_seen_before_events():
    observer, backend, device, clock = setup()
    device.held = 1
    first = observer.sample()
    assert not first.coverage_complete and first.held_key_count == 1
    still_held = observer.sample()
    assert still_held.coverage_complete and not still_held.clear_at(clock[0])
    device.held = 0
    released = observer.sample()
    assert released.clear_at(clock[0])
    assert not released.clear_at(clock[0] + 0.101)
    assert not released.clear_at(clock[0] - 0.01)


@pytest.mark.parametrize("events", [
    [(1, 30, 1), (1, 30, 0)],  # brief key press and release
    [(1, 272, 1), (1, 272, 0)],  # mouse button, no function keys required
    [(1, 304, 1)],  # gamepad button
    [(2, 0, 1)],  # mouse motion
])
def test_brief_owner_activity_cannot_disappear_between_snapshots(events):
    observer, backend, device, clock = setup()
    observer.sample()
    device.pending = events
    observed = observer.sample()
    assert observed.coverage_complete and observed.held_key_count == 0
    assert observed.activity and not observed.clear_at(clock[0])
    assert observer.sample().clear_at(clock[0])


def test_uninterpreted_absolute_axis_is_not_assumed_neutral():
    observer, backend, device, clock = setup()
    device.types.add(3)
    observer.sample()
    observed = observer.sample()
    assert observed.coverage_complete and observed.unsupported_motion_devices == 1
    assert not observed.clear_at(clock[0])


def test_inaccessible_node_stays_in_inventory_and_prevents_clear():
    observer, backend, device, clock = setup()
    backend.denied = set(backend.nodes)
    for _ in range(2):
        observed = observer.sample()
        assert not observed.coverage_complete and not observed.clear_at(clock[0])
        assert observed.reason == "device_unreadable"
    backend.denied.clear()
    assert not observer.sample().coverage_complete
    assert observer.sample().clear_at(clock[0])


def test_path_replacement_and_hotplug_during_scan_invalidate_coverage():
    observer, backend, device, clock = setup()
    observer.sample()
    first_generation = observer.generation
    old = next(iter(backend.nodes))
    backend.nodes = {DeviceIdentity(old.path, 1, 2, 1): device}
    assert not observer.sample().coverage_complete
    assert observer.generation > first_generation
    new = DeviceIdentity("/dev/input/event2", 1, 3, 2)
    device.on_events = lambda: backend.nodes.update({new: Device()})
    observed = observer.sample()
    assert observed.reason == "input_topology_changed_during_scan"
    assert not observed.coverage_complete and device.closed >= 2


def test_overflow_sample_is_unsafe_and_next_scan_rechecks_active_keys():
    observer, backend, device, clock = setup()
    observer.sample()
    device.pending = [(0, 3, 0), (0, 0, 0)]
    assert observer.sample().reason == "event_stream_dropped"
    device.held = 1
    assert not observer.sample().clear_at(clock[0])
    device.held = 0
    assert observer.sample().clear_at(clock[0])


def test_overflow_waits_for_report_before_resynchronizing():
    observer, backend, device, clock = setup()
    observer.sample()
    device.pending = [(0, 3, 0)]
    assert not observer.sample().coverage_complete
    assert not observer.sample().coverage_complete
    device.pending = [(0, 0, 0)]
    assert observer.sample().clear_at(clock[0])


def test_only_exact_helper_node_is_excluded_and_loss_of_identity_is_unsafe():
    observer, backend, device, clock = setup()
    helper = DeviceIdentity("/dev/input/event2", 1, 2, 2)
    backend.nodes[helper] = Device(held=1)
    backend.exclude = helper
    observer.sample()
    assert observer.sample().clear_at(clock[0])
    device.held = 1  # a different device always counts, whatever its name
    assert not observer.sample().clear_at(clock[0])
    del backend.nodes[helper]
    observed = observer.sample()
    assert observed.reason == "helper_not_in_input_topology"
    assert not observed.coverage_complete


def test_slow_scan_clock_rollback_device_failure_and_close_never_clear():
    observer, backend, device, clock = setup()
    observer.sample()
    device.on_events = lambda: clock.__setitem__(0, clock[0] + 0.06)
    assert not observer.sample().coverage_complete
    device.on_events = lambda: clock.__setitem__(0, clock[0] - 0.02)
    assert not observer.sample().clear_at(clock[0])
    device.on_events = lambda: None
    device.fail = True
    assert observer.sample().reason == "device_removed"
    observer.close()
    observer.close()
    assert not observer.sample().coverage_complete


def test_native_backend_opens_readonly_and_closes_on_capability_failure(monkeypatch):
    opened, closed = [], []
    monkeypatch.setattr(os, "open", lambda path, flags: opened.append((path, flags)) or 17)
    monkeypatch.setattr(os, "close", closed.append)
    monkeypatch.setattr(os, "fstat", lambda fd: SimpleNamespace(st_dev=1, st_ino=2, st_rdev=3))
    def fail(fd):
        raise OSError("capabilities unavailable")
    api = SimpleNamespace(ioctl_capabilities=fail)
    with pytest.raises(OSError):
        _ReadOnlyDevice(DeviceIdentity("/dev/input/event7", 1, 2, 3), api)
    assert opened[0][1] & os.O_ACCMODE == os.O_RDONLY
    assert opened[0][1] & os.O_NONBLOCK
    assert closed == [17]
