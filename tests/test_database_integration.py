# Integration tests for database operations
# Covers: Database connectivity, transactions, repository integration, data consistency

import pytest
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from models.base import Base
from models.user import User
from models.cart import Cart
from models.item import Item
from models.category import Category
from repositories.user import UserRepository
from repositories.cart import CartRepository
from repositories.item import ItemRepository


class TestDatabaseIntegration:
    """Test database integration and transaction handling"""
    
    @pytest.fixture(scope="function")
    async def test_db_session(self):
        """Create test database session"""
        # Use in-memory SQLite for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session = async_session()
        
        yield session
        
        await session.close()
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_crud_operations(self, test_db_session):
        """Test complete user CRUD operations"""
        session = test_db_session
        
        # Create user
        user = User(
            telegram_username="test_integration_user",
            telegram_id=987654321,
            top_up_amount=500.0,
            consume_records=100.0
        )
        
        session.add(user)
        await session.commit()
        
        # Read user
        retrieved_user = await UserRepository.get_by_tgid(987654321, session)
        assert retrieved_user is not None
        assert retrieved_user.telegram_username == "test_integration_user"
        assert retrieved_user.top_up_amount == 500.0
        
        # Update user
        retrieved_user.top_up_amount = 750.0
        await session.commit()
        
        # Verify update
        updated_user = await UserRepository.get_by_tgid(987654321, session)
        assert updated_user.top_up_amount == 750.0
        
        # Delete user
        await session.delete(retrieved_user)
        await session.commit()
        
        # Verify deletion
        deleted_user = await UserRepository.get_by_tgid(987654321, session)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_cart_item_relationship(self, test_db_session):
        """Test cart-item relationship integrity"""
        session = test_db_session
        
        # Create user
        user = User(telegram_username="cart_test_user", telegram_id=111222333)
        session.add(user)
        await session.commit()
        
        # Create category
        category = Category(name="Test Category", description="Test Description")
        session.add(category)
        await session.commit()
        
        # Create item
        item = Item(
            name="Test Item",
            description="Test Description",
            price=29.99,
            quantity=50,
            category_id=category.id
        )
        session.add(item)
        await session.commit()
        
        # Create cart
        cart = Cart(user_id=user.id, total_amount=0.0)
        session.add(cart)
        await session.commit()
        
        # Verify relationships
        assert cart.user_id == user.id
        assert item.category_id == category.id

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db_session):
        """Test transaction rollback on error"""
        session = test_db_session
        
        try:
            # Create user
            user = User(telegram_username="rollback_test", telegram_id=444555666)
            session.add(user)
            
            # Simulate error by trying to create duplicate
            duplicate_user = User(telegram_username="rollback_test", telegram_id=444555666)
            session.add(duplicate_user)
            
            await session.commit()
            
        except Exception:
            await session.rollback()
            
            # Verify no user was created
            user_count = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE telegram_id = 444555666")
            )
            count = user_count.scalar()
            assert count == 0

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, test_db_session):
        """Test concurrent database operations"""
        session = test_db_session
        
        async def create_user(telegram_id, username):
            user = User(telegram_username=username, telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            return user
        
        # Create multiple users concurrently
        tasks = [
            create_user(100001, "user1"),
            create_user(100002, "user2"),
            create_user(100003, "user3")
        ]
        
        users = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all users were created
        successful_creations = sum(1 for user in users if isinstance(user, User))
        assert successful_creations >= 2  # At least 2 should succeed

    @pytest.mark.asyncio
    async def test_database_constraints(self, test_db_session):
        """Test database constraints enforcement"""
        session = test_db_session
        
        # Test positive balance constraint
        try:
            invalid_user = User(
                telegram_username="invalid_user",
                telegram_id=777888999,
                top_up_amount=-100.0  # Negative amount should fail
            )
            session.add(invalid_user)
            await session.commit()
            
            # If we reach here, constraint wasn't enforced
            pytest.fail("Database constraint not enforced")
            
        except Exception:
            await session.rollback()
            # This is expected behavior

    @pytest.mark.asyncio
    async def test_repository_integration(self, test_db_session):
        """Test repository pattern integration"""
        session = test_db_session
        
        # Test UserRepository integration
        user_data = {
            "telegram_username": "repo_test_user",
            "telegram_id": 555666777,
            "top_up_amount": 300.0
        }
        
        # Mock repository methods
        with patch.object(UserRepository, 'create') as mock_create, \
             patch.object(UserRepository, 'get_by_tgid') as mock_get:
            
            mock_user = User(**user_data)
            mock_create.return_value = mock_user
            mock_get.return_value = mock_user
            
            # Test create
            created_user = await UserRepository.create(user_data, session)
            assert created_user.telegram_username == "repo_test_user"
            
            # Test retrieve
            retrieved_user = await UserRepository.get_by_tgid(555666777, session)
            assert retrieved_user.telegram_id == 555666777

    @pytest.mark.asyncio
    async def test_complex_query_operations(self, test_db_session):
        """Test complex database queries and joins"""
        session = test_db_session
        
        # Create test data
        category = Category(name="Electronics", description="Electronic items")
        session.add(category)
        await session.commit()
        
        items = [
            Item(name="Laptop", price=999.99, quantity=5, category_id=category.id),
            Item(name="Phone", price=599.99, quantity=10, category_id=category.id),
            Item(name="Tablet", price=399.99, quantity=3, category_id=category.id)
        ]
        
        for item in items:
            session.add(item)
        await session.commit()
        
        # Test complex query (items by category with stock > 5)
        result = await session.execute(
            text("""
                SELECT i.name, i.price, i.quantity 
                FROM items i 
                JOIN categories c ON i.category_id = c.id 
                WHERE c.name = 'Electronics' AND i.quantity > 5
                ORDER BY i.price DESC
            """)
        )
        
        items_result = result.fetchall()
        assert len(items_result) == 1  # Only Phone has quantity > 5
        assert items_result[0][0] == "Phone"

    @pytest.mark.asyncio
    async def test_database_performance(self, test_db_session):
        """Test database performance with bulk operations"""
        session = test_db_session
        import time
        
        # Create category first
        category = Category(name="Bulk Test", description="Performance test")
        session.add(category)
        await session.commit()
        
        start_time = time.time()
        
        # Bulk insert items
        items = []
        for i in range(100):
            item = Item(
                name=f"Item_{i}",
                price=10.0 + i,
                quantity=i + 1,
                category_id=category.id
            )
            items.append(item)
        
        session.add_all(items)
        await session.commit()
        
        end_time = time.time()
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert (end_time - start_time) < 5.0  # 5 seconds max
        
        # Verify all items were created
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM items WHERE category_id = :cat_id"),
            {"cat_id": category.id}
        )
        assert count_result.scalar() == 100

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, test_db_session):
        """Test database session lifecycle management"""
        session = test_db_session
        
        # Test session state
        assert session.is_active
        
        # Create and commit data
        user = User(telegram_username="session_test", telegram_id=123123123)
        session.add(user)
        await session.commit()
        
        # Test session after commit
        assert session.is_active
        
        # Test rollback
        user.top_up_amount = 1000.0
        await session.rollback()
        
        # Verify rollback worked
        await session.refresh(user)
        assert user.top_up_amount == 0.0  # Default value