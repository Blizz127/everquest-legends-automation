"""A reached probe floor, retained without inventing a travel observation.

Only an in-memory transaction can produce this reference. It keeps the exact
reader lease and cancellation ancestry alive; neither files nor expired
calibration can recreate it. The next planning height needs a new stopped pair.
"""
from hashlib import sha256
import json

from .camp_floor_checkpoint import CampFloorCheckpoint
from .destination_floor_bootstrap import DestinationFloorCheckpoint
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot


class CampProbeFloorReference:
    """Historical endpoint floor owned by one continued probe transaction."""
    def __init__(self,transaction,result):
        # Local import avoids the preparation -> height -> reference cycle.
        from .camp_probe_transaction import CampProbeTransaction
        if (type(transaction) is not CampProbeTransaction or transaction.phase!='retaining'
                or transaction.result is not result or transaction._continuation is not None):
            raise ValueError('Only the owning confirmed transaction can retain its endpoint')
        transaction._check()
        p=transaction.preparation;parent=p.checkpoint
        self._transaction=transaction;self._result=result;self._parent=parent
        self._chain=transaction._endpoint.fork();self._chain_state=_chain_snapshot(self._chain)
        self._reader=p.reader
        self._terrain,self._static,self._bsp=parent._terrain,parent._static,parent._bsp
        self._policy,self._model=parent._policy,parent._model
        self._context=(transaction,result,parent,self._chain,self._reader,self._terrain,
                       self._static,self._bsp,self._policy,self._model)
        self._result_state=transaction._result_values(result)
        self.valid=True;self.reason=''
        self._payload=encoded(dict(format='eql-camp-probe-floor-v1',
            parent_floor_sha256=parent.sha256,probe_result_sha256=result.sha256,
            floor_proof_sha256=self._chain.previous.proof_sha256,
            source_wld_sha256=self._chain.inventory_sha256,
            selected_ids=self._chain.previous.selected_ids,chain_index=self._chain.index,
            arrival_position=result.package_xyz,arrival_log_seq=result.second.log_line_seq,
            arrival_received_at=result.second.received_monotonic,
            arrival_observed_at=result.observed_at,arrival_expires_at=result.expires_at,
            raw_z_minus_source_z=result.raw_z_minus_source_z,
            requires_new_stopped_pair=True,old_calibration_renewed=False,
            historical_floor_only=True,current_position_verified=False,
            current_heading_verified=False,current_motion_verified=False,
            input_authorized=False,sender_origin_verified=False,real_client_accepted=False))
        self.sha256=sha256(self._payload).hexdigest();self._payload_identity=self._payload

    def invalidate(self,reason):
        if self.valid:self.reason=str(reason)
        self.valid=False
        self._chain=self._chain_state=None

    def _assert_intact(self):
        t=self._transaction
        if (not self.valid or t.phase!='continued' or t._continuation is not self
                or any(a is not b for a,b in zip(self._context,
                    (t,self._result,self._parent,self._chain,self._reader,self._terrain,
                     self._static,self._bsp,self._policy,self._model)))
                or t.result is not self._result or t.preparation.checkpoint is not self._parent
                or t._result_values(self._result)!=self._result_state
                or _chain_snapshot(self._chain)!=self._chain_state
                or self._reader is not t.preparation.reader
                or any(a is not b for a,b in zip(
                    (self._terrain,self._static,self._bsp,self._policy,self._model),
                    (self._parent._terrain,self._parent._static,self._parent._bsp,
                     self._parent._policy,self._parent._model)))
                or self._payload is not self._payload_identity
                or sha256(self._payload).hexdigest()!=self.sha256):
            raise ValueError('Retained probe floor changed or was discarded')

    def check(self):
        """Check provenance and the original lease; do not renew observation age."""
        with self._transaction.lock:
            try:
                nodes=[];node=self;seen=set()
                while type(node) is CampProbeFloorReference:
                    if id(node) in seen:raise ValueError('Cyclic camp floor ancestry')
                    seen.add(id(node));node._assert_intact();nodes.append(node);node=node._parent
                if type(node) not in (CampFloorCheckpoint, DestinationFloorCheckpoint):
                    raise ValueError('Missing original camp floor ancestor')
                p=self._transaction.preparation
                scope=(p.binding_reader,p.owner_binding,p.lease,p.reader,p.clock,p.wall,self._transaction.lock)
                if any(any(a is not b for a,b in zip(scope,
                        (v._transaction.preparation.binding_reader,v._transaction.preparation.owner_binding,
                         v._transaction.preparation.lease,v._transaction.preparation.reader,
                         v._transaction.preparation.clock,v._transaction.preparation.wall,v._transaction.lock)))
                       for v in nodes):
                    # Distinct scopes cannot share a provider observation.
                    self._transaction._check();self._assert_intact();return
                binding=p.binding_reader();p.lease.check();node.check();now=p.clock()
                node._assert_intact()
                for v in reversed(nodes):
                    preparation=v._transaction.preparation
                    try:preparation._check_local(binding,now)
                    except Exception as error:
                        preparation.cancel(str(error));raise
                    v._transaction._assert_context();v._assert_intact()
            except Exception as error:
                self.invalidate(str(error));raise ValueError(self.reason) from error

    def fork(self):
        with self._transaction.lock:
            self.check();branch=self._chain.fork();self.check()
            return branch

    def snapshot(self,*,include_evidence=False):
        record=dict(valid=self.valid,reason=self.reason,evidence_sha256=self.sha256,
            historical_floor_only=True,requires_new_stopped_pair=True,
            current_position_verified=False,current_heading_verified=False,
            current_motion_verified=False,input_authorized=False,
            sender_origin_verified=False,real_client_accepted=False)
        if include_evidence:record['evidence']=json.loads(self._payload)
        return record


def camp_floor_anchor(checkpoint):
    """Return the actual anchor object, raw reply and source position, without a pose."""
    if type(checkpoint) is CampFloorCheckpoint:
        anchor=checkpoint._reference
        return anchor,anchor.raw_fix,anchor.package_xyz
    if type(checkpoint) is CampProbeFloorReference:
        anchor=checkpoint._result
        return anchor,anchor.second,anchor.package_xyz
    if type(checkpoint) is DestinationFloorCheckpoint:
        anchor=checkpoint._anchor
        return anchor,anchor.second,anchor.package_xyz
    raise ValueError('Exact camp arrival or retained probe floor required')


CAMP_FLOOR_TYPES=(CampFloorCheckpoint,CampProbeFloorReference,DestinationFloorCheckpoint)


def assert_camp_ancestry(checkpoint):
    """Final non-provider check for cancellation after the full ancestry scan."""
    seen=set();node=checkpoint
    while type(node) is CampProbeFloorReference:
        if id(node) in seen:raise ValueError('Cyclic retained camp floor ancestry')
        seen.add(id(node));node._assert_intact()
        tx=node._transaction
        if tx.preparation.phase!='consumed' or tx.preparation._start is not tx.ticket.start:
            raise ValueError('Retained camp ancestor preparation ended')
        node=node._parent
    if type(node) not in (CampFloorCheckpoint, DestinationFloorCheckpoint):
        raise ValueError('Missing original camp floor ancestor')
    node._assert_intact()
