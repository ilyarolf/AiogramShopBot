# Test configuration and fixtures
# Provides common test fixtures and configuration for all test modules

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Mock ngrok before any imports that might trigger it
@pytest.fixture(autouse=True)
def mock_ngrok():
    """Mock ngrok to prevent actual tunneling during tests"""
    with patch('ngrok_executor.start_ngrok', return_value="http://mock-tunnel.ngrok.io"):
        yield

# Set test environment before imports
os.environ["RUNTIME_ENVIRONMENT"] = "test"
os.environ["WEBHOOK_HOST"] = "http://test-webhook.com"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CURRENCY"] = "USD"
os.environ["KRYPTO_EXPRESS_API_KEY"] = "test_api_key"
os.environ["KRYPTO_EXPRESS_API_URL"] = "https://api.test.com"

from models.base import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_async_session():
    """Create mock async database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = Mock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session