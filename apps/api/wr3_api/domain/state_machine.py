from wr3_api.domain.enums import AuditState


TRANSITIONS: dict[AuditState, set[AuditState]] = {
    AuditState.CREATED: {AuditState.QUEUED, AuditState.REJECTED},
    AuditState.QUEUED: {AuditState.INGESTING, AuditState.FAILED},
    AuditState.INGESTING: {AuditState.STATIC_RUNNING, AuditState.NEEDS_SOURCE, AuditState.FAILED},
    AuditState.NEEDS_SOURCE: {AuditState.QUEUED, AuditState.TERMINAL},
    AuditState.STATIC_RUNNING: {
        AuditState.TRIAGE_RUNNING,
        AuditState.PARTIAL,
        AuditState.FAILED,
    },
    AuditState.TRIAGE_RUNNING: {AuditState.POC_RUNNING, AuditState.SCORING, AuditState.FAILED},
    AuditState.POC_RUNNING: {AuditState.FUZZING_RUNNING, AuditState.SCORING, AuditState.FAILED},
    AuditState.FUZZING_RUNNING: {AuditState.SCORING, AuditState.PARTIAL, AuditState.FAILED},
    AuditState.SCORING: {AuditState.HUMAN_REVIEW, AuditState.COMPLETED, AuditState.FAILED},
    AuditState.HUMAN_REVIEW: {AuditState.COMPLETED, AuditState.CHANGES_REQUESTED},
    AuditState.CHANGES_REQUESTED: {AuditState.QUEUED, AuditState.TERMINAL},
    AuditState.PARTIAL: {AuditState.COMPLETED, AuditState.RETRYING},
    AuditState.RETRYING: {AuditState.QUEUED, AuditState.FAILED},
    AuditState.COMPLETED: {AuditState.TERMINAL},
    AuditState.FAILED: {AuditState.RETRYING, AuditState.TERMINAL},
    AuditState.REJECTED: {AuditState.TERMINAL},
    AuditState.TERMINAL: set(),
}

STAGE_PROGRESS: dict[AuditState, int] = {
    AuditState.CREATED: 2,
    AuditState.QUEUED: 5,
    AuditState.INGESTING: 15,
    AuditState.NEEDS_SOURCE: 20,
    AuditState.STATIC_RUNNING: 35,
    AuditState.TRIAGE_RUNNING: 55,
    AuditState.POC_RUNNING: 70,
    AuditState.FUZZING_RUNNING: 78,
    AuditState.SCORING: 88,
    AuditState.HUMAN_REVIEW: 94,
    AuditState.CHANGES_REQUESTED: 90,
    AuditState.PARTIAL: 92,
    AuditState.COMPLETED: 100,
    AuditState.FAILED: 100,
    AuditState.RETRYING: 10,
    AuditState.REJECTED: 100,
    AuditState.TERMINAL: 100,
}


class InvalidTransition(ValueError):
    pass


def can_transition(from_state: AuditState, to_state: AuditState) -> bool:
    return to_state in TRANSITIONS[from_state]


def assert_transition(from_state: AuditState, to_state: AuditState) -> None:
    if not can_transition(from_state, to_state):
        raise InvalidTransition(f"Invalid audit transition: {from_state} -> {to_state}")
