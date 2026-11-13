"""Offline CLI. It has no live game input or network backend."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from dataclasses import asdict

from .control import ControlPlane
from .modes import Action, ActionKind
from .sim import (SimSink, run_assist_demo, run_demo, run_gauge_demo,
                  run_navigation_demo, synthetic_graph)
from .synthetic_run import default_output_dir, run_synthetic_1_50
from .client_ingest import import_retail_copy
from .target import inspect_eqhost
from .poi_index import build_poi_index, current_summary
from .nav import MAP_STORE
from .zone_candidates import build_zone_candidates
from .spell_catalog import build_spell_level_index
from .ui_schema import index_ui_widgets
from .nav_evidence import DATA_ROOT, audit_butcherblock
from .pfs_archive import PFSArchive
from .wld_inventory import WLDInventory
from .placement_audit import audit_object_locations, read_object_locations
from .mesh_geometry import read_meshes, summarize_meshes
from .model_links import combine_model_links
from .instance_geometry import summarize_instances
from .candidate_scene import write_candidate_scene
from .material_audit import summarize_butcher_materials


def shell() -> None:
    control = ControlPlane()
    sink = SimSink(control.controller)
    print("OFFLINE SIMULATOR — no game input. Commands: mode off|assist|full, "
          "key F7|F8|F9, action KIND, queue KIND, drain, stop, safety REASON, "
          "reset safety, route, status, quit")
    print(control.indicator.text)
    while True:
        try:
            raw = input("eql-sim> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return
        normalized = raw.lower()
        if normalized in {"quit", "exit"}:
            return
        if normalized.startswith("mode ") or normalized in {"stop", "reset safety"}:
            try:
                print(control.handle_command(raw).text)
            except (RuntimeError, ValueError) as exc:
                print(exc)
        elif normalized.startswith("key "):
            try:
                print(control.handle_hotkey(raw.split(maxsplit=1)[1]).text)
            except (RuntimeError, ValueError) as exc:
                print(exc)
        elif normalized.startswith("safety "):
            try:
                print(control.emergency_stop(raw.split(maxsplit=1)[1]).text)
            except ValueError as exc:
                print(exc)
        elif normalized.startswith("action ") or normalized.startswith("queue "):
            try:
                kind = ActionKind(normalized.split(maxsplit=1)[1])
                action = Action(kind, "synthetic")
                if normalized.startswith("queue "):
                    print("QUEUED (simulation only)" if control.queue(action) else "DENIED")
                else:
                    print("ALLOWED (simulation only)" if sink.submit(action) else "DENIED")
            except ValueError:
                print("Unknown action kind")
        elif normalized == "drain":
            result = control.drain()
            sent = sum(sink.submit(item.action, item.permit) for item in result.ready)
            print(f"DRAINED {sent} simulated actions; {result.dropped + len(result.ready) - sent} dropped")
        elif normalized == "route":
            print(" -> ".join(synthetic_graph().route("start", "camp")))
        elif normalized == "status":
            print(f"{control.indicator.text} — {len(sink.accepted)} accepted, "
                  f"{len(sink.rejected)} denied")
        elif raw:
            print("Unknown command")


def main() -> None:
    parser = argparse.ArgumentParser(description="EverQuest Legends offline planning prototype")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="run one synthetic scenario")
    group.add_argument("--demo-navigation", action="store_true",
                       help="show offline stuck detection and replanning")
    group.add_argument("--demo-assist", action="store_true",
                       help="show an offline strict current-target rotation proposal")
    group.add_argument("--demo-gauges", action="store_true",
                       help="read fabricated player HP/mana bars; no game capture")
    group.add_argument("--shell", action="store_true", help="switch simulated modes without restarting")
    group.add_argument("--synthetic-1-50", action="store_true",
                       help="run a closed-loop synthetic level 1–50 scenario; not real-client proof")
    group.add_argument("--ingest-retail-copy", action="store_true",
                       help="read copied client text files into the untracked local map store")
    group.add_argument("--inspect-target", action="store_true",
                       help="inspect a copied eqhost.txt without connecting to its server")
    group.add_argument("--index-pois", action="store_true",
                       help="index unverified labels from the active map snapshot")
    group.add_argument("--query-pois", metavar="TEXT",
                       help="search unverified labels in the active map snapshot")
    group.add_argument("--index-zone-candidates", action="store_true",
                       help="cross-reference map labels with client zone names as unverified candidates")
    group.add_argument("--query-zone-candidates", metavar="TEXT",
                       help="search unverified zone-line candidates")
    group.add_argument("--index-spell-levels", action="store_true",
                       help="index client class levels for spells and skills; no server availability claim")
    group.add_argument("--query-spell-levels", metavar="TEXT",
                       help="search client spell/skill level candidates")
    group.add_argument("--index-ui-widgets", action="store_true",
                       help="index static client UI widget names; no live values")
    group.add_argument("--query-ui-widgets", metavar="TEXT",
                       help="search static default UI widget names")
    group.add_argument("--audit-butcherblock", action="store_true",
                       help="audit retained Butcherblock mesh evidence without accepting routes")
    group.add_argument("--inspect-s3d", action="store_true",
                       help="inventory a copied client S3D archive inside the EQL data store")
    group.add_argument("--inspect-wld", action="store_true",
                       help="inventory fragments in a WLD member of a copied S3D")
    group.add_argument("--audit-butcher-placements", action="store_true",
                       help="match copied Butcherblock object locations to exact actor definitions")
    group.add_argument("--audit-butcher-meshes", action="store_true",
                       help="decode copied Butcherblock 0x36 mesh arrays without accepting a route")
    group.add_argument("--audit-butcher-model-links", action="store_true",
                       help="trace copied Butcherblock actor definitions through mesh references")
    group.add_argument("--audit-butcher-instances", action="store_true",
                       help="count copied Butcherblock instanced mesh geometry without accepting collision")
    group.add_argument("--build-butcher-candidate-scene", action="store_true",
                       help="write provisional solid-flag Butcherblock OBJ outside git; no route acceptance")
    group.add_argument("--audit-butcher-materials", action="store_true",
                       help="trace copied Butcherblock polygon material chains without accepting collision")
    parser.add_argument("--output", type=Path,
                        help="synthetic trace directory; defaults under ~/.local/share/eql-automation/runs")
    parser.add_argument("--source", type=Path,
                        help="copied retail client text directory for --ingest-retail-copy")
    parser.add_argument("--member", help="WLD member name for --inspect-wld")
    parser.add_argument("--map", dest="map_name", help="filter POI query by map file stem")
    parser.add_argument("--limit", type=int, default=20, help="maximum POI query results")
    parser.add_argument("--class-name", help="filter client spell candidates by class name")
    parser.add_argument("--level", type=int, help="filter client spell candidates unlocked by this level")
    parser.add_argument("--mesh", type=Path,
                        help="optional retained mesh inside ~/.local/share/eql-automation for --audit-butcherblock")
    args = parser.parse_args()
    if args.demo:
        print(json.dumps(run_demo(), indent=2))
    elif args.demo_navigation:
        print(json.dumps(run_navigation_demo(), indent=2))
    elif args.demo_assist:
        print(json.dumps(run_assist_demo(), indent=2))
    elif args.demo_gauges:
        print(json.dumps(run_gauge_demo(), indent=2))
    elif args.synthetic_1_50:
        print(json.dumps(run_synthetic_1_50(args.output or default_output_dir()), indent=2))
    elif args.ingest_retail_copy:
        if args.source is None:
            parser.error("--ingest-retail-copy requires --source")
        print(json.dumps(import_retail_copy(args.source, args.output) if args.output
                         else import_retail_copy(args.source), indent=2))
    elif args.inspect_target:
        if args.source is None:
            parser.error("--inspect-target requires --source pointing to eqhost.txt")
        print(json.dumps(asdict(inspect_eqhost(args.source)), indent=2))
    elif args.index_pois or args.query_pois is not None:
        store = args.output or MAP_STORE
        summary = args.source or current_summary(store)
        index, path = build_poi_index(summary, store)
        if args.index_pois:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "label_count": len(index.pois),
                              "hint_counts": index.counts(),
                              "index_path": str(path),
                              "all_labels_verified": False}, indent=2))
        else:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "query": args.query_pois,
                              "results": [asdict(poi) for poi in index.search(
                                  args.query_pois, map_name=args.map_name,
                                  limit=args.limit)]}, indent=2))
    elif args.index_zone_candidates or args.query_zone_candidates is not None:
        store = args.output or MAP_STORE
        summary = args.source or current_summary(store)
        index, path = build_zone_candidates(summary, store)
        if args.index_zone_candidates:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "candidate_count": len(index.candidates),
                              "match_counts": index.counts(),
                              "index_path": str(path),
                              "transitions_verified": False}, indent=2))
        else:
            print(json.dumps({"snapshot_id": index.snapshot_id,
                              "query": args.query_zone_candidates,
                              "results": [asdict(item) for item in index.search(
                                  args.query_zone_candidates,
                                  source_map=args.map_name,
                                  limit=args.limit)]}, indent=2))
    elif args.index_spell_levels or args.query_spell_levels is not None:
        store = args.output or MAP_STORE
        source = args.source
        if source is None:
            source = Path(json.loads(current_summary(store).read_text())["source_dir"])
        index, path = build_spell_level_index(source, store)
        if args.index_spell_levels:
            print(json.dumps({"spell_catalog_sha256": index.spell_sha256,
                              "class_names_sha256": index.class_name_sha256,
                              "client_level_candidate_count": len(index.spells),
                              "class_candidate_counts": index.counts(),
                              "index_path": str(path),
                              "server_availability_verified": False,
                              "vendor_stock_verified": False}, indent=2))
        else:
            print(json.dumps({"query": args.query_spell_levels,
                              "class": args.class_name,
                              "level": args.level,
                              "results": [asdict(item) for item in index.search(
                                  args.query_spell_levels,
                                  class_name=args.class_name,
                                  level=args.level,
                                  limit=args.limit)],
                              "server_availability_verified": False}, indent=2))
    elif args.index_ui_widgets or args.query_ui_widgets is not None:
        store = args.output or MAP_STORE
        source = args.source
        if source is None:
            source = Path(json.loads(current_summary(store).read_text())["source_dir"])
        schema, path = index_ui_widgets(source, store)
        if args.index_ui_widgets:
            print(json.dumps({"widget_count": len(schema.widgets),
                              "source_sha256": schema.source_sha256,
                              "index_path": str(path),
                              "active_skin_verified": False,
                              "runtime_values_verified": False,
                              "hotkeys_verified": False}, indent=2))
        else:
            print(json.dumps({"query": args.query_ui_widgets,
                              "results": [asdict(item) for item in schema.search(
                                  args.query_ui_widgets, args.limit)],
                              "runtime_values_verified": False}, indent=2))
    elif args.audit_butcherblock:
        print(json.dumps(audit_butcherblock(store=args.output or MAP_STORE,
                                           mesh_path=args.mesh).to_dict(), indent=2))
    elif args.inspect_s3d:
        if args.source is None:
            parser.error("--inspect-s3d requires --source pointing to a copied .s3d")
        path = args.source.resolve()
        if not path.is_relative_to(DATA_ROOT.resolve()) or path.suffix.casefold() != ".s3d":
            parser.error("S3D source must be inside the approved EQL data store")
        if args.limit < 1:
            parser.error("--limit must be positive")
        archive = PFSArchive(path)
        print(json.dumps({"source": str(path), "archive_sha256": archive.sha256,
                          "member_count": len(archive.members),
                          "members": [asdict(item) for item in archive.members[:args.limit]],
                          "wld_members": [asdict(item) for item in archive.members
                                          if item.name.casefold().endswith(".wld")],
                          "all_members_decompressed": True,
                          "collision_decoded": False,
                          "navigability_verified": False}, indent=2))
    elif args.inspect_wld:
        if args.source is None or not args.member:
            parser.error("--inspect-wld requires --source copied .s3d and --member .wld")
        path = args.source.resolve()
        if not path.is_relative_to(DATA_ROOT.resolve()) or path.suffix.casefold() != ".s3d":
            parser.error("S3D source must be inside the approved EQL data store")
        if args.limit < 1:
            parser.error("--limit must be positive")
        archive = PFSArchive(path)
        if args.member.casefold() not in {item.name.casefold() for item in archive.members
                                          if item.name.casefold().endswith(".wld")}:
            parser.error("--member must name a WLD file in this archive")
        member = next(item.name for item in archive.members
                      if item.name.casefold() == args.member.casefold())
        wld = WLDInventory(archive.read_member(member))
        locations = wld.placement_references()
        references = Counter(name for name, _ in locations)
        flags = Counter(flag for _, flag in locations)
        print(json.dumps({"source": str(path), "archive_sha256": archive.sha256,
                          "member": member, "wld_sha256": wld.sha256,
                          "version_hex": f"0x{wld.version:08x}",
                          "fragment_count": wld.fragment_count,
                          "unresolved_fragment_name_refs": wld.unresolved_fragment_name_refs,
                          "bsp_region_count": wld.bsp_region_count,
                          "string_table_bytes": wld.string_table_bytes,
                          "fragment_type_counts": {f"0x{kind:02x}": count
                                                   for kind, count in wld.type_counts.items()},
                          "type_0x15_count": len(locations),
                          "type_0x15_unique_references": len(references),
                          "type_0x15_top_references": references.most_common(args.limit),
                          "type_0x15_flags": {f"0x{flag:x}": count
                                               for flag, count in sorted(flags.items())},
                          "sample_fragments": [asdict(item) for item in wld.fragments[:args.limit]],
                          "trailing_bytes_hex": wld.trailing_bytes_hex,
                          "collision_decoded": False, "navigability_verified": False}, indent=2))
    elif args.audit_butcher_placements:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        sources = (asset_root / "butcher.s3d", asset_root / "butcher_obj.s3d",
                   asset_root / "butcher_2_obj.s3d")
        if any(not path.resolve().is_relative_to(DATA_ROOT.resolve()) for path in sources):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        terrain, objects1, objects2 = (PFSArchive(path) for path in sources)
        placements = WLDInventory(terrain.read_member("objects.wld"))
        model1 = WLDInventory(objects1.read_member("butcher_obj.wld"))
        model2 = WLDInventory(objects2.read_member("butcher_2_obj.wld"))
        audit = audit_object_locations(placements, (model1, model2))
        print(json.dumps({"archive_sha256": {source.name: archive.sha256
                                              for source, archive in zip(
                                                  sources, (terrain, objects1, objects2))},
                          "wld_sha256": {"objects.wld": placements.sha256,
                                         "butcher_obj.wld": model1.sha256,
                                         "butcher_2_obj.wld": model2.sha256},
                          **asdict(audit)}, indent=2))
    elif args.audit_butcher_meshes:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        pairs = (("butcher.s3d", "butcher.wld"),
                 ("butcher_obj.s3d", "butcher_obj.wld"),
                 ("butcher_2_obj.s3d", "butcher_2_obj.wld"))
        if any(not (asset_root / source).resolve().is_relative_to(DATA_ROOT.resolve())
               for source, _ in pairs):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        inventories = []
        for source, member in pairs:
            archive = PFSArchive(asset_root / source)
            wld = WLDInventory(archive.read_member(member))
            meshes = read_meshes(wld)
            inventories.append({"archive": source, "archive_sha256": archive.sha256,
                                "member": member, "wld_sha256": wld.sha256,
                                **asdict(summarize_meshes(meshes))})
        print(json.dumps({"inventories": inventories,
                          "collision_composed": False,
                          "navigability_verified": False}, indent=2))
    elif args.audit_butcher_model_links:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        pairs = (("butcher.s3d", "objects.wld"),
                 ("butcher_obj.s3d", "butcher_obj.wld"),
                 ("butcher_2_obj.s3d", "butcher_2_obj.wld"))
        if any(not (asset_root / source).resolve().is_relative_to(DATA_ROOT.resolve())
               for source, _ in pairs):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        wlds = tuple(WLDInventory(PFSArchive(asset_root / source).read_member(member))
                     for source, member in pairs)
        links = combine_model_links(wlds[1:])
        locations = read_object_locations(wlds[0])
        placed_names = {item.actor_name for item in locations}
        print(json.dumps({"wld_sha256": {member: wld.sha256
                                         for (_, member), wld in zip(pairs, wlds)},
                          "actor_definition_count": len(links),
                          "unique_linked_mesh_count": len({(wld.sha256, link.mesh_fragment_index)
                                                           for wld, link in links.values()}),
                          "exact_expected_mesh_name_count": sum(
                              link.exact_expected_mesh_name for _, link in links.values()),
                          "placement_count": len(locations),
                          "placed_actor_names": len(placed_names),
                          "placements_with_mesh": sum(item.actor_name in links
                                                      for item in locations),
                          "unlinked_placement_names": sorted(placed_names - set(links)),
                          "collision_composed": False,
                          "navigability_verified": False}, indent=2))
    elif args.audit_butcher_instances:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        pairs = (("butcher.s3d", "objects.wld"),
                 ("butcher_obj.s3d", "butcher_obj.wld"),
                 ("butcher_2_obj.s3d", "butcher_2_obj.wld"))
        if any(not (asset_root / source).resolve().is_relative_to(DATA_ROOT.resolve())
               for source, _ in pairs):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        wlds = tuple(WLDInventory(PFSArchive(asset_root / source).read_member(member))
                     for source, member in pairs)
        summary = summarize_instances(wlds[0], wlds[1:])
        print(json.dumps({"wld_sha256": {member: wld.sha256
                                         for (_, member), wld in zip(pairs, wlds)},
                          **asdict(summary)}, indent=2))
    elif args.build_butcher_candidate_scene:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        pairs = (("butcher.s3d", "butcher.wld"),
                 ("butcher.s3d", "objects.wld"),
                 ("butcher_obj.s3d", "butcher_obj.wld"),
                 ("butcher_2_obj.s3d", "butcher_2_obj.wld"))
        if any(not (asset_root / source).resolve().is_relative_to(DATA_ROOT.resolve())
               for source, _ in pairs):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        archives = {source: PFSArchive(asset_root / source) for source, _ in pairs}
        wlds = tuple(WLDInventory(archives[source].read_member(member))
                     for source, member in pairs)
        destination = DATA_ROOT / "nav-candidates"
        if not destination.resolve().is_relative_to(DATA_ROOT.resolve()):
            parser.error("Candidate scene destination must stay inside the approved EQL data store")
        scene = write_candidate_scene(destination, wlds[0], wlds[1], wlds[2:])
        print(json.dumps({"archive_sha256": {name: archive.sha256
                                              for name, archive in archives.items()},
                          "wld_sha256": {member: wld.sha256
                                         for (_, member), wld in zip(pairs, wlds)},
                          **asdict(scene)}, indent=2))
    elif args.audit_butcher_materials:
        asset_root = DATA_ROOT / "client-data" / "retail-full" / "assets"
        pairs = (("butcher.s3d", "butcher.wld"),
                 ("butcher.s3d", "objects.wld"),
                 ("butcher_obj.s3d", "butcher_obj.wld"),
                 ("butcher_2_obj.s3d", "butcher_2_obj.wld"))
        if any(not (asset_root / source).resolve().is_relative_to(DATA_ROOT.resolve())
               for source, _ in pairs):
            parser.error("Butcherblock source must stay inside the approved EQL data store")
        archives = {source: PFSArchive(asset_root / source) for source, _ in pairs}
        wlds = tuple(WLDInventory(archives[source].read_member(member))
                     for source, member in pairs)
        summary = summarize_butcher_materials(wlds[0], wlds[1], wlds[2:])
        print(json.dumps({"wld_sha256": {member: wld.sha256
                                         for (_, member), wld in zip(pairs, wlds)},
                          **summary}, indent=2))
    else:
        shell()


if __name__ == "__main__":
    main()
