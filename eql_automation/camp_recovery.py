"""Resource recovery between encounters; posture remains a request, not a fact."""
from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path

EXE_PIN='fe41a8db0b2cc2dc8848d82dce41d3f94cb6aa86d2aac21aa774efab7146bf36'


class PostureCommandBinding:
    """Bind command semantics to the installed copy inspected statically."""
    def __init__(self,game_dir):
        self.path=Path(game_dir)/'eqgame.exe'
        before=self.identity()
        if sha256(self.path.read_bytes()).hexdigest()!=EXE_PIN or self.identity()!=before:
            raise ValueError('Rest commands require the inspected client build')
        self.bound=before

    def identity(self):
        s=self.path.stat()
        return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

    def check(self):
        if self.identity()!=self.bound:
            raise ValueError('Client executable changed during camp')


@dataclass
class CampRecovery:
    started: float
    phase: str='stand_before_sit'
    wait_until: float=0.
    last_sample: float=float('-inf')
    good_samples: int=0
    sit_attempts: int=0
    posture_requested: str | None=None
    posture_observed: str | None=None
    best_hp: float=0.
    best_mana: float=0.
    progress_at: float | None=None
    last_stand_completed_at: float | None=None

    def command(self,now):
        if now<self.wait_until:return None
        return {'stand_before_sit':'/stand','sit_once':'/sit on','stand_after_rest':'/stand'}.get(self.phase)

    def submitted(self,command,now):
        if command!=self.command(now):raise ValueError('Unexpected recovery command completion')
        self.good_samples=0
        if self.phase=='stand_before_sit':
            self.phase='sit_once';self.posture_requested='standing';self.wait_until=now+.5
        elif self.phase=='sit_once':
            self.sit_attempts+=1
            if self.sit_attempts!=1:raise ValueError('A sit toggle cannot be retried blindly')
            self.phase='recovering';self.posture_requested='sit_toggle';self.wait_until=now+.5
        else:
            self.phase='stand_settle';self.posture_requested='standing';self.wait_until=now+.5
            self.last_stand_completed_at=now

    def sample(self,now,sampled_at,hp,mana):
        if self.phase not in {'recovering','stand_settle'}:return
        if (type(sampled_at) not in (int,float) or not math.isfinite(sampled_at) or not 0<=now-sampled_at<=1.5 or
                any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in (hp,mana))):
            raise ValueError('Recovery requires fresh readable HP and mana')
        if sampled_at<=self.last_sample:return
        self.last_sample=sampled_at
        if sampled_at<self.wait_until:return
        if self.progress_at is None or hp>self.best_hp+.005 or mana>self.best_mana+.005:
            self.best_hp=max(self.best_hp,hp);self.best_mana=max(self.best_mana,mana);self.progress_at=now
        if hp>=.95 and mana>=.90:self.good_samples+=1
        else:self.good_samples=0
        if self.phase=='recovering' and self.good_samples>=2 and now>=self.wait_until:
            self.phase='stand_after_rest';self.good_samples=0
        elif self.phase=='stand_settle' and self.good_samples>=2 and now>=self.wait_until:
            self.phase='recovered'
        if now-self.started>300 or self.progress_at is not None and now-self.progress_at>90:
            raise ValueError('Resource recovery timed out without sufficient progress')
