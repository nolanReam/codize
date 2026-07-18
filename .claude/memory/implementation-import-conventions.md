# Implementation import conventions (Milestone 15A)

**Product purpose:** "Bring Back What Changed" — after using their prompt
in an external AI tool, the student brings the implementation material back
into Codize (pasted AI response, git diff, code snippet, changed-file list,
and/or their own summary) so later milestones can help them organize it.
M15A is persistence ONLY: no LLM, no extraction, no summary, no correctness
analysis, no code execution, no repo fetching.

**It is a workflow section, not a subsystem:** `implementation_import` is the
fifth entry in `schemas/workflow.py::SECTION_MODELS`, stored per-phase in the
same `projects.workflow_artifacts` JSONB (no migration — the column shape is
backend-owned), served by the SAME generic `GET /workflow/{phase}` +
`PUT /workflow/{phase}/{section}` routes with the same ownership (JWT-only
identity → repository user_id filter), eligibility (active project + real
roadmap phase), full-section-replace semantics, server-stamped `saved_at`,
and error mapping (409/404/422). See [[workflow-artifact-conventions]].

**Canonical schema** (`ImplementationImportArtifact`, extra="forbid"):
required `source_kind` ∈ {ai_response, git_diff, changed_files, code_snippet,
manual_summary, other}; optional `content` ≤ 40,000 chars, `changed_files`
≤ 100 × 300 chars, `student_summary` ≤ 4,000, `tool_name` ≤ 100 (limits are
named constants `IMPORT_*_MAX`). At least ONE of content / changed_files /
student_summary must survive normalization — a fully empty or whitespace-only
import is rejected with a student-friendly message. Do NOT add analysis
fields (ai_summary, risk_score, correctness_score…) here: student source
material stays separate from future AI-generated extraction, which gets its
own shape in M15C.

**Formatting is the material:** normalization is edges-only — strip trailing
whitespace and leading whitespace-only LINES (regex `_LEADING_BLANK_LINES`,
preserving first-line indentation), strip()/dedupe/drop-empty on
changed_files and short fields. Internal indentation, line breaks, diff
markers, and Markdown are stored verbatim; nothing is silently truncated
(oversize → 422 naming the field, never echoing the content). The
serialized-body belt is per-section: `MAX_IMPORT_SECTION_CHARS = 100_000`
(others keep 30 KB) — field caps are authoritative, the belt only rejects
grossly oversized bodies before validation.

**Secret safety:** the shared `_reject_secret_like` marker guard
(`sb_secret_`, `sk-or-`, `AIza`, `-----BEGIN `) applies to every free-text
field; a rejected save persists nothing and the error never echoes the value
(only pydantic's loc + msg surface). Env-var NAMES without values are
ordinary educational text. The write-time guard stays a seatbelt, not a
scanner — value-shaped Bearer/JWT REDACTION lives in the defense-context
layer, which raw imports never enter.

**Untrusted-data boundary (the durable contract):** import content is
student-provided, self-reported, unverified project material — never proof of
correctness, never an instruction source. "Ignore all previous instructions"
stored inside an import is inert data in M15A. Any future LLM consumer (M15C
extraction, M16 Change Map / Review Assistant) MUST treat it as untrusted
project data under the M14A untrusted-data rules and must not follow
instructions embedded in it.

**Deliberately NOT in the Defense Context Pack:** the M14 manifest
(`_SOURCE_DEFS`, fixed 8 sources) does not include implementation_import, so
raw imports cannot reach gate prompts or the context summary by construction
(tested: `test_raw_import_never_enters_the_defense_context`). Raw imports are
large, may contain irrelevant instructions, and would bloat gate prompts —
if defense integration ever happens it is a NORMALIZED Change Map added
through the spec-guardian process in M15C/M16, never the raw import.

**Seams:** M15B frontend (BUILT 2026-07-13 — see
[[implementation-import-ui-conventions]]) uses exactly the planned seam: the
existing routes (`GET /workflow/{phase}` returns `implementation_import` as a
fifth key; `PUT /workflow/{phase}/implementation_import` saves it — same
useWorkflowSection pattern as the other sections). M15C extraction (BUILT
2026-07-13 — see [[change-map-conventions]]) consumes exactly the planned
seam: `workflow_service.get_implementation_import(project, phase_number)` →
`StoredImplementationImport | None` (the validated artifact + `saved_at`;
absent or corrupt stored data returns None, never raw JSON; read-only, takes
an already-loaded project so it duplicates no ownership logic). The Change
Map binds to `saved_at` — replacing an import makes the map stale, never
rewrites it. Raw imports still never enter the defense context; extraction
applies full M14A redaction to a VIEW and never mutates the stored artifact.

**M15C.2 UI consumer:** the saved import now hands off to
`/app/phase/change-map` after a successful save, but saving still performs only
the generic implementation-import PUT—no generation is triggered. The Change
Map page reads this section plus the top-level `change_map` through the same GET
and calls extraction only after **Create Change Map**. Replacing this section
continues to do exactly one thing: stamp a new `saved_at`, which makes an
existing map stale; the frontend leaves that map visible, blocks confirmation,
and requires deliberate replacement generation. See
[[change-map-ui-conventions]].
