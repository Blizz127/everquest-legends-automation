"""Explicit copied-source staircase proposal; never a movement permit."""
from dataclasses import dataclass
from .ground_binding import finite


@dataclass(frozen=True)
class SourceStairHint:
    start: tuple
    end: tuple
    tread_ids: tuple
    radius: float
    max_rise: float = 2.
    max_lift: float = 4.
    vertical_model: str = 'lift_transfer'

    def validate(self):
        if (any(type(p) is not tuple or len(p)!=2 or not all(finite(v) for v in p)
                for p in (self.start,self.end)) or self.start==self.end
                or not all(finite(v) for v in (self.radius,self.max_rise,self.max_lift))
                or not .05<=self.radius<=10 or not 0<self.max_rise<=4
                or not 0<self.max_lift<=4 or type(self.tread_ids) is not tuple
                or not 2<=len(self.tread_ids)<=32
                or self.vertical_model not in ('lift_transfer','bounded_source_contacts')):
            raise ValueError('Explicit finite stair departure, destination and treads required')
        keys=[]
        for group in self.tread_ids:
            if type(group) is not tuple or not 1<=len(group)<=64:
                raise ValueError('Bounded exact stair tread source groups required')
            for key in group:
                if (type(key) is not tuple or len(key)!=2
                        or not all(type(v) is int and v>=0 for v in key)):
                    raise ValueError('Exact stair source IDs required')
                keys.append(key)
        if len(keys)!=len(set(keys)):
            raise ValueError('Stair treads must have distinct source IDs')


