# Database Migrations

## Wallet Rounding Fix (2025-10-24)

### Problem
Floating-point precision errors caused wallet balances to have more than 2 decimal places, leading to:
- Tiny negative balances (e.g., `-1.82e-12 EUR`)
- CHECK constraint violations when trying to update wallets
- Admin unable to completely empty wallets

### Solution
Round all wallet amounts to exactly 2 decimal places.

### Migration Options

#### Option 1: Python Script (Recommended)

```bash
# From project root
python migrations/fix_wallet_rounding.py
```

**Advantages:**
- Uses existing ORM models
- Detailed logging
- Safe error handling

#### Option 2: SQL Script (Direct)

```bash
# Backup database first
cp shop.db shop.db.backup

# Apply SQL migration
sqlite3 shop.db < migrations/fix_wallet_rounding.sql
```

**Advantages:**
- Faster for large databases
- No Python dependencies

### Verification

After migration, verify that all balances are correctly rounded:

```sql
-- Check for precision errors
SELECT telegram_id, top_up_amount
FROM users
WHERE top_up_amount != ROUND(top_up_amount, 2);

-- Should return 0 rows

-- Check for negative balances
SELECT telegram_id, top_up_amount
FROM users
WHERE top_up_amount < 0;

-- Should return 0 rows
```

### Rollback

If needed, restore from backup:

```bash
cp shop.db.backup shop.db
```

### Future Prevention

All wallet operations now use `round(amount, 2)` to prevent future precision errors.
See commits:
- 5a5a99e: fix: replace deprecated consume_records with top_up_amount
- 7bc44f9: fix: prevent negative wallet balance in REDUCE_BALANCE operation
- a7bf2e7: fix: round all wallet amounts to 2 decimal places
