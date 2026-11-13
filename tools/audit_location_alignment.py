#!/usr/bin/env python3
"""Compare filtered historical /loc lines with copied client terrain offline.

This never accepts a coordinate transform, navigation edge, or live position.
The input must contain only the owner's own system location/zone lines and
must be kept outside git in the approved EQL data store.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eql_automation.client_ingest import sha256_file
from eql_automation.location_alignment import (
    historical_zone_locations, score_location_transforms,
)
from eql_automation.location_log import unique_client_zone_ids
from eql_automation.mesh_geometry import read_meshes
from eql_automation.pfs_archive import PFSArchive
from eql_automation.wld_inventory import WLDInventory


DATA_ROOT = Path.home() / ".local/share/eql-automation"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zone", choices=("butcher", "crushbone", "gfaydark"))
    parser.add_argument("display_name")
    parser.add_argument("filtered_system_lines", type=Path)
    args = parser.parse_args()
    approved = (DATA_ROOT / "client-data").resolve()
    log_lines = args.filtered_system_lines.resolve()
    archive_path = (approved / "retail-full/assets" / f"{args.zone}.s3d").resolve()
    names_path = (approved / "retail-sample/Resources/ZoneNames.txt").resolve()
    if (not log_lines.is_relative_to(approved) or
            not archive_path.is_relative_to(approved) or
            not names_path.is_relative_to(approved)):
        parser.error("Every source must stay inside the approved EQL client-data store")
    if (not log_lines.is_file() or log_lines.stat().st_size > 2 * 1024 * 1024 or
            not archive_path.is_file() or not names_path.is_file()):
        parser.error("Filtered lines or copied client sources are missing or too large")
    names_hash = sha256_file(names_path)
    unique_names, _ambiguous = unique_client_zone_ids(names_path)
    zone_id = unique_names.get(args.display_name)
    if zone_id is None:
        parser.error("Display name is absent or ambiguous in copied ZoneNames.txt")
    log_hash = sha256_file(log_lines)
    archive_hash = sha256_file(archive_path)
    try:
        samples = historical_zone_locations(
            log_lines.read_text(encoding="utf-8").splitlines(), args.display_name)
    except ValueError as exc:
        parser.error(str(exc))
    if not samples:
        parser.error("No historical /loc samples after entered-zone lines")
    archive = PFSArchive(archive_path)
    wld = WLDInventory(archive.read_member(f"{args.zone}.wld"))
    try:
        audit = score_location_transforms(samples, read_meshes(wld))
    except ValueError as exc:
        parser.error(str(exc))
    if (sha256_file(log_lines) != log_hash or
            sha256_file(archive_path) != archive_hash or
            sha256_file(names_path) != names_hash):
        parser.error("An input changed during the audit")
    print(json.dumps({
        "format": "eql-historical-loc-wld-audit-v1",
        "source_log_lines_sha256": log_hash,
        "source_archive_sha256": archive_hash,
        "source_wld_sha256": wld.sha256,
        "source_zone_names_sha256": names_hash,
        "zone_asset_name": args.zone,
        "zone_display_name": args.display_name,
        "zone_id": zone_id,
        "zone_asset_to_display_name_verified": False,
        **audit,
    }, indent=2))


if __name__ == "__main__":
    main()
