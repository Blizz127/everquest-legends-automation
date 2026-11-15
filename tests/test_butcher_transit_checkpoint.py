import json
import importlib.util
from hashlib import sha256
from pathlib import Path
import sys

import pytest

from tools.audit_butcher_camp_transit import write_checkpoint


def test_alias_launch_pins_canonical_sources_before_loading_geometry(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    alias = tmp_path/'home-alias'
    alias.symlink_to(project, target_is_directory=True)
    spec = importlib.util.spec_from_file_location(
        'butcher_alias_launch', alias/'tools/audit_butcher_camp_transit.py')
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setattr(sys, 'path', list(sys.path))
    spec.loader.exec_module(module)
    seen = []
    class CheckpointReached(Exception):
        pass
    def stop_before_geometry(output, record):
        seen.append(record)
        raise CheckpointReached
    monkeypatch.setattr(module, 'write_checkpoint', stop_before_geometry)
    with pytest.raises(CheckpointReached):
        module.run(tmp_path/'unused.json', destination='goblin', wall_budget=30., cpu_budget=5.)
    assert module.PROJECT == project
    assert module.SOURCE_SCRIPT == project/'tools/audit_butcher_camp_transit.py'
    pins = seen[0]['code_sha256']
    for name in ('audit_butcher_camp_transit', 'source_walk_repairs',
                 'source_transit_centers', 'source_walk_prefix',
                 'source_walk_shortcuts', 'source_transit_departures'):
        relative = 'tools/'+name+'.py'
        assert pins[relative] == sha256((project/relative).read_bytes()).hexdigest()
    assert not (tmp_path/'unused.json').exists()


def test_interrupted_checkpoint_keeps_old_record_and_can_save_final_refusal(tmp_path, monkeypatch):
    path = tmp_path/'result.json'
    write_checkpoint(path, {'completed': False, 'stage': 'checking'})
    original = json.dump
    def interrupted(record, stream, **kwargs):
        stream.write('{')
        raise TimeoutError('offline budget')
    monkeypatch.setattr(json, 'dump', interrupted)
    with pytest.raises(TimeoutError): write_checkpoint(path, {'completed': False, 'stage': 'later'})
    assert json.loads(path.read_text()) == {'completed': False, 'stage': 'checking'}
    assert list(tmp_path.iterdir()) == [path]
    monkeypatch.setattr(json, 'dump', original)
    write_checkpoint(path, {'completed': True, 'status': 'refused'})
    assert json.loads(path.read_text()) == {'completed': True, 'status': 'refused'}
