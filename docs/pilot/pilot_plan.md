# Codize Pilot Plan

The plan for a small, structured usability pilot of the Codize MVP. Read this
before scheduling any sessions.

## 1. Why we're piloting

Codize claims to help student builders escape the **80% trap** — where AI gets
you a project that *runs* but that you can't actually explain, verify, or defend.
The MVP walks a student through the **Codize Build Loop**:

> **Plan → Prompt → Generate → Review → Verify → Explain → Commit/Reflect**

…and ends each phase with a **Project Defense** (the Interrogation Gate): a
short, live, implementation-specific conversation the student has to pass by
reasoning about their *own* code, not textbook knowledge.

The pilot exists to answer, with real users:

1. Can users **understand what Codize is for**?
2. Can users **complete the core workflow without help**?
3. Does Codize help users **write better AI prompts**?
4. Does Codize help users **review what the AI changed**?
5. Does Codize make users **complete verification steps they normally skip**?
6. Does Codize make users feel **more able to defend/explain their project**?
7. Where does the app feel **confusing, slow, annoying, or unnecessary**?

Confidence movement is measured by the pre→post surveys (same six statements);
the headline is the "I could explain/defend my project" row.

## 2. What is NOT being tested

- Not a performance/load test, not a security pentest, not a marketing test.
- Not the out-of-scope surfaces (they don't exist in the MVP): browser IDE,
  GitHub OAuth, AI news, community/social, tool marketplace, analytics
  dashboard, hosted coding runtime, gamification.
- Not evidence-aware gating — the Project Defense uses the student's reasoning,
  not their uploaded evidence, by design.

## 3. Audience & recruitment

**Target testers (3–10 total)** — people who already code a little *with* AI:

- AP CSA students
- other high-school CS students
- hackathon friends
- older TheCoderSchool students (if allowed)
- Spark Code volunteers / instructors
- peers who have used Claude Code, Cursor, Replit, ChatGPT, or Copilot for coding

**Not** for this first pilot: elementary / Scratch-level students — the flow
assumes the tester has built or is building a real code project with AI.

Aim for a spread of experience: a couple who barely understand their AI-built
code, a couple who are more confident. That contrast is where the 80%-trap
insight shows up.

**Recruitment channels:** a CS teacher's class, a hackathon group chat, a coding
club, coworkers/volunteers. Keep it to people you can support live (in person or
screen-share).

**Group size rationale:** 3 testers surfaces the biggest usability breakages;
5–8 is the sweet spot for this kit; beyond ~10 you're re-confirming, not
learning. Start small, fix the obvious, then run the rest.

## 3a. The one core task (what the whole pilot is built around)

Frame every session around a single task:

> **Build or continue one AI-assisted project phase using Codize, then generate a
> Project Defense Report.**

Testers should use a **real project of their own** — something small is fine — in
one of the three archetypes Codize supports (an AI-powered app, a REST API
backend, or a full-stack web app). Discourage a brand-new blank idea they have no
intention of building; the defense lands harder on code they actually wrote.

**Success is NOT "the tester liked the app."** Success is whether Codize helped
the tester:

- create a **better prompt** than they'd have written alone,
- **identify what the AI changed**,
- **verify something they normally would have skipped**,
- **explain their project more clearly** (pre→post confidence),
- and produce a **useful Project Defense Report**.

A tester can enjoy the app and still fail every one of those — measure the
outcomes, not the vibe.

## 4. Consent & privacy (mandatory)

- **Minors:** Most of this audience is under 18. Get **parental/guardian
  consent** before the session (a short written/email OK is fine). Do not run a
  session with a minor without it.
- **Pseudonymous only:** Refer to every tester as **P1, P2, …** in all notes,
  surveys, bug reports, and the results summary. Keep any name↔ID mapping (if you
  even need one) **out of this repo** and delete it after the pilot.
- **Collect only what the surveys ask.** Do **not** collect: full legal names,
  home address, phone number, email used outside the throwaway test account,
  government IDs, date of birth, health data, precise geolocation, photos of the
  tester, or anything a school would consider a student record.
- **Recording:** Only record audio/screen with explicit consent (and
  parent/guardian consent for minors). If in doubt, take written notes instead.
- **Test accounts are disposable:** created via SQL with a placeholder email,
  used only for the pilot, and **deleted afterward** (see `tester_script.md`).
- Data lives in facilitator notes and the survey/summary docs only. There is no
  requirement to persist tester data anywhere beyond aggregated, de-identified
  findings.

## 4a. What we collect vs. what testers bring

**What data we collect** (all de-identified, P# only): pre/post survey answers
(1–5 scales + short open text), the completion-funnel counts, facilitator
observation notes, and bug reports. That's it — no analytics, no tracking, no
survey backend, nothing that identifies a tester.

**What a tester needs before starting:** a **real project** they've built or want
to build with AI (something small is fine), access to **their usual AI coding
tool** (ChatGPT / Claude / Cursor / Copilot / Replit), a browser, and ~40 minutes.
They install **nothing** — the facilitator runs Codize.

## 5. Logistics

- **Format:** 1:1, in person or over screen-share. One facilitator per tester.
- **Duration:** ~30–45 min per tester (5 pre-survey, 20–30 walkthrough, 5–10
  post-survey + debrief).
- **Environment:** the facilitator runs Codize locally (backend + frontend) on
  one trusted machine. Testers drive that machine or screen-share — they do
  **not** need to install anything. See `demo_checklist.md` and `tester_script.md`.
- **Materials per session:** this repo's pilot docs, a filled `pre_survey.md`, a
  blank `observation_notes_template.md`, and a way to file bugs
  (`bug_report_template.md` → your issue tracker or a notes file).

## 6. Roles

- **Facilitator** — runs the environment, reads the script, stays hands-off while
  the tester works, prompts think-aloud, does not coach past a stall unless the
  tester is fully blocked (note the stall first).
- **Note-taker** (can be the same person for small pilots) — fills the
  observation template live.

## 7. Schedule (suggested)

| Day | Activity |
|---|---|
| −3 to −1 | Recruit; secure consent; pre-flight `demo_checklist.md`; create test-user template. |
| Day 1 | Run first 2–3 sessions. Triage bugs the same day. |
| Day 1 eve | Fix only **blocking** issues (or note them); do not expand scope. |
| Day 2 | Run remaining sessions. |
| Day 3 | Aggregate into `results_summary_template.md`; delete test accounts + any name map. |

## 8. Success & failure criteria (how we'll read the results)

Signals to weigh in the summary, not hard gates:

**Success signals**
- Most testers reach a completed Project Defense **unaided** and export a report.
- Post-survey "I could explain/defend my project" **rises** vs. pre.
- Testers used the **generated prompt**, could **name what the AI changed**, and
  **completed a verification step** they said they'd normally skip.
- Testers describe the Defense as making them think about **their own** code.

**Failure signals**
- Testers can't get through the flow without the facilitator driving.
- Comprehension of "what is Codize" is shaky at landing/intake.
- The Defense feels like a **gameable quiz**, or testers pass with generic
  answers.
- The Prompt Builder / Review / Verify steps feel like busywork they skip.
- Blocking bugs, or confidence doesn't move.

**Reading it:** 🟢 mostly success signals · 🟡 finish only with help / shaky
comprehension · 🔴 can't complete / core promise doesn't land.

## 8a. Summarizing results honestly

Aggregate into `results_summary_template.md`. Rules: report **N and real
numbers only**; report the **spread**, including negatives; a 3–10 person pilot
shows usability breaks and direction, **not** proof of learning outcomes. The
template's §11 gives an honest résumé/college-app sentence structure plus an
explicit overclaim guardrail — use it. **Never invent results.**

## 9. Out-of-scope reminders for the facilitator

Don't promise or demo features that aren't in the MVP (§2). If a tester asks for
them, note it as a feature request in observation notes — it's useful signal, not
a bug.
