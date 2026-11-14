from queue import Queue
from types import SimpleNamespace

import pytest

from eql_automation.owner_nov12_recovery import make_owner_nov12_engine


class BookkeepingEngine:
    def __init__(self):
        self.jobs = Queue()
        self.cancel_generation = 4
        self.active = self.preparing = self.stopping = self.measurement_only = False
        self.autopilot = self.pointer = None
        self.keys = set()
        self.sender = SimpleNamespace(unfinished=True, dismissed=True, held=set())
        self.deferred = "prepare"
        self.command_recovery_pending = True
        self.cancelled = False
        self.stopped_mid_command = True
        self.target_name = "old target"
        self.calls = []

    def post(self, name, value=None):
        self.jobs.put((name, value))

    def handle_job(self, name, value):
        self.calls.append((name, value))

    def reset_target(self, ready, **options):
        assert options == dict(forget=True, clear_seen=True, clear_role=True)
        self.target_ready = ready
        self.target_name = None

    def emit(self, text):
        self.status = text

    def trace(self, *args, **kwargs):
        self.last_trace = (args, kwargs)

    def send(self, *_):
        raise AssertionError("Recovery must not send input")

    def stop_action(self, *_args, **_kwargs):
        raise AssertionError("Confirmation must not call key-release paths")


def make_engine():
    return make_owner_nov12_engine(BookkeepingEngine)()


def test_confirmed_recovery_stays_off_and_invalidates_queued_work():
    engine = make_engine()
    engine.post("prepare_later")
    engine.post("arm")
    assert engine.handle_job("owner_chat_closed", {"chat_closed": True, "generation": 4})
    assert not engine.active and engine.cancelled
    assert engine.cancel_generation == 5
    assert engine.deferred is None and not engine.command_recovery_pending
    assert not engine.sender.unfinished and not engine.sender.dismissed
    assert engine.target_name is None and engine.target_ready is False
    assert engine.last_trace[1]["game_input_sent"] is False
    while not engine.jobs.empty():
        engine.handle_job(*engine.jobs.get())
    assert engine.calls == []
    engine.post("arm")
    engine.handle_job(*engine.jobs.get())
    assert engine.calls == [("arm", 5)]  # A fresh owner request can reach the engine.


@pytest.mark.parametrize("value", [None, True, {}, {"chat_closed": False, "generation": 4},
                                   {"chat_closed": 1, "generation": 4},
                                   {"chat_closed": True, "generation": 3},
                                   {"chat_closed": True, "generation": True}])
def test_recovery_requires_explicit_fresh_confirmation(value):
    engine = make_engine()
    assert not engine.handle_job("owner_chat_closed", value)
    assert engine.sender.unfinished and engine.cancel_generation == 4
    assert engine.calls == []


@pytest.mark.parametrize("field,value", [("active", True), ("preparing", True),
                                         ("stopping", True), ("measurement_only", True),
                                         ("autopilot", object()), ("pointer", object()),
                                         ("keys", {9})])
def test_recovery_refuses_active_or_unsettled_state(field, value):
    engine = make_engine()
    setattr(engine, field, value)
    assert not engine.handle_job("owner_chat_closed", {"chat_closed": True, "generation": 4})
    assert engine.sender.unfinished and engine.cancel_generation == 4


def test_recovery_never_releases_an_uncertain_held_key():
    engine = make_engine()
    engine.sender.held.add(42)
    assert not engine.handle_job("owner_chat_closed", {"chat_closed": True, "generation": 4})
    assert engine.sender.held == {42} and engine.sender.unfinished


@pytest.mark.parametrize("job", ["prepare_later", "prepare", "arm", "heal"])
def test_stop_after_post_cancels_all_input_start_requests(job):
    engine = make_engine()
    engine.sender.unfinished = False
    engine.post(job)
    engine.cancel_generation += 1  # F9 processed before the GUI job is dequeued.
    engine.handle_job(*engine.jobs.get())
    engine.handle_job(job, None)
    assert engine.calls == []
    engine.post(job)
    engine.handle_job(*engine.jobs.get())
    assert engine.calls == [(job, 5)]


def test_unfinished_draft_explains_explicit_recovery():
    engine = make_engine()
    engine.post("arm")
    engine.handle_job(*engine.jobs.get())
    assert engine.calls == [] and "Chat recovery" in engine.status
