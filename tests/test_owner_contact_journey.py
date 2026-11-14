"""Whole owner travel/camp adapter with actual pipe sender, synthetic client."""
from dataclasses import replace
from hashlib import sha256
import json

from eql_automation.camp_contact_checkpoint import CampContactCheckpoint
from eql_automation.native_region_policy import encoded
from eql_automation.navigation_phase import navigation_active
from eql_automation.portal_precision import SourceFace
from eql_automation.source_contact_hint import SourceContactHint
from eql_automation.source_itinerary import SourceWalkHint
from eql_automation.source_observer import SourceItineraryObserver
from test_motion_collection import retained
from test_owner_journey_runtime import h,start
from test_owner_route_trial import finish
from test_owner_source_travel import configure


def contact_destination(h,monkeypatch):
    assets=configure(h,monkeypatch,destination_id='north-wall');p=assets.planner
    vertices=((390.,225.,.2945911407470703),(410.,225.,.2945911407470703),
              (410.,240.,.2945911407470703),(390.,240.,.2945911407470703))
    p.static.sources=tuple(SourceFace(tuple((y,x,z) for x,y,z in tri),0,'TransparentMasked',20,i)
        for i,tri in enumerate(((vertices[0],vertices[1],vertices[2]),(vertices[0],vertices[2],vertices[3]))))
    p.static.identities={20:dict(placement_fragment=110,model_wld_sha256='e'*64,transform_sha256='f'*64)}
    p.static.faces_for_footprint=lambda _:p.static.sources
    guide=replace(assets.guide,goal=(400.,228.5),operations=(SourceWalkHint((400.,200.),(400.,220.)),
        SourceContactHint(((400.,220.),(400.,228.5)),((20,0),(20,1)),1.4)))
    assets=replace(assets,guide=guide,source_evidence=encoded(dict(synthetic=True,destination_id='north-wall',
        guide_sha256=sha256(encoded(guide.record())).hexdigest())))
    h.source_loading[0]=lambda:assets
    apply=h.apply
    def contact_step(key,receipt):
        apply(key,receipt)
        h.point[2]=2.79 if h.point[0]>=225 else 2.7
    h.apply=contact_step
    return assets


def test_owner_contact_travel_releases_navigation_then_starts_same_sender_camp(h,monkeypatch):
    contact_destination(h,monkeypatch);e=h.engine;captured=[]
    from eql_automation.source_motion import SourceReceiptLedger
    cancel=SourceReceiptLedger.cancel;refusals=[]
    def remember(ledger,reason):
        refusals.append(str(reason));return cancel(ledger,reason)
    monkeypatch.setattr(SourceReceiptLedger,'cancel',remember)
    check=SourceItineraryObserver.check
    def active_only(observer):
        assert e.journey is None or e.journey.phase!='camp','Old movement observer resumed'
        return check(observer)
    monkeypatch.setattr(SourceItineraryObserver,'check',active_only)
    capture=e._capture_trial_continuation
    def keep(p):
        token=capture(p)
        if token:captured.append(token)
        return token
    e._capture_trial_continuation=keep
    start(h,'north-wall');h.due_trial();record=finish(h,timeout=100.)
    assert record is not None and record['outcome']=='arrived',(h.notices,refusals)
    assert record['continuation']['camp_started'] and len(captured)==1,h.notices
    token=captured[0];checkpoint=token.floor_checkpoint
    assert type(checkpoint) is CampContactCheckpoint and e.journey.arrival_floor is checkpoint
    assert checkpoint._reference is token.receipt.second
    assert token.runtime.ledger.reference is not checkpoint._reference
    assert abs(checkpoint._reference.package_xyz[1]-228.5)<=.25
    assert checkpoint._reference.package_xyz[2]!=.2
    basis=json.loads(token.motion_basis)
    assert basis['format']=='eql-camp-contact-arrival-motion-v1'
    assert basis['arrival_position']==list(checkpoint._reference.package_xyz)
    assert e.journey.phase=='camp' and e.camp_session.preparation_due
    assert e.sender is h.sender and not h.sender.held and not h.observer_closed
    assert e.live_zone_tracker.lease is None and not navigation_active(e)
    checkpoint.check();assert not h.commands and not record['real_client_accepted']
    e.stop_action('F9');assert not checkpoint.valid and h.observer_closed
