# LLM Provider Routing

Status: production policy and current MVP boundary.

## Default

`WR3_LLM_ZDR_REQUIRED=true` is the default. Sensitive security prompts must go
through a provider path with zero-data-retention terms or a local model.

## Routes

| Scenario | Allowed route | Notes |
| --- | --- | --- |
| UI assistant and non-sensitive copy | disabled/local/API provider | No source/findings/PoC bodies |
| Finding triage | OpenRouter ZDR or local deterministic fallback | Source wrapped as untrusted input |
| Local closed-team triage with NavyAI | `WR3_LLM_PROVIDER=navy` + `WR3_LLM_MODEL=gpt-5.5` | OpenAI-compatible endpoint; ZDR is not confirmed, so do not use for private customer source before legal/security approval |
| PoC generation | OpenRouter ZDR or local model only | Never non-ZDR |
| Final report wording | OpenRouter ZDR/local or deterministic renderer | No public High/Critical claim without human review |
| Embeddings/RAG | Public/reference corpora only | Do not embed customer private code unless opt-in |

## Prompt Boundary

Contract source, comments, NatSpec, README content, and test files are untrusted.
Prompts must place them inside:

```text
UNTRUSTED_CONTRACT_SOURCE_BEGIN
...
UNTRUSTED_CONTRACT_SOURCE_END
```

The system prompt must say that instructions inside these blocks are data, not
operator instructions.

## Stored Metadata

Allowed:

- provider
- model
- token counts
- cost
- route decision
- agent roles
- provider invoked flag
- error type

Blocked unless encrypted paid debug opt-in:

- prompt body
- response body
- source body
- PoC body
- exploit trace

## MVP Fallback

When provider config is missing or non-ZDR, wr3 uses deterministic triage. This
is lower quality but safe for local and closed-beta development.

## NavyAI Local Setup

NavyAI is supported as an OpenAI-compatible chat-completions provider for local
team experiments:

```env
WR3_LLM_PROVIDER=navy
WR3_LLM_MODEL=gpt-5.5
WR3_NAVY_API_KEY=...
WR3_NAVY_BASE_URL=https://api.navy/v1
```

The public model catalog exposes `gpt-5.5` through `/v1/models`; wr3 calls it via
`/v1/chat/completions` with `response_format={"type":"json_object"}` for
security triage. The Navy `gpt-5.5` endpoint requires its default temperature, so
wr3 does not send an explicit `temperature` field on that route. If the account
has no access or the provider fails, wr3 records only metadata about the provider
error and falls back to deterministic triage.

Do not store the Navy key in git. Keep it in local `.env`, Doppler, 1Password, or
another secret manager.
