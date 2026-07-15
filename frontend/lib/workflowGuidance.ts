import type { GuidedStageId } from "./guidedProjectNavigation";

export interface WorkflowGuidanceContent {
  title: string;
  why: string;
  action: string;
  example: string;
  terms?: ReadonlyArray<{ term: string; definition: string }>;
  recovery?: string;
}

export const WORKFLOW_GUIDANCE: Record<GuidedStageId, WorkflowGuidanceContent> = {
  prompt: {
    title: "Prompt Builder",
    why: "A useful AI request gives enough context to help without giving up your own decisions.",
    action:
      "Describe the Context (what exists), the Task (what AI should help with now), and Guardrails (what AI should avoid changing or deciding).",
    example:
      "Context: I have a small study planner. Task: add one deadline filter. Guardrails: keep the existing data shape and explain each changed file.",
    terms: [
      { term: "Prompt", definition: "The request and context you give an AI tool." },
      { term: "Guardrail", definition: "A boundary that says what should stay unchanged or remain your decision." },
    ],
  },
  import: {
    title: "Bring Back What Changed",
    why:
      "After AI responds, bring back the response, change summary, changed-file list, diff, code snippet, or your own summary so Codize can help you understand what happened.",
    action:
      "Choose the input that best matches what you have and record it once. Remove secrets before pasting logs or configuration.",
    example: "A git diff plus: “AI added a filter and changed the task query.”",
    recovery: "Start with the most recent AI change instead of asking for another patch.",
    terms: [
      { term: "Implementation", definition: "The code and files that make the project behavior work." },
      { term: "Diff", definition: "A text view of lines added, removed, or changed." },
    ],
  },
  change_map: {
    title: "Change Map",
    why: "Change Map separates what Codize inferred from what you actually confirm.",
    action:
      "For each item choose the current labels: Looks right, I need to correct it, Not accurate or not relevant, I’m not sure, or I need to inspect this. Source references explain an inference; they do not prove it is correct.",
    example: "If a file is named in the diff but its behavior is unclear, choose “I need to inspect this.”",
    recovery: "Map the latest change before deciding which patch, if any, should come next.",
    terms: [
      { term: "Change Map", definition: "A reviewable draft of what appears to have changed." },
      { term: "Inference", definition: "A conclusion suggested by the available material, not a verified fact." },
    ],
  },
  review: {
    title: "Review",
    why: "Review is where you decide what to keep, revise, remove, test, or leave uncertain.",
    action:
      "Read the Change Map item, then record your decision. Needs testing means the behavior still needs a performed check; it does not mean Verified.",
    example: "Choose Needs testing when a new error state looks plausible but you have not triggered it yourself.",
    recovery: "Make one decision at a time; you do not need to solve every uncertain item before recording it honestly.",
  },
  verification: {
    title: "Verification",
    why: "Codize suggests checks. You perform them and record what happened.",
    action:
      "Perform the check, then record Passed, Failed, Skipped, or Not applicable. Passed and Failed both preserve useful results; Skipped and Not applicable mean different things. A suggestion is not proof, and Codize did not observe the result.",
    example: "Run the sign-in flow, observe the behavior, then record Passed or Failed with a short note.",
    recovery: "Record what actually happens before asking AI for another patch.",
    terms: [
      { term: "Verification", definition: "A check you perform to see how the implementation behaves." },
    ],
  },
  evidence: {
    title: "Evidence",
    why: "Evidence is supporting material you choose to keep with a performed check.",
    action:
      "Attach available output, an observation, screenshot note, link, response, or other support to an eligible result. A result is not Evidence; unavailable Evidence stays unavailable.",
    example: "Keep the relevant test output with a failed check so the failure is easier to investigate.",
    terms: [
      { term: "Evidence", definition: "Student-provided material kept with a performed check; it is not an independent guarantee." },
    ],
  },
  defense: {
    title: "Project Defense",
    why: "Project Defense asks you to explain the implementation in your own words.",
    action:
      "Keep the project open, name real files or functions, and explain why the implementation behaves that way. Project records provide context; they do not answer for you, no answer is generated, and Evidence does not guarantee PASS.",
    example: "Explain where a saved value enters the system, how it is transformed, and what could make that path fail.",
    terms: [
      { term: "Project Defense", definition: "Three grounded questions that ask you to explain your own implementation." },
    ],
  },
  report: {
    title: "Defense Report",
    why:
      "The Defense Report keeps a record of what you changed, reviewed, tested, documented, and explained.",
    action:
      "Read it as a project record: student-recorded content remains student-recorded, Verification is not independent proof, Evidence is student-provided, and PASS/FAIL is the evaluator outcome.",
    example: "Use unresolved risks and next actions to decide what the next deliberate change should be.",
    terms: [
      { term: "Defense Report", definition: "A durable, provenance-aware record of the workflow and Defense outcome." },
    ],
  },
};
