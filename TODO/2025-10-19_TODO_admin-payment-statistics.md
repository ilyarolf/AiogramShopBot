# Admin Payment Statistics Dashboard

**Date:** 2025-10-19
**Priority:** Low
**Estimated Effort:** Medium (2-3 hours)

---

## Description
Create an admin statistics dashboard that provides insights into payment patterns, failures, and revenue metrics by analyzing the PaymentTransaction table.

## User Story
As a shop administrator, I want to see detailed payment statistics including underpayment rates, penalty fees collected, and timeout reasons, so that I can understand payment behavior and optimize the payment system.

## Acceptance Criteria
- [ ] Admin dashboard shows payment statistics:
  - Total successful payments (PAID orders)
  - Total timeouts (TIMEOUT orders)
  - Breakdown of timeout reasons:
    - No payment received (0 PaymentTransactions)
    - 1st underpayment only (1 PaymentTransaction)
    - 2nd underpayment failure (2 PaymentTransactions with penalty)
    - Late payment after deadline (is_late_payment = true)
  - Total overpayments forfeited (≤0.1% tolerance)
  - Total overpayments credited to wallets (>0.1%)
  - Total penalty fees collected (5% of failed payments)
  - Average payment completion rate
  - Average retry rate (orders with partial payments)
- [ ] Time-based filters:
  - Last 7 days
  - Last 30 days
  - Last 90 days
  - Custom date range
- [ ] Export to CSV for financial reporting
- [ ] Charts/graphs for visual representation (optional)

## Technical Notes

### Data Sources
All statistics derived from `PaymentTransaction` table:

**Timeout Reason Analysis:**
```sql
-- Orders with no payment
SELECT COUNT(*) FROM orders
WHERE status = 'TIMEOUT'
AND id NOT IN (SELECT DISTINCT order_id FROM payment_transactions)

-- Orders with 1st underpayment only
SELECT COUNT(*) FROM orders
WHERE status = 'TIMEOUT'
AND id IN (
  SELECT order_id FROM payment_transactions
  WHERE is_underpayment = true
  GROUP BY order_id HAVING COUNT(*) = 1
)

-- Orders with 2nd underpayment (penalty applied)
SELECT COUNT(*) FROM orders
WHERE status = 'TIMEOUT'
AND id IN (
  SELECT order_id FROM payment_transactions
  WHERE penalty_applied = true
)
```

**Revenue Metrics:**
```sql
-- Total penalty fees collected
SELECT SUM(fiat_amount * penalty_percent / 100)
FROM payment_transactions
WHERE penalty_applied = true

-- Total overpayments forfeited (minor overpayments)
-- NOTE: Not tracked in PaymentTransaction (by design)
-- Would need separate tracking if important

-- Total overpayments credited to wallets
SELECT SUM(wallet_credit_amount)
FROM payment_transactions
WHERE is_overpayment = true AND wallet_credit_amount IS NOT NULL
```

## Implementation Order
1. Create `services/payment_statistics.py` with query methods
2. Create admin handler `handlers/admin/statistics.py`
3. Implement UI with inline keyboard for date range selection
4. Add export to CSV functionality
5. Add localization keys (DE/EN)
6. Testing with various payment scenarios

## Dependencies
- Requires PaymentTransaction table to be populated
- Admin authentication/authorization must be in place
- Data retention: Works within 30-day window (before cleanup)

## Notes
- Statistics only cover last 30 days due to data retention policy
- For long-term financial reporting, consider aggregated monthly summaries before cleanup
- Can be extended with charts using matplotlib or similar library

---

**Status:** Planned (Low Priority)
**Implements:** Payment pattern analysis and financial reporting for admin
