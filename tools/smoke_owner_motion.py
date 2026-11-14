#!/usr/bin/env python3
"""Exercise a pinned owner preview with synthetic logs and pipe-only input.

Never creates a virtual input device, opens a game window or reads game data.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stop',choices=('none','motion-down','final-pair'),default='none')
    args=parser.parse_args()
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(args.preview.resolve()))
    import owner_nov12_entry
    owner_nov12_entry.verify_snapshot(args.preview)
    os.chdir(args.preview.resolve())
    import rotation_engine,rotation_core
    from eql_automation.owner_supervised_motion import make_owner_nov12_engine,MOTION_JOB
    from eql_automation.owner_location_hotkey_test import HOTKEY_TEST_JOB
    from eql_automation.owner_input_observer import OwnerInputObservation
    from eql_automation.supervised_motion import SupervisedMotionExecutors
    from eql_automation import uinput_watchdog as watchdog
    if args.output.resolve().is_relative_to((Path.home()/'Games/everquest-legends').resolve()):
        raise ValueError('Output must be outside protected prefix')
    with tempfile.TemporaryDirectory(prefix='eql-motion-pipe-smoke-') as temporary:
        root=Path(temporary);game=root/'fixture';(game/'Logs').mkdir(parents=True)
        log=game/'Logs/eqlog_Probe_private.txt';log.touch()
        for name in ('eqclient.ini','Probe_private_LO1.ini'):(game/name).write_text('synthetic fixture\n')
        class Observer:
            def __init__(self,**kw):pass
            def sample(self):
                driver=e.motion_collection_driver
                if args.stop=='final-pair' and driver and len(driver.session.receipts)==7:
                    raise ValueError('synthetic physical input before final pair')
                now=time.monotonic()
                return OwnerInputObservation(now,now,1,True,1,0,False,0,'synthetic owner input')
            def close(self):pass
        e=make_owner_nov12_engine(rotation_engine.Engine,observer_factory=Observer,
            output_root=root/'motion',hotkey_output=root/'hotkey')(
            rotation_core.Settings(game_dir=str(game),character='Probe',server='private'),
            lambda *_:None,lambda *_:None,measurement_only=True)
        e.selector.close()
        win=SimpleNamespace(id=42)
        e.gate=SimpleNamespace(windows=lambda:[win],focused_window=lambda:win,
            game_session=lambda:dict(pid=10,start_ticks='100'),focused=lambda:True,controls_ready=lambda:True)
        e.trace=lambda *_a,**_kw:None;e.emit=lambda *_:None
        e.input_events=e.read_log=lambda:None;e.blocked_keys=lambda:False
        rd,wr=os.pipe()
        class Pipe:
            def fileno(self):return wr
            def write(self,kind,code,value):os.write(wr,watchdog._EVENT.pack(0,0,kind,code,value))
            def syn(self):self.write(0,0,0)
        sender=rotation_engine.KeySender.__new__(rotation_engine.KeySender)
        sender.ui=Pipe();sender.codes=SimpleNamespace(EV_KEY=1,KEY_UP=103,KEY_LEFT=105,KEY_RIGHT=106)
        sender.held=set();sender.unfinished=sender.dismissed=False
        sender.gate=e.gate;sender.allowed=e.allowed
        def ensure():e.sender=sender;return sender
        e.ensure_sender=ensure
        def forbidden(*a,**kw):raise AssertionError('Unexpected input/capture method')
        e.send=e.hold=e.ensure_pointer=forbidden
        point=[0.,0.,0.];heading=[350.];events=[]
        original_status=watchdog._read_status
        def status(*a,**kw):
            value=original_status(*a,**kw)
            if value=='DOWN':
                driver=e.motion_collection_driver
                if driver is None or driver.session.phase=='requesting':
                    with log.open('a') as out:
                        out.write(datetime.now().strftime('[%a %b %d %H:%M:%S %Y] ')+
                            'Your Location is '+', '.join(f'{v:.2f}' for v in point)+'\n')
                elif args.stop=='motion-down':e.stop_action('synthetic F9 during motion DOWN')
            return value
        watchdog._read_status=status
        original_pulse=SupervisedMotionExecutors.run_pulse
        def pulse(self,request):
            result=original_pulse(self,request);r=result.receipt
            held=((r.up_started_at-r.down_completed_at)+r.maximum_held_seconds)/2
            if request.probe.key=='forward':
                rad=math.radians(heading[0]);point[0]+=math.cos(rad)*30*held;point[1]+=math.sin(rad)*30*held
            else:heading[0]=(heading[0]+(-1 if request.probe.key=='right' else 1)*170*max(0.,held-.03))%360
            return result
        SupervisedMotionExecutors.run_pulse=pulse
        def tick():
            e.autopilot_tick(time.monotonic())
            os.set_blocking(rd,False)
            try:events.extend(row[2:] for row in watchdog._EVENT.iter_unpack(os.read(rd,65536)))
            except BlockingIOError:pass
        def job(name,value):e.post(name,value);e.handle_job(*e.jobs.get_nowait())
        try:
            job(HOTKEY_TEST_JOB,dict(key_name='F4',confirmed=True));assert e.hotkey_test
            e.hotkey_test['due']=time.monotonic()-.001
            until=time.monotonic()+5
            while e.hotkey_test and time.monotonic()<until:tick();time.sleep(.01)
            assert e.last_hotkey_test and e.last_hotkey_test['outcome']=='observed_location', e.last_hotkey_test
            job(MOTION_JOB,dict(open_flat_clear=True));assert e.supervised_motion
            e.supervised_motion['due']=time.monotonic()-.001
            until=time.monotonic()+20
            while e.supervised_motion and time.monotonic()<until:tick();time.sleep(.01)
            record=e.last_motion_collection_result
            assert e.supervised_motion is None and record is not None
            downs=[code for kind,code,value in events if kind==1 and value==1]
            released=all((1,code,0) in events for code in set(downs)) and not sender.held
            result=dict(format='eql-owner-motion-pipe-smoke-v1',stop=args.stop,
                synthetic_positions=True,synthetic_owner_input=True,game_input_sent=False,
                outcome=record['outcome'],reason=record['reason'],receipt_count=len(record['receipts']),
                position_count=len(record['raw_fixes']),downs=downs,all_released=released,
                finished_stopped=e.cancelled,record=record)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
            assert released and e.cancelled
            if args.stop=='none':assert record['outcome']=='complete' and len(record['receipts'])==7,record['reason']
            else:
                assert record['outcome']=='stopped' and record['estimate'] is None
                assert (len(record['receipts'])==7 if args.stop=='final-pair' else 103 in downs)
            print(json.dumps({k:v for k,v in result.items() if k!='record'}))
        finally:
            e._cancel_motion('smoke teardown');e._finish_motion('smoke teardown');e._close_supervised('smoke teardown')
            watchdog._read_status=original_status;SupervisedMotionExecutors.run_pulse=original_pulse
            os.close(wr);os.close(rd)


if __name__=='__main__':main()
