"""Explicit dependencies for the optional reached-camp probe handoff.

No default producer or movement policy is supplied. A launcher must provide
current bounds/evidence and admission before this path can be enabled.
"""
from dataclasses import dataclass

from .flat_record import flat_record_state
from .ground_binding import finite
from .motion_calibration import PROBES,Probe
from .route_geometry import RouteMotionBounds
from .source_itinerary import SourceItineraryGuide,_guide_snapshot
from .source_section_manifest import WalkingSections


@dataclass(frozen=True)
class CampProbePlan:
    bounds: RouteMotionBounds
    bounds_basis: bytes
    policy_factory: object
    probes: tuple=PROBES
    maximum_seconds: float=120.
    route_guide: SourceItineraryGuide | None=None
    route_plan_factory: object=None
    destination_id: str | None=None
    destination_evidence: bytes | None=None
    route_sections: WalkingSections | None=None

    def state(self):
        if self.route_sections is not None:
            if (type(self.route_sections) is not WalkingSections
                    or self.route_sections.original is not self.route_guide
                    or self.route_plan_factory is None or self.destination_id is None):
                raise ValueError('Camp partition requires its exact full destination guide')
            self.route_sections.check()
        if (type(self.bounds) is not RouteMotionBounds or type(self.bounds_basis) is not bytes
                or not callable(self.policy_factory) or type(self.probes) is not tuple
                or not 1<=len(self.probes)<=7 or any(type(p) is not Probe for p in self.probes)
                or not finite(self.maximum_seconds) or not 0<self.maximum_seconds<=1500
                or self.route_guide is not None and type(self.route_guide) is not SourceItineraryGuide
                or self.route_plan_factory is not None and (not callable(self.route_plan_factory)
                    or self.route_guide is None)
                or (self.destination_id is None)!=(self.destination_evidence is None)
                or self.destination_id is not None and (type(self.destination_id) is not str
                    or not self.destination_id or type(self.destination_evidence) is not bytes
                    or not 0<len(self.destination_evidence)<=16384 or self.route_plan_factory is None)):
            raise ValueError('Explicit camp probe bounds, policy and finite plan required')
        return self.owner_state(),(None if self.route_guide is None else _guide_snapshot(self.route_guide))

    def owner_state(self):
        """Field/identity pin; callers must separately check guide contents.

        A section child uses BoundWalkingSection for its active operations and
        validates the full partition at handoffs. This avoids rebuilding the
        complete destination snapshot inside every parent-budget callback.
        """
        return (id(self),id(self.bounds),flat_record_state(self.bounds),self.bounds_basis,
                id(self.policy_factory),tuple(flat_record_state(p) for p in self.probes),self.maximum_seconds,
                id(self.route_guide),
                id(self.route_plan_factory),self.destination_id,self.destination_evidence,
                None if self.route_sections is None else
                    (id(self.route_sections),self.route_sections.record_sha256))
