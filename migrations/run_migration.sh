#!/bin/bash

# Wallet Rounding Migration Runner
# This script safely applies the wallet rounding fix to your database

set -e  # Exit on error

echo "=========================================="
echo "Wallet Rounding Migration"
echo "=========================================="
echo ""

# Check if database exists
if [ ! -f "shop.db" ]; then
    echo "❌ Error: shop.db not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

# Create backup
BACKUP_FILE="shop.db.backup.$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup: $BACKUP_FILE"
cp shop.db "$BACKUP_FILE"
echo "✅ Backup created successfully"
echo ""

# Ask user which method to use
echo "Choose migration method:"
echo "1) Python script (recommended, detailed logging)"
echo "2) SQL script (faster, less output)"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo "Running Python migration..."
        echo "=========================================="
        python migrations/fix_wallet_rounding.py
        ;;
    2)
        echo ""
        echo "Running SQL migration..."
        echo "=========================================="
        sqlite3 shop.db < migrations/fix_wallet_rounding.sql
        echo ""
        echo "✅ SQL migration completed"
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Backup saved as: $BACKUP_FILE"
echo ""
echo "To verify the migration, run:"
echo "  sqlite3 shop.db \"SELECT COUNT(*) FROM users WHERE top_up_amount != ROUND(top_up_amount, 2);\""
echo ""
echo "Expected result: 0"
echo ""
echo "To rollback if needed:"
echo "  cp $BACKUP_FILE shop.db"
echo ""
