from __future__ import annotations

import os

import pytest

from app.config import Settings


# The health/API unit tests deliberately do not require external services.
# Real startup remains enabled in every normal Compose deployment.
os.environ.setdefault("KiN_DISABLE_DEPENDENCY_STARTUP", "true")


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", KiN_LOG_LEVEL="WARNING")


@pytest.fixture
def integration_enabled() -> bool:
    return os.getenv("KiN_RUN_INTEGRATION") == "1"
