"""No-device checks for the optional owner-started October engine adapter."""
from pathlib import Path

import pytest

from eql_automation.owner_live_adapter import make_owner_rotation_engine
from eql_automation import owner_live_entry


class FakeSettings:
    level = 10


class FakeSender:
    unfinished = False


class OctoberEngineFixture:
    """Only the inherited calls that the adapter must constrain."""

    def __init__(self):
        self.preparing = False
        self.prepared = False
        self.prepared_level = None
        self.active = False
        self.cancel_generation = 0
        self.settings = FakeSettings()
        self.sender = FakeSender()
        self.sent = []
        self.statuses = []

    def emit(self, text):
        self.statuses.append(text)

    def stop_action(self, reason):
        self.active = False
        self.emit(reason)

    def send(self, command):
        self.sent.append(command)

    def handle_job(self, name, value):
        if name == "prepare":
            self.preparing = True
            self.send("/attack off")
            self.send("/outputfile spellbook eql-rotation-spellbook.txt")
            self.send("/memspellslot 1 200")
            self.preparing = False
            self.prepared = True
            self.prepared_level = self.settings.level
        elif name == "arm":
            self.send("/attack on")
            self.active = True
        elif name == "attack_off":
            self.send("/attack off")

    def input_events(self):
        self.sender.unfinished = False  # The unsafe October clear behavior.


def test_owner_rotation_never_toggles_attack_or_auto_prepares():
    engine = make_owner_rotation_engine(OctoberEngineFixture)()
    engine.handle_job("arm", 0)
    assert engine.sent == [] and not engine.active
    assert "Press F6" in engine.statuses[-1]
    engine.handle_job("prepare", 0)
    assert engine.sent == ["/outputfile spellbook eql-rotation-spellbook.txt",
                           "/memspellslot 1 200"]
    engine.handle_job("arm", 0)
    assert engine.active
    assert engine.sent == ["/outputfile spellbook eql-rotation-spellbook.txt",
                           "/memspellslot 1 200"]
    assert "autoattack manual" in engine.statuses[-1]
    engine.handle_job("attack_off", 0)
    assert all(not command.startswith("/attack") for command in engine.sent)
    engine.stop_action("owner pressed F9")
    assert engine.statuses[-1] == "Rotation OFF · owner pressed F9"


def test_combat_command_allowlist_and_uncertain_draft_persistence():
    engine = make_owner_rotation_engine(OctoberEngineFixture)()
    engine.send("/cast 3")
    engine.send("/doability Bash")
    assert engine.sent == ["/cast 3", "/doability Bash"]
    for command in ("/target player", "/attack on; /target player",
                    "/memspellslot 1 200"):
        with pytest.raises(ValueError, match="rotation-only input scope"):
            engine.send(command)
    engine.sender.unfinished = True
    engine.input_events()
    assert engine.sender.unfinished


def test_legacy_source_hash_guard_rejects_missing_and_changed_files(tmp_path: Path,
                                                                    monkeypatch):
    monkeypatch.setattr(owner_live_entry, "LEGACY_SOURCE_HASHES",
                        {"rotation_engine.py": "0" * 64})
    with pytest.raises(RuntimeError, match="missing"):
        owner_live_entry.verify_legacy_source(tmp_path)
    (tmp_path / "rotation_engine.py").write_text("changed")
    with pytest.raises(RuntimeError, match="changed"):
        owner_live_entry.verify_legacy_source(tmp_path)
