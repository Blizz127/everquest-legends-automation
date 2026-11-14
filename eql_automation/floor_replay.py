"""Conditional floor-aware geometry trials for offline replay only.

Each trial forks its source chain. The caller commits that fork only after
accepted geometry and completed simulated actuation; rejected/shortened
trials cannot change the previous supporting floor. All terrain heights are
checked for occupancy before selected faces feed the source/baked comparison.
"""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from .ground_sweep import GroundCoverage,GroundFace
from .portal_precision import PrecisionCheck,SourceSupport,retry_precision_gap,source_support
from .source_floor_chain import FloorChainStep


@dataclass(frozen=True)
class FloorTrial:
    candidate: bool
    reason: str
    coverage: GroundCoverage
    floor_step: FloorChainStep | None = None
    source_support: SourceSupport | None = None
    precision_retry: PrecisionCheck | None = None
    excluded_baked_detail_ids: tuple[int, ...] = ()
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_floor_trial(view, chain, original, footprint, detail_ids, *, reference,
                      component,vertical_window,maximum_source_z_difference,allow_overlap=False):
    """Return (proposed chain or None, complete conditional trial evidence)."""
    allowed=('uncovered_ground_area','overlapping_ground_faces') if allow_overlap is True else ('uncovered_ground_area',)
    if not original.candidate and original.reason not in allowed:
        return None,FloorTrial(False,original.reason,original)
    try:
        sources=view.source_faces_for_footprint(footprint)
    except ValueError:
        return None,FloorTrial(False,'source_inventory_unavailable',original)
    # advance() replaces state attributes and never mutates the previous
    # immutable records/patch dictionary shared by this shallow snapshot.
    proposed=copy(chain)
    step=proposed.advance(footprint,sources)
    if not step.candidate:
        return None,FloorTrial(False,step.reason,original,step)
    selected=tuple(s for s in sources if (s.fragment,s.face) in step.selected_ids)
    ground=view.ground
    polygons=tuple(int(ground.polys[i]) for i in detail_ids)
    faces=tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in ground.triangles[i]),
                          int(ground.areas[poly]),int(ground.components[poly]))
                for i,poly in zip(detail_ids,polygons))
    # Ground coverage already ignores surfaces wholly outside this explicit
    # height window. Do not compare those overhead/below-floor surfaces to the
    # selected supporting floor. Use the WHOLE triangle's Z range, not nearest
    # height or just its center: crossing triangles remain in every check.
    # Precision correction changes only XY, so this exclusion also remains
    # valid for the corrected triangles. Source occupancy above checked all
    # heights and is independent of this baked support comparison.
    low,high=reference[2]-vertical_window,reference[2]+vertical_window
    excluded=tuple(i for i,face in zip(detail_ids,faces)
                   if max(p[2] for p in face.vertices)<low or min(p[2] for p in face.vertices)>high)
    kept=tuple((face,poly) for i,face,poly in zip(detail_ids,faces,polygons) if i not in excluded)
    faces=tuple(face for face,_ in kept)
    polygons=tuple(poly for _,poly in kept)
    coverage=original;precision=None
    if original.candidate:
        support=source_support(footprint,selected,faces,maximum_z_difference=maximum_source_z_difference)
    else:
        present=set(polygons)
        possible=set().union(*(view.by_polygon.get(poly,set()) for poly in present))
        seams=tuple(view.seams[i] for i in sorted(possible)
                    if view.seams[i].source in present and view.seams[i].target in present)
        if not 1<=len(seams)<=8:
            precision=PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
        else:
            precision=retry_precision_gap(original,footprint,faces,polygons,seams,selected,
                reference=reference,component=component,vertical_window=vertical_window,
                maximum_source_z_difference=maximum_source_z_difference,allow_overlap=allow_overlap)
        if not precision.candidate:
            return None,FloorTrial(False,precision.reason,original,step,precision.source_support,precision,excluded)
        coverage=precision.coverage;support=precision.source_support
    if support is None or not support.candidate:
        return None,FloorTrial(False,'source_support_missing' if support is None else support.reason,
                               coverage,step,support,precision,excluded)
    return proposed,FloorTrial(True,'conditional_source_and_baked_footprint_only',coverage,step,support,precision,excluded)
