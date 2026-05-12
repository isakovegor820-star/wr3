import assert from "node:assert/strict";
import test from "node:test";
import { FixtureEvmAdapter, ingestAuditInput } from "../src/index.js";

test("ingestion accepts source and computes deterministic hash", async () => {
  const result = await ingestAuditInput({
    chain: "base",
    address: "0x0000000000000000000000000000000000000000",
    source: "contract Vault {}",
    requested_depth: "preliminary",
    visibility: "private",
    user_intent: "pre_launch_self_check",
    tier: "free"
  });
  assert.equal(result.status, "ready");
  if (result.status === "ready") {
    assert.equal(result.source.contract_name, "Vault");
    assert.equal(result.source.source_hash.length, 64);
  }
});

test("ingestion asks for source when no explorer is configured", async () => {
  const result = await ingestAuditInput({
    chain: "base",
    address: "0x0000000000000000000000000000000000000000",
    source: null,
    requested_depth: "preliminary",
    visibility: "private",
    user_intent: "pre_launch_self_check",
    tier: "free"
  });
  assert.equal(result.status, "needs_source");
});

test("fixture adapter normalizes tx.origin finding", async () => {
  const result = await ingestAuditInput({
    chain: "base",
    address: "0x0000000000000000000000000000000000000000",
    source: "contract Vault { function a() public { tx.origin; } }",
    requested_depth: "preliminary",
    visibility: "private",
    user_intent: "pre_launch_self_check",
    tier: "free"
  });
  assert.equal(result.status, "ready");
  if (result.status !== "ready") return;
  const adapter = new FixtureEvmAdapter();
  const engineResult = await adapter.run(result.source, { auditId: "audit-test" });
  assert.equal(engineResult.status, "success");
  assert.equal(engineResult.findings[0]?.taxonomy.wr3_category, "access_control");
});
