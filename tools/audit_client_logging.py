#!/usr/bin/env python3
"""Retain focused static logging evidence from the owner's pinned client copy.

Uses objdump, not a running client or process memory. Static call shapes do not
prove Linux/Wine descriptor lifetimes or uninterrupted runtime logging.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import subprocess

STORE = Path.home()/'.local/share/eql-automation'
EXE = STORE/'client-data/runtime-20261114T0503Z/eqgame.exe'
STRINGS = STORE/'client-data/location-resource-20261114T101437Z/eqstr_us.txt'
EXE_PIN = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
STRINGS_PIN = '0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde'
SPANS = {
    'log_command': (0x23ede0, 0x23f057, 'f30ac604d3e1d792c16b21db53faf99b3f9cfc2879fafdb33d70ff5d7ee26e97'),
    'chat_log_flag_check': (0x11f70f, 0x11f751, '719f368f91a0ff8c7365d9fa642cbab2625fcb4fcabedba99edab05e75f76c72'),
    'buffer_flush': (0x120612, 0x1206b3, 'df71b702921ade9d4f5c3685921102e93ed1f24962a01c40fd822adbac55a37d'),
    'open_wrapper': (0x761480, 0x76148b, 'ef8609534ba66c8abf441badd80ae23a01176abefa4849f1873efa2db5886487'),
    'initial_log_setting': (0x27dc0e, 0x27dc2d, 'c965636c62e58f93adcb907d8cec5f2e55fd18801291323cc2930da1dfd5ea5c'),
}


def inspect():
    raw, strings = EXE.read_bytes(), STRINGS.read_bytes()
    if sha256(raw).hexdigest() != EXE_PIN or sha256(strings).hexdigest() != STRINGS_PIN:
        raise ValueError('Logging source differs from inspected owner copies')
    pe = unpack_from('<I', raw, 0x3c)[0]; opt = pe+24
    base = unpack_from('<Q', raw, opt+24)[0]
    count, size = unpack_from('<H', raw, pe+6)[0], unpack_from('<H', raw, pe+20)[0]
    sections = [unpack_from('<8sIIIIIIHHI', raw, opt+size+i*40) for i in range(count)]
    def read_span(start, end):
        for section in sections:
            if section[2] <= start < end <= section[2]+section[3]:
                offset = section[4]+start-section[2]
                return raw[offset:offset+end-start]
        raise ValueError('Unbacked source span')
    messages = {}
    for line in strings.decode('latin-1').splitlines():
        key, sep, body = line.partition(' ')
        if sep and key in ('12096', '13221', '13222'):
            messages[key] = body
    if set(messages) != {'12096', '13221', '13222'}:
        raise ValueError('Logging notices missing from client catalog')
    spans = {}
    for name, (start, end, pin) in SPANS.items():
        if sha256(read_span(start, end)).hexdigest() != pin:
            raise ValueError('Changed native logging span: '+name)
        spans[name] = dict(start=hex(base+start), end_exclusive=hex(base+end), sha256=pin,
            disassembly=subprocess.check_output(['objdump', '-d', '-M', 'intel',
                '--start-address='+hex(base+start), '--stop-address='+hex(base+end), str(EXE)], text=True))
    assert read_span(0x8c47e8, 0x8c47ea) == b'a\0'
    return dict(format='eql-client-logging-static-v1',
        recorded_utc=datetime.now(timezone.utc).isoformat(),
        executable=dict(path=str(EXE), sha256=EXE_PIN),
        strings=dict(path=str(STRINGS), sha256=STRINGS_PIN, messages=messages),
        spans=spans, tool='objdump; not REA native-engine evidence',
        logging_flag='0x140f43518', filename_field='+0x194dc',
        flush_calls=['0x140761480', '0x140766c60', '0x140761194'],
        flush_mode='a',
        inferred_flush_behavior='open append stream, write buffered data, close stream in the same flush',
        descriptor_lifetime_runtime_verified=False, uninterrupted_logging_verified=False,
        old_zone_bootstrap_authorized=False, game_executed=False, game_input_sent=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    path = parser.parse_args().output
    if path.exists() or path.is_symlink() or not path.resolve().is_relative_to((STORE/'client-data').resolve()):
        parser.error('Choose a new private client-data output')
    record = inspect()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        json.dump(record, out, indent=2); out.write('\n')
    print(json.dumps(dict(path=str(path), sha256=sha256(path.read_bytes()).hexdigest(),
        messages=record['strings']['messages'], runtime_verified=False, game_input_sent=False)))
