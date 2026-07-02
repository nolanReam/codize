from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

FAKE_SERVICE_ROLE = "fake-service-role-key-for-tests"
FAKE_GEMINI = "fake-gemini-key-for-tests"
FAKE_OPENROUTER = "fake-openrouter-key-for-tests"


def test_settings_load_without_env(monkeypatch):
    for var in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
                "LLM_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL",
                "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "APP_ENV", "CORS_ORIGINS"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.app_env == "development"
    assert s.cors_origin_list == ["http://localhost:3000"]
    # LLM defaults fixed by the M7 instructions.
    assert s.llm_provider == "gemini"
    assert s.gemini_model == "gemini-2.5-flash-lite"
    assert s.openrouter_model == "cohere/north-mini-code:free"


def test_secret_values_never_in_repr_or_dump(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_ROLE)
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_GEMINI)
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_OPENROUTER)
    s = Settings(_env_file=None)
    exposed = repr(s) + str(s) + str(s.model_dump())
    assert FAKE_SERVICE_ROLE not in exposed
    assert FAKE_GEMINI not in exposed
    assert FAKE_OPENROUTER not in exposed
    # ...but the backend can still read them deliberately.
    assert s.supabase_service_role_key.get_secret_value() == FAKE_SERVICE_ROLE
    assert s.gemini_api_key.get_secret_value() == FAKE_GEMINI
    assert s.openrouter_api_key.get_secret_value() == FAKE_OPENROUTER


def test_cors_origins_parse_and_never_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://codize.example")
    s = Settings(_env_file=None)
    assert s.cors_origin_list == ["http://localhost:3000", "https://codize.example"]
    assert "*" not in s.cors_origin_list


def test_no_response_leaks_server_only_values(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_ROLE)
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_GEMINI)
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_OPENROUTER)
    client = TestClient(create_app())
    for path in ("/health", "/does-not-exist", "/openapi.json"):
        resp = client.get(path)
        assert FAKE_SERVICE_ROLE not in resp.text, path
        assert FAKE_GEMINI not in resp.text, path
        assert FAKE_OPENROUTER not in resp.text, path
