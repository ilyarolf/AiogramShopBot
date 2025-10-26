# Payment Validation System - Follow-up Tasks

**Date:** 2025-10-22
**Priority:** Medium
**Status:** Testing Phase (feature/payment-amount-validation branch)
**Estimated Effort:** Low-Medium (1-2 hours)

---

## Description
Follow-up improvements for the payment validation system that were identified during testing phase. These enhancements improve user experience and cart handling logic.

## Context
The main payment validation system has been implemented and is currently in testing on the `feature/payment-amount-validation` branch. These tasks were identified as UX improvements during the testing phase.

---

## Task 1: Cart Stock Reduction Logic

### Current Behavior
When a user tries to checkout but insufficient stock is available:
- The entire cart item is removed
- User loses their selection

### Desired Behavior
When insufficient stock is available:
- Reduce quantity to maximum available stock instead of removing
- Process order with reduced quantity
- Show clear warning to user with yellow triangle (⚠️)
- User must be explicitly informed about quantity reduction

### Acceptance Criteria
- [ ] Check available stock during checkout confirmation
- [ ] If `requested_qty > available_qty`: Set `cart_item.quantity = available_qty`
- [ ] Display warning message with ⚠️ icon
- [ ] Message clearly states: "Quantity reduced from X to Y due to stock availability"
- [ ] User must acknowledge reduction before proceeding
- [ ] Log quantity adjustments for debugging

### Implementation Notes
- Modify `CartService.get_crypto_selection_for_checkout()` in `services/cart.py`
- Add localization strings:
  - `stock_quantity_reduced_warning` (DE/EN)
  - Include original quantity, new quantity, and product name
- Consider adding configuration: `ALLOW_PARTIAL_STOCK_CHECKOUT = True/False`

### Files to Modify
- `services/cart.py` - Cart checkout logic
- `l10n/de.json` - German localization
- `l10n/en.json` - English localization

---

## Status

- [x] ~~Skip crypto selection when wallet balance sufficient~~ (Completed 2025-10-22)
- [ ] Cart stock reduction logic (Pending)

---

## Testing Notes

When testing cart stock reduction:
1. Add item with quantity 5 to cart
2. Reduce stock to 3 via admin panel
3. Attempt checkout
4. Verify: Quantity reduced to 3 (not removed)
5. Verify: Warning message displayed with ⚠️
6. Verify: Order processes successfully with qty=3

---

## Related Features

- Main feature: Invoice-Based Payment System (Completed)
- Related: Strike System (separate TODO) - Should not trigger strike for stock reduction
