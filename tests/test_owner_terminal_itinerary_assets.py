"""Terminal selection and lazy assets; native loaders are explicit stand-ins.

Copied guide/profile checks use the actual private files when available. The
owner tests drive real root stages with synthetic log entries, without input.
"""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

import eql_automation.owner_zone_itinerary_assets as module
from eql_automation.native_region_policy import encoded
from eql_automation.zone_itinerary_budget import load_terminal_camp
import test_owner_zone_itinerary_assets as original


TERMINAL_REQUEST = dict(itinerary_id=module.OWNER_TERMINAL_ITINERARY_ID,
                       open_flat_clear=True, owner_supervised_continuation=True)


@pytest.fixture
def terminal_owner(tmp_path,monkeypatch):
    generator=original.owner.__wrapped__(tmp_path,monkeypatch)
    f=next(generator)
    identifier=module.OWNER_TERMINAL_ITINERARY_DESTINATION
    guide=original.Guide(identifier)
    f.assets[identifier]=original.Assets(identifier,guide)
    f.sections[identifier]=None
    target=load_terminal_camp(identifier,zone_catalog=original.CATALOG)
    terminal=module._CopiedTerminal(target,encoded(guide.record()),1053,7)
    f.terminal_copied=replace(f.copied,terminal=terminal)
    f.terminal_metadata_calls=[]
    def load(copied):
        assert copied is f.copied
        f.terminal_metadata_calls.append(True)
        return f.terminal_copied
    monkeypatch.setattr(module,'_load_terminal_camp_assets',load)
    monkeypatch.setattr(original,'REQUEST',dict(TERMINAL_REQUEST))
    def reach():
        f.destination_zone()
        for phase,zone in (('walking',54),('crossing',54),('loading',None),
                           ('arrival',58),('bootstrap',58)):
            f.root.advance(f.root.stage,phase,zone_id=zone)
        f.engine.journey.destination_id=identifier
        f.enter('Clan Crushbone')
    f.reach_terminal=reach
    yield f
    generator.close()


def test_real_slave_mines_metadata_and_unchanged_stop_profile_bytes():
    path=Path.home()/'.local/share/eql-automation/owner-route-data'/module.CATALOG_DATA_NAME/'ZoneNames.txt'
    if not path.exists():pytest.skip('Requires privately staged copied client assets')
    copied=module._load_copied_itinerary()
    stop,bounds,basis=module._profile(copied)
    assert stop.terminal_camp is None
    assert sha256(basis).hexdigest()=='65ee75c225420421290347d28c2a9e3b560304c9ea2c43725c8a39a91608fdec'
    terminal=module._load_terminal_camp_assets(copied)
    target=terminal.terminal.target
    assert (target.destination_id,target.source_zone_id,target.source_name)==('slave-mines',58,'Clan Crushbone')
    assert target.guide_sha256=='88aecac52585363add569d3f66ed9ba19921725e81e3a1626e96c50cfdc847e7'
    assert sha256(terminal.terminal.guide_record).hexdigest()=='3e90a2ffcc3f74586727e46c4e596dbaab3414064dcbb312e17e0da5459fccad'
    assert (terminal.terminal.operation_count,terminal.terminal.ordinary_step_count)==(1053,7)
    selected,new_bounds,new_basis=module._terminal_profile(terminal)
    assert selected.terminal_camp is target and selected.legs is stop.legs
    assert (selected.maximum_seconds,selected.maximum_pulses,selected.maximum_total_hold,
            selected.maximum_displacement_reserve)==(22680.,39021,7804.2,130077.7)
    assert selected.maximum_seconds-stop.maximum_seconds==3000.
    assert selected.maximum_pulses-stop.maximum_pulses==3007
    assert selected.maximum_total_hold-stop.maximum_total_hold==pytest.approx(601.4)
    assert selected.maximum_displacement_reserve-stop.maximum_displacement_reserve==pytest.approx(10025.9)
    assert new_bounds.forward_speed_upper_bound==bounds.forward_speed_upper_bound==30.
    evidence=json.loads(new_basis)
    assert evidence['terminal_walking_sections'] is None
    assert not evidence['camp_combat_in_navigation_budget']
    assert not evidence['client_motion_bounds_measured'] and not evidence['real_client_accepted']


def test_terminal_is_explicit_and_creation_loads_no_native_assets(terminal_owner):
    f=terminal_owner
    plan=module.load_owner_zone_itinerary(f.engine,dict(TERMINAL_REQUEST))
    assert f.terminal_metadata_calls==[True] and not f.calls
    assert f.engine.journey is None and f.engine.zone_itinerary_owner is None
    assert plan.declaration.record_id==module.OWNER_TERMINAL_ITINERARY_ID
    assert plan.declaration.terminal_camp is f.terminal_copied.terminal.target
    assert plan.declaration.target_count==3


@pytest.mark.parametrize('level',(0,20,50,-1,True,False,1.,'1',None))
def test_unsupported_terminal_level_refused_before_binding_or_metadata(terminal_owner,monkeypatch,level):
    f=terminal_owner;f.engine.settings.level=level
    monkeypatch.setattr(module,'_load_copied_itinerary',lambda:pytest.fail('Invalid level read metadata'))
    f.engine.sender.ui.fileno=lambda:pytest.fail('Invalid level read sender descriptor')
    with pytest.raises(ValueError,match='configured integer level'):
        module.load_owner_zone_itinerary(f.engine,dict(TERMINAL_REQUEST))
    assert not f.terminal_metadata_calls and not f.calls


@pytest.mark.parametrize('level',(1,19))
def test_supported_terminal_level_has_original_captured_request(terminal_owner,level):
    f=terminal_owner;f.engine.settings.level=level
    plan=f.start()
    assert f.owner.settings[-1]==level
    assert f.root.declaration is plan.declaration and f.root.declaration.terminal_camp is not None


def test_existing_stop_selection_does_not_load_terminal_or_gain_level_gate(terminal_owner,monkeypatch):
    f=terminal_owner;f.engine.settings.level=20
    monkeypatch.setattr(module,'_load_terminal_camp_assets',lambda _:pytest.fail('Stop requested camp metadata'))
    stop=dict(TERMINAL_REQUEST,itinerary_id=module.OWNER_ITINERARY_ID)
    plan=module.load_owner_zone_itinerary(f.engine,stop)
    _,_,old_basis=module._profile(f.copied)
    assert plan.bounds_basis==old_basis and plan.declaration.terminal_camp is None
    assert (plan.declaration.maximum_seconds,plan.declaration.maximum_pulses)==(19680.,36014)


def test_terminal_metadata_callback_cannot_raise_level_before_plan_publication(terminal_owner,monkeypatch):
    f=terminal_owner
    def load(_):
        f.engine.settings.level=20
        return f.terminal_copied
    monkeypatch.setattr(module,'_load_terminal_camp_assets',load)
    with pytest.raises(ValueError):module.load_owner_zone_itinerary(f.engine,dict(TERMINAL_REQUEST))
    assert not f.calls and f.engine.zone_itinerary_owner is None


def test_stop_request_cannot_be_upgraded_by_a_metadata_callback(terminal_owner,monkeypatch):
    f=terminal_owner
    request=dict(TERMINAL_REQUEST,itinerary_id=module.OWNER_ITINERARY_ID)
    def load():
        request['itinerary_id']=module.OWNER_TERMINAL_ITINERARY_ID
        return f.copied
    monkeypatch.setattr(module,'_load_copied_itinerary',load)
    monkeypatch.setattr(module,'_load_terminal_camp_assets',lambda _:pytest.fail('Stop request loaded camp'))
    with pytest.raises(ValueError,match='request changed'):
        module.load_owner_zone_itinerary(f.engine,request)
    assert not f.calls


def test_terminal_assets_wait_for_fresh_observed_crushbone_under_original_root(terminal_owner):
    f=terminal_owner;plan=f.start();root=f.root;expiry=root.expires_at;owner=f.owner
    f.reach_terminal()
    assert root.stage.kind=='terminal_camp' and root.stage.phase=='bootstrap'
    assert root.stage.leg_index==2 and root.leg is plan.declaration.terminal_camp
    assets=plan.destination_provider('slave-mines')
    assert assets is f.assets['slave-mines']
    assert plan.sections_provider(assets) is None
    assert f.calls==[('destination','slave-mines'),('sections','slave-mines')]
    assert f.owner is owner and f.root is root and root.expires_at==expiry
    assert f.engine.jobs.empty() and not f.engine.sender.held


def test_terminal_crossing_request_never_calls_crossing_loader(terminal_owner):
    f=terminal_owner;plan=f.start();f.reach_terminal()
    with pytest.raises(ValueError,match='no crossing corridor'):
        plan.crossing_provider('slave-mines')
    assert not f.calls


def test_terminal_guide_cannot_load_while_still_in_gfay(terminal_owner):
    f=terminal_owner;plan=f.start();f.destination_zone()
    with pytest.raises(ValueError):plan.destination_provider('slave-mines')
    assert not f.calls


@pytest.mark.parametrize('kind',('destination','sections'))
@pytest.mark.parametrize('fault',('F8','F9','settings','zone','root','catalog'))
def test_terminal_loader_late_veto_cannot_publish_assets(terminal_owner,kind,fault):
    f=terminal_owner;plan=f.start();f.reach_terminal()
    def hook(_):
        if fault in ('F8','F9'):f.engine.cancel_generation+=1
        elif fault=='settings':f.engine.settings.level=20
        elif fault=='zone':f.tracker.reader._clear_zone()
        elif fault=='root':f.root.cancel('Synthetic root cancellation')
        else:f.tracker.reader.zone_ids['Changed']=999
    f.hook=hook
    with pytest.raises(ValueError):
        if kind=='destination':plan.destination_provider('slave-mines')
        else:plan.sections_provider(f.assets['slave-mines'])
    assert f.calls==[(kind,'slave-mines')]
    assert not f.engine.sender.held


def test_terminal_cannot_acquire_a_walking_partition(terminal_owner):
    f=terminal_owner;plan=f.start();f.reach_terminal()
    f.sections['slave-mines']=original.Sections(f.assets['slave-mines'].guide,1,'a'*64)
    with pytest.raises(ValueError,match='unsectioned'):
        plan.sections_provider(f.assets['slave-mines'])


def test_none_sections_still_pin_input_guide_after_final_owner_callback(terminal_owner):
    f=terminal_owner;plan=f.start();f.reach_terminal()
    descriptor=f.engine.sender.ui.fileno
    changed=[]
    def fileno():
        if f.calls and not changed:
            changed.append(True)
            f.assets['slave-mines'].guide.values['late_change']=True
        return descriptor()
    f.engine.sender.ui.fileno=fileno
    with pytest.raises(ValueError,match='asset changed'):
        plan.sections_provider(f.assets['slave-mines'])
    assert changed


def test_terminal_section_loader_cannot_mutate_guide_before_returning_none(terminal_owner):
    f=terminal_owner;plan=f.start();f.reach_terminal()
    def hook(_):f.assets['slave-mines'].guide.values['changed_by_section_loader']=True
    f.hook=hook
    with pytest.raises(ValueError,match='asset changed'):
        plan.sections_provider(f.assets['slave-mines'])
    assert f.calls==[('sections','slave-mines')]


def test_stop_request_cannot_silently_adopt_terminal_metadata(terminal_owner,monkeypatch):
    f=terminal_owner
    monkeypatch.setattr(module,'_load_copied_itinerary',lambda:f.terminal_copied)
    with pytest.raises(ValueError,match='Stop itinerary'):
        module.load_owner_zone_itinerary(f.engine,dict(TERMINAL_REQUEST,itinerary_id=module.OWNER_ITINERARY_ID))


def test_terminal_profile_requires_adjacent_pinned_camp(terminal_owner):
    f=terminal_owner
    changed=replace(f.terminal_copied.terminal.target,source_name='Different Crushbone')
    with pytest.raises(ValueError,match='adjacent'):
        module._terminal_profile(replace(f.terminal_copied,
            terminal=replace(f.terminal_copied.terminal,target=changed)))
