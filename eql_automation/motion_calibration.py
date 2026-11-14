"""Reduce a finite stop/observe experiment using the retained navigation code.

This module sends no input and does not authorize its proposed experiment.
The initial travel envelope and current scene must be resolved independently.
Endpoint bearings cannot rule out extra full turns, and descriptor timestamps
do not establish client input-consumption times. Results are conditional
estimates, never a verified maximum speed or an accepted live calibration.
"""
from dataclasses import asdict, dataclass
import math
from statistics import median

from .uinput_watchdog import PulseReceipt


class CalibrationUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class Probe:
    key: str
    key_code: int
    seconds: float


# Experiment choices, not constants obtained from the game. No initial
# heading is needed: each forward leg measures the heading after its turn.
PROBES = (Probe("forward", 103, .10), Probe("right", 106, .05),
          Probe("forward", 103, .10), Probe("right", 106, .15),
          Probe("forward", 103, .10), Probe("left", 105, .15),
          Probe("forward", 103, .10))


@dataclass(frozen=True)
class Position:
    at: float                         # received monotonic; not game timestamp
    sequence: int
    raw_yxz: tuple[float, float, float]
    zone: str | None                   # None for explicitly relative measurement
    log_epoch: int
    zone_generation: int | None


@dataclass(frozen=True)
class StoppedPair:
    first: Position
    second: Position


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def pair_geometry(pair, horizontal_error):
    a, b = pair.first.raw_yxz, pair.second.raw_yxz
    return (tuple((x+y)/2 for x,y in zip(a,b)),
            horizontal_error + math.dist(a[:2], b[:2])/2)


def measure_forward(index, before, after, receipt, *, legacy, horizontal_error):
    """Shared incremental/complete estimator after validated pair/receipt input."""
    start, e1 = pair_geometry(before, horizontal_error)
    end, e2 = pair_geometry(after, horizontal_error)
    distance, error = math.dist(start[:2], end[:2]), e1 + e2
    if distance <= error:
        raise CalibrationUnavailable("Forward displacement cannot resolve a heading")
    low = receipt.up_started_at - receipt.down_completed_at
    high = receipt.maximum_held_seconds
    return dict(index=index, displacement=distance,
        heading=legacy.bearing(legacy.Loc(*start), legacy.Loc(*end)),
        heading_error_degrees=math.degrees(math.asin(error/distance)),
        speed=distance/((low+high)/2),
        conditional_speed_interval=((distance-error)/high, (distance+error)/low))


def common_speed(legs):
    low = max(leg["conditional_speed_interval"][0] for leg in legs)
    high = min(leg["conditional_speed_interval"][1] for leg in legs)
    if low > high:
        raise CalibrationUnavailable("Forward samples contradict a constant-speed estimate")
    return min(max(median(leg["speed"] for leg in legs), low), high), low, high


def measure_turn(index, before, after, receipt, *, legacy):
    delta = legacy.wrap180(after["heading"] - before["heading"])
    error = before["heading_error_degrees"] + after["heading_error_degrees"]
    if abs(delta) <= error or abs(delta) + error >= 180:
        raise CalibrationUnavailable("Turn is inactive/ambiguous under the position-error assumption")
    low = receipt.up_started_at - receipt.down_completed_at
    high = receipt.maximum_held_seconds
    return dict(index=index, seconds=(low+high)/2, seconds_interval=(low,high),
                delta=delta, delta_error=error)


def reduce_experiment(pairs, receipts, *, legacy, horizontal_error, record_id):
    """Analyze eight stationary pairs and seven actual release receipts.

    ``legacy`` is the pinned owner's navigation module (Loc, bearing, wrap180,
    fit_calibration). ``horizontal_error`` is an explicit assumed XY error
    radius for each printed fix, not a verified precision claim. The result
    retains raw samples, timing and conditional uncertainty for later review.
    It cannot be fed to the legacy saved-calibration loader as a live result.
    """
    if len(pairs) != 8:
        raise CalibrationUnavailable("Need eight stopped pairs")
    return _reduce_legs(pairs[:-1], pairs[1:], receipts, pairs=pairs,
        legacy=legacy, horizontal_error=horizontal_error, record_id=record_id,
        separated=False)


def reduce_probe_legs(before, after, receipts, *, legacy, horizontal_error, record_id):
    """Fit seven individually observed probes without inventing shared pairs.

    Each before/after pair is kept at its actual time. Quiet gaps are checked
    for translation; unchanged heading across those gaps remains an assumption.
    The seven keys and requested durations must match PROBES exactly.
    """
    if len(before) != 7 or len(after) != 7:
        raise CalibrationUnavailable("Need seven distinct before/after pairs")
    pairs = [pair for leg in zip(before, after) for pair in leg]
    return _reduce_legs(before, after, receipts, pairs=pairs, legacy=legacy,
        horizontal_error=horizontal_error, record_id=record_id, separated=True)


def _reduce_legs(before, after, receipts, *, pairs, legacy, horizontal_error,
                 record_id, separated):
    if (len(receipts) != 7 or not isinstance(record_id, str)
            or not record_id.strip() or not finite(horizontal_error) or horizontal_error <= 0):
        raise CalibrationUnavailable("Need seven receipts and an explicit positive position-error assumption")
    binding = None
    previous = None
    for pair in pairs:
        if not isinstance(pair, StoppedPair):
            raise CalibrationUnavailable("Expected a stopped position pair")
        for fix in (pair.first, pair.second):
            if (not isinstance(fix, Position) or not finite(fix.at) or fix.at < 0
                    or not integer(fix.sequence) or not integer(fix.log_epoch)
                    or not ((fix.zone is None and fix.zone_generation is None)
                        or (isinstance(fix.zone, str) and bool(fix.zone)
                            and integer(fix.zone_generation)))
                    or not isinstance(fix.raw_yxz, (tuple, list)) or len(fix.raw_yxz) != 3
                    or not all(finite(v) for v in fix.raw_yxz)):
                raise CalibrationUnavailable("Invalid raw position/provenance")
            current = (fix.zone, fix.log_epoch, fix.zone_generation)
            if binding is None:
                binding = current
            if current != binding or (previous and (
                    fix.sequence <= previous.sequence or fix.at <= previous.at)):
                raise CalibrationUnavailable("Repeated/reordered fixes or zone/log generation changed")
            previous = fix
        a, b = pair.first, pair.second
        drift = math.dist(a.raw_yxz[:2], b.raw_yxz[:2])
        if (not .4 - 1e-9 <= b.at - a.at <= 2.5 or drift > .25
                or abs(a.raw_yxz[2] - b.raw_yxz[2]) > .25):
            raise CalibrationUnavailable("Positions do not form a stopped pair")
    if pairs[-1].second.at - pairs[0].first.at > 120:
        raise CalibrationUnavailable("Finite experiment exceeded its 120-second analysis window")

    if separated:
        for index in range(6):
            p, r = pair_geometry(after[index], horizontal_error)
            q, s = pair_geometry(before[index+1], horizontal_error)
            if math.dist(p[:2], q[:2]) > min(.25, r+s) or abs(p[2]-q[2]) > .25:
                raise CalibrationUnavailable("Unexplained translation between probe legs")

    for index, (probe, receipt) in enumerate(zip(PROBES, receipts)):
        if not isinstance(receipt, PulseReceipt):
            raise CalibrationUnavailable("Actual child DOWN/UP receipt required; legacy elapsed time is insufficient")
        stamps = (receipt.down_started_at, receipt.down_completed_at,
                  receipt.up_started_at, receipt.up_completed_at)
        if (not integer(receipt.key_code) or receipt.key_code != probe.key_code
                or not finite(receipt.requested_seconds) or receipt.requested_seconds != probe.seconds
                or receipt.completion != "elapsed" or not all(finite(v) for v in stamps)
                or not stamps[0] <= stamps[1] < stamps[2] <= stamps[3]
                or not 0 < receipt.maximum_held_seconds <= .2
                or stamps[2] - stamps[1] < probe.seconds - 1e-9
                or not 0 <= stamps[0] - before[index].second.at <= .5
                or not .12 - 1e-9 <= after[index].first.at - stamps[3] <= 2.5):
            raise CalibrationUnavailable("Wrong key/duration, cancelled receipt, overrun or out-of-order stopped observation")
        start, start_error = pair_geometry(before[index], horizontal_error)
        end, end_error = pair_geometry(after[index], horizontal_error)
        if abs(end[2] - start[2]) > .25:
            raise CalibrationUnavailable("Experiment changed height")
        if (probe.key != "forward" and math.dist(start[:2], end[:2])
                > min(.25, start_error + end_error)):
            raise CalibrationUnavailable("Turn translated the character; possible strafe or residual movement")

    legs = []
    for index in (0, 2, 4, 6):
        legs.append(measure_forward(index, before[index], after[index], receipts[index],
                                    legacy=legacy, horizontal_error=horizontal_error))
    # An overlap is needed before treating four legs as a constant-speed fit.
    speed, speed_low, speed_high = common_speed(legs)

    turns = []
    for index, left_leg, right_leg in zip((1, 3, 5), legs, legs[1:]):
        turns.append(measure_turn(index, left_leg, right_leg, receipts[index], legacy=legacy))
    short, long, left = turns
    if short["delta"] * long["delta"] <= 0 or short["delta"] * left["delta"] >= 0:
        raise CalibrationUnavailable("Right/left direction measurements contradict one another")
    t1, t2 = short["seconds"], long["seconds"]
    a1, a2 = abs(short["delta"]), abs(long["delta"])
    dt_low = long["seconds_interval"][0] - short["seconds_interval"][1]
    dt_high = long["seconds_interval"][1] - short["seconds_interval"][0]
    if dt_low <= 0 or a2 - a1 <= short["delta_error"] + long["delta_error"]:
        raise CalibrationUnavailable("The two active turn samples do not identify a rate")
    rate = (a2 - a1) / (t2 - t1)
    latency = t1 - a1 / rate
    # Crucial: the retained fit clamps latency. Reject an impossible intercept
    # first instead of allowing that clamp to manufacture a valid-looking fit.
    if not 0 <= latency <= min(.2, legacy.LATENCY_MAX):
        raise CalibrationUnavailable("Unclamped turn latency is outside the bounded model")
    rate_low = (a2 - a1 - short["delta_error"] - long["delta_error"]) / dt_high
    rate_high = (a2 - a1 + short["delta_error"] + long["delta_error"]) / dt_low
    latency_low = short["seconds_interval"][0] - (a1 + short["delta_error"]) / rate_low
    latency_high = short["seconds_interval"][1] - (a1 - short["delta_error"]) / rate_high
    expected = rate * max(0., left["seconds"] - latency)
    expected_low = rate_low * max(0., left["seconds_interval"][0] - latency_high)
    expected_high = rate_high * max(0., left["seconds_interval"][1] - latency_low)
    actual_low = abs(left["delta"]) - left["delta_error"]
    actual_high = abs(left["delta"]) + left["delta_error"]
    if actual_high < expected_low or actual_low > expected_high:
        raise CalibrationUnavailable("Independent left-turn trial contradicts the fitted right turns")
    try:
        fitted = legacy.fit_calibration(speed, (t1, short["delta"]), (t2, long["delta"]),
            (left["seconds"], left["delta"]), now=0.)
    except legacy.CalibrationError as exc:
        raise CalibrationUnavailable("Retained fit domain not resolved: " + str(exc)) from exc
    result = dict(format="eql-conditional-motion-estimate-v1", record_id=record_id,
        zone_binding=dict(zone=binding[0], generation=binding[2],
                          source='unbound' if binding[0] is None else 'supplied_log_binding'),
        input_authorized=False, real_client_accepted=False, live_calibration_verified=False,
        verified_speed_upper_bound=None, full_turn_ambiguity_resolved=False,
        client_consumption_timing_verified=False,
        assumptions=["supplied horizontal error radius bounds each fix",
            "each stopped pair represents one stationary position between samples",
            "each forward leg is straight with fixed heading and speed",
            "turning is a constant-rate pivot after a fixed latency",
            "turns contain no unobserved complete revolution",
            "descriptor hold spans model client-held time",
            "stopped fixes were requested after release without an older request in flight"],
        horizontal_error_assumed=horizontal_error,
        interval_semantics="conservative outer bounds conditional on assumptions, not confidence intervals",
        total_requested_hold=sum(probe.seconds for probe in PROBES),
        total_maximum_descriptor_hold=sum(r.maximum_held_seconds for r in receipts),
        speed_estimator="median projected into common conditional interval",
        estimate=dict(run_speed=fitted.run_speed, turn_rate=fitted.turn_rate,
            turn_latency=fitted.turn_latency, right_sign=fitted.right_sign,
            final_heading=legs[-1]["heading"], back_speed=None),
        conditional_intervals=dict(speed=(speed_low, speed_high), turn_rate=(rate_low, rate_high),
                                   unclamped_latency=(latency_low, latency_high)),
        independent_left_residual_degrees=abs(left["delta"]) - expected,
        forward_legs=legs, turns=turns, pairs=[asdict(p) for p in pairs],
        receipts=[asdict(r) for r in receipts], proposed_sequence=[asdict(p) for p in PROBES])

    if separated:
        result.update(format="eql-conditional-separated-motion-estimate-v1",
            before_pairs=[asdict(p) for p in before], after_pairs=[asdict(p) for p in after],
            final_observed_at=after[-1].second.at, current_heading_verified=False)
        result.pop("pairs")
        result["assumptions"].append("no unobserved heading change between probe legs")
    return result
