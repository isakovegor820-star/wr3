# Legal Disclaimer Draft

This draft is not legal advice and must be reviewed by a qualified legal
reviewer before paid or public launch.

wr3 provides AI-assisted pre-audit and exploitability triage. wr3 is not a
replacement for a comprehensive human security audit and does not guarantee that
any smart contract, protocol, token, account, or system is secure, safe, free of
bugs, or free of economic risk.

Reports are limited to the submitted scope, available source, configured tools,
engine versions, and score version shown in the report. A lack of Critical or
High findings means only that wr3 did not detect such findings in the analyzed
scope with the configured engine version.

wr3 does not perform active validation against live third-party systems unless
the project owner has provided explicit written authorization or the target is
inside an applicable Safe Harbor scope. wr3 does not provide instructions to
exploit live third-party contracts.

Maximum liability should be capped at the amount paid for the specific audit or
report, subject to final legal review.

## Data Retention Draft

Private source, private findings, raw outputs, PoC artifacts, and fuzzer
counterexamples are customer confidential or sensitive security data. Retention
should follow the active tier: Free 7 days, Hobby 30 days, Team 180 days, Pro 1
year unless a separate engagement letter says otherwise.

MVP API includes owner-requested audit deletion through
`DELETE /v1/audits/{id}`. Before paid launch, object storage deletion for R2/KMS
artifacts must be wired and tested so report, raw-output, PoC, and fuzzer
objects are removed or cryptographically shredded with the DB record.
