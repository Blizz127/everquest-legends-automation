"""Keep a live-observed zone across passive tracking and route startup.

The tracker starts at EOF in the expected character log. It never scans old
zone entries, trusts the helper's historical ``zone`` field, or sends input.
An exclusive lease hands the *same reader* to height/route startup so its zone
is retained without replaying positions. The lease is in-memory and bound to
this helper's current settings and game process; it cannot survive a restart.
"""
from pathlib import Path
import time

from .location_log import LocationLogReader
from .motion_collection import immutable_binding
from .owner_navigation_preflight import window_identity


class ZoneReaderLease:
    """Exclusive, revocable access to the tracker reader; no movement permit."""

    def __init__(self, tracker):
        self._tracker = tracker
        self.reader = tracker.reader
        self.owner_binding = tracker.owner_binding
        self.active = True

    def check(self):
        tracker = self._tracker
        if (not self.active or tracker.lease is not self
                or tracker.reader is not self.reader):
            raise ValueError('Current-zone reader lease ended')
        tracker.check_binding()
        return self.owner_binding

    def release(self):
        """Return ownership, including after cancellation; safe in finally."""
        self.active = False
        if self._tracker.lease is self:
            self.reader.latest = None
            self._tracker.lease = None


class LiveZoneTracker:
    """One helper/game binding; passive polls stop while the reader is leased."""

    def __init__(self, log_path, zone_names_path, *, expected_character,
                 expected_server, binding_reader, clock=time.monotonic):
        if not callable(binding_reader) or not callable(clock):
            raise ValueError('Current game binding and clock required')
        self.binding_reader, self.clock = binding_reader, clock
        self.owner_binding = binding_reader()
        if not immutable_binding(self.owner_binding):
            raise ValueError('Immutable game/character binding required')
        self.reader = LocationLogReader(Path(log_path), Path(zone_names_path),
            expected_character=expected_character, expected_server=expected_server)
        self.lease = None
        self.closed = False
        self.check_binding()

    def close(self):
        self.closed = True
        self.reader._clear_zone()
        self.revoke_lease()

    def revoke_lease(self):
        if self.lease is not None:
            self.lease.active = False
            # Do not poll its cursor until the borrower finishes cleanup.

    def check_binding(self):
        if self.closed:
            raise ValueError('Current-zone tracker closed')
        try:
            if self.binding_reader() != self.owner_binding:
                raise ValueError('Game process or character settings changed')
        except Exception:
            self.close()
            raise
        return self.owner_binding

    def poll(self):
        self.check_binding()
        if self.lease is not None:
            return  # The height/route consumer alone may advance this reader.
        try:
            self.reader.poll(now=self.clock())
            self.check_binding()
        except Exception:
            self.close()
            raise

    def acquire(self):
        if self.lease is not None:
            raise ValueError('Current-zone reader already leased')
        self.poll()
        reader = self.reader
        if (reader.zone_id is None or reader.zone_display_name is None
                or reader.tail.identity is None or reader.tail.partial):
            raise ValueError('A complete live-observed zone entry is required')
        # Discard positions consumed during passive tracking. The route's height
        # startup must obtain its own new stopped pair after this handoff.
        reader.latest = None
        self.lease = ZoneReaderLease(self)
        return self.lease


def owner_zone_binding(engine):
    settings = engine.settings
    return (str(Path(settings.game_dir).resolve()), settings.character,
            settings.server, *window_identity(engine.gate, require_focus=False))


def make_zone_tracking_engine(base_engine, *, clock=time.monotonic):
    """Observe from actual helper log ticks; never create a sender or device.

    A missing window/catalog/log is reported in the trace and leaves zone
    unknown. It does not interrupt assist. Existing route cancellation still
    owns movement cleanup; invalidation also revokes its reader lease.
    """
    class ZoneTrackingEngine(base_engine):
        def __init__(self, *args, **kwargs):
            self.live_zone_tracker = None
            self._live_zone_status = None
            super().__init__(*args, **kwargs)

        def _zone_status(self, reason=None):
            tracker = self.live_zone_tracker
            reader = None if tracker is None or tracker.closed else tracker.reader
            state = (reason, None if reader is None else reader.zone_id,
                     None if reader is None else reader.zone_display_name,
                     None if reader is None else reader.zone_generation)
            if state != self._live_zone_status:
                self._live_zone_status = state
                self.trace('current_zone_tracking', reason=reason, zone_id=state[1],
                    zone_display_name=state[2], zone_generation=state[3],
                    source='appended_zone_entry', game_input_sent=False,
                    movement_authorized=False)

        def _close_zone_tracker(self):
            tracker, self.live_zone_tracker = self.live_zone_tracker, None
            if tracker is not None:
                tracker.close()

        def _service_zone_tracker(self):
            try:
                if self.stopping:
                    raise ValueError('Helper stopping')
                binding = owner_zone_binding(self)
                tracker = self.live_zone_tracker
                if tracker is not None and (tracker.closed or tracker.owner_binding != binding):
                    self._close_zone_tracker()
                    tracker = None
                if tracker is None:
                    game = Path(self.settings.game_dir)
                    self.live_zone_tracker = LiveZoneTracker(
                        game/'Logs'/f'eqlog_{self.settings.character}_{self.settings.server}.txt',
                        game/'Resources/ZoneNames.txt',
                        expected_character=self.settings.character,
                        expected_server=self.settings.server,
                        binding_reader=lambda: owner_zone_binding(self), clock=clock)
                self.live_zone_tracker.poll()
                self._zone_status()
            except Exception as error:
                self._close_zone_tracker()
                self._zone_status(str(error))

        def read_log(self):
            # Initialize before the inherited consumer can handle a transition.
            # The two tails have independent cursors; neither steals its lines.
            self._service_zone_tracker()
            result = super().read_log()
            # Inherited processing may change settings or reenter through pump.
            if self.live_zone_tracker is not None:
                try:
                    self.live_zone_tracker.check_binding()
                except Exception as error:
                    self._close_zone_tracker()
                    self._zone_status(str(error))
            return result

        def lease_current_zone(self):
            request = (self.cancel_generation, self.route_session_epoch)
            def check():
                if (self.measurement_only is not True or not self._route_idle()
                        or self.cancelled or not self.jobs.empty()
                        or self.route_session_driver is not None
                        or request != (self.cancel_generation, self.route_session_epoch)):
                    raise ValueError('Idle measurement route startup required')
            check()
            self._service_zone_tracker()
            if self.live_zone_tracker is None:
                raise ValueError('Current-zone tracking unavailable')
            lease = self.live_zone_tracker.acquire()
            try:
                check()
                lease.check()
            except Exception:
                lease.release()
                raise
            return lease

        def _revoke_zone_lease(self):
            if self.live_zone_tracker is not None:
                self.live_zone_tracker.revoke_lease()

        def post(self, name, value=None):
            self._revoke_zone_lease()
            return super().post(name, value)

        def stop_action(self, reason, *, keep_autopilot=False):
            self._revoke_zone_lease()
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            self._revoke_zone_lease()
            return super().stop_autopilot(reason)

        def run(self):
            try:
                return super().run()
            finally:
                self._close_zone_tracker()

    return ZoneTrackingEngine
