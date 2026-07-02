import pytest

from app.core import security
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clean_caches():
    """Settings and the JWKS client are lru_cached; tests that change env vars
    must not see another test's cached instances."""
    get_settings.cache_clear()
    security._jwks_client.cache_clear()
    yield
    get_settings.cache_clear()
    security._jwks_client.cache_clear()
