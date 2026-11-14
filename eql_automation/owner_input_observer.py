"""Read-only Linux input observation for a future owner-run movement check.

No grabs, writes, virtual devices or permission changes. Device values remain
ephemeral; results contain counts, not typed keys. Unknown axes prevent a clear
result until a device-specific neutral/contact reader is available.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import stat
import time


@dataclass(frozen=True, order=True)
class DeviceIdentity:
    path: str
    device: int
    inode: int
    rdev: int


def identity(path: Path) -> DeviceIdentity:
    info = path.lstat()
    if not stat.S_ISCHR(info.st_mode):
        raise OSError("input path is not a direct character device")
    return DeviceIdentity(str(path), info.st_dev, info.st_ino, info.st_rdev)


@dataclass(frozen=True)
class OwnerInputObservation:
    started_at: float
    finished_at: float
    topology_generation: int
    coverage_complete: bool
    device_count: int
    held_key_count: int
    activity: bool
    unsupported_motion_devices: int
    reason: str

    def clear_at(self, now: float) -> bool:
        """Use collection start for freshness; never freshen a slow scan."""
        return (all(math.isfinite(v) for v in (now, self.started_at, self.finished_at))
                and self.started_at <= self.finished_at <= now
                and now - self.started_at <= 0.1
                and self.coverage_complete and self.device_count > 0
                and self.held_key_count == 0 and not self.activity
                and self.unsupported_motion_devices == 0)


class _ReadOnlyDevice:
    def __init__(self, node, api):
        self.node, self.api = node, api
        self.fd = os.open(node.path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            self.check_identity()
            self.types = frozenset(api.ioctl_capabilities(self.fd))
        except BaseException:
            self.close()
            raise

    def check_identity(self):
        info = os.fstat(self.fd)
        if ((info.st_dev, info.st_ino, info.st_rdev) !=
                (self.node.device, self.node.inode, self.node.rdev)):
            raise OSError("input descriptor identity changed")

    def held_count(self):
        # EV_KEY includes keyboard, mouse and controller buttons.
        return len(self.api.ioctl_EVIOCG_bits(self.fd, 1)) if 1 in self.types else 0

    def events(self):
        collected = []
        while len(collected) < 4096:
            try:
                batch = list(self.api.device_read_many(self.fd))
            except BlockingIOError:
                return collected
            if not batch:
                raise OSError("input device reached EOF")
            collected.extend((int(e[2]), int(e[3]), int(e[4])) for e in batch)
        raise OSError("input event budget exhausted")

    def close(self):
        if self.fd >= 0:
            fd, self.fd = self.fd, -1
            os.close(fd)


class LinuxInputBackend:
    def __init__(self):
        # InputDevice() first tries O_RDWR, so intentionally use only its
        # read ioctls with our own O_RDONLY descriptor.
        from evdev import _input, _uinput
        self.api, self.uinput = _input, _uinput

    def enumerate(self):
        # Do not use evdev.list_devices(): it omits inaccessible nodes.
        return tuple(sorted(identity(p) for p in Path("/dev/input").glob("event[0-9]*")))

    def open(self, node):
        return _ReadOnlyDevice(node, self.api)

    def excluded_helper(self, ui):
        if ui is None:
            return None
        # UI must remain alive throughout observation. The kernel identifies
        # this exact uinput descriptor; names are never exclusion evidence.
        fd = ui.fileno()
        os.fstat(fd)
        sysname = self.uinput.get_sysname(fd)
        if isinstance(sysname, bytes):
            sysname = sysname.decode("ascii")
        if not isinstance(sysname, str) or re.fullmatch(r"input[0-9]+", sysname) is None:
            raise OSError("cannot bind helper to its kernel input device")
        parent = Path("/sys/class/input") / sysname
        entries = tuple(parent.glob("event[0-9]*"))
        if len(entries) != 1 or entries[0].resolve().parent != parent.resolve():
            raise OSError("helper event identity is ambiguous")
        if (Path("/sys/class/input") / entries[0].name / "device").resolve() != parent.resolve():
            raise OSError("helper sysfs device link changed")
        node = identity(Path("/dev/input") / entries[0].name)
        major, minor = (int(n) for n in (entries[0] / "dev").read_text().strip().split(":"))
        event_fd = os.open(node.path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            info = os.fstat(event_fd)
            if (info.st_dev, info.st_ino, info.st_rdev) != (node.device, node.inode, node.rdev):
                raise OSError("helper event node changed while opening")
        finally:
            os.close(event_fd)
        current = self.uinput.get_sysname(fd)
        if isinstance(current, bytes):
            current = current.decode("ascii")
        if node.rdev != os.makedev(major, minor) or current != sysname:
            raise OSError("helper event identity changed")
        return node


class OwnerInputObserver:
    """Persistent observation, intended for one serialized engine thread.

    First attach, topology changes and read errors invalidate that observation.
    The next stable scan may become clear. This checks owner input only; focus,
    chat, target, combat, position and geometry still require separate evidence.
    """
    def __init__(self, *, backend=None, helper_ui=None, clock=time.monotonic):
        self.backend = LinuxInputBackend() if backend is None else backend
        self.helper_ui, self.clock = helper_ui, clock
        self.devices = {}
        self.desynced = set()
        self.topology = None
        self.generation = 0
        self.closed = False

    def _drop_devices(self):
        devices, self.devices = self.devices, {}
        self.desynced.clear()
        for device in devices.values():
            try:
                device.close()
            except OSError:
                pass

    def close(self):
        self.closed = True
        self._drop_devices()

    def sample(self):
        began = self.clock()
        complete, activity, held, unsupported = True, False, 0, 0
        reason, count = "observed", 0
        try:
            if self.closed or not math.isfinite(began):
                raise OSError("observer_closed_or_invalid_clock")
            nodes = self.backend.enumerate()
            excluded = self.backend.excluded_helper(self.helper_ui)
            if excluded is not None and excluded not in nodes:
                raise OSError("helper_not_in_input_topology")
            topology = (nodes, excluded)
            if topology != self.topology:
                self._drop_devices()
                self.topology = None
                self.generation += 1
                for node in nodes:
                    if node != excluded:
                        self.devices[node] = self.backend.open(node)
                self.topology = topology
                complete, reason = False, "topology_changed"
            count = len(self.devices)
            if not count:
                complete, reason = False, "no_owner_input_devices"
            for node, device in self.devices.items():
                device.check_identity()
                # Snapshot both sides of draining: keys held before attach
                # and brief presses between scans must not disappear.
                held_before = device.held_count()
                events = device.events()
                held += max(held_before, device.held_count())
                unsupported += int(3 in device.types)  # EV_ABS needs contact/neutral interpretation.
                activity |= any(t == 1 or (t in (2, 3) and v != 0) for t, c, v in events)
                dropped = False
                for event_type, code, value in events:
                    if event_type == 0 and code == 3:  # SYN_DROPPED
                        dropped = True
                        self.desynced.add(node)
                    elif event_type == 0 and code == 0:  # SYN_REPORT
                        self.desynced.discard(node)
                if dropped or node in self.desynced:
                    complete, reason = False, "event_stream_dropped"
                if self.clock() - began > 0.05:
                    raise OSError("input_scan_too_slow")
            if (self.backend.enumerate(), self.backend.excluded_helper(self.helper_ui)) != topology:
                raise OSError("input_topology_changed_during_scan")
        except (OSError, ValueError, RuntimeError) as error:
            complete, reason = False, str(error)
            self._drop_devices()
            self.topology = None
        finished = self.clock()
        if not math.isfinite(finished) or not 0 <= finished - began <= 0.05:
            complete, reason = False, "invalid_or_slow_observation_clock"
        return OwnerInputObservation(began, finished, self.generation, complete,
                                     count, held, activity, unsupported, reason)
