"""Provider test controls.

Live provider tests are opt-in because they use real credentials and external
network calls. This keeps the default test suite hermetic.
"""

import os

import pytest


LIVE_PROVIDER_TESTS_ENV = "KABBALAH_RUN_LIVE_PROVIDER_TESTS"

LIVE_PROVIDER_TEST_FILES = {
    "test_deepseek_provider.py",
    "test_google_gemini_provider.py",
    "test_groq_provider.py",
    "test_mistral_provider.py",
    "test_openai_provider.py",
    "test_together_provider.py",
}


def pytest_collection_modifyitems(config, items):
    if os.getenv(LIVE_PROVIDER_TESTS_ENV) == "1":
        return

    skip_live = pytest.mark.skip(
        reason=f"live provider tests require {LIVE_PROVIDER_TESTS_ENV}=1"
    )

    for item in items:
        if item.path.name in LIVE_PROVIDER_TEST_FILES:
            item.add_marker(skip_live)
