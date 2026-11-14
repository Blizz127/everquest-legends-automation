"""Bind a mixed source itinerary to an actual current-start planning session.

The result deliberately has no FixedRoute: source steps cannot be represented
as baked reciprocal portals. Execution and height continuation need their own
source-backed consumer; existing baked route drivers cannot consume this type.
"""
from dataclasses import dataclass, field
import time

from .current_route_start import CurrentStartPlanner, CurrentStartPlan
from .ground_binding import finite
from .source_itinerary import SourceItineraryGuide, SourceItineraryPlan, plan_source_itinerary


@dataclass(frozen=True)
class CurrentSourceItinerary:
    initial: CurrentStartPlan
    itinerary: SourceItineraryPlan
    requires_fresh_start_pair: bool = field(default=True, init=False)
    source_execution_wired: bool = field(default=False, init=False)
    input_authorized: bool = field(default=False, init=False)
    real_client_accepted: bool = field(default=False, init=False)


def plan_current_source_itinerary(planner, reader, first, second, *, guide,
                                  maximum_seconds=240., clock=time.monotonic,
                                  **start_options):
    if (type(planner) is not CurrentStartPlanner or planner.zone != 'crushbone'
            or planner.zone_id != 58 or planner.region_policy is None
            or type(guide) is not SourceItineraryGuide
            or not finite(maximum_seconds) or not 0 < maximum_seconds <= 300
            or not callable(clock) or 'length' in start_options):
        raise ValueError('Current native Crushbone source itinerary context required')
    owner = start_options.get('owner_binding')
    binding = start_options.get('binding_reader')
    if not callable(binding):
        raise ValueError('Current owner binding required')
    began = last = clock()
    identity = (reader.tail.identity, reader.tail.epoch, reader.zone_generation,
                reader.zone_id, reader.zone_display_name)
    policy = planner.region_policy

    def check():
        nonlocal last
        actual = binding()
        planner._check_views()
        now = clock()
        if (actual != owner or not finite(began) or not finite(now)
                or not began <= last <= now <= began+maximum_seconds
                or planner.region_policy is not policy
                or reader.latest is not second or reader.log_line_seq != second.log_line_seq
                or reader.tail.partial
                or identity != (reader.tail.identity, reader.tail.epoch, reader.zone_generation,
                                reader.zone_id, reader.zone_display_name)):
            raise ValueError('Current source itinerary owner/log context changed or expired')
        last = now

    check()
    initial = planner.plan(reader, first, second, length=.75, clock=clock,
        maximum_seconds=min(30., maximum_seconds), **start_options)
    check()
    if (guide.radius != initial.planning_bounds.body_radius
            or guide.body_height != initial.planning_bounds.body_height):
        raise ValueError('Source itinerary and current body hypotheses differ')
    # This exact printed position, including its selected source floor, is the
    # only start. Historical guide starts are merely checked rejoin candidates.
    start = (second.raw_coordinates[1], second.raw_coordinates[0])
    plan = plan_source_itinerary(initial.floor_chain, start, guide,
        planner.source, planner.static, planner.bsp, policy, check_context=check,
        max_seconds=max(.001, began+maximum_seconds-last), clock=clock)
    check()
    return CurrentSourceItinerary(initial, plan)
