# Referral System

**Date:** 2025-10-19
**Priority:** Low-Medium
**Estimated Effort:** High (3-4 hours)

---

## Description
Implement a referral system where established users (5+ completed orders) receive a unique referral code. When a new customer uses a referral code at checkout, the new customer receives 10% discount on their first order, and the referrer receives 10% discount on their next order.

## User Story
As a shop administrator, I want to incentivize existing customers to refer new users through viral word-of-mouth marketing, while keeping the system economically balanced with anti-abuse safeguards.

## Acceptance Criteria
- [ ] Users receive unique referral code after 5 successful (PAID) orders
- [ ] Referral code format: `U_{5-random-chars}` (e.g., `U_A3F9K`, `U_7X2PM`)
- [ ] Referral code is shown in user profile/account section
- [ ] New users can enter referral code during checkout (optional field)
- [ ] When referral code is applied:
  - **New customer:** 10% discount on first order (applied immediately, cap at €50)
  - **Referrer:** 10% discount credit for their next order (cap at €50)
- [ ] Cart shows notification about discount application
- [ ] Each referral code can be used once per user-pair (User A can refer User B only once)
- [ ] Users cannot use their own referral code
- [ ] **Referral limit:** Maximum 10 successful referrals per user (prevents industrial farming)
- [ ] Referral discount credits expire after 90 days
- [ ] Referral tracking:
  - Track who referred whom
  - Store discount amount for auditing
- [ ] After 5th successful order, user receives notification with their referral code
- [ ] Discount cannot exceed order total (min. payment = €0.01)
- [ ] Optional monitoring: Alert admin if user reaches referral limit

## Security and Anti-Abuse Analysis

### Economic Safeguards:
With **€50 minimum order value**, the referral system is naturally protected from abuse:

**Fake-Account Economics:**
- Attacker investment: 5 Orders × €50 = €250 (to get referral code)
- Per fake order: €50 - 10% discount = €45 cost
- Per fake order reward: €5 discount credit (10% of €50)
- **ROI: ~10%** (extremely low for high effort)

**Why Abuse is Unprofitable:**
1. High barrier to entry (€250 investment)
2. Each fake order costs €45 real money
3. Discount cap at €50 limits gains
4. Crypto payment fees reduce margins further
5. Time investment makes it uneconomical

### Implemented Safeguards:

1. **5-Order Threshold**
   - Prevents immediate multi-account abuse
   - Requires €250+ investment before referral eligibility
   - Makes throwaway accounts economically unviable

2. **10-Referral Limit Per User**
   - Prevents industrial farming
   - Balanced for viral growth without abuse
   - Admin can monitor users approaching limit

3. **One-Time Use Per User-Pair**
   - User A can refer User B only once
   - Prevents double-dipping from same relationship
   - Database constraint: `UniqueConstraint('referrer_user_id', 'referred_user_id')`

4. **Self-Referral Prevention**
   - Users cannot use their own referral code
   - Database constraint: `CheckConstraint('referrer_user_id != referred_user_id')`

5. **Payment Requirement**
   - Only PAID orders count toward 5-order threshold
   - Prevents fake orders from qualifying user

6. **90-Day Expiry**
   - Discount credits expire after 90 days
   - Prevents unlimited accumulation

7. **Discount Cap**
   - Both discounts capped at €50
   - Prevents abuse on large orders

## Technical Notes

### Database Models

**User Model Extensions:**
```python
# models/user.py
class User(Base):
    # Existing fields...

    # Referral System
    referral_code = Column(String(8), unique=True, nullable=True)  # U_A3F9K
    referral_code_created_at = Column(DateTime, nullable=True)
    successful_orders_count = Column(Integer, default=0)  # Tracks PAID orders
    referral_eligible = Column(Boolean, default=False)  # True after 5 orders

    # Anti-Abuse
    max_referrals = Column(Integer, default=10)  # Max 10 successful referrals
    successful_referrals_count = Column(Integer, default=0)

    # Who referred this user?
    referred_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referred_at = Column(DateTime, nullable=True)
```

**New Models:**
```python
# models/referral_discount.py
class ReferralDiscount(Base):
    __tablename__ = 'referral_discounts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    discount_percentage = Column(Float, default=10.0)
    max_discount_amount = Column(Float, default=50.0)  # Cap at €50
    reason = Column(String, nullable=False)  # "Referred user U_A3F9K"

    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)

    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)  # 90-day expiry

# models/referral_usage.py
class ReferralUsage(Base):
    __tablename__ = 'referral_usages'

    id = Column(Integer, primary_key=True)
    referral_code = Column(String(8), nullable=False)
    referrer_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referred_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    discount_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('referrer_user_id', 'referred_user_id', name='uq_referrer_referred'),
        CheckConstraint('referrer_user_id != referred_user_id', name='check_no_self_referral'),
    )
```

### Referral Code Generation
```python
import secrets
import string

def generate_referral_code() -> str:
    """Generates unique referral code in format U_XXXXX"""
    alphabet = string.ascii_uppercase + string.digits  # A-Z, 0-9
    random_part = ''.join(secrets.choice(alphabet) for _ in range(5))
    return f"U_{random_part}"
```

## Implementation Order

1. Create `models/referral_discount.py` and `models/referral_usage.py`
2. Update `models/user.py` with referral fields
3. Create database migrations
4. Create repositories for referral models
5. Implement referral code generation logic
6. Update `OrderService.complete_order_payment()` to check for 5th order and grant referral eligibility
7. Create notification service for referral eligibility
8. Add referral code input step in checkout flow (FSM state)
9. Update order creation to apply referral discount
10. Implement referral usage tracking
11. Add user profile section to display referral code
12. Add localization keys (DE/EN)
13. Comprehensive testing

## Dependencies
- Requires database migrations
- Requires FSM state for referral code input
- Must update order creation flow
- Must update invoice display to show referral discount

## Open Questions
1. Should referral limit be configurable per user by admin?
2. Should we display referral statistics to users (e.g., "You've referred 3/10 friends")?
3. Should admins be able to manually grant/revoke referral eligibility?

---

**Status:** Planned
**Notes:** Low priority - implement after core payment system is stable