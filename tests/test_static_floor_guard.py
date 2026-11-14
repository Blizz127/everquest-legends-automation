from dataclasses import replace
from types import SimpleNamespace

from eql_automation.portal_precision import SourceFace
from eql_automation.static_floor_guard import check_static_floor
from test_floor_replay import setup,trial


def context(faces=()):
    data=setup();_,accepted=trial(data)
    assert accepted.candidate
    view=SimpleNamespace(inventory_sha256='d'*64,faces_for_footprint=lambda _:faces)
    return accepted,data[2],data[1].source_faces_for_footprint(data[2]),view


def test_static_wall_blocks_without_changing_selected_terrain_floor():
    wall=SourceFace(((-2.,32.,-1.),(2.,32.,-1.),(0.,32.,10.)),16,'TransparentMasked',101,0)
    args=context((wall,));before=args[0].floor_step.selected_ids
    result=check_static_floor(*args)
    assert not result.candidate and result.reason=='other_source_surface_intersects_body_band'
    assert args[0].floor_step.selected_ids==before
    assert result.occupancy.selected_ids==before


def test_high_static_face_is_classified_without_becoming_selected_floor():
    high=SourceFace(((-10.,20.,70.),(-10.,50.,70.),(10.,35.,70.)),0,'Diffuse',101,0)
    args=context((high,));result=check_static_floor(*args)
    assert result.candidate and result.static_faces==1
    assert result.occupancy.faces[0].classification=='overhead'
    assert (101,0) not in result.occupancy.selected_ids
    assert not result.input_authorized and not result.real_client_accepted


def test_changed_cell_or_terrain_cannot_reuse_accepted_selection():
    accepted,footprint,terrain,view=context()
    changed=tuple((x+.01,y) for x,y in footprint)
    assert check_static_floor(accepted,changed,terrain,view).reason=='terrain_cell_changed_since_floor_trial'
    modified=(replace(terrain[0],flag=16),*terrain[1:])
    assert check_static_floor(accepted,footprint,modified,view).reason=='terrain_cell_changed_since_floor_trial'


def test_query_budget_and_identity_collision_refuse_without_truncation():
    accepted,footprint,terrain,view=context()
    def failed(_):raise ValueError('budget')
    view.faces_for_footprint=failed
    assert check_static_floor(accepted,footprint,terrain,view).reason=='static_query_refused'
    view.faces_for_footprint=lambda _:terrain
    assert check_static_floor(accepted,footprint,terrain,view).reason=='invalid_or_duplicate_source_identity'


def test_failed_terrain_trial_is_never_recovered_by_empty_static_query():
    accepted,footprint,terrain,view=context()
    result=check_static_floor(replace(accepted,candidate=False),footprint,terrain,view)
    assert not result.candidate and result.reason=='accepted_terrain_trial_required'
