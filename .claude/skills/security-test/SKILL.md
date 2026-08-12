# Security and Test

## Purpose

Provide risk-based validation for the current V1 implementation and future V2 work without turning V1 lifecycle tests into V2 product requirements.

Use for authentication, authorization, data access, schema, routes, untrusted content, runtime prompts, integrations, deployment, and other security-sensitive changes.

## Durable checks

- Keep every server secret out of frontend code, responses, logs, fixtures, and commits.
- Derive identity from verified authentication; enforce owner scoping and RLS.
- Define and test grants and write boundaries for new data.
- Validate user, external, and model input/output at trust boundaries; fail closed where integrity or claims are at risk.
- Treat imported/repository content as untrusted; retain prompt-injection, redaction, truncation, grounding, and leak defenses.
- Preserve provenance and uncertainty; suggestions and claims are not verification.
- Test idempotency, concurrency/versioning, staleness, retries, cross-user access, malformed input, and safe errors.
- Report commands, environments, results, and unverified items honestly.

Run existing gate/cooldown/unlock/phase tests only when maintaining those current V1 subsystems. They prove legacy compatibility, not V2 requirements.

Never modify live external services or production data without explicit authorization.
