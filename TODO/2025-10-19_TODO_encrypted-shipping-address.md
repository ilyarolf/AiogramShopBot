# Encrypted Shipping Address Submission

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** High (3-4 hours)

---

## Description
Implement a secure system for users to submit shipping addresses after successful payment. Offers two encryption options: server-side encryption (user-friendly) or client-side encryption via external web tool (maximum security). All shipping data is encrypted with admin's GPG public key and stored encrypted in database.

## User Story
As a privacy-conscious customer, I want to submit my shipping address in an encrypted form, so that only the shop administrator can read it and my personal data remains confidential.

## Acceptance Criteria
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
  - Bot sends link to external encryption tool
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

## Technical Notes

### Database Changes
```python
# models/order.py - ADD FIELDS
shipping_address_encrypted = Column(Text, nullable=True)
shipping_address_submitted_at = Column(DateTime, nullable=True)
```

### FSM States (Option A)
```python
class ShippingAddressStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_street = State()
    waiting_for_city = State()
    waiting_for_postal_code = State()
    waiting_for_country = State()
```

### Server-Side Encryption
Create `services/encryption.py` using `python-gnupg` library to encrypt shipping data with admin's public key.

### External Web Tool (Option B)
Static HTML page with OpenPGP.js for client-side encryption. Hosted at `https://yourdomain.com/encrypt-shipping`.

## Implementation Order
1. Add database fields to Order model
2. Create `services/encryption.py` with GPG encryption
3. Implement FSM-based address input (Option A)
4. Create external web tool (Option B)
5. Add "Submit Shipping Address" button after payment
6. Implement admin view for encrypted address
7. Add validation (order cannot ship without address)
8. Add localization keys (DE/EN)
9. Testing: Both encryption methods, admin decryption

## Dependencies
- Requires `python-gnupg` library
- Requires GPG public key file
- External web tool requires static file hosting
- FSM implementation required

---

**Status:** Planned