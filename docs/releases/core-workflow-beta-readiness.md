# Core Workflow Beta Readiness

## Release identity

| Item | Result |
| --- | --- |
| Checkpoint | M16R — Core Workflow Beta Readiness, Live Deployment, and Pilot Smoke |
| Reviewed source commit | `1a450868d13d9ccf200297778dd3bc5fd429dd54` |
| Final deployed commit | `1a450868d13d9ccf200297778dd3bc5fd429dd54` (no release-blocking code fix required) |
| Branch | `main` |
| Deployment date | 2026-07-15 UTC (2026-07-14 PDT) |
| Decision | **READY WITH NON-BLOCKING LIMITATIONS** |

## Production targets and deployments

| Target | Status |
| --- | --- |
| Frontend | Vercel team/project `spark-codes-projects/codize`; production alias `codize-app.vercel.app`; deployment `dpl_4gYsDMjaYkupTqcuQCTzY1qaubLH` is `READY` |
| Backend | Railway project `codize-backend`, environment `production`, service `codize`; deployment `a3e5dd77-590e-41c3-9835-7288690875fe` is `SUCCESS`; `/health` returned 200 |
| Database | Supabase project `Codize` (`tadkbymxkdncqahzshml`), shared friend-pilot target; healthy; no M16R schema change |
| Migration ledger | Current through `20260714084458_harden_workflow_artifact_write_boundary`; the reviewed repository migration is `20260714064425_harden_workflow_artifact_write_boundary.sql` |

Backend was deployed first from a clean archive of the reviewed commit and checked for health, CORS, protected-route authentication, and API compatibility before the frontend was deployed. The frontend was then deployed from a clean frontend-only archive of the same commit. Production and preview frontend configuration contains only the three intended encrypted public client settings; shipped bundles expose only the expected public Supabase and Railway origins and no credential-shaped values.

Rollback references:

- Vercel previous production deployment: `dpl_ANX6a8pEhUXV2xfsmTmvdkWEuL1e` (`READY`, source commit `dc6f45d0cc7ea99fe272c5f0f40e3af38fab0252`).
- Railway previous deployment: `6249d7ff-2b6b-4867-aa55-2db650680439` (source commit `dc6f45d0cc7ea99fe272c5f0f40e3af38fab0252`). Railway lists it as `REMOVED`; rollback material is retained in the reviewed commit and would require a clean redeploy rather than assuming a one-click active rollback.

## Verification evidence

Local release gate:

- Backend: 722 tests passed.
- Frontend: typecheck passed; lint passed with no warnings or errors; 25 test files / 251 tests passed; production build passed with 17 static routes.
- Prebuild validator: 244 checks passed.
- `git diff --check`: passed; secret scan found no credential exposure (only deliberate PEM-marker fixtures).

Hosted smoke used one dedicated, uniquely marked QA project and the real hosted provider path. The completed sequence was:

`Prompt Builder → Bring Back What Changed → Change Map → Review → Verification → Evidence → Project Defense → Defense Report`

- Prompt Builder built and saved the structured prompt; it correctly made no model call under the current client-side contract.
- Implementation import preserved diff formatting and inert injection-shaped text literally; it did not execute or create DOM nodes.
- One Change Map generation produced six grounded items. Confirmed, student-edited, needs-inspection, uncertain, and rejected decisions persisted and were carried forward according to the reviewed contract.
- Review initialized only after its explicit action and carried forward only the two relevant items. Verification carried forward only the needs-testing item; Passed, Failed, Skipped, and Not applicable states were rendered and the final recorded result persisted honestly.
- Evidence required an explicit eligible target and kept Verification context, student-provided material, and the student's explanation distinct.
- Project Defense generated three grounded questions and used one evaluator call. No model call was repeated to force an outcome. The actual outcome was **PASS**.
- Defense Report loaded from the server-owned record and separated Change Map provenance, Review decisions, recorded Verification, student-provided Evidence, transcript, and evaluator outcome. Report reads were deterministic and did not invoke the provider.
- The roadmap provider response drifted structurally once and the designed, validated template fallback activated successfully. OpenRouter fallback was not invoked.

Security and integrity checks:

- Anonymous protected-route checks returned 401. A second authenticated QA identity saw zero owner project rows and received controlled workspace-not-ready responses from workflow, gate, context, and report routes.
- The owner could read its project through RLS but a direct client PATCH to the project table was blocked with 403. Normal API writes touched only the intended workflow sections.
- Phase 2 remained empty after all Phase 1 workflow writes, confirming phase isolation.
- Context-summary and report responses exposed no score, threshold, raw context pack, grounding terms, prompts, expected concepts, or evaluator internals. Injection-shaped imported text remained inert.
- Browser console: 0 warnings and 0 errors. Completed browser requests showed no 4xx/5xx responses; canceled navigation-prefetch/test-harness requests were non-production failures. Railway HTTP logs showed 146 successful requests, four intentional isolation 409s, and zero 5xx responses. Runtime logs contained no secrets or QA content.

Rendered-interface audit (`codize-ui-ux`, audit mode only):

- 36 route/viewport combinations inspected across 390, 768, 1080, and 1920 px.
- No horizontal overflow, clipped visible controls, missing page headings, or unnamed visible controls.
- Keyboard focus had a visible 2 px outline; reduced-motion limited animation and transition durations to 0.01 ms.
- Primary workflow actions, truth labels, Report hierarchy, desktop layout, and compact mobile navigation remained usable and legible.

## Data preservation and cleanup

Only aggregate pilot-state counts were compared. No real pilot content was opened or modified. The guarded QA cleanup removed the dedicated journey identity/project and two isolation identities. Post-cleanup aggregates exactly matched the pre-smoke baseline: 5 auth users, 5 profiles, 5 projects, 4 gate sessions, 0 unlocks, 1 project with workflow artifacts, and 2,913 workflow-artifact bytes. No M16R marker remained. Local deployment staging and temporary QA-helper files were removed.

## Defects, limitations, and next checkpoint

No release-blocking defect was confirmed, so no application code, provider, model, prompt, evaluator, scoring, retry, cooldown, or schema change was made.

Known non-blocking limitations:

- `npm audit --omit=dev` reports two moderate findings affecting the current Next/PostCSS dependency chain (no high or critical findings). The reported PostCSS issue concerns CSS stringification; this checkpoint did not broaden scope into a dependency upgrade without a confirmed hosted exploit path.
- The Gemini production path was exercised; the configured OpenRouter fallback remains live-unverified because it was not needed.
- Railway's previous deployment is retained as a reference but currently listed as `REMOVED`; backend rollback would be a controlled clean redeploy of the previous reviewed commit.

Recommendation for M17: proceed only as a new checkpoint, using the already approved guided-navigation scope; do not fold it into this release record or alter the verified core-workflow contracts.
