# Security and Test

## Purpose

Provide risk-based validation for the current V1 implementation and future V2 work without turning V1 lifecycle tests into V2 product requirements.

Use when authentication, authorization, data access, schema, API routes, untrusted content, runtime prompts, external integrations, deployment configuration, or other security-sensitive behavior changes.

## Durable security checks

1. No provider, database, service-role, OAuth, webhook, or other server secret enters frontend source, client responses, logs, fixtures, or commits.
2. Protected routes derive identity from verified authentication, never a client-supplied user ID.
3. Every data path enforces ownership. New tables receive explicit RLS, grants, backend/client write boundaries, and cross-user tests.
4. Validate user input and external/model output at trust boundaries. Reject malformed or oversized values without echoing secrets.
5. Treat imported, repository, and user content as untrusted data. Verify prompt-injection isolation, redaction, truncation, grounding, and leak prevention where applicable.
6. Preserve provenance and uncertainty; do not convert student statements, agent claims, suggested checks, or AI summaries into verified facts.
7. Verify idempotency, concurrency/version behavior, stale-state handling, retries, and fail-closed storage for state-changing flows.
8. Confirm error responses do not expose stack traces, prompts, raw untrusted material, credentials, or internal scoring/policy metadata.

## Validation routing

- Run the relevant backend and frontend tests for the touched subsystem.
- Add negative, cross-user, malformed-input, and retry/failure cases proportionate to risk.
- Verify schema/RLS with database tooling after an authorized schema change.
- Verify browser flows, console/network behavior, accessibility, and responsive states after user-facing changes.
- Scan changed files and the relevant repository surface with `rg`; review every match instead of trusting a zero-context string scan.
- Report test environment, command, result, and anything not verified.

## V1 compatibility

If a task changes the current V1 intake, roadmap, phase, gate, cooldown, unlock, Defense, or workflow subsystem, run its existing contract tests. Those tests prove V1 compatibility only; they do not make the behavior a V2 requirement.

## External safety

Do not modify live Supabase, Railway, Vercel, GitHub, provider settings, or production data without explicit authorization. Use temporary data, record exact targets, and verify cleanup.
