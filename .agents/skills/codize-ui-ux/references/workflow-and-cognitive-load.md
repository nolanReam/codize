# Workflow and Cognitive Load

## Orient before asking for work

- **Principle:** Show where the student is, what just happened, and the one next action before secondary detail.
- **Why:** Pilot users were unsure what they would do before starting and did not know where to look first.
- **Use:** Cockpit, Phase Workspace, Build Loop pages, prerequisites, completion states, and recovery.
- **Do not use:** Do not replace useful persistent state with a generic “continue” button.
- **Anti-pattern:** A page opens with several equal cards and paragraphs but no clear state/action.
- **Codize:** Preserve the Cockpit's “Do this next,” Phase Workspace's “Next step,” current phase, Build Loop state, and separate build-task/workflow progress.
- **Source:** `[P1, P2; S3 00:06–01:36; A1, A2, A6]`

## Reduce simultaneous decisions

- **Principle:** Present controls relevant to the current task and defer optional or advanced choices.
- **Why:** Too many visible choices make new users inspect everything.
- **Use:** Multi-step forms, secondary guidance, source detail, technical evidence types, and destructive options.
- **Do not use:** Never hide the primary action, required warning, current system state, or the consequence of a decision.
- **Anti-pattern:** Always-open guidance rails, all evidence types visible, or destructive replacement beside the main action.
- **Codize:** Keep visible page explanation to roughly one or two sentences; use collapsed `GuideCard`/`details.help`; keep “More options” secondary; use starter chips and placeholders instead of instruction walls.
- **Source:** `[P1, P2; S1 00:24–04:47; S2 00:17–04:57; A2, A6]`

## Keep the Build Loop truthful

- **Principle:** Communicate the shared Goal → Plan → Prompt → external AI tool → Bring Back → Change Map → Review → Verification → Evidence → Project Defense → Learning Progress/Report relationship without inventing progress.
- **Why:** Users confused build-task progress with workflow progress.
- **Use:** Navigation, Cockpit, Phase Workspace, handoffs, and completion copy.
- **Do not use:** Do not merge build tasks, saved workflow artifacts, Change Map status, Review-target progress, suggested checks, performed checks, evidence, gate state, or roadmap phase advancement.
- **Anti-pattern:** “Everything complete” because a form was saved, 6/5 progress, or a checked task advancing the phase.
- **Codize:** Generate happens in the student's external tool. Preserve each implemented progress contract and its provenance; suggested checks are not performed checks, recorded results are not independent verification, and only the gate advances a phase.
- **Source:** `[P1; A1–A7]`

## Guide navigation from state

- **Principle:** Keep Project Home available, make the current actionable step dominant, show the journey for orientation, and route completed work through a secondary project record.
- **Why:** Equal module navigation makes the student reconstruct prerequisite and workflow logic.
- **Use:** Shell navigation, Project Home, Continue actions, direct-route prerequisites, completed work, and stale downstream records.
- **Do not use:** Do not create a rigid wizard that blocks safe backward viewing or rely on hidden links as integrity enforcement.
- **Anti-pattern:** Every workflow module is a permanent equal-priority tab.
- **Codize:** Future stages remain visible but unavailable with a reason. Upstream edits warn about downstream staleness; stale records remain readable and are never silently rewritten.
- **Source:** `[A1, A7]`

## Support prevention and recovery

- **Principle:** Guide deliberate work before generation and provide a calm path back after stale, failed, incomplete, or patch-loop states.
- **Why:** Codize must help students avoid losing control and recover when they already have.
- **Use:** Prompt guardrails, Bring Back, Change Map, Review, Verification, stale states, gate retry, and drafts.
- **Do not use:** Do not shame, dead-end, or erase the prior record to make recovery look clean.
- **Anti-pattern:** “Start over” without explaining what is replaced, or failure copy that reads as punishment.
- **Codize:** Use direct warm copy: review and retry, inspect what changed, regenerate deliberately, preserve readable stale snapshots, and explain replacement consequences before mutation.
- **Source:** `[A1; P2; A3–A5]`

## Let content determine layout

- **Principle:** Decide what must be scanned, compared, edited, or referenced before styling the container.
- **Why:** Layout without content intent creates polished but unhelpful screens.
- **Use:** Any new page, card, list, or dashboard.
- **Do not use:** Do not assume short ideal text or fixed row heights for user-provided paths, evidence, errors, or explanations.
- **Anti-pattern:** Designing around perfect demo content, then clipping real content or breaking responsive layouts.
- **Codize:** Test long file paths, code-shaped content, multi-line student explanations, API errors, stale banners, and no-data states.
- **Source:** `[S5 00:25–03:30; A3–A6]`

## Keep help contextual

- **Principle:** Put the smallest useful explanation next to the decision it supports.
- **Why:** The pilot root cause was text density, not missing guidance.
- **Use:** Field hints, examples, uncertainty language, definitions, and preparation tips.
- **Do not use:** Do not hide load-bearing instructions only inside a disclosure.
- **Anti-pattern:** Repeating the same Build Loop explanation on every page.
- **Codize:** Reuse `LoopOverview`, `GuideCard`, labels, placeholders, and starter chips. Keep the Prompt Builder as the first-value hero; make Evidence, Verification, and Defense feel lightweight and coach-like.
- **Source:** `[P1, P2; S2 00:38–01:03; A2, A6]`
