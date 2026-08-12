# Forms, Feedback, and States

> V1-specific component names and workflow examples below are current implementation references only. For V2, apply the underlying feedback/accessibility principles within the canonical Exact UX and approved Figma composition.

## Reduce blank-page work without taking authorship

- **Principle:** Offer editable starters, examples, and choices while leaving the student in control.
- **Why:** Prompt Builder became the strongest pilot surface when it reduced interpretation work.
- **Use:** Intake, Prompt Builder, evidence kind selection, Review decisions, and verification results.
- **Do not use:** Do not silently prefill consequential claims, auto-select certainty, or make every student submit the same answer.
- **Anti-pattern:** Empty textarea plus a long paragraph explaining what to type.
- **Codize:** Use tap-to-fill chips where reuse is safe, realistic placeholders, native radios/checkboxes, and explicit optional labels. Preserve typed content on validation or network failure.
- **Source:** `[P1, P2; S2 01:03–03:29; A2, A5, A6]`

## Show timely, useful system status

- **Principle:** Acknowledge actions and expose enough state for the user to decide what to do next.
- **Why:** Feedback builds predictability, trust, and control.
- **Use:** Loading, generation, save, copy, initialization, confirmation, retry, and long-running operations.
- **Do not use:** Do not reveal internal mechanics the user cannot act on or invent progress stages.
- **Anti-pattern:** A button appears frozen; a save succeeds with no confirmation; a model call shows fictional percentages.
- **Codize:** Disable duplicate actions locally, use stable labels such as “Saving…” or “Preparing your Review…”, announce results, show saved timestamps where useful, and keep retryable input intact.
- **Source:** `[S3 00:06–02:08; A2–A6]`

## Design states as part of the feature

For each relevant state, define the visible truth and primary action:

| State | Show | Primary action |
|---|---|---|
| prerequisite | what is missing and why this surface is unavailable | go to the prerequisite |
| empty | what belongs here and the smallest useful start | create/start |
| loading | what operation is underway, without fake precision | wait; cancel only if supported |
| success/saved | what completed and what remains | continue or keep editing |
| error | safe cause or generic fallback; preserve work | retry or correct the field |
| disabled | reason and route to eligibility | satisfy prerequisite |
| incomplete | completed versus remaining, without judgment | continue current work |
| complete | what the completion means and does not mean | next workflow step |
| stale | old record remains readable; why it no longer matches | update/rebuild deliberately |
| retry/recovery | what stays preserved and what happens on retry | retry smallest failed step |

- **Principle:** Keep the action state-specific.
- **Why:** Generic states create dead ends or false confidence.
- **Do not use:** Do not call a saved draft verified, a confirmed Change Map correct, or a Review complete if server-saved decisions are still dirty.
- **Codize:** Reuse `Async`, `NotReady`, `SaveBar`, notices, workflow hooks, and typed helpers where their contracts fit.
- **Source:** `[P1, P2; S3; A2–A6]`

## Preserve work and make replacement explicit

- **Principle:** Keep unsaved work through navigation and preserve server records until a deliberate replacement succeeds.
- **Why:** Pilot users expected typed work to survive navigation.
- **Use:** Workflow forms, gate steps, intake edits, linked Review, Change Map, and retry flows.
- **Do not use:** Do not persist secret-looking text, cross user/phase/version boundaries, or merge incompatible drafts.
- **Anti-pattern:** Navigation silently discards work; entering edit mode mutates state; stale data is auto-regenerated.
- **Codize:** Reuse authenticated, phase/version-scoped draft helpers; clear drafts only after successful save/submit or explicit discard. Put destructive replacement behind an inline explanation and final explicit action.
- **Source:** `[P1; A2–A5]`

## Make errors recoverable and honest

- **Principle:** Put field errors near the field, preserve user input, and distinguish user correction from service retry.
- **Why:** Users need to know whether to edit, wait, or retry.
- **Use:** Validation, API failures, secret guards, stale conflicts, and model generation failures.
- **Do not use:** Do not echo secret-like input, expose 5xx internals, or use red for neutral waiting/cooldown.
- **Anti-pattern:** One generic error at page top for a specific field, or failure that clears the form.
- **Codize:** Show safe backend 4xx messages; genericize 5xx; use `aria-invalid` and `aria-describedby`; keep cooldown amber; reserve danger styling for errors and recorded failures.
- **Source:** `[S3; A2–A6]`

## Preserve uncertainty and provenance

- **Principle:** State who supplied information, what was observed, and what remains unverified.
- **Why:** Honest uncertainty is part of the learning workflow, not a defect to hide.
- **Use:** AI-drafted Change Maps, self-reported evidence, Review targets, verification results, Defense context, and reports.
- **Do not use:** Do not use green verified styling for “uncertain,” “needs inspection,” “skipped,” “n/a,” or a student claim.
- **Anti-pattern:** “Approved,” “proven,” or “verified” after a save or confirmation.
- **Codize:** Keep “appears to have changed,” “self-reported,” “needs testing,” “I’m not sure,” source labels, and current/stale binding visible where decisions depend on them.
- **Source:** `[A1, A3–A6]`
