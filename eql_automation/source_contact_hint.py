"""Explicit thin-sheet corridor proposal, without a movement permit."""
from dataclasses import dataclass

from .ground_binding import finite


@dataclass(frozen=True)
class SourceContactHint:
    waypoints: tuple
    face_ids: tuple
    radius: float
    max_rise: float = .125

    @property
    def start(self):return self.waypoints[0]

    @property
    def end(self):return self.waypoints[-1]

    def validate(self):
        if (type(self.waypoints) is not tuple or not 2<=len(self.waypoints)<=129
                or any(type(p) is not tuple or len(p)!=2 or not all(finite(v) for v in p)
                       for p in self.waypoints)
                or any(a==b for a,b in zip(self.waypoints,self.waypoints[1:]))
                or not finite(self.radius) or not .05<=self.radius<=10.
                or not finite(self.max_rise) or not 0<self.max_rise<=.125
                or type(self.face_ids) is not tuple or not 1<=len(self.face_ids)<=16
                or any(type(key) is not tuple or len(key)!=2
                       or any(type(v) is not int or v<0 for v in key) for key in self.face_ids)
                or len(set(self.face_ids))!=len(self.face_ids)):
            raise ValueError('Continuous finite contact waypoints and exact bounded sheet IDs required')
