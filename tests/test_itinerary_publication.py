"""A stop during child construction must not publish that child afterward."""
import pytest

import eql_automation.zone_itinerary_runtime as runtime_module
from test_zone_itinerary_runtime import complete_first, fitter, itinerary, legacy, run_until


@pytest.mark.parametrize('fault', ('F8', 'attack'))
def test_destination_candidate_is_cleaned_before_publication_after_late_veto(itinerary, monkeypatch, fault):
    f=itinerary
    complete_first(f)
    r=f.controller
    original=runtime_module.DestinationBootstrapRuntime
    candidates=[]
    def construct(*args, **kwargs):
        candidate=original(*args, **kwargs)
        candidates.append(candidate)
        if fault=='F8':
            f.engine.cancel_generation+=1
            r.cancel('Synthetic F8 at destination construction return')
        else:
            f.append('Training dummy hits YOU for 2 points of damage.')
        return candidate
    monkeypatch.setattr(runtime_module, 'DestinationBootstrapRuntime', construct)
    sent,pulses=len(f.sent),len(f.pulses)
    with pytest.raises((ValueError, RuntimeError)):
        r.tick()
    assert len(candidates)==1
    assert r.phase=='stopped' and r.bootstrap is None and r.assets is None
    assert candidates[0].closed and candidates[0].phase=='stopped'
    assert not r.lease.active and not f.root.valid
    assert len(f.sent)==sent and len(f.pulses)==pulses
    assert f.closed_observer==0
    r.release()
    assert f.closed_observer==1 and not f.sender.held


def test_destination_child_is_published_after_construction_checks(itinerary):
    f=itinerary
    complete_first(f)
    sent,pulses=len(f.sent),len(f.pulses)
    f.controller.tick()
    r=f.controller
    assert r.phase=='bootstrap' and r.bootstrap.phase=='new'
    assert r.assets is f.assets and r.journey.destination_assets is f.assets
    assert r.bootstrap.lease is r.lease and r.lease.active
    assert len(f.sent)==sent and len(f.pulses)==pulses


def test_source_candidate_is_not_published_after_late_owner_stop(itinerary, monkeypatch):
    f=itinerary
    complete_first(f)
    r=f.controller
    original=runtime_module.start_destination_source
    candidates=[]
    at_stop=[]
    def adopt(*args, **kwargs):
        candidate=original(*args, **kwargs)
        candidates.append(candidate)
        at_stop.append((len(f.sent),len(f.pulses)))
        f.engine.cancel_generation+=1
        r.cancel('Synthetic F8 at source adoption return')
        return candidate
    monkeypatch.setattr(runtime_module, 'start_destination_source', adopt)
    with pytest.raises((ValueError, RuntimeError)):
        run_until(f, lambda:bool(candidates))
    assert len(candidates)==1
    assert r.phase=='stopped' and r.source is None
    assert candidates[0].phase=='stopped'
    assert not f.root.valid and not r.lease.active
    assert (len(f.sent),len(f.pulses))==at_stop[0]
    assert f.closed_observer==0
    r.release()
    assert f.closed_observer==1 and not f.sender.held
