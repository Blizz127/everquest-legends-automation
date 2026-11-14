"""Cheap in-memory value pins for records whose fields are immutable.

These snapshots never deserialize or authorize anything. They replace repeated
JSON/deepcopy checks of already validated scalar records, not evidence files.
Nested mutable records must be snapshotted separately by their owner.
"""
from datetime import datetime


_SCALARS=(type(None),bool,int,float,str,bytes,datetime)


def _value(value):
    kind=type(value)
    if kind in _SCALARS:return kind,value
    if kind is tuple:return tuple,tuple(_value(v) for v in value)
    raise ValueError('Flat record contains a mutable or unknown field')


def flat_record_state(record):
    return type(record),id(record),tuple((key,_value(value)) for key,value in vars(record).items())
