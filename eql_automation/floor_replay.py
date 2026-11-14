"""Conditional floor-aware source geometry trials, without input authority.

Each trial forks its source chain. The caller commits that fork only after
accepted geometry and its matching actuation receipt; rejected/shortened
trials cannot change the previous supporting floor. All terrain heights are
checked for occupancy before selected faces feed the source/baked comparison.
Replay uses synthetic receipts. The route ledger additionally requires a
checked sender receipt; these trials never authorize live movement themselves.
"""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass,replace

from .ground_sweep import GroundCoverage,GroundFace,cross,hull
from .portal_precision import PrecisionCheck,SourceSupport,plane,retry_precision_gap,source_support
from .source_floor_chain import FloorChainStep
from .fixed_route_follower import FixedRoute


@dataclass(frozen=True)
class FloorSeedBinding:
    baseline_plan_sha256: str
    replay_plan_sha256: str
    complete_static_chain_matches_replay_plan: bool
    unchanged_prefix_segments: int
    scope: str = 'initial_floor_seed_only; every replay footprint is checked anew'
    input_authorized: bool = False
    real_client_accepted: bool = False


def bind_floor_replay_seed(baseline, candidate):
    """Bind a known copied-data seed to a plan with exactly the same first leg.

    The caller hash-checks both plan files and the source/profile inventory.
    A changed suffix gets no whole-route claim from the old static scan.
    """
    if (not isinstance(baseline,FixedRoute) or not isinstance(candidate,FixedRoute)
            or not baseline.segments or not candidate.segments
            or baseline.zone!=candidate.zone or baseline.mesh_sha256!=candidate.mesh_sha256
            or baseline.half_width!=candidate.half_width
            or baseline.segments[0]!=candidate.segments[0]):
        raise ValueError('Conditional floor seed requires the identical first leg, zone, mesh and width')
    same=baseline.artifact_sha256==candidate.artifact_sha256
    if same and baseline!=candidate:
        raise ValueError('One pinned plan identity cannot describe two routes')
    prefix=0
    for old,new in zip(baseline.segments,candidate.segments):
        if old!=new:break
        prefix+=1
    return FloorSeedBinding(baseline.artifact_sha256,candidate.artifact_sha256,same,prefix)


@dataclass(frozen=True)
class FloorTrial:
    candidate: bool
    reason: str
    coverage: GroundCoverage
    floor_step: FloorChainStep | None = None
    source_support: SourceSupport | None = None
    precision_retry: PrecisionCheck | None = None
    excluded_baked_detail_ids: tuple[int, ...] = ()
    reference_gap_seam_indices: tuple[int, ...] = ()
    input_authorized: bool = False
    real_client_accepted: bool = False


def reference_gap_seams(faces,seams,reference,vertical_window):
    """Attribute missing XY support to an exact modeled gap, never a Z mismatch."""
    for face in faces:
        triangle=hull(p[:2] for p in face.vertices)
        surface=plane(face.vertices)
        if (len(triangle)==3 and surface is not None
                and all(cross(p,triangle[(i+1)%3],reference[:2])>=-1e-10 for i,p in enumerate(triangle))
                and abs(surface[2](reference[:2])-reference[2])<=vertical_window):
            return ()  # Existing in-window XY support means this is not a gap.
    return tuple(i for i,seam in enumerate(seams)
                 if seam.tile_boundary is not None
                 and seam.tile_boundary.lower_tile_maximum<reference[seam.axis]<seam.tile_boundary.upper_tile_minimum
                 and seam.span[0]<reference[1-seam.axis]<seam.span[1])


def check_floor_trial(view, chain, original, footprint, detail_ids, *, reference,
                      component,vertical_window,maximum_source_z_difference,allow_overlap=False,
                      expected_zone_line=None):
    """Return (proposed chain or None, complete conditional trial evidence)."""
    allowed=('uncovered_ground_area','reference_ground_not_supported')
    if allow_overlap is True:allowed+=('overlapping_ground_faces',)
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
    coverage=original;precision=None;reference_gaps=()
    if original.candidate:
        support=source_support(footprint,selected,faces,maximum_z_difference=maximum_source_z_difference)
    else:
        present=set(polygons)
        possible=set().union(*(view.by_polygon.get(poly,set()) for poly in present))
        seams=tuple(view.seams[i] for i in sorted(possible)
                    if view.seams[i].source in present and view.seams[i].target in present)
        retry_basis=original
        if original.reason=='reference_ground_not_supported':
            reference_gaps=reference_gap_seams(faces,seams,reference,vertical_window)
            if not reference_gaps:
                return None,FloorTrial(False,'reference_not_in_exact_tile_gap',original,step,
                                       excluded_baked_detail_ids=excluded)
            # The same original coverage has a proved XY gap at its reference.
            # Preserve that attribution and require all usual corrected-height,
            # coverage, source, area, component and exact-side checks below.
            retry_basis=replace(original,reason='uncovered_ground_area')
        if not 1<=len(seams)<=8:
            precision=PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
        else:
            precision=retry_precision_gap(retry_basis,footprint,faces,polygons,seams,selected,
                reference=reference,component=component,vertical_window=vertical_window,
                maximum_source_z_difference=maximum_source_z_difference,allow_overlap=allow_overlap,
                expected_zone_line=expected_zone_line)
        if not precision.candidate:
            return None,FloorTrial(False,precision.reason,original,step,precision.source_support,precision,excluded,reference_gaps)
        coverage=precision.coverage;support=precision.source_support
    if support is None or not support.candidate:
        return None,FloorTrial(False,'source_support_missing' if support is None else support.reason,
                               coverage,step,support,precision,excluded,reference_gaps)
    return proposed,FloorTrial(True,'conditional_source_and_baked_footprint_only',coverage,step,support,precision,excluded,reference_gaps)
