"""Exact modeled gaps/overlaps through real route checks and watchdog pipes."""
from dataclasses import replace

import numpy as np
import pytest

from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.portal_precision import PortalLink, SourceFace, collect_seams
from eql_automation.route_precision import RoutePrecisionPolicy
from test_destination_route import f, nav_module
from test_destination_route_runtime import exercise_destination
from test_ground_observer import rectangle
from test_route_floor_commit import legacy
from test_tile_rounding import grid


def configure_seam(f, nav_module, *, overlap=False, allow_overlap=True, distance=6.):
    p=f.planner
    model=replace(grid(origin=(-2803.8125,-2693.15625)) if overlap else grid(),
        zone=p.zone,mesh_sha256=p.pins[0],source_archive_sha256=p.pins[1])
    tile=14 if overlap else 18
    a,b=model.sides(0,tile)[1],model.sides(0,tile+1)[0]
    def rect(lo,hi,z):
        return tuple(tuple((x,y*2,z) for x,y,z in t) for t in rectangle(lo,hi,z))
    triangles=np.asarray(rect(a-10,a,.6)+rect(b,b+10,.6))
    p.mesh._detail=p.ground.triangles=triangles
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    source_triangles=rect(a-10,b+10,.2)
    p.source.sources=tuple(SourceFace(tuple((y,x,z) for x,y,z in tri),0,'Diffuse',10,i)
        for i,tri in enumerate(source_triangles))
    xyz=np.asarray(source_triangles)
    p.source.source_minimum=xyz.min(axis=1);p.source.source_maximum=xyz.max(axis=1)
    rings=np.zeros((2,6,3))
    for i,(lo,hi) in enumerate(((a-10,a),(b,b+10))):
        rings[i,:4]=((lo,0.,.6),(hi,0.,.6),(hi,8.,.6),(lo,8.,.6))
    portals=np.asarray([((a,0.,.6),(a,8.,.6)),((b,8.,.6),(b,0.,.6))])
    links=tuple(PortalLink(i,1-i,tuple(map(tuple,edge))) for i,edge in enumerate(portals))
    p.source.tile_grid=model
    p.source.seams=collect_seams(links,p.ground.areas,p.ground.components,tile_grid=model)
    assert len(p.source.seams)==1
    assert p.source.seams[0].actual_ulp_steps==(5 if overlap else 6)
    p.source.by_polygon={0:{0},1:{0}}
    f.planner=CurrentStartPlanner(mesh=p.mesh,ground=p.ground,source=p.source,static=p.static,bsp=p.bsp,
        zone_short_name=p.zone,expected_zone_id=p.zone_id,expected_zone_name=p.zone_name,
        mesh_sha256=p.pins[0],source_archive_sha256=p.pins[1],source_wld_sha256=p.pins[2],
        static_inventory_sha256=p.pins[3],precision_policy=RoutePrecisionPolicy(model,allow_overlap))
    p=f.planner
    f.nav=nav_module.NavMesh(rings,np.asarray([4,4]),p.ground.areas,np.asarray([0,1]),
        np.asarray([1,0]),portals,triangles,p.ground.polys,component=p.ground.components)
    f.nav.sha256=p.pins[0]
    from eql_automation.destination_route import plan_destination
    f.plan_destination=lambda:plan_destination(p,f.nav,f.reader,f.a,f.b,goal_xy=f.goal,
                                               **f.destination_options)
    f.start=(round(a-distance,2),4.);f.goal=(round(b+distance,2),4.);f.wall_x=(a+b)/2
    return f


@pytest.mark.parametrize('overlap',[False,True])
def test_matching_tile_policy_crosses_real_numerical_seam(f,nav_module,legacy,overlap):
    # Keep the pipe case focused on the crossing. The separate ordinary
    # destination case exercises the longer corridor; these exact boundaries
    # need observations on both sides, not six remote units on either side.
    configure_seam(f,nav_module,overlap=overlap,distance=1.5)
    session=exercise_destination(f,legacy)
    assert session.phase=='arrived'


def test_overlap_without_explicit_permission_stops_before_seam(f,nav_module,legacy):
    configure_seam(f,nav_module,overlap=True,allow_overlap=False)
    exercise_destination(f,legacy,refusal='Terrain:')


def test_tile_policy_cannot_clear_static_wall_at_boundary(f,nav_module,legacy):
    configure_seam(f,nav_module,overlap=True)
    exercise_destination(f,legacy,wall=True)
