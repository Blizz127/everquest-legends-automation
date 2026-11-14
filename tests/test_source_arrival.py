"""Source/arrival reuse of one real lease and reader; all input is synthetic."""
import pytest
from datetime import datetime,timedelta
from types import SimpleNamespace

from eql_automation.motion_collection import CommandReceipt,LocationRequest
from test_zone_arrival import h
from test_route_floor_commit import setup as floor_setup,receipt,legacy
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.provisional_floor_commit import ProvisionalRouteFloorCommit
from eql_automation.zone_arrival import ZoneArrivalHandoff


def start(h,observer=None):
    h.held.clear();released=h.now;h.now+=2.6
    h.observed=[]
    def observe(raw):
        assert 0<=h.now-raw.received_monotonic<=.5
        h.observed.append(raw)
        return raw if observer is None else observer(raw)
    h.session.start_source_pair(released_at=released,observe_fix=observe)
    return h.session.source_collector


def send_source(h,request,body='Your Location is -12, 34, 5'):
    assert isinstance(request,LocationRequest) and h.session.phase=='await_loading'
    began=h.now;h.now+=.02
    h.session.command_sent(request,CommandReceipt(began,h.now))
    if body is not None:h.append(body)


def complete_source(h):
    send_source(h,h.tick());assert h.tick() is None
    send_source(h,h.tick(.41));assert h.tick() is None
    assert h.session.source_collector is None and h.session.source_result is not None


def complete_destination(h):
    h.ready=True;h.send(h.tick(.2));assert h.tick() is None
    h.send(h.tick(.41));assert h.tick() is None
    assert h.session.phase=='complete'
    assert h.session.collector.first.zone_id==h.session.collector.second.zone_id==58


def test_complete_source_pair_aligns_each_reply_and_returns_once(h):
    reader=h.lease.reader;collector=start(h)
    send_source(h,h.tick());h.tick()
    assert h.observed==[collector.first] and h.session.source_result is None
    send_source(h,h.tick(.41));h.tick()
    assert h.observed==[collector.first,collector.second]
    result=h.session.take_source_pair()
    assert result.first is collector.first and result.second is collector.second
    assert result.observations==tuple(h.observed) and not result.input_authorized
    assert not result.real_client_accepted and h.session.reader is reader
    assert h.session.source_result is None and h.session.source_collector is None
    assert h.session.phase=='await_loading' and not h.releases
    with pytest.raises(ValueError,match='No complete source pair'):h.session.take_source_pair()
    assert h.session.phase=='stopped'


@pytest.mark.parametrize('phase',['before_request','await_first','between','await_second','completed','take_flush'])
@pytest.mark.parametrize('same_batch_entry',[False,True])
def test_loading_at_every_source_phase_retires_pair_and_preserves_arrival(h,phase,same_batch_entry):
    collector=start(h);reader=h.lease.reader
    if phase!='before_request':send_source(h,h.tick(),body=None)
    if phase in ('between','await_second','completed','take_flush'):
        h.append('Your Location is -12, 34, 5');h.tick()
    if phase in ('await_second','completed','take_flush'):
        send_source(h,h.tick(.41),body=None)
    if phase in ('completed','take_flush'):
        h.append('Your Location is -12, 34, 5');h.tick()
        assert h.session.source_result is not None and h.session.source_collector is None
    h.append('LOADING, PLEASE WAIT...')
    if same_batch_entry:h.append('You have entered Clan Crushbone.')
    if phase=='take_flush':assert h.session.take_source_pair() is None
    else:assert h.tick() is None
    assert h.session.phase==('await_ready' if same_batch_entry else 'loading')
    assert h.session.source_result is None and h.session.source_collector is None
    assert len(h.releases)==1 and h.session.reader is reader and not h.held
    if phase not in ('completed','take_flush'):assert collector.phase=='stopped'
    if not same_batch_entry:
        h.now+=2;h.append('You have entered Clan Crushbone.');h.tick()
    complete_destination(h)
    assert all(raw.zone_id==54 for raw in h.observed)
    assert h.session.collector.first is not collector.first


def test_source_pair_can_repeat_without_new_reader_or_arrival_deadline(h):
    reader=h.lease.reader;deadline=h.session.deadline
    first=start(h);complete_source(h);one=h.session.take_source_pair()
    second=start(h);complete_source(h);two=h.session.take_source_pair()
    assert one.second.log_line_seq+1==two.first.log_line_seq
    assert first is not second and h.session.reader is reader and h.session.deadline==deadline
    h.append('LOADING, PLEASE WAIT...');h.append('You have entered Clan Crushbone.');h.tick()
    complete_destination(h)


@pytest.mark.parametrize('body',['You have entered Butcherblock Mountains.',
    'LOADING, PLEASE WAIT...',"Logging to 'eqlog.txt' is now *OFF*.",
    'Your Location is 1, 2, 3','a bat hits YOU for 3 points of damage.'])
def test_invalid_later_boundary_or_hazard_is_not_hidden_by_source_transition(h,body):
    start(h);send_source(h,h.tick(),body=None)
    h.append('LOADING, PLEASE WAIT...');h.append(body)
    with pytest.raises(ValueError):h.tick()
    assert h.session.phase=='stopped' and not h.held
    assert h.session.source_result is h.session.source_collector is None


@pytest.mark.parametrize('change',['duplicate','unsolicited','partial','moved','wrong_receipt','expired','owner'])
def test_source_collection_retains_existing_pair_checks(h,change):
    start(h)
    if change=='unsolicited':h.append('Your Location is 1, 2, 3')
    else:
        request=h.tick()
        if change=='wrong_receipt':
            with pytest.raises(ValueError):
                h.session.command_sent(request,CommandReceipt(h.now-1,h.now))
            assert h.session.phase=='stopped';return
        send_source(h,request,body=None)
        if change=='duplicate':h.append('Your Location is 1, 2, 3');h.append('Your Location is 1, 2, 3')
        elif change=='partial':
            with h.log.open('a') as out:out.write('[unfinished')
        elif change=='moved':
            h.append('Your Location is 1, 2, 3');h.tick()
            send_source(h,h.tick(.41),'Your Location is 2, 2, 3')
        elif change=='expired':h.now+=3
        elif change=='owner':h.owner=('changed',)
    with pytest.raises(ValueError):h.tick()
    assert h.session.phase=='stopped' and h.session.source_result is None


@pytest.mark.parametrize('change',['cancel','consume','reenter'])
def test_source_observer_callback_cannot_publish_after_cancellation_or_reader_use(h,change):
    def observe(raw):
        if change=='cancel':h.session.cancel('F9 during source observation')
        elif change=='consume':
            h.append('LOADING, PLEASE WAIT...');h.lease.reader.poll(now=h.now)
        else:
            with pytest.raises(ValueError):h.session.tick()
        return raw
    start(h,observe);send_source(h,h.tick())
    with pytest.raises(ValueError):h.tick()
    assert h.session.phase=='stopped' and h.session.source_result is None and not h.held


def test_release_callback_cannot_steal_the_same_batch_destination(h):
    start(h)
    def release():
        h.append('You have entered Clan Crushbone.');h.lease.reader.poll(now=h.now)
    h.release_hook=release;h.append('LOADING, PLEASE WAIT...')
    with pytest.raises(ValueError,match='lease changed'):h.tick()
    assert h.session.phase=='stopped' and not h.held


def test_reentrant_source_setup_cannot_replace_another_collector(h):
    calls=[]
    def current():
        calls.append(1)
        if len(calls)==2:
            try:h.session.start_source_pair(released_at=h.now-.2,observe_fix=lambda raw:raw)
            except ValueError:pass
    h.current=current
    with pytest.raises(ValueError):start(h)
    assert h.session.phase=='stopped' and h.session.source_collector is None


@pytest.mark.parametrize('loading',[False,True])
def test_owned_source_pair_resolves_or_discards_the_actual_provisional_ledger(tmp_path,legacy,loading):
    s=SimpleNamespace(now=100.,ready=False)
    clock=lambda:s.now
    wall=lambda:datetime(2026,11,14,12)+timedelta(seconds=s.now-100.)
    log=tmp_path/'eqlog_Probe_private.txt';log.touch()
    catalog=tmp_path/'zones.txt';catalog.write_text('54^Fixture^0^0\n58^Clan Crushbone^0^0\n')
    def append(body):
        with log.open('a') as out:out.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    tracker=LiveZoneTracker(log,catalog,expected_character='Probe',expected_server='private',
        binding_reader=lambda:('synthetic-owner',),clock=clock)
    append('You have entered Fixture.')
    append('Your Location is 2, 1, 2.7');append('Your Location is 2, 1, 2.7')
    tracker.poll();lease=tracker.acquire();reader=lease.reader
    def context():
        return (lease.check(),id(reader),reader.tail.identity,reader.tail.epoch,
            reader.zone_id,reader.zone_display_name,reader.zone_generation,'synthetic-line')
    f=floor_setup(legacy,clock=clock,ledger_factory=lambda *a,**kw:
        ProvisionalRouteFloorCommit(*a,context_reader=context,**kw))
    def release():
        f.ledger.cancel('source retired on loading or stop')
        return CommandReceipt(clock(),clock())
    arrival=ZoneArrivalHandoff(lease,'Clan Crushbone',release_controls=release,
        ready_for_location=lambda:s.ready,check_current=lambda:None,clock=clock,local_wall_clock=wall)
    try:
        ticket=f.stage();sent=receipt(ticket);s.now=sent.up_completed_at+.001
        sealed=f.ledger.seal_release(ticket,sent)
        def observe(raw):
            return f.observer.observe(raw,route=f.runner.route,segment_index=0,
                height_calibration=f.runner.height_calibration,
                motion_calibration_record_id=f.runner.calibration,now=clock(),
                floor_chain=f.ledger.floor_for_observation(sealed),mode='measurement')
        s.now+=2.6;arrival.start_source_pair(released_at=sent.up_completed_at,observe_fix=observe)
        for i in range(2):
            request=arrival.tick();arrival.command_sent(request,CommandReceipt(clock(),clock()))
            if loading and i==1:
                append('LOADING, PLEASE WAIT...');append('You have entered Clan Crushbone.')
            else:append('Your Location is 2, 1.22, 2.7')
            arrival.tick();s.now+=.41
        if not loading:
            pair=arrival.take_source_pair();f.ledger.resolve_source(sealed,*pair.observations)
            assert f.ledger.chain.index==2 and f.runner.steps==1 and f.runner.phase=='ready'
            assert pair.first is pair.observations[0].raw_fix and pair.second is reader.latest
        else:
            assert arrival.phase=='await_ready' and arrival.source_result is None
            assert f.ledger.chain.index==1 and f.runner.phase=='halted' and f.ledger._sealed is None
            s.ready=True
            for i in range(2):
                request=arrival.tick();arrival.command_sent(request,CommandReceipt(clock(),clock()))
                append('Your Location is -12, 34, 5');arrival.tick();s.now+=.41
            assert arrival.phase=='complete' and arrival.collector.second.zone_id==58
            assert f.ledger.chain.index==1 and f.runner.steps==0
    finally:lease.release();tracker.close()
