# Codize — Demo Script

> [!WARNING]
> **Historical V1 demo script.** Do not present its workflow or Defense framing as Codize V2.

A short, natural script for showing Codize to a mentor, a tester, or a camera.
Target length **~4–6 minutes**. Talk like a builder, not a salesperson — show the
product doing the thing, don't oversell.

**Before you start:** run `pre_pilot_smoke_checklist.md`, be logged out on the
landing page, and have a real (small) project in mind to use for intake. Use the
product's words — **"Project Defense," "defend what you built"** — never "quiz."

---

## 0. The hook (spoken, ~20s) — the 80% Trap

> "If you've built something with AI, you know this feeling: it *works*, but you
> couldn't really explain how, and the second it breaks you're stuck asking the
> AI to patch it over and over. AI gets you to about 80% — and the last 20%,
> actually understanding and being able to defend your own project, is where
> people get stuck. That's the gap Codize is built for."

## 1. The promise (spoken, ~15s)

> "Codize walks you through building one piece of your project the right way —
> plan, prompt, generate, review, verify, explain — and then it makes you
> **defend it**: a short conversation about your *own* code that you can't fake
> with textbook answers."

## 2. Landing page (~20s)

Show the landing page. Let the 80% Trap framing land — read one line of it aloud.

> "This is the pitch in one screen. Let me actually go through it."

## 3. Intake (~30s)

Sign in; start intake.

> "It starts by asking what I'm building and who it helps — five quick questions,
> no dashboard, no setup. The first one is always 'what problem are you solving,
> and who does it help.'"

Answer honestly about your real project; complete the five.

## 4. Cockpit (~20s)

> "From my answers it figures out what kind of project this is and builds a
> roadmap — real phases, in order, with the security steps baked in from phase
> one, not bolted on later."

Point at the current phase / mission.

## 5. Phase workflow (~20s)

Open the current phase.

> "Each phase is a workspace for the Build Loop — plan, prompt, generate, review,
> verify, explain, commit. It's an engineering cockpit, not a checklist app."

## 6. Prompt Builder (~30s)

> "Instead of me winging a prompt, Codize helps me write a *good* one for exactly
> this step."

Build a prompt; note that you'd take it to your own AI tool (ChatGPT/Claude/
Cursor) — Codize deliberately doesn't generate the code for you.

## 7. Review / Evidence / Verification (~30s)

> "When I come back, I record what the AI actually changed, drop in evidence — a
> link or a commit — and go through the verification steps people normally skip.
> It's honest: it's *my* self-report, and it shows what I didn't do."

Fill one item in each; save.

## 8. Project Defense — the gate (the centerpiece, ~60–90s)

> "Now the important part. To move on, I have to **defend** this phase."

Start the gate.

> "First it makes me point at a concrete piece of my own code — my anchor. Then it
> asks me three questions about how *my* implementation actually works."

Answer the three turns for real.

> "Notice these aren't trivia — a generic textbook answer won't pass. It's
> checking whether *I* understand what *I* built."

Show the verdict.

> "Pass or fail, it's about my own project. If I fail, there's a cooldown — no
> spamming retries until something sticks."

## 9. Project Defense Report (~30s)

Open the report; copy/download the Markdown.

> "And it all comes together as a Project Defense Report I can hand to a teacher
> or a hackathon judge — what I built, what I verified, and proof I can explain
> it. No scores or gimmicks — just the real thing."

## 10. Close — what the pilot measures (~20s)

> "So the question I'm testing with this pilot isn't 'do people like it' — it's:
> did Codize help someone write a better prompt, catch what the AI changed, verify
> something they'd have skipped, and actually *defend* their project. That's the
> whole point."

---

## Delivery notes

- **Don't** demo or promise out-of-scope features (browser IDE, GitHub OAuth,
  community, marketplace, analytics, gamification). If asked: *"not in this
  version."*
- If a live LLM call is slow or 502s, say *"that's a live model call — one retry"*
  and move on; it's honest and normal.
- Keep momentum — the gate and the report are the moments that sell it; don't
  linger on setup screens.
- If recording: no secrets on screen (close `.env`, the SQL editor, and any
  key-bearing terminal), and use a placeholder test account.
