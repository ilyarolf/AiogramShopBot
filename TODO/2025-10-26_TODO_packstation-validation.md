# Packstation Address Validation

**Date:** 2025-10-26
**Priority:** Medium
**Estimated Effort:** Medium (2-3 hours)

---

## Description
Implement intelligent validation for Packstation addresses. Items with `supports_packstation=False` cannot be shipped to Packstations, but if the order contains AT LEAST ONE packstation-capable item, all items can be shipped (they'll be packed together in a packstation-compatible package).

## User Story
As a customer ordering to a Packstation, I want to be informed during checkout if my order can be shipped there, so I can provide an alternative address if needed.

## Business Logic

### Rule: "One Packstation Item = All Items Can Ship"
If an order contains:
- **ANY item with `supports_packstation=True`**: All items in the order can ship to Packstation
- **ALL items with `supports_packstation=False`**: Order CANNOT ship to Packstation

**Rationale:** Large items can be packed together with packstation-capable items in one large package suitable for Packstation delivery.

### Examples

**Example 1: Mixed Order (Allowed)**
- Item A: USB-Stick (`supports_packstation=True`)
- Item B: Large Textbook (`supports_packstation=False`)
- **Result:** ✅ Can ship to Packstation (because USB-Stick is packstation-capable)

**Example 2: All Non-Packstation (Blocked)**
- Item A: Large Box (`supports_packstation=False`)
- Item B: Heavy Book (`supports_packstation=False`)
- **Result:** ❌ Cannot ship to Packstation

**Example 3: All Packstation (Allowed)**
- Item A: USB-Stick (`supports_packstation=True`)
- Item B: SD-Card (`supports_packstation=True`)
- **Result:** ✅ Can ship to Packstation

## Technical Implementation

### 1. Address Pattern Detection

Add to `services/shipping.py`:

```python
import re

PACKSTATION_KEYWORDS = [
    r'\bpackstation\b',
    r'\bpostfiliale\b',
    r'\bpaketstation\b',
    r'\bpakstation\b',  # Common typo
    r'\bpack\s*station\b',
    r'\bpost\s*filiale\b'
]

def is_packstation_address(address: str) -> bool:
    """
    Detects if an address is a Packstation/Postfiliale address.

    Args:
        address: User-provided shipping address (decrypted)

    Returns:
        True if address contains Packstation keywords, False otherwise
    """
    address_lower = address.lower()

    for pattern in PACKSTATION_KEYWORDS:
        if re.search(pattern, address_lower):
            return True

    return False
```

### 2. Order Packstation Capability Check

Add to `services/order.py`:

```python
async def check_order_supports_packstation(
    order_items: list,
    session: AsyncSession | Session
) -> bool:
    """
    Checks if order can be shipped to Packstation.

    Logic: If ANY item in the order supports Packstation, then ALL items can ship
    (because they'll be packed together in a packstation-compatible package).

    Args:
        order_items: List of Item DTOs or Item models
        session: DB session

    Returns:
        True if order can ship to Packstation, False otherwise
    """
    # Check if ANY item supports packstation
    for item in order_items:
        if item.supports_packstation:
            return True  # One packstation item = all can ship

    return False  # No packstation items = cannot ship to packstation
```

### 3. Validation During Address Confirmation

Update `services/order.py` → `confirm_shipping_address()`:

```python
async def confirm_shipping_address(
    callback: CallbackQuery,
    session: AsyncSession | Session,
    state: FSMContext
) -> tuple[str, InlineKeyboardBuilder]:
    """
    Level 1: Confirm Shipping Address

    - Validate if address is Packstation
    - Check if order items support Packstation
    - Block order if Packstation address but no packstation-capable items
    """
    # ... existing code to get order_id and address from FSM state ...

    # Get order items
    order_items = await ItemRepository.get_by_order_id(order_id, session)

    # Check if address is Packstation
    is_packstation = ShippingService.is_packstation_address(address)

    if is_packstation:
        # Check if order supports Packstation
        can_ship_to_packstation = await check_order_supports_packstation(order_items, session)

        if not can_ship_to_packstation:
            # BLOCK: Packstation address but no packstation-capable items
            message_text = Localizator.get_text(BotEntity.USER, "packstation_not_supported").format(
                address=address
            )

            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "reenter_address"),
                callback_data=OrderCallback.create(level=2, order_id=order_id)  # Re-enter address
            )
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                callback_data=OrderCallback.create(level=4, order_id=order_id)  # Cancel order
            )

            return message_text, kb_builder

    # ... existing code to save address and continue ...
```

### 4. Localization Keys

Add to `l10n/de.json`:
```json
"packstation_not_supported": "⚠️ <b>Packstation-Lieferung nicht möglich</b>\n\n📦 Ihre Bestellung enthält Artikel, die nicht an eine Packstation geliefert werden können.\n\n<b>Ihre Adresse:</b>\n{address}\n\n<i>Bitte geben Sie eine reguläre Lieferadresse ein oder passen Sie Ihre Bestellung an.</i>",
"reenter_address": "🔄 Andere Adresse eingeben"
```

Add to `l10n/en.json`:
```json
"packstation_not_supported": "⚠️ <b>Packstation delivery not possible</b>\n\n📦 Your order contains items that cannot be delivered to a Packstation.\n\n<b>Your address:</b>\n{address}\n\n<i>Please provide a regular delivery address or adjust your order.</i>",
"reenter_address": "🔄 Enter different address"
```

### 5. Admin View Enhancement

Update `handlers/admin/shipping_management.py` → `show_order_details()`:

```python
# Show Packstation indicator if applicable
if shipping_address:
    is_packstation = ShippingService.is_packstation_address(shipping_address)
    if is_packstation:
        message_text += "\n📦 <b>Packstation-Lieferung</b>\n"
```

## Testing Checklist

- [ ] **T1: Packstation with compatible items**
  - Add packstation-capable item to cart
  - Enter Packstation address
  - Verify order proceeds without error

- [ ] **T2: Packstation with incompatible items**
  - Add ONLY non-packstation items to cart
  - Enter Packstation address
  - Verify error message displayed
  - Verify "Re-enter address" button works

- [ ] **T3: Mixed order to Packstation**
  - Add one packstation-capable + one non-packstation item
  - Enter Packstation address
  - Verify order proceeds (because one item is packstation-capable)

- [ ] **T4: Non-Packstation address**
  - Add any items
  - Enter regular address (no "Packstation" keyword)
  - Verify no validation error regardless of item types

- [ ] **T5: Keyword detection**
  - Test addresses: "Packstation 123", "Postfiliale 456", "Paketstation 789"
  - Verify all detected as Packstation addresses

- [ ] **T6: Case insensitivity**
  - Test: "PACKSTATION", "PackStation", "packstation"
  - Verify all detected correctly

## Database Schema Check

Verify `items` table has column (migration already exists):
```sql
ALTER TABLE items ADD COLUMN supports_packstation BOOLEAN NOT NULL DEFAULT FALSE;
```

## Edge Cases

1. **Typos**: "Pakstation", "Pack Station" → Should still detect
2. **Mixed case**: "PACKSTATION 123" → Should detect
3. **Substring match**: "My Packstation" → Should detect
4. **False positives**: "Backstreet" → Should NOT detect (word boundary check)

## Notes

- This implements the "one packstation item = all can ship" business rule
- Alternative approaches (stricter rules) were considered but rejected for business reasons
- Admin can still manually override by contacting customer if needed
- Consider adding admin note field for special shipping instructions

---

**Status:** Planned
**Blocked by:** None
**Related:** SHIPPING_REQUIREMENTS.md (Section 12.1)
