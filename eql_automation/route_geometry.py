"""Terrain/static/BSP preparation for the receipt-bound route sender.

All movement/body bounds are supplied by the caller. This module measures
nothing and grants no input authority. The independent live scene/command
guard is still required by run_checked_route_step. A slow geometry check
expires normally; it must never renew the proposal timestamp.
"""
from copy import copy, deepcopy
from dataclasses import asdict, dataclass, field
import json
from types import MappingProxyType

from .bsp_floor_guard import check_bsp_floor
from .fixed_route_follower import finite
from .floor_replay import check_floor_trial
from .ground_sweep import motion_footprint
from .native_region_policy import NativeZeroRegionTrialPolicy, encoded, pin
from .route_floor_commit import RouteFloorCommit, _binding_snapshot, _chain_snapshot
from .route_precision import precision_binding, validate_precision_seams
from .static_floor_guard import check_static_floor


@dataclass(frozen=True)
class RouteMotionBounds:
    record_id: str
    calibration_record_id: str
    minimum_requested_hold: float
    maximum_requested_hold: float
    maximum_actual_hold: float
    forward_speed_upper_bound: float
    pivot_displacement_upper_bound: float
    position_error: float
    heading_error_degrees: float
    post_release_drift: float
    body_radius: float
    body_height: float

    def validate(self, runner, chain):
        self.validate_values(calibration_record_id=runner.calibration,
                             maximum_step_seconds=runner.max_step_seconds)
        if self.body_height != chain.body_height:
            raise ValueError('Missing matching external motion/body bounds')

    def validate_values(self, *, calibration_record_id, maximum_step_seconds):
        """Validate explicit hypotheses before a follower/floor chain exists."""
        values = (self.minimum_requested_hold, self.maximum_requested_hold,
                  self.maximum_actual_hold, self.forward_speed_upper_bound,
                  self.pivot_displacement_upper_bound, self.position_error,
                  self.heading_error_degrees, self.post_release_drift,
                  self.body_radius, self.body_height)
        if (not isinstance(self.record_id, str) or not self.record_id
                or self.calibration_record_id != calibration_record_id
                or not isinstance(calibration_record_id,str) or not calibration_record_id
                or not finite(maximum_step_seconds) or not 0<maximum_step_seconds<=.2
                or not all(finite(v) for v in values)
                or not 0 < self.minimum_requested_hold <= self.maximum_requested_hold
                    <= self.maximum_actual_hold <= maximum_step_seconds
                or self.forward_speed_upper_bound <= 0
                or min(self.pivot_displacement_upper_bound, self.position_error,
                       self.post_release_drift) < 0
                or not 0 <= self.heading_error_degrees <= 180
                or not 0 < self.body_radius <= 100
                or not 0 < self.body_height <= 100):
            raise ValueError('Missing matching external motion/body bounds')


@dataclass(frozen=True)
class RouteGeometryRecord:
    ticket: object
    terrain: object
    static: object
    bsp: object
    precision_policy: object = None
    expected_zone_line: object = None
    region_policy: object = None
    native_region_evidence: object = None
    input_authorized: bool = field(default=False, init=False)
    real_client_accepted: bool = field(default=False, init=False)


class RouteGeometryPreparer:
    """Concrete ``prepare_step`` callback; retains the exact ticket's checks.

    Load and pin the copied source views before invoking the sender. The
    static inventory pin must come from the selected zone's complete placement
    audit. Neither a record name nor successful source checks establishes that
    supplied bounds describe the current client. Live authorization must do so.
    """
    def __init__(self, ledger, *, ground, source, static, bsp, bounds,
                 static_inventory_sha256, vertical_window,
                 maximum_source_z_difference, precision_policy=None, expected_zone_line=None,
                 region_policy=None):
        if (not isinstance(ledger, RouteFloorCommit)
                or not isinstance(bounds, RouteMotionBounds)
                or not finite(vertical_window) or not 0 < vertical_window <= 100
                or not finite(maximum_source_z_difference)
                or not 0 < maximum_source_z_difference <= 100):
            raise ValueError('Need route ledger, explicit bounds and ground tolerances')
        self.ledger = ledger
        self.ground, self.source, self.static, self.bsp = ground, source, static, bsp
        self.bounds = bounds
        self.static_inventory_sha256 = static_inventory_sha256
        self.vertical_window = vertical_window
        self.maximum_source_z_difference = maximum_source_z_difference
        self.precision_policy = precision_policy
        self.expected_zone_line = expected_zone_line
        if region_policy is not None and type(region_policy) is not NativeZeroRegionTrialPolicy:
            raise ValueError('Explicit native region policy required')
        self.region_policy = self._region_policy = region_policy
        self._classifier = region_policy.classifier if region_policy else None
        self._region_pin = pin(region_policy.record()) if region_policy else None
        self._zone_line = self._zone_line_binding()
        self._precision = self._precision_binding()
        validate_precision_seams(source, precision_policy)
        self._record = None
        self._record_context = None
        self._issued_record = self._record_seal = None
        self._cache = None
        self._cache_seals = None
        self._bindings()

    def _zone_line_binding(self):
        line=self.expected_zone_line
        r=self.ledger.runner;g=r.geometry_evidence
        if line!=g.expected_zone_line:
            raise ValueError('Route observations and footprint need the same expected zone line')
        if line is None:return None
        from .zone_line import ExpectedZoneLine
        if not isinstance(line,ExpectedZoneLine):
            raise ValueError('Explicit expected zone-line geometry required')
        line.check_geometry(zone=r.route.zone,mesh_sha256=r.route.mesh_sha256,
            archive_sha256=g.source_archive_sha256,wld_sha256=g.source_wld_sha256,bsp=self.bsp)
        if self.ground.polygons_for_area(line.area_id)!=line.polygon_ids:
            raise ValueError('Zone-line polygon inventory changed')
        return line.sha256

    def _precision_binding(self):
        r = self.ledger.runner
        return precision_binding(self.source, self.precision_policy,
            zone=r.route.zone, mesh_sha256=r.route.mesh_sha256,
            archive_sha256=r.geometry_evidence.source_archive_sha256)

    def _bindings(self):
        r = self.ledger.runner
        self.bounds.validate(r, self.ledger.chain)
        g = r.geometry_evidence
        if self.region_policy is not self._region_policy:
            raise ValueError('Route native region policy changed')
        if self.region_policy is not None:
            p = self.region_policy
            if (r.mode_reader() != 'measurement' or self.expected_zone_line is not None
                    or p.classifier is not self._classifier or pin(p.record()) != self._region_pin
                    or r.height_calibration.zone_id != 58
                    or self.ledger.chain.inventory_sha256 != p.wld_sha256):
                raise ValueError('Native region geometry requires its original Crushbone measurement scope')
            p.check_context(zone=r.route.zone, pins=(r.route.mesh_sha256,
                g.source_archive_sha256, g.source_wld_sha256, self.static_inventory_sha256), bsp=self.bsp)
        if (getattr(self.source, 'ground', None) is not self.ground
                or getattr(self.source, 'mesh_sha256', None) != r.route.mesh_sha256
                or getattr(self.ground, 'mesh_sha256', None) != r.route.mesh_sha256
                or self.source.archive_sha256 != g.source_archive_sha256
                or self.source.wld_sha256 != g.source_wld_sha256
                or self.bsp.wld_sha256 != g.source_wld_sha256
                or not isinstance(self.static_inventory_sha256, str)
                or len(self.static_inventory_sha256) != 64
                or any(c not in '0123456789abcdef' for c in self.static_inventory_sha256)
                or self.static.inventory_sha256 != self.static_inventory_sha256
                or self._precision_binding() != self._precision
                or self._zone_line_binding() != self._zone_line
                or self.maximum_source_z_difference > g.maximum_source_baked_z_difference):
            raise ValueError('Route geometry source or inventory binding differs')

    def record_for(self, ticket):
        """Read checks only while this exact one-use ticket remains pending."""
        with self.ledger.lock:
            self.ledger.check_pending(ticket)
            self._bindings()
            if (self._record is None or self._record.ticket is not ticket
                    or self._record is not self._issued_record
                    or self._context() != self._record_context):
                raise ValueError('No geometry record for this exact ticket')
            record = self._record
            if not self.regions_allowed(record):
                raise ValueError('Route region evidence refused')
            if self.region_policy is not None and (
                    self._seal(record.terrain, record.static, record.bsp, record.native_region_evidence)
                    != self._record_seal
                    or record.terrain.floor_step.geometry_sha256 != ticket.preparation.geometry_sha256):
                raise ValueError('Native geometry record differs from its exact ticket')
            return self._record

    def regions_allowed(self, record):
        """Shared decision for this exact record; legacy BSP is never rewritten."""
        if record.region_policy is not self.region_policy:
            return False
        if self.region_policy is None:
            return record.native_region_evidence is None and record.bsp.candidate is True
        values = json.loads(encoded([asdict(x) for x in (record.terrain, record.static, record.bsp)]))
        return self.region_policy.validate(record.native_region_evidence,
            **dict(zip(('terrain', 'static', 'bsp'), values)))

    def _seal(self, terrain, static, bsp, native):
        if self.region_policy is None:
            return None
        record = RouteGeometryRecord(None, terrain, static, bsp,
            region_policy=self.region_policy, native_region_evidence=native)
        if not self.regions_allowed(record):
            raise ValueError('Native geometry evidence refused')
        return (id(native), native.sha256, pin([asdict(x) for x in (terrain, static, bsp)]))

    def _context(self):
        r = self.ledger.runner
        return (_binding_snapshot(r), r.index, r.last_seq, r.last_fix_at, r.steps,
                r.component, r.released_at, r.step_started_at, r.best_remaining,
                r.no_progress_steps, id(r.pose), deepcopy(vars(r.pose)),
                self.bounds, self.vertical_window, self.maximum_source_z_difference,
                id(self.ground), id(self.source), id(self.static), id(self.bsp),
                self.static_inventory_sha256, self.bsp.inventory_sha256,
                self._precision_binding(),self._zone_line_binding(),
                id(self.region_policy), id(self._classifier), self._region_pin)

    def _trial(self, kind, position, heading, component, chain, bounds):
        b = bounds
        reach = b.forward_speed_upper_bound * b.maximum_actual_hold if kind == 'forward' else 0.
        pivot_radius = b.pivot_displacement_upper_bound if kind == 'pivot' else 0.
        footprint = motion_footprint(position[:2], heading, reach,
            position_error=b.position_error, heading_error_degrees=b.heading_error_degrees,
            post_release_drift=b.post_release_drift, extra_radius=b.body_radius + pivot_radius)
        crossing={} if self.expected_zone_line is None else dict(expected_zone_line=self.expected_zone_line)
        original, detail_ids = self.ground.check(footprint, reference=position,
            component=component, vertical_window=self.vertical_window,**crossing)
        sources = self.source.source_faces_for_footprint(footprint)
        fork, trial = check_floor_trial(self.source, chain, original, footprint, detail_ids,
            reference=position, component=component, vertical_window=self.vertical_window,
            maximum_source_z_difference=self.maximum_source_z_difference,
            allow_overlap=self.precision_policy.allow_overlap if self.precision_policy else False,**crossing)
        if not trial.candidate:
            return 'Terrain: ' + trial.reason
        static = check_static_floor(trial, footprint, sources, self.static)
        if not static.candidate:
            return 'Static geometry: ' + static.reason
        bsp = check_bsp_floor(trial, footprint, sources, self.bsp,**crossing)
        native = None
        if self.region_policy is not None:
            native, static = self.region_policy.evaluate(trial, footprint, sources, self.static, bsp)
        elif not bsp.candidate:
            return 'BSP volume: ' + bsp.reason
        return (footprint, sources, fork, trial, static, bsp, _chain_snapshot(fork), native)

    def precompute(self, scene):
        """Evaluate both controls while stopped, before the fresh proposal.

        No input is armed here. This does not extend the reference's 0.5s
        lifetime. Exact arithmetic runs outside the stop lock; OFF can revoke
        immediately. A rejected candidate does not authorize the other one.
        """
        try:
            with self.ledger.lock:
                self._cache = self._record = self._issued_record = self._cache_seals = None
                self._bindings()
                r, b = self.ledger.runner, self.bounds
                r._check(self.ledger.clock())
                if (r.phase != 'ready' or self.ledger._pending is not None
                        or self.ledger._busy is not None
                        or not 0 <= self.ledger.clock() - r.last_fix_at <= .5):
                    raise ValueError('Need a fresh stopped position before geometry preparation')
                context, base = self._context(), _chain_snapshot(self.ledger.chain)
                reference = scene.reference_fix
                position = reference.mesh_projection.package_xyz
                if position != (r.pose.x, r.pose.y, r.pose.z):
                    raise ValueError('Geometry reference differs from stopped pose')
                polygon = r.route.segments[r.index].polygon
                component = int(self.ground.components[polygon])
                heading, serial, chain = r.pose.heading, r.serial, copy(self.ledger.chain)
            trials, seals = {}, {}
            for kind in ('forward', 'pivot'):
                try:
                    trials[kind] = self._trial(kind, position, heading, component, chain, b)
                    value = trials[kind]
                    if not isinstance(value, str):
                        seals[kind] = self._seal(value[3], value[4], value[5], value[7])
                except ValueError as error:
                    trials[kind] = 'Geometry query refused: ' + str(error)
                with self.ledger.lock:
                    self._bindings()
                    r._check(self.ledger.clock())
                    if (r.phase != 'ready' or self._context() != context or r.serial != serial
                            or self.ledger._pending is not None or self.ledger._busy is not None
                            or _chain_snapshot(self.ledger.chain) != base
                            or not 0 <= self.ledger.clock() - r.last_fix_at <= .5):
                        raise ValueError('Stopped geometry context changed or expired')
            with self.ledger.lock:
                self._bindings()
                r._check(self.ledger.clock())
                if (r.phase != 'ready' or self._context() != context or r.serial != serial
                        or _chain_snapshot(self.ledger.chain) != base
                        or not 0 <= self.ledger.clock() - r.last_fix_at <= .5):
                    raise ValueError('Stopped geometry context changed or expired')
                self._cache = (reference, context, base, serial, MappingProxyType(trials))
                self._cache_seals = (self._cache, MappingProxyType(seals))
        except BaseException:
            self.ledger.cancel('Route geometry precomputation failed')
            raise

    def __call__(self, proposal, scene):
        with self.ledger.lock:
            self._record = None
            cache, self._cache = self._cache, None  # Consume once even on refusal.
            try:
                self._bindings()
                r, b = self.ledger.runner, self.bounds
                if (cache is None or proposal is not r.pending or r.phase != 'proposed'
                        or self._cache_seals is None or cache is not self._cache_seals[0]
                        or scene.reference_fix is not cache[0] or self._context() != cache[1]
                        or _chain_snapshot(self.ledger.chain) != cache[2]
                        or r.serial != cache[3] + 1):
                    raise ValueError('No exact precomputed geometry for this proposal/reference')
                seconds = r.suggest_hold(proposal, minimum_seconds=b.minimum_requested_hold,
                                         maximum_seconds=b.maximum_requested_hold)
                if proposal.forward and proposal.turn is None:
                    kind, key = 'forward', 103
                elif not proposal.forward and proposal.turn in ('left', 'right'):
                    kind, key = 'pivot', {'left': 105, 'right': 106}[proposal.turn]
                else:
                    raise ValueError('Proposal has no exclusive supported movement')
                selected = cache[4][kind]
                if isinstance(selected, str):
                    raise ValueError(selected)
                footprint, sources, fork, trial, static, bsp, fork_state, native = selected
                seal = self._seal(trial, static, bsp, native)
                if seal != self._cache_seals[1].get(kind):
                    raise ValueError('Cached native geometry evidence changed')

                def evaluate(preparation, base):
                    if (_chain_snapshot(base)[1:] != cache[2][1:]
                            or _chain_snapshot(fork) != fork_state
                            or preparation.footprint != footprint or preparation.sources != sources):
                        raise ValueError('Precomputed floor or exact cell changed')
                    return fork, trial

                ticket = self.ledger.stage(proposal, reference_fix=scene.reference_fix,
                    footprint=footprint, sources=sources, requested_seconds=seconds,
                    maximum_actual_hold=b.maximum_actual_hold, movement_key=key,
                    motion_bounds_record_id=b.record_id, check_geometry=evaluate)
                self._record = RouteGeometryRecord(ticket, trial, static, bsp,
                    self.precision_policy, self.expected_zone_line, self.region_policy, native)
                self._issued_record = self._record
                self._record_seal = seal
                self._record_context = self._context()
                return ticket
            except BaseException:
                self.ledger.cancel('Route geometry preparation failed')
                raise
