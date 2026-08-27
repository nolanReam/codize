export type BuildPageLoadStatus = "loading" | "empty" | "active" | "completed" | "error";

export function resolveLoadedBuildStatus(
  hasCurrentChange: boolean,
  hasRecentCompletedChange: boolean
): Exclude<BuildPageLoadStatus, "loading" | "error"> {
  if (hasCurrentChange) return "active";
  return hasRecentCompletedChange ? "completed" : "empty";
}
