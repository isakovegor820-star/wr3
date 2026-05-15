# Disclosure UI

Open:

```text
http://127.0.0.1:3001/disclosure
```

The local UI talks to reviewer-only API routes with the dev reviewer header.

## Supported Local Flow

1. Create a disclosure case for a finding id.
2. View the private case list.
3. Add contact-log entries.
4. Advance status through the disclosure timeline:
   - Day 0 private contact.
   - Day 7 SEAL 911 escalation.
   - Day 14 CVE/EUVD preparation.
   - Day 45 coordinated notice.
   - Day 90 limited disclosure.
   - Day 180 full PoC only if allowed.

No public scam/fraud accusation is created from this UI. Paid/public launch
still requires external legal review.
