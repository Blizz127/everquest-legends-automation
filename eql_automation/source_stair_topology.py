"""Offline staircase support inventory; not a movement or collision permit.

Narrow treads can be real stairs even when a full body cap cannot fit on each
tread. This describes their exact support/riser topology without treating them
as ordinary continuous floor or weakening the existing single-step checks.
"""
from dataclasses import asdict
from fractions import Fraction
import math

from eql_automation.ground_sweep import hull
from eql_automation.portal_precision import SourceFace
from eql_automation.source_detour import swept_square
from eql_automation.source_occupancy import exact_floor_partition
from eql_automation.source_step import digest, expanded, patches, riser_link


def audit_stair_topology(sources, tread_ids, *, start, end, radius,
                        max_rise=2., check_context=lambda: None):
    if (not isinstance(sources, tuple) or not 1 <= len(sources) <= 1024
            or not all(type(s) is SourceFace for s in sources)
            or not isinstance(tread_ids, tuple) or not 2 <= len(tread_ids) <= 32
            or any(not isinstance(ids, tuple) or not 1 <= len(ids) <= 64 for ids in tread_ids)
            or type(radius) not in (int, float) or not math.isfinite(radius) or not .05 <= radius <= 10
            or type(max_rise) not in (int, float) or not math.isfinite(max_rise) or not 0 < max_rise <= 4
            or any(type(p) is not tuple or len(p) != 2 or any(type(v) not in (float, int)
                   or not math.isfinite(v) for v in p) for p in (start, end))
            or not 0 < math.dist(start, end) <= 100):
        raise ValueError('Bounded offline staircase inventory and endpoints required')
    inventory = {(s.fragment, s.face): s for s in sources}
    ids = [key for group in tread_ids for key in group]
    if (len(inventory) != len(sources) or len(set(ids)) != len(ids)
            or any(key not in inventory for key in ids)
            or any(inventory[key].flag != 0 or inventory[key].material_class != 'Diffuse' for key in ids)):
        raise ValueError('Distinct retained dry source treads required')
    boundary = expanded(swept_square(start, end, radius))
    record = dict(kind='offline_stair_support_topology', start=start, end=end,
        radius=radius, max_individual_rise=max_rise,
        geometry_sha256=digest([asdict(s) for s in sources]),
        tread_ids=tread_ids, footprint_exact=[[str(v) for v in p] for p in boundary],
        topology_candidate=False, treads=[], risers=[],
        full_body_clearance_checked=False, static_objects_checked=False,
        bsp_regions_checked=False, executable_itinerary=False,
        floor_lineage_adopted=False, client_step_capability_verified=False,
        input_authorized=False, real_client_accepted=False)
    def refuse(reason):
        return dict(record, reason=reason)
    supports = []
    for group in tread_ids:
        check_context()
        selected = patches(group, inventory, boundary)
        heights = {z for _, _, _, zs in selected for z in zs}
        if len(selected) != len(group) or len(heights) != 1:
            return refuse('tread_not_one_retained_flat_surface')
        supports.append(selected)
        height = next(iter(heights))
        record['treads'].append(dict(source_ids=group, height_exact=str(height),
            projected_patches_exact=[[[str(v) for v in p] for p in patch]
                                     for _, _, patch, _ in selected]))
    projected = tuple(patch for selected in supports for _, _, patch, _ in selected)
    if not exact_floor_partition(boundary, projected):
        return refuse('treads_do_not_exactly_partition_corridor')
    for point, selected in ((start, supports[0]), (end, supports[-1])):
        cap = expanded(swept_square(point, point, radius))
        if not exact_floor_partition(cap, tuple(hull(p[:2] for p in points)
                                               for _, points, _, _ in selected)):
            return refuse('endpoint_not_wholly_supported_by_end_tread')
    direction = None
    for lower, upper in zip(supports, supports[1:]):
        check_context()
        low = lower[0][3][0]; high = upper[0][3][0]
        sign = 'up' if high > low else 'down'
        if high == low or direction is not None and direction != sign:
            return refuse('nonmonotonic_or_equal_tread_heights')
        direction = sign
        pair = (lower, upper) if sign == 'up' else (upper, lower)
        link = riser_link(*pair, boundary, sources, Fraction(max_rise))
        if link is None:
            return refuse('complete_bounded_source_riser_not_found')
        record['risers'].append(link)
    check_context()
    record.update(topology_candidate=True, reason='exact_stair_support_topology_only',
                  direction=direction, full_projected_support_partition=True,
                  complete_endpoint_support=True)
    return record
