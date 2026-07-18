import { WORKFLOW_JOURNEY, type WorkflowJourneyStageId } from "@/lib/workflowJourney";

const ACTION_BY_STAGE: Record<WorkflowJourneyStageId, string> = {
  prompt: "Build the prompt you will use in your external AI tool.",
  import: "Bring back the response, diff, changed files, or your own notes.",
  change_map: "Review a draft of what appears to have changed.",
  review: "Decide what to keep, revise, remove, test, or leave uncertain.",
  verification: "Perform checks and record what actually happened.",
  evidence: "Attach available support without overstating what it proves.",
  defense: "Explain your implementation in your own words.",
  report: "Open the saved record of your workflow and Defense outcome.",
};

export default function LoopOverview({ defaultOpen = false }: { defaultOpen?: boolean }) {
  return (
    <details className="help" open={defaultOpen}>
      <summary>What you&rsquo;ll actually do &mdash; the whole Journey in 8 stages</summary>
      <div className="help-body">
        <ol style={{ margin: "6px 0", paddingLeft: 20 }}>
          {WORKFLOW_JOURNEY.map((stage) => (
            <li key={stage.id}>
              <strong>{stage.label}:</strong> {ACTION_BY_STAGE[stage.id]}
            </li>
          ))}
        </ol>
        <p className="muted" style={{ margin: "6px 0 0" }}>
          Use your AI tool after Prompt Builder, then return with what changed. Repeat per phase;
          you never have to do all of it at once.
        </p>
      </div>
    </details>
  );
}
