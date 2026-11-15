"""Copied metadata for explicit Newbie -> Goblin -> Slave Mines progression.

This module loads no native geometry and creates no owner, root or input grant.
The controller must admit the actual recovered Goblin level event. The origin
camp keeps its own retained probe bounds; the independent envelope below is for
later zone bootstraps and is not a client measurement or a replacement fit.
"""
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
from pathlib import Path

from .butcher_assets import DATA_NAME as BUTCHER_DATA_NAME, DATA_PINS as BUTCHER_PINS
from .camp_annotations import read_camp_annotations
from .flat_record import flat_record_state
from .motion_calibration import PROBES
from .native_region_policy import encoded
from .owner_route_assets import checked_bytes
from .owner_section_assets import load_guide_walking_sections
from . import owner_zone_itinerary_assets as itinerary
from .route_geometry import RouteMotionBounds
from .source_destinations import destination_spec, load_source_guide
from .source_itinerary import SourceItineraryGuide, _guide_snapshot
from .source_section_manifest import WalkingSections
from .zone_itinerary_budget import _declaration_state


CAMP_PROGRESSION_ID = 'butcher-newbie-goblin-slave-mines'
CAMP_ORIGIN_ITINERARY_ID = 'butcher-goblin-gfay-crushbone-slave-mines-camp'
CAMP_ORIGIN_MAXIMUM_SECONDS = 22500.
CAMP_ORIGIN_MAXIMUM_PULSES = 39014
CAMP_ORIGIN_MAXIMUM_TOTAL_HOLD = 7802.8
CAMP_ORIGIN_MAXIMUM_DISPLACEMENT = 130051.8

_LABELS = (
    ('newbie-hills', 'L01-04_Newbie_Hills_L4_Krag_Aviak', (1, 4), (650., -2700., 0.)),
    ('goblin-camp', 'L05-08_Goblin_Camp_ALT', (5, 8), (2069., 298., 0.)),
    ('exit-hint', 'L04-10_GO_TO_GFAY_THEN_CRUSHBONE', (4, 10), (3061., 1316., 0.)),
)


def _selection_state(selection):
    from .camp_progression import CampProgressionSelection
    if type(selection) is not CampProgressionSelection:
        raise ValueError('Exact copied camp progression selection required')
    selection.check()
    return selection.state()


def _copied_state(copied):
    if (type(copied) is not itinerary._CopiedItinerary
            or type(copied.terminal) is not itinerary._CopiedTerminal):
        raise ValueError('Exact copied terminal itinerary metadata required')
    terminal = copied.terminal
    return (id(copied), copied.catalog_record, copied.ambiguous,
        id(copied.legs), tuple(flat_record_state(leg) for leg in copied.legs),
        id(copied.assets), tuple(flat_record_state(row) for row in copied.assets),
        id(terminal), flat_record_state(terminal.target), terminal.guide_record,
        terminal.operation_count, terminal.ordinary_step_count)


def _origin_profile(copied):
    # The existing profile verifies all child limits and the standard probes.
    base, bounds, basis = itinerary._terminal_profile(copied)
    if (base.maximum_seconds, base.maximum_pulses, base.maximum_total_hold,
            base.maximum_displacement_reserve) != (22680., 39021, 7804.2, 130077.7):
        raise ValueError('Review camp-origin accounting after terminal profile changes')
    declaration = replace(base, record_id=CAMP_ORIGIN_ITINERARY_ID,
        maximum_seconds=CAMP_ORIGIN_MAXIMUM_SECONDS,
        maximum_pulses=CAMP_ORIGIN_MAXIMUM_PULSES,
        maximum_total_hold=CAMP_ORIGIN_MAXIMUM_TOTAL_HOLD,
        maximum_displacement_reserve=CAMP_ORIGIN_MAXIMUM_DISPLACEMENT)
    declaration.validate()
    bounds = replace(bounds, record_id=CAMP_ORIGIN_ITINERARY_ID+'-unmeasured-envelope-v1')
    record = json.loads(basis)
    record.update(itinerary_id=CAMP_ORIGIN_ITINERARY_ID, progression_id=CAMP_PROGRESSION_ID,
        bounds=asdict(bounds), initial_probe_bounds_source='retained camp-arrival planning hypotheses',
        later_bootstrap_bounds_source='independent unmeasured audit hypotheses',
        root_limits=dict(maximum_seconds=declaration.maximum_seconds,
            maximum_pulses=declaration.maximum_pulses,
            maximum_total_hold=declaration.maximum_total_hold,
            maximum_displacement_reserve=declaration.maximum_displacement_reserve))
    record['cap_basis'].update(initial_preparation_allowance_seconds=0.,
        external_measurement_pulses=14, initial_camp_probes_charged_to_first_child=7,
        origin_reduction=dict(maximum_seconds=180., maximum_pulses=7,
            maximum_total_hold=1.4, maximum_displacement_reserve=25.9))
    return declaration, bounds, encoded(record)


def _load_progression_metadata():
    """Hash-check copied maps and guides; no terrain or current floor is read."""
    copied = itinerary._load_terminal_camp_assets(itinerary._load_copied_itinerary())
    copied_state = _copied_state(copied)
    declaration, bounds, basis = _origin_profile(copied)
    directory = Path.home()/'.local/share/eql-automation/owner-route-data'/BUTCHER_DATA_NAME
    annotations = read_camp_annotations(checked_bytes(directory/'butcher_3.txt',
                                                       BUTCHER_PINS['butcher_3.txt']))
    selected = {}
    for identifier, label, levels, xyz in _LABELS:
        matches = [row for row in annotations if row.raw_label == label]
        if len(matches) != 1 or (matches[0].level_hint, matches[0].map_xyz) != (levels, xyz):
            raise ValueError('Copied Butcher progression annotation changed')
        selected[identifier] = matches[0]
    guides = {}
    for identifier in ('newbie-hills', 'goblin-camp'):
        spec = destination_spec(identifier)
        guide = load_source_guide(directory, identifier)
        annotation = selected[identifier]
        if ((spec.zone, spec.zone_id, spec.arrival_mode) != ('butcher', 68, 'camp')
                or guide.goal != (-annotation.map_xyz[0], -annotation.map_xyz[1])
                or (guide.radius, guide.body_height) != (1.2, 6.)):
            raise ValueError('Initial progression guides differ from copied camps or body hypotheses')
        guides[identifier] = dict(guide_file_sha256=spec.file_sha256,
            guide_sha256=sha256(encoded(guide.record())).hexdigest(), goal=guide.goal)
    first = SourceItineraryGuide.from_record(json.loads(copied.assets[0].guide_record))
    if first.operations[0].start != tuple(guides['goblin-camp']['goal']):
        raise ValueError('First crossing approach no longer starts at the copied Goblin endpoint')
    evidence = encoded(dict(kind='copied-camp-progression-selection-v1',
        progression_id=CAMP_PROGRESSION_ID, itinerary_id=CAMP_ORIGIN_ITINERARY_ID,
        initial_destination_id='newbie-hills', trigger_destination_id='goblin-camp',
        terminal_destination_id='slave-mines', initial_configured_levels=[1, 4],
        crossing_observed_levels=[9, 10], source_zone='butcher', source_zone_id=68,
        source_name=declaration.legs[0].source_name,
        map_sha256=BUTCHER_PINS['butcher_3.txt'],
        catalog_file_sha256=itinerary.DATA_PINS['ZoneNames.txt'],
        catalog_sha256=declaration.legs[0].catalog_sha256,
        annotations={name: asdict(row) for name, row in selected.items()}, initial_guides=guides,
        first_crossing_destination_id=declaration.legs[0].destination_id,
        first_crossing_guide_sha256=declaration.legs[0].guide_sha256,
        first_crossing_start_xy=first.operations[0].start,
        first_crossing_goal_xy=first.goal, itinerary=asdict(declaration),
        later_bootstrap_bounds=asdict(bounds), bounds_basis_sha256=sha256(basis).hexdigest(),
        label_z_used_for_floor=False, map_hint_used_as_crossing_endpoint=False,
        live_suitability_verified=False, native_geometry_loaded=False,
        current_character_observation=False, input_authorized=False,
        movement_authorized=False, runtime_continuation_enabled=False, real_client_accepted=False))
    if _copied_state(copied) != copied_state:
        raise ValueError('Copied itinerary changed while selecting progression metadata')
    return copied, evidence


def load_owner_camp_progression(engine, declaration):
    """Select copied metadata; the owner controller separately admits activity."""
    from .camp_progression import CampProgressionSelection
    if (type(declaration) is not dict or set(declaration) != {
            'progression_id', 'open_flat_clear', 'owner_supervised_continuation'}
            or declaration.get('progression_id') != CAMP_PROGRESSION_ID
            or declaration.get('open_flat_clear') is not True
            or declaration.get('owner_supervised_continuation') is not True):
        raise ValueError('Select the explicit supervised Newbie to Slave Mines progression')
    level = engine.settings.level
    if type(level) is not int or not 1 <= level <= 4:
        raise ValueError('Progression requires a configured integer level from 1 through 4')
    request = encoded(declaration)
    binding = itinerary._ProviderOwner(engine)
    copied, evidence = _load_progression_metadata()
    binding.check(copied=copied)
    if encoded(declaration) != request:
        raise ValueError('Progression request changed during copied metadata loading')
    result = CampProgressionSelection(CAMP_PROGRESSION_ID, 'newbie-hills', 'goblin-camp',
        'slave-mines', CAMP_ORIGIN_ITINERARY_ID, evidence)
    _selection_state(result)
    return result


def _check_retained_bounds(bounds):
    if type(bounds) is not RouteMotionBounds:
        raise ValueError('Exact retained camp probe bounds required')
    bounds.validate_values(calibration_record_id=bounds.calibration_record_id,
                           maximum_step_seconds=.2)
    if ((bounds.body_radius, bounds.body_height) != (1.2, 6.)
            or any(not bounds.minimum_requested_hold <= probe.seconds <= bounds.maximum_requested_hold
                   for probe in PROBES)):
        raise ValueError('Retained camp body and requested holds must match the copied guide and probes')


@dataclass(frozen=True)
class CampOriginItineraryAssets:
    """Pinned proposals for the controller's common lazy plan factory.

    ``probe_bounds`` belongs to later zone bootstraps. Initial probes continue
    using ``retained_bounds`` and the originating camp's historical basis.
    """
    selection: object
    copied: object
    declaration: object
    probe_bounds: RouteMotionBounds
    bounds_basis: bytes
    route_guide: SourceItineraryGuide
    route_sections: WalkingSections
    retained_bounds: RouteMotionBounds
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_state', self.state())

    def state(self):
        return (_selection_state(self.selection), _copied_state(self.copied),
            _declaration_state(self.declaration), flat_record_state(self.probe_bounds),
            self.bounds_basis, id(self.route_guide), _guide_snapshot(self.route_guide),
            itinerary._section_state(self.route_sections), flat_record_state(self.retained_bounds))

    def check(self):
        if self.state() != self._state:
            raise ValueError('Camp-origin copied metadata, selection or retained bounds changed')
        self.route_sections.check()
        _check_retained_bounds(self.retained_bounds)
        self.declaration.validate()
        if self.state() != self._state:
            raise ValueError('Camp-origin metadata changed during validation')


def load_camp_origin_itinerary(selection, *, retained_bounds):
    """Materialize copied proposals, never revive an idle owner or create a root."""
    selected = _selection_state(selection)
    if (selection.profile_id != CAMP_PROGRESSION_ID
            or selection.initial_destination_id != 'newbie-hills'
            or selection.trigger_destination_id != 'goblin-camp'
            or selection.terminal_destination_id != 'slave-mines'
            or selection.itinerary_id != CAMP_ORIGIN_ITINERARY_ID):
        raise ValueError('Exact registered camp-origin progression selection required')
    _check_retained_bounds(retained_bounds)
    retained = flat_record_state(retained_bounds)
    copied, evidence = _load_progression_metadata()
    if selection.evidence != evidence:
        raise ValueError('Progression copied evidence differs from its original selection')
    copied_state = _copied_state(copied)
    declaration, bounds, basis = _origin_profile(copied)
    row = copied.assets[0]
    guide = SourceItineraryGuide.from_record(json.loads(row.guide_record))
    sections = load_guide_walking_sections(row.identifier, guide)
    if (type(sections) is not WalkingSections or sections.original is not guide
            or len(sections.guides) != 2 or sections.record_sha256 != row.sections_sha256
            or (guide.radius, guide.body_height) !=
                (retained_bounds.body_radius, retained_bounds.body_height)):
        raise ValueError('Camp-origin first guide, sections or retained body changed')
    sections.check()
    if (_selection_state(selection) != selected or flat_record_state(retained_bounds) != retained
            or _copied_state(copied) != copied_state
            or encoded(guide.record()) != row.guide_record):
        raise ValueError('Camp-origin selection, bounds or guide changed during copied loading')
    result = CampOriginItineraryAssets(selection, copied, declaration, bounds, basis,
        guide, sections, retained_bounds)
    result.check()
    return result
