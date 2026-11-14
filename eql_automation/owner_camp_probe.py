"""Explicit dependencies for the optional reached-camp probe handoff.

No default producer or movement policy is supplied. A launcher must provide
current bounds/evidence and admission before this path can be enabled.
"""
from dataclasses import asdict,dataclass

from .ground_binding import finite
from .motion_calibration import PROBES,Probe
from .native_region_policy import encoded
from .route_geometry import RouteMotionBounds
from .source_itinerary import SourceItineraryGuide,_guide_snapshot


@dataclass(frozen=True)
class CampProbePlan:
    bounds: RouteMotionBounds
    bounds_basis: bytes
    policy_factory: object
    probes: tuple=PROBES
    maximum_seconds: float=120.
    route_guide: SourceItineraryGuide | None=None

    def state(self):
        if (type(self.bounds) is not RouteMotionBounds or type(self.bounds_basis) is not bytes
                or not callable(self.policy_factory) or type(self.probes) is not tuple
                or not 1<=len(self.probes)<=7 or any(type(p) is not Probe for p in self.probes)
                or not finite(self.maximum_seconds) or not 0<self.maximum_seconds<=300
                or self.route_guide is not None and type(self.route_guide) is not SourceItineraryGuide):
            raise ValueError('Explicit camp probe bounds, policy and finite plan required')
        return (id(self),id(self.bounds),encoded(asdict(self.bounds)),self.bounds_basis,
                id(self.policy_factory),encoded([asdict(p) for p in self.probes]),self.maximum_seconds,
                None if self.route_guide is None else (id(self.route_guide),_guide_snapshot(self.route_guide)))
