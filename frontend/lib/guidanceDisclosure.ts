import type { GuidedStageId } from "./guidedProjectNavigation";

export function guidanceStorageKey(userId: string, stage: GuidedStageId): string {
  // The current product exposes exactly one active project per account. Match
  // the existing draft convention without putting a project name/content in
  // browser storage.
  return `codize:guide:${userId}:active-project:${stage}`;
}

export function readGuidanceOpen(storage: Storage, key: string): boolean | null {
  try {
    const value = storage.getItem(key);
    return value === "1" ? true : value === "0" ? false : null;
  } catch {
    return null;
  }
}

export function writeGuidanceOpen(storage: Storage, key: string, open: boolean): void {
  try {
    storage.setItem(key, open ? "1" : "0");
  } catch {
    // Guidance preferences are optional. Storage failure never blocks work.
  }
}
