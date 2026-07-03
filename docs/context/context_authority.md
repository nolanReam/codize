# Codize Context Authority

Which document wins when sources disagree. Established during the product
vision reset (2026-07-03, after Milestone 12 at `44442b0`). Future Claude
sessions should resolve conflicts using this hierarchy.

## Authority hierarchy

1. **`instructions.md`** (repo root)
   - Controls the **active Claude Code task/process only** — what the current
     session should and should not do.
   - Its content is replaced per session/milestone. It does **not** permanently
     redefine product vision unless it explicitly updates the context docs
     below.

2. **`docs/context/codize_product_vision_v3.md`**
   - Controls current **product positioning, UX direction, MVP scope, and
     M13+ frontend direction** (AI Workflow Trainer / Project Defense
     Workflow; the Codize Build Loop).
   - If it conflicts with the master spec on UX positioning or frontend
     direction, **v3 wins**.

3. **`docs/context/codize_master_spec_v2.1.md`**
   - Controls **backend invariants, core architecture, intake questions,
     the three archetypes, security constraints, RLS/auth requirements, and
     gate mechanics** (turn structure, temperatures, cooldown, fail-closed
     evaluation, hidden scores/thresholds) — unless explicitly superseded by
     v3 with user approval.
   - If it conflicts with v3 on backend security, auth, RLS, or gate safety
     invariants, **the spec wins**.

4. **`CLAUDE.md`, `.claude/skills/`, and `.claude/memory/`**
   - Control durable **implementation conventions and operational memory**
     (how things were built, verified decisions, one lesson per memory file).

5. **`docs/context/codize_roadmap_v2.html`** — **LEGACY**
   - The original build/learning roadmap for Codize itself. Useful historical
     context for why technical decisions were made (async FastAPI, service
     layer, gate temperatures, RLS shape).
   - **Not current product direction.** Do not use it to define M13 unless
     explicitly instructed.

6. **`docs/context/conversations.json`** — **ARCHIVE**
   - Historical product-debate record only. Not authoritative. Do not read
     unless explicitly needed (large, ~1.4MB — grep, don't read whole).

## What "legacy" means

Legacy files are **not deleted or renamed**. Marking a file legacy means:

- future sessions should know it is old context,
- it can still be referenced for history,
- it must not override the current v3 product direction,
- it should not drive M13 frontend decisions.
