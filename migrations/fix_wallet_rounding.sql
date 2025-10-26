-- One-time migration: Round all wallet amounts to 2 decimal places
-- This fixes floating-point precision errors in existing wallet balances

-- Backup current state (optional)
-- CREATE TABLE users_backup AS SELECT * FROM users;

-- Fix wallet balances
UPDATE users
SET top_up_amount = ROUND(top_up_amount, 2)
WHERE top_up_amount != ROUND(top_up_amount, 2);

-- Fix any negative balances (should not exist but just in case)
UPDATE users
SET top_up_amount = 0.0
WHERE top_up_amount < 0;

-- Verify results
SELECT
    COUNT(*) as total_users,
    COUNT(CASE WHEN top_up_amount != ROUND(top_up_amount, 2) THEN 1 END) as users_with_precision_errors,
    COUNT(CASE WHEN top_up_amount < 0 THEN 1 END) as users_with_negative_balance
FROM users;
