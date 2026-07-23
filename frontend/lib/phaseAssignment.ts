import { promptInputsHaveStudentWork, type PromptBuilderInputs } from "./promptBuilder";
import {
  scopePracticeHasStudentWork,
  type ScopePracticeFields,
} from "./boundedAssignment";
import type { PromptBuilderArtifact } from "./types";

export interface AssignmentSwitchProtection {
  hasDraft: boolean;
  hasSavedPrompt: boolean;
  savedPromptIsLegacy: boolean;
}

export function assignmentSwitchProtection(
  currentTaskId: string | null,
  nextTaskId: string,
  draft: PromptBuilderInputs | null,
  savedPrompt: PromptBuilderArtifact | null,
  scopeDraft: ScopePracticeFields | null = null
): AssignmentSwitchProtection | null {
  if (!currentTaskId || currentTaskId === nextTaskId) return null;
  const hasDraft =
    promptInputsHaveStudentWork(draft) || scopePracticeHasStudentWork(scopeDraft);
  const savedBinding = savedPrompt?.assignment_task_id;
  const hasSavedPrompt = Boolean(
    savedPrompt && (savedBinding == null || savedBinding === currentTaskId)
  );
  if (!hasDraft && !hasSavedPrompt) return null;
  return {
    hasDraft,
    hasSavedPrompt,
    savedPromptIsLegacy: hasSavedPrompt && savedBinding == null,
  };
}
