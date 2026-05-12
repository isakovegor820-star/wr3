import type { Artifact } from "@wr3/types";

export function createArtifact(input: {
  auditId: string;
  kind: Artifact["kind"];
  uri: string;
  private?: boolean;
  encryptionKeyRef?: string | null;
  retentionUntil?: string | null;
}): Artifact {
  return {
    id: `wr3-artifact-${input.auditId}-${input.kind}-${Math.random().toString(36).slice(2, 10)}`,
    audit_id: input.auditId,
    kind: input.kind,
    uri: input.uri,
    private: input.private ?? true,
    encryption_key_ref: input.encryptionKeyRef ?? null,
    retention_until: input.retentionUntil ?? null
  };
}

export function assertPrivateSecurityArtifact(artifact: Artifact): void {
  if ((artifact.kind === "poc" || artifact.kind === "fuzzer_counterexample") && !artifact.private) {
    throw new Error("PoC and fuzzer artifacts must be private/gated");
  }
}
