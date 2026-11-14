#!/usr/bin/env python3
"""Audit the copied client's movement composition without executing client code.

This records static dependencies, not a speed certification. A run-speed sample
does not bound the extra velocity/contribution fields or the clock callback.
Only the pinned owner copy is accepted; native output stays in the private store.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import subprocess

STORE = Path.home() / '.local/share/eql-automation'
EXE = STORE / 'client-data/runtime-20261114T0503Z/eqgame.exe'
EXE_SHA = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
BASE = 0x140000000
SPANS = {
    'actor_constructor_table': (0x3141c0, 0x314201),
    'embedded_motion_constructor': (0x3144ea, 0x314525),
    'motion_getter': (0x31ebb0, 0x31ebb8),
    'update_dispatch': (0x1bbde5, 0x1bbe44),
    'motion_update': (0x694a70, 0x694e09),
    'time_adapter': (0x3316a0, 0x331708),
    'time_callback': (0x694eb0, 0x694ec1),
    'heading_update': (0x6a0c00, 0x6a0c7a),
    'pitch_update': (0x6a0c80, 0x6a0cb5),
    'extra_horizontal_input': (0x3314c0, 0x3315f0),
    'input_vector': (0x6a09b0, 0x6a0bff),
    'residual_and_input_combination': (0x694ed0, 0x69500b),
    'additional_position_update': (0x331240, 0x331380),
    'external_vector_addition': (0x338b7a, 0x338caf),
    'collision_dispatch': (0x277980, 0x277b86),
}
TABLES = {
    'actor': (0x9c4558, {0xf0: 0x31ebb0}),
    'embedded_motion': (0x9c4498, {
        0x08: 0x694ed0, 0x10: 0x694a70, 0x18: 0x6a0c80,
        0x20: 0x6a09b0, 0x50: 0x3310d0, 0x60: 0x3314c0,
        0x78: 0x331240, 0x80: 0x3316a0,
    }),
}
CONSTANTS = {
    'tick_delta_multiplier': (0x8e73cc, 0.019999999552965164),
    'heading_wrap': (0x938660, 512.0),
    'pitch_minimum': (0x9386c4, -128.0),
    'pitch_maximum': (0x938628, 128.0),
    'extra_input_multiplier': (0x8d7c80, 0.5),
    'tiny_residual_threshold': (0x8e73c4, 2 ** -23),
}


def inspect(exe=EXE):
    """Return only facts tied to the exact file and explicitly scoped inferences."""
    raw = exe.read_bytes()
    if sha256(raw).hexdigest() != EXE_SHA:
        raise ValueError('Executable differs from the inspected owner copy')
    pe = unpack_from('<I', raw, 0x3c)[0]
    optional = pe + 24
    if unpack_from('<Q', raw, optional + 24)[0] != BASE:
        raise ValueError('Changed image base')
    section_start = optional + unpack_from('<H', raw, pe + 20)[0]
    sections = [unpack_from('<8sIIIIIIHHI', raw, section_start + 40 * i)
                for i in range(unpack_from('<H', raw, pe + 6)[0])]

    def source(rva, size):
        for section in sections:
            if section[2] <= rva and rva + size <= section[2] + section[3]:
                start = section[4] + rva - section[2]
                if start + size <= len(raw):
                    return start, raw[start:start + size]
        raise ValueError('Span is not wholly backed by one source section')

    bindings = {}
    for name, (table, slots) in TABLES.items():
        observed = {}
        for slot, target in slots.items():
            offset, payload = source(table + slot, 8)
            actual = unpack_from('<Q', payload)[0]
            if actual != BASE + target:
                raise ValueError('Changed movement dispatch binding')
            observed[hex(slot)] = dict(target=hex(actual), file_offset=offset,
                                      source_sha256=sha256(payload).hexdigest())
        bindings[name] = dict(table=hex(BASE + table), slots=observed)
    constants = {}
    for name, (rva, expected) in CONSTANTS.items():
        offset, payload = source(rva, 4)
        value = unpack_from('<f', payload)[0]
        if value != expected:
            raise ValueError('Changed movement constant')
        constants[name] = dict(va=hex(BASE + rva), file_offset=offset,
                               float32=value, source_sha256=sha256(payload).hexdigest())
    spans = {}
    for name, (start, end) in SPANS.items():
        offset, payload = source(start, end - start)
        spans[name] = dict(start=hex(BASE + start), end_exclusive=hex(BASE + end),
                           file_offset=offset, byte_count=len(payload),
                           source_sha256=sha256(payload).hexdigest())
    return dict(
        format='eql-client-motion-composition-static-v1',
        executable=dict(path=str(exe), sha256=EXE_SHA, image_base=hex(BASE)),
        tool='bounded objdump; not REA native-engine evidence',
        tables=bindings, constants=constants, spans=spans,
        observed_relations={
            'dispatch': 'actor virtual+f0 returns actor+21d8; embedded virtual+10 calls 694a70 before 277980 collision processing',
            'time': 'uint32 tick difference converted to float32 then multiplied by float32 0.02; embedded virtual+80 returns the integration factor',
            'time_dependency': '3316a0 forwards to 694eb0, then global object 140fe8e70 virtual+18; its implementation is unresolved here',
            'heading': 'actor+94 adds actor+a0 times integration factor then wraps with 512; the angle range does not cap turn rate',
            'pitch': 'actor+98 adds actor+9c times integration factor then clamps to [-128,128]',
            'input_vector': '6a09b0 consumes actor+8c and +94, adds projected terms to the existing vector; actor+90 and additional callbacks also affect it',
            'extra_input': '3314c0 conditionally uses actor+484 or +488 times 0.5 and optional runtime global 140f42ff0, then adds projected terms to the vector',
            'residual': '694ed0 scales existing actor+80/+84 velocities, zeroes tiny components, then adds the computed input vector',
            'integration': '694a70 multiplies the resulting actor+80/+84/+88 velocities by its integration factor and adds them to actor+74/+78/+7c',
            'post_integration': 'embedded virtual+78 calls 331240 after the position writes and before actor virtual+e8',
            'post_integration_amplitudes': '331240 uses embedded-state amplitudes +20 (vertical, multiplied by integration factor) and +1c (horizontal, no additional time-factor multiplication in this function); phase wrapping does not bound amplitude',
            'external_vector': '3388f0 can add separately projected scalar contributions to actor+80/+84/+88; inspected contribution span has no magnitude clamp',
        },
        inference={
            'status': 'INFERRED from the listed static spans, not execution',
            'normal_run_speed_alone_bounds_final_motion': False,
            'reason': 'Final position depends on pre-existing velocity, additional input/position terms and an unresolved clock callback, as well as the forward scalar.',
        },
        unknowns=[
            'Actual live actor/vtable, state and contribution-field values.',
            'Magnitude bounds and producers for forward scalar, residual velocity, extra horizontal input and post-integration position terms.',
            'Clock source units, effective time callback, scheduling/input-consumption latency and maximum integration factor.',
            'All callers, alternative vtables and other position writers including server corrections.',
            'Current forced movement, scene clearance, obstacles, active doors, combat and real route acceptance.',
        ],
        verified_speed_upper_bound=None, current_motion_verified=False,
        current_heading_verified=False, native_executed=False,
        game_input_sent=False, movement_authorized=False, real_client_accepted=False,
    )


def run(exe, output):
    record = inspect(exe)
    output = output.resolve()
    if not output.is_relative_to((STORE / 'client-data').resolve()):
        raise ValueError('Keep native evidence in the approved private data store')
    output.mkdir(parents=True, exist_ok=False)
    for name, span in record['spans'].items():
        command = ['objdump', '-d', '-M', 'intel',
                   '--start-address=' + span['start'],
                   '--stop-address=' + span['end_exclusive'], str(exe)]
        result = subprocess.run(command, check=True, capture_output=True, timeout=10)
        (output / (name + '.txt')).write_bytes(result.stdout)
        span.update(command=command, disassembly_sha256=sha256(result.stdout).hexdigest())
    if sha256(exe.read_bytes()).hexdigest() != EXE_SHA:
        raise ValueError('Executable changed during inspection')
    record['created_at'] = datetime.now(timezone.utc).isoformat()
    destination = output / 'probe.json'
    destination.write_text(json.dumps(record, indent=2) + '\n')
    return dict(path=str(destination), sha256=sha256(destination.read_bytes()).hexdigest(),
                spans=len(SPANS), verified_speed_upper_bound=None,
                movement_authorized=False, real_client_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--output', type=Path, default=STORE / 'client-data' / (
        'native-motion-update-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args = parser.parse_args()
    print(json.dumps(run(args.exe, args.output), indent=2))
