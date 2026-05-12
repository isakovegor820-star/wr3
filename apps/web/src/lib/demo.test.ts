import assert from "node:assert/strict";
import test from "node:test";
import { scoreBand } from "@wr3/shared";
import { demoAudit, demoFindings } from "./demo";

test("demo audit stays in caution band and has redacted PoC artifacts", () => {
  assert.equal(scoreBand(demoAudit.score?.final_score ?? 0), "yellow");
  assert.ok(demoFindings.length > 0);
  assert.equal(demoFindings[0]?.evidence.poc_artifact_uri, null);
});
