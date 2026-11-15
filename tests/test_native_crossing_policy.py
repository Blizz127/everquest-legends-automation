"""Explicit transition cells, using actual source-floor and native classifiers."""
from dataclasses import asdict, replace

import pytest

from eql_automation.bsp_clip import check_bsp_wedge
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.native_body_regions import classify_source_body_regions
from eql_automation.native_crossing_policy import NativeCrossingRegionPolicy, check_source_crossing_cell
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import _zero_native
from eql_automation.zone_line import ExpectedZoneLine
from test_client_classification import view, leaf
from test_source_itinerary import fixture
from types import SimpleNamespace


def setup(*, nodes=None, labels=None):
    prefix, _, terrain, static, _, _ = fixture()
    nodes = nodes or (leaf(3),)
    model = view(nodes, wld_pin=terrain.wld_sha256)
    bsp = BspVolumeView(SimpleNamespace(nodes=nodes,
        labels_by_region={2:{'zoneline'}} if labels is None else labels),
        region_count=3, wld_sha256=terrain.wld_sha256)
    ordinary = NativeZeroRegionTrialPolicy('e'*64, terrain.archive_sha256,
        terrain.wld_sha256, static.inventory_sha256, bsp.inventory_sha256,
        model.inventory_sha256, model)
    line = ExpectedZoneLine('test-native-crossing', ordinary.zone, ordinary.mesh_sha256,
        terrain.archive_sha256, terrain.wld_sha256, bsp.inventory_sha256, 'f'*64,
        'DRNTP00255000001', 2, (1,), (2,))
    policy = NativeCrossingRegionPolicy(ordinary, line)
    return prefix, terrain, static, bsp, policy


def run(values, **changes):
    prefix, terrain, static, bsp, policy = values
    return check_source_crossing_cell(prefix, (-2.,0.), (-2.5,0.), radius=.2,
        **dict(dict(terrain=terrain, static=static, bsp=bsp, policy=policy), **changes))


def test_exact_transition_is_distinct_from_ordinary_zero_travel():
    values=setup(); before=_chain_snapshot(values[0])
    branch, result=run(values); record=result.record()
    assert _chain_snapshot(values[0])==before and branch is not values[0]
    assert record['terrain']['candidate'] and record['static']['candidate']
    assert record['original_bsp']['reason']=='labelled_bsp_volume'
    assert record['scoped_bsp']['candidate']
    assert record['possible_transition_regions']==[2]
    assert record['native']['possible_flags']==[0x80000000]
    assert not record['source_floor_committed'] and not record['runtime_ready']
    assert not record['input_authorized'] and not record['real_client_accepted']
    footprint=swept_square((-2.,0.),(-2.5,0.),.2)
    native=classify_source_body_regions(branch.previous,footprint,
        values[1].source_faces_for_footprint(footprint),values[2],values[4].ordinary.classifier,
        source_wld_sha256=values[1].wld_sha256)
    with pytest.raises(ValueError,match='nonzero'): _zero_native(native)
    with pytest.raises(ValueError,match='seal'): replace(result,payload=result.payload+b' ').record()


@pytest.mark.parametrize('clipped',[False,True])
def test_source_body_bsp_threads_only_explicit_transition_permission(clipped):
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    values=setup();branch,_=run(values)
    footprint=swept_square((-2.,0.),(-2.5,0.),.2)
    sources=values[1].source_faces_for_footprint(footprint)
    args=(branch.previous,footprint,sources,values[3])
    assert not check_source_body_bsp(*args,clip_branches=clipped).candidate
    result=check_source_body_bsp(*args,clip_branches=clipped,
        expected_zone_line=values[-1].expected_zone_line)
    assert result.candidate and not result.input_authorized


@pytest.mark.parametrize('nodes',[(leaf(1),),
    ((1.,0.,0.,0.,0,2,3),leaf(1),leaf(3)),
    ((1.,0.,0.,0.,0,0,2),leaf(3))])
def test_zero_mixed_expected_transition_and_native_missing_child_keep_metadata(nodes):
    values=setup(nodes=nodes)
    _,result=run(values)
    record=result.record()
    assert set(record['native']['possible_flags']) <= {0,0x80000000}
    assert record['geometry_candidate'] and not record['input_authorized']


@pytest.mark.parametrize('hazard',['water','zoneline','unknown'])
def test_bsp_expected_region_does_not_hide_a_second_label(hazard):
    values=setup(nodes=((1.,0.,0.,0.,0,2,3),leaf(3),leaf(1)),
                 labels={2:{'zoneline'},0:{hazard}})
    with pytest.raises(ValueError,match='BSP'): run(values)


def test_native_water_refuses_even_if_old_bsp_mapping_is_unlabelled():
    values=setup(nodes=((1.,0.,0.,0.,0,2,3),leaf(3),leaf(2)))
    with pytest.raises(ValueError,match='another native hazard'): run(values)


def test_native_incomplete_model_refuses():
    values=setup(nodes=((1.,0.,0.,0.,0,1,2),leaf(3)))
    # The ordinary clipped BSP also catches this cycle before native evaluation.
    with pytest.raises(ValueError,match='BSP'): run(values)


@pytest.mark.parametrize('field,value', [('region_ids',(1,)),('wld_sha256','1'*64),
    ('bsp_inventory_sha256','1'*64),('raw_label','DRNTP00255000099')])
def test_foreign_transition_identity_refuses(field,value):
    *_,policy=setup()
    with pytest.raises(ValueError):
        NativeCrossingRegionPolicy(policy.ordinary,replace(policy.expected_zone_line,**{field:value}))


def test_terrain_and_static_checks_are_not_waived():
    values=setup(); prefix,terrain,static,bsp,policy=values
    old=terrain.source_faces_for_footprint
    terrain.source_faces_for_footprint=lambda _:()
    with pytest.raises(ValueError,match='terrain'): run(values)
    terrain.source_faces_for_footprint=old
    from test_source_step import face
    static.sources=(face(((-2.25,-1.,.5),(-2.25,1.,.5),(-2.25,0.,8.)),0,7),)
    static.faces_for_footprint=lambda _:static.sources
    with pytest.raises(ValueError,match='static'): run(values)


def test_changed_prefix_during_geometry_callback_refuses():
    values=setup(); prefix,terrain,*_=values
    original=terrain.source_faces_for_footprint
    def mutate(footprint):
        prefix.index+=1
        return original(footprint)
    terrain.source_faces_for_footprint=mutate
    with pytest.raises(ValueError,match='committed conditional source floor'): run(values)


def test_clipped_wedge_default_and_missing_child_refusal_are_preserved():
    *_,bsp,policy=setup()
    polygon=((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.))
    assert check_bsp_wedge(bsp,polygon,(0.,0.,0.),(0.,0.,6.)).reason=='labelled_bsp_volume'
    result=check_bsp_wedge(bsp,polygon,(0.,0.,0.),(0.,0.,6.),
                           expected_zone_line=policy.expected_zone_line)
    assert result.candidate and result.labelled_regions==((2,('zoneline',)),)
    *_,bsp,policy=setup(nodes=((1.,0.,0.,0.,0,2,0),leaf(3)))
    result=check_bsp_wedge(bsp,polygon,(0.,0.,0.),(0.,0.,6.),
                           expected_zone_line=policy.expected_zone_line)
    assert not result.candidate and result.reason=='missing_bsp_child'


@pytest.mark.parametrize('change', ['query', 'storage', 'classifier'])
def test_geometry_storage_and_classifier_replacements_cannot_keep_old_pins(monkeypatch,change):
    import eql_automation.native_crossing_policy as module
    values=setup(); _,terrain,static,_,policy=values
    classify=module.classify_source_body_regions
    def changed(*args,**kwargs):
        result=classify(*args,**kwargs)
        if change=='query':
            original=terrain.source_faces_for_footprint
            terrain.source_faces_for_footprint=lambda footprint:original(footprint)
        elif change=='storage':static.sources=()
        else:
            model=view((leaf(3),),wld_pin=terrain.wld_sha256)
            object.__setattr__(policy.ordinary,'classifier',model)
        return result
    monkeypatch.setattr(module,'classify_source_body_regions',changed)
    with pytest.raises(ValueError,match='prefix or policy changed'): run(values)


def test_final_height_callback_cannot_publish_after_mutating_departure(monkeypatch):
    from eql_automation.source_floor_chain import SourceFloorChain
    values=setup(); prefix=values[0]
    original=SourceFloorChain.floor_at
    def changed(self,point):
        result=original(self,point)
        if self is not prefix:prefix.index+=1
        return result
    monkeypatch.setattr(SourceFloorChain,'floor_at',changed)
    with pytest.raises(ValueError,match='committed conditional source floor'): run(values)


@pytest.mark.parametrize('change', ['extra_flag', 'record', 'label', 'incomplete', 'aggregate'])
def test_rewritten_native_outcomes_cannot_pass_exact_transition(monkeypatch,change):
    import eql_automation.native_crossing_policy as module
    values=setup(); classify=module.classify_source_body_regions
    def changed(*args,**kwargs):
        result=classify(*args,**kwargs)
        if change=='incomplete':return replace(result,complete=False)
        if change=='aggregate':return replace(result,possible_flags=(0,))
        value=result.pieces[0]['classification']['possible_classes'][0]
        if change=='extra_flag':value['flags'] |= 1<<20
        elif change=='record':value['record_index']+=1
        else:value['raw_label']='DRNTP00255000099'
        return result
    monkeypatch.setattr(module,'classify_source_body_regions',changed)
    with pytest.raises(ValueError):run(values)
