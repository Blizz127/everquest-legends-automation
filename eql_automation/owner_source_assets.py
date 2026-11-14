"""Private source-guide destination for one owner-started same-zone trial."""
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from .current_route_start import CurrentStartPlanner, encoded
from .source_itinerary import SourceItineraryGuide


@dataclass(frozen=True)
class SourceDestinationAssets:
    planner: CurrentStartPlanner
    guide: SourceItineraryGuide
    target_name: str
    source_evidence: bytes
    destination_id: str = 'slave-mines'
    _guide_state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.guide) is not SourceItineraryGuide:
            raise ValueError('Exact copied source guide required')
        self.guide.validate()
        object.__setattr__(self, '_guide_state', tuple(vars(self.guide).items()))
        self.check()

    def check(self):
        from .source_destinations import destination_spec
        spec=destination_spec(self.destination_id)
        if (type(self.planner) is not CurrentStartPlanner or self.planner.zone != spec.zone
                or self.planner.zone_id != spec.zone_id or self.planner.region_policy is None
                or self.guide.zone != spec.zone
                or (self.guide.wld_sha256, self.guide.static_inventory_sha256) != self.planner.pins[2:]
                or tuple(vars(self.guide).items()) != self._guide_state
                or not isinstance(self.target_name, str) or not self.target_name
                or type(self.source_evidence) is not bytes or not 0 < len(self.source_evidence) <= 65536):
            raise ValueError('Current zone-bound planner and unchanged private guide required')
        self.planner._check_views()


def load_owner_source_destination(engine):
    from .owner_route_assets import load_owner_crushbone_planner, load_owner_butcher_planner
    from .source_destinations import destination_spec, load_source_guide, source_data_name
    journey=getattr(engine,'journey',None)
    identifier='slave-mines' if journey is None else journey.destination_id
    spec=destination_spec(identifier)
    planner = (load_owner_butcher_planner(engine) if spec.zone=='butcher' else load_owner_crushbone_planner(engine))
    guide = load_source_guide(Path.home()/'.local/share/eql-automation/owner-route-data'/source_data_name(identifier),identifier)
    evidence = encoded(dict(kind='copied_client_source_guide', zone=spec.zone,
        destination_id=identifier,guide_file_sha256=spec.file_sha256, guide_sha256=sha256(encoded(guide.record())).hexdigest(),
        package_goal_xy=guide.goal, target=spec.label, current_position=False,
        arrival_mode=spec.arrival_mode,
        safe_camp_verified=False, real_client_accepted=False))
    return SourceDestinationAssets(planner,guide,planner.zone_name+' '+spec.label,evidence,identifier)
