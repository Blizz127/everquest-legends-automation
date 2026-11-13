from pathlib import Path

import pytest

from eql_automation.target import inspect_eqhost, require_private_target


def test_official_target_cannot_be_bound_as_private(tmp_path: Path):
    path = tmp_path / "eqhost.txt"
    path.write_text("[LoginServer]\nHost=lvseqns-livl01.everquestlegends.com:15900\n")
    actual = inspect_eqhost(path)
    assert actual.official_domain is True
    with pytest.raises(PermissionError, match="Daybreak official"):
        require_private_target(actual, expected_host=actual.host,
                               expected_port=actual.port,
                               expected_eqhost_sha256=actual.eqhost_sha256)


def test_private_target_requires_exact_reviewed_endpoint_and_hash(tmp_path: Path):
    path = tmp_path / "eqhost.txt"
    path.write_text("[LoginServer]\nHost=private.example.test:5998\n")
    actual = inspect_eqhost(path)
    assert actual.official_domain is False
    with pytest.raises(PermissionError, match="reviewed target"):
        require_private_target(actual, expected_host=actual.host,
                               expected_port=5998, expected_eqhost_sha256="0" * 64)
    require_private_target(actual, expected_host="PRIVATE.EXAMPLE.TEST",
                           expected_port=5998,
                           expected_eqhost_sha256=actual.eqhost_sha256)
