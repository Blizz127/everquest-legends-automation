"""Pinned metadata plus synthetic provider callbacks; no client/device input.

The lifecycle cases use actual tracker/root/owner contracts and small stand-ins
for native asset loader results. They do not claim geometry or live acceptance.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
from queue import Queue
import threading
from types import SimpleNamespace

import pytest

import eql_automation.owner_zone_itinerary_assets as module
from eql_automation.native_region_policy import encoded
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity, window_identity
from eql_automation.owner_zone_itinerary import _ItineraryOwner
from eql_automation.owner_zone_tracker import LiveZoneTracker, owner_zone_binding
from eql_automation.route_step_sender import _fd_identity
from eql_automation.source_destinations import destination_spec
from eql_automation.zone_itinerary_budget import ZoneItineraryBudget
from test_owner_zone_itinerary import synthetic_legs


CATALOG = {'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58}
REQUEST = dict(itinerary_id=module.OWNER_ITINERARY_ID,
               open_flat_clear=True, owner_supervised_continuation=True)
COPIED_LOADER = module._load_copied_itinerary


class Guide:
    def __init__(self, identifier): self.values = dict(synthetic=True, identifier=identifier)
    def record(self): return dict(self.values)


class Assets:
    def __init__(self, identifier, guide):
        spec = destination_spec(identifier)
        self.destination_id, self.guide = identifier, guide
        self.target_name, self.source_evidence = identifier, encoded(dict(synthetic=True))
        self.planner = SimpleNamespace(zone=spec.zone, zone_id=spec.zone_id,
            zone_name=next(name for name, value in CATALOG.items() if value==spec.zone_id), pins=('a'*64,)*4)
    def check(self): pass


class Sections:
    def __init__(self, guide, count, pin):
        self.original, self.guides = guide, (guide,)*count
        self.ranges, self.record_sha256 = tuple((i,i) for i in range(count)), pin
        self._state = (pin,count)
    def check(self): pass


@pytest.fixture
def owner(tmp_path, monkeypatch):
    rd, wr = os.pipe()
    state = SimpleNamespace(now=100., calls=[], hook=lambda kind:None)
    state.clock = lambda:state.now
    game = tmp_path/'game'; (game/'Logs').mkdir(parents=True)
    log = game/'Logs/eqlog_Probe_private.txt'; log.touch()
    names = tmp_path/'ZoneNames.txt'
    names.write_text(''.join(f'{value}^{name}^0^0\n' for name,value in CATALOG.items()))
    window = SimpleNamespace(id=7)
    engine = SimpleNamespace(cancel_generation=1, supervised_epoch=2, route_session_epoch=3,
        settings=SimpleNamespace(game_dir=str(game), character='Probe', server='private', level=1),
        gate=SimpleNamespace(windows=lambda:[window], game_session=lambda:dict(pid=8,start_ticks='9')),
        sender=SimpleNamespace(ui=SimpleNamespace(fileno=lambda:wr), held=set(), unfinished=False, dismissed=False),
        jobs=Queue(), g0_stop_lock=threading.RLock(), stopping=False, cancelled=True,
        journey=None, zone_itinerary_owner=None, live_zone_tracker=None)
    tracker = LiveZoneTracker(log,names,expected_character='Probe',expected_server='private',
        binding_reader=lambda:owner_zone_binding(engine),clock=state.clock)
    engine.live_zone_tracker=tracker
    def enter(name):
        with log.open('a') as stream:
            stream.write('[Sun Nov 15 12:00:00 2026] You have entered '+name+'.\n')
        tracker.poll()
    enter('Butcherblock Mountains')
    legs, crossings = synthetic_legs(CATALOG)
    identifiers = module.OWNER_ITINERARY_DESTINATIONS
    guides = {identifier:Guide(identifier) for identifier in identifiers}
    assets = {identifier:Assets(identifier,guides[identifier]) for identifier in identifiers}
    sections = {identifier:Sections(guides[identifier],count,str(index+1)*64)
        for index,(identifier,count) in enumerate(zip(identifiers,module.OWNER_ITINERARY_SECTION_COUNTS))}
    copied = module._CopiedItinerary(encoded(CATALOG),frozenset(),legs,tuple(
        module._CopiedLeg(identifier,encoded(guides[identifier].record()),sections[identifier].record_sha256,
            len(sections[identifier].guides),module._crossing_record(crossings[identifier])) for identifier in identifiers))
    monkeypatch.setattr(module, '_load_copied_itinerary', lambda:copied)
    monkeypatch.setattr(module, 'SourceDestinationAssets', Assets)
    monkeypatch.setattr(module, 'WalkingSections', Sections)
    def destination_loader(actual):
        assert actual is engine
        state.calls.append(('destination',engine.journey.destination_id))
        state.hook('destination')
        return assets[engine.journey.destination_id]
    def sections_loader(actual, value):
        assert actual is engine
        state.calls.append(('sections',value.destination_id))
        state.hook('sections')
        return sections[value.destination_id]
    def crossing_loader(actual, identifier):
        assert actual is engine
        state.calls.append(('crossing',identifier))
        state.hook('crossing')
        return crossings[identifier]
    monkeypatch.setattr(module, 'load_owner_source_destination', destination_loader)
    monkeypatch.setattr(module, 'load_owner_walking_sections', sections_loader)
    monkeypatch.setattr(module, 'load_owner_source_crossing', crossing_loader)
    state.engine,state.tracker,state.copied = engine,tracker,copied
    state.assets,state.sections,state.crossings = assets,sections,crossings
    state.enter=enter
    def start():
        plan=module.load_owner_zone_itinerary(engine,dict(REQUEST))
        owner=_ItineraryOwner(engine,plan,encoded(REQUEST),engine.cancel_generation,
            settings_identity(engine.settings),(engine.supervised_epoch,engine.route_session_epoch),
            engine.sender,engine.sender.ui,engine.gate,tracker,tracker.reader,
            window_identity(engine.gate,require_focus=False),wr,_fd_identity(wr))
        engine.zone_itinerary_owner=owner
        root=ZoneItineraryBudget(plan.declaration,clock=state.clock,stop_lock=engine.g0_stop_lock,
            owner_binding=owner.binding(),binding_reader=owner.binding)
        owner.root=owner._root=root
        engine.journey=Journey(engine.cancel_generation,settings_identity(engine.settings),'travel',
            destination_id=identifiers[0])
        owner.adopt_journey(engine.journey)
        owner.starting=False;engine.cancelled=False
        state.plan,state.owner,state.root=plan,owner,root
        return plan
    state.start=start
    def destination_zone():
        root=state.root
        for phase,zone in (('crossing',68),('loading',None),('arrival',54),('bootstrap',54)):
            root.advance(root.stage,phase,zone_id=zone)
        engine.journey.destination_id=identifiers[1]
        enter('The Greater Faydark')
    state.destination_zone=destination_zone
    yield state
    tracker.close()
    os.close(rd);os.close(wr)


def test_copied_catalog_guides_sections_and_crossings_match_selected_profile():
    path=Path.home()/'.local/share/eql-automation/owner-route-data'/module.CATALOG_DATA_NAME/'ZoneNames.txt'
    if not path.exists():pytest.skip('Requires privately staged copied client assets')
    copied=COPIED_LOADER()
    assert tuple(row.section_count for row in copied.assets)==(2,8)
    assert [(leg.source_zone_id,leg.destination_zone_id) for leg in copied.legs]==[(68,54),(54,58)]
    limits,bounds,basis=module._profile(copied)
    assert (limits.maximum_seconds,limits.maximum_pulses,limits.maximum_total_hold,
            limits.maximum_displacement_reserve)==(19680.,36014,7202.8,120051.8)
    assert (bounds.maximum_actual_hold,bounds.forward_speed_upper_bound,
            bounds.body_radius,bounds.body_height)==(.2,30.,1.2,6.)
    record=json.loads(basis)
    assert not record['client_motion_bounds_measured'] and not record['input_authorized']
    assert not record['real_client_accepted']


def test_plan_creation_reads_no_native_destination_assets(owner):
    plan=module.load_owner_zone_itinerary(owner.engine,dict(REQUEST))
    assert owner.calls==[] and owner.engine.journey is None
    assert plan.declaration.record_id==module.OWNER_ITINERARY_ID
    assert tuple(leg.destination_id for leg in plan.declaration.legs)==module.OWNER_ITINERARY_DESTINATIONS


@pytest.mark.parametrize('boundary', ('descriptor','window'))
def test_stop_during_initial_binding_is_not_adopted_as_a_new_request(owner,monkeypatch,boundary):
    e=owner.engine
    monkeypatch.setattr(module,'_load_copied_itinerary',lambda:pytest.fail('Revoked binding loaded metadata'))
    if boundary=='descriptor':
        original=e.sender.ui.fileno
        def changed():
            e.cancel_generation+=1
            return original()
        e.sender.ui.fileno=changed
    else:
        original=e.gate.windows
        def changed():
            e.cancel_generation+=1
            return original()
        e.gate.windows=changed
    with pytest.raises(ValueError):module.load_owner_zone_itinerary(e,dict(REQUEST))
    assert not owner.calls


@pytest.mark.parametrize('change', (
    {'itinerary_id':'other'}, {'open_flat_clear':False}, {'open_flat_clear':1},
    {'owner_supervised_continuation':False}, {'owner_supervised_continuation':1}, {'extra':True}))
def test_invalid_request_never_reads_metadata_or_native_assets(owner,monkeypatch,change):
    monkeypatch.setattr(module,'_load_copied_itinerary',lambda:pytest.fail('Invalid request loaded metadata'))
    with pytest.raises(ValueError):
        module.load_owner_zone_itinerary(owner.engine,dict(REQUEST,**change))
    assert owner.calls==[]


@pytest.mark.parametrize('fault', ('generation','settings','epoch','tracker','log','zone','catalog','partial','request'))
def test_initial_metadata_callbacks_cannot_publish_a_revoked_plan(owner,monkeypatch,fault):
    e=owner.engine;request=dict(REQUEST)
    def load():
        if fault=='generation':e.cancel_generation+=1
        elif fault=='settings':e.settings.level+=1
        elif fault=='epoch':e.route_session_epoch+=1
        elif fault=='tracker':e.live_zone_tracker=None
        elif fault=='log':owner.tracker.reader.tail.epoch+=1
        elif fault=='zone':owner.tracker.reader._clear_zone()
        elif fault=='catalog':owner.tracker.reader.zone_ids['Unpinned']=999
        elif fault=='partial':owner.tracker.reader.tail.partial=b'partial'
        else:request['open_flat_clear']=False
        return owner.copied
    monkeypatch.setattr(module,'_load_copied_itinerary',load)
    with pytest.raises(ValueError):module.load_owner_zone_itinerary(e,request)
    assert not owner.calls and e.zone_itinerary_owner is None and not e.sender.held


def test_gfay_native_assets_wait_for_the_actual_observed_next_leg(owner):
    plan=owner.start()
    identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    first=plan.destination_provider(identifier)
    assert first is owner.assets[identifier]
    assert plan.sections_provider(first) is owner.sections[identifier]
    assert plan.crossing_provider(identifier) is owner.crossings[identifier]
    assert {value for _,value in owner.calls}=={identifier}
    owner.destination_zone()
    identifier=module.OWNER_ITINERARY_DESTINATIONS[1]
    second=plan.destination_provider(identifier)
    assert second is owner.assets[identifier]
    assert plan.sections_provider(second) is owner.sections[identifier]
    assert plan.crossing_provider(identifier) is owner.crossings[identifier]
    assert owner.root.stage.phase=='bootstrap' and owner.root.stage.leg_index==1


def test_future_destination_refusal_retires_the_provider(owner):
    plan=owner.start()
    with pytest.raises(ValueError):plan.destination_provider(module.OWNER_ITINERARY_DESTINATIONS[1])
    assert owner.calls==[]
    with pytest.raises(ValueError,match='retired'):
        plan.destination_provider(module.OWNER_ITINERARY_DESTINATIONS[0])


@pytest.mark.parametrize('kind', ('destination','sections','crossing'))
@pytest.mark.parametrize('fault', ('F9','settings','root','zone'))
def test_lazy_asset_callback_changes_cannot_publish_a_result(owner,kind,fault):
    plan=owner.start();identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    def hook(actual):
        if fault=='F9':owner.engine.cancel_generation+=1
        elif fault=='settings':owner.engine.settings.level+=1
        elif fault=='root':owner.root.cancel('Synthetic root cancellation')
        else:owner.tracker.reader._clear_zone()
    owner.hook=hook
    with pytest.raises(ValueError):
        if kind=='destination':plan.destination_provider(identifier)
        elif kind=='sections':plan.sections_provider(owner.assets[identifier])
        else:plan.crossing_provider(identifier)
    assert owner.calls==[(kind,identifier)] and not owner.engine.sender.held


@pytest.mark.parametrize('kind', ('destination','sections','crossing'))
def test_changed_loader_asset_is_rejected(owner,kind):
    plan=owner.start();identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    if kind=='destination':owner.assets[identifier].guide.values['mutated']=True
    elif kind=='sections':owner.sections[identifier].record_sha256='f'*64
    else:owner.crossings[identifier]=replace(owner.crossings[identifier],destination='changed')
    with pytest.raises((ValueError,TypeError)):
        if kind=='destination':plan.destination_provider(identifier)
        elif kind=='sections':plan.sections_provider(owner.assets[identifier])
        else:plan.crossing_provider(identifier)


def test_final_descriptor_callback_cannot_mutate_a_returned_guide(owner):
    plan=owner.start();identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    descriptor=owner.engine.sender.ui.fileno
    changed=[]
    def fileno():
        if owner.calls and not changed:
            changed.append(True)
            owner.assets[identifier].guide.values['late_change']=True
        return descriptor()
    owner.engine.sender.ui.fileno=fileno
    with pytest.raises(ValueError,match='asset changed'):
        plan.destination_provider(identifier)
    assert changed


def test_final_descriptor_callback_cannot_replace_partition_pins(owner):
    plan=owner.start();identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    descriptor=owner.engine.sender.ui.fileno
    changed=[]
    def fileno():
        if owner.calls and not changed:
            changed.append(True)
            owner.sections[identifier]._state=('replaced',)
        return descriptor()
    owner.engine.sender.ui.fileno=fileno
    with pytest.raises(ValueError,match='asset changed'):
        plan.sections_provider(owner.assets[identifier])
    assert changed


@pytest.mark.parametrize('fault', ('plan','root','owner','journey'))
def test_lazy_providers_cannot_adopt_a_replacement_owner_scope(owner,fault):
    plan=owner.start();identifier=module.OWNER_ITINERARY_DESTINATIONS[0]
    plan.crossing_provider(identifier)
    o=owner.owner
    if fault=='plan':o.plan=replace(plan)
    elif fault=='root':o.root=o._root=object()
    elif fault=='owner':owner.engine.zone_itinerary_owner=replace(o)
    else:o.journey=o._journey=owner.engine.journey=replace(o.journey)
    before=len(owner.calls)
    with pytest.raises(ValueError):plan.crossing_provider(identifier)
    assert len(owner.calls)==before


def test_profile_rejects_new_partition_counts_without_silently_raising_caps(owner):
    row=replace(owner.copied.assets[1],section_count=9)
    with pytest.raises(ValueError,match='profile needs review'):
        module._profile(replace(owner.copied,assets=(owner.copied.assets[0],row)))


def test_actual_owner_wrapper_accepts_the_pinned_provider_before_source_loading(owner):
    from eql_automation.owner_zone_itinerary import ITINERARY_JOB, make_zone_itinerary_engine
    from eql_automation.owner_route_trial import SOURCE_JOB
    from test_owner_zone_itinerary import Base
    state=SimpleNamespace(sender=owner.engine.sender,gate=owner.engine.gate,tracker=owner.tracker,
        now=owner.now,asset_seconds=0.,asset_hook=lambda:None)
    engine=make_zone_itinerary_engine(Base,itinerary_provider=module.load_owner_zone_itinerary,
                                      clock=owner.clock)(state)
    engine.settings=owner.engine.settings
    engine.post(ITINERARY_JOB,dict(REQUEST))
    engine.handle_job(*engine.jobs.get_nowait())
    selected=engine.zone_itinerary_owner
    assert selected is not None, engine.messages
    assert selected.plan.declaration.record_id==module.OWNER_ITINERARY_ID
    assert selected.root.declaration is selected.plan.declaration
    assert selected.root.started==owner.now and selected.root.snapshot()['reserved_pulses']==0
    assert len(engine.delegated)==1 and engine.delegated[0][0]==SOURCE_JOB
    assert engine.journey is selected.journey and engine.supervised_motion is selected.pending
    assert owner.calls==[] and engine.jobs.empty()
    engine.stop_action('Synthetic test cleanup')
    assert not selected.root.valid and engine.zone_itinerary_owner is None
