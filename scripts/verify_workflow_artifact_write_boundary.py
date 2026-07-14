"""Authenticated PostgREST + FastAPI smoke for the M16S.1 write boundary.

Run only after the forward migration is deployed to a known-safe environment:

    SUPABASE_URL=... SUPABASE_ANON_KEY=... \
    SUPABASE_SERVICE_ROLE_KEY=... CODIZE_API_BASE_URL=... \
        python scripts/verify_workflow_artifact_write_boundary.py

The script creates two temporary confirmed users through the trusted Auth
admin API, exercises the real Data API with their JWTs, verifies one real
FastAPI workflow save, and deletes both users in a finally block. It never
prints credentials, tokens, keys, artifact bodies, or user-provided content.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request


failures: list[str] = []


def request(method: str, url: str, headers: dict[str, str], body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else None
        except (TypeError, ValueError):
            return exc.code, None
    except urllib.error.URLError:
        return 0, None


def check(name: str, passed: bool) -> None:
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def permission_denied(status: int, body) -> bool:
    return status in (401, 403) and isinstance(body, dict) and body.get("code") == "42501"


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    publishable = os.environ.get("SUPABASE_ANON_KEY", "")
    secret = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    api_base = os.environ.get("CODIZE_API_BASE_URL", "").rstrip("/")
    if not all((supabase_url, publishable, secret, api_base)):
        sys.exit(
            "Set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, "
            "and CODIZE_API_BASE_URL."
        )

    suffix = secrets.token_hex(6)
    emails = [f"m16s1-{suffix}-a@codize.local", f"m16s1-{suffix}-b@codize.local"]
    passwords = [secrets.token_urlsafe(24), secrets.token_urlsafe(24)]
    user_ids: list[str] = []

    admin_headers = {
        "apikey": secret,
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }
    service_headers = {
        **admin_headers,
        "Prefer": "return=representation",
    }

    def admin(method: str, path: str, body=None):
        return request(method, f"{supabase_url}/auth/v1/admin{path}", admin_headers, body)

    def rest(method: str, path: str, token: str | None = None, body=None, prefer=None):
        headers = {"apikey": publishable, "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if prefer:
            headers["Prefer"] = prefer
        return request(method, f"{supabase_url}/rest/v1{path}", headers, body)

    def service_rest(method: str, path: str, body=None, prefer=None):
        headers = dict(service_headers)
        if prefer:
            headers["Prefer"] = prefer
        return request(method, f"{supabase_url}/rest/v1{path}", headers, body)

    def login(email: str, password: str) -> str:
        status, body = request(
            "POST",
            f"{supabase_url}/auth/v1/token?grant_type=password",
            {"apikey": publishable, "Content-Type": "application/json"},
            {"email": email, "password": password},
        )
        if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
            raise RuntimeError("temporary user login failed")
        return body["access_token"]

    def api(method: str, path: str, token: str, body=None):
        return request(
            method,
            f"{api_base}{path}",
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            body,
        )

    try:
        for email, password in zip(emails, passwords, strict=True):
            status, body = admin(
                "POST",
                "/users",
                {"email": email, "password": password, "email_confirm": True},
            )
            if status not in (200, 201) or not isinstance(body, dict) or not body.get("id"):
                raise RuntimeError("temporary user creation failed")
            user_ids.append(body["id"])
        check("temporary users created", len(user_ids) == 2)

        phase_one = {
            "phase": 1,
            "phase_title": "Foundation",
            "core_concept": "Request flow",
            "ai_appropriate_tasks": ["Draft one route"],
            "human_required_tasks": ["Review the route"],
            "explanation_gate_targets": ["Explain the request flow"],
            "gate_depth": "implementation",
            "unlock_condition": "Explain the phase",
            "functional_unlock": "Continue",
        }
        phase_two = {
            **phase_one,
            "phase": 2,
            "phase_title": "Validation",
            "core_concept": "Verification flow",
        }
        roadmap = {
            "archetype_id": 2,
            "phases": [phase_one, phase_two],
        }
        project_rows = []
        for index, user_id in enumerate(user_ids):
            payload = {
                "user_id": user_id,
                "intake_purpose": f"M16S.1 temporary project {index + 1}",
            }
            if index == 0:
                payload.update({
                    "intake_scope": "One temporary route",
                    "intake_stack": "FastAPI",
                    "intake_self_assessment": "Intermediate",
                    "intake_timeline": "Today",
                    "intake_completed_at": "2026-07-14T00:00:00Z",
                    "archetype_id": 2,
                    "roadmap": roadmap,
                    "status": "active",
                    "task_progress": {"1": ["ai-1"]},
                    "workflow_artifacts": {},
                })
            status, body = service_rest("POST", "/projects", payload)
            if status not in (200, 201) or not isinstance(body, list) or len(body) != 1:
                raise RuntimeError("temporary project creation failed")
            project_rows.append(body[0])
        project_a = project_rows[0]
        project_b = project_rows[1]

        token_a = login(emails[0], passwords[0])
        token_b = login(emails[1], passwords[1])
        check("owner can authenticate", bool(token_a))

        select = urllib.parse.quote("id,user_id,workflow_artifacts", safe=",")
        status, body = rest("GET", f"/projects?select={select}", token_a)
        check(
            "owner can read own project and workflow state",
            status == 200 and isinstance(body, list) and len(body) == 1
            and body[0].get("id") == project_a["id"],
        )

        protected_attempts = (
            ("full workflow-artifact replacement", {"workflow_artifacts": {"forged": True}}),
            ("nested workflow-artifact replacement", {
                "workflow_artifacts": {"1": {"change_map": {"status": "confirmed"}}}
            }),
            ("mixed project/workflow update", {
                "intake_purpose": "smuggled",
                "workflow_artifacts": {"forged": True},
            }),
        )
        for label, payload in protected_attempts:
            status, body = rest(
                "PATCH", f"/projects?id=eq.{project_a['id']}", token_a, payload,
                "return=representation",
            )
            check(f"owner direct {label} denied", permission_denied(status, body))

        status, body = rest(
            "POST", "/projects?on_conflict=id", token_a,
            {"id": project_a["id"], "user_id": user_ids[0],
             "workflow_artifacts": {"forged": True}},
            "return=representation,resolution=merge-duplicates",
        )
        check("owner protected upsert denied", permission_denied(status, body))

        status, body = rest(
            "POST", "/projects", token_a,
            {"user_id": user_ids[0], "intake_purpose": "forged",
             "workflow_artifacts": {"forged": True}},
        )
        check("owner forged project insert denied", permission_denied(status, body))

        status, body = rest("GET", f"/projects?id=eq.{project_a['id']}&select=id", token_b)
        check("another user cannot read or infer owner project", status == 200 and body == [])
        status, body = rest(
            "PATCH", f"/projects?id=eq.{project_a['id']}", token_b,
            {"workflow_artifacts": {"forged": True}},
        )
        check(
            "another user cannot update owner project",
            permission_denied(status, body) or (status in (200, 204) and (body or []) == []),
        )

        status, body = rest("GET", "/projects?select=id")
        check("anonymous project read denied", permission_denied(status, body))
        status, body = rest(
            "POST", "/projects", body={"user_id": user_ids[0], "workflow_artifacts": {}},
        )
        check("anonymous project write denied", permission_denied(status, body))

        # Restore only temporary owner-A rows through the trusted path so this
        # smoke can still verify backend compatibility when run pre-deployment
        # to demonstrate the old direct-write vulnerability.
        service_rest(
            "DELETE", f"/projects?user_id=eq.{user_ids[0]}&id=neq.{project_a['id']}"
        )
        service_rest(
            "PATCH", f"/projects?id=eq.{project_a['id']}&user_id=eq.{user_ids[0]}",
            {
                "intake_purpose": "M16S.1 temporary project 1",
                "intake_scope": "One temporary route",
                "intake_stack": "FastAPI",
                "intake_self_assessment": "Intermediate",
                "intake_timeline": "Today",
                "intake_completed_at": "2026-07-14T00:00:00Z",
                "archetype_id": 2,
                "roadmap": roadmap,
                "status": "active",
                "task_progress": {"1": ["ai-1"]},
                "workflow_artifacts": {},
            },
        )

        trusted_value = {"1": {"prompt_builder": {"saved_at": "trusted-smoke"}}}
        status, body = service_rest(
            "PATCH", f"/projects?id=eq.{project_a['id']}&user_id=eq.{user_ids[0]}",
            {"workflow_artifacts": trusted_value},
        )
        check("trusted backend can update workflow artifacts", status == 200 and len(body or []) == 1)

        status, body = service_rest(
            "GET", f"/projects?id=eq.{project_a['id']}"
            "&select=user_id,intake_purpose,task_progress,workflow_artifacts"
        )
        check(
            "trusted write preserves ownership and neighboring project state",
            status == 200 and len(body or []) == 1
            and body[0].get("user_id") == user_ids[0]
            and body[0].get("intake_purpose") == "M16S.1 temporary project 1"
            and body[0].get("task_progress") == {"1": ["ai-1"]},
        )

        prompt = {
            "inputs": {"goal": "Confirm the trusted workflow write path"},
            "generated_prompt": "Add one route, explain it, and do not change unrelated files.",
            "why_stronger": "The request is scoped and asks for an explanation.",
        }
        status, body = api("PUT", "/workflow/1/prompt_builder", token_a, prompt)
        check("FastAPI Prompt Builder save succeeds", status == 200)
        status, body = api("GET", "/workflow/1", token_a)
        check(
            "FastAPI workflow read returns the saved artifact",
            status == 200 and isinstance(body, dict)
            and isinstance(body.get("sections", {}).get("prompt_builder"), dict),
        )

        implementation_import = {
            "source_kind": "git_diff",
            "content": (
                "diff --git a/app/routes/items.py b/app/routes/items.py\n"
                "+    return owner_items"
            ),
            "changed_files": ["app/routes/items.py"],
            "student_summary": "The implementation added an owner-filtered item route.",
        }
        status, body = api(
            "PUT", "/workflow/1/implementation_import", token_a,
            implementation_import,
        )
        check("FastAPI Implementation Import save succeeds", status == 200)

        status, change_map = api("POST", "/workflow/1/change-map/generate", token_a)
        check(
            "FastAPI Change Map generation succeeds",
            status == 200 and isinstance(change_map, dict) and bool(change_map.get("items")),
        )
        inferred_items = change_map.get("items", []) if isinstance(change_map, dict) else []
        change_updates = [
            {"item_id": item["item_id"], "student_decision": "confirmed"}
            for item in inferred_items
            if item.get("origin") == "ai_inferred" and item.get("item_id")
        ]
        status, body = api(
            "PUT", "/workflow/1/change-map", token_a, {"updates": change_updates}
        )
        check("FastAPI Change Map save succeeds", status == 200)
        status, body = api("POST", "/workflow/1/change-map/confirm", token_a)
        check("FastAPI Change Map confirmation succeeds", status == 200)

        status, review_response = api(
            "POST", "/workflow/1/review/from-change-map", token_a
        )
        review_artifact = (
            review_response.get("artifact", {})
            if isinstance(review_response, dict) else {}
        )
        check(
            "FastAPI linked Review initialization succeeds",
            status == 200 and bool(review_artifact.get("review_targets")),
        )
        review_updates = [
            {
                "review_target_id": target["review_target_id"],
                "review_decision": "needs_verification",
                "student_rationale": "Verify this behavior through the public route.",
            }
            for target in review_artifact.get("review_targets", [])
        ]
        status, body = api(
            "PUT", "/workflow/1/review_board", token_a,
            {"target_updates": review_updates},
        )
        check("FastAPI Review update succeeds", status == 200)

        status, verification_response = api(
            "POST", "/workflow/1/verification/from-review", token_a
        )
        verification_artifact = (
            verification_response.get("artifact", {})
            if isinstance(verification_response, dict) else {}
        )
        check(
            "FastAPI linked Verification initialization succeeds",
            status == 200 and bool(verification_artifact.get("verification_targets")),
        )
        verification_updates = [
            {
                "verification_target_id": target["verification_target_id"],
                "student_check": "Call the route as the owner and inspect the response.",
                "result": "pass",
                "result_notes": "The temporary owner received the expected response.",
            }
            for target in verification_artifact.get("verification_targets", [])
        ]
        status, body = api(
            "PUT", "/workflow/1/verification", token_a,
            {"target_updates": verification_updates},
        )
        check("FastAPI Verification update succeeds", status == 200)

        status, body = api("GET", "/workflow/1", token_a)
        sections = body.get("sections", {}) if isinstance(body, dict) else {}
        check(
            "neighboring workflow sections and Change Map remain intact",
            status == 200
            and all(
                isinstance(sections.get(section), dict)
                for section in (
                    "prompt_builder", "implementation_import", "review_board",
                    "verification",
                )
            )
            and isinstance(body.get("change_map"), dict),
        )
        status, body = api("GET", "/workflow/2", token_a)
        phase_two_sections = body.get("sections", {}) if isinstance(body, dict) else {}
        check(
            "FastAPI workflow writes remain phase-isolated",
            status == 200
            and body.get("change_map") is None
            and all(value is None for value in phase_two_sections.values()),
        )

        status, body = rest("DELETE", f"/projects?id=eq.{project_a['id']}", token_a)
        check("owner direct project delete denied", permission_denied(status, body))

        status, body = service_rest("GET", f"/projects?id=eq.{project_b['id']}&select=id")
        check("temporary second-owner project remained intact", status == 200 and len(body or []) == 1)
    except (RuntimeError, KeyError) as exc:
        print(f"FAIL  smoke setup or execution failed ({exc})")
        failures.append("smoke setup or execution")
    finally:
        for user_id in reversed(user_ids):
            admin("DELETE", f"/users/{user_id}")
        if user_ids:
            encoded = ",".join(user_ids)
            status, body = service_rest("GET", f"/projects?user_id=in.({encoded})&select=id")
            check("temporary projects cleaned by user cascade", status == 200 and body == [])

    print()
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
        raise SystemExit(1)
    print("All workflow-artifact write-boundary smoke checks passed; cleanup complete.")


if __name__ == "__main__":
    main()
