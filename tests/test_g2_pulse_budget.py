import pytest

from eql_automation.g2_pulse_budget import G2Halt, G2PulseBudget, G2Scene


def scene(at, x=0.0, *, zone="gfaydark", **changes):
    data = dict(at=at, zone=zone, raw_location=(x, 0.0, 10.0),
                log_epoch=1, fix_seq=round(at * 100) + 1,
                focused=True, owner_keys_clear=True, chat_clear=True,
                target_absent=True, combat_clear=True, no_transition=True,
                no_incoming_attack=True)
    data.update(changes)
    return G2Scene(**data)


def ready(*, radius=18, speed=20, bound=60):
    return G2PulseBudget(scene(0), scene(0.5), geometry_candidate=True,
                         owner_confirmed_g0=True, clear_radius=radius,
                         measured_speed=speed, verified_speed_upper_bound=bound,
                         speed_bound_observed_at=0.4)


def arm(budget, begin, x=0.0):
    permit = budget.reserve_forward(scene(begin, x=x))
    assert permit.seconds == 0.15
    assert budget.confirm_keydown(scene(begin + 0.01, x=x), permit) == 0.15
    return permit


def pulse(budget, begin, end, x):
    arm(budget, begin, x - 3.0)
    budget.record_hold(scene(begin + 0.15, x=x - 3.0), 0.15)
    budget.record_fix(scene(end, x=x))
    budget.record_still(scene(end + 0.45, x=x))


def test_two_bounded_pulses_are_only_recording_evidence():
    budget = ready()
    pulse(budget, 0.5, 0.85, 3.0)
    pulse(budget, 1.3, 1.65, 6.0)
    result = budget.finish(scene(2.55, x=6.0), scene(3.0, x=6.0))
    assert (result.pulses, result.total_held, result.displacement) == (2, 0.30, 6.0)
    assert not result.real_client_accepted and budget.stage == "done"


def test_missing_g0_geometry_or_unsafe_scene_sends_no_pulse():
    for options in ({"geometry_candidate": False}, {"owner_confirmed_g0": False}):
        with pytest.raises(G2Halt):
            gates = {"geometry_candidate": True, "owner_confirmed_g0": True}
            gates.update(options)
            G2PulseBudget(scene(0), scene(0.5), clear_radius=18,
                          measured_speed=20, verified_speed_upper_bound=60,
                          speed_bound_observed_at=0.4, **gates)
    budget = ready()
    with pytest.raises(G2Halt, match="unsafe"):
        budget.reserve_forward(scene(0.5, target_absent=False))
    assert budget.stage == "halted" and budget.pulses == 0


def test_current_position_or_radius_change_blocks_second_pulse():
    budget = ready(radius=12, speed=30)
    pulse(budget, 0.5, 0.85, 3.0)
    with pytest.raises(G2Halt, match="budget"):
        budget.reserve_forward(scene(1.3, x=3.0))
    assert budget.pulses == 1 and budget.stage == "halted"

    moved = ready()
    with pytest.raises(G2Halt, match="budget"):
        moved.reserve_forward(scene(0.5, x=1.0))


def test_three_is_the_absolute_pulse_limit():
    budget = ready()
    pulse(budget, 0.5, 0.85, 3.0)
    pulse(budget, 1.3, 1.65, 6.0)
    pulse(budget, 2.1, 2.45, 9.0)
    with pytest.raises(G2Halt, match="budget"):
        budget.reserve_forward(scene(2.91, x=9.0))
    assert budget.stage == "halted" and budget.pulses == 3


def test_missing_fix_overlong_hold_or_new_target_latches_halt():
    budget = ready()
    arm(budget, 0.5)
    with pytest.raises(G2Halt, match="duration"):
        budget.record_hold(scene(0.65), 0.21)
    assert budget.stage == "halted"

    budget = ready()
    arm(budget, 0.5)
    budget.record_hold(scene(0.65), 0.15)
    with pytest.raises(G2Halt, match="unsafe"):
        budget.record_fix(scene(0.8, x=3, target_absent=False))
    assert budget.stage == "halted"


def test_postrelease_drift_and_time_window_do_not_pass():
    budget = ready()
    pulse(budget, 0.5, 0.85, 3.0)
    with pytest.raises(G2Halt, match="stopped"):
        budget.finish(scene(1.75, x=3.4), scene(2.2, x=3.4))
    assert budget.stage == "halted"

    budget = ready()
    with pytest.raises(G2Halt, match="unsafe"):
        budget.reserve_forward(scene(16.0))


def test_second_pulse_needs_delayed_stillness_and_verified_speed_bound():
    budget = ready()
    arm(budget, 0.5)
    budget.record_hold(scene(0.65), 0.15)
    budget.record_fix(scene(0.85, x=3.0))
    with pytest.raises(G2Halt, match="wrong phase"):
        budget.reserve_forward(scene(0.85, x=3.0))
    assert budget.stage == "halted" and budget.pulses == 1

    budget = ready()
    arm(budget, 0.5)
    budget.record_hold(scene(0.65), 0.15)
    budget.record_fix(scene(0.85, x=3.0))
    with pytest.raises(G2Halt, match="continued"):
        budget.record_still(scene(1.3, x=3.4))

    with pytest.raises(G2Halt, match="calibration"):
        ready(bound=1)
    with pytest.raises(G2Halt, match="budget"):
        ready(radius=1, speed=1).reserve_forward(scene(0.5))


def test_stale_hold_and_reused_or_slow_fixes_are_rejected():
    budget = ready()
    arm(budget, 0.5)
    with pytest.raises(G2Halt, match="duration"):
        budget.record_hold(scene(10.5), 0.15)

    budget = ready()
    arm(budget, 0.5)
    budget.record_hold(scene(0.65), 0.15)
    with pytest.raises(G2Halt, match="position"):
        budget.record_fix(scene(0.85, x=3, fix_seq=51))

    budget = ready()
    pulse(budget, 0.5, 0.85, 3.0)
    with pytest.raises(G2Halt, match="stopped"):
        budget.finish(scene(1.75, x=3.0), scene(14.9, x=3.0))


def test_off_cancels_a_queued_pulse_before_keydown():
    budget = ready()
    permit = budget.reserve_forward(scene(0.5))
    budget.cancel()
    with pytest.raises(G2Halt, match="cancelled"):
        budget.confirm_keydown(scene(0.51), permit)
    assert budget.pulses == 0 and budget.stage == "halted"
