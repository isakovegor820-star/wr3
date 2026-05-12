from wr3_api.services.observability import LlmCostEvent, LlmCostLedger, SensitiveScrubber


def test_sensitive_scrubber_redacts_source_findings_prompts_and_tokens():
    payload = {
        "source": "contract Secret {}",
        "nested": {
            "prompt": "private prompt",
            "token": "secret-token",
            "safe_metric": 123,
        },
        "items": [{"raw_output": "private"}],
    }

    scrubbed = SensitiveScrubber().scrub(payload)

    assert scrubbed["source"] == "[REDACTED]"
    assert scrubbed["nested"]["prompt"] == "[REDACTED]"
    assert scrubbed["nested"]["token"] == "[REDACTED]"
    assert scrubbed["nested"]["safe_metric"] == 123
    assert scrubbed["items"][0]["raw_output"] == "[REDACTED]"


def test_llm_cost_ledger_summarizes_without_prompt_body():
    ledger = LlmCostLedger()
    ledger.record(
        LlmCostEvent(
            provider="openrouter",
            model="test-model",
            prompt_tokens=100,
            completion_tokens=20,
            estimated_cost_usd=0.01,
            layer="triage",
            audit_id="audit-1",
        )
    )

    summary = ledger.summary()

    assert summary["total_cost_usd"] == 0.01
    assert summary["by_layer"] == {"triage": 0.01}
    assert "prompt" not in summary
