"""Optional /location acquisition through an owner-configured game hotbutton.

This avoids chat drafting entirely. The owner must configure a single-command
hotbutton, verify its key in the current client, and keep its bar/page unchanged.
No key is assumed and no client files are changed. The configured command is an owner assertion; a returned key
receipt is not evidence of its client effect. RouteSession accepts the fresh
location reply separately and stops on missing or ambiguous replies.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import os
from pathlib import Path

from .owner_input_observer import OwnerInputObservation
from .uinput_watchdog import _EVENT, PulseSelection, selected_key_pulse_receipt


class HotkeyStopped(RuntimeError):
    pass


def _fd_identity(fd):
    info = os.fstat(fd)
    return info.st_dev, info.st_ino, info.st_rdev, info.st_mode


# F6-F12 belong to the retained helper. Printable keys, Escape, Enter, arrows,
# modifiers and those helper controls cannot be used by this acquisition path.
HOTKEY_CODES = {**{f'F{i}': 58+i for i in range(1, 6)},
                **{f'F{i}': 170+i for i in range(13, 25)}}


def _source_hashes(paths):
    records = []
    for value in paths:
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Hotbutton configuration must be a direct file')
        if path.stat().st_size > 4*1024*1024:
            raise ValueError('Hotbutton configuration is unexpectedly large')
        records.append((str(path.resolve()), sha256(path.read_bytes()).hexdigest()))
    return tuple(records)


@dataclass(frozen=True)
class OwnerLocationHotkey:
    """Owner's explicit setup declaration, never inferred from default keys.

    ``confirmation_id`` references the owner's same-session setup/test record.
    Saved INI hashes detect persisted edits, not unflushed hotbar/page changes;
    owner input must stop the route before it can change those in the client.
    """
    key_name: str
    confirmation_id: str
    configuration_sha256: tuple

    @classmethod
    def configured(cls, key_name, *, confirmation_id, configuration_paths):
        if key_name not in HOTKEY_CODES or not isinstance(confirmation_id, str) or not confirmation_id.strip():
            raise ValueError('Explicit non-helper function key and owner setup confirmation required')
        paths = tuple(configuration_paths)
        if not paths:
            raise ValueError('Current saved client/hotbutton configuration files required')
        return cls(key_name, confirmation_id, _source_hashes(paths))

    def check(self):
        if (self.key_name not in HOTKEY_CODES or not isinstance(self.confirmation_id, str)
                or not self.confirmation_id.strip() or not self.configuration_sha256
                or _source_hashes(path for path, _ in self.configuration_sha256) != self.configuration_sha256):
            raise HotkeyStopped('Owner hotbutton setup is absent or saved configuration changed')


@dataclass(frozen=True)
class HotkeyReceipt:
    pulse: object
    released_at: float


def send_location_hotkey(sender, *, binding, owner_input, lock, clock, expires_at,
                         ensure_current, cancel, pump, record_event):
    """Send one configured key, sharing the same transaction in setup and routes.

    The caller owns the current owner request and supplies its cancellation and
    session checks. This function owns descriptor/key cleanup. It never creates
    a device, reads a location log or clears the caller's cancellation state.
    """
    if (not isinstance(binding, OwnerLocationHotkey)
            or not all(callable(value) for value in
                       (clock, ensure_current, cancel, pump, record_event))):
        raise ValueError('Owner setup binding and current request callbacks required')
    marker, fd, claimed, selected, receipt = object(), None, False, False, None
    released_at, error_text, cleanup_error = None, None, None
    original_ui = original_fd = device_identity = None
    topology = None
    code = HOTKEY_CODES[binding.key_name]

    def state_check():
        ensure_current()
        if (clock() > expires_at or sender.ui is not original_ui
                or original_ui.fileno() != original_fd or _fd_identity(original_fd) != device_identity
                or getattr(sender, '_eql_route_operation', None) is not marker):
            raise HotkeyStopped('Hotbutton owner request or sender changed')
        if (sender.unfinished or sender.dismissed
                or sender.held - ({code} if selected else set())):
            raise HotkeyStopped('Hotbutton requires idle command and key state')

    def check():
        nonlocal topology
        state_check()
        sender.check()  # Original owner-input/F9/focus checks remain active.
        state_check()
        binding.check()
        sample = owner_input.sample()
        if not isinstance(sample, OwnerInputObservation) or not sample.clear_at(clock()):
            raise HotkeyStopped('Owner activity or incomplete input observation')
        if topology is not None and sample.topology_generation != topology:
            raise HotkeyStopped('Owner input device topology changed')
        topology = sample.topology_generation
        if not sender.gate.controls_ready():
            raise HotkeyStopped('Game focus changed during hotbutton observation')
        state_check()

    def stop():
        try:
            with lock:
                check()
            return False
        except Exception as error:
            cancel(str(error))
            return True

    def select():
        nonlocal selected
        check()
        selected = True
        sender.held.add(code)
        return PulseSelection(code, .020, min(expires_at, clock()+.1))

    try:
        with lock:
            if sender is None or sender.held or getattr(sender, '_eql_route_operation', None) is not None:
                raise HotkeyStopped('Idle existing route sender required')
            original_ui = sender.ui
            original_fd = original_ui.fileno()
            device_identity = _fd_identity(original_fd)
            sender._eql_route_operation = marker
            claimed = True
            check()
            fd = os.dup(original_fd)
        receipt = selected_key_pulse_receipt(fd, select, pump=pump, should_stop=stop, go_lock=lock)
        with lock:
            check()
    except BaseException as error:
        error_text = type(error).__name__+': '+str(error)
        cancel(str(error))
        raise
    finally:
        try:
            with lock:
                if selected and fd is not None:
                    try:
                        # Always release the pinned original device, even after replacement,
                        # focus loss or F9. Never send Escape/Enter or change the target.
                        for event in ((1, code, 0), (0, 0, 0)):
                            if os.write(fd, _EVENT.pack(0, 0, *event)) != _EVENT.size:
                                raise OSError('Incomplete hotbutton release')
                        released_at = clock()
                        if (sender.ui is original_ui and original_ui.fileno() == original_fd
                                and _fd_identity(original_fd) == device_identity):
                            sender.held.discard(code)
                    except BaseException as error:
                        cleanup_error = error
                        cancel('Hotbutton release failed: '+str(error))
                record_event(dict(kind='location_hotbutton_result',
                    key_name=binding.key_name, owner_confirmation_id=binding.confirmation_id,
                    configuration_sha256=binding.configuration_sha256,
                    receipt=None if receipt is None else asdict(receipt), released_at=released_at,
                    error=error_text, cleanup_error=None if cleanup_error is None else str(cleanup_error),
                    client_effect_verified=False, chat_keys_sent=False))
        finally:
            if fd is not None:
                os.close(fd)
            if claimed and getattr(sender, '_eql_route_operation', None) is marker:
                sender._eql_route_operation = None
        if cleanup_error is not None:
            raise cleanup_error
    return HotkeyReceipt(receipt, released_at)
