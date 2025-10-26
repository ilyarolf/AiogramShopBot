# Separate Crypto Wallets per User (Currency Conversion Risk Mitigation)

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** Large (4-5 days)

---

## Description
Currently, the wallet system uses a single fiat balance (`top_up_amount`) which forces the shop operator to bear 100% of currency conversion risk. When crediting overpayments, cancellations, or late payments to the wallet in fiat, the shop loses money if crypto prices rise before the user spends the balance.

## User Story
As a shop operator, I want users to have separate crypto balances (BTC, LTC, USDT) so that I don't bear the currency conversion risk when crediting wallets.

## Business Impact

### Current Risk:
- User overpays €50 in BTC (0.001 BTC @ €50,000/BTC)
- Shop credits €50 to wallet (fiat)
- BTC price rises to €60,000/BTC
- User spends €50 from wallet on new order
- Shop must now pay 0.000833 BTC (instead of original 0.001 BTC)
- **Shop loses ~16.7% due to rate change**

### With Crypto Wallets:
- User overpays 0.001 BTC
- Shop credits 0.001 BTC to BTC wallet
- User spends 0.001 BTC on new order
- **No conversion risk for shop**

## Acceptance Criteria
- [ ] User model has separate balance fields per crypto:
  - `btc_balance` (Float, default 0.0)
  - `ltc_balance` (Float, default 0.0)
  - `usdt_balance` (Float, default 0.0)
- [ ] Wallet credits (overpayment, cancellation, late payment) are stored in the original crypto currency
- [ ] Checkout allows user to select which crypto wallet to use (or auto-select based on availability)
- [ ] Wallet display shows all crypto balances with current fiat equivalent
- [ ] Top-up functionality creates invoice in chosen crypto
- [ ] Migration preserves existing `top_up_amount` fiat balances (one-time conversion to EUR-based legacy balance)

## Technical Notes
- This was the original wallet design before invoice migration (see git commit f2f2798)
- Short-term: Keep `top_up_amount` for MVP payment validation
- Medium-term: Implement full crypto wallet system to eliminate conversion risk

## Implementation After
Payment validation system is stable and tested in production.

---

**Status:** Planned
**Depends On:** Payment validation feature completion