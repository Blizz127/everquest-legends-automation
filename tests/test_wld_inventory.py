"""Focused structural checks for WLD inventory framing and string references."""
from struct import pack

import pytest

from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def fixture_wld() -> bytes:
    names = b"\x00TREE_ACTORDEF\x00MESH1\x00"
    encoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                    for index, value in enumerate(names))
    header = pack("<7I", 0x54503D02, 0x00015500, 2, 0, 0, len(names), 0)
    # A 0x15 location refers to TREE_ACTORDEF; 0x36 is an opaque mesh here.
    location = pack("<IIi", 12, 0x15, 0) + pack("<iI", -1, 814)
    mesh = pack("<IIi", 8, 0x36, -15) + pack("<I", 7)
    return header + encoded + location + mesh + b"\x00\x00\x00\x00"


def test_inventory_counts_fragments_and_resolves_placement_reference():
    wld = WLDInventory(fixture_wld())
    assert wld.fragment_count == 2
    assert wld.type_counts == {0x15: 1, 0x36: 1}
    assert wld.placement_references() == (("TREE_ACTORDEF", 814),)
    assert wld.fragments[1].name == "MESH1"
    assert wld.body(wld.fragments[0]) == pack("<iI", -1, 814)
    assert wld.trailing_bytes_hex == "00000000"


def test_invalid_fragment_size_and_name_reference_are_rejected():
    raw = bytearray(fixture_wld())
    fragment_start = 28 + len(b"\x00TREE_ACTORDEF\x00MESH1\x00")
    raw[fragment_start:fragment_start + 4] = pack("<I", 10_000)
    with pytest.raises(ValueError, match="bounds"):
        WLDInventory(bytes(raw))
    raw = bytearray(fixture_wld())
    raw[fragment_start + 12:fragment_start + 16] = pack("<i", -10_000)
    with pytest.raises(ValueError, match="reference"):
        WLDInventory(bytes(raw)).placement_references()


def test_unresolved_fragment_name_is_reported_without_losing_inventory():
    raw = bytearray(fixture_wld())
    fragment_start = 28 + len(b"\x00TREE_ACTORDEF\x00MESH1\x00")
    raw[fragment_start + 8:fragment_start + 12] = pack("<i", -0x1000000)
    wld = WLDInventory(bytes(raw))
    assert wld.unresolved_fragment_name_refs == 1
    assert wld.fragment_count == 2
