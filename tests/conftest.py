"""
Pytest configuration and fixtures for tests.

This file is automatically loaded by pytest and provides shared fixtures
and configuration for all tests.
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to Python path so tests can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock config module completely before any imports
config_mock = MagicMock()
config_mock.PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT = 0.1
config_mock.PAYMENT_UNDERPAYMENT_RETRY_ENABLED = True
config_mock.PAYMENT_UNDERPAYMENT_RETRY_TIMEOUT_MINUTES = 30
config_mock.PAYMENT_UNDERPAYMENT_PENALTY_PERCENT = 5.0
config_mock.PAYMENT_LATE_PENALTY_PERCENT = 5.0
config_mock.DATA_RETENTION_DAYS = 30
config_mock.REFERRAL_DATA_RETENTION_DAYS = 365
sys.modules['config'] = config_mock
