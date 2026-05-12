import type { AuditInput, Chain, EngineRunResult, Finding, NormalizedSource } from "@wr3/types";

export type EngineRunOptions = {
  auditId: string;
  timeoutMs?: number;
  artifactBaseUri?: string;
  allowNetwork?: boolean;
};

export type EngineAdapter = {
  name: string;
  version(): Promise<string>;
  supports(input: AuditInput | NormalizedSource): boolean;
  run(input: NormalizedSource, opts: EngineRunOptions): Promise<EngineRunResult>;
  normalize(raw: unknown, input: NormalizedSource, opts: EngineRunOptions): Finding[];
};

export type ExplorerSourcePuller = {
  name: string;
  supports(chain: Chain): boolean;
  pull(address: string, chain: Chain): Promise<ExplorerSourceResult>;
};

export type ExplorerSourceResult =
  | {
      status: "verified";
      source: string;
      contractName: string;
      fileName: string;
      explorerUrl?: string;
    }
  | {
      status: "missing" | "unsupported" | "rate_limited" | "failed";
      reason: string;
    };

export type ArtifactManifest = {
  auditId: string;
  artifacts: Array<{
    kind: "raw_output" | "report" | "poc" | "fuzzer_counterexample" | "manifest";
    uri: string;
    private: boolean;
  }>;
};
