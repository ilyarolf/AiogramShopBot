# Test cases for CartService and cart operations
# Covers: Cart creation, item management, cart calculations, validation

import pytest
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from services.cart import CartService
from models.cart import Cart, CartDTO
from models.cartItem import CartItem, CartItemDTO
from models.item import Item
from models.user import User


class TestCartService:
    """Test cart service functionality"""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        return User(
            id=1,
            telegram_id=123456789,
            telegram_username="test_user",
            top_up_amount=1000.0,
            consume_records=100.0
        )

    @pytest.fixture
    def mock_item(self):
        """Create mock item"""
        return Item(
            id=1,
            name="Test Product",
            price=25.99,
            quantity=10,
            category_id=1,
            subcategory_id=1
        )

    @pytest.fixture
    def mock_cart(self):
        """Create mock cart"""
        return Cart(
            id=1,
            user_id=1,
            total_amount=0.0
        )

    @pytest.fixture
    def mock_cart_item(self):
        """Create mock cart item"""
        return CartItem(
            id=1,
            cart_id=1,
            item_id=1,
            quantity=2,
            price=25.99,
            subtotal=51.98
        )

    @pytest.mark.asyncio
    async def test_create_cart_success(self, mock_user):
        """Test successful cart creation"""
        mock_session = AsyncMock()
        cart_dto = CartDTO(user_id=1, total_amount=0.0)
        
        with patch('services.cart.CartRepository.create', return_value=cart_dto) as mock_create:
            result = await CartService.create_cart(mock_user.id, mock_session)
            
            mock_create.assert_called_once()
            assert result.user_id == 1
            assert result.total_amount == 0.0

    @pytest.mark.asyncio
    async def test_add_item_to_cart_new_item(self, mock_user, mock_item, mock_cart):
        """Test adding new item to cart"""
        mock_session = AsyncMock()
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.get_by_cart_and_item', return_value=None), \
             patch('services.cart.CartItemRepository.create') as mock_create_item, \
             patch('services.cart.CartRepository.update_total') as mock_update_total:
            
            await CartService.add_item_to_cart(
                mock_user.id, 
                mock_item.id, 
                quantity=3, 
                session=mock_session
            )
            
            mock_create_item.assert_called_once()
            mock_update_total.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_item_to_cart_existing_item(self, mock_user, mock_item, mock_cart, mock_cart_item):
        """Test adding quantity to existing cart item"""
        mock_session = AsyncMock()
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.get_by_cart_and_item', return_value=mock_cart_item), \
             patch('services.cart.CartItemRepository.update_quantity') as mock_update_qty, \
             patch('services.cart.CartRepository.update_total') as mock_update_total:
            
            await CartService.add_item_to_cart(
                mock_user.id, 
                mock_item.id, 
                quantity=2, 
                session=mock_session
            )
            
            mock_update_qty.assert_called_once()
            mock_update_total.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_item_from_cart(self, mock_user, mock_cart, mock_cart_item):
        """Test removing item from cart"""
        mock_session = AsyncMock()
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.get_by_cart_and_item', return_value=mock_cart_item), \
             patch('services.cart.CartItemRepository.delete') as mock_delete, \
             patch('services.cart.CartRepository.update_total') as mock_update_total:
            
            await CartService.remove_item_from_cart(
                mock_user.id, 
                mock_cart_item.item_id, 
                session=mock_session
            )
            
            mock_delete.assert_called_once()
            mock_update_total.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_cart_total(self, mock_cart):
        """Test cart total calculation"""
        mock_session = AsyncMock()
        mock_cart_items = [
            CartItem(id=1, cart_id=1, item_id=1, quantity=2, price=25.99, subtotal=51.98),
            CartItem(id=2, cart_id=1, item_id=2, quantity=1, price=15.50, subtotal=15.50),
            CartItem(id=3, cart_id=1, item_id=3, quantity=3, price=10.00, subtotal=30.00)
        ]
        
        with patch('services.cart.CartItemRepository.get_by_cart_id', return_value=mock_cart_items):
            total = await CartService.calculate_cart_total(mock_cart.id, mock_session)
            
            expected_total = 51.98 + 15.50 + 30.00
            assert abs(total - expected_total) < 0.01

    @pytest.mark.asyncio
    async def test_clear_cart(self, mock_user, mock_cart):
        """Test clearing all items from cart"""
        mock_session = AsyncMock()
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.delete_by_cart_id') as mock_clear, \
             patch('services.cart.CartRepository.update_total') as mock_update_total:
            
            await CartService.clear_cart(mock_user.id, mock_session)
            
            mock_clear.assert_called_once_with(mock_cart.id, mock_session)
            mock_update_total.assert_called_once_with(mock_cart.id, 0.0, mock_session)

    @pytest.mark.asyncio
    async def test_get_cart_items(self, mock_user, mock_cart):
        """Test retrieving cart items"""
        mock_session = AsyncMock()
        mock_cart_items = [
            CartItem(id=1, cart_id=1, item_id=1, quantity=2, price=25.99),
            CartItem(id=2, cart_id=1, item_id=2, quantity=1, price=15.50)
        ]
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.get_by_cart_id', return_value=mock_cart_items):
            
            items = await CartService.get_cart_items(mock_user.id, mock_session)
            
            assert len(items) == 2
            assert items[0].quantity == 2
            assert items[1].quantity == 1

    @pytest.mark.asyncio
    async def test_update_item_quantity(self, mock_user, mock_cart, mock_cart_item):
        """Test updating item quantity in cart"""
        mock_session = AsyncMock()
        new_quantity = 5
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.CartItemRepository.get_by_cart_and_item', return_value=mock_cart_item), \
             patch('services.cart.CartItemRepository.update_quantity') as mock_update, \
             patch('services.cart.CartRepository.update_total') as mock_update_total:
            
            await CartService.update_item_quantity(
                mock_user.id, 
                mock_cart_item.item_id, 
                new_quantity, 
                mock_session
            )
            
            mock_update.assert_called_once()
            mock_update_total.assert_called_once()

    @pytest.mark.asyncio
    async def test_cart_validation_invalid_quantity(self, mock_user, mock_item):
        """Test cart validation with invalid quantities"""
        mock_session = AsyncMock()
        
        # Test negative quantity
        with pytest.raises(ValueError):
            await CartService.add_item_to_cart(
                mock_user.id, 
                mock_item.id, 
                quantity=-1, 
                session=mock_session
            )
        
        # Test zero quantity
        with pytest.raises(ValueError):
            await CartService.add_item_to_cart(
                mock_user.id, 
                mock_item.id, 
                quantity=0, 
                session=mock_session
            )

    @pytest.mark.asyncio
    async def test_cart_item_price_consistency(self, mock_user, mock_cart, mock_item):
        """Test that cart item prices match current item prices"""
        mock_session = AsyncMock()
        quantity = 2
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.ItemRepository.get_by_id', return_value=mock_item), \
             patch('services.cart.CartItemRepository.get_by_cart_and_item', return_value=None), \
             patch('services.cart.CartItemRepository.create') as mock_create:
            
            await CartService.add_item_to_cart(
                mock_user.id, 
                mock_item.id, 
                quantity=quantity, 
                session=mock_session
            )
            
            # Verify create was called with correct price
            create_call = mock_create.call_args[0][0]  # First argument (CartItemDTO)
            assert create_call.price == mock_item.price
            assert create_call.subtotal == mock_item.price * quantity

    @pytest.mark.asyncio
    async def test_cart_stock_validation(self, mock_user, mock_cart, mock_item):
        """Test cart validation against item stock"""
        mock_session = AsyncMock()
        
        # Test adding more items than available in stock
        excessive_quantity = mock_item.quantity + 10
        
        with patch('services.cart.CartRepository.get_user_cart', return_value=mock_cart), \
             patch('services.cart.ItemRepository.get_by_id', return_value=mock_item):
            
            with pytest.raises(ValueError, match="Insufficient stock"):
                await CartService.add_item_to_cart(
                    mock_user.id, 
                    mock_item.id, 
                    quantity=excessive_quantity, 
                    session=mock_session
                )

    @pytest.mark.asyncio
    async def test_cart_decimal_precision(self, mock_user, mock_cart):
        """Test cart handles decimal precision correctly"""
        mock_session = AsyncMock()
        
        # Items with precise decimal prices
        mock_cart_items = [
            CartItem(id=1, cart_id=1, item_id=1, quantity=3, price=10.333, subtotal=30.999),
            CartItem(id=2, cart_id=1, item_id=2, quantity=2, price=5.666, subtotal=11.332)
        ]
        
        with patch('services.cart.CartItemRepository.get_by_cart_id', return_value=mock_cart_items):
            total = await CartService.calculate_cart_total(mock_cart.id, mock_session)
            
            # Should handle decimal precision correctly
            expected_total = 30.999 + 11.332
            assert abs(total - expected_total) < 0.001