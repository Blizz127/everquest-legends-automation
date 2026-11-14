"""Read-only contact state for the owner's observed type-B touchpad.

Semantics: docs.kernel.org/input/multi-touch-protocol.html and Linux UAPI
input.h. This does not interpret joystick axes, touchscreens or unknown pads.
"""
from __future__ import annotations

from array import array
import fcntl
import platform


ABS_VOLUME = 32
ABS_MT_SLOT = 47
ABS_MT_TRACKING_ID = 57
TOUCHPAD_AXES = frozenset({0, 1, 47, 53, 54, 55, 57})
TOUCHPAD_PROPERTIES = frozenset({0, 2})  # POINTER, BUTTONPAD
MAX_CONTACT_SLOTS = 32


def absolute_profile(capabilities, properties):
    """Accept the observed contact layout or a volume-only absolute control."""
    if 3 not in capabilities:
        return "none"
    axes = frozenset(item[0] if isinstance(item, tuple) else item
                     for item in capabilities[3])
    if axes == {ABS_VOLUME}:
        return "volume"
    keys = frozenset(capabilities.get(1, ()))
    if (axes == TOUCHPAD_AXES and frozenset(properties) == TOUCHPAD_PROPERTIES
            and {325, 330} <= keys):  # BTN_TOOL_FINGER, BTN_TOUCH
        return "type_b_touchpad"
    return "unsupported"


def read_tracking_ids(fd, slots, *, ioctl=fcntl.ioctl):
    """EVIOCGMTSLOTS on x86_64 Linux, reading every slot with invalid sentinels."""
    if (platform.system() != "Linux" or platform.machine() != "x86_64"
            or isinstance(slots, bool) or not isinstance(slots, int)
            or not 1 <= slots <= MAX_CONTACT_SLOTS):
        raise OSError("unsupported_contact_ioctl_platform_or_slot_count")
    values = array("i", [ABS_MT_TRACKING_ID] + [-2] * slots)
    if values.itemsize != 4:
        raise OSError("unsupported_contact_ioctl_integer_size")
    size = len(values) * values.itemsize
    request = (2 << 30) | (size << 16) | (ord("E") << 8) | 0x0a
    ioctl(fd, request, values, True)
    if values[0] != ABS_MT_TRACKING_ID or any(v < -1 for v in values[1:]):
        raise OSError("invalid_or_incomplete_contact_slot_snapshot")
    return tuple(values[1:])


def touchpad_contact_count(fd, api, *, read_slots=read_tracking_ids):
    def bounds():
        info = api.ioctl_EVIOCGABS(fd, ABS_MT_SLOT)
        if (len(info) != 6 or any(isinstance(v, bool) or not isinstance(v, int) for v in info)
                or info[1] != 0 or not 0 <= info[2] < MAX_CONTACT_SLOTS
                or not info[1] <= info[0] <= info[2]):
            raise OSError("invalid_touchpad_slot_bounds")
        return info[1], info[2]

    before = bounds()
    values = read_slots(fd, before[1] + 1)
    if (len(values) != before[1] + 1 or before != bounds()
            or any(isinstance(v, bool) or not isinstance(v, int) or v < -1 for v in values)):
        raise OSError("touchpad_slots_changed_or_incomplete")
    # Zero is an active contact ID. Only -1 denotes an unused slot.
    return sum(v >= 0 for v in values)
