from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "readiness"


@dataclass(frozen=True)
class DrillStep:
    minute: int
    actor: str
    action: str
    expected_evidence: str


SCENARIOS = [
    {
        "id": "customer_zero_day_leak",
        "severity": "SEV-0",
        "trigger": "Private PoC artifact is suspected to be visible outside owner/reviewer scope.",
        "success_criteria": [
            "Public links disabled or redacted within 15 minutes.",
            "Customer notification draft ready within 2 hours.",
            "Artifact access logs preserved without copying sensitive payloads into public docs.",
        ],
    },
    {
        "id": "false_public_high_claim",
        "severity": "SEV-1",
        "trigger": "Public page shows a High/Critical risk claim without human approval.",
        "success_criteria": [
            "Claim removed or replaced with neutral wording within 1 hour.",
            "Human review status recorded.",
            "Regression task opened for public redaction gate.",
        ],
    },
    {
        "id": "sandbox_secret_exposure",
        "severity": "SEV-0",
        "trigger": "Sandbox worker receives DB credentials or secret-manager token.",
        "success_criteria": [
            "Worker stopped immediately.",
            "Secrets rotated.",
            "Sandbox env policy test added or updated.",
        ],
    },
]

STEPS = [
    DrillStep(0, "incident_commander", "Freeze deploys and name the incident.", "Incident id and commander recorded."),
    DrillStep(5, "tech_lead", "Disable affected route/provider/worker.", "Mitigation command or config change noted."),
    DrillStep(10, "security_reviewer", "Preserve scrubbed logs and artifact access metadata.", "No raw source/findings/PoC copied into drill artifact."),
    DrillStep(15, "product_lead", "Prepare customer/public communication draft.", "Draft uses no scam/fraud wording."),
    DrillStep(30, "tech_lead", "Rotate suspected secrets or artifact keys if needed.", "Rotation checklist linked."),
    DrillStep(60, "incident_commander", "Create follow-up actions and owners.", "Action list has owner/date."),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "kind": "wr3_incident_response_tabletop",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "local_tabletop_artifact_created",
        "production_blocker": "A live incident drill with the actual staging/prod access team is still required before public launch.",
        "scenarios": SCENARIOS,
        "timeline_steps": [asdict(step) for step in STEPS],
        "safety_rules": [
            "Do not paste raw findings, PoC, private source, private keys, or prompts into the drill artifact.",
            "Customer security findings stay private until disclosure gates allow publication.",
            "No active mainnet action is part of incident response unless explicit Safe Harbor/authorization exists.",
        ],
    }
    json_path = OUT_DIR / f"incident_tabletop_{stamp}.json"
    md_path = OUT_DIR / f"incident_tabletop_{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# wr3 Incident Response Tabletop",
                "",
                f"- Created: {payload['created_at']}",
                f"- Status: {payload['status']}",
                f"- Production blocker: {payload['production_blocker']}",
                "",
                "## Scenarios",
                "",
                *[
                    f"- **{scenario['id']} ({scenario['severity']})**: {scenario['trigger']}"
                    for scenario in SCENARIOS
                ],
                "",
                "## Timeline",
                "",
                "| Minute | Actor | Action | Expected evidence |",
                "| --- | --- | --- | --- |",
                *[
                    f"| {step.minute} | {step.actor} | {step.action} | {step.expected_evidence} |"
                    for step in STEPS
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in payload.items() if key not in {"scenarios", "timeline_steps"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
