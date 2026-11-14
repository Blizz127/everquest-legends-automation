"""Synthetic private history, real retained rotation/parser and pipe sender."""
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from eql_automation import camp_candidate_history as history
from eql_automation import owner_camp_runtime as runtime
from test_owner_camp_runtime import client, h


def set_freeport(h):
    e=h.engine;e.settings.server='freeport';e.zone='gfaydark'
    new_path=e.log_path();h.path.rename(new_path);h.path=new_path
    e.tail=e.make_tail();e.tail.poll()
    return e


@pytest.fixture
def seed(tmp_path, monkeypatch, client):
    record = dict(format='eql-owner-npc-history-v1', server='freeport',
        client_sha256=history.EXE_PIN, source_log_sha256=history.SOURCE_LOG_PIN,
        source_bytes=1000, current_target_authorized=False,
        zones=[dict(zone=zone, zone_long=client.default_guide().zone_long(zone),
            candidates=[dict(name='Orc fixture', levels=[5], pairs=[[2,3]])])
            for zone in ('gfaydark', 'crushbone')])
    store=tmp_path/'store';path=store/'owner-route-data'/history.HISTORY_NAME
    path.parent.mkdir(parents=True)
    raw=json.dumps(record).encode();path.write_bytes(raw)
    monkeypatch.setattr(history, 'HISTORY_PIN', sha256(raw).hexdigest())
    monkeypatch.setattr(runtime, 'load_owner_candidates',
        lambda server,zone,**kw:history.load_owner_candidates(server,zone,store=store,**kw))
    return store,path,record


def test_exact_server_zone_and_provenance(seed,client):
    store,path,_=seed
    rows=history.load_owner_candidates('freeport','gfaydark',store=store,client=client)
    assert len(rows)==1 and rows[0].levels==(5,) and rows[0].pairs==((2,3),)
    assert rows[0].source_sha256==history.SOURCE_LOG_PIN
    assert rows[0].origin=='retained_owner_history' and rows[0].history_sha256==sha256(path.read_bytes()).hexdigest()
    assert history.load_owner_candidates('private','gfaydark',store=store,client=client)==()
    assert history.load_owner_candidates('freeport','unknown',store=store,client=client)==()
    assert history.load_owner_candidates('freeport','gfaydark',store=store,client=client,excluded=['orc fixture'])==()


@pytest.mark.parametrize('kind',('changed','oversized','symlink','fifo'))
def test_changed_or_nonregular_seed_refused(seed,client,kind):
    store,path,_=seed
    if kind=='changed':path.write_bytes(b'changed')
    elif kind=='oversized':path.write_bytes(b'x'*(history.MAX_HISTORY_BYTES+1))
    elif kind=='symlink':
        other=path.with_suffix('.copy');path.rename(other);path.symlink_to(other)
    else:path.unlink();os.mkfifo(path)
    with pytest.raises((OSError,ValueError)):
        history.load_owner_candidates('freeport','gfaydark',store=store,client=client)


def test_missing_optional_seed_returns_no_names(seed,client):
    store,path,_=seed;path.unlink()
    assert history.load_owner_candidates('freeport','gfaydark',store=store,client=client)==()


@pytest.mark.parametrize('field,value',(('client_sha256','wrong'),('source_log_sha256','wrong'),
    ('current_target_authorized',True),('server','other')))
def test_wrong_provenance_refused_even_when_repinned(seed,client,monkeypatch,field,value):
    store,path,record=seed;record[field]=value
    raw=json.dumps(record).encode();path.write_bytes(raw)
    monkeypatch.setattr(history,'HISTORY_PIN',sha256(raw).hexdigest())
    with pytest.raises(ValueError,match='provenance'):
        history.load_owner_candidates('freeport','gfaydark',store=store,client=client)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
def test_empty_history_bootstraps_names_but_waits_for_fresh_consideration(h,seed):
    e=set_freeport(h)
    assert e.start_stationary_camp(),h.notices
    assert e.camp_session.candidates[0].origin=='retained_owner_history'
    h.tick();assert h.commands==['/target Orc_fixture','/consider']
    assert not e.active and e.camp_session.kills==0
    assert e.camp_session.snapshot()['candidates'][0]['history_sha256']==history.HISTORY_PIN
    h.append('Targeted (NPC): Orc fixture')
    h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    h.tick();assert not e.native_attack_off_pending
    h.tick();assert e.camp_session.phase=='fight' and '/cast 3' in h.commands
    assert not any(c.startswith('/attack') for c in h.commands)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
@pytest.mark.parametrize('feedback',('Targeted (PC): Orc fixture',
    'Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 30)',
    'Other fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)'))
def test_retained_history_never_overrides_bad_live_target(h,seed,feedback):
    e=set_freeport(h)
    assert e.start_stationary_camp();h.tick();h.append(feedback);h.tick()
    assert not e.active and not any(c.startswith('/cast') for c in h.commands)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
def test_current_character_history_wins_without_opening_optional_seed(h,seed,monkeypatch):
    e=set_freeport(h)
    for line in ('You have entered '+e.camp_client.default_guide().zone_long('gfaydark')+'.', 'Targeted (NPC): Current fixture',
        'Current fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)',
        'You have slain Current fixture!'):
        h.append(line)
    monkeypatch.setattr(runtime,'load_owner_candidates',lambda *a,**k:pytest.fail('Opened fallback'))
    rows=e._load_camp_candidates()
    assert len(rows)==1 and rows[0].name=='Current fixture' and rows[0].origin=='selected_character_log'


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
def test_f9_during_fallback_load_cannot_start_camp(h,seed,monkeypatch):
    e=set_freeport(h);loaded=[]
    original=runtime.load_owner_candidates
    def interrupted(*args,**kwargs):
        rows=original(*args,**kwargs);loaded.append(rows);e.stop_action('F9');return rows
    monkeypatch.setattr(runtime,'load_owner_candidates',interrupted)
    assert not e.start_stationary_camp()
    assert loaded and e.camp_session is None and e.cancelled and not h.commands


def test_retained_artifact_reproduces_without_raw_chat(client):
    store=Path.home()/'.local/share/eql-automation'
    raw=history.build_owner_history(store/'owner-traces/eqlog-Legira-20261113.txt',client)
    assert sha256(raw).hexdigest()==history.HISTORY_PIN
    record=json.loads(raw)
    assert {row['zone']:len(row['candidates']) for row in record['zones']}==dict(gfaydark=5,crushbone=4,butcher=0)
    for zone in record['zones']:
        for candidate in zone['candidates']:
            assert set(candidate)=={'name','levels','pairs'}
