"""Phase-aware location-command evidence from independent current observations.

This fills the executor's check_input seam, not the still-missing calibrated
pixel classifier. It cannot turn frame candidates, a quiet log, or a successful
uinput write into chat-focus/text evidence. No input/display/device is opened.
The existing safety scope reads its separate veto tail, never the route's
exclusive location reader.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

from .command_submission import (CommandSubmissionSnapshot, LOCATION_COMMAND,
                                 LOCATION_KEYS, LOCATION_EVENTS)
from .g2_safety_provider import G2SafetyProvider, G2UiObservation
from .g2_scene_observer import G2ObservationUnavailable
from .motion_collection import LocationRequest
from .motion_executors import MeasurementInputEvidence


@dataclass(frozen=True)
class CommandUiObservation(G2UiObservation):
    """Independent classifier result bound to this invocation and exact draft.

    Empty pixels do not establish closed chat or an absent draft. During
    typing, the complete field, focus, insertion point and lack of selection
    all need positive evidence. Default/unknown values therefore refuse.
    """
    request: LocationRequest | None = None
    phase: str | None = None
    submission: CommandSubmissionSnapshot | None = None
    input_focused: bool | None = None
    draft_absent: bool = False
    visible_prefix: str | None = None
    text_complete: bool = False
    caret_at_end: bool = False
    selection_absent: bool = False


def check_submission(phase, snapshot):
    if (not isinstance(snapshot, CommandSubmissionSnapshot)
            or snapshot.command != LOCATION_COMMAND or snapshot.uncertain
            or not snapshot.operation_id or type(snapshot.submitted_key_count) is not int):
        raise G2ObservationUnavailable('Missing exact unambiguous location submission')
    count = snapshot.submitted_key_count
    if (not 0 <= count <= len(LOCATION_KEYS) or len(snapshot.writes) != count * 4
            or snapshot.submitted_prefix != LOCATION_COMMAND[:min(count, len(LOCATION_COMMAND))]
            or snapshot.attempted_key_codes != LOCATION_KEYS[:count]
            or snapshot.enter_submitted is not (count == len(LOCATION_KEYS))
            or snapshot.next_key_code != (LOCATION_KEYS[count] if count < len(LOCATION_KEYS) else None)
            or any(not w.complete or w.index != i or w.event != LOCATION_EVENTS[i]
                   for i, w in enumerate(snapshot.writes))
            or any(a.finished_at > b.started_at for a, b in zip(snapshot.writes, snapshot.writes[1:]))):
        raise G2ObservationUnavailable('Location prefix write history is incomplete or changed')
    if (phase not in ('command_start', 'command_first_key', 'command_key', 'command_end')
            or (phase in ('command_start', 'command_first_key') and count != 0)
            or (phase == 'command_key' and not 1 <= count < len(LOCATION_KEYS))
            or (phase == 'command_end' and count != len(LOCATION_KEYS))):
        raise G2ObservationUnavailable('Location observation phase differs from submitted prefix')


class CommandInputProvider:
    """Use with either checked location executor, in measurement mode only.

    ``ui_observer(window, request, phase, submission)`` must capture and
    independently classify a new frame inside the safety scope. A
    PreparedUiFrameReader's diagnostic dictionary is intentionally insufficient.
    The owning executor still checks request/session identity and revocation
    before every write; this provider cannot attach or start a helper.
    """
    def __init__(self, safety, *, ui_observer):
        if not isinstance(safety, G2SafetyProvider) or not callable(ui_observer):
            raise ValueError('Bound safety scope and independent command UI classifier required')
        self.safety, self.ui_observer = safety, ui_observer
        self.last_observation = None

    def __call__(self, request, phase, submission):
        self.last_observation = None
        if not isinstance(request, LocationRequest):
            raise G2ObservationUnavailable('Location command request required; movement is unsupported')
        check_submission(phase, submission)
        now = self.safety.clock()
        if not request.issued_at <= now <= request.expires_at:
            raise G2ObservationUnavailable('Location request has expired or is not issued yet')
        began, visual = self.safety.observe_ui(
            lambda window: self.ui_observer(window, request, phase, submission))
        if (not isinstance(visual, CommandUiObservation) or visual.request is not request
                or visual.phase != phase or visual.submission is not submission
                or (submission.writes and visual.started_at < submission.writes[-1].finished_at)):
            raise G2ObservationUnavailable('UI observation does not bind this exact command prefix')
        if phase == 'command_key':
            if (visual.chat_clear is not False or visual.input_focused is not True
                    or visual.draft_absent is not False
                    or visual.visible_prefix != submission.submitted_prefix
                    or not all(v is True for v in
                               (visual.text_complete, visual.caret_at_end, visual.selection_absent))):
                raise G2ObservationUnavailable('Current complete focused command draft is unverified')
        elif (visual.chat_clear is not True or visual.input_focused is not False
                or visual.draft_absent is not True or visual.visible_prefix is not None):
            raise G2ObservationUnavailable('Current closed chat and absent draft are unverified')
        finished = self.safety.clock()
        expires = min(request.expires_at, began + .1)
        if not request.issued_at <= began <= finished <= expires:
            raise G2ObservationUnavailable('Command observation expired during classification')
        record = dict(format='eql-command-input-evidence-v1', phase=phase,
            operation_id=submission.operation_id, revision=submission.revision,
            frame_sha256=visual.frame_sha256, calibration_sha256=visual.calibration_sha256,
            began=began, finished=finished)
        digest = sha256(json.dumps(record, sort_keys=True, allow_nan=False).encode()).hexdigest()
        self.last_observation = visual
        return MeasurementInputEvidence(request, phase, began, expires,
                                        'command-ui-' + digest, submission)
