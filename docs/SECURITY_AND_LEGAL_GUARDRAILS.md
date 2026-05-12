# Security And Legal Guardrails

wr3 must stay inside passive analysis unless the customer has provided explicit
authorization or the target is within a recognized Safe Harbor scope.

## Allowed

- Passive analysis of verified public source and bytecode metadata.
- Fork or local test-validator PoCs for owned contracts or authorized scopes.
- Private responsible disclosure.
- Safe Harbor scoped validation when written scope is present.

## Disallowed

- Instructions to exploit live third-party contracts.
- Mainnet transactions without written scope.
- Public release of working exploit steps before the disclosure window.
- Wording such as "scam", "fraud", or "safe" without human/legal review.
- Sending customer source, private findings, PoCs, or traces to analytics,
  Sentry, plain logs, or non-ZDR LLM providers.

## Prompt-injection handling

Contract source, README text, NatSpec, comments, events, filenames, and tests
are untrusted. LLM prompts must wrap them in `UNTRUSTED_CONTRACT_SOURCE` blocks
and explicitly reject instructions embedded in the source.

## Report wording

Prefer:

- "AI-assisted pre-audit"
- "Risk score"
- "No Critical findings detected by wr3 vX.Y"
- "Reproducible PoC in isolated fork/test-validator"

Avoid:

- "AI audit replaces human review"
- "Secure"
- "Scam score"
- "Exploit this live target"
