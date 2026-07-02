"""Codize auth + RLS verification over the real Auth and PostgREST APIs.

Prerequisite: run the SETUP section of scripts/verify_auth.sql (via Supabase
MCP execute_sql) to create the two test users. Run the CLEANUP section after.

Usage:
    SUPABASE_URL=https://<ref>.supabase.co SUPABASE_ANON_KEY=<anon key> \
        python scripts/verify_auth.py

Uses only the public anon key and throwaway test-user credentials (these are
not secrets — the users exist only for the duration of a verification run).
Exits 0 only if every check passes.
"""

import json
import os
import sys
import urllib.error
import urllib.request

USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
PROJECT_B = "bbbbbbbb-0000-4000-8000-000000000001"
CREDS_A = ("rls-test-a@codize.local", "C0dize!Test-A-9f2k")  # throwaway test user
CREDS_B = ("rls-test-b@codize.local", "C0dize!Test-B-7x4m")  # throwaway test user

failures = []


def request(method, url, headers, body=None):
    """Return (status, parsed_json_or_None). HTTP errors are returned, not raised."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except (ValueError, TypeError):
            return e.code, None


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not anon:
        sys.exit("Set SUPABASE_URL and SUPABASE_ANON_KEY in the environment (see .env.example).")

    def login(email, password):
        status, body = request(
            "POST", f"{url}/auth/v1/token?grant_type=password",
            {"apikey": anon, "Content-Type": "application/json"},
            {"email": email, "password": password},
        )
        if status != 200 or "access_token" not in (body or {}):
            sys.exit(f"Login failed for {email} (HTTP {status}): {body}\n"
                     "Did you run the SETUP section of scripts/verify_auth.sql?")
        return body["access_token"]

    def rest(method, path, token=None, body=None, representation=False):
        headers = {"apikey": anon, "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if representation:
            headers["Prefer"] = "return=representation"
        return request(method, f"{url}/rest/v1{path}", headers, body)

    token_a = login(*CREDS_A)
    token_b = login(*CREDS_B)
    print("PASS  password login issues JWTs for both test users")

    s, b = rest("GET", "/profiles?select=user_id", token_a)
    check("A sees exactly own profile", s == 200 and b == [{"user_id": USER_A}], f"{s} {b}")

    s, b = rest("GET", "/projects?select=id,user_id", token_a)
    check("B's project invisible to A", s == 200 and b == [], f"{s} {b}")

    s, b = rest("GET", f"/profiles?user_id=eq.{USER_B}&select=user_id", token_a)
    check("direct query for B's profile returns nothing", s == 200 and b == [], f"{s} {b}")

    s, b = rest("GET", "/gate_sessions?select=score", token_a)
    check("gate score column denied to students (42501)",
          s in (401, 403) and (b or {}).get("code") == "42501", f"{s} {b}")

    s, b = rest("PATCH", f"/projects?id=eq.{PROJECT_B}", token_a,
                {"intake_purpose": "tampered"}, representation=True)
    check("A's update of B's project touches 0 rows", s in (200, 204) and (b or []) == [], f"{s} {b}")

    s, b = rest("POST", "/unlocks", token_a,
                {"user_id": USER_A, "project_id": PROJECT_B,
                 "phase_number": 1, "unlock_key": "forged"})
    check("unlock forgery denied (42501)",
          s in (401, 403) and (b or {}).get("code") == "42501", f"{s} {b}")

    s, b = rest("GET", "/profiles?select=user_id")  # anon: no Authorization header
    check("anon denied on profiles (42501)",
          s in (401, 403) and (b or {}).get("code") == "42501", f"{s} {b}")

    s, b = rest("GET", "/projects?select=id")
    check("anon denied on projects (42501)",
          s in (401, 403) and (b or {}).get("code") == "42501", f"{s} {b}")

    s, b = rest("PATCH", f"/profiles?user_id=eq.{USER_A}", token_a,
                {"display_name": "Test A"}, representation=True)
    check("A can update own profile", s == 200 and len(b or []) == 1, f"{s} {b}")

    s, b = rest("GET", "/projects?select=id,intake_purpose", token_b)
    check("B sees own project, untampered",
          s == 200 and b == [{"id": PROJECT_B, "intake_purpose": "user B purpose"}], f"{s} {b}")

    print()
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("All auth/RLS checks passed. Now run the CLEANUP section of scripts/verify_auth.sql.")


if __name__ == "__main__":
    main()
