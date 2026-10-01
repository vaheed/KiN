from __future__ import annotations

import os

import pytest

from app.config import Settings


# The health/API unit tests deliberately do not require external services.
# Real startup remains enabled in every normal Compose deployment.
os.environ.setdefault("KIN_DISABLE_DEPENDENCY_STARTUP", "true")


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", KIN_LOG_LEVEL="WARNING")


@pytest.fixture
def integration_enabled() -> bool:
    return os.getenv("KIN_RUN_INTEGRATION") == "1"
