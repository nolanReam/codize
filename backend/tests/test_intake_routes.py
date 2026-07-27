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
    ("GET", "/intake/entry-profile"),
    ("PUT", "/intake/entry-profile"),
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
    app.state.test_project_repo = fake
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


def test_entry_profile_route_persists_only_student_choices_and_server_derives_fields(client):
    resp = client.put(
        "/intake/entry-profile",
        json={
            "current_situation": "already_building",
            "coding_confidence": "new_to_code",
            "ai_changed_files": "yes",
        },
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    profile = resp.json()["profile"]
    assert profile["recommended_start"] == "implementation_import"
    assert profile["guidance_depth"] == "more"
    assert profile["completed"] is True
    assert client.get("/intake/entry-profile", headers=auth_headers()).json()["profile"] == profile


@pytest.mark.parametrize(
    "forged",
    [
        {"recommended_start": "report"},
        {"recommendation": "prompt_builder"},
        {"guidance_depth": "minimal"},
        {"complete": True},
        {"completed": True},
        {"recovery_emphasis": True},
        {"workflow_complete": True},
        {"workflow_status": "active"},
        {"current_stage": "report"},
        {"stale": False},
        {"defense_state": "passed"},
        {"defense_ready": True},
        {"report_ready": True},
        {"workflow_artifacts": {}},
        {"phase": 1},
        {"user_id": USER_B},
    ],
)
def test_entry_profile_rejects_server_owned_or_unknown_fields(client, forged):
    resp = client.put(
        "/intake/entry-profile", json=forged, headers=auth_headers()
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": {"status": 422, "message": "Invalid request."}}


@pytest.mark.parametrize(
    "field",
    ["current_situation", "coding_confidence", "ai_changed_files"],
)
def test_entry_profile_rejects_explicit_null_choices(client, field):
    resp = client.put(
        "/intake/entry-profile", json={field: None}, headers=auth_headers()
    )
    assert resp.status_code == 422
    assert resp.json() == {"error": {"status": 422, "message": "Invalid request."}}


def test_second_user_update_cannot_change_the_first_users_profile(client):
    first = client.put(
        "/intake/entry-profile",
        json={"current_situation": "stuck", "coding_confidence": "know_basics"},
        headers=auth_headers(USER_A),
    ).json()["profile"]
    client.put(
        "/intake/entry-profile",
        json={
            "current_situation": "starting_fresh",
            "coding_confidence": "comfortable",
        },
        headers=auth_headers(USER_B),
    )
    assert client.get(
        "/intake/entry-profile", headers=auth_headers(USER_A)
    ).json()["profile"] == first


def test_hidden_ai_change_field_is_rejected_outside_already_building(client):
    resp = client.put(
        "/intake/entry-profile",
        json={"current_situation": "stuck", "ai_changed_files": "yes"},
        headers=auth_headers(),
    )
    assert resp.status_code == 422


def test_entry_profiles_are_owner_scoped(client):
    client.put(
        "/intake/entry-profile",
        json={"current_situation": "stuck", "coding_confidence": "know_basics"},
        headers=auth_headers(USER_A),
    )
    assert client.get(
        "/intake/entry-profile", headers=auth_headers(USER_B)
    ).json() == {"profile": None}


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


def test_editing_an_answered_question_before_completion_succeeds(client):
    answer_all_five(client)
    resp = client.post(
        "/intake/answers",
        json={"question": 3, "answer": "AP CSA Java, no framework yet."},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answers"]["stack"] == "AP CSA Java, no framework yet."
    assert body["next_question"] is None
    assert body["completed"] is False


def test_editing_after_completion_returns_controlled_409(client):
    answer_all_five(client)
    assert client.post("/intake/complete", headers=auth_headers()).status_code == 200
    resp = client.post(
        "/intake/answers",
        json={"question": 3, "answer": "changing my stack"},
        headers=auth_headers(),
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["message"] == "Intake is already completed."


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
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key-for-tests")
    answer_all_five(client)
    for method, path in (*ALL_ROUTES[:2], ("POST", "/intake/complete")):
        text = client.request(method, path, headers=auth_headers()).text
        assert "fake-service-role-key-for-tests" not in text
        assert "fake-gemini-key-for-tests" not in text


STUDYFLOW_ANSWERS = {
    1: (
        "A browser-based homework tracker where students add assignments with a title, "
        "subject, and due date; mark them complete; filter and delete them; and keep "
        "the data after refreshing through browser local storage."
    ),
    2: (
        "No accounts\nNo backend\nNo database\nNo AI product features\n"
        "No notifications\nNo calendar integration"
    ),
    3: (
        "Plain HTML, CSS, and JavaScript. The student understands basic variables, "
        "functions, arrays, conditionals, loops, DOM events, and local storage."
    ),
    4: (
        "The student becomes confused when coding AI changes several connected "
        "functions or modifies several files."
    ),
    5: "Produce a working and understandable first version within one week.",
}


def submit_answers(client, answers, user_id=USER_A):
    for number in range(1, 6):
        response = client.post(
            "/intake/answers",
            json={"question": number, "answer": answers[number]},
            headers=auth_headers(user_id),
        )
        assert response.status_code == 200


def test_production_studyflow_semantics_round_trip_through_authenticated_routes(client):
    submit_answers(client, STUDYFLOW_ANSWERS)
    before = client.get("/intake/status", headers=auth_headers()).json()
    assert before["answers"] == {
        "purpose": STUDYFLOW_ANSWERS[1],
        "scope": STUDYFLOW_ANSWERS[2],
        "stack": STUDYFLOW_ANSWERS[3],
        "self_assessment": STUDYFLOW_ANSWERS[4],
        "timeline": STUDYFLOW_ANSWERS[5],
    }

    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.status_code == 200
    assert completed.json() == {
        "completed": True,
        "archetype_id": 3,
        "archetype_name": "Browser App",
    }
    persisted = client.get("/intake/status", headers=auth_headers()).json()
    assert persisted["archetype_id"] == 3
    assert persisted["archetype_name"] == "Browser App"
    assert persisted["answers"] == before["answers"]


@pytest.mark.parametrize("field_number", [1, 2, 3, 4, 5])
@pytest.mark.parametrize(
    "meta_language",
    [
        "Claude changed several files.",
        "I use ChatGPT while coding.",
        "Codex wrote connected functions.",
        "Cursor generated most of the application.",
        "AI generated connected functions I do not understand.",
        "I do not understand some AI-generated code.",
        "I want help reviewing changes created by coding AI.",
        "AI sometimes changes files outside my request.",
        "Gemini helped me write the JavaScript.",
        "I want to learn how to use AI without losing control.",
        "Cursor wrote most of the code.",
        "I want help inspecting AI-generated changes.",
    ],
)
def test_ai_coding_tool_meta_language_in_any_free_text_answer_does_not_change_route_result(
    client, field_number, meta_language
):
    answers = dict(STUDYFLOW_ANSWERS)
    answers[field_number] = f"{answers[field_number]} {meta_language}"
    submit_answers(client, answers)
    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.status_code == 200
    assert completed.json()["archetype_name"] == "Browser App"


def test_browser_local_route_does_not_require_literal_backend_database_negations(client):
    answers = dict(STUDYFLOW_ANSWERS)
    answers[2] = (
        "Students add, complete, filter, and delete assignments. "
        "The current version is client-side only."
    )
    submit_answers(client, answers)
    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.status_code == 200
    assert completed.json()["archetype_name"] == "Browser App"


@pytest.mark.parametrize(
    ("scope", "expected_name"),
    [
        ("Save assignments in localStorage.", "Browser App"),
        ("Keep data after refresh using browser storage.", "Browser App"),
        ("Use IndexedDB in the browser.", "Browser App"),
        ("Persist settings client-side.", "Browser App"),
        ("Store everything locally in the browser.", "Browser App"),
        ("No backend or database.", "Browser App"),
        ("Without accounts, authentication, or a server.", "Browser App"),
        ("Backend, database, and AI features are out of scope.", "Browser App"),
        ("Do not add a backend.", "Browser App"),
        ("The current version is client-side only.", "Browser App"),
        ("A future version may have accounts, but version one does not.", "Browser App"),
        ("Users create accounts and sign in.", "Full-Stack Web App"),
        ("Assignments sync through a database.", "Full-Stack Web App"),
        ("The browser calls my backend API.", "Full-Stack Web App"),
        ("A server stores user data.", "Full-Stack Web App"),
        ("The app has authenticated user profiles.", "Full-Stack Web App"),
        ("Users submit notes and Gemini summarizes them.", "AI-Powered App"),
        ("The app includes a model-backed chatbot.", "AI-Powered App"),
        ("An LLM generates study questions.", "AI-Powered App"),
        ("The application calls OpenAI to analyze text.", "AI-Powered App"),
        ("The app uses localStorage now; a database may be added later.", "Browser App"),
        ("Keep the information on the current device.", "Browser App"),
        ("The app works offline and keeps local state.", "Browser App"),
        ("No account is required; each browser has its own data.", "Browser App"),
        ("I use ChatGPT to build it, but the product has no AI features.", "Browser App"),
        ("Gemini helped me write the JavaScript.", "Browser App"),
        ("The interface looks like a chatbot but uses scripted responses only.", "Browser App"),
        ("The app calls a weather API but has no backend or LLM.", "Browser App"),
        ("The app is named AI StudyFlow but contains no model behavior.", "Browser App"),
        ("No database, but the browser calls a custom backend API.", "Full-Stack Web App"),
        ("Assignments sync between devices through a database.", "Full-Stack Web App"),
        ("User profiles are stored in Supabase.", "Full-Stack Web App"),
        (
            "The browser uses localStorage as a cache, but the server is authoritative.",
            "Full-Stack Web App",
        ),
        ("The app works offline and syncs to the backend later.", "Full-Stack Web App"),
        ("No backend, but the browser calls my own API.", "Full-Stack Web App"),
        ("No database, but assignments sync between devices.", "Full-Stack Web App"),
        ("Users submit text to OpenAI for analysis.", "AI-Powered App"),
        ("Generate summaries from notes.", "AI-Powered App"),
        ("No AI feature, but Gemini generates summaries.", "AI-Powered App"),
        (
            "No backend, but Supabase authentication and database are required.",
            "Full-Stack Web App",
        ),
    ],
)
def test_authenticated_route_capability_regression_matrix(client, scope, expected_name):
    answers = dict(STUDYFLOW_ANSWERS)
    answers[2] = scope
    submit_answers(client, answers)
    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.status_code == 200
    assert completed.json()["archetype_name"] == expected_name


def test_completion_recalculates_and_replaces_a_stale_precompletion_archetype(client):
    submit_answers(client, STUDYFLOW_ANSWERS)
    repo = client.app.state.test_project_repo
    project = repo._rows[0]
    project["archetype_id"] = 1

    completed = client.post("/intake/complete", headers=auth_headers())
    assert completed.status_code == 200
    assert completed.json()["archetype_id"] == 3
    assert completed.json()["archetype_name"] == "Browser App"
    assert repo._rows[0]["archetype_id"] == 3


def test_completed_intake_refresh_returns_the_same_student_visible_label(client):
    submit_answers(client, STUDYFLOW_ANSWERS)
    completed = client.post("/intake/complete", headers=auth_headers()).json()
    refreshed = client.get("/intake/status", headers=auth_headers()).json()
    assert completed["archetype_name"] == "Browser App"
    assert refreshed["archetype_name"] == completed["archetype_name"]


def test_malformed_completed_archetype_state_does_not_return_a_false_label(client):
    submit_answers(client, STUDYFLOW_ANSWERS)
    repo = client.app.state.test_project_repo
    repo._rows[0]["archetype_id"] = 1
    repo._rows[0]["intake_completed_at"] = "2026-07-26T00:00:00+00:00"

    refreshed = client.get("/intake/status", headers=auth_headers())

    assert refreshed.status_code == 200
    assert refreshed.json()["archetype_id"] == 1
    assert refreshed.json()["archetype_name"] is None


def test_answer_route_rejects_unknown_fields_without_persisting(client):
    response = client.post(
        "/intake/answers",
        json={"question": 1, "answer": STUDYFLOW_ANSWERS[1], "archetype_id": 1},
        headers=auth_headers(),
    )
    assert response.status_code == 422
    assert response.json() == {"error": {"status": 422, "message": "Invalid request."}}
    assert client.get("/intake/status", headers=auth_headers()).json()["started"] is False


def test_answer_route_preserves_the_existing_unicode_character_limit(client):
    accepted = "🙂" * 4000
    response = client.post(
        "/intake/answers",
        json={"question": 1, "answer": accepted},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert response.json()["answers"]["purpose"] == accepted


def test_answer_route_rejects_over_limit_content_without_echoing_it(client):
    rejected = "private-student-prose-" + ("🙂" * 4001)
    response = client.post(
        "/intake/answers",
        json={"question": 1, "answer": rejected},
        headers=auth_headers(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "Answer is too long (max 4000 characters)."
    )
    assert "private-student-prose" not in response.text


def test_studyflow_route_state_is_isolated_from_another_user(client):
    submit_answers(client, STUDYFLOW_ANSWERS, USER_A)
    assert client.post(
        "/intake/complete", headers=auth_headers(USER_A)
    ).json()["archetype_name"] == "Browser App"

    other = client.get("/intake/status", headers=auth_headers(USER_B)).json()
    assert other["started"] is False
    assert other["archetype_id"] is None
