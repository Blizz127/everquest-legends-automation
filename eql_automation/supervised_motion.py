"""Concrete executors for the owner's explicitly supervised motion experiment.

Open/flat/clear ground is an owner declaration, not independently observed
collision clearance. This is measurement-only; it grants no route authority.
The existing finite collector, watchdog and release accounting remain in use.
"""
from .location_hotkey import OwnerLocationHotkey, send_location_hotkey
from .motion_collection import CommandReceipt, CollectionStopped, LocationRequest
from .motion_executors import MeasurementExecutors, MeasurementInputEvidence


class SupervisedMotionExecutors(MeasurementExecutors):
    def __init__(self, engine, session, *, hotkey, owner_input, check_current, measurement_account=None):
        from .initial_itinerary_measurement import InitialItineraryMeasurement
        if not isinstance(hotkey, OwnerLocationHotkey) or not callable(check_current):
            raise ValueError('Owner-tested hotbutton and current supervised session required')
        if (measurement_account is not None and (type(measurement_account) is not InitialItineraryMeasurement
                or measurement_account.session is not session)):
            raise ValueError('Initial measurement accounting must own the exact experiment')
        self.hotkey, self.owner_input, self.check_current = hotkey, owner_input, check_current
        self.measurement_account = self._measurement_account = measurement_account
        super().__init__(engine, session, check_input=self._observe_pulse)

    def _account(self):
        if (self.measurement_account is not self._measurement_account
                or self._measurement_account is not None and self._measurement_account.session is not self.session):
            if self._measurement_account is not None:
                self._measurement_account.cancel('Initial measurement account changed')
            raise CollectionStopped('Initial measurement account changed')
        if self.measurement_account is not None:
            self.measurement_account.check()
        return self.measurement_account

    def _observe_pulse(self, request, phase, submission):
        if phase not in ('pulse_start', 'pulse_held', 'pulse_end') or submission is not None:
            raise CollectionStopped('Supervised movement observer cannot authorize typed commands')
        began = self.session.clock()
        self.check_current()
        account = self._account()
        limit = min(request.expires_at+.2 if phase != 'pulse_start' else request.expires_at, began+.1)
        if account is not None:
            limit = min(limit, account.observe(request, phase))
        return MeasurementInputEvidence(request, phase, began,
            limit,
            'owner-supervised-open-ground', None)

    def run_pulse(self, request):
        account = self._account()
        try:
            released = super().run_pulse(request)
            self._account()
            if account is not None:
                account.released(request, released)
            return released
        except BaseException as error:
            if account is not None:
                account.cancel(error)
            raise

    def request_location(self, request):
        if not isinstance(request, LocationRequest):
            raise ValueError('Location request required')
        e, s, binding = self.engine, self.session, self.hotkey
        sender, driver = e.sender, self._bound_driver()

        def current():
            s._check()
            self.check_current()
            self._account()
            if (s.pending is not request or s.phase != 'requesting'
                    or self._bound_driver() is not driver or e.sender is not sender
                    or self.hotkey is not binding or e.cancelled or not e.jobs.empty()):
                raise CollectionStopped('Supervised location request revoked')

        def pump():
            e.pump()
            e.autopilot_tick(s.clock())

        account = self._account()
        deadline = {} if account is None else dict(release_deadline=account.release_deadline)
        receipt = send_location_hotkey(sender, binding=binding, owner_input=self.owner_input,
            lock=s.lock, clock=s.clock, expires_at=request.expires_at, ensure_current=current,
            cancel=s.cancel if account is None else account.cancel,
            pump=pump, record_event=s.executor_events.append, **deadline)
        return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)
