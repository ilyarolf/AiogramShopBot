# 🧪 Testing Guide: Shipping Management System

**Copied from:** `feature/shipping-management-system` branch (commit 5ac7253)
**Updated for:** `feature/shipping-management-v2` branch
**Date:** 2025-01-23

---

## 📋 Prerequisites

### 1. Environment Setup
```bash
# Generate encryption key for shipping addresses
openssl rand -hex 32

# Add to .env file
ENCRYPTION_SECRET=<your-generated-key-32-bytes>
```

### 2. Database Migration
The new shipping fields will be auto-created by SQLAlchemy when you start the bot:
- `items` table: `is_physical`, `shipping_cost`, `allows_packstation` columns
- `orders` table: `shipping_cost`, `shipped_at` columns
- `shipping_addresses` table: Complete new table with encryption

**⚠️ Backup your database before testing!**
```bash
cp database.db database.db.backup
```

### 3. Import Test Data
```bash
# Start bot in admin mode
# Navigate to: Admin Menu → Lagerverwaltung → Artikel hinzufügen → JSON

# Upload the file: test_physical_items.json
```

---

## 🧪 Test Scenarios

### Test 1: Digital-Only Order (No Shipping)
**Purpose:** Verify digital items skip shipping flow entirely

**Steps:**
1. As User: Browse to "Digital" → "Software-Lizenzen"
2. Add "Windows 10 Pro Lizenz" to cart (9.99€)
3. Go to cart → Checkout
4. **Expected:** Cart shows:
   ```
   Windows 10 Pro Lizenz (1) = 9.99€

   Gesamtpreis: 9.99€
   ```
   (No shipping line!)
5. Click "Bestätigen"
6. **Expected:** Crypto selection appears immediately (NO address request)
7. Select crypto → Pay
8. **Expected:** Order status = PAID immediately (not PAID_AWAITING_SHIPMENT)

**✅ Pass Criteria:**
- No shipping cost shown
- No address collection triggered
- Order goes directly to PAID status
- User receives digital item immediately

---

### Test 2: Physical-Only Order (With Shipping)
**Purpose:** Verify shipping address collection for physical items

**Steps:**
1. As User: Browse to "Hardware" → "USB-Sticks"
2. Add 1x "SanDisk 32GB USB 3.0 Stick" to cart (15.99€, shipping 2.50€)
3. Go to cart → Checkout
4. **Expected:** Cart shows:
   ```
   SanDisk 32GB... (1) = 15.99€

   Gesamtpreis: 18.49€
   ```
   (Total includes shipping: 15.99 + 2.50 = 18.49)
5. Click "Bestätigen"
6. **Expected:** Address request appears:
   ```
   📬 Bitte geben Sie Ihre vollständige Versandadresse ein:

   Die Adresse sollte enthalten:
   - Name
   - Straße und Hausnummer
   - PLZ und Ort
   - Land

   Ihre Adresse wird verschlüsselt gespeichert.
   ```
7. Enter address (free text):
   ```
   Max Mustermann
   Musterstraße 123
   12345 Berlin
   Deutschland
   ```
8. **Expected:** Confirmation screen with address preview
9. Click "Bestätigen"
10. **Expected:** Crypto selection appears
11. Select crypto → Pay
12. **Expected:** Order status = PAID_AWAITING_SHIPMENT (not PAID)

**✅ Pass Criteria:**
- Shipping cost calculated correctly (2.50€)
- Address collection triggered
- Address stored encrypted in database
- Order status = PAID_AWAITING_SHIPMENT after payment
- Admin receives notification

---

### Test 3: Mixed Cart (Physical + Digital)
**Purpose:** Verify correct shipping calculation for mixed carts

**Steps:**
1. As User: Add multiple items:
   - 1x "USB-Stick" (15.99€, shipping 2.50€)
   - 1x "Windows License" (9.99€, digital, no shipping)
2. Go to cart → Checkout
3. **Expected:** Cart shows:
   ```
   USB-Stick (1) = 15.99€
   Windows License (1) = 9.99€

   Gesamtpreis: 28.48€
   ```
   (Items: 25.98€ + Shipping: 2.50€ = 28.48€)
4. Complete checkout with address
5. **Expected:** Order status = PAID_AWAITING_SHIPMENT
6. **Expected:** User receives Windows license immediately (digital)
7. **Expected:** USB-Stick awaits shipment (physical)

**✅ Pass Criteria:**
- Shipping = MAX(all physical shipping costs)
- Address required because cart has physical items
- Digital items delivered immediately after payment
- Physical items await admin shipment

---

### Test 4: Multiple Physical Items - MAX Shipping Cost
**Purpose:** Verify MAX shipping cost logic (not SUM)

**Steps:**
1. As User: Add multiple physical items:
   - 2x "USB-Stick" (15.99€ each, shipping 2.50€)
   - 1x "T-Shirt" (24.99€, shipping 3.99€)
2. Go to cart → Checkout
3. **Expected:** Cart shows:
   ```
   USB-Stick (2) = 31.98€
   T-Shirt (1) = 24.99€

   Gesamtpreis: 60.96€
   ```
   **Calculation:** Items: 56.97€ + Shipping: 3.99€ (MAX, not 2.50+3.99!)
4. Complete checkout

**✅ Pass Criteria:**
- Shipping = MAX(2.50, 3.99) = 3.99€
- NOT SUM = 2.50+3.99 = 6.49€
- This is the correct behavior!

---

### Test 5: Packstation Restriction Warning
**Purpose:** Verify Packstation warning for restricted items

**Steps:**
1. As User: Add "Grafikkarte" to cart (packstation_allowed=false)
2. Go to cart → Checkout → Bestätigen
3. **Expected:** Address request shows additional warning:
   ```
   ⚠️ Hinweis: Ihre Bestellung enthält Artikel, die NICHT an
   eine Packstation geliefert werden können. Bitte geben Sie
   eine vollständige Hausadresse an.
   ```

**✅ Pass Criteria:**
- Warning appears for Packstation-restricted items
- No warning for Packstation-allowed items (USB, Stickers, T-Shirt)

**⚠️ Status:** Not yet implemented in v2 - planned enhancement

---

### Test 6: Admin Shipping Management
**Purpose:** Verify admin can mark orders as shipped

**Steps:**
1. Complete Test 2 or Test 3 (create order with PAID_AWAITING_SHIPMENT status)
2. As Admin: Navigate to "Admin Menu" → "📦 Versandverwaltung"
3. **Expected:** List shows pending orders:
   ```
   📦 Order #2025-abc123 | @username | 18.49€
   ```
4. Click on order
5. **Expected:** Order details screen shows:
   - Order ID
   - Customer: @username (ID: 123456)
   - Shipping address (decrypted!)
   - Price breakdown:
     - Artikel: 15.99€
     - Versand: 2.50€
     - Gesamtsumme: 18.49€
   - Physical items list only
6. Click "✅ Als versendet markieren"
7. **Expected:** Confirmation screen:
   ```
   ❓ Möchten Sie die Bestellung #2025-abc123 wirklich als versendet markieren?
   ```
8. Confirm
9. **Expected:** Success message:
   ```
   ✅ Bestellung #2025-abc123 wurde als versendet markiert!

   Der Kunde wurde benachrichtigt.
   ```
10. **Expected:** User receives Telegram notification:
    ```
    📦 Ihre Bestellung wurde versendet!

    📋 Bestellcode: 2025-abc123

    Ihre Bestellung ist unterwegs. Vielen Dank für Ihren Einkauf!
    ```
11. Check order status
12. **Expected:** Order status = SHIPPED, shipped_at timestamp set

**✅ Pass Criteria:**
- Admin sees decrypted address
- Only physical items shown in admin view
- User receives "Order shipped" notification
- Order status changes to SHIPPED
- shipped_at timestamp set

---

### Test 7: Address Encryption Verification
**Purpose:** Verify addresses are encrypted in database

**Steps:**
1. Complete Test 2 (create order with address)
2. Open database with SQLite browser:
   ```bash
   sqlite3 database.db
   SELECT * FROM shipping_addresses;
   ```
3. **Expected:** `encrypted_address` column contains binary/hex data, NOT plaintext
   ```
   id  order_id  encrypted_address      nonce             tag
   1   42        \x8a7f2d...            \x9b3e...         \x4c1a...
   ```
4. In Admin UI: View order details
5. **Expected:** Address is decrypted and readable:
   ```
   Max Mustermann
   Musterstraße 123
   12345 Berlin
   Deutschland
   ```

**✅ Pass Criteria:**
- Database stores encrypted bytes (BLOB)
- Admin UI shows decrypted plaintext
- Decryption only possible with ENCRYPTION_SECRET

---

### Test 8: Address Validation
**Purpose:** Verify minimum address length validation

**Steps:**
1. Start checkout with physical item
2. Enter very short address: "Test"
3. **Expected:** Error message:
   ```
   ⚠️ Die Adresse ist zu kurz!

   Bitte geben Sie eine vollständige Versandadresse ein (mindestens 10 Zeichen).
   ```
4. Bot stays in FSM state, waiting for new address
5. Enter address with 10+ characters
6. **Expected:** Confirmation screen appears

**✅ Pass Criteria:**
- Addresses < 10 chars rejected
- Addresses ≥ 10 chars accepted
- User can retry without restarting checkout

---

### Test 9: Order Cancellation with Physical Items
**Purpose:** Verify address handling when order is cancelled

**Steps:**
1. Create order with physical items + address
2. Note the order_id
3. Check database before cancellation:
   ```sql
   SELECT * FROM shipping_addresses WHERE order_id = <order_id>;
   ```
   **Expected:** Address exists
4. Cancel order (within grace period)
5. **Expected:** Order cancelled successfully
6. Check database after cancellation:
   ```sql
   SELECT * FROM shipping_addresses WHERE order_id = <order_id>;
   ```
   **Expected:** Address record still exists (tied to order)

**⚠️ Note:** Addresses are kept with cancelled orders for admin records.
GDPR cleanup happens after retention period (90 days).

**✅ Pass Criteria:**
- Order cancellation works normally
- Address is kept in database
- Address encrypted at rest

---

### Test 10: JSON Import with Shipping Fields
**Purpose:** Verify JSON import validates shipping fields

**Test Data (Invalid):**
```json
[
  {
    "category": "Test",
    "subcategory": "MissingFields",
    "price": 99.99,
    "description": "Physical item without shipping fields",
    "private_data": "DATA",
    "is_physical": true
  }
]
```

**Steps:**
1. As Admin: Try to import above JSON
2. **Expected:** Error or default values applied:
   - `shipping_cost` defaults to 0.0
   - `allows_packstation` defaults to false

**Test Data (Valid):**
```json
[
  {
    "category": "Hardware",
    "subcategory": "Test-USB",
    "price": 19.99,
    "description": "Test USB Stick",
    "private_data": "Serial: TEST-001",
    "is_physical": true,
    "shipping_cost": 2.50,
    "allows_packstation": true
  }
]
```

**Steps:**
1. As Admin: Import above JSON
2. **Expected:** Success message
3. Check item in database:
   ```sql
   SELECT description, is_physical, shipping_cost, allows_packstation
   FROM items
   WHERE description = 'Test USB Stick';
   ```
4. **Expected:** All fields populated correctly

**✅ Pass Criteria:**
- Valid JSON imports successfully
- All shipping fields stored correctly
- Items appear in shop catalog

---

## 🔍 Database Verification Queries

```sql
-- Check items have shipping fields
SELECT id, description, is_physical, shipping_cost, allows_packstation
FROM items
WHERE is_physical = 1
LIMIT 10;

-- Check orders have shipping_cost
SELECT id, status, total_price, shipping_cost, shipped_at
FROM orders
WHERE status IN ('PAID_AWAITING_SHIPMENT', 'SHIPPED')
ORDER BY id DESC
LIMIT 10;

-- Check encrypted addresses exist
SELECT id, order_id, length(encrypted_address) as encrypted_bytes,
       length(nonce) as nonce_bytes, length(tag) as tag_bytes
FROM shipping_addresses;

-- Check order status flow
SELECT status, COUNT(*) as count
FROM orders
GROUP BY status
ORDER BY count DESC;

-- Verify MAX shipping cost calculation
SELECT o.id, o.total_price, o.shipping_cost,
       GROUP_CONCAT(i.description) as items
FROM orders o
JOIN items i ON i.order_id = o.id
WHERE o.status IN ('PAID_AWAITING_SHIPMENT', 'SHIPPED')
GROUP BY o.id;
```

---

## 🐛 Common Issues & Solutions

### Issue: "Encryption key not found"
**Solution:** Set `ENCRYPTION_SECRET` in .env (exactly 32 bytes hex)
```bash
openssl rand -hex 32
# Copy output to .env: ENCRYPTION_SECRET=<output>
```

### Issue: "Address always shows decrypted in DB"
**Solution:** You're looking at wrong column - check `encrypted_address` (BLOB), not a text field

### Issue: "Shipping cost not added to order"
**Solution:**
- Check `ItemRepository.get_single()` returns items with `shipping_cost` field
- Verify MAX logic: `max(max_shipping_cost, item.shipping_cost)`
- Check logs: "Order creation: Items=X | Shipping=Y (MAX) | Total=Z"

### Issue: "Admin can't see shipping management button"
**Solution:**
- Check `ShippingManagementCallback` is imported in `handlers/admin/admin.py`
- Verify localization key exists: `shipping_management`
- Check admin menu button order (line 41 in admin.py)

### Issue: "FSM state not working - no address prompt"
**Solution:**
- Ensure `FSMContext` is passed to cart handlers
- Check `state` parameter in `checkout_processing(callback, session, state)`
- Verify `shipping_router` is registered in `run.py`

### Issue: "Order goes to PAID instead of PAID_AWAITING_SHIPMENT"
**Solution:**
- Check `has_physical_items = any(item.is_physical for item in items)`
- Verify items actually have `is_physical=True` in database
- Check order completion logic in `services/order.py:176-185`

### Issue: "Shipping cost is SUM instead of MAX"
**Solution:**
- You're on the wrong branch or commit
- This was fixed in commit 8035e57
- Check: `max_shipping_cost = max(max_shipping_cost, sample_item.shipping_cost)`

---

## ✅ Final Checklist

Before marking shipping feature as complete:

- [ ] All 10 test scenarios pass
- [ ] Database queries show correct data structure
- [ ] Encryption key generated and set in .env
- [ ] Test data imported successfully (test_physical_items.json)
- [ ] Admin can decrypt and view addresses
- [ ] Users receive shipped notifications
- [ ] Localization works in both DE and EN
- [ ] No errors in bot logs during testing
- [ ] MAX shipping cost logic verified (not SUM)
- [ ] Mixed carts tested (digital + physical)
- [ ] JSON import validation works

---

## 📊 Expected Test Results Summary

| Test | Scenario | Expected Result |
|------|----------|----------------|
| 1 | Digital-only | No shipping, direct to PAID |
| 2 | Physical-only | Address collected, PAID_AWAITING_SHIPMENT |
| 3 | Mixed cart | MAX shipping, address required, digitals delivered |
| 4 | Multi-physical | MAX shipping (not SUM!) |
| 5 | Packstation warning | ⏳ Not implemented yet |
| 6 | Admin mark shipped | Status→SHIPPED, user notified |
| 7 | Encryption | DB encrypted (BLOB), Admin decrypted (text) |
| 8 | Address validation | Short addresses rejected, retry possible |
| 9 | Order cancellation | Works normally, address kept |
| 10 | JSON validation | Valid imports succeed, fields populated |

---

## 🎯 Success Criteria

✅ **Feature is production-ready when:**
1. All core tests (1-4, 6-10) pass without errors
2. Database migration completes successfully
3. Encryption/decryption works correctly (AES-256-GCM)
4. Admin and user workflows are intuitive
5. No security vulnerabilities (addresses encrypted at rest)
6. Localization complete (DE + EN)
7. Performance acceptable (encryption doesn't slow checkout)
8. MAX shipping cost logic verified and documented

---

## 🚀 Branch Comparison

| Feature | `feature/shipping-management-system` | `feature/shipping-management-v2` |
|---------|-------------------------------------|----------------------------------|
| Shipping cost logic | ✅ MAX | ✅ MAX |
| Address encryption | ✅ AES-256-GCM | ✅ AES-256-GCM |
| Admin management | ✅ Complete | ✅ Complete |
| User notifications | ✅ Complete | ✅ Complete |
| Packstation warning | ✅ Implemented | ⏳ Planned |
| Order detail view | ✅ Implemented | ⏳ Planned |
| Product shipping info | ✅ Implemented | ⏳ Planned |
| Test structure | ✅ Separated | ✅ Docs created |
| Payment validation | ❌ Broken | ✅ Preserved |

**Current Status:** v2 has core features + working payment system. Missing UX enhancements.

---

**Good luck with testing! 🚀**

For requirements and implementation details, see: `docs/SHIPPING_REQUIREMENTS.md`
