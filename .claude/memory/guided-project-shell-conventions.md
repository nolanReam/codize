# Guided Project Shell Conventions

> [!WARNING]
> **Current/legacy V1 product or lifecycle record.** Use this file only to understand or maintain the implemented V1 subsystem. It is not V2 product or architecture authority.

M16N is frontend-only. It changes navigation hierarchy, not workflow routes,
backend lifecycle, artifacts, providers, evaluator behavior, PASS/FAIL,
retries, cooldowns, Report truth, or database schema.

## One model

`frontend/lib/guidedProjectNavigation.ts` is the shared typed deterministic
model. `GuidedProjectNavigationProvider` loads existing server state from
evaluation, the current phase workflow view, current gate, and intake status.
Desktop sidebar, mobile drawer, global Continue, Project Home, compact Journey,
and Project Record consume that same model. Successful API
mutations emit one refresh event; GETs never do, so there is no request loop.

Never create a second lifecycle helper. `derivePhaseNextStep` remains only as
a compatibility wrapper over the shared model. Current route is a display
state (`aria-current="page"`), not workflow progress. Opening a completed deep
link never changes Continue.

## Hierarchy and routes

- Project Home is `/app`, always first and always available. “Cockpit” is no
  longer student-facing; the one-project selection behavior is unchanged.
- Continue is the only dominant global workflow action.
- Journey order is exactly Prompt Builder → Bring Back What Changed → Change
  Map → Review → Verification → Evidence → Project Defense → Defense Report.
- Completed Journey rows are compact non-links. Future rows are readable
  non-links labeled Later. Needs-attention rows use text plus restrained amber.
- Project Record is a native disclosure using the existing deep links. It
  contains only saved/current historical work, including prior-phase Reports.
  It is a project record, not proof or independent verification.
- Project Home is the sole orientation dashboard. It owns the current phase's
  plain-language purpose, one ordered AI-appropriate/student-owned task list,
  compact workflow position, collapsed roadmap, and compact Record access.

## Saved-state authority and priority

Prompt Builder and Import use their saved server artifacts. Change Map uses
stored status and stale. Linked Review uses saved target decisions; linked
Verification uses saved recorded results (result correctness is not a score);
linked Evidence completes only on `evidence_record_complete`. Defense uses the
exact evaluation/current-gate lifecycle, and Report availability follows a
saved failed or passed attempt. Unsaved drafts, optimistic component state,
route presence, browser history, and linked section presence do not advance
navigation.

Continue selects the earliest dependency needing work: stale Change Map,
Review, Verification, then Evidence before any downstream stage. Evidence
incomplete remains current. After Evidence completion, remaining saved build
tasks route to Project Home's `#current-work` section so Defense is never offered before backend
eligibility. Defense then distinguishes Start, Continue, Try again, cooldown
(non-action), and final View Defense Report. A failed attempt remains in the
record without being called complete.

## Compatibility and responsive behavior

Manual Review, Verification, Evidence, legacy attempts, prior projects, and
Report fallback keep their existing routes and persistence. Existing manual
Review keeps its established Evidence-first continuation; no conversion or new
mandatory handoff is introduced. Workflow capture stays exactly N/5 and only
the gate advances phases.

Desktop uses the existing sticky dark rail. At 840px and below the same model
opens in a modal drawer. Focus enters the drawer, Tab is trapped, Escape and
backdrop close it, and focus returns to the trigger. Loading preserves Project
Home and a stable shell; failure preserves Project Home/current content and
offers retry without guessed stage state. Future, complete, current, and stale
meaning always appears in text, not color alone; reduced-motion and current
focus styles remain global.

M18B.1 removes Phase Workspace from desktop and mobile navigation. The bare
`/app/phase` route remains only as a compatibility redirect to
`/app#current-phase`; workflow child routes under `/app/phase/*` are unchanged.
Before a roadmap exists, the shell shows only Project Home, setup Continue,
Help, and account controls. Once active, Journey and Project Record are compact
disclosures; the mobile pair shares an exclusive disclosure group. The closed
Menu button has no `aria-controls` relationship until the drawer exists.

## Exact M17 seam

M17 may add first-time entry, project-state diagnosis, starting-new/already-
building guidance, the 80% Trap Quick Start, patch-loop recovery entry,
Guided/Builder/Recovery entry, progressive beginner explanations, and adaptive
recommendations. It must feed/reuse this shared M16N model and shell. It must
not create a parallel sidebar or alternate lifecycle state machine.

Implemented M17 keeps this exact boundary. `GuidedProjectNavigationProvider`
loads the entry profile beside its existing evaluation/workflow/gate/intake
snapshot and passes it into `guidedProjectNavigation.ts`. A completed profile
may choose Prompt, Import, or the Quick Start presentation, but only while the
project is still at its untouched first phase. Real saved Import continues to
Change Map even when Prompt is absent; Prompt is labeled for the next change.
Any saved/stale downstream dependency uses the established M16N priority and
overrides entry history. Legacy missing/malformed profiles preserve the prior
shell and receive standard guidance. No second sidebar, lifecycle helper, or
workflow completion field exists.

M18A-R makes two authority rules explicit. The backend readiness blocker is the
final prerequisite authority before offering a new Defense attempt; the shell
must not reconstruct typed validity from raw section presence. Once a Defense
attempt exists, its lifecycle is the continuation authority: in-progress,
cooldown, retry, and completed attempts remain resumable/reportable even when
an upstream artifact later becomes stale. The stale record stays visibly
flagged, but it cannot redirect the primary Continue action away from the
existing Defense lifecycle.

## Exact M18B.2 seam

M18B.2 may add explicit selected phase-assignment/task state and bind Prompt
Builder to that selection. It must reuse Project Home's ordered current-work
list, the existing phase task ids/data, and the shared Continue lifecycle. It
must not restore Phase Workspace, create a second task recommendation model,
infer assignment selection from checkbox completion, or change roadmap/gate
authority. M18B.1 stores no selection and Prompt Builder remains unbound.
