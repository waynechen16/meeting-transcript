"""Shared pytest fixtures.

The ``mock_database`` autouse fixture patches ``main.Database`` so that tests
which trigger the FastAPI lifespan (Starlette TestClient) never create a real
SQLite file.  Tests that exercise ``db.py`` directly import ``Database`` from
``db``, not from ``main``, so they are unaffected by this patch.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_database():
    mock = MagicMock()
    mock.init = AsyncMock()
    mock.close = AsyncMock()
    mock.create_session = AsyncMock()
    mock.end_session = AsyncMock()
    mock.save_segment = AsyncMock()
    with patch("main.Database", return_value=mock):
        yield mock
