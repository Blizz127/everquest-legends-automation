"""Typed source completion checks shared by first and onward camp handoffs."""
from .ground_binding import finite
from .source_walk_driver import SourceWalkFinished
from .source_contact_controller import SourceContactArrival,SourceContactController
from .camp_contact_checkpoint import CampContactCheckpoint
from .camp_floor_checkpoint import CampFloorCheckpoint


def arrival_reference(receipt):
    if type(receipt) is SourceContactArrival:return receipt.second
    if type(receipt) is SourceWalkFinished:return receipt.reference
    raise ValueError('Exact source arrival receipt required')


def arrival_itinerary(receipt):
    if type(receipt) is SourceContactArrival:return receipt.record()['itinerary_sha256']
    if type(receipt) is SourceWalkFinished:return receipt.itinerary_sha256
    raise ValueError('Exact source arrival receipt required')


def validate_contact_completion(runtime):
    """Active-only check before releasing the reader/navigation scope."""
    r=runtime;c=r.transfer;receipt=r.completed_arrival
    r.check_current();r.check_contact_boundary()
    if (r.phase!='complete' or type(receipt) is not SourceContactArrival
            or type(c) is not SourceContactController or c.ordinary is not r.ledger
            or c.arrival is not receipt or c.reference is not receipt.second
            or r.collector is not None or r.seal is not None or r.pending_preflight is not None
            or r.contact_boundary is None or r._contact_driver_state is None
            or r.contact_boundary.cell_index!=len(r.driver.targets)-1
            or r.driver._boundary is not r.contact_boundary
            or arrival_itinerary(receipt)!=r.driver.plan.sha256
            or c.hint.end!=tuple(r.driver.plan.record()['goal'])):
        raise ValueError('Exact terminal contact completion required')
    c.validate_arrival(receipt)
    r.check_contact_boundary()
    if (r.phase!='complete' or r.completed_arrival is not receipt or r.transfer is not c
            or r.collector is not None or r.seal is not None or c.arrival is not receipt):
        raise ValueError('Contact completion changed during final observation')
    return receipt.second


def assert_retained_arrival(runtime,receipt,checkpoint,now):
    """Pure identity/freshness check after callbacks and navigation release.

    Full historical checkpoint checks precede physical sampling at the caller.
    This must not rearm the released reader or retired movement observer.
    """
    r=runtime;reference=arrival_reference(receipt)
    checkpoint._assert_intact()
    if (r.phase!='complete' or r.completed_arrival is not receipt
            or not finite(now) or not 0<=now-reference.raw_fix.received_monotonic<=.5
            or checkpoint._reference is not reference):
        raise ValueError('Source arrival changed or expired after capture')
    if type(receipt) is SourceContactArrival:
        if (type(checkpoint) is not CampContactCheckpoint or checkpoint._arrival is not receipt
                or type(r.transfer) is not SourceContactController or r.transfer.arrival is not receipt
                or r.transfer.reference is not reference or r.transfer.phase!='arrived'
                or not receipt.issued_at<=now<=receipt.expires_at):
            raise ValueError('Contact arrival lost its original stopped-pair deadline or identity')
        r.check_contact_boundary()
    elif type(checkpoint) is not CampFloorCheckpoint or r.ledger.reference is not reference:
        raise ValueError('Ordinary source arrival lost its reached floor')
