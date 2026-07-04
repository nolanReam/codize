# Codize Pilot — Results Summary (TEMPLATE)

Fill this **after** all sessions, from real collected data only. Every value is a
placeholder — **do not invent numbers.** Leave a cell blank or "n/a" if you
didn't measure it. Keep everything de-identified (P# only).

---

## 1. Pilot overview

- **Pilot dates:** ____________ → ____________
- **Facilitator(s):** ____________
- **Build under test (commit):** ____________
- **Number of testers:** ____  (target 3–10)

## 2. Tester profiles (non-identifying)

| P# | Profile (e.g. "AP CSA, uses ChatGPT weekly") | Usual AI tool | Project type attempted |
|----|----------------------------------------------|---------------|------------------------|
| P1 | | | |
| P2 | | | |
| P3 | | | |
| …  | | | |

## 3. Completion funnel (count of testers who reached each stage)

| Stage | Count | / N |
|---|:---:|:---:|
| Completed intake | | |
| Got a roadmap (active project) | | |
| **Generated a prompt** (Prompt Builder) | | |
| **Completed the Review Board** | | |
| **Submitted evidence** (Evidence Panel) | | |
| **Completed verification** (Verification Lab) | | |
| **Attempted** the Project Defense (gate) | | |
| **Passed** the Project Defense | | |
| **Exported** the Project Defense Report | | |
| Completed the whole flow **unaided** | | |

- **Overall completion rate (finished the core task):** ___ / ___ = ___%

## 4. Confidence shift (pre → post, mean of 1–5)

Report mean before/after and the delta. The **explain/defend** row is the headline.

| Statement | Pre | Post | Δ |
|---|:---:|:---:|:---:|
| Confident writing prompts for AI coding help | | | |
| Confident reviewing AI-generated code | | | |
| I verify/test AI code before moving on | | | |
| I understand how my AI-built project works | | | |
| **Could explain/defend my project right now** | | | |
| I know which parts I don't fully understand | | | |

## 5. Did Codize help the Build Loop? (post A, mean of 1–5)

| Item | Mean |
|---|:---:|
| Helped write a better prompt | |
| Helped notice something AI changed | |
| Made me verify something I'd normally skip | |
| Report felt useful | |

- **Gate sentiment (post B5 tally):** Useful ___ · Fair ___ · Annoying ___ ·
  Confusing ___ · Too easy ___ · Too hard ___
- **"Use again" (post 19):** Yes ___ · Maybe ___ · No ___
- **Mean "use on next project" (post 21, 0–10):** ___

## 6. Top 3 useful moments

1.
2.
3.

## 7. Top 3 friction points

1.
2.
3.

## 8. Bugs found

| Bug ID | Surface | Severity | Blocked completion? | One-line |
|---|---|---|:---:|---|
| BUG-01 | | | | |
| | | | | |

- Blockers: ___  Major: ___  Minor: ___

## 9. Changes to make next (prioritized; blocking/major first)

1.
2.
3.

## 10. Honest conclusion

One paragraph. What did the pilot actually show — and what did it **not** show?
Small pilots find usability breaks and directional signal, not statistically
significant effects. Say so.

_______________________________________________

---

## 11. Evidence phrasing — for a résumé / college app (use honestly)

You may summarize the pilot as evidence, but **only with real numbers, and
without overclaiming.** A small pilot is a small pilot: report N, report exactly
what you measured, and never imply statistical significance, causation beyond
what you observed, or a larger study than you ran.

**Sample sentence structure (fill with real values):**

> "In an early pilot with **X** student builders, **Y** completed a verification
> step they said they normally skip, and average self-reported confidence in
> explaining an AI-assisted project changed from **A/5** to **B/5**."

**Do NOT write things like:**

- "Proven to improve learning outcomes." (A pilot proves nothing at this scale.)
- "Students learn X% better with Codize." (No control group, no such measure.)
- "Everyone loved it." (Report the spread, including the negatives.)
- Any number you didn't actually collect, or a tester count larger than N.

**Guardrail:** if a sentence would be false when a skeptical teacher asked
"how exactly did you measure that?", cut it.

## 12. Housekeeping done

- [ ] Test users deleted (SQL CLEANUP).
- [ ] Any name↔P# mapping deleted (kept outside the repo).
- [ ] Bugs filed in the tracker.
- [ ] No sensitive personal data stored in this summary or the repo.
