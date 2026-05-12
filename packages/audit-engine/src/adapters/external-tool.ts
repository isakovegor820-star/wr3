import { spawn } from "node:child_process";
import type { EngineRunResult, NormalizedSource } from "@wr3/types";
import type { EngineAdapter, EngineRunOptions } from "../contracts.js";

export abstract class ExternalCliAdapter implements EngineAdapter {
  abstract name: string;
  abstract command: string;

  abstract normalize(raw: unknown, input: NormalizedSource, opts: EngineRunOptions): EngineRunResult["findings"];

  supports(input: NormalizedSource): boolean {
    return input.chain !== "solana";
  }

  async version(): Promise<string> {
    try {
      const result = await runCommand(this.command, ["--version"], 5000);
      return result.stdout.trim() || `${this.name}:unknown`;
    } catch {
      return `${this.name}:not-installed`;
    }
  }

  async run(input: NormalizedSource, opts: EngineRunOptions): Promise<EngineRunResult> {
    const version = await this.version();
    if (version.endsWith(":not-installed")) {
      return {
        engine: this.name,
        status: "skipped",
        duration_ms: 0,
        findings: [],
        artifacts: [],
        raw_output: null,
        error: `${this.command} binary not installed`,
        versions: { [this.name]: version }
      };
    }
    return {
      engine: this.name,
      status: "skipped",
      duration_ms: 0,
      findings: [],
      artifacts: [],
      raw_output: null,
      error: "External CLI execution is stubbed until sandbox worker is enabled",
      versions: { [this.name]: version }
    };
  }
}

async function runCommand(command: string, args: string[], timeoutMs: number): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error("command timed out"));
    }, timeoutMs);
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      clearTimeout(timeout);
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(stderr || `command exited ${code}`));
    });
  });
}
