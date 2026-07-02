"""Intake route tests: auth-enforced, thin handlers, controlled errors.

Repository is overridden with the in-memory fake; auth uses the offline
ES256 pattern from test_archetype_routes.py.
"""

import time
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.core import security
from app.main import create_app
from app.services.project_repository import get_project_repository
from tests.fakes import InMemoryProjectRepository

_key = ec.generate_private_key(ec.SECP256R1())

USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

FIVE_ANSWERS = {
    1: "Help my study group track shared expenses so nobody loses money.",
    2: "A REST backend exposing expense data through HTTP endpoints.",
    3: "Python and FastAPI.",
    4: "Sometimes, depends",
    5: "About six weeks.",
}

ALL_ROUTES = (
    ("GET", "/intake/questions"),
    ("GET", "/intake/status"),
    ("POST", "/intake/answers"),
    ("POST", "/intake/complete"),
)


def auth_headers(user_id=USER_A):
    claims = {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 3600}
    return {"Authorization": f"Bearer {pyjwt.encode(claims, _key, algorithm='ES256')}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://stub-project.supabase.co")
    monkeypatch.setattr(
        security, "_jwks_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=_key.public_key())
        ),
    )
    app = create_app()
    # One shared fake per test so state persists across requests.
    fake = InMemoryProjectRepository()
    app.dependency_overrides[get_project_repository] = lambda: fake
    return TestClient(app)


def answer_all_five(client, user_id=USER_A):
    for n in (1, 2, 3, 4, 5):
        resp = client.post(
            "/intake/answers",
            json={"question": n, "answer": FIVE_ANSWERS[n]},
            headers=auth_headers(user_id),
        )
        assert resp.status_code == 200


def test_all_intake_routes_require_auth(client):
    for method, path in ALL_ROUTES:
        resp = client.request(method, path)
        assert resp.status_code == 401
        assert resp.json()["error"]["status"] == 401


def test_questions_route_returns_the_five_spec_questions(client):
    resp = client.get("/intake/questions", headers=auth_headers())
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 5
    assert questions[0]["text"] == (
        "What problem do you want to solve, and who does solving it help?"
    )
    assert [q["number"] for q in questions] == [1, 2, 3, 4, 5]


def test_full_intake_flow_through_routes(client):
    status = client.get("/intake/status", headers=auth_headers()).json()
    assert status["started"] is False and status["next_question"] == 1

    answer_all_five(client)

    resp = client.post("/intake/complete", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is True
    assert body["archetype_id"] == 2  # backend/API-only answers
    assert body["archetype_name"] == "REST API Backend"

    status = client.get("/intake/status", headers=auth_headers()).json()
    assert status["completed"] is True and status["archetype_id"] == 2


def test_out_of_order_answer_returns_controlled_409(client):
    resp = client.post(
        "/intake/answers",
        json={"question": 3, "answer": "skipping"},
        headers=auth_headers(),
    )
    assert resp.status_code == 409
    assert resp.json() == {
        "error": {"status": 409, "message": "Questions are answered in order; expected question 1."}
    }


@pytest.mark.parametrize("bad_question", [0, 6, -1, "one"])
def test_invalid_question_index_returns_controlled_422(client, bad_question):
    resp = client.post(
        "/intake/answers",
        json={"question": bad_question, "answer": "whatever"},
        headers=auth_headers(),
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": {"status": 422, "message": "Invalid request."}}


def test_empty_answer_returns_controlled_422(client):
    resp = client.post(
        "/intake/answers",
        json={"question": 1, "answer": "   "},
        headers=auth_headers(),
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": {"status": 422, "message": "Answer cannot be empty."}}


def test_premature_complete_returns_controlled_409(client):
    resp = client.post("/intake/complete", headers=auth_headers())
    assert resp.status_code == 409
    assert resp.json()["error"]["message"].startswith("Intake is not complete")


def test_users_cannot_see_each_others_intake_state(client):
    answer_all_five(client, USER_A)
    status_b = client.get("/intake/status", headers=auth_headers(USER_B)).json()
    assert status_b["started"] is False
    assert status_b["answered_questions"] == []


def test_intake_responses_contain_no_secrets(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-service-role-key-for-tests")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key-for-tests")
    answer_all_five(client)
    for method, path in (*ALL_ROUTES[:2], ("POST", "/intake/complete")):
        text = client.request(method, path, headers=auth_headers()).text
        assert "fake-service-role-key-for-tests" not in text
        assert "fake-anthropic-key-for-tests" not in text
