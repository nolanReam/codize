# Pilot UX lessons (first real tester, Ethan — 2026-07-06/07)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

Scores: landing clarity 4/5, intake 4/5, **Prompt Builder 5/5**, overall
usefulness 3/5, would-use-again "maybe". Most useful: Prompt Builder. Most
confusing: not knowing what he was going to do before starting. Felt
unnecessary: Evidence Panel. Hardest: the gate felt "too strict". Prompt
Builder itself: useful but too much reading. Dashboard: "a little
overwhelming".

**The root problem was text density, not missing guidance.** M13E.1/E.2
added help as always-visible rails/hints/paragraphs; the tester experienced
that as homework and a manual. The M13E.3 rule (apply to ALL future
protected-app work):

- **Progressive disclosure**: max 1–2 explanatory sentences visible at the
  top of a screen; everything else behind `details.help` / collapsed
  `GuideCard` (which is a `<details>` since M13E.3 — don't revert it to an
  always-open card).
- **One primary action per screen**, visually accented
  (`borderColor: var(--accent)` card + one `btn primary`).
- Prefer chips/labels/placeholders over hint paragraphs.
- Don't repeat the same workflow explanation on multiple pages.

**Product direction signal**: guided prompting is the core value moment —
keep the Prompt Builder the hero and route attention to it. Evidence/
Verification/Gate must read as *lightweight proof and coaching*, never as
forms/rubrics/exams: "one small piece is enough", skipped/n-a are fine,
failing the gate = "review and retry", the strictness stays INTERNAL
(evaluator untouched) while the copy stays warm. The 8-line `LoopOverview`
component answers "what am I about to do" — reuse it instead of writing new
onboarding walls.
