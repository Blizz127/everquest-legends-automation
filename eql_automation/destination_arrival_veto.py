"""Transfer an arrival's continuous hazard history to destination preparation.

This is a one-use observer handoff, not a movement permit. It neither polls the
location reader nor issues input. A failed claim also retires the old arrival;
its caller remains responsible for the enclosing runtime's cleanup.
"""
from .ground_binding import finite
from .location_log import LocationLogReader, NonReplayingLogTail, RawLocationFix
from .owner_zone_tracker import ZoneReaderLease
from .scene_log_veto import ExpectedArrivalLogVeto, SceneLogVeto
from .stopped_location_pair import StoppedLocationPair
from .zone_arrival import ZoneArrivalHandoff


_RETIRED = 'Destination hazard observer transferred'
_TAIL_FIELDS = ('path', 'max_bytes', 'include_first_created_file',
    'awaiting_first_creation', 'initialized', 'identity', 'position', 'partial',
    'anchor', 'epoch')
_VETO_FIELDS = ('cancel_generation', 'clock', '_last_finished', '_last_log_time',
    '_line_seq', '_latched')


def _values(obj, fields):
    return tuple(getattr(obj, name) for name in fields)


def _binding(a):
    """Pin the completed reader/pair without executing arrival callbacks."""
    r, p, v = a.reader, a.collector, a.veto
    return (id(a.lease), id(r), id(r.tail), id(p), id(p.first), id(p.second),
        id(p.latest), id(r.latest), p.phase, p.seq, p.zone, p.owner,
        id(p.lease), id(p.reader), p.pending, a.owner, a.destination,
        a.destination_id, a.source_generation, a.entry, a.loading, a.release,
        a.log_binding, a.veto_binding, a.last_at, a.deadline, id(a.clock),
        id(a.check_current), r.zone_id, r.zone_display_name, r.zone_generation,
        r.log_line_seq, tuple(r.zone_ids.items()), _values(r.tail, _TAIL_FIELDS),
        id(v), id(v.tail), v.destination, _values(v.tail, _TAIL_FIELDS),
        _values(v, _VETO_FIELDS))


def _require_completed(a):
    if (type(a) is not ZoneArrivalHandoff or a.phase != 'complete'
            or hasattr(a, '_destination_veto_claim')):
        raise ValueError('One unclaimed completed ZoneArrivalHandoff required')
    r, p, v = a.reader, a.collector, a.veto
    if (type(a.lease) is not ZoneReaderLease or not a.lease.active
            or type(r) is not LocationLogReader or a.lease.reader is not r
            or type(p) is not StoppedLocationPair or p.phase != 'complete'
            or p.lease is not a.lease or p.reader is not r or p.owner != a.owner
            or type(p.first) is not RawLocationFix or type(p.second) is not RawLocationFix
            or p.pending is not None or p.latest is not p.second or r.latest is not p.second
            or r.log_line_seq != p.seq or p.seq != p.second.log_line_seq
            or p.second.log_line_seq != p.first.log_line_seq + 1
            or type(r.tail) is not NonReplayingLogTail
            or type(v) is not ExpectedArrivalLogVeto
            or type(v.tail) is not NonReplayingLogTail
            or v.destination != a.destination
            or type(v.cancel_generation) is not int or v.cancel_generation < 0
            or v.clock is not a.clock or not callable(a.check_current)
            or a.entry is None or a.loading is None or a.release is None):
        raise ValueError('Completed arrival lease, generation and destination pair required')
    zone = (a.destination_id, a.destination, a.entry.zone_generation)
    log = (r.tail.identity, r.tail.epoch)
    if ((r.zone_id, r.zone_display_name, r.zone_generation) != zone
            or r.zone_ids.get(a.destination) != a.destination_id
            or a.entry.kind != 'entered' or a.loading.kind != 'loading'
            or (a.entry.zone_id, a.entry.zone_name) != zone[:2]
            or a.entry.zone_generation <= a.source_generation
            or p.zone != (*zone[:2], *log, zone[2])
            or any((raw.zone_id, raw.zone_display_name, raw.zone_generation) != zone
                   or raw.log_epoch != r.tail.epoch for raw in (p.first, p.second))
            or not .4 <= p.second.received_monotonic-p.first.received_monotonic <= 2.5
            or log != a.log_binding or log != a.veto_binding or log[0] is None
            or (v.tail.identity, v.tail.epoch) != log
            or v.tail.path != r.tail.path
            or (v.tail.position != r.tail.position and v._latched is None)
            or v.tail.partial or r.tail.partial):
        raise ValueError('Completed destination pair or continuous log binding changed')


def continue_destination_veto(arrival):
    """Claim a completed arrival and return an exact, ordinary ``SceneLogVeto``.

    The expected-transition exemptions end before any callback or log poll.
    Cursor, anchor, epoch, timestamps, sequence and any latched veto are copied
    without constructing an EOF baseline. The old controller becomes stopped,
    retaining its complete pair and active lease; snapshot completion evidence
    before calling if needed. Subsequent arrival ticks cannot consume either
    reader or invoke its release callback. Duplicate/failed claims cannot retry.

    The caller must keep enforcing the destination lease, cancellation and UI
    bindings while using the returned observer. A quiet log grants no authority.
    """
    _require_completed(arrival)
    original = arrival.veto
    pinned = _binding(arrival)
    # These objects contain cursor state only, not open handles. Copy each known
    # field so no baseline read can skip bytes appended after the last arrival
    # check, and so the retired observer cannot advance the destination cursor.
    continued = SceneLogVeto.__new__(SceneLogVeto)
    continued.tail = NonReplayingLogTail.__new__(NonReplayingLogTail)
    for name in _TAIL_FIELDS:
        setattr(continued.tail, name, getattr(original.tail, name))
    for name in _VETO_FIELDS:
        setattr(continued, name, getattr(original, name))
    claim = object()
    arrival._destination_veto_claim = claim
    arrival._destination_log_veto = continued
    original_reason = arrival.reason

    def unchanged():
        if (arrival._destination_veto_claim is not claim
                or arrival._destination_log_veto is not continued
                or arrival.phase != 'complete' or arrival.reason != original_reason
                or _binding(arrival) != pinned or not arrival.lease.active
                or continued.cancel_generation != original.cancel_generation
                or continued.clock is not original.clock
                or arrival.lease._tracker.lease is not arrival.lease
                or arrival.lease._tracker.reader is not arrival.reader
                or arrival.lease._tracker.closed):
            raise ValueError('Destination veto handoff context changed')

    try:
        arrival.check_current()
        owner = arrival.lease.check()
        now = arrival.clock()
        unchanged()
        if (owner != arrival.owner or not finite(now)
                or not arrival.last_at <= now <= arrival.deadline
                or arrival.collector.second.received_monotonic > now):
            raise ValueError('Destination veto owner, generation or deadline changed')
        observation = continued.poll()
        unchanged()
        if not observation.continuity_available or observation.reason is not None:
            raise ValueError('Destination hazard observer veto: '+str(observation.reason))
        if not now <= observation.finished_at <= arrival.deadline:
            raise ValueError('Destination veto observation exceeded arrival deadline')
        # A clock used by poll may pump cancellation or replace the process.
        # Recheck callbacks, then scan again under the strict classifier so
        # hazards appended by those final callbacks are not skipped either.
        arrival.check_current()
        owner = arrival.lease.check()
        unchanged()
        if owner != arrival.owner:
            raise ValueError('Destination veto owner changed during observation')
        observation = continued.poll()
        unchanged()
        if not observation.continuity_available or observation.reason is not None:
            raise ValueError('Destination hazard observer veto: '+str(observation.reason))
        if not now <= observation.finished_at <= arrival.deadline:
            raise ValueError('Destination veto observation exceeded arrival deadline')
        # Retire only after callbacks, so a cancellation raised by one of them
        # remains visible. The independent copied tail already prevents a
        # reentrant old observer from consuming any destination bytes; its
        # cursor changes are rejected by unchanged().
        arrival.phase, arrival.reason = 'stopped', _RETIRED
        return continued
    except BaseException as error:
        arrival.phase = 'stopped'
        arrival.reason = 'Destination hazard observer transfer refused: '+str(error)
        raise
