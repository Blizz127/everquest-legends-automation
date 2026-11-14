"""Nominal corner targeting with real geometry and synthetic receipts."""
import pytest
from test_source_contact_controller import begin,pulse,pair
from test_source_motion import f,legacy

@pytest.mark.parametrize('f',['contact_bend'],indirect=True)
def test_contact_controller_reaches_nominal_corner_before_turning(f):
    c,pre=begin(f,waypoints=((4.,2.),(4.,3.8),(6.,3.8)))
    assert c.targets==((4.,3.8),(6.,3.8))
    rows=pre.contact_index.plan.record()['contact_walks']['accepted_envelopes']
    assert rows[0]['checked_end']==[4.,4.8] and rows[1]['checked_end']==[7.,3.8]
    old=f.ledger._state()
    for y,z in ((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79)):
        assert c.next_command().target==(4.,3.8)
        seal=pulse(f,c);result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=y,z=z))
        assert result.kind=='in_contact' and f.ledger._state()==old
    assert c.cursor==1 and c.arrival is None
    command=c.next_command()
    assert command.kind=='right' and command.target==(6.,3.8)
    # A real corner pivot remains in the checked union; no straight chase
    # of the runout endpoint or skip to the final destination took place.
    seal=pulse(f,c)
    c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.6,z=2.79))
    assert c.cursor==1 and c.pose.heading>0. and f.ledger._state()==old


@pytest.mark.parametrize('f',['contact_close'],indirect=True)
def test_one_receipt_can_settle_at_close_waypoints_without_recounting_movement(f):
    c,_=begin(f,waypoints=((4.,2.),(4.,3.6),(4.,3.8)))
    assert c.targets==((4.,3.6),(4.,3.8))
    for y in (2.4,2.8,3.2):
        seal=pulse(f,c);c.acknowledge_stopped(seal,*pair(f,c,seal,y=y))
    old=f.ledger._state();steps=c.local_steps
    seal=pulse(f,c);f.now=seal.receipt.up_completed_at+.2
    a=c.observe_reply(seal,f.position(x=4.01,y=3.55,z=2.79));f.now+=.4
    b=c.observe_reply(seal,f.position(x=4.01,y=3.8,z=2.79))
    result=c.acknowledge_stopped(seal,a,b)
    assert result.kind=='settling' and c.cursor==1 and c._sealed is seal and c.local_steps==steps
    result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.8,z=2.79))
    assert result.kind=='arrived' and c.cursor==2 and c.local_steps==steps+1
    assert f.ledger._state()==old and not f.drain_events()
