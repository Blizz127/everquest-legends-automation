"""Conditional motion fit from a completed, still-owned camp probe sequence.

Use each transaction's actual immediate before/after observations. Later
confirmation and planning pairs establish continuity, never new timestamps for
old measurements. This record neither authorizes input nor bounds future speed.
"""
from dataclasses import asdict
from hashlib import sha256
import math

from .camp_probe_preparation import _raw_record
from .camp_probe_transaction import CampProbeTransaction
from .motion_calibration import (CalibrationUnavailable, Position, StoppedPair,
    PROBES, pair_geometry, reduce_probe_legs)
from .native_region_policy import encoded


def _pair(first, second):
    def position(raw):
        return Position(raw.received_monotonic, raw.log_line_seq, raw.raw_coordinates,
                        'zone-id:'+str(raw.zone_id), raw.log_epoch, raw.zone_generation)
    return StoppedPair(position(first), position(second))


def _gap(left, right, error):
    a, b = left.second, right.first
    if (a.sequence >= b.sequence or a.at >= b.at
            or (a.zone, a.log_epoch, a.zone_generation) != (b.zone, b.log_epoch, b.zone_generation)):
        raise CalibrationUnavailable('Repeated/reordered camp continuity observations')
    p, r = pair_geometry(left, error)
    q, s = pair_geometry(right, error)
    if math.dist(p[:2], q[:2]) > min(.25, r+s) or abs(p[2]-q[2]) > .25:
        raise CalibrationUnavailable('Unexplained translation during camp probe collection')


def reduce_camp_probes(runtime, *, legacy, record_id):
    """Consume no cursor, send no input and retain no live calibration authority."""
    from .camp_probe_runtime import CampProbeRuntime
    if type(runtime) is not CampProbeRuntime:
        raise ValueError('Exact camp probe runtime required')
    with runtime.lock:
        def capture():
            runtime._check()
            if (runtime.phase != 'complete' or runtime.busy or runtime.closed
                    or runtime.sender.held or getattr(runtime.sender, '_eql_route_operation', None) is not None):
                raise ValueError('Completed idle camp probes must still own their scope')
            if (runtime.probes != PROBES or len(runtime.transactions) != 7
                    or len(runtime.results) != 7 or runtime.index != 7):
                raise CalibrationUnavailable('Calibration requires the complete standard seven-probe sequence')
            before, after, receipts, confirmations, planning, evidence, identities = [], [], [], [], [], [], []
            parent = runtime.root.checkpoint
            for index, (tx, result, probe) in enumerate(zip(runtime.transactions, runtime.results, PROBES)):
                if (type(tx) is not CampProbeTransaction or tx.phase != 'continued'
                        or tx.result is not result or tx.lock is not runtime.lock
                        or tx.preparation.checkpoint is not parent
                        or tx.preparation.lease is not runtime.lease
                        or tx.preparation.reader is not runtime.lease.reader
                        or tx.preparation.clock is not runtime.clock
                        or tx._continuation is None or tx._continuation._result is not result
                        or tx.preparation.bounds is not runtime.root.bounds
                        or tx.preparation.bounds_basis != runtime.root.bounds_basis
                        or tx.ticket.kind != probe.key or tx.ticket.movement_key != probe.key_code
                        or tx.ticket.requested_seconds != probe.seconds):
                    raise ValueError('Camp calibration transaction chain changed')
                tx._check(); tx._continuation.check()
                if index == 0 and tx.preparation is not runtime.root:
                    raise ValueError('Camp calibration root changed')
                start = tx.ticket.start.height
                before.append(_pair(start.first, start.second))
                after.append(_pair(*tx._planning_pair))
                receipts.append(tx.seal.receipt)
                confirmations.append(_pair(result.first, result.second))
                h = tx.preparation.height
                planning.append(_pair(h.first, h.second))
                evidence.append(dict(preparation_sha256=tx.preparation.sha256,
                    result_sha256=result.sha256, floor_sha256=tx._continuation.sha256,
                    start_height_sha256=start.sha256, planning_height_sha256=h.sha256,
                    raw_z_minus_source_z=result.raw_z_minus_source_z,
                    planning=[_raw_record(h.first), _raw_record(h.second)],
                    before=[_raw_record(start.first), _raw_record(start.second)],
                    after=[_raw_record(raw) for raw in tx._planning_pair],
                    confirmation=[_raw_record(result.first), _raw_record(result.second)],
                    receipt=asdict(tx.seal.receipt)))
                identities.append((id(tx), id(result), id(tx.preparation), id(tx._continuation)))
                parent = tx._continuation
            if runtime.reference is not parent:
                raise ValueError('Camp calibration final floor differs from its last probe')
            return before, after, receipts, confirmations, planning, evidence, identities

        before, after, receipts, confirmations, planning, evidence, identities = capture()
        frozen = encoded(evidence)
        error = runtime.root.bounds.position_error
        for i in range(7):
            _gap(planning[i], before[i], error)
            _gap(after[i], confirmations[i], error)
            if i:
                _gap(confirmations[i-1], planning[i], error)
                if abs(evidence[i]['raw_z_minus_source_z']-evidence[i-1]['raw_z_minus_source_z']) > .05:
                    raise CalibrationUnavailable('Camp probe height correspondence changed')
        if confirmations[-1].second.at - before[0].first.at > 120:
            raise CalibrationUnavailable('Camp calibration exceeded its 120-second analysis window')
        try:
            result = reduce_probe_legs(before, after, receipts, legacy=legacy,
                                      horizontal_error=error, record_id=record_id)
        finally:
            # Even an unidentifiable fit must not disguise a callback that
            # cancelled or changed the actual probe scope.
            checked = capture()
            if checked[-1] != identities or encoded(checked[-2]) != frozen:
                raise ValueError('Camp calibration changed during reduction')
        result.update(format='eql-conditional-camp-motion-estimate-v1',
            source_floor_sha256=runtime.root.checkpoint.sha256,
            reached_floor_sha256=runtime.reference.sha256,
            retained_evidence=evidence, retained_evidence_sha256=sha256(frozen).hexdigest(),
            confirmed_at=confirmations[-1].second.at, sender_origin_verified=False)
        return result
