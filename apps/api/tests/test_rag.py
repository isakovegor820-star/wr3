from wr3_api.services.rag import LocalKnowledgeBase, chunk_text_content


def test_local_knowledge_base_returns_relevant_security_context():
    kb = LocalKnowledgeBase()
    kb.ingest(
        source="solodit",
        title="Vault reentrancy incident",
        content=(
            "A vault withdraw function transferred funds before updating accounting. "
            "The recommended mitigation was checks-effects-interactions and a reentrancy guard."
        ),
        tags=["evm", "reentrancy"],
    )
    kb.ingest(
        source="helius",
        title="Solana PDA signer issue",
        content="A program accepted unchecked accounts and failed to validate PDA seeds.",
        tags=["solana", "pda"],
    )

    results = kb.search("withdraw accounting reentrancy guard", tags=["evm"])

    assert results
    assert results[0].document.title == "Vault reentrancy incident"
    assert results[0].document.source == "solodit"


def test_knowledge_ingest_is_deterministic_for_same_content():
    kb = LocalKnowledgeBase()

    first = kb.ingest(source="defihacklabs", title="Case", content="oracle manipulation case")
    second = kb.ingest(source="defihacklabs", title="Case renamed", content="oracle manipulation case")

    assert first.id == second.id
    assert first.content_hash == second.content_hash


def test_chunk_text_content_keeps_empty_input_safe():
    assert chunk_text_content("") == [""]
