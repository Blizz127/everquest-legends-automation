from datetime import datetime, timedelta

import pytest

from eql_automation.g2_scene_observer import (
    G2ObservationUnavailable, G2ReadOnlySceneObserver, G2SafetyObservation,
)
from eql_automation.location_log import LocationLogReader


BASE = datetime(2026, 11, 13, 14, 10, 0)


def line(second: int, body: str) -> str:
    stamp = (BASE + timedelta(seconds=second)).strftime("%a %b %d %H:%M:%S %Y")
    return f"[{stamp}] {body}\r\n"


def fixture(tmp_path):
    log = tmp_path / "eqlog_Probe_private.txt"
    log.touch()
    zones = tmp_path / "ZoneNames.txt"
    zones.write_text("54^Greater Faydark^0^0\n")
    now = [100.0]
    wall = [BASE]
    safety_at = [100.0]
    reader = LocationLogReader(log, zones, expected_character="Probe",
                               expected_server="private")

    def safety():
        return G2SafetyObservation(safety_at[0], True, True, True, True,
                                   True, True, True)

    observer = G2ReadOnlySceneObserver(
        reader, zone_short_name="gfaydark", zone_display_name="Greater Faydark",
        zone_id=54, safety_provider=safety, monotonic_clock=lambda: now[0],
        local_wall_clock=lambda: wall[0])
    return log, now, wall, safety_at, observer


def test_requires_new_zone_entry_then_single_fresh_fix_and_expires(tmp_path):
    log, now, wall, safety_at, observer = fixture(tmp_path)
    with log.open("a") as source:
        source.write(line(0, "Your Location is 1, 2, 3"))
    with pytest.raises(G2ObservationUnavailable, match="single-zone"):
        observer()
    with log.open("a") as source:
        source.write(line(1, "You have entered Greater Faydark.") +
                     line(1, "Your Location is 4, 5, 6"))
    now[0] = safety_at[0] = 101.0
    wall[0] = BASE + timedelta(seconds=1)
    first = observer()
    assert first.zone == "gfaydark" and first.raw_location == (4.0, 5.0, 6.0)
    assert first.fix_seq == 1 and first.zone_generation == 1
    now[0] = safety_at[0] = 101.2
    again = observer()
    assert again.at == 101.2 and again.fix_seq == first.fix_seq
    now[0] = safety_at[0] = 101.51
    with pytest.raises(G2ObservationUnavailable, match="fresh"):
        observer()


def test_batch_rejected_until_new_single_line_and_same_zone_reentry_changes_generation(tmp_path):
    log, now, wall, safety_at, observer = fixture(tmp_path)
    with log.open("a") as source:
        source.write(line(0, "You have entered Greater Faydark.") +
                     line(0, "Your Location is 1, 2, 3") +
                     line(0, "Your Location is 1, 2, 3"))
    with pytest.raises(G2ObservationUnavailable, match="Batched"):
        observer()
    now[0] = safety_at[0] = 100.1
    with pytest.raises(G2ObservationUnavailable, match="single-zone"):
        observer()
    with log.open("a") as source:
        source.write(line(1, "Your Location is 1, 2, 3"))
    now[0] = safety_at[0] = 101.0
    wall[0] = BASE + timedelta(seconds=1)
    accepted = observer()
    with log.open("a") as source:
        source.write(line(2, "LOADING, PLEASE WAIT...") +
                     line(2, "You have entered Greater Faydark."))
    now[0] = safety_at[0] = 102.0
    wall[0] = BASE + timedelta(seconds=2)
    with pytest.raises(G2ObservationUnavailable, match="single-zone"):
        observer()
    with log.open("a") as source:
        source.write(line(3, "Your Location is 1, 2, 3"))
    now[0] = safety_at[0] = 103.0
    wall[0] = BASE + timedelta(seconds=3)
    assert observer().zone_generation > accepted.zone_generation


def test_rejects_delayed_log_line_and_stale_independent_checks(tmp_path):
    log, now, wall, safety_at, observer = fixture(tmp_path)
    with log.open("a") as source:
        source.write(line(0, "You have entered Greater Faydark.") +
                     line(0, "Your Location is 1, 2, 3"))
    wall[0] = BASE + timedelta(seconds=5)
    with pytest.raises(G2ObservationUnavailable, match="timestamp"):
        observer()
    with log.open("a") as source:
        source.write(line(5, "Your Location is 1, 2, 3"))
    now[0] = 105.0
    safety_at[0] = 104.0
    with pytest.raises(G2ObservationUnavailable, match="Independent"):
        observer()
    safety_at[0] = 105.0
    assert observer().fix_seq == 2


def test_safety_check_can_advance_clock_but_intervening_loading_revokes_fix(tmp_path):
    log, now, wall, _safety_at, observer = fixture(tmp_path)
    with log.open("a") as source:
        source.write(line(0, "You have entered Greater Faydark.") +
                     line(0, "Your Location is 1, 2, 3"))

    def safe_after_poll():
        now[0] += 0.02
        return G2SafetyObservation(now[0], True, True, True, True,
                                   True, True, True)

    observer.safety_provider = safe_after_poll
    first = observer()
    assert first.at == 100.02 and first.fix_seq == 1

    def loading_during_check():
        with log.open("a") as source:
            source.write(line(0, "LOADING, PLEASE WAIT..."))
        return G2SafetyObservation(now[0], True, True, True, True,
                                   True, True, True)

    observer.safety_provider = loading_during_check
    with pytest.raises(G2ObservationUnavailable, match="fresh"):
        observer()
    assert observer.trusted_fix is None
