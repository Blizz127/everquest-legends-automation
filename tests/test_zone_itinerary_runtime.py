"""Two actual crossing runtimes with synthetic clocks, scenes and sender receipts.

Every floor, location reader, probe transaction, fitted motion, source runner,
section continuation and crossing is an actual production contract. Only game
feedback and low-level senders are simulated; no client/device acceptance claim.
"""
from dataclasses import replace
from datetime import datetime, timedelta
import math
import os
import threading
from types import SimpleNamespace

import numpy as np
import pytest

import eql_automation.camp_probe_runtime as probes_module
import eql_automation.camp_source_runtime as source_module
import eql_automation.destination_bootstrap_runtime as bootstrap_module
import eql_automation.owner_source_crossing as crossing_module
import eql_automation.section_continuation as section_module
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_probe_sender import SentCampProbe
from eql_automation.camp_source_runtime import CampSourceRuntime
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.destination_bootstrap_runtime import DestinationBootstrapRuntime
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.location_hotkey import HotkeyReceipt, OwnerLocationHotkey
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy, encoded
from eql_automation.observed_height import measure_current_height
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.owner_source_crossing import OwnerSourceCrossingRuntime, PinnedSourceCrossingSpec
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.portal_precision import SourceFace
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.section_continuation import SectionContinuation
from eql_automation.source_destinations import destination_spec
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.source_motion import SourceReceiptLedger
from eql_automation.source_observer import SourceItineraryObserver
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from eql_automation.uinput_watchdog import PulseReceipt
from eql_automation.zone_itinerary_budget import ZoneItineraryBudget, ZoneItineraryDeclaration, ZoneItineraryLeg
from eql_automation.zone_itinerary_runtime import ZoneItineraryPlan, ZoneItineraryRuntime
from eql_automation.zone_line import ExpectedZoneLine
from test_client_classification import leaf, view
from test_current_route_start import fixture as geometry_fixture
from test_installed_region_model import files
from test_motion_calibration import legacy as fitter
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender


def planner(tmp_path, model, *, zone, zone_id, name, split):
    tmp_path.mkdir()
    f = geometry_fixture(tmp_path)
    old = f.planner
    corners = ((-50., -50., .2), (100., -50., .2), (100., 100., .2), (-50., 100., .2))
    old.source.sources = tuple(SourceFace(tuple((y, x, z) for x, y, z in tri), 0, 'Diffuse', 10, i)
        for i, tri in enumerate(((corners[0], corners[1], corners[2]), (corners[0], corners[2], corners[3]))))
    coords = np.asarray([s.vertices_wld for s in old.source.sources])[:, :, [1, 0, 2]]
    old.source.source_minimum, old.source.source_maximum = coords.min(axis=1), coords.max(axis=1)
    detail = coords.copy(); detail[:, :, 2] = .6
    old.ground.triangles = old.mesh._detail = detail
    old.ground.minimum, old.ground.maximum = detail.min(axis=1), detail.max(axis=1)
    nodes = ((1., 0., 0., -split, 0, 2, 3), leaf(3), leaf(1))
    bsp = BspVolumeView(SimpleNamespace(nodes=nodes, labels_by_region={2:{'zoneline'}}),
                       region_count=3, wld_sha256=old.pins[2])
    classifier = view(nodes, wld_pin=old.pins[2])
    policy = NativeZeroRegionTrialPolicy(*old.pins, bsp.inventory_sha256,
                                        classifier.inventory_sha256, classifier, zone=zone)
    p = CurrentStartPlanner(mesh=old.mesh, ground=old.ground, source=old.source, static=old.static,
        bsp=bsp, zone_short_name=zone, expected_zone_id=zone_id, expected_zone_name=name,
        mesh_sha256=old.pins[0], source_archive_sha256=old.pins[1], source_wld_sha256=old.pins[2],
        static_inventory_sha256=old.pins[3], region_policy=policy)
    p.installed_region_model = model
    return p


def crossing_spec(p, identifier, *, start_y, split, destination_zone, destination_id, destination_name):
    line = ExpectedZoneLine('synthetic-'+identifier, p.zone, *p.pins[:3], p.bsp.inventory_sha256,
        'f'*64, 'DRNTP00255000001', 2, (1,), (2,))
    points = [(4., start_y), (4., split-2.), (4., split+1.)]
    return PinnedSourceCrossingSpec(identifier, p.zone, destination_name, destination_id, destination_zone,
        'e'*64, points[0], points[-1], ((points[0], points[0]), *tuple(zip(points, points[1:])),
        (points[-1], points[-1])), line, 'd'*64, encoded({'synthetic':identifier}))


def position(f):
    f.append(f'Your Location is {f.y:.2f}, {f.x:.2f}, 2.70')
    return f.reader.poll(now=f.now)[0]


def pair(f):
    released = f.now
    f.now += .2; a = position(f)
    f.now += .5; b = position(f)
    return a, b, released


def run_until(f, predicate, *, limit=20000):
    for _ in range(limit):
        if predicate(): return
        runtime = f.controller if f.controller is not None else f.first
        runtime.tick()
        if f.controller is not None:
            for name in ('bootstrap', 'source', 'section', 'crossing'):
                child = getattr(f.controller, name)
                if child is not None and child not in f.children[name]: f.children[name].append(child)
        f.now += .05
    pytest.fail('Synthetic itinerary did not finish: '+str(runtime.snapshot()))


@pytest.fixture
def itinerary(tmp_path, monkeypatch, legacy, fitter, request):
    model = files(tmp_path, monkeypatch)
    f = SimpleNamespace(now=100., x=4., y=3., heading=0., focus=True, active=False, closed_observer=0,
        owner=('synthetic-itinerary-owner',), controller=None, first=None, sent=[], pulses=[], transitions=[],
        current_hook=None, send_hook=None, pulse_hook=None, children={k:[] for k in ('bootstrap','source','section','crossing')})
    f.clock = lambda:f.now
    f.wall = lambda:datetime(2026,11,15,12)+timedelta(seconds=f.now-100.)
    f.lock = threading.RLock()
    f.engine = SimpleNamespace(g0_stop_lock=f.lock, cancel_generation=1, zone_loading_until=0.)
    f.journey = SimpleNamespace(generation=1, destination_id='butcher-gfay-crossing', destination_assets=None,
                                arrival_floor=None, phase='source_crossing')
    f.engine.journey = f.journey
    log = tmp_path/'eqlog_Probe_private.txt'; log.touch()
    names = tmp_path/'ZoneNames.txt'
    names.write_text('68^Butcherblock Mountains^0^0\n54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n')
    def append(body):
        with log.open('a') as out: out.write(f.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    f.append = append
    f.tracker = LiveZoneTracker(log, names, expected_character='Probe', expected_server='private',
                                binding_reader=lambda:f.owner, clock=f.clock)
    append('You have entered Butcherblock Mountains.'); f.tracker.poll()
    f.lease = f.tracker.acquire(); f.reader = f.lease.reader
    f.butcher = planner(tmp_path/'butcher', model, zone='butcher', zone_id=68, name='Butcherblock Mountains', split=8.)
    f.gfay = planner(tmp_path/'gfay', model, zone='gfaydark', zone_id=54, name='The Greater Faydark', split=30.)
    f.specs = (
        crossing_spec(f.butcher, 'butcher-gfay-crossing', start_y=3., split=8.,
                      destination_zone='gfaydark', destination_id=54, destination_name='The Greater Faydark'),
        crossing_spec(f.gfay, 'gfay-butcher-crushbone-crossing', start_y=22., split=30.,
                      destination_zone='crushbone', destination_id=58, destination_name='Clan Crushbone'))
    legs=[]
    for p, spec in zip((f.butcher,f.gfay), f.specs):
        registered=destination_spec(spec.destination_id)
        legs.append(ZoneItineraryLeg(spec.destination_id, p.zone, p.zone_id, p.zone_name,
            spec.destination_zone, spec.destination_zone_id, spec.destination, registered.file_sha256,
            spec.corridor_file_sha256, spec.expected_zone_line.sha256, 'c'*64))
    declaration = ZoneItineraryDeclaration('synthetic-two-actual-crossings', tuple(legs), 600., 500, 100., 1000.)
    f.root = ZoneItineraryBudget(declaration, clock=f.clock, stop_lock=f.lock,
        owner_binding=f.owner, binding_reader=lambda:f.owner)
    f.bounds = RouteMotionBounds('independent-destination-bounds', 'synthetic-explicit-hypotheses',
                                 .01, .15, .18, 11., .02, .01, 2., .01, .1, 6.)
    f.basis = encoded({'kind':'synthetic independent destination hypotheses', 'source_motion_reused':False})
    points=[(4.,float(y)) for y in (3,5,7,9,11,13,15,17,19,21,22)]
    guide = SourceItineraryGuide('gfaydark', *f.gfay.pins[2:], 'e'*64, .1, 6., points[-1],
                                 tuple(SourceWalkHint(a,b) for a,b in zip(points,points[1:])))
    f.assets = SourceDestinationAssets(f.gfay, guide, 'Synthetic GFay pre-line', encoded({'synthetic':True}), legs[1].destination_id)
    f.sections = None
    if getattr(request,'param',None) == 'sections':
        chain=SourceFloorChain(inventory_sha256=f.gfay.source.wld_sha256,
            seed_evidence_sha256='b'*64,
            seed_ids=f.gfay.source.propose_unique_diffuse_floor((4.,3.),body_height=6.).selected_ids,
            body_height=6.)
        cap=((3.9,2.9),(4.1,2.9),(4.1,3.1),(3.9,3.1))
        assert chain.advance(cap,f.gfay.source.source_faces_for_footprint(cap)).candidate
        record=plan_walk_sections(chain,guide,f.gfay,bounds=f.bounds,maximum_length=11.,minimum_length=7.,
            candidate_spacing=.5,check_context=lambda:None,clock=f.clock)
        f.sections=parse_walking_sections(guide,record)
        assert len(f.sections.guides)==2
    f.plan = ZoneItineraryPlan(declaration, f.bounds, f.basis,
        lambda identifier:f.assets if identifier==legs[1].destination_id else None,
        lambda assets:f.sections, lambda identifier:next(s for s in f.specs if s.destination_id==identifier))

    # Actual initial stopped source ledger; no fabricated arrival/checkpoint.
    p=f.butcher; a,b,released=pair(f)
    initial_bounds=replace(f.bounds,maximum_requested_hold=.1)
    initial=SourceItineraryGuide('butcher',*p.pins[2:],'e'*64,.1,6.,(4.,4.),
                                 (SourceWalkHint((4.,3.),(4.,4.)),))
    plan=plan_current_source_itinerary(p,f.reader,a,b,guide=initial,heading=0.,
        motion_record_id=f.bounds.calibration_record_id,bounds=initial_bounds,half_width=.3,
        vertical_window=1.,maximum_source_z_difference=1.,owner_binding=f.owner,binding_reader=lambda:f.owner,
        released_at=released,record_id='synthetic-first-preline',clock=f.clock,local_wall_clock=f.wall)
    a,b,released=pair(f)
    height=measure_current_height(plan.initial.observer,f.reader,a,b,route=plan.initial.route,segment_index=0,
        floor_plan=plan.initial,owner_binding=f.owner,binding_reader=lambda:f.owner,clock=f.clock,
        local_wall_clock=f.wall,record_id='synthetic-initial-height',released_at=released)
    observer=SourceItineraryObserver(plan,f.reader,height_calibration=height,binding_reader=lambda:f.owner,
        mode_reader=lambda:'measurement',generation_reader=lambda:f.engine.cancel_generation,generation=1,clock=f.clock)
    motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=1,turn_latency=.03,back_speed=0.)
    ledger=SourceReceiptLedger(observer,terrain=p.source,static=p.static,bsp=p.bsp,bounds=initial_bounds,
        installed_model=model,legacy=legacy,motion=motion,heading=0.,stop_lock=f.lock)
    released=f.now; f.now+=.2
    a=observer.observe(position(f),checked_chain=ledger.chain)
    f.now+=.5
    b=observer.observe(position(f),checked_chain=ledger.chain)
    ledger.start(a,b,released_at=released)
    checkpoint=CampFloorCheckpoint(ledger); f.initial_floor=checkpoint
    f.journey.arrival_floor=checkpoint
    f.rd,f.wr=os.pipe(); f.sender=PipeSender(f.wr)
    window=SimpleNamespace(id=7)
    f.gate=SimpleNamespace(windows=lambda:[window],focused_window=lambda:window if f.focus else None,
        game_session=lambda:dict(pid=8,start_ticks='9'),controls_ready=lambda:f.focus)
    def sample():return OwnerInputObservation(f.now,f.now,1,True,1,0,f.active,0,'synthetic itinerary observer')
    def close():f.closed_observer+=1
    f.owner_input=SimpleNamespace(sample=sample,close=close)
    config=tmp_path/'synthetic-hotbutton.ini';config.write_text('Synthetic F1 = /location\n')
    f.hotkey=OwnerLocationHotkey.configured('F1',confirmation_id='synthetic-only',configuration_paths=(config,))
    def current():
        if f.current_hook is not None:
            hook,f.current_hook=f.current_hook,None;hook()
    f.current=current

    def location(sender, **options):
        options['ensure_current']()
        if f.send_hook is not None:
            hook,f.send_hook=f.send_hook,None;hook()
        options['ensure_current']()
        began=f.now;f.now+=.01
        receipt=PulseReceipt(59,.005,began,began+.001,began+.006,f.now,'elapsed')
        f.sent.append((f.reader.zone_id,receipt,options.get('release_deadline')))
        f.append(f'Your Location is {f.y:.2f}, {f.x:.2f}, 2.70')
        return HotkeyReceipt(receipt,f.now)
    for target in (probes_module,source_module,bootstrap_module,crossing_module,section_module):
        monkeypatch.setattr(target,'send_location_hotkey',location)

    def receipt(key,seconds):
        if f.pulse_hook is not None:
            hook,f.pulse_hook=f.pulse_hook,None;hook()
        at=f.now
        result=PulseReceipt(key,seconds,at+.001,at+.0012,at+.0012+seconds,at+.0014+seconds,'elapsed')
        f.now=result.up_completed_at+.001
        held=(result.maximum_held_seconds+result.up_started_at-result.down_completed_at)/2
        if key==103:
            f.x+=math.sin(math.radians(f.heading))*10.*held
            f.y+=math.cos(math.radians(f.heading))*10.*held
        else:f.heading=(f.heading+(1 if key==106 else -1)*170.*max(0.,held-.03))%360.
        f.x,f.y=round(f.x,2),round(f.y,2)
        f.pulses.append((f.reader.zone_id,result))
        return result

    def probe(sender,tx,start,*,policy,requested_seconds,**options):
        assert policy.check() is True
        ticket=tx.stage(start,movement_key={'forward':103,'left':105,'right':106}[tx.preparation.kind],requested_seconds=requested_seconds)
        authorization=policy.authorize(ticket)
        assert policy.still_authorized(authorization) is True
        result=receipt(ticket.movement_key,requested_seconds)
        assert policy.check() is True
        return SentCampProbe(tx.seal_release(ticket,result),f.now)
    monkeypatch.setattr(probes_module,'send_camp_probe',probe)

    def source(sender,ledger,*,policy,kind,requested_seconds,**options):
        geometry=ledger.prepare(kind)
        scene=policy.observe();policy.validate_scene(scene)
        ticket=ledger.stage(geometry,requested_seconds=requested_seconds)
        authorization=policy.authorize(ticket,scene)
        assert policy.still_authorized(authorization,policy.observe(validate_reference=False)) is True
        result=receipt(ticket.movement_key,requested_seconds)
        return ledger.seal_release(ticket,result)
    monkeypatch.setattr(source_module,'run_checked_source_step',source)

    def crossing(sender,corridor,*,policy,kind,requested_seconds,**options):
        geometry=corridor.prepare(kind,policy=policy)
        scene=policy.observe();policy.validate_scene(scene)
        ticket=corridor.stage(geometry,requested_seconds=requested_seconds)
        authorization=policy.authorize(ticket,scene)
        assert policy.still_authorized(authorization,policy.observe(validate_reference=False)) is True
        result=receipt(ticket.movement_key,requested_seconds)
        if ticket.touches_line:
            destination=corridor.arrival.destination
            f.transitions.append((f.reader.zone_id,destination))
            f.append('LOADING, PLEASE WAIT...');f.append('You have entered '+destination+'.')
            f.x,f.y,f.heading=4.,3.,0.
        return corridor.released(result)
    monkeypatch.setattr(crossing_module,'run_checked_source_crossing_step',crossing)

    f.root.advance(f.root.stage,'crossing',zone_id=68)
    f.first=OwnerSourceCrossingRuntime(f.engine,f.journey,destination_id=legs[0].destination_id,
        corridor_spec=f.specs[0],checkpoint=checkpoint,motion_basis=encoded({'synthetic':True}),
        motion=motion,heading=0.,bounds=initial_bounds,legacy=legacy,lease=f.lease,sender=f.sender,
        hotkey=f.hotkey,owner_input=f.owner_input,topology=1,gate=f.gate,window=GameWindowIdentity(7,8,9),
        released_at=f.now,owner_binding=f.owner,binding_reader=lambda:f.owner,
        generation_reader=lambda:f.engine.cancel_generation,pump=lambda:None,command_state_clear=lambda:True,
        clock=f.clock,local_wall_clock=f.wall,journey_budget=f.root)
    f.engine.source_crossing_run=f.first
    f.create=lambda:ZoneItineraryRuntime(f.engine,f.journey,f.first,plan=f.plan,root=f.root,
        check_current=f.current,pump=lambda:None,command_state_clear=lambda:True,
        fit_library=fitter,steering_library=legacy)
    yield f
    target=f.controller if f.controller is not None else f.first
    if not target.closed:
        if target.phase not in ('complete','stopped'):target.cancel('synthetic test cleanup')
        target.release()
    os.close(f.wr);os.close(f.rd)


def complete_first(f):
    run_until(f,lambda:f.first.phase=='complete')
    assert type(f.first) is OwnerSourceCrossingRuntime and f.root.stage.phase=='arrival'
    assert len(f.first.events)>0 and not f.initial_floor.valid
    assert len(f.first.corridor.arrival.collector.requests)==2
    f.controller=f.create()
    assert f.first.phase=='transferred' and f.first.closed and f.root.stage.phase=='bootstrap'


@pytest.mark.parametrize('itinerary',[None,'sections'],indirect=True)
def test_two_actual_crossings_remeasure_destination_walk_and_finish_one_root(itinerary):
    f=itinerary;expires=f.root.expires_at;original_observer=f.owner_input
    complete_first(f)
    run_until(f,lambda:f.controller.phase=='complete')
    r=f.controller
    assert r.root.stage.phase=='complete' and r.root.stage.leg_index==1
    assert r.expires_at==f.root.expires_at==expires
    assert f.transitions==[(68,'The Greater Faydark'),(54,'Clan Crushbone')]
    assert len(r.records)==2 and f.reader.zone_id==58
    assert len(f.children['bootstrap'])==1 and type(f.children['bootstrap'][0]) is DestinationBootstrapRuntime
    assert len(f.children['bootstrap'][0].runtime.results)==7
    assert f.children['source'] and all(type(v) is CampSourceRuntime for v in f.children['source'])
    assert f.children['crossing'] and all(type(v) is OwnerSourceCrossingRuntime for v in f.children['crossing'])
    if f.sections is not None:
        assert len(f.children['section'])==1 and type(f.children['section'][0]) is SectionContinuation
        assert len(f.children['section'][0].runtime.results)==7
    else:assert not f.children['section']
    assert r.owner_input is original_observer and f.closed_observer==1
    assert not f.sender.held and f.tracker.lease is None
    assert f.root.snapshot()['reserved_pulses']==len(f.pulses)
    assert not r.snapshot()['real_client_accepted'] and not r.snapshot()['source_zone_state_reused']


@pytest.mark.parametrize('fault',('F8','F9','lease','root','attack'))
def test_destination_handoff_refuses_cancelled_owner_or_stale_resource(itinerary,fault):
    f=itinerary;complete_first(f)
    sent,pulses=len(f.sent),len(f.pulses)
    if fault in ('F8','F9'):
        f.engine.cancel_generation+=1
    elif fault=='lease':f.controller.lease.active=False
    elif fault=='root':f.root.cancel('Synthetic root budget stop')
    else:f.append('Training dummy hits YOU for 2 points of damage.')
    with pytest.raises((ValueError,RuntimeError)):f.controller.tick()
    assert f.controller.phase=='stopped' and len(f.sent)==sent and len(f.pulses)==pulses
    f.controller.release()
    assert f.closed_observer==1 and not f.sender.held
