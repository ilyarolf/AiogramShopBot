# Admin Order Cancellation

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** Medium (1.5-2 hours)

---

## Description
Enable administrators to manually cancel orders at any point in the order lifecycle without penalizing the customer with strikes. Admin cancellations are tracked separately from user cancellations and trigger appropriate notifications to the affected user.

## User Story
As an administrator, I want to manually cancel problematic orders (fraud, out-of-stock errors, customer service requests) without affecting the customer's strike count, so that I can maintain operational flexibility and customer satisfaction.

## Acceptance Criteria
- [ ] Admin panel shows list of active orders (PENDING_PAYMENT, PAID, SHIPPED)
- [ ] Admin can select an order and click "Cancel Order" button
- [ ] Confirmation dialog shows order details and reason input field
- [ ] Order status is set to `CANCELLED_BY_ADMIN` (already exists in OrderStatus enum)
- [ ] User receives notification about admin cancellation with reason
- [ ] If order was PENDING_PAYMENT:
  - Reserved items are released back to stock
  - Invoice is marked as cancelled
- [ ] If order was PAID:
  - Admin must manually process refund (system shows refund instructions)
  - Items remain marked as sold (admin must manually adjust stock if needed)
  - Refund tracking record is created
- [ ] User does NOT receive a strike (unlike CANCELLED_BY_USER after grace period)
- [ ] Admin action is logged with:
  - Admin user ID
  - Timestamp
  - Cancellation reason
  - Order state at time of cancellation

## Technical Notes

### New Model: AdminActionLog
```python
class AdminActionLog(Base):
    __tablename__ = 'admin_action_logs'

    id = Column(Integer, primary_key=True)
    admin_user_id = Column(Integer, nullable=False)  # Telegram ID
    action_type = Column(String, nullable=False)  # "CANCEL_ORDER", "BAN_USER", etc.
    target_order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    target_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
```

### Service Logic
`OrderService.cancel_order_by_admin(order_id, admin_user_id, reason, session)` handles:
- PENDING_PAYMENT → Release reserved items
- PAID → Show manual refund instructions with crypto details
- SHIPPED → Instruct admin to contact customer for return

### Implementation Order
1. Create `models/admin_action_log.py`
2. Create database migration
3. Create repositories
4. Implement `OrderService.cancel_order_by_admin()`
5. Create admin UI handlers
6. Implement user notifications
7. Add localization keys (DE/EN)
8. Testing

## Dependencies
- Requires `AdminActionLog` model
- User notification system must be functional
- Admin authentication/authorization must be in place

---

**Status:** Planned