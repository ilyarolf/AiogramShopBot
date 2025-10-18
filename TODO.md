# List of features to be implemented

## Return to Category After Add to Cart

### Description
After adding an item to the cart, the user should be redirected back to the category/subcategory view they were browsing, instead of being taken back to the main bittcategory list.

### User Story
As a user, I want to continue shopping in the same category after adding an item to my cart, so that I can quickly add multiple items from the same category without having to navigate back each time.

### Acceptance Criteria
- [ ] After clicking "Add to Cart", user is returned to the subcategory list they were viewing
- [ ] Category and page context is preserved in callback data
- [ ] Navigation state is maintained through the add-to-cart flow
- [ ] User can see confirmation that item was added (existing behavior)

### Technical Notes
- The callback data needs to include category_id and current page
- Modify `CartService.add_to_cart()` to redirect to the original category view
- Update `AllCategoriesCallback` to carry category context through the flow
- The "Back" navigation should also respect the category context

### Estimated Effort
Medium (20-30 minutes)

---

## Strike System and User Ban Management

### Description
Implement a comprehensive strike and ban system to prevent users with multiple violations from placing orders. Users receive strikes for order timeouts and late cancellations. After reaching a strike limit, users are banned and shown a ban message instead of normal shop functionality.

### User Story
As a shop administrator, I want to automatically ban users who repeatedly cancel orders late or let them timeout, so that I can maintain order quality and prevent abuse of the reservation system.

### Acceptance Criteria
- [ ] User model includes `strikes` counter, `is_banned` flag, and `ban_reason` field
- [ ] Strikes are incremented when:
  - Order times out (TIMEOUT status)
  - User cancels order after grace period expires
- [ ] User is automatically banned when strike limit is reached (configurable, e.g., 3 strikes)
- [ ] Banned users see a ban message with:
  - Clear statement that they are banned
  - The reason for the ban (e.g., "Too many order cancellations/timeouts")
  - Instructions to contact support
- [ ] Banned users cannot:
  - Add items to cart
  - View cart (shows ban message instead)
  - Place orders
  - Access checkout
- [ ] Cart is automatically cleared when banned user tries to access it
- [ ] Localization keys for ban messages in German and English
- [ ] Admin can manually unban users (future enhancement)

### Technical Notes

#### Database Changes
- Add to User model:
  ```python
  strikes = Column(Integer, default=0)
  is_banned = Column(Boolean, default=False)
  ban_reason = Column(String, nullable=True)
  banned_at = Column(DateTime, nullable=True)
  ```

#### Strike Logic
- Implement in `OrderService`:
  - `increment_strike(user_id, reason)` - Adds strike and checks ban threshold
  - Auto-ban when `strikes >= BAN_STRIKE_THRESHOLD` (config value)
- Call `increment_strike()` from:
  - `OrderService.cancel_order_by_user()` when `within_grace_period == False`
  - Timeout job when marking orders as TIMEOUT

#### Ban Middleware/Guard
- Create `BanCheckMiddleware` or add to existing middleware
- Check `user.is_banned` on every cart/order operation
- Redirect banned users to ban message view
- Clear cart if banned user has items

#### Ban Message View
- Create `CartService.show_ban_message()` method
- Display:
  - Ban icon and header
  - Ban reason (from `user.ban_reason`)
  - Support contact link (from config)
  - No action buttons (prevent any shopping actions)

#### Localization Keys (DE/EN)
- `user_banned_title`: "Account Suspended" / "Account gesperrt"
- `user_banned_message`: Message template with {reason} and {support_link}
- `ban_reason_strikes`: "Multiple order violations (timeouts/late cancellations)"
- `ban_contact_support`: "Please contact support if you have questions"

#### Configuration
- `BAN_STRIKE_THRESHOLD` (default: 3)
- `SUPPORT_LINK` (already exists in config)

#### Implementation Order
1. Database model changes (add strike/ban fields)
2. Strike increment logic in OrderService
3. Auto-ban logic when threshold reached
4. Ban check middleware
5. Ban message view
6. Cart clearing for banned users
7. Localization keys
8. Integration with timeout job
9. Testing with multiple scenarios

### Estimated Effort
High (2-3 hours)

### Dependencies
- Requires timeout job to be implemented (for TIMEOUT strikes)
- Requires User model migrations

---

## Tiered Pricing (Staffelpreise)

### Description
Implement a flexible tiered pricing system where items can have different price points based on quantity purchased. Each item can define its own quantity tiers (e.g., 1, 5, 10, 25) with corresponding unit prices. Customers are incentivized to buy larger quantities as the unit price decreases with higher tiers. Customers manually select tier quantities and are responsible for choosing the optimal combination themselves.

### User Story
As a shop administrator, I want to configure tiered pricing for individual products, so that customers receive quantity discounts and are encouraged to purchase larger amounts.

### Acceptance Criteria
- [ ] JSON import format supports tiered pricing configuration (**TXT format NOT supported**)
- [ ] Each item can have 1-N price tiers (quantity → unit price)
- [ ] Items with single tier (e.g., only "1: €10.50") have fixed pricing
- [ ] Items with multiple tiers offer quantity discounts
- [ ] Quantity selector shows ONLY available tier quantities as buttons (e.g., "1x", "5x", "10x", "25x")
- [ ] **NO free-text quantity input** - customer can only select from configured tier buttons
- [ ] Price details are displayed in the message text above buttons
- [ ] Buttons show only quantity labels (e.g., "1x", "5x"), NOT prices
- [ ] Customer can add multiple quantities of the same tier to cart
  - Example: Customer can click "10x" button three times to get 30 units total (3 separate cart items)
- [ ] Each tier quantity added to cart is a separate cart item with its tier price
- [ ] Customer is responsible for choosing optimal combination (no automatic optimization)

### Technical Notes

**NEW JSON format:**
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "description": "Organic Dragon Well green tea",
  "private_data": "TEA-DRAGONWELL-UNIT061",
  "price_tiers": [
    {"quantity": 1, "unit_price": 11.00},
    {"quantity": 5, "unit_price": 9.00},
    {"quantity": 10, "unit_price": 7.50},
    {"quantity": 25, "unit_price": 6.00}
  ]
}
```

**Database Changes:**
- Create new `price_tiers` table with columns: `id`, `item_id`, `quantity`, `unit_price`
- Relationship: `Item.price_tiers` (one-to-many)
- Repository: `PriceTierRepository` with CRUD operations

**UI Example:**
```
Green Tea - Organic Dragon Well

Prices:
• 1 pc: €11.00/pc (€11.00 total)
• 5 pc: €9.00/pc (€45.00 total)
• 10 pc: €7.50/pc (€75.00 total)

Select quantity:
[1x] [5x] [10x] [25x]
```

### Estimated Effort
High (3-4 hours)

### Dependencies
- Requires database migration for `price_tiers` table
- Must update `ItemRepository.add_many()` to return created items (for getting IDs)
- UI changes to quantity selector

---

## Shipping Cost Management

### Description
Implement a shipping cost system where items can optionally have shipping costs. When an order is created, the highest shipping cost among all items in the order is applied once. The shipping cost is included in the order total price but displayed as a separate line item in the invoice and cart view.

### User Story
As a shop administrator, I want to configure shipping costs for physical products, so that customers are charged the appropriate shipping fee based on the most expensive shipping method required in their order.

### Acceptance Criteria
- [ ] JSON import format supports optional shipping cost configuration
- [ ] Items without shipping cost have `shipping_cost = 0.0` (default)
- [ ] Items with shipping cost have a positive float value (e.g., 0.99, 1.50, 5.99)
- [ ] When order is created, calculate max shipping cost: `max(item.shipping_cost for item in order_items)`
- [ ] Order `total_price` includes shipping: `total_price = items_sum + max_shipping_cost`
- [ ] Order model stores shipping cost separately for invoice display
- [ ] Cart view displays shipping cost breakdown:
  - "Items: €15.00"
  - "Shipping: €5.99"
  - "Total: €20.99"
- [ ] Invoice displays shipping as separate line item
- [ ] Multiple identical items share single shipping cost (max shipping applies once per order)
- [ ] If all items have no shipping cost, order has €0.00 shipping

### Technical Notes

**NEW JSON format:**
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "price": 12.25,
  "description": "Organic Dragon Well green tea",
  "private_data": "TEA-DRAGONWELL-UNIT061",
  "shipping_cost": 1.50
}
```

**Database Changes:**
- Add `Item.shipping_cost` field (Float, nullable=False, default=0.0)
- Add `Order.shipping_cost` field (Float, nullable=False, default=0.0)

**Order Calculation Example:**
```
Cart:
- 2x Green Tea (€12.00 each, €1.50 shipping)
- 1x Premium Tea (€25.00, €5.99 shipping)
- 1x eBook (€9.99, €0.00 shipping)

Calculation:
- Items total: €58.99
- Max shipping: max(€1.50, €5.99, €0.00) = €5.99
- Order total: €58.99 + €5.99 = €64.98
```

### Estimated Effort
Medium-High (1.5-2 hours)

### Dependencies
- Requires database migration for `shipping_cost` fields in Item and Order tables
- Must update all cart/order display logic
- Localization updates required

---

## Upselling Options (Optional Add-ons)

### Description
Implement an optional upselling system where items can offer additional options like premium packaging or insured shipping. Users select quantity first, then see upselling options in a second step before adding to cart. Each cart item can have different upselling selections.

### User Story
As a shop administrator, I want to offer optional add-ons like premium packaging and insured shipping for products, so that customers can customize their purchase and I can increase revenue through upselling.

### Acceptance Criteria
- [ ] JSON import format supports optional upselling configuration (**TXT format NOT supported**)
- [ ] Items without upsells go directly to cart after quantity selection (current behavior)
- [ ] Items with upsells show a second step with upselling options after quantity selection
- [ ] Two upsell types supported:
  - **Packaging:** Per-item option (e.g., "Standard" (free) vs "Premium" (+€4.00))
  - **Shipping Insurance:** Per-order option (e.g., "Standard shipping" vs "Insured shipping" (replaces standard shipping cost))
- [ ] User flow:
  1. Select quantity (e.g., "10x")
  2. See upselling options screen with toggleable buttons
  3. Click "Add to Cart" to confirm selection
- [ ] Upselling screen shows:
  - Selected item and quantity
  - Base price calculation
  - Packaging options (if configured)
  - Shipping options (if configured)
  - Total price preview
  - "Add to Cart" and "Cancel" buttons
- [ ] Each cart item stores its own upselling selections
- [ ] Multiple cart items of same product can have different upselling choices
- [ ] Cart displays upselling add-ons as sub-items with their prices
- [ ] Insured shipping replaces standard shipping cost (not additive)

### Technical Notes

**NEW JSON format:**
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "price_tiers": [...],
  "shipping_cost": 1.50,
  "upsells": [
    {
      "type": "packaging",
      "name_key": "upsell_premium_packaging",
      "price": 4.00
    },
    {
      "type": "shipping_insurance",
      "name_key": "upsell_insured_shipping",
      "price": 3.00
    }
  ]
}
```

**Localization (de.json / en.json):**
```json
// de.json
{
  "upsell_premium_packaging": "Komfort-Verpackung",
  "upsell_insured_shipping": "Versicherter Versand"
}

// en.json
{
  "upsell_premium_packaging": "Premium Packaging",
  "upsell_insured_shipping": "Insured Shipping"
}
```

**In code:**
```python
upsell_name = Localizator.get_text(BotEntity.USER, upsell.name_key)
```

**Database Changes:**
- Create new `upsells` table with columns: `id`, `item_id`, `type`, `name`, `price`
- Update `CartItem` model: Add `selected_upsells` JSON field
- Upsell types enum: `PACKAGING`, `SHIPPING_INSURANCE`

**User Flow Example:**
```
Step 1: Quantity Selection
[1x] [5x] [10x] [25x]

↓ User clicks "10x"

Step 2: Upselling Screen
Green Tea - 10x
Basispreis: €75.00

📦 Verpackung:
[✓ Standard (inkl.)] [Komfort +€4.00]

🚚 Versand:
[✓ Standard €1.50] [Versichert €3.00]

Gesamt: €75.00

[✓ In Warenkorb legen] [✗ Abbrechen]
```

**Cart Display:**
```
Green Tea - 10x
  + Komfort-Verpackung €4.00
= €79.00

Green Tea - 10x = €75.00

Items: €154.00
Shipping: €3.00 (versichert)
Total: €157.00
```

### Estimated Effort
High (3-4 hours)

### Dependencies
- Requires database migration for `upsells` table and `cart_items.selected_upsells` JSON field
- Requires callback data structure extension (careful: Telegram has 64-byte limit!)
- Requires new handler for upselling screen
- UI/UX requires careful design for toggle button behavior

### Technical Challenges
- **Callback Data Size Limit:** Telegram has 64-byte limit. Solution: Use compressed encoding `p123s456` for upsell IDs
- **N+1 Query Problem:** Use eager loading with JOINs
- **Upsell Consistency:** Store full upsell data in JSON (not just ID) to preserve pricing even if admin deletes upsell

---

## Referral System

### Description
Implement a referral system where established users (5+ completed orders) receive a unique referral code. When a new customer uses a referral code at checkout, the new customer receives 10% discount on their first order, and the referrer receives 1 FREE item (smallest quantity of cheapest item from their next cart) automatically added at checkout.

### User Story
As a shop administrator, I want to incentivize existing customers to refer new users through viral word-of-mouth marketing, while keeping the system economically balanced with minimum order values.

### Acceptance Criteria
- [ ] Users receive unique referral code after 5 successful (PAID) orders
- [ ] Referral code format: `U_{5-random-chars}` (e.g., `U_A3F9K`, `U_7X2PM`)
- [ ] Referral code is shown in user profile/account section
- [ ] New users can enter referral code during checkout (optional field)
- [ ] When referral code is applied:
  - **New customer:** 10% discount on first order (applied immediately, cap at €50)
  - **Referrer:** 1× FREE bonus item credit for their next order
- [ ] Bonus item selection algorithm (executed at checkout):
  1. Find cheapest item by unit price from cart
  2. Use smallest available quantity tier for that item
  3. If tie (same unit price + quantity): select random
  4. If item out of stock: try next-cheapest item
  5. If no items available: bonus credit is saved for future order
- [ ] Cart shows notification: "🎁 1 Gratis-Artikel wird beim Abschluss des Bestellvorgangs automatisch hinzugefügt"
- [ ] Bonus item is added automatically during order creation (not visible in cart preview)
- [ ] Bonus item is marked with `is_referral_bonus = True` flag
- [ ] Bonus item costs €0.00 (excluded from order total calculation)
- [ ] Each referral code can be used once per user-pair (User A can refer User B only once)
- [ ] Users cannot use their own referral code
- [ ] **NO HARD LIMIT on referrals per user** (viral growth is desired!)
- [ ] Referral bonus credits expire after 90 days
- [ ] Referral tracking:
  - Track who referred whom
  - Track bonus item details (subcategory, quantity, retail value)
  - Store discount amount for auditing
- [ ] After 5th successful order, user receives notification:
  - Congratulations message
  - Their unique referral code
  - Explanation of benefits (10% for friend, free item for them)
  - Instructions on how to share the code
- [ ] Discount cannot exceed order total (min. payment = €0.01)
- [ ] Optional monitoring: Alert admin if user exceeds 50 referrals (manual review)

### Security and Anti-Abuse Analysis

#### ✅ **Economic Safeguards (Self-Correcting System):**

With **€50 minimum order value**, the referral system is naturally protected from abuse:

**Fake-Account Economics:**
- Attacker investment: 5 Orders × €50 = €250 (to get referral code)
- Per fake order: €50 - 10% discount = €45 cost
- Per fake order reward: ~€15 bonus item (smallest tier of cheapest item)
- **ROI: 5-20%** (extremely low for high effort)

**Why Abuse is Unprofitable:**
1. ✅ High barrier to entry (€250 investment)
2. ✅ Each fake order costs €45 real money
3. ✅ Bonus items are small (~€10-20 value)
4. ✅ Crypto payment fees reduce margins further
5. ✅ Time investment makes it uneconomical

**Viral Growth is DESIRED:**
- If code goes viral (100+ uses) → 100 new paying customers!
- Your cost: ~€1500 in bonus items + €500 in 10% discounts
- Your gain: €4500 in revenue from new customers
- **Net profit: ~€2500 + 100 customers in database**

#### ✅ **Implemented Safeguards:**

1. **5-Order Threshold**
   - ✅ Prevents immediate multi-account abuse
   - ✅ Requires €250+ investment before referral eligibility
   - ✅ Makes throwaway accounts economically unviable

2. **One-Time Use Per User-Pair**
   - ✅ User A can refer User B only once
   - ✅ Prevents double-dipping from same relationship
   - ✅ Database constraint: `UniqueConstraint('referrer_user_id', 'referred_user_id')`

3. **Self-Referral Prevention**
   - ✅ Users cannot use their own referral code
   - ✅ Database constraint: `CheckConstraint('referrer_user_id != referred_user_id')`

4. **Payment Requirement**
   - ✅ Only PAID orders count toward 5-order threshold
   - ✅ Prevents fake orders from qualifying user

5. **90-Day Expiry**
   - ✅ Bonus credits expire after 90 days
   - ✅ Prevents unlimited accumulation

6. **Discount Cap**
   - ✅ New customer discount capped at €50
   - ✅ Prevents abuse on large orders

#### ⚠️ **Monitoring Recommendations (Optional):**

**Soft Limits (No Hard Enforcement):**
- Alert admin if user exceeds 50 successful referrals
- Manual review for suspicious patterns:
  - Multiple accounts from same IP
  - Unusually high referral rates
  - Repeated cancelled orders after referral

**Why NO Hard Limit:**
- Viral growth is the GOAL
- 100+ referrals = excellent marketing ROI
- €50 minimum order makes abuse unprofitable
- Self-correcting economic model

#### 🔒 **Recommended Security Implementation:**

```python
# models/user.py
class User(Base):
    # Existing fields...

    # Referral System
    referral_code = Column(String(8), unique=True, nullable=True)  # U_A3F9K
    referral_code_created_at = Column(DateTime, nullable=True)
    successful_orders_count = Column(Integer, default=0)  # Tracks PAID orders
    referral_eligible = Column(Boolean, default=False)  # True after 5 orders

    # Anti-Abuse
    max_referrals = Column(Integer, default=10)  # Max 10 successful referrals
    successful_referrals_count = Column(Integer, default=0)

    # Who referred this user?
    referred_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referred_at = Column(DateTime, nullable=True)

# models/referral_discount.py (NEW FILE)
class ReferralDiscount(Base):
    __tablename__ = 'referral_discounts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    discount_percentage = Column(Float, default=10.0)
    max_discount_amount = Column(Float, default=50.0)  # Cap at €50
    reason = Column(String, nullable=False)  # "Referred user U_A3F9K"

    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)

    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)  # Optional: 90-day expiry

# models/referral_usage.py (NEW FILE)
class ReferralUsage(Base):
    __tablename__ = 'referral_usages'

    id = Column(Integer, primary_key=True)
    referral_code = Column(String(8), nullable=False)
    referrer_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    discount_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        # Prevent same user from being referred by same code twice
        UniqueConstraint('referrer_user_id', 'referred_user_id', name='uq_referrer_referred'),
        # Prevent self-referral
        CheckConstraint('referrer_user_id != referred_user_id', name='check_no_self_referral'),
    )
```

### Technical Notes

#### Referral Code Generation

```python
import secrets
import string

def generate_referral_code() -> str:
    """
    Generates a unique referral code in format U_XXXXX
    where X is alphanumeric (uppercase + numbers)
    """
    alphabet = string.ascii_uppercase + string.digits  # A-Z, 0-9
    random_part = ''.join(secrets.choice(alphabet) for _ in range(5))
    return f"U_{random_part}"

# In OrderService.complete_order_payment():
async def complete_order_payment(order_id: int, session: AsyncSession):
    # ... existing code ...

    # Check if user now qualifies for referral
    user = await UserRepository.get_by_order_id(order_id, session)
    user.successful_orders_count += 1

    if user.successful_orders_count == 5 and not user.referral_eligible:
        # Generate referral code
        while True:
            code = generate_referral_code()
            # Check uniqueness
            existing = await UserRepository.get_by_referral_code(code, session)
            if not existing:
                break

        user.referral_code = code
        user.referral_code_created_at = datetime.utcnow()
        user.referral_eligible = True

        await UserRepository.update(user, session)

        # Send notification
        await NotificationService.send_referral_eligibility_notification(user, session)
```

#### Checkout Flow with Referral

```python
# In checkout process (after crypto selection, before order creation)
async def show_referral_code_input(callback: CallbackQuery, session: AsyncSession):
    """
    Shows optional referral code input before order creation.
    """
    user = await UserRepository.get_by_tgid(callback.from_user.id, session)

    # Check if user already used referral bonus
    if user.referred_by_user_id is not None:
        # Skip referral input, proceed to order creation
        return await create_order(callback, session)

    message_text = Localizator.get_text(BotEntity.USER, "referral_code_prompt")
    kb_builder = InlineKeyboardBuilder()

    # "Enter Referral Code" button (triggers FSM state for text input)
    kb_builder.button(
        text=Localizator.get_text(BotEntity.USER, "enter_referral_code"),
        callback_data=CartCallback.create(6)  # Level 6 = Enter Referral Code
    )

    # "Skip" button
    kb_builder.button(
        text=Localizator.get_text(BotEntity.USER, "skip_referral"),
        callback_data=CartCallback.create(4, cryptocurrency=selected_crypto)  # Proceed to order
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())

# FSM state handler for referral code input
@router.message(StateFilter(CheckoutState.waiting_for_referral_code))
async def process_referral_code(message: Message, state: FSMContext, session: AsyncSession):
    """
    Validates and applies referral code.
    """
    referral_code = message.text.strip().upper()
    user = await UserRepository.get_by_tgid(message.from_user.id, session)

    # Validate referral code
    referrer = await UserRepository.get_by_referral_code(referral_code, session)

    if not referrer:
        await message.answer(Localizator.get_text(BotEntity.USER, "referral_code_invalid"))
        return

    if referrer.id == user.id:
        await message.answer(Localizator.get_text(BotEntity.USER, "referral_code_self"))
        return

    if referrer.successful_referrals_count >= referrer.max_referrals:
        await message.answer(Localizator.get_text(BotEntity.USER, "referral_code_limit_reached"))
        return

    # Check if already used this referrer's code
    existing_usage = await ReferralUsageRepository.get_by_users(referrer.id, user.id, session)
    if existing_usage:
        await message.answer(Localizator.get_text(BotEntity.USER, "referral_code_already_used"))
        return

    # Store referral code in state for order creation
    await state.update_data(referral_code=referral_code, referrer_id=referrer.id)

    await message.answer(Localizator.get_text(BotEntity.USER, "referral_code_applied"))
    await state.clear()

    # Proceed to order creation
    await create_order_with_referral(message, referrer.id, session)
```

#### Order Creation with Referral Discount

```python
async def create_order_with_referral(
    callback: CallbackQuery,
    referrer_id: int | None,
    session: AsyncSession
):
    """
    Creates order with referral discount applied (if applicable).
    """
    user = await UserRepository.get_by_tgid(callback.from_user.id, session)
    cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

    # Calculate base order total
    base_total = 0.0
    for cart_item in cart_items:
        # ... calculate items + shipping + upsells ...
        base_total += item_price

    # Apply referral discount (if applicable)
    referral_discount_amount = 0.0
    if referrer_id is not None:
        # New customer gets 10% off
        referral_discount_amount = min(
            base_total * 0.10,  # 10%
            50.0,  # Cap at €50
            base_total - 0.01  # Min payment €0.01
        )

    final_total = base_total - referral_discount_amount

    # Create order
    order_dto = OrderDTO(
        user_id=user.id,
        total_price=final_total,
        # ... other fields ...
    )
    order_id = await OrderRepository.create(order_dto, session)

    # Record referral usage (if applicable)
    if referrer_id is not None:
        user.referred_by_user_id = referrer_id
        user.referred_at = datetime.utcnow()
        await UserRepository.update(user, session)

        # Create referral usage record
        referral_usage = ReferralUsageDTO(
            referral_code=referrer.referral_code,
            referrer_user_id=referrer_id,
            referred_user_id=user.id,
            order_id=order_id,
            discount_amount=referral_discount_amount
        )
        await ReferralUsageRepository.create(referral_usage, session)

        # Grant referrer a 10% discount for next order
        referrer_discount = ReferralDiscountDTO(
            user_id=referrer_id,
            discount_percentage=10.0,
            max_discount_amount=50.0,
            reason=f"Referred user {user.telegram_username or user.telegram_id}"
        )
        await ReferralDiscountRepository.create(referrer_discount, session)

        # Increment referrer's successful referrals
        referrer = await UserRepository.get_by_id(referrer_id, session)
        referrer.successful_referrals_count += 1
        await UserRepository.update(referrer, session)

        # Notify referrer
        await NotificationService.send_referral_success_notification(referrer, user, session)

    # ... rest of order creation (invoice, etc.) ...
```

#### Applying Referral Discount on Next Order

```python
async def calculate_order_total_with_discounts(
    user_id: int,
    base_total: float,
    session: AsyncSession
) -> tuple[float, int | None]:
    """
    Calculates final order total with referral discount applied.
    Returns (final_total, used_discount_id)
    """
    # Get oldest unused referral discount
    unused_discount = await ReferralDiscountRepository.get_oldest_unused(user_id, session)

    if not unused_discount:
        return base_total, None

    # Calculate discount amount
    discount_amount = min(
        base_total * (unused_discount.discount_percentage / 100),
        unused_discount.max_discount_amount,
        base_total - 0.01  # Min payment €0.01
    )

    final_total = base_total - discount_amount

    return final_total, unused_discount.id

# Mark discount as used after successful payment
async def mark_discount_used(discount_id: int, order_id: int, session: AsyncSession):
    discount = await ReferralDiscountRepository.get_by_id(discount_id, session)
    discount.used = True
    discount.used_at = datetime.utcnow()
    discount.order_id = order_id
    await ReferralDiscountRepository.update(discount, session)
```

### Localization Keys

```json
// de.json
{
  "referral_eligibility_notification": "🎉 <b>Glückwunsch!</b>\n\nDu hast 5 erfolgreiche Bestellungen abgeschlossen und kannst jetzt Freunde werben!\n\n🎁 <b>Dein Referral-Code:</b> <code>{referral_code}</code>\n\n<b>Vorteile:</b>\n• Dein Freund erhält <b>10% Rabatt</b> auf die erste Bestellung\n• Du erhältst <b>10% Rabatt</b> auf deine nächste Bestellung\n\n📤 Teile deinen Code mit Freunden und profitiert beide!",

  "referral_code_prompt": "🎁 <b>Hast du einen Referral-Code?</b>\n\nWenn ein Freund dich geworben hat, gib hier seinen Code ein und erhalte <b>10% Rabatt</b> auf diese Bestellung!",

  "enter_referral_code": "📝 Referral-Code eingeben",
  "skip_referral": "⏩ Überspringen",

  "referral_code_invalid": "❌ Ungültiger Referral-Code. Bitte überprüfe den Code und versuche es erneut.",
  "referral_code_self": "❌ Du kannst deinen eigenen Referral-Code nicht verwenden.",
  "referral_code_limit_reached": "❌ Dieser Referral-Code hat das maximale Limit erreicht.",
  "referral_code_already_used": "❌ Du hast diesen Referral-Code bereits verwendet.",
  "referral_code_applied": "✅ Referral-Code angewendet! Du erhältst 10% Rabatt auf diese Bestellung.",

  "referral_success_notification": "🎉 <b>Neuer Referral!</b>\n\nDein Freund <b>{referred_username}</b> hat deinen Referral-Code verwendet.\n\nDu erhältst <b>10% Rabatt</b> auf deine nächste Bestellung! 🎁",

  "order_with_referral_discount": "📦 <b>Bestellung #{invoice_number}</b>\n\n<b>Artikel:</b> €{items_total:.2f}\n<b>Versand:</b> €{shipping_cost:.2f}\n<b>Zwischensumme:</b> €{subtotal:.2f}\n\n🎁 <b>Referral-Rabatt (10%):</b> -€{discount_amount:.2f}\n\n<b>Gesamt:</b> €{total_price:.2f}"
}

// en.json
{
  "referral_eligibility_notification": "🎉 <b>Congratulations!</b>\n\nYou've completed 5 successful orders and can now refer friends!\n\n🎁 <b>Your Referral Code:</b> <code>{referral_code}</code>\n\n<b>Benefits:</b>\n• Your friend gets <b>10% off</b> their first order\n• You get <b>10% off</b> your next order\n\n📤 Share your code with friends and both benefit!",

  "referral_code_prompt": "🎁 <b>Do you have a referral code?</b>\n\nIf a friend referred you, enter their code here and get <b>10% off</b> this order!",

  "enter_referral_code": "📝 Enter Referral Code",
  "skip_referral": "⏩ Skip",

  "referral_code_invalid": "❌ Invalid referral code. Please check and try again.",
  "referral_code_self": "❌ You cannot use your own referral code.",
  "referral_code_limit_reached": "❌ This referral code has reached its maximum limit.",
  "referral_code_already_used": "❌ You have already used this referral code.",
  "referral_code_applied": "✅ Referral code applied! You'll receive 10% off this order.",

  "referral_success_notification": "🎉 <b>New Referral!</b>\n\nYour friend <b>{referred_username}</b> used your referral code.\n\nYou'll get <b>10% off</b> your next order! 🎁",

  "order_with_referral_discount": "📦 <b>Order #{invoice_number}</b>\n\n<b>Items:</b> €{items_total:.2f}\n<b>Shipping:</b> €{shipping_cost:.2f}\n<b>Subtotal:</b> €{subtotal:.2f}\n\n🎁 <b>Referral Discount (10%):</b> -€{discount_amount:.2f}\n\n<b>Total:</b> €{total_price:.2f}"
}
```

### Implementation Order

1. Create `models/referral_discount.py` and `models/referral_usage.py`
2. Update `models/user.py` with referral fields
3. Create database migrations
4. Create `repositories/referral_discount.py` and `repositories/referral_usage.py`
5. Implement referral code generation logic
6. Update `OrderService.complete_order_payment()` to check for 5th order and grant referral eligibility
7. Create `NotificationService.send_referral_eligibility_notification()`
8. Add referral code input step in checkout flow (FSM state)
9. Update `OrderService.create_order_from_cart()` to apply referral discount
10. Implement referral usage tracking
11. Add user profile section to display referral code
12. Add localization keys (DE/EN)
13. Testing:
    - User reaches 5 orders → receives code
    - New user uses code → 10% off
    - Referrer gets 10% off next order
    - Self-referral prevention
    - Code uniqueness
    - Max referrals limit (10)

### Estimated Effort
High (3-4 hours)

### Dependencies
- Requires database migrations for User, ReferralDiscount, and ReferralUsage tables
- Requires FSM state for referral code input
- Must update order creation flow
- Must update invoice display to show referral discount

### Security Recommendations Summary

1. ✅ **Implement 10-referral limit per user** (prevents industrial farming)
2. ✅ **Cap discount at €50** (prevents abuse on large orders)
3. ✅ **Only one discount per order** (prevents stacking)
4. ✅ **Minimum payment €0.01** (prevents free orders)
5. ✅ **Track successful_orders_count** (only PAID orders count)
6. ✅ **Unique constraint on referrer-referred pairs** (prevents double-dipping)
7. ✅ **Self-referral check** (database constraint)
8. ⚠️ **Monitor for suspicious patterns** (optional: multiple accounts from same IP)

### Open Questions
1. Should referral discounts expire after 90 days?
2. Should there be a minimum order value to qualify for referral discount?
3. Should admins be able to manually adjust referral limits for trusted users?
4. Should we display referral statistics to users (e.g., "You've referred 3/10 friends")?

---

## Admin Order Cancellation

### Description
Enable administrators to manually cancel orders at any point in the order lifecycle without penalizing the customer with strikes. Admin cancellations are tracked separately from user cancellations and trigger appropriate notifications to the affected user.

### User Story
As an administrator, I want to manually cancel problematic orders (fraud, out-of-stock errors, customer service requests) without affecting the customer's strike count, so that I can maintain operational flexibility and customer satisfaction.

### Acceptance Criteria
- [ ] Admin panel shows list of active orders (PENDING_PAYMENT, PAID, SHIPPED)
- [ ] Admin can select an order and click "Cancel Order" button
- [ ] Confirmation dialog shows order details and reason input field
- [ ] Order status is set to `CANCELLED_BY_ADMIN` (already exists in OrderStatus enum)
- [ ] User receives notification about admin cancellation with reason
- [ ] If order was PENDING_PAYMENT:
  - Reserved items are released back to stock
  - Invoice is marked as cancelled
- [ ] If order was PAID:
  - Admin must manually process refund (system shows refund instructions)
  - Items remain marked as sold (admin must manually adjust stock if needed)
  - Refund tracking record is created
- [ ] User does NOT receive a strike (unlike CANCELLED_BY_USER after grace period)
- [ ] Admin action is logged with:
  - Admin user ID
  - Timestamp
  - Cancellation reason
  - Order state at time of cancellation

### Technical Notes

#### Admin Handler
```python
# handlers/admin/order_management.py (NEW FILE)
async def show_active_orders(callback: CallbackQuery, session: AsyncSession):
    """Shows list of active orders for admin to manage."""
    orders = await OrderRepository.get_active_orders(session)

    kb_builder = InlineKeyboardBuilder()
    for order in orders:
        order_text = f"#{order.invoice.invoice_number} - {order.user.telegram_username} - €{order.total_price:.2f}"
        kb_builder.button(
            text=order_text,
            callback_data=OrderManagementCallback.create(1, order_id=order.id)
        )

    kb_builder.adjust(1)
    await callback.message.edit_text("Active Orders:", reply_markup=kb_builder.as_markup())

async def show_order_details(callback: CallbackQuery, session: AsyncSession):
    """Shows order details with cancel button."""
    unpacked_cb = OrderManagementCallback.unpack(callback.data)
    order = await OrderRepository.get_by_id(unpacked_cb.order_id, session)

    details = f"""
📦 Order #{order.invoice.invoice_number}
User: @{order.user.telegram_username}
Status: {order.status.value}
Total: €{order.total_price:.2f}
Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}
    """

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="❌ Cancel Order",
        callback_data=OrderManagementCallback.create(2, order_id=order.id)
    )
    kb_builder.button(text="« Back", callback_data=OrderManagementCallback.create(0))

    await callback.message.edit_text(details, reply_markup=kb_builder.as_markup())

async def request_cancellation_reason(callback: CallbackQuery, state: FSMContext):
    """Prompts admin for cancellation reason."""
    unpacked_cb = OrderManagementCallback.unpack(callback.data)

    await state.update_data(order_id=unpacked_cb.order_id)
    await state.set_state(OrderManagementStates.cancellation_reason)

    await callback.message.edit_text(
        "Please provide a cancellation reason (will be shown to user):"
    )

async def cancel_order_by_admin(message: Message, state: FSMContext, session: AsyncSession):
    """Executes admin cancellation."""
    data = await state.get_data()
    order_id = data['order_id']
    reason = message.text

    admin_user_id = message.from_user.id

    result = await OrderService.cancel_order_by_admin(
        order_id,
        admin_user_id,
        reason,
        session
    )

    await state.clear()
    await message.answer(f"✅ Order cancelled successfully.\n\n{result}")
```

#### Service Logic
```python
# services/order.py
@staticmethod
async def cancel_order_by_admin(
    order_id: int,
    admin_user_id: int,
    reason: str,
    session: AsyncSession | Session
) -> str:
    """
    Cancels an order by admin without user penalty.

    Returns:
        str: Result message with refund instructions if needed
    """
    from datetime import datetime

    # Get order
    order = await OrderRepository.get_by_id(order_id, session)

    if not order:
        raise ValueError("Order not found")

    if order.status in [OrderStatus.CANCELLED_BY_USER, OrderStatus.CANCELLED_BY_ADMIN, OrderStatus.TIMEOUT]:
        raise ValueError(f"Order already cancelled (Status: {order.status.value})")

    # Handle based on status
    if order.status == OrderStatus.PENDING_PAYMENT:
        # Release reserved items
        items = await ItemRepository.get_by_order_id(order_id, session)
        for item in items:
            item.order_id = None
        await ItemRepository.update(items, session)

        result_msg = "Order cancelled. Reserved items released back to stock."

    elif order.status == OrderStatus.PAID:
        # PAID orders require manual refund
        invoice = await InvoiceRepository.get_by_order_id(order_id, session)
        result_msg = f"""
Order cancelled. MANUAL REFUND REQUIRED:

Invoice: #{invoice.invoice_number}
Amount: €{order.total_price:.2f} ({invoice.payment_amount_crypto} {invoice.payment_crypto_currency.value})
Payment Address: {invoice.payment_address}

⚠️ You must manually process the refund via KryptoExpress dashboard.
        """

        # Create refund tracking record
        # TODO: Implement RefundRepository.create_pending_refund()

    elif order.status == OrderStatus.SHIPPED:
        result_msg = "Order cancelled. Contact customer for return shipping instructions."

    # Set order status
    await OrderRepository.update_status(order_id, OrderStatus.CANCELLED_BY_ADMIN, session)

    # Log admin action
    await AdminActionLogRepository.create(
        admin_user_id=admin_user_id,
        action_type="CANCEL_ORDER",
        target_order_id=order_id,
        reason=reason,
        session=session
    )

    # Notify user
    user = await UserRepository.get_by_id(order.user_id, session)
    await NotificationService.send_admin_cancellation_notification(
        user,
        order,
        reason,
        session
    )

    await session_commit(session)

    return result_msg
```

#### Database Changes
```python
# models/admin_action_log.py (NEW FILE)
class AdminActionLog(Base):
    __tablename__ = 'admin_action_logs'

    id = Column(Integer, primary_key=True)
    admin_user_id = Column(Integer, nullable=False)  # Telegram ID
    action_type = Column(String, nullable=False)  # "CANCEL_ORDER", "BAN_USER", etc.
    target_order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    target_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
```

### Localization Keys

```json
// de.json
{
  "admin_order_cancellation_notification": "⚠️ <b>Bestellung storniert</b>\n\nDeine Bestellung <b>#{invoice_number}</b> wurde vom Administrator storniert.\n\n<b>Grund:</b> {reason}\n\n<b>Status:</b> {status_message}\n\nBei Fragen kontaktiere bitte den Support: {support_link}",

  "admin_order_cancelled_pending": "Die Reservierung wurde aufgehoben. Du kannst eine neue Bestellung aufgeben.",
  "admin_order_cancelled_paid": "Die Rückerstattung wird in Kürze bearbeitet."
}

// en.json
{
  "admin_order_cancellation_notification": "⚠️ <b>Order Cancelled</b>\n\nYour order <b>#{invoice_number}</b> has been cancelled by an administrator.\n\n<b>Reason:</b> {reason}\n\n<b>Status:</b> {status_message}\n\nIf you have questions, please contact support: {support_link}",

  "admin_order_cancelled_pending": "The reservation has been released. You can place a new order.",
  "admin_order_cancelled_paid": "Your refund will be processed shortly."
}
```

### Implementation Order

1. Create `models/admin_action_log.py` with database schema
2. Create database migration
3. Create `repositories/admin_action_log.py`
4. Implement `OrderService.cancel_order_by_admin()`
5. Create `handlers/admin/order_management.py` with UI
6. Add `OrderManagementCallback` to callbacks.py
7. Create `OrderManagementStates` FSM states
8. Implement `NotificationService.send_admin_cancellation_notification()`
9. Add localization keys (DE/EN)
10. Add "Order Management" button to admin menu
11. Testing:
    - Cancel PENDING_PAYMENT order → items released
    - Cancel PAID order → refund instructions shown
    - User receives notification without strike
    - Admin action logged correctly

### Estimated Effort
Medium (1.5-2 hours)

### Dependencies
- Requires `AdminActionLog` model and repository
- User notification system must be functional
- Admin authentication/authorization must be in place

---

## Invoice-Based Payment System & Stock Management

### Description
Implement a comprehensive invoice-based payment system integrated with KryptoExpress API for cryptocurrency payments. The system handles invoice generation, payment tracking, stock reservation during payment processing, and automatic fulfillment upon payment confirmation. Includes webhook support for real-time payment status updates.

### User Story
As a customer, I want to receive a unique payment invoice with crypto payment details when I checkout, and have my order automatically processed when payment is confirmed, so that I have a seamless and secure purchase experience.

### Current Implementation Status
**✅ PARTIALLY IMPLEMENTED** (Branch: `feature/invoice-stock-management`)

**Already Implemented:**
- ✅ Invoice model with unique invoice numbers (format: `YYYY-XXXXXX`)
- ✅ InvoiceService with KryptoExpress API integration
- ✅ Mock payment mode for testing without real API
- ✅ OrderService creates invoices during checkout
- ✅ Stock reservation during PENDING_PAYMENT status
- ✅ Payment completion marks items as sold and updates order status

**Missing Features:**
- ⚠️ Webhook endpoint for KryptoExpress payment notifications
- ⚠️ Payment timeout job (expires unpaid orders)
- ⚠️ Invoice display in user interface (show payment address, QR code, amount)
- ⚠️ Payment status polling (optional: if webhooks fail)
- ⚠️ Admin invoice management (view, resend, mark paid manually)

### Acceptance Criteria

#### Core Invoice System (✅ Implemented)
- [x] Each order generates unique invoice with format `YYYY-XXXXXX`
- [x] Invoice stores payment details: address, crypto amount, currency, processing ID
- [x] InvoiceService integrates with KryptoExpress API
- [x] Mock mode for development/testing without real API keys
- [x] Stock reservation during PENDING_PAYMENT status prevents overselling
- [x] Payment completion triggers `OrderService.complete_order_payment()`

#### Missing Features (To Implement)
- [ ] **Webhook Endpoint:**
  - Receive POST requests from KryptoExpress on payment status updates
  - Validate webhook signature (HMAC)
  - Update order status based on payment status
  - Trigger order fulfillment on successful payment
  - Handle failed/expired payments

- [ ] **Payment Timeout Job:**
  - Scheduled job runs every 5 minutes
  - Checks for orders with `expires_at < now()` and status PENDING_PAYMENT
  - Marks expired orders as TIMEOUT status
  - Releases reserved stock
  - Notifies user (if enabled)
  - Increments user strike counter

- [ ] **Invoice Display UI:**
  - Show invoice details after checkout
  - Display payment address with copy-to-clipboard button
  - Show QR code for crypto payment (encoded payment address + amount)
  - Display countdown timer until payment expires
  - Show payment amount in both crypto and fiat
  - "Check Payment Status" button for manual refresh

- [ ] **Payment Status Polling (Fallback):**
  - If webhook fails, poll KryptoExpress API every 30 seconds
  - Check payment status via `payment_processing_id`
  - Update order status on confirmed payment
  - Max 20 polling attempts (10 minutes)

- [ ] **Admin Invoice Management:**
  - View all invoices with filters (status, date range, crypto)
  - Search by invoice number or order ID
  - Manually mark invoice as paid (emergency override)
  - Resend payment notification to user
  - View payment transaction details from KryptoExpress

### Technical Notes

#### Webhook Endpoint
```python
# handlers/webhook/payment_webhook.py (NEW FILE)
from aiogram import Router, F
from aiogram.types import Update
import hmac
import hashlib

webhook_router = Router()

@webhook_router.post("/webhook/kryptoexpress")
async def handle_payment_webhook(request: Request, session: AsyncSession):
    """
    Handles KryptoExpress payment status webhooks.

    Expected payload:
    {
        "id": 123456,  # payment_processing_id
        "status": "COMPLETED" | "FAILED" | "EXPIRED",
        "cryptoAmount": 0.0012,
        "cryptoCurrency": "BTC",
        "timestamp": "2025-01-18T12:00:00Z",
        "signature": "hmac_sha256_signature"
    }
    """

    # Parse payload
    payload = await request.json()

    # Validate signature
    signature = payload.pop('signature')
    expected_signature = hmac.new(
        config.KRYPTO_EXPRESS_WEBHOOK_SECRET.encode(),
        json.dumps(payload, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Find invoice by processing ID
    processing_id = payload['id']
    invoice = await InvoiceRepository.get_by_payment_processing_id(processing_id, session)

    if not invoice:
        logging.warning(f"Webhook received for unknown processing ID: {processing_id}")
        return {"status": "ignored"}

    # Handle payment status
    payment_status = payload['status']

    if payment_status == "COMPLETED":
        # Payment successful → complete order
        await OrderService.complete_order_payment(invoice.order_id, session)

        # Notify user
        order = await OrderRepository.get_by_id(invoice.order_id, session)
        user = await UserRepository.get_by_id(order.user_id, session)
        await NotificationService.send_payment_confirmed_notification(user, order, session)

        logging.info(f"Payment completed for order {invoice.order_id}")

    elif payment_status in ["FAILED", "EXPIRED"]:
        # Payment failed → release stock and mark order
        await OrderService.expire_order(invoice.order_id, session)
        logging.info(f"Payment {payment_status.lower()} for order {invoice.order_id}")

    await session_commit(session)

    return {"status": "processed"}
```

#### Payment Timeout Job
```python
# jobs/payment_timeout_job.py (NEW FILE)
import asyncio
from datetime import datetime

async def check_expired_orders():
    """
    Runs every 5 minutes to expire unpaid orders.
    """
    async with get_async_session() as session:
        # Get expired orders
        expired_orders = await OrderRepository.get_expired_pending_orders(session)

        for order in expired_orders:
            logging.info(f"Expiring order {order.id} (created: {order.created_at})")

            # Release stock
            items = await ItemRepository.get_by_order_id(order.id, session)
            for item in items:
                item.order_id = None
            await ItemRepository.update(items, session)

            # Update status
            await OrderRepository.update_status(order.id, OrderStatus.TIMEOUT, session)

            # Increment user strike
            user = await UserRepository.get_by_id(order.user_id, session)
            await OrderService.increment_strike(user.id, "Order timeout", session)

            # Notify user (optional)
            await NotificationService.send_order_timeout_notification(user, order, session)

        await session_commit(session)

        logging.info(f"Expired {len(expired_orders)} orders")

# In main.py or scheduler
async def start_payment_timeout_job():
    while True:
        try:
            await check_expired_orders()
        except Exception as e:
            logging.error(f"Payment timeout job error: {e}")

        await asyncio.sleep(300)  # 5 minutes
```

#### Invoice Display UI
```python
# services/cart.py
async def show_invoice(callback: CallbackQuery, order_id: int, session: AsyncSession):
    """Shows invoice with payment details."""
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)

    # Calculate time remaining
    time_remaining = (order.expires_at - datetime.now()).total_seconds() / 60

    message_text = Localizator.get_text(BotEntity.USER, "invoice_payment_details").format(
        invoice_number=invoice.invoice_number,
        crypto_amount=invoice.payment_amount_crypto,
        crypto_currency=invoice.payment_crypto_currency.value,
        fiat_amount=invoice.fiat_amount,
        fiat_currency=invoice.fiat_currency.value,
        payment_address=invoice.payment_address,
        expires_in_minutes=int(time_remaining)
    )

    kb_builder = InlineKeyboardBuilder()

    # Copy address button (deeplink to clipboard)
    kb_builder.button(
        text="📋 Copy Address",
        callback_data=InvoiceCallback.create(1, invoice_id=invoice.id)
    )

    # Check payment status button
    kb_builder.button(
        text="🔄 Check Payment Status",
        callback_data=InvoiceCallback.create(2, invoice_id=invoice.id)
    )

    kb_builder.adjust(1)

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())

    # Send QR code image
    qr_image = generate_crypto_qr_code(
        invoice.payment_address,
        invoice.payment_amount_crypto,
        invoice.payment_crypto_currency
    )
    await callback.message.answer_photo(qr_image, caption="Scan QR to pay")
```

#### Repository Extensions
```python
# repositories/order.py
@staticmethod
async def get_expired_pending_orders(session: AsyncSession) -> list[OrderDTO]:
    """Gets all PENDING_PAYMENT orders past their expires_at time."""
    stmt = select(Order).where(
        Order.status == OrderStatus.PENDING_PAYMENT,
        Order.expires_at < datetime.now()
    )
    result = await session_execute(stmt, session)
    orders = result.scalars().all()

    return [OrderDTO.model_validate(o, from_attributes=True) for o in orders]
```

### Configuration (.env)
```bash
# KryptoExpress API
KRYPTO_EXPRESS_API_URL=https://api.kryptoexpress.com
KRYPTO_EXPRESS_API_KEY=your_api_key_here
KRYPTO_EXPRESS_WEBHOOK_SECRET=your_webhook_secret_here

# Order Settings
ORDER_TIMEOUT_MINUTES=15  # How long user has to pay
ORDER_CANCEL_GRACE_PERIOD_MINUTES=5  # Free cancellation window
```

### Localization Keys

```json
// de.json
{
  "invoice_payment_details": "💳 <b>Rechnung #{invoice_number}</b>\n\n<b>Zu zahlender Betrag:</b>\n{crypto_amount} {crypto_currency} (≈ €{fiat_amount:.2f})\n\n<b>Zahlungsadresse:</b>\n<code>{payment_address}</code>\n\n⏰ <b>Verfällt in:</b> {expires_in_minutes} Minuten\n\n⚠️ Bitte überweise <b>exakt</b> den angegebenen Betrag an die Adresse oben.",

  "payment_confirmed": "✅ <b>Zahlung bestätigt!</b>\n\nDeine Bestellung #{invoice_number} wurde erfolgreich bezahlt.\n\nDeine Artikel werden in Kürze versendet.",

  "order_timeout": "⏰ <b>Bestellung abgelaufen</b>\n\nDeine Bestellung #{invoice_number} ist abgelaufen, da keine Zahlung innerhalb von {timeout_minutes} Minuten eingegangen ist.\n\nDie Reservierung wurde aufgehoben. Du kannst eine neue Bestellung aufgeben."
}

// en.json
{
  "invoice_payment_details": "💳 <b>Invoice #{invoice_number}</b>\n\n<b>Amount to Pay:</b>\n{crypto_amount} {crypto_currency} (≈ €{fiat_amount:.2f})\n\n<b>Payment Address:</b>\n<code>{payment_address}</code>\n\n⏰ <b>Expires in:</b> {expires_in_minutes} minutes\n\n⚠️ Please send <b>exactly</b> the specified amount to the address above.",

  "payment_confirmed": "✅ <b>Payment Confirmed!</b>\n\nYour order #{invoice_number} has been successfully paid.\n\nYour items will be shipped shortly.",

  "order_timeout": "⏰ <b>Order Expired</b>\n\nYour order #{invoice_number} has expired because no payment was received within {timeout_minutes} minutes.\n\nThe reservation has been released. You can place a new order."
}
```

### Implementation Order

1. ✅ Invoice model and repository (DONE)
2. ✅ InvoiceService with KryptoExpress integration (DONE)
3. ✅ OrderService integration (DONE)
4. ✅ Stock reservation logic (DONE)
5. [ ] Add webhook endpoint (`handlers/webhook/payment_webhook.py`)
6. [ ] Implement webhook signature validation
7. [ ] Create payment timeout job (`jobs/payment_timeout_job.py`)
8. [ ] Add timeout job to application startup
9. [ ] Implement invoice display UI (`services/cart.py`)
10. [ ] Add QR code generation for crypto payments
11. [ ] Implement "Check Payment Status" polling fallback
12. [ ] Add admin invoice management views
13. [ ] Add configuration values to `.env` and `config.py`
14. [ ] Add localization keys (DE/EN)
15. [ ] Testing:
    - Create order → invoice generated
    - Webhook receives payment → order completed
    - Order expires → stock released, user notified
    - Payment polling works if webhook fails
    - Admin can view/manage invoices

### Estimated Effort
High (4-5 hours for missing features)

### Dependencies
- Requires KryptoExpress API credentials
- Webhook endpoint must be publicly accessible (use ngrok for development)
- QR code generation library (e.g., `qrcode` or `segno`)
- Scheduled job system (asyncio or APScheduler)

### Benefits
- Automated payment processing reduces manual work
- Stock reservation prevents overselling
- Webhook integration provides real-time updates
- Invoice system creates audit trail
- Timeout job prevents indefinite stock locks
- Mock mode enables development without real payments

---

## GPG Public Key Display

### Description
Display the shop administrator's public GPG key in the main menu to enable users to verify encrypted communications and understand encryption options for sensitive data like shipping addresses.

### User Story
As a privacy-conscious customer, I want to see the shop's public GPG key, so that I can verify the identity of the shop and optionally encrypt sensitive information before sending it.

### Acceptance Criteria
- [ ] Main menu has "🔐 GPG Public Key" button
- [ ] Clicking button shows formatted public key in message
- [ ] Message includes:
  - Full ASCII-armored public key block
  - Key fingerprint
  - Key expiration date (if applicable)
  - Short explanation of what GPG is
  - Link to GPG tutorial (optional)
- [ ] "Copy Key" functionality (user can select and copy)
- [ ] Back button to return to main menu
- [ ] Localization (DE/EN)

### Technical Notes

#### Configuration (.env)
```bash
# GPG Configuration
GPG_PUBLIC_KEY_FILE=/path/to/pubkey.asc  # Path to ASCII-armored public key
GPG_KEY_FINGERPRINT=ABCD1234EFGH5678...  # Key fingerprint for display
```

#### Implementation
```python
# services/user.py or handlers/user/menu.py
async def show_gpg_public_key(callback: CallbackQuery):
    """Shows shop's public GPG key."""

    # Read public key from file
    with open(config.GPG_PUBLIC_KEY_FILE, 'r') as f:
        public_key = f.read()

    message_text = Localizator.get_text(BotEntity.USER, "gpg_public_key_info").format(
        fingerprint=config.GPG_KEY_FINGERPRINT
    )

    # Send key as monospace text
    key_message = f"```\n{public_key}\n```"

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="« Back",
        callback_data=UserMenuCallback.create(0)
    )

    await callback.message.edit_text(
        message_text + "\n\n" + key_message,
        parse_mode="Markdown",
        reply_markup=kb_builder.as_markup()
    )
```

### Localization Keys

```json
// de.json
{
  "gpg_public_key_info": "🔐 <b>Öffentlicher GPG-Schlüssel</b>\n\n<b>Fingerprint:</b>\n<code>{fingerprint}</code>\n\n<b>Verwendung:</b>\nDu kannst diesen Schlüssel verwenden, um sensible Daten (z.B. Versanddaten) zu verschlüsseln, bevor du sie uns sendest.\n\n<b>GPG-Tutorial:</b> https://gnupg.org/gph/de/manual/c14.html",

  "menu_gpg_key": "🔐 GPG Public Key"
}

// en.json
{
  "gpg_public_key_info": "🔐 <b>Public GPG Key</b>\n\n<b>Fingerprint:</b>\n<code>{fingerprint}</code>\n\n<b>Usage:</b>\nYou can use this key to encrypt sensitive data (e.g., shipping address) before sending it to us.\n\n<b>GPG Tutorial:</b> https://gnupg.org/gph/en/manual/c14.html",

  "menu_gpg_key": "🔐 GPG Public Key"
}
```

### Implementation Order
1. Add GPG configuration to `.env` and `config.py`
2. Store public key file in project directory
3. Add "GPG Public Key" button to main user menu
4. Implement `show_gpg_public_key()` handler
5. Add localization keys
6. Testing: View key, verify formatting, copy key

### Estimated Effort
Low (30 minutes)

### Dependencies
- Requires GPG public key file
- No database changes needed

---

## Encrypted Shipping Address Submission

### Description
Implement a secure system for users to submit shipping addresses after successful payment. Offers two encryption options: server-side encryption (user-friendly) or client-side encryption via external web tool (maximum security). All shipping data is encrypted with admin's GPG public key and stored encrypted in database.

### User Story
As a privacy-conscious customer, I want to submit my shipping address in an encrypted form, so that only the shop administrator can read it and my personal data remains confidential.

### Acceptance Criteria
- [ ] After payment confirmed (OrderStatus.PAID), bot prompts for shipping address
- [ ] User has two options:
  - **Option A (Recommended):** Enter address in bot → server-side encryption
  - **Option B (Advanced):** Encrypt externally → paste encrypted block
- [ ] **Option A Flow (FSM-based):**
  - Bot asks: Name, Street, City, Postal Code, Country (step-by-step)
  - Bot encrypts complete address with GPG public key (server-side)
  - Encrypted text stored in `orders.shipping_address_encrypted` field
  - Bot confirms: "✅ Shipping address received (encrypted)"
- [ ] **Option B Flow:**
  - Bot sends link to external encryption tool: `https://yourdomain.com/encrypt-shipping`
  - Web tool has embedded GPG public key (client-side encryption with OpenPGP.js)
  - User encrypts in browser, copies encrypted block
  - User pastes encrypted text back to bot
  - Bot stores encrypted text without modification
- [ ] Admin panel shows:
  - "📦 View Encrypted Shipping Address" button
  - Displays ASCII-armored encrypted block
  - "Copy to Decrypt" button
  - Admin decrypts locally with private key
- [ ] Order cannot be marked as SHIPPED until shipping address is submitted
- [ ] User can update shipping address (generates new encrypted version)
- [ ] Localization (DE/EN)

### Technical Notes

#### Database Changes
```python
# models/order.py - ADD FIELD
class Order(Base):
    # ... existing fields ...

    shipping_address_encrypted = Column(Text, nullable=True)  # GPG-encrypted address
    shipping_address_submitted_at = Column(DateTime, nullable=True)
```

#### FSM States (Option A)
```python
# handlers/user/constants.py
class ShippingAddressStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_street = State()
    waiting_for_city = State()
    waiting_for_postal_code = State()
    waiting_for_country = State()
```

#### Server-Side Encryption (Option A)
```python
# services/encryption.py (NEW FILE)
import gnupg

class EncryptionService:

    @staticmethod
    def encrypt_shipping_address(
        name: str,
        street: str,
        city: str,
        postal_code: str,
        country: str
    ) -> str:
        """
        Encrypts shipping address with admin's GPG public key.
        Returns ASCII-armored encrypted block.
        """
        # Initialize GPG
        gpg = gnupg.GPG()

        # Import public key
        with open(config.GPG_PUBLIC_KEY_FILE, 'r') as f:
            import_result = gpg.import_keys(f.read())

        # Format address
        plaintext = f"""
Name: {name}
Street: {street}
City: {city}
Postal Code: {postal_code}
Country: {country}
"""

        # Encrypt
        encrypted = gpg.encrypt(
            plaintext,
            config.GPG_KEY_FINGERPRINT,
            armor=True,
            always_trust=True
        )

        if not encrypted.ok:
            raise ValueError(f"Encryption failed: {encrypted.status}")

        return str(encrypted)
```

#### Handler (Option A - FSM Flow)
```python
# handlers/user/shipping.py (NEW FILE)
from aiogram.fsm.context import FSMContext

@router.callback_query(F.data == "submit_shipping_address")
async def start_shipping_address_flow(callback: CallbackQuery, state: FSMContext):
    """Starts shipping address submission flow."""

    message_text = Localizator.get_text(BotEntity.USER, "shipping_address_choose_method")

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="🔐 Enter in Bot (Recommended)",
        callback_data=ShippingCallback.create(1)  # Option A
    )
    kb_builder.button(
        text="🌐 Encrypt Externally (Advanced)",
        callback_data=ShippingCallback.create(2)  # Option B
    )
    kb_builder.adjust(1)

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())

@router.callback_query(ShippingCallback.filter(F.level == 1))
async def start_option_a(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Option A: FSM-based address input."""

    # Get order ID from callback data
    order_id = callback.data.split(":")[1]
    await state.update_data(order_id=order_id)

    await state.set_state(ShippingAddressStates.waiting_for_name)

    await callback.message.edit_text(
        Localizator.get_text(BotEntity.USER, "shipping_address_enter_name")
    )

@router.message(ShippingAddressStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Processes name input."""
    await state.update_data(name=message.text)
    await state.set_state(ShippingAddressStates.waiting_for_street)

    await message.answer(
        Localizator.get_text(BotEntity.USER, "shipping_address_enter_street")
    )

# ... (similar handlers for street, city, postal_code, country)

@router.message(ShippingAddressStates.waiting_for_country)
async def process_country(message: Message, state: FSMContext, session: AsyncSession):
    """Final step: encrypt and save address."""
    data = await state.get_data()
    data['country'] = message.text

    # Encrypt address
    encrypted_address = EncryptionService.encrypt_shipping_address(
        name=data['name'],
        street=data['street'],
        city=data['city'],
        postal_code=data['postal_code'],
        country=data['country']
    )

    # Save to order
    order_id = data['order_id']
    await OrderRepository.update_shipping_address(
        order_id,
        encrypted_address,
        session
    )

    await state.clear()

    await message.answer(
        Localizator.get_text(BotEntity.USER, "shipping_address_submitted_success")
    )
```

#### Handler (Option B - External Encryption)
```python
@router.callback_query(ShippingCallback.filter(F.level == 2))
async def start_option_b(callback: CallbackQuery, state: FSMContext):
    """Option B: External encryption link."""

    order_id = callback.data.split(":")[1]
    await state.update_data(order_id=order_id)
    await state.set_state(ShippingAddressStates.waiting_for_encrypted_block)

    encryption_url = f"{config.EXTERNAL_ENCRYPTION_URL}?pubkey={config.GPG_KEY_FINGERPRINT}"

    message_text = Localizator.get_text(BotEntity.USER, "shipping_address_external_link").format(
        url=encryption_url
    )

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="🌐 Open Encryption Tool", url=encryption_url)

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())

@router.message(ShippingAddressStates.waiting_for_encrypted_block)
async def process_encrypted_block(message: Message, state: FSMContext, session: AsyncSession):
    """Receives and stores encrypted block from user."""

    encrypted_block = message.text.strip()

    # Basic validation (check if it looks like GPG block)
    if not encrypted_block.startswith("-----BEGIN PGP MESSAGE-----"):
        await message.answer(
            Localizator.get_text(BotEntity.USER, "shipping_address_invalid_format")
        )
        return

    data = await state.get_data()
    order_id = data['order_id']

    # Save to order
    await OrderRepository.update_shipping_address(
        order_id,
        encrypted_block,
        session
    )

    await state.clear()

    await message.answer(
        Localizator.get_text(BotEntity.USER, "shipping_address_submitted_success")
    )
```

#### Admin Panel - View Encrypted Address
```python
# handlers/admin/order_management.py
async def show_encrypted_shipping_address(callback: CallbackQuery, session: AsyncSession):
    """Shows encrypted shipping address for admin to decrypt."""

    unpacked_cb = OrderManagementCallback.unpack(callback.data)
    order = await OrderRepository.get_by_id(unpacked_cb.order_id, session)

    if not order.shipping_address_encrypted:
        await callback.answer("❌ No shipping address submitted yet", show_alert=True)
        return

    message_text = f"""
📦 <b>Encrypted Shipping Address</b>

Order: #{order.invoice.invoice_number}
Submitted: {order.shipping_address_submitted_at.strftime('%Y-%m-%d %H:%M')}

<b>Encrypted Block:</b>
<code>{order.shipping_address_encrypted}</code>

<b>Decrypt with:</b>
<code>echo "ENCRYPTED_BLOCK" | gpg --decrypt</code>
"""

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="« Back", callback_data=OrderManagementCallback.create(0))

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())
```

### Configuration (.env)
```bash
# Shipping Encryption
GPG_PUBLIC_KEY_FILE=/path/to/pubkey.asc
GPG_KEY_FINGERPRINT=ABCD1234EFGH5678...
EXTERNAL_ENCRYPTION_URL=https://yourdomain.com/encrypt-shipping  # For Option B
```

### External Web Tool (Option B)
```html
<!-- static/encrypt-shipping.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Encrypt Shipping Address</title>
    <script src="https://unpkg.com/openpgp@5.10.1/dist/openpgp.min.js"></script>
</head>
<body>
    <h1>Encrypt Your Shipping Address</h1>

    <textarea id="plaintext" placeholder="Enter your shipping address..."></textarea>

    <button onclick="encryptAddress()">🔐 Encrypt</button>

    <textarea id="encrypted" readonly placeholder="Encrypted text will appear here..."></textarea>

    <button onclick="copyToClipboard()">📋 Copy</button>

    <script>
        const publicKeyArmored = `INSERT_PUBLIC_KEY_HERE`;

        async function encryptAddress() {
            const plaintext = document.getElementById('plaintext').value;

            const publicKey = await openpgp.readKey({ armoredKey: publicKeyArmored });

            const encrypted = await openpgp.encrypt({
                message: await openpgp.createMessage({ text: plaintext }),
                encryptionKeys: publicKey
            });

            document.getElementById('encrypted').value = encrypted;
        }

        function copyToClipboard() {
            const encrypted = document.getElementById('encrypted');
            encrypted.select();
            document.execCommand('copy');
            alert('✅ Copied! Now paste it back to the Telegram bot.');
        }
    </script>
</body>
</html>
```

### Localization Keys

```json
// de.json
{
  "shipping_address_choose_method": "📦 <b>Versanddaten eingeben</b>\n\nWähle eine Methode:\n\n🔐 <b>Im Bot eingeben (Empfohlen):</b>\nEinfach und schnell. Daten werden automatisch verschlüsselt.\n\n🌐 <b>Extern verschlüsseln (Fortgeschritten):</b>\nMaximale Sicherheit. Du verschlüsselst selbst im Browser.",

  "shipping_address_enter_name": "📝 <b>Vollständiger Name:</b>\n\nBitte gib deinen vollständigen Namen ein (wie er auf dem Paket stehen soll).",

  "shipping_address_enter_street": "🏠 <b>Straße + Hausnummer:</b>",

  "shipping_address_enter_city": "🏙 <b>Stadt:</b>",

  "shipping_address_enter_postal_code": "📮 <b>Postleitzahl:</b>",

  "shipping_address_enter_country": "🌍 <b>Land:</b>",

  "shipping_address_submitted_success": "✅ <b>Versanddaten empfangen!</b>\n\nDeine Adresse wurde verschlüsselt gespeichert. Nur der Shop-Administrator kann sie entschlüsseln.\n\nDeine Bestellung wird in Kürze versendet.",

  "shipping_address_external_link": "🌐 <b>Externe Verschlüsselung</b>\n\nKlicke auf den Button unten, um das Verschlüsselungs-Tool zu öffnen.\n\n<b>Anleitung:</b>\n1. Gib deine Versanddaten im Tool ein\n2. Klicke 'Encrypt'\n3. Kopiere den verschlüsselten Text\n4. Sende ihn hier zurück an den Bot\n\n{url}",

  "shipping_address_invalid_format": "❌ <b>Ungültiges Format</b>\n\nDer verschlüsselte Text muss mit \"-----BEGIN PGP MESSAGE-----\" beginnen.\n\nBitte verschlüssele deine Adresse erneut und sende den kompletten Block."
}

// en.json
{
  "shipping_address_choose_method": "📦 <b>Submit Shipping Address</b>\n\nChoose a method:\n\n🔐 <b>Enter in Bot (Recommended):</b>\nSimple and fast. Data is automatically encrypted.\n\n🌐 <b>Encrypt Externally (Advanced):</b>\nMaximum security. You encrypt yourself in the browser.",

  "shipping_address_enter_name": "📝 <b>Full Name:</b>\n\nPlease enter your full name (as it should appear on the package).",

  "shipping_address_enter_street": "🏠 <b>Street + Number:</b>",

  "shipping_address_enter_city": "🏙 <b>City:</b>",

  "shipping_address_enter_postal_code": "📮 <b>Postal Code:</b>",

  "shipping_address_enter_country": "🌍 <b>Country:</b>",

  "shipping_address_submitted_success": "✅ <b>Shipping address received!</b>\n\nYour address has been encrypted and stored. Only the shop administrator can decrypt it.\n\nYour order will be shipped soon.",

  "shipping_address_external_link": "🌐 <b>External Encryption</b>\n\nClick the button below to open the encryption tool.\n\n<b>Instructions:</b>\n1. Enter your shipping address in the tool\n2. Click 'Encrypt'\n3. Copy the encrypted text\n4. Send it back here to the bot\n\n{url}",

  "shipping_address_invalid_format": "❌ <b>Invalid Format</b>\n\nThe encrypted text must start with \"-----BEGIN PGP MESSAGE-----\".\n\nPlease encrypt your address again and send the complete block."
}
```

### Implementation Order

1. Add database field `shipping_address_encrypted` to Order model
2. Create database migration
3. Install `python-gnupg` library: `pip install python-gnupg`
4. Create `services/encryption.py` with server-side encryption
5. Create `handlers/user/shipping.py` with FSM flow
6. Create `ShippingAddressStates` FSM states
7. Add "Submit Shipping Address" prompt after payment
8. Implement Option A (FSM flow)
9. Create external web tool (Option B) - deploy to static hosting
10. Implement Option B (external encryption handler)
11. Add admin view for encrypted addresses
12. Add localization keys (DE/EN)
13. Testing:
    - Option A: Enter address → verify encryption → admin can decrypt
    - Option B: External tool → paste back → admin can decrypt
    - Verify encrypted data is stored correctly

### Estimated Effort
High (3-4 hours)

### Dependencies
- Requires GPG public key configured
- Requires `python-gnupg` library
- Option B requires static web hosting for encryption tool
- Must update order creation flow to prompt for shipping

### Security Considerations
- ✅ **Option A:** Data visible briefly on server during encryption (acceptable for most use cases)
- ✅ **Option B:** True end-to-end encryption (data never visible on server)
- ⚠️ **Important:** Private key must NEVER be on server - only admin's local machine
- ✅ Encrypted data in database is useless without private key
- ✅ Use `always_trust=True` in GPG to avoid key validation issues

---

## Order Shipment Management

### Description
Enable administrators to mark paid orders as shipped, triggering user notifications. Simple workflow without tracking numbers - admin confirms shipment, user gets notified.

### User Story
As an administrator, I want to mark orders as shipped after I've sent the package, so that customers are automatically notified and the order status is updated in the system.

### Acceptance Criteria
- [ ] Admin panel shows list of PAID orders ready for shipment
- [ ] Filter: "Orders awaiting shipment" (PAID status + shipping address submitted)
- [ ] Admin can click "Mark as Shipped" button for each order
- [ ] Confirmation dialog: "Mark order #YYYY-XXXXXX as shipped?"
- [ ] Order status changes to `SHIPPED`
- [ ] `shipped_at` timestamp is recorded
- [ ] User receives notification: "Your order has been shipped!"
- [ ] No tracking number field (shipment confirmation only)
- [ ] Order cannot be marked as shipped if:
  - Status is not PAID
  - Shipping address is not submitted
- [ ] Admin can view shipment history (orders marked as SHIPPED)
- [ ] Localization (DE/EN)

### Technical Notes

#### Database Changes
```python
# models/order.py - ADD FIELD
class Order(Base):
    # ... existing fields ...

    shipped_at = Column(DateTime, nullable=True)
    shipped_by_admin_id = Column(Integer, nullable=True)  # Telegram ID of admin who marked it
```

#### Admin Handler
```python
# handlers/admin/order_management.py
async def show_orders_awaiting_shipment(callback: CallbackQuery, session: AsyncSession):
    """Shows orders ready to be shipped (PAID + address submitted)."""

    orders = await OrderRepository.get_orders_awaiting_shipment(session)

    if not orders:
        await callback.answer("✅ No orders awaiting shipment", show_alert=True)
        return

    kb_builder = InlineKeyboardBuilder()

    for order in orders:
        order_text = f"#{order.invoice.invoice_number} - {order.user.telegram_username} - €{order.total_price:.2f}"
        kb_builder.button(
            text=order_text,
            callback_data=ShipmentCallback.create(1, order_id=order.id)
        )

    kb_builder.adjust(1)
    kb_builder.row(AdminConstants.back_to_main_button)

    await callback.message.edit_text(
        "📦 Orders Awaiting Shipment:",
        reply_markup=kb_builder.as_markup()
    )

async def confirm_mark_as_shipped(callback: CallbackQuery, session: AsyncSession):
    """Shows confirmation dialog for marking as shipped."""

    unpacked_cb = ShipmentCallback.unpack(callback.data)
    order = await OrderRepository.get_by_id(unpacked_cb.order_id, session)

    details = f"""
📦 <b>Mark as Shipped?</b>

Order: #{order.invoice.invoice_number}
User: @{order.user.telegram_username}
Total: €{order.total_price:.2f}
Payment: {order.created_at.strftime('%Y-%m-%d %H:%M')}

⚠️ User will be notified immediately.
"""

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="✅ Confirm Shipment",
        callback_data=ShipmentCallback.create(2, order_id=order.id, confirmed=True)
    )
    kb_builder.button(
        text="❌ Cancel",
        callback_data=ShipmentCallback.create(0)
    )

    await callback.message.edit_text(details, reply_markup=kb_builder.as_markup())

async def mark_order_as_shipped(callback: CallbackQuery, session: AsyncSession):
    """Marks order as shipped and notifies user."""

    unpacked_cb = ShipmentCallback.unpack(callback.data)
    order_id = unpacked_cb.order_id
    admin_id = callback.from_user.id

    # Update order
    await OrderRepository.mark_as_shipped(order_id, admin_id, session)

    # Get order and user
    order = await OrderRepository.get_by_id(order_id, session)
    user = await UserRepository.get_by_id(order.user_id, session)

    # Notify user
    await NotificationService.send_order_shipped_notification(user, order, session)

    await callback.answer("✅ Order marked as shipped", show_alert=True)

    # Return to orders list
    await show_orders_awaiting_shipment(callback, session)
```

#### Repository Method
```python
# repositories/order.py
@staticmethod
async def get_orders_awaiting_shipment(session: AsyncSession) -> list[OrderDTO]:
    """Gets PAID orders with shipping address submitted, not yet shipped."""

    stmt = select(Order).where(
        Order.status == OrderStatus.PAID,
        Order.shipping_address_encrypted.isnot(None),
        Order.shipped_at.is_(None)
    ).order_by(Order.created_at.desc())

    result = await session_execute(stmt, session)
    orders = result.scalars().all()

    return [OrderDTO.model_validate(o, from_attributes=True) for o in orders]

@staticmethod
async def mark_as_shipped(order_id: int, admin_id: int, session: AsyncSession):
    """Marks order as shipped."""

    stmt = update(Order).where(Order.id == order_id).values(
        status=OrderStatus.SHIPPED,
        shipped_at=datetime.now(),
        shipped_by_admin_id=admin_id
    )

    await session_execute(stmt, session)
    await session_commit(session)
```

### Localization Keys

```json
// de.json
{
  "order_shipped_notification": "📦 <b>Bestellung versendet!</b>\n\nDeine Bestellung <b>#{invoice_number}</b> wurde versendet.\n\n<b>Bestelldetails:</b>\n• Artikel: {item_count}x\n• Gesamt: €{total_price:.2f}\n\n<b>Versanddatum:</b> {shipped_at}\n\nDas Paket sollte in den nächsten Tagen bei dir ankommen.\n\nViel Freude mit deinen Artikeln! 🎉",

  "admin_mark_as_shipped": "✅ Als versendet markieren"
}

// en.json
{
  "order_shipped_notification": "📦 <b>Order Shipped!</b>\n\nYour order <b>#{invoice_number}</b> has been shipped.\n\n<b>Order Details:</b>\n• Items: {item_count}x\n• Total: €{total_price:.2f}\n\n<b>Ship Date:</b> {shipped_at}\n\nYour package should arrive in the next few days.\n\nEnjoy your items! 🎉",

  "admin_mark_as_shipped": "✅ Mark as Shipped"
}
```

### Implementation Order

1. Add `shipped_at` and `shipped_by_admin_id` to Order model
2. Create database migration
3. Create `OrderRepository.get_orders_awaiting_shipment()`
4. Create `OrderRepository.mark_as_shipped()`
5. Create admin handlers in `handlers/admin/order_management.py`
6. Add "Orders Awaiting Shipment" button to admin menu
7. Implement `NotificationService.send_order_shipped_notification()`
8. Add localization keys (DE/EN)
9. Testing:
    - Pay for order → submit shipping → admin marks as shipped
    - User receives notification
    - Order status = SHIPPED
    - Cannot mark as shipped without address

### Estimated Effort
Medium (1.5 hours)

### Dependencies
- Requires Order model with `shipped_at` field
- Requires shipping address submission to be implemented first
- User notification system must be functional

---

## Admin Order Refund with Crypto Return

### Description
Enable administrators to cancel paid orders and process manual refunds by requesting the user's cryptocurrency return address. Admin initiates cancellation, user provides crypto address, admin manually sends refund via KryptoExpress or wallet, and logs the transaction in the system.

### User Story
As an administrator, I want to cancel a paid order and refund the customer, so that I can handle customer service issues (out of stock, shipping problems, etc.) professionally and provide refunds in a traceable manner.

### Acceptance Criteria
- [ ] Admin panel shows all orders with status PAID or SHIPPED
- [ ] Admin can click "Cancel & Refund" button on any order
- [ ] Admin enters cancellation reason (required, shown to user)
- [ ] Order status changes to `CANCELLED_BY_ADMIN`
- [ ] Bot automatically sends message to user:
  - Notification that order was cancelled with reason
  - Request for cryptocurrency return address (same crypto as original payment)
  - Instructions: "Please send your [BTC/ETH/etc.] address for refund"
- [ ] User sends crypto address as text message (FSM state: `waiting_for_refund_address`)
- [ ] Bot validates address format (basic regex check)
- [ ] Bot stores address in `orders.refund_crypto_address` field
- [ ] Bot notifies admin: "User provided refund address: [ADDRESS]"
- [ ] Admin panel shows:
  - Order details
  - Original payment: amount, crypto, address
  - User's refund address
  - "Mark Refund as Sent" button
- [ ] Admin manually sends refund via KryptoExpress dashboard or wallet
- [ ] Admin clicks "Mark Refund as Sent" and enters:
  - Transaction ID/hash
  - Amount sent
  - Optional notes
- [ ] Bot records refund in `refunds` table
- [ ] Bot notifies user: "Refund sent! TX: [HASH]"
- [ ] Order marked as `refund_completed = True`
- [ ] Admin can view refund history for auditing
- [ ] Localization (DE/EN)

### Technical Notes

#### Database Changes
```python
# models/order.py - ADD FIELDS
class Order(Base):
    # ... existing fields ...

    refund_crypto_address = Column(String, nullable=True)  # User's return address
    refund_requested_at = Column(DateTime, nullable=True)
    refund_completed = Column(Boolean, default=False)

# models/refund.py (NEW FILE)
class Refund(Base):
    __tablename__ = 'refunds'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    admin_user_id = Column(Integer, nullable=False)  # Who processed refund

    # Refund details
    crypto_currency = Column(SQLEnum(Cryptocurrency), nullable=False)
    refund_amount_crypto = Column(Float, nullable=False)
    refund_amount_fiat = Column(Float, nullable=False)
    refund_address = Column(String, nullable=False)  # User's address

    # Transaction proof
    transaction_hash = Column(String, nullable=True)
    transaction_sent_at = Column(DateTime, nullable=True)

    # Admin notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationship
    order = relationship('Order', back_populates='refund')
```

#### FSM State
```python
# handlers/user/constants.py
class RefundStates(StatesGroup):
    waiting_for_crypto_address = State()
```

#### Admin Handler - Initiate Refund
```python
# handlers/admin/order_management.py
async def initiate_order_refund(callback: CallbackQuery, state: FSMContext):
    """Admin initiates refund - prompts for cancellation reason."""

    unpacked_cb = OrderManagementCallback.unpack(callback.data)

    await state.update_data(order_id=unpacked_cb.order_id)
    await state.set_state(OrderManagementStates.refund_reason)

    await callback.message.edit_text(
        "💸 <b>Order Refund</b>\n\nPlease enter the cancellation reason (will be shown to user):"
    )

@router.message(StateFilter(OrderManagementStates.refund_reason), AdminIdFilter())
async def process_refund_reason(message: Message, state: FSMContext, session: AsyncSession):
    """Processes refund reason and notifies user."""

    data = await state.get_data()
    order_id = data['order_id']
    reason = message.text
    admin_id = message.from_user.id

    # Get order
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)

    # Cancel order
    await OrderRepository.update_status(order_id, OrderStatus.CANCELLED_BY_ADMIN, session)
    await OrderRepository.update_refund_requested(order_id, session)

    # Log admin action
    await AdminActionLogRepository.create(
        admin_user_id=admin_id,
        action_type="INITIATE_REFUND",
        target_order_id=order_id,
        reason=reason,
        session=session
    )

    # Notify user and request refund address
    user = await UserRepository.get_by_id(order.user_id, session)

    user_message = Localizator.get_text(BotEntity.USER, "order_refund_request_address").format(
        invoice_number=invoice.invoice_number,
        reason=reason,
        crypto_currency=invoice.payment_crypto_currency.value,
        refund_amount_crypto=invoice.payment_amount_crypto,
        refund_amount_fiat=order.total_price
    )

    # Set user FSM state to wait for address
    user_state = FSMContext(
        storage=dp.storage,
        key=StorageKey(bot_id=dp.bot.id, user_id=user.telegram_id, chat_id=user.telegram_id)
    )
    await user_state.set_state(RefundStates.waiting_for_crypto_address)
    await user_state.update_data(order_id=order_id)

    # Send message to user
    await dp.bot.send_message(user.telegram_id, user_message)

    await state.clear()
    await message.answer(
        f"✅ Refund initiated for order #{invoice.invoice_number}\n\n"
        f"User has been notified and asked for their {invoice.payment_crypto_currency.value} address."
    )
```

#### User Handler - Receive Refund Address
```python
# handlers/user/refund.py (NEW FILE)
@router.message(StateFilter(RefundStates.waiting_for_crypto_address))
async def receive_refund_address(message: Message, state: FSMContext, session: AsyncSession):
    """User sends their crypto address for refund."""

    crypto_address = message.text.strip()
    data = await state.get_data()
    order_id = data['order_id']

    # Get order to determine crypto type
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)
    crypto_currency = invoice.payment_crypto_currency

    # Validate address format (basic check)
    if not validate_crypto_address(crypto_address, crypto_currency):
        await message.answer(
            Localizator.get_text(BotEntity.USER, "refund_address_invalid").format(
                crypto_currency=crypto_currency.value
            )
        )
        return

    # Save address
    await OrderRepository.update_refund_address(order_id, crypto_address, session)

    # Notify user
    await message.answer(
        Localizator.get_text(BotEntity.USER, "refund_address_received").format(
            crypto_address=crypto_address
        )
    )

    # Notify admin
    for admin_id in config.ADMIN_IDS:
        await dp.bot.send_message(
            admin_id,
            f"💸 <b>Refund Address Received</b>\n\n"
            f"Order: #{invoice.invoice_number}\n"
            f"User: @{order.user.telegram_username}\n"
            f"Crypto: {crypto_currency.value}\n"
            f"Address: <code>{crypto_address}</code>\n\n"
            f"Please process refund manually and mark as sent in admin panel."
        )

    await state.clear()

def validate_crypto_address(address: str, crypto: Cryptocurrency) -> bool:
    """Basic regex validation for crypto addresses."""

    address_patterns = {
        Cryptocurrency.BTC: r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,59}$',
        Cryptocurrency.ETH: r'^0x[a-fA-F0-9]{40}$',
        Cryptocurrency.LTC: r'^(ltc1|[LM])[a-zA-HJ-NP-Z0-9]{26,59}$',
        Cryptocurrency.SOL: r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
        Cryptocurrency.BNB: r'^0x[a-fA-F0-9]{40}$',
        # Add more as needed
    }

    pattern = address_patterns.get(crypto)
    if not pattern:
        return True  # Skip validation if unknown

    import re
    return bool(re.match(pattern, address))
```

#### Admin Handler - Mark Refund as Sent
```python
# handlers/admin/order_management.py
async def show_refund_details(callback: CallbackQuery, session: AsyncSession):
    """Shows refund details and 'Mark as Sent' button."""

    unpacked_cb = OrderManagementCallback.unpack(callback.data)
    order = await OrderRepository.get_by_id(unpacked_cb.order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(unpacked_cb.order_id, session)

    if not order.refund_crypto_address:
        await callback.answer("⚠️ User has not provided refund address yet", show_alert=True)
        return

    details = f"""
💸 <b>Refund Details</b>

<b>Order:</b> #{invoice.invoice_number}
<b>User:</b> @{order.user.telegram_username}

<b>Original Payment:</b>
• Amount: {invoice.payment_amount_crypto} {invoice.payment_crypto_currency.value}
• Fiat: €{order.total_price:.2f}
• Paid to: <code>{invoice.payment_address}</code>

<b>Refund To:</b>
<code>{order.refund_crypto_address}</code>

⚠️ Please send refund manually via KryptoExpress or your wallet.
"""

    kb_builder = InlineKeyboardBuilder()

    if not order.refund_completed:
        kb_builder.button(
            text="✅ Mark Refund as Sent",
            callback_data=RefundCallback.create(1, order_id=order.id)
        )
    else:
        kb_builder.button(text="✅ Refund Already Sent", callback_data="noop")

    kb_builder.button(text="« Back", callback_data=OrderManagementCallback.create(0))
    kb_builder.adjust(1)

    await callback.message.edit_text(details, reply_markup=kb_builder.as_markup())

async def request_refund_transaction_hash(callback: CallbackQuery, state: FSMContext):
    """Prompts admin for transaction hash."""

    unpacked_cb = RefundCallback.unpack(callback.data)

    await state.update_data(order_id=unpacked_cb.order_id)
    await state.set_state(OrderManagementStates.refund_tx_hash)

    await callback.message.edit_text(
        "💸 <b>Transaction Hash</b>\n\n"
        "Please enter the refund transaction hash/ID:"
    )

@router.message(StateFilter(OrderManagementStates.refund_tx_hash), AdminIdFilter())
async def process_refund_tx_hash(message: Message, state: FSMContext, session: AsyncSession):
    """Records refund transaction."""

    data = await state.get_data()
    order_id = data['order_id']
    tx_hash = message.text.strip()
    admin_id = message.from_user.id

    # Get order details
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)

    # Create refund record
    refund_dto = RefundDTO(
        order_id=order_id,
        admin_user_id=admin_id,
        crypto_currency=invoice.payment_crypto_currency,
        refund_amount_crypto=invoice.payment_amount_crypto,
        refund_amount_fiat=order.total_price,
        refund_address=order.refund_crypto_address,
        transaction_hash=tx_hash,
        transaction_sent_at=datetime.now()
    )

    await RefundRepository.create(refund_dto, session)

    # Mark order refund as completed
    await OrderRepository.mark_refund_completed(order_id, session)

    # Notify user
    user = await UserRepository.get_by_id(order.user_id, session)
    await NotificationService.send_refund_completed_notification(
        user,
        order,
        invoice,
        tx_hash,
        session
    )

    await state.clear()
    await message.answer(
        f"✅ Refund recorded for order #{invoice.invoice_number}\n\n"
        f"Transaction: <code>{tx_hash}</code>\n\n"
        f"User has been notified."
    )
```

### Localization Keys

```json
// de.json
{
  "order_refund_request_address": "💸 <b>Bestellung storniert - Rückerstattung</b>\n\nDeine Bestellung <b>#{invoice_number}</b> wurde vom Administrator storniert.\n\n<b>Grund:</b> {reason}\n\n<b>Rückerstattung:</b>\n• Betrag: {refund_amount_crypto} {crypto_currency}\n• Fiat-Wert: €{refund_amount_fiat:.2f}\n\n📤 <b>Bitte sende deine {crypto_currency}-Adresse</b> für die Rückerstattung.\n\nHinweis: Stelle sicher, dass die Adresse korrekt ist. Falsche Adressen können zu Verlusten führen!",

  "refund_address_invalid": "❌ <b>Ungültige Adresse</b>\n\nDie eingegebene {crypto_currency}-Adresse scheint ungültig zu sein.\n\nBitte überprüfe die Adresse und sende sie erneut.",

  "refund_address_received": "✅ <b>Adresse empfangen</b>\n\nDeine Rückerstattungsadresse wurde gespeichert:\n<code>{crypto_address}</code>\n\nDie Rückerstattung wird in Kürze bearbeitet. Du erhältst eine Benachrichtigung, sobald die Transaktion gesendet wurde.",

  "refund_completed_notification": "✅ <b>Rückerstattung gesendet!</b>\n\nDeine Rückerstattung für Bestellung <b>#{invoice_number}</b> wurde versendet.\n\n<b>Transaktions-Details:</b>\n• Betrag: {refund_amount_crypto} {crypto_currency}\n• An: <code>{refund_address}</code>\n• TX-Hash: <code>{transaction_hash}</code>\n\nDie Transaktion sollte in Kürze in deiner Wallet sichtbar sein."
}

// en.json
{
  "order_refund_request_address": "💸 <b>Order Cancelled - Refund</b>\n\nYour order <b>#{invoice_number}</b> has been cancelled by an administrator.\n\n<b>Reason:</b> {reason}\n\n<b>Refund:</b>\n• Amount: {refund_amount_crypto} {crypto_currency}\n• Fiat Value: €{refund_amount_fiat:.2f}\n\n📤 <b>Please send your {crypto_currency} address</b> for the refund.\n\nNote: Make sure the address is correct. Wrong addresses can lead to losses!",

  "refund_address_invalid": "❌ <b>Invalid Address</b>\n\nThe entered {crypto_currency} address appears to be invalid.\n\nPlease check the address and send it again.",

  "refund_address_received": "✅ <b>Address Received</b>\n\nYour refund address has been saved:\n<code>{crypto_address}</code>\n\nThe refund will be processed shortly. You will receive a notification once the transaction is sent.",

  "refund_completed_notification": "✅ <b>Refund Sent!</b>\n\nYour refund for order <b>#{invoice_number}</b> has been sent.\n\n<b>Transaction Details:</b>\n• Amount: {refund_amount_crypto} {crypto_currency}\n• To: <code>{refund_address}</code>\n• TX Hash: <code>{transaction_hash}</code>\n\nThe transaction should be visible in your wallet shortly."
}
```

### Implementation Order

1. Create `models/refund.py` with Refund table
2. Add refund fields to Order model (`refund_crypto_address`, etc.)
3. Create database migration
4. Create `repositories/refund.py`
5. Create `RefundStates` FSM states
6. Implement admin "Cancel & Refund" handler
7. Implement user refund address submission handler
8. Add `validate_crypto_address()` helper function
9. Implement admin "Mark Refund as Sent" flow
10. Create `NotificationService.send_refund_completed_notification()`
11. Add admin view for refund history
12. Add localization keys (DE/EN)
13. Testing:
    - Admin cancels paid order → user receives notification
    - User sends address → admin receives notification
    - Admin marks as sent → user receives TX confirmation
    - Refund logged in database

### Estimated Effort
High (3-4 hours)

### Dependencies
- Requires Order and Refund models
- Requires FSM for address collection
- User notification system must be functional
- Admin authentication must be in place

### Security Considerations
- ⚠️ **Manual refund process** - No automatic sending (reduces risk)
- ✅ **Address validation** - Basic regex check prevents obvious errors
- ✅ **Audit trail** - All refunds logged with admin ID and TX hash
- ⚠️ **No reversibility** - Crypto transactions are final (admin must double-check)
- ✅ **User confirmation** - User provides address explicitly

---

## Power-Referrer Code Rotation

### Description
Implement automatic referral code rotation for power-referrers who reach their maximum referral limit. When a referral code reaches its usage limit (configured via `.env`), the system automatically generates a new code for the user and notifies them. This enables unlimited viral growth while maintaining tracking and monitoring capabilities.

### User Story
As a power-referrer who has successfully referred many customers, I want to automatically receive a new referral code when my current code reaches its limit, so that I can continue referring new customers without interruption.

### Acceptance Criteria
- [ ] Maximum referrals per code is configurable via `.env` file: `REFERRAL_CODE_MAX_USES`
- [ ] When a referral code reaches `REFERRAL_CODE_MAX_USES` successful referrals:
  - Old code is marked as `expired = True` and `expired_at = datetime.now()`
  - New referral code is generated (same format: `U_XXXXX`)
  - User receives notification with new code
- [ ] Old code stops accepting new referrals (validation check in checkout)
- [ ] User's referral history is preserved across code rotations
- [ ] Notification message includes:
  - Congratulations on reaching the limit
  - Statistics (e.g., "You've successfully referred 50 customers!")
  - New referral code
  - Encouragement to continue sharing
- [ ] Database tracks code rotation history:
  - Which codes belong to same user
  - When each code was created/expired
  - How many successful referrals per code
- [ ] Admin dashboard shows power-referrer statistics:
  - Users with multiple codes
  - Total referrals across all codes
  - Code rotation history
- [ ] Error handling: If code generation fails, retry up to 5 times before alerting admin

### Technical Notes

#### Configuration (.env)
```bash
# Referral System
REFERRAL_CODE_MAX_USES=20  # Max successful referrals per code before rotation
```

#### Database Changes
```python
# models/user.py - ADD FIELDS
class User(Base):
    # ... existing fields ...

    # Referral Code Rotation
    referral_codes_generated_count = Column(Integer, default=0)  # How many codes this user had
    current_referral_code_uses = Column(Integer, default=0)  # Uses of current code
    total_successful_referrals = Column(Integer, default=0)  # Across ALL codes

# NEW TABLE: models/referral_code_history.py
class ReferralCodeHistory(Base):
    __tablename__ = 'referral_code_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(String(8), nullable=False)  # U_XXXXX
    created_at = Column(DateTime, default=func.now())
    expired_at = Column(DateTime, nullable=True)
    successful_referrals_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Relationship
    user = relationship('User', back_populates='referral_code_history')
```

#### Code Rotation Logic
```python
# services/referral.py
async def check_and_rotate_code_if_needed(
    user_id: int,
    session: AsyncSession
) -> tuple[bool, str | None]:
    """
    Checks if user's referral code needs rotation.
    Returns (rotated: bool, new_code: str | None)
    """
    user = await UserRepository.get_by_id(user_id, session)
    max_uses = config.REFERRAL_CODE_MAX_USES

    if user.current_referral_code_uses >= max_uses:
        # Expire old code
        old_code = user.referral_code
        await ReferralCodeHistoryRepository.expire_code(
            user_id,
            old_code,
            user.current_referral_code_uses,
            session
        )

        # Generate new code
        new_code = await generate_unique_referral_code(session)

        # Update user
        user.referral_code = new_code
        user.current_referral_code_uses = 0
        user.referral_codes_generated_count += 1
        await UserRepository.update(user, session)

        # Create history record
        await ReferralCodeHistoryRepository.create(
            user_id=user_id,
            code=new_code,
            is_active=True,
            session=session
        )

        # Send notification
        await NotificationService.send_code_rotation_notification(
            user,
            old_code,
            new_code,
            user.total_successful_referrals,
            session
        )

        return True, new_code

    return False, None

# Called after each successful referral usage
async def increment_referral_usage(user_id: int, session: AsyncSession):
    """Increments referral usage counters and checks for rotation."""
    user = await UserRepository.get_by_id(user_id, session)
    user.current_referral_code_uses += 1
    user.total_successful_referrals += 1
    await UserRepository.update(user, session)

    # Check if rotation needed
    rotated, new_code = await check_and_rotate_code_if_needed(user_id, session)

    if rotated:
        logging.info(f"Rotated referral code for user {user_id}: {new_code}")
```

#### Validation in Checkout
```python
async def validate_referral_code(code: str, session: AsyncSession) -> tuple[bool, str | None]:
    """
    Validates referral code and returns (is_valid, error_message).
    """
    # Find user by code
    referrer = await UserRepository.get_by_referral_code(code, session)

    if not referrer:
        return False, "referral_code_invalid"

    # Check if code is expired (reached max uses)
    if referrer.current_referral_code_uses >= config.REFERRAL_CODE_MAX_USES:
        return False, "referral_code_expired"

    # Check if code is still active in history
    code_history = await ReferralCodeHistoryRepository.get_by_code(code, session)
    if code_history and not code_history.is_active:
        return False, "referral_code_expired"

    return True, None
```

### Localization Keys

```json
// de.json
{
  "referral_code_rotation_notification": "🎉 <b>Unglaublich!</b>\n\nDein Referral-Code <code>{old_code}</code> hat das Limit von {max_uses} erfolgreichen Empfehlungen erreicht!\n\n📊 <b>Deine Statistiken:</b>\n• Gesamt empfohlene Kunden: <b>{total_referrals}</b>\n• Generierte Codes: <b>{codes_count}</b>\n\n🎁 <b>Dein neuer Referral-Code:</b> <code>{new_code}</code>\n\n🚀 Mach weiter so! Teile deinen neuen Code mit Freunden und verdiene weiterhin Belohnungen!",

  "referral_code_expired": "❌ Dieser Referral-Code ist abgelaufen. Der Code-Besitzer hat möglicherweise einen neuen Code erhalten."
}

// en.json
{
  "referral_code_rotation_notification": "🎉 <b>Incredible!</b>\n\nYour referral code <code>{old_code}</code> has reached the limit of {max_uses} successful referrals!\n\n📊 <b>Your Statistics:</b>\n• Total referred customers: <b>{total_referrals}</b>\n• Generated codes: <b>{codes_count}</b>\n\n🎁 <b>Your new referral code:</b> <code>{new_code}</code>\n\n🚀 Keep it up! Share your new code with friends and continue earning rewards!",

  "referral_code_expired": "❌ This referral code has expired. The code owner may have received a new code."
}
```

### Admin Dashboard Enhancements

```python
# Admin view for power-referrer statistics
async def get_power_referrer_stats(session: AsyncSession):
    """Returns statistics for users with multiple referral codes."""
    power_referrers = await UserRepository.get_users_with_multiple_codes(session)

    stats = []
    for user in power_referrers:
        code_history = await ReferralCodeHistoryRepository.get_all_by_user(user.id, session)
        stats.append({
            'user_id': user.id,
            'telegram_username': user.telegram_username,
            'current_code': user.referral_code,
            'total_referrals': user.total_successful_referrals,
            'codes_generated': user.referral_codes_generated_count,
            'code_history': [
                {
                    'code': ch.code,
                    'created_at': ch.created_at,
                    'expired_at': ch.expired_at,
                    'referrals': ch.successful_referrals_count
                }
                for ch in code_history
            ]
        })

    return stats
```

### Implementation Order

1. Add `REFERRAL_CODE_MAX_USES` to `.env` and `config.py`
2. Create `models/referral_code_history.py` with database schema
3. Update `models/user.py` with rotation tracking fields
4. Create database migration
5. Create `repositories/referral_code_history.py`
6. Implement `check_and_rotate_code_if_needed()` in `services/referral.py`
7. Update `increment_referral_usage()` to check for rotation
8. Update `validate_referral_code()` to check expiry status
9. Create `NotificationService.send_code_rotation_notification()`
10. Add localization keys (DE/EN)
11. Implement admin dashboard statistics view
12. Testing:
    - User reaches 50 referrals → code rotates automatically
    - Old code stops working
    - New code works immediately
    - History is preserved
    - Notification is sent
    - Admin can view power-referrer statistics

### Estimated Effort
Medium-High (2-3 hours)

### Dependencies
- Requires base Referral System to be implemented first
- Requires `REFERRAL_CODE_MAX_USES` configuration
- Must update referral validation logic
- Notification system must be functional

### Benefits
- Enables unlimited viral growth
- Maintains tracking and audit trail
- Rewards power-referrers with automatic new codes
- Prevents code sharing abuse (expired codes stop working)
- Provides valuable analytics for admin