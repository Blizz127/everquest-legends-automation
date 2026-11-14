from hashlib import sha256

import pytest

from eql_automation.installed_region_model import verify_installed_region_model


def files(tmp_path, monkeypatch):
    import eql_automation.installed_region_model as module
    import eql_automation.native_region_policy as policy_module
    for name, attr, data in (('eqgame.exe','CLIENT_SHA256',b'synthetic client'),
                             ('EQGraphics.dll','ENGINE_SHA256',b'synthetic renderer')):
        (tmp_path/name).write_bytes(data)
        for target in (module, policy_module):
            monkeypatch.setattr(target, attr, sha256(data).hexdigest())
    return verify_installed_region_model(tmp_path)


def test_hashes_real_fixture_bytes_without_claiming_memory_or_input(tmp_path, monkeypatch):
    model = files(tmp_path, monkeypatch)
    model.check(); record=model.record()
    assert record['installed_file_hashes_verified']
    assert not record['runtime_memory_verified'] and not record['input_authorized']
    assert len(model.files)==2


@pytest.mark.parametrize('change', ['rewrite', 'replace', 'symlink', 'remove'])
def test_changed_file_identity_refuses_without_rehash_or_replacement(tmp_path, monkeypatch, change):
    model=files(tmp_path, monkeypatch); path=tmp_path/'eqgame.exe'
    data=path.read_bytes()
    if change=='rewrite': path.write_bytes(data)
    elif change=='replace':
        replacement=tmp_path/'other';replacement.write_bytes(data);replacement.replace(path)
    elif change=='symlink':
        path.unlink();other=tmp_path/'other';other.write_bytes(data);path.symlink_to(other)
    else: path.unlink()
    with pytest.raises((ValueError, OSError)): model.check()


def test_wrong_hash_and_symlink_refuse_initial_binding(tmp_path, monkeypatch):
    files(tmp_path, monkeypatch)
    path=tmp_path/'eqgame.exe';path.write_bytes(b'wrong')
    with pytest.raises(ValueError,match='hash'): verify_installed_region_model(tmp_path)
    path.unlink();other=tmp_path/'other';other.write_bytes(b'synthetic client');path.symlink_to(other)
    with pytest.raises(ValueError,match='Unsupported'): verify_installed_region_model(tmp_path)
