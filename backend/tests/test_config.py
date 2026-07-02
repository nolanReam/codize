from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

FAKE_SERVICE_ROLE = "fake-service-role-key-for-tests"
FAKE_ANTHROPIC = "fake-anthropic-key-for-tests"


def test_settings_load_without_env(monkeypatch):
    for var in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
                "ANTHROPIC_API_KEY", "APP_ENV", "CORS_ORIGINS"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.app_env == "development"
    assert s.cors_origin_list == ["http://localhost:3000"]


def test_secret_values_never_in_repr_or_dump(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_ROLE)
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC)
    s = Settings(_env_file=None)
    exposed = repr(s) + str(s) + str(s.model_dump())
    assert FAKE_SERVICE_ROLE not in exposed
    assert FAKE_ANTHROPIC not in exposed
    # ...but the backend can still read them deliberately.
    assert s.supabase_service_role_key.get_secret_value() == FAKE_SERVICE_ROLE
    assert s.anthropic_api_key.get_secret_value() == FAKE_ANTHROPIC


def test_cors_origins_parse_and_never_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://codize.example")
    s = Settings(_env_file=None)
    assert s.cors_origin_list == ["http://localhost:3000", "https://codize.example"]
    assert "*" not in s.cors_origin_list


def test_no_response_leaks_server_only_values(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_SERVICE_ROLE)
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC)
    client = TestClient(create_app())
    for path in ("/health", "/does-not-exist", "/openapi.json"):
        resp = client.get(path)
        assert FAKE_SERVICE_ROLE not in resp.text, path
        assert FAKE_ANTHROPIC not in resp.text, path
