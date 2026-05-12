import assert from "node:assert/strict";
import test from "node:test";
import { scoreAudit, scoreBand, type Finding } from "../src/index.js";

function finding(overrides: Partial<Finding>): Finding {
  return {
    id: "wr3-find-test",
    audit_id: "audit-test",
    chain: "base",
    contract: { address: "0x0000000000000000000000000000000000000000", name: "Vault", file: "src/Vault.sol" },
    location: { file: "src/Vault.sol", start_line: 10, end_line: 20, function: "withdraw" },
    taxonomy: { swc: "SWC-107", cwe: "CWE-841", wr3_category: "reentrancy" },
    severity: "high",
    confidence: 1,
    exploitability: "confirmed",
    sources: ["test"],
    evidence: {
      static_trace: "test",
      poc_status: "not_attempted",
      poc_artifact_uri: null,
      fuzzer_counterexample_uri: null
    },
    summary: "Test finding",
    description: "Test description",
    impact: "Funds can be affected",
    recommendation: "Add a guard",
    dismissal_reason: null,
    human_review_status: "pending",
    ...overrides
  };
}

test("confirmed high caps final score", () => {
  const score = scoreAudit([finding({ severity: "high", exploitability: "confirmed" })]);
  assert.equal(score.final_score, 69);
  assert.ok(score.caps_applied.includes("confirmed_high"));
});

test("confirmed critical caps score to red band", () => {
  const score = scoreAudit([finding({ severity: "critical", exploitability: "confirmed" })]);
  assert.equal(score.final_score, 39);
  assert.equal(scoreBand(score.final_score), "red");
});

test("source and centralization caps compose conservatively", () => {
  const score = scoreAudit([], { unverifiedSource: true, unlimitedOwnerMint: true });
  assert.equal(score.final_score, 59);
  assert.deepEqual(score.caps_applied, ["unverified_source", "unlimited_owner_mint"]);
});
