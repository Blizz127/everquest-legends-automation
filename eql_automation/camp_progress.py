"""Receipt-window camp metrics. These observations never authorize input.

Logged percentage awards are gross messages, not raw XP, a current XP bar,
net level progress or verified normal/AA allocation. Never combine their sums
across an observed level boundary. A stopped report is historical evidence.
"""
from dataclasses import dataclass, field
from math import isfinite

from .location_log import is_logging_boundary
from .prior_rotation_core import level_from_message
from .telemetry import DEATH, LOG_GAIN, LEVEL_LOSS, GAIN_SCALE


@dataclass
class CampProgress:
    started: float
    configured_level: int
    last_sequence: int = 0
    as_of: float = field(init=False)
    window_started: float = field(init=False)
    reported_level: int | None = None
    award_events: int = 0
    window_award_events: int = 0
    window_micropoints: int = 0
    matching_kills: int = 0
    last_kill_sequence: int = 0
    observed_deaths: int = 0
    last_client_stamp: object = None
    arrival_destination: dict | None = None
    continuous: bool = True
    unavailable_reason: str | None = None
    finished: bool = False
    finish_reason: str | None = None
    revision: int = 0
    closed_award_windows: list = field(default_factory=list)

    def __post_init__(self):
        self.as_of = self.window_started = self.started

    def advance(self, now):
        if self.finished:
            return False
        if type(now) not in (float, int) or not isfinite(now) or now < self.as_of:
            self.invalidate('Observation clock did not advance monotonically')
            return False
        self.as_of = now
        return self.continuous

    def invalidate(self, reason):
        if self.continuous:
            self.continuous = False
            self.unavailable_reason = str(reason)
            self.revision += 1

    def observe(self, stamp, body, seq, now):
        if not self.advance(now):
            return
        if (type(seq) is not int or seq != self.last_sequence + 1 or
                self.last_client_stamp is not None and stamp < self.last_client_stamp):
            self.invalidate('Client log sequence or timestamp continuity changed')
            return
        self.last_sequence = seq
        self.last_client_stamp = stamp
        level = level_from_message(body)
        loss = LEVEL_LOSS.fullmatch(body)
        if level is not None or loss:
            previous = self.snapshot()
            self.closed_award_windows.append(dict(
                ended_by_sequence=seq, reported_level=self.reported_level,
                seconds=previous['award_window_seconds'], events=self.window_award_events,
                logged_award_percent=previous['logged_award_percent'],
                logged_award_percent_per_hour=previous['logged_award_percent_per_hour']))
            self.reported_level = int(loss[1]) if loss else level
            if not 1 <= self.reported_level <= 50:
                self.reported_level = None
            self.window_started = now
            self.window_micropoints = self.window_award_events = 0
            self.revision += 1
        if DEATH.match(body):
            self.observed_deaths += 1
            self.revision += 1
        if (is_logging_boundary(body) or body.startswith(('You have entered ',
                'LOADING, PLEASE WAIT', 'Returning to '))):
            self.invalidate('Client log or zone boundary ended the observation window')
            return
        award = LOG_GAIN.fullmatch(body)
        if award:
            whole, _, fraction = award[1].partition('.')
            self.window_micropoints += int(whole)*GAIN_SCALE + int(fraction.ljust(6,'0'))
            self.window_award_events += 1
            self.award_events += 1
            self.revision += 1

    def matching_kill(self, seq):
        # Called only after the existing camp's engagement checks accept a kill.
        if self.continuous and not self.finished and seq == self.last_sequence and seq > self.last_kill_sequence:
            self.last_kill_sequence = seq
            self.matching_kills += 1
            self.revision += 1

    def bind_arrival(self, *, destination_id, name, zone, itinerary_sha256, stopped_log_seq):
        if self.finished or self.arrival_destination is not None:
            raise ValueError('Camp arrival attribution is already closed or assigned')
        self.arrival_destination = dict(destination_id=destination_id, name=name, zone=zone,
            itinerary_sha256=itinerary_sha256, stopped_log_seq=stopped_log_seq,
            source='camp_started_after_checked_stopped_arrival',
            current_position_verified=False, safe_camp_verified=False, real_client_accepted=False)
        self.revision += 1

    def finish(self, now, reason):
        if not self.finished:
            self.advance(now)
            self.finished = True
            self.finish_reason = str(reason)
            self.revision += 1

    def snapshot(self):
        seconds = max(0., self.as_of-self.started)
        window = max(0., self.as_of-self.window_started)
        usable = self.continuous and seconds > 0
        return dict(state='stopped' if self.finished else 'observing',
            configured_level=self.configured_level, client_reported_level=self.reported_level,
            current_xp=None, xp_units_per_hour=None, net_xp_progress=None,
            observation_seconds=seconds, last_log_sequence=self.last_sequence,
            last_client_timestamp=None if self.last_client_stamp is None else self.last_client_stamp.isoformat(),
            client_timestamp_timezone='unverified_local',
            continuous=self.continuous, unavailable_reason=self.unavailable_reason,
            finish_reason=self.finish_reason, arrival_destination=self.arrival_destination,
            matching_kills=self.matching_kills, observed_deaths=self.observed_deaths,
            xp_award_events=self.award_events,
            xp_award_events_per_hour=self.award_events*3600/seconds if usable else None,
            matching_kills_per_hour=self.matching_kills*3600/seconds if usable else None,
            award_window_seconds=window, award_window_level=self.reported_level,
            award_window_events=self.window_award_events,
            logged_award_percent=self.window_micropoints/GAIN_SCALE,
            logged_award_percent_per_hour=(self.window_micropoints/GAIN_SCALE*3600/window
                                          if self.continuous and window > 0 else None),
            rate_meaning='gross logged awards per receipt-window hour; not total or net XP',
            closed_award_windows=list(self.closed_award_windows),
            real_client_accepted=False)

    def summary(self):
        s=self.snapshot()
        rate=s['logged_award_percent_per_hour']
        text=f"Kills: {self.matching_kills} · XP awards: {self.award_events}"
        # A first-second extrapolation is noisy; keep the raw count visible.
        if rate is not None and s['award_window_seconds'] >= 60:
            text+=f" · logged awards {rate:.2f}%/h"
        text+=f" · deaths observed: {self.observed_deaths}"
        if not self.continuous:text+=' · rate unavailable'
        return text
