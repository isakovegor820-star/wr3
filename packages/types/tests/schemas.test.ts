import assert from "node:assert/strict";
import test from "node:test";
import { auditInputSchema, canTransition, findingSchema } from "../src/index.js";

test("audit input validates supported EVM scan request", () => {
  const parsed = auditInputSchema.parse({
    chain: "base",
    address: "0x0000000000000000000000000000000000000000",
    source: "contract A {}",
    requested_depth: "preliminary",
    visibility: "private",
    user_intent: "pre_launch_self_check"
  });
  assert.equal(parsed.tier, "free");
  assert.equal(parsed.allow_bytecode_only, false);
});

test("finding schema enforces confidence range", () => {
  assert.throws(() =>
    findingSchema.parse({
      id: "x",
      audit_id: "audit",
      chain: "base",
      contract: { address: null, name: "A", file: null },
      location: { file: null, start_line: null, end_line: null, function: null },
      taxonomy: { swc: null, cwe: null, wr3_category: "other" },
      severity: "high",
      confidence: 1.2,
      exploitability: "likely",
      sources: ["fixture"],
      evidence: {
        static_trace: null,
        poc_status: "not_attempted",
        poc_artifact_uri: null,
        fuzzer_counterexample_uri: null
      },
      summary: "Bad",
      description: "Bad",
      impact: "Bad",
      recommendation: "Fix",
      dismissal_reason: null,
      human_review_status: "pending"
    })
  );
});

test("state machine keeps created to completed non-direct", () => {
  assert.equal(canTransition("created", "queued"), true);
  assert.equal(canTransition("created", "completed"), false);
});
