#!/usr/bin/env python3
"""Run original engine stop/recovery methods without devices or a game session."""
from queue import SimpleQueue
from types import SimpleNamespace

from owner_nov12_smoke_base import main as base_smoke


def main():
    base_smoke()
    from rotation_engine import Engine
    from eql_automation.owner_nov12_recovery import make_owner_nov12_engine
    adapted = make_owner_nov12_engine(Engine)
    engine = adapted.__new__(adapted)  # Never initialize devices or start a worker.
    calls, traces, notices = [], [], []
    engine.__dict__.update(
        jobs=SimpleQueue(), cancel_generation=0, active=False, preparing=False,
        stopping=False, measurement_only=False, autopilot=None, pointer=None,
        keys=set(), deferred=None, cancelled=True, command_recovery_pending=False,
        stopped_mid_command=False, attack_started=False, recent_attackers={},
        target_retaliation=False, attackers_seen=set(), target_name="old target",
        native_attack_off_pending=False, last_action_role=None,
        sender=SimpleNamespace(unfinished=False, dismissed=False, held=set(),
                               release_all=lambda: calls.append("release")),
        trace=lambda event, **values: traces.append((event, values)),
        emit=notices.append)
    # A GUI click was queued, then the real stop method processed F9 first.
    engine.post("prepare_later")
    engine.stop_action("F9 smoke")
    engine.handle_job(*engine.jobs.get())
    assert engine.deferred is None and not engine.active
    assert calls == ["release"]

    engine.sender.unfinished = engine.sender.dismissed = True
    engine.deferred = "prepare"
    generation = engine.cancel_generation
    engine.post("arm")
    engine.post("prepare_later")
    calls.clear()
    assert engine.handle_job("owner_chat_closed", {
        "chat_closed": True, "generation": generation})
    assert calls == [] and not engine.active and engine.cancelled
    assert engine.deferred is None and not engine.sender.unfinished
    assert engine.target_name is None and engine.target_ready is False
    while not engine.jobs.empty():
        engine.handle_job(*engine.jobs.get())
    assert not engine.active and engine.deferred is None
    assert traces[-1][0] == "owner_chat_closed"
    assert traces[-1][1]["game_input_sent"] is False

    # A fresh F8 can arm while unfocused, but never sends input in this smoke.
    engine.settings = SimpleNamespace(level=7)
    engine.prepared = True
    engine.prepared_level = 7
    engine.stop_keys_held = lambda: False
    engine.gate = SimpleNamespace(controls_ready=lambda: False)
    engine.post("arm")
    engine.handle_job(*engine.jobs.get())
    assert engine.active and not engine.cancelled and calls == []
    assert engine.target_name is None and engine.target_ready is None
    print("PASS: original-engine queued Prepare canceled by F9; confirmed local recovery stays off; stale starts canceled; fresh F8 required; no game input")


if __name__ == "__main__":
    main()
