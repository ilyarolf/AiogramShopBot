# TODO Feature Files

This directory contains individual feature specifications for planned implementations.

## File Naming Convention

Format: `YYYY-MM-DD_TODO_feature-name.md`

Example: `2025-10-19_TODO_add-separate-crypto-wallets.md`

- **Date**: When the feature idea was first documented
- **Feature Name**: Kebab-case description of the feature

## Feature Status

- **Planned**: Not yet started
- **In Progress**: Currently being implemented
- **Completed**: Implementation finished (file should be moved to `/docs/engineering/completed/` or deleted)

## Priority Levels

- **High**: Critical features that block other functionality
- **Medium**: Important features that enhance user experience
- **Low**: Nice-to-have features that can be implemented later

## Current Features

### Payment System
- `2025-10-19_TODO_add-separate-crypto-wallets.md` - Separate crypto wallets per user to eliminate currency conversion risk

### User Management
- `2025-10-19_TODO_strike-system-and-user-ban.md` - Strike system and automatic user bans for order violations

### Pricing & Catalog
- `2025-10-19_TODO_tiered-pricing.md` - Staffelpreise (tiered pricing) for quantity discounts
- `2025-10-19_TODO_shipping-cost-management.md` - Shipping cost calculation and display
- `2025-10-19_TODO_upselling-options.md` - Optional add-ons (premium packaging, insured shipping)

### Marketing
- `2025-10-19_TODO_referral-system.md` - Referral code system with discounts for referrer and referred

### Admin Tools
- `2025-10-19_TODO_admin-order-cancellation.md` - Admin ability to cancel orders without user penalty

### Security & Privacy
- `2025-10-19_TODO_gpg-public-key-display.md` - Display shop's GPG public key in menu
- `2025-10-19_TODO_encrypted-shipping-address.md` - GPG-encrypted shipping address submission

## Adding New Features

When adding a new feature specification:

1. Create a new file with current date: `YYYY-MM-DD_TODO_feature-name.md`
2. Use the template structure:
   - Title
   - Metadata (Date, Priority, Estimated Effort)
   - Description
   - User Story
   - Acceptance Criteria
   - Technical Notes
   - Implementation Order
   - Dependencies
   - Status

3. Update this README with a link to the new feature

## Completed Features

When a feature is completed:
- Move the file to `/docs/engineering/completed/` for archival
- OR delete if the feature is well-documented in code/CHANGELOG
- Update this README to remove the feature from the list