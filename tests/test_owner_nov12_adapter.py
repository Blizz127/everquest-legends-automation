from types import SimpleNamespace

import pytest

from eql_automation.owner_nov12_adapter import make_owner_nov12_engine


class FakeNovemberEngine:
    def __init__(self):
        self.calls = []
        self.status = ""
        self.preparing = False
        self.sender = None
        self.native_attack_off_pending = True
        self.attack_started = True
        self.command_recovery_pending = False

    def send(self, command):
        self.calls.append(("send", command))

    def handle_job(self, name, value):
        self.calls.append(("job", name, value))

    def stop_action(self, reason, *, keep_autopilot=False):
        self.calls.append(("stop", reason, keep_autopilot))

    def recover_interrupted_command(self):
        self.calls.append(("recover",))
        return True

    def input_events(self):
        if self.sender:
            self.sender.unfinished = False

    def emit(self, message):
        self.status = message


def test_assist_only_sends_current_target_rotation_and_explicit_prep():
    engine = make_owner_nov12_engine(FakeNovemberEngine)()
    engine.send("/attack on")
    engine.send("/attack off")
    assert engine.calls == []
    engine.send("/consider")
    engine.send("/cast 3")
    engine.send("/doability Bash")
    with pytest.raises(ValueError):
        engine.send("/target_a_goblin")
    with pytest.raises(ValueError):
        engine.send("/location")
    with pytest.raises(ValueError):
        engine.send("/outputfile spellbook eql-rotation-spellbook.txt")
    engine.preparing = True
    engine.send("/outputfile spellbook eql-rotation-spellbook.txt")
    assert engine.calls == [
        ("send", "/consider"), ("send", "/cast 3"),
        ("send", "/doability Bash"),
        ("send", "/outputfile spellbook eql-rotation-spellbook.txt"),
    ]


def test_movement_route_and_attack_off_jobs_never_reach_base():
    engine = make_owner_nov12_engine(FakeNovemberEngine)()
    for job in ("autopilot_start", "autopilot_later", "nav_calibrate",
                "nav_stop_check", "record_point", "route_delete", "attack_off"):
        engine.handle_job(job, 1)
    assert engine.calls == []
    assert "F11 movement" in engine.status
    engine.handle_job("arm", 1)
    assert engine.calls == [("job", "arm", 1)]
    assert engine.flush_native_attack_off()
    assert not engine.native_attack_off_pending
    assert not engine.attack_started


def test_stop_indicator_and_uncertain_draft_fail_closed():
    engine = make_owner_nov12_engine(FakeNovemberEngine)()
    engine.stop_action("F9", keep_autopilot=True)
    assert engine.calls == [("stop", "Rotation OFF · melee is manual · F9", False)]
    engine.sender = SimpleNamespace(unfinished=True)
    with pytest.raises(InterruptedError):
        engine.send("/cast 3")
    engine.input_events()
    assert engine.sender.unfinished
    engine.command_recovery_pending = True
    assert not engine.recover_interrupted_command()
    assert engine.calls[-1][0] == "stop"
