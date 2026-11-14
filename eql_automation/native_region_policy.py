"""Explicit native-zero policy for copied Crushbone geometry and height.

This does not authorize movement. The original BSP result is retained, and
terrain/static collision remain separate. Installed binary matching, the
native bounds query and actual body/movement behavior are still unverified.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from .client_region_classification import (
    ARITHMETIC, MODEL, CLIENT_SHA256, ENGINE_SHA256, ClientBspClassificationView)
from .ground_binding import digest
from .native_body_regions import classify_source_body_regions
from .static_floor_guard import check_static_floor


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def pin(value):
    return sha256(encoded(value)).hexdigest()


@dataclass(frozen=True)
class NativeRegionPlanningEvidence:
    """Bytes keep nested classification dictionaries out of mutable state."""
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Native planning evidence seal changed')
        value = json.loads(self.payload)
        if encoded(value) != self.payload:
            raise ValueError('Native planning evidence is not canonical')
        return value


@dataclass(frozen=True)
class NativeZeroRegionTrialPolicy:
    mesh_sha256: str
    archive_sha256: str
    wld_sha256: str
    static_inventory_sha256: str
    bsp_inventory_sha256: str
    classification_inventory_sha256: str
    classifier: ClientBspClassificationView

    def __post_init__(self):
        if (not all(digest(v) for v in (self.mesh_sha256, self.archive_sha256,
                self.wld_sha256, self.static_inventory_sha256,
                self.bsp_inventory_sha256, self.classification_inventory_sha256))
                or type(self.classifier) is not ClientBspClassificationView):
            raise ValueError('Pinned native planning policy required')
        self.check_classifier()

    def record(self):
        return dict(format='eql-native-zero-planning-policy-v2', zone='crushbone',
            scope='copied_initial_and_per_move_geometry; supervised_measurement_only',
            mesh_sha256=self.mesh_sha256, archive_sha256=self.archive_sha256,
            wld_sha256=self.wld_sha256, static_inventory_sha256=self.static_inventory_sha256,
            bsp_inventory_sha256=self.bsp_inventory_sha256,
            classification_inventory_sha256=self.classification_inventory_sha256,
            client_sha256=CLIENT_SHA256, engine_sha256=ENGINE_SHA256,
            model=MODEL, arithmetic=ARITHMETIC, installed_binary_match_verified=False,
            native_bounds_checked=False, input_authorized=False, real_client_accepted=False)

    def check_classifier(self):
        self.classifier._check()
        if (self.classifier.wld_sha256 != self.wld_sha256
                or self.classifier.inventory_sha256 != self.classification_inventory_sha256):
            raise ValueError('Native planning classifier differs from policy')

    def check_context(self, *, zone, pins, bsp):
        self.check_classifier()
        if (zone != 'crushbone'
                or pins != (self.mesh_sha256, self.archive_sha256,
                            self.wld_sha256, self.static_inventory_sha256)
                or bsp.inventory_sha256 != self.bsp_inventory_sha256
                or bsp.wld_sha256 != self.wld_sha256):
            raise ValueError('Native planning policy is only for its pinned Crushbone views')

    def _payload(self, terrain, static, bsp, native):
        """Validate every piece, not just the aggregate possible_flags tuple."""
        self.check_classifier()
        try:
            step = terrain['floor_step']
            selected = step['selected_ids']
            if (terrain['candidate'] is not True or step['candidate'] is not True
                    or step['occupancy']['candidate'] is not True
                    or selected != step['occupancy']['selected_ids'] or not selected
                    or static['candidate'] is not True or static['occupancy']['candidate'] is not True
                    or static['static_inventory_sha256'] != self.static_inventory_sha256
                    or bsp['candidate'] is not True and not (
                        bsp['candidate'] is False and bsp['reason'] == 'missing_bsp_child'
                        and bsp['traversal']['reason'] == 'missing_bsp_child')
                    or bsp['wld_sha256'] != self.wld_sha256
                    or bsp['bsp_inventory_sha256'] != self.bsp_inventory_sha256
                    or bsp['selected_ids'] != selected
                    or bsp['floor_proof_sha256'] != step['proof_sha256']
                    or bsp['geometry_sha256'] != step['geometry_sha256']
                    or not digest(step['proof_sha256']) or not digest(step['geometry_sha256'])
                    or native['complete'] is not True
                    or native['reason'] != 'native_body_metadata_only'
                    or native['floor_proof_sha256'] != step['proof_sha256']
                    or native['geometry_sha256'] != step['geometry_sha256']
                    or native['static_inventory_sha256'] != self.static_inventory_sha256
                    or native['classification_inventory_sha256'] != self.classification_inventory_sha256
                    or native['possible_flags'] != [0]
                    or native['grounded_body_assumed'] is not True
                    or native['terrain_collision_margins_unchanged'] is not True
                    or any(native[k] is not False for k in ('below_floor_classified',
                        'native_bounds_checked', 'collision_behavior_verified',
                        'input_authorized', 'real_client_accepted'))
                    or native['volume_scope'] !=
                        'above_each_checked_source_floor_patch; original_AABB_enclosure'):
                raise ValueError('Native-zero planning needs matching complete terrain/static/body evidence')
            pieces = native['pieces']
            if not pieces or [p['selected_id'] for p in pieces] != selected:
                raise ValueError('Native body pieces do not cover the selected floor')
            for piece in pieces:
                c = piece['classification']
                if (c['complete'] is not True or not c['possible_classes']
                        or c['inventory_sha256'] != self.classification_inventory_sha256
                        or c['wld_sha256'] != self.wld_sha256
                        or c['query_scope'] != MODEL or c['arithmetic'] != ARITHMETIC
                        or not digest(c['volume_sha256']) or not digest(c['trace_sha256'])
                        or any(c[k] is not False for k in ('ancestor_clipping_used',
                            'bounds_checked', 'collision_verified', 'input_authorized', 'real_client_accepted'))
                        or any(type(v['flags']) is not int or v['flags'] != 0
                               or type(v['class_id']) is not int or v['class_id'] != 0
                               for v in c['possible_classes'])):
                    raise ValueError('Every native body classification must have complete full flags zero')
            if any(item[k] is not False for item in (terrain, static, bsp)
                   for k in ('input_authorized', 'real_client_accepted')):
                raise ValueError('Planning evidence cannot claim input or live acceptance')
        except (KeyError, TypeError, IndexError) as error:
            raise ValueError('Malformed native planning evidence') from error
        return dict(format='eql-native-zero-planning-evidence-v1', policy=self.record(),
            terrain_sha256=pin(terrain), static_sha256=pin(static), bsp_sha256=pin(bsp),
            native_body=native, native_body_sha256=pin(native),
            measurement_planning_allowed=True, input_authorized=False, real_client_accepted=False)

    def evaluate(self, terrain, footprint, sources, static_view, bsp):
        # Recheck the exact terrain/static cell before recording native metadata.
        static = check_static_floor(terrain, footprint, sources, static_view)
        native = classify_source_body_regions(terrain.floor_step, footprint, sources,
            static_view, self.classifier, source_wld_sha256=self.wld_sha256)
        records = json.loads(encoded([asdict(x) for x in (terrain, static, bsp, native)]))
        payload = encoded(self._payload(*records))
        return NativeRegionPlanningEvidence(payload, sha256(payload).hexdigest()), static

    def validate(self, evidence, *, terrain, static, bsp):
        if type(evidence) is not NativeRegionPlanningEvidence:
            raise ValueError('Exact sealed native planning evidence required')
        saved = evidence.record()
        current = self._payload(terrain, static, bsp, saved['native_body'])
        if encoded(current) != evidence.payload:
            raise ValueError('Native planning evidence no longer matches its floor or policy')
        return True
