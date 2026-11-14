#!/usr/bin/env python3
"""Exercise the actual helper preflight with synthetic input observations only."""
from pathlib import Path
from types import SimpleNamespace


def main():
    from owner_nov12_entry import verify_snapshot
    verify_snapshot(Path(__file__).resolve().parent)
    from rotation_core import Settings
    from rotation_engine import Engine
    from eql_automation.owner_navigation_preflight import make_owner_nov12_engine,PREFLIGHT_JOB
    from eql_automation.owner_input_observer import OwnerInputObservation
    now=[100.];opened=[];traces=[]
    def forbidden(*args,**kwargs):raise AssertionError('Preflight attempted input, capture or sender creation')
    class Observer:
        def __init__(self,**kwargs):
            assert kwargs['helper_ui'] is None
            self.count=0;self.closed=False;opened.append(self)
        def sample(self):
            self.count+=1
            return OwnerInputObservation(now[0],now[0],1,self.count>1,2,0,False,0,
                                         'topology_changed' if self.count==1 else 'observed')
        def close(self):self.closed=True
    adapted=make_owner_nov12_engine(Engine,observer_factory=Observer,clock=lambda:now[0])
    e=adapted(Settings(),lambda _:None,lambda *_:None,measurement_only=True)
    e.trace_path=None;e.trace=lambda event,**values:traces.append((event,values))
    e.send=e.hold=e.ensure_sender=forbidden
    window=SimpleNamespace(id=42)
    e.gate=SimpleNamespace(windows=lambda:[window],game_session=lambda:{'pid':10,'start_ticks':'100'},
        focused_window=lambda:window,controls_ready=lambda:True,capture=forbidden)
    try:
        assert e.sender is None and not e.selector.get_map()
        e.post(PREFLIGHT_JOB);e.handle_job(*e.jobs.get_nowait())
        assert e.deferred is None and not opened
        now[0]+=4;e.autopilot_tick(now[0])
        now[0]+=.03;e.autopilot_tick(now[0])
        result=[v for name,v in traces if name=='nav_preflight_result'][-1]
        assert result['input_sample_clear'] and not result['movement_authorized']
        assert result['missing_providers'] and not result['game_input_sent']
        assert opened[-1].closed and e.sender is None
        e.post(PREFLIGHT_JOB);e.handle_job(*e.jobs.get_nowait());now[0]+=4;e.autopilot_tick(now[0])
        e.stop_autopilot('F11 fixture')
        assert opened[-1].closed and e.navigation_preflight is None
        e.measurement_only=False;e.post(PREFLIGHT_JOB);e.handle_job(*e.jobs.get_nowait())
        assert e.navigation_preflight is None and len(opened)==2
    finally:e.selector.close()
    print('PASS: actual Engine preflight dispatch, baseline/later sample, cleanup, F11 and assist refusal; no devices, capture or game input')


if __name__=='__main__':main()
