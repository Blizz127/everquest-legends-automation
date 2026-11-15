"""Parse a pinned walking-section partition as proposals, never input authority."""
from dataclasses import dataclass
from hashlib import sha256
import math

from .ground_binding import finite
from .native_region_policy import encoded
from .source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot


def _same_walking_guide(guide,state):
    """Compare the retained values without rebuilding thousands of nested tuples.

    This runs at every parent-budget boundary, including before DOWN. Preserve
    the original snapshot's field order and extra-field detection. Unusual
    records use the original comparison instead of a weaker fast path.
    """
    if ((guide.zone,guide.wld_sha256,guide.static_inventory_sha256,
            guide.provenance_sha256,guide.radius,guide.body_height,guide.goal)!=state[:7]
            or len(guide.operations)!=len(state[7])):
        return False
    return _same_operations(guide.operations,state[7])


def _same_operations(operations,state):
    if len(operations)!=len(state):return False
    for op,(kind,fields) in zip(operations,state):
        if type(op) is not kind:return False
        if (kind is not SourceWalkHint or len(fields)!=2
                or fields[0][0]!='start' or fields[1][0]!='end'):
            if tuple(vars(op).items())!=fields:return False
            continue
        values=vars(op)
        if (len(values)!=2 or next(iter(values))!='start'
                or values.get('start')!=fields[0][1] or values.get('end')!=fields[1][1]):
            return False
    return True


class BoundWalkingSection:
    """Current input depends on this section; future proposals wait for adoption.

    Full manifest validation is still required at every section handoff. Tuple
    and snapshot identities pin partition structure between those boundaries;
    current operations in both the original and parsed guide are checked afresh.
    """
    def __init__(self,sections,index):
        if type(sections) is not WalkingSections or type(index) is not int:
            raise ValueError('Exact walking partition and section index required')
        sections.check()
        if not 0<=index<len(sections.guides):raise ValueError('Invalid active section')
        self.sections=sections;self.index=index
        self.original=sections.original;self.operations=self.original.operations
        self.guides=sections.guides;self.ranges=sections.ranges;self.state=sections._state
        self.operation_tuples=tuple(g.operations for g in self.guides)
        self.guide=self.guides[index];self.active_operations=self.guide.operations
        self.first,self.last=self.ranges[index]

    def check(self,index):
        s=self.sections
        if (index!=self.index or s.original is not self.original
                or self.original.operations is not self.operations or s.guides is not self.guides
                or s.ranges is not self.ranges or s._state is not self.state
                or s.record_sha256!=self.state[3]
                or any(g.operations is not ops or
                    (g.zone,g.wld_sha256,g.static_inventory_sha256,g.provenance_sha256,
                     g.radius,g.body_height,g.goal)!=state[:7]
                    for g,ops,state in zip(self.guides,self.operation_tuples,self.state[1]))
                or self.guide.operations is not self.active_operations
                or (self.original.zone,self.original.wld_sha256,self.original.static_inventory_sha256,
                    self.original.provenance_sha256,self.original.radius,self.original.body_height,
                    self.original.goal)!=self.state[0][:7]
                or not _same_walking_guide(self.guide,self.state[1][index])
                or not _same_operations(self.operations[self.first:self.last+1],
                    self.state[0][7][self.first:self.last+1])):
            raise ValueError('Active walking section or partition structure changed')


@dataclass(frozen=True)
class WalkingSections:
    original: SourceItineraryGuide
    guides: tuple
    ranges: tuple
    record_sha256: str
    _state: tuple

    def check(self):
        if (not _same_walking_guide(self.original,self._state[0])
                or len(self.guides)!=len(self._state[1])
                or not all(_same_walking_guide(g,s) for g,s in zip(self.guides,self._state[1]))
                or (self.ranges,self.record_sha256)!=self._state[2:]):
            raise ValueError('Pinned walking-section partition changed')

    def section_for_entry(self, operation):
        """Choose only after the actual current-start planner checked its rejoin."""
        self.check()
        if type(operation) is not int or not 0 <= operation < len(self.original.operations):
            raise ValueError('Current-start guide operation index required')
        return next(i for i,(first,last) in enumerate(self.ranges) if first <= operation <= last)


def parse_walking_sections(original, record):
    if type(original) is not SourceItineraryGuide or type(record) is not dict:
        raise ValueError('Exact original guide and section proposal record required')
    original.validate()
    root_pin = sha256(encoded(original.record())).hexdigest()
    rows = record.get('sections')
    maximum = record.get('maximum_section_length')
    if (record.get('format') != 'eql-copied-source-walk-sections-v1'
            or record.get('original_guide_sha256') != root_pin
            or type(rows) is not list or not 1 <= len(rows) <= 16
            or not finite(maximum) or not 0 < maximum <= 2000.
            or any(type(op) is not SourceWalkHint for op in original.operations)):
        raise ValueError('Bounded ordinary partition for the exact original guide required')
    guides = []; ranges = []; cursor = 0
    for i,row in enumerate(rows):
        if type(row) is not dict:raise ValueError('Exact section proposal required')
        guide = SourceItineraryGuide.from_record(row['guide'])
        first,last = row.get('first_operation'),row.get('last_operation')
        final = i == len(rows)-1
        if (type(first) is not int or type(last) is not int or first != cursor
                or not first <= last < len(original.operations) or row.get('final') is not final
                or row.get('original_guide_sha256') != root_pin
                or guide.operations != original.operations[first:last+1]
                or guide.goal != guide.operations[-1].end
                or (guide.zone,guide.wld_sha256,guide.static_inventory_sha256,guide.radius,guide.body_height)
                    != (original.zone,original.wld_sha256,original.static_inventory_sha256,
                        original.radius,original.body_height)
                or row.get('guide_sha256') != sha256(encoded(guide.record())).hexdigest()):
            raise ValueError('Walking sections must retain all ordered operations and source/body pins')
        distance = sum(math.dist(op.start,op.end) for op in guide.operations)
        if (not finite(row.get('distance')) or not 0 < distance <= maximum
                or not math.isclose(distance,row['distance'],rel_tol=1e-12,abs_tol=1e-9)):
            raise ValueError('Section length differs from its exact operation range')
        reserve = row.get('measurement_reserve')
        reserve_pin = None if reserve is None else sha256(encoded(reserve)).hexdigest()
        if (row.get('reserve_sha256') != reserve_pin or (reserve is None) != final
                or row.get('current_character_observation') is not False
                or row.get('input_authorized') is not False):
            raise ValueError('Section reserves are offline proposals, not live observations')
        evidence = dict(kind='copied_source_walking_section',original_guide_sha256=root_pin,
            first_operation=first,last_operation=last,distance=row['distance'],final=final,
            reserve_sha256=reserve_pin,current_character_observation=False,input_authorized=False)
        if guide.provenance_sha256 != sha256(encoded(evidence)).hexdigest():
            raise ValueError('Section provenance differs from its retained partition')
        guides.append(guide); ranges.append((first,last)); cursor = last+1
    if cursor != len(original.operations) or guides[-1].goal != original.goal:
        raise ValueError('Section partition does not reach the complete original destination')
    guides,ranges = tuple(guides),tuple(ranges)
    pin = sha256(encoded(record)).hexdigest()
    state = _guide_snapshot(original),tuple(_guide_snapshot(g) for g in guides),ranges,pin
    result = WalkingSections(original,guides,ranges,pin,state)
    result.check()
    return result
