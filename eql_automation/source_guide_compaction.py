"""Compact nearly straight proposal hints without accepting their geometry.

Step hints, reversals and turns beyond the explicit rounding tolerance remain
explicit. Tiny XY changes are proposals, never equivalence proofs. Every new
swept footprint must be rebuilt by the source itinerary checker from the
current floor. Runtime movement pulse and observation limits do not change.
"""
from dataclasses import replace
from hashlib import sha256
import math

from .ground_binding import finite
from .native_region_policy import encoded
from .source_itinerary import SourceItineraryGuide,SourceWalkHint,SourceStepHint
from .source_stair_hint import SourceStairHint
from .source_contact_hint import SourceContactHint


def compact_source_guide(guide,*,maximum_length=8.,tolerance=1e-8):
    if (type(guide) is not SourceItineraryGuide or not finite(maximum_length)
            or not .25<=maximum_length<=16 or not finite(tolerance) or not 0<=tolerance<=1e-7):
        raise ValueError('Bounded source-guide compaction required')
    guide.validate();original=guide.record();result=[];points=[]
    original_start=guide.operations[0].start
    position=original_start
    def flush():
        if points:
            result.append(SourceWalkHint(points[0],points[-1]));points.clear()
    def append_walk(a,b):
        if a==b:return
        if points:
            dx,dy=b[0]-points[0][0],b[1]-points[0][1]
            length=math.hypot(dx,dy)
            # Test every retained intermediate point against the prospective
            # segment; local near-collinearity must not accumulate a shortcut.
            straight=(0<length<=maximum_length and
                all(abs(dx*(p[1]-points[0][1])-dy*(p[0]-points[0][0]))<=tolerance*length
                    and 0<=(p[0]-points[0][0])*dx+(p[1]-points[0][1])*dy<=length*length
                    for p in points[1:]) and
                (a[0]-points[-2][0])*(b[0]-a[0])+(a[1]-points[-2][1])*(b[1]-a[1])>=0)
            if straight:points.append(b);return
            flush()
        points.extend((a,b))
    for operation in guide.operations:
        if operation.start!=position:raise ValueError('Exactly contiguous proposal hints required')
        if type(operation) in (SourceStepHint,SourceStairHint,SourceContactHint):
            flush();result.append(operation)
        else:
            a=operation.start;b=operation.end
            count=max(1,math.ceil(math.dist(a,b)/maximum_length))
            prior=a
            for index in range(count):
                end=b if index==count-1 else tuple(a[k]+(b[k]-a[k])*(index+1)/count for k in (0,1))
                append_walk(prior,end);prior=end
        position=operation.end
    flush()
    if not result:result.append(SourceWalkHint(original_start,position))
    if result[0].start!=original_start or result[-1].end!=position:
        raise ValueError('Compaction changed itinerary endpoints')
    provenance=sha256(encoded(dict(source_guide=original,maximum_length=maximum_length,
        tolerance=tolerance,kind='straight_proposal_compaction'))).hexdigest()
    compacted=replace(guide,provenance_sha256=provenance,operations=tuple(result))
    compacted.validate();return compacted
