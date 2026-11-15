"""Pinned search metadata with the real retained camp engine and pipe sender."""
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from eql_automation import camp_search_history as search
from eql_automation import camp_candidate_history as history
from eql_automation import owner_camp_runtime as runtime
from eql_automation.camp_session import NpcCandidate
from test_owner_camp_runtime import client, h
from test_camp_search_extraction import base, line, extract


@pytest.fixture
def seed(tmp_path, monkeypatch, client):
    record=extract(base()+line('You have slain a bat!',3))
    record.update(format='eql-owner-npc-search-suggestions-v1',server='freeport',
        client_sha256=search.EXE_PIN,source_log_sha256=search.SOURCE_PIN,
        zone='butcher',zone_long=client.default_guide().zone_long('butcher'))
    store=tmp_path/'store';path=store/'owner-route-data'/search.SEARCH_NAME
    path.parent.mkdir(parents=True);raw=json.dumps(record).encode();path.write_bytes(raw)
    monkeypatch.setattr(search,'SEARCH_PIN',sha256(raw).hexdigest())
    monkeypatch.setattr(runtime,'load_owner_search_candidates',
        lambda server,zone,**kw:search.load_owner_search_candidates(server,zone,store=store,**kw))
    return store,path,record


def setup_camp(h,monkeypatch):
    e=h.engine;e.settings.server='freeport';e.zone='butcher'
    new_path=e.log_path();h.path.rename(new_path);h.path=new_path
    e.tail=e.make_tail();e.tail.poll()
    monkeypatch.setattr(runtime,'load_owner_candidates',lambda *a,**kw:())
    return e


def test_pinned_search_provenance_and_scope(seed,client):
    store,path,_=seed
    row,=search.load_owner_search_candidates('freeport','butcher',store=store,client=client)
    assert row.levels==row.pairs==() and row.selection_kill_pairs==((1,2,3),)
    assert row.origin=='retained_owner_selection_kill'
    assert row.evidence_kind=='npc_selection_owner_kill' and row.history_sha256==search.SEARCH_PIN
    assert search.load_owner_search_candidates('private','butcher',store=store,client=client)==()
    assert search.load_owner_search_candidates('freeport','gfaydark',store=store,client=client)==()
    assert search.load_owner_search_candidates('freeport','butcher',store=store,client=client,excluded=['A BAT'])==()
    path.unlink()
    assert search.load_owner_search_candidates('freeport','butcher',store=store,client=client)==()


@pytest.mark.parametrize('kind',('changed','oversized','symlink','fifo'))
def test_modified_or_nonregular_search_refuses(seed,client,kind):
    store,path,_=seed
    if kind=='changed':path.write_bytes(b'changed')
    elif kind=='oversized':path.write_bytes(b'x'*(search.MAX_HISTORY_BYTES+1))
    elif kind=='symlink':
        other=path.with_suffix('.copy');path.rename(other);path.symlink_to(other)
    else:path.unlink();os.mkfifo(path)
    with pytest.raises((ValueError,OSError)):
        search.load_owner_search_candidates('freeport','butcher',store=store,client=client)


@pytest.mark.parametrize('field,value',(('client_sha256','wrong'),('source_log_sha256','wrong'),
    ('current_target_authorized',True),('prior_consideration_claimed',True)))
def test_repinned_provenance_cannot_claim_authority(seed,client,monkeypatch,field,value):
    store,path,record=seed;record[field]=value
    raw=json.dumps(record).encode();path.write_bytes(raw)
    monkeypatch.setattr(search,'SEARCH_PIN',sha256(raw).hexdigest())
    with pytest.raises(ValueError,match='provenance'):
        search.load_owner_search_candidates('freeport','butcher',store=store,client=client)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
def test_search_alone_never_casts_then_fresh_consideration_uses_existing_path(h,seed,monkeypatch):
    e=setup_camp(h,monkeypatch)
    assert e.start_stationary_camp(),h.notices
    h.tick();assert h.commands==['/target a_bat','/consider'] and not e.active
    snapshot=e.camp_session.snapshot()['candidates'][0]
    assert snapshot['pairs']==() and snapshot['selection_kill_pairs']==((1,2,3),)
    h.append('a bat scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    h.tick();assert e.camp_session.phase=='fight' and '/cast 3' in h.commands
    assert not any(c.startswith('/attack') for c in h.commands)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
@pytest.mark.parametrize('feedback',('Targeted (PC): a bat','Targeted (Pet): a bat',
    'a bat scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 30)',
    'a snake scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)',
    'a bat regards you as an ally -- looks like quite a gamble. (Lvl: 5)','stale'))
def test_search_cannot_override_bad_current_target(h,seed,monkeypatch,feedback):
    e=setup_camp(h,monkeypatch);assert e.start_stationary_camp();h.tick()
    if feedback=='stale':
        h.append('a bat scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)');h.now+=4.
    else:h.append(feedback)
    h.tick();assert not e.active and not any(c.startswith('/cast') for c in h.commands)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
@pytest.mark.parametrize('source',('current','qualified','qualified_error'))
def test_qualified_sources_take_precedence(h,seed,monkeypatch,source):
    e=setup_camp(h,monkeypatch)
    candidate=NpcCandidate('a snake',(5,),'a'*64,((1,2),))
    monkeypatch.setattr(runtime,'load_owner_search_candidates',lambda *a,**kw:pytest.fail('Opened search fallback'))
    monkeypatch.setattr(runtime,'observed_candidates',lambda *a,**kw:(candidate,) if source=='current' else ())
    def qualified(*a,**kw):
        if source=='current':pytest.fail('Opened qualified fallback')
        if source=='qualified_error':raise ValueError('Qualified history changed')
        return (candidate,)
    monkeypatch.setattr(runtime,'load_owner_candidates',qualified)
    if source=='qualified_error':
        with pytest.raises(ValueError,match='Qualified history changed'):e._load_camp_candidates()
    else:assert e._load_camp_candidates()==(candidate,)


@pytest.mark.parametrize('h',[{'real_history':True}],indirect=True)
def test_f9_during_search_load_cannot_start(h,seed,monkeypatch):
    e=setup_camp(h,monkeypatch);original=runtime.load_owner_search_candidates
    def interrupted(*args,**kwargs):
        rows=original(*args,**kwargs);e.stop_action('F9');return rows
    monkeypatch.setattr(runtime,'load_owner_search_candidates',interrupted)
    assert not e.start_stationary_camp()
    assert e.camp_session is None and e.cancelled and not h.commands


def test_owner_artifact_reproduces_and_qualified_history_unchanged(client):
    store=Path.home()/'.local/share/eql-automation'
    qualified=store/'owner-route-data'/history.HISTORY_NAME
    before=sha256(qualified.read_bytes()).hexdigest()
    raw=search.build_owner_search_history(store/'owner-traces/owner-log-20261115T0243Z.txt',client)
    assert sha256(raw).hexdigest()==search.SEARCH_PIN
    record=json.loads(raw)
    assert len(record['candidates'])==8
    assert sum(len(row['selection_kill_pairs']) for row in record['candidates'])==16
    assert all(row['pairs']==[] and row['levels']==[] for row in record['candidates'])
    assert sha256(qualified.read_bytes()).hexdigest()==before==history.HISTORY_PIN
