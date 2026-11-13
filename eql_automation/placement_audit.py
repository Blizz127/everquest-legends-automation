"""Read-only 0x15 placement provenance checks for copied client WLD files.

Field layout follows the VisualEQ 0x15 loader, cross-checked against the
owner's Butcherblock bytes. This does not compose model geometry or collision.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from struct import unpack_from

from .wld_inventory import WLDInventory


# The exact IEEE-754 float32 value in 22 copied Butcherblock 0x15 records.
DROPPED_TREE_Z = -32767.998046875


@dataclass(frozen=True)
class ObjectLocation:
    fragment_index: int
    actor_name: str
    flags: int
    x: float
    y: float
    z: float
    rot_z: float
    rot_y: float
    rot_x: float
    scale_y: float
    scale_x: float
    dropped_tree_sentinel: bool


@dataclass(frozen=True)
class PlacementAudit:
    placement_count: int
    non_sentinel_count: int
    dropped_tree_sentinel_count: int
    dropped_tree_names: dict[str, int]
    unique_actor_references: int
    exact_model_matches: int
    unmatched_actor_names: tuple[str, ...]
    model_definition_count: int
    unused_model_definitions: tuple[str, ...]
    collision_composed: bool = False
    navigability_verified: bool = False


def read_object_locations(wld: WLDInventory) -> tuple[ObjectLocation, ...]:
    locations = []
    for fragment in wld.fragments:
        if fragment.type_code != 0x15:
            continue
        if fragment.body_size < 52:
            raise ValueError("WLD 0x15 object location is too short")
        (reference, flags, _fragment1, x, y, z, rot_z, rot_y, rot_x,
         _unknown, scale_y, scale_x, _vertex_colors) = unpack_from(
             "<iII9fI", wld.raw, fragment.body_offset)
        actor_name = wld.resolve_name(reference, strict=True)
        if not actor_name:
            raise ValueError("WLD 0x15 object location lacks an actor name")
        if not all(map(isfinite, (x, y, z, rot_z, rot_y, rot_x, scale_y, scale_x))):
            raise ValueError("WLD 0x15 object location contains nonfinite transform")
        locations.append(ObjectLocation(fragment.index, actor_name, flags,
                                        x, y, z, rot_z, rot_y, rot_x,
                                        scale_y, scale_x, z == DROPPED_TREE_Z))
    return tuple(locations)


def audit_object_locations(objects: WLDInventory,
                           model_libraries: tuple[WLDInventory, ...]) -> PlacementAudit:
    locations = read_object_locations(objects)
    model_names = []
    for library in model_libraries:
        for fragment in library.fragments:
            if fragment.type_code == 0x14:
                if not fragment.name:
                    raise ValueError("WLD 0x14 model definition lacks a name")
                model_names.append(fragment.name)
    if len(set(model_names)) != len(model_names):
        raise ValueError("Duplicate exact actor definition names")
    definitions = set(model_names)
    references = Counter(item.actor_name for item in locations)
    dropped = Counter(item.actor_name for item in locations if item.dropped_tree_sentinel)
    matched = sum(item.actor_name in definitions for item in locations)
    return PlacementAudit(
        placement_count=len(locations),
        non_sentinel_count=len(locations) - sum(dropped.values()),
        dropped_tree_sentinel_count=sum(dropped.values()),
        dropped_tree_names=dict(sorted(dropped.items())),
        unique_actor_references=len(references),
        exact_model_matches=matched,
        unmatched_actor_names=tuple(sorted(set(references) - definitions)),
        model_definition_count=len(model_names),
        unused_model_definitions=tuple(sorted(definitions - set(references))),
    )
