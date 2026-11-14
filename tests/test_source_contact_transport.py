"""Actual watchdog/pipe writes only; no client/device input."""
import pytest
from eql_automation.source_step_sender import run_checked_source_step
from test_source_contact_controller import begin
from test_source_motion import f,legacy
from test_route_step_sender import after_down

pytestmark=pytest.mark.parametrize('f',['contact_preflight'],indirect=True)


@pytest.mark.parametrize('cancel',[False,True])
def test_contact_sender_releases_real_pipe_and_preserves_ordinary_floor(f,monkeypatch,cancel):
    c,_=begin(f,real=True);old=f.ledger._state()
    if cancel:after_down(monkeypatch,lambda:c.cancel('F9 after contact DOWN'))
    def send():return run_checked_source_step(f.sender,c,policy=f.policy,kind='forward',
        requested_seconds=.02,command_state_clear=lambda:True,pump=lambda:None)
    if cancel:
        with pytest.raises(RuntimeError):send()
    else:
        seal=send();assert seal.receipt.completion=='elapsed'
    events=f.drain_events()
    assert events[:4]==((1,103,1),(0,0,0),(1,103,0),(0,0,0))
    assert not f.sender.held and f.ledger._state()==old and c.arrival is None
    assert f.ledger.phase==('stopped' if cancel else 'contact_transfer')
