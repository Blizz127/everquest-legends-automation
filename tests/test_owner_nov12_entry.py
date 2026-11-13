from pathlib import Path

import pytest

from tools.owner_nov12_entry import verify_snapshot


def test_snapshot_guard_rejects_missing_and_changed_sources(tmp_path: Path):
    with pytest.raises(RuntimeError, match="missing"):
        verify_snapshot(tmp_path)
    for name in ("rotation_core.py", "rotation_engine.py", "eql_rotation.py"):
        (tmp_path / name).write_text("changed source")
    with pytest.raises(RuntimeError, match="source mismatch"):
        verify_snapshot(tmp_path)
