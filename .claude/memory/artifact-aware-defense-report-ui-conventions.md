# Artifact-Aware Defense and Report UI Conventions

M16C.2 is a frontend-only integration over the reviewed M16C.1 contracts. No
backend, migration, provider, prompt, evaluator, threshold, PASS/FAIL, cooldown,
retry, or model behavior changed.

## Project Defense

`/app/gate` keeps `GET /gate/current` and the existing start/turn/evaluate
requests authoritative. `GET /gate/context-summary` is an independent,
non-blocking request used only before a new attempt to orient the student. It
renders the server labels for Change Map, Review, Verification, and Evidence,
their exact current/missing/incomplete/stale/manual/malformed state, and
truncation. It never renders artifact content, source ids, bindings,
fingerprints, snapshot metadata, or evaluator internals. Failure gets a local
retry and cannot disable Begin.

The ready screen explains that the project record helps Codize ask relevant
questions but cannot answer or guarantee a pass. It also explains that a new
attempt gets a stable server-owned record. The client does not claim a resumed
attempt has a snapshot because `GET /gate/current` exposes no such flag.
Answers are never generated or prefilled. The existing user/attempt/step-scoped
draft remains the only local answer persistence, and successful submission
clears it. Existing 2,000-character anchor and 8,000-character answer caps,
question order, safe loading, PASS/FAIL, cooldown, and retry behavior remain.

## Defense Report

`/app/report?phase=N` calls only `GET /evaluation` for pre-active routing and
`GET /report/{phase}` for report data. It does not fetch workflow artifacts,
intake, context packs, or gate internals and never reconstructs a Report in the
browser. The explicit phase query keeps a completed phase reachable after a
PASS advances the project.

Render order is: phase/outcome; workflow-context source; exact server truth
notice; source-state overview; Change Map; Review; Verification; Evidence;
student-safe Defense transcript; evaluator outcome. `defense_attempt` is a
server-owned record captured for that attempt. `current_workflow` is clearly
labeled as the current saved project record used for a legacy attempt and must
never be called a snapshot.

Preserve Change Map origin/decision/uncertainty, including rejected items.
Review `needs_verification` means needs testing, not verified. Verification
results are student-recorded and render pass, fail, skipped, not applicable,
and unrecorded exactly. In Evidence, check/result/notes are a separate
“Verification context — not Evidence” block. Student-provided entries,
student explanation, unavailable reason, stale-support omission,
not-addressed, and manual records are separate. Evidence is never proof.

All response strings render as React text. Never use raw HTML or Markdown
rendering, embeds, iframes, remote previews, or arbitrary auto-linking.
`safeEvidenceHref` is the sole external-link gate: only valid `http:`/`https:`
`app_url` entries become links, with `_blank` and `noopener noreferrer`.
Markdown copy/download escapes user content and remains a plain report export.

Source states and results use text plus color, semantic headings, status/error
announcements, visible native focus, wrapping for long text/URLs, and the
global reduced-motion kill switch. The layouts have no horizontal overflow at
390, 768, 1080, or 1920 px.

## Completed core workflow seam

The exact completed-core-workflow seam is:

`Prompt Builder → Bring Back What Changed → Change Map → Review → Verification → Evidence → Project Defense → Defense Report`

The workflow artifact counter remains exactly N/5. Change Map is still a
derived sibling record, and Defense/Report add no captured artifact.
