"""Resolve copied WLD actor definitions to their static 0x36 meshes.

Butcherblock's 0x14 actor definition has a 1-based 0x2D reference at body
offset 32; that 0x2D has a 1-based 0x36 reference at body offset 0. Both
positions were checked against the owner's copied object WLD files. No
placement transform or collision is computed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from struct import unpack_from

from .wld_inventory import WLDFragment, WLDInventory


@dataclass(frozen=True)
class ModelLink:
    actor_name: str
    actor_fragment_index: int
    mesh_ref_fragment_index: int
    mesh_fragment_index: int
    mesh_name: str | None
    exact_expected_mesh_name: bool


def _reference(wld: WLDInventory, source: WLDFragment, offset: int,
               expected_type: int) -> WLDFragment:
    if source.body_size < offset + 4:
        raise ValueError("WLD model reference field is truncated")
    number = unpack_from("<I", wld.raw, source.body_offset + offset)[0]
    if number < 1 or number > len(wld.fragments):
        raise ValueError("WLD model reference is out of bounds")
    target = wld.fragments[number - 1]
    if target.type_code != expected_type:
        raise ValueError("WLD model reference has wrong fragment type")
    return target


def read_model_links(wld: WLDInventory) -> tuple[ModelLink, ...]:
    links = []
    for actor in wld.fragments:
        if actor.type_code != 0x14:
            continue
        if not actor.name or not actor.name.endswith("_ACTORDEF"):
            raise ValueError("WLD static actor has no exact _ACTORDEF name")
        mesh_ref = _reference(wld, actor, 32, 0x2D)
        mesh = _reference(wld, mesh_ref, 0, 0x36)
        expected_name = actor.name.removesuffix("_ACTORDEF") + "_DMSPRITEDEF"
        links.append(ModelLink(actor.name, actor.index, mesh_ref.index,
                               mesh.index, mesh.name, mesh.name == expected_name))
    names = [link.actor_name for link in links]
    if len(names) != len(set(names)):
        raise ValueError("WLD has duplicate static actor definitions")
    return tuple(links)


def combine_model_links(libraries: tuple[WLDInventory, ...]) -> dict[str, tuple[WLDInventory, ModelLink]]:
    result = {}
    for library in libraries:
        for link in read_model_links(library):
            if link.actor_name in result:
                raise ValueError("Duplicate static actor definition across WLDs")
            result[link.actor_name] = (library, link)
    return result
