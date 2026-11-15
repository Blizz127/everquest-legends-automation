"""Dispatch protocols with real intent/Journey/tracker, without game input.

The small base models owner dispatch only. Actual probe, section and terminal
execution is exercised by the separate composed progression runtime fixture.
"""
from copy import deepcopy

import pytest

from eql_automation.camp_progression import CampProgression, continuation_available
from eql_automation.owner_camp_progression import CAMP_PROGRESSION_JOB, make_camp_progression_engine
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_route_trial import SOURCE_JOB
from test_camp_progression import owner as progression_owner, selection


REQUEST=dict(progression_id='butcher-newbie-goblin-slave-mines',open_flat_clear=True,
             owner_supervised_continuation=True)


class DispatchBase:
    def __init__(self,f):
        self.__dict__.update(vars(f.engine))
        self.__dict__.pop('_navigation_busy',None);self.__dict__.pop('trace',None)
        self.f=f;self.journey=None;self.supervised_motion=None
        self.delegated=[];self.messages=[];self.traces=[];self._journey_assist=None

    def _supervised_job_names(self):return (SOURCE_JOB,)

    def _navigation_busy(self):return self.supervised_motion is not None

    def post(self,name,value=None):
        self.supervised_epoch+=1;self.route_session_epoch+=1
        if name in self._supervised_job_names():
            value=dict(declaration=value,epoch=self.supervised_epoch,
                generation=self.cancel_generation,settings=settings_identity(self.settings))
        self.jobs.put((name,value))

    def handle_job(self,name,value):
        if name=='arm':
            self.stop_action('F8 takeover')
            self._journey_assist=(self.cancel_generation,settings_identity(self.settings))
            return
        self.delegated.append((name,value))
        if name!=SOURCE_JOB:return
        declaration=value['declaration']
        self.journey=Journey(self.cancel_generation,settings_identity(self.settings),'travel',
            destination_id=declaration['destination_id'],continue_camps=declaration['continue_camps'])
        self._prepare_supervised_job(name)
        if self.journey is not None:self.supervised_motion=dict(job=name)

    def _prepare_supervised_job(self,name):
        self.f.asset_hook(self)
        return dict(destination=self.journey.destination_assets if self.journey is not None else None)

    def stop_action(self,reason,*,keep_autopilot=False):
        self.cancel_generation+=1;self.cancelled=True
        self.journey=self.supervised_motion=None

    def _camp_continuation_available(self,j):return j.continue_camps is True
    def autopilot_payload(self):return {}
    def trace(self,name,**payload):self.traces.append((name,payload))
    def emit(self,message):self.messages.append(message)


@pytest.fixture
def dispatch(progression_owner):
    f=progression_owner
    f.provider_calls=[];f.asset_hook=lambda e:None;f.provider_hook=lambda e:None
    def provider(e,declaration):
        f.provider_calls.append(deepcopy(declaration));f.provider_hook(e)
        return f.selection
    def no_origin(*args,**kwargs):raise AssertionError('Initial dispatch cannot load a Goblin origin')
    f.engine=make_camp_progression_engine(DispatchBase,progression_provider=provider,
        origin_provider=no_origin,clock=f.clock)(f)
    yield f
    f.engine.stop_action('dispatch fixture cleanup')


def start(f,request=None):
    e=f.engine;e.post(CAMP_PROGRESSION_JOB,dict(REQUEST) if request is None else request)
    return e.handle_job(*e.jobs.get_nowait())


def test_initial_request_captures_typed_intent_before_source_assets_and_posts_no_second_job(dispatch):
    f=dispatch;e=f.engine;seen=[]
    def assets(e):
        assert type(e.journey.progression) is CampProgression
        assert e.journey.progression is e.journey._progression
        assert e.journey.continue_camps is True and e.journey._continue_camps is True
        assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None
        assert e.journey.progression.root is None
        seen.append(e.journey)
    f.asset_hook=assets;generation=e.cancel_generation
    start(f)
    assert seen==[e.journey] and e.cancel_generation==generation
    assert len(e.delegated)==1 and e.delegated[0][0]==SOURCE_JOB
    assert e.delegated[0][1]['declaration']==dict(open_flat_clear=True,
        destination_id='newbie-hills',continue_camps=True)
    assert f.provider_calls==[REQUEST] and e.jobs.empty()
    assert continuation_available(e.journey)
    assert e._camp_progression_request is None and e._camp_progression_pending is None
    assert e.autopilot_payload()['camp_progression']['progression_id']==REQUEST['progression_id']


def test_queued_progression_choice_is_detached_from_mutable_gui_dictionary(dispatch):
    f=dispatch;e=f.engine;request=dict(REQUEST)
    e.post(CAMP_PROGRESSION_JOB,request);request['open_flat_clear']=False
    e.handle_job(*e.jobs.get_nowait())
    assert f.provider_calls==[REQUEST] and e.journey is not None


@pytest.mark.parametrize('change',(
    {'progression_id':'another-profile'}, {'open_flat_clear':False},
    {'owner_supervised_continuation':False}, {'continue_camps':True},
    {'open_flat_clear':1}, {'owner_supervised_continuation':1},
))
def test_only_the_exact_explicit_three_key_request_can_start(dispatch,change):
    f=dispatch;request=dict(REQUEST);request.update(change)
    start(f,request)
    assert f.engine.journey is None and not f.engine.delegated and not f.provider_calls


@pytest.mark.parametrize('key',tuple(REQUEST))
def test_missing_explicit_choice_does_not_start(dispatch,key):
    request=dict(REQUEST);del request[key]
    start(dispatch,request)
    assert dispatch.engine.journey is None and not dispatch.engine.delegated


@pytest.mark.parametrize('level',(0,5,9,10,50,True,1.,'1',None))
def test_configured_departure_level_is_checked_before_source_dispatch(dispatch,level):
    dispatch.engine.settings.level=level
    start(dispatch)
    assert dispatch.engine.journey is None and not dispatch.engine.delegated
    assert not dispatch.provider_calls


@pytest.mark.parametrize('field',('generation','epoch','settings'))
def test_stale_queued_envelope_cannot_create_a_new_journey(dispatch,field):
    f=dispatch;e=f.engine;e.post(CAMP_PROGRESSION_JOB,dict(REQUEST))
    name,value=e.jobs.get_nowait();value[field]=() if field=='settings' else value[field]+1
    e.handle_job(name,value)
    assert e.journey is None and not e.delegated and not f.provider_calls


@pytest.mark.parametrize('action',('F8','F9'))
@pytest.mark.parametrize('boundary',('provider','assets'))
def test_stop_during_dispatch_cannot_publish_or_revive_progression(dispatch,action,boundary):
    f=dispatch;e=f.engine;captured=[]
    def stop(e):
        if e.journey is not None:captured.append(e.journey.progression)
        if action=='F8':e.handle_job('arm',e.cancel_generation)
        else:e.stop_action('F9 during dispatch')
    if boundary=='provider':f.provider_hook=stop
    else:f.asset_hook=stop
    generation=e.cancel_generation
    start(f)
    assert e.journey is None and e.supervised_motion is None and e.zone_itinerary_owner is None
    assert e.cancel_generation==generation+1
    assert not e.sender.held and e.jobs.empty()
    if action=='F8':assert e._journey_assist is not None
    if boundary=='provider':assert not e.delegated
    else:
        assert len(e.delegated)==1 and len(captured)==1
        assert not continuation_available(captured[0].intent.journey)


def test_equal_value_replacement_selection_is_not_adopted_after_provider_mutation(dispatch):
    f=dispatch
    f.provider_hook=lambda e:object.__setattr__(f.selection,'initial_destination_id','goblin-camp')
    start(f)
    assert f.engine.journey is None and not f.engine.delegated


def test_ordinary_source_dispatch_does_not_acquire_progression_or_origin_budget(dispatch):
    f=dispatch;e=f.engine
    e.handle_job(SOURCE_JOB,dict(declaration=dict(open_flat_clear=True,
        destination_id='newbie-hills',continue_camps=True)))
    assert e.journey is not None and getattr(e.journey,'progression',None) is None
    assert e._camp_continuation_available(e.journey)
    assert not f.provider_calls and e._camp_progression_pending is None


def test_wrong_provider_type_cannot_become_an_owner_intent(dispatch):
    f=dispatch;f.selection=object()
    start(f)
    assert not f.engine.delegated and f.engine.journey is None


def test_intent_cleanup_failure_cannot_skip_existing_owner_stop(dispatch):
    f=dispatch;e=f.engine;start(f)
    c=e.journey.progression;generation=e.cancel_generation
    def broken_cancel(reason):raise ValueError('synthetic changed intent')
    c.cancel=broken_cancel
    e.stop_action('F9')
    assert e.cancel_generation==generation+1 and e.journey is None
    assert e.supervised_motion is None and not e.sender.held
