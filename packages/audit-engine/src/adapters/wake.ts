import type { EngineRunResult, NormalizedSource } from "@wr3/types";
import type { EngineRunOptions } from "../contracts.js";
import { ExternalCliAdapter } from "./external-tool.js";

export class WakeCliAdapter extends ExternalCliAdapter {
  name = "wake";
  command = "wake";

  normalize(_raw: unknown, _input: NormalizedSource, _opts: EngineRunOptions): EngineRunResult["findings"] {
    return [];
  }
}
