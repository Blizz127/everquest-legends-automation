"""Synthetic geometry plus the owner's actual pinned fitting implementation."""
from dataclasses import replace
from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import time

import pytest

from eql_automation.motion_calibration import (CalibrationUnavailable, Position, PROBES,
                                             StoppedPair, reduce_experiment)
from eql_automation.uinput_watchdog import PulseReceipt, timed_key_pulse_receipt, _EVENT


PIN = "69dbc6472447942cc30dbe592a6e1cf02998c0a0b8811a8bb59672655dc4049e"
SOURCE = Path.home()/".local/share/eql-automation/owner-assist/0.39.10/navigation.py"


@pytest.fixture(scope="module")
def legacy():
    if not SOURCE.exists():
        pytest.skip("Requires retained owner navigation source")
    assert sha256(SOURCE.read_bytes()).hexdigest() == PIN
    spec = importlib.util.spec_from_file_location("calibration_retained_navigation", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def experiment(*, sign=-1, heading=350., speed=30., rate=170., latency=.03,
               rounded=False, actual_receipts=None, left_multiplier=1.):
    pairs, receipts = [], []
    point = (0., 0., 0.)
    def pair(at):
        coords = tuple(round(v, 2) for v in point) if rounded else point
        seq = len(pairs) * 2
        return StoppedPair(Position(at, seq, coords, "synthetic", 2, 3),
                           Position(at+.4, seq+1, coords, "synthetic", 2, 3))
    pairs.append(pair(100. if actual_receipts is None else actual_receipts[0].down_started_at-.5))
    for index, probe in enumerate(PROBES):
        start = pairs[-1].second.at+.01
        receipt = (PulseReceipt(probe.key_code, probe.seconds, start, start+.0002,
                     start+.0002+probe.seconds, start+.0004+probe.seconds, "elapsed")
                   if actual_receipts is None else actual_receipts[index])
        receipts.append(receipt)
        seconds = ((receipt.up_started_at-receipt.down_completed_at)
                   +(receipt.up_completed_at-receipt.down_started_at))/2
        if probe.key == "forward":
            rad = math.radians(heading)
            point = (point[0]+math.cos(rad)*speed*seconds,
                     point[1]+math.sin(rad)*speed*seconds, point[2])
        else:
            heading = (heading+sign*(1 if probe.key == "right" else -1)
                       *rate*(left_multiplier if probe.key == "left" else 1.)
                       *max(0., seconds-latency)) % 360
        pairs.append(pair(receipt.up_completed_at+.13))
    return pairs, receipts, heading


def reduce(legacy, pairs, receipts, **kw):
    return reduce_experiment(pairs, receipts, legacy=legacy, horizontal_error=.01,
                             record_id="synthetic-receipts-only", **kw)


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("heading", [0., 90., 350.])
@pytest.mark.parametrize("rounded", [False, True])
def test_fits_without_initial_motion_and_never_certifies_a_bound(legacy, sign, heading, rounded):
    pairs, receipts, final = experiment(sign=sign, heading=heading, rounded=rounded)
    report = reduce(legacy, pairs, receipts)
    estimate = report["estimate"]
    assert estimate["run_speed"] == pytest.approx(30., abs=.05)
    if rounded:
        low, high = report["conditional_intervals"]["turn_rate"]
        assert low <= 170. <= high
        assert low <= estimate["turn_rate"] <= high
    else:
        assert estimate["turn_rate"] == pytest.approx(170.)
    assert estimate["turn_latency"] == pytest.approx(.03, abs=.002)
    assert estimate["right_sign"] == sign
    assert abs(legacy.wrap180(estimate["final_heading"]-final)) < .25
    assert estimate["back_speed"] is None
    assert report["verified_speed_upper_bound"] is None
    for flag in ("input_authorized", "real_client_accepted", "live_calibration_verified",
                 "full_turn_ambiguity_resolved", "client_consumption_timing_verified"):
        assert report[flag] is False
    assert legacy.Calibration.from_json(report) is None
    assert len(report["receipts"]) == 7 and len(report["pairs"]) == 8


def test_inactive_short_sample_is_rejected_before_legacy_latency_clamp(legacy):
    pairs, receipts, _ = experiment(latency=.08)
    with pytest.raises(CalibrationUnavailable, match="inactive/ambiguous"):
        reduce(legacy, pairs, receipts)


def test_negative_unclamped_latency_is_rejected(legacy):
    pairs, receipts, _ = experiment(latency=-.02)
    with pytest.raises(CalibrationUnavailable, match="Unclamped"):
        reduce(legacy, pairs, receipts)


def test_left_point_residual_rejected_even_when_outer_intervals_overlap(legacy):
    pairs, receipts, _ = experiment(left_multiplier=1.35)
    with pytest.raises(CalibrationUnavailable, match="Retained fit domain.*mirror images"):
        reduce_experiment(pairs, receipts, legacy=legacy, horizontal_error=.02, record_id="left-residual")


def test_identifiable_slow_turn_reports_legacy_fit_domain_limit(legacy):
    pairs, receipts, _ = experiment(rate=80.)
    with pytest.raises(CalibrationUnavailable, match="Retained fit domain.*did not grow"):
        reduce(legacy, pairs, receipts)


@pytest.mark.parametrize("change", ["old_elapsed", "cancelled", "long", "too_short", "wrong_key",
    "request", "nan", "unordered", "wrong_generation", "repeated_fix", "moving_pair",
    "turn_translation", "height", "early_fix", "missing", "speed_change", "left_strafe"])
def test_incomplete_or_contradictory_measurements_rejected(legacy, change):
    pairs, receipts, _ = experiment()
    if change == "old_elapsed": receipts[0] = .1508157029893482
    elif change == "cancelled": receipts[0] = replace(receipts[0], completion="stopped")
    elif change == "long": receipts[0] = replace(receipts[0], up_completed_at=receipts[0].down_started_at+.201)
    elif change == "too_short":
        receipts[0] = replace(receipts[0], up_started_at=receipts[0].down_completed_at+.02,
                              up_completed_at=receipts[0].down_completed_at+.021)
    elif change == "wrong_key": receipts[0] = replace(receipts[0], key_code=105)
    elif change == "request": receipts[0] = replace(receipts[0], requested_seconds=.11)
    elif change == "nan": receipts[0] = replace(receipts[0], down_started_at=float("nan"))
    elif change == "unordered": receipts[1], receipts[3] = receipts[3], receipts[1]
    elif change == "wrong_generation": pairs[2] = replace(pairs[2], second=replace(pairs[2].second, log_epoch=4))
    elif change == "repeated_fix": pairs[2] = replace(pairs[2], second=replace(pairs[2].second, sequence=0))
    elif change == "moving_pair": pairs[2] = replace(pairs[2], second=replace(pairs[2].second, raw_yxz=(9.,9.,0.)))
    elif change in ("turn_translation", "height", "speed_change", "left_strafe"):
        index = {"turn_translation":2, "height":3, "speed_change":7, "left_strafe":6}[change]
        pair = pairs[index]
        y,x,z = pair.first.raw_yxz
        coords = (y,x,z+1) if change=="height" else (y+1,x,z)
        pairs[index] = StoppedPair(replace(pair.first,raw_yxz=coords),replace(pair.second,raw_yxz=coords))
    elif change == "early_fix": pairs[1] = replace(pairs[1], first=replace(pairs[1].first,at=receipts[0].up_completed_at))
    else: pairs.pop()
    with pytest.raises(CalibrationUnavailable): reduce(legacy, pairs, receipts)


def test_large_error_refuses_unresolved_heading(legacy):
    pairs, receipts, _ = experiment()
    with pytest.raises(CalibrationUnavailable, match="resolve a heading"):
        reduce_experiment(pairs, receipts, legacy=legacy, horizontal_error=3., record_id="large-error")


def test_actual_child_receipts_on_pipe_then_synthetic_positions(legacy):
    """The actual watchdog writes only a pipe. All position feedback is simulated."""
    rd, wr = os.pipe()
    receipts = []
    try:
        for index, probe in enumerate(PROBES):
            if index:
                # Make room for the explicit synthetic stopped pair; this is
                # a test-clock wait, never game input or an owner test.
                time.sleep(.54)
            receipts.append(timed_key_pulse_receipt(wr, probe.key_code, probe.seconds))
    finally:
        os.close(wr)
    data = os.read(rd, 65536)
    os.close(rd)
    events = [(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    assert len(events) == 42
    for index, probe in enumerate(PROBES):
        assert events[index*6:index*6+6] == [(1,probe.key_code,1),(0,0,0),
            (1,probe.key_code,0),(0,0,0),(1,probe.key_code,0),(0,0,0)]
    pairs, receipts, _ = experiment(actual_receipts=receipts)
    report = reduce(legacy, pairs, receipts)
    assert report["estimate"]["turn_rate"] == pytest.approx(170.)
    assert report["real_client_accepted"] is False


def test_cli_pins_inputs_and_preserves_existing_output(tmp_path):
    if not SOURCE.exists():
        pytest.skip("Requires retained navigation source")
    store = tmp_path/".local/share/eql-automation"
    store.mkdir(parents=True)
    navigation = store/"navigation.py"
    navigation.write_bytes(SOURCE.read_bytes())
    pairs, receipts, _ = experiment(rounded=True)
    path = store/"experiment.json"
    path.write_text(json.dumps(dict(format="eql-motion-experiment-v1", record_id="synthetic-cli",
        horizontal_error=.01, pairs=[asdict(p) for p in pairs], receipts=[asdict(r) for r in receipts])))
    output = store/"result.json"
    command = [sys.executable, "tools/reduce_motion_calibration.py", "--input", str(path),
        "--input-sha256", sha256(path.read_bytes()).hexdigest(), "--navigation", str(navigation),
        "--output", str(output)]
    env = dict(os.environ, HOME=str(tmp_path))
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    original = output.read_bytes()
    assert not json.loads(original)["input_authorized"]
    assert subprocess.run(command, capture_output=True, env=env).returncode != 0
    assert output.read_bytes() == original
    command[-1] = str(store/"changed-input.json")
    path.write_text(path.read_text()+"\n")
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    assert result.returncode != 0 and "Experiment hash changed" in result.stderr
    assert not Path(command[-1]).exists()
