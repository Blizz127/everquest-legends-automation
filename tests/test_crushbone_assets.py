"""Source provenance and layered-label regressions; never a movement test."""
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from eql_automation.camp_annotations import read_camp_annotations
from eql_automation.crushbone_assets import DATA_NAME, CLASSIFICATION_PIN, load_crushbone_assets
from eql_automation.owner_route_assets import checked_bytes
from test_source_floor_observation import face, view


def test_map_hints_preserve_source_z_without_promoting_it_to_support():
    from hashlib import sha256
    data = b'P -10, 20, 999, 1, 2, 3, 2, L07-10_Example_Camp\n'
    value, = read_camp_annotations(data)
    assert value.map_xyz == (-10., 20., 999.)
    assert value.map_sha256 == sha256(data).hexdigest()
    assert value.name == 'Example Camp' and value.level_hint == (7, 10)
    assert value.hint_includes(7) and value.hint_includes(10)
    assert not value.hint_includes(11)
    for bad in (True, 7., 0, 51):
        with pytest.raises(ValueError): value.hint_includes(bad)
    with pytest.raises(FrozenInstanceError): value.name = 'changed'


@pytest.mark.parametrize('text', [
    'P 1, 2, nan, 0, 0, 0, 1, L07-10_Nonfinite',
    'P 1, 2, 3, 0, 0, 0, 1, L10-07_Reversed',
    'P 1, 2, 3, 0, 0, 0, 1, L00-05_Zero',
    'P 1, 2, 3, 0, 0, 0, 1, to_Another_Zone',
    'P 1, 2, 3, 0, 0, 0, 1, L01-05_Duplicate\n'*2,
])
def test_invalid_or_ambiguous_annotations_refuse(text):
    with pytest.raises(ValueError): read_camp_annotations(text.encode())


def test_point_diagnostic_keeps_boundary_and_all_diffuse_layers():
    source = view(face(0.), face(624., material='Boundary', index=2), face(40., index=3))
    hits = source.source_hits_at((.1, .2))
    assert tuple(h.identity for h in hits) == ('wld:7:face:1', 'wld:7:face:2', 'wld:7:face:3')
    assert tuple(h.height for h in hits) == pytest.approx((.4, 624.4, 40.4))
    assert hits[1].material_class == 'Boundary' and hits[1].flag == 0
    with pytest.raises(ValueError, match='collision/material'):
        source.source_floor_at((.1, .2))
    with pytest.raises(ValueError, match='layered'):
        view(face(), face(40., index=3)).source_floor_at((.1, .2))
    assert source.source_hits_at((8., 8.)) == ()


def test_changed_or_symlinked_copied_data_refuses(tmp_path):
    import hashlib
    data = tmp_path/'data'; data.write_bytes(b'original')
    pin = hashlib.sha256(data.read_bytes()).hexdigest()
    link = tmp_path/'link'; link.symlink_to(data)
    with pytest.raises(ValueError): checked_bytes(link, pin)
    data.write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'): checked_bytes(data, pin)


def test_retained_crushbone_loader_reports_real_layers_without_accepted_destinations(monkeypatch):
    store = Path.home()/'.local/share/eql-automation'
    root = store/'owner-route-data'/DATA_NAME
    helper = store/'owner-assist/0.39.4'
    if not root.is_dir() or not (helper/'eqnav/zonegeom.py').is_file():
        pytest.skip('Approved private copied Crushbone inputs not staged here')
    monkeypatch.syspath_prepend(str(helper))
    assets = load_crushbone_assets(root)
    assert assets.classification.inventory_sha256 == CLASSIFICATION_PIN
    native = assets.classification.classify_point_after_bounds(-424.04,274.06,0.)
    assert native.complete and native.classification.flags == 0
    assert not native.collision_verified and not native.input_authorized
    report = assets.annotation_report()
    assert (report['zone_id'], report['zone_name']) == (58, 'Clan Crushbone')
    assert (report['terrain_faces'], report['static_faces'], report['placements']) == (21834, 9576, 178)
    assert len(report['rows']) == 5
    assert [len(r['source_intersections']) for r in report['rows']] == [0, 4, 2, 2, 4]
    assert [len(r['diffuse_heights']) for r in report['rows']] == [0, 3, 1, 1, 3]
    assert all('source_refusal' in r and not r['usable_destination'] for r in report['rows'])
    assert not report['label_z_used_for_floor_selection'] and not report['route_accepted']
    assert not report['game_input_sent'] and not report['current_character_position']
    proposals = assets.annotation_report(body_height=6.)['rows']
    assert [i for i, r in enumerate(proposals) if 'floor_seed_proposal' in r] == [2, 3]
    assert all(not r['usable_destination'] for r in proposals)
    with pytest.raises(ValueError): assets.planner.ground.triangles[0, 0, 0] = 99.
    with pytest.raises(ValueError): assets.planner.source.source_minimum[0, 0] = 99.
