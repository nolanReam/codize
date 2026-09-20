# Codize V2 Phase 7.6B release-truth audit

**Status:** Internal implementation/audit record. Not public policy. Not legal advice.

**Audit date:** 2026-09-19

**Repository baseline:** `ox/v2-beta-staging` at `66d627dda563566b4f0b4b9b3f7fcce62b6b0baa`, clean before implementation.

**Confirmed operating intentions:** United States-only pilot; Nolan operates the pilot with a parent or guardian helping with legal and administrative matters; recruitment through a school, class, or teacher; public contact `codizeapp@gmail.com`.

Those intentions do not establish a legal entity, school or district approval, legal review, participant age, or parental consent.

## Classification key

- **CONFIRMED** — established by current source, migrations/tests, or a successful read-only runtime observation.
- **UNVERIFIED** — plausible or documented historically, but not established in the current deployed environment.
- **REQUIRES OPERATOR DECISION** — Nolan and the accountable adult must select and operationalize the answer.
- **REQUIRES ADULT/LEGAL REVIEW** — a qualified adult and, where appropriate, legal or school reviewer must approve the position before publication or enrollment.

## 1. Deployed preview inspection

### CONFIRMED

- Repository tests identify the branch preview origin as `https://codize-git-ox-v2-beta-staging-spark-codes-projects.vercel.app`.
- A fresh unauthenticated read-only browser context on 2026-09-19 received an HTTP 302 from every tested preview path to Vercel's SSO endpoint.
- The browser therefore rendered `Login – Vercel`, not Codize. `/`, `/login`, the new informational paths, candidate legal paths, and sampled `/app/**` paths all met the same Vercel access gate.
- The access gate set `_vercel_sso_nonce` on the preview domain. The redirected Vercel login set Vercel/Google-login cookies and Vercel-owned local/session storage. Those values belong to the Vercel authentication surface and are not evidence of Codize application storage.
- The SSO page loaded Vercel assets, Google Identity assets, and a Vercel Sentry endpoint. These are not Codize application requests and must not be listed as Codize product processors solely from this observation.
- No account was created, no form was submitted, no authenticated route was opened, and no application data was requested.

### UNVERIFIED

- Codize's deployed runtime cookies, browser-storage keys, third-party scripts, Supabase requests, API origin, and console behavior remain unverified because the preview app was not reachable without Vercel SSO credentials.
- The preview's deployed commit could not be read through the protected page.
- The repository has no local `.env`, `frontend/.env.local`, or backend `.env` in this worktree, so current hosted Supabase and provider settings were not available locally.

### Required follow-up

Use an explicitly authorized Vercel preview session or a separately approved public pilot URL and repeat the inventory in a fresh profile. Record cookie/storage **names, domains, purposes, and expiry**, never token values. Capture requests by origin/path with query strings and authorization headers removed. Verify the deployed commit before treating the result as release evidence.

## 2. Source-confirmed browser storage and tracking

### CONFIRMED

- `@supabase/supabase-js` is instantiated in the browser without a custom storage option. Supabase documents `persistSession` as on by default and local storage as the default browser persistence mechanism.
- Codize source writes these non-authentication keys:
  - `codize:tutorial-seen` in local storage;
  - per-user guidance-disclosure state in local storage;
  - legacy scoped unsent drafts in local storage;
  - `codize:reconnection-checked` in session storage.
- Project setup in the V2 route is saved through the backend and is not a local-storage draft.
- Accepted prompt text is written to the clipboard only after the student chooses the copy/handoff action.
- No `document.cookie` assignment, cookie helper, analytics SDK, advertising SDK, session-replay SDK, or application error-monitoring SDK was found in current frontend/backend source or package manifests.
- No product telemetry persistence was found.
- Next.js Google fonts are declared through `next/font/google`, which bundles the resulting font files with the application build rather than requiring a runtime Google Fonts stylesheet request.

### UNVERIFIED

- Exact Supabase auth key name, access/refresh-token lifetime, and browser persistence on the deployed app.
- Whether Vercel, Railway, Supabase, or an email provider injects or records additional operational data in the live environment.
- Actual host log fields and retention periods.

### Cookie/consent recommendation

For the intended United States-only pilot and the source-confirmed absence of analytics/advertising tracking, do **not** add a generic cookie banner now. Publish a browser-storage disclosure only after the accessible runtime audit confirms the inventory. Reassess before adding analytics, session replay, advertising, or enrolling users outside the decided pilot geography. State privacy law, school requirements, and the classification of persistent preference/draft storage require adult/legal review.

## 3. Authentication settings

### CONFIRMED

- The application supports email/password signup and sign-in through Supabase Auth.
- The client requires at least eight password characters and requests an email-confirmation redirect back to `/login`.
- The frontend sends the Supabase access token to FastAPI; product data is not read from the browser through the Supabase Data API.
- The backend validates authenticated users and owner-scopes application operations.
- Signup collects no age, birth date, school, class, teacher, guardian, legal name, or acceptance record.

### UNVERIFIED

- Whether email confirmation is currently enabled in the hosted Supabase project. A source comment says it is enabled, but dashboard/runtime settings were not available.
- Hosted password policy, breached-password protection, token/session lifetimes, CAPTCHA/rate-limit settings, Site URL, redirect allowlist, email provider, and MFA availability.
- Supabase project region and current subprocessor/data-transfer configuration.

### Required follow-up

An authorized Supabase administrator should capture a redacted settings checklist covering the fields above. Do not include keys, tokens, user emails, or account records in the audit evidence.

## 4. Route inventory

### CONFIRMED from current source

Public functional routes after this phase:

- `/`
- `/login`
- `/why-codize`
- `/how-it-works`

Public aliases `/character` and `/settings` redirect into authenticated application destinations.

Current V2 signed-in routes:

- `/app/projects`
- `/app/project/[id]`
- `/app/project/[id]/plan`
- `/app/project/[id]/build`
- `/app/project/[id]/learning`
- `/app/project/[id]/history`
- `/app/character`
- `/app/settings`

Legacy V1 routes remain compiled and can be addressed directly after authentication, including `/app`, `/app/intake`, `/app/phase` and its prompt/import/change-map/review/verify/evidence children, `/app/gate`, and `/app/report`.

The normal V2 post-authentication destination is `/app/projects`. That does not by itself make the legacy routes unavailable.

### REQUIRES OPERATOR DECISION

- Decide whether legacy V1 routes will remain enabled during the school pilot. If they remain, public privacy and provider disclosures must cover their behavior. If they should be unavailable, that is a separate removal/guarding change with regression testing.

## 5. AI-provider paths

### CONFIRMED

- The legacy roadmap, gate, and workflow routers depend on the shared LLM service.
- The service can call Google Gemini and OpenRouter when corresponding server-only keys are configured. `LLM_PROVIDER` selects the preferred order; a deterministic stub is used when explicitly selected or when no live provider key exists.
- Imported/pasted project material, intake context, and gate answers can therefore enter a provider prompt on those legacy paths when a live provider is configured.
- Current V2 routers do not import or invoke the shared LLM service. The implemented V2 prompt/handoff/build/check/recovery loop is deterministic and manual.
- The student separately copies an accepted prompt into their own coding AI. Codize does not make that external-tool request for them.

### UNVERIFIED

- Which provider keys and primary provider are configured on the hosted backend.
- Whether all legacy provider-touching routes are enabled and reachable in the pilot deployment.
- Provider retention, training use, region, DPA, and subprocessor terms for the configured accounts.
- OpenRouter has historical source notes saying live fallback was not verified; current hosted status is unknown.

### Required publication boundary

Codize cannot say “we never send project content to an AI provider” while provider-backed legacy paths may be deployed. Before publishing Privacy, either disable those paths for the pilot or document the exact enabled provider flows after verifying hosted configuration.

## 6. Data and retention mechanisms

### CONFIRMED

V1 can store authentication/profile linkage, five intake answers, archetype and roadmap output, project phase/status, task progress, prompts, pasted/imported material, review/verification/evidence records, gate questions/answers, hidden evaluation fields, and unlock state.

V2 can store project/setup text, plan items, current-change intent and boundaries, prompt drafts and accepted versions, selected coding agent/effort, checks and student observations, project facts with provenance, bounded build turns, provider-attempt metadata, recovery records, learner evidence, and user preferences.

V2 schema has capability fields for project deletion requests, a future purge boundary, build-turn retention class/expiry/redaction, and an atomic project purge. Exact standard-project recovery and raw-content retention durations are intentionally not hard-coded.

No scheduler or worker that expires/redacts build turns was found. No API that begins ordinary standard-project deletion was found.

### UNVERIFIED

- Hosted database migration state and whether every local migration is applied.
- Log and backup retention across Vercel, Railway, Supabase, and any email/AI provider.
- Whether any operator exports or offline copies exist.

### REQUIRES OPERATOR DECISION

- Retention by data class.
- Whether raw drafts/turns should be collected for the pilot at all.
- Standard project recovery behavior.
- Minimal deletion receipt/audit record, if any.
- Backup and log handling that can actually be honored.

## 7. Ordinary account/data deletion readiness

### Finding

**Codize is not currently ready to fulfill an ordinary account/data-deletion request through the product.**

The existing authenticated endpoint only discards a `temporary_recovery` V2 project. The underlying database function also supports an eligible `deletion_pending` standard project, but no application command was found that begins that state. There is no ordinary project-delete UI/API, account-delete UI/API, or account-level orchestrator.

Deleting the Supabase Auth user alone is unsafe for V2: `v2_projects`, `v2_learner_evidence`, and `v2_user_preferences` intentionally use `on delete restrict`. V1 profile/project/gate/unlock rows cascade from Auth, but the V2 roots must be handled first in the documented order.

### Smallest safe manual runbook to build and test

This is a prerequisite outline, not an instruction to run ad-hoc SQL:

1. Establish an authenticated deletion-request channel, requester identity check, accountable adult approval path, and incident/escalation owner.
2. Build one backend-only, idempotent operator command. It must accept the resolved Supabase user UUID—not a client-supplied owner ID—and expose a dry-run inventory containing counts only, never content.
3. Revoke/suspend active sessions at the start of execution so writes cannot race cleanup.
4. In a locked database transaction, handle V2 learner-evidence minimization/deletion, clear/delete user preferences, and delete every V2 project so project-owned rows cascade. For account deletion, remaining V2 learner-evidence and preference roots must then be deleted rather than retained.
5. Verify that no V2 owner roots remain. Then delete legacy domain rows if not already covered by the eventual Auth cascade.
6. Delete the Supabase Auth user last through an authorized administrative boundary. A failed domain cleanup must not delete Auth first.
7. Verify zero owner-scoped rows across V1 and V2, revoked sessions, and failed sign-in. Record only the minimum approved deletion receipt.
8. Process provider/log/backup obligations according to the reviewed vendor capabilities and published policy; do not promise immediate backup erasure unless it is real.

### Prerequisites before any real request

- Adult/legal-approved retention and identity-verification rules.
- A reviewed table/vendor inventory.
- Concurrency, retry, partial-failure, and audit-log design.
- Tests proving cross-owner isolation and idempotency.
- One explicitly authorized synthetic staging account exercising the full process.
- A recovery/incident procedure if Auth deletion succeeds but an external-system step fails.

No account or synthetic data was created or deleted during this audit.

## 8. School pilot review packet

A school or district reviewer should receive a concise packet answering:

1. **Operator:** Nolan, the accountable adult contact, the legal/operator arrangement, and `codizeapp@gmail.com`.
2. **Authorization:** who at the school may approve or invite use; whether district review, vendor registration, or a data agreement is required. A teacher invitation alone must not be represented as district approval.
3. **Audience:** decided age floor, how age is established, parental/guardian notice or consent, and what happens if Codize learns a participant is under the permitted age.
4. **Data map:** every field collected, why it is needed, where it is stored, who can access it, and whether it is optional.
5. **Educational records:** whether students will enter assignments, grades, teacher feedback, class rosters, school identifiers, or other records. The pilot should instruct students not to enter these unless the school has reviewed the flow.
6. **Providers:** Vercel, Railway, Supabase, email provider, and any enabled Gemini/OpenRouter processing, with purpose, region, retention, training terms, and subprocessors.
7. **External coding AI:** students manually send prompts to their own tool; which school accounts/tools are permitted is a school decision.
8. **Access/security:** authentication, owner scoping, administrative access, incident contact, secrets boundary, and current limitations.
9. **Retention/deletion:** actual periods, ordinary request channel, tested deletion ability, backups/logs, and end-of-pilot cleanup.
10. **Accessibility:** target, tested support, known limitations, and feedback process.

### REQUIRES ADULT/LEGAL OR SCHOOL REVIEW

- Whether the service is directed to children and how under-13 users are handled.
- Whether parent/guardian consent or notice is required for each participant group.
- Whether school-submitted or student-created information becomes an education record and what FERPA responsibilities or agreements apply.
- Whether state student-privacy laws, district procurement rules, or school board policies apply.
- Whether the operator arrangement is sufficient for contracts, incident response, and rights requests.
- Whether live AI-provider processing is acceptable for school use.

No COPPA, FERPA, school-approval, nonprofit, incorporation, or legal-review claim is currently supportable.

---

# INTERNAL DRAFT — Privacy Notice outline

**DO NOT PUBLISH. UNRESOLVED FIELDS REMAIN.**

1. **Who operates Codize**
   - Nolan with parent/guardian administrative support.
   - Contact: `codizeapp@gmail.com`.
   - `[UNRESOLVED: legal/controller identity, mailing address, accountable adult name/contact]`
2. **Who may use the pilot**
   - United States-only school/class/teacher recruitment.
   - `[UNRESOLVED: minimum age, under-13 rule, guardian/school consent process]`
3. **What is collected**
   - Email/authentication and session information.
   - Profile/account identifiers and login timestamps.
   - Project/setup text, plans, current changes, prompts, checks, observations, recovery records, history, preferences, and learner-support evidence.
   - Legacy intake/workflow/gate material if legacy routes remain enabled.
   - Browser storage and clipboard actions.
   - Operational request/error/security logs, after host verification.
4. **Why it is used**
   - Authenticate users; save and resume projects; prepare handoffs; guide checking/recovery/understanding; secure and operate the service.
   - `[UNRESOLVED: lawful bases are a legal determination; do not add them from this outline]`
5. **AI and external coding tools**
   - Manual user-directed handoff to the student's own coding AI.
   - Exact Codize-side provider flows only after hosted verification.
6. **Service providers and transfers**
   - Supabase, Vercel, Railway, email provider, and enabled AI providers.
   - `[UNRESOLVED: exact accounts, regions, subprocessors, DPAs, retention/training terms]`
7. **Cookies/browser storage**
   - List each verified key/cookie, purpose, duration, and controller after accessible deployment inspection.
8. **Retention**
   - `[UNRESOLVED: every period, deletion-pending behavior, logs, backups, inactive accounts, end-of-pilot cleanup]`
9. **Access and deletion requests**
   - Contact address and identity-verification process.
   - `[UNRESOLVED: response procedure and timing; manual deletion capability must be implemented/tested first]`
10. **Security and limitations**
    - Owner-scoped/backend boundary in plain language without absolute-security promises.
11. **Children/student privacy**
    - `[UNRESOLVED: approved eligibility/consent/school terms]`
12. **Changes and contact**
    - Effective date/version and reviewed update process.

# INTERNAL DRAFT — Terms of Use outline

**DO NOT PUBLISH. REQUIRES ADULT/LEGAL REVIEW.**

1. Operator identity and contact. `[UNRESOLVED: contracting party and address]`
2. Pilot eligibility, United States scope, school authorization boundary, and parent/guardian requirements. `[UNRESOLVED]`
3. Account accuracy and security.
4. Acceptable use, including no secrets, sensitive personal information, harmful activity, or content the user lacks permission to submit.
5. Student content ownership and only the limited operating license actually needed. `[UNRESOLVED: exact license]`
6. External coding-AI tools and separate provider terms.
7. Product limitations: educational guidance and recorded checks are not guarantees of correctness, security, availability, learning, grades, or certification.
8. Beta changes, availability, suspension, and termination. `[UNRESOLVED: operational commitments]`
9. Privacy Notice incorporation.
10. Account/content deletion mechanics only after they exist.
11. `[UNRESOLVED AND LEGAL: governing law, disputes, warranties, liability, indemnity, IP complaints]`
12. Version/effective date and acceptance mechanism. `[UNRESOLVED: clickwrap, acceptance record, re-consent]`

Exclude payment, subscription, renewal, and refund terms while those features do not exist.

# INTERNAL DRAFT — Accessibility Statement outline

**DO NOT PUBLISH AS A CONFORMANCE CLAIM.**

1. Codize's goal is an interface students can use with keyboard, assistive technology, zoom, reduced motion, and different viewport sizes.
2. Current implementation practices: semantic headings/landmarks, labelled controls, visible focus, text status, responsive layout, and reduced-motion support.
3. `[UNRESOLVED: adopted standard; WCAG 2.2 AA is the recommended target, not a current certification]`
4. Tested environments, dates, methods, and explicitly stated gaps.
5. Known limitations discovered through audit; do not use an empty boilerplate list.
6. Feedback channel: `codizeapp@gmail.com` and the information that helps reproduce a barrier.
7. `[UNRESOLVED: accountable responder and response process; do not promise an SLA that cannot be met]`
8. Last reviewed date and statement version.

Accessibility remains an implementation and testing requirement regardless of the statement.

## 9. Exact blockers before public legal routes

1. Legal/operator/controller identity and accountable adult details.
2. School/district authorization path and whether a data agreement is required.
3. Age floor, under-13 response, and parent/guardian notice/consent process.
4. Decision on legacy route availability.
5. Verified hosted AI-provider configuration and reviewed provider terms.
6. Accessible deployed cookie/storage/network inventory at the release commit.
7. Verified Supabase auth/session configuration.
8. Retention values for product content, raw turns, logs, backups, inactive accounts, and end-of-pilot cleanup.
9. Implemented and synthetic-staging-tested ordinary account deletion.
10. Vendor list, regions, subprocessors, access roles, and incident process.
11. Terms content decisions and acceptance-record design.
12. Accessibility target, full audit, known limitations, and accountable response process.

Until these close, `/privacy`, `/terms`, and `/accessibility` must remain absent and the public footer/signup must not link to them.

## 10. Implementation and local verification record

Implemented `/why-codize` and `/how-it-works` with a shared public document shell, page metadata, native document scrolling, responsive layouts, semantic landmarks/headings, skip navigation, restrained focus/hover treatment, and no animation dependency. The How It Works page uses a clearly labelled fictional static walkthrough rather than student data or fabricated screenshots.

The landing hero, header, narrative, media, and motion code were not changed. Its footer now links only to the two implemented pages, the confirmed contact email, and Sign in. No Privacy, Terms, or Accessibility route/link was added. Signup mode now uses the future notice location for a truthful pilot-contact line and makes no Terms-acceptance claim.

Local optimized-build QA:

- 1440×900, 390×844, and 320×700: both new routes returned 200 with one `h1`, header/main/footer landmarks, complete content, and no horizontal overflow.
- Reduced motion: matched and complete; the public document pages contain no entrance or scroll animation.
- Keyboard: skip link, navigation, and evidence disclosures showed a 3 px visible focus outline; Enter opened the native disclosure and activated route navigation.
- Console/hydration: zero console errors, page errors, or Next.js error overlays on either route.
- Landing: existing H1 and minimal header remained intact; no console error or horizontal overflow.
- Focused contracts: 14 passed before the final full run.
- Full frontend suite: 429 tests passed across 53 files.
- `npm run typecheck`: pass.
- `npm run lint`: pass, with only Next.js's existing deprecation notice for `next lint`.
- `npm run build`: pass; 24 static pages generated and both new routes prerendered.
- `git diff --check`: pass at final review.

Rendered evidence is outside the repository under `C:/Users/purpl/.codex/visualizations/2026/09/20/01a0bc44-006c-74d0-b7a3-dc350bfaefb2/`.

Production mutation count: **ZERO**. The deployed preview inspection used unauthenticated GET requests only. Nothing was pushed, deployed, migrated, submitted, created, or deleted.
