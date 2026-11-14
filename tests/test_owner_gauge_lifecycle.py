from types import SimpleNamespace

import pytest

from eql_automation.owner_gauge_lifecycle import make_owner_nov12_engine


class Base:
    def __init__(self):
        self.hp, self.mana, self.last_gauge = .2, .3, 100.
        self.active = False
        self.cancel_generation = 1
        self.sender = SimpleNamespace(unfinished=False)
        self.calls = []

    def stop_action(self, reason, **kwargs):
        self.calls.append(("stop", self.hp, self.mana))
        raise OSError("fixture release failure")

    def handle_job(self, name, value):
        self.calls.append((name, self.hp, self.mana, self.last_gauge))


def test_cleanup_failure_cannot_keep_old_gauges():
    engine = make_owner_nov12_engine(Base)()
    with pytest.raises(OSError, match="fixture release failure"):
        engine.stop_action("F9")
    assert engine.calls == [("stop", None, None)]
    assert engine.hp is engine.mana is None
    assert engine.last_gauge == float("-inf")


@pytest.mark.parametrize("job", ["arm", "settings"])
def test_inactive_start_or_settings_requires_resample(job):
    engine = make_owner_nov12_engine(Base)()
    engine.handle_job(job, 1)
    assert engine.calls == [(job, None, None, float("-inf"))]


def test_stale_queued_start_still_cannot_arm():
    engine = make_owner_nov12_engine(Base)()
    engine.handle_job("arm", 0)
    assert engine.calls == [] and not engine.active
    assert engine.hp is engine.mana is None


def test_active_target_refresh_does_not_discard_current_sample():
    engine = make_owner_nov12_engine(Base)()
    engine.active = True
    engine.handle_job("arm", 1)
    assert engine.calls == [("arm", .2, .3, 100.)]


def test_explicit_heal_does_not_depend_on_a_gauge():
    engine = make_owner_nov12_engine(Base)()
    engine._invalidate_gauges()
    engine.handle_job("heal", 1)
    assert engine.calls == [("heal", None, None, float("-inf"))]
