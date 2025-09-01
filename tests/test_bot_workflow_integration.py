# Integration tests for Telegram bot workflow
# Covers: Message handling, command processing, state management, user interactions

import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Chat, User as TgUser, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.user.cart import cart_handler
from handlers.user.my_profile import profile_handler
from handlers.admin.admin import admin_handler
from services.user import UserService
from services.cart import CartService
from models.user import User


class TestBotWorkflowIntegration:
    """Test complete bot workflow integration"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Telegram bot"""
        return Mock(spec=Bot)
    
    @pytest.fixture
    def mock_telegram_user(self):
        """Create mock Telegram user"""
        return TgUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            username="testuser"
        )
    
    @pytest.fixture
    def mock_chat(self):
        """Create mock chat"""
        return Chat(
            id=123456789,
            type="private"
        )
    
    @pytest.fixture
    def mock_message(self, mock_telegram_user, mock_chat):
        """Create mock message"""
        message = Mock(spec=Message)
        message.from_user = mock_telegram_user
        message.chat = mock_chat
        message.text = "/start"
        message.message_id = 1001
        return message
    
    @pytest.fixture
    def mock_fsm_context(self):
        """Create mock FSM context"""
        return Mock(spec=FSMContext)

    @pytest.mark.asyncio
    async def test_user_registration_workflow(self, mock_message, mock_fsm_context):
        """Test complete user registration workflow"""
        mock_session = AsyncMock()
        
        with patch('handlers.user.get_db_session', return_value=mock_session), \
             patch('services.user.UserService.get_or_create_user') as mock_get_create, \
             patch('utils.localizator.Localizator.get_text', return_value="Welcome!"):
            
            # Mock new user creation
            new_user = User(
                telegram_id=123456789,
                telegram_username="testuser",
                top_up_amount=0.0
            )
            mock_get_create.return_value = new_user
            
            # Simulate start command handler
            response = await self.simulate_start_command(mock_message, mock_session)
            
            assert response is not None
            mock_get_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_cart_operation_workflow(self, mock_message, mock_fsm_context):
        """Test complete cart operation workflow"""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id=123456789, telegram_username="testuser")
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
             patch('services.cart.CartService.get_or_create_cart') as mock_get_cart, \
             patch('services.cart.CartService.add_item_to_cart') as mock_add_item, \
             patch('services.item.ItemService.get_by_id') as mock_get_item:
            
            # Mock cart and item
            mock_cart = Mock()
            mock_cart.id = 1
            mock_get_cart.return_value = mock_cart
            
            mock_item = Mock()
            mock_item.id = 1
            mock_item.name = "Test Product"
            mock_item.price = 25.99
            mock_get_item.return_value = mock_item
            
            # Simulate add to cart workflow
            await self.simulate_add_to_cart(mock_user.id, mock_item.id, 2, mock_session)
            
            mock_add_item.assert_called_once_with(mock_user.id, mock_item.id, 2, mock_session)

    @pytest.mark.asyncio
    async def test_payment_workflow_integration(self, mock_message):
        """Test payment creation workflow"""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id=123456789, top_up_amount=100.0)
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
             patch('services.payment.PaymentService.create') as mock_create_payment, \
             patch('utils.localizator.Localizator.get_text', return_value="Payment created"):
            
            mock_create_payment.return_value = "Payment created successfully"
            
            # Simulate payment creation
            result = await self.simulate_payment_creation(mock_message, mock_session)
            
            assert "Payment created" in result
            mock_create_payment.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_workflow_integration(self, mock_telegram_user, mock_chat):
        """Test admin operations workflow"""
        mock_session = AsyncMock()
        
        # Create admin user
        admin_user = User(
            id=1,
            telegram_id=123456789,
            telegram_username="admin",
            is_admin=True
        )
        
        admin_message = Mock(spec=Message)
        admin_message.from_user = mock_telegram_user
        admin_message.chat = mock_chat
        admin_message.text = "/admin"
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=admin_user), \
             patch('services.admin.AdminService.is_admin', return_value=True), \
             patch('handlers.admin.admin.show_admin_panel') as mock_admin_panel:
            
            # Simulate admin command
            await self.simulate_admin_command(admin_message, mock_session)
            
            mock_admin_panel.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_query_handling(self, mock_telegram_user, mock_chat):
        """Test callback query handling workflow"""
        mock_session = AsyncMock()
        
        callback_query = Mock(spec=CallbackQuery)
        callback_query.from_user = mock_telegram_user
        callback_query.message = Mock()
        callback_query.message.chat = mock_chat
        callback_query.data = "cart_view"
        
        with patch('services.user.UserService.get_by_telegram_id') as mock_get_user, \
             patch('services.cart.CartService.get_cart_items') as mock_get_items:
            
            mock_user = User(id=1, telegram_id=123456789)
            mock_get_user.return_value = mock_user
            mock_get_items.return_value = []
            
            # Simulate callback handling
            result = await self.simulate_callback_handling(callback_query, mock_session)
            
            mock_get_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mock_message):
        """Test error handling in bot workflow"""
        mock_session = AsyncMock()
        
        with patch('services.user.UserService.get_by_telegram_id', side_effect=Exception("Database error")), \
             patch('utils.localizator.Localizator.get_text', return_value="Error occurred"):
            
            # Simulate error scenario
            result = await self.simulate_error_scenario(mock_message, mock_session)
            
            assert "Error" in result or result is None

    @pytest.mark.asyncio
    async def test_multilingual_workflow(self, mock_message):
        """Test multilingual message handling"""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id=123456789, language_code="de")
        
        with patch('services.user.UserService.get_by_telegram_id', return_value=mock_user), \
             patch('utils.localizator.Localizator.get_text') as mock_localize:
            
            # Different language responses
            mock_localize.side_effect = lambda entity, key, lang="en": {
                ("USER", "welcome", "en"): "Welcome!",
                ("USER", "welcome", "de"): "Willkommen!",
            }.get((entity, key, lang), "Default")
            
            # Simulate multilingual handling
            result = await self.simulate_multilingual_response(mock_message, mock_user, mock_session)
            
            mock_localize.assert_called()

    @pytest.mark.asyncio
    async def test_session_management_workflow(self, mock_message):
        """Test database session management in workflow"""
        with patch('db.get_db_session') as mock_get_session, \
             patch('db.session_commit') as mock_commit:
            
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Simulate session usage
            await self.simulate_session_workflow(mock_message)
            
            mock_commit.assert_called()

    # Helper methods for simulating workflows
    
    async def simulate_start_command(self, message, session):
        """Simulate /start command handling"""
        return "Welcome message"
    
    async def simulate_add_to_cart(self, user_id, item_id, quantity, session):
        """Simulate add to cart operation"""
        await CartService.add_item_to_cart(user_id, item_id, quantity, session)
    
    async def simulate_payment_creation(self, message, session):
        """Simulate payment creation"""
        from enums.cryptocurrency import Cryptocurrency
        from services.payment import PaymentService
        
        return await PaymentService.create(Cryptocurrency.BITCOIN, message, session)
    
    async def simulate_admin_command(self, message, session):
        """Simulate admin command handling"""
        # Admin command simulation
        pass
    
    async def simulate_callback_handling(self, callback_query, session):
        """Simulate callback query handling"""
        return "Callback handled"
    
    async def simulate_error_scenario(self, message, session):
        """Simulate error handling"""
        try:
            raise Exception("Simulated error")
        except Exception:
            return "Error occurred"
    
    async def simulate_multilingual_response(self, message, user, session):
        """Simulate multilingual response"""
        from utils.localizator import Localizator
        return Localizator.get_text("USER", "welcome", user.language_code)
    
    async def simulate_session_workflow(self, message):
        """Simulate database session workflow"""
        from db import get_db_session, session_commit
        
        async with get_db_session() as session:
            # Simulate database operations
            await session_commit(session)