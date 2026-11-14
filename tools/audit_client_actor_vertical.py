#!/usr/bin/env python3
"""Reproduce the retained client's location/vertical-query provenance.

Reads pinned files and disassembles bounded spans; never loads client code.
This is an evidence report, not a character-height calibration or route gate.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
from struct import unpack_from
import subprocess

STORE = Path.home()/'.local/share/eql-automation'
EXE = STORE/'client-data/runtime-20261114T0503Z/eqgame.exe'
STRINGS = STORE/'client-data/location-resource-20261114T101437Z/eqstr_us.txt'
EXE_SHA = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
STRINGS_SHA = '0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde'
SPANS = {
    'location_handler': (0x24d280, 0x24d3e3),
    'base_constructor_binding': (0x331a60, 0x331a82),
    'derived_constructor_binding': (0x3141c0, 0x314201),
    'movement_clamp': (0x275e2b, 0x275e57),
    'ground_value_assignment': (0x2762f0, 0x276380),
    'downward_query': (0x276d80, 0x277010),
    'clamp_offset_getter': (0x277010, 0x277117),
    'separate_extent_getter': (0x277120, 0x277191),
    'lower_region_sample': (0x277e50, 0x27816f),
    'query_constructor': (0xe7c60, 0xe7d52),
    'query_dispatch_and_outputs': (0x194700, 0x1948a9),
    'query_point_output': (0x5c39c0, 0x5c3a86),
    'query_vector_normalization': (0xf5460, 0xf5524),
    'query_collision_candidate': (0x5c3850, 0x5c39b5),
    'query_validity': (0x5c3b10, 0x5c3b3f),
    'collision_solver': (0x5c5790, 0x5c641a),
}
CONSTANTS = {
    'query_size_factor': 0x8a42f0,
    'ground_result_addend': 0x938544,
    'minimum_clamp_offset': 0x938590,
    'downward_end_z': 0x9386cc,
    'lower_region_addend': 0x910d70,
    'failure_sentinel': 0x8e7414,
    'query_output_retraction': 0xb69814,
    'other_kind_factor': 0x8e93f8,
    'kinds_2_9_10_factor': 0x8d7c80,
    'normalization_epsilon': 0x8e73c4,
}


def inspect(exe=EXE, strings=STRINGS):
    raw, resource = exe.read_bytes(), strings.read_bytes()
    if sha256(raw).hexdigest() != EXE_SHA:
        raise ValueError('Executable differs from the inspected owner copy')
    if sha256(resource).hexdigest() != STRINGS_SHA:
        raise ValueError('Location resource differs from the inspected owner copy')
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
        raise ValueError('Unbacked source RVA')

    messages = [line for line in resource.decode('cp1252').splitlines()
                if line.startswith('13177 ')]
    if messages != ['13177 Your Location is %1, %2, %3']:
        raise ValueError('Location output order has changed')
    bindings = {}
    for table in (0x9c4558, 0x9cc468):
        target = unpack_from('<Q', raw, offset(table+0x128))[0]
        if target != base+0x277010:
            raise ValueError('Changed constructor-bound offset getter')
        bindings[hex(base+table)] = dict(slot='0x128', target=hex(target))
    command = unpack_from('<QQ', raw, offset(0xde9bc0))
    if command != (base+0x969780, base+0x24d280):
        raise ValueError('Changed location command binding')
    if raw[offset(0x96d75c):offset(0x96d75c)+6] != b'%1.2f\0':
        raise ValueError('Changed coordinate format')
    record = dict(format='eql-client-actor-vertical-static-v1',
        executable=dict(path=str(exe), sha256=EXE_SHA, image_base=hex(base)),
        location_resource=dict(path=str(strings), sha256=STRINGS_SHA,
            message_id=13177, coordinate_actor_offsets=['0x74','0x78','0x7c'],
            coordinate_format='%1.2f', height_adjustment_in_output=False),
        constructor_bound_vtables=bindings,
        constants={name:dict(va=hex(base+rva),
            float32=unpack_from('<f', raw, offset(rva))[0],
            bytes_hex=raw[offset(rva):offset(rva)+4].hex())
            for name,rva in CONSTANTS.items()}, spans={},
        verified_static_relations={
            'movement_clamp': 'if actor+38 > actorZ-offset: actorZ=actor+38+offset',
            'offset': '277010 state-dependent value; not field158 or field164 directly',
            'offset_state_exclusions': 'state281 in {0x6f,0x78}, stateb6>=5 or virtual+a0 true gives zero',
            'offset_kinds_2_9_10': 'max(binary32 1.9, binary32 field158*0.5)',
            'offset_other_kinds': '1.9 for finite field158; native negative branch multiplies by 0.75 first',
            'offset_subobject': 'if positive, object12c8 exists and predicate+a0 false, max with its virtual+88 result',
            'query_size_r': 'binary32 field158*0.1; exact zero replaced by binary32 0.1; query stores r, r*r and 1/r',
            'downward_query': 'same first two coordinates; end third coordinate -32767',
            'query_point_output': 'start if length(t*delta)<=0.002; otherwise start+normalized(t*delta)*max(0,length-0.002)',
            'timed_face_branch': 'with start C, direction V, runtime vector U: D=V-U; S=C+/-r*N; solver point P=(S+t*D)+t*U',
            'zero_relative_motion_overlap': 'can return t=0, mode=1, P=C; not universally a radius-offset point',
            'post_query_value': 'binary32 outputZ-r, then +0.062',
            'assignment': '2762f0 stores 276d80 return in actor+38, including failure sentinel',
            'separate_region_point': 'inputZ + (0.25 - branch-dependent extent difference)',
        },
        limitations=[
            'Static instructions, not a native execution observation.',
            'Relations are descriptive; separate binary32 operations must retain their rounding order.',
            'Actual active actor vtable, fields and state are unobserved.',
            'Cache, Scene predicate, callbacks and global thresholds affect query outcome.',
            'Runtime vector at 0x140fe6c28 and non-face solver branches remain unbound.',
            'Point output and collision geometry must not be replaced by a universal floor offset.',
            'No body dimensions, step capability, dynamic doors or motion bounds established.',
            'No missing-BSP-child or dry-space policy changed.',
        ], native_executed=False, game_input_sent=False,
        live_actor_dimensions_verified=False, route_accepted=False,
        real_client_accepted=False)
    for name, (start, end) in SPANS.items():
        record['spans'][name] = dict(start=hex(base+start), end_exclusive=hex(base+end),
            file_offset=offset(start), byte_count=end-start,
            source_span_sha256=sha256(raw[offset(start):offset(end-1)+1]).hexdigest())
    return record


def run(exe, strings, output):
    record = inspect(exe, strings)
    output = output.resolve()
    if not output.is_relative_to((STORE/'client-data').resolve()):
        raise ValueError('Keep native evidence in the approved private data store')
    output.mkdir(parents=True, exist_ok=False)
    for name, span in record['spans'].items():
        command = ['objdump', '-d', '-M', 'intel',
                   '--start-address='+span['start'],
                   '--stop-address='+span['end_exclusive'], str(exe)]
        result = subprocess.run(command, check=True, capture_output=True, timeout=10)
        (output/(name+'.txt')).write_bytes(result.stdout)
        span.update(disassembly_sha256=sha256(result.stdout).hexdigest(), command=command)
    # Reject a replacement while objdump was reading the file.
    if sha256(exe.read_bytes()).hexdigest() != EXE_SHA:
        raise ValueError('Executable changed during inspection')
    destination = output/'probe.json'
    destination.write_text(json.dumps(record, indent=2)+'\n')
    return dict(path=str(destination), sha256=sha256(destination.read_bytes()).hexdigest(),
                spans=len(SPANS), location_order_verified=True, route_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--strings', type=Path, default=STRINGS)
    parser.add_argument('--output', type=Path, default=STORE/'client-data'/(
        'native-actor-vertical-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args = parser.parse_args()
    print(json.dumps(run(args.exe, args.strings, args.output), indent=2))
