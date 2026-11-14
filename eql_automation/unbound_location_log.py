"""Fresh raw /location diagnostics when no new zone-entry event is available.

These records deliberately are NOT RawLocationFix navigation inputs. They
carry no zone, alignment, request correlation or movement authorization.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import time

from .location_log import NonReplayingLogTail,parse_client_log_line,parse_raw_location,is_logging_boundary


@dataclass(frozen=True)
class UnboundLocationObservation:
    raw_coordinates: tuple[float,float,float]
    log_local_time: datetime
    received_monotonic: float
    log_epoch: int
    log_line_seq: int
    zone_binding_verified: bool = False
    coordinates_aligned_to_wld: bool = False
    request_correlation_verified: bool = False
    input_authorized: bool = False


class UnboundLocationReader:
    """Read one stationary diagnostic session; resets/transitions latch refusal."""

    def __init__(self,path: Path,*,expected_character,expected_server,max_bytes=512*1024):
        if path.name!=f'eqlog_{expected_character}_{expected_server}.txt':
            raise ValueError('Diagnostic log does not match expected character/server')
        self.tail=NonReplayingLogTail(path,max_bytes=max_bytes)
        self.tail.poll()  # Existing bytes never bootstrap a position or zone.
        if self.tail.identity is None:raise ValueError('Expected character log is missing')
        self.latest=None;self.last_received=None;self.last_log_time=None
        self.line_seq=0;self.refused=False

    def _refuse(self,reason):
        self.latest=None;self.refused=True
        raise ValueError(reason)

    def poll(self,*,now=None):
        if self.refused:raise ValueError('Diagnostic session refused; restart observation')
        now=time.monotonic() if now is None else now
        if not isinstance(now,(int,float)) or isinstance(now,bool) or not isfinite(now):
            self._refuse('Diagnostic poll time must be finite')
        if self.last_received is not None and now<self.last_received:
            self._refuse('Diagnostic poll clock moved backward')
        self.last_received=now
        try:lines,reset=self.tail.poll()
        except (OSError,ValueError):
            self.latest=None;self.refused=True
            raise
        if reset:self._refuse('Character log changed during observation')
        found=[]
        for line in lines:
            parsed=parse_client_log_line(line)
            if parsed is None:
                if any(marker in line for marker in ('LOADING, PLEASE WAIT', 'You have entered ', "Logging to '")):
                    self._refuse('Unparsed transition or logging change during observation')
                continue
            log_time,body=parsed
            if self.last_log_time is not None and log_time<self.last_log_time:
                self._refuse('Client log clock moved backward')
            self.last_log_time=log_time
            if body.startswith(('LOADING, PLEASE WAIT', 'You have entered ')) or is_logging_boundary(body):
                self._refuse('Zone transition or logging change during stationary observation')
            raw=parse_raw_location(body)
            if raw is None:
                if body.startswith('Your Location is '):self._refuse('Malformed raw location')
                continue
            self.line_seq+=1
            self.latest=UnboundLocationObservation(raw,log_time,now,self.tail.epoch,self.line_seq)
            found.append(self.latest)
        return found
