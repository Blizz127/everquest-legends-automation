#!/usr/bin/env python3
"""Reproduce current-zone label dispatch from pinned owner client copies.

Static evidence only: no process attachment, native execution, UI capture or
input. A hidden/unupdated label and the XML-to-runtime adapter link still need
runtime validation before this source can bind a route's current zone.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
from struct import unpack_from
import subprocess
import xml.etree.ElementTree as ET

STORE = Path.home()/'.local/share/eql-automation'
EXE = STORE/'client-data/runtime-20261114T0503Z/eqgame.exe'
XML = STORE/'client-data/ui-scene-20261114T045729Z/EQUI_MapViewWnd.xml'
EXE_SHA = 'fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
XML_SHA = '6bcdcc7b20c6510c5797e044ab3193b8a7fa2386dc87e8d770b5387346fe6419'
SPANS = {
    'dispatch': (0x540243, 0x540271, 'd6153e5df08364b792ef5a7009b5bf44af2bd78142429bc6acdff4e5bbe93019'),
    'selectors_1018_1023': (0x548d6d, 0x548d73, '03414590b23d00b8df9b71a4037ad44b310fcd3de38ba24a4313f9f3c5b75d07'),
    'destinations_1018_1023': (0x548920, 0x548938, '276d52703ff493680f2eece0bd88ce88ee4d10dcbcfaac4c6e00896efe3d02c6'),
    'type_1020_actor_zone': (0x547e32, 0x547e82, '26dfa7d629ecda78a45d7c2f545cfae53a67c9cd68ec927f5e4de9c66045248e'),
    'types_1021_1023_actor_coordinates': (0x547e82, 0x547eee, '43aaae859a4224288db94d7fb06343ec2daffb5357cc0b9353d071bdae5a75ff'),
    'location_actor_coordinates': (0x24d280, 0x24d3e3, 'e519458ba5ac02a907fd13a20ee90f57453fa34fbd041ad0806128026916a7a3'),
    'label_update_caller': (0x467840, 0x4679ac, 'f2469b8006da6af5a86c7a94f889fcada580c0c6d8ee25735b5912c99c0b8dd2'),
    'adapter_update_caller': (0x3f23d0, 0x3f2489, '9f6e05dc286baf286c5ffbe65f1476680c693023858565b17c0c0e5e847b7363'),
    'zone_name_lookup': (0x6ec290, 0x6ec389, '9b19f0c3e04bffda8c6e53ceb6daaaef9f05d31ffaa434e6d87d380a3ff7e8fe'),
}


def inspect(exe=EXE, xml=XML):
    raw, ui = exe.read_bytes(), xml.read_bytes()
    if sha256(raw).hexdigest() != EXE_SHA or sha256(ui).hexdigest() != XML_SHA:
        raise ValueError('Current-zone source differs from inspected owner copies')
    pe = unpack_from('<I', raw, 0x3c)[0]; opt = pe+24
    base = unpack_from('<Q', raw, opt+24)[0]
    count, size = unpack_from('<H', raw, pe+6)[0], unpack_from('<H', raw, pe+20)[0]
    sections = [unpack_from('<8sIIIIIIHHI', raw, opt+size+i*40) for i in range(count)]
    def offset(rva):
        for section in sections:
            if section[2] <= rva < section[2]+section[3]:
                return section[4]+rva-section[2]
        raise ValueError('Unbacked source RVA')
    root = ET.fromstring(ui)
    for name, kind in (('MRA_ZoneLabel',1020), ('MRA_LocXCoords',1021),
                       ('MRA_LocYCoords',1022), ('MRA_LocZCoords',1023)):
        labels = root.findall(".//Label[@item='"+name+"']")
        if len(labels) != 1 or labels[0].findtext('EQType') != str(kind):
            raise ValueError('Map label EQType changed: '+name)
    for address, expected in ((0xb28084,b'%.0f\0'),(0x96d75c,b'%1.2f\0')):
        if raw[offset(address):offset(address)+len(expected)] != expected:
            raise ValueError('Actor coordinate formatting changed')
    bindings = []
    for kind, expected in zip(range(1018, 1024),
                              (0x547d73, 0x547dca, 0x547e32, 0x547e82, 0x547eba, 0x547ed4)):
        selector = raw[offset(0x548974+kind-1)]
        target = unpack_from('<I', raw, offset(0x5485f4+4*selector))[0]
        if target != expected or selector != kind-815:
            raise ValueError('Changed adjacent native EQType dispatch')
        bindings.append(dict(eqtype=kind, selector=selector, destination=hex(base+target)))
    spans = {}
    for name, (start, end, pin) in SPANS.items():
        source = raw[offset(start):offset(start)+end-start]
        if sha256(source).hexdigest() != pin:
            raise ValueError('Changed native span: '+name)
        row = dict(start=hex(base+start), end_exclusive=hex(base+end), source_sha256=pin)
        if name not in ('selectors_1018_1023', 'destinations_1018_1023'):
            row['disassembly'] = subprocess.check_output(['objdump', '-d', '-M', 'intel',
                '--start-address='+hex(base+start), '--stop-address='+hex(base+end), str(exe)], text=True)
        spans[name] = row
    return dict(format='eql-current-zone-label-static-v1', observed_at_utc=datetime.now(timezone.utc).isoformat(),
        executable=dict(path=str(exe), sha256=EXE_SHA), xml=dict(path=str(xml), sha256=XML_SHA),
        label='MRA_ZoneLabel', eqtype=1020, dispatch=bindings, source_spans=spans,
        native_type_1020_source='actor global 0x140f3a808, field +0x1ec; zone catalog 0x140f3a7c8',
        selected_map_field_used_by_type_1020=False,
        coordinate_fields=['actor+0x74','actor+0x78','actor+0x7c'],
        map_coordinate_format='%.0f', location_coordinate_format='%1.2f',
        map_coordinate_order='X label = first raw location; Y label = second; Z label = third',
        coordinate_format_difference_bound=.505,
        null_behavior='missing actor/catalog leaves initialized empty output',
        invalid_zone_behavior='zone lookup initializes Unknown Zone',
        instance_suffix='lookup can append space plus integer for flagged zone metadata',
        xml_to_runtime_adapter_link_complete=False, runtime_label_refresh_verified=False,
        native_executed=False, game_input_sent=False, current_zone_observed=False,
        route_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    path = parser.parse_args().output
    if path.exists() or path.is_symlink() or not path.resolve().is_relative_to((STORE/'client-data').resolve()):
        raise ValueError('Choose a new private client-data output')
    record = inspect()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out: json.dump(record, out, indent=2); out.write('\n')
    print(json.dumps(dict(path=str(path), sha256=sha256(path.read_bytes()).hexdigest(),
                         eqtype=1020, native_source='current_actor_zone', current_zone_observed=False)))
