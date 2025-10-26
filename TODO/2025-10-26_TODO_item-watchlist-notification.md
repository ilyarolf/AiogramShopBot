# Item Watchlist & Restock Notification System

**Date:** 2025-10-26
**Priority:** Medium
**Estimated Effort:** Medium (3-4 hours)
**Evil Factor:** ⭐⭐ (Better UX, but requires new user engagement model)

---

## Description
Implement a user-managed watchlist for out-of-stock items with automatic notifications when items are restocked. When a user encounters an out-of-stock item, they can add it to their watchlist. When the admin restocks that item, all subscribed users receive a notification.

## User Story
As a customer, I want to be notified when an out-of-stock item I'm interested in becomes available again, so I can purchase it without having to constantly check the shop.

## Business Value
- **Increased conversion**: Captures interest even when item is unavailable
- **Customer retention**: Brings users back to the shop automatically
- **Demand signals**: Provides admin visibility into which items are most wanted
- **Reduced cart abandonment**: Users don't leave frustrated when item is unavailable

## Feature Components

### 1. Watchlist Management (User Side)

#### Out-of-Stock Item Display
When viewing an item with `available_qty = 0`:

```
🔴 <b>Ausverkauft</b>

📦 <b>Green Tea Premium</b>
💰 12.50€
📝 Organic Dragon Well green tea from Hangzhou

<i>⏳ Nachschub ist unterwegs!</i>

[🔔 Benachrichtigen, wenn verfügbar]
[⬅️ Zurück]
```

#### Watchlist View
New menu option in user main menu:

```
🔔 <b>Deine Merkliste</b>

Du wirst benachrichtigt, wenn diese Artikel wieder verfügbar sind:

1️⃣ <b>Green Tea Premium</b> (12.50€)
   📦 Kategorie: Tea → Green Tea
   [❌ Von Merkliste entfernen]

2️⃣ <b>USB-Stick 64GB</b> (8.99€)
   📦 Kategorie: Electronics → Storage
   [❌ Von Merkliste entfernen]

<i>📊 Du hast 2 Artikel auf deiner Merkliste</i>

[⬅️ Zurück zum Menü]
```

#### Empty Subcategory Placeholder
When subcategory exists but all items are out of stock:

```
📂 <b>Green Tea</b>

<i>🚚 Alle Artikel sind derzeit ausverkauft, aber Nachschub ist unterwegs!</i>

<b>Möchtest du benachrichtigt werden, wenn neue Ware eintrifft?</b>

Verfügbare Artikel:
• Green Tea Premium (12.50€) [🔔 Benachrichtigen]
• Dragon Well Special (18.00€) [🔔 Benachrichtigen]

[⬅️ Zurück zu Kategorien]
```

### 2. Admin Restock Workflow

#### Restock Notification Trigger
When admin increases stock for an item (via JSON import or manual update):

```python
# In services/admin.py or wherever stock is updated
async def restock_item(item_id: int, new_quantity: int, session):
    item = await ItemRepository.get_by_id(item_id, session)
    old_quantity = item.quantity

    item.quantity = new_quantity
    await session_commit(session)

    # If item was out of stock and now has stock, notify watchers
    if old_quantity == 0 and new_quantity > 0:
        await notify_item_watchers(item_id, session)
```

#### Notification Message (to subscribed users)
```
🎉 <b>Gute Nachricht!</b>

Der Artikel auf deiner Merkliste ist wieder verfügbar:

📦 <b>Green Tea Premium</b>
💰 12.50€
📝 Organic Dragon Well green tea from Hangzhou

✨ <b>Jetzt zugreifen, bevor er wieder ausverkauft ist!</b>

[🛒 Zum Artikel] [🗑️ Von Merkliste entfernen]
```

#### Admin Dashboard Statistics
In admin panel, show watchlist stats:

```
📊 <b>Watchlist Statistics</b>

Top 5 Most Wanted Items:
1️⃣ Green Tea Premium - 47 watchers 👀
2️⃣ USB-Stick 64GB - 23 watchers 👀
3️⃣ Premium Coffee Beans - 18 watchers 👀
4️⃣ Notebook A5 - 12 watchers 👀
5️⃣ Wireless Mouse - 8 watchers 👀

💡 <i>Diese Artikel sollten priorisiert werden!</i>
```

## Technical Implementation

### Database Schema

#### New Table: `item_watchlist`
```sql
CREATE TABLE item_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP NULL,  -- Track when user was last notified
    UNIQUE(user_id, item_id)  -- User can only watch an item once
);

CREATE INDEX idx_watchlist_item ON item_watchlist(item_id);
CREATE INDEX idx_watchlist_user ON item_watchlist(user_id);
```

### Models

#### models/item_watchlist.py
```python
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class ItemWatchlist(Base):
    __tablename__ = 'item_watchlist'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    notified_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="watchlist")
    item = relationship("Item", back_populates="watchers")

    __table_args__ = (
        Index('idx_watchlist_item', 'item_id'),
        Index('idx_watchlist_user', 'user_id'),
    )
```

#### Update models/user.py
```python
# Add to User model
watchlist = relationship("ItemWatchlist", back_populates="user", cascade="all, delete-orphan")
```

#### Update models/item.py
```python
# Add to Item model
watchers = relationship("ItemWatchlist", back_populates="item", cascade="all, delete-orphan")
```

### Repositories

#### repositories/item_watchlist.py
```python
from typing import List, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from models.item_watchlist import ItemWatchlist
from models.item import Item
from models.user import User

class ItemWatchlistRepository:
    @staticmethod
    async def add_to_watchlist(user_id: int, item_id: int, session: AsyncSession | Session) -> ItemWatchlist:
        """
        Add item to user's watchlist.
        Returns existing entry if already watching.
        """
        # Check if already watching
        stmt = select(ItemWatchlist).where(
            ItemWatchlist.user_id == user_id,
            ItemWatchlist.item_id == item_id
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new watchlist entry
        watchlist_entry = ItemWatchlist(
            user_id=user_id,
            item_id=item_id
        )
        session.add(watchlist_entry)
        return watchlist_entry

    @staticmethod
    async def remove_from_watchlist(user_id: int, item_id: int, session: AsyncSession | Session) -> bool:
        """Remove item from user's watchlist. Returns True if removed, False if not found."""
        stmt = delete(ItemWatchlist).where(
            ItemWatchlist.user_id == user_id,
            ItemWatchlist.item_id == item_id
        )
        result = await session.execute(stmt)
        return result.rowcount > 0

    @staticmethod
    async def get_user_watchlist(user_id: int, session: AsyncSession | Session) -> List[ItemWatchlist]:
        """Get all items on user's watchlist with eager loading."""
        stmt = select(ItemWatchlist).where(
            ItemWatchlist.user_id == user_id
        ).options(
            selectinload(ItemWatchlist.item)
        ).order_by(ItemWatchlist.created_at.desc())

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_item_watchers(item_id: int, session: AsyncSession | Session) -> List[ItemWatchlist]:
        """Get all users watching an item."""
        stmt = select(ItemWatchlist).where(
            ItemWatchlist.item_id == item_id
        ).options(
            selectinload(ItemWatchlist.user)
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_watchlist_count(user_id: int, session: AsyncSession | Session) -> int:
        """Get count of items on user's watchlist."""
        stmt = select(func.count(ItemWatchlist.id)).where(
            ItemWatchlist.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalar()

    @staticmethod
    async def get_most_watched_items(limit: int = 10, session: AsyncSession | Session) -> List[tuple]:
        """
        Get most watched items with watcher count.
        Returns: [(item, watcher_count), ...]
        """
        stmt = select(
            Item,
            func.count(ItemWatchlist.id).label('watcher_count')
        ).join(
            ItemWatchlist, Item.id == ItemWatchlist.item_id
        ).group_by(
            Item.id
        ).order_by(
            func.count(ItemWatchlist.id).desc()
        ).limit(limit)

        result = await session.execute(stmt)
        return result.all()

    @staticmethod
    async def is_watching(user_id: int, item_id: int, session: AsyncSession | Session) -> bool:
        """Check if user is watching an item."""
        stmt = select(ItemWatchlist).where(
            ItemWatchlist.user_id == user_id,
            ItemWatchlist.item_id == item_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
```

### Services

#### services/watchlist.py
```python
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from aiogram import Bot
from repositories.item_watchlist import ItemWatchlistRepository
from repositories.item import ItemRepository
from services.localizator import Localizator, BotEntity
from datetime import datetime
import logging

class WatchlistService:
    @staticmethod
    async def notify_item_watchers(item_id: int, session: AsyncSession | Session, bot: Bot):
        """
        Notify all users watching an item that it's back in stock.
        Called when item is restocked (quantity changes from 0 to >0).
        """
        # Get item details
        item = await ItemRepository.get_by_id(item_id, session)
        if not item or item.quantity == 0:
            logging.warning(f"[Watchlist] Attempted to notify for item {item_id} but it's not in stock")
            return

        # Get all watchers
        watchers = await ItemWatchlistRepository.get_item_watchers(item_id, session)

        if not watchers:
            logging.info(f"[Watchlist] No watchers for item {item_id}")
            return

        logging.info(f"[Watchlist] Notifying {len(watchers)} users about restock of item {item_id}")

        # Send notification to each watcher
        for watchlist_entry in watchers:
            user = watchlist_entry.user

            try:
                message_text = Localizator.get_text(BotEntity.USER, "watchlist_item_restocked").format(
                    item_name=item.description,
                    price=item.price,
                    currency=Localizator.get_currency_symbol()
                )

                # TODO: Add inline keyboard with [View Item] and [Remove from Watchlist] buttons

                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode="HTML"
                )

                # Update notified_at timestamp
                watchlist_entry.notified_at = datetime.now()

                logging.info(f"[Watchlist] ✅ Notified user {user.telegram_id} about item {item_id}")

            except Exception as e:
                logging.error(f"[Watchlist] ❌ Failed to notify user {user.telegram_id}: {e}")

        await session_commit(session)

    @staticmethod
    async def format_watchlist_display(user_id: int, session: AsyncSession | Session) -> str:
        """Format user's watchlist for display."""
        watchlist = await ItemWatchlistRepository.get_user_watchlist(user_id, session)

        if not watchlist:
            return Localizator.get_text(BotEntity.USER, "watchlist_empty")

        message_lines = [
            Localizator.get_text(BotEntity.USER, "watchlist_header"),
            ""
        ]

        for idx, entry in enumerate(watchlist, start=1):
            item = entry.item
            message_lines.append(
                f"{idx}️⃣ <b>{item.description}</b> ({item.price:.2f}{Localizator.get_currency_symbol()})"
            )
            # TODO: Add category/subcategory info
            message_lines.append("")

        message_lines.append(
            f"<i>📊 Du hast {len(watchlist)} Artikel auf deiner Merkliste</i>"
        )

        return "\n".join(message_lines)
```

### Handlers

#### handlers/user/watchlist.py
```python
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.item_watchlist import ItemWatchlistRepository
from services.watchlist import WatchlistService
from services.localizator import Localizator, BotEntity
from callbacks import WatchlistCallback

router = Router()

@router.callback_query(WatchlistCallback.filter(F.action == "add"))
async def add_to_watchlist(
    callback: CallbackQuery,
    callback_data: WatchlistCallback,
    session: AsyncSession,
    state: FSMContext
):
    """Add item to user's watchlist."""
    user_id = callback.from_user.id
    item_id = callback_data.item_id

    # Add to watchlist
    await ItemWatchlistRepository.add_to_watchlist(user_id, item_id, session)
    await session_commit(session)

    await callback.answer(
        Localizator.get_text(BotEntity.USER, "watchlist_added"),
        show_alert=True
    )

@router.callback_query(WatchlistCallback.filter(F.action == "remove"))
async def remove_from_watchlist(
    callback: CallbackQuery,
    callback_data: WatchlistCallback,
    session: AsyncSession,
    state: FSMContext
):
    """Remove item from user's watchlist."""
    user_id = callback.from_user.id
    item_id = callback_data.item_id

    removed = await ItemWatchlistRepository.remove_from_watchlist(user_id, item_id, session)

    if removed:
        await callback.answer(
            Localizator.get_text(BotEntity.USER, "watchlist_removed"),
            show_alert=True
        )
    else:
        await callback.answer("Artikel nicht auf Merkliste gefunden", show_alert=True)

@router.callback_query(WatchlistCallback.filter(F.action == "view"))
async def view_watchlist(
    callback: CallbackQuery,
    callback_data: WatchlistCallback,
    session: AsyncSession,
    state: FSMContext
):
    """View user's complete watchlist."""
    user_id = callback.from_user.id

    message_text = await WatchlistService.format_watchlist_display(user_id, session)

    # TODO: Add keyboard with remove buttons for each item

    await callback.message.edit_text(
        text=message_text,
        parse_mode="HTML"
    )
```

### Callbacks

#### Add to callbacks.py
```python
class WatchlistCallback(CallbackData, prefix="watchlist"):
    action: str  # "add", "remove", "view"
    item_id: int
```

### Localization

#### l10n/de.json
```json
"watchlist_item_restocked": "🎉 <b>Gute Nachricht!</b>\n\nDer Artikel auf deiner Merkliste ist wieder verfügbar:\n\n📦 <b>{item_name}</b>\n💰 {price}{currency}\n\n✨ <b>Jetzt zugreifen, bevor er wieder ausverkauft ist!</b>",
"watchlist_added": "✅ Artikel wurde zu deiner Merkliste hinzugefügt!",
"watchlist_removed": "🗑️ Artikel wurde von deiner Merkliste entfernt",
"watchlist_empty": "🔔 <b>Deine Merkliste ist leer</b>\n\n<i>Wenn du auf einen ausverkauften Artikel stößt, kannst du dich für eine Benachrichtigung registrieren!</i>",
"watchlist_header": "🔔 <b>Deine Merkliste</b>\n\nDu wirst benachrichtigt, wenn diese Artikel wieder verfügbar sind:",
"item_out_of_stock_notify": "🔴 <b>Ausverkauft</b>\n\n<i>⏳ Nachschub ist unterwegs!</i>\n\nMöchtest du benachrichtigt werden, wenn dieser Artikel wieder verfügbar ist?",
"subcategory_all_out_of_stock": "🚚 <b>Alle Artikel sind derzeit ausverkauft, aber Nachschub ist unterwegs!</b>\n\n<i>Möchtest du benachrichtigt werden, wenn neue Ware eintrifft?</i>"
```

#### l10n/en.json
```json
"watchlist_item_restocked": "🎉 <b>Good news!</b>\n\nAn item on your watchlist is back in stock:\n\n📦 <b>{item_name}</b>\n💰 {price}{currency}\n\n✨ <b>Get it now before it sells out again!</b>",
"watchlist_added": "✅ Item added to your watchlist!",
"watchlist_removed": "🗑️ Item removed from your watchlist",
"watchlist_empty": "🔔 <b>Your watchlist is empty</b>\n\n<i>When you encounter an out-of-stock item, you can register for notifications!</i>",
"watchlist_header": "🔔 <b>Your Watchlist</b>\n\nYou'll be notified when these items are back in stock:",
"item_out_of_stock_notify": "🔴 <b>Out of Stock</b>\n\n<i>⏳ Restocking soon!</i>\n\nWould you like to be notified when this item is available again?",
"subcategory_all_out_of_stock": "🚚 <b>All items are currently out of stock, but restocking soon!</b>\n\n<i>Would you like to be notified when new stock arrives?</i>"
```

## Integration Points

### 1. Item Detail View
When displaying out-of-stock item, add "Notify me" button:

```python
# In handlers/user/subcategory.py or item detail handler
if item.quantity == 0:
    kb_builder.button(
        text="🔔 Benachrichtigen, wenn verfügbar",
        callback_data=WatchlistCallback(action="add", item_id=item.id)
    )
```

### 2. Empty Subcategory Placeholder
When subcategory has no available items:

```python
# In services/subcategory.py
if all_items_out_of_stock:
    message_text = Localizator.get_text(BotEntity.USER, "subcategory_all_out_of_stock")
    # List all out-of-stock items with watchlist buttons
```

### 3. Admin Restock Detection
When admin imports JSON with new stock:

```python
# In services/admin.py → import_shop_data()
for item_data in json_data:
    item = await ItemRepository.get_by_id(item_id, session)
    old_quantity = item.quantity
    new_quantity = item_data['quantity']

    item.quantity = new_quantity
    await session_commit(session)

    # Trigger notifications if restocked
    if old_quantity == 0 and new_quantity > 0:
        await WatchlistService.notify_item_watchers(item.id, session, bot)
```

### 4. User Main Menu
Add watchlist menu item:

```python
kb_builder.button(
    text="🔔 Meine Merkliste",
    callback_data=WatchlistCallback(action="view", item_id=0)
)
```

## Testing Checklist

- [ ] **T1: Add item to watchlist**
  - View out-of-stock item
  - Click "Notify me" button
  - Verify success message
  - Check database entry created

- [ ] **T2: View watchlist**
  - Add multiple items to watchlist
  - Open watchlist menu
  - Verify all items displayed correctly

- [ ] **T3: Remove from watchlist**
  - Add item to watchlist
  - Click remove button
  - Verify item removed

- [ ] **T4: Restock notification**
  - User adds out-of-stock item to watchlist
  - Admin restocks item (JSON import or manual)
  - Verify user receives notification

- [ ] **T5: Multiple watchers**
  - Multiple users watch same item
  - Admin restocks item
  - Verify all users receive notification

- [ ] **T6: Empty subcategory placeholder**
  - Create subcategory with all items out of stock
  - View subcategory
  - Verify placeholder message with watchlist buttons

- [ ] **T7: Watchlist persistence**
  - Add items to watchlist
  - Restart bot
  - Verify watchlist still intact

- [ ] **T8: Admin statistics**
  - Multiple users watch items
  - Open admin dashboard
  - Verify watchlist statistics displayed correctly

- [ ] **T9: Cascade delete**
  - User has watchlist items
  - Delete user
  - Verify watchlist entries deleted (cascade)

- [ ] **T10: Item deletion**
  - User watches item
  - Admin deletes item
  - Verify watchlist entry deleted (cascade)

## Edge Cases

1. **Item restocked but user already bought**: Notification still sent (user can buy more)
2. **Item restocked then sold out again**: Next restock triggers new notifications
3. **User blocks bot**: Notification fails gracefully, log error
4. **Duplicate watchlist entries**: Prevented by UNIQUE constraint
5. **Watchlist for digital items**: Allowed (digital items can also be out of stock)

## Future Enhancements

- [ ] Watchlist limit per user (e.g., max 20 items)
- [ ] Expiry for watchlist entries (auto-remove after 90 days)
- [ ] Weekly digest: "5 items on your watchlist are still unavailable"
- [ ] Admin: Broadcast message to all watchers of an item
- [ ] Analytics: Track conversion rate (notification → purchase)
- [ ] Email notifications (if user provides email)

## Notes

- Notifications are sent immediately when item is restocked
- Users can watch items even if they have low stock (not just out of stock)
- Watchlist is per-user, not per-cart (persistent across sessions)
- Admin can see demand signals before restocking decisions
- Consider rate limiting: Max 1 notification per item per 24 hours per user

---

**Status:** Planned
**Dependencies:** None (standalone feature)
**Evil Factor Rationale:** Medium complexity, requires new engagement model (push notifications), but provides significant UX improvement and business value.
