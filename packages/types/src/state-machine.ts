import type { AuditState } from "./enums.js";

export const auditTransitions: Record<AuditState, AuditState[]> = {
  created: ["queued", "rejected"],
  queued: ["ingesting", "failed"],
  ingesting: ["static_running", "needs_source", "failed"],
  needs_source: ["queued", "terminal"],
  static_running: ["triage_running", "partial", "failed"],
  triage_running: ["poc_running", "scoring", "failed"],
  poc_running: ["fuzzing_running", "scoring", "failed"],
  fuzzing_running: ["scoring", "partial", "failed"],
  scoring: ["human_review", "completed", "failed"],
  human_review: ["completed", "changes_requested"],
  changes_requested: ["queued", "terminal"],
  partial: ["completed", "retrying"],
  retrying: ["queued", "failed"],
  completed: ["terminal"],
  failed: ["retrying", "terminal"],
  rejected: ["terminal"],
  terminal: []
};

export const stageProgress: Record<AuditState, number> = {
  created: 2,
  queued: 5,
  ingesting: 15,
  needs_source: 20,
  static_running: 35,
  triage_running: 55,
  poc_running: 70,
  fuzzing_running: 78,
  scoring: 88,
  human_review: 94,
  changes_requested: 90,
  partial: 92,
  completed: 100,
  failed: 100,
  retrying: 10,
  rejected: 100,
  terminal: 100
};

export function canTransition(from: AuditState, to: AuditState): boolean {
  return auditTransitions[from].includes(to);
}

export function assertTransition(from: AuditState, to: AuditState): void {
  if (!canTransition(from, to)) {
    throw new Error(`Invalid audit transition: ${from} -> ${to}`);
  }
}
