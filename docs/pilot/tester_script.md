# Codize Tester Script

This is the script you hand to a tester (or read aloud). It's written for a high
school CS student — plain language, no setup steps. The facilitator handles all
the technical setup **before** the session using `demo_checklist.md`; the tester
just uses the browser.

> **Facilitator:** stand up the app first (`demo_checklist.md`), have the tester's
> pre-survey done (`pre_survey.md`), and keep `observation_notes_template.md` open.
> Use the product's words — **"Project Defense"**, **"defend what you built."**
> Never say "quiz" or "test." Let the tester drive; when they stall, note it
> *before* you help.

---

## For the tester — read this first

### What Codize is

Codize helps you actually **understand and defend the projects you build with
AI**. Lots of people use AI to get a project to *"it runs"* — but then can't
explain how it works or fix it when it breaks. That's the **80% trap**. Codize
walks you through building one piece of your project the right way and then has
you **defend it** in a short conversation about your own code.

### What you'll do

You'll take one project you're building (or want to build) with AI, go through
**one phase** of it in Codize, and end by generating a **Project Defense Report**
you could show a teacher or a hackathon judge.

### How long it takes

About **30–45 minutes**.

### What you should NOT worry about

- **There are no wrong answers.** We're testing the tool, not you.
- You won't break anything. Click around.
- If something is confusing, **say so out loud** — that's exactly what helps us.
- You don't need a "finished" or impressive project. Something small and real is
  perfect.
- Codize does **not** run or grade your actual code. It won't see your files
  unless you tell it about them.

### Think out loud

Before you click something, say what you *expect* to happen. When something
surprises you, say that too.

---

## The walkthrough

Pick **one real project** you've built or want to build with an AI tool. You'll
use it the whole way through.

**1. Landing page.** Look at the first page. In your own words, tell the
facilitator: *what do you think Codize is for?*

**2. Sign up / log in.** The facilitator will give you a test login. Sign in.

**3. Intake (5 questions).** Codize asks you five short questions about your
project — starting with *"What problem do you want to solve, and who does solving
it help?"* Answer honestly about your real project. (You can't skip the first
one — that's on purpose.)

**4. Your roadmap appears.** Codize turns your answers into a step-by-step
roadmap of phases for your project. Read the current (first) phase. *Does it feel
like it fits your project?*

**5. Open your current phase.** This is your workspace for one phase — the Build
Loop: **Plan → Prompt → Generate → Review → Verify → Explain → Commit.**

**6. Prompt Builder.** Use the Prompt Builder to create a prompt for the thing
you're building in this phase. This is the "Prompt" step — Codize helps you write
a *better* prompt than you might on your own.

**7. Go to your own AI tool.** Take that prompt to the AI coding tool you
normally use (ChatGPT, Claude, Cursor, Copilot, Replit — whatever you like) and
generate or change some code. Codize doesn't do this for you on purpose — you use
your own tool.

**8. Come back to Codize.**

**9. Review Board.** Write down what the AI actually changed — the "Review" step.
What files/functions changed? What did it do that you asked for, and anything you
*didn't* ask for?

**10. Evidence Panel.** Add evidence of what you did — a link, a commit hash, or
a short note. (Codize doesn't check your code for you; you're recording what you
did.)

**11. Verification Lab.** Go through the verification checks — the step people
usually skip. Mark what you actually verified. **Be honest** — only check what
you really did.

**12. Project Defense (the gate).** When the phase is ready, start your Project
Defense. Codize will:
- ask you to **name one concrete part of your own code** (your "anchor"),
- ask you **three questions** about how *your* implementation works,
- then tell you whether you **passed**.

Answer in your own words about your own project. Generic textbook answers won't
pass — it's checking whether you understand *your* code.
*(If you don't pass, there's a 30-minute wait before you can retry — that's
normal, not a lockout. For today you probably won't wait it out.)*

**13. Project Defense Report.** Open your report. It pulls together your project,
what you built this phase, and your defense.

**14. Copy / export the report.** Copy or download it as Markdown. Imagine
showing it to a teacher or judge — *would it hold up?*

**15. Post-survey.** The facilitator will give you a few quick questions
(`post_survey.md`).

---

## Quick debrief (facilitator asks, ~2 min)

- What was the single most confusing moment?
- Did the Project Defense make you think about your project differently?
- Would you use this on your next AI project? Why or why not?

---

## Facilitator: things that are expected (don't treat as bugs)

- The roadmap may come back **personalized** or as a **standard template
  version** — both are fine.
- Roadmap and gate questions are **live AI calls** — a short wait or a one-tap
  retry is normal.
- A gate fail triggers a **30-minute cooldown** — intended.
- Verification is **self-reported**; Codize doesn't run the tester's code.
- **Scores and internal reasoning are hidden** by design — if a tester wants to
  "see their score," note the reaction; it isn't a bug.
- Out of scope (don't demo/promise): browser IDE, GitHub OAuth, community,
  tool marketplace, analytics dashboard, hosted runtime, gamification.

Anything else that breaks, blocks, or errors → `bug_report_template.md`.
