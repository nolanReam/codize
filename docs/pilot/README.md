# Codize Pilot Kit

Everything needed to run a small, structured pilot of **Codize** — the AI coding
workflow trainer / Project Defense Workflow — with **3–10 testers** drawn from
high-school CS, AP CSA, hackathon, or general AI-coding-tool users.

Codize teaches student builders to escape the "80% trap": to use AI tools
deliberately, verify what the AI generated, and be able to **defend the project
they shipped**. The pilot's job is to find out whether the current MVP actually
produces that outcome — and where it confuses, blocks, or bores a real student.

## What's in this kit

| File | Use it to… |
|---|---|
| `pilot_plan.md` | Understand the whole pilot: goals, audience, logistics, schedule, roles, consent, and privacy rules. **Read this first.** |
| `tester_script.md` | Run one tester session end-to-end: environment setup, the exact walkthrough, and what "good" looks like at each step. Doubles as the facilitator runbook. |
| `pre_survey.md` | Capture each tester's background **before** they start (baseline). |
| `post_survey.md` | Capture reactions, confidence change, and NPS **after** they finish. |
| `observation_notes_template.md` | Facilitator's live notes during a session (one copy per tester). |
| `bug_report_template.md` | Log a single defect with enough detail to reproduce it. |
| `demo_checklist.md` | Pre-flight the environment and give a clean live demo without surprises. |
| `results_summary_template.md` | Aggregate findings into a decision-ready summary **after** the pilot. Ships empty — fill it with real data only. |

## Ground rules baked into this kit

- **No product code changes are part of running the pilot.** This kit is docs only.
- **Do not collect sensitive personal data.** Use pseudonymous participant IDs
  (P1, P2, …). No full legal names, addresses, government IDs, health data, or
  precise location in any survey or note. See the privacy section of
  `pilot_plan.md`.
- **Many testers may be minors.** Obtain parental/guardian consent before a
  session with anyone under 18 (see `pilot_plan.md`).
- **Never invent results.** `results_summary_template.md` and the survey files
  are empty templates; they get filled only with data you actually collected.
- **Test accounts are throwaway.** Create login-capable users via SQL, use a
  non-personal placeholder email, and delete them after the pilot.

## Suggested order of use

1. Read `pilot_plan.md`; recruit 3–10 testers; secure consent.
2. Pre-flight with `demo_checklist.md` on the exact machine you'll use.
3. Per tester: `pre_survey.md` → run `tester_script.md` while filling
   `observation_notes_template.md` → `post_survey.md`. File any
   `bug_report_template.md` as issues surface.
4. After all sessions: aggregate into `results_summary_template.md` and decide
   what to fix before a wider pilot.
