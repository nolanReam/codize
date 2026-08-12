# Codize Pilot — Bug Report

> [!WARNING]
> **Historical V1 pilot template.** Reuse only generic bug-reporting fields unless a V2 pilot explicitly adopts it.

One defect per report. Copy this block into your issue tracker (or a notes file)
for each bug. Enough detail to **reproduce** is the whole point.

Before filing, check it isn't an **expected** behavior listed in
`tester_script.md` → "Known issues & limits" (roadmap fallback, gate cooldown,
self-reported verification, hidden scores, out-of-scope features). Those are not
bugs.

**Privacy:** reference the tester only as **P#**. Do not paste anything with
personal data, and never paste secrets — redact any key, token, or JWT before
including logs.

---

- **Bug ID:** BUG-____  (e.g. BUG-01)
- **Date / facilitator:** ____________
- **Participant:** P___  (or "facilitator, during setup")
- **Surface:** ☐ Landing ☐ Login ☐ Intake ☐ Roadmap ☐ Cockpit/Phase
  ☐ Prompt Builder ☐ Review ☐ Evidence ☐ Verification ☐ **Project Defense (gate)**
  ☐ Report/Export ☐ Reconnection ☐ Setup/Env ☐ Other: ______

## Severity & impact

- ☐ **Blocker** — tester cannot proceed / data loss / crash
- ☐ **Major** — wrong behavior, but a workaround exists
- ☐ **Minor** — cosmetic, copy, or small UX friction
- ☐ **Question** — unsure if bug or intended

- **Did it block the tester from completing the task?** ☐ Yes ☐ No — how they
  got past it (if they did): ____________________

## What happened

**Summary (one line):** ____________________________________________

**Steps to reproduce:**
1.
2.
3.

**Expected:** ____________________________________________

**Actual:** ____________________________________________

## Evidence (redact secrets/PII)

- Frontend error message shown to the user: ____________________
- Backend/console error (if visible; strip keys/tokens/JWTs): ____________________
- Screenshot ref (only if consent given; no tester face/PII): ____________________
- Reproducible on retry? ☐ every time ☐ sometimes ☐ once

## Environment

- Backend commit / branch: ____________
- Browser: ____________
- Device / OS: ____________
- LLM path (if known): ☐ Gemini ☐ OpenRouter fallback ☐ n/a
- Was it a live LLM call (roadmap/gate) that just needed a retry? ☐ yes ☐ no

## Facilitator notes / suspected cause

_______________________________________________
