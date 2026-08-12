# Codize V2 product UI

## Product truth

Codize is a beginner-first AI coding mentor for students using external coding agents. The promise is **Build something real with AI. Learn how it works as you go.** The defining rule is **one project, one current change, one useful habit at a time**. `[A1]`

Chat is the primary Build interface, not an unconstrained chatbot and not the source of truth. Structured product logic decides state, intervention, help, and legal transitions. `[A1, A2]`

## Information architecture

- Primary: Project, Build, Learning, History.
- Secondary: Character, Settings.
- Something broke is contextual on Project/Build, not primary navigation.
- The current change is visually dominant; the broader plan is secondary and editable.
- Show one primary cognitive task/action at a time. `[A2]`

## Interaction model

- Reach a useful external-agent prompt quickly.
- Teach only when the current project creates a reason.
- Ask before telling when the student can reason; provide nudge → clue → teach when help is requested.
- Skip redundant questions when the student already demonstrated the habit.
- Return from the coding agent through Worked / Something's wrong / Unsure, then check, inspect, understand, or recover as needed.
- Recovery observes and narrows before producing another patch prompt.
- Support fades per competency and can return for novel/high-risk work. `[A1, A2]`

## Truth and agency

Distinguish student statements, agent claims, repository observations, system inference, performed checks, and evidence. Never imply correctness, security, verification, or mastery without support. Automate clerical context gathering, not the student's consequential judgment. `[A1, A2]`

## Character

The character is a warm, readable companion and the face of the mentor, not the coder or a reward target. Character differences are cosmetic. Motion and sound are optional; reduced-motion equivalents are required. `[A3]`

## V1 implementation boundary

The current engineering-cockpit styling and Prompt → Import → Change Map → Review → Verification → Evidence → Defense → Report journey are V1 implementation truth. Preserve them only for scoped maintenance. Do not use phase progression, gates, Defense, hidden scores, or old artifacts as V2 design requirements. `[I1, I2]`

## Visual source

Approved Figma controls current V2 composition, styling, component appearance, responsive layout, and motion intent. Do not invent a V2 palette or page composition from the V1 CSS when Figma can answer the question. `[A4]`
