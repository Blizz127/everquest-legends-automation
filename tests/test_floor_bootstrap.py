"""Overhead source sheets, complete body checks and bound fresh height samples."""
from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np
import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.observed_height import measure_current_height, current_height_allowed
from eql_automation.portal_precision import SourceFace
from test_current_route_start import fixture, ARCHIVE, WLD
from test_source_floor_observation import view, face
from test_ground_observer import rectangle
from test_destination_route import f as destination_fixture, nav_module


def point_view(*faces):
    source = view(*faces)
    source.archive_sha256, source.wld_sha256 = ARCHIVE, WLD
    return source


def add_boundary(f, *, sloping=False):
    source = f.planner.source
    patches = rectangle(0., 20., 624.)
    added = tuple(SourceFace(tuple((y, x, 15.-20.*(y-2.) if sloping else z)
        for x, y, z in triangle), 0, 'Boundary', 99, i) for i, triangle in enumerate(patches))
    source.sources = tuple(source.sources)+added
    xyz = np.asarray([s.vertices_wld for s in source.sources])[:, :, [1, 0, 2]]
    source.source_minimum, source.source_maximum = xyz.min(axis=1), xyz.max(axis=1)


def fresh(f, plan):
    released = f.now
    f.now += .2; a = f.position()
    f.now += .5; b = f.position()
    options = dict(route=plan.route, segment_index=0, owner_binding=f.owner,
        binding_reader=lambda:f.owner, clock=f.clock, record_id='new-height',
        released_at=released, local_wall_clock=f.wall, floor_plan=plan)
    return a, b, options


def test_overhead_proposal_preserves_all_hits_and_strict_default():
    source = point_view(face(), face(624., material='Boundary', index=2))
    with pytest.raises(ValueError, match='collision/material'): source.source_floor_at((.1, .2))
    proposal = source.propose_unique_diffuse_floor((.1, .2), body_height=6.)
    assert proposal.selected_ids == ((7, 1),)
    assert proposal.height == pytest.approx(.4)
    assert proposal.intersections == source.source_hits_at((.1, .2))
    assert not proposal.input_authorized and not proposal.real_client_accepted
    assert proposal.numeric_margin == .01


@pytest.mark.parametrize('height,material,flag', [
    (6.01, 'Boundary', 0), (6., 'Boundary', 0), (-20., 'Boundary', 0),
    (624., 'Water', 0), (624., 'Boundary', 16), (624., 'Diffuse', 0),
])
def test_no_contact_unknown_flags_or_second_floor_waived(height, material, flag):
    source = point_view(face(), face(height, material=material, flag=flag, index=2))
    with pytest.raises(ValueError): source.propose_unique_diffuse_floor((0., 0.), body_height=6.)


@pytest.mark.parametrize('body', [True, 0., -1., 101., float('nan'), float('inf')])
def test_explicit_body_hypothesis_required(body):
    with pytest.raises(ValueError): point_view(face()).propose_unique_diffuse_floor((.1, .2), body_height=body)


def test_proposal_keeps_all_coplanar_edge_ids():
    neighbor = SourceFace(((1., 0., 1.), (1., 1., 3.), (0., 1., 2.)), 0, 'Diffuse', 7, 2)
    proposal = point_view(face(), neighbor).propose_unique_diffuse_floor((.5, .5), body_height=6.)
    assert proposal.selected_ids == ((7, 1), (7, 2)) and proposal.height == 1.5


def test_checked_initial_floor_produces_fresh_height_and_retains_proof(tmp_path):
    f = fixture(tmp_path); add_boundary(f)
    with pytest.raises(ValueError, match='collision/material'): f.plan()
    f.options['allow_overhead_boundary'] = True
    plan = f.plan()
    assert json.loads(plan.evidence_bytes)['seed']['source_floor_proposal']['intersections']
    a, b, options = fresh(f, plan)
    with pytest.raises(ValueError, match='collision/material'):
        measure_current_height(plan.observer, f.reader, a, b, **{**options, 'floor_plan':None})
    cal = measure_current_height(plan.observer, f.reader, a, b, **options)
    assert cal.raw_z_minus_source_z == 2.5
    assert cal.evidence.source_floor_kind == 'checked_initial_plan_floor'
    assert cal.evidence.source_floor_proof_sha256 == plan.floor_chain.previous.proof_sha256
    assert cal.evidence.source_floor_seed_sha256 == plan.floor_chain.seed_evidence_sha256
    assert current_height_allowed(cal, mode='measurement', route_sha256=plan.route.artifact_sha256,
                                  owner_binding=f.owner)
    assert not current_height_allowed(cal, mode='full_auto')
    for field in ('source_floor_proof_sha256', 'source_floor_seed_sha256'):
        broken = replace(cal, evidence=replace(cal.evidence, **{field:None}))
        assert not current_height_allowed(broken, mode='measurement')


def test_point_overhead_is_not_full_swept_clearance(tmp_path):
    f = fixture(tmp_path); add_boundary(f, sloping=True)
    proposal = f.planner.source.propose_unique_diffuse_floor((4., 2.), body_height=6.)
    assert proposal.height == .2
    f.options['allow_overhead_boundary'] = True
    with pytest.raises(ValueError, match='other_source_surface_intersects_body_band'): f.plan()


@pytest.mark.parametrize('hazard', ['wall', 'water', 'missing_bsp'])
def test_overhead_proposal_preserves_static_and_region_refusals(tmp_path, hazard):
    f = fixture(tmp_path, **({hazard:True} if hazard != 'missing_bsp' else {}))
    add_boundary(f); f.options['allow_overhead_boundary'] = True
    if hazard == 'missing_bsp':
        bsp = BspVolumeView(SimpleNamespace(nodes=((1.,0.,0.,0.,0,0,0),), labels_by_region={}),
                            region_count=1, wld_sha256=WLD)
        f.planner.bsp = bsp; f.planner.bsp_pin = bsp.inventory_sha256
        f.planner._views = (*f.planner._views[:-1], bsp)
    with pytest.raises(ValueError, match='static geometry|BSP'): f.plan()


def test_destination_wrapped_initial_proof_is_accepted(destination_fixture):
    f = destination_fixture
    plan = f.plan_destination()
    a, b, options = fresh(f, plan)
    cal = measure_current_height(plan.observer, f.reader, a, b, **options)
    assert cal.evidence.source_floor_proof_sha256 == plan.floor_chain.previous.proof_sha256


@pytest.mark.parametrize('change', ['proof', 'seed', 'wld', 'body', 'halted', 'advanced',
                                  'old_pair', 'other_route', 'other_log', 'out_of_cell'])
def test_changed_initial_floor_or_unbound_samples_refuse(tmp_path, change):
    f = fixture(tmp_path); plan = f.plan(); a, b, options = fresh(f, plan)
    chain = plan.floor_chain
    if change == 'proof': chain.previous = replace(chain.previous, proof_sha256='f'*64)
    elif change == 'seed': chain.seed_evidence_sha256 = 'f'*64
    elif change == 'wld': chain.inventory_sha256 = 'f'*64
    elif change == 'body': chain.body_height += 1.
    elif change == 'halted': chain.halted = True
    elif change == 'advanced': chain.index += 1
    elif change == 'old_pair': a, b = f.a, f.b; f.reader.latest = b
    elif change == 'other_route': options['route'] = replace(plan.route)
    elif change == 'other_log': f.reader.tail.identity = (123, 456)
    elif change == 'out_of_cell':
        a = replace(a, raw_coordinates=(2., 8., 2.7)); b = replace(b, raw_coordinates=(2., 8., 2.7))
        f.reader.latest = b
    with pytest.raises(ValueError): measure_current_height(plan.observer, f.reader, a, b, **options)


@pytest.mark.parametrize('stage', ['lookup', 'final_callback'])
@pytest.mark.parametrize('change', ['chain', 'source', 'mesh', 'ground', 'owner'])
def test_height_callbacks_cannot_return_a_changed_floor(tmp_path, stage, change):
    f = fixture(tmp_path); plan = f.plan(); a, b, options = fresh(f, plan)
    def mutate():
        if change == 'chain': plan.floor_chain.body_height += 1
        elif change == 'owner': f.owner = ('changed',)
        else: setattr(plan.observer, change, object())
    if stage == 'lookup':
        original = plan.floor_chain.floor_at
        def lookup(xy):
            value = original(xy); mutate(); return value
        plan.floor_chain.floor_at = lookup
    else:
        calls = []
        def binding():
            calls.append(1)
            if len(calls) == 4: mutate()
            return f.owner
        options['binding_reader'] = binding
    with pytest.raises((ValueError, AttributeError)):
        measure_current_height(plan.observer, f.reader, a, b, **options)


def test_final_binding_delay_cannot_return_expired_height(tmp_path):
    f = fixture(tmp_path); plan = f.plan(); a, b, options = fresh(f, plan)
    calls = []
    def binding():
        calls.append(1)
        if len(calls) == 4: f.now += .6
        return f.owner
    options['binding_reader'] = binding
    with pytest.raises(ValueError, match='expired'):
        measure_current_height(plan.observer, f.reader, a, b, **options)
    assert len(calls) == 4
