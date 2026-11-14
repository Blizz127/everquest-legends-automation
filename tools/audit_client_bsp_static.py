#!/usr/bin/env python3
"""Reproduce bounded static evidence from the owner's retained graphics DLL.

Only reads the PE and runs objdump; it never loads or executes client code.
Disassembly is private client data and goes into the approved local data store.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
from struct import iter_unpack, unpack_from
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.client_bsp_probe import ENGINE_SHA256, QUERY_RVA

STORE = Path.home()/'.local/share/eql-automation'
DLL = STORE/'client-data/font-runtime-20261114T0706Z/EQGraphics.dll'
SPANS = {
    'wld_reader': (0x2bf3a0, 0x2bf6f6),
    'world_conversion': (0x2c03f0, 0x2c0856),
    'tree_expansion': (0x2c0860, 0x2c0b4f),
    'tree_assignment': (0x2bc750, 0x2bc7ef),
    'point_query': (QUERY_RVA, 0x2bc719),
    'type_copy': (0x2ba670, 0x2ba770),
    'region_type_map': (0x2bcce0, 0x2bcda0),
    'label_query': (0x2bc510, 0x2bc5ce),
    'nine_point_query': (0x2bd290, 0x2bd5d5),
    'scene_default_query': (0xf78c0, 0xf796f),
    'scene_zero_query': (0xf8c40, 0xf8e4f),
}


def run(dll, output):
    raw = dll.read_bytes()
    if sha256(raw).hexdigest() != ENGINE_SHA256:
        raise ValueError('Graphics DLL differs from the inspected owner copy')
    pe = unpack_from('<I', raw, 0x3c)[0]
    optional = pe + 24
    base = unpack_from('<Q', raw, optional + 24)[0]
    count = unpack_from('<H', raw, pe + 6)[0]
    size = unpack_from('<H', raw, pe + 20)[0]
    sections = [unpack_from('<8sIIIIIIHHI', raw, optional+size+40*i)
                for i in range(count)]

    def offset(rva):
        for section in sections:
            if section[2] <= rva < section[2] + section[3]:
                return section[4] + rva - section[2]
        raise ValueError(f'RVA {rva:x} is not file backed')

    output = output.resolve()
    if not output.is_relative_to((STORE/'client-data').resolve()):
        raise ValueError('Keep client disassembly in the approved private data store')
    output.mkdir(parents=True, exist_ok=False)
    record = dict(format='eql-client-bsp-static-v1', source=str(dll),
                  source_sha256=ENGINE_SHA256, image_base=hex(base), spans={},
                  native_executed=False, real_client_accepted=False,
                  route_accepted=False, game_input_sent=False)
    for name, (start, end) in SPANS.items():
        command = ['objdump', '-d', '-M', 'intel',
                   f'--start-address={base+start:#x}',
                   f'--stop-address={base+end:#x}', str(dll)]
        result = subprocess.run(command, check=True, capture_output=True, timeout=10)
        (output/(name+'.txt')).write_bytes(result.stdout)
        record['spans'][name] = dict(start=hex(base+start), end_exclusive=hex(base+end),
            source_span_sha256=sha256(raw[offset(start):offset(end-1)+1]).hexdigest(),
            disassembly_sha256=sha256(result.stdout).hexdigest(), command=command)
    exception_rva, exception_size = unpack_from('<II', raw, optional+112+3*8)
    pdata = raw[offset(exception_rva):offset(exception_rva)+exception_size]
    record['conversion_unwind_ranges'] = []
    for start, end, unwind in iter_unpack('<III', pdata):
        if 0x2c03f0 <= start < 0x2c0856:
            version_flags, _, codes, _ = unpack_from('<4B', raw, offset(unwind))
            flags = version_flags >> 3
            chain = (unpack_from('<III', raw, offset(unwind)+((4+codes*2+3)&~3))
                     if flags & 4 else ())
            record['conversion_unwind_ranges'].append(dict(
                start=hex(base+start), end_exclusive=hex(base+end), flags=flags,
                chained_runtime_function=[hex(value) for value in chain]))
    record['bounds_margin'] = dict(va=hex(base+0x372874),
                                  float32=unpack_from('<f', raw, offset(0x372874))[0])
    record['verified_static_behavior'] = dict(
        native_bounds_gate='strict interior of runtime bounds expanded by 2000 float32',
        null_root_inside_bounds=1, missing_child=-1, region_return='nonzero reference minus one',
        zero_plane_child='first child (+0x10)',
        scalar_order='float32 y*ny + x*nx, then z*nz, then split; separate MULSS/ADDSS',
        query_minus_one_label='NULL; not a classified dry label',
        scene_null_label_fallback='caller default or unclassified zero, wrapper dependent',
        upstream_position_height='unresolved', live_mxcsr='unverified')
    destination = output/'probe.json'
    destination.write_text(json.dumps(record, indent=2)+'\n')
    return dict(path=str(destination), sha256=sha256(destination.read_bytes()).hexdigest(),
                source_sha256=ENGINE_SHA256, spans=len(SPANS), native_executed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, default=DLL)
    parser.add_argument('--output', type=Path, default=STORE/'client-data'/(
        'bsp-native-query-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args = parser.parse_args()
    print(json.dumps(run(args.dll, args.output), indent=2))
