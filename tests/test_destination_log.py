from datetime import datetime, timedelta
import json
from pathlib import Path
import pytest

from eql_automation.destination_log import DestinationLogReader, DestinationTracker
from eql_automation import watch_destination


BASE = datetime.now().replace(microsecond=0)


def line(second: int, body: str) -> str:
    stamp = (BASE + timedelta(seconds=second)).strftime("%a %b %d %H:%M:%S %Y")
    return f"[{stamp}] {body}\r\n"


def fixture(tmp_path: Path):
    game = tmp_path / "game"
    (game / "Logs").mkdir(parents=True)
    (game / "Resources").mkdir()
    log = game / "Logs/eqlog_Legira_freeport.txt"
    zones = game / "Resources/ZoneNames.txt"
    zones.write_text("54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n")
    return game, log, zones


def reader(log, zones):
    return DestinationLogReader(log, zones, expected_character="Legira",
                                expected_server="freeport",
                                destination="Clan Crushbone")


@pytest.mark.parametrize('notice', ["Logging to 'eqlog.txt' is now *OFF*.",
                                    "Logging to 'eqlog.txt' is now *ON*."])
@pytest.mark.parametrize('malformed', [False, True])
def test_logging_boundary_cannot_bridge_destination_entry(notice, malformed):
    tracker = DestinationTracker('Clan Crushbone', 58)
    rows = [line(0, 'LOADING, PLEASE WAIT...'), line(1, 'You have entered Clan Crushbone.'),
            '[bad timestamp] '+notice if malformed else line(2, notice),
            line(3, 'Your Location is 1, 2, 3')]
    assert all(tracker.consume(row, received_monotonic=100+i, log_epoch=0) is None
               for i, row in enumerate(rows))


def test_direct_tracker_refuses_reversed_receipt_clock():
    tracker = DestinationTracker('Clan Crushbone', 58)
    tracker.consume(line(0, 'LOADING, PLEASE WAIT...'), received_monotonic=10, log_epoch=0)
    tracker.consume(line(1, 'You have entered Clan Crushbone.'), received_monotonic=9, log_epoch=0)
    assert tracker.consume(line(2, 'Your Location is 1, 2, 3'),
                           received_monotonic=11, log_epoch=0) is None


def test_existing_source_zone_history_is_skipped_but_fresh_destination_is_captured(tmp_path):
    _game, log, zones = fixture(tmp_path)
    log.write_text(line(0, "You have entered The Greater Faydark.") +
                   line(1, "Your Location is 10, 20, 30"))
    watcher = reader(log, zones)
    with log.open("a") as source:
        source.write(line(2, "Your Location is 11, 21, 31") +
                     line(3, "LOADING, PLEASE WAIT...") +
                     line(8, "You have entered Clan Crushbone.") +
                     line(9, "Your Location is -1.50, 2.25, 3.00"))
    observations = watcher.poll(now=100)
    assert len(observations) == 1
    found = observations[0]
    assert found.zone_id == 58 and found.raw_location == (-1.5, 2.25, 3.0)
    assert (found.preloading_line_seq, found.loading_line_seq,
            found.entered_line_seq, found.location_line_seq) == (1, 2, 3, 4)
    assert found.preloading_raw_location == (11.0, 21.0, 31.0)
    assert not any((found.source_zone_verified, found.crossing_method_verified,
                    found.spawn_coordinate_verified, found.route_accepted,
                    found.real_client_movement_accepted))


def test_late_or_first_malformed_fix_and_other_entry_do_not_capture(tmp_path):
    _game, log, zones = fixture(tmp_path)
    log.touch()
    watcher = reader(log, zones)
    with log.open("a") as source:
        source.write(line(0, "LOADING, PLEASE WAIT...") +
                     line(4, "You have entered Clan Crushbone.") +
                     line(35, "Your Location is 1, 2, 3") +
                     line(36, "Your Location is 4, 5, 6"))
    assert watcher.poll(now=100) == []
    with log.open("a") as source:
        source.write(line(37, "LOADING, PLEASE WAIT...") +
                     line(38, "You have entered Other Zone.") +
                     line(39, "Your Location is 7, 8, 9") +
                     line(40, "LOADING, PLEASE WAIT...") +
                     line(41, "You have entered Clan Crushbone.") +
                     line(42, "Your Location is nan, 2, 3") +
                     line(43, "Your Location is 10, 11, 12"))
    assert watcher.poll(now=101) == []


def test_location_during_loading_and_log_reset_invalidate(tmp_path):
    _game, log, zones = fixture(tmp_path)
    log.touch()
    watcher = reader(log, zones)
    with log.open("a") as source:
        source.write(line(0, "LOADING, PLEASE WAIT...") +
                     line(1, "Your Location is 1, 2, 3") +
                     line(2, "You have entered Clan Crushbone.") +
                     line(3, "Your Location is 4, 5, 6"))
    assert watcher.poll(now=100) == []
    with log.open("a") as source:
        source.write(line(4, "LOADING, PLEASE WAIT..."))
    assert watcher.poll(now=101) == []
    replacement = tmp_path / "replacement"
    replacement.write_text(line(5, "You have entered Clan Crushbone.") +
                           line(6, "Your Location is 7, 8, 9"))
    replacement.replace(log)
    assert watcher.poll(now=102) == []


def test_owner_cli_writes_only_private_observation_file(tmp_path, monkeypatch):
    game, log, _zones = fixture(tmp_path)
    log.write_text(line(0, "You have entered The Greater Faydark."))
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    original_sleep = watch_destination.time.sleep
    appended = [False]

    def append_after_first_poll(_seconds):
        if not appended[0]:
            appended[0] = True
            with log.open("a") as source:
                source.write(line(1, "Your Location is 10, 20, 30") +
                             line(2, "LOADING, PLEASE WAIT...") +
                             line(6, "You have entered Clan Crushbone.") +
                             line(7, "Your Location is 1, 2, 3"))

    monkeypatch.setattr(watch_destination.time, "sleep", append_after_first_poll)
    try:
        result = watch_destination.main([
            "--character", "Legira", "--server", "freeport",
            "--game-root", str(game), "--seconds", "2",
            "--poll-seconds", "0.05"])
    finally:
        monkeypatch.setattr(watch_destination.time, "sleep", original_sleep)
    assert result == 0
    outputs = list((tmp_path / ".local/share/eql-automation/owner-traces").glob("*.json"))
    assert len(outputs) == 1 and outputs[0].stat().st_mode & 0o777 == 0o600
    payload = json.loads(outputs[0].read_text())
    assert payload["zone_id"] == 58 and payload["raw_location"] == [1.0, 2.0, 3.0]
    assert payload["preloading_raw_location"] == [10.0, 20.0, 30.0]
    assert payload["preloading_log_time"] is not None
    assert payload["entry_to_location_seconds"] == 1
    assert payload["source_zone_verified"] is False
    assert payload["raw_coordinates_aligned_to_wld"] is False


def test_owner_cli_refuses_stale_appends_or_ambiguous_batches(tmp_path, monkeypatch):
    game, log, _zones = fixture(tmp_path)
    log.touch()
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    original_sleep = watch_destination.time.sleep

    def run_with_lines(lines):
        appended = [False]

        def append_once(_seconds):
            if not appended[0]:
                appended[0] = True
                with log.open("a") as source:
                    source.write(lines)

        monkeypatch.setattr(watch_destination.time, "sleep", append_once)
        try:
            return watch_destination.main([
                "--character", "Legira", "--server", "freeport",
                "--game-root", str(game), "--seconds", "0.05",
                "--poll-seconds", "0.05"])
        finally:
            monkeypatch.setattr(watch_destination.time, "sleep", original_sleep)

    old = (BASE - timedelta(hours=1)).strftime("%a %b %d %H:%M:%S %Y")
    stale = (f"[{old}] LOADING, PLEASE WAIT...\r\n"
             f"[{old}] You have entered Clan Crushbone.\r\n"
             f"[{old}] Your Location is 1, 2, 3\r\n")
    assert run_with_lines(stale) == 2
    both = (line(0, "LOADING, PLEASE WAIT...") +
            line(1, "You have entered Clan Crushbone.") +
            line(2, "Your Location is 1, 2, 3") +
            line(3, "LOADING, PLEASE WAIT...") +
            line(4, "You have entered Clan Crushbone.") +
            line(5, "Your Location is 4, 5, 6"))
    assert run_with_lines(both) == 2
    assert not list((tmp_path / ".local/share/eql-automation/owner-traces").glob("*.json"))


def test_old_preloading_fix_is_discarded_while_destination_remains_observed():
    tracker = DestinationTracker("Clan Crushbone", 58)
    lines = [line(0, "Your Location is 1, 2, 3"),
             line(40, "LOADING, PLEASE WAIT..."),
             line(45, "You have entered Clan Crushbone."),
             line(46, "Your Location is 4, 5, 6")]
    observations = [tracker.consume(item, received_monotonic=100,
                                    log_epoch=1) for item in lines]
    found = observations[-1]
    assert found is not None and found.raw_location == (4.0, 5.0, 6.0)
    assert found.preloading_raw_location is None
