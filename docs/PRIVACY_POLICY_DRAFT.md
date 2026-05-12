# Privacy Policy Draft

Status: draft only. External legal review is required.

## Data Collected

- Account identifiers: email, wallet address, Telegram subject, GitHub subject.
- Audit input: contract address, chain, pasted source, verified source metadata.
- Audit output: findings, reports, raw engine metadata, score breakdown.
- Operational metadata: audit state transitions, engine runtime, error type,
  token/cost counters, billing status.
- Payment metadata: provider, tier, invoice/transaction reference.

## Sensitive Data

Private source, private reports, findings, PoC artifacts, fuzzer
counterexamples, and prompt/response bodies are customer confidential or
sensitive security data. They must be encrypted at rest and excluded from plain
logs and analytics.

## Providers

wr3 may use infrastructure and security providers such as Cloudflare, Oracle,
Sentry, Doppler/1Password, OpenRouter ZDR, email delivery, and payment
providers. Sensitive prompts should only use ZDR/local paths unless the customer
explicitly opts in.

## Retention

Retention follows the tier policy:

- Free: 7 days.
- Hobby: 30 days.
- Team: 180 days.
- Pro: 365 days or custom agreement.

Users may request deletion of private audit records. Production object storage
deletion must remove encrypted artifacts as part of the deletion workflow before
public launch.

## Training Data

Customer private code and findings are not used for model training without
explicit opt-in.

## Contact

Add security and privacy contact addresses before public launch.
