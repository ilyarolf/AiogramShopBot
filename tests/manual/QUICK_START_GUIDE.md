# Payment Testing - Quick Start Guide

This guide helps you quickly test cryptocurrency payments and wallet top-ups without needing real crypto transactions.

## Prerequisites

```bash
# Install test dependencies
pip install -r tests/manual/requirements.txt

# Ensure .env is configured
RUNTIME_ENVIRONMENT=DEV  # Automatically starts ngrok
KRYPTO_EXPRESS_API_SECRET=your-secret-key
```

## Quick Test: Wallet Top-Up (TOPUP)

### 1. Start Bot

```bash
python run.py
```

Bot automatically:
- Starts ngrok tunnel (DEV mode)
- Exposes webhook endpoint
- Shows webhook URL in logs

### 2. Create TOPUP Request

1. **Open bot in Telegram**
2. **Go to:** My Profile → Top Up Wallet
3. **Select crypto:** BTC (or any cryptocurrency)
4. **Enter amount:** 50 EUR
5. **Bot responds with:**
   ```
   💵 Deposit to the address...

   Reference: TOPUP-2025-ABCDEF
   Payment status: ⚪ Pending.

   Your BTC address:
   bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
   ```

6. **Copy the reference:** `TOPUP-2025-ABCDEF`

### 3. Simulate Payment Webhook

```bash
# Simulate payment for wallet top-up
python tests/manual/simulate_payment_webhook.py \
  --invoice-number TOPUP-2025-ABCDEF \
  --amount-paid 0.00105390 \
  --amount-required 0.00105390 \
  --crypto BTC
```

**Expected Result:**
- ✅ Wallet balance increased by €50.00
- 🔔 Notification: "Your balance was successfully funded by 50.00 EUR"
- 📊 Admin notification about deposit

### 4. Verify Wallet Balance

1. **Open bot:** My Profile
2. **Check balance:** Should show +€50.00
3. **Use for shopping:** Balance is now available for orders

---

## Quick Test: Order Payment

### 1. Add Items to Cart

1. **Navigate:** 🛒 Shop → Category → Subcategory
2. **Add items:** Select quantity → Add to cart
3. **Checkout:** 🛒 Cart → 💳 Checkout
4. **Select crypto:** BTC

### 2. Note Order Details

Bot message:
```
✅ Order created successfully!

📋 Order code: ORDER-2025-GHIJKL
💰 Total price: 20.00 EUR

🪙 Amount to pay:
0.00042156 BTC

📬 Payment address:
bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

⏰ Expires at: 15:45 (15 minutes)
```

Copy: `ORDER-2025-GHIJKL` and `0.00042156`

### 3. Simulate Payment

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number ORDER-2025-GHIJKL \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC
```

**Expected Result:**
- ✅ Order status: PAID
- 📦 Items delivered via message
- 📊 Admin notification about purchase

---

## Common Test Scenarios

### Overpayment (10%)

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number ORDER-2025-GHIJKL \
  --amount-paid 0.00046372 \
  --amount-required 0.00042156 \
  --crypto BTC
```

**Result:** Order paid + Excess (€2.00) credited to wallet

---

### Underpayment (90%)

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number ORDER-2025-GHIJKL \
  --amount-paid 0.00037940 \
  --amount-required 0.00042156 \
  --crypto BTC
```

**Result:** New invoice for remaining €2.00 (30 min extension)

---

### Late Payment

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number ORDER-2025-GHIJKL \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC \
  --late
```

**Result:** Order cancelled + 5% penalty + Net credited to wallet (€19.00)

---

### Double Payment

First, complete order normally, then:

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number ORDER-2025-GHIJKL \
  --amount-paid 0.00042156 \
  --amount-required 0.00042156 \
  --crypto BTC
```

**Result:** Full amount (€20.00) credited to wallet (NO penalty)

---

## Testing Unban System

### 1. Get Banned (Simulate Strikes)

Create 3 orders and let them timeout (or cancel late):

```bash
# Create order → Wait 15 min → Auto-cancelled with strike
# Repeat 3 times → User banned
```

### 2. Unban via Wallet Top-Up

1. **Try to shop:** Get ban message with unban instructions
2. **Go to:** My Profile → Top Up Wallet
3. **Top up:** ≥ €50.00 (configured in UNBAN_TOP_UP_AMOUNT)
4. **Simulate payment:**

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number TOPUP-2025-XYZABC \
  --amount-paid 0.00105390 \
  --amount-required 0.00105390 \
  --crypto BTC
```

**Expected Result:**
- ✅ User unbanned automatically
- 💰 Wallet balance: +€50.00 (available for shopping)
- 🔔 Notification: "Account unbanned! You can shop again."
- ⚠️ Strikes remain (next strike = immediate re-ban)

---

## Invoice Number Format Reference

| Type | Format | Example | Description |
|------|--------|---------|-------------|
| **Order** | `ORDER-YYYY-XXXXXX` | `ORDER-2025-A3F9B2` | Regular shopping orders |
| **Top-Up** | `TOPUP-YYYY-XXXXXX` | `TOPUP-2025-K7M2P9` | Wallet deposit/top-up |
| **Legacy** | `YYYY-XXXXXX` | `2025-A3F9B2` | Old format (still supported) |

**Important:** Always use the exact reference shown in bot message!

---

## Webhook Simulator Script Options

```bash
python tests/manual/simulate_payment_webhook.py \
  --invoice-number <REFERENCE>     # Order or TOPUP reference
  --amount-paid <CRYPTO_AMOUNT>    # Amount sent by "customer"
  --amount-required <CRYPTO_AMOUNT> # Expected amount
  --crypto <BTC|LTC|ETH|SOL>       # Cryptocurrency used
  [--late]                         # Simulate late payment (after deadline)
  [--webhook-url <URL>]            # Custom webhook URL (optional)
```

**Notes:**
- `amount-paid` and `amount-required` must be in **crypto** (not fiat)
- Fiat amounts are automatically calculated by bot using original exchange rate
- Bot automatically detects TOPUP vs ORDER from invoice number prefix

---

## Troubleshooting

### Webhook not received

```bash
# Check bot logs
tail -f logs/bot.log | grep webhook

# Verify ngrok is running (DEV mode)
curl http://localhost:4040/api/tunnels

# Test webhook manually
curl -X POST https://YOUR-NGROK-URL.ngrok.io/webhook/cryptoprocessing/event \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","invoice_number":"TEST-2025-ABCDEF"}'
```

### Invoice number not found

- Verify exact format: `ORDER-2025-XXXXXX` or `TOPUP-2025-XXXXXX`
- Check database: `sqlite3 shop.db "SELECT invoice_number FROM invoices;"`
- Use bot message value exactly (copy-paste)

### Signature validation fails

```bash
# Check API secret matches
echo $KRYPTO_EXPRESS_API_SECRET

# .env file should match test script signature generation
# Both must use same secret key
```

### Amount mismatch

- Use **crypto amounts** (BTC, LTC, ETH), NOT fiat (EUR/USD)
- Copy exact crypto amount from bot message
- Bot calculates fiat using original invoice exchange rate

---

## Next Steps

After successful testing:

1. ✅ TOPUP tested → Wallet balance increases
2. ✅ ORDER tested → Items delivered
3. ✅ Overpayment → Wallet credited
4. ✅ Underpayment → Retry or penalty
5. ✅ Late/Double → Wallet credited (with/without penalty)
6. ✅ Unban → User unbanned + wallet funded

**Ready for production:**
- Configure real KryptoExpress credentials
- Set RUNTIME_ENVIRONMENT=PROD
- Monitor first real transactions
- Check admin notifications working

---

## Full Documentation

For detailed scenarios and edge cases:
- **Full Test Guide:** `tests/manual/payment-shipment-test-guide.md`
- **Strike System Tests:** `tests/strike-system/TEST_CASES.md`
- **Test Checklist:** `TEST_CHECKLIST.md`

---

## Support

**Common Issues:**
- Webhook signature: Check KRYPTO_EXPRESS_API_SECRET in .env
- Invoice not found: Use exact reference from bot (including prefix)
- Amount mismatch: Use crypto amounts, not fiat

**For help:**
- Check logs: `logs/bot.log`
- Check database: `sqlite3 shop.db`
- Review webhook payload in logs
