# Changelog

All notable changes to this project will be documented in this file.

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