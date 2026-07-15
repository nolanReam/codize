import type {
  AiChangeState,
  CodingConfidence,
  EntryProfile,
  EntrySituation,
  GuidanceDepth,
  RecommendedStart,
} from "./types";

export const ENTRY_SITUATIONS: ReadonlyArray<{
  value: EntrySituation;
  label: string;
  description: string;
}> = [
  {
    value: "starting_fresh",
    label: "I have an idea and want help starting.",
    description: "I have not built much yet, or I want a better plan before asking AI to code.",
  },
  {
    value: "already_building",
    label: "I have already started building with AI.",
    description: "I have prompts, code, files, or an early version of the project.",
  },
  {
    value: "stuck",
    label: "I keep patching problems and I am not sure what changed.",
    description: "The project mostly works, but fixes keep creating new confusion or errors.",
  },
];

export const CODING_CONFIDENCE_CHOICES: ReadonlyArray<{
  value: CodingConfidence;
  label: string;
}> = [
  { value: "new_to_code", label: "I am new to coding." },
  { value: "know_basics", label: "I know the basics." },
  { value: "comfortable", label: "I am comfortable reading and changing code." },
];

export const AI_CHANGE_CHOICES: ReadonlyArray<{
  value: AiChangeState;
  label: string;
}> = [
  { value: "yes", label: "Yes" },
  { value: "not_yet", label: "Not yet" },
  { value: "unsure", label: "I am not sure" },
];

export const SITUATION_LABELS: Record<EntrySituation, string> = {
  starting_fresh: "Starting fresh",
  already_building: "Already building",
  stuck: "Stuck in a patch loop",
};

export const CONFIDENCE_LABELS: Record<CodingConfidence, string> = {
  new_to_code: "More guidance",
  know_basics: "Standard guidance",
  comfortable: "Minimal guidance",
};

export interface StartingRecommendation {
  id: RecommendedStart;
  label: string;
  reason: string;
  actionLabel: string;
  href: string;
}

export const STARTING_RECOMMENDATIONS: Record<RecommendedStart, StartingRecommendation> = {
  prompt_builder: {
    id: "prompt_builder",
    label: "Prompt Builder",
    reason: "Turn your idea into a structured request before asking AI to build.",
    actionLabel: "Start Prompt Builder",
    href: "/app/phase/prompt",
  },
  implementation_import: {
    id: "implementation_import",
    label: "Bring Back What Changed",
    reason: "Start by recording what AI changed so you can review and test it.",
    actionLabel: "Bring Back What Changed",
    href: "/app/phase/import",
  },
  quick_start: {
    id: "quick_start",
    label: "80% Trap Quick Start",
    reason: "Pause the patch loop, bring back the latest change, and rebuild a clear record before the next patch.",
    actionLabel: "Start the 80% Trap Quick Start",
    href: "/app?quick-start=1",
  },
};

export const QUICK_START_STEPS = [
  "Pause before asking AI for another patch.",
  "Bring back the latest AI response or change summary.",
  "Map what changed.",
  "Review the decisions.",
  "Verify the behavior before the next patch.",
] as const;

export const TRAP_DEFINITION =
  "The first version feels mostly finished, but the last part turns into a cycle of patches, repeated errors, and changes you no longer understand.";

const SITUATIONS = new Set<EntrySituation>(ENTRY_SITUATIONS.map((choice) => choice.value));
const CONFIDENCE = new Set<CodingConfidence>(
  CODING_CONFIDENCE_CHOICES.map((choice) => choice.value)
);
const AI_CHANGES = new Set<AiChangeState>(AI_CHANGE_CHOICES.map((choice) => choice.value));
const STARTS = new Set<RecommendedStart>(Object.keys(STARTING_RECOMMENDATIONS) as RecommendedStart[]);
const DEPTHS = new Set<GuidanceDepth>(["more", "standard", "minimal"]);

export function normalizeEntryProfile(value: unknown): EntryProfile | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const situation = raw.current_situation;
  const confidence = raw.coding_confidence;
  const aiChanges = raw.ai_changed_files;
  const start = raw.recommended_start;
  if (raw.schema_version !== "1.0") return null;
  if (situation !== null && !SITUATIONS.has(situation as EntrySituation)) return null;
  if (confidence !== null && !CONFIDENCE.has(confidence as CodingConfidence)) return null;
  if (aiChanges !== null && !AI_CHANGES.has(aiChanges as AiChangeState)) return null;
  if (start !== null && !STARTS.has(start as RecommendedStart)) return null;
  if (!DEPTHS.has(raw.guidance_depth as GuidanceDepth)) return null;
  if (typeof raw.completed !== "boolean" || typeof raw.recovery_emphasis !== "boolean") return null;
  if (typeof raw.updated_at !== "string") return null;
  if (situation !== "already_building" && aiChanges !== null) return null;
  return raw as unknown as EntryProfile;
}

export type EntryStep = "situation" | "confidence" | "ai_changes" | "recommendation";

export function nextEntryStep(profile: EntryProfile | null): EntryStep {
  if (!profile?.current_situation) return "situation";
  if (!profile.coding_confidence) return "confidence";
  if (profile.current_situation === "already_building" && !profile.ai_changed_files) {
    return "ai_changes";
  }
  return "recommendation";
}

export function guidanceDepth(profile: EntryProfile | null): GuidanceDepth {
  return profile?.guidance_depth ?? "standard";
}

export function recommendationFor(profile: EntryProfile | null): StartingRecommendation | null {
  if (!profile?.completed || !profile.recommended_start) return null;
  const base = STARTING_RECOMMENDATIONS[profile.recommended_start];
  if (
    profile.current_situation === "already_building" &&
    profile.ai_changed_files === "unsure"
  ) {
    return {
      ...base,
      reason:
        "Bring back the latest AI response or change summary, then separate what is known from what still needs inspection.",
    };
  }
  if (
    profile.current_situation === "already_building" &&
    profile.ai_changed_files === "not_yet"
  ) {
    return {
      ...base,
      reason: "Create a clear request before the next AI-generated change.",
    };
  }
  return base;
}
