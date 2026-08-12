# Change Map conventions (Milestone 15C.1)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

**Purpose (prevention-first, recovery-capable):** convert a saved M15A
implementation import into an AI-generated, EDITABLE DRAFT of what APPEARS to
have changed, so the student reviews/corrects it before continuing. The map
answers "what appears to have changed, what should I inspect, what do I still
need to understand" — it never claims the implementation is correct, never
claims Codize verified anything, and works identically for a beginner's
per-step import and an experienced user reconstructing a project (one
architecture, no separate modes).

**Provenance chain, never blended:** student import (untrusted) → AI draft
(`origin=ai_inferred`, `draft_text`, server-owned after generation) → student
decision (`student_decision`, `student_text`) → derived downstream text
(`change_map_service.confirmed_items`/`unresolved_items`). AI inference never
becomes student-confirmed by generation; AI uncertainty (`supported` /
`ambiguous` / `needs_inspection` — deliberately NO numeric confidence) is a
separate axis from the student decision (`pending_review` / `confirmed` /
`edited` / `rejected` / `uncertain` / `needs_inspection`). `student_text` is
stored ONLY for `edited` and `student_added` (schema-enforced) so wording
authorship stays unambiguous. Effective text: confirmed→draft_text,
edited/student_added→student_text, rejected→excluded forever,
uncertain/needs_inspection→unresolved context only, pending→nothing.

**Persistence:** `projects.workflow_artifacts[phase]["change_map"]` — a
SIBLING key beside the five student sections, same column, NO migration.
It is deliberately NOT in `SECTION_MODELS`: the generic
`PUT /workflow/{phase}/{section}` 404s on it (server-owned provenance is
unreachable by full-replace), `workflow_service._stored_sections` filters it
out of every section read, which ALSO keeps it out of the M14 defense context
(fixed 8-source manifest — live-checked unchanged). `GET /workflow/{phase}`
returns it TOP-LEVEL (`change_map` key + computed `stale`), never inside
`sections` — the frontend counts section values for "N/5 captured" (the
M15B /4→/5 lesson).

**Generation safety order** (`change_map_service.generate_change_map`):
typed read (`workflow_service.get_implementation_import`) → M14A
`redact_secrets` per field, THEN deterministic truncation (summary 4k /
files 12k whole-entries / content 20k head+tail with visible markers;
cuts never split the redaction marker) → explicit untrusted-data delimiters
(`=== BEGIN IMPORT … === END IMPORT ===`, all three material sections always
present with "(none provided)") → `prompts/change_map_extraction.md` at
temperature 0 → fence-tolerant fail-closed parse (`GeneratedChangeMap`,
extra=forbid, ≥1 item, ≤40 items / 600-char text / 5 refs / 300-char
excerpts) → deterministic validation → ONE corrective regeneration
(categories only, never raw output/material) → retryable 502 with nothing
stored. The student's stored import is NEVER mutated — redaction applies to
the extraction view only; `source_redacted`/`source_truncated` are honest
metadata.

**Deterministic validation (model provenance is never trusted):** every
source reference targets a field the import actually contains, kind must
match, `file_path` must appear in the material, `supporting_excerpt` must be
an EXACT substring of the sanitized extraction view (edges canonicalized —
live flash-lite appends stray trailing spaces; whitespace-only excerpts
explicitly rejected because indentation makes them trivial substrings), and
every code-shaped identifier in draft text must appear in the material
(reuses `grounding_service.extract_grounding_terms` — M14B untouched).
Live lesson: the prompt must demand SINGLE-LINE character-exact excerpts
including diff markers (+/-/spaces) — flash-lite otherwise joins lines and
strips markers.

**Server-assigned, model/client can never set:** `item_id`
(`cm-`/`sa-` + sha256(category\ndraft_text)[:12] — deterministic, no
timestamps), `origin`, `student_decision=pending_review`, `generated_at`,
`confirmed_at`, `status`, `source_import_saved_at`, redaction/truncation
flags.

**Lifecycle:** `POST /workflow/{phase}/change-map/generate` (409 without an
import; existing map — draft OR confirmed — requires explicit
`{"replace_existing": true}`; 502 nothing-stored on failure).
`PUT /workflow/{phase}/change-map` (no LLM): `updates` patch student-owned
fields of AI items by id; `student_added_items` is the FULL replacement set
(origin student_added, text required, decisions limited to
confirmed/uncertain/needs_inspection); any successful update returns the map
to draft (a decision change invalidates a confirmation).
`POST /workflow/{phase}/change-map/confirm` (no LLM): blocks on
pending_review items and on staleness; rejected/uncertain/needs_inspection
are honest and allowed — confirmation means "I reviewed this map and these
unresolved items remain", never "every item is correct".

**Staleness:** `stale = change_map.source_import_saved_at !=
implementation_import.saved_at` (or import missing/corrupt) — server-derived
on read (`workflow_service.change_map_is_stale`), never stored, never
client-controlled. Replacing the import never rewrites the map silently.

**Stub provider:** `StubProvider._change_map` fires on the
`CODIZE CHANGE MAP EXTRACTION` marker and emits a small grounded draft from
the rendered import block — it passes the SAME deterministic validation a
live model must, so `LLM_PROVIDER=stub` smokes the whole pipeline with zero
model calls.

**Seams:** M15C.2 UI reads `GET /workflow/{phase}` → `change_map` (+`stale`)
and drives the PUT/confirm routes above. M16A.1 now consumes the exact typed
backend seam: `workflow_service.get_change_map(project, phase) →
StoredChangeMap | None`, then `change_map_service.confirmed_items(map)`
(reviewed effective statements) / `unresolved_items(map)` (cautious context)
to create a separate linked Review draft. This does NOT make Change Map
confirmation implementation approval: every Review target begins `pending`.
Verification/Defense/Report integration remains unwired.
Adversarial matrix: `docs/testing/m15c_change_map_adversarial.md`. See
[[implementation-import-conventions]], [[workflow-artifact-conventions]],
[[defense-context-conventions]], [[grounded-defense-conventions]].

**M15C.2 frontend consumer (built 2026-07-13):** strict mirror types and the
three API methods live in `frontend/lib/types.ts` + `api.ts`; the page is
`/app/phase/change-map`; pure UI/domain logic is `lib/changeMap.ts`. The client
never generates on load, never auto-regenerates, never treats supported as
verified, never shows numeric confidence, and renders bounded references as
plain text only. The update payload contains only `updates` (AI item id + the
three student-owned decision/text/note fields) and the full
`student_added_items` replacement set (no origin/id/provenance). Confirmation
is locally gated on saved/non-stale/no-pending state but the backend remains
authoritative. Stale/confirmed maps stay visible; replacing a map is explicit
and destructive-review wording is mandatory. Local review drafts reuse the
existing secret-guarded system with a generated-map timestamp in the surface
key, so replacement maps cannot consume old decisions. Build Loop status is
separate from N/5. M16A.1 consumes the confirmed map only through the backend
seam above; the M15C.2 frontend itself remains unchanged. Full conventions:
[[change-map-ui-conventions]].

**M16A.1 Review consumer (built 2026-07-13):** only six categories become
Review decision targets, in this priority order: behavior_change,
implementation_decision, out_of_scope_change, security_sensitive_area,
unresolved_risk, unverified_behavior. changed_file and
question_to_understand remain context; rejected/pending never enter; uncertain
and needs_inspection enter with `source_resolution=unresolved`. Review stores
the bounded effective-text snapshot + item/category/origin/student-decision
snapshot and binds to this map's generated_at + confirmed_at. A later map
edit/reconfirmation/regeneration or import staleness makes the Review stale on
read without rewriting either record. Raw import and source references are
never copied. See [[change-map-review-integration-conventions]].
