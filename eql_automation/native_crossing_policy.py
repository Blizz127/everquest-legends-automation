"""Offline source cells approaching one exact native transition region.

This is distinct from ordinary native-zero travel. It does not authorize
movement, commit an arrived floor, prove a server destination, or replace the
runtime loading/arrival handshake. The copied original BSP result is retained.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math

from .bsp_floor_guard import check_source_body_bsp
from .client_region_classification import NativeRegionClass
from .native_body_regions import classify_source_body_regions
from .native_region_policy import NativeZeroRegionTrialPolicy, encoded
from .route_floor_commit import _chain_snapshot
from .source_detour import swept_square
from .source_itinerary import xy
from .source_probe_geometry import _source_storage
from .static_floor_guard import check_source_static_floor
from .ground_binding import finite
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class SourceCrossingCell:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Source crossing cell seal changed')
        value = json.loads(self.payload)
        if encoded(value) != self.payload:
            raise ValueError('Source crossing cell is not canonical')
        return value


@dataclass(frozen=True)
class NativeCrossingRegionPolicy:
    ordinary: NativeZeroRegionTrialPolicy
    expected_zone_line: ExpectedZoneLine

    def __post_init__(self):
        if (type(self.ordinary) is not NativeZeroRegionTrialPolicy
                or type(self.expected_zone_line) is not ExpectedZoneLine):
            raise ValueError('Exact native policy and expected transition required')
        self.check_classifier()

    def check_classifier(self):
        p, line = self.ordinary, self.expected_zone_line
        p.check_classifier()
        line.check_sources(zone=p.zone, mesh_sha256=p.mesh_sha256,
            archive_sha256=p.archive_sha256, wld_sha256=p.wld_sha256)
        if line.bsp_inventory_sha256 != p.bsp_inventory_sha256:
            raise ValueError('Native crossing BSP source differs')
        classifier = p.classifier
        regions = tuple(i for i, record in enumerate(classifier.mapping)
            if record >= 0 and classifier.records[record][1] == line.raw_label)
        if regions != line.region_ids:
            raise ValueError('Expected transition differs from effective native region mapping')
        for region in regions:
            value = classifier._region(region)
            if (value.flags != 0x80000000 or value.class_id != 0
                    or value.origin != 'typed_region' or value.matched_prefix != 'DR'
                    or value.callback_invoked is not True
                    or value.transition_write_kind != 'copy_complete_label'
                    or value.transition_source != line.raw_label):
                raise ValueError('Expected native region is not the exact pure DR transition')

    def check_context(self, terrain, static, bsp):
        self.check_classifier()
        p = self.ordinary
        p.check_context(zone=p.zone, pins=(p.mesh_sha256, terrain.archive_sha256,
            terrain.wld_sha256, static.inventory_sha256), bsp=bsp)
        self.expected_zone_line.check_bsp(bsp)

    def record(self):
        self.check_classifier()
        return dict(format='eql-native-crossing-region-policy-v1',
            ordinary=self.ordinary.record(), expected_zone_line=self.expected_zone_line.record(),
            scope='offline_source_cell_only', input_authorized=False,
            destination_verified=False, real_client_accepted=False)

    def classify(self, native):
        """Require complete native evidence; preserve every possible outcome."""
        self.check_classifier()
        p, line = self.ordinary, self.expected_zone_line
        if (native.complete is not True or native.reason != 'native_body_metadata_only'
                or native.classification_inventory_sha256 != p.classification_inventory_sha256
                or not native.pieces):
            raise ValueError('Complete native crossing body evidence required')
        flags = set(); touched = set()
        for piece in native.pieces:
            c = piece['classification']
            if (c['complete'] is not True or not c['possible_classes']
                    or c['inventory_sha256'] != p.classification_inventory_sha256
                    or c['wld_sha256'] != p.wld_sha256):
                raise ValueError('Incomplete or foreign native crossing piece')
            for value in c['possible_classes']:
                region = value['region_id']
                if region is None:
                    expected = NativeRegionClass('missing_child', 0, 0)
                elif type(region) is int and 0 <= region < len(p.classifier.mapping):
                    expected = p.classifier._region(region)
                else:
                    raise ValueError('Invalid native crossing region identity')
                if value != asdict(expected):
                    raise ValueError('Native crossing outcome differs from copied classification')
                flags.add(expected.flags)
                if expected.flags == 0 and expected.class_id == 0:
                    continue
                if (region not in line.region_ids or expected.flags != 0x80000000
                        or expected.raw_label != line.raw_label):
                    raise ValueError('Crossing contains another native hazard or transition')
                touched.add(region)
        if tuple(sorted(flags)) != native.possible_flags:
            raise ValueError('Native crossing aggregate differs from its complete pieces')
        return tuple(sorted(touched))


def check_source_crossing_cell(prefix, start, end, *, radius, terrain, static, bsp, policy):
    """Fork the supplied floor and check one proposed footprint without input.

    Returned ancestry is for offline continuation only. Even a possible native
    transition overlap does not prove that a client will zone during movement.
    """
    if (type(policy) is not NativeCrossingRegionPolicy or not xy(start) or not xy(end)
            or not finite(radius) or not .05 <= radius <= 10 or math.dist(start, end) > 80):
        raise ValueError('Explicit bounded source crossing cell required')
    policy.check_context(terrain, static, bsp)
    original = _chain_snapshot(prefix)
    policy_record = policy.record()
    policy_state = encoded(policy_record)
    classifier = policy.ordinary.classifier
    storage = _source_storage(terrain, static)
    def identity():
        return (id(policy.ordinary), tuple(vars(policy.ordinary).items()),
                id(policy.expected_zone_line), tuple(vars(policy.expected_zone_line).items()))
    policy_identity = identity()
    prefix.floor_at(start)
    if prefix.inventory_sha256 != policy.ordinary.wld_sha256:
        raise ValueError('Crossing source floor belongs to another inventory')
    footprint = swept_square(start, end, radius)
    sources = terrain.source_faces_for_footprint(footprint)
    if _chain_snapshot(prefix) != original:
        raise ValueError('Crossing source prefix or policy changed during checking')
    branch = prefix.fork()
    floor = branch.advance(footprint, sources)
    if not floor.candidate:
        raise ValueError('Crossing terrain: '+floor.reason)
    placed = check_source_static_floor(floor, footprint, sources, static)
    if not placed.candidate:
        raise ValueError('Crossing static: '+placed.reason)
    # Keep both the original refusal and the explicitly scoped BSP result.
    original_bsp = check_source_body_bsp(floor, footprint, sources, bsp, clip_branches=True)
    scoped_bsp = check_source_body_bsp(floor, footprint, sources, bsp, clip_branches=True,
                                     expected_zone_line=policy.expected_zone_line)
    if not scoped_bsp.candidate and scoped_bsp.reason != 'missing_bsp_child':
        raise ValueError('Crossing BSP: '+scoped_bsp.reason)
    native = classify_source_body_regions(floor, footprint, sources, static,
        classifier, source_wld_sha256=policy.ordinary.wld_sha256)
    touched = policy.classify(native)
    start_height, end_height = branch.floor_at(start)[0], branch.floor_at(end)[0]
    policy.check_context(terrain, static, bsp)
    current_policy = encoded(policy.record())
    if (_chain_snapshot(prefix) != original or current_policy != policy_state
            or identity() != policy_identity or policy.ordinary.classifier is not classifier
            or _source_storage(terrain, static) != storage):
        raise ValueError('Crossing source prefix or policy changed during checking')
    evidence = dict(format='eql-source-crossing-cell-v1', policy=policy_record,
        start=start, end=end, radius=radius, footprint=footprint,
        departure_floor_sha256=prefix.previous.proof_sha256,
        terrain=asdict(floor), static=asdict(placed), original_bsp=asdict(original_bsp),
        scoped_bsp=asdict(scoped_bsp), native=asdict(native),
        start_floor_height=start_height, end_floor_height=end_height,
        possible_transition_regions=touched, geometry_candidate=True,
        source_floor_committed=False, runtime_ready=False,
        input_authorized=False, real_client_accepted=False)
    payload = encoded(evidence)
    return branch, SourceCrossingCell(payload, sha256(payload).hexdigest())
