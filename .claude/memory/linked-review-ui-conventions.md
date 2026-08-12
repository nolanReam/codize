# Linked Review UI conventions (Milestone 16A.2)

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.

**Semantic boundary:** Change Map asks whether a description accurately records
what appears to have changed. Review asks what the student thinks should happen
next. A confirmed source is not approved, correct, safe, tested, or verified.
The route is the existing `/app/phase/review`; there is no parallel page.

**Two compatible modes:** a strict runtime guard recognizes the additive
M16A.1 shape (`initialized_from_change_map=true`, binding timestamps, stale,
targets). That shape gets linked Review. Any existing manual/legacy artifact
keeps the original files + seven optional fields, local draft key, generic PUT,
errors, and UI. It is never converted automatically. Starting a linked Review
over manual work is secondary and requires a replacement warning.

**Explicit initialization:** no Review API runs on mount. No artifact first
inspects the existing top-level Change Map: missing → Create Change Map; draft →
finish reviewing; stale → regenerate; confirmed/current → Start Review. The
button calls `POST /workflow/{phase}/review/from-change-map` with no body.
Duplicate actions are disabled by local in-flight state. Only a deliberate
replacement sends `{replace_existing:true}`. A 409 refetches the single workflow
source of truth so a concurrent existing Review is displayed. Initialization
has one stable, announced “Preparing your Review…” state and no model/progress
fiction.

**Targets and categories:** render only populated groups, in the backend order:
Behavior changes, Implementation decisions, Possible out-of-scope changes,
Areas to review carefully, Unresolved risks, Behavior still needing testing.
Preserve target order inside a group. Changed files and questions do not become
targets. The bounded `change_text` is React plain text (`white-space:pre-wrap`,
safe wrapping), never Markdown/HTML/linkified content. Never render target/item
ids, source timestamps, schema/provider names, raw imports, references, or
excerpts.

**Source honesty:** derive the human label from the exact snapshot:
confirmed → Confirmed in Change Map; edited → Corrected by you in Change Map;
student origin → Added by you; uncertain → Marked uncertain in Change Map;
needs inspection → Still needs inspection. Unresolved states use calm amber
guidance, never a green verified treatment.

**Student decisions:** exact values are pending/keep/revise/remove/
needs_verification/uncertain, displayed as Not reviewed yet/Keep/Revise/Remove/
Needs testing/I'm not sure. Use fieldset + legend + real radios. Keep has no
active explanation. Revise exposes proposed revision plus optional rationale;
the backend rule is at least one of those two. Remove, Needs testing, and
Uncertain expose optional rationale with decision-specific labels. Both fields
cap at 2,000 Python-style Unicode code points; no `maxLength`, clipping, or AI
rewrite. Hidden rationale/revision remains local for toggling but is excluded
from the canonical payload and dirty comparison.

**Save and dirty state:** linked Review continues through the generic
`PUT /workflow/{phase}/review_board`. The payload is only changed
`target_updates`, each containing review_target_id + review_decision + normalized
student_rationale/student_revision. No source/provenance/stale/generated field
is echoed. Dirty state compares this exact canonical payload against the server
artifact; reverting is clean, and hidden text cannot create a phantom change.
422/network failure keeps the local form. Save success reconciles from the
returned artifact, clears the local draft, remains on the page, and announces
“Review saved.”

**Drafts:** reuse `useDraft` and its 400ms debounce, authenticated-user scope,
storage-failure tolerance, and four-marker secret guard. Surface:
`linked_review:active-project:<phase>:<fingerprint>`. Codize currently has one
project per user, so `active-project` is the project scope until multi-project
exposes a safe client id. Fingerprint is a compact hash of Change Map generated/
confirmed bindings plus ordered target ids—never source text. Stored value is
only fingerprint + target id references + decision/rationale/revision. Exact-id
restore only; stale or rebuilt/rebound Review rejects the old draft. Manual
Review stays on `review_board:<phase>` and cannot cross into linked state.

**Progress/completion:** progress is `N of M items reviewed`; non-pending means
reviewed. Keep, Revise, Remove, Needs testing, and Uncertain all count. Complete
requires at least one target, no pending decisions, valid active fields, and a
clean server-saved form. Needs-testing and uncertainty stay visible after
completion. Zero targets do not say 0/0 or complete; they show a neutral no-
automatic-target message and allow navigation without inventing items.

**Staleness/replacement:** server-derived `stale` is read-only. Old snapshots
and decisions remain visible for historical understanding, but controls/save
are disabled. If the current Change Map is not confirmed/current, return there
first. Otherwise Rebuild Review opens an inline warning explaining that targets
and decisions will be replaced, then and only then sends replacement. Success
clears the old local draft and uses the returned pending targets; never merge or
build client version history. Current Review rebuild is secondary under More
options.

**Navigation/status:** linked completion offers **Continue to Verification** at
`/app/phase/verify` as navigation only. Build Loop Review status distinguishes
not started, ready to start, in progress, complete, and stale; manual artifacts
retain saved/done behavior. Phase next action is Change Map while missing/draft/
stale, then Start Review, Continue Review, Rebuild Review, or Continue to
Verification. Manual Review preserves its established evidence-first next step.
The generic five section values still determine workflow N/5; target progress
never changes it or build-task/Change Map/Defense progress.

**Accessibility/responsive:** one page h1; category h3s; source region label;
semantic radios; visible label focus ring; explicit words for state; field
errors wired through `aria-describedby`; initialization/save/completion live
regions; native disclosures and inline warnings; no hover-only information.
Target/source text wraps anywhere. Decision controls become one column and
primary actions full width at 640px; the standard workspace rail collapses at
1150px and shell at 840px. Existing reduced-motion global rule applies.

**No M16B integration:** no Verification suggestion/check/result is generated
or prefilled; no Evidence, Defense Context, Project Defense, evaluator, Report,
provider, prompt, backend, or migration change exists in M16A.2.

**Exact M16B frontend seam:** `/app/phase/verify` currently receives navigation
only. Future work should request a server-produced handoff after an explicit
student action, keyed by saved Review target references from the current linked
artifact. It must not infer tests client-side from Change Map/source text and
must not equate `needs_verification` with a performed check.

**Exact M16B backend seam:** load a typed `StoredReviewBoardArtifact`, then call
`review_service.needs_verification_targets(review) ->
list[NeedsVerificationReviewTarget]`. Each typed result contains the Review
target id, Change Map item id, reviewed effective-text snapshot, optional
student rationale, and category. That seam currently creates no Verification
records.
