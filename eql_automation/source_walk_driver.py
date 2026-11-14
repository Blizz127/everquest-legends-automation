"""Follow source walk legs; an explicit step boundary cannot be auto-consumed."""
from dataclasses import dataclass,field
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .ground_sweep import motion_footprint
from .source_motion import SourceReceiptLedger
from .source_step_sender import run_checked_source_step


@dataclass(frozen=True)
class SourceWalkCommand:
    kind: str
    requested_seconds: float
    cell_index: int
    target: tuple
    reference: object


@dataclass(frozen=True)
class SourceStepBoundary:
    cell_index: int
    start: tuple
    planned_start: tuple
    end: tuple
    transition_sha256: str
    reference: object
    floor_proof_sha256: str
    approach_cell_indices: tuple
    input_authorized: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SourceWalkFinished:
    itinerary_sha256: str
    reference: object
    real_client_accepted: bool = field(default=False,init=False)


@dataclass(frozen=True)
class _Target:
    kind: str
    start: tuple
    end: tuple
    transition: str | None


class SourceWalkDriver:
    """Automatic aiming through ordinary cells using measured retained motion.

    The owner runtime must obtain and acknowledge each fresh stopped pair
    before calling again. This object never reads the log or types a command.
    Walking cannot consume a conditional step or its planned landing.
    """
    def __init__(self,ledger):
        if type(ledger) is not SourceReceiptLedger:
            raise ValueError('Exact source movement ledger required')
        self.ledger=ledger;self.plan=ledger.observer.itinerary
        cells=self.plan.record()['cells'];self.index=0
        self._payload=self.plan.payload
        targets=[]
        for row in cells:
            if (row['kind'] not in ('walk','step')
                    or not all(finite(v) for v in (*row['start'],*row['end'],
                        row['start_floor_height'],row['end_floor_height']))):
                raise ValueError('Source itinerary needs explicit floor heights at every target')
            targets.append(_Target(row['kind'],(*row['start'],row['start_floor_height']),
                (*row['end'],row['end_floor_height']),
                row['transfer']['transition_sha256'] if row['kind']=='step' else None))
        self.targets=self._targets=tuple(targets)

    def _step_boundary(self,position):
        """Hand off before an ordinary maximum-hold envelope reaches a riser.

        This is a request to replan, never a shortened movement bound or a
        skipped walk suffix. The current index/floor stay unchanged, and the
        step planner must check the actual departure and any remaining approach.
        """
        b=self.ledger.bounds
        footprint=motion_footprint((0.,0.),0.,b.forward_speed_upper_bound*b.maximum_actual_hold,
            position_error=b.position_error,heading_error_degrees=b.heading_error_degrees,
            post_release_drift=b.post_release_drift,extra_radius=b.body_radius)
        reserve=max(math.hypot(*point) for point in footprint)+.25
        distance=0.;previous=position[:2];approach=[]
        for index in range(self.index,len(self.targets)):
            row=self.targets[index]
            if row.kind=='step':
                distance+=math.dist(previous,row.start[:2])
                if distance<=reserve:
                    return SourceStepBoundary(index,position,row.start,row.end,row.transition,
                        self.ledger.reference,self.ledger.chain.previous.proof_sha256,tuple(approach))
                return None
            distance+=math.dist(previous,row.end[:2])
            if distance>reserve:return None
            approach.append(index);previous=row.end[:2]
        return None

    def next_action(self):
        l=self.ledger
        with l.lock:
            try:
                l._check()
                if (l.phase!='ready' or l.observer.itinerary is not self.plan
                        or self.plan.payload is not self._payload
                        or self.targets is not self._targets):
                    raise RouteHalt('Source walk needs an unchanged itinerary and stopped acknowledgment')
                l.observer.validate(l.reference,l.chain,maximum_age=.5)
                p=l.reference.package_xyz
                boundary=self._step_boundary(p)
                if boundary is not None:return boundary
                while self.index<len(self.targets):
                    row=self.targets[self.index]
                    if row.kind=='step':
                        start=row.start
                        if math.dist(p[:2],start[:2])>.25 or abs(p[2]-start[2])>.25:
                            raise RouteHalt('Source step departure is not the observed stopped endpoint')
                        return SourceStepBoundary(self.index,p,start,row.end,row.transition,
                            l.reference,l.chain.previous.proof_sha256,())
                    target=row.end
                    remaining=math.dist(p[:2],target[:2])
                    if remaining<=.25:
                        if abs(p[2]-target[2])>.25:
                            raise RouteHalt('Observed source target is on a different floor')
                        self.index+=1;continue
                    a,b=row.start[:2],row.end[:2];length=math.dist(a,b)
                    if length:
                        along=sum((p[k]-a[k])*(b[k]-a[k]) for k in (0,1))/length**2
                        closest=tuple(a[k]+min(1.,max(0.,along))*(b[k]-a[k]) for k in (0,1))
                        if (math.dist(p[:2],closest)>l.observer.initial.route.half_width
                                or along>1.+.25/length):
                            raise RouteHalt('Observed source movement left its planned walk leg')
                    heading=l.legacy.bearing(*p[:2],*target[:2])
                    error=l.legacy.wrap180(heading-l.pose.heading)
                    low,high=l.bounds.minimum_requested_hold,l.bounds.maximum_requested_hold
                    if abs(error)>1.:
                        if high<=l.motion.turn_latency:
                            raise RouteHalt('Source turn cannot overcome measured latency')
                        kind='right' if error*l.motion.right_sign>0 else 'left'
                        seconds=min(high,max(low,l.motion.turn_latency+abs(error)/l.motion.turn_rate))
                    else:
                        kind='forward';speed=l.pose.speed
                        if not finite(speed) or speed<=0:raise RouteHalt('No measured source walk speed')
                        count=max(1,math.ceil(remaining/(speed*high)))
                        seconds=remaining/speed/count
                        if seconds<low:
                            if count!=1 or low*speed-remaining>.25:
                                raise RouteHalt('Minimum source pulse overshoots its target')
                            seconds=low
                    return SourceWalkCommand(kind,seconds,self.index,target,l.reference)
                return SourceWalkFinished(self.plan.sha256,l.reference)
            except BaseException as error:l.cancel(str(error));raise

    def drive_one(self,sender,*,policy,command_state_clear,pump):
        action=self.next_action()
        if type(action) is not SourceWalkCommand:return action
        return run_checked_source_step(sender,self.ledger,policy=policy,kind=action.kind,
            requested_seconds=action.requested_seconds,command_state_clear=command_state_clear,pump=pump)
