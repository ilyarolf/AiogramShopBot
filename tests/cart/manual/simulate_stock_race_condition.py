"""
===============================================================================
Stock Race Condition Simulator - INTERACTIVE
===============================================================================

DESCRIPTION:
    Simulates a REAL race condition where items are sold by another user
    while you have them in your cart and are checking out.

    This tests the atomic stock reservation during order creation.

HOW IT WORKS:
    1. You add items to cart in the bot
    2. Script waits for your signal
    3. You start checkout process
    4. Script "steals" items in the background (marks them as sold/reserved)
    5. Your checkout detects insufficient stock
    6. Stock adjustment confirmation screen appears

REQUIREMENTS:
    - Python 3.10+
    - Virtual environment activated
    - Bot must be running in another terminal
    - Database configured and accessible

SETUP:
    1. Navigate to project root:
       cd /path/to/AiogramShopBot

    2. Activate virtual environment:
       source venv/bin/activate        # Linux/Mac
       venv\Scripts\activate          # Windows

USAGE:
    Terminal 1 - Start bot:
        $ cd ~/git/AiogramShopBot
        $ source venv/bin/activate
        $ python main.py

    Terminal 2 - Run this script:
        $ cd ~/git/AiogramShopBot
        $ source venv/bin/activate
        $ python3 tests/manual/simulate_race_condition.py

    Follow the interactive prompts!

EXAMPLE SESSION:
    $ python3 tests/manual/simulate_race_condition.py

    [Script shows your current cart items]
    You have in cart:
    - iPhone 15 Pro: 3 items

    How many items should be "stolen"?
    1) Steal 1 item  (2 remain)
    2) Steal 2 items (1 remains)
    3) Steal all 3 items (0 remain)
    Choice: 2

    Ready! When you press ENTER, I will steal 2 items.
    Then immediately press Checkout in the bot!
    Press ENTER to start...

    ✅ Stolen 2 items! Quick, press Checkout now!
    [You press Checkout in bot]
    [Bot shows: "Only 1 of 3 available"]

===============================================================================
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set TEST mode to avoid starting ngrok/webhook
os.environ["RUNTIME_ENVIRONMENT"] = "TEST"

from sqlalchemy import select, update
from db import get_db_session
from models.item import Item
from models.category import Category
from models.subcategory import Subcategory
from models.user import User
from models.cart import Cart
from models.cartItem import CartItem
from models.shipping_address import ShippingAddress  # Required for Order relationship
import config

print(f"Debug: RUNTIME_ENVIRONMENT = {config.RUNTIME_ENVIRONMENT}")
print(f"Debug: DB_NAME = {config.DB_NAME}\n")


async def get_user_cart():
    """Get the user's current cart and show what's in it."""
    async with get_db_session() as session:
        # Get user (assuming first user for testing)
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalar()

        if not user:
            print("❌ No user found in database. Please register in the bot first.")
            return None

        print(f"👤 User: {user.telegram_username} (ID: {user.telegram_id})")

        # Get cart items
        stmt = (
            select(CartItem, Category.name, Subcategory.name)
            .join(Cart, CartItem.cart_id == Cart.id)
            .join(Category, CartItem.category_id == Category.id)
            .join(Subcategory, CartItem.subcategory_id == Subcategory.id)
            .where(Cart.user_id == user.id)
        )
        result = await session.execute(stmt)
        cart_items = result.all()

        if not cart_items:
            print("🛒 Cart is empty. Please add items in the bot first!")
            return None

        print("\n🛒 Current cart contents:")
        items_info = []
        for cart_item, cat_name, subcat_name in cart_items:
            # Get available stock
            stmt_stock = (
                select(Item)
                .where(Item.subcategory_id == cart_item.subcategory_id)
                .where(Item.is_sold == False)
                .where(Item.order_id == None)
            )
            result_stock = await session.execute(stmt_stock)
            available = result_stock.scalars().all()

            print(f"   - {cat_name} → {subcat_name}")
            print(f"     Quantity in cart: {cart_item.quantity}")
            print(f"     Available stock: {len(available)}")

            items_info.append({
                'cart_item': cart_item,
                'category': cat_name,
                'subcategory': subcat_name,
                'available': available,
                'quantity_in_cart': cart_item.quantity
            })

        return items_info


async def steal_items(subcategory_id: int, quantity: int):
    """
    "Steals" items by marking them as sold (simulating another user buying them).
    This creates the race condition.
    """
    async with get_db_session() as session:
        # Get available items
        stmt = (
            select(Item)
            .where(Item.subcategory_id == subcategory_id)
            .where(Item.is_sold == False)
            .where(Item.order_id == None)
            .limit(quantity)
        )
        result = await session.execute(stmt)
        items = result.scalars().all()

        if not items:
            print("⚠️ No items available to steal!")
            return 0

        # Mark as sold
        for item in items:
            item.is_sold = True

        await session.commit()
        return len(items)


async def main():
    """Main interactive flow."""
    print("=" * 60)
    print("STOCK RACE CONDITION SIMULATOR")
    print("=" * 60)
    print()

    # Step 1: Show current cart
    items_info = await get_user_cart()
    if not items_info:
        return

    print("\n" + "=" * 60)
    print("SELECT ITEM TO MANIPULATE")
    print("=" * 60)

    # Step 2: Let user choose which item to manipulate
    for idx, info in enumerate(items_info, 1):
        print(f"{idx}) {info['subcategory']} "
              f"({info['quantity_in_cart']} in cart, "
              f"{len(info['available'])} available)")

    try:
        choice = int(input("\nWhich item? "))
        if choice < 1 or choice > len(items_info):
            print("Invalid choice!")
            return
    except ValueError:
        print("Invalid input!")
        return

    selected = items_info[choice - 1]

    # Step 3: Choose how many to steal
    print("\n" + "=" * 60)
    print("HOW MANY TO STEAL?")
    print("=" * 60)

    max_steal = len(selected['available'])
    options = []

    if max_steal >= 1:
        remaining = max_steal - 1
        options.append((1, remaining))
        print(f"1) Steal 1 item  ({remaining} remain)")

    if max_steal >= 2:
        steal_half = max_steal // 2
        remaining = max_steal - steal_half
        options.append((steal_half, remaining))
        print(f"2) Steal {steal_half} items ({remaining} remain)")

    if max_steal >= 1:
        options.append((max_steal, 0))
        print(f"{len(options)}) Steal ALL {max_steal} items (0 remain)")

    try:
        steal_choice = int(input("\nChoice: "))
        if steal_choice < 1 or steal_choice > len(options):
            print("Invalid choice!")
            return
    except ValueError:
        print("Invalid input!")
        return

    steal_qty, remaining = options[steal_choice - 1]

    # Step 4: Ready prompt
    print("\n" + "=" * 60)
    print("READY TO SIMULATE RACE CONDITION")
    print("=" * 60)
    print(f"When you press ENTER:")
    print(f"  - Script will steal {steal_qty} items")
    print(f"  - {remaining} items will remain")
    print(f"  - You have {selected['quantity_in_cart']} in cart")
    print()
    print(f"Expected result at checkout:")
    if remaining == 0:
        print(f"  ❌ Order cancelled - all items out of stock")
    elif remaining < selected['quantity_in_cart']:
        print(f"  ⚠️ Stock adjustment: only {remaining} of {selected['quantity_in_cart']} available")
    else:
        print(f"  ✅ Full stock available")
    print()
    print("After pressing ENTER, immediately go to your bot and press Checkout!")
    print()
    input("Press ENTER to steal items and start race condition...")

    # Step 5: Steal items
    stolen = await steal_items(selected['cart_item'].subcategory_id, steal_qty)

    print()
    print("=" * 60)
    print(f"✅ Stolen {stolen} items!")
    print("=" * 60)
    print()
    print("🏃 Quick! Press Checkout in the bot NOW!")
    print()
    print(f"Expected: Stock adjustment screen showing {remaining} of {selected['quantity_in_cart']} available")
    print()


if __name__ == "__main__":
    asyncio.run(main())
