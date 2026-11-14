"""One explicitly declared final crossing pulse, separate from route travel."""
from dataclasses import dataclass

from .fixed_route_follower import RouteHalt
from .scene_log_veto import ExpectedArrivalLogVeto
from .supervised_route import SupervisedRouteDeclaration,SupervisedRoutePolicy
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class SupervisedCrossingDeclaration(SupervisedRouteDeclaration):
    expected_zone_line_sha256: str = ''
    destination: str = ''


class SupervisedCrossingPolicy(SupervisedRoutePolicy):
    """Source-side checks only; no movement is authorized after loading.

    The arrival controller owns transition ordering and subsequent stopped
    positions. This policy cannot be passed to the ordinary route sender.
    """
    def __init__(self,geometry,**kwargs):
        veto=kwargs.get('log_veto');d=kwargs.get('declaration')
        if (type(d) is not SupervisedCrossingDeclaration or type(veto) is not ExpectedArrivalLogVeto
                or veto.destination!=d.destination):
            raise ValueError('Crossing needs its own exact destination and continued hazard observer')
        super().__init__(geometry,**kwargs)

    def _validate_geometry(self,geometry,d):
        line=geometry.expected_zone_line
        if (type(d) is not SupervisedCrossingDeclaration or d.scope!='zone_crossing'
                or not isinstance(line,ExpectedZoneLine) or line.sha256!=d.expected_zone_line_sha256
                or line.crossing_id!=d.record_id or not d.destination or d.maximum_steps!=1):
            raise ValueError('One declared crossing and exact zone-line geometry required')

    def authorize(self,ticket,observed):
        self.validate_scene(observed,self.ledger)
        record=self.geometry.record_for(ticket)
        line=self.geometry.expected_zone_line
        if (ticket.preparation.movement_key!=103 or record.expected_zone_line!=line
                or record.bsp.traversal is None
                or not any(line.allows_region(region,labels)
                           for region,labels in record.bsp.traversal.labelled_regions)):
            raise RouteHalt('Final crossing must move forward through the exact expected region')
        return super().authorize(ticket,observed)

    def snapshot(self):
        record=super().snapshot()
        return dict(record,kind='owner_supervised_final_crossing_pulse',
                    expected_zone_line=self.geometry.expected_zone_line.record(),
                    destination=self.declaration.destination)
