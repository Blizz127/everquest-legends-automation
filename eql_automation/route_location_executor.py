"""Checked /location commands for the explicit route-session driver.

Reuse the measurement command's actual KeySender code, pinned descriptor,
per-key submission observations and unconditional release. There is no motion
method here: route pulses remain with run_checked_route_step and its ledger.
No provider, virtual device or owner hotkey is constructed by this module.
"""
from .motion_collection import CollectionStopped
from .motion_executors import _LocationExecutor
from .route_session import RouteSession,RouteSessionDriver


class RouteLocationExecutor(_LocationExecutor):
    """Require a current independent chat/scene observer for every command key.

    ``check_input`` follows MeasurementInputEvidence and exact submission
    identity semantics. Engine flags alone cannot supply that evidence.
    This initial helper attachment is measurement-only; assist rejects it.
    """
    command_purpose = 'route_position'
    def __init__(self,engine,session,*,check_input):
        if (not isinstance(session,RouteSession) or not callable(check_input)
                or session.mode != 'measurement'
                or session.lock is not getattr(engine,'g0_stop_lock',None)):
            raise ValueError('Bound measurement route and independent command observer required')
        self.engine,self.session,self.check_input = engine,session,check_input

    def _bound_driver(self):
        e=self.engine;driver=e.route_session_driver
        if (not isinstance(driver,RouteSessionDriver) or driver.session is not self.session
                or driver.sender is not e.sender or not driver.busy
                or not e._route_idle() or self.session.mode != 'measurement'):
            raise CollectionStopped('Route command driver or idle binding changed')
        return driver
