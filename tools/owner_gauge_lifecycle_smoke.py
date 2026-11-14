#!/usr/bin/env python3
"""Exercise the retained engine with inert input/capture seams; no devices."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import sys
import time


def run(preview):
    sys.path.insert(0, str(preview))
    from owner_nov12_entry import verify_snapshot
    verify_snapshot(preview)
    from rotation_engine import Engine
    from rotation_core import Rotation
    from eql_automation.owner_nov12_recovery import make_owner_nov12_engine as old
    from eql_automation.owner_gauge_lifecycle import make_owner_nov12_engine as fixed

    def fixture(adapted):
        engine = adapted.__new__(adapted)  # Never initialize devices/worker.
        commands = []
        profile = {"quick_heal": SimpleNamespace(busy_seconds=2.0)}
        engine.__dict__.update(
            active=True, preparing=False, stopping=False, measurement_only=False,
            autopilot=None, pointer=None, keys=set(), cancel_generation=0,
            cancelled=False, attack_started=False, recent_attackers={},
            target_retaliation=False, native_attack_off_pending=False,
            last_action_role=None, command_recovery_pending=False,
            stopped_mid_command=False, deferred=None, hp=.2, mana=.7,
            last_gauge=time.monotonic(),
            sender=SimpleNamespace(unfinished=False, dismissed=False, held=set(),
                release_all=lambda: None, command=commands.append),
            trace=lambda *a, **k: None, emit=lambda *a, **k: None,
            stop_keys_held=lambda: False, blocked_keys=lambda: False,
            pump=lambda: None,
            settings=SimpleNamespace(level=7, auto_stance=False, character="Fixture",
                server="fixture", mode="balanced", damage_interval=5.,
                smart_heal=True, use_stuns=True, use_bash=True, hp_region=None),
            prepared=True, prepared_level=7,
            gate=SimpleNamespace(controls_ready=lambda: True),
            attackers_seen=set(), target_ready=None, command_pause_until=0,
            zone_loading_until=0, buff_retry_at={}, mana_blocked_until=0,
            recent_commands=[], profile=profile, rotation=Rotation(profile, 7),
            catalog=SimpleNamespace(profile=lambda *args: profile),
            make_tail=lambda: SimpleNamespace(poll=lambda: None),
            startup_zone=lambda: "fixture", known=None, retired_rotation=None,
        )
        return engine, commands

    def restart(adapted):
        engine, commands = fixture(adapted)
        engine.stop_action("synthetic OFF")
        # The old idle loop advances this without reading gauges while OFF.
        engine.last_gauge = time.monotonic()
        engine.handle_job("arm", engine.cancel_generation)
        engine.combat_tick(time.monotonic())
        engine.combat_tick(time.monotonic())
        return engine, commands

    retained, old_commands = restart(old(Engine))
    assert retained.hp == .2 and old_commands == ["/alt activate 6001"]
    engine, commands = restart(fixed(Engine))
    assert engine.hp is engine.mana is None and engine.last_gauge == float("-inf")
    assert commands == ["/consider"]
    engine.hp, engine.mana = .2, .7  # Synthetic fresh gauge sample.
    engine.combat_tick(time.monotonic())
    assert commands == ["/consider", "/alt activate 6001"]

    for field, value in (("hp_region", {"box": [1, 2, 101, 12]}),
                         ("character", "OtherFixture")):
        engine, commands = fixture(fixed(Engine))
        engine.active = False  # Retained inactive settings path never stops.
        changed = SimpleNamespace(**vars(engine.settings))
        setattr(changed, field, value)
        engine.handle_job("settings", changed)
        assert engine.hp is engine.mana is None and engine.last_gauge == float("-inf")
        assert not engine.active and commands == []

    engine, commands = fixture(fixed(Engine))
    previous_generation = engine.cancel_generation
    engine.stop_action("synthetic F9")
    engine.handle_job("arm", previous_generation)
    assert not engine.active and commands == []
    engine.handle_job("heal", engine.cancel_generation)
    assert commands == ["/cast 1"] and engine.hp is engine.mana is None

    # This fixture never creates an Engine normally, a WindowGate, a sender,
    # a worker, or a device. Only command strings reach the in-memory recorder.
    return dict(retained_bug_reproduced=True, stale_gauge_heal_prevented=True,
        fresh_low_sample_resumes_heal=True, inactive_calibration_invalidates=True,
        inactive_identity_invalidates=True, stale_start_refused=True,
        explicit_f10_without_hp=True, game_input_sent=False, devices_opened=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.preview.resolve()), sort_keys=True))
