#!/usr/bin/env python3
"""Build retained assist, itineraries and explicit early-camp progression."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path

from build_nov12_preview_03926 import build


def _record_itinerary_mode(output):
    """Update only descriptive metadata after verifying the new snapshot."""
    manifest = output / 'SOURCE_HASHES.json'
    raw = manifest.read_bytes()
    pins = json.loads(raw)
    info = output / 'BUILD_INFO.json'
    record = json.loads(info.read_bytes())
    if (record['source_manifest_sha256'] != sha256(raw).hexdigest()
            or record['preview_hashes'] != pins
            or record['entry_sha256'] != sha256((output / 'owner_nov12_entry.py').read_bytes()).hexdigest()):
        raise ValueError('New preview metadata differs from its sealed snapshot')
    for name, expected in pins.items():
        relative = Path(name)
        path = output / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError('New preview source changed: ' + name)
    tree = ast.parse((output / 'eql_automation/__init__.py').read_text())
    versions = [ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == '__version__'
                        for target in node.targets)]
    if len(versions) != 1 or type(versions[0]) is not str or not versions[0]:
        raise ValueError('Copied runtime must declare one source version')
    # BUILD_INFO is descriptive metadata, excluded from SOURCE_HASHES by the
    # shared builder. Runtime, manifest and entry hashes remain unchanged.
    record.update(source_version=versions[0], real_itinerary_acceptance=False, real_terminal_camp_acceptance=False, real_camp_progression_acceptance=False,
        mode='F8 owner-targeted assist; explicit single-destination travel/camp choices; '
             'separate supervised Butcherblock → Greater Faydark → Clan Crushbone itinerary, then stop without camping; '
             'separate supervised itinerary to Slave Mines with fresh spell preparation and stationary camping, stops at observed level 20; '
             'separate explicit Newbie Hills → Goblin Camp → Greater Faydark → Crushbone → Slave Mines progression; '
             'configured level 1–4 admission, observed level departures, terminal camp stops at observed level 20; '
             'no automatic relocation after Slave Mines; F11 stationary camp/off or travel stop; F9 OFF; no loot input')
    info.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.45',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',
            'nov12-7e3cd28-stair-landing-test.patch','nov12-7e3cd28-throne-contact-test.patch',
            'nov12-7e3cd28-butcher-newbie-test.patch','nov12-7e3cd28-butcher-goblin-test.patch',
            'nov12-7e3cd28-goblin-sections.patch','nov12-7e3cd28-camp-progress.patch',
            'nov12-7e3cd28-gfay-crossing-destinations.patch',
            'nov12-7e3cd28-zone-itinerary.patch',
            'nov12-7e3cd28-zone-itinerary-terminal-camp.patch',
            'nov12-7e3cd28-camp-progression.patch'),
        entry_name='owner_nov12_entry_03945.py',
        change='Adds a distinct supervised early-camp progression from Newbie Hills through Goblin Camp and both zone crossings to Slave Mines; configured integer level 1–4 is required to start, fresh observed levels control departures, and final stationary camping stops at observed level 20 without later relocation; the 6h15 cap covers Goblin-onward navigation only; existing itinerary and ordinary controls preserved; actual routes, camp suitability, level gains and 1-50 automation remain unverified')
    _record_itinerary_mode(args.output)
    print(args.output)
