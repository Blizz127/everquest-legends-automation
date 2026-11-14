#!/usr/bin/env python3
"""Retain bounded static posture-command evidence; never executes the client."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
import argparse
import json
import subprocess

STORE=Path.home()/'.local/share/eql-automation'
EXE=STORE/'client-data/runtime-20261114T0503Z/eqgame.exe'
STRINGS=STORE/'client-data/location-resource-20261114T101437Z/eqstr_us.txt'
EXE_PIN='fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'
STRINGS_PIN='0dd0117a23092cb195d0e62d6b03a49bf1aaf8dbfb843dd629e38ca950732fde'


def inspect():
    raw=EXE.read_bytes();catalog=STRINGS.read_bytes()
    assert sha256(raw).hexdigest()==EXE_PIN and sha256(catalog).hexdigest()==STRINGS_PIN
    pe=unpack_from('<I',raw,0x3c)[0];opt=pe+24
    base=unpack_from('<Q',raw,opt+24)[0]
    count,size=unpack_from('<H',raw,pe+6)[0],unpack_from('<H',raw,pe+20)[0]
    sections=[unpack_from('<8sIIIIIIHHI',raw,opt+size+i*40) for i in range(count)]
    def span(start,end):
        for section in sections:
            if section[2]<=start<end<=section[2]+section[3]:
                offset=section[4]+start-section[2]
                return raw[offset:offset+end-start]
        raise ValueError('Unbacked source span')
    registry=[]
    for text,entry,name,handler in (('/sit',0xdeb160,0x969e3c,0x250380),('/stand',0xdeb180,0x969e44,0x2503f0)):
        assert span(name,name+len(text)+1)==text.encode()+b'\0'
        assert unpack_from('<QQ',span(entry,entry+16))==(base+name,base+handler)
        registry.append(dict(command=text,entry=hex(base+entry),handler=hex(base+handler)))
    messages={}
    for line in catalog.decode('latin-1').splitlines():
        key,_,body=line.partition(' ')
        if key in {'12946','6517','9175','9176','12441'}:messages[key]=body
    assert messages['12946']=='off'
    spans={}
    for name,start,end in (('sit_handler',0x250380,0x2503e2),('stand_handler',0x2503f0,0x250417),
                           ('posture_toggle',0x2b28d0,0x2b29da)):
        spans[name]=dict(start=hex(base+start),end_exclusive=hex(base+end),sha256=sha256(span(start,end)).hexdigest(),
            disassembly=subprocess.check_output(['objdump','-d','-M','intel',
                '--start-address='+hex(base+start),'--stop-address='+hex(base+end),str(EXE)],text=True))
    assert sha256(EXE.read_bytes()).hexdigest()==EXE_PIN
    return dict(format='eql-posture-commands-static-v1',recorded_utc=datetime.now(timezone.utc).isoformat(),
        executable=dict(path=str(EXE),sha256=EXE_PIN),strings=dict(path=str(STRINGS),sha256=STRINGS_PIN,messages=messages),
        command_registry=registry,spans=spans,
        observed_control_flow='sit compares the first three argument characters with resource12946 off; non-off arguments reach the posture toggle; stand requests state0x64',
        inferred_semantics='sit on is a toggle, not an idempotent seated-state request; no retry from unknown posture',
        method='bounded objdump; REA native provider unavailable because its configured Java lacks JDK21',
        native_executed=False,game_input_sent=False,posture_observed=False,server_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((STORE/'client-data').resolve()):
        raise ValueError('Choose a new private client-data output')
    record=inspect();output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as out:json.dump(record,out,indent=2);out.write('\n')
    print(json.dumps(dict(path=str(output),sha256=sha256(output.read_bytes()).hexdigest(),registry=record['command_registry'],runtime_verified=False)))
