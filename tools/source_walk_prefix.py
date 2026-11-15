"""Reproduce a saved offline walking prefix, including checked detour caps."""
from hashlib import sha256
import math

from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import SourceWalkHint, _guide_snapshot
from eql_automation.source_probe_geometry import check_source_footprint


def replay_walk_prefix(prefix, guide, evidence, planner, *, check_context):
    """Recheck every recorded cell from the supplied original seed/prefix.

    Proofs and path coordinates are expectations, never trusted floor state.
    Detour endpoint caps are retained as zero-length walking operations so
    the same proof ancestry is reproduced without introducing another seed.
    """
    guide.validate()
    completed = evidence.get('completed_operations')
    rows = evidence.get('checked_cells', ())
    if (evidence.get('kind') != 'offline_checked_walking_repairs'
            or evidence.get('source_guide_sha256') != sha256(encoded(guide.record())).hexdigest()
            or type(completed) is not int or not 0 < completed < len(guide.operations)
            or type(rows) not in (list, tuple) or not 0 < len(rows) <= 10000
            or any(type(op) is not SourceWalkHint for op in guide.operations)
            or guide.zone != planner.region_policy.zone
            or guide.wld_sha256 != prefix.inventory_sha256
            or guide.wld_sha256 != planner.source.wld_sha256
            or guide.static_inventory_sha256 != planner.static.inventory_sha256
            or guide.body_height != prefix.body_height):
        raise ValueError('Matching incomplete ordinary-walk evidence required')
    snapshot = _chain_snapshot(prefix); guide_state = _guide_snapshot(guide)
    def evidence_state():
        return (evidence.get('kind'), evidence.get('source_guide_sha256'),
            evidence.get('completed_operations'), tuple(evidence['next_position']),
            evidence['reached_proof_sha256'], tuple((tuple(r['start']),tuple(r['end']),
                r['previous_sha256'],r['proof_sha256']) for r in evidence['checked_cells']))
    saved_evidence = evidence_state()
    position = guide.operations[0].start; branch = prefix.fork(); operations = []

    def check():
        check_context()
        if (_chain_snapshot(prefix) != snapshot or _guide_snapshot(guide) != guide_state
                or evidence_state() != saved_evidence):
            raise ValueError('Retained prefix or replay evidence changed')

    for row in rows:
        check()
        a, b = tuple(row['start']), tuple(row['end'])
        if (any(len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v)
                                  for v in p) for p in (a,b))
                or a != position or math.dist(a,b) > 80
                or row['previous_sha256'] != branch.previous.proof_sha256):
            raise ValueError('Saved walking prefix lost exact continuity')
        result = check_source_footprint(branch, swept_square(a,b,guide.radius),
            terrain=planner.source, static=planner.static, bsp=planner.bsp,
            region_policy=planner.region_policy)
        if result.terrain.proof_sha256 != row['proof_sha256']:
            raise ValueError('Rebuilt prefix differs from its recorded floor proof')
        branch = result.branch; position = b; operations.append(SourceWalkHint(a,b))
    check()
    if (position != tuple(evidence['next_position'])
            or position != guide.operations[completed-1].end
            or branch.previous.proof_sha256 != evidence['reached_proof_sha256']):
        raise ValueError('Rebuilt prefix differs from its recorded stopping point')
    return branch, position, tuple(operations)
