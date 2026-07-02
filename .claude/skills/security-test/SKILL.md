# Security & Test Skill

Purpose:

Provide a repeatable validation workflow for Codize.

Invoke automatically whenever:

* database schema changes
* authentication changes
* API routes change
* gate logic changes
* deployment configuration changes

## Security Validation

Verify:

1. No API keys in frontend source.
2. No service-role keys exposed.
3. No secrets committed to git.
4. Backend routes enforce auth.
5. RLS enabled on all tables.
6. Ownership policies verified.

Commands:

```bash
grep -R "service_role" .
grep -R "sk-" .
grep -R "ANTHROPIC_API_KEY" .
```

Review all matches.

False positives allowed.
Exposure is not.

---

## Database Validation

Use MCP database tools.

For every table:

* confirm RLS enabled
* confirm ownership policy exists
* confirm anon writes denied

Record findings.

---

## Gate Validation

Run pytest suite.

Required tests:

* PASS case
* FAIL generic answer
* FAIL textbook answer
* FAIL missing anchor reference
* PASS implementation-specific answer

All tests must pass.

---

## API Validation

Run:

```bash
pytest
```

Verify:

* authentication
* authorization
* protected routes
* cooldown enforcement
* unlock logic

---

## Frontend Validation

Run Playwright.

Verify:

* signup flow
* intake flow
* roadmap generation
* gate interaction
* reconnection modal

---

## Reporting

Before reporting success:

Confirm every claim with:

* test output
* tool output
* MCP inspection

If unverified:

state "unverified".

If failed:

state "failed".

Never infer success.
