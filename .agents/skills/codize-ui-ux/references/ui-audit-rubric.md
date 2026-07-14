# UI Audit Rubric

Audit a real journey and its states. Render in a browser when available; do not grade a screenshot alone.

## Finding classes

1. **Confirmed defect** — reproducible task, usability, accessibility, responsive, honesty, or contract failure.
2. **Likely improvement** — evidence-backed friction with some contextual uncertainty.
3. **Subjective preference** — aesthetic direction without demonstrated user/task harm.

Within confirmed defects, prioritize:

- **P0:** blocks the core journey, exposes sensitive data, or creates a materially false claim;
- **P1:** prevents or seriously misdirects common task completion or accessibility;
- **P2:** meaningful friction, ambiguity, recovery, or responsive problem;
- **P3:** localized polish or consistency issue.

## Audit sequence

1. Name the user, goal, entry point, end state, and key decision.
2. Walk the happy path and prerequisite, empty, loading, error, retry, saved, incomplete, complete, disabled, and stale states that apply.
3. Verify navigation and progress against real Codize contracts.
4. Test keyboard, focus, announcements, semantics, reduced motion, and approximately 390px/tablet/1080p/1920px.
5. Test long user content, paths, errors, and slow/failing operations.
6. Compare with existing components/tokens and adjacent pages.
7. Classify findings; apply the smallest-change test.
8. Re-run the journey after fixes and run relevant frontend checks.

## Rubric

### Goal and action

- Can the user state what this page is for after the title and first one or two sentences?
- Is the current workflow state visible?
- Is there one obvious primary action for the state?
- Are secondary/destructive actions visually secondary and deliberate?
- Does completion lead to the correct next workflow step?

### Information and visual hierarchy

- Does the scan order match goal → state → action → supporting detail?
- Are related items grouped without box overload?
- Are type, spacing, alignment, contrast, and color drawn from the current system?
- Are badges/pills limited to real status?
- Does wide space carry useful context without overlong lines or dead canvas?

### Cognitive load and disclosure

- Is visible explanatory copy concise?
- Are optional guidance and advanced/source details disclosed contextually?
- Are required warnings, state, and primary actions still visible?
- Are examples/chips/placeholders reducing blank-page friction without taking authorship?
- Is repeated workflow explanation reused or removed?

### Status, feedback, and recovery

- Does every action acknowledge receipt and eventual outcome?
- Are loading labels stable and free of fake progress?
- Does save success identify what was saved?
- Are errors safe, specific when possible, and recoverable without losing work?
- Are prerequisite, empty, disabled, incomplete, complete, and stale states actionable?
- Are replacement and destructive consequences explicit before mutation?

### Trust and product truth

- Are AI drafts, student claims, student decisions, observed results, and verified facts distinct?
- Is uncertainty preserved rather than forced into success/failure?
- Are build tasks, five artifacts, Change Map, Review progress, gate state, and phase advancement separate?
- Are hidden scores, thresholds, prompts, evaluator reasoning, secrets, and unsupported claims absent?
- Does the copy remain direct and non-shaming?

### Accessibility and responsive behavior

- Are controls semantic, named, keyboard-operable, and visibly focused?
- Are errors and status changes announced appropriately?
- Is state conveyed with words/structure, not color alone?
- Does content work with reduced motion, touch, zoom, long text, and narrow screens?
- Is there no horizontal overflow, clipping, unreachable sticky content, or hover-only information?

### Polish and consistency

- Does the surface preserve the dark/violet engineering-cockpit identity?
- Are motion and visual effects purposeful and restrained?
- Are new patterns necessary, reusable, and compatible with adjacent pages?
- Does polish improve comprehension rather than optimize only for a screenshot?

## Output format

For each finding, report:

```text
[Class/Priority] Short title
Evidence: route, state, viewport, interaction, or code location
User impact: what becomes blocked, ambiguous, misleading, or harder
Category: functional | visual | subjective
Smallest fix: scoped recommendation
Verify: exact journey, viewport, keyboard/state check, and relevant automated checks
```

Then summarize:

- confirmed defects first;
- likely improvements second;
- subjective preferences last;
- strengths worth preserving;
- out-of-scope observations separately.
