# Changelog

All notable changes to this project will be documented in this file.

## 2025-10-30

### Strike System & Automated User Ban Management

**Key Features**
- Automatic strike tracking for order violations (timeouts, late cancellations after grace period)
- Automatic ban after configurable strike threshold (default: 3 strikes)
- Self-service unban via wallet top-up (default: 50 EUR, balance usable for shopping)
- Admin panel for banned user management with click-to-unban UI
- Strike statistics in user profile with status indicators and violation history

**User Experience**
- Banned users receive clear messages with unban instructions and support access
- Shopping restricted, but FAQ and Support remain accessible
- Strike count preserved after unban (next violation = immediate re-ban)
- Notifications for ban/unban events with transparent explanations

**Configuration**
- MAX_STRIKES_BEFORE_BAN: Strike threshold before ban (default: 3)
- EXEMPT_ADMINS_FROM_BAN: Admin exemption for testing (default: true)
- UNBAN_TOP_UP_AMOUNT: Minimum wallet top-up to unban (default: 50.0 EUR)

**Documentation**
- Quick start guide for payment testing including TOPUP scenarios
- Strike system test cases and webhook simulator improvements

## 2025-10-26

### Comprehensive Shipping & Order Management System

**Shipping Management**
- Physical item support with encrypted shipping address collection (AES-256)
- Packstation support for German customers
- Per-item shipping costs (uses MAX of all items, not SUM for fair pricing)
- Admin shipment dashboard with order fulfillment workflow
- Automatic address retention cleanup after configurable period (default 90 days)
- Customer notifications for shipment updates

**Cart/Order Domain Separation (Phase 1 Refactoring)**
- Orchestrated order creation with stock reservation
- Real-time stock adjustment notifications during checkout
- Partial stock reservation support (e.g., requested 5, got 3)
- Strike-through formatting for sold-out items in adjustment screen

**Enhanced Order Cancellation System**
- Grace period for free cancellations (default 5 minutes, configurable)
- Two-step confirmation dialog with transparent fee warnings
- Hybrid penalty system:
  * Wallet used: Refund minus processing fee
  * Wallet NOT used but balance exists: Charge reservation fee
  * No wallet balance: No fee, just strike
- Detailed cancellation notifications explaining why fees apply

**Invoice & Payment Improvements**
- Minimalist tabular invoice format for better readability
- Consistent invoice display across all order states
- Separate delivery status for digital vs physical items
- Complete order overview in pending order screens
- Grace period countdown in order details
- Invoice database persistence fix for crypto payments
- Direct payment redirect (removed unnecessary intermediate screens)

**Admin Enhancements**
- Complete order overview showing ALL items (digital + physical)
- Digital items marked as "Delivered" (instant delivery)
- Physical items grouped under "Items to be shipped"
- User identification with both username and Telegram ID
- Consistent order views across user and admin interfaces

**Data Retention & Cleanup**
- Automated cleanup job for old orders/invoices (configurable, default: 30 days)
- Payment transaction cleanup (cascade with orders)
- Referral data retention (365 days for abuse detection)
- Orphaned invoice safety cleanup

**User Experience**
- Out-of-stock items immediately removed from cart (prevents loops)
- Pending order display with item details and grace period info
- Transparent fee calculations and explanations
- Improved error handling for all edge cases

**Technical Improvements**
- N+1 query prevention with proper eager loading
- Session commit optimization to prevent data loss
- Idempotent payment completion (prevents duplicate buy records)
- Wallet amount rounding fixes (2 decimal places everywhere)
- Domain separation: _format_payment_screen moved to OrderService


**Database Changes**
- New tables: shipping_addresses, payment_transactions, referral_usage, referral_discount
- Extended Item model: is_physical, shipping_cost, supports_packstation
- Extended Order model: shipping_address_id, shipping_cost, wallet_used
- New order statuses: PENDING_PAYMENT_AND_ADDRESS, PAID_AWAITING_SHIPMENT
- New enums: OrderCancelReason, PaymentValidationResult

**Configuration**
- ENCRYPTION_SECRET: For shipping address encryption
- SHIPPING_ADDRESS_RETENTION_DAYS: Address cleanup (default 90)
- PAYMENT_LATE_PENALTY_PERCENT: Late cancellation fee (default 10%)
- TEST runtime mode: For testing scripts without production side effects

**Documentation**
- TEST_CHECKLIST.md: Comprehensive testing guide 
- REFACTORING_PLAN.md: Cart/Order separation roadmap
- SHIPPING_REQUIREMENTS.md: Shipping feature specifications
- Payment validation design docs
- Terms & Conditions (DE/EN)
- TODO system with Evil Factor ratings for future features

**Testing & Tools**
- Payment webhook simulator for local testing
- Race condition testing tools
- Interactive migration runner
- Manual test scenarios with documented test data
- Stock adjustment test helpers

## 2025-10-23

### Payment Validation & Wallet Integration System

**Core Payment Processing**
- Implemented 4-phase payment validation system: database models (Order, Invoice, PaymentTransaction), PaymentValidator service with tolerance-based validation, invoice generation with multi-language notifications (DE/EN), automatic wallet balance usage
- Payment edge case handling: exact payments, minor overpayment (forfeits to shop), significant overpayment (wallet credit), underpayment with retry invoice (2 attempts then cancel with penalty), late payments (credited to wallet with configurable penalty), double payments (credited to wallet without penalty), currency mismatch detection
- Penalty calculation uses Decimal with ROUND_DOWN to favor customer (prevents rounding errors like 18.91 * 5% = 0.9455 rounding to 0.95 instead of 0.94)

**Wallet Integration**
- Automatic wallet balance deduction at checkout: calculates wallet_used = min(balance, total_price)
- Multi-source payments: wallet + crypto invoice combined in single order
- Wallet-only orders: status=PAID immediately, items delivered without crypto invoice
- Wallet balance refunds with configurable penalties for late/timeout cancellations
- Wallet rollback on stock reservation failure

**Order Lifecycle Management**
- Order creation with stock reservation using SELECT FOR UPDATE (prevents race conditions)
- Grace period cancellation: configurable duration (default 5 min), free within period, penalty + strike after
- Automatic timeout: configurable duration (default 15 min), applies penalty on expiration
- Order completion workflow: set status=PAID first (source of truth), mark items sold, create Buy records, commit, deliver items via Telegram DM
- Unified completion path for all payment methods (wallet/crypto/mixed)

**Stock Management**
- Fixed availability calculation: get_available_qty() now filters order_id == None (excludes reserved items)
- Auto-removal of out-of-stock items from cart with user notification
- Zero-stock items hidden from catalog automatically

**User Experience**
- Return to subcategory list after adding item to cart
- Skip crypto selection when wallet balance sufficient
- Conditional grace period warnings (with/without fee mention based on wallet_used)
- Display data retention period in purchase history header (from DATA_RETENTION_DAYS config)
- Invoice numbers (2025-ABCDEF format) instead of DB IDs in all notifications
- Crypto amount formatting: 9e-06 → 0.000009 (8 decimals, trailing zeros removed)

**Technical Improvements**
- Database: Removed unique constraint on invoice.order_id for partial payment support, added wallet_used field to Order model, fixed SQLAlchemy relationships (Order.invoices, Invoice.order)
- Repositories: Added UserRepository.get_by_id() for order workflows
- Order cancellation: Unified cancel_order() method with OrderCancelReason enum (USER, TIMEOUT, ADMIN)
- Fiat calculation: Calculate from crypto using invoice exchange rate instead of trusting webhook fiatAmount
- Import fixes: Moved format_crypto_amount and other imports to top-level to fix UnboundLocalError/NameError
- Session commit: Added missing session_commit() after order cancellation to persist wallet refunds

**Configuration**
- Added configurable parameters: ORDER_TIMEOUT_MINUTES, ORDER_CANCEL_GRACE_PERIOD_MINUTES, PAYMENT_TOLERANCE_OVERPAYMENT_PERCENT, PAYMENT_UNDERPAYMENT_PENALTY_PERCENT, PAYMENT_LATE_PENALTY_PERCENT, DATA_RETENTION_DAYS
- Removed unused security config variables from .env.template (rate limiting, logging, webhook security, database backup - documented in security audit TODO for future implementation)

**Testing & Documentation**
- Manual webhook simulator with HMAC-SHA512 signature verification
- E2E test structure for payment flows
- Testing guide with 10 payment scenarios: exact payment, minor/significant overpayment, underpayment retry, double underpayment, late payment, double payment, currency mismatch, full/partial wallet payment, order cancellation
- Test shop data: 23 items, 2 categories, 4 subcategories
- Security audit findings documented with implementation roadmap
- TODO organization: Moved completed payment-validation-followup TODO to TODO/done/ folder

**Breaking Changes**
- Database migration required: Drop unique constraint on invoice.order_id column to allow multiple invoices per order (underpayment retry scenario)

## 2025-10-19

### UX Improvement: Return to Category After Add to Cart
- After adding item to cart, user is now redirected back to subcategory list
- User can continue shopping in same category without re-navigating
- Added toast notification (`callback.answer()`) instead of full message edit
- Preserves shopping context and improves multi-item cart building flow

## 2025-10-18

### Code Quality: DTO Naming Refactoring
- Renamed `TablePaymentDTO` to `DepositRecordDTO` for better clarity
- Added documentation explaining purpose: tracks deposit (balance top-up) payment records
- Updated all references in: `repositories/payment.py`, `services/notification.py`, `processing/processing.py`
- Added backwards compatibility alias to prevent breaking changes
- Improved variable naming: `table_payment_dto` → `deposit_record` throughout codebase

### Webhook Enhancement for Invoice-Based Payments
- Extended `/cryptoprocessing/event` webhook to handle both DEPOSIT and PAYMENT types
- Added `_handle_order_payment()` function for invoice-based order payments
- Added `_handle_deposit_payment()` function (refactored from existing code)
- Webhook now checks `invoices` table first, falls back to `payments` table
- Automatic order completion when KryptoExpress confirms payment
- Duplicate protection: Only processes payment if order status is still `PENDING_PAYMENT`
- Enhanced logging: detailed webhook event tracking with emojis for better readability
- Logs include: Payment ID, type, status, crypto/fiat amounts, order details, and processing results

### Configuration Template System
- Added `.env.template` with comprehensive documentation for all config parameters
- Each parameter now includes usage instructions and examples
- Removed `.env` from git tracking (now in .gitignore)
- Updated `.gitignore` to allow `.env.template` in repository
- Instructions included in template: `cp .env.template .env` then fill in values
- Enhanced `KRYPTO_EXPRESS_API_SECRET` documentation: clarified it's self-generated (not from KryptoExpress)
- Added step-by-step guide for generating API secret with `openssl rand -hex 32`
- Documented HMAC-SHA512 webhook verification flow

### Payment Timeout Job Implementation
- Added background job for automatic order expiry (`jobs/payment_timeout_job.py`)
- Job checks every 60 seconds for expired pending orders
- Automatically cancels expired orders and releases reserved stock
- Sets order status to TIMEOUT with cancelled_at timestamp
- Integrated job into bot startup/shutdown lifecycle in `bot.py`
- Added qrcode and Pillow libraries to requirements.txt (for future QR code feature)

## 2025-10-17

### Order Expiry Display Enhancement
- Added expiry time (HH:MM) to order messages alongside remaining minutes
- Show "Order expired!" message when viewing expired orders
- Hide cancel button for expired orders
- Added three new localization keys: `order_created_success` (updated), `order_pending`, `order_expired`
- Fixed timezone mismatch bug (order.created_at was None for new orders)
- Fixed OrderStatus enum reference (changed CANCELLED to CANCELLED_BY_USER/CANCELLED_BY_ADMIN)
- Added missing config import in services/cart.py