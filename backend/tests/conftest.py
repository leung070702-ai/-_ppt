"""Shared pytest fixtures for backend tests."""

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    """Create an isolated in-process API client."""

    with TestClient(app) as test_client:
        yield test_client
