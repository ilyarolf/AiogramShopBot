# Strike System & Top-Up Unban Test Cases

This document contains all test cases for the Strike System and Top-Up Unban functionality.

## Prerequisites

1. Bot running locally with ngrok/webhook enabled
2. `.env` configured with test values:
   ```bash
   MAX_STRIKES_BEFORE_BAN=3
   EXEMPT_ADMINS_FROM_BAN=true  # For testing without getting banned yourself
   UNBAN_TOP_UP_AMOUNT=50.0
   ORDER_TIMEOUT_MINUTES=2      # Faster testing
   ORDER_CANCEL_GRACE_PERIOD_MINUTES=0  # No grace period for testing
   ```
3. Test user account (NOT admin)

---

## Test Suite 1: Strike Accumulation & Ban

### TC-1.1: First Strike (Order Timeout)
**Objective**: User receives strike when order times out

**Steps**:
1. Create order as test user
2. Wait for ORDER_TIMEOUT_MINUTES (2 min)
3. Wait for PaymentTimeoutJob to fire (runs every 60s)

**Expected Result**:
- ✅ Order status → TIMEOUT
- ✅ Strike created in UserStrike table
- ✅ User receives "Order Cancelled" notification with strike warning
- ✅ Strike count: 1/3 (visible in My Profile → Strike Statistics)

---

### TC-1.2: Second Strike (Late Cancellation)
**Objective**: User receives strike for cancelling after grace period

**Steps**:
1. Create order as test user
2. Wait for grace period to expire (ORDER_CANCEL_GRACE_PERIOD_MINUTES)
3. Manually cancel order via bot

**Expected Result**:
- ✅ Order status → CANCELLED
- ✅ Strike created in UserStrike table
- ✅ User receives "Order Cancelled" notification with strike warning
- ✅ Strike count: 2/3
- ✅ Status shows: "⚠️ Warning - 1 strikes until ban"

---

### TC-1.3: Third Strike → Automatic Ban
**Objective**: User is automatically banned after reaching threshold

**Steps**:
1. Create order as test user (who already has 2 strikes)
2. Let order timeout

**Expected Result**:
- ✅ Strike count: 3/3
- ✅ `user.is_blocked = True`
- ✅ User receives ban notification
- ✅ User blocked from shopping (Cart, Browse Categories blocked)
- ✅ User CAN still access My Profile

---

### TC-1.4: Strike Count Display Accuracy
**Objective**: Strike count shows actual DB records, not cached counter

**Steps**:
1. Check Strike Statistics in My Profile
2. Compare with DB query: `SELECT COUNT(*) FROM user_strikes WHERE user_id = X`

**Expected Result**:
- ✅ Displayed count matches DB count
- ✅ No negative "remaining strikes"
- ✅ Invoice numbers shown (not DB order IDs)

---

## Test Suite 2: Banned User Access Control

### TC-2.1: Banned User - Blocked Routes
**Objective**: Banned users cannot access shopping functions

**Steps**:
1. As banned user, try to:
   - Browse categories
   - View cart
   - Create order

**Expected Result**:
- ✅ All shopping routes blocked
- ✅ IsUserExistFilter returns False
- ✅ No error, just no response

---

### TC-2.2: Banned User - Protected Routes
**Objective**: Banned users CAN access My Profile for top-up

**Steps**:
1. As banned user, click "My Profile"
2. View profile menu

**Expected Result**:
- ✅ Profile opens successfully
- ✅ Top-Up button visible
- ✅ Strike Statistics visible
- ✅ Purchase History visible

---

## Test Suite 3: Wallet Top-Up Unban

### TC-3.1: Get Payment ID for Top-Up
**Objective**: Create top-up and get payment ID

**Steps**:
1. As banned user: My Profile → Top Up Balance
2. Select cryptocurrency (e.g., BTC)
3. Bot creates payment and shows address
4. Check logs for payment ID:
   ```
   💰 Processing DEPOSIT payment (ID: 12345)
   ```
5. OR query database:
   ```sql
   SELECT processing_payment_id FROM payments
   WHERE user_id = X
   ORDER BY id DESC LIMIT 1;
   ```

**Expected Result**:
- ✅ Payment ID obtained (e.g., 12345)

---

### TC-3.2: Top-Up Below Threshold (No Unban)
**Objective**: Top-up < 50 EUR does NOT unban

**Steps**:
1. Get payment ID from TC-3.1
2. Simulate webhook with 49 EUR:
   ```bash
   python tests/payment/manual/simulate_payment_webhook.py \
       --payment-id 12345 \
       --amount-paid 0.001 \
       --deposit \
       --fiat-amount 49.0
   ```

**Expected Result**:
- ✅ Wallet credited with 49 EUR
- ✅ User receives "New Deposit" notification
- ✅ User still BANNED (`user.is_blocked = True`)
- ✅ No unban notification

---

### TC-3.3: Top-Up Exactly at Threshold (Unban)
**Objective**: Top-up = 50 EUR unbans user

**Steps**:
1. Get new payment ID (create another top-up)
2. Simulate webhook with 50 EUR:
   ```bash
   python tests/payment/manual/simulate_payment_webhook.py \
       --payment-id 12346 \
       --amount-paid 0.001 \
       --deposit \
       --fiat-amount 50.0
   ```

**Expected Result**:
- ✅ Wallet credited with 50 EUR
- ✅ User receives "New Deposit" notification
- ✅ User receives "Account Unbanned" notification
- ✅ User UNBANNED (`user.is_blocked = False`)
- ✅ Strike count remains at 3 (NOT reset!)
- ✅ User can shop again

---

### TC-3.4: Top-Up Above Threshold (Unban)
**Objective**: Top-up > 50 EUR unbans user

**Steps**:
1. Get new payment ID
2. Simulate webhook with 100 EUR:
   ```bash
   python tests/payment/manual/simulate_payment_webhook.py \
       --payment-id 12347 \
       --amount-paid 0.002 \
       --deposit \
       --fiat-amount 100.0
   ```

**Expected Result**:
- ✅ Wallet credited with 100 EUR
- ✅ User receives both notifications
- ✅ User UNBANNED
- ✅ Strike count remains unchanged

---

## Test Suite 4: Immediate Re-Ban After Unban

### TC-4.1: One More Strike After Unban → Immediate Ban
**Objective**: User with 3 strikes gets immediately banned on 4th strike

**Steps**:
1. Ensure user has 3 strikes and was unbanned via top-up (from TC-3.3)
2. Verify `user.strike_count = 3` in DB
3. Create new order
4. Let order timeout

**Expected Result**:
- ✅ Strike count: 4
- ✅ User IMMEDIATELY BANNED again
- ✅ Ban notification sent
- ✅ Logic: `actual_strike_count (4) >= MAX_STRIKES_BEFORE_BAN (3)` → Ban

---

## Test Suite 5: Admin Exemption

### TC-5.1: Admin with EXEMPT_ADMINS_FROM_BAN=true
**Objective**: Admin accumulates strikes but is NOT banned

**Steps**:
1. Set `EXEMPT_ADMINS_FROM_BAN=true`
2. As admin user, accumulate 5+ strikes

**Expected Result**:
- ✅ Strikes recorded in DB
- ✅ Strike count: 5/3 (shows in profile)
- ✅ Admin NOT banned
- ✅ Admin can still shop
- ✅ Logs show: "⚠️ Admin X reached ban threshold but is exempt"

---

### TC-5.2: Admin Unban Script
**Objective**: Unban admin after testing

**Steps**:
```bash
# Unban all admins from ADMIN_ID_LIST
python tests/strike-system/unban_admin.py

# Unban all admins + reset strikes
python tests/strike-system/unban_admin.py --reset-strikes

# Unban specific admin
python tests/strike-system/unban_admin.py --telegram-id 123456789
```

**Expected Result**:
- ✅ Admin unbanned
- ✅ Optionally: strikes reset to 0

---

## Test Suite 6: Edge Cases

### TC-6.1: Negative Remaining Strikes
**Objective**: Never show negative remaining strikes

**Steps**:
1. User with 5 strikes (MAX=3)
2. Check Strike Statistics

**Expected Result**:
- ✅ Shows: "5/3"
- ✅ Remaining: 0 (NOT -2)
- ✅ Status: "🚫 Banned"

---

### TC-6.2: Strike Count Sync
**Objective**: DB count is source of truth

**Steps**:
1. Check `user.strike_count` in DB
2. Check `COUNT(*) FROM user_strikes`
3. View Strike Statistics in bot

**Expected Result**:
- ✅ All three numbers match
- ✅ Display uses actual DB count

---

### TC-6.3: Invoice Numbers in Strike List
**Objective**: Show invoice numbers, not order IDs

**Steps**:
1. View Strike Statistics
2. Check strikes list

**Expected Result**:
- ✅ Shows: "2025-ABC123" (invoice number)
- ✅ NOT: "#42" (database order ID)

---

## Verification Queries

### Check User Strike Count
```sql
SELECT u.telegram_id, u.strike_count, COUNT(us.id) as actual_strikes
FROM users u
LEFT JOIN user_strikes us ON u.id = us.user_id
WHERE u.telegram_id = YOUR_USER_ID
GROUP BY u.id;
```

### Check Strike Records
```sql
SELECT
    us.created_at,
    us.strike_type,
    i.invoice_number,
    us.reason
FROM user_strikes us
LEFT JOIN invoices i ON us.order_id = i.order_id
WHERE us.user_id = USER_ID
ORDER BY us.created_at DESC;
```

### Check Ban Status
```sql
SELECT
    telegram_id,
    is_blocked,
    blocked_at,
    blocked_reason,
    strike_count,
    top_up_amount
FROM users
WHERE telegram_id = YOUR_USER_ID;
```

---

## Summary Checklist

### Strike System
- [ ] TC-1.1: First strike recorded
- [ ] TC-1.2: Second strike recorded
- [ ] TC-1.3: Third strike → Ban
- [ ] TC-1.4: Strike count accurate

### Access Control
- [ ] TC-2.1: Shopping blocked when banned
- [ ] TC-2.2: Profile accessible when banned

### Top-Up Unban
- [ ] TC-3.1: Payment ID obtained
- [ ] TC-3.2: Top-up < 50 EUR (no unban)
- [ ] TC-3.3: Top-up = 50 EUR (unban)
- [ ] TC-3.4: Top-up > 50 EUR (unban)

### Re-Ban
- [ ] TC-4.1: One more strike after unban → immediate ban

### Admin
- [ ] TC-5.1: Admin exempt from ban
- [ ] TC-5.2: Admin unban script works

### Edge Cases
- [ ] TC-6.1: No negative remaining strikes
- [ ] TC-6.2: Strike count synced
- [ ] TC-6.3: Invoice numbers shown
