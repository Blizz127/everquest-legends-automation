from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

import pytest

from eql_automation.g2_safety_provider import (
    GameWindowIdentity, G2SafetyProvider, G2UiObservation, focused_game_identity,
)
from eql_automation.g2_scene_observer import G2ObservationUnavailable, G2ReadOnlySceneObserver
from eql_automation.location_log import LocationLogReader
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.scene_log_veto import SceneLogVeto


WINDOW = GameWindowIdentity(42, 1234, 600)


class Gate:
    def __init__(self):
        self.window = WINDOW
        self.focused = True
        self.ready = True
        self.count = 1

    def windows(self):
        return [SimpleNamespace(id=self.window.window_id)] * self.count

    def focused_window(self):
        return SimpleNamespace(id=self.window.window_id) if self.focused else None

    def game_session(self):
        return {"pid": self.window.pid, "start_ticks": str(self.window.start_ticks)}

    def controls_ready(self):
        return self.ready


def fixture(tmp_path):
    clock, generation, mode = [100.0], [7], ["measurement"]
    gate = Gate()
    records, frames = [], []
    def sample():
        started = clock[0]
        clock[0] += .001
        current = OwnerInputObservation(started, clock[0], 1, True, 26, 0, False, 0, "observed")
        return records.pop(0)(current) if records else current
    def ui(window):
        assert window == WINDOW
        started = clock[0]
        clock[0] += .005
        current = G2UiObservation(started, clock[0], window, "f" * 64, "c" * 64,
                                  True, True, True, True, True)
        return frames.pop(0)(current) if frames else current
    log_path = tmp_path / "eqlog_Probe_private.txt"
    log_path.touch(exist_ok=True)
    veto = SceneLogVeto(log_path, expected_character="Probe", expected_server="private",
                        cancel_generation=7, clock=lambda: clock[0])
    provider = G2SafetyProvider(log_veto=veto, expected_log_path=log_path,
                                gate=gate, input_observer=SimpleNamespace(sample=sample),
                                ui_observer=ui, expected_window=WINDOW,
                                calibration_sha256="c" * 64, cancel_generation=7,
                                generation_reader=lambda: generation[0], mode_reader=lambda: mode[0],
                                clock=lambda: clock[0])
    return provider, gate, clock, generation, mode, records, frames


def test_success_preserves_oldest_time_and_brackets_frame_with_input(tmp_path):
    provider, gate, clock, *_ = fixture(tmp_path)
    result = provider()
    assert result.observed_at == 100.0 < clock[0]
    assert result.owner_keys_clear and result.chat_clear and result.focused
    assert provider.last_ui.window == WINDOW
    assert provider.last_ui.started_at >= 100.001


@pytest.mark.parametrize("transform", [
    lambda o: replace(o, activity=True),
    lambda o: replace(o, held_key_count=1),
    lambda o: replace(o, active_contact_count=1),
    lambda o: replace(o, coverage_complete=False),
    lambda o: replace(o, unsupported_motion_devices=1),
    lambda o: replace(o, topology_generation=2),
])
def test_owner_activity_or_topology_change_during_image_rejects(tmp_path, transform):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    records.extend([lambda o: o, transform])
    with pytest.raises(G2ObservationUnavailable):
        provider()
    assert provider.last_ui is None


@pytest.mark.parametrize("kind", ["cancel", "mode", "process", "window", "focus", "grabs"])
def test_off_assist_switch_relogin_focus_or_window_change_during_image_rejects(tmp_path, kind):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    def during(o):
        if kind == "cancel": generation[0] += 1
        if kind == "mode": mode[0] = "assist"
        if kind == "process": gate.window = replace(WINDOW, start_ticks=601)
        if kind == "window": gate.window = replace(WINDOW, window_id=43)
        if kind == "focus": gate.focused = False
        if kind == "grabs": gate.ready = False
        return o
    frames.append(during)
    with pytest.raises(G2ObservationUnavailable):
        provider()


@pytest.mark.parametrize("transform", [
    lambda o: replace(o, started_at=99.9),
    lambda o: replace(o, finished_at=100.09),
    lambda o: replace(o, started_at=float("nan")),
    lambda o: replace(o, frame_sha256=""),
    lambda o: replace(o, calibration_sha256="d" * 64),
    lambda o: replace(o, window=replace(WINDOW, pid=1235)),
    lambda o: replace(o, chat_clear=False),
    lambda o: replace(o, target_absent=None),
    lambda o: replace(o, combat_clear=1),
    lambda o: replace(o, no_transition=False),
    lambda o: replace(o, no_incoming_attack=False),
])
def test_cached_unbound_or_unknown_ui_never_supplies_safety(transform, tmp_path):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    frames.append(transform)
    with pytest.raises(G2ObservationUnavailable):
        provider()


def test_initial_input_attach_prevents_ui_capture_and_clock_or_callback_failure_refuses(tmp_path):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    records.append(lambda o: replace(o, coverage_complete=False))
    frames.append(lambda o: pytest.fail("UI should not capture while input is incomplete"))
    with pytest.raises(G2ObservationUnavailable):
        provider()
    assert len(frames) == 1
    frames.clear()
    def slow(o):
        clock[0] += .101
        return o
    frames.append(slow)
    with pytest.raises(G2ObservationUnavailable):
        provider()
    def backward(o):
        clock[0] -= 1
        return o
    frames.append(backward)
    with pytest.raises(G2ObservationUnavailable):
        provider()
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    def failed(window):
        raise OSError("capture unavailable")
    provider.ui_observer = failed
    with pytest.raises(G2ObservationUnavailable, match="failed"):
        provider()


def test_multiple_game_windows_are_not_bound_even_with_one_focused():
    gate = Gate()
    gate.count = 2
    with pytest.raises(G2ObservationUnavailable):
        focused_game_identity(gate)


def test_provider_connects_to_existing_fresh_log_scene_without_movement(tmp_path):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    path = tmp_path / "eqlog_Probe_private.txt"
    path.touch()
    zones = tmp_path / "ZoneNames.txt"
    zones.write_text("54^Greater Faydark^0^0\n")
    reader = LocationLogReader(path, zones, expected_character="Probe", expected_server="private")
    wall = datetime(2026, 11, 14, 1, 0, 0)
    prefix = wall.strftime("[%a %b %d %H:%M:%S %Y] ")
    with path.open("a") as output:
        output.write(prefix + "You have entered Greater Faydark.\n")
        output.write(prefix + "Your Location is 1, 2, 3\n")
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    scene = G2ReadOnlySceneObserver(reader, zone_short_name="gfaydark",
                                  zone_display_name="Greater Faydark", zone_id=54,
                                  safety_provider=provider, monotonic_clock=lambda: clock[0],
                                  local_wall_clock=lambda: wall)
    observed = scene()
    assert observed.zone == "gfaydark" and observed.raw_location == (1., 2., 3.)
    assert observed.owner_keys_clear and observed.fix_seq == 1
    mode[0] = "assist"
    with pytest.raises(G2ObservationUnavailable):
        scene()


@pytest.mark.parametrize("when", ["before", "during", "after"])
def test_log_hazard_brackets_ui_and_stays_latched(tmp_path, when):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    def attack():
        with provider.log_path.open("a") as output:
            output.write("[Sat Nov 14 01:00:00 2026] Training dummy hits YOU for 2 points of damage.\n")
    if when == "before": attack()
    if when == "during": frames.append(lambda o: (attack(), o)[1])
    if when == "after": records.extend([lambda o:o, lambda o:(attack(),o)[1]])
    with pytest.raises(G2ObservationUnavailable, match="log veto"):
        provider()
    assert provider.last_ui is None
    assert provider.last_log_veto.reason == "incoming_attack"
    with provider.log_path.open("a") as output:
        output.write("[Sat Nov 14 01:00:00 2026] Auto attack is off.\n")
    with pytest.raises(G2ObservationUnavailable, match="log veto"):
        provider()


@pytest.mark.parametrize("change", ["generation", "focus", "mode", "process"])
def test_binding_change_during_final_log_io_refuses(tmp_path, change):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    original = provider.log_veto.tail.poll
    calls = [0]
    def poll():
        result = original()
        calls[0] += 1
        if calls[0] == 2:
            if change == "generation": generation[0] += 1
            elif change == "focus": gate.focused = False
            elif change == "mode": mode[0] = "assist"
            elif change == "process": gate.window = replace(WINDOW, start_ticks=601)
        return result
    provider.log_veto.tail.poll = poll
    with pytest.raises(G2ObservationUnavailable): provider()
    assert provider.last_ui is None


def test_wrong_log_binding_and_generation_refuse(tmp_path):
    provider, gate, clock, generation, mode, records, frames = fixture(tmp_path)
    kwargs = dict(gate=gate, input_observer=provider.input_observer, ui_observer=provider.ui_observer,
                  log_veto=provider.log_veto, expected_log_path=provider.log_path,
                  expected_window=WINDOW, calibration_sha256="c" * 64, cancel_generation=7,
                  generation_reader=lambda:generation[0], mode_reader=lambda:mode[0], clock=lambda:clock[0])
    with pytest.raises(ValueError): G2SafetyProvider(**{**kwargs, "expected_log_path":tmp_path/"other.txt"})
    with pytest.raises(ValueError): G2SafetyProvider(**{**kwargs, "cancel_generation":8})
    provider.log_veto.tail.path = tmp_path / "other.txt"
    with pytest.raises(G2ObservationUnavailable, match="source/generation"): provider()
