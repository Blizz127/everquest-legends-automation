"""One owner helper: supervised source travel, then a stationary spell camp.

Only an explicit travel job opens navigation. Arrival is an in-memory stopped
receipt from that same job; saved reports cannot start a camp. No login or game
launch, and no claim that copied geometry establishes live camp safety.
"""
from dataclasses import dataclass, field
import json
import time

from .navigation_phase import navigation_active
from .owner_camp_runtime import make_owner_camp_engine
from .owner_location_hotkey_test import HOTKEY_TEST_JOB
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_trial import SOURCE_JOB, make_owner_route_trial_engine, zone_binding
from .source_walk_driver import SourceWalkFinished
from .source_destinations import destination_spec
from .camp_motion_continuity import CampInputContinuity, arrival_motion_basis
from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_contact_checkpoint import CampContactCheckpoint
from .source_contact_controller import SourceContactArrival
from .source_arrival import arrival_reference,arrival_itinerary,validate_contact_completion,assert_retained_arrival
from .owner_camp_position import make_camp_position_engine


@dataclass
class Journey:
    generation: int
    settings: tuple
    phase: str
    candidates: tuple = ()
    destination_id: str = 'slave-mines'
    destination_assets: object = None
    camp_motion: object = None
    arrival_floor: object = None
    location_binding: object = None
    height_check_done: bool = False
    last_considered_level_advance: object = None
    continue_camps: bool = False
    walking: object = None
    _continue_camps: bool = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.continue_camps) is not bool:raise ValueError('Explicit camp continuation choice required')
        self._continue_camps=self.continue_camps


@dataclass(frozen=True)
class Arrival:
    journey: Journey
    pending: dict
    runtime: object
    receipt: object
    tracker: object
    zone: tuple
    window: tuple
    sender: object
    gate: object
    captured_at: float
    destination_id: str
    destination: object
    source_evidence: bytes
    motion_basis: bytes
    floor_checkpoint: object


def make_owner_journey_engine(base_engine, *, client, clock=time.monotonic,
                              camp_options=None, camp_probe_plan_provider=None,
                              section_provider=None, camp_section_provider=None, **route_options):
    movement = make_owner_route_trial_engine(base_engine, clock=clock, **route_options)
    options = dict(repeat=True, auto_prepare=True)
    options.update(camp_options or {})
    camp = make_owner_camp_engine(movement, client=client, clock=clock, **options)

    class OwnerJourneyEngine(camp):
        def __init__(self, *args, **kwargs):
            self.journey = None
            self.journey_last_result = None
            self._journey_assist = None
            # Remains latched across route cleanup: F11 DOWN can be noticed by
            # the physical-input observer before native F11 RELEASE is handled.
            self._journey_f11_release = False
            super().__init__(*args, **kwargs)

        def _owner_navigation_active(self):
            j = self.journey
            return (j is not None and j.phase in {'setup', 'travel'}
                    and j.generation == self.cancel_generation
                    and j.continue_camps is j._continue_camps
                    and (j.destination_assets is None or j.destination_assets.destination_id==j.destination_id)
                    and j.settings == settings_identity(self.settings) and not self.stopping)

        def post(self,name,value=None):
            # GUI state/caller-owned dictionaries cannot change an already queued choice.
            if name==SOURCE_JOB and isinstance(value,dict):value=dict(value)
            return super().post(name,value)

        def _navigation_busy(self):
            return any(getattr(self, name, None) is not None for name in (
                'route_trial', 'supervised_motion', 'motion_collection_driver',
                'route_session_driver', 'hotkey_test'))

        def autopilot_payload(self):
            data = super().autopilot_payload()
            if self.journey is not None:
                data['journey_phase'] = self.journey.phase
                data['journey_destination_id'] = self.journey.destination_id
                data['journey_continue_camps'] = self.journey.continue_camps
                if self.journey.camp_motion is not None:
                    data['camp_input_continuity']=self.journey.camp_motion.snapshot()
            data['journey_last_result'] = self.journey_last_result
            return data

        def stop_action(self, reason, *, keep_autopilot=False):
            j, self.journey = self.journey, None
            self._journey_assist = None
            continuity=None
            if j is not None and j.camp_motion is not None:
                monitor,j.camp_motion=j.camp_motion,None
                try:monitor.close(reason)
                except Exception as error:reason=str(reason)+'; camp input cleanup: '+str(error)
                continuity=monitor.snapshot(include_basis=True)
                self.trace('journey_camp_input_closed',**continuity)
            if j is not None and j.arrival_floor is not None:
                checkpoint,j.arrival_floor=j.arrival_floor,None
                checkpoint.invalidate(reason)
            if j is not None:
                self.journey_last_result = dict(phase='stopped', reason=str(reason),
                    prior_phase=j.phase,destination_id=(j.destination_id if j.destination_assets is None
                        else j.destination_assets.destination_id),camp_input_continuity=continuity,
                    real_client_accepted=False)
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            if self.journey is not None or self._navigation_busy() or self._journey_f11_release:
                return self.stop_action(reason)
            return super().stop_autopilot(reason)

        def autopilot_hotkey_released(self):
            # The packaged native input loop calls this after its ordinary
            # physical-key bookkeeping and release deduplication. GUI stops
            # must not consume a native key release which is still outstanding.
            if self._journey_f11_release:
                self._journey_f11_release = False
                return self.stop_action('F11 OFF · travel/camp cancelled')
            if self.autopilot_running() or self.deferred in {'autopilot_start', 'stationary_camp_start'}:
                return self.stop_autopilot('F11 OFF · camp cancelled')
            if self.gate.controls_ready() and not self.preparing and not self.stop_keys_held():
                self.jobs.put(('autopilot_start', self.cancel_generation))

        def handle_job(self, name, value):
            if name == 'quit':
                self.stopping = True
                self.stop_action('Helper closing · travel/camp cancelled'); return
            if name == 'autopilot_start' and self._journey_f11_release:
                self._journey_f11_release = False
                self.stop_action('F11 OFF · travel/camp cancelled'); return
            if name == 'arm' and (self.journey is not None or self._navigation_busy()):
                if type(value) is not int or value != self.cancel_generation: return
                expected = value+1
                self.stop_action('Travel OFF · releasing movement before owner-targeted assist')
                if self.cancel_generation == expected and not self.stopping:
                    self._journey_assist = (expected, settings_identity(self.settings))
                return
            if name in {SOURCE_JOB, HOTKEY_TEST_JOB}:
                if (not isinstance(value, dict) or value.get('generation') != self.cancel_generation
                        or value.get('settings') != settings_identity(self.settings)):
                    return
                if self.journey is not None or self._navigation_busy() or self.camp_session is not None:
                    self.stop_action('Stop the current activity before requesting travel/setup'); return
                selected='slave-mines';continuation=False
                if name==SOURCE_JOB:
                    declaration=value.get('declaration')
                    try:
                        if not isinstance(declaration,dict) or not set(declaration)<={'open_flat_clear','destination_id','continue_camps'}:
                            raise ValueError('Invalid source destination request')
                        selected=destination_spec(declaration.get('destination_id','slave-mines')).identifier
                        continuation=declaration.get('continue_camps',False)
                        if type(continuation) is not bool:raise ValueError('Invalid camp continuation choice')
                        if destination_spec(selected).arrival_mode=='stop' and continuation:
                            raise ValueError('The stair landing test ends on arrival; camp continuation is unavailable')
                    except ValueError as error:
                        self.emit('Travel did not start: '+str(error));return
                    value=dict(value,declaration={'open_flat_clear':declaration.get('open_flat_clear')})
                self.journey = Journey(self.cancel_generation, settings_identity(self.settings),
                    'setup' if name == HOTKEY_TEST_JOB else 'travel',destination_id=selected,
                    continue_camps=continuation)
                self._journey_f11_release = True
                result = super().handle_job(name, value)
                if not self._navigation_busy(): self.journey = None
                return result
            if self.journey is not None or self._navigation_busy():
                self.stop_action('Another owner job stopped travel; retry after release'); return
            return super().handle_job(name, value)

        def _supervised_job_names(self):
            return (SOURCE_JOB,)  # Separate movement previews retain their other jobs.

        def _prepare_supervised_job(self, name):
            recipe = super()._prepare_supervised_job(name)
            if name == SOURCE_JOB:
                j = self.journey
                destination=recipe['destination']
                if j is None or destination.destination_id!=j.destination_id:
                    raise ValueError('Loaded source destination differs from the queued choice')
                j.destination_assets=destination
                movement_only=destination_spec(j.destination_id).arrival_mode=='stop'
                candidates = () if movement_only else tuple(super()._load_camp_candidates(destination_spec(j.destination_id).zone))
                if j is None or self.journey is not j or not navigation_active(self):
                    raise ValueError('Travel cancelled while loading observed camp candidates')
                if not movement_only and not candidates:
                    raise ValueError('No observed search names in the selected zone; travel-to-camp unavailable')
                j.candidates = candidates
            return recipe

        def _trial_current(self,p):
            result=super()._trial_current(p)
            j=self.journey
            if (j is not None and p['job']==SOURCE_JOB and
                    (p['continuation']['destination'] is not j.destination_assets
                     or j.destination_assets.destination_id!=j.destination_id)):
                raise ValueError('Queued source destination changed during travel')
            return result

        def _load_camp_candidates(self, zone=None):
            j = self.journey
            if j is not None and j.phase == 'handoff': return j.candidates
            return super()._load_camp_candidates(zone)

        def _finish_hotkey_test(self, outcome, reason):
            j = self.journey
            result = super()._finish_hotkey_test(outcome, reason)
            if self.journey is j and j is not None and j.phase == 'setup': self.journey = None
            return result

        def _capture_trial_continuation(self, p):
            j = self.journey
            r = p.get('source_runtime')
            if j is None or p['job'] != SOURCE_JOB or r is None or r.phase != 'complete': return None
            r.check_current()
            receipt = r.completed_arrival
            contact=type(receipt) is SourceContactArrival
            if contact:
                validate_contact_completion(r)
            elif (type(receipt) is not SourceWalkFinished or receipt.reference is not r.ledger.reference
                    or receipt.itinerary_sha256 != r.driver.plan.sha256
                    or r.transfer is not None or r.collector is not None or r.seal is not None):
                raise ValueError('No unchanged stopped source-arrival receipt')
            final = receipt if contact else r.driver.next_action()
            if ((not contact and (type(final) is not SourceWalkFinished or final.reference is not receipt.reference))
                    or p['busy'] or self.sender.held or self.sender.unfinished
                    or getattr(self.sender, '_eql_route_operation', None) is not None
                    or self.journey is not j or not navigation_active(self)):
                raise ValueError('Arrival changed before movement release')
            tracker = self.live_zone_tracker
            if tracker is None or tracker.reader is not r.reader or r.zone[0] != destination_spec(j.destination_id).zone_id:
                raise ValueError('Current selected-zone arrival required')
            destination=p['continuation']['destination']
            if destination is not j.destination_assets or destination.destination_id!=j.destination_id:
                raise ValueError('Source destination changed before arrival')
            checkpoint=CampContactCheckpoint(r.transfer,receipt) if contact else CampFloorCheckpoint(r.ledger)
            try:
                basis=arrival_motion_basis(r,p,checkpoint)
                checkpoint.check()
                now=clock()
                assert_retained_arrival(r,receipt,checkpoint,now)
                if (self.journey is not j or j.phase!='travel' or j.generation!=self.cancel_generation
                        or j.settings!=settings_identity(self.settings) or not navigation_active(self)
                        or (not contact and r.ledger.phase!='ready') or not checkpoint.valid
                        or p['busy'] or self.sender.held or self.sender.unfinished
                        or self.live_zone_tracker is not tracker or tracker.reader is not r.reader
                        or j.destination_assets is not destination):
                    raise ValueError('Arrival changed during floor checkpoint capture')
                token = Arrival(j,p,r,receipt,tracker,r.zone,p['window'],self.sender,self.gate,now,
                    j.destination_id,destination,destination.source_evidence,basis,checkpoint)
                j.arrival_floor=checkpoint;j.phase='handoff'
                return token
            except BaseException as error:
                checkpoint.invalidate(str(error));raise

        def _arrival_current(self, token):
            j, p, r = token.journey, token.pending, token.runtime
            token.tracker.poll()
            sample = p['observer'].sample()
            veto = p['veto'].poll()
            window = window_identity(self.gate, require_focus=True)
            token.floor_checkpoint.check()
            now = clock()
            assert_retained_arrival(r,token.receipt,token.floor_checkpoint,now)
            if (self.journey is not j or j.phase != 'handoff' or j.generation != self.cancel_generation
                    or j.settings != settings_identity(self.settings) or self.route_trial is not None
                    or self._navigation_busy() or not self.jobs.empty() or self.stopping
                    or self.sender is not token.sender or self.gate is not token.gate
                    or self.sender.held or self.sender.unfinished or self.sender.dismissed
                    or getattr(self.sender, '_eql_route_operation', None) is not None
                    or window != token.window or self.live_zone_tracker is not token.tracker
                    or token.tracker.lease is not None or zone_binding(token.tracker.reader) != token.zone
                    or j.destination_id!=token.destination_id or j.destination_assets is not token.destination
                    or p['continuation']['destination'] is not token.destination
                    or token.destination.source_evidence is not token.source_evidence
                    or j.arrival_floor is not token.floor_checkpoint or not token.floor_checkpoint.valid
                    or not sample.clear_at(now) or sample.topology_generation != p['topology']
                    or not veto.continuity_available or veto.reason is not None):
                raise ValueError('Fresh arrival, owner input or released navigation scope changed')

        def _camp_start_stop(self, reason):
            j = self.journey
            if j is None or j.phase != 'handoff': return super()._camp_start_stop(reason)
            expected = j.generation+1
            # Only this intentional camp-start stop may adopt one increment.
            # Nested owner F9 uses our outer stop_action and destroys the token.
            super().stop_action(reason)
            if self.journey is not j or self.cancel_generation != expected:
                raise ValueError('Owner cancelled the travel-to-camp handoff')
            j.generation = expected

        def _continue_finished_trial(self, p, token):
            try:return self._continue_source_journey(p,token)
            except Exception as error:
                if self.journey is token.journey:self.stop_action(str(error))
                raise

        def _continue_source_journey(self,p,token):
            self._arrival_current(token)
            self.zone = destination_spec(token.destination_id).zone  # Fresh zone-bound arrival.
            if destination_spec(token.destination_id).arrival_mode=='stop':
                result=dict(phase='arrived',destination_id=token.destination_id,
                    itinerary_sha256=arrival_itinerary(token.receipt),
                    stopped_log_seq=arrival_reference(token.receipt).raw_fix.log_line_seq,
                    actual_position=arrival_reference(token.receipt).package_xyz,
                    camp_started=False,real_client_accepted=False)
                self.stop_action('Destination reached · movement stopped')
                self.journey_last_result=result
                self.trace('journey_movement_arrival',**result)
                return result
            started = self.start_stationary_camp(arrival_check=lambda:self._arrival_current(token))
            j = token.journey
            if self.journey is not j or self.cancel_generation != j.generation:
                return dict(camp_started=False, reason='Owner changed the handoff')
            if not started or self.camp_session is None:
                self.stop_action('Arrived; camp did not start'); return dict(camp_started=False)
            if (j.destination_id!=token.destination_id or j.destination_assets is not token.destination
                    or p['continuation']['destination'] is not token.destination
                    or token.destination.source_evidence is not token.source_evidence
                    or j.arrival_floor is not token.floor_checkpoint or not token.floor_checkpoint.valid):
                self.stop_action('Source destination changed during camp handoff')
                return dict(camp_started=False,reason='Destination changed before handoff commit')
            j.phase = 'camp'
            self._retain_camp_input(token)
            if self.journey is not j or not self._camp_current():
                if self.journey is j:self.stop_action('Camp input continuity changed during handoff')
                return dict(camp_started=False,reason='Camp input continuity changed')
            spec=destination_spec(token.destination_id)
            self.camp_session.progress.bind_arrival(destination_id=spec.identifier,name=spec.label,
                zone=spec.zone,itinerary_sha256=arrival_itinerary(token.receipt),
                stopped_log_seq=arrival_reference(token.receipt).raw_fix.log_line_seq)
            self.journey_last_result = dict(phase='camp', itinerary_sha256=arrival_itinerary(token.receipt),
                destination_id=token.destination_id,destination=json.loads(token.source_evidence),
                stopped_log_seq=arrival_reference(token.receipt).raw_fix.log_line_seq,
                camp_started=True, safe_camp_verified=False, real_client_accepted=False,
                camp_input_continuity=j.camp_motion.snapshot(include_basis=True))
            self.trace('journey_camp_handoff', **self.journey_last_result)
            return dict(self.journey_last_result)

        def _camp_motion_binding(self):
            tracker=self.live_zone_tracker
            lease=self._camp_location_lease()
            if (tracker is None or self.sender is None or
                    tracker.lease is not None and tracker.lease is not lease):
                raise ValueError('Camp cannot retain navigation ownership')
            if lease is not None:lease.check()
            tracker.poll()
            window=window_identity(self.gate,require_focus=True)
            return (self.sender,self.sender.ui,self.gate,tracker,tracker.reader,self.camp_session,
                self.cancel_generation,settings_identity(self.settings)[:4],
                zone_binding(tracker.reader),window)

        def _camp_location_lease(self):
            return None

        def _retain_camp_input(self,token):
            j=token.journey
            binding=self._camp_motion_binding()
            if (self.journey is not j or j.phase!='camp' or self.camp_session is None or
                    binding[0] is not token.sender or binding[2] is not token.gate or
                    binding[3] is not token.tracker or binding[8]!=token.zone or binding[9]!=token.window
                    or j.arrival_floor is not token.floor_checkpoint or not token.floor_checkpoint.valid):
                raise ValueError('Arrival input monitor lost its camp owner')
            j.camp_motion=CampInputContinuity(token.pending['observer'],topology=token.pending['topology'],
                basis=token.motion_basis,binding=binding,clock=clock,floor=token.floor_checkpoint)
            j.location_binding=token.pending['binding']

        def _camp_current(self,*,allow_pending_level=False,observe_input=True):
            if not super()._camp_current(allow_pending_level=allow_pending_level):return False
            j=self.journey;camp=self.camp_session
            if j is None or j.phase!='camp':return True
            if j.continue_camps is not j._continue_camps:return False
            monitor=j.camp_motion
            if monitor is None:return False
            try:
                if observe_input:monitor.check(self._camp_motion_binding())
                # Source route/location senders sample the exact retained
                # physical observer at admission and through release. Their
                # nested binding checks need ownership, not another recursive
                # physical sample and full historical-floor serialization.
                monitor.check_binding(self._camp_motion_binding())
                if self.journey is not j or j.camp_motion is not monitor or self.camp_session is not camp:
                    raise ValueError('Camp owner changed during input observation')
            except Exception as error:
                monitor.invalidate(str(error));camp.stop(str(error));return False
            return True

        def _finish_trial_input_observer(self,pending):
            j=self.journey
            if j is not None and j.phase=='camp' and j.camp_motion is not None and j.camp_motion.observer is pending['observer']:
                if self._camp_current():return  # Ownership transferred; no route input authority.
                self.stop_action('Camp input continuity changed at navigation cleanup')
            elif j is not None and j.arrival_floor is not None:
                self.stop_action('Camp handoff ended before floor ownership transfer')
            return super()._finish_trial_input_observer(pending)

        def start_stationary_camp(self, **kwargs):
            if self._navigation_busy() or self.journey is not None and self.journey.phase != 'handoff':
                self.emit('Camp waits for navigation to release'); return False
            return super().start_stationary_camp(**kwargs)

        def autopilot_tick(self, now):
            result = super().autopilot_tick(now)
            if self.journey is not None and self.journey.phase in {'setup', 'travel'} and not self._navigation_busy():
                self.journey = None
            pending = self._journey_assist
            if pending is not None and not self._navigation_busy():
                self._journey_assist = None
                if (pending == (self.cancel_generation, settings_identity(self.settings))
                        and not self.stopping and self.jobs.empty()
                        and self.sender is not None and not self.sender.held
                        and getattr(self.sender, '_eql_route_operation', None) is None):
                    super().handle_job('arm', pending[0])
            return result

    result=make_camp_position_engine(OwnerJourneyEngine,clock=clock,
                                    probe_plan_provider=camp_probe_plan_provider)
    if section_provider is not None:
        from .owner_walking_sections import make_walking_sections_engine
        result=make_walking_sections_engine(result,section_provider=section_provider,clock=clock)
    if camp_section_provider is not None:
        from .owner_camp_sections import make_camp_sections_engine
        result=make_camp_sections_engine(result,section_provider=camp_section_provider,clock=clock)
    return result
