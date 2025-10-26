# Option B Refactoring Plan - Order BEFORE Crypto Selection

**Status:** All 3 steps completed ✅✅✅

**Goal:** Create order and reserve stock BEFORE user selects cryptocurrency, so user sees stock adjustments early.

---

## ✅ Step 1: Level 3 - Create Order Before Crypto Selection (DONE)

**Commit:** 67c563b

**Changes:**
- `get_crypto_selection_for_checkout()` now creates order with `PENDING_SELECTION`
- Stock check happens immediately at checkout
- Handles 4 cases:
  1. All sold out → Error
  2. Stock adjustments → Adjustment screen + save order_id to FSM
  3. Wallet sufficient → Complete order
  4. Wallet insufficient → Crypto selection + save order_id to FSM

**Result:** User sees stock issues BEFORE selecting crypto ✅

---

## ✅ Step 2: Level 4 - Only Create Invoice (Order Exists) (DONE)

**Commit:** d8ae0a0

**File:** `services/cart.py` → `create_order_with_selected_crypto()`

**Old Behavior (WRONG):**
```python
# Level 4 currently creates NEW order + invoice
order, stock_adjustments = await OrderService.create_order_from_cart(
    user_id=user.id,
    cart_items=cart_items,
    crypto_currency=crypto_currency,  # User just selected this
    session=session
)
```

**New Behavior (CORRECT):**
```python
# Level 4 should:
# 1. Load existing order from FSM (created in Level 3)
# 2. Update order crypto_currency (from PENDING_SELECTION to BTC/ETH/etc)
# 3. Create invoice with selected crypto
# 4. Show payment screen
```

### Implementation Plan:

#### 2.1. Load Order from FSM
```python
# Get order_id from FSM state (saved in Level 3)
if not state:
    raise ValueError("FSM state required")

data = await state.get_data()
order_id = data.get("order_id")

if not order_id:
    raise ValueError("Order ID not found in FSM")

order = await OrderRepository.get_by_id(order_id, session)
```

#### 2.2. Update Order Crypto Currency
```python
# Update order with selected crypto
from sqlalchemy import update
from models.order import Order

stmt = (
    update(Order)
    .where(Order.id == order_id)
    .values(crypto_currency_selected=crypto_currency)  # New field? Or just create invoice?
)
await session_execute(stmt, session)
```

**OR** (simpler): Just create invoice, no need to update order

#### 2.3. Calculate Remaining Amount
```python
# Order already created with wallet deduction
# Just create invoice for remaining amount
remaining_amount = order.total_price - order.wallet_used

if remaining_amount <= 0:
    # Should not happen (wallet-only handled in Level 3)
    raise ValueError("No invoice needed - order already paid")
```

#### 2.4. Create Invoice
```python
await InvoiceService.create_invoice_with_kryptoexpress(
    order_id=order.id,
    fiat_amount=remaining_amount,
    fiat_currency=config.CURRENCY,
    crypto_currency=crypto_currency,
    session=session
)
```

#### 2.5. Save Shipping Address (if exists)
```python
# Extract shipping address from FSM state if present
shipping_address = data.get("shipping_address")
if shipping_address:
    await ShippingService.save_shipping_address(order.id, shipping_address, session)
```

#### 2.6. Clear Cart
```python
# Clear cart (order items already reserved)
cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
for cart_item in cart_items:
    await CartItemRepository.remove_from_cart(cart_item.id, session)
```

#### 2.7. Show Payment Screen
```python
# Get invoice
invoice = await InvoiceRepository.get_by_order_id(order.id, session)

# Build payment message (same as current)
message_text = (
    f"✅ <b>Order created successfully!</b>\n\n"
    f"📋 <b>Order ID:</b> <code>{invoice.invoice_number}</code>\n"
    f"💰 <b>Total price:</b> {order.total_price:.2f} EUR\n"
    # ... payment details
)
```

### Key Differences from Current Code:

| Aspect | Current (Step 1) | New (Step 2) |
|--------|------------------|--------------|
| Order creation | ❌ Creates new order | ✅ Loads existing order from FSM |
| Stock check | ❌ Happens here | ✅ Already done in Level 3 |
| Adjustment screen | ❌ Can show here | ✅ Never shows (handled in Level 3) |
| Cart items | ❌ Loads from DB | ✅ Already reserved (skip or just for notification) |
| Wallet deduction | ❌ Happens here | ✅ Already done in Level 3 |

### Error Handling:

```python
# Order not found in FSM
if not order_id:
    return "❌ Session expired. Please checkout again.", kb_builder

# Order already has invoice (double-click prevention)
existing_invoice = await InvoiceRepository.get_by_order_id(order_id, session)
if existing_invoice:
    # Show existing invoice instead
    return await CartService._show_existing_invoice(order, existing_invoice)

# Order wrong status (shouldn't happen)
if order.status not in [OrderStatus.PENDING_PAYMENT, OrderStatus.PAID]:
    return "❌ Order cannot be modified (Status: {order.status})", kb_builder
```

---

## ✅ Step 3: Level 9 - Crypto Selection After Adjustment (DONE)

**Commit:** 0f99b73

**File:** `services/cart.py` → `confirm_adjusted_order()`

**Old Behavior:**
- After "Continue Payment" on adjustment screen
- Shows invoice OR wallet success

**New Behavior:**
- After "Continue Payment" on adjustment screen
- If wallet sufficient → Complete order
- **If wallet insufficient → Show crypto selection! (NEW)**

### Implementation:

```python
async def confirm_adjusted_order(...):
    # Get order from FSM
    data = await state.get_data()
    order_id = data.get("order_id")
    order = await OrderRepository.get_by_id(order_id, session)

    # Case 1: Wallet sufficient
    if order.status == OrderStatus.PAID:
        # Complete order (same as current)
        await OrderService.complete_order_payment(order.id, session)
        # Clear cart
        # Show success
        return message, kb_builder

    # Case 2: Wallet insufficient - NEW!
    # Don't show invoice yet - show crypto selection first!
    return CartService._show_crypto_selection_screen()
```

**Key Point:** Order already exists with PENDING_SELECTION, just need to show crypto buttons!

---

## Testing Checklist

After all 3 steps:

### Test 1: Normal Flow (No Adjustments, Crypto Payment)
- [ ] Add items to cart
- [ ] Click checkout
- [ ] **NEW:** Order created immediately
- [ ] No stock adjustments
- [ ] Crypto selection shown
- [ ] Select BTC
- [ ] **NEW:** Invoice created (no new order)
- [ ] Payment screen shown

### Test 2: Stock Adjustment Flow
- [ ] Add 5 items to cart
- [ ] Run race condition script (steal 3)
- [ ] Click checkout
- [ ] **NEW:** Order created + Adjustment screen shown IMMEDIATELY
- [ ] User sees: "Requested: 5 | Available: 2"
- [ ] Click "Continue Payment"
- [ ] **NEW:** Crypto selection shown (not invoice!)
- [ ] Select ETH
- [ ] **NEW:** Invoice created for adjusted amount
- [ ] Payment screen shown

### Test 3: Wallet-Only Flow
- [ ] Sufficient wallet balance
- [ ] Add items to cart
- [ ] Click checkout
- [ ] **NEW:** Order created + completed immediately
- [ ] No crypto selection shown
- [ ] Items delivered

### Test 4: Cancel from Adjustment Screen
- [ ] Trigger adjustment screen
- [ ] Click "Cancel"
- [ ] Order cancelled
- [ ] Cart cleared
- [ ] Wallet refunded (if used)

---

## Potential Issues & Solutions

### Issue 1: Double Order Creation
**Problem:** Level 4 tries to create order again
**Solution:** Check FSM for existing order_id first

### Issue 2: Expired FSM State
**Problem:** User waits too long, FSM cleared
**Solution:** Show "Session expired" error, redirect to cart

### Issue 3: Order Already Has Invoice
**Problem:** User clicks crypto button twice
**Solution:** Check for existing invoice, show it instead

### Issue 4: Cart Already Cleared
**Problem:** Level 4 tries to clear cart again
**Solution:** Safe operation (clearing empty cart is fine)

---

## Database Impact

**No schema changes required** ✅

Existing fields are sufficient:
- `Order.wallet_used` - Already tracked
- `Invoice.order_id` - Already supports multiple invoices per order
- FSM state - Already used for shipping address

---

## Rollback Plan

If issues arise:

1. **Revert Step 3** (Level 9) - Least critical
2. **Revert Step 2** (Level 4) - More critical
3. **Revert Step 1** (Level 3) - Most critical (but shouldn't need to)

Each step is in separate commit for easy revert.

---

## Implementation Summary

1. ✅ Review this plan
2. ✅ Implement Step 2 (Level 4) - Commit d8ae0a0
3. ✅ Implement Step 3 (Level 9) - Commit 0f99b73
4. ⏳ Test all flows (See TESTING_GUIDE.md)
5. ⏳ Push to remote

---

**Questions?** Review this file before starting next session!
