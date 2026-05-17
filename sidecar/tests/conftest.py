"""Shared pytest fixtures.

The ``mock_database`` autouse fixture patches ``main.Database`` so that tests
which trigger the FastAPI lifespan (Starlette TestClient) never create a real
SQLite file.  Tests that exercise ``db.py`` directly import ``Database`` from
``db``, not from ``main``, so they are unaffected by this patch.

``WHISPER_MODEL`` is pinned to ``tiny`` so that tests which load the model
do not accidentally download or use the large production model.
"""

import os

# Pin to tiny before main.py is imported (MODEL_SIZE is read at import time).
os.environ.setdefault("WHISPER_MODEL", "tiny")

from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402


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
