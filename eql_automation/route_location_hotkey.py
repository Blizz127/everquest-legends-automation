"""Route integration for the shared owner-configured location hotbutton sender."""
from .location_hotkey import OwnerLocationHotkey, HOTKEY_CODES, send_location_hotkey
from .motion_collection import CollectionStopped, CommandReceipt, LocationRequest
from .route_session import RouteSession, RouteSessionDriver


class RouteLocationHotkeyExecutor:
    def __init__(self, engine, session, *, hotkey, owner_input):
        if (not isinstance(session, RouteSession) or session.mode != 'measurement'
                or session.lock is not getattr(engine, 'g0_stop_lock', None)
                or not isinstance(hotkey, OwnerLocationHotkey)
                or not callable(getattr(owner_input, 'sample', None))):
            raise ValueError('Measurement route, explicit owner hotbutton and input observer required')
        hotkey.check()
        self.engine, self.session, self.hotkey, self.owner_input = engine, session, hotkey, owner_input

    def request_location(self, request):
        e, s, binding = self.engine, self.session, self.hotkey
        if not isinstance(request, LocationRequest):
            raise ValueError('Location request required')
        sender, driver = e.sender, e.route_session_driver

        def current():
            s._check()
            if (s.pending is not request or s.phase != 'requesting'
                    or self.hotkey is not binding or e.route_session_driver is not driver
                    or not isinstance(driver, RouteSessionDriver) or driver.session is not s
                    or driver.sender is not sender or not driver.busy or e.sender is not sender
                    or not e._route_idle() or e.cancelled or not e.jobs.empty()
                    or e.command_recovery_pending):
                raise CollectionStopped('Route hotbutton request, owner mode or sender changed')

        def pump():
            e.pump()
            e.autopilot_tick(s.clock())

        receipt = send_location_hotkey(sender, binding=binding, owner_input=self.owner_input,
            lock=s.lock, clock=s.clock, expires_at=request.expires_at, ensure_current=current,
            cancel=s.cancel, pump=pump, record_event=s.executor_events.append)
        # The session independently accepts the fresh location reply afterward.
        return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)
