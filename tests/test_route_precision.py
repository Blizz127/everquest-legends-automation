"""A model/option change cannot reuse a prepared source-floor ticket."""
from dataclasses import replace

import pytest

from eql_automation.route_geometry import RouteGeometryPreparer
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.route_precision import RoutePrecisionPolicy, validate_precision_seams
from test_route_geometry import build, stage
from test_route_floor_commit import legacy, receipt
from test_tile_rounding import grid


def with_policy(legacy, **options):
    f=build(legacy, **options);p=f.prepare
    model=replace(grid(),zone=f.runner.route.zone,mesh_sha256=p.source.mesh_sha256,
                  source_archive_sha256=p.source.archive_sha256)
    p.source.tile_grid=model
    f.prepare=RouteGeometryPreparer(f.ledger,ground=p.ground,source=p.source,static=p.static,bsp=p.bsp,
        bounds=p.bounds,static_inventory_sha256=p.static_inventory_sha256,vertical_window=p.vertical_window,
        maximum_source_z_difference=p.maximum_source_z_difference,
        precision_policy=RoutePrecisionPolicy(model,True))
    return f


def test_policy_is_bound_to_pending_record_and_release_commits_once(legacy):
    f=with_policy(legacy);chain=f.ledger.chain;before=chain.previous
    ticket=stage(f);record=f.prepare.record_for(ticket)
    assert record.precision_policy is f.prepare.precision_policy
    assert record.precision_policy.record()['real_client_accepted'] is False
    assert f.ledger.chain is chain and chain.previous is before
    result=receipt(ticket);f.state['now']=result.up_completed_at+.001
    f.ledger.commit(ticket,result)
    assert f.ledger.chain.index==chain.index+1
    with pytest.raises(RouteHalt):f.ledger.commit(ticket,result)


@pytest.mark.parametrize('change',['manifest','grid_identity','policy','overlap','seams'])
def test_changed_model_or_option_invalidates_precomputed_checks(legacy,change):
    f=with_policy(legacy);p=f.prepare;p.precompute(f.scene)
    if change=='manifest':p.source.tile_grid=replace(p.source.tile_grid,manifest_sha256='f'*64)
    elif change=='grid_identity':p.source.tile_grid=replace(p.source.tile_grid)
    elif change=='policy':p.precision_policy=replace(p.precision_policy)
    elif change=='overlap':p.precision_policy=replace(p.precision_policy,allow_overlap=False)
    else:p.source.seams=(object(),)
    with pytest.raises(ValueError):p(f.runner.propose(f.clock()),f.scene)
    assert f.ledger._pending is None and f.ledger.chain.index==1


@pytest.mark.parametrize('hazard',['water','missing_source'])
def test_model_never_replaces_body_volume_or_source_support(legacy,hazard):
    f=with_policy(legacy,water=hazard=='water')
    if hazard=='missing_source':f.prepare.source.source_faces_for_footprint=lambda _:()
    with pytest.raises(ValueError,match='BSP volume|Terrain'):stage(f)
    assert f.ledger.chain.index==1 and f.ledger._pending is None


def test_tile_source_cannot_be_used_without_explicit_policy(legacy):
    f=with_policy(legacy);f.prepare.precision_policy=None
    with pytest.raises(ValueError,match='explicit'):stage(f)


@pytest.mark.parametrize('value',[None,0,1,'yes'])
def test_overlap_option_is_a_boolean(value):
    with pytest.raises(ValueError):RoutePrecisionPolicy(grid(),value)


def test_tile_seams_cannot_be_reused_after_hiding_the_grid():
    from types import SimpleNamespace
    from eql_automation.portal_precision import PortalLink, collect_seams
    model=grid();a,b=model.sides(0,18)[1],model.sides(0,19)[0]
    seams=collect_seams((PortalLink(0,1,((a,0.,.6),(a,8.,.6))),
        PortalLink(1,0,((b,8.,.6),(b,0.,.6)))),(63,63),(7,7),tile_grid=model)
    assert len(seams)==1
    with pytest.raises(ValueError,match='explicit'):
        validate_precision_seams(SimpleNamespace(seams=seams,tile_grid=None),None)
