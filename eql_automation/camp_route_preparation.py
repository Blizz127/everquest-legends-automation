"""Prepare an onward source route on the actual retained camp floor.

No baked support is selected and no old travel observer is restarted. Planning
may outlive its input pair; a newly collected matching pair must follow it.
This preparation owns no sender and does not authorize route execution.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json
import time

from .camp_probe_floor import CAMP_FLOOR_TYPES
from .camp_probe_preparation import _check_height_record, _height_state
from .camp_stopped_height import CampStoppedHeight, measure_camp_stopped_height
from .flat_record import flat_record_state
from .ground_binding import finite
from .motion_collection import immutable_binding
from .native_region_policy import encoded
from .owner_zone_tracker import ZoneReaderLease
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_itinerary import SourceItineraryGuide, _guide_snapshot, plan_source_itinerary
from .source_section_manifest import WalkingSections


@dataclass(frozen=True)
class CampRouteStart:
    height: CampStoppedHeight
    preparation_sha256: str
    itinerary_sha256: str
    observed_at: float
    expires_at: float
    input_authorized: bool = field(default=False, init=False)
    real_client_accepted: bool = field(default=False, init=False)


class CampRoutePreparation:
    def __init__(self, checkpoint, height, lease, *, guide, bounds, owner_binding,
                 binding_reader, local_wall_clock, clock=time.monotonic, sections=None):
        if (type(checkpoint) not in CAMP_FLOOR_TYPES or type(height) is not CampStoppedHeight
                or type(lease) is not ZoneReaderLease or type(guide) is not SourceItineraryGuide
                or type(bounds) is not RouteMotionBounds or not immutable_binding(owner_binding)
                or not all(callable(f) for f in (binding_reader, local_wall_clock, clock))):
            raise ValueError('Retained camp floor, fresh height, guide and exact reader scope required')
        guide.validate()
        if sections is not None:
            if type(sections) is not WalkingSections or sections.original is not guide:
                raise ValueError('Camp sections must retain the exact full guide')
            sections.check()
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id, maximum_step_seconds=.2)
        if (guide.radius != bounds.body_radius or guide.body_height != bounds.body_height
                or guide.wld_sha256 != checkpoint._terrain.wld_sha256
                or guide.static_inventory_sha256 != checkpoint._static.inventory_sha256):
            raise ValueError('Onward guide differs from retained source or body dimensions')
        self.checkpoint, self.height, self.lease, self.reader = checkpoint, height, lease, lease.reader
        self.guide, self.bounds = guide, bounds
        self.sections=self._sections=sections
        self.section_index=self.full_itinerary=None
        self._selection_state=None
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self.clock, self.wall = clock, local_wall_clock
        self._objects = (checkpoint, height, lease, lease.reader, guide, bounds, owner_binding,
                         binding_reader, clock, local_wall_clock)
        self._height = _height_state(height)
        self._height_raw = (flat_record_state(height.first), flat_record_state(height.second))
        self._guide = _guide_snapshot(guide)
        self._bounds = flat_record_state(bounds)
        self.phase, self.reason, self.last_at = 'new', '', None
        self.itinerary = self.payload = self.sha256 = self.start = None
        self._itinerary_state = self._record_state = self._start_state = None
        self._prefix = self._prefix_state = None
        self._consume_pending = False
        _check_height_record(height, checkpoint, owner_binding)
        self.check(fresh=height)

    def cancel(self, reason):
        self.phase, self.reason = 'stopped', str(reason)
        self._prefix = self._prefix_state = self.start = self._start_state = None

    def check(self, *, fresh=None):
        try:
            if self.phase == 'stopped':
                raise ValueError(self.reason)
            binding = self.binding_reader()
            self.lease.check(); self.checkpoint.check()
            now = self.clock()
            self.checkpoint._assert_intact()
            if self.sections is not self._sections:
                raise ValueError('Camp walking partition changed')
            if self.sections is not None:self.sections.check()
            if (self.phase == 'stopped' or binding != self.owner_binding
                    or any(a is not b for a, b in zip(self._objects,
                        (self.checkpoint, self.height, self.lease, self.reader, self.guide, self.bounds,
                         self.owner_binding, self.binding_reader, self.clock, self.wall)))
                    or self.lease.reader is not self.reader or self.reader is not self.checkpoint._reader
                    or not self.lease.active or self.lease._tracker.lease is not self.lease
                    or _height_state(self.height) != self._height
                    or (flat_record_state(self.height.first), flat_record_state(self.height.second)) != self._height_raw
                    or _guide_snapshot(self.guide) != self._guide or flat_record_state(self.bounds) != self._bounds
                    or self.reader.tail.partial or not finite(now)
                    or self.last_at is not None and now < self.last_at):
                raise ValueError('Camp route planning scope changed')
            if self._prefix is not None and _chain_snapshot(self._prefix) != self._prefix_state:
                raise ValueError('Retained camp route prefix changed')
            if self._itinerary_state is not None:
                plan, payload, digest = self._itinerary_state
                if self.itinerary is not plan or plan.payload is not payload or plan.sha256 != digest:
                    raise ValueError('Prepared camp itinerary changed')
                # Canonical bytes were validated when this plan was retained.
                # Exact immutable payload identity and digest are pinned above.
            if self._record_state is not None and (self.payload, self.sha256) != self._record_state:
                raise ValueError('Camp route evidence changed')
            if self._selection_state is not None:
                index,full,payload,digest=self._selection_state
                if (self.section_index!=index or self.full_itinerary is not full
                        or full.payload is not payload or full.sha256!=digest):
                    raise ValueError('Camp section selection changed')
            if fresh is not None:
                _check_height_record(fresh, self.checkpoint, self.owner_binding)
                if (self.reader.latest is not fresh.second or self.reader.log_line_seq != fresh.second.log_line_seq
                        or not fresh.observed_at <= now <= fresh.expires_at):
                    raise ValueError('Camp route needs a fresh latest stopped pair')
            self.last_at = now
            return now
        except Exception as error:
            self.cancel(error)
            raise ValueError(self.reason) from error

    def prepare(self, *, maximum_seconds=120.):
        if self.phase != 'new':
            raise ValueError('Camp route can only be prepared once')
        try:
            self.check(fresh=self.height)
            self.phase = 'planning'
            began=self.clock()
            self._prefix = self.checkpoint.fork()
            self._prefix_state = _chain_snapshot(self._prefix)
            c = self.checkpoint
            plan = plan_source_itinerary(self._prefix, self.height.package_xyz[:2], self.guide,
                c._terrain, c._static, c._bsp, c._policy,
                check_context=self.check, max_seconds=maximum_seconds, clock=self.clock)
            self.check()
            if self.sections is not None:
                full=plan;entry=full.record()['guide_entry']
                index=self.sections.section_for_entry(entry)
                remaining=began+maximum_seconds-self.clock()
                if remaining<=0:raise ValueError('Camp section planning deadline expired')
                plan=plan_source_itinerary(self._prefix,self.height.package_xyz[:2],
                    self.sections.guides[index],c._terrain,c._static,c._bsp,c._policy,
                    check_context=self.check,max_seconds=remaining,clock=self.clock)
                self.check()
                if plan.record()['guide_entry']+self.sections.ranges[index][0]!=entry:
                    raise ValueError('Camp section rejoin differs from the verified full-guide entry')
                self.section_index,self.full_itinerary=index,full
                self._selection_state=(index,full,full.payload,full.sha256)
            self.itinerary = plan
            self._itinerary_state = (plan, plan.payload, plan.sha256)
            self.payload = encoded(dict(format='eql-camp-route-preparation-v1',
                checkpoint_sha256=c.sha256, planning_height_sha256=self.height.sha256,
                planning_position=self.height.package_xyz,
                planning_observed_at=self.height.observed_at, planning_expires_at=self.height.expires_at,
                guide_sha256=sha256(encoded(self.guide.record())).hexdigest(),
                itinerary=plan.record(), itinerary_sha256=plan.sha256,
                section_index=self.section_index,
                full_itinerary_sha256=None if self.full_itinerary is None else self.full_itinerary.sha256,
                section_manifest_sha256=None if self.sections is None else self.sections.record_sha256,
                requires_new_matching_pair=True, old_calibration_renewed=False,
                source_execution_wired=False, input_authorized=False, real_client_accepted=False))
            self.sha256 = sha256(self.payload).hexdigest()
            self._record_state = (self.payload, self.sha256)
            self.check(); self.phase = 'prepared'
            return self.snapshot()
        except Exception as error:
            self.cancel(error)
            raise

    def observe_start(self, first, second, *, minimum_log_seq, released_at):
        if self.phase != 'prepared':
            raise ValueError('Prepared camp route required')
        try:
            self.check()
            if minimum_log_seq < self.height.second.log_line_seq:
                raise ValueError('Camp route start predates its planning pair')
            height = measure_camp_stopped_height(self.checkpoint, self.reader, first, second,
                minimum_log_seq=minimum_log_seq, released_at=released_at,
                owner_binding=self.owner_binding, binding_reader=self.binding_reader,
                clock=self.clock, local_wall_clock=self.wall)
            if (height.package_xyz != self.height.package_xyz
                    or height.raw_z_minus_source_z != self.height.raw_z_minus_source_z):
                raise ValueError('Camp route start moved after planning; replan required')
            self.check(fresh=height)
            self.start = CampRouteStart(height, self.sha256, self.itinerary.sha256,
                                        height.observed_at, height.expires_at)
            self._start_state = (self.start, _height_state(height),
                                (flat_record_state(height.first), flat_record_state(height.second)))
            self.phase = 'ready'
            self.check_start(self.start)
            return self.start
        except Exception as error:
            self.cancel(error)
            raise

    def check_start(self, start):
        if (self.phase != 'ready' or start is not self.start or self._start_state is None
                or start.preparation_sha256 != self.sha256 or start.itinerary_sha256 != self.itinerary.sha256
                or start.observed_at != start.height.observed_at or start.expires_at != start.height.expires_at
                or (start, _height_state(start.height),
                    (flat_record_state(start.height.first), flat_record_state(start.height.second))) != self._start_state):
            raise ValueError('Exact current onward-route start required')
        self.check(fresh=start.height)
        if self.phase != 'ready' or self.start is not start:
            raise ValueError('Camp route start changed during validation')
        return self.itinerary

    def consume_start(self, start):
        """Transfer this fresh start once; the original lease/deadline still apply.

        The caller holds the original stop lock. Only the reached prefix is
        returned; no future itinerary branch or movement permission is supplied.
        """
        if self._consume_pending:
            raise ValueError('Camp route start transfer already pending')
        self._consume_pending = True
        try:
            self.check_start(start)
            prefix = self._prefix.fork()
            self.check_start(start)
            self.phase = 'observing'
            return prefix
        finally:
            self._consume_pending = False

    def snapshot(self, *, include_evidence=False):
        result = dict(phase=self.phase, reason=self.reason, sha256=self.sha256,
            itinerary_sha256=None if self.itinerary is None else self.itinerary.sha256,
            goal=self.guide.goal,
            section_index=self.section_index,
            section_goal=None if self.sections is None or self.section_index is None
                         else self.sections.guides[self.section_index].goal,
            start=None if self.start is None else dict(height_sha256=self.start.height.sha256,
                observed_at=self.start.observed_at, expires_at=self.start.expires_at),
            input_authorized=False, real_client_accepted=False, source_execution_wired=False)
        if include_evidence:
            result['evidence'] = None if self.payload is None else json.loads(self.payload)
        return result
