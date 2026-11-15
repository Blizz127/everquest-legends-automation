"""Typed progression intent contracts with synthetic owner state, without input.

These tests use real Journey/selection records. Later handoff fixtures explicitly
model ownership transitions; they do not claim route or live-client execution.
"""
from dataclasses import replace
from hashlib import sha256
import os
from queue import Queue
import threading
from types import SimpleNamespace

import pytest

import eql_automation.camp_progression as progression
from eql_automation.camp_progression import CampProgressionSelection
from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_motion_continuity import CampInputContinuity
from eql_automation.camp_recovery import CampRecovery
from eql_automation.camp_session import CampLevelAdvance, NpcCandidate, StationaryCamp
from eql_automation.camp_source_runtime import CampSourceRuntime
from eql_automation.camp_stopped_height import CampStoppedHeight
from eql_automation.flat_record import flat_record_state
from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.native_region_policy import encoded
from eql_automation.owner_camp_arrival import CampDestination
from eql_automation.owner_camp_probe import CampProbePlan
from eql_automation.owner_camp_sections import CampWalkingJourney
from eql_automation.owner_journey_runtime import Arrival, Journey
from eql_automation.owner_itinerary_camp_arrival import ItineraryCampArrival
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_route_trial import zone_binding
from eql_automation.owner_source_runtime import OwnerSourceRuntime
from eql_automation.owner_zone_tracker import LiveZoneTracker, ZoneReaderLease
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.section_continuation import SectionArrival
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot
from eql_automation.source_section_manifest import WalkingSections
from eql_automation.source_walk_driver import SourceWalkFinished
from eql_automation.zone_itinerary_budget import ZoneItineraryBudget, ZoneItineraryDeclaration, load_terminal_camp
from eql_automation.zone_itinerary_runtime import ZoneItineraryRuntime
from test_owner_zone_itinerary import synthetic_legs


PROFILE = 'butcher-newbie-goblin-slave-mines'
ITINERARY = 'butcher-goblin-gfay-crushbone-slave-mines-camp'
REQUEST = encoded(dict(progression_id=PROFILE, open_flat_clear=True,
                       owner_supervised_continuation=True))


def selection(**changes):
    fields = dict(profile_id=PROFILE, initial_destination_id='newbie-hills',
        trigger_destination_id='goblin-camp', terminal_destination_id='slave-mines',
        itinerary_id=ITINERARY, evidence=encoded(dict(synthetic=True,
            input_authorized=False, real_client_accepted=False)))
    fields.update(changes)
    return CampProgressionSelection(**fields)


@pytest.fixture
def owner(tmp_path):
    f = SimpleNamespace(now=100., selections=[], clock_hook=None)
    def clock():
        hook, f.clock_hook = f.clock_hook, None
        if hook is not None: hook()
        return f.now
    f.clock = clock
    game = tmp_path/'client'; logs = game/'Logs'; logs.mkdir(parents=True)
    log = logs/'eqlog_Probe_private.txt'; log.touch()
    names = tmp_path/'ZoneNames.txt'
    names.write_text('68^Butcherblock Mountains^0^0\n54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n')
    settings = SimpleNamespace(game_dir=str(game), character='Probe',
                               server='private', level=1)
    tracker = LiveZoneTracker(log, names, expected_character='Probe',
        expected_server='private', binding_reader=lambda:('synthetic-owner',), clock=f.clock)
    with log.open('a') as out:
        out.write('[Sun Nov 15 12:00:00 2026] You have entered Butcherblock Mountains.\n')
    tracker.poll()
    read_fd, write_fd = os.pipe()
    ui = os.fdopen(write_fd, 'wb', buffering=0)
    sender = SimpleNamespace(ui=ui, held=set(), unfinished=False, dismissed=False,
                             _eql_route_operation=None)
    window = SimpleNamespace(id=7)
    gate = SimpleNamespace(windows=lambda:[window], focused_window=lambda:window,
        game_session=lambda:dict(pid=8, start_ticks='9'), controls_ready=lambda:True)
    j = Journey(4, settings_identity(settings), 'setup',
                destination_id='newbie-hills', continue_camps=True)
    e = SimpleNamespace(settings=settings, journey=j, cancel_generation=4,
        supervised_epoch=2, route_session_epoch=3, g0_stop_lock=threading.RLock(),
        jobs=Queue(), stopping=False, cancelled=False, active=False,
        target_ready=False, preparing=False, camp_session=None, autopilot=None,
        zone_itinerary_owner=None, zone_itinerary_run=None, live_zone_tracker=tracker,
        sender=sender, gate=gate, _navigation_busy=lambda:False,
        trace=lambda *args, **kwargs:None)
    f.engine, f.journey, f.selection = e, j, selection()
    f.tracker, f.reader, f.log, f.ui, f.read_fd = tracker, tracker.reader, log, ui, read_fd
    yield f
    tracker.reader = f.reader
    tracker.close(); ui.close(); os.close(read_fd)


def capture(f):
    return progression.capture_progression_intent(f.engine, f.journey, f.selection,
                                                  REQUEST, clock=f.clock)


@pytest.fixture
def newbie_arrival(owner, tmp_path):
    """Actual owner records with an explicit geometry-free checkpoint shell.

    The controller receives a synthetic completed route; checkpoint/geometry
    validation itself is covered elsewhere. No runtime execution is implied.
    """
    f = owner; e = f.engine; j = f.journey
    f.controller = capture(f)
    with f.log.open('a') as out:
        out.write('[Sun Nov 15 12:00:00 2026] Your Location is 2.00, 4.00, 2.70\n')
    raw = f.reader.poll(now=f.now)[0]
    reference = SimpleNamespace(itinerary_sha256='a'*64, raw_fix=raw)
    floor = object.__new__(CampFloorCheckpoint)
    floor._reader = f.reader; floor._reference = reference
    floor.valid = True; floor.sha256 = 'b'*64
    floor._assert_intact = lambda:None
    observer = SimpleNamespace(close=lambda:pytest.fail('Intent controller closed physical input'))
    config = tmp_path/'synthetic-hotbutton.ini'; config.write_text('Synthetic F4 = /location\n')
    hotkey = OwnerLocationHotkey.configured('F4', confirmation_id='synthetic-progression',
                                           configuration_paths=(config,))
    binding = (e.sender, e.sender.ui, e.gate, f.tracker, f.reader, object(), 5)
    monitor = CampInputContinuity(observer, topology=1, basis=b'{}', binding=binding,
                                 clock=f.clock, floor=floor)
    lease = ZoneReaderLease(f.tracker); f.tracker.lease = lease; lease.release()
    receipt = SourceWalkFinished('a'*64, reference)
    runtime = object.__new__(OwnerSourceRuntime)
    runtime.phase = 'complete'; runtime.completed_arrival = receipt
    runtime.lease = lease; runtime.ledger = SimpleNamespace(reference=reference)
    destination = CampDestination('newbie-hills', b'{}')
    pending = dict(generation=e.cancel_generation, observer=observer, binding=hotkey)
    token = Arrival(j, pending, runtime, receipt, f.tracker,
        (68, 'Butcherblock Mountains', f.reader.zone_generation), (7, 8, 9),
        e.sender, e.gate, f.now, 'newbie-hills', destination, b'{}', b'{}', floor)
    e.cancel_generation += 1; j.generation = e.cancel_generation
    camp = StationaryCamp((NpcCandidate('a goblin', (1,), 'c'*64, ((1,2),)),),
                          e.settings.level, e.cancel_generation, f.now, 'butcher', repeat=True)
    camp.progress.bind_arrival(destination_id='newbie-hills', name='Synthetic Newbie Hills',
        zone='butcher', itinerary_sha256=receipt.itinerary_sha256, stopped_log_seq=raw.log_line_seq)
    e.camp_session = e.autopilot = camp
    j.phase = 'camp'; j.destination_assets = destination
    j.arrival_floor = floor; j.camp_motion = monitor; j.location_binding = hotkey
    f.arrival, f.camp, f.floor, f.monitor = token, camp, floor, monitor
    return f


@pytest.fixture
def goblin_arrival(newbie_arrival):
    """Synthetic two-section completion after the actual initial adoption."""
    f = newbie_arrival; e = f.engine; j = f.journey
    f.controller.adopt_camp_handoff(e, f.arrival, f.camp)
    old_camp = f.camp
    old_camp.level = e.settings.level = 5
    old_camp.level_source = 'client_log'
    old_camp.last_level_advance = CampLevelAdvance(4, 5, 20, old_camp.generation)
    guide = SourceItineraryGuide('butcher', 'a'*64, 'b'*64, 'c'*64, .1, 6.,
        (4.,4.), (SourceWalkHint((4.,2.), (4.,3.)), SourceWalkHint((4.,3.), (4.,4.))))
    guides = tuple(replace(guide, goal=op.end, operations=(op,)) for op in guide.operations)
    ranges = ((0,0), (1,1)); pin = 'd'*64
    sections = WalkingSections(guide, guides, ranges, pin,
        (_guide_snapshot(guide), tuple(_guide_snapshot(g) for g in guides), ranges, pin))
    bounds = RouteMotionBounds('synthetic-probe', 'synthetic-hypotheses',
                               .01, .15, .18, 12., .02, .01, 2., .01, .1, 6.)
    plan = CampProbePlan(bounds, b'{}', lambda tx:None, route_guide=guide,
        route_plan_factory=lambda *args:None, destination_id='goblin-camp',
        destination_evidence=b'{}', route_sections=sections)
    pending = SimpleNamespace(probe_plan=plan, probe_plan_state=plan.state(),
        journey=j, camp=old_camp, sender=e.sender, ui=e.sender.ui, gate=e.gate,
        monitor=f.monitor, hotkey=j.location_binding, tracker=f.tracker, reader=f.reader,
        window=(7,8,9), generation=e.cancel_generation, settings=settings_identity(e.settings),
        level_advance=old_camp.last_level_advance)
    pending.level_advance_state = flat_record_state(pending.level_advance)
    pending.probe_log_veto = SceneLogVeto(f.log, expected_character='Probe',
        expected_server='private', cancel_generation=e.cancel_generation, clock=f.clock)
    trip = CampWalkingJourney(pending, epochs=(e.supervised_epoch,e.route_session_epoch))
    trip.select(1)
    budget = JourneyInputBudget(JourneyBudgetDeclaration('e'*64, 'goblin-camp', 'camp',
        2, 3000., 6000, 1200., 20000.), clock=f.clock, stop_lock=e.g0_stop_lock,
        owner_binding=('synthetic-camp-sections',), binding_reader=lambda:('synthetic-camp-sections',))
    trip.budget = trip._budget = budget
    budget.cancel('Synthetic final section released'); trip.set_stage('finished')
    old_camp.stop('Synthetic actual camp retirement', now=f.now)
    floor = object.__new__(CampFloorCheckpoint)
    floor._reader = f.reader; floor._reference = f.floor._reference
    floor.valid = True; floor.sha256 = 'f'*64; floor._assert_intact = lambda:None
    receipt = SourceWalkFinished('a'*64, floor._reference)
    source = object.__new__(CampSourceRuntime)
    source.phase = 'complete'; source.completed_arrival = receipt
    source.ledger = SimpleNamespace(reference=floor._reference)
    source.lease = f.arrival.runtime.lease
    arrival = SectionArrival(source, receipt, floor, b'{}', budget, 'e'*64, [True])
    source._section_arrival = arrival
    e.cancel_generation += 1; j.generation = e.cancel_generation
    j.settings = pending.settings; j.destination_id = 'goblin-camp'
    j.destination_assets = CampDestination('goblin-camp', b'{}')
    camp = StationaryCamp(old_camp.candidates, 5, e.cancel_generation, f.now, 'butcher', repeat=True)
    camp.progress.bind_arrival(destination_id='goblin-camp', name='Synthetic Goblin Camp',
        zone='butcher', itinerary_sha256=receipt.itinerary_sha256,
        stopped_log_seq=receipt.reference.raw_fix.log_line_seq)
    monitor = CampInputContinuity(f.monitor.observer, topology=1, basis=b'{}',
        binding=(e.sender,e.sender.ui,e.gate,f.tracker,f.reader,camp,e.cancel_generation),
        clock=f.clock, floor=floor)
    e.camp_session = e.autopilot = camp
    j.arrival_floor = floor; j.camp_motion = monitor
    f.arrival, f.camp, f.floor, f.monitor, f.trip = arrival, camp, floor, monitor, trip
    return f


@pytest.fixture
def departure(goblin_arrival, request):
    f = goblin_arrival; e = f.engine; j = f.journey; camp = f.camp
    f.controller.adopt_camp_handoff(e, f.arrival, camp, trip=f.trip)
    level = getattr(request, 'param', 9)
    camp.level = e.settings.level = level
    camp.level_source = 'client_log'; camp.kills = 1; camp.phase = 'position_check'
    camp.last_level_advance = CampLevelAdvance(level-1, level, 30, e.cancel_generation)
    f.now += 1.
    recovery = camp.recovery = CampRecovery(f.now-3, phase='stand_after_rest')
    recovery.submitted('/stand', f.now-2)
    recovery.sample(f.now-.8, f.now-.8, 1., 1.)
    recovery.sample(f.now-.5, f.now-.5, 1., 1.)
    assert recovery.phase == 'recovered'
    baseline = f.reader.log_line_seq
    lease = ZoneReaderLease(f.tracker); f.tracker.lease = lease
    def position():
        with f.log.open('a') as out:
            out.write('[Sun Nov 15 12:00:01 2026] Your Location is 2.00, 4.00, 2.70\n')
        return f.reader.poll(now=f.now)[0]
    first = position(); f.now += .4; second = position()
    payload = encoded(dict(synthetic=True, input_authorized=False, real_client_accepted=False))
    height = CampStoppedHeight(f.floor, first, second, (4.,2.,.2), 2.5,
        f.now, f.now+.5, payload, sha256(payload).hexdigest())
    veto = SceneLogVeto(f.log, expected_character='Probe', expected_server='private',
                        cancel_generation=e.cancel_generation, clock=f.clock)
    pending = SimpleNamespace(journey=j, camp=camp, floor=f.floor, monitor=f.monitor,
        hotkey=j.location_binding, sender=e.sender, ui=e.sender.ui, gate=e.gate,
        tracker=f.tracker, reader=f.reader, lease=lease, cancelled=False,
        generation=e.cancel_generation, settings=settings_identity(e.settings), window=(7,8,9),
        level_advance=camp.last_level_advance, level_advance_state=flat_record_state(camp.last_level_advance),
        recovery=recovery, released_at=recovery.last_stand_completed_at,
        probe_log_veto=veto, _probe_log_veto=veto, result=height, baseline=baseline,
        probe_plan=None, probe_plan_state=None, runtime=None, route_runtime=None)
    e.camp_position = pending
    f.pending = pending
    return f


def root_for(f):
    catalog = {'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58}
    legs, _ = synthetic_legs(catalog)
    declaration = ZoneItineraryDeclaration(ITINERARY, legs, 22500., 39014, 7802.8, 130051.8,
        terminal_camp=load_terminal_camp('slave-mines', zone_catalog=catalog))
    return ZoneItineraryBudget(declaration, clock=f.clock, stop_lock=f.engine.g0_stop_lock,
        owner_binding=('synthetic-camp-root',), binding_reader=lambda:('synthetic-camp-root',))


def prepare_root(f):
    p = f.pending
    # Same typed two-section mechanics as the completed Newbie trip; the new
    # first-crossing plan is an explicit synthetic proposal, not executed.
    p.probe_plan = replace(f.trip.plan, destination_id='butcher-gfay-crossing')
    p.probe_plan_state = p.probe_plan.state()
    return root_for(f)


@pytest.fixture
def first_crossing(departure):
    f = departure; e = f.engine; j = f.journey; p = f.pending; c = f.controller
    origin = c.claim_goblin_origin(e, p)
    root = prepare_root(f); c.bind_root(origin, root)
    trip = CampWalkingJourney(p, epochs=(e.supervised_epoch,e.route_session_epoch))
    trip.select(1)
    child = JourneyInputBudget(JourneyBudgetDeclaration('e'*64,
        root.leg.destination_id, 'zone_crossing', 2, 3000., 6000, 1200., 20000.),
        clock=f.clock, stop_lock=e.g0_stop_lock, owner_binding=('synthetic-first-walk',),
        binding_reader=lambda:('synthetic-first-walk',), parent_budget=root)
    trip.budget = trip._budget = child
    floor = object.__new__(CampFloorCheckpoint)
    floor._reader = f.reader
    floor._reference = SimpleNamespace(itinerary_sha256='a'*64, raw_fix=p.result.second)
    floor.valid = True; floor.sha256 = 'f'*64; floor._assert_intact = lambda:None
    receipt = SourceWalkFinished('a'*64, floor._reference)
    source = object.__new__(CampSourceRuntime)
    source.phase = 'complete'; source.completed_arrival = receipt; source.lease = p.lease
    source.ledger = SimpleNamespace(reference=floor._reference)
    arrival = SectionArrival(source, receipt, floor, b'{}', child, 'e'*64, [True])
    source._section_arrival = arrival
    p.lease.release(); child.cancel('Synthetic final first-approach section')
    trip.set_stage('finished'); f.camp.stop('Synthetic crossing handoff', now=f.now)
    e.camp_session = e.autopilot = e.camp_position = None
    j.phase = 'source_crossing_handoff'; j.settings = p.settings
    j.destination_id = trip.destination_id; j.arrival_floor = floor
    f.root, f.crossing_trip, f.crossing_arrival = root, trip, arrival
    return f


@pytest.fixture
def terminal_transfer(first_crossing):
    """Account the remaining synthetic itinerary, retaining genuine root state."""
    f = first_crossing; e = f.engine; j = f.journey; c = f.controller; root = f.root
    c.commit_first_crossing(e, f.crossing_trip, f.crossing_arrival)
    for phase, zone_id in (('crossing',68), ('loading',None), ('arrival',54),
            ('bootstrap',54), ('walking',54), ('crossing',54), ('loading',None),
            ('arrival',58), ('bootstrap',58), ('walking',58)):
        root.advance(root.stage, phase, zone_id=zone_id)
    child = JourneyInputBudget(JourneyBudgetDeclaration('e'*64, 'slave-mines', 'camp',
        1, 1500., 3000, 600., 10000.), clock=f.clock, stop_lock=e.g0_stop_lock,
        owner_binding=('synthetic-terminal-walk',), binding_reader=lambda:('synthetic-terminal-walk',),
        parent_budget=root)
    with f.log.open('a') as out:
        out.write('[Sun Nov 15 12:00:01 2026] You have entered Clan Crushbone.\n')
        out.write('[Sun Nov 15 12:00:01 2026] Your Location is 2.00, 4.00, 2.70\n')
    raw = f.reader.poll(now=f.now)[0]
    floor = object.__new__(CampFloorCheckpoint)
    floor._reader = f.reader; floor._reference = SimpleNamespace(itinerary_sha256='a'*64, raw_fix=raw)
    floor.valid = True; floor.sha256 = 'f'*64; floor._assert_intact = lambda:None
    receipt = SourceWalkFinished('a'*64, floor._reference)
    source = object.__new__(CampSourceRuntime)
    source.phase = 'complete'; source.completed_arrival = receipt
    source.lease = f.pending.lease; source.ledger = SimpleNamespace(reference=floor._reference)
    arrival = SectionArrival(source, receipt, floor, b'{}', child, 'e'*64, [True])
    source._section_arrival = arrival
    child.cancel('Synthetic completed terminal route')
    epoch = root.stage.epoch
    root.advance(root.stage, 'arrival', zone_id=58)
    root.advance(root.stage, 'complete', zone_id=58)
    run = object.__new__(ZoneItineraryRuntime)
    run.root = root; run.closed = True; run.phase = 'terminal_transferred'
    run.engine = e; run.journey = j; run._observer_transferred = True
    monitor = CampInputContinuity(c.origin.monitor.observer, topology=1, basis=b'{}',
        binding=(e,run,j,e.sender,f.tracker,f.reader,e.cancel_generation), clock=f.clock)
    veto = SceneLogVeto(f.log, expected_character='Probe', expected_server='private',
        cancel_generation=e.cancel_generation, clock=f.clock)
    destination = CampDestination('slave-mines', b'{}')
    i = c.intent
    token = ItineraryCampArrival(run,j,arrival,destination,f.camp.candidates,monitor,
        e.sender,e.sender.ui,e.gate,f.tracker,f.reader,j.location_binding,veto,f.pending.lease,
        root,root.declaration.terminal_camp,e.cancel_generation,settings_identity(e.settings),
        zone_binding(f.reader),i.window,i.fd,i.fd_identity,f.clock,root.expires_at,epoch,
        progression_origin=c.origin)
    run.terminal_transfer = run._camp_arrival_token = token
    run.terminal_arrival = arrival
    j.destination_id = 'slave-mines'; j.destination_assets = destination
    j.arrival_floor = floor; j.camp_motion = monitor; j.phase = 'handoff'
    f.terminal_token = token
    return f


def terminal_generation_gap(f):
    token = f.terminal_token
    token._claim[0] = True
    f.engine.cancel_generation += 1; f.journey.generation = f.engine.cancel_generation


def publish_terminal_camp(f):
    token = f.terminal_token; e = f.engine; j = f.journey
    if e.cancel_generation == token.generation: terminal_generation_gap(f)
    camp = StationaryCamp(token.candidates, e.settings.level, e.cancel_generation,
                          f.now, 'crushbone', repeat=True)
    camp.progress.bind_arrival(destination_id='slave-mines', name='Synthetic Slave Mines',
        zone='crushbone', itinerary_sha256=token.arrival.receipt.itinerary_sha256,
        stopped_log_seq=token.arrival.receipt.reference.raw_fix.log_line_seq)
    monitor = CampInputContinuity(token.monitor.observer, topology=1, basis=b'{}',
        binding=(e.sender,e.sender.ui,e.gate,f.tracker,f.reader,camp,e.cancel_generation),
        clock=f.clock, floor=token.arrival.checkpoint)
    e.camp_session = e.autopilot = camp; j.camp_motion = monitor; j.phase = 'camp'
    return camp


def test_selection_is_a_pinned_proposal_without_input_authority():
    s = selection()
    before = s.state()
    s.check()
    assert s.state() == before
    assert s.profile_id == PROFILE and s.itinerary_id == ITINERARY
    assert s.initial_destination_id == 'newbie-hills'
    assert s.trigger_destination_id == 'goblin-camp'
    assert s.terminal_destination_id == 'slave-mines'


@pytest.mark.parametrize('field', ('profile_id', 'initial_destination_id',
    'trigger_destination_id', 'terminal_destination_id', 'itinerary_id'))
def test_selection_cannot_substitute_an_unregistered_progression(field):
    with pytest.raises(ValueError):
        selection(**{field: 'another-destination'}).check()


@pytest.mark.parametrize('evidence', (
    b'', b'{}', b'[]', b'not json',
    b'{"input_authorized": false, "real_client_accepted": false}',
    encoded(dict(input_authorized=True, real_client_accepted=False)),
    encoded(dict(input_authorized=0, real_client_accepted=False)),
    encoded(dict(input_authorized=False, real_client_accepted=True)),
    encoded(dict(input_authorized=False, real_client_accepted=0)),
    '{"input_authorized":false,"real_client_accepted":false}',
))
def test_selection_requires_canonical_bytes_and_explicit_non_authority(evidence):
    with pytest.raises((ValueError, TypeError)):
        selection(evidence=evidence).check()


@pytest.mark.parametrize('field,value', (
    ('profile_id', 'changed'), ('initial_destination_id', 'goblin-camp'),
    ('trigger_destination_id', 'newbie-hills'), ('terminal_destination_id', 'north-wall'),
    ('itinerary_id', 'changed'),
    ('evidence', encoded(dict(changed=True, input_authorized=False, real_client_accepted=False))),
))
def test_selection_detects_changes_after_publication(field, value):
    s = selection()
    object.__setattr__(s, field, value)
    with pytest.raises(ValueError):
        s.check()


@pytest.mark.parametrize('level', (1, 2, 3, 4))
def test_explicit_initial_capture_attaches_the_same_controller_without_new_generation(owner, level):
    f = owner; e = f.engine; j = f.journey
    e.settings.level = level; j.settings = settings_identity(e.settings)
    generation = e.cancel_generation
    controller = capture(f)
    assert j.progression is controller and j._progression is controller
    assert e.cancel_generation == generation and e.journey is j
    assert j.continue_camps is True and j._continue_camps is True
    assert e.camp_session is None and e.zone_itinerary_owner is None
    assert e.zone_itinerary_run is None and e.jobs.empty()
    assert progression.continuation_available(j)


@pytest.mark.parametrize('level', (0, 5, 9, 10, 20, 50, True, False, 1., '1', None))
def test_initial_capture_does_not_promote_configured_level_into_later_camp_progress(owner, level):
    f = owner; e = f.engine; j = f.journey
    e.settings.level = level; j.settings = settings_identity(e.settings)
    with pytest.raises(ValueError):
        capture(f)
    assert getattr(j, 'progression', None) is None
    assert getattr(j, '_progression', None) is None
    assert e.cancel_generation == 4 and e.camp_session is None


@pytest.mark.parametrize('fault', ('journey', 'generation', 'settings', 'destination',
    'continuation_false', 'continuation_pin', 'continuation_int'))
def test_initial_capture_refuses_changed_owner_or_missing_explicit_continuation(owner, fault):
    f = owner; e = f.engine; j = f.journey
    if fault == 'journey': e.journey = replace(j)
    elif fault == 'generation': e.cancel_generation += 1
    elif fault == 'settings': e.settings.character = 'Other'
    elif fault == 'destination': j.destination_id = 'goblin-camp'
    elif fault == 'continuation_false': j.continue_camps = j._continue_camps = False
    elif fault == 'continuation_pin': j._continue_camps = False
    else: j.continue_camps = j._continue_camps = 1
    with pytest.raises(ValueError):
        capture(f)
    assert getattr(j, 'progression', None) is None
    assert getattr(j, '_progression', None) is None


def test_capture_cannot_replace_an_existing_intent(owner):
    f = owner; controller = capture(f)
    with pytest.raises(ValueError):
        capture(f)
    assert f.journey.progression is controller
    assert f.journey._progression is controller
    assert progression.continuation_available(f.journey)


def test_cancellation_is_sticky_and_does_not_rewrite_owner_choice(owner):
    f = owner; controller = capture(f)
    controller.cancel('F9')
    controller.cancel('Repeated stop')
    assert not progression.continuation_available(f.journey)
    assert f.journey.continue_camps is True and f.journey._continue_camps is True
    assert f.engine.cancel_generation == 4 and f.engine.camp_session is None
    with pytest.raises(ValueError):
        capture(f)


def test_bare_continuation_boolean_is_not_a_typed_progression_authority(owner):
    assert not progression.continuation_available(owner.journey)


@pytest.mark.parametrize('fault', ('generation', 'journey', 'sender', 'gate', 'tracker',
    'reader', 'character', 'server', 'game_dir', 'epochs', 'public_controller',
    'private_controller', 'continuation', 'continuation_pin'))
def test_retained_intent_rejects_changed_owner_binding(owner, fault):
    f = owner; e = f.engine; j = f.journey; controller = capture(f)
    if fault == 'generation': e.cancel_generation += 1
    elif fault == 'journey': e.journey = replace(j)
    elif fault == 'sender': e.sender = SimpleNamespace(**vars(e.sender))
    elif fault == 'gate': e.gate = SimpleNamespace(**vars(e.gate))
    elif fault == 'tracker': e.live_zone_tracker = SimpleNamespace(**vars(f.tracker))
    elif fault == 'reader': f.tracker.reader = object()
    elif fault == 'character': e.settings.character = 'Other'
    elif fault == 'server': e.settings.server = 'another-server'
    elif fault == 'game_dir': e.settings.game_dir += '-other'
    elif fault == 'epochs': e.supervised_epoch += 1
    elif fault == 'public_controller': j.progression = object()
    elif fault == 'private_controller': j._progression = object()
    elif fault == 'continuation': j.continue_camps = False
    else: j._continue_camps = False
    with pytest.raises(ValueError):
        controller.check_binding(e)


def test_retained_binding_check_does_not_call_expired_input_providers(owner):
    f = owner; controller = capture(f)
    def forbidden(*args, **kwargs):
        pytest.fail('Passive progression binding called an input provider')
    f.engine.gate.windows = f.engine.gate.focused_window = forbidden
    f.engine.gate.game_session = forbidden
    f.tracker.binding_reader = forbidden
    controller.check_binding(f.engine)


@pytest.mark.parametrize('fault', ('selection', 'request', 'generation', 'window', 'clock', 'lock'))
def test_original_intent_record_is_immutable_after_capture(owner, fault):
    f = owner; controller = capture(f); intent = controller.intent
    if fault == 'selection': object.__setattr__(intent.selection, 'evidence', b'{}')
    elif fault == 'request': object.__setattr__(intent, 'request_bytes', encoded(dict(changed=True)))
    elif fault == 'generation': object.__setattr__(intent, 'generation', intent.generation+1)
    elif fault == 'window': object.__setattr__(intent.window, 'pid', 99)
    elif fault == 'clock': object.__setattr__(intent, 'clock', lambda:f.now)
    else: object.__setattr__(intent, 'lock', threading.RLock())
    with pytest.raises(ValueError):
        intent.check()


@pytest.mark.parametrize('fault', ('generation', 'journey', 'continuation', 'settings'))
def test_clock_callback_cannot_publish_a_cancelled_capture(owner, fault):
    f = owner; e = f.engine; j = f.journey; callbacks = []
    def clock():
        if not callbacks:
            callbacks.append(True)
            if fault == 'generation': e.cancel_generation += 1
            elif fault == 'journey': e.journey = None
            elif fault == 'continuation': j.continue_camps = False
            else: e.settings.level = 5
        return f.now
    with pytest.raises(ValueError):
        progression.capture_progression_intent(e, j, f.selection, REQUEST, clock=clock)
    assert callbacks
    assert getattr(j, 'progression', None) is None
    assert getattr(j, '_progression', None) is None


def test_actual_initial_camp_handoff_adopts_exactly_one_existing_generation(newbie_arrival):
    f = newbie_arrival; e = f.engine; c = f.controller; generation = e.cancel_generation
    assert c.adopt_camp_handoff(e, f.arrival, f.camp) is f.camp
    assert c.phase == 'newbie_camp' and c.origin is None and c.root is None
    c.check_binding(e)
    assert e.cancel_generation == generation and f.journey.generation == generation
    assert progression.continuation_available(f.journey) and not f.tracker.lease
    assert f.journey.camp_motion is f.monitor and f.journey.arrival_floor is f.floor
    with pytest.raises(ValueError):
        c.adopt_camp_handoff(e, f.arrival, f.camp)
    assert c.phase == 'newbie_camp' and e.camp_session is f.camp and f.camp.running


@pytest.mark.parametrize('fault', ('wrong_token', 'generation_skipped', 'camp_replaced',
    'camp_stopped', 'target', 'arrival_attribution', 'receipt', 'source_cancelled',
    'active_lease', 'floor', 'observer', 'expired'))
def test_initial_camp_adoption_requires_the_completed_original_handoff(newbie_arrival, fault):
    f = newbie_arrival; e = f.engine; token = f.arrival; camp = f.camp
    if fault == 'wrong_token': token = SimpleNamespace(**vars(token))
    elif fault == 'generation_skipped':
        e.cancel_generation += 1; f.journey.generation = e.cancel_generation
        camp.generation = e.cancel_generation
    elif fault == 'camp_replaced': e.camp_session = replace(camp)
    elif fault == 'camp_stopped': camp.stop('Synthetic stop', now=f.now)
    elif fault == 'target': f.journey.destination_id = 'goblin-camp'
    elif fault == 'arrival_attribution': camp.progress.arrival_destination['destination_id'] = 'goblin-camp'
    elif fault == 'receipt': token.runtime.completed_arrival = replace(token.receipt)
    elif fault == 'source_cancelled': token.runtime.phase = 'stopped'
    elif fault == 'active_lease': token.runtime.lease.active = True
    elif fault == 'floor': f.journey.arrival_floor = object()
    elif fault == 'observer': token.pending['observer'] = object()
    else: f.now = token.receipt.reference.raw_fix.received_monotonic+.501
    with pytest.raises(ValueError):
        f.controller.adopt_camp_handoff(e, token, camp)
    assert f.controller.phase == 'newbie_request'
    assert f.controller.origin is None and f.controller.root is None


@pytest.mark.parametrize('fault', ('camp_session', 'autopilot', 'camp_stopped', 'monitor',
                                  'floor', 'attribution'))
def test_adoption_clock_callback_cannot_publish_stale_camp_ownership(newbie_arrival, fault):
    f = newbie_arrival; e = f.engine; c = f.controller; fired = []
    state = c.phase, c._generation, c._adoptions
    def changed():
        fired.append(True)
        if fault == 'camp_session': e.camp_session = replace(f.camp)
        elif fault == 'autopilot': e.autopilot = replace(f.camp)
        elif fault == 'camp_stopped': f.camp.stop('Synthetic owner stop', now=f.now)
        elif fault == 'monitor': f.journey.camp_motion = object()
        elif fault == 'floor': f.journey.arrival_floor = object()
        else: f.camp.progress.arrival_destination['destination_id'] = 'goblin-camp'
    f.clock_hook = changed
    with pytest.raises(ValueError):
        c.adopt_camp_handoff(e, f.arrival, f.camp)
    assert fired and (c.phase, c._generation, c._adoptions) == state


def test_goblin_adoption_requires_the_original_finished_section_trip(goblin_arrival):
    f = goblin_arrival; generation = f.engine.cancel_generation
    assert f.controller.adopt_camp_handoff(f.engine, f.arrival, f.camp, trip=f.trip) is f.camp
    assert f.controller.phase == 'goblin_camp'
    f.controller.check_binding(f.engine)
    assert f.engine.cancel_generation == generation
    assert f.journey.continue_camps is True and f.journey._continue_camps is True
    assert f.controller.origin is None and f.controller.root is None
    with pytest.raises(ValueError):
        f.controller.adopt_camp_handoff(f.engine, f.arrival, f.camp, trip=f.trip)
    assert f.controller.phase == 'goblin_camp' and f.camp.running


@pytest.mark.parametrize('fault', ('missing_trip', 'trip_copy', 'unfinished', 'not_final',
    'unclaimed', 'live_budget', 'advance_replaced', 'wrong_generation', 'wrong_destination'))
def test_goblin_adoption_cannot_skip_or_reconstruct_the_actual_section_handoff(goblin_arrival, fault):
    f = goblin_arrival; trip = f.trip
    if fault == 'missing_trip': trip = None
    elif fault == 'trip_copy': trip = SimpleNamespace(**vars(trip))
    elif fault == 'unfinished': trip.stage = trip._stage = 'sections'
    elif fault == 'not_final': trip.index = 0
    elif fault == 'unclaimed': f.arrival._claim[0] = False
    elif fault == 'live_budget': trip.budget.valid = True
    elif fault == 'advance_replaced': trip.camp.last_level_advance = replace(trip.level_advance)
    elif fault == 'wrong_generation': trip.generation += 1
    else: trip.destination_id = 'slave-mines'
    with pytest.raises(ValueError):
        f.controller.adopt_camp_handoff(f.engine, f.arrival, f.camp, trip=trip)
    assert f.controller.phase == 'newbie_camp' and f.controller.origin is None


@pytest.mark.parametrize('departure', (9, 10), indirect=True)
def test_goblin_origin_requires_and_retains_the_actual_current_level_event(departure):
    f = departure; c = f.controller; p = f.pending
    origin = c.claim_goblin_origin(f.engine, p)
    assert c.origin is origin and c.phase == 'origin_claimed' and c.root is None
    assert origin.level_advance is p.camp.last_level_advance
    assert origin.pending is p and origin.height is p.result and origin.recovery is p.recovery
    assert origin.historical_settings[4] == 5 and origin.current_settings[4] in (9,10)
    assert f.journey.settings == origin.historical_settings
    assert not progression.continuation_available(f.journey)
    with pytest.raises(ValueError): c.claim_goblin_origin(f.engine, p)
    assert c.origin is origin and p.lease.active


@pytest.mark.parametrize('fault', ('configured_only', 'advance_replaced', 'old_generation',
    'already_considered', 'pending_level', 'preparation', 'no_kill', 'recovery', 'unrecovered',
    'height', 'height_digest', 'height_expired', 'old_pair', 'lease', 'queued', 'wrong_camp',
    'attribution', 'monitor', 'veto'))
def test_configured_level_or_changed_camp_evidence_cannot_create_departure_authority(departure, fault):
    f = departure; p = f.pending; camp = f.camp
    if fault == 'configured_only': camp.level_source = 'owner_configuration'
    elif fault == 'advance_replaced': camp.last_level_advance = replace(p.level_advance)
    elif fault == 'old_generation':
        advance = replace(p.level_advance, generation=p.generation-1)
        p.level_advance = camp.last_level_advance = advance
        p.level_advance_state = flat_record_state(advance)
    elif fault == 'already_considered': f.journey.last_considered_level_advance = p.level_advance
    elif fault == 'pending_level': camp.pending_level = 10
    elif fault == 'preparation': camp.preparation_due = True
    elif fault == 'no_kill': camp.kills = 0
    elif fault == 'recovery': camp.recovery = replace(p.recovery)
    elif fault == 'unrecovered': p.recovery.phase = 'stand_settle'
    elif fault == 'height': p.result = replace(p.result, checkpoint=object())
    elif fault == 'height_digest': p.result = replace(p.result, sha256='0'*64)
    elif fault == 'height_expired': f.now = p.result.expires_at+.001
    elif fault == 'old_pair': p.baseline = p.result.first.log_line_seq
    elif fault == 'lease': p.lease.release()
    elif fault == 'queued': f.engine.jobs.put(('arm',p.generation))
    elif fault == 'wrong_camp': p.camp = replace(camp)
    elif fault == 'attribution': camp.progress.arrival_destination['destination_id'] = 'newbie-hills'
    elif fault == 'monitor': f.journey.camp_motion = object()
    else: p._probe_log_veto = object()
    with pytest.raises(ValueError): f.controller.claim_goblin_origin(f.engine, p)
    assert f.controller.origin is None and f.controller.root is None
    assert f.controller.phase == 'goblin_camp'


def test_one_root_is_bound_to_actual_departure_before_probe_execution(departure):
    f = departure; c = f.controller
    origin = c.claim_goblin_origin(f.engine, f.pending)
    root = prepare_root(f)
    c.bind_root(origin, root)
    assert c.root is root and c.phase == 'navigating'
    assert root.stage.phase == 'walking' and root.stage.leg_index == 0
    assert root._initial_measurement is None and root.snapshot()['reserved_pulses'] == 0
    assert f.pending.runtime is None and f.pending.route_runtime is None
    with pytest.raises(ValueError): c.bind_root(origin, root_for(f))
    assert c.root is root and root.valid
    with pytest.raises(ValueError): progression.active_origin_authority(f.journey, root)
    c.cancel('F9 before probe DOWN')
    assert not progression.continuation_available(f.journey)
    assert f.pending.lease.active and root.valid


@pytest.mark.parametrize('field', ('runtime', 'route_runtime'))
def test_root_cannot_be_attached_after_initial_probe_or_route_execution_starts(departure, field):
    f = departure; c = f.controller
    origin = c.claim_goblin_origin(f.engine, f.pending); root = prepare_root(f)
    setattr(f.pending, field, object())
    with pytest.raises(ValueError): c.bind_root(origin, root)
    assert c.root is None and c.phase == 'origin_claimed'


def test_first_crossing_promotes_only_the_completed_original_walk(first_crossing):
    f = first_crossing; c = f.controller; generation = f.engine.cancel_generation
    c.commit_first_crossing(f.engine, f.crossing_trip, f.crossing_arrival)
    assert progression.active_origin_authority(f.journey, f.root) is c.origin
    assert f.journey.settings == c.origin.current_settings
    assert f.engine.cancel_generation == generation and f.root.stage.phase == 'walking'
    with pytest.raises(ValueError):
        c.commit_first_crossing(f.engine, f.crossing_trip, f.crossing_arrival)


def test_terminal_consumption_ends_relocation_without_changing_the_original_choice(terminal_transfer):
    f = terminal_transfer; c = f.controller; token = f.terminal_token
    generation = f.engine.cancel_generation
    receipt = c.consume_terminal(token)
    assert c.phase == 'consumed' and c.terminal_receipt is receipt
    assert receipt.origin is c.origin and receipt.root is f.root and receipt.token is token
    assert progression.terminal_authority(f.journey, f.root, token) is receipt
    assert not progression.continuation_available(f.journey)
    assert f.journey.continue_camps is True and f.journey._continue_camps is True
    assert f.engine.cancel_generation == generation and f.engine.camp_session is None
    with pytest.raises(ValueError): c.consume_terminal(token)
    with pytest.raises(ValueError): progression.active_origin_authority(f.journey, f.root)
    with pytest.raises(ValueError): c.claim_goblin_origin(f.engine, f.pending)


def test_consumed_terminal_allows_only_the_existing_camp_start_generation_gap(terminal_transfer):
    f = terminal_transfer; c = f.controller; token = f.terminal_token
    receipt = c.consume_terminal(token)
    terminal_generation_gap(f)
    assert f.engine.camp_session is None and f.journey.phase == 'handoff'
    assert progression.terminal_authority(f.journey, f.root, token) is receipt
    camp = publish_terminal_camp(f)
    c.record_terminal_camp(f.engine, token, camp)
    assert c.phase == 'terminal_camp' and not progression.continuation_available(f.journey)
    assert progression.terminal_authority(f.journey, f.root, token) is receipt
    with pytest.raises(ValueError): c.record_terminal_camp(f.engine, token, camp)
    assert camp.running and f.engine.camp_session is camp


@pytest.mark.parametrize('fault', ('unclaimed', 'wrong_phase', 'monitor', 'floor', 'destination',
                                  'autopilot', 'second_increment', 'journey_generation'))
def test_terminal_generation_gap_cannot_be_used_as_general_restart_authority(terminal_transfer, fault):
    f = terminal_transfer; token = f.terminal_token
    f.controller.consume_terminal(token); terminal_generation_gap(f)
    if fault == 'unclaimed': token._claim[0] = False
    elif fault == 'wrong_phase': f.journey.phase = 'camp'
    elif fault == 'monitor': f.journey.camp_motion = object()
    elif fault == 'floor': f.journey.arrival_floor = object()
    elif fault == 'destination': f.journey.destination_assets = object()
    elif fault == 'autopilot': f.engine.autopilot = object()
    elif fault == 'second_increment':
        f.engine.cancel_generation += 1; f.journey.generation = f.engine.cancel_generation
    else: f.journey.generation -= 1
    with pytest.raises(ValueError): progression.terminal_authority(f.journey, f.root, token)
    assert f.controller.phase == 'consumed' and f.engine.camp_session is None


def test_released_adapter_uses_consumed_typed_origin_through_terminal_generation_gap(terminal_transfer):
    from eql_automation.owner_itinerary_camp_arrival import _active_progression, _released_progression
    f = terminal_transfer; token = f.terminal_token; c = f.controller
    assert token.progression_origin is c.origin
    assert _active_progression(f.journey, f.root) is c.origin
    with pytest.raises(ValueError): _released_progression(token)
    c.consume_terminal(token)
    _released_progression(token)
    with pytest.raises(ValueError): _active_progression(f.journey, f.root)
    terminal_generation_gap(f); _released_progression(token)
    camp = publish_terminal_camp(f); c.record_terminal_camp(f.engine, token, camp)
    _released_progression(token)
    assert f.journey.continue_camps is True and f.journey._continue_camps is True


@pytest.mark.parametrize('fault', ('public_flag', 'private_flag', 'origin', 'cancelled'))
def test_released_adapter_rejects_changed_or_revoked_progression_authority(terminal_transfer, fault):
    from eql_automation.owner_itinerary_camp_arrival import _released_progression
    f = terminal_transfer; token = f.terminal_token
    f.controller.consume_terminal(token)
    if fault == 'public_flag': f.journey.continue_camps = False
    elif fault == 'private_flag': f.journey._continue_camps = False
    elif fault == 'origin': object.__setattr__(token, 'progression_origin', None)
    else: f.controller.cancel('F9')
    with pytest.raises(ValueError): _released_progression(token)


@pytest.mark.parametrize('fault', ('destination_id', 'destination_assets'))
def test_adopted_camp_continuation_rejects_replaced_destination(newbie_arrival, fault):
    f = newbie_arrival
    f.controller.adopt_camp_handoff(f.engine, f.arrival, f.camp)
    assert progression.continuation_available(f.journey)
    if fault == 'destination_id': f.journey.destination_id = 'goblin-camp'
    else: f.journey.destination_assets = replace(f.arrival.destination)
    assert not progression.continuation_available(f.journey)


def test_origin_capture_clock_cannot_rewrite_the_observed_event_and_its_pending_pin(departure):
    f = departure; p = f.pending; fired = []
    def changed():
        fired.append(True)
        object.__setattr__(p.level_advance, 'camp_log_seq', p.level_advance.camp_log_seq+100)
        p.level_advance_state = flat_record_state(p.level_advance)
    f.clock_hook = changed
    with pytest.raises(ValueError): f.controller.claim_goblin_origin(f.engine, p)
    assert fired and f.controller.origin is None and f.controller.phase == 'goblin_camp'


@pytest.mark.parametrize('fault', ('unclaimed', 'trip_stage', 'lease', 'journey_phase', 'root_stage'))
def test_first_crossing_clock_cannot_retire_or_replace_the_checked_section(first_crossing, fault):
    f = first_crossing; fired = []
    def changed():
        fired.append(True)
        if fault == 'unclaimed': f.crossing_arrival._claim[0] = False
        elif fault == 'trip_stage': f.crossing_trip.set_stage('sections')
        elif fault == 'lease': f.crossing_arrival.runtime.lease.active = True
        elif fault == 'journey_phase': f.journey.phase = 'camp'
        else: f.root.advance(f.root.stage, 'crossing', zone_id=68)
    f.clock_hook = changed
    with pytest.raises(ValueError):
        f.controller.commit_first_crossing(f.engine, f.crossing_trip, f.crossing_arrival)
    assert fired and not f.controller._promoted


@pytest.mark.parametrize('fault', ('different_origin', 'missing_origin', 'monitor_floor',
    'monitor_closed', 'monitor_invalid', 'camp_session', 'autopilot'))
def test_terminal_consumption_requires_unstarted_provisional_cleanup_owner(terminal_transfer, fault):
    f = terminal_transfer; token = f.terminal_token
    if fault in ('different_origin', 'missing_origin'):
        origin = replace(f.controller.origin) if fault == 'different_origin' else None
        token = replace(token, progression_origin=origin)
        token.run.terminal_transfer = token.run._camp_arrival_token = token
    elif fault == 'monitor_floor': token.monitor.floor = token.arrival.checkpoint
    elif fault == 'monitor_closed': token.monitor.closed = True
    elif fault == 'monitor_invalid': token.monitor.valid = False
    elif fault == 'camp_session': f.engine.camp_session = object()
    else: f.engine.autopilot = object()
    with pytest.raises(ValueError): f.controller.consume_terminal(token)
    assert f.controller.phase == 'navigating' and f.controller.terminal_receipt is None


def test_nested_terminal_consumption_cannot_replace_the_already_published_receipt(terminal_transfer):
    f = terminal_transfer; c = f.controller; token = f.terminal_token; consumed = []
    def consume_inside_clock():
        consumed.append(c.consume_terminal(token))
    f.clock_hook = consume_inside_clock
    with pytest.raises(ValueError): c.consume_terminal(token)
    assert len(consumed) == 1 and c.terminal_receipt is consumed[0]
    assert c.phase == 'consumed' and not progression.continuation_available(f.journey)
    assert progression.terminal_authority(f.journey, f.root, token) is consumed[0]


def test_nested_camp_adoption_cannot_record_the_same_generation_twice(newbie_arrival):
    f = newbie_arrival; c = f.controller; adopted = []
    def adopt_inside_clock():
        adopted.append(c.adopt_camp_handoff(f.engine, f.arrival, f.camp))
    f.clock_hook = adopt_inside_clock
    with pytest.raises(ValueError): c.adopt_camp_handoff(f.engine, f.arrival, f.camp)
    assert adopted == [f.camp] and c.phase == 'newbie_camp'
    assert c._adoptions == (id(f.arrival),)
    assert f.engine.cancel_generation == f.camp.generation
    c.check_binding(f.engine)


def test_nested_origin_claim_cannot_replace_the_original_observed_departure(departure):
    f = departure; c = f.controller; claimed = []
    def claim_inside_clock():
        claimed.append(c.claim_goblin_origin(f.engine, f.pending))
    f.clock_hook = claim_inside_clock
    with pytest.raises(ValueError): c.claim_goblin_origin(f.engine, f.pending)
    assert len(claimed) == 1 and c.origin is claimed[0]
    assert c.phase == 'origin_claimed' and c.root is None
    c.check_binding(f.engine)


@pytest.mark.parametrize('fault', ('basis', 'binding', 'topology', 'closed', 'invalid',
                                  'configured_level', 'camp_level'))
def test_terminal_camp_record_rechecks_successor_continuity_and_exact_level(terminal_transfer, fault):
    f = terminal_transfer; c = f.controller; token = f.terminal_token
    c.consume_terminal(token); camp = publish_terminal_camp(f); monitor = f.journey.camp_motion
    if fault == 'basis': monitor.basis = b'{"changed":true}'
    elif fault == 'binding': monitor.binding = tuple(list(monitor.binding))
    elif fault == 'topology': monitor.topology += 1
    elif fault == 'closed': monitor.closed = True
    elif fault == 'invalid': monitor.valid = False
    elif fault == 'configured_level': f.engine.settings.level += 1
    else: camp.level += 1
    with pytest.raises(ValueError): c.record_terminal_camp(f.engine, token, camp)
    assert c.phase == 'consumed'
    assert c.terminal_receipt.token is token


def test_active_origin_helper_keeps_the_exact_observed_departure_settings(first_crossing):
    f = first_crossing
    f.controller.commit_first_crossing(f.engine, f.crossing_trip, f.crossing_arrival)
    assert progression.active_origin_authority(f.journey, f.root) is f.controller.origin
    f.engine.settings.level += 1
    with pytest.raises(ValueError): progression.active_origin_authority(f.journey, f.root)


def test_consumed_terminal_helper_keeps_the_exact_settings_before_camp_start(terminal_transfer):
    f = terminal_transfer; token = f.terminal_token
    receipt = f.controller.consume_terminal(token)
    assert progression.terminal_authority(f.journey, f.root, token) is receipt
    f.engine.settings.level += 1
    with pytest.raises(ValueError): progression.terminal_authority(f.journey, f.root, token)
