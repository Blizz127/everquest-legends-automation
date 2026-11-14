"""One bounded owner-supervised corridor through one exact expected zone line.

The same declaration and counters cover all dry approach, pivot and crossing
pulses. Reserved steps include the last loading pulse, even though its source
floor will never commit. No independent scene/body verification is claimed.
"""
from dataclasses import dataclass

from .fixed_route_follower import RouteHalt
from .provisional_floor_commit import ProvisionalRouteFloorCommit
from .supervised_crossing import SupervisedCrossingDeclaration
from .supervised_route import SupervisedRoutePolicy
from .zone_arrival import ZoneArrivalHandoff
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class SupervisedCorridorDeclaration(SupervisedCrossingDeclaration):
    scope: str = 'zone_crossing_corridor'


class SupervisedCrossingCorridorPolicy(SupervisedRoutePolicy):
    def __init__(self,geometry,*,arrival,**kwargs):
        self.arrival=arrival
        self._line=geometry.expected_zone_line
        self._tickets=[];self._admitting=False
        super().__init__(geometry,**kwargs)

    def _validate_geometry(self,geometry,d):
        a=self.arrival;line=geometry.expected_zone_line
        if (type(d) is not SupervisedCorridorDeclaration or d.scope!='zone_crossing_corridor'
                or type(a) is not ZoneArrivalHandoff or type(line) is not ExpectedZoneLine
                or type(geometry.ledger) is not ProvisionalRouteFloorCommit or line is not self._line
                or line.sha256!=d.expected_zone_line_sha256 or line.crossing_id!=d.record_id
                or d.destination!=a.destination or a.maximum_source_seconds!=d.maximum_seconds):
            raise ValueError('One exact provisional corridor, arrival reader and aggregate scope required')
        if hasattr(self,'log_veto') and self.log_veto is not a.veto:
            raise ValueError('Corridor must keep the same arrival hazard observer')

    def _check(self):
        a=self.arrival
        if a.loading is not None or a.phase!='await_loading':
            raise RouteHalt('Source corridor movement ends on loading or arrival cancellation')
        began=super()._check()
        if (a.loading is not None or a.phase!='await_loading'
                or len(self._tickets)>self.declaration.maximum_steps):
            raise RouteHalt('Source corridor scope or aggregate step budget changed')
        return began

    def authorize(self,ticket,observed):
        with self.ledger.lock:
            if (self._admitting or any(ticket is old for old in self._tickets)
                    or len(self._tickets)>=self.declaration.maximum_steps):
                self.cancel('Corridor step already reserved or aggregate budget exhausted')
                raise RouteHalt('No new movement slot in the same corridor')
            self._admitting=True
            try:
                self._check()
                record=self.geometry.record_for(ticket)
                if (record.expected_zone_line is not self._line
                        or ticket.preparation.movement_key not in (103,105,106)):
                    raise RouteHalt('Corridor pulse differs from its exact line or movement keys')
                self._tickets.append(ticket)
                authorization=super().authorize(ticket,observed)
                self._check()
                return authorization
            except BaseException:
                self.cancel('Corridor movement admission failed');raise
            finally:self._admitting=False

    def snapshot(self):
        return dict(super().snapshot(),kind='owner_supervised_crossing_corridor',
            reserved_movements=len(self._tickets),expected_zone_line=self._line.record(),
            destination=self.declaration.destination)
