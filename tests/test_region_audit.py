"""Synthetic checks for bounded copied-WLD region references."""
from struct import pack

import pytest

from eql_automation.bsp_probe import BspPointLookup, nearby_zoneline_candidate
from eql_automation.nav import Point
from eql_automation.region_audit import audit_bsp_regions
from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def region_wld(*, water_id: int = 1, tree_region_ref: int = 2) -> WLDInventory:
    names = b"\x00WT_ZONE\x00Z000_ZONE\x00"
    encoded_names = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                          for index, value in enumerate(names))

    def fragment(type_code: int, name_ref: int, body: bytes) -> bytes:
        return pack("<IIi", len(body) + 4, type_code, name_ref) + body

    tree = fragment(0x21, 0, pack("<I4f3I", 1, 0, 0, 1, 0,
                                  tree_region_ref, 0, 0))
    regions = [fragment(0x22, 0, b"\x00\x00\x00\x00") for _ in range(3)]
    water = fragment(0x29, -1, pack("<4I", 0, 1, water_id, 0))
    label = b"DRNTP00255000001\x00"
    encoded_label = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                          for index, value in enumerate(label))
    zoneline = fragment(0x29, -9, pack("<4I", 0, 1, 2, len(label)) + encoded_label)
    records = [tree, *regions, water, zoneline]
    header = pack("<7I", 0x54503D02, 0x00015500, len(records), 3,
                  0, len(names), 0)
    return WLDInventory(header + encoded_names + b"".join(records))


def test_water_and_zoneline_markers_remain_candidate_region_ids():
    audit = audit_bsp_regions(region_wld())
    assert audit["bsp_region_count"] == 3
    assert audit["bsp_regions_referenced_by_tree"] == 1
    assert audit["record_class_counts"] == {"water": 1, "zoneline": 1}
    assert audit["candidate_region_ids"] == {"water": [1], "zoneline": [2]}
    assert audit["real_client_accepted"] is False


def test_bad_region_and_tree_references_are_rejected():
    with pytest.raises(ValueError, match="0x29 region ID"):
        audit_bsp_regions(region_wld(water_id=3))
    with pytest.raises(ValueError, match="BSP tree reference"):
        audit_bsp_regions(region_wld(tree_region_ref=4))


def point_wld(*, root_left: int = 2) -> WLDInventory:
    names = b"\x00WT_ZONE\x00DRNTP_ZONE\x00"
    encoded_names = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                          for index, value in enumerate(names))

    def fragment(type_code: int, name_ref: int, body: bytes) -> bytes:
        return pack("<IIi", len(body) + 4, type_code, name_ref) + body

    def node(nx: float, ny: float, region: int, left: int, right: int) -> bytes:
        return pack("<4f3I", nx, ny, 0, 0, region, left, right)

    nodes = (node(1, 0, 0, root_left, 5) + node(0, 1, 0, 3, 4) +
             node(0, 0, 2, 0, 0) + node(0, 0, 3, 0, 0) +
             node(0, 0, 1, 0, 0))
    tree = fragment(0x21, 0, pack("<I", 5) + nodes)
    regions = [fragment(0x22, 0, b"\x00\x00\x00\x00") for _ in range(3)]
    water = fragment(0x29, -1, pack("<4I", 0, 1, 1, 0))
    zone = fragment(0x29, -9, pack("<4I", 0, 1, 2, 0))
    records = [tree, *regions, water, zone]
    header = pack("<7I", 0x54503D02, 0x00015500, len(records), 3,
                  0, len(names), 0)
    return WLDInventory(header + encoded_names + b"".join(records))


def test_bsp_point_lookup_labels_branches_and_fails_closed():
    lookup = BspPointLookup(point_wld())
    assert lookup.probe(1, 1, 0).labels == ("water",)
    assert lookup.probe(1, -1, 0).zoneline_candidate
    assert lookup.probe(-1, 0, 0).labels == ()
    assert lookup.probe(0, 1, 0).reason == "on BSP plane"
    assert BspPointLookup(point_wld(root_left=0)).probe(1, 1, 0).reason == "missing BSP child"
    assert BspPointLookup(point_wld(root_left=1)).probe(1, 1, 0).reason == "cycle"
    overflow = BspPointLookup(point_wld())
    overflow.nodes = ((1e308, 1e308, 0, 0, 0, 2, 5), *overflow.nodes[1:])
    assert overflow.probe(1e308, 1e308, 0).reason == "nonfinite BSP distance"
    nearby = nearby_zoneline_candidate(lookup, Point(0, 0, 0), 0,
                                       transform="x,y", radius=10, step=5)
    assert nearby["nearest_zoneline_candidate"]["region_id"] == 2
    assert nearby["navigation_edge_accepted"] is False
