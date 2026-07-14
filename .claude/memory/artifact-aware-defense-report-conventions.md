# Artifact-aware Defense and Report conventions (M16C.1)

One server-derived contract owns downstream parsing:
`workflow_context_service.build_workflow_context(owned_project, phase)` →
`CuratedWorkflowContext`. Defense and Report never independently parse raw
workflow JSON. The normalizer is deterministic, provider-free, phase-scoped,
plain-text-only, bounded by item/field/aggregate/serialized code-point limits,
and uses the shared value-shaped secret redactor. Raw Implementation Import,
database ids, bindings, fingerprints, timestamps, provider data, prompts,
expected concepts, scores, and thresholds are absent.

Source states are `missing | manual | current | stale | incomplete |
malformed`. Change Map drafts carry no downstream content; confirmed AI
wording stays labeled student-confirmed AI inference, student edits/additions
retain authorship, rejected items remain rejected, and uncertain/
needs-inspection items remain unresolved. Review is student judgment.
Verification keeps pass/fail/skipped/not_applicable/unrecorded exactly and is
never Evidence.

Linked Evidence uses only `get_stored_evidence` + `evidence_is_stale`.
Check/result/notes are Verification context. Only student entries are
Evidence; explanation is student explanation; unavailable reason is
unavailable, never an entry. Stale linked Evidence remains stored but support
content is omitted from current grounding. Manual Evidence remains compatible.
Evidence never proves correctness and no artifact state decides Defense.

Defense keeps the existing question generator, grounding validator, providers,
three-turn lifecycle, and separate artifact-blind temperature-0 evaluator.
Turn 1 stores the curated context as server-owned metadata in the first turns
JSONB item; later turns reuse it. Gate APIs still whitelist turn/question/
answer. Legacy in-flight sessions acquire a snapshot on their next successful
turn; legacy completed attempts use a labeled current-state Report fallback.
No migration was needed.

`GET /report/{phase}` is deterministic, authenticated, owner/phase-scoped,
read-only, provider-free, and unstored. It returns the same curated context,
`defense_attempt | current_workflow` source, public Defense transcript/outcome,
and truth notice. Snapshot-backed Reports describe what was available for the
attempt; later edits do not rewrite it. Hidden evaluator/provider/context
internals remain absent.

Exact M16C.2 frontend seam: Defense reads `GET /gate/context-summary` →
`workflow_sources[{source_id,label,state,truncated}]` for state display only;
Report reads `GET /report/{phase}` and renders its curated workflow context plus
Defense record. Never submit context/provenance, parse raw workflow JSON, treat
Verification as Evidence, treat unavailable as Evidence, or claim Codize
independently verified correctness.
