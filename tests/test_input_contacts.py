from types import SimpleNamespace

import pytest

from eql_automation.input_contacts import (
    absolute_profile, read_tracking_ids, touchpad_contact_count, TOUCHPAD_AXES,
)


def pad():
    return {1: [272, 325, 328, 330, 333, 334, 335],
            3: [(code, (0, 0, 10, 0, 0, 0)) for code in TOUCHPAD_AXES]}


def test_only_observed_contact_shape_or_volume_control_is_supported():
    assert absolute_profile({1: [30]}, ()) == "none"
    assert absolute_profile({3: [(32, (80, 0, 100, 0, 0, 0))]}, ()) == "volume"
    assert absolute_profile(pad(), [0, 2]) == "type_b_touchpad"
    assert absolute_profile(pad(), [1]) == "unsupported"
    missing_key = pad(); missing_key[1].remove(330)
    assert absolute_profile(missing_key, [0, 2]) == "unsupported"
    extra_axis = pad(); extra_axis[3].append((2, (0, 0, 1, 0, 0, 0)))
    assert absolute_profile(extra_axis, [0, 2]) == "unsupported"
    assert absolute_profile({3: [(0, (0, -100, 100, 0, 0, 0))]}, ()) == "unsupported"


def test_native_ioctl_requests_all_slots_and_reads_signed_unused_id():
    def ioctl(fd, request, values, mutate):
        assert fd == 9 and mutate is True
        assert request == (2 << 30) | (16 << 16) | (ord('E') << 8) | 0x0a
        assert list(values) == [57, -2, -2, -2]
        values[1:] = type(values)('i', [-1, 0, 23])
    assert read_tracking_ids(9, 3, ioctl=ioctl) == (-1, 0, 23)


def test_incomplete_or_failed_slot_read_is_not_contact_free():
    with pytest.raises(OSError, match="incomplete"):
        read_tracking_ids(9, 3, ioctl=lambda *args: None)
    def failure(*args):
        raise PermissionError("read refused")
    with pytest.raises(PermissionError):
        read_tracking_ids(9, 3, ioctl=failure)


@pytest.mark.parametrize("count", [0, 33, -1, True, 1.5])
def test_slot_buffer_is_bounded(count):
    with pytest.raises(OSError):
        read_tracking_ids(9, count, ioctl=lambda *args: pytest.fail("ioctl called"))


def test_current_slot_is_not_a_substitute_for_all_slot_contacts():
    api = SimpleNamespace(ioctl_EVIOCGABS=lambda fd, code: (0, 0, 4, 0, 0, 0))
    def read(fd, count):
        assert count == 5
        return (-1, -1, -1, 0, 99)
    assert touchpad_contact_count(9, api, read_slots=read) == 2
    assert touchpad_contact_count(9, api, read_slots=lambda fd, n: (-1,) * n) == 0


@pytest.mark.parametrize("info", [
    (0, 1, 5, 0, 0, 0), (0, 0, 32, 0, 0, 0),
    (6, 0, 4, 0, 0, 0), (0, 0, 4), (0, 0, True, 0, 0, 0),
])
def test_invalid_slot_bounds_refuse_before_reading(info):
    api = SimpleNamespace(ioctl_EVIOCGABS=lambda fd, code: info)
    with pytest.raises(OSError, match="bounds"):
        touchpad_contact_count(9, api, read_slots=lambda *args: pytest.fail("slots read"))


def test_bounds_changed_during_snapshot_or_short_response_refuses():
    calls = iter([(0, 0, 4, 0, 0, 0), (0, 0, 5, 0, 0, 0)])
    api = SimpleNamespace(ioctl_EVIOCGABS=lambda *args: next(calls))
    with pytest.raises(OSError, match="changed"):
        touchpad_contact_count(9, api, read_slots=lambda fd, n: (-1,) * n)
    api = SimpleNamespace(ioctl_EVIOCGABS=lambda *args: (0, 0, 4, 0, 0, 0))
    with pytest.raises(OSError, match="incomplete"):
        touchpad_contact_count(9, api, read_slots=lambda fd, n: (-1,))
