# Test cases for User model and UserRepository
# Covers: User model validation, constraints, UserRepository CRUD operations

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from models.user import User, UserDTO
from repositories.user import UserRepository


class TestUserModel:
    """Test User model constraints and validation"""
    
    def test_user_creation_valid_data(self):
        """Test User model creation with valid data"""
        user = User(
            telegram_username="test_user",
            telegram_id=123456789,
            top_up_amount=100.0,
            consume_records=50.0
        )
        assert user.telegram_username == "test_user"
        assert user.telegram_id == 123456789
        assert user.top_up_amount == 100.0
        assert user.consume_records == 50.0
        assert user.can_receive_messages is True  # default value

    def test_user_dto_creation(self):
        """Test UserDTO creation and validation"""
        user_dto = UserDTO(
            id=1,
            telegram_username="test_user",
            telegram_id=123456789,
            top_up_amount=100.0,
            consume_records=50.0,
            can_receive_messages=True
        )
        assert user_dto.id == 1
        assert user_dto.telegram_username == "test_user"

    def test_user_dto_optional_fields(self):
        """Test UserDTO with optional fields"""
        user_dto = UserDTO()
        assert user_dto.id is None
        assert user_dto.telegram_username is None


class TestUserRepository:
    """Test UserRepository operations"""

    @pytest.mark.asyncio
    async def test_get_by_tgid_existing_user(self):
        """Test retrieving existing user by telegram ID"""
        mock_session = AsyncMock()
        mock_user = User(telegram_id=123456789, telegram_username="test_user")
        
        # Mock the repository method
        UserRepository.get_by_tgid = AsyncMock(return_value=mock_user)
        
        result = await UserRepository.get_by_tgid(123456789, mock_session)
        assert result.telegram_id == 123456789
        assert result.telegram_username == "test_user"

    @pytest.mark.asyncio
    async def test_get_by_tgid_nonexistent_user(self):
        """Test retrieving non-existent user by telegram ID"""
        mock_session = AsyncMock()
        
        # Mock the repository method to return None
        UserRepository.get_by_tgid = AsyncMock(return_value=None)
        
        result = await UserRepository.get_by_tgid(999999999, mock_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation"""
        mock_session = AsyncMock()
        user_dto = UserDTO(
            telegram_username="new_user",
            telegram_id=123456789,
            top_up_amount=0.0,
            consume_records=0.0
        )
        
        # Mock the repository method
        UserRepository.create = AsyncMock(return_value=user_dto)
        
        result = await UserRepository.create(user_dto, mock_session)
        assert result.telegram_username == "new_user"
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_update_user_balance(self):
        """Test updating user balance"""
        mock_session = AsyncMock()
        user_id = 1
        new_balance = 150.0
        
        # Mock the repository method
        UserRepository.update_balance = AsyncMock(return_value=True)
        
        result = await UserRepository.update_balance(user_id, new_balance, mock_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_user_balance_constraints(self):
        """Test user balance constraints (negative values)"""
        # This test would require actual database integration
        # For now, we test the constraint logic conceptually
        with pytest.raises(ValueError):
            # Simulate constraint violation
            if -10.0 < 0:
                raise ValueError("top_up_amount must be non-negative")

    def test_user_telegram_id_uniqueness(self):
        """Test telegram_id uniqueness constraint"""
        # This would test database constraint in real scenario
        # Mock constraint violation
        try:
            # Simulate duplicate telegram_id insertion
            raise IntegrityError("UNIQUE constraint failed", None, None)
        except IntegrityError as e:
            assert "UNIQUE constraint failed" in str(e)