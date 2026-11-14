import json
from types import SimpleNamespace

import pytest

from tools import capture_owner_location as tool


class Gate:
    def __init__(self):
        self.window = SimpleNamespace(id=42)
        self.session = {"pid": 10, "start_ticks": "100"}
        self.focus = True
        self.closed = False
        self.display = SimpleNamespace(close=self.close)

    def close(self): self.closed = True
    def windows(self): return [self.window]
    def game_session(self): return self.session.copy()
    def focused_window(self): return self.window if self.focus else None


def fixture(tmp_path, monkeypatch, *, appended="Your Location is 1, 2, 3", during=None):
    output = tmp_path / "private"
    monkeypatch.setattr(tool, "DEFAULT_OUTPUT", output)
    game = tmp_path / "game"
    (game / "Logs").mkdir(parents=True)
    log = game / "Logs/eqlog_Test_freeport.txt"
    log.write_text("[Sat Nov 14 03:00:00 2026] Your Location is 9, 9, 9\n")
    gate = Gate()
    state = {"time": 100., "appended": False, "captures": 0}

    def append(body):
        with log.open("a") as f:
            f.write(f"[Sat Nov 14 03:00:01 2026] {body}\n")

    def sleep(delay):
        state["time"] += delay
        if not state["appended"] and appended is not None:
            append(appended)
            state["appended"] = True

    def capture(**kwargs):
        state["captures"] += 1
        assert kwargs["include_chat"] is False
        state["time"] += kwargs["delay"]
        metadata = {"game_session": gate.session.copy(), "focused_window_id": gate.window.id,
                    "capture_started_monotonic": state["time"],
                    "capture_ended_monotonic": state["time"] + .01,
                    "game_input_sent": False, "chat_crop_included": False, "crops": {}}
        state["time"] += .02
        if during: during(gate, metadata, append, log, state)
        dest = output / "capture"
        dest.mkdir(parents=True)
        (dest / "metadata.json").write_text(json.dumps(metadata))
        return dest

    kwargs = dict(label="test", timeout=1., settle=.2, preview=tmp_path / "preview",
                  game=game, character="Test", server="freeport", output=output,
                  gate_factory=lambda: gate, capture_fn=capture,
                  clock=lambda: state["time"], sleep=sleep)
    return kwargs, gate, state, output


def test_stationary_pair_skips_history_and_carries_no_navigation_authority(tmp_path, monkeypatch):
    kwargs, gate, state, _ = fixture(tmp_path, monkeypatch)
    dest = tool.collect(**kwargs)
    record = json.loads((dest / "unbound-location.json").read_text())
    assert record["location"]["raw_coordinates"] == [1., 2., 3.]
    assert "zone_id" not in record["location"]
    for flag in ("zone_binding_verified", "coordinates_aligned_to_wld",
                 "request_correlation_verified", "input_authorized"):
        assert record["location"][flag] is False
    assert record["game_input_sent"] is False and record["live_route_accepted"] is False
    assert record["log_flush_delay_verified"] is False
    assert record["ui_metadata_sha256"] == tool.file_sha(dest / "metadata.json")
    assert gate.closed and state["captures"] == 1


@pytest.mark.parametrize("change", ["process", "window", "focus", "transition", "location",
                                    "reset", "expired", "reversed_time", "chat"])
def test_changed_capture_interval_never_publishes_a_pair(tmp_path, monkeypatch, change):
    def during(gate, metadata, append, log, state):
        if change == "process": gate.session["start_ticks"] = "200"
        elif change == "window": gate.window.id += 1
        elif change == "focus": gate.focus = False
        elif change == "transition": append("LOADING, PLEASE WAIT...")
        elif change == "location": append("Your Location is 4, 5, 6")
        elif change == "reset": log.write_text("")
        elif change == "expired": state["time"] += 11
        elif change == "reversed_time": metadata["capture_started_monotonic"] = 0
        elif change == "chat": metadata["crops"]["MainChat"] = {}
    kwargs, gate, _, output = fixture(tmp_path, monkeypatch, during=during)
    with pytest.raises(ValueError): tool.collect(**kwargs)
    assert not (output / "capture/unbound-location.json").exists()
    assert gate.closed


def test_timeout_does_not_capture_or_use_historical_location(tmp_path, monkeypatch):
    kwargs, gate, state, output = fixture(tmp_path, monkeypatch, appended=None)
    with pytest.raises(ValueError, match="timeout"): tool.collect(**kwargs)
    assert state["captures"] == 0 and gate.closed and not output.exists()


def test_unfocused_location_is_not_reused_after_refocus(tmp_path, monkeypatch):
    kwargs, gate, state, _ = fixture(tmp_path, monkeypatch)
    gate.focus = False
    with pytest.raises(ValueError, match="sampled game focus"): tool.collect(**kwargs)
    assert state["captures"] == 0 and gate.closed


@pytest.mark.parametrize("field,value", [("character", "../Test"), ("server", "free*"),
                                         ("label", "../capture"), ("timeout", float("nan"))])
def test_bad_parameters_refuse_before_opening_a_gate(tmp_path, monkeypatch, field, value):
    kwargs, gate, state, _ = fixture(tmp_path, monkeypatch)
    kwargs[field] = value
    kwargs["gate_factory"] = lambda: pytest.fail("invalid arguments opened a game gate")
    with pytest.raises(ValueError): tool.collect(**kwargs)
    assert state["captures"] == 0


def test_actual_crop_writer_omits_chat_for_location_diagnostic(tmp_path, monkeypatch):
    import sys
    from tools import capture_owner_ui as ui

    class Frame:
        width = height = 100
        size = (100, 100)
        def tobytes(self): return b"synthetic-frame"
        def crop(self, box): return self
        def save(self, path): path.write_bytes(b"synthetic-crop")

    class Layout:
        sources = {}
        skin = "fixture"
        ui_scale = 1
        def window(self, name):
            assert name != "MainChat"
            return SimpleNamespace(x=1, y=1, w=10, h=10)
        def control(self, *args): return SimpleNamespace(x=1, y=1, w=5, h=5)

    gate = Gate()
    gate.capture = lambda: Frame()
    monkeypatch.setitem(sys.modules, "rotation_engine", SimpleNamespace(WindowGate=lambda: gate))
    monkeypatch.setitem(sys.modules, "uilayout", SimpleNamespace(
        UiLayout=SimpleNamespace(load=lambda *args, **kwargs: Layout())))
    monkeypatch.setattr(ui, "checked_preview", lambda _: None)
    monkeypatch.setattr(ui, "DEFAULT_OUTPUT", tmp_path / "private")
    # The production capture installs an owner-only umask. Restore it after the fixture.
    import os
    old_umask = os.umask(0o077)
    try:
        dest = ui.capture(label="fixture", delay=0, preview=tmp_path, game=tmp_path / "game",
                          character="Test", server="freeport", output=ui.DEFAULT_OUTPUT,
                          include_chat=False)
    finally:
        os.umask(old_umask)
    metadata = json.loads((dest / "metadata.json").read_text())
    assert "MainChat" not in metadata["crops"] and not (dest / "MainChat.png").exists()
    assert metadata["chat_crop_included"] is False and gate.closed
    assert metadata["capture_started_monotonic"] <= metadata["capture_ended_monotonic"]
