"""Read copied WLD BSP region labels as offline hazard candidates.

The 0x29 layout and labels follow LanternExtractor's BspRegionType parser:
https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/BspRegionType.cs
The 0x21 tree references follow its BspTree parser. These labels do not
establish a client's movement, collision, or an actionable zone transition.
"""
from __future__ import annotations

from collections import Counter
from struct import unpack_from

from .wld_inventory import WLDInventory, XOR_KEY


MAX_REGION_TEXT = 4096


def _classes(label: str) -> tuple[str, ...]:
    text = label.lower()
    if text.startswith(("wtn_", "wt_")):
        return ("water",)
    if text.startswith("wtntp"):
        return ("water", "zoneline")
    if text.startswith(("lan_", "la_")):
        return ("lava",)
    if text.startswith("lantp"):
        return ("lava", "zoneline")
    if text.startswith("drntp"):
        return ("zoneline",)
    if text.startswith("drp_"):
        return ("pvp",)
    if text.startswith("drn_"):
        return ("slippery",) if "_s_" in text else ("unknown",)
    if text.startswith("sln_"):
        return ("water_blocks_los",)
    if text.startswith("vwn_"):
        return ("freezing_water",)
    return ("unknown",)


def audit_bsp_regions(wld: WLDInventory) -> dict:
    """Validate BSP/region references and summarize labelled region IDs.

    IDs in 0x29 records are zero-based region-list indices. The 0x21 tree
    stores one-based region and child references, with zero meaning absent.
    No 0x22 shape/PVS or client collision behavior is decoded here.
    """
    region_count = wld.bsp_region_count
    if wld.type_counts.get(0x22, 0) != region_count:
        raise ValueError("WLD BSP region count does not match 0x22 fragments")
    trees = [fragment for fragment in wld.fragments if fragment.type_code == 0x21]
    if len(trees) != 1:
        raise ValueError("WLD must have exactly one BSP tree")
    body = wld.body(trees[0])
    if len(body) < 4:
        raise ValueError("WLD BSP tree is truncated")
    node_count = unpack_from("<I", body)[0]
    if node_count > 2 * region_count + 10000 or len(body) != 4 + 28 * node_count:
        raise ValueError("WLD BSP node count or length is invalid")
    referenced_tree_regions: set[int] = set()
    for index in range(node_count):
        region_ref, left_ref, right_ref = unpack_from("<3I", body, 4 + index * 28 + 16)
        if region_ref > region_count or left_ref > node_count or right_ref > node_count:
            raise ValueError("WLD BSP tree reference is out of range")
        if region_ref:
            referenced_tree_regions.add(region_ref - 1)

    classes: dict[str, set[int]] = {}
    record_classes: Counter[str] = Counter()
    references_checked = 0
    for fragment in wld.fragments:
        if fragment.type_code != 0x29:
            continue
        body = wld.body(fragment)
        if len(body) < 12:
            raise ValueError("WLD 0x29 region type is truncated")
        _flags, count = unpack_from("<II", body)
        if count > region_count or 12 + 4 * count > len(body):
            raise ValueError("WLD 0x29 region count exceeds bounds")
        region_ids = unpack_from(f"<{count}I", body, 8)
        if len(set(region_ids)) != count or any(value >= region_count for value in region_ids):
            raise ValueError("WLD 0x29 region ID is duplicate or out of range")
        text_size = unpack_from("<I", body, 8 + 4 * count)[0]
        text_start = 12 + 4 * count
        text_end = text_start + text_size
        if (text_size > MAX_REGION_TEXT or text_end > len(body) or
                len(body) - text_end > 3 or any(body[text_end:])):
            raise ValueError("WLD 0x29 region label exceeds bounds")
        if text_size:
            decoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                            for index, value in enumerate(body[text_start:text_end]))
            label = decoded.split(b"\x00", 1)[0].decode("latin-1")
        else:
            label = fragment.name or ""
        if not label:
            raise ValueError("WLD 0x29 region label is empty")
        for category in _classes(label):
            classes.setdefault(category, set()).update(region_ids)
            record_classes[category] += 1
        references_checked += count
    return {
        "wld_sha256": wld.sha256,
        "bsp_region_count": region_count,
        "bsp_node_count": node_count,
        "bsp_regions_referenced_by_tree": len(referenced_tree_regions),
        "region_type_record_count": wld.type_counts.get(0x29, 0),
        "region_references_checked": references_checked,
        "record_class_counts": dict(sorted(record_classes.items())),
        "candidate_region_ids": {name: sorted(indices)
                                 for name, indices in sorted(classes.items())},
        "region_shapes_decoded": False,
        "collision_verified": False,
        "zonelines_traversed": False,
        "real_client_accepted": False,
    }
