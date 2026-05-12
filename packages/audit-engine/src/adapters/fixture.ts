import type { EngineRunResult, Finding, NormalizedSource } from "@wr3/types";
import type { EngineAdapter, EngineRunOptions } from "../contracts.js";

export class FixtureEvmAdapter implements EngineAdapter {
  name = "fixture_evm";

  async version(): Promise<string> {
    return "fixture-evm-v0.1";
  }

  supports(input: NormalizedSource): boolean {
    return input.chain !== "solana";
  }

  async run(input: NormalizedSource, opts: EngineRunOptions): Promise<EngineRunResult> {
    const started = performance.now();
    const findings = this.normalize(input.source, input, opts);
    return {
      engine: this.name,
      status: "success",
      duration_ms: Math.round(performance.now() - started),
      findings,
      artifacts: [],
      raw_output: JSON.stringify({ fixture_findings: findings.length }),
      error: null,
      versions: { [this.name]: await this.version() }
    };
  }

  normalize(raw: unknown, input: NormalizedSource, opts: EngineRunOptions): Finding[] {
    const source = String(raw).toLowerCase();
    const findings: Finding[] = [];
    if (source.includes("tx.origin")) {
      findings.push(makeFinding(opts.auditId, input, {
        severity: "high",
        confidence: 0.82,
        exploitability: "likely",
        category: "access_control",
        summary: "Authorization depends on tx.origin",
        impact: "Phishing flows can pass authorization through an intermediate caller.",
        recommendation: "Use msg.sender based authorization and explicit role checks."
      }));
    }
    if (source.includes("delegatecall")) {
      findings.push(makeFinding(opts.auditId, input, {
        severity: "high",
        confidence: 0.72,
        exploitability: "theoretical",
        category: "upgradeability",
        summary: "Delegatecall requires strict target control",
        impact: "A controlled or unvalidated delegatecall target can modify caller storage.",
        recommendation: "Restrict delegatecall targets and validate implementation code hashes."
      }));
    }
    if (findings.length === 0) {
      findings.push(makeFinding(opts.auditId, input, {
        severity: "info",
        confidence: 0.9,
        exploitability: "unknown",
        category: "informational",
        summary: "No fixture findings detected",
        impact: "This fixture pass found no known pattern.",
        recommendation: "Run production static analysis and human review before launch."
      }));
    }
    return findings;
  }
}

function makeFinding(
  auditId: string,
  input: NormalizedSource,
  args: {
    severity: Finding["severity"];
    confidence: number;
    exploitability: Finding["exploitability"];
    category: string;
    summary: string;
    impact: string;
    recommendation: string;
  }
): Finding {
  return {
    id: `wr3-find-${auditId}-${args.category}`,
    audit_id: auditId,
    chain: input.chain,
    contract: { address: input.address, name: input.contract_name, file: input.file_name },
    location: { file: input.file_name, start_line: null, end_line: null, function: null },
    taxonomy: { swc: null, cwe: null, wr3_category: args.category },
    severity: args.severity,
    confidence: args.confidence,
    exploitability: args.exploitability,
    sources: ["fixture_evm"],
    evidence: {
      static_trace: args.summary,
      poc_status: "not_attempted",
      poc_artifact_uri: null,
      fuzzer_counterexample_uri: null
    },
    summary: args.summary,
    description: args.summary,
    impact: args.impact,
    recommendation: args.recommendation,
    dismissal_reason: null,
    human_review_status: args.severity === "high" || args.severity === "critical" ? "pending" : "not_required"
  };
}
