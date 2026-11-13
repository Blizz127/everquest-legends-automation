from pathlib import Path

import pytest

from eql_automation.transition_log import TransitionLogReader, TransitionTracker


ZONES = {"The Greater Faydark": 54, "Clan Crushbone": 58}


def line(minute: int, second: int, body: str) -> str:
    return f"[Fri Nov 13 09:{minute:02d}:{second:02d} 2026] {body}\r\n"


def sequence(*, source_minute=10, dest_minute=10, dest_second=15):
    return (
        line(10, 0, "You have entered The Greater Faydark."),
        line(source_minute, 1, "Your Location is 1, 2, 3"),
        line(10, 5, "LOADING, PLEASE WAIT..."),
        line(10, 10, "You have entered Clan Crushbone."),
        line(dest_minute, dest_second, "Your Location is 4, 5, 6"),
    )


def test_fresh_manual_transition_pairs_locations_without_claiming_spawn():
    tracker = TransitionTracker(ZONES)
    observed = [tracker.consume(text, received_monotonic=100, log_epoch=1)
                for text in sequence()]
    pair = observed[-1]
    assert pair is not None
    assert pair.source_fix.zone_id == 54 and pair.destination_fix.zone_id == 58
    assert pair.source_fix.raw_location == (1.0, 2.0, 3.0)
    assert pair.destination_fix.raw_location == (4.0, 5.0, 6.0)
    assert pair.source_fix.line_seq < pair.loading_line_seq < pair.entered_line_seq < pair.destination_fix.line_seq
    assert not pair.route_accepted and not pair.spawn_coordinate_verified
    assert tracker.consume(line(10, 16, "Your Location is 7, 8, 9"),
                           received_monotonic=101, log_epoch=1) is None


def test_stale_source_or_destination_fix_never_pairs():
    source_stale = TransitionTracker(ZONES)
    entries = (
        line(10, 0, "You have entered The Greater Faydark."),
        line(10, 1, "Your Location is 1, 2, 3"),
        line(10, 35, "LOADING, PLEASE WAIT..."),
        line(10, 40, "You have entered Clan Crushbone."),
        line(10, 41, "Your Location is 4, 5, 6"),
    )
    assert all(source_stale.consume(text, received_monotonic=1,
                                    log_epoch=1) is None for text in entries)
    destination_stale = TransitionTracker(ZONES)
    assert all(destination_stale.consume(text, received_monotonic=1,
                                         log_epoch=1) is None
               for text in sequence(dest_minute=10, dest_second=41))


def test_same_zone_unknown_entry_chat_spoof_and_clock_rollback_fail_closed():
    same = TransitionTracker(ZONES)
    lines = list(sequence())
    lines[3] = line(10, 10, "You have entered The Greater Faydark.")
    assert all(same.consume(text, received_monotonic=1,
                            log_epoch=1) is None for text in lines)
    unknown = TransitionTracker(ZONES)
    lines[3] = line(10, 10, "You have entered An Unknown Zone.")
    assert all(unknown.consume(text, received_monotonic=1,
                               log_epoch=1) is None for text in lines)
    spoof = TransitionTracker(ZONES)
    lines = list(sequence())
    lines[2] = line(10, 5, "Other says, 'LOADING, PLEASE WAIT...'")
    assert all(spoof.consume(text, received_monotonic=1,
                             log_epoch=1) is None for text in lines)
    tracker = TransitionTracker(ZONES)
    tracker.consume(line(10, 0, "You have entered The Greater Faydark."),
                    received_monotonic=2, log_epoch=1)
    assert tracker.consume(line(10, 1, "Your Location is 1, 2, 3"),
                           received_monotonic=1, log_epoch=1) is None
    assert tracker.zone is None


def test_intervening_location_or_malformed_entry_breaks_pairing():
    base = list(sequence())
    for intrusion in (
        line(10, 7, "Your Location is 9, 9, 9"),
        line(10, 7, "You have entered An Unknown Zone"),
        line(10, 7, "LOADING, PLEASE WAIT"),
    ):
        tracker = TransitionTracker(ZONES)
        rows = base[:3] + [intrusion] + base[3:]
        assert all(tracker.consume(text, received_monotonic=1,
                                   log_epoch=1) is None for text in rows)
    zone_ids = dict(ZONES)
    tracker = TransitionTracker(zone_ids)
    zone_ids.clear()
    assert tracker.zone_ids == ZONES


def test_tail_skips_history_and_invalidates_replaced_log(tmp_path: Path):
    log = tmp_path / "eqlog_Probe_private.txt"
    zones = tmp_path / "ZoneNames.txt"
    zones.write_text("54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n")
    log.write_text("".join(sequence()))
    reader = TransitionLogReader(log, zones, expected_character="Probe",
                                 expected_server="private")
    assert reader.poll(now=1) == []
    with log.open("a") as stream:
        stream.writelines(sequence())
    pairs = reader.poll(now=2)
    assert len(pairs) == 1 and not pairs[0].spawn_coordinate_verified
    replacement = tmp_path / "replacement.log"
    replacement.write_text("".join(sequence()))
    replacement.replace(log)
    assert reader.poll(now=3) == []
    with log.open("a") as stream:
        stream.write(line(10, 16, "Your Location is 7, 8, 9"))
    assert reader.poll(now=4) == []
    with pytest.raises(ValueError, match="clock"):
        reader.poll(now=2)


def test_fresh_test_character_can_include_first_created_log(tmp_path: Path):
    log = tmp_path / "eqlog_Probe_private.txt"
    zones = tmp_path / "ZoneNames.txt"
    zones.write_text("54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n")
    fresh = TransitionLogReader(log, zones, expected_character="Probe",
                                expected_server="private",
                                fresh_test_character=True)
    log.write_text("".join(sequence()))
    assert len(fresh.poll(now=1)) == 1
    with pytest.raises(ValueError, match="Fresh test-character"):
        TransitionLogReader(log, zones, expected_character="Probe",
                            expected_server="private",
                            fresh_test_character=1)
