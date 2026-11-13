"""Resolve 1-based actor-to-mesh chains without fuzzy name matching."""
from struct import pack

import pytest

from eql_automation.model_links import read_model_links
from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def linked_wld(actor_ref: int = 2) -> WLDInventory:
    names = b"\x00BTENT_ACTORDEF\x00BTENT_DMSPRITEDEF\x00"
    encoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                    for index, value in enumerate(names))
    mesh_name_ref = -names.index(b"BTENT_DMSPRITEDEF")
    actor_name_ref = -names.index(b"BTENT_ACTORDEF")
    mesh = pack("<IIiI", 8, 0x36, mesh_name_ref, 0)
    mesh_ref = pack("<IIiII", 12, 0x2D, 0, 1, 0)
    actor_body = bytearray(40)
    actor_body[32:36] = pack("<I", actor_ref)
    actor = pack("<IIi", len(actor_body) + 4, 0x14, actor_name_ref) + actor_body
    header = pack("<7I", 0x54503D02, 0x00015500, 3, 0, 0, len(names), 0)
    return WLDInventory(header + encoded + mesh + mesh_ref + actor + b"\xff" * 4)


def test_exact_actor_resolves_through_1_based_mesh_reference():
    links = read_model_links(linked_wld())
    assert len(links) == 1
    assert links[0].actor_name == "BTENT_ACTORDEF"
    assert links[0].mesh_fragment_index == 0
    assert links[0].exact_expected_mesh_name is True


def test_wrong_reference_type_is_rejected():
    with pytest.raises(ValueError, match="wrong fragment type"):
        read_model_links(linked_wld(actor_ref=1))
