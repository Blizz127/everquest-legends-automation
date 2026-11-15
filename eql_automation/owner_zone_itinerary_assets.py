"""One pinned copied itinerary, with native destination loading kept lazy.

The limits and body/movement envelope are selected test hypotheses. They are
not client measurements, an ETA, spawn evidence or permission to send input.
Only the existing owner runtime supplies observations and input authorization.
"""
from dataclasses import asdict, dataclass
from pathlib import Path

from .gfay_assets import DATA_NAME as CATALOG_DATA_NAME, DATA_PINS
from .location_log import LocationLogReader, unique_zone_ids_from_text
from .motion_calibration import PROBES
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_assets import checked_bytes
from .owner_section_assets import load_guide_walking_sections, load_owner_walking_sections
from .owner_source_assets import SourceDestinationAssets, load_owner_source_destination
from .owner_source_crossing import PinnedSourceCrossingSpec, load_owner_source_crossing, load_source_crossing_spec
from .owner_zone_tracker import LiveZoneTracker
from .route_geometry import RouteMotionBounds
from .route_step_sender import _fd_identity
from .source_destinations import load_source_guide, source_data_name
from .source_section_manifest import WalkingSections
from .supervised_route import scope_limits
from .zone_itinerary_budget import ZoneItineraryBudget, ZoneItineraryDeclaration, load_zone_itinerary
from .zone_itinerary_runtime import ZoneItineraryPlan


OWNER_ITINERARY_ID = 'butcher-gfay-crushbone'
OWNER_ITINERARY_DESTINATIONS = ('butcher-gfay-crossing', 'gfay-butcher-crushbone-crossing')
OWNER_ITINERARY_SECTION_COUNTS = (2, 8)
# Ten walking scopes, two crossing scopes, and fourteen probes outside their
# child budgets. The eight later section measurements already use child caps.
# Duration includes an explicit 1500-second destination preparation allowance;
# the shared first destination-walk lifetime can make that allowance redundant.
OWNER_ITINERARY_MAXIMUM_SECONDS = 19680.
OWNER_ITINERARY_MAXIMUM_PULSES = 36014
OWNER_ITINERARY_MAXIMUM_TOTAL_HOLD = 7202.8
OWNER_ITINERARY_MAXIMUM_DISPLACEMENT = 120051.8


@dataclass(frozen=True)
class _CopiedLeg:
    identifier: str
    guide_record: bytes
    sections_sha256: str
    section_count: int
    crossing_record: bytes


@dataclass(frozen=True)
class _CopiedItinerary:
    catalog_record: bytes
    ambiguous: frozenset
    legs: tuple
    assets: tuple


def _crossing_record(value):
    if type(value) is not PinnedSourceCrossingSpec or type(value.source_evidence) is not bytes:
        raise ValueError('Exact pinned source crossing required')
    record = asdict(value)
    record['source_evidence'] = value.source_evidence.hex()
    return encoded(record)


def _destination_state(value):
    return (id(value), id(value.planner), id(value.guide), value.destination_id,
            value.target_name, value.source_evidence, encoded(value.guide.record()),
            value.planner.zone, value.planner.zone_id, value.planner.zone_name, value.planner.pins)


def _section_state(value):
    return (id(value), id(value.original), id(value.guides), id(value.ranges),
            id(value._state), value.record_sha256, value.ranges, encoded(value.original.record()),
            tuple(encoded(guide.record()) for guide in value.guides))


def _load_copied_itinerary():
    """Read small catalog/guide/partition files, never a native zone planner."""
    directory = Path.home()/'.local/share/eql-automation/owner-route-data'
    raw = checked_bytes(directory/CATALOG_DATA_NAME/'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    catalog, ambiguous = unique_zone_ids_from_text(raw.decode('latin-1'))
    crossings = tuple(load_source_crossing_spec(identifier) for identifier in OWNER_ITINERARY_DESTINATIONS)
    indexed = dict(zip(OWNER_ITINERARY_DESTINATIONS, crossings))
    legs = load_zone_itinerary(OWNER_ITINERARY_DESTINATIONS, zone_catalog=catalog,
                               crossing_provider=indexed.__getitem__)
    rows = []
    for identifier, count, crossing in zip(OWNER_ITINERARY_DESTINATIONS,
                                         OWNER_ITINERARY_SECTION_COUNTS, crossings):
        guide = load_source_guide(directory/source_data_name(identifier), identifier)
        sections = load_guide_walking_sections(identifier, guide)
        if (type(sections) is not WalkingSections or sections.original is not guide
                or len(sections.guides) != count or (guide.radius, guide.body_height) != (1.2, 6.)):
            raise ValueError('Copied itinerary partition or body hypotheses changed')
        sections.check()
        rows.append(_CopiedLeg(identifier, encoded(guide.record()), sections.record_sha256,
                               count, _crossing_record(crossing)))
    return _CopiedItinerary(encoded(catalog), frozenset(ambiguous), legs, tuple(rows))


def _profile(copied):
    if (tuple(row.section_count for row in copied.assets) != OWNER_ITINERARY_SECTION_COUNTS
            or any(scope_limits(scope) != (1500., 3000, 10000., 600.)
                   for scope in ('destination_travel', 'zone_crossing_corridor'))
            or tuple((p.key, p.seconds) for p in PROBES) != (
                ('forward', .1), ('right', .05), ('forward', .1), ('right', .15),
                ('forward', .1), ('left', .15), ('forward', .1))):
        raise ValueError('Itinerary profile needs review after child scope or probe changes')
    bounds = RouteMotionBounds(OWNER_ITINERARY_ID+'-unmeasured-envelope-v1',
        'independent-audit-hypotheses', .01, .15, .2, 30., .4, .01, 2., .1, 1.2, 6.)
    declaration = ZoneItineraryDeclaration(OWNER_ITINERARY_ID, copied.legs,
        OWNER_ITINERARY_MAXIMUM_SECONDS, OWNER_ITINERARY_MAXIMUM_PULSES,
        OWNER_ITINERARY_MAXIMUM_TOTAL_HOLD, OWNER_ITINERARY_MAXIMUM_DISPLACEMENT)
    basis = encoded(dict(kind='explicit-unmeasured-itinerary-hypotheses-v1',
        itinerary_id=OWNER_ITINERARY_ID, bounds=asdict(bounds),
        source='same independent profile as the copied GFay transit audit',
        catalog_file_sha256=DATA_PINS['ZoneNames.txt'],
        section_counts=OWNER_ITINERARY_SECTION_COUNTS,
        root_limits=dict(maximum_seconds=declaration.maximum_seconds,
            maximum_pulses=declaration.maximum_pulses,
            maximum_total_hold=declaration.maximum_total_hold,
            maximum_displacement_reserve=declaration.maximum_displacement_reserve),
        cap_basis=dict(walking_scopes=10, crossing_scopes=2,
            external_measurement_pulses=14, section_measurement_pulses_already_in_child_budgets=56,
            initial_preparation_allowance_seconds=180., destination_preparation_allowance_seconds=1500.,
            simultaneous_child_limit_exhaustion_guaranteed=False),
        client_motion_bounds_measured=False, current_character_observation=False,
        destination_server_verified=False, spawn_coordinate_verified=False,
        input_authorized=False, real_client_accepted=False))
    return declaration, bounds, basis


class _ProviderOwner:
    """Capture the original request; adopt only its exact later root owner."""
    def __init__(self, engine):
        self.engine = engine
        self.tracker = engine.live_zone_tracker
        if type(self.tracker) is not LiveZoneTracker or type(self.tracker.reader) is not LocationLogReader:
            raise ValueError('Current observed owner zone tracker required')
        self.reader, self.settings = self.tracker.reader, settings_identity(engine.settings)
        self.sender, self.gate = engine.sender, engine.gate
        if self.sender is None:
            raise ValueError('Released existing owner sender required')
        self.ui = self.sender.ui
        self.generation = engine.cancel_generation
        self.epochs = engine.supervised_epoch, engine.route_session_epoch
        if any(type(value) is not int or value < 0 for value in (self.generation, *self.epochs)):
            raise ValueError('Exact owner generation and request epochs required')
        self.owner_binding = self.tracker.owner_binding
        self.tail = self.reader.tail
        self.log_identity = self.tail.identity, self.tail.epoch, self.tail.path
        self.initial_zone_generation = self.reader.zone_generation
        self.owner = self.root = self.journey = None
        self.valid = True
        self.fd = self.ui.fileno()
        self.fd_identity = _fd_identity(self.fd)
        self.window = window_identity(self.gate, require_focus=False)
        self.check()

    def check(self, *, copied=None, plan=None, identifier=None):
        e, tracker, reader = self.engine, self.tracker, self.reader
        if not self.valid:
            raise ValueError('Itinerary asset provider was retired')
        owner = None if plan is None else getattr(e, 'zone_itinerary_owner', None)
        if plan is not None:
            from .owner_zone_itinerary import _ItineraryOwner
            if (type(owner) is not _ItineraryOwner or owner.engine is not e or owner.plan is not plan
                    or type(owner.root) is not ZoneItineraryBudget
                    or owner.root.declaration is not plan.declaration):
                raise ValueError('Lazy assets require the original itinerary owner and root')
            if self.owner is None:
                self.owner, self.root, self.journey = owner, owner.root, owner.journey
            if owner is not self.owner or owner.root is not self.root or owner.journey is not self.journey:
                raise ValueError('Itinerary owner, root or journey was replaced')
            owner.check()
        tracker.check_binding()
        window = window_identity(self.gate, require_focus=False)
        descriptor = self.ui.fileno()
        descriptor_identity = _fd_identity(self.fd)
        settings = settings_identity(e.settings)
        queue_empty = e.jobs.empty()
        if plan is not None:
            plan.check()
        expected_log = Path(self.settings[1])/'Logs'/f'eqlog_{self.settings[2]}_{self.settings[3]}.txt'
        if (not self.valid or e.live_zone_tracker is not tracker or tracker.closed
                or tracker.reader is not reader or tracker.owner_binding is not self.owner_binding
                or e.sender is not self.sender or self.sender.ui is not self.ui or e.gate is not self.gate
                or e.cancel_generation != self.generation
                or (e.supervised_epoch, e.route_session_epoch) != self.epochs or settings != self.settings
                or descriptor != self.fd or descriptor_identity != self.fd_identity or window != self.window
                or e.stopping or not queue_empty or self.sender.held
                or self.sender.unfinished or self.sender.dismissed
                or getattr(self.sender, '_eql_route_operation', None) is not None
                or reader.tail is not self.tail or self.tail.identity is None or self.tail.partial
                or (self.tail.identity, self.tail.epoch, self.tail.path) != self.log_identity
                or self.tail.path != expected_log
                or (reader.expected_character, reader.expected_server) != self.settings[2:4]):
            raise ValueError('Itinerary request, process, sender, log or owner binding changed')
        if copied is not None and (encoded(reader.zone_ids) != copied.catalog_record
                or frozenset(reader.ambiguous_zone_names) != copied.ambiguous):
            raise ValueError('Observed log catalog differs from the checked copied catalog')
        if plan is None:
            if (e.journey is not None or getattr(e, 'zone_itinerary_owner', None) is not None
                    or tracker.lease is not None or reader.zone_id != 68
                    or reader.zone_generation != self.initial_zone_generation
                    or copied is not None and (reader.zone_id, reader.zone_display_name) !=
                        (copied.legs[0].source_zone_id, copied.legs[0].source_name)):
                raise ValueError('Itinerary must start in the unchanged observed Butcherblock zone')
            return None
        if (owner.closed or e.zone_itinerary_owner is not owner or owner.root is not self.root
                or owner.journey is not self.journey or e.journey is not self.journey
                or self.journey is None or self.journey.destination_id != identifier
                or identifier not in OWNER_ITINERARY_DESTINATIONS
                or self.root.leg.destination_id != identifier
                or (reader.zone_id, reader.zone_display_name) !=
                    (self.root.leg.source_zone_id, self.root.leg.source_name)
                or self.root.stage.phase not in ('walking', 'bootstrap') or not self.root.valid):
            raise ValueError('Lazy assets differ from the current observed itinerary leg')
        return self.root.stage, self.journey, reader.zone_generation


def load_owner_zone_itinerary(engine, declaration):
    """Resolve the selected copied plan without opening native zone geometry."""
    if (type(declaration) is not dict or set(declaration) != {
            'itinerary_id', 'open_flat_clear', 'owner_supervised_continuation'}
            or declaration.get('itinerary_id') != OWNER_ITINERARY_ID
            or declaration.get('open_flat_clear') is not True
            or declaration.get('owner_supervised_continuation') is not True):
        raise ValueError('Select the explicit supervised Butcherblock to Crushbone itinerary')
    request = encoded(declaration)
    binding = _ProviderOwner(engine)
    copied = _load_copied_itinerary()
    binding.check(copied=copied)
    if encoded(declaration) != request:
        raise ValueError('Itinerary request changed during copied asset loading')
    limits, bounds, basis = _profile(copied)
    rows = {row.identifier: row for row in copied.assets}
    destination_loader, section_loader, crossing_loader = (
        load_owner_source_destination, load_owner_walking_sections, load_owner_source_crossing)
    plan = None

    def load(kind, identifier, assets=None):
        try:
            scope = binding.check(copied=copied, plan=plan, identifier=identifier)
            row = rows[identifier]
            if kind == 'destination':
                result = destination_loader(engine)
                if type(result) is not SourceDestinationAssets or result.destination_id != identifier:
                    raise ValueError('Lazy destination loader changed the selected guide')
                result.check()
                if encoded(result.guide.record()) != row.guide_record:
                    raise ValueError('Lazy destination guide differs from its copied plan')
                pin, pin_reader = _destination_state(result), _destination_state
            elif kind == 'sections':
                if type(assets) is not SourceDestinationAssets or assets.destination_id != identifier:
                    raise ValueError('Exact selected destination assets required for sections')
                assets.check()
                if encoded(assets.guide.record()) != row.guide_record:
                    raise ValueError('Section guide differs from its copied plan')
                result = section_loader(engine, assets)
                if (type(result) is not WalkingSections or result.original is not assets.guide
                        or len(result.guides) != row.section_count
                        or result.record_sha256 != row.sections_sha256):
                    raise ValueError('Lazy walking partition differs from its copied plan')
                result.check()
                pin, pin_reader = _section_state(result), _section_state
            else:
                result = crossing_loader(engine, identifier)
                if _crossing_record(result) != row.crossing_record:
                    raise ValueError('Lazy crossing differs from its copied plan')
                pin, pin_reader = row.crossing_record, _crossing_record
            if binding.check(copied=copied, plan=plan, identifier=identifier) != scope:
                raise ValueError('Itinerary stage changed during asset loading')
            if pin_reader(result) != pin:
                raise ValueError('Itinerary asset changed during final owner validation')
            return result
        except BaseException:
            binding.valid = False
            raise

    plan = ZoneItineraryPlan(limits, bounds, basis,
        lambda identifier: load('destination', identifier),
        lambda assets: load('sections', getattr(assets, 'destination_id', None), assets),
        lambda identifier: load('crossing', identifier))
    binding.check(copied=copied)
    if encoded(declaration) != request:
        raise ValueError('Itinerary request changed before plan publication')
    plan.check()
    return plan
