# Shipping Management System - Requirements & Specification

**Branch:** `feature/shipping-management-v2`
**Status:** ✅ Implemented
**Date:** 2025-01-23

---

## 1. Core Requirements

### 1.1 Item Model Extensions
- [x] `is_physical` (Boolean) - Identifies physical items requiring shipment
- [x] `shipping_cost` (Float, >= 0) - Shipping cost per item
- [x] `allows_packstation` (Boolean) - Can be shipped to DHL Packstation

### 1.2 Order Model Extensions
- [x] `shipping_cost` (Float, default=0.0) - Total shipping cost for order
- [x] `shipped_at` (DateTime, nullable) - Timestamp when order was marked as shipped

### 1.3 Order Status Extensions
- [x] `PAID_AWAITING_SHIPMENT` - Order paid, contains physical items, awaiting admin shipment
- [x] `SHIPPED` - Physical items have been shipped by admin

### 1.4 Shipping Address Storage
- [x] `ShippingAddress` model with AES-256-GCM encryption
- [x] Order-specific encryption keys using PBKDF2
- [x] Encrypted fields: `encrypted_address`, `nonce`, `tag`
- [x] One-to-one relationship with Order

---

## 2. Business Logic Requirements

### 2.1 Cart Checkout Flow

#### Digital-Only Cart (No Physical Items)
1. User clicks "Checkout"
2. System shows order summary
3. User confirms → Crypto selection
4. User selects crypto → Order created
5. **No shipping address required**

#### Physical-Only Cart
1. User clicks "Checkout"
2. System detects physical items
3. **FSM State triggered:** `ShippingAddressStates.waiting_for_address`
4. User enters shipping address (free text)
5. System validates address (min 10 characters)
6. User confirms address
7. **FSM State:** `ShippingAddressStates.confirm_address`
8. System shows crypto selection
9. User selects crypto → Order created **with encrypted address**
10. **Shipping cost added to order total**

#### Mixed Cart (Digital + Physical)
**Critical:** If cart contains **at least one physical item**, shipping address is required.

1. User clicks "Checkout"
2. System detects mixed items
3. **Shipping address flow triggered** (same as physical-only)
4. Digital items are included in order but don't add shipping cost
5. **Only physical items contribute to shipping cost**
6. User receives digital items immediately after payment
7. Physical items await shipment

**Example:**
- Cart: USB-Stick (physical, 2.50€ shipping) + Windows License (digital, 0€ shipping)
- **Total shipping:** 2.50€
- **Address required:** Yes (because USB-Stick is physical)

### 2.2 Shipping Cost Calculation

```python
total_shipping_cost = 0.0
for cart_item in cart_items:
    sample_item = get_single(cart_item.subcategory_id)
    if sample_item.is_physical:
        total_shipping_cost += sample_item.shipping_cost * cart_item.quantity

order.total_price = items_price + total_shipping_cost
```

**Rules:**
- Shipping cost is **per item**, not per order
- Multiple items → Shipping costs accumulate
- Digital items → `shipping_cost = 0.0`
- Example: 3x USB-Stick (2.50€ each) → 7.50€ total shipping

### 2.3 Order Status Transitions

```
PENDING_PAYMENT
    ↓ (payment received)
    ↓
[Has physical items?]
    ↓ YES → PAID_AWAITING_SHIPMENT → (admin marks shipped) → SHIPPED
    ↓ NO  → PAID (order complete)
```

---

## 3. Admin Requirements

### 3.1 Shipping Management Interface

**Access:** Admin Menu → "📦 Versandverwaltung"

**Level 0: Order List**
- Shows all orders with status `PAID_AWAITING_SHIPMENT`
- Displays: Invoice number, username, total price
- Button per order to view details

**Level 1: Order Details**
- Order ID and customer info (username, telegram ID)
- **Shipping address** (decrypted for admin view)
- **Physical items only** (digital items not shown here)
- Price breakdown: Items + Shipping + Total
- "Mark as Shipped" button

**Level 2: Confirmation**
- Confirm dialog: "Mark order #XXX as shipped?"
- Confirm / Cancel buttons

**Level 3: Execute**
- Set order status to `SHIPPED`
- Set `shipped_at` timestamp
- **Send notification to user**
- Show success message

### 3.2 Admin Notifications

**When:** Physical order is paid (status → `PAID_AWAITING_SHIPMENT`)

**Message:**
```
📦 Neue physische Bestellung!

Bestellung #INV-12345 von Benutzer @username wartet auf Versandbearbeitung.

Bitte überprüfen Sie die Versandverwaltung.
```

---

## 4. User Requirements

### 4.1 Shipping Address Collection

**Trigger:** Cart has physical items + user clicks "Checkout"

**FSM States:**
1. `waiting_for_address` - User must send address as text message
2. `confirm_address` - User confirms address with inline button

**Validation:**
- Minimum 10 characters
- Free-text format (user provides full address)
- No structured validation (name, street, city, etc.)

**Address Format (User Guideline):**
```
📬 Bitte geben Sie Ihre vollständige Versandadresse ein:

Die Adresse sollte enthalten:
- Name
- Straße und Hausnummer
- PLZ und Ort
- Land

Ihre Adresse wird verschlüsselt gespeichert.
```

### 4.2 User Notifications

**Order Shipped:**
```
📦 Ihre Bestellung wurde versendet!

📋 Bestellcode: INV-12345

Ihre Bestellung ist unterwegs. Vielen Dank für Ihren Einkauf!
```

---

## 5. Security Requirements

### 5.1 Address Encryption
- **Algorithm:** AES-256-GCM
- **Key Derivation:** PBKDF2 with order-specific salt
- **Storage:** `encrypted_address` (ciphertext), `nonce` (12 bytes), `tag` (16 bytes)
- **Decryption:** Only possible with `order_id` + `ENCRYPTION_SECRET`

### 5.2 Environment Variable
```bash
ENCRYPTION_SECRET=your-32-byte-secret-key-here
```

**Length:** Must be exactly 32 bytes (256 bits)

---

## 6. Database Schema Changes

### New Fields: `items` Table
```sql
is_physical BOOLEAN NOT NULL DEFAULT FALSE
shipping_cost FLOAT NOT NULL DEFAULT 0.0
allows_packstation BOOLEAN NOT NULL DEFAULT FALSE

CHECK (shipping_cost >= 0)
```

### New Fields: `orders` Table
```sql
shipping_cost FLOAT NOT NULL DEFAULT 0.0
shipped_at TIMESTAMP NULL
```

### New Table: `shipping_addresses`
```sql
CREATE TABLE shipping_addresses (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    encrypted_address BLOB NOT NULL,
    nonce BLOB NOT NULL,
    tag BLOB NOT NULL
)
```

---

## 7. Import/Export Requirements

### JSON Import Format
```json
{
  "category": "Hardware",
  "subcategory": "USB-Sticks",
  "price": 15.99,
  "description": "SanDisk 32GB USB 3.0 Stick",
  "private_data": "Serial: USB-001",
  "is_physical": true,
  "shipping_cost": 2.50,
  "allows_packstation": true
}
```

**Required Fields for Physical Items:**
- `is_physical: true`
- `shipping_cost: <float>` (must be > 0 for physical items)
- `allows_packstation: <boolean>`

**Digital Items:**
- `is_physical: false`
- `shipping_cost: 0.0`
- `allows_packstation: false`

---

## 8. Edge Cases & Validation

### 8.1 Empty Shipping Address
- **Validation:** Min 10 characters
- **Error:** "Adresse zu kurz! Bitte vollständige Adresse eingeben."
- **User can retry:** System stays in FSM state

### 8.2 FSM State Cleanup
- **After order creation:** FSM state cleared with `state.clear()`
- **After cart cancellation:** FSM state cleared

### 8.3 Mixed Cart Shipping Cost
- **Only physical items contribute to shipping**
- Digital items have `shipping_cost = 0.0`
- Example: USB (2.50€) + License (0€) = 2.50€ total shipping

### 8.4 Multiple Physical Items
- **Shipping costs accumulate per item**
- Example: 2x USB (2.50€ each) + 1x T-Shirt (3.99€) = 8.99€ shipping

### 8.5 Packstation Restrictions
- **`allows_packstation = false`:** Cannot be shipped to Packstation (e.g., large items)
- **Future enhancement:** Check user address for "Packstation" keyword and validate against item restrictions

---

## 9. Localization Keys

### Admin (de.json / en.json)
```json
"shipping_management": "📦 Versandverwaltung",
"awaiting_shipment_orders": "📦 <b>Bestellungen zur Versandvorbereitung:</b>",
"no_orders_awaiting_shipment": "✅ <b>Keine Bestellungen warten auf Versand.</b>",
"order_details_header": "📦 <b>Bestelldetails #{order_id}</b>",
"order_user": "👤 <b>Kunde:</b> {username} (ID: {user_id})",
"order_shipping_address": "📬 <b>Versandadresse:</b>\n{address}",
"order_items_list": "📦 <b>Versandartikel:</b>\n{items}",
"mark_as_shipped": "✅ Als versendet markieren",
"confirm_mark_shipped": "❓ <b>Möchten Sie die Bestellung #{order_id} wirklich als versendet markieren?</b>",
"order_marked_shipped": "✅ <b>Bestellung #{order_id} wurde als versendet markiert!</b>\n\nDer Kunde wurde benachrichtigt.",
"order_awaiting_shipment_notification": "📦 <b>Neue physische Bestellung!</b>\n\nBestellung #{invoice_number} von Benutzer {username} wartet auf Versandbearbeitung.\n\nBitte überprüfen Sie die Versandverwaltung."
```

### User (de.json / en.json)
```json
"shipping_address_request": "📬 <b>Bitte geben Sie Ihre vollständige Versandadresse ein:</b>\n\nDie Adresse sollte enthalten:\n- Name\n- Straße und Hausnummer\n- PLZ und Ort\n- Land\n\n<i>Ihre Adresse wird verschlüsselt gespeichert.</i>",
"shipping_address_invalid": "⚠️ <b>Die Adresse ist zu kurz!</b>\n\nBitte geben Sie eine vollständige Versandadresse ein (mindestens 10 Zeichen).",
"shipping_address_confirm": "📬 <b>Bitte bestätigen Sie Ihre Versandadresse:</b>\n\n{address}\n\n<i>Ist diese Adresse korrekt?</i>",
"order_shipped_notification": "📦 <b>Ihre Bestellung wurde versendet!</b>\n\n📋 Bestellcode: {invoice_number}\n\nIhre Bestellung ist unterwegs. Vielen Dank für Ihren Einkauf!"
```

---

## 10. File Structure

```
models/
  ├── item.py (+ is_physical, shipping_cost, allows_packstation)
  ├── order.py (+ shipping_cost, shipped_at)
  └── shipping_address.py (NEW)

enums/
  └── order_status.py (+ PAID_AWAITING_SHIPMENT, SHIPPED)

services/
  ├── shipping.py (NEW - encryption, address management)
  └── order.py (+ shipping cost calculation, status logic)

handlers/
  ├── user/
  │   ├── shipping_handlers.py (NEW - address input)
  │   ├── shipping_states.py (NEW - FSM states)
  │   └── cart.py (+ level 6 handler for address confirmation)
  └── admin/
      └── shipping_management.py (NEW - 4-level workflow)

repositories/
  └── order.py (+ get_orders_awaiting_shipment, get_by_id_with_items)

callbacks.py (+ ShippingManagementCallback)
run.py (+ shipping_router, shipping_management_router)
```

---

## 11. Testing Requirements

See: `SHIPPING_TEST_GUIDE.md`

---

## 12. Future Enhancements

### 12.1 Packstation Validation
- Parse user address for "Packstation" keyword
- Check if all physical items allow Packstation
- Reject order if mismatch

### 12.2 Shipping Cost Rules
- Per-subcategory shipping cost (not per-item)
- Combined shipping discounts (e.g., 2+ items → reduced shipping)
- Free shipping threshold (e.g., > 50€ order value)

### 12.3 Tracking Numbers
- Add `tracking_number` field to Order
- Display tracking link in user notification

### 12.4 Multiple Shipments
- Split orders into multiple shipments
- Track partial shipments

### 12.5 Shipping Providers
- Select shipping provider (DHL, DPD, Hermes)
- Provider-specific address validation

---

## 13. Migration Checklist

When deploying to production:

1. **Run database migration** to add new columns
2. **Set `ENCRYPTION_SECRET`** in .env (32-byte secret)
3. **Import test data** to verify shipping cost calculations
4. **Test complete flow:**
   - Digital-only order
   - Physical-only order
   - Mixed order
   - Admin shipment workflow
5. **Verify notifications:**
   - Admin receives notification for physical orders
   - User receives notification when shipped
6. **Check encryption:**
   - Addresses are encrypted in database
   - Decryption works in admin panel

---

## 14. Known Limitations

1. **No structured address validation** (name, street, city separate)
2. **No Packstation address parsing** (future enhancement)
3. **Shipping cost per item** (not optimized for bulk shipments)
4. **No tracking numbers** (future enhancement)
5. **No shipping cost preview** in product view (future enhancement)

---

## Status Summary

✅ **Implemented:** All core requirements
✅ **Tested:** Unit tests pending (see test guide)
✅ **Documented:** This file + test guide
⏳ **Migration:** Pending production deployment
