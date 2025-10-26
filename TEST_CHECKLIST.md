# Test Checklist: Cart/Order Separation (Phase 1)

## Prerequisites
- [ ] Bot is running
- [ ] Database is accessible
- [ ] Test user account available
- [ ] Test items in inventory (both digital and physical)

---

## [T1] Basic Cart → Order Flow (Digital Items)

### Scenario: Happy path with digital items only

**Steps:**
1. [ ] Add digital items to cart
2. [ ] Navigate to cart (button or `/cart`)
3. [ ] Click "Checkout" button
4. [ ] Verify checkout confirmation screen shows (Level 2)
5. [ ] Click "Confirm" button
6. [ ] **CRITICAL**: Verify redirect to Order domain (OrderCallback Level 0)
7. [ ] Verify order creation message appears
8. [ ] Verify "Continue to Payment" button exists
9. [ ] Click "Continue to Payment"
10. [ ] Verify payment screen appears (crypto selection or direct payment)

**Expected Results:**
- No errors during flow
- Cart → Order transition works seamlessly
- OrderCallback routing works correctly

---

## [T2] Physical Items Flow

### Scenario: Order with physical items requires address

**Steps:**
1. [ ] Clear cart
2. [ ] Add physical items to cart
3. [ ] Navigate to cart and checkout (Level 2 → Confirm)
4. [ ] Verify order creation (OrderCallback Level 0)
5. [ ] **CRITICAL**: Verify shipping address request appears
6. [ ] Verify FSM state is set to `ShippingAddressStates.waiting_for_address`
7. [ ] Enter shipping address as text message
8. [ ] Verify address confirmation screen (OrderCallback Level 1)
9. [ ] Click "Confirm Address"
10. [ ] Verify redirect to payment (OrderCallback Level 3)

**Expected Results:**
- Address collection FSM works
- Address is saved to order
- Order status: PENDING_PAYMENT_AND_ADDRESS → PENDING_PAYMENT

---

## [T3] Stock Adjustments

### Scenario: Order with insufficient stock

**Setup:**
- Ensure at least one item in cart has limited stock (< requested quantity)

**Steps:**
1. [ ] Add items to cart (ensure one has insufficient stock)
2. [ ] Navigate to cart and checkout
3. [ ] Verify order creation starts (OrderCallback Level 0)
4. [ ] **CRITICAL**: Verify stock adjustment screen appears (OrderCallback Level 9)
5. [ ] Verify message shows which items were adjusted
6. [ ] Verify adjusted quantities are displayed
7. [ ] Verify "Continue Payment" button exists
8. [ ] Click "Continue Payment"
9. [ ] Verify redirect to address collection (physical) or payment (digital)

**Expected Results:**
- Stock adjustments detected
- User sees clear message about changes
- Can proceed or cancel order
- Cart NOT cleared yet (user might cancel)

---

## [T4] All Items Out of Stock

### Scenario: All requested items are unavailable

**Setup:**
- Empty stock for all items in cart

**Steps:**
1. [ ] Add items to cart
2. [ ] Admin: Remove all stock for those items
3. [ ] User: Checkout
4. [ ] **CRITICAL**: Verify "All items out of stock" error appears
5. [ ] Verify "Back to Cart" button exists (CartCallback - cross-domain)
6. [ ] Verify order was cancelled (status: CANCELLED_BY_SYSTEM)
7. [ ] Click "Back to Cart"
8. [ ] Verify cart is empty

**Expected Results:**
- Clear error message
- Order cancelled automatically
- Stock released
- Cart cleared

---

## [T5] Order Cancellation

### Scenario A: Cancel within grace period (free)

**Steps:**
1. [ ] Create order (any type)
2. [ ] Immediately click "Cancel Order" (OrderCallback Level 4)
3. [ ] Verify cancellation message mentions "free cancellation"
4. [ ] Verify no strike applied
5. [ ] Verify wallet refunded (if wallet was used)
6. [ ] Verify stock released
7. [ ] Verify cart cleared
8. [ ] Click "Back to Cart" button
9. [ ] Verify back at cart screen

**Expected Results:**
- Order cancelled without penalty
- Wallet refunded
- Stock released

### Scenario B: Cancel after grace period (with strike)

**Steps:**
1. [ ] Create order
2. [ ] Wait > `ORDER_CANCEL_GRACE_PERIOD_MINUTES` (or mock timestamp)
3. [ ] Click "Cancel Order"
4. [ ] Verify cancellation message mentions "strike"
5. [ ] Verify strike applied to user
6. [ ] Verify wallet refunded with processing fee deducted
7. [ ] Verify stock released

**Expected Results:**
- Order cancelled with penalty
- Strike recorded
- Wallet refunded minus fee

---

## [T6] Cross-Domain Navigation

### Scenario: Navigation between Cart and Order domains

**Test Callback Usage:**
1. [ ] From Cart Level 0: Click "Checkout" → Goes to Cart Level 2
2. [ ] From Cart Level 2: Click "Confirm" → Goes to Cart Level 3
3. [ ] From Cart Level 3: Automatically redirects to **OrderCallback Level 0** ✅
4. [ ] From Order domain: Click "Back to Cart" → Goes to **CartCallback Level 0** ✅
5. [ ] From Order domain: Click "Cancel" → Goes to OrderCallback Level 4 ✅

**Expected Results:**
- Cart domain uses CartCallback
- Order domain uses OrderCallback
- Cross-domain "Back to Cart" uses CartCallback
- No callback routing errors

---

## [T7] Payment Processing

### Scenario A: Wallet covers full amount

**Steps:**
1. [ ] User has sufficient wallet balance
2. [ ] Create order
3. [ ] Verify order paid immediately (no crypto selection needed)
4. [ ] Verify "Order completed" message
5. [ ] Verify wallet deducted
6. [ ] Verify cart cleared
7. [ ] Verify order status: PAID

**Expected Results:**
- No crypto selection shown
- Immediate payment completion
- Clean UX

### Scenario B: Wallet insufficient → Crypto payment

**Steps:**
1. [ ] User has insufficient wallet balance
2. [ ] Create order
3. [ ] Verify crypto selection screen appears (OrderCallback Level 3)
4. [ ] Select cryptocurrency (e.g., BTC)
5. [ ] Verify payment screen with QR code and address
6. [ ] Verify wallet amount deducted (partial payment)
7. [ ] Verify remaining crypto amount shown
8. [ ] Verify invoice created

**Expected Results:**
- Crypto selection appears
- Wallet used partially
- Invoice created for remaining amount
- Payment address displayed

---

## [T8] Re-enter Address Flow

### Scenario: User cancels address confirmation

**Steps:**
1. [ ] Create order with physical items
2. [ ] Enter shipping address
3. [ ] On confirmation screen, click "Cancel" (OrderCallback Level 2)
4. [ ] Verify FSM state reset to `waiting_for_address`
5. [ ] Verify address input prompt reappears
6. [ ] Enter new address
7. [ ] Confirm address
8. [ ] Verify redirect to payment

**Expected Results:**
- User can re-enter address
- FSM state properly managed
- No data loss

---

## [T9] Pending Order Detection

### Scenario: User has existing pending order

**Steps:**
1. [ ] Create order but don't complete payment
2. [ ] Navigate to cart
3. [ ] **CRITICAL**: Verify pending order shown instead of cart
4. [ ] Verify order details displayed (invoice, address, expiry)
5. [ ] Verify "Continue to Payment" button exists
6. [ ] Verify "Cancel Order" button exists
7. [ ] Click "Continue to Payment"
8. [ ] Verify redirect to payment screen

**Expected Results:**
- Pending order takes priority over cart
- Clear order status shown
- Can continue or cancel

---

## [T10] Order Expiration

### Scenario: Order expires before payment

**Setup:**
- Set `ORDER_TIMEOUT_MINUTES` to low value (e.g., 1 minute) or mock timestamp

**Steps:**
1. [ ] Create order
2. [ ] Wait until order expires
3. [ ] Navigate to cart
4. [ ] Verify "Order expired" message shown
5. [ ] Verify order auto-cancelled (status: CANCELLED_BY_SYSTEM)
6. [ ] Verify stock released
7. [ ] Verify wallet refunded
8. [ ] Verify cart empty message shown

**Expected Results:**
- Order auto-cancelled on expiry
- Clean error message
- Resources released

---

## [R1-R5] Regression Tests

### Verify old flows still work:
1. [ ] Add to cart with stock validation
2. [ ] Remove items from cart
3. [ ] Cart pagination (if many items)
4. [ ] Admin notification on new order
5. [ ] Localization (all messages display correctly)

---

## [E1-E5] Edge Cases

1. [ ] **Double-click prevention**: Rapidly click "Checkout" button → Should not create duplicate orders
2. [ ] **FSM state loss**: Clear FSM state mid-order → Should handle gracefully
3. [ ] **Network timeout**: Simulate slow API response → Should not break flow
4. [ ] **Invalid order_id**: Manually craft callback with invalid order_id → Should show error
5. [ ] **Mixed cart (digital + physical)**: Order with both types → Should collect address

---

## [CR1-CR8] Code Review Checklist

1. [ ] No `CartCallback` in Order domain methods (except cross-domain "Back to Cart")
2. [ ] No `OrderCallback` in Cart domain methods (except Level 3 hand-off)
3. [ ] All order-related imports removed from cart handlers
4. [ ] No dead code in CartService (6 methods deleted)
5. [ ] OrderService has all required methods
6. [ ] FSM states properly managed (set/clear at right times)
7. [ ] Session commits in correct places
8. [ ] Error handling for all edge cases

---

## [P1-P4] Performance Tests

1. [ ] Order creation < 2 seconds
2. [ ] Stock reservation is atomic (no race conditions)
3. [ ] Database queries optimized (no N+1 queries)
4. [ ] Memory usage stable during heavy load

---

## Notes

- **Critical paths**: Cart Level 3 → OrderCallback Level 0 (main transition point)
- **Cross-domain navigation**: Always verify correct Callback type used
- **FSM state management**: Verify state.clear() called after completion
- **Cart clearing**: Only cleared after successful order creation OR cancellation

---

## Test Environment

- [ ] Development: localhost
- [ ] Staging: staging server
- [ ] Production: final smoke test

---

## Sign-off

- [ ] All tests passed
- [ ] No regressions found
- [ ] Ready for production deployment

---

**Last Updated**: 2025-10-25
**Phase**: Phase 1 - Cart/Order Separation
**Tested By**: _____________
**Date**: _____________
