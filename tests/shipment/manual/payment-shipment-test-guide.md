# Payment Validation System - Testing Guide

This guide provides step-by-step instructions for testing the payment validation system with realistic scenarios.

## Overview

The payment validation system handles cryptocurrency payments via KryptoExpress. This testing guide allows you to test all payment scenarios without requiring real crypto payments.

**Important Note**: The bot calculates fiat amounts from crypto amounts using the original invoice exchange rate. The webhook simulator only requires crypto amounts - fiat amounts are automatically calculated by the bot to prevent divergence due to exchange rate fluctuations.

## Prerequisites

### 1. Install Test Dependencies

```bash
cd /path/to/AiogramShopBot
pip install -r tests/manual/requirements.txt
```

### 2. Configure Environment

Add to your `.env` file:

```bash
# KryptoExpress Configuration (use test credentials)
KRYPTO_EXPRESS_API_KEY=your-test-api-key
KRYPTO_EXPRESS_API_SECRET=your-test-api-secret
KRYPTO_EXPRESS_API_URL=https://kryptoexpress.pro/api

# Bot Configuration
TOKEN=your-telegram-bot-token
ADMIN_ID_LIST=your-telegram-user-id
CURRENCY=EUR

# Order Configuration
ORDER_TIMEOUT_MINUTES=15
ORDER_CANCEL_GRACE_PERIOD_MINUTES=5
```

### 3. Setup Test Shop Data

#### A. Import Test Items

Import test items via bot admin panel:

1. **Start bot as admin:**
   ```bash
   python run.py
   ```

2. **Open bot in Telegram** and send `/admin`

3. **Import items:**
   - Go to: Add Items → Import JSON (or equivalent)
   - Upload: `tests/manual/test_shop_data.json`
   - Or manually add items as described below

**Manual Import Alternative:**

If JSON import is not available, add items manually via bot admin panel:

1. **Create Categories:**
   - Category 1: "Digital Products"
   - Category 2: "Gift Cards"

2. **Create Subcategories:**
   - Under "Digital Products":
     - "Game Keys" (price: €10)
     - "Software Licenses" (price: €25)
   - Under "Gift Cards":
     - "Steam Cards" (price: €20)
     - "Amazon Cards" (price: €50)

3. **Add Items:**
   - Add 5 items to "Game Keys" (use dummy codes from JSON)
   - Add 3 items to "Software Licenses"
   - Add 10 items to "Steam Cards"
   - Add 5 items to "Amazon Cards"

#### B. Setup Test User

Create a test user manually:

1. **Start bot as regular user** (use your personal Telegram account or create test account)

2. **Send `/start` to bot** to register user

3. **Credit wallet balance (as admin):**
   - Open bot as admin
   - Go to: Manage Users
   - Find your test user
   - Credit wallet: €100 (for wallet payment testing)

**Note your Telegram User ID:**
- Use @userinfobot or similar to get your Telegram ID
- You'll need this ID to identify test orders in database

## Test Shop Data

The provided test data (`tests/manual/test_shop_data.json`) contains:

**23 Test Items across 4 Subcategories:**
- **Digital Products → Game Keys:** 5 items @ €10 each
- **Digital Products → Software Licenses:** 3 items @ €25 each
- **Gift Cards → Steam Cards:** 10 items @ €20 each
- **Gift Cards → Amazon Cards:** 5 items @ €50 each

**Item Content Format:**
- All codes are dummy/example data (e.g., "STEAM-KEY-AAAAA-BBBBB-CCCCC")
- Replace with real codes in production environment

## Testing Workflow

### Phase 1: Setup and Bot Start

1. **Start the bot:**
   ```bash
   python run.py
   ```

2. **Start ngrok tunnel** (for webhook testing on localhost):
   ```bash
   ngrok http 8000
   ```

   Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

3. **Set webhook URL environment variable:**
   ```bash
   export WEBHOOK_URL="https://abc123.ngrok.io/webhook/cryptoprocessing/event"
   export KRYPTO_EXPRESS_API_SECRET="your-test-api-secret"
   ```

### Phase 2: Create Order in Bot

1. **Open bot in Telegram** (as test user)

2. **Navigate to shop:**
   - Click "🛒 Shop"
   - Select "Digital Products"
   - Select "Game Keys"

3. **Add items to cart:**
   - Select quantity (e.g., 2 items = €20)
   - Click "Add to cart"

4. **Checkout:**
   - Click "🛒 Cart"
   - Click "💳 Checkout"
   - Confirm checkout

5. **Select cryptocurrency:**
   - Click "BTC" (or any other crypto)

6. **Note order details from bot message:**
   ```
   ✅ Order created successfully!

   📋 Order ID: 2025-ABCDEF
   💰 Total price: 20.00 EUR

   💳 Payment details:
   🪙 Amount to pay:
   0.00042156 BTC

   📬 Payment address:
   bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

   ⏰ Expires at: 15:45 (15 minutes)
   ```

   **Copy these values for testing:**
   - Order ID: `2025-ABCDEF` (copy exactly as shown)
   - Amount required: `0.00042156` BTC

### Phase 3: Simulate Payment Webhook

Now simulate the payment webhook based on the scenario you want to test.

#### Scenario 1: Exact Payment ✅

**Expected behavior:** Order completed, items marked as sold

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC \
```

**Verify in bot:**
- Order status: PAID
- Items delivered via message
- Wallet balance unchanged (or increased if overpaid)

---

#### Scenario 2: Minor Overpayment (0.05%) 💰

**Expected behavior:** Order completed, excess forfeited to shop

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.000421771 \
  --amount-required 0.00042156 \
  --crypto BTC \
```

**Verify in bot:**
- Order status: PAID
- Items delivered
- Wallet balance unchanged (excess < 0.1% → forfeited)

---

#### Scenario 3: Significant Overpayment (10%) 💳

**Expected behavior:** Order completed, excess credited to wallet

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00046372 \
  --amount-required 0.00042156 \
  --crypto BTC \
```

**Verify in bot:**
- Order status: PAID
- Items delivered
- Wallet balance increased by €2.00 (excess > 0.1%)
- Notification: "Overpayment of €2.00 credited to wallet"

---

#### Scenario 4: Underpayment (90%) - First Attempt ⚠️

**Expected behavior:** New invoice created for remaining amount

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00037940 \
  --amount-required 0.00042156 \
  --crypto BTC \
```

**Verify in bot:**
- Order status: PENDING_PAYMENT (still pending)
- New invoice created for €2.00 (remaining amount)
- Deadline extended by +15 minutes
- Notification: "Underpayment detected. Please pay remaining €2.00"

**Note:** Payment ID remains the same for second attempt!

---

#### Scenario 5: Underpayment (Second Attempt) 💸

**Expected behavior:** Order cancelled, 5% penalty, net to wallet

```bash
# First payment (from previous scenario): €18.00
# Second payment: €1.00 (still short by €1.00)

python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00002108 \
  --amount-required 0.00004216 \
  --crypto BTC \
```

**Verify in bot:**
- Order status: CANCELLED
- Total received: €19.00 (€18 + €1)
- Penalty: €0.95 (5% of €19)
- Wallet credit: €18.05 (€19 - €0.95)
- Notification: "Second underpayment. Order cancelled. €18.05 credited to wallet after penalty"

---

#### Scenario 6: Currency Mismatch ❌

**Expected behavior:** Payment rejected, order still pending

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.05 \
  --amount-required 0.00042156 \
  --crypto LTC \
```

**Verify in bot:**
- Order status: PENDING_PAYMENT (unchanged)
- Notification: "Currency mismatch. Expected BTC, received LTC. Payment rejected."
- Order deadline unchanged

---

#### Scenario 7: Late Payment (After Deadline) ⏰

**Expected behavior:** Order cancelled, 5% penalty, net to wallet

**First, wait for order to expire (15 minutes), OR:**

```bash
# Manually expire order in database
# OR simulate expired payment webhook
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC \
  --late
```

**Verify in bot:**
- Order status: CANCELLED
- Penalty: €1.00 (5% of €20)
- Wallet credit: €19.00 (€20 - €1)
- Notification: "Late payment. Order cancelled. €19.00 credited to wallet after penalty"
- Items returned to stock (available again)

---

#### Scenario 8: Double Payment (No Penalty) ⚠️

**Expected behavior:** Second payment fully credited to wallet (NO PENALTY)

**Important:** Double payment is not the user's fault (technical issue/misunderstanding), so **NO 5% penalty applies**. Full amount goes to wallet.

**First, complete an order normally (Scenario 1), then:**

```bash
# Send the same webhook again with same invoice number
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC
```

**Verify in bot:**
- Order status: PAID (unchanged)
- Wallet balance increased by €20.00 (**NO penalty deducted**)
- Notification: "⚠️ Double Payment Detected. We received a duplicate payment for order #X. Amount credited to wallet: €20.00. Your order was already completed."
- Items NOT delivered again (already sold)

**Compare with Late Payment (Scenario 7):**
- Late Payment = User's fault → 5% penalty
- Double Payment = Not user's fault → NO penalty

---

### Phase 4: Wallet Payment Scenarios

#### Scenario 9: Full Wallet Payment (No Invoice) 💰

**Setup:**
1. Ensure user has sufficient wallet balance (≥ cart total)
2. Add items to cart (e.g., 1 Game Key = €10)
3. Click checkout
4. Select crypto

**Expected behavior:** Order paid immediately, no invoice created

**Verify in bot:**
- Message: "✅ Order Paid Successfully (Wallet)"
- Order status: PAID
- Items delivered immediately
- Wallet balance reduced by €10
- No payment address shown

---

#### Scenario 10: Partial Wallet Payment + Crypto Invoice 💳

**Setup:**
1. Ensure user has partial wallet balance (e.g., €5)
2. Add items to cart (total €20)
3. Click checkout
4. Select crypto (e.g., BTC)

**Expected behavior:** Wallet partially used, invoice for remaining amount

**Verify in bot:**
- Message shows:
  - Total price: €20.00
  - Wallet balance used: €5.00
  - Remaining to pay: €15.00
- Invoice created for €15.00 (not €20!)
- Payment address shown for €15.00 worth of BTC

**Then simulate payment for remaining amount:**
```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.00031617 \
  --amount-required 0.00031617 \
  --crypto BTC \
```

**Verify:**
- Order status: PAID
- Items delivered
- Total paid: €5 (wallet) + €15 (crypto) = €20

---

#### Scenario 11: Wallet-Only Order with Invoice Tracking 📋

**Setup:**
1. Ensure user has sufficient wallet balance (≥ cart total)
2. Add items to cart (e.g., 2 Game Keys = €20)
3. Click checkout

**Expected behavior:** Order paid immediately, invoice created for tracking

**Verify in bot:**
- Message: "✅ Order Paid Successfully (Wallet)"
- Order status: PAID
- Items delivered immediately
- Wallet balance reduced by €20
- **Invoice number generated** (e.g., "2025-ABC123")
- No payment address (wallet-only)

**Verify in Order History:**
- Navigate to: My Profile → Order History → Select Order
- **Invoice Number:** Shows "2025-ABC123" (NOT "N/A")
- Total: €20.00
- Status: Paid

**Purpose:** Ensures all orders have invoices for tracking/auditing, even when paid entirely by wallet.

---

#### Scenario 12: Stock Adjustment with Wallet Payment (Partial Steal) ⚠️

**Setup:**
1. Ensure user has sufficient wallet balance (≥ cart total)
2. Add 5x items to cart (e.g., 5x Game Keys = €50)
3. **Before clicking checkout:** Run race condition script to steal 3 items

**Expected behavior:** Adjustment screen shown, user confirms, order completed

**Test steps:**

1. **Add items to cart:**
   - Add 5x Game Keys to cart (€50 total)

2. **Run race condition script** (Terminal 2):
   ```bash
   RUNTIME_ENVIRONMENT=TEST python tests/manual/simulate_race_condition.py
   ```
   - Select "Game Keys"
   - Choose to steal 3 items
   - Press ENTER

3. **Immediately click Checkout** in bot

**Verify - Adjustment Screen:**
- Message: "⚠️ Stock adjustments during reservation:"
- Shows: "Requested: 5 | Available: 2"
- New total: €20.00 (2 items instead of 5)
- Buttons: "✅ Continue Payment" and "❌ Cancel Order"

4. **Click "Continue Payment"**

**Verify - Order Completion:**
- Message: "✅ Order Paid Successfully (Wallet)"
- Items delivered: 2 Game Keys (not 5)
- Wallet balance reduced by €20 (not €50)
- Order status: PAID
- **Invoice created with correct amount** (€20, not €50)

5. **Click "Cancel Order" instead (alternative path)**

**Verify - Order Cancellation:**
- Message: "✅ Order cancelled successfully!"
- Cart cleared
- Wallet balance unchanged (full refund)
- Reserved items released back to stock

**Purpose:** Tests atomic stock reservation with wallet payments and ensures invoice amounts reflect actual reserved quantities.

---

#### Scenario 13: Multiple Invoices Display (Underpayment) 📋📋

**Setup:**
1. Create order with underpayment (Scenario 4 - First Attempt)
2. Verify multiple invoices are created
3. Check order history displays ALL invoices

**Test steps:**

1. **Create order and underpay:**
   ```bash
   # First payment: 90% of required amount
   python tests/manual/simulate_payment_webhook.py \
     --invoice-number 2025-ABCDEF \
     --amount-paid 0.00037940 \
     --amount-required 0.00042156 \
     --crypto BTC \
   ```

2. **Verify new invoice created:**
   - Order status: PENDING_PAYMENT_PARTIAL
   - New invoice number: 2025-XYZ789
   - Remaining amount: €2.00

3. **Complete second payment:**
   ```bash
   # Second payment: remaining amount
   python tests/manual/simulate_payment_webhook.py \
     --invoice-number 2025-XYZ789 \
     --amount-paid 0.00004216 \
     --amount-required 0.00004216 \
     --crypto BTC \
   ```

4. **Check Order History:**
   - Navigate to: My Profile → Order History → Select Order
   - **Invoice Numbers:** Shows BOTH invoices (one per line):
     ```
     Invoice Number: 2025-ABCDEF
                    2025-XYZ789
     ```
   - **NOT:** "Invoice Number: N/A"
   - **NOT:** Only first invoice shown

**Expected Display:**
```
📋 Order Details

Invoice Number: 2025-ABCDEF
                2025-XYZ789

Status: Paid ✅
Paid on: 2025-10-24 14:30

Items:
1. Game Key #1
2. Game Key #2

Subtotal: €20.00
Total: €20.00
```

**Purpose:** Ensures all invoices (original + partial payment invoices) are visible for audit trail and user transparency.

---

### Phase 5: Automated Test Run

Run all scenarios automatically:

```bash
# Set payment ID offset (avoid conflicts with real orders)
export PAYMENT_ID=999000

# Run all scenarios
./tests/manual/run_payment_scenarios.sh
```

**Expected output:**
```
================================================================
   Payment Validation Test Scenarios
================================================================

Webhook URL: https://abc123.ngrok.io/webhook/cryptoprocessing/event
Payment ID: 999000

================================================================

Starting test scenarios...

========================================
Scenario: Exact Payment (0.001 BTC)
========================================
...
✅ Success

========================================
Scenario: Minor Overpayment (0.05% - forfeits)
========================================
...
✅ Success

[... 6 more scenarios ...]

================================================================
   Test Results Summary
================================================================
Passed: 8
Failed: 0
Total:  8
================================================================

✅ All tests passed!
```

## Verification Checklist

After running tests, verify:

### Database State
```sql
-- Check order status
SELECT id, user_id, status, total_price, wallet_used
FROM orders
WHERE id IN (123456, ...);

-- Check payment transactions
SELECT order_id, crypto_amount, fiat_amount, is_underpayment, penalty_applied
FROM payment_transactions
WHERE order_id IN (123456, ...);

-- Check wallet balance
SELECT id, top_up_amount
FROM users
WHERE id = 999;

-- Check items (sold/available)
SELECT id, subcategory_id, is_sold, order_id
FROM items
WHERE order_id IN (123456, ...);
```

### Bot Notifications
- User receives order status notifications
- Admin receives purchase notifications
- Wallet credit notifications (if applicable)

### Logs
Check application logs for:
```
✅ Payment validated: EXACT
💰 Order creation: Total=20.00 EUR | Wallet=0.00 EUR | Remaining=20.00 EUR
📋 Created invoice for remaining amount: 20.00 EUR
✅ Order completed: Order #123456
```

## Troubleshooting

### Webhook not received
```bash
# Check ngrok is running
curl https://abc123.ngrok.io/health

# Check webhook URL is correct
echo $WEBHOOK_URL

# Check bot logs for errors
tail -f logs/bot.log
```

### Signature validation fails
```bash
# Verify API secret matches
echo $KRYPTO_EXPRESS_API_SECRET

# Check .env file has correct secret
cat .env | grep KRYPTO_EXPRESS_API_SECRET

# Test without signature (WARNING: only for debugging!)
python tests/manual/simulate_payment_webhook.py \
  --invoice-number 2025-ABCDEF \
  --amount-paid 0.001 \
  --no-signature
```

### Order not found
```bash
# Check payment ID matches order ID
# Payment ID format: KE-123456 → use 123456
# Check database for order
sqlite3 shop.db "SELECT * FROM orders WHERE id = 123456;"
```

### Wallet not credited
- Check overpayment threshold (> 0.1%)
- Check second underpayment logic
- Check late payment logic
- Verify wallet balance calculation in logs

## Advanced Testing

### Test with Real KryptoExpress API

1. **Disable webhook simulator**
2. **Use KryptoExpress testnet:**
   ```bash
   export KRYPTO_EXPRESS_API_KEY=testnet-key
   export KRYPTO_EXPRESS_API_SECRET=testnet-secret
   ```
3. **Make real test payment** (use testnet crypto)
4. **Wait for webhook** from KryptoExpress

### Test Edge Cases

#### Concurrent Orders
```bash
# Create multiple orders simultaneously
# Test payment ID collision handling
```

#### Stock Exhaustion
```bash
# Add all items to cart
# Verify stock reservation
# Verify rollback on payment failure
```

#### Deadline Edge Cases
```bash
# Payment received exactly at deadline
# Payment received 1 second after deadline
```

## Next Steps

After successful testing:
1. ✅ All scenarios pass
2. ✅ Database state correct
3. ✅ Notifications working
4. ✅ Logs show expected flow
5. **→ Deploy to production**
6. **→ Configure real KryptoExpress credentials**
7. **→ Test with small real payment**

## Support

For issues or questions:
- Check logs: `logs/bot.log`
- Check database: `sqlite3 shop.db`
- Review code: `services/payment_validator.py`, `services/order.py`
- Create GitHub issue with test scenario details
