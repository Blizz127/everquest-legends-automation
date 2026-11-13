from pathlib import Path

import pytest

from eql_automation.target_log import TargetLogMonitor


def append(path: Path, *bodies: str, stamp: str = "Fri Nov 13 09:30:00 2026") -> None:
    with path.open("a", encoding="utf-8") as source:
        for body in bodies:
            source.write(f"[{stamp}] {body}\n")


def test_existing_history_is_skipped_and_same_name_is_not_unique(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    append(path, "Targeted (NPC): a goblin")
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    assert reader.poll(now=1.0) is None
    append(path, "Targeted (NPC): a goblin", "Targeted (NPC): a goblin")
    hint = reader.poll(now=2.0)
    assert hint is not None
    assert hint.display_name == "a goblin"
    assert hint.kind == "npc"
    assert hint.explicit_selection_count == 2
    assert not hint.uniquely_verified
    assert reader.poll(now=2.1) is None  # No new selection event.


def test_zone_death_and_targetless_messages_revoke_hints(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    path.touch()
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    for index, revocation in enumerate(("Consider whom?", "LOADING, PLEASE WAIT...",
                                        "You have entered The Greater Faydark.", "You died")):
        append(path, "Targeted (NPC): a goblin")
        assert reader.poll(now=2.0 + index) is not None
        append(path, revocation)
        assert reader.poll(now=2.1 + index) is None
        assert reader.last_invalidation


def test_log_replacement_and_timestamp_regression_never_restore_hint(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    path.touch()
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    append(path, "Targeted (NPC): a goblin", stamp="Fri Nov 13 09:31:00 2026")
    assert reader.poll(now=1.0) is not None
    append(path, "Targeted (NPC): a goblin", stamp="Fri Nov 13 09:30:00 2026")
    assert reader.poll(now=2.0) is None
    assert reader.last_invalidation == "log time moved backward"
    old = tmp_path / "old.log"
    path.rename(old)
    append(path, "Targeted (NPC): stale target")
    assert reader.poll(now=3.0) is None
    assert reader.last_invalidation == "log reset"


def test_character_binding_and_bad_observation_time(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    path.touch()
    with pytest.raises(ValueError):
        TargetLogMonitor(path, expected_character="Owner", expected_server="Private")
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    append(path, "Targeted (NPC): a goblin")
    assert reader.poll(now=1.0) is not None
    with pytest.raises(ValueError):
        reader.poll(now=float("nan"))
    assert reader.last_logged_hint is None
    with pytest.raises(ValueError):
        reader.poll(now=0.5)
    assert reader.last_invalidation == "observation time moved backward"


def test_unrecognized_selection_and_bad_line_revoke_prior_hint(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    path.touch()
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    for index, body in enumerate(("Targeted (Pet): a wolf", "Targeted (NPC):",
                                  "Targeted (NPC):   ", "not a timestamped game line")):
        append(path, "Targeted (NPC): a goblin")
        assert reader.poll(now=2.0 + index) is not None
        if body == "not a timestamped game line":
            with path.open("a", encoding="utf-8") as source:
                source.write(body + "\n")
        else:
            append(path, body)
        assert reader.poll(now=2.1 + index) is None
        assert reader.last_logged_hint is None


def test_log_read_failure_revokes_hint(tmp_path: Path):
    path = tmp_path / "eqlog_Fresh_Private.txt"
    path.touch()
    reader = TargetLogMonitor(path, expected_character="Fresh", expected_server="Private")
    append(path, "Targeted (NPC): a goblin")
    assert reader.poll(now=1.0) is not None
    path.unlink()
    path.mkdir()
    with pytest.raises((IsADirectoryError, ValueError)):
        reader.poll(now=2.0)
    assert reader.last_logged_hint is None
