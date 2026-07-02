# Codize backend (FastAPI)

Async FastAPI service. Architecture rule: **Frontend → this backend → external
services (Supabase, Anthropic)** — the frontend never calls external services
directly except Supabase Auth. Route handlers stay thin; product logic lives in
`app/services/` (from Milestone 5 on).

## Layout

```
app/
├── main.py        app factory + CORS + error handlers
├── core/
│   ├── config.py    centralized settings (SecretStr for server-only values)
│   ├── errors.py    consistent JSON error shape, no internal detail leaks
│   └── security.py  Supabase JWT verification (JWKS / ES256)
├── deps/auth.py   require_user dependency → 401 on missing/invalid token
├── routers/       thin route handlers (health; archetypes — auth-required, read-only;
│                  intake — auth-required five-question flow, M6)
├── services/      product logic (template_service.py: archetype template engine, M5;
│                  intake_service.py + project_repository.py: intake engine, M6)
├── schemas/       request/response models (intake.py)
├── templates/     the three archetype JSON templates (Milestone 1)
└── prompts/       the six system prompts (Milestone 1)
tests/             pytest suite
```

## Setup & run

From `backend/`:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # (Windows; use .venv/bin/pip elsewhere)
.venv\Scripts\uvicorn app.main:app --reload
```

Configuration comes from environment variables or a `.env` file in the working
directory — see the repo-root `.env.example` for the contract. Never commit a
real `.env`; server-only values (`SUPABASE_SERVICE_ROLE_KEY`,
`ANTHROPIC_API_KEY`) exist only in the backend environment.

## Tests

```bash
.venv\Scripts\python -m pytest
```

Auth tests sign tokens with a locally generated ES256 key and stub only the
JWKS fetch, so the full verification path runs offline. Live verification of a
real Supabase JWT additionally requires `SUPABASE_URL` (used to derive the
JWKS URL: `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`).

## Auth model (docs/auth.md)

- Frontend sends `Authorization: Bearer <supabase access token>` on every request.
- `require_user` verifies the token server-side (signature via JWKS, `exp`,
  `aud == "authenticated"`) and exposes `CurrentUser` with `user_id = sub`.
- Missing/invalid token → **401**. Wrong-user resource → **403/404**, decided
  per endpoint in the service layer (the backend uses the service-role key,
  which bypasses RLS, so every user-scoped query must filter by
  `user_id == sub` itself).
- UI hiding is never security; every protected endpoint enforces this
  dependency.
