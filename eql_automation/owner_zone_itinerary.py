"""Explicit multi-zone owner job on one sender, generation and root budget.

The provider resolves copied assets and independently declared motion bounds
before input. This wrapper never posts a second travel job or turns arrival
metadata into a calibration. The continuation owns fresh destination probes.
"""
from copy import deepcopy
from dataclasses import dataclass

from .flat_record import flat_record_state
from .journey_input_budget import JourneyInputBudget
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_trial import SOURCE_JOB
from .route_step_sender import _fd_identity
from .zone_itinerary_budget import ZoneItineraryBudget


ITINERARY_JOB = 'zone_itinerary'


@dataclass
class _ItineraryOwner:
    engine: object
    plan: object
    request_bytes: bytes
    generation: int
    settings: tuple
    epochs: tuple
    sender: object
    ui: object
    gate: object
    tracker: object
    reader: object
    window: tuple
    fd: int
    fd_identity: tuple
    root: object = None
    journey: object = None
    pending: object = None
    initial_account: object = None
    starting: bool = True
    closed: bool = False

    def __post_init__(self):
        self._state = self._identity()
        self._root = self._journey = self._pending = self._initial_account = None

    def _identity(self):
        return (id(self.engine), id(self.plan), self.request_bytes, self.generation,
            self.settings, self.epochs, id(self.sender), id(self.ui), id(self.gate),
            id(self.tracker), id(self.reader), self.window, self.fd, self.fd_identity)

    def binding(self):
        e = self.engine
        window = window_identity(e.gate, require_focus=False)
        descriptor = self.ui.fileno()
        descriptor_identity = _fd_identity(self.fd)
        settings = settings_identity(e.settings)
        queue_empty = e.jobs.empty()
        root = self.root
        if (type(root) is ZoneItineraryBudget and root is self._root
                and root.declaration is self.plan.declaration and root._checking):
            # Root.check pins every declaration/leg field before and after
            # this callback. Recheck the other plan pins here without walking
            # those same legs again inside deeply nested source observations.
            state = (id(self.plan.probe_bounds), flat_record_state(self.plan.probe_bounds),
                self.plan.bounds_basis, id(self.plan.destination_provider),
                id(self.plan.sections_provider), id(self.plan.crossing_provider))
            if state != self.plan._state[1:]:
                raise ValueError('Selected itinerary plan changed')
        else:
            self.plan.check()
        if (self.closed or e.zone_itinerary_owner is not self or self._identity() != self._state
                or self.root is not self._root or self.journey is not self._journey
                or self.pending is not self._pending or self.initial_account is not self._initial_account
                or self.generation != e.cancel_generation or self.settings != settings
                or self.epochs != (e.supervised_epoch, e.route_session_epoch)
                or e.sender is not self.sender or self.sender.ui is not self.ui
                or e.gate is not self.gate or e.live_zone_tracker is not self.tracker
                or self.tracker.reader is not self.reader or self.tracker.closed
                or descriptor != self.fd or descriptor_identity != self.fd_identity
                or window != self.window or e.stopping or not queue_empty
                or self.sender.unfinished or self.sender.dismissed
                or not self.starting and e.cancelled
                or self.journey is None and e.journey is not None
                or self.journey is not None and (e.journey is not self.journey
                    or self.journey.generation != self.generation or self.journey.settings != self.settings
                    or self.journey.continue_camps is not False or self.journey._continue_camps is not False)):
            raise ValueError('Itinerary owner, generation, process, request or sender changed')
        # Zone, lease and leg-specific child phases legitimately change.
        return (id(self), self.generation, self.settings, self.epochs, id(self.sender),
                id(self.ui), id(self.gate), id(self.tracker), id(self.reader), self.window)

    def check(self):
        if self.root is not None:
            # Root.check charges this binding reader's time between its clock
            # reads. Keep a final owner check after the root's last callback.
            self.root.check()
        return self.binding()

    def adopt_journey(self, journey):
        if self.journey is None:
            self.journey = self._journey = journey
        elif self.journey is not journey:
            raise ValueError('Itinerary cannot adopt a replacement journey')
        self.check()

    def adopt_pending(self, pending):
        if self.pending is None:
            self.pending = self._pending = pending
        elif self.pending is not pending:
            raise ValueError('Itinerary cannot adopt a replacement initial request')


def make_zone_itinerary_engine(base, *, itinerary_provider, clock):
    if not callable(itinerary_provider) or not callable(clock):
        raise ValueError('Explicit itinerary provider and clock required')

    class ZoneItineraryEngine(base):
        def __init__(self, *args, **kwargs):
            self.zone_itinerary_owner = None
            self.zone_itinerary_run = None
            self._zone_itinerary_stopping = None
            super().__init__(*args, **kwargs)

        def _supervised_job_names(self):
            return (*super()._supervised_job_names(), ITINERARY_JOB)

        def post(self, name, value=None):
            if name == ITINERARY_JOB:
                value = deepcopy(value)
            return super().post(name, value)

        def _itinerary_current(self):
            owner = self.zone_itinerary_owner
            if owner is None:
                raise ValueError('No retained explicit zone itinerary owner')
            return owner.check()

        def handle_job(self, name, value):
            if name != ITINERARY_JOB:
                return super().handle_job(name, value)
            from .zone_itinerary_runtime import ZoneItineraryPlan
            if type(value) is not dict or set(value) != {'declaration', 'epoch', 'generation', 'settings'}:
                return
            token = (value['generation'], value['epoch'], self.route_session_epoch,
                     value['settings'], self.sender, self.gate)
            settings = settings_identity(self.settings)
            busy = self._navigation_busy()
            if token != (self.cancel_generation, self.supervised_epoch, self.route_session_epoch,
                         settings, self.sender, self.gate):
                return
            if self.journey is not None or busy or self.zone_itinerary_owner is not None:
                self.stop_action('Stop the current activity before requesting a zone itinerary')
                return
            declaration = value['declaration']
            owner = None
            try:
                if (type(declaration) is not dict or declaration.get('open_flat_clear') is not True
                        or declaration.get('owner_supervised_continuation') is not True):
                    raise ValueError('Explicit initial ground and destination supervision declarations required')
                request = encoded(declaration)
                if not 0 < len(request) <= 16384:
                    raise ValueError('Finite explicit itinerary declaration required')
                plan = itinerary_provider(self, deepcopy(declaration))
                if type(plan) is not ZoneItineraryPlan:
                    raise ValueError('Pinned explicit zone itinerary plan required')
                plan.check()
                tracker = self.live_zone_tracker
                sender, gate = token[4:]
                if tracker is None or tracker.closed or sender is None or sender.held:
                    raise ValueError('Observed current zone and released tested sender required')
                reader = tracker.reader
                first = plan.declaration.legs[0]
                if (reader.zone_id, reader.zone_display_name) != (first.source_zone_id, first.source_name):
                    raise ValueError('Itinerary first leg does not match the observed current zone')
                ui = sender.ui
                window = window_identity(gate, require_focus=False)
                descriptor = ui.fileno()
                descriptor_identity = _fd_identity(descriptor)
                settings = settings_identity(self.settings)
                queue_empty = self.jobs.empty()
                busy = self._navigation_busy()
                # Providers and descriptor/window/queue reads can reenter F8/F9.
                # Pin the original request only after every callback finishes.
                if (token != (self.cancel_generation, self.supervised_epoch, self.route_session_epoch,
                              settings, self.sender, self.gate)
                        or self.stopping or not queue_empty or self.journey is not None or busy
                        or self.zone_itinerary_owner is not None or self.live_zone_tracker is not tracker
                        or tracker.closed or tracker.reader is not reader or sender.ui is not ui):
                    raise ValueError('Itinerary cancelled while its copied plan was loading')
                owner = _ItineraryOwner(self, plan, request, token[0], token[3], (token[1], token[2]),
                    sender, ui, gate, tracker, reader, window, descriptor, descriptor_identity)
                self.zone_itinerary_owner = owner
                binding = owner.binding()
                owner.root = owner._root = ZoneItineraryBudget(plan.declaration, clock=clock,
                    stop_lock=self.g0_stop_lock, owner_binding=binding, binding_reader=owner.binding)
                owner.check()
                delegated = dict(value, declaration=dict(open_flat_clear=True,
                    destination_id=first.destination_id, continue_camps=False))
                result = super().handle_job(SOURCE_JOB, delegated)
                owner.starting = False
                if self.zone_itinerary_owner is not owner:
                    return result
                if self.journey is None or self.supervised_motion is None:
                    raise ValueError('Initial itinerary measurement did not start')
                owner.check()
                self.trace('zone_itinerary_started', itinerary=plan.declaration.record_id,
                    root=owner.root.snapshot(), real_client_accepted=False)
                self.emit('Zone itinerary active · one trip budget · F8 assist / F9 or F11 stop.')
                return result
            except BaseException as error:
                if owner is not None and self.zone_itinerary_owner is owner:
                    self.stop_action(str(error))
                self.emit('Zone itinerary did not start: '+str(error))

        def _prepare_supervised_job(self, name):
            owner = self.zone_itinerary_owner
            if owner is not None:
                if name != SOURCE_JOB:
                    raise ValueError('Itinerary only adopts its initial source job')
                owner.adopt_journey(self.journey)
            recipe = super()._prepare_supervised_job(name)
            if owner is not None:
                owner.check()
                if recipe['destination'].destination_id != owner.root.leg.destination_id:
                    raise ValueError('Initial source assets differ from the itinerary first leg')
                recipe['maximum_seconds'] = min(recipe['maximum_seconds'], owner.root.expires_at-recipe['started'])
                if recipe['maximum_seconds'] <= 0:
                    raise ValueError('Itinerary expired during initial source preparation')
            return recipe

        def _supervised_current(self, pending, *, active):
            owner = self.zone_itinerary_owner
            if owner is not None:
                owner.adopt_pending(pending)
                owner.check()
            result = super()._supervised_current(pending, active=active)
            if owner is not None:
                owner.check()
            return result

        def _supervised_measurement_account(self, pending, session):
            owner = self.zone_itinerary_owner
            if owner is None:
                return super()._supervised_measurement_account(pending, session)
            from .initial_itinerary_measurement import InitialItineraryMeasurement
            owner.check()
            if pending is not owner.pending or owner.initial_account is not None:
                raise ValueError('Initial itinerary measurement accounting cannot restart')
            account = InitialItineraryMeasurement(session, owner.root, bounds=owner.plan.probe_bounds,
                bounds_basis=owner.plan.bounds_basis, source_reader=owner.reader)
            owner.initial_account = owner._initial_account = account
            owner.check()
            return account

        def _trial_scope_current(self, pending):
            owner = self.zone_itinerary_owner
            if owner is not None:
                if pending is not owner.pending:
                    raise ValueError('Itinerary source request changed')
                if 'expires' in pending:
                    pending['expires'] = min(pending['expires'], owner.root.expires_at)
            result = super()._trial_scope_current(pending)
            if owner is not None:
                # The inherited check sends no input. Validate the persistent
                # root after all of its callbacks, once per scope check; this
                # path is nested repeatedly by source observation ancestry.
                owner.check()
            return result

        def _section_parent_budget(self, pending):
            owner = self.zone_itinerary_owner
            if owner is None:
                return super()._section_parent_budget(pending)
            owner.check()
            if pending is not owner.pending:
                raise ValueError('Initial itinerary section request changed')
            return owner.root

        def _source_journey_budget(self, pending):
            budget = super()._source_journey_budget(pending)
            owner = self.zone_itinerary_owner
            if owner is None:
                return budget
            owner.check()
            if pending is not owner.pending:
                raise ValueError('Initial itinerary source request changed')
            if budget is None:
                return owner.root
            if type(budget) is not JourneyInputBudget or budget.parent_budget is not owner.root:
                raise ValueError('Initial sections lost the persistent itinerary parent')
            return budget

        def _source_input_release_deadline(self, pending):
            owner = self.zone_itinerary_owner
            if owner is None:
                return super()._source_input_release_deadline(pending)
            owner.check()
            if pending is not owner.pending:
                raise ValueError('Itinerary location request changed')
            return owner.root.expires_at

        def _source_crossing_budget(self, journey, destination_id):
            owner = self.zone_itinerary_owner
            if owner is None:
                return super()._source_crossing_budget(journey, destination_id)
            owner.check()
            root = owner.root
            if journey is not owner.journey or destination_id != root.leg.destination_id:
                raise ValueError('Crossing does not belong to the itinerary active leg')
            if root.stage.phase == 'walking':
                root.advance(root.stage, 'crossing', zone_id=root.leg.source_zone_id)
            elif root.stage.phase != 'crossing':
                raise ValueError('Itinerary crossing started out of order')
            owner.check()
            return root

        def _sync_itinerary_crossing(self, runtime):
            owner = self.zone_itinerary_owner
            owner.check()
            root = owner.root
            if runtime.journey is not owner.journey or runtime.destination_id != root.leg.destination_id:
                raise ValueError('Completed crossing differs from the itinerary leg')
            # The crossing owns the evidence: an entry alone is insufficient
            # for arrival until both stopped replies and input release exist.
            runtime._advance_observed_journey()
            owner.check()

        def _finish_source_crossing(self, crossing):
            owner = self.zone_itinerary_owner
            if owner is None:
                return super()._finish_source_crossing(crossing)
            from .zone_itinerary_runtime import ZoneItineraryRuntime
            with self.g0_stop_lock:
                owner.check()
                if self.source_crossing_run is not crossing or crossing.busy or crossing.phase != 'complete':
                    raise ValueError('Itinerary crossing handoff is not idle and complete')
                crossing.check_current()
                self._sync_itinerary_crossing(crossing)
                import navigation
                from eqnav import steer
                def pump():
                    self.pump()
                    self.autopilot_tick(clock())
                runtime = ZoneItineraryRuntime(self, owner.journey, crossing,
                    plan=owner.plan, root=owner.root, check_current=owner.binding,
                    pump=pump, command_state_clear=lambda:self._route_idle() and not self.cancelled and self.jobs.empty(),
                    fit_library=navigation, steering_library=steer, clock=clock)
                try:
                    owner.check()
                    if self.source_crossing_run is not crossing or self.zone_itinerary_run is not None:
                        raise ValueError('Itinerary crossing ownership changed during transfer')
                    self.source_crossing_run = None
                    self.zone_itinerary_run = runtime
                    owner.journey.phase = 'zone_itinerary'
                    self._itinerary_current()
                except BaseException:
                    runtime.cancel('Itinerary owner changed during crossing transfer')
                    runtime.release()
                    raise
                self.trace('zone_itinerary_destination_handoff', itinerary=owner.plan.declaration.record_id,
                    root=owner.root.snapshot(), real_client_accepted=False)
                return dict(phase='zone_itinerary', camp_started=False, real_client_accepted=False)

        def _navigation_busy(self):
            return self.zone_itinerary_run is not None or super()._navigation_busy()

        def _owner_navigation_active(self):
            if self.zone_itinerary_run is not None:
                try:
                    self._itinerary_current()
                except (ValueError, AttributeError):
                    return False
                return True
            return super()._owner_navigation_active()

        def zone_changed(self, body, now):
            run = self.zone_itinerary_run
            crossing = None if run is None else run.crossing
            if crossing is not None and not crossing.closed and crossing.phase != 'stopped' and not self.cancelled:
                expected = 'You have entered '+crossing.corridor_spec.destination+'.'
                if body in ('LOADING, PLEASE WAIT...', expected):
                    self.zone_loading_until = now+(2. if body == expected else 120.)
                    self.trace('owner_itinerary_transition_seen', line=body,
                        destination_id=crossing.destination_id, exclusive_arrival_reader=True, real_client_accepted=False)
                    return
            return super().zone_changed(body, now)

        def _cleanup_zone_itinerary(self):
            run = self.zone_itinerary_run
            if run is not None and not run.busy and (run.closed or run.phase == 'stopped'):
                if not run.closed:
                    run.release()
                if self.zone_itinerary_run is run:
                    self.zone_itinerary_run = None
            if self._zone_itinerary_stopping is not None and not self._navigation_busy():
                self._zone_itinerary_stopping = None

        def stop_action(self, reason, *, keep_autopilot=False):
            owner = self.zone_itinerary_owner
            if owner is not None:
                owner.closed = True
                if owner.root is not None:
                    owner.root.cancel(reason)
                    root = owner.root
                    # Display-only metadata survives owner revocation until
                    # initial or destination navigation has released input.
                    self._zone_itinerary_stopping = dict(
                        record_id=root.declaration.record_id,
                        leg=root.stage.leg_index+1, legs=len(root.declaration.legs),
                        stage='stopping', real_client_accepted=False)
            run = self.zone_itinerary_run
            if run is not None:
                run.cancel(reason)
            try:
                return super().stop_action(reason, keep_autopilot=keep_autopilot)
            finally:
                if self.zone_itinerary_owner is owner:
                    self.zone_itinerary_owner = None
                self._cleanup_zone_itinerary()

        def _finish_zone_itinerary(self, run):
            with self.g0_stop_lock:
                owner = self.zone_itinerary_owner
                if owner is None or self.zone_itinerary_run is not run:
                    return None
                owner.check()
                generation, journey = owner.generation, owner.journey
                snapshot = run.snapshot()
                owner.check()
                if (self.zone_itinerary_run is not run or run.phase != 'complete' or run.busy
                        or owner.root.stage.phase != 'complete'
                        or owner.root.stage.leg_index != len(owner.root.declaration.legs)-1):
                    raise ValueError('Itinerary completion lost its owner')
                run.release()
                owner.check()
                if self.zone_itinerary_run is not run:
                    return None
                self.zone_itinerary_run = None
                result = dict(phase='zone_itinerary_complete', itinerary=snapshot,
                    destination_zone=owner.root.leg.destination_zone, camp_started=False, real_client_accepted=False)
                self.zone = owner.root.leg.destination_zone
                self.stop_action('Zone itinerary complete · movement stopped')
                if (self.cancel_generation != generation+1 or self.journey is not None
                        or self.zone_itinerary_run is not None or self._journey_assist is not None or self.active):
                    return None
                self.journey_last_result = result
                self.trace('zone_itinerary_completed', **result)
                self.emit('Zone itinerary complete · movement stopped.')
                return result

        def autopilot_payload(self):
            data = super().autopilot_payload()
            owner = self.zone_itinerary_owner
            if owner is not None and owner.root is not None:
                root = owner.root
                data['zone_itinerary'] = dict(record_id=owner.plan.declaration.record_id,
                    leg=root.stage.leg_index+1, legs=len(root.declaration.legs), stage=root.stage.phase,
                    budget=root.snapshot(), real_client_accepted=False)
            if self._zone_itinerary_stopping is not None and self._navigation_busy():
                data.update(zone_itinerary=dict(self._zone_itinerary_stopping),
                    journey_phase='zone_itinerary', state='stopping', phase='Releasing itinerary input')
            elif self.zone_itinerary_run is not None:
                data.update(journey_phase='zone_itinerary', state='running',
                            phase='Zone itinerary · '+self.zone_itinerary_run.phase)
            return data

        def autopilot_tick(self, now):
            self._cleanup_zone_itinerary()
            result = super().autopilot_tick(now)
            owner = self.zone_itinerary_owner
            if owner is None:
                return result
            try:
                owner.check()
                run = self.zone_itinerary_run
                crossing = self.source_crossing_run
                if crossing is not None and not crossing.busy:
                    self._sync_itinerary_crossing(crossing)
                if run is not None and not run.busy:
                    run.tick()
                    if run.phase == 'complete':
                        self._finish_zone_itinerary(run)
                elif not self._navigation_busy() and not owner.starting:
                    self.stop_action('Itinerary child stopped before its next checked handoff')
            except BaseException as error:
                if self.zone_itinerary_owner is owner:
                    self.stop_action(str(error))
                self.emit('Zone itinerary stopped: '+str(error))
            finally:
                self._cleanup_zone_itinerary()
            return result

    return ZoneItineraryEngine
