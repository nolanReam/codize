// One typed student-facing definition of the implemented eight-stage Journey.
// Purpose-specific views may add copy, but they must preserve this order and
// these labels. External AI generation happens between Prompt and Bring Back;
// it is not a Codize route or a ninth stage.
export const WORKFLOW_JOURNEY = [
  { id: "prompt", label: "Prompt Builder", href: "/app/phase/prompt" },
  { id: "import", label: "Bring Back What Changed", href: "/app/phase/import" },
  { id: "change_map", label: "Change Map", href: "/app/phase/change-map" },
  { id: "review", label: "Review", href: "/app/phase/review" },
  { id: "verification", label: "Verification", href: "/app/phase/verify" },
  { id: "evidence", label: "Evidence", href: "/app/phase/evidence" },
  { id: "defense", label: "Project Defense", href: "/app/gate" },
  { id: "report", label: "Defense Report", href: "/app/report" },
] as const;

export type WorkflowJourneyStageId = (typeof WORKFLOW_JOURNEY)[number]["id"];
