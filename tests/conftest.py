import pytest
import asyncio
import aiosqlite
import os
import json
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
from app.engine import engine

# Use a separate database for testing
TEST_DB_PATH = "data/test_simulator.db"

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    # Setup environment variables for testing if needed
    os.environ["MQTT_HOST"] = "mock_host"
    os.environ["MQTT_PORT"] = "1883"
    yield
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

@pytest.fixture
async def db():
    # Initialize test database
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    
    # Path is imported in database.py, but used dynamically in get_db
    # We'll monkeypatch it in the app.database module
    import app.database
    original_path = app.database.DB_PATH
    app.database.DB_PATH = TEST_DB_PATH
    
    await init_db()
    
    async with aiosqlite.connect(TEST_DB_PATH) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        yield db_conn
    
    app.database.DB_PATH = original_path

@pytest.fixture
def mock_mqtt(mocker):
    # Mock the MQTT client in the engine
    mock_client = MagicMock()
    mocker.patch('paho.mqtt.client.Client', return_value=mock_client)
    # Also patch the instance on the engine
    engine.mqtt_client = mock_client
    return mock_client

@pytest.fixture
def client(db):
    # Override the get_db dependency to use our test DB
    async def override_get_db():
        async with aiosqlite.connect(TEST_DB_PATH) as db_conn:
            db_conn.row_factory = aiosqlite.Row
            yield db_conn

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
