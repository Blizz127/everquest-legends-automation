import json

import pytest

from tools.audit_butcher_camp_transit import write_checkpoint


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
