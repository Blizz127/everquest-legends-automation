"""Copied progression metadata and adversarial callbacks; no input or geometry."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import eql_automation.owner_camp_progression_assets as module
from eql_automation.camp_progression import CampProgressionSelection
from eql_automation.native_region_policy import encoded
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot
from eql_automation.source_section_manifest import WalkingSections
from eql_automation.zone_itinerary_budget import load_terminal_camp
import test_owner_zone_itinerary_assets as original


REQUEST = dict(progression_id=module.CAMP_PROGRESSION_ID, open_flat_clear=True,
               owner_supervised_continuation=True)


def selection(evidence):
    return CampProgressionSelection(module.CAMP_PROGRESSION_ID, 'newbie-hills',
        'goblin-camp', 'slave-mines', module.CAMP_ORIGIN_ITINERARY_ID, evidence)


def retained_bounds():
    # Deliberately different from the later-zone independent profile.
    return module.RouteMotionBounds('retained-test', 'historical-test',
        .01, .15, .18, 12., .2, .005, 1., .03, 1.2, 6.)


def split(guide):
    guides = tuple(replace(guide, goal=op.end, operations=(op,)) for op in guide.operations)
    ranges = ((0, 0), (1, 1)); pin = 'd'*64
    return WalkingSections(guide, guides, ranges, pin,
        (_guide_snapshot(guide), tuple(_guide_snapshot(g) for g in guides), ranges, pin))


@pytest.fixture
def copied(monkeypatch):
    legs, crossings = original.synthetic_legs(original.CATALOG)
    guide = SourceItineraryGuide('butcher', 'a'*64, 'b'*64, 'c'*64, 1.2, 6.,
        (-2071., -298.), (SourceWalkHint((-2069., -298.), (-2070., -298.)),
                         SourceWalkHint((-2070., -298.), (-2071., -298.))))
    rows = tuple(module.itinerary._CopiedLeg(leg.destination_id,
        encoded(guide.record()) if index == 0 else b'{}', 'd'*64 if index == 0 else 'e'*64,
        count, module.itinerary._crossing_record(crossings[leg.destination_id]))
        for index, (leg, count) in enumerate(zip(legs, (2, 8))))
    terminal = module.itinerary._CopiedTerminal(
        load_terminal_camp('slave-mines', zone_catalog=original.CATALOG), b'{}', 1053, 7)
    data = module.itinerary._CopiedItinerary(encoded(original.CATALOG), frozenset(),
                                           legs, rows, terminal)
    evidence = encoded(dict(synthetic=True, input_authorized=False, movement_authorized=False,
        current_character_observation=False, native_geometry_loaded=False,
        runtime_continuation_enabled=False, real_client_accepted=False))
    state = SimpleNamespace(data=data, evidence=evidence, guide=guide,
        selection=selection(evidence), bounds=retained_bounds(), sections_calls=[])
    monkeypatch.setattr(module, '_load_progression_metadata', lambda:(data, evidence))
    def load(identifier, actual):
        assert identifier == legs[0].destination_id
        state.sections_calls.append(actual)
        return split(actual)
    monkeypatch.setattr(module, 'load_guide_walking_sections', load)
    return state


@pytest.fixture
def owner(tmp_path, monkeypatch, copied):
    generator = original.owner.__wrapped__(tmp_path, monkeypatch)
    f = next(generator)
    f.progression = copied
    yield f
    generator.close()


@pytest.mark.parametrize('level', (0, 5, 9, 20, 50, -1, True, False, 1., '1', None))
def test_initial_level_gate_precedes_metadata_or_owner_callbacks(owner, monkeypatch, level):
    owner.engine.settings.level = level
    monkeypatch.setattr(module, '_load_progression_metadata', lambda:pytest.fail('Read copied assets'))
    owner.engine.sender.ui.fileno = lambda:pytest.fail('Read sender descriptor')
    with pytest.raises(ValueError, match='configured integer level'):
        module.load_owner_camp_progression(owner.engine, dict(REQUEST))


@pytest.mark.parametrize('level', (1, 2, 3, 4))
def test_initial_selection_is_explicit_and_does_not_create_runtime(owner, level):
    owner.engine.settings.level = level
    selected = module.load_owner_camp_progression(owner.engine, dict(REQUEST))
    assert type(selected) is CampProgressionSelection
    assert selected.initial_destination_id == 'newbie-hills'
    assert selected.trigger_destination_id == 'goblin-camp'
    assert selected.itinerary_id == module.CAMP_ORIGIN_ITINERARY_ID
    assert selected.evidence == owner.progression.evidence
    assert owner.engine.journey is None and owner.engine.zone_itinerary_owner is None
    assert not owner.calls


@pytest.mark.parametrize('fault', ('missing', 'extra', 'wrong_id', 'flat_false',
                                   'flat_int', 'supervision_false', 'supervision_int', 'not_dict'))
def test_request_contract_is_exact_before_metadata(owner, monkeypatch, fault):
    request = dict(REQUEST)
    if fault == 'missing':request.pop('open_flat_clear')
    elif fault == 'extra':request['continue_camps'] = True
    elif fault == 'wrong_id':request['progression_id'] = module.itinerary.OWNER_TERMINAL_ITINERARY_ID
    elif fault == 'flat_false':request['open_flat_clear'] = False
    elif fault == 'flat_int':request['open_flat_clear'] = 1
    elif fault == 'supervision_false':request['owner_supervised_continuation'] = False
    elif fault == 'supervision_int':request['owner_supervised_continuation'] = 1
    else:request = tuple(request.items())
    monkeypatch.setattr(module, '_load_progression_metadata', lambda:pytest.fail('Read copied assets'))
    with pytest.raises(ValueError, match='explicit supervised'):
        module.load_owner_camp_progression(owner.engine, request)


@pytest.mark.parametrize('fault', ('request', 'level', 'cancel', 'sender', 'zone', 'log', 'catalog'))
def test_initial_metadata_callback_cannot_change_the_original_admission(owner, monkeypatch, fault):
    f = owner; request = dict(REQUEST); copied = f.progression
    def load():
        if fault == 'request':request['progression_id'] = 'changed'
        elif fault == 'level':f.engine.settings.level = 5
        elif fault == 'cancel':f.engine.cancel_generation += 1
        elif fault == 'sender':f.engine.sender = SimpleNamespace()
        elif fault == 'zone':f.enter('The Greater Faydark')
        elif fault == 'log':f.tracker.reader.tail.epoch += 1
        else:object.__setattr__(copied.data, 'catalog_record', encoded({'Other':68}))
        return copied.data, copied.evidence
    monkeypatch.setattr(module, '_load_progression_metadata', load)
    with pytest.raises((ValueError, AttributeError)):
        module.load_owner_camp_progression(f.engine, request)
    assert f.engine.journey is None and f.engine.zone_itinerary_owner is None and not f.calls


def test_origin_metadata_preserves_retained_bounds_and_charges_initial_probes_in_child(copied):
    result = module.load_camp_origin_itinerary(copied.selection, retained_bounds=copied.bounds)
    result.check()
    assert result.selection is copied.selection and result.copied is copied.data
    assert result.retained_bounds is copied.bounds
    assert result.retained_bounds.forward_speed_upper_bound == 12.
    assert result.probe_bounds.forward_speed_upper_bound == 30.
    assert result.route_sections.original is result.route_guide
    assert result.declaration.legs is copied.data.legs
    assert result.declaration.terminal_camp is copied.data.terminal.target
    d = result.declaration
    assert (d.maximum_seconds, d.maximum_pulses, d.maximum_total_hold,
            d.maximum_displacement_reserve) == (22500., 39014, 7802.8, 130051.8)
    basis = json.loads(result.bounds_basis)
    assert basis['cap_basis']['initial_camp_probes_charged_to_first_child'] == 7
    assert basis['cap_basis']['external_measurement_pulses'] == 14
    assert basis['cap_basis']['initial_preparation_allowance_seconds'] == 0.
    assert not basis['client_motion_bounds_measured']
    assert not basis['camp_combat_in_navigation_budget'] and not basis['input_authorized']


@pytest.mark.parametrize('fault', ('body_radius', 'body_height', 'minimum_hold', 'maximum_hold',
                                  'actual_hold', 'not_exact'))
def test_origin_bounds_must_fit_copied_body_and_all_standard_probes(copied, monkeypatch, fault):
    bounds = copied.bounds
    changes = {'body_radius':dict(body_radius=.1), 'body_height':dict(body_height=5.),
        'minimum_hold':dict(minimum_requested_hold=.06),
        'maximum_hold':dict(maximum_requested_hold=.1),
        'actual_hold':dict(maximum_actual_hold=.1)}
    bounds = SimpleNamespace(**vars(bounds)) if fault == 'not_exact' else replace(bounds, **changes[fault])
    monkeypatch.setattr(module, '_load_progression_metadata', lambda:pytest.fail('Read copied assets'))
    with pytest.raises(ValueError):
        module.load_camp_origin_itinerary(copied.selection, retained_bounds=bounds)


@pytest.mark.parametrize('fault', ('selection', 'retained', 'catalog', 'leg', 'terminal', 'row', 'guide'))
def test_origin_section_callback_mutations_are_rejected(copied, monkeypatch, fault):
    def load(identifier, guide):
        result = split(guide)
        if fault == 'selection':object.__setattr__(copied.selection, 'evidence', b'{}')
        elif fault == 'retained':object.__setattr__(copied.bounds, 'post_release_drift', .04)
        elif fault == 'catalog':object.__setattr__(copied.data, 'catalog_record', b'{}')
        elif fault == 'leg':object.__setattr__(copied.data.legs[0], 'source_name', 'Changed')
        elif fault == 'terminal':object.__setattr__(copied.data.terminal, 'operation_count', 999)
        elif fault == 'row':object.__setattr__(copied.data.assets[0], 'guide_record', b'{}')
        else:object.__setattr__(guide.operations[0], 'start', (0., 0.))
        return result
    monkeypatch.setattr(module, 'load_guide_walking_sections', load)
    with pytest.raises(ValueError):
        module.load_camp_origin_itinerary(copied.selection, retained_bounds=copied.bounds)


@pytest.mark.parametrize('fault', ('selection', 'retained', 'declaration', 'later_bounds', 'basis',
                                  'terminal', 'guide', 'sections'))
def test_published_origin_metadata_cannot_be_mutated(copied, fault):
    result = module.load_camp_origin_itinerary(copied.selection, retained_bounds=copied.bounds)
    if fault == 'selection':object.__setattr__(result.selection, 'evidence', b'{}')
    elif fault == 'retained':object.__setattr__(result.retained_bounds, 'forward_speed_upper_bound', 14.)
    elif fault == 'declaration':object.__setattr__(result.declaration, 'maximum_pulses', 1)
    elif fault == 'later_bounds':object.__setattr__(result.probe_bounds, 'body_radius', .1)
    elif fault == 'basis':object.__setattr__(result, 'bounds_basis', b'{}')
    elif fault == 'terminal':object.__setattr__(result.copied.terminal.target, 'source_name', 'Changed')
    elif fault == 'guide':object.__setattr__(result.route_guide.operations[-1], 'end', (0., 0.))
    else:object.__setattr__(result.route_sections, 'ranges', ((0, 1),))
    with pytest.raises(ValueError):result.check()


def test_changed_copied_evidence_cannot_materialize_the_original_selection(copied, monkeypatch):
    monkeypatch.setattr(module, '_load_progression_metadata', lambda:(copied.data, encoded(dict(changed=True))))
    with pytest.raises(ValueError, match='original selection'):
        module.load_camp_origin_itinerary(copied.selection, retained_bounds=copied.bounds)
    assert not copied.sections_calls


def test_validation_callback_cannot_mutate_published_retained_bounds(copied, monkeypatch):
    result = module.load_camp_origin_itinerary(copied.selection, retained_bounds=copied.bounds)
    original_check = WalkingSections.check
    def check(sections):
        original_check(sections)
        object.__setattr__(result.retained_bounds, 'post_release_drift', .04)
    monkeypatch.setattr(WalkingSections, 'check', check)
    with pytest.raises(ValueError, match='during validation'):
        result.check()


def test_real_copied_progression_has_adjacent_routes_and_preserves_old_profiles(monkeypatch):
    path = Path.home()/'.local/share/eql-automation/owner-route-data'/module.BUTCHER_DATA_NAME/'butcher_3.txt'
    if not path.exists():pytest.skip('Requires privately staged copied client assets')
    monkeypatch.setattr(module.itinerary, 'load_owner_source_destination',
                        lambda *a:pytest.fail('Loaded native destination'))
    monkeypatch.setattr(module.itinerary.ZoneItineraryBudget, '__init__',
                        lambda *a, **k:pytest.fail('Created root'))
    copied, evidence = module._load_progression_metadata()
    result = module.load_camp_origin_itinerary(selection(evidence), retained_bounds=retained_bounds())
    result.check(); record = json.loads(evidence)
    assert record['initial_configured_levels'] == [1, 4]
    assert record['crossing_observed_levels'] == [9, 10]
    assert record['annotations']['goblin-camp']['level_hint'] == [5, 8]
    assert record['annotations']['exit-hint']['map_xyz'] == [3061., 1316., 0.]
    assert record['first_crossing_start_xy'] == [-2069., -298.]
    assert record['first_crossing_goal_xy'] != [-3061., -1316.]
    assert [(leg.source_zone_id, leg.destination_zone_id) for leg in copied.legs] == [(68, 54), (54, 58)]
    assert len(result.route_guide.operations) == 314 and len(result.route_sections.guides) == 2
    assert not record['map_hint_used_as_crossing_endpoint'] and not record['real_client_accepted']
    stop, _, old_basis = module.itinerary._profile(copied)
    terminal, _, _ = module.itinerary._terminal_profile(copied)
    assert stop.maximum_seconds == 19680. and terminal.maximum_seconds == 22680.
    assert sha256(old_basis).hexdigest() == '65ee75c225420421290347d28c2a9e3b560304c9ea2c43725c8a39a91608fdec'
