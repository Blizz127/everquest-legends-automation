"""Checks the duplicate-name and sentinel pitfalls in object placement audits."""
from struct import pack

from eql_automation.placement_audit import DROPPED_TREE_Z, audit_object_locations
from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def make_wld(names: bytes, fragments: list[tuple[int, int, bytes]]) -> WLDInventory:
    encoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                    for index, value in enumerate(names))
    header = pack("<7I", 0x54503D02, 0x00015500, len(fragments), 0, 0, len(names), 0)
    framed = b"".join(pack("<IIi", len(body) + 4, kind, name_ref) + body
                      for kind, name_ref, body in fragments)
    return WLDInventory(header + encoded + framed + b"\xff" * 4)


def location(name_ref: int, z: float) -> tuple[int, int, bytes]:
    body = pack("<iII9fI", name_ref, 814, 0,
                1.0, 2.0, z, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0)
    return 0x15, 0, body + b"\x00" * 4


def test_exact_actor_names_do_not_merge_similar_models_and_sentinel_is_excluded():
    names = b"\x00BTENT_ACTORDEF\x00BTENT1_ACTORDEF\x00"
    first = -names.index(b"BTENT_ACTORDEF")
    second = -names.index(b"BTENT1_ACTORDEF")
    objects = make_wld(names, [location(first, 10.0), location(second, DROPPED_TREE_Z)])
    models = make_wld(names, [(0x14, first, pack("<I", 0)),
                              (0x14, second, pack("<I", 0))])
    audit = audit_object_locations(objects, (models,))
    assert audit.placement_count == 2
    assert audit.non_sentinel_count == 1
    assert audit.dropped_tree_sentinel_count == 1
    assert audit.exact_model_matches == 2
    assert audit.unmatched_actor_names == ()
    assert audit.collision_composed is False

    only_btent = make_wld(names, [(0x14, first, pack("<I", 0))])
    unmatched = audit_object_locations(objects, (only_btent,))
    assert unmatched.unmatched_actor_names == ("BTENT1_ACTORDEF",)
    assert unmatched.exact_model_matches == 1
