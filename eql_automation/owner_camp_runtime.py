"""Owner-started stationary encounters through the retained rotation engine.

The optional repeated session recovers resources between encounters. Assist
keeps manual movement/targeting/posture; all camp input shares its stop scope.
"""
from __future__ import annotations

from datetime import datetime
import math
import time

from .camp_session import StationaryCamp, observed_candidates
from .camp_recovery import CampRecovery, PostureCommandBinding
from .location_log import NonReplayingLogTail
from .owner_gauge_lifecycle import make_owner_nov12_engine as assist_engine

CAMP_JOB = 'stationary_camp_start'


class CampLogTail:
    def __init__(self, path, engine):
        self.tail = NonReplayingLogTail(path); self.engine = engine; self.seq = 0

    def poll(self):
        rows, reset = self.tail.poll()
        camp = self.engine.camp_session
        if reset and camp is not None:
            camp.stop('Client log continuity changed')
        for raw in rows:
            self.seq += 1
            if camp is not None:
                camp.observe(raw, self.seq, self.engine.camp_clock(), self.engine.camp_wall(),
                    consider=self.engine.camp_client.consider_target,
                    safe=self.engine.camp_client.safe_leveling_target)
        return rows


def make_owner_camp_engine(base_engine, *, client, candidates_loader=None,
                           clock=time.monotonic, wall=datetime.now, repeat=False,
                           posture_loader=PostureCommandBinding):
    """Bind only to the existing owner helper; construction sends no input."""
    class OwnerCampEngine(assist_engine(base_engine)):
        camp_client = client
        camp_clock = staticmethod(clock)
        camp_wall = staticmethod(wall)

        def __init__(self, *args, **kwargs):
            self.camp_session = None; self.camp_last_result = None
            self._camp_command = None; self._camp_binding = None
            self._camp_posture = None
            self._camp_checked_at = 0.
            super().__init__(*args, **kwargs)

        def make_tail(self):
            return CampLogTail(self.log_path(), self)

        def emit(self, text=None):
            if text and self.camp_session is not None:
                text = 'CAMP TEST · '+text
            return super().emit(text)

        def post(self, name, value=None):
            if name in {CAMP_JOB, 'stationary_camp_later'} and value is None:
                value = self.cancel_generation
            return super().post(name, value)

        def handle_job(self, name, value):
            name = {'autopilot_start':CAMP_JOB, 'autopilot_later':'stationary_camp_later'}.get(name,name)
            if name in {CAMP_JOB, 'stationary_camp_later'}:
                if type(value) is not int or value != self.cancel_generation:
                    return
                if name == 'stationary_camp_later':
                    expected = value+1
                    self.stop_action('Camp countdown · focus EverQuest within four seconds')
                    due = clock()+4.
                    if self.cancel_generation == expected and not self.stopping:
                        self.deferred = CAMP_JOB; self.next_job_at = due
                    return
                return self.start_stationary_camp()
            if self.camp_session is not None and name in {'arm', 'prepare', 'prepare_later', 'heal'}:
                # Explicit assist request replaces camp, but an old queued key
                # release cannot acquire the new generation.
                if type(value) is not int or value != self.cancel_generation:
                    return
                expected = value+1
                self.stop_action('Camp OFF · switching to owner-targeted assist')
                if self.cancel_generation != expected:
                    return
                value = expected
            return super().handle_job(name, value)

        def start_stationary_camp(self):
            entry_generation = self.cancel_generation
            if (self.measurement_only or self.preparing or self.stopping or self.recorder is not None
                    or self.autopilot_running() or self.pointer is not None):
                self.emit('Camp did not start: stop the other activity first'); return False
            if not self.prepared or self.prepared_level != self.settings.level or self.rotation is None:
                self.emit('Prepare the spell bar with F6 before starting the camp test'); return False
            if not self.rotation.spell_action('nuke', self.rotation.damage_interval):
                self.emit('Camp requires a prepared general damage spell'); return False
            if type(self.settings.level) is not int or not 1 <= self.settings.level < (20 if repeat else 21):
                self.emit('Camp supports configured levels below 20 and stops new pulls at level 20'); return False
            if (not self.gate.controls_ready() or self.blocked_keys() or
                    self.sender and (self.sender.unfinished or self.sender.held)):
                self.emit('Camp did not start: focus EverQuest, close chat and release keys'); return False
            if self.cancel_generation != entry_generation:
                return False
            generation = entry_generation+1
            self.stop_action('Camp starting · spell-only · '+('repeat to level 20' if repeat else 'one kill')+' · F9 stops')
            self.read_log()  # Drain existing replies before creating this scope.
            if generation != self.cancel_generation:
                return False
            if candidates_loader is None:
                guide = client.default_guide()
                if self.zone is None:
                    self.emit('No historical zone hint for candidate names'); return False
                excluded = [t.name for c in guide.camps for t in c.targets if t.avoid]
                candidates = observed_candidates(self.log_path(), guide.zone_long(self.zone),
                    consider=client.consider_target, safe=client.safe_leveling_target, excluded=excluded)
            else:
                candidates = candidates_loader(self)
            if generation != self.cancel_generation or not self.gate.controls_ready():
                return False
            candidates = tuple(c for c in candidates if client.valid_target_name(c.name))[:8]
            if not candidates:
                self.emit('Camp did not start: no paired NPC/consider and kill evidence in this log'); return False
            try:
                posture = posture_loader(self.settings.game_dir) if repeat else None
            except (OSError,ValueError) as error:
                self.emit('Camp did not start: '+str(error));return False
            sender = self.ensure_sender()
            self.hp, self.mana = self.gate.read_gauges(self.settings.hp_region, self.settings.mana_region)
            self.last_gauge = clock()
            if generation != self.cancel_generation:
                return False
            if not self._camp_gauges_ok():
                self.emit('Camp needs readable HP ≥70% and mana ≥50%; recover before retrying'); return False
            self.reset_target(False, forget=True, clear_seen=True, clear_role=True)
            self.native_attack_off_pending = False
            camp = StationaryCamp(candidates, self.settings.level, generation, clock(), self.zone,repeat=repeat)
            binding = (sender, self.gate, self.tail, self.tail.tail.epoch,
                self.settings.character, self.settings.server, self.settings.level, self.zone)
            focused = self.gate.controls_ready(); blocked = self.blocked_keys()
            if (not focused or blocked or generation != self.cancel_generation or
                    self.camp_session is not None or self.active or self.stopping or self.preparing):
                return False
            self.camp_session = camp; self.autopilot = camp; self._camp_binding = binding
            self._camp_posture = posture
            self.cancelled = False; self.active = False; self.deferred = None
            self.trace('camp_start', **self.camp_session.snapshot())
            self.emit('Acquiring observed NPC · '+('repeated camp to level 20' if repeat else 'one kill')+' · spell-only · F9 stops')
            return True

        def _camp_gauges_ok(self):
            return all(type(v) in (float, int) and math.isfinite(v) and lower <= v <= 1.
                       for v, lower in ((self.hp, .70), (self.mana, .50)))

        def _camp_current(self, *, allow_pending_level=False):
            camp = self.camp_session
            if camp is None or not camp.running:
                return False
            focused = self.gate.controls_ready(); blocked = self.blocked_keys()
            try:
                if camp.repeat:self._camp_posture.check()
            except (OSError,ValueError,AttributeError):
                return False
            now = clock()
            current = (self.sender, self.gate, self.tail, self.tail.tail.epoch,
                self.settings.character, self.settings.server, self.settings.level, self.zone)
            binding_matches=self._camp_binding == current
            if allow_pending_level and self._camp_binding is not None:
                binding_matches=(current[:6]==self._camp_binding[:6] and current[7:]==self._camp_binding[7:] and
                    current[6]==camp.pending_level and camp.pending_level>=camp.level)
            valid = (self.camp_session is camp and camp.running and binding_matches and self.autopilot is camp and
                    self.cancel_generation == camp.generation and not self.cancelled and
                    not self.stopping and not self.measurement_only and not self.preparing and
                    not self.command_recovery_pending and self.sender is not None and
                    now-camp.started <= camp.session_seconds and focused and not blocked)
            if valid:self._camp_checked_at=now
            return valid

        def _camp_can_cast(self):
            camp = self.camp_session
            return (self._camp_current() and camp.authorized(self._camp_checked_at) and self.active and
                    self.target_ready is True and not self.target_retaliation and
                    (self.target_name or '').casefold() == (camp.requested or '').casefold())

        def owner_extra_command_permitted(self, command):
            camp = self.camp_session
            return (camp is not None and self._camp_command == command and self._camp_current() and
                    self._camp_noncast_permitted(camp,command) and self.camp_session is camp and
                    camp.running and not self.cancelled and self.cancel_generation==camp.generation)

        def _camp_noncast_permitted(self,camp,command):
            if command=='/consider':return camp.phase=='probe'
            if camp.phase=='target':return command==client.target_command(camp.requested)
            return (camp.repeat and camp.phase=='recovery' and camp.recovery is not None and
                    command==camp.recovery.command(self._camp_checked_at) and command in {'/stand','/sit on'})

        def allowed(self):
            allowed = super().allowed()  # May consume F9 and replace the scope.
            if self._camp_command is None:
                return allowed and self.camp_session is None
            camp = self.camp_session
            if not allowed or camp is None or not self._camp_current():
                return False
            if self._camp_command.startswith('/cast ') or self._camp_command == '/alt activate 6001':
                return self._camp_can_cast()
            return self.owner_extra_command_permitted(self._camp_command)

        def send(self, command):
            camp = self.camp_session
            if camp is None:
                return super().send(command)
            if command in {'/attack on', '/attack off'}:
                return None
            if self._camp_command is not None:
                raise InterruptedError('Nested camp command refused')
            casting = command.startswith('/cast ') or command == '/alt activate 6001'
            permitted = (self._camp_can_cast() if casting else self._camp_current() and
                self._camp_noncast_permitted(camp,command))
            if not permitted:
                raise InterruptedError('Camp command lost its target or owner scope')
            self._camp_command = command
            try:
                result = super().send(command)
                if self.camp_session is not camp or not self._camp_current():
                    raise InterruptedError('Camp changed during command completion')
                return result
            finally:
                self._camp_command = None

        def read_log(self):
            super().read_log()
            camp = self.camp_session
            if camp is not None:
                if camp.running and camp.pending_level is not None:
                    if not self._camp_current(allow_pending_level=True):
                        self.stop_action('Observed level changed outside the camp scope');return
                    camp.level=camp.pending_level;camp.pending_level=None;camp.level_source='client_log'
                    self._camp_binding=(*self._camp_binding[:6],camp.level,*self._camp_binding[7:])
                    self.trace('camp_level',level=camp.level,prepared_level=self.prepared_level,
                               spell_upgrades_applied=False)
                if not camp.running:
                    self.stop_action(camp.reason)
                else:
                    # Base retaliation/old target approval cannot arm the camp.
                    valid = camp.authorized(clock()) and self.target_ready is True and not self.target_retaliation
                    valid = valid and (self.target_name or '').casefold() == (camp.requested or '').casefold()
                    self.active = bool(valid)
                    if not valid:
                        self.target_ready = False

        def combat_tick(self, now):
            camp = self.camp_session
            if camp is None:
                return super().combat_tick(now)
            if not self._camp_current():
                self.stop_action('Camp scope, focus, input or time bound changed'); return
            if not self._camp_can_cast() or now < max(self.command_pause_until, self.rotation.busy_until):
                return
            if now >= camp.grant_until-2:
                return  # Refresh before typing; do not start at token expiry.
            if now-self.last_gauge > 1.5 or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in (self.hp, self.mana)):
                self.stop_action('Camp HP/mana observation became unavailable'); return
            action = self.rotation.choose(now, self.hp, self.mana, allow_offense=False)
            if action is None and self.hp > .65 and self.mana > .25 and now >= self.mana_blocked_until:
                action = self.rotation.spell_action('nuke', self.rotation.damage_interval)
            if action and self.rotation.ready(action, now):
                if action.command.startswith('/cast ') or action.command == '/alt activate 6001':
                    self.perform_action(action)

        def autopilot_tick(self, now):
            camp = self.camp_session
            if camp is None:
                return super().autopilot_tick(now)
            if not self._camp_current() or self.sender.unfinished:
                self.stop_action('Camp interrupted; explicit restart required'); return
            if camp.phase == 'loot_observation':
                self.active = False
                if now-camp.killed_at >= 2:
                    if not camp.repeat:
                        self.stop_action('One matching kill observed; camp finished; loot completion unknown')
                    elif camp.level>=camp.target_level:
                        self.stop_action('Target level observed; camp stopped; loot completion unknown')
                    elif now>=max(self.command_pause_until,self.rotation.busy_until):
                        self._camp_begin_recovery(camp,now)
                return
            if camp.repeat and camp.level>=camp.target_level and camp.engaged_name is None:
                self.stop_action('Target level observed; no further pulls');return
            if camp.phase=='recovery':
                self._camp_recovery_tick(camp,now);return
            if camp.phase=='waiting_respawn':
                if now>=camp.wait_until:camp.reset_round()
                else:return
            engaged=camp.phase in {'fight','consider','probe'} and camp.engaged_name is not None
            if engaged and camp.last_progress is not None and now-camp.last_progress > 30:
                self.stop_action('No matching spell damage for 30 seconds; camp stopped'); return
            if engaged and camp.encounter_started is not None and now-camp.encounter_started>240:
                self.stop_action('Encounter exceeded four minutes');return
            if now < max(self.command_pause_until, self.rotation.busy_until):
                return
            if camp.phase == 'fight':
                if now < camp.grant_until-2:
                    return
                self.active = False; self.target_ready = False
                camp.phase = 'probe'
            if camp.phase == 'select':
                self.active = False; self.target_ready = False
                if not self._camp_fresh_gauges(now) or not self._camp_gauges_ok():
                    self.stop_action('Recover HP/mana before the next camp attempt'); return
                name = camp.next_candidate(now)
                if name is None:
                    if not camp.running:self.stop_action(camp.reason)
                    return
                if not self.send_target(name):
                    self.stop_action('Candidate target command was refused'); return
                if self.camp_session is not camp or not self._camp_current():
                    return
                camp.phase = 'probe'
            if camp.phase == 'probe':
                self.send('/consider')
                if self.camp_session is camp and self._camp_current():
                    camp.expect_reply(self.tail.seq, clock(), wall())
            elif camp.phase == 'consider' and now-camp.reply_started > 6:
                self.stop_action('No fresh consideration reply; camp stopped')

        def _camp_begin_recovery(self,camp,now):
            if not self._camp_fresh_gauges(now):
                self.stop_action('Recovery requires fresh readable HP and mana');return
            camp.grant_until=0.;camp.phase='recovery'
            self.active=False;self.target_ready=False
            full=self.hp>=.95 and self.mana>=.90
            camp.recovery=CampRecovery(now,phase='stand_after_rest' if full else 'stand_before_sit')
            self.trace('camp_recovery_start',hp=self.hp,mana=self.mana,posture_observed=None)
            self.emit('Between fights · recovering resources · posture requested, not confirmed · F9 stops')

        def _camp_fresh_gauges(self,now):
            return (type(self.last_gauge) in (int,float) and math.isfinite(self.last_gauge) and
                    0<=now-self.last_gauge<=1.5 and all(type(v) in (int,float) and
                    math.isfinite(v) and 0<=v<=1 for v in (self.hp,self.mana)))

        def _camp_recovery_tick(self,camp,now):
            self.active=False;self.target_ready=False
            recovery=camp.recovery
            if not self._camp_fresh_gauges(now):
                self.stop_action('Recovery requires fresh readable HP and mana');return
            if now<max(self.command_pause_until,self.rotation.busy_until):return
            try:
                recovery.sample(now,self.last_gauge,self.hp,self.mana)
                command=recovery.command(now)
                if command:
                    self.send(command)
                    completed=clock()
                    if self.camp_session is not camp or not self._camp_current():return
                    recovery.submitted(command,completed)
                    if command=='/sit on':camp.rest_count+=1
                    self.trace('camp_posture_requested',command=command,posture_observed=None)
                if recovery.phase=='recovered':
                    camp.record('recovery_complete',hp=self.hp,mana=self.mana,posture_observed=None)
                    self.trace('camp_recovery_complete',hp=self.hp,mana=self.mana,posture_observed=None)
                    camp.reset_round()
                    self.reset_target(False,forget=True,clear_seen=True,clear_role=True)
                    self.native_attack_off_pending=False
            except (OSError,ValueError) as error:
                if self.camp_session is camp:self.stop_action('Recovery stopped: '+str(error))

        def stop_action(self, reason, *, keep_autopilot=False):
            camp = self.camp_session
            if camp is not None:
                camp.stop(reason)
                self.camp_last_result = camp.snapshot()
                self.trace('camp_finished', **self.camp_last_result)
                self.camp_session = None; self._camp_binding = None; self._camp_posture = None
            try:
                return super().stop_action(reason, keep_autopilot=False)
            finally:
                if self.autopilot is camp:
                    self.autopilot = None

        def stop_autopilot(self, reason):
            if self.camp_session is not None:
                return self.stop_action(reason)
            return super().stop_autopilot(reason)

        def handle_input_failure(self, error):
            if self.camp_session is not None:
                return self.stop_action('Camp input failed: '+str(error))
            return super().handle_input_failure(error)

    return OwnerCampEngine
