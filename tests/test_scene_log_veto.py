from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from eql_automation.scene_log_veto import SceneLogVeto, classify_log_veto


PREFIX = "[Sat Nov 14 01:00:00 2026] "


def append(path, body):
    with path.open("a") as output:
        output.write(PREFIX + body + "\n")


def monitor(path, **kwargs):
    return SceneLogVeto(path, expected_character="Probe", expected_server="private",
                        cancel_generation=7, **kwargs)


@pytest.mark.parametrize("body,reason", [
    ("Training dummy hits YOU for 2 points of damage.", "incoming_attack"),
    ("Training dummy hits YOU for 1 point of damage.", "incoming_attack"),
    ("Training dummy frenzies on YOU for 18 points of damage. (Riposte)", "incoming_attack"),
    ("Training dummy tries to hit YOU, but misses! (Riposte)", "incoming_attack"),
    ("Training dummy tries to bash YOU, but YOU are INVULNERABLE!", "incoming_attack"),
    ("You have taken 1 damage from Test Spell by a training dummy.", "incoming_attack"),
    ("You were hit by non-melee for 5 damage.", "incoming_attack"),
    ("You are stunned!", "player_hazard"),
    ("YOU are drowning!", "player_hazard"),
    ("YOU were injured by falling.", "player_hazard"),
    ("You have been slain by a training dummy!", "death"),
    ("Auto attack is on.", "native_melee_on"),
    ("LOADING, PLEASE WAIT...", "zone_transition"),
    ("You have entered Test Zone.", "zone_transition"),
    ("Targeted (Player): Test Player", "target_selection"),
    ("Targeted (Unrecognized):", "target_selection"),
    ("LOADING, PLEASE WAIT", "unrecognized_safety_message"),
    ("You have entered Test Zone", "unrecognized_safety_message"),
    ("Auto attack is unknown.", "unrecognized_safety_message"),
])
def test_observed_message_shapes_latch_and_never_grant_permission(tmp_path, body, reason):
    path = tmp_path / "eqlog_Probe_private.txt"
    path.touch()
    reader = monitor(path)
    append(path, body)
    observed = reader.poll()
    assert observed.reason == reason and observed.continuity_available
    assert observed.log_line_seq == 1 and observed.input_authorized is False
    append(path, "Auto attack is off.")
    assert reader.poll() is observed
    with pytest.raises(FrozenInstanceError):
        observed.reason = None


@pytest.mark.parametrize("body", [
    "Auto attack is off.", "You are no longer stunned.", "Your Location is 1, 2, 3",
    "Player tells General:1, 'Auto attack is on.'",
    "Player says, 'Training dummy hits YOU for 2 points of damage.'",
    "Player tells you, 'You have been slain by a training dummy!'",
])
def test_whole_message_matching_does_not_read_keywords_inside_chat(body):
    assert classify_log_veto(body) is None


def test_history_skipped_and_quiet_observation_never_claims_safety(tmp_path):
    path = tmp_path / "eqlog_Probe_private.txt"
    append(path, "Auto attack is on.")
    reader = monitor(path)
    for _ in range(2):
        record = reader.poll()
        assert record.reason is None and record.continuity_available
        assert record.log_line_seq == 0 and record.input_authorized is False
        assert not any(hasattr(record, key) for key in ("safe", "clear", "no_incoming_attack"))
    append(path, "Auto attack is on.")
    assert reader.poll().reason == "native_melee_on"


@pytest.mark.parametrize("change", ["missing", "deleted", "replacement", "truncate", "rewrite",
                                   "backlog", "partial", "baseline_partial", "malformed", "encoding",
                                   "source_clock", "read_failure"])
def test_continuity_loss_latches_even_if_log_recovers(tmp_path, change):
    path = tmp_path / "eqlog_Probe_private.txt"
    if change != "missing":
        append(path, "old history" * 3)
    if change == "baseline_partial":
        with path.open("ab") as output:
            output.write(b"unfinished")
    reader = monitor(path, max_bytes=256)
    if change == "deleted": path.unlink()
    elif change == "replacement":
        path.rename(tmp_path / "previous.txt")
        path.touch()
    elif change == "truncate": path.write_bytes(b"")
    elif change == "rewrite": path.write_bytes(b"x" * path.stat().st_size)
    elif change == "backlog":
        with path.open("ab") as output: output.write(b"x" * 257)
    elif change == "partial":
        with path.open("ab") as output: output.write(PREFIX.encode() + b"Training dummy hits")
    elif change == "malformed":
        with path.open("a") as output: output.write("without timestamp\n")
    elif change == "encoding":
        with path.open("ab") as output: output.write(PREFIX.encode() + b"\xff\n")
    elif change == "source_clock":
        append(path, "first")
        assert reader.poll().reason is None
        with path.open("a") as output:
            output.write("[Sat Nov 14 00:59:59 2026] earlier\n")
    elif change == "read_failure":
        path.unlink()
        path.mkdir()
    record = reader.poll()
    assert record.reason and record.continuity_available is False
    if path.is_dir(): path.rmdir()
    path.write_bytes(b"")
    append(path, "Auto attack is off.")
    assert reader.poll() is record


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, None, -1.])
def test_bad_observation_clock_latches(tmp_path, bad):
    path = tmp_path / "eqlog_Probe_private.txt"
    path.touch()
    now = [10.]
    reader = monitor(path, clock=lambda: now[0])
    now[0] = bad
    result = reader.poll()
    assert result.reason and not result.continuity_available
    now[0] = 11.
    assert reader.poll() is result


def test_clock_reversal_during_read_and_equal_source_seconds(tmp_path):
    path = tmp_path / "eqlog_Probe_private.txt"
    path.touch()
    values = iter([10., 10., 11., 10.5])
    reader = monitor(path, clock=lambda: next(values))
    append(path, "first")
    append(path, "second")
    result = reader.poll()
    assert result.log_line_seq == 2 and not result.continuity_available
    assert result.log_local_time == datetime(2026, 11, 14, 1, 0, 0)


def test_filename_and_generation_binding(tmp_path):
    with pytest.raises(ValueError): monitor(tmp_path / "eqlog_Other_private.txt")
    with pytest.raises(ValueError):
        SceneLogVeto(tmp_path / "eqlog_Probe_private.txt", expected_character="Probe",
                     expected_server="private", cancel_generation=True)
