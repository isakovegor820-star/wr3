"""The triage prompt must cap contract source so real multi-file protocols don't
blow the token budget (Sourcify sources can be 100k+ tokens)."""
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import Chain
from wr3_api.domain.schemas import AuditRecord, CreateAuditRequest
from wr3_api.services.llm_triage import LlmTriageRouter, _cap_source_for_triage


def test_source_capped_for_triage(monkeypatch):
    monkeypatch.setenv("WR3_LLM_MAX_SOURCE_CHARS", "500")
    get_settings.cache_clear()
    try:
        huge = "contract C { uint x; }\n" * 2000  # ~44k chars
        capped = _cap_source_for_triage(huge)
        assert len(capped) < 700  # ~500 cap + the truncation marker
        assert "обрезан" in capped

        # short source passes through untouched
        assert _cap_source_for_triage("contract X {}") == "contract X {}"

        # the assembled agent prompt is bounded, not the full 44k source
        router = LlmTriageRouter()
        record = AuditRecord(
            request=CreateAuditRequest(chain=Chain.BASE, address="0x" + "1" * 40, source="x")
        )
        prompt = router.build_prompt_preview(record, huge)
        assert len(prompt) < 2000
    finally:
        get_settings.cache_clear()


def test_cap_disabled_when_zero(monkeypatch):
    monkeypatch.setenv("WR3_LLM_MAX_SOURCE_CHARS", "0")
    get_settings.cache_clear()
    try:
        src = "contract C {}\n" * 100
        assert _cap_source_for_triage(src) == src  # 0 = no cap
    finally:
        get_settings.cache_clear()
