import { evidenceArtifactMode, isLinkedEvidenceArtifact } from "./evidence";
import { isLinkedReviewArtifact, linkedReviewAllowsVerification, targetFormFromReview } from "./review";
import {
  isLinkedVerificationArtifact,
  linkedVerificationRecorded,
  targetFormFromVerification,
} from "./verification";
import type {
  Evaluation,
  EntryProfile,
  GateCurrent,
  WorkflowPhaseState,
  WorkflowSections,
} from "./types";
import { WORKFLOW_JOURNEY } from "./workflowJourney";

export const GUIDED_NAVIGATION_REFRESH_EVENT = "codize:guided-navigation-refresh";

export const GUIDED_JOURNEY = WORKFLOW_JOURNEY;

export type GuidedStageId = (typeof GUIDED_JOURNEY)[number]["id"];
export type GuidedStageState =
  | "complete"
  | "continue"
  | "ready"
  | "needs_attention"
  | "later"
  | "unavailable";

export interface GuidedJourneyStage {
  id: GuidedStageId;
  label: string;
  href: string;
  state: GuidedStageState;
  stateLabel: "Complete" | "Continue" | "Ready" | "Needs attention" | "Later" | "Unavailable";
  reason: string;
}

export interface GuidedContinueAction {
  label: string;
  href: string | null;
  reason: string;
  stageId: GuidedStageId | null;
  unavailable: boolean;
}

export interface ProjectRecordItem {
  id: string;
  stageId: GuidedStageId;
  label: string;
  href: string;
  state: "complete" | "in_progress" | "needs_attention";
  stateLabel: "Complete" | "Saved" | "Needs update" | "Needs attention";
  description?: string;
}

export interface GuidedProjectNavigation {
  projectHome: { label: "Project Home"; href: "/app" };
  projectLabel: string;
  phaseLabel: string | null;
  continueAction: GuidedContinueAction;
  journey: GuidedJourneyStage[];
  projectRecord: ProjectRecordItem[];
  evaluation: Evaluation | null;
  workflow: WorkflowPhaseState | null;
}

export interface GuidedNavigationInput {
  evaluation: Evaluation | null;
  workflow: WorkflowPhaseState | null;
  gate: GateCurrent | null;
  projectLabel?: string | null;
  entryProfile?: EntryProfile | null;
}

const LABEL_BY_ID = new Map(GUIDED_JOURNEY.map((stage) => [stage.id, stage.label]));
const HREF_BY_ID = new Map(GUIDED_JOURNEY.map((stage) => [stage.id, stage.href]));

function action(
  stageId: GuidedStageId | null,
  label: string,
  reason: string,
  href: string | null = stageId ? HREF_BY_ID.get(stageId) ?? null : null
): GuidedContinueAction {
  return { label, reason, href, stageId, unavailable: href === null };
}

function stage(
  id: GuidedStageId,
  state: GuidedStageState,
  reason: string
): GuidedJourneyStage {
  const labels: Record<GuidedStageState, GuidedJourneyStage["stateLabel"]> = {
    complete: "Complete",
    continue: "Continue",
    ready: "Ready",
    needs_attention: "Needs attention",
    later: "Later",
    unavailable: "Unavailable",
  };
  return {
    id,
    label: LABEL_BY_ID.get(id) ?? id,
    href: HREF_BY_ID.get(id) ?? "/app",
    state,
    stateLabel: labels[state],
    reason,
  };
}

function laterJourney(reason = "Complete the earlier steps first."): GuidedJourneyStage[] {
  return GUIDED_JOURNEY.map((item) => stage(item.id, "later", reason));
}

function reviewIsComplete(sections: WorkflowSections): boolean {
  const review = sections.review_board;
  if (!review) return false;
  if (!isLinkedReviewArtifact(review)) return true;
  if (review.stale) return false;
  return linkedReviewAllowsVerification(review, targetFormFromReview(review));
}

function verificationIsComplete(sections: WorkflowSections): boolean {
  const verification = sections.verification;
  if (!verification) return false;
  if (!isLinkedVerificationArtifact(verification)) return true;
  if (verification.stale) return false;
  return (
    verification.verification_targets.length === 0 ||
    linkedVerificationRecorded(verification, targetFormFromVerification(verification))
  );
}

function evidenceIsComplete(sections: WorkflowSections): boolean {
  const evidence = sections.evidence;
  const mode = evidenceArtifactMode(evidence);
  if (mode === "none" || mode === "invalid_linked") return false;
  if (mode === "legacy") return true;
  if (!isLinkedEvidenceArtifact(evidence)) return false;
  return !evidence.stale && evidence.evidence_record_complete;
}

function recordItem(
  stageId: GuidedStageId,
  state: ProjectRecordItem["state"],
  stateLabel: ProjectRecordItem["stateLabel"],
  description?: string,
  suffix?: string,
  href?: string
): ProjectRecordItem {
  const baseLabel = LABEL_BY_ID.get(stageId) ?? stageId;
  return {
    id: `${stageId}${suffix ? `-${suffix}` : ""}`,
    stageId,
    label: suffix ? `${baseLabel} · ${suffix}` : baseLabel,
    href: href ?? HREF_BY_ID.get(stageId) ?? "/app",
    state,
    stateLabel,
    description,
  };
}

function buildRecord(
  evaluation: Evaluation,
  workflow: WorkflowPhaseState,
  gate: GateCurrent | null
): ProjectRecordItem[] {
  const { sections, change_map: map } = workflow;
  const record: ProjectRecordItem[] = [];
  if (sections.prompt_builder) record.push(recordItem("prompt", "complete", "Complete"));
  if (sections.implementation_import) record.push(recordItem("import", "complete", "Complete"));
  if (map) {
    record.push(
      map.stale
        ? recordItem(
            "change_map",
            "needs_attention",
            "Needs update",
            "Your implementation material changed. The saved map remains readable."
          )
        : map.status === "confirmed"
          ? recordItem("change_map", "complete", "Complete")
          : recordItem("change_map", "in_progress", "Saved")
    );
  }
  if (sections.review_board) {
    const review = sections.review_board;
    record.push(
      isLinkedReviewArtifact(review) && review.stale
        ? recordItem(
            "review",
            "needs_attention",
            "Needs update",
            "An upstream Change Map changed. The saved Review remains readable."
          )
        : reviewIsComplete(sections)
          ? recordItem("review", "complete", "Complete")
          : recordItem("review", "in_progress", "Saved")
    );
  }
  if (sections.verification) {
    const verification = sections.verification;
    record.push(
      isLinkedVerificationArtifact(verification) && verification.stale
        ? recordItem(
            "verification",
            "needs_attention",
            "Needs update",
            "The saved Review changed. These recorded results remain readable."
          )
        : verificationIsComplete(sections)
          ? recordItem("verification", "complete", "Complete")
          : recordItem("verification", "in_progress", "Saved")
    );
  }
  if (sections.evidence) {
    const evidence = sections.evidence;
    record.push(
      isLinkedEvidenceArtifact(evidence) && evidence.stale
        ? recordItem(
            "evidence",
            "needs_attention",
            "Needs update",
            "Saved Verification results changed. This Evidence remains readable."
          )
        : evidenceIsComplete(sections)
          ? recordItem("evidence", "complete", "Complete")
          : recordItem("evidence", "in_progress", "Saved")
    );
  }

  const currentPhase = evaluation.current_phase ?? workflow.phase;
  const failedAttempt = evaluation.recent_gate?.outcome === "failed";
  if (gate?.state === "in_progress") {
    record.push(recordItem("defense", "in_progress", "Saved"));
  } else if (gate?.state === "cooldown" || failedAttempt) {
    record.push(recordItem("defense", "needs_attention", "Needs attention"));
    record.push(
      recordItem(
        "report",
        "complete",
        "Complete",
        "Report from the saved Defense attempt.",
        `Phase ${currentPhase}`,
        `/app/report?phase=${currentPhase}`
      )
    );
  } else if (gate?.state === "passed" || evaluation.state === "complete") {
    record.push(recordItem("defense", "complete", "Complete"));
    record.push(
      recordItem(
        "report",
        "complete",
        "Complete",
        undefined,
        `Phase ${currentPhase}`,
        `/app/report?phase=${currentPhase}`
      )
    );
  }

  const completedPhases = evaluation.completed_phases ?? 0;
  if (completedPhases > 0 && evaluation.state !== "complete") {
    const suffix = `Phase ${completedPhases}`;
    record.push(
      recordItem(
        "report",
        "complete",
        "Complete",
        "Report from the most recently completed phase.",
        suffix,
        `/app/report?phase=${completedPhases}`
      )
    );
  }
  return record.filter(
    (item, index, all) => all.findIndex((candidate) => candidate.id === item.id) === index
  );
}

function preActiveModel(input: GuidedNavigationInput): GuidedProjectNavigation {
  const evaluation = input.evaluation;
  const profile = input.entryProfile;
  const continueAction = evaluation?.state === "not_started" && !profile
    ? action(
        null,
        "Find my starting point",
        "Answer a few short questions and get one recommended place to begin.",
        "/app/intake"
      )
    : evaluation?.state === "roadmap_needed"
      ? action(null, "Finish project setup", evaluation.next_action, "/app/intake")
      : action(
          null,
          profile?.completed ? "Continue project details" : "Continue project setup",
          evaluation?.next_action ?? "Set up your project first.",
          "/app/intake"
        );
  return {
    projectHome: { label: "Project Home", href: "/app" },
    projectLabel: input.projectLabel?.trim() || "Your project",
    phaseLabel: null,
    continueAction,
    journey: laterJourney("Finish project setup to open this stage."),
    projectRecord: [],
    evaluation,
    workflow: null,
  };
}

export function buildGuidedProjectNavigation(
  input: GuidedNavigationInput
): GuidedProjectNavigation {
  const { evaluation, workflow, gate } = input;
  if (
    !evaluation ||
    !workflow ||
    evaluation.state === "not_started" ||
    evaluation.state === "intake_needed" ||
    evaluation.state === "roadmap_needed"
  ) {
    return preActiveModel(input);
  }

  const { sections, change_map: map } = workflow;
  const journey = laterJourney();
  const set = (id: GuidedStageId, stateValue: GuidedStageState, reason: string) => {
    journey[GUIDED_JOURNEY.findIndex((item) => item.id === id)] = stage(id, stateValue, reason);
  };
  let continueAction: GuidedContinueAction;
  const hasWorkflowProgress =
    Object.values(sections).some((section) => section != null) || map != null;
  const entryStart =
    !hasWorkflowProgress &&
    workflow.phase === 1 &&
    (evaluation.completed_phases ?? 0) === 0 &&
    input.entryProfile?.completed
      ? input.entryProfile.recommended_start
      : null;
  const importFirst =
    !sections.prompt_builder &&
    (Boolean(sections.implementation_import) ||
      entryStart === "implementation_import" ||
      entryStart === "quick_start");

  if (!sections.prompt_builder && !importFirst) {
    set("prompt", "continue", "Save the prompt you will use for this phase.");
    continueAction = action("prompt", "Continue Prompt Builder", "Plan one clear ask for your AI tool.");
  } else {
    if (sections.prompt_builder) {
      set("prompt", "complete", "A prompt is saved for this phase.");
    } else {
      set(
        "prompt",
        "later",
        "This phase began from an existing AI change. Use Prompt Builder before your next change."
      );
    }
    if (!sections.implementation_import) {
      set("import", "continue", "Bring back the response, diff, changed files, or your notes.");
      continueAction = entryStart === "quick_start"
        ? action(
            "import",
            "Start the 80% Trap Quick Start",
            "Pause the patch loop, then bring back the latest AI change.",
            "/app?quick-start=1"
          )
        : action(
            "import",
            "Bring Back What Changed",
            "Record the saved output from your external AI tool."
          );
    } else {
      set("import", "complete", "Implementation material is saved for this phase.");
      if (!map) {
        set("change_map", "ready", "Your saved implementation material is ready to map.");
        continueAction = action("change_map", "Continue Change Map", "Create a draft of what appears to have changed.");
      } else if (map.stale) {
        set("change_map", "needs_attention", "Implementation material changed after this map was created.");
        continueAction = action("change_map", "Rebuild Change Map", "Use the latest saved implementation material.");
      } else if (map.status !== "confirmed") {
        set("change_map", "continue", "Review and confirm the saved Change Map draft.");
        continueAction = action("change_map", "Continue Change Map", "Correct the draft and preserve honest uncertainty.");
      } else {
        set("change_map", "complete", "The Change Map was reviewed and confirmed.");
        const review = sections.review_board;
        if (!review) {
          set("review", "ready", "The confirmed Change Map is ready for your decisions.");
          continueAction = action("review", "Continue Review", "Decide what to keep, revise, remove, test, or leave uncertain.");
        } else if (isLinkedReviewArtifact(review) && review.stale) {
          set("review", "needs_attention", "The Change Map changed after this Review was created.");
          continueAction = action("review", "Rebuild Review", "Rebuild from the current confirmed Change Map.");
        } else if (!reviewIsComplete(sections)) {
          set("review", "continue", "Some saved Review decisions are still pending.");
          continueAction = action("review", "Continue Review", "Record a decision for each Review item.");
        } else {
          set("review", "complete", "Review decisions are saved.");

          // Existing manual projects keep their established Evidence-first
          // continuation. This does not convert or add a lifecycle requirement.
          const legacyReview = !isLinkedReviewArtifact(review);
          if (legacyReview && !sections.evidence) {
            set("evidence", "ready", "This manual project can continue with its existing Evidence workflow.");
            continueAction = action("evidence", "Continue Evidence", "Save supporting material through the existing manual workflow.");
          } else {
            if (legacyReview && sections.evidence) {
              set("evidence", "complete", "Manual Evidence is saved.");
            }
            const verification = sections.verification;
            if (!verification) {
              set("verification", "ready", "Review is complete and Verification can begin.");
              continueAction = action("verification", "Continue Verification", "Perform checks and record what actually happened.");
            } else if (isLinkedVerificationArtifact(verification) && verification.stale) {
              set("verification", "needs_attention", "Review changed after these checks were created.");
              continueAction = action("verification", "Rebuild Verification", "Rebuild checks from the current saved Review.");
            } else if (!verificationIsComplete(sections)) {
              set("verification", "continue", "Some Verification results are not yet recorded.");
              continueAction = action("verification", "Continue Verification", "Perform each check and record the result.");
            } else {
              set("verification", "complete", "Verification results are recorded.");
              const evidence = sections.evidence;
              if (!evidence) {
                set("evidence", "ready", "Saved Verification results are ready for supporting Evidence.");
                continueAction = action("evidence", "Continue Evidence", "Choose performed checks and record available support.");
              } else if (isLinkedEvidenceArtifact(evidence) && evidence.stale) {
                set("evidence", "needs_attention", "Verification changed after this Evidence was created.");
                continueAction = action("evidence", "Rebuild Evidence", "Keep the old record readable and rebuild from current results.");
              } else if (!evidenceIsComplete(sections)) {
                set("evidence", "continue", "The saved Evidence record is not complete yet.");
                continueAction = action("evidence", "Continue Evidence", "Address each selected result with support or an unavailable reason.");
              } else {
                set("evidence", "complete", "The Evidence record is complete.");
                const tasksRemain =
                  evaluation.state === "in_progress" &&
                  (evaluation.incomplete_tasks?.length ?? 0) > 0;
                if (tasksRemain) {
                  set("defense", "later", "Finish the remaining saved phase tasks before starting Defense.");
                  continueAction = action(
                    null,
                    "Finish phase build tasks",
                    `${evaluation.incomplete_tasks?.length ?? 0} build task(s) remain before Project Defense.`,
                    "/app/phase"
                  );
                } else if (evaluation.state === "complete" || gate?.state === "passed") {
                  set("defense", "complete", "The final Project Defense is complete.");
                  set("report", "continue", "The saved Defense Report is available.");
                  const phase = evaluation.current_phase ?? workflow.phase;
                  continueAction = action(
                    "report",
                    "View Defense Report",
                    "Review the project record and its preserved uncertainty.",
                    `/app/report?phase=${phase}`
                  );
                } else if (gate?.state === "in_progress" || evaluation.recent_gate?.outcome === "in_progress") {
                  set("defense", "continue", "A saved Defense attempt is in progress.");
                  continueAction = action("defense", "Continue Project Defense", "Resume the saved question or answer.");
                } else if (gate?.state === "cooldown" || evaluation.state === "cooldown") {
                  const seconds = gate?.cooldown_seconds_remaining ?? evaluation.cooldown_seconds_remaining;
                  const minutes = seconds == null ? null : Math.max(1, Math.ceil(seconds / 60));
                  set("defense", "needs_attention", "A retry opens after the current cooldown.");
                  continueAction = action(
                    "defense",
                    "Project Defense cooldown",
                    minutes == null
                      ? "Review your work while the saved cooldown finishes."
                      : `Retry opens in about ${minutes} minute${minutes === 1 ? "" : "s"}.`,
                    null
                  );
                } else if (evaluation.recent_gate?.outcome === "failed") {
                  set("defense", "needs_attention", "The saved attempt needs another try.");
                  continueAction = action("defense", "Try Project Defense again", "Review the feedback, then begin another attempt.");
                } else {
                  set("defense", "ready", "Workflow records and phase tasks are ready for Defense.");
                  continueAction = action("defense", "Start Project Defense", "Explain the implementation in your own words.");
                }
              }
            }
          }
        }
      }
    }
  }

  // Continue stays on the earliest dependency, while Journey still exposes
  // every saved downstream record that needs attention. This makes multiple
  // stale artifacts globally visible without directing the student past the
  // first required repair.
  if (map?.stale) {
    set("change_map", "needs_attention", "Implementation material changed after this map was created.");
  }
  if (isLinkedReviewArtifact(sections.review_board) && sections.review_board.stale) {
    set("review", "needs_attention", "The Change Map changed after this Review was created.");
  }
  if (
    isLinkedVerificationArtifact(sections.verification) &&
    sections.verification.stale
  ) {
    set("verification", "needs_attention", "Review changed after these checks were created.");
  }
  if (isLinkedEvidenceArtifact(sections.evidence) && sections.evidence.stale) {
    set("evidence", "needs_attention", "Verification changed after this Evidence was created.");
  }

  return {
    projectHome: { label: "Project Home", href: "/app" },
    projectLabel: input.projectLabel?.trim() || evaluation.phase_title || "Your project",
    phaseLabel:
      evaluation.current_phase == null
        ? null
        : `Phase ${evaluation.current_phase}${evaluation.phase_title ? ` · ${evaluation.phase_title}` : ""}`,
    continueAction,
    journey,
    projectRecord: buildRecord(evaluation, workflow, gate),
    evaluation,
    workflow,
  };
}

export function routeIsActive(pathname: string, href: string): boolean {
  const path = href.split("?")[0];
  if (path === "/app" || path === "/app/phase") return pathname === path;
  return pathname === path || pathname.startsWith(`${path}/`);
}
