from wr3_api.domain.enums import Chain, Severity
from wr3_api.services.news import NewsDeduper, infer_category, normalize_defillama_hack


def test_normalize_defillama_hack_infers_chain_category_and_severity():
    item = normalize_defillama_hack(
        {
            "name": "Base lending oracle manipulation",
            "technique": "Price oracle was manipulated for $2.5m",
            "amount": "2.5m",
            "date": "2026-05-11T00:00:00Z",
            "url": "https://example.com/postmortem",
        }
    )

    assert item.chain == Chain.BASE
    assert item.category == "oracle"
    assert item.severity == Severity.HIGH
    assert item.url == "https://example.com/postmortem"


def test_news_deduper_removes_semantically_close_items():
    first = normalize_defillama_hack(
        {"name": "BSC bridge private key compromise", "technique": "$12m private key leak"}
    )
    second = normalize_defillama_hack(
        {"name": "BNB bridge key compromise", "technique": "$12m private key leak"}
    )

    deduped = NewsDeduper(threshold=0.75).dedupe([first, second])

    assert len(deduped) == 1


def test_infer_category_keeps_defamation_safe_language():
    assert infer_category("project was a scam fraud rug") == "incident"
