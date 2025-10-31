-- Add topup_reference column to payments table
-- Format: TOPUP-YYYY-ABCDEF (similar to invoice numbers)
-- This provides a user-friendly reference for top-up transactions

ALTER TABLE payments ADD COLUMN topup_reference TEXT UNIQUE;

-- Create index for fast lookup
CREATE INDEX idx_payments_topup_reference ON payments(topup_reference);
