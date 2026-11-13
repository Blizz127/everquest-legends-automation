from eql_automation.melee_stop import NativeMeleeStopGate, MeleeState, StopDecision


def test_unknown_and_unverified_on_state_never_toggle():
    gate = NativeMeleeStopGate()
    assert gate.request_stop(10) is StopDecision.MANUAL
    assert gate.observe("[Fri Nov 13 10:00:00 2026] Auto attack is on.", 10)
    assert gate.request_stop(11) is StopDecision.MANUAL
    assert gate.pending_since is None


def test_verified_toggle_is_reserved_once_and_requires_exact_off_ack():
    gate = NativeMeleeStopGate(toggle_verified=True)
    assert gate.observe("Auto attack is on.", 10)
    assert gate.request_stop(11) is StopDecision.SEND_ONCE
    assert gate.request_stop(11.1) is StopDecision.WAIT
    assert not gate.observe("A player says, 'Auto attack is off.'", 11.2)
    assert gate.request_stop(11.3) is StopDecision.WAIT
    assert gate.observe("Auto attack is off.", 11.4)
    assert gate.request_stop(11.5) is StopDecision.CONFIRMED


def test_timeout_or_wrong_ack_fails_without_retry():
    gate = NativeMeleeStopGate(toggle_verified=True)
    gate.observe("Auto attack is on.", 1)
    assert gate.request_stop(2) is StopDecision.SEND_ONCE
    assert gate.request_stop(5.1) is StopDecision.MANUAL
    assert gate.request_stop(5.2) is StopDecision.MANUAL
    assert gate.state is MeleeState.UNKNOWN
    gate.invalidate()
    gate.observe("Auto attack is on.", 7)
    assert gate.request_stop(8) is StopDecision.SEND_ONCE
    gate.observe("Auto attack is on.", 8.1)
    assert gate.request_stop(8.2) is StopDecision.MANUAL


def test_log_gap_and_clock_rollback_discard_state():
    gate = NativeMeleeStopGate(toggle_verified=True)
    gate.observe("Auto attack is off.", 4)
    assert gate.request_stop(5) is StopDecision.CONFIRMED
    gate.invalidate()  # Loading, relogin, tail replacement or unreadable poll.
    assert gate.request_stop(6) is StopDecision.MANUAL
    gate.observe("Auto attack is on.", 8)
    assert not gate.observe("Auto attack is off.", 7)
    assert gate.request_stop(9) is StopDecision.MANUAL


def test_same_instant_off_message_cannot_ack_a_new_toggle():
    gate = NativeMeleeStopGate(toggle_verified=True)
    gate.observe("Auto attack is on.", 1)
    assert gate.request_stop(2) is StopDecision.SEND_ONCE
    gate.observe("Auto attack is off.", 2)
    assert gate.request_stop(2.1) is StopDecision.WAIT
