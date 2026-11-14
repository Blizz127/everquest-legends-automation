from pathlib import Path

import pytest

from eql_automation.location_log import (
    LocationLogReader, NonReplayingLogTail, parse_client_log_line,
    parse_raw_location, unique_client_zone_ids,
)


def stamped(second: int, body: str) -> str:
    return f"[Thu Nov 05 19:49:{second:02d} 2026] {body}\r\n"


def fixture_paths(tmp_path: Path) -> tuple[Path, Path]:
    zones = tmp_path / "ZoneNames.txt"
    zones.write_text("1^Example One^0^0\n2^Example Two^0^0\n")
    return tmp_path / "eqlog_Probe_private.txt", zones


def reader_for(log: Path, zones: Path, *, max_bytes: int = 512 * 1024):
    return LocationLogReader(log, zones, expected_character="Probe",
                             expected_server="private", max_bytes=max_bytes)


def test_exact_location_parser_keeps_raw_axis_order():
    assert parse_raw_location("Your Location is -1.25, 2.00, +3") == (-1.25, 2.0, 3.0)
    for body in ("Your Location is 1, 2", "Your Location is 1, 2, 3, 4",
                 "Your Location is nan, 2, 3", "Your Location is inf, 2, 3",
                 "Your Location is 1e99, 2, 3", "Other: Your Location is 1, 2, 3"):
        assert parse_raw_location(body) is None
    assert parse_client_log_line(stamped(11, "Your Location is 1, 2, 3")) is not None
    assert parse_client_log_line("[invalid] Your Location is 1, 2, 3") is None


def test_location_reader_skips_history_and_requires_entered_zone(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.write_text(stamped(1, "You have entered Example One.") +
                   stamped(2, "Your Location is 99, 99, 99"))
    reader = reader_for(log, zones)
    assert reader.poll(now=1) == []
    assert reader.latest is None and reader.zone_id is None
    with log.open("a") as source:
        source.write(stamped(3, "Your Location is 1, 2, 3"))
    assert reader.poll(now=2) == []  # History cannot supply a trusted zone.
    with log.open("a") as source:
        source.write(stamped(4, "You have entered Example One.") +
                     stamped(5, "Your Location is -1.25, 2.00, 3.50"))
    fixes = reader.poll(now=3)
    assert len(fixes) == 1
    assert fixes[0].zone_id == 1
    assert fixes[0].raw_coordinates == (-1.25, 2.0, 3.5)
    assert fixes[0].coordinates_aligned_to_wld is False
    assert fixes[0].received_monotonic == 3
    assert fixes[0].log_line_seq == 1
    assert fixes[0].zone_generation > 0


def test_loading_and_zone_entry_invalidate_previous_position(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3"))
    assert len(reader.poll(now=1)) == 1
    previous_epoch = reader.latest.log_epoch
    with log.open("a") as source:
        source.write(stamped(3, "LOADING, PLEASE WAIT...") +
                     stamped(4, "Your Location is 4, 5, 6"))
    assert reader.poll(now=2) == []
    assert reader.latest is None and reader.zone_id is None
    with log.open("a") as source:
        source.write(stamped(5, "You have entered Example Two."))
    assert reader.poll(now=3) == []
    assert reader.zone_id == 2 and reader.latest is None
    with log.open("a") as source:
        source.write(stamped(6, "Your Location is 7, 8, 9"))
    fixes = reader.poll(now=4)
    assert len(fixes) == 1 and fixes[0].zone_id == 2
    assert fixes[0].log_epoch == previous_epoch


def test_same_batch_loading_and_new_zone_drop_old_zone_fixes(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3") +
                     stamped(3, "LOADING, PLEASE WAIT..."))
    assert reader.poll(now=1) == []
    assert reader.latest is None and reader.zone_id is None
    with log.open("a") as source:
        source.write(stamped(4, "You have entered Example One.") +
                     stamped(5, "Your Location is 4, 5, 6") +
                     stamped(6, "You have entered Example Two.") +
                     stamped(7, "Your Location is 7, 8, 9"))
    fixes = reader.poll(now=2)
    assert len(fixes) == 1
    assert fixes[0].zone_id == 2 and fixes[0].raw_coordinates == (7, 8, 9)


def test_partial_location_waits_for_newline(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("ab") as source:
        source.write(stamped(1, "You have entered Example One.").encode())
        source.write(stamped(2, "Your Location is 1, 2, 3").encode()[:-2])
    assert reader.poll(now=1) == []
    assert reader.zone_id == 1
    with log.open("ab") as source:
        source.write(b"\r\n")
    fixes = reader.poll(now=2)
    assert len(fixes) == 1 and fixes[0].raw_coordinates == (1.0, 2.0, 3.0)


def test_malformed_position_or_transition_invalidates_pending_fix(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3") +
                     stamped(3, "Your Location is nan, 2, 3"))
    assert reader.poll(now=1) == []
    assert reader.latest is None and reader.zone_id == 1
    with log.open("a") as source:
        source.write(stamped(4, "Your Location is 4, 5, 6") +
                     "[invalid] LOADING, PLEASE WAIT...\n")
    assert reader.poll(now=2) == []
    assert reader.latest is None and reader.zone_id is None


@pytest.mark.parametrize('body', [
    "Logging to 'eqlog.txt' is now *ON*.",
    "Logging to 'eqlog.txt' is now *OFF*.",
    "Logging to 'custom.txt' is now *ON*.",
    "Logging to 'eqlog.txt' is now",
    "LOADING, PLEASE WAIT", "You have entered Example Two",
])
def test_logging_restart_or_incomplete_transition_discards_zone_and_same_batch_fix(tmp_path, body):
    log, zones = fixture_paths(tmp_path); log.touch()
    reader = reader_for(log, zones)
    with log.open('a') as out:
        out.write(stamped(1, 'You have entered Example One.') +
                  stamped(2, 'Your Location is 1, 2, 3') + stamped(3, body) +
                  stamped(4, 'Your Location is 4, 5, 6'))
    assert reader.poll(now=1) == []
    assert reader.zone_id is None and reader.latest is None
    with log.open('a') as out:
        out.write(stamped(5, 'You have entered Example Two.') +
                  stamped(6, 'Your Location is 7, 8, 9'))
    fix, = reader.poll(now=2)
    assert fix.zone_id == 2 and fix.raw_coordinates == (7., 8., 9.)


def test_logging_notice_inside_chat_does_not_change_zone(tmp_path):
    log, zones = fixture_paths(tmp_path); log.touch()
    reader = reader_for(log, zones)
    with log.open('a') as out:
        out.write(stamped(1, 'You have entered Example One.') +
                  stamped(2, "Player says, 'Logging to 'eqlog.txt' is now *ON*.'") +
                  stamped(3, 'Your Location is 1, 2, 3'))
    fix, = reader.poll(now=1)
    assert fix.zone_id == 1


def test_unknown_or_ambiguous_zone_does_not_emit_fix(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    zones.write_text("1^Example One^0^0\n2^Example One^0^0\n")
    unique, ambiguous = unique_client_zone_ids(zones)
    assert "Example One" not in unique and ambiguous == {"Example One"}
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3") +
                     stamped(3, "You have entered Unknown Place.") +
                     stamped(4, "Your Location is 4, 5, 6"))
    assert reader.poll(now=1) == []
    assert reader.latest is None and reader.zone_id is None


def test_older_log_timestamp_invalidates_zone_until_new_entry(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(50, "You have entered Example One.") +
                     stamped(51, "Your Location is 1, 2, 3"))
    assert len(reader.poll(now=1)) == 1
    with log.open("a") as source:
        source.write(stamped(9, "Your Location is 4, 5, 6") +
                     stamped(10, "Your Location is 7, 8, 9"))
    assert reader.poll(now=2) == []
    assert reader.zone_id is None and reader.latest is None
    with log.open("a") as source:
        source.write(stamped(11, "You have entered Example One.") +
                     stamped(12, "Your Location is 10, 11, 12"))
    assert len(reader.poll(now=3)) == 1


def test_rotation_truncation_and_backlog_drop_untrusted_content(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones, max_bytes=160)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3"))
    assert len(reader.poll(now=1)) == 1
    first_epoch = reader.latest.log_epoch
    replacement = tmp_path / "replacement"
    replacement.write_text(stamped(3, "You have entered Example Two.") +
                           stamped(4, "Your Location is 4, 5, 6"))
    replacement.replace(log)
    assert reader.poll(now=2) == []
    assert reader.zone_id is None and reader.latest is None
    assert reader.tail.epoch > first_epoch
    with log.open("a") as source:
        source.write(stamped(5, "Your Location is 7, 8, 9"))
    assert reader.poll(now=3) == []
    with log.open("a") as source:
        source.write(stamped(6, "You have entered Example Two.") +
                     stamped(7, "Your Location is 10, 11, 12"))
    assert len(reader.poll(now=4)) == 1
    log.write_text(stamped(8, "You have entered Example One.") +
                   stamped(9, "Your Location is 13, 14, 15"))
    assert reader.poll(now=5) == []  # Same inode rewrite changes the anchor.
    assert reader.latest is None
    with log.open("a") as source:
        source.write("x" * 161 + "\n")
    assert reader.poll(now=6) == []  # Oversized backlog is skipped.
    assert reader.latest is None


def test_reader_requires_expected_character_log_and_finite_poll_time(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    with pytest.raises(ValueError, match="expected character"):
        LocationLogReader(log, zones, expected_character="SomeoneElse",
                          expected_server="private")
    reader = reader_for(log, zones)
    with pytest.raises(ValueError, match="finite"):
        reader.poll(now=float("nan"))
    assert reader.latest is None
    assert NonReplayingLogTail(log).poll() == ([], False)


def test_same_inode_regrowth_with_changed_anchor_skips_history(tmp_path: Path):
    log, _zones = fixture_paths(tmp_path)
    log.write_bytes(b"old\n" * 40)
    tail = NonReplayingLogTail(log)
    assert tail.poll() == ([], True)
    with log.open("ab") as source:
        source.write(b"fresh\n")
    assert tail.poll() == (["fresh"], False)
    with log.open("r+b") as source:
        source.seek(0)
        source.write(b"changed\n" * 40)
        source.seek(0, 2)
        source.write(b"new but untrusted\n")
    assert tail.poll() == ([], True)


def test_rotated_log_accepts_only_fresh_appends_with_new_time_baseline(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(50, "You have entered Example One.") +
                     stamped(51, "Your Location is 1, 2, 3"))
    assert len(reader.poll(now=1)) == 1
    replacement = tmp_path / "old-history"
    replacement.write_text(stamped(1, "You have entered Example Two.") +
                           stamped(2, "Your Location is 9, 9, 9"))
    replacement.replace(log)
    assert reader.poll(now=2) == []
    assert reader.latest is None and reader.zone_id is None
    with log.open("a") as source:
        source.write(stamped(3, "You have entered Example Two.") +
                     stamped(4, "Your Location is 4, 5, 6"))
    fixes = reader.poll(now=3)
    assert len(fixes) == 1
    assert fixes[0].zone_id == 2 and fixes[0].raw_coordinates == (4, 5, 6)


def test_poll_clock_rollback_clears_zone_and_requires_new_entry(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3"))
    assert len(reader.poll(now=5)) == 1
    with log.open("a") as source:
        source.write(stamped(3, "Your Location is 4, 5, 6"))
    with pytest.raises(ValueError, match="moved backward"):
        reader.poll(now=4)
    assert reader.latest is None and reader.zone_id is None
    assert reader.poll(now=6) == []  # Pending fix cannot rebind an old zone.
    with log.open("a") as source:
        source.write(stamped(4, "You have entered Example Two.") +
                     stamped(5, "Your Location is 7, 8, 9"))
    fixes = reader.poll(now=7)
    assert len(fixes) == 1 and fixes[0].zone_id == 2


def test_location_line_identity_and_zone_generation_do_not_claim_request_identity(tmp_path: Path):
    log, zones = fixture_paths(tmp_path)
    log.touch()
    reader = reader_for(log, zones)
    with log.open("a") as source:
        source.write(stamped(1, "You have entered Example One.") +
                     stamped(2, "Your Location is 1, 2, 3") +
                     stamped(2, "Your Location is 1, 2, 3"))
    first, second = reader.poll(now=1)
    assert second.log_line_seq == first.log_line_seq + 1
    assert second.zone_generation == first.zone_generation
    assert second.raw_coordinates == first.raw_coordinates
    with log.open("a") as source:
        source.write(stamped(3, "LOADING, PLEASE WAIT...") +
                     stamped(4, "You have entered Example One.") +
                     stamped(5, "Your Location is 1, 2, 3"))
    after = reader.poll(now=2)
    assert len(after) == 1
    assert after[0].log_line_seq == second.log_line_seq + 1
    assert after[0].zone_generation > second.zone_generation
    assert after[0].log_epoch == second.log_epoch  # Zone change is separate from log reset.
