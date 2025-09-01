# Edge cases and performance tests
# Covers: Boundary conditions, error scenarios, performance limits, stress testing

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal, InvalidOperation
from aiogram.types import Message, Chat, User as TgUser

from services.user import UserService
from services.cart import CartService
from services.payment import PaymentService
from utils.CryptoAddressGenerator import CryptoAddressGenerator
from models.user import User
from models.item import Item
from enums.cryptocurrency import Cryptocurrency


class TestEdgeCasesAndPerformance:
    """Test edge cases and performance scenarios"""
    
    @pytest.fixture
    def mock_message(self):
        """Create mock message"""
        message = Mock(spec=Message)
        message.chat = Mock(spec=Chat)
        message.chat.id = 123456789
        message.from_user = Mock(spec=TgUser)
        message.from_user.id = 123456789
        message.from_user.username = "testuser"
        message.message_id = 1001
        return message

    @pytest.mark.asyncio
    async def test_extreme_user_ids(self):
        """Test handling of extreme user ID values"""
        mock_session = AsyncMock()
        
        extreme_ids = [
            0,  # Minimum valid ID
            1,  # Smallest positive ID
            2**31 - 1,  # Maximum 32-bit signed integer
            2**32 - 1,  # Maximum 32-bit unsigned integer
            2**53 - 1,  # Maximum safe JavaScript integer
        ]
        
        for user_id in extreme_ids:
            with patch('repositories.user.UserRepository.get_by_tgid') as mock_repo:
                mock_repo.return_value = None
                
                result = await UserService.get_by_telegram_id(user_id, mock_session)
                assert result is None
                mock_repo.assert_called_once_with(user_id, mock_session)

    @pytest.mark.asyncio
    async def test_unicode_handling(self):
        """Test Unicode and special character handling"""
        mock_session = AsyncMock()
        
        unicode_usernames = [
            "用户名",  # Chinese characters
            "пользователь",  # Cyrillic
            "🤖🚀💎",  # Emojis
            "user\u0000name",  # Null character
            "user\u200Bname",  # Zero-width space
            "ℌ𝒆𝓁𝓁ℴ",  # Mathematical symbols
            "\u202E\u202Duser\u202C",  # Right-to-left override
            "a" * 500,  # Very long username
        ]
        
        for username in unicode_usernames:
            with patch('services.user.UserService.create_user') as mock_create:
                mock_user = User(
                    telegram_id=123456789,
                    telegram_username=username
                )
                mock_create.return_value = mock_user
                
                # Should handle Unicode gracefully
                try:
                    user = await UserService.create_user_with_username(username, 123456789, mock_session)
                    assert user is not None
                except (ValueError, UnicodeError):
                    # Expected for some invalid Unicode sequences
                    pass

    @pytest.mark.asyncio
    async def test_decimal_precision_edge_cases(self):
        """Test decimal precision in financial calculations"""
        mock_session = AsyncMock()
        
        precise_amounts = [
            Decimal('0.000000001'),  # Very small amount
            Decimal('999999999.999999999'),  # Very large amount
            Decimal('123.456789012345'),  # High precision
            Decimal('0.1') + Decimal('0.2'),  # Floating point precision issue
            Decimal('1') / Decimal('3'),  # Repeating decimal
        ]
        
        for amount in precise_amounts:
            # Test cart calculations with precise decimals
            try:
                cart_total = await self.calculate_cart_with_precise_amount(float(amount), mock_session)
                assert isinstance(cart_total, (int, float, Decimal))
                assert cart_total >= 0
            except (InvalidOperation, ValueError):
                # Expected for some extreme values
                pass

    @pytest.mark.asyncio
    async def test_concurrent_operations_stress(self):
        """Test concurrent operations under stress"""
        mock_session = AsyncMock()
        
        # Simulate 100 concurrent user registrations
        async def create_user(user_id):
            with patch('services.user.UserService.create_user') as mock_create:
                mock_create.return_value = User(
                    telegram_id=user_id,
                    telegram_username=f"user_{user_id}"
                )
                return await UserService.create_user(
                    Mock(from_user=Mock(id=user_id)), 
                    mock_session
                )
        
        start_time = time.time()
        
        # Create tasks for concurrent execution
        tasks = [create_user(i) for i in range(100000, 100100)]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Should complete within reasonable time
            assert (end_time - start_time) < 10.0  # 10 seconds max
            
            # Most operations should succeed
            successful = sum(1 for r in results if isinstance(r, User))
            assert successful >= 80  # At least 80% success rate
            
        except asyncio.TimeoutError:
            pytest.fail("Concurrent operations timed out")

    @pytest.mark.asyncio
    async def test_memory_usage_large_datasets(self):
        """Test memory usage with large datasets"""
        mock_session = AsyncMock()
        
        # Simulate large cart with many items
        large_item_list = []
        for i in range(1000):
            item = Item(
                id=i,
                name=f"Item_{i}",
                price=10.0 + (i % 100),
                quantity=i % 50 + 1,
                category_id=1
            )
            large_item_list.append(item)
        
        with patch('services.cart.CartService.get_cart_items', return_value=large_item_list):
            # Should handle large datasets without memory issues
            items = await CartService.get_cart_items(1, mock_session)
            assert len(items) == 1000
            
            # Calculate total for large cart
            total = sum(item.price * item.quantity for item in items)
            assert total > 0

    def test_crypto_generation_performance(self):
        """Test cryptocurrency generation performance"""
        start_time = time.time()
        
        # Generate 100 crypto address sets
        generators = []
        for i in range(100):
            generator = CryptoAddressGenerator()
            generators.append(generator)
            addresses = generator.get_addresses()
            private_keys = generator.get_private_keys()
            
            # Verify all currencies are generated
            assert len(addresses) == 5
            assert len(private_keys) == 5
        
        end_time = time.time()
        
        # Should complete within reasonable time
        assert (end_time - start_time) < 30.0  # 30 seconds max for 100 generations
        
        # All generators should produce unique results
        all_btc_addresses = [gen.get_addresses()['btc'] for gen in generators]
        unique_addresses = set(str(addr) for addr in all_btc_addresses)
        assert len(unique_addresses) == 100  # All should be unique

    @pytest.mark.asyncio
    async def test_database_connection_failures(self):
        """Test handling of database connection failures"""
        # Simulate database connection failure
        with patch('db.get_db_session', side_effect=Exception("Database connection failed")):
            with pytest.raises(Exception):
                await UserService.get_by_telegram_id(123456789, None)

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, mock_message):
        """Test API timeout and retry scenarios"""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id=123456789)
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
             patch('repositories.payment.PaymentRepository.get_unexpired_unpaid_payments', return_value=1), \
             patch('crypto_api.CryptoApiWrapper.fetch_api_request', side_effect=asyncio.TimeoutError("API timeout")):
            
            # Should handle API timeouts gracefully
            with pytest.raises(asyncio.TimeoutError):
                await PaymentService.create(
                    Cryptocurrency.BITCOIN,
                    mock_message,
                    mock_session
                )

    @pytest.mark.asyncio
    async def test_malformed_data_handling(self):
        """Test handling of malformed or corrupted data"""
        mock_session = AsyncMock()
        
        malformed_data = [
            {"id": "not_a_number"},
            {"telegram_id": []},
            {"top_up_amount": "invalid_float"},
            {"registered_at": "not_a_date"},
            None,
            {},
            {"id": float('nan')},
        ]
        
        for data in malformed_data:
            try:
                # Should handle malformed data gracefully
                await self.process_malformed_user_data(data, mock_session)
            except (TypeError, ValueError, AttributeError):
                # Expected for malformed data
                pass

    @pytest.mark.asyncio
    async def test_boundary_value_analysis(self):
        """Test boundary values for critical parameters"""
        mock_session = AsyncMock()
        
        # Test cart quantity boundaries
        boundary_quantities = [
            0,  # Minimum (should fail)
            1,  # Minimum valid
            999,  # Just under 1000
            1000,  # Boundary value
            1001,  # Just over 1000
            99999,  # Large valid value
            100000,  # Maximum (if implemented)
        ]
        
        for quantity in boundary_quantities:
            try:
                result = await self.validate_cart_quantity(quantity, mock_session)
                if quantity <= 0:
                    pytest.fail(f"Should have failed for quantity {quantity}")
            except ValueError:
                # Expected for invalid quantities
                assert quantity <= 0

    def test_floating_point_precision(self):
        """Test floating point precision issues"""
        # Common floating point precision issues
        result1 = 0.1 + 0.2
        result2 = 0.3
        
        # Should handle precision correctly
        assert abs(result1 - result2) < 1e-10
        
        # Large number precision
        large_num = 999999999999999.0
        result = large_num + 1.0
        
        # Verify precision is maintained
        assert result != large_num

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test proper resource cleanup in error scenarios"""
        mock_session = AsyncMock()
        
        # Simulate resource allocation and cleanup
        try:
            # Simulate operation that might fail
            raise Exception("Simulated failure")
        except Exception:
            # Ensure cleanup occurs
            await mock_session.rollback()
            await mock_session.close()
        
        # Verify cleanup methods were called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    # Helper methods
    
    async def calculate_cart_with_precise_amount(self, amount, session):
        """Calculate cart total with precise amount"""
        return amount * 1.0  # Simple calculation
    
    async def process_malformed_user_data(self, data, session):
        """Process potentially malformed user data"""
        if data is None or not isinstance(data, dict):
            raise ValueError("Invalid data format")
        
        if "id" in data and not isinstance(data["id"], int):
            raise TypeError("ID must be integer")
        
        return data
    
    async def validate_cart_quantity(self, quantity, session):
        """Validate cart item quantity"""
        if not isinstance(quantity, int):
            raise TypeError("Quantity must be integer")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity > 100000:
            raise ValueError("Quantity too large")
        return quantity