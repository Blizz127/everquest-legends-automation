"""Actual retained owner/camp/itinerary lifecycle on synthetic terrain and pipes.

Only terrain proposals, game log feedback and combat preparation/recovery are
synthetic. Initial arrival, seven-probe fits, section arrivals, progression
intent, parent budgets and terminal camp adoption are production objects.
No installed client, character, device or network is used.
"""
from dataclasses import replace
from hashlib import sha256
import json
import time
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.camp_progression import CampProgressionSelection, continuation_available
from eql_automation.camp_recovery import CampRecovery
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy, encoded
from eql_automation.owner_camp_progression import CAMP_PROGRESSION_JOB, make_camp_progression_engine
from eql_automation.owner_camp_progression_assets import (
    CAMP_PROGRESSION_ID, CAMP_ORIGIN_ITINERARY_ID, CampOriginItineraryAssets)
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.owner_source_crossing import PinnedSourceCrossingSpec
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_destinations import destination_spec
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot
from eql_automation.source_section_manifest import WalkingSections
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryDeclaration, ZoneItineraryLeg, load_terminal_camp)
from eql_automation.zone_line import ExpectedZoneLine
import eql_automation.owner_camp_plan_provider as camp_provider
import eql_automation.owner_zone_itinerary_assets as itinerary_assets
import test_owner_journey_runtime as journey_fixture
from test_client_classification import leaf, view
from test_installed_region_model import files
from test_motion_collection import retained
from test_owner_camp_level_recheck import ding
from test_route_step_sender import after_down


REQUEST = dict(progression_id=CAMP_PROGRESSION_ID, open_flat_clear=True,
               owner_supervised_continuation=True)
CATALOG = {'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58}


def _partition(guide):
    """Two explicit synthetic proposals; actual runtime proves each handoff."""
    guides = tuple(replace(guide, goal=op.end, operations=(op,)) for op in guide.operations)
    ranges = tuple((i,i) for i in range(len(guides)))
    pin = sha256(encoded(guide.record())).hexdigest()
    result = WalkingSections(guide, guides, ranges, pin,
        (_guide_snapshot(guide), tuple(_guide_snapshot(g) for g in guides), ranges, pin))
    result.check()
    return result


def _geometry(h, monkeypatch):
    """Reuse the broad flat synthetic source plane, with distinct zone policies."""
    model = files(h.game, monkeypatch)
    old = h.loader
    planners = {}
    for zone, zone_id, name, split in (
            ('butcher',68,'Butcherblock Mountains',350.),
            ('gfaydark',54,'The Greater Faydark',300.),
            ('crushbone',58,'Clan Crushbone',500.)):
        nodes = ((1.,0.,0.,-split,0,2,3), leaf(3), leaf(1))
        bsp = BspVolumeView(SimpleNamespace(nodes=nodes,labels_by_region={2:{'zoneline'}}),
                            region_count=3,wld_sha256=old.pins[2])
        classifier = view(nodes,wld_pin=old.pins[2])
        policy = NativeZeroRegionTrialPolicy(*old.pins,bsp.inventory_sha256,
            classifier.inventory_sha256,classifier,zone=zone)
        p = CurrentStartPlanner(mesh=old.mesh,ground=old.ground,source=old.source,
            static=old.static,bsp=bsp,zone_short_name=zone,expected_zone_id=zone_id,
            expected_zone_name=name,mesh_sha256=old.pins[0],source_archive_sha256=old.pins[1],
            source_wld_sha256=old.pins[2],static_inventory_sha256=old.pins[3],region_policy=policy)
        p.installed_region_model = model
        planners[zone] = p
    guides = {}
    assets = {}
    for identifier, zone, points in (
            ('newbie-hills','butcher',(212.,214.)),
            ('goblin-camp','butcher',(214.,239.,264.)),
            ('butcher-gfay-crossing','butcher',(264.,289.,314.)),
            ('gfay-butcher-crushbone-crossing','gfaydark',(212.,237.,262.)),
            ('slave-mines','crushbone',(212.,215.))):
        p = planners[zone]
        guide = SourceItineraryGuide(zone,*p.pins[2:],'e'*64,1.2,6.,(396.5,points[-1]),
            tuple(SourceWalkHint((396.5,a),(396.5,b)) for a,b in zip(points,points[1:])))
        guides[identifier] = guide
        assets[identifier] = SourceDestinationAssets(p,guide,'Synthetic '+identifier,
            encoded(dict(synthetic=True,destination_id=identifier,
                         guide_sha256=sha256(encoded(guide.record())).hexdigest())),identifier)
        assets[identifier].check()
    partitions = {identifier:_partition(guides[identifier]) for identifier in
        ('goblin-camp','butcher-gfay-crossing','gfay-butcher-crushbone-crossing')}
    crossings = {}
    for identifier, source, start, split, destination, zone_id, name in (
            ('butcher-gfay-crossing','butcher',314.,350.,'gfaydark',54,'The Greater Faydark'),
            ('gfay-butcher-crushbone-crossing','gfaydark',262.,300.,'crushbone',58,'Clan Crushbone')):
        p = planners[source]
        line = ExpectedZoneLine('synthetic-'+identifier,source,*p.pins[:3],p.bsp.inventory_sha256,
            'f'*64,'DRNTP00255000001',2,(1,),(2,))
        points = tuple((396.5,y) for y in (start,start+10.,start+20.,split-2.,split+1.5))
        crossings[identifier] = PinnedSourceCrossingSpec(identifier,source,name,zone_id,destination,
            'e'*64,points[0],points[-1],((points[0],points[0]),*tuple(zip(points,points[1:])),
            (points[-1],points[-1])),line,'d'*64,encoded({'synthetic':identifier}))
    # Production metadata independently verifies the copied real route. This
    # fixture declares its explicit synthetic geometry in the same typed legs.
    catalog_pin=sha256(encoded(CATALOG)).hexdigest()
    legs = tuple(ZoneItineraryLeg(identifier,spec.zone,planners[spec.zone].zone_id,
        planners[spec.zone].zone_name,spec.destination_zone,spec.destination_zone_id,
        spec.destination,destination_spec(identifier).file_sha256,spec.corridor_file_sha256,
        spec.expected_zone_line.sha256,catalog_pin) for identifier,spec in crossings.items())
    terminal = load_terminal_camp('slave-mines',zone_catalog=CATALOG)
    rows = tuple(itinerary_assets._CopiedLeg(identifier,encoded(guides[identifier].record()),
        partitions[identifier].record_sha256,len(partitions[identifier].guides),
        itinerary_assets._crossing_record(crossings[identifier])) for identifier in crossings)
    copied = itinerary_assets._CopiedItinerary(encoded(CATALOG),frozenset(),legs,rows,
        itinerary_assets._CopiedTerminal(terminal,encoded(guides['slave-mines'].record()),1,0))
    declaration = ZoneItineraryDeclaration(CAMP_ORIGIN_ITINERARY_ID,legs,
        22500.,39014,7802.8,130051.8,terminal)
    bounds = RouteMotionBounds('synthetic-later-zone-envelope','synthetic-independent-hypotheses',
        .01,.15,.2,60.,.4,.01,10.,.1,1.2,6.)
    basis = encoded(dict(kind='synthetic independent later-zone hypotheses',
        source_motion_reused=False,input_authorized=False,real_client_accepted=False))
    return SimpleNamespace(planners=planners,guides=guides,assets=assets,partitions=partitions,
        crossings=crossings,copied=copied,declaration=declaration,bounds=bounds,basis=basis)


@pytest.fixture
def progression(tmp_path, retained, monkeypatch):
    selected = CampProgressionSelection(CAMP_PROGRESSION_ID,'newbie-hills','goblin-camp',
        'slave-mines',CAMP_ORIGIN_ITINERARY_ID,encoded(dict(synthetic=True,
            input_authorized=False,real_client_accepted=False)))
    state = SimpleNamespace(selected=selected,requests=[],origins=[],probe_starts=[],initial_arrivals=[],
        camp_arrivals=[],crossing_admissions=[],runtimes=[],terminal_tokens=[],transitions=[],receipts=[])
    original_factory = journey_fixture.make_owner_journey_engine
    def select(e,request):
        assert request == REQUEST and e.settings.level == 1
        state.requests.append(dict(request))
        return selected
    def origin(selection,*,retained_bounds):
        assert selection is selected
        g = state.geometry
        result = CampOriginItineraryAssets(selected,g.copied,g.declaration,g.bounds,g.basis,
            g.guides['butcher-gfay-crossing'],g.partitions['butcher-gfay-crossing'],retained_bounds)
        result.check();state.origins.append(result)
        return result
    def factory(base,**options):
        options['camp_probe_plan_provider'] = camp_provider.owner_camp_probe_plan
        options['source_crossing_provider'] = lambda e,identifier:state.geometry.crossings[identifier]
        options['zone_itinerary_provider'] = lambda *a:pytest.fail('No standalone itinerary request')
        return make_camp_progression_engine(original_factory(base,**options),
            progression_provider=select,origin_provider=origin)
    monkeypatch.setattr(journey_fixture,'make_owner_journey_engine',factory)
    generator = journey_fixture.h.__wrapped__(tmp_path,retained,monkeypatch,
                                              SimpleNamespace(param='camp_sections'))
    h = next(generator);e = h.engine;state.h=h;h.progression=state
    state.diagnostics=tmp_path/'progression-state.json'
    state.geometry = g = _geometry(h,monkeypatch)
    e.settings.level=1
    h.loading[0]=lambda:g.planners['butcher']
    h.source_loading[0]=lambda:g.assets[e.journey.destination_id]
    e._test_camp_sections=lambda identifier,guide:g.partitions[identifier]
    e._close_zone_tracker()
    (h.game/'Resources/ZoneNames.txt').write_text(''.join(
        f'{identifier}^{name}^0^0\n' for name,identifier in CATALOG.items()))
    e._service_zone_tracker();h.append('You have entered Butcherblock Mountains.')
    e._service_zone_tracker();e.read_log()
    monkeypatch.setattr(camp_provider,'choose_next_destination',lambda root,current_id,level:
        (camp_provider.destination_spec('goblin-camp'),encoded(dict(kind='synthetic-camp-proposal',
            destination_id='goblin-camp',input_authorized=False,real_client_accepted=False)))
        if current_id=='newbie-hills' and 5<=level<=8 else None)
    monkeypatch.setattr(camp_provider,'load_source_guide',lambda root,identifier:g.guides[identifier])
    monkeypatch.setattr(itinerary_assets,'load_owner_source_destination',lambda engine:g.assets[engine.journey.destination_id])
    monkeypatch.setattr(itinerary_assets,'load_owner_walking_sections',lambda engine,assets:g.partitions.get(assets.destination_id))
    monkeypatch.setattr(itinerary_assets,'load_owner_source_crossing',lambda engine,identifier:g.crossings[identifier])

    # Preserve every real sender/policy check; game displacement follows each
    # completed watchdog receipt and locations are fresh lines in the test log.
    import eql_automation.owner_source_runtime as initial_source
    import eql_automation.camp_source_runtime as camp_source
    import eql_automation.camp_probe_runtime as probes
    import eql_automation.owner_source_crossing as crossing
    def movement(original):
        def send(*args,**kwargs):
            result=original(*args,**kwargs)
            h.apply(result.receipt.key_code,result.receipt);state.receipts.append(result.receipt)
            return result
        return send
    monkeypatch.setattr(initial_source,'run_checked_source_step',movement(initial_source.run_checked_source_step))
    monkeypatch.setattr(camp_source,'run_checked_source_step',movement(camp_source.run_checked_source_step))
    original_probe=probes.send_camp_probe
    def probe(*args,**kwargs):
        result=original_probe(*args,**kwargs);receipt=result.seal.receipt
        h.apply(receipt.key_code,receipt);state.receipts.append(receipt)
        return result
    monkeypatch.setattr(probes,'send_camp_probe',probe)
    original_crossing=crossing.run_checked_source_crossing_step
    def cross(*args,**kwargs):
        result=original_crossing(*args,**kwargs)
        # The source corridor holds its sealed receipt, while its public result
        # records whether this exact footprint reached the native zone line.
        corridor=args[1]
        receipt=corridor.receipt
        h.apply(receipt.key_code,receipt);state.receipts.append(receipt)
        if result['touches_line']:
            destination=corridor.arrival.destination
            assert destination not in state.transitions
            state.transitions.append(destination)
            h.append('LOADING, PLEASE WAIT...');h.append('You have entered '+destination+'.')
            h.point[:]=[200.,396.5,2.7];h.heading=0.
        return result
    monkeypatch.setattr(crossing,'run_checked_source_crossing_step',cross)
    def reply():
        p=e.camp_position;trial=e.route_trial
        initial=None if trial is None else trial.get('source_runtime')
        requested=(initial is not None and initial.collector is not None
                   and initial.collector.phase=='requesting')
        requested=requested or p is not None and (p.sending or any(
            r is not None and r.current_input_key()==62 for r in (p.runtime,p.route_runtime)))
        requested=requested or any(r is not None and r.current_input_key()==62 for r in
            (e.camp_section_run,e.source_crossing_run,e.zone_itinerary_run))
        if requested:h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,reply)

    capture=e._capture_trial_continuation
    def captured(p):
        result=capture(p)
        if result is not None:state.initial_arrivals.append(result)
        return result
    monkeypatch.setattr(e,'_capture_trial_continuation',captured)
    begin=e._camp_probe_started
    def begun(p):
        result=begin(p);w=e.camp_walking
        assert w is not None and p.runtime is None
        root=None if e.zone_itinerary_owner is None else e.zone_itinerary_owner.root
        if p.journey.destination_id=='goblin-camp':
            assert root is p.journey.progression.root is w.budget.parent_budget
            assert root.snapshot()['reserved_pulses']==0
            assert root.stage.phase=='walking' and root.stage.leg_index==0
        else:assert root is None and w.budget.parent_budget is None
        state.probe_starts.append((p,w,root,len(state.receipts)))
        return result
    monkeypatch.setattr(e,'_camp_probe_started',begun)
    advance=e._advance_camp_section
    def advanced(w,arrival):
        result=advance(w,arrival)
        if isinstance(result,dict) and result.get('camp_started'):
            state.camp_arrivals.append((w,arrival,e.camp_session,e.cancel_generation))
        return result
    monkeypatch.setattr(e,'_advance_camp_section',advanced)
    first=e._start_source_crossing_from_camp_section
    def admitted(w,arrival):
        result=first(w,arrival)
        r=e.source_crossing_run
        if r is not None:
            state.crossing_admissions.append((r,e.zone_itinerary_owner,w,
                r.owner_input,r.log_veto,r.checkpoint))
        return result
    monkeypatch.setattr(e,'_start_source_crossing_from_camp_section',admitted)
    transferred=e._terminal_itinerary_transferred
    def terminal(run,token):
        state.terminal_tokens.append((run,token,e.cancel_generation,e.journey.progression))
        return transferred(run,token)
    monkeypatch.setattr(e,'_terminal_itinerary_transferred',terminal)
    try:yield h
    finally:
        _write_diagnostics(h)
        generator.close()


def _write_diagnostics(h):
    """Retain exact failed-scope evidence without reviving or checking it."""
    e=h.engine;s=h.progression
    def runtime(r):
        if r is None:return None
        return {name:getattr(r,name,None) for name in
            ('phase','reason','index','closed','busy','input_kind','input_request','request',
             'started','expires_at','last_release','last_movement_release')}
    rows=[]
    for p,w,root,count in s.probe_starts:
        rows.append(dict(destination_id=w.destination_id,stage=w.stage,section=w.index,
            receipts_at_start=count,probe=runtime(p.runtime),source=runtime(p.route_runtime),
            completed_probes=0 if p.runtime is None else len(p.runtime.results),
            pending_reason=p.reason,root=None if root is None else root.snapshot(),
            child=w.budget.snapshot(),last_result=p.probe_record))
    data=dict(journey_last_result=e.journey_last_result,
        camp_position_last_result=e.camp_position_last_result,
        probe_starts=rows,total_receipts=len(s.receipts),
        last_receipts=[vars(r) for r in s.receipts[-12:]],
        transitions=s.transitions,notices=h.notices,traces=h.traces[-500:],events=h.events[-100:],
        cancelled=e.cancelled,cancel_generation=e.cancel_generation,
        observer_closed=h.observer_closed,held=list(e.sender.held),
        tracker_lease_active=e.live_zone_tracker.lease is not None)
    s.diagnostics.write_text(json.dumps(data,indent=2,default=str)+'\n')


def _until(h,predicate,*,timeout=240.):
    e=h.engine;deadline=time.monotonic()+timeout
    while not predicate() and time.monotonic()<deadline:
        h.tick();h.drain()
        r=e.zone_itinerary_run
        if r is not None and r not in h.progression.runtimes:h.progression.runtimes.append(r)
        if e.journey is None:
            _write_diagnostics(h)
            result=e.journey_last_result or {}
            pytest.fail('Progression stopped: '+str(result.get('reason'))+
                '\nEvidence: '+str(h.progression.diagnostics)+'\n'+'\n'.join(map(str,h.notices[-12:])))
        time.sleep(.01)
    assert predicate(),(e.autopilot_payload(),h.notices[-12:])


def _recover(h):
    """Combat/preparation is separately covered; supply its completed recovery."""
    import rotation_core
    e=h.engine;camp=e.camp_session
    camp.preparation_due=False
    e.profile={};e.rotation=rotation_core.Rotation(e.profile,e.settings.level,damage_interval=4.)
    now=time.monotonic();camp.kills+=1;camp.phase='recovery'
    r=camp.recovery=CampRecovery(now-3.,phase='stand_after_rest')
    r.submitted('/stand',now-2.);r.sample(now-.8,now-.8,1.,1.);r.sample(now-.5,now-.5,1.,1.)
    assert r.phase=='recovered'
    e.hp=e.mana=1.;e.last_gauge=now;e.active=False;e.target_ready=False
    e.command_pause_until=0.;e.rotation.busy_until=0.
    e._camp_recovery_tick(camp,now)


def test_real_owner_newbie_goblin_itinerary_consumes_one_progression(progression):
    h=progression;e=h.engine;s=h.progression
    initial_generation=e.cancel_generation
    e.post(CAMP_PROGRESSION_JOB,dict(REQUEST));e.handle_job(*e.jobs.get_nowait())
    assert e.supervised_motion is not None and e.journey.destination_id=='newbie-hills',h.notices
    j=e.journey;c=j.progression
    assert c.intent.journey is j and c.root is None and c.phase=='newbie_request'
    h.due_trial();_until(h,lambda:e.camp_session is not None)
    newbie=e.camp_session;newbie_floor=j.arrival_floor;observer=j.camp_motion.observer
    assert c.phase=='newbie_camp' and e.cancel_generation==initial_generation+1
    assert j.continue_camps is j._continue_camps is True
    assert newbie.progress.arrival_destination['destination_id']=='newbie-hills'
    assert newbie_floor.valid and e.live_zone_tracker.lease is None and not h.observer_closed
    assert len(s.initial_arrivals)==1 and s.initial_arrivals[0].journey is j
    assert s.initial_arrivals[0].floor_checkpoint is newbie_floor
    assert s.initial_arrivals[0].runtime.completed_arrival is s.initial_arrivals[0].receipt

    ding(h,5);newbie_advance=newbie.last_level_advance
    _recover(h);_until(h,lambda:e.camp_session is not None and e.camp_session is not newbie)
    goblin=e.camp_session;goblin_generation=e.cancel_generation
    assert e.journey is j and j.progression is c and c.phase=='goblin_camp'
    assert goblin_generation==initial_generation+2 and j.destination_id=='goblin-camp'
    assert len(s.camp_arrivals)==1
    trip,arrival,adopted,_=s.camp_arrivals[0]
    assert trip.level_advance is newbie_advance and adopted is goblin
    assert arrival.checkpoint is j.arrival_floor and not trip.budget.valid
    assert len(trip.pending.runtime.results)==7 and trip.index==len(trip.sections.guides)-1
    assert j.camp_motion.observer is observer and not newbie.running and not newbie_floor.valid
    assert c.root is None and len(s.probe_starts)==1

    ding(h,9);goblin_advance=goblin.last_level_advance
    _recover(h);_until(h,lambda:e.camp_session is not None and e.camp_session is not goblin)
    terminal=e.camp_session
    assert e.journey is j and j.progression is c and c.phase=='terminal_camp'
    assert e.cancel_generation==goblin_generation+1==initial_generation+3
    assert j.destination_id=='slave-mines' and e.zone=='crushbone'
    assert e.live_zone_tracker.reader.zone_id==58 and e.live_zone_tracker.lease is None
    assert terminal.preparation_due and terminal.progress.arrival_destination['destination_id']=='slave-mines'
    assert terminal is not goblin and not goblin.running
    assert s.requests==[REQUEST] and len(s.origins)==1 and len(s.probe_starts)==2
    pending,origin_trip,root,_=s.probe_starts[1]
    assert c.origin.level_advance is goblin_advance and c.origin.pending is pending
    assert c.root is root and len(pending.runtime.results)==7 and origin_trip.budget.parent_budget is root
    assert not origin_trip.budget.valid and root.stage.phase=='complete'
    assert s.transitions==['The Greater Faydark','Clan Crushbone']
    assert len(s.crossing_admissions)==len(s.runtimes)==len(s.terminal_tokens)==1
    first,owner,crossing_trip,first_observer,first_veto,first_floor=s.crossing_admissions[0]
    run=s.runtimes[0];_,token,transfer_generation,controller=s.terminal_tokens[0]
    assert controller is c and transfer_generation==goblin_generation
    assert first.journey_budget is run.root is root and first_observer is run.owner_input is observer
    assert crossing_trip is origin_trip and first_veto is origin_trip.veto
    assert owner.closed and run.closed and first.closed
    assert not first_floor.valid and j.arrival_floor is token.arrival.checkpoint and j.arrival_floor.valid
    assert j.arrival_floor._policy.zone=='crushbone'
    assert j.camp_motion.observer is observer and not h.observer_closed
    assert e.zone_itinerary_owner is e.zone_itinerary_run is e.source_crossing_run is None
    assert e.camp_walking is e.camp_section_run is e.camp_position is None
    assert not e.sender.held and not h.commands and not continuation_available(j)
    assert c.terminal_receipt is not None and j.continue_camps is j._continue_camps is True

    # A new observed level and recovered kill cannot spend this finite intent
    # again or create another navigation job/camp generation.
    ding(h,10);event_start=len(h.events);before=(len(s.receipts),e.cancel_generation)
    _recover(h);_until(h,lambda:e.camp_position is None,timeout=10.);h.drain()
    assert e.camp_session is terminal and e.camp_position is None
    assert (len(s.receipts),e.cancel_generation)==before
    # The ordinary camp may check its newly reached floor once; it must not
    # obtain another motion probe or navigation job from the spent intent.
    assert all(kind!=1 or key==62 for kind,key,value in h.events[event_start:])
    assert e.jobs.empty() and not continuation_available(j)
