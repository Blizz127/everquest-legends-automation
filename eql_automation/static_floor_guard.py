"""Add copied static-instance occupancy without changing terrain floor identity."""
from dataclasses import asdict,dataclass
from hashlib import sha256
import json
import re

from .floor_replay import FloorTrial
from .source_occupancy import SourceOccupancy,check_selected_floor_clearance


@dataclass(frozen=True)
class StaticFloorCheck:
    candidate: bool
    reason: str
    static_inventory_sha256: str | None = None
    static_faces: int | None = None
    occupancy: SourceOccupancy | None = None
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_static_floor(floor_trial,footprint,terrain_sources,static_view):
    """Require the exact already-checked cell; static faces can only obstruct it."""
    if (not isinstance(floor_trial,FloorTrial) or not floor_trial.candidate
            or floor_trial.floor_step is None or not floor_trial.floor_step.candidate
            or floor_trial.floor_step.occupancy is None or not floor_trial.floor_step.occupancy.candidate):
        return StaticFloorCheck(False,'accepted_terrain_trial_required')
    step=floor_trial.floor_step
    try:
        geometry=sha256(json.dumps({'footprint':footprint,'sources':[asdict(s) for s in terrain_sources]},
                                  sort_keys=True,separators=(',',':')).encode()).hexdigest()
    except (TypeError,ValueError):
        return StaticFloorCheck(False,'invalid_terrain_cell')
    if geometry!=step.geometry_sha256:
        return StaticFloorCheck(False,'terrain_cell_changed_since_floor_trial')
    inventory=getattr(static_view,'inventory_sha256',None)
    if not isinstance(inventory,str) or re.fullmatch('[0-9a-f]{64}',inventory) is None:
        return StaticFloorCheck(False,'static_inventory_identity_required')
    try:
        static=static_view.faces_for_footprint(footprint)
    except ValueError:
        return StaticFloorCheck(False,'static_query_refused',inventory)
    if not isinstance(static,tuple) or not isinstance(terrain_sources,tuple):
        return StaticFloorCheck(False,'invalid_complete_source_inventory',inventory)
    selection=sha256(json.dumps({'terrain_proof':step.proof_sha256,'static_inventory':inventory},
                               sort_keys=True,separators=(',',':')).encode()).hexdigest()
    occupancy=check_selected_floor_clearance(footprint,terrain_sources+static,
        selected_ids=step.selected_ids,selection_evidence_sha256=selection,
        body_height=step.occupancy.hypothetical_body_height)
    return StaticFloorCheck(occupancy.candidate,
        'conditional_terrain_and_static_occupancy_only' if occupancy.candidate else occupancy.reason,
        inventory,len(static),occupancy)
