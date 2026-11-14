"""Concrete executors for the owner's explicitly supervised motion experiment.

Open/flat/clear ground is an owner declaration, not independently observed
collision clearance. This is measurement-only; it grants no route authority.
The existing finite collector, watchdog and release accounting remain in use.
"""
from .location_hotkey import OwnerLocationHotkey, send_location_hotkey
from .motion_collection import CommandReceipt, CollectionStopped, LocationRequest
from .motion_executors import MeasurementExecutors, MeasurementInputEvidence


class SupervisedMotionExecutors(MeasurementExecutors):
    def __init__(self, engine, session, *, hotkey, owner_input, check_current):
        if not isinstance(hotkey, OwnerLocationHotkey) or not callable(check_current):
            raise ValueError('Owner-tested hotbutton and current supervised session required')
        self.hotkey, self.owner_input, self.check_current = hotkey, owner_input, check_current
        super().__init__(engine, session, check_input=self._observe_pulse)

    def _observe_pulse(self, request, phase, submission):
        if phase not in ('pulse_start', 'pulse_held', 'pulse_end') or submission is not None:
            raise CollectionStopped('Supervised movement observer cannot authorize typed commands')
        began = self.session.clock()
        self.check_current()
        return MeasurementInputEvidence(request, phase, began,
            min(request.expires_at+.2 if phase != 'pulse_start' else request.expires_at, began+.1),
            'owner-supervised-open-ground', None)

    def request_location(self, request):
        if not isinstance(request, LocationRequest):
            raise ValueError('Location request required')
        e, s, binding = self.engine, self.session, self.hotkey
        sender, driver = e.sender, self._bound_driver()

        def current():
            s._check()
            self.check_current()
            if (s.pending is not request or s.phase != 'requesting'
                    or self._bound_driver() is not driver or e.sender is not sender
                    or self.hotkey is not binding or e.cancelled or not e.jobs.empty()):
                raise CollectionStopped('Supervised location request revoked')

        def pump():
            e.pump()
            e.autopilot_tick(s.clock())

        receipt = send_location_hotkey(sender, binding=binding, owner_input=self.owner_input,
            lock=s.lock, clock=s.clock, expires_at=request.expires_at, ensure_current=current,
            cancel=s.cancel, pump=pump, record_event=s.executor_events.append)
        return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)
