# TODO - Feature Overview

**Note:** Detailed feature specifications are now organized in the `/TODO/` directory.

See `/TODO/README.md` for the complete list and organization structure.

## Quick Links

### High Priority
- [Security Audit Findings](TODO/2025-10-22_TODO_security-audit-findings.md) ⚠️ **NEW**
- [Strike System and User Ban Management](TODO/2025-10-19_TODO_strike-system-and-user-ban.md)
- [Admin Order Cancellation](TODO/2025-10-19_TODO_admin-order-cancellation.md)

### Payment System
- [Separate Crypto Wallets](TODO/2025-10-19_TODO_add-separate-crypto-wallets.md) - Eliminate currency conversion risk
- **KryptoExpress Balance in Admin Dashboard** - Display merchant wallet balances from KryptoExpress API

### Catalog & Pricing
- [Tiered Pricing](TODO/2025-10-19_TODO_tiered-pricing.md) - Quantity discounts (Staffelpreise)
- [Shipping Cost Management](TODO/2025-10-19_TODO_shipping-cost-management.md)
- [Upselling Options](TODO/2025-10-19_TODO_upselling-options.md) - Add-ons like premium packaging

### Marketing
- [Referral System](TODO/2025-10-19_TODO_referral-system.md) - Viral growth with discount codes

### Security & Privacy
- [GPG Public Key Display](TODO/2025-10-19_TODO_gpg-public-key-display.md)
- [Encrypted Shipping Address](TODO/2025-10-19_TODO_encrypted-shipping-address.md)

## Recently Completed Features

### 2025-10-19
- ✅ **Return to Category After Add to Cart** - User stays in subcategory after adding item
- ✅ **Invoice-Based Payment System** - KryptoExpress integration with stock reservation
- ✅ **Payment Success Notifications** - User and admin notifications on successful payment

### 2025-10-18
- ✅ **Order Grace Period Cancellation** - Users can cancel within 5 minutes without penalty
- ✅ **Order Timeout Monitoring** - Background job expires unpaid orders after 15 minutes
- ✅ **Webhook System** - Real-time payment status updates from KryptoExpress

## How to Use This File

1. Browse the **Quick Links** section above to find features by category
2. Click on a link to open the detailed feature specification
3. Each feature file contains:
   - Complete technical specification
   - Acceptance criteria
   - Implementation order
   - Dependencies
   - Estimated effort

## Adding New Features

When proposing a new feature:
1. Create a file in `/TODO/` following the naming convention: `YYYY-MM-DD_TODO_feature-name.md`
2. Use the template structure (see existing files for examples)
3. Add a link in this file under the appropriate category
4. Update `/TODO/README.md`