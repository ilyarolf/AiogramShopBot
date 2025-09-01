# Test cases for PaymentService
# Covers: Payment creation, API integration, validation, security, error handling

import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram.types import Message, Chat

from services.payment import PaymentService
from enums.cryptocurrency import Cryptocurrency
from enums.payment import PaymentType
from models.payment import ProcessingPaymentDTO
from models.user import User


class TestPaymentService:
    """Test payment service functionality"""
    
    @pytest.fixture
    def mock_message(self):
        """Create mock Telegram message"""
        message = Mock(spec=Message)
        message.chat = Mock(spec=Chat)
        message.chat.id = 123456789
        message.message_id = 1001
        return message

    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        return User(
            id=1,
            telegram_id=123456789,
            telegram_username="test_user",
            top_up_amount=100.0,
            consume_records=50.0
        )

    @pytest.fixture
    def mock_payment_dto(self):
        """Create mock payment DTO"""
        return ProcessingPaymentDTO(
            id="payment_123",
            paymentType=PaymentType.DEPOSIT,
            fiatCurrency="USD",
            cryptoCurrency=Cryptocurrency.BITCOIN,
            address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            cryptoAmount=0.001,
            fiatAmount=50.0
        )

    @pytest.mark.asyncio
    async def test_create_payment_success(self, mock_message, mock_user, mock_payment_dto):
        """Test successful payment creation"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=2), \
             patch('services.payment.CryptoApiWrapper.fetch_api_request', return_value=mock_payment_dto.model_dump()), \
             patch('services.payment.PaymentRepository.create'), \
             patch('services.payment.session_commit'), \
             patch('services.payment.Localizator.get_text', return_value="Payment created: {crypto_name} {addr}"):
            
            result = await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            assert "Payment created" in result
            assert result is not None

    @pytest.mark.asyncio
    async def test_create_payment_too_many_requests(self, mock_message, mock_user):
        """Test payment creation with too many pending payments"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=5), \
             patch('services.payment.Localizator.get_text', return_value="Too many payment requests"):
            
            result = await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            assert result == "Too many payment requests"

    @pytest.mark.asyncio
    async def test_create_payment_api_failure(self, mock_message, mock_user):
        """Test payment creation with API failure"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=2), \
             patch('services.payment.CryptoApiWrapper.fetch_api_request', side_effect=Exception("API Error")):
            
            with pytest.raises(Exception):
                await PaymentService.create(
                    Cryptocurrency.BITCOIN,
                    mock_message,
                    mock_session
                )

    @pytest.mark.asyncio
    async def test_create_payment_invalid_cryptocurrency(self, mock_message, mock_user):
        """Test payment creation with invalid cryptocurrency"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=2):
            
            # Test with None cryptocurrency
            with pytest.raises((AttributeError, TypeError)):
                await PaymentService.create(
                    None,
                    mock_message,
                    mock_session
                )

    @pytest.mark.asyncio
    async def test_create_payment_user_not_found(self, mock_message):
        """Test payment creation when user not found"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=None):
            
            with pytest.raises(AttributeError):
                await PaymentService.create(
                    Cryptocurrency.BITCOIN,
                    mock_message,
                    mock_session
                )

    @pytest.mark.asyncio
    async def test_payment_dto_validation(self):
        """Test ProcessingPaymentDTO validation"""
        # Valid DTO
        valid_dto = ProcessingPaymentDTO(
            id="payment_123",
            paymentType=PaymentType.DEPOSIT,
            fiatCurrency="USD",
            cryptoCurrency=Cryptocurrency.BITCOIN
        )
        assert valid_dto.id == "payment_123"
        assert valid_dto.paymentType == PaymentType.DEPOSIT

    @pytest.mark.asyncio
    async def test_payment_security_headers(self, mock_message, mock_user, mock_payment_dto):
        """Test that API requests include proper security headers"""
        mock_session = AsyncMock()
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=2), \
             patch('services.payment.CryptoApiWrapper.fetch_api_request', return_value=mock_payment_dto.model_dump()) as mock_api, \
             patch('services.payment.PaymentRepository.create'), \
             patch('services.payment.session_commit'), \
             patch('services.payment.Localizator.get_text', return_value="Payment created"), \
             patch('services.payment.config.KRYPTO_EXPRESS_API_KEY', 'test_api_key'):
            
            await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            # Verify API was called with correct headers
            mock_api.assert_called_once()
            call_args = mock_api.call_args
            headers = call_args[1]['headers']
            assert 'X-Api-Key' in headers
            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_payment_amount_limits(self, mock_message, mock_user):
        """Test payment amount validation and limits"""
        mock_session = AsyncMock()
        
        # Test with extreme amounts
        extreme_payment_dto = ProcessingPaymentDTO(
            id="payment_extreme",
            paymentType=PaymentType.DEPOSIT,
            fiatCurrency="USD",
            cryptoCurrency=Cryptocurrency.BITCOIN,
            cryptoAmount=999999.99999999,  # Very large amount
            fiatAmount=999999999.99
        )
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=2), \
             patch('services.payment.CryptoApiWrapper.fetch_api_request', return_value=extreme_payment_dto.model_dump()), \
             patch('services.payment.PaymentRepository.create'), \
             patch('services.payment.session_commit'), \
             patch('services.payment.Localizator.get_text', return_value="Payment: {fiat_amount}"):
            
            result = await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_payment_creation(self, mock_message, mock_user):
        """Test concurrent payment creation scenarios"""
        mock_session = AsyncMock()
        
        # Simulate race condition where payment count changes between check and creation
        payment_counts = [4, 5]  # Changes from 4 to 5 during execution
        count_iter = iter(payment_counts)
        
        def mock_get_unexpired_payments(*args):
            return next(count_iter)
        
        with patch('services.payment.UserRepository.get_by_tgid', return_value=mock_user), \
             patch('services.payment.PaymentRepository.get_unexpired_unpaid_payments', side_effect=mock_get_unexpired_payments), \
             patch('services.payment.Localizator.get_text', return_value="Too many requests"):
            
            # First call should succeed (count=4)
            result1 = await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            # Second call should fail (count=5)
            result2 = await PaymentService.create(
                Cryptocurrency.BITCOIN,
                mock_message,
                mock_session
            )
            
            assert result2 == "Too many requests"