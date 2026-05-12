import { createHash } from "node:crypto";
import type { AuditInput, Chain, NormalizedSource } from "@wr3/types";
import type { ExplorerSourcePuller } from "./contracts.js";

export type IngestionResult =
  | { status: "ready"; source: NormalizedSource }
  | { status: "needs_source"; limitations: string[] }
  | { status: "rejected"; limitations: string[] };

export function normalizeSourceFromInput(input: AuditInput): IngestionResult {
  const limitations: string[] = [];
  if (input.chain === "solana") {
    limitations.push("solana_beta_static_subset_only");
  }
  if (input.source?.trim()) {
    return {
      status: "ready",
      source: {
        chain: input.chain,
        address: input.address,
        source: input.source,
        source_hash: hashSource(input.source),
        verified: Boolean(input.address),
        contract_name: guessContractName(input.source, input.chain),
        file_name: input.chain === "solana" ? "program.rs" : "Contract.sol",
        limitations
      }
    };
  }
  return {
    status: "needs_source",
    limitations: ["verified_source_pull_not_configured_or_source_missing"]
  };
}

export async function ingestAuditInput(
  input: AuditInput,
  explorers: ExplorerSourcePuller[] = []
): Promise<IngestionResult> {
  if (input.source?.trim()) {
    return normalizeSourceFromInput(input);
  }
  if (!input.address) {
    return { status: "needs_source", limitations: ["address_or_source_required"] };
  }
  const puller = explorers.find((candidate) => candidate.supports(input.chain));
  if (!puller) {
    return { status: "needs_source", limitations: [`no_explorer_puller_for_${input.chain}`] };
  }
  const pulled = await puller.pull(input.address, input.chain);
  if (pulled.status !== "verified") {
    return { status: "needs_source", limitations: [`explorer_source_${pulled.status}:${pulled.reason}`] };
  }
  return {
    status: "ready",
    source: {
      chain: input.chain,
      address: input.address,
      source: pulled.source,
      source_hash: hashSource(pulled.source),
      verified: true,
      contract_name: pulled.contractName,
      file_name: pulled.fileName,
      limitations: []
    }
  };
}

export function hashSource(source: string): string {
  return createHash("sha256").update(source).digest("hex");
}

function guessContractName(source: string, chain: Chain): string {
  if (chain === "solana") {
    return source.includes("#[program]") ? "AnchorProgram" : "SolanaProgram";
  }
  const match = source.match(/\b(?:contract|library|interface)\s+([A-Za-z_][A-Za-z0-9_]*)/);
  return match?.[1] ?? "Contract";
}
