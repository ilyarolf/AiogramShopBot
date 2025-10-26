# Payment Validation & Multi-Source Payment - Technical Design

**Version:** 1.0
**Date:** 2025-10-19
**Branch:** `feature/payment-amount-validation`

---

## Executive Summary

This document describes the technical implementation of a comprehensive payment validation system with support for:
- Exact payment validation with configurable overpayment tolerance
- **Zero tolerance for underpayment** - any amount below required triggers underpayment flow
- Overpayment handling with automatic wallet credit
- Underpayment retry mechanism (one-time extension)
- Multi-source payments (Wallet + Crypto Invoice)
- Late payment handling with penalty fees
- Admin goodwill mechanisms

**Key Requirements:**
- ✅ **Absolute zero tolerance for underpayment** - `paid < required` always triggers underpayment flow
- ✅ 0.1% overpayment tolerance (configurable) - small overpayments forfeit to shop
- ✅ One retry allowed for underpayment with 30-minute extension
- ✅ 5% penalty fee for late/failed payments (configurable)
- ✅ Automatic wallet usage during checkout
- ✅ Exchange rate locked at order creation

---

## 1. Payment Scenarios - Detailed Flow

### Scenario A: Exact Payment ✅
**Condition:** `paid == required` (exactly matching)

**Flow:**
1. Webhook receives payment confirmation
2. Validate currency matches invoice
3. Validate amount exactly matches required
4. Complete order → Status: `PAID`
5. Mark items as sold
6. Send payment confirmation notification to user

**Database Changes:**
- Order: `status` → `PAID`, `paid_at` → now()
- Items: `is_sold` → true

**Example:**
- Required: 0.00100000 BTC
- Paid: 0.00100000 BTC
- Result: Order completed ✅

---

### Scenario B: Minor Overpayment (≤0.1%) 💰
**Condition:** `required < paid <= required * (1 + tolerance_percent/100)`

Where `tolerance_percent` = 0.1 (default, configurable)

**Flow:**
1. Validate payment exceeds required
2. Calculate excess: `excess = paid - required`
3. Check if excess within tolerance threshold
4. Complete order normally
5. **No wallet credit** (amount forfeits to shop)
6. Send payment confirmation (no mention of overpayment)

**Example:**
- Required: 0.00100000 BTC
- Tolerance: 0.1% → threshold = 0.00100100 BTC
- Paid: 0.00100099 BTC
- Excess: 0.00000099 BTC (0.099%)
- Result: Order completed, excess forfeits ✅

**Note:** User is NOT notified about the forfeited amount.

---

### Scenario C: Significant Overpayment (>0.1%) 💰
**Condition:** `paid > required * (1 + tolerance_percent/100)`

**Flow:**
1. Validate payment significantly exceeds required
2. Calculate excess: `excess = paid - required`
3. Complete order → Status: `PAID`
4. Calculate fiat value of excess using original exchange rate
5. Credit excess to user wallet (Fiat equivalent)
6. Create `PaymentTransaction` record
7. Send notification with wallet credit info

**Example:**
- Required: €10.00 (0.00025 BTC at order creation)
- Tolerance: 0.1% → threshold = 0.00025025 BTC
- Paid: 0.00030 BTC
- Excess: 0.00005 BTC
- Wallet credit: `(0.00005 / 0.00025) * €10.00 = €2.00`

**Notification:**
```
✅ Zahlung bestätigt!
📋 Bestellcode: #12345
💰 Gezahlt: €10.00

Du hast €2.00 zu viel gezahlt.
Der Überschuss wurde deinem Wallet gutgeschrieben.

Aktuelles Wallet-Guthaben: €7.00
```

---

### Scenario D: Underpayment - First Attempt 🔄
**Condition:** `paid < required` (ANY amount below required)

**Critical:** There is **ZERO tolerance** for underpayment. Even 0.00000001 BTC below required triggers this flow.

**Flow:**
1. Validate payment is insufficient
2. Calculate remaining: `remaining = required - paid`
3. Create `PaymentTransaction` record for partial payment
4. Update Order: `status` → `PENDING_PAYMENT_PARTIAL`, `retry_count` → 1
5. Extend timeout: `expires_at` → now() + 30 minutes, store `original_expires_at`
6. Create new Invoice for remaining amount:
   - `is_partial_payment` → true
   - `parent_invoice_id` → original invoice ID
   - `payment_attempt` → 2
   - Generate new crypto address via KryptoExpress
7. Send notification to user with new payment details

**Example:**
- Required: €15.00 (0.00030000 BTC)
- Paid: 0.00029999 BTC (€14.9995)
- Remaining: 0.00000001 BTC (€0.0005)
- Result: Underpayment flow triggered ⚠️

**Another Example:**
- Required: €15.00 (0.00030 BTC)
- Paid: 0.00025 BTC (€12.50)
- Remaining: 0.00005 BTC (€2.50)

**Notification:**
```
⚠️ Zu wenig gezahlt!

Eingezahlt: 0.00025 BTC (€12.50)
Gefordert: 0.00030 BTC (€15.00)
Offen: 0.00005 BTC (€2.50)

📬 Neue Zahlungsadresse:
bc1q...

⏰ Verlängerte Frist: 30 Minuten
Neue Deadline: 14:45 Uhr
```

**Database Changes:**
- Order: `status` → `PENDING_PAYMENT_PARTIAL`, `retry_count` → 1, `expires_at` → extended, `total_paid_crypto` → 0.00025
- Invoice (new): parent_invoice_id, payment_amount_crypto = 0.00005
- PaymentTransaction: Record 0.00025 BTC payment

---

### Scenario E: Underpayment - Second Attempt (Still Insufficient) ❌
**Condition:** After first underpayment, second payment also `< remaining`

**Flow:**
1. Validate second payment insufficient
2. Cancel order → Status: `CANCELLED_UNDERPAYMENT`
3. Release reserved stock
4. Calculate total paid: `total = first_payment + second_payment`
5. Calculate fiat equivalent using original exchange rate
6. Calculate wallet credit with penalty: `credit = total_fiat * (1 - penalty_percent/100)`
7. Add credit to user wallet
8. Create `PaymentTransaction` records for both payments
9. Send notification to user
10. Send notification to admin for review

**Example:**
- Required: €15.00 (0.00030 BTC)
- First payment: 0.00025 BTC (€12.50)
- Second payment: 0.00003 BTC (€1.50)
- Total paid: 0.00028 BTC (€14.00)
- Penalty: €0.70 (5%)
- Wallet credit: €13.30

**User Notification:**
```
❌ Zahlung fehlgeschlagen

Deine Bestellung wurde nach mehrfacher Unterzahlung storniert.

Eingezahltes Guthaben: €14.00
Bearbeitungsgebühr: -€0.70 (5%)
Wallet-Gutschrift: €13.30

Aktuelles Wallet-Guthaben: €13.30
```

**Admin Notification:**
```
⚠️ Order #12345 - Mehrfache Unterzahlung

User: @username (ID: 123456)
Gefordert: 0.00030 BTC (€15.00)
Erhalten: 0.00028 BTC (€14.00)
  • 1. Zahlung: 0.00025 BTC
  • 2. Zahlung: 0.00003 BTC

Wallet-Gutschrift: €13.30 (nach 5% Gebühr)
Status: CANCELLED_UNDERPAYMENT
```

---

### Scenario F: Late Payment (After Timeout) ⏰
**Condition:** Payment arrives after `order.expires_at`

**Flow:**
1. Check if order exists and status is `TIMEOUT` or `PENDING_PAYMENT`
2. Order already cancelled by timeout job
3. Calculate fiat equivalent using original exchange rate
4. Calculate wallet credit with penalty: `credit = paid_fiat * (1 - penalty_percent/100)`
5. Add to user wallet
6. Create `PaymentTransaction` record
7. Send notification to user

**Example:**
- Order expired at 14:30
- Payment received at 14:35
- Amount: 0.00030 BTC (= €15.00 at original rate)
- Penalty: €0.75 (5%)
- Wallet credit: €14.25

**User Notification:**
```
⏰ Verspätete Zahlung

Deine Zahlung ist nach Ablauf der Zahlungsfrist eingegangen.
Die Bestellung wurde bereits storniert.

Gezahlt: 0.00030 BTC (€15.00)
Bearbeitungsgebühr: -€0.75 (5%)
Wallet-Gutschrift: €14.25

💡 Bei nachweisbarer Blockchain-Verzögerung kontaktiere bitte den Support.
```

---

## 2. Payment Validation Logic

### 2.1 Core Validation Algorithm

```python
def validate_payment(paid: float, required: float, tolerance_percent: float = 0.1):
    """
    Validate payment amount.

    Rules:
    - paid < required: UNDERPAYMENT (ZERO tolerance!)
    - paid == required: EXACT_MATCH
    - required < paid <= required * (1 + tolerance/100): MINOR_OVERPAYMENT (forfeits)
    - paid > required * (1 + tolerance/100): OVERPAYMENT (wallet credit)
    """

    # CRITICAL: Underpayment check comes FIRST
    if paid < required:
        return UNDERPAYMENT

    # Calculate tolerance threshold
    tolerance_multiplier = 1 + (tolerance_percent / 100)
    tolerance_threshold = required * tolerance_multiplier

    # Exact match
    if paid == required:
        return EXACT_MATCH

    # Minor overpayment (within tolerance)
    if paid <= tolerance_threshold:
        return MINOR_OVERPAYMENT

    # Significant overpayment
    return OVERPAYMENT
```

### 2.2 Validation Examples

| Required | Paid | Tolerance | Result | Wallet Credit |
|----------|------|-----------|--------|---------------|
| 0.00100000 | 0.00099999 | 0.1% | **UNDERPAYMENT** | No (Retry flow) |
| 0.00100000 | 0.00100000 | 0.1% | EXACT_MATCH | No |
| 0.00100000 | 0.00100050 | 0.1% | MINOR_OVERPAYMENT | No (Forfeits) |
| 0.00100000 | 0.00100100 | 0.1% | MINOR_OVERPAYMENT | No (Forfeits) |
| 0.00100000 | 0.00100101 | 0.1% | OVERPAYMENT | Yes (0.00000101) |
| 0.00100000 | 0.00110000 | 0.1% | OVERPAYMENT | Yes (0.00010000) |

**Key Insight:** The tolerance is ONLY for overpayment, NOT underpayment!

---

## 3. Database Schema Extensions

### 3.1 New Enums

#### OrderStatus
```python
# enums/order_status.py
class OrderStatus(Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PENDING_PAYMENT_PARTIAL = "PENDING_PAYMENT_PARTIAL"  # NEW - after 1st underpayment
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"
    CANCELLED_BY_ADMIN = "CANCELLED_BY_ADMIN"
    CANCELLED_UNDERPAYMENT = "CANCELLED_UNDERPAYMENT"  # NEW - after 2nd underpayment
    TIMEOUT = "TIMEOUT"
```

#### PaymentValidationResult
```python
# enums/payment_validation.py (NEW FILE)
from enum import Enum

class PaymentValidationResult(Enum):
    EXACT_MATCH = "EXACT_MATCH"              # Paid exactly required
    MINOR_OVERPAYMENT = "MINOR_OVERPAYMENT"  # 0 < overpayment ≤ tolerance (forfeits)
    OVERPAYMENT = "OVERPAYMENT"              # overpayment > tolerance (wallet credit)
    UNDERPAYMENT = "UNDERPAYMENT"            # paid < required (ZERO tolerance)
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"  # Wrong crypto
```

### 3.2 Extended Models

#### Order Model
```python
# models/order.py
class Order(Base):
    __tablename__ = 'orders'

    # Existing fields...
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT)
    total_price = Column(Float, nullable=False)
    currency = Column(SQLEnum(Currency), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # NEW FIELDS
    total_paid_crypto = Column(Float, default=0.0)  # Sum of partial payments in crypto
    retry_count = Column(Integer, default=0)  # Underpayment retry counter (0 or 1)
    original_expires_at = Column(DateTime, nullable=True)  # Original deadline before extension

    # Relations
    user = relationship('User', backref='orders')
    items = relationship('Item', backref='order')
    invoice = relationship('Invoice', back_populates='order', uselist=False)
```

#### Invoice Model
```python
# models/invoice.py
class Invoice(Base):
    __tablename__ = 'invoices'

    # Existing fields...
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    invoice_number = Column(String, unique=True)
    payment_address = Column(String)
    payment_amount_crypto = Column(Float)
    payment_crypto_currency = Column(SQLEnum(Cryptocurrency))
    payment_processing_id = Column(Integer)
    fiat_amount = Column(Float)
    fiat_currency = Column(SQLEnum(Currency))

    # NEW FIELDS for partial payments
    is_partial_payment = Column(Boolean, default=False)
    parent_invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)
    actual_paid_amount_crypto = Column(Float, nullable=True)  # What was actually received
    payment_attempt = Column(Integer, default=1)  # 1st or 2nd payment attempt

    # Relations
    order = relationship('Order', back_populates='invoice')
    parent_invoice = relationship('Invoice', remote_side=[id], backref='partial_invoices')
```

### 3.3 New Table: PaymentTransaction

```python
# models/payment_transaction.py (NEW FILE)
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Boolean, func, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from models.base import Base


class PaymentTransaction(Base):
    """
    Tracks individual payment transactions for an order.
    Used for audit trail and multi-payment scenarios.
    """
    __tablename__ = 'payment_transactions'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)

    # Transaction details
    crypto_amount = Column(Float, nullable=False)
    crypto_currency = Column(SQLEnum(Cryptocurrency), nullable=False)
    fiat_amount = Column(Float, nullable=False)  # Calculated using invoice exchange rate
    fiat_currency = Column(SQLEnum(Currency), nullable=False)

    # Payment source
    transaction_hash = Column(String, nullable=True)
    payment_address = Column(String, nullable=False)
    payment_processing_id = Column(Integer, nullable=False)

    # Classification
    is_overpayment = Column(Boolean, default=False)
    is_underpayment = Column(Boolean, default=False)
    is_late_payment = Column(Boolean, default=False)

    # Penalty tracking
    penalty_applied = Column(Boolean, default=False)
    penalty_percent = Column(Float, default=0.0)

    # Wallet credit
    wallet_credit_amount = Column(Float, nullable=True)  # Amount credited to wallet (if any)

    # Metadata
    received_at = Column(DateTime, default=func.now())

    # Relations
    order = relationship('Order', backref='payment_transactions')
    invoice = relationship('Invoice', backref='payment_transactions')
```

---

## 4. Configuration Parameters

### 4.1 Environment Variables (.env)

```bash
# Payment Validation Settings
PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT=0.1  # Overpayment tolerance (0.1 = 0.1%)
PAYMENT_UNDERPAYMENT_RETRY_ENABLED=true    # Allow one retry for underpayment
PAYMENT_UNDERPAYMENT_RETRY_TIMEOUT_MINUTES=30  # Extension time
PAYMENT_UNDERPAYMENT_PENALTY_PERCENT=5     # Penalty fee for 2nd underpayment (0 = disabled)
PAYMENT_LATE_PENALTY_PERCENT=5             # Late payment penalty
```

### 4.2 Config Module (config.py)

```python
# config.py additions
import os

# Payment Validation
PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT = float(os.getenv('PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT', '0.1'))
PAYMENT_UNDERPAYMENT_RETRY_ENABLED = os.getenv('PAYMENT_UNDERPAYMENT_RETRY_ENABLED', 'true').lower() == 'true'
PAYMENT_UNDERPAYMENT_RETRY_TIMEOUT_MINUTES = int(os.getenv('PAYMENT_UNDERPAYMENT_RETRY_TIMEOUT_MINUTES', '30'))
PAYMENT_UNDERPAYMENT_PENALTY_PERCENT = float(os.getenv('PAYMENT_UNDERPAYMENT_PENALTY_PERCENT', '5'))
PAYMENT_LATE_PENALTY_PERCENT = float(os.getenv('PAYMENT_LATE_PENALTY_PERCENT', '5'))
```

---

## 5. Service Layer - Payment Validator

### 5.1 PaymentValidator Service

```python
# services/payment_validator.py (NEW FILE)
from enums.cryptocurrency import Cryptocurrency
from enums.payment_validation import PaymentValidationResult
import config


class PaymentValidator:
    """Validates payment amounts against invoice requirements"""

    @staticmethod
    def validate_payment(
        paid_crypto: float,
        required_crypto: float,
        paid_currency: Cryptocurrency,
        required_currency: Cryptocurrency
    ) -> PaymentValidationResult:
        """
        Validate a payment amount against requirements.

        CRITICAL: Zero tolerance for underpayment!
        Tolerance only applies to overpayment.

        Returns:
        - CURRENCY_MISMATCH: Wrong cryptocurrency used
        - UNDERPAYMENT: Payment below required (ANY amount, zero tolerance!)
        - EXACT_MATCH: Payment exactly matches required
        - MINOR_OVERPAYMENT: 0 < overpayment <= tolerance (forfeits)
        - OVERPAYMENT: overpayment > tolerance (wallet credit)
        """
        # Currency check
        if paid_currency != required_currency:
            return PaymentValidationResult.CURRENCY_MISMATCH

        # CRITICAL: Underpayment check - ZERO tolerance
        if paid_crypto < required_crypto:
            return PaymentValidationResult.UNDERPAYMENT

        # Exact match
        if paid_crypto == required_crypto:
            return PaymentValidationResult.EXACT_MATCH

        # Calculate tolerance threshold for overpayment
        tolerance_multiplier = 1 + (config.PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT / 100)
        tolerance_threshold = required_crypto * tolerance_multiplier

        # Minor overpayment (within tolerance - forfeits)
        if paid_crypto <= tolerance_threshold:
            return PaymentValidationResult.MINOR_OVERPAYMENT

        # Significant overpayment (wallet credit)
        return PaymentValidationResult.OVERPAYMENT

    @staticmethod
    def calculate_fiat_from_crypto(
        crypto_amount: float,
        crypto_currency: Cryptocurrency,
        invoice_fiat_amount: float,
        invoice_crypto_amount: float
    ) -> float:
        """
        Calculate fiat equivalent using the exchange rate from invoice creation.

        Formula: (paid_crypto / invoice_crypto) * invoice_fiat

        This ensures we always use the LOCKED exchange rate from order creation,
        not current market rates.
        """
        if invoice_crypto_amount == 0:
            raise ValueError("Invoice crypto amount cannot be zero")

        ratio = crypto_amount / invoice_crypto_amount
        return ratio * invoice_fiat_amount

    @staticmethod
    def apply_penalty(amount: float, penalty_percent: float) -> tuple[float, float]:
        """
        Apply penalty fee to an amount.

        Returns: (amount_after_penalty, penalty_amount)

        Example: apply_penalty(100, 5) → (95.0, 5.0)
        """
        penalty_amount = amount * (penalty_percent / 100)
        amount_after_penalty = amount - penalty_amount
        return amount_after_penalty, penalty_amount
```

---

## 6. Implementation Phases

### Phase 1: Core Validation & Database (Priority: CRITICAL)
**Security Fix - Prevent underpayment acceptance**

**Estimated Time:** 2-3 days

**Tasks:**
1. Create new enum: `PaymentValidationResult`
2. Extend `OrderStatus` enum with new states
3. Add new fields to `Order` model
4. Add new fields to `Invoice` model
5. Create `PaymentTransaction` model
6. Create database migration script
7. Implement `PaymentValidator` service with unit tests
8. Add config parameters to `.env.template`

**Acceptance Criteria:**
- ✅ Database schema updated successfully
- ✅ Migration tested on copy of production DB
- ✅ PaymentValidator correctly identifies all scenarios
- ✅ Unit tests: 100% coverage on PaymentValidator

**Deliverables:**
- Migration script: `migrations/add_payment_validation_fields.py`
- Service: `services/payment_validator.py`
- Tests: `tests/unit/test_payment_validator.py`

---

### Phase 2: Exact Payment & Minor Overpayment
**MVP: Secure basic payment validation**

**Estimated Time:** 2 days

**Tasks:**
1. Update `_handle_order_payment()` in `processing/processing.py`
2. Add currency mismatch check
3. Implement `_handle_exact_payment()`
4. Implement `_handle_minor_overpayment()`
5. Add comprehensive logging
6. Update existing payment confirmation notification

**Acceptance Criteria:**
- ✅ Exact payments (paid == required) complete order
- ✅ Minor overpayments (≤0.1%) complete order, forfeit silently
- ✅ Currency mismatches are rejected
- ✅ All scenarios logged with emoji indicators

**Deliverables:**
- Updated: `processing/processing.py`
- Tests: `tests/integration/test_exact_payment.py`

---

### Phase 3: Significant Overpayment → Wallet
**Feature: Credit excess to wallet**

**Estimated Time:** 2-3 days

**Tasks:**
1. Implement `_handle_overpayment()`
2. Create `PaymentTransactionService.create_transaction()`
3. Add localization keys: `order_payment_confirmed_with_overpayment` (DE/EN)
4. Implement notification method in `NotificationService`
5. Create webhook simulation test script

**Acceptance Criteria:**
- ✅ Overpayments >0.1% credited to wallet
- ✅ Fiat calculation uses original exchange rate
- ✅ User receives notification with wallet balance
- ✅ PaymentTransaction record created

**Deliverables:**
- Service: `services/payment_transaction.py`
- Localization: Updated `l10n/de.json` & `l10n/en.json`
- Updated: `services/notification.py`
- Tests: `tests/integration/test_overpayment.py`

---

### Phase 4: First Underpayment with Retry
**Feature: One-time retry with 30min extension**

**Estimated Time:** 3-4 days

**Tasks:**
1. Implement `_handle_first_underpayment()`
2. Create `InvoiceService.create_partial_invoice()`
3. Integrate with KryptoExpress API for new address
4. Implement timeout extension logic
5. Add localization keys: `payment_underpaid_retry` (DE/EN)
6. Implement notification
7. Update timeout job to respect `original_expires_at`

**Acceptance Criteria:**
- ✅ First underpayment creates new partial invoice
- ✅ Timeout extended by 30 minutes from notification time
- ✅ User receives new payment address
- ✅ Order status: `PENDING_PAYMENT_PARTIAL`
- ✅ PaymentTransaction records partial payment

**Deliverables:**
- Updated: `services/invoice.py`
- Updated: `jobs/payment_timeout_job.py`
- Localization updates
- Tests: `tests/integration/test_first_underpayment.py`

---

### Phase 5: Second Underpayment → Cancel with Penalty
**Feature: Cancel order, wallet credit with 5% penalty**

**Estimated Time:** 2-3 days

**Tasks:**
1. Implement `_handle_second_underpayment()`
2. Stock release logic via `OrderService.release_reserved_stock()`
3. Penalty calculation and wallet credit
4. Add localization keys: `order_cancelled_underpayment`, `admin_multiple_underpayment` (DE/EN)
5. Implement user and admin notifications

**Acceptance Criteria:**
- ✅ Order cancelled after 2nd underpayment
- ✅ Stock released successfully
- ✅ Total payments calculated correctly
- ✅ 5% penalty applied
- ✅ Wallet credited with net amount
- ✅ User and admin notified

**Deliverables:**
- Updated: `processing/processing.py`
- Updated: `services/order.py`
- Localization updates
- Tests: `tests/integration/test_second_underpayment.py`

---

### Phase 6: Late Payment Handling
**Feature: Post-timeout payments → Wallet with penalty**

**Estimated Time:** 2 days

**Tasks:**
1. Detect late payments (order already timed out)
2. Implement `_handle_late_payment()`
3. Apply 5% penalty
4. Wallet credit
5. Add localization key: `payment_late` (DE/EN)
6. Implement notification

**Acceptance Criteria:**
- ✅ Payments after timeout detected
- ✅ Order already cancelled (by timeout job)
- ✅ 5% penalty applied
- ✅ Wallet credited
- ✅ User notified with support hint

**Deliverables:**
- Updated: `processing/processing.py`
- Localization updates
- Tests: `tests/integration/test_late_payment.py`

---

### Phase 7: Wallet Integration at Checkout
**Feature: Auto-use wallet balance during checkout**

**Estimated Time:** 3 days

**Tasks:**
1. Modify `CartService.checkout()` to check wallet balance
2. Auto-deduct from wallet if balance > 0
3. Create invoice only for remaining amount (if any)
4. Handle case where wallet covers full order (no invoice needed)
5. Update order creation messages
6. Add localization keys for wallet usage display

**Acceptance Criteria:**
- ✅ Wallet automatically applied at checkout
- ✅ Invoice only for remaining amount
- ✅ User sees: "Wallet: €5.00 | Invoice: €10.00"
- ✅ Full wallet payment: Order completes immediately

**Deliverables:**
- Updated: `services/cart.py`
- Updated: `services/order.py`
- Localization updates
- Tests: `tests/integration/test_wallet_checkout.py`

---

### Phase 8: Testing & Documentation
**Quality Assurance**

**Estimated Time:** 3-4 days

**Tasks:**
1. Comprehensive webhook simulation for all scenarios
2. Integration test suite
3. Update test scripts in `tests/webhook/`
4. Update CHANGELOG.md
5. Update README.md (if needed)
6. Integrate T&Cs into FAQ (`faq_string` update)
7. Code review
8. Performance testing

**Acceptance Criteria:**
- ✅ All scenarios tested via webhook simulation
- ✅ Integration tests pass
- ✅ Documentation complete
- ✅ Code reviewed and approved
- ✅ Ready for staging deployment

**Deliverables:**
- Updated: `tests/webhook/test_payment_webhook.py`
- Updated: `CHANGELOG.md`
- Updated: `l10n/*/faq_string` with T&Cs
- Test report document

---

## 7. Total Timeline

**Estimated Total:** 20-25 working days (~4-5 weeks)

**Critical Path:**
1. Phase 1 (3 days) → Phase 2 (2 days) = **5 days for security fix MVP**
2. Phases 3-5 (7-10 days) = Full payment validation
3. Phase 6-7 (5 days) = Enhanced features
4. Phase 8 (3-4 days) = QA

**Fast Track Option (Security Fix Only):**
- Phase 1 + Phase 2 = 5 days
- Deploy security fix, implement features later

---

## 8. Open Questions

### 8.1 Resolved ✅
- [x] Underpayment tolerance: **ZERO** - confirmed!
- [x] Overpayment threshold: 0.1% configurable
- [x] Penalty fees: 5% for late/failed payments
- [x] Wallet withdrawal: Not available for users
- [x] T&Cs: Documented (DE/EN)

### 8.2 To Be Decided ❓

1. **KryptoExpress API Integration:**
   - How to create partial invoice? (Need to check API docs)
   - Do we cancel old payment_processing_id when creating new one?
   - API rate limits for invoice creation?

2. **User Model - top_up_amount:**
   - Field doesn't exist in current User model
   - Need to add it in migration or already exists elsewhere?

3. **Timeout Job:**
   - How to handle `PENDING_PAYMENT_PARTIAL` orders in timeout job?
   - Should we have different timeout for retry (currently 30min)?

4. **Testing Strategy:**
   - Prefer webhook simulation or small real payments?
   - Mock KryptoExpress for unit tests?

5. **Admin Notifications:**
   - Current: Send to all ADMIN_ID_LIST
   - Need separate channel for payment issues?

---

## 9. Risk Analysis

### Critical Risks 🔴

**1. Exchange Rate Calculation Error**
- **Impact:** Shop loses money on refunds/credits
- **Mitigation:**
  - Extensive unit tests with edge cases
  - Always use invoice's stored rate, never current rate
  - Code review by two developers

**2. Race Conditions**
- **Impact:** Multiple webhooks process same payment
- **Mitigation:**
  - Database transactions with proper locking
  - Check order status before processing
  - Idempotency keys in PaymentTransaction

**3. Underpayment Logic Error**
- **Impact:** Orders complete with insufficient payment
- **Mitigation:**
  - Zero tolerance enforced in code
  - Cannot override without code change
  - Comprehensive test suite

### Medium Risks 🟡

**4. KryptoExpress API Failure**
- **Impact:** Cannot create partial invoice
- **Mitigation:**
  - Fallback: Admin manual review
  - Error notification to admin
  - Wallet credit for user (safe default)

**5. User Confusion**
- **Impact:** Support tickets, bad UX
- **Mitigation:**
  - Clear notifications in T&Cs language
  - Support hint in messages
  - Admin can manually assist

### Low Risks 🟢

**6. Config Errors**
- **Impact:** Wrong tolerance/penalty values
- **Mitigation:**
  - Validation in config.py
  - Sane defaults (0.1%, 5%)
  - Config documented in .env.template

---

## 10. Success Metrics

**Phase 1-2 (Security):**
- 100% of payments validated before order completion
- 0 underpayments accepted as "paid"
- 0 currency mismatches accepted

**Phase 3-5 (Features):**
- >90% of first underpayments result in successful retry
- <5% orders cancelled due to second underpayment
- 100% of overpayments correctly credited

**Phase 6-7 (UX):**
- <2% late payments (indicates good blockchain performance)
- Average wallet usage: 20-30% of order value
- User complaints about retry: <5%

**Phase 8 (Quality):**
- Code coverage: >85%
- All integration tests pass
- Zero critical bugs in staging

---

## Next Steps

**Immediate Actions:**
1. ✅ Review this corrected design document
2. ⏳ Discuss any remaining concerns or changes
3. ⏳ Decide on fast-track (Phase 1+2 only) vs full implementation
4. ⏳ Answer open questions (Section 8.2)
5. ⏳ Begin Phase 1: Database extensions

**Ready to proceed with Phase 1?**
