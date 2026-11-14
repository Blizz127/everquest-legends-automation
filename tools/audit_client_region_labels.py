#!/usr/bin/env python3
"""Retain installed classifier/actor-query evidence and copied zone flag maps.

No client execution or input. Disassembly and client-derived inventories stay
in the private data store, separate from code and documentation.
"""
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
from struct import unpack_from
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.client_bsp_probe import ENGINE_SHA256
from eql_automation.client_region_labels import CLIENT_SHA256, ClientRegionMap, decode_client_region_label
from eql_automation.pfs_archive import PFSArchive
from eql_automation.wld_inventory import WLDInventory

STORE = Path.home()/'.local/share/eql-automation'
EXE = STORE/'client-data/runtime-20261114T0503Z/eqgame.exe'
DLL = STORE/'client-data/font-runtime-20261114T0706Z/EQGraphics.dll'
SPANS = {
    EXE: (CLIENT_SHA256, {
        'callback_registration': (0x1b2056,0x1b206a),
        'callback': (0x1c3170,0x1c34a2),
        'prefix_compare': (0x75e960,0x75e9dd),
        'query_default_wrapper': (0x1b0ba0,0x1b0bd2),
        'actor_query_update': (0x277980,0x277b86),
        'actor_lower_query': (0x277e50,0x27816f),
        'region_sound_state': (0x336d30,0x336ddd),
        'unnamed_offset_getter': (0x277720,0x277729),
    }),
    DLL: (ENGINE_SHA256, {
        'scene_callback_setter': (0xf8e50,0xf8e79),
        'callback_field_store': (0x2ba360,0x2ba365),
    }),
}
WLD_PINS = {
    'butcher':'d4c8db248f4b7d23fe714ff3dceedaf0c83696b178327efcf88d6091e35c722c',
    'crushbone':'ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1',
    'gfaydark':'3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138',
}


def run(output):
    output = output.resolve()
    if not output.is_relative_to((STORE/'client-data').resolve()):
        raise ValueError('Keep copied client evidence in the private data store')
    output.mkdir(parents=True, exist_ok=False)
    result = dict(format='eql-client-region-classification-v1', binaries={}, zones={},
        code_sha256=sha256((PROJECT/'eql_automation/client_region_labels.py').read_bytes()).hexdigest(),
        native_executed=False, game_input_sent=False, input_authorized=False,
        route_accepted=False, real_client_accepted=False,
        numeric_zero_is_not_dry_evidence=True, live_actor_dimensions_verified=False)
    for binary, (expected, spans) in SPANS.items():
        raw = binary.read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError('Changed client binary: '+str(binary))
        pe = unpack_from('<I', raw, 0x3c)[0]; optional = pe + 24
        base = unpack_from('<Q', raw, optional + 24)[0]
        count = unpack_from('<H', raw, pe + 6)[0]
        size = unpack_from('<H', raw, pe + 20)[0]
        sections = [unpack_from('<8sIIIIIIHHI', raw, optional+size+i*40) for i in range(count)]

        def offset(rva):
            for section in sections:
                if section[2] <= rva < section[2] + section[3]:
                    return section[4] + rva - section[2]
            raise ValueError('Unbacked source RVA')

        data = dict(path=str(binary), sha256=expected, spans={})
        for name, (start, end) in spans.items():
            command = ['objdump','-d','-M','intel',f'--start-address={base+start:#x}',
                       f'--stop-address={base+end:#x}',str(binary)]
            text = subprocess.run(command, check=True, capture_output=True, timeout=10).stdout
            (output/(name+'.txt')).write_bytes(text)
            data['spans'][name] = dict(start=hex(base+start),end_exclusive=hex(base+end),
                source_span_sha256=sha256(raw[offset(start):offset(end-1)+1]).hexdigest(),
                disassembly_sha256=sha256(text).hexdigest(),command=command)
        if binary == EXE:
            data['lower_probe_constant'] = dict(va=hex(base+0x910d70),
                value=unpack_from('<f',raw,offset(0x910d70))[0])
            start = offset(0x936b50)
            data['transition_format'] = raw[start:raw.index(0,start)].decode('ascii')
        result['binaries'][binary.name] = data
    for zone, expected in WLD_PINS.items():
        archive = STORE/'client-data/retail-full/assets'/(zone+'.s3d')
        archive_hash = sha256(archive.read_bytes()).hexdigest()
        wld = WLDInventory(PFSArchive(archive).read_member(zone+'.wld'))
        if wld.sha256 != expected:
            raise ValueError('Changed source WLD: '+zone)
        mapping = ClientRegionMap(wld)
        records = [dict(fragment_index=index,label=label,region_ids=ids,
                        decoded=asdict(decode_client_region_label(label)))
                   for index,label,ids in mapping.records]
        mapped = Counter(mapping.flags_for_region(i).flags
                         for i,r in enumerate(mapping.region_to_record) if r != -1)
        result['zones'][zone] = dict(archive_sha256=archive_hash,wld_sha256=wld.sha256,
            region_count=len(mapping.region_to_record),records=records,
            region_to_record=mapping.region_to_record,overwrites=mapping.overwrites,
            mapped_flag_counts={hex(k):v for k,v in sorted(mapped.items())},
            unmapped_regions=sum(r == -1 for r in mapping.region_to_record),
            all_type_records_contiguous=True)
        if sha256(archive.read_bytes()).hexdigest() != archive_hash:
            raise ValueError('Archive changed during inspection')
    destination = output/'probe.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    return dict(path=str(destination),sha256=sha256(destination.read_bytes()).hexdigest(),
        zones={zone:{k:data[k] for k in ('region_count','mapped_flag_counts','unmapped_regions')}
               for zone,data in result['zones'].items()},route_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=STORE/'client-data'/(
        'native-region-flags-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args = parser.parse_args()
    print(json.dumps(run(args.output),indent=2))
