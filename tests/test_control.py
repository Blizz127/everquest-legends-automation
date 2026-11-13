"""Focused safety checks for the offline mode control layer."""

import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from eql_automation.control import ControlPlane
from eql_automation.modes import Action, ActionKind, Mode


def intent(kind: ActionKind, detail: str = "synthetic") -> Action:
    return Action(kind, detail)


def test_commands_and_simulated_hotkeys_switch_without_restart():
    indicators = []
    control = ControlPlane(indicators.append)
    assert control.indicator.mode == Mode.OFF
    assert control.handle_command("mode assist").mode == Mode.ASSIST
    assert control.handle_hotkey("f7").mode == Mode.FULL_AUTO
    assert control.handle_hotkey("F8").mode == Mode.ASSIST
    assert control.handle_hotkey("F9").mode == Mode.OFF
    assert [item.mode for item in indicators] == [
        Mode.OFF, Mode.ASSIST, Mode.FULL_AUTO, Mode.ASSIST, Mode.OFF]
    assert "generation 4" in indicators[-1].text
    assert "simulated F9" in indicators[-1].text


@pytest.mark.parametrize("kind", [
    ActionKind.ATTACK, ActionKind.MOVE, ActionKind.TARGET, ActionKind.LOOT,
    ActionKind.VENDOR, ActionKind.CAMP, ActionKind.REST, ActionKind.ZONE,
    ActionKind.LOGIN, ActionKind.RECOVER, ActionKind.SCRIBE,
    ActionKind.MEMORIZE,
])
def test_assist_queue_denies_nonrotation_actions(kind):
    control = ControlPlane()
    control.handle_command("mode assist")
    assert not control.queue(intent(kind))
    assert control.drain().ready == ()


def test_assist_rotation_actions_can_queue_but_spoofed_commands_cannot():
    control = ControlPlane()
    control.handle_command("mode assist")
    for kind in (ActionKind.CAST, ActionKind.ABILITY,
                 ActionKind.HEAL, ActionKind.BUFF):
        assert control.queue(intent(kind))
    assert not control.queue(intent(ActionKind.CAST, "/attack on"))
    result = control.drain()
    assert result.dropped == 0
    assert len(result.ready) == 4
    assert all(control.allows(item) for item in result.ready)


def test_switch_cancels_queued_and_already_drained_intents():
    control = ControlPlane()
    control.handle_command("mode full")
    assert control.queue(intent(ActionKind.MOVE))
    drained = control.drain()
    assert control.allows(drained.ready[0])
    assert control.queue(intent(ActionKind.LOOT))
    control.handle_command("mode assist")
    assert not control.allows(drained.ready[0])
    assert control.drain().dropped == 1
    assert control.queue(intent(ActionKind.CAST, "/cast 1"))
    control.handle_command("stop")
    assert control.drain().dropped == 1


def test_emergency_stop_latches_off_until_explicit_reset():
    control = ControlPlane()
    control.handle_hotkey("F7")
    assert control.queue(intent(ActionKind.MOVE))
    indicator = control.emergency_stop("unknown target")
    assert indicator.mode == Mode.OFF and indicator.safety_latched
    assert "unknown target" in indicator.text
    assert control.drain().dropped == 1
    with pytest.raises(RuntimeError, match="Safety stop is latched"):
        control.handle_command("mode assist")
    assert control.handle_command("reset safety").mode == Mode.OFF
    assert not control.safety_latched
    assert control.handle_command("mode assist").mode == Mode.ASSIST


def test_invalid_request_preserves_current_permit():
    control = ControlPlane()
    control.handle_command("mode assist")
    assert control.queue(intent(ActionKind.HEAL))
    generation = control.indicator.generation
    with pytest.raises(ValueError):
        control.handle_hotkey("F6")
    with pytest.raises(ValueError):
        control.handle_command("mode invalid")
    assert control.indicator.generation == generation
    assert len(control.drain().ready) == 1


def test_concurrent_activation_cannot_override_emergency_stop():
    control = ControlPlane()
    barrier = Barrier(3)

    def activate():
        barrier.wait()
        try:
            control.handle_command("mode assist")
        except RuntimeError:
            pass  # Emergency stop won the transition lock.

    def emergency():
        barrier.wait()
        control.emergency_stop("synthetic danger")

    with ThreadPoolExecutor(max_workers=2) as executor:
        activation = executor.submit(activate)
        stop = executor.submit(emergency)
        barrier.wait()
        activation.result()
        stop.result()
    assert control.indicator.mode == Mode.OFF
    assert control.safety_latched
    assert not control.queue(intent(ActionKind.CAST))


def test_failed_mode_indicator_latches_off():
    calls = 0

    def notify(_indicator):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError("synthetic display failure")

    control = ControlPlane(notify)
    with pytest.raises(RuntimeError, match="Mode indicator failed"):
        control.handle_command("mode assist")
    assert control.indicator.mode == Mode.OFF
    assert control.safety_latched
    assert not control.queue(intent(ActionKind.CAST))
