// Deterministic Prompt Builder (v0.1). Pure text assembly — no LLM call, no
// randomness: the same inputs always produce the same prompt. The output is
// meant to be pasted into the student's external AI tool (Claude Code,
// Cursor, Copilot, ChatGPT, …).

export interface PromptBuilderInputs {
  projectGoal: string;
  phaseGoal: string;
  aiTask: string;
  files: string;
  constraints: string;
  doNotChange: string;
  planFirst: boolean;
  wantChecks: boolean;
  uncertainty: string;
}

export interface BuiltPrompt {
  prompt: string;
  whyStronger: string;
  badPrompt: string;
}

export function promptInputsHaveStudentWork(inputs: PromptBuilderInputs | null): boolean {
  if (!inputs) return false;
  return [
    inputs.projectGoal,
    inputs.phaseGoal,
    inputs.aiTask,
    inputs.files,
    inputs.constraints,
    inputs.doNotChange,
    inputs.uncertainty,
  ].some((value) => typeof value === "string" && value.trim().length > 0);
}

// The backend caps generated_prompt at 8000 chars; stay under it.
const MAX_PROMPT_CHARS = 7900;

const clean = (s: string) => s.replace(/\s+/g, " ").trim();

export function buildPrompt(raw: PromptBuilderInputs): BuiltPrompt {
  const i = {
    projectGoal: clean(raw.projectGoal),
    phaseGoal: clean(raw.phaseGoal),
    aiTask: clean(raw.aiTask),
    files: clean(raw.files),
    constraints: clean(raw.constraints),
    doNotChange: clean(raw.doNotChange),
    uncertainty: clean(raw.uncertainty),
  };

  const lines: string[] = [];
  if (i.projectGoal) lines.push(`I'm building: ${i.projectGoal}`);
  if (i.phaseGoal) lines.push(`Right now I'm working on: ${i.phaseGoal}`);
  lines.push("");
  lines.push(`Your task: ${i.aiTask || "(describe the one thing you want the AI to do)"}`);
  if (i.files) lines.push(`Only work in these files/components: ${i.files}`);
  if (i.constraints) lines.push(`Constraints: ${i.constraints}`);
  if (i.doNotChange) lines.push(`Do NOT change: ${i.doNotChange}`);
  lines.push("Do not touch anything outside the scope above. If you think something else must change, stop and tell me why first.");
  if (raw.planFirst) {
    lines.push("Before writing any code, give me a short plan of what you'll change and why, and wait for my go-ahead.");
  }
  if (raw.wantChecks) {
    lines.push("After the code, list exactly what I should manually verify to prove this works (including one failure case).");
  }
  lines.push("Explain any assumption you make about my code or data instead of silently guessing.");
  if (i.uncertainty) {
    lines.push(`Heads up — I'm least sure about: ${i.uncertainty}. Flag anything that touches this.`);
  }

  const whyParts: string[] = [
    "It scopes the request to one task instead of asking for everything at once.",
  ];
  if (i.files) whyParts.push("It names the exact files, so the AI can't rewrite things you don't understand.");
  if (i.doNotChange) whyParts.push("It fences off what must not change — the top cause of AI breaking working code.");
  if (raw.planFirst) whyParts.push("It demands a plan before code, so you stay the decision-maker.");
  if (raw.wantChecks) whyParts.push("It asks for verification steps, so you can prove the result instead of trusting it.");
  whyParts.push("It forces assumptions into the open, where you can check them.");

  const badPrompt = `Build ${i.aiTask || i.projectGoal || "my app"} for me. Make it work.`;

  return {
    prompt: lines.join("\n").slice(0, MAX_PROMPT_CHARS),
    whyStronger: whyParts.join(" "),
    badPrompt,
  };
}
