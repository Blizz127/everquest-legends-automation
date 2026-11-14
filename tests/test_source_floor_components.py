from types import SimpleNamespace

from eql_automation.source_floor_components import SourceFloorComponents
from test_source_step import setup,check


def test_step_disconnection_is_model_only_then_landing_changes_component():
    args=setup();sources=args[3].source_faces_for_footprint(())
    graph=SourceFloorComponents(sources,inventory_sha256=args[0].inventory_sha256)
    assert graph.goal(args[0],args[1]).possible
    blocked=graph.goal(args[0],args[2])
    assert not blocked.possible and blocked.reason=='different_exact_edge_floor_component'
    assert not blocked.physical_disconnection_proven
    transition,landing=check(args)
    assert transition.candidate and graph.goal(landing,args[2]).possible


def test_goal_queries_keep_all_height_layers_and_require_exact_triangle_membership():
    args=setup();sources=args[3].source_faces_for_footprint(())
    graph=SourceFloorComponents(sources,inventory_sha256=args[0].inventory_sha256)
    # Both components meet in XY along the actual step. Neither layer is
    # silently chosen by nearest height; the precheck remains an overapproximation.
    shared=graph.goal(args[0],(0.,0.))
    assert shared.possible and len(shared.goal_components)==2
    assert not graph.goal(args[0],(20.,0.)).possible
