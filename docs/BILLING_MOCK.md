# Billing Mock

Open:

```text
http://127.0.0.1:3001/billing
```

The page stores `wr3-local-tier` in browser localStorage and lets localhost
switch between Free, Hobby, Team, and Pro.

## What It Tests

- UI display of current tier/quota.
- Server-side `tier` field on audit creation.
- Quota/degraded-mode path in the API.
- PoC/fuzzing gating behavior for Team/Pro/deep scans.

This is not a payment provider. Request Finance, Polar/Lemon, USDC operations,
refund handling, and support workflows remain production/business tasks.
