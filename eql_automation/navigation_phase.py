"""Admission for an explicit supervised navigation phase, never ordinary assist."""

def navigation_active(engine):
    predicate = getattr(engine, '_owner_navigation_active', None)
    return predicate() is True if predicate is not None else engine.measurement_only is True
