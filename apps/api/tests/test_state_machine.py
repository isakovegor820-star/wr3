import pytest

from wr3_api.domain.enums import AuditState
from wr3_api.domain.state_machine import InvalidTransition, assert_transition, can_transition


def test_core_audit_transition_path_is_valid():
    path = [
        AuditState.CREATED,
        AuditState.QUEUED,
        AuditState.INGESTING,
        AuditState.STATIC_RUNNING,
        AuditState.TRIAGE_RUNNING,
        AuditState.SCORING,
        AuditState.COMPLETED,
    ]
    for left, right in zip(path, path[1:]):
        assert can_transition(left, right)


def test_invalid_transition_is_rejected():
    with pytest.raises(InvalidTransition):
        assert_transition(AuditState.CREATED, AuditState.COMPLETED)
