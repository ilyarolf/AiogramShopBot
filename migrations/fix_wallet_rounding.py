#!/usr/bin/env python3
"""
One-time migration: Round all wallet amounts to 2 decimal places

This script fixes floating-point precision errors in existing wallet balances.

Usage:
    python migrations/fix_wallet_rounding.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Prevent ngrok from starting
os.environ['RUNTIME_ENVIRONMENT'] = 'MIGRATION'

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.user import User


async def fix_wallet_rounding():
    """Round all user wallet amounts to 2 decimal places and fix negatives"""

    # Create async engine directly (avoid importing config which starts ngrok)
    engine = create_async_engine('sqlite+aiosqlite:///shop.db', echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        # Get all users
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

        fixed_count = 0
        negative_count = 0

        print(f"Found {len(users)} users to check...")

        for user in users:
            original_amount = user.top_up_amount

            # Round to 2 decimals
            rounded_amount = round(original_amount, 2)

            # Fix negatives (shouldn't exist but just in case)
            if rounded_amount < 0:
                rounded_amount = 0.0
                negative_count += 1
                print(f"⚠️  User {user.telegram_id}: Fixed negative balance {original_amount:.10f} → 0.00")

            # Check if rounding changed anything
            if original_amount != rounded_amount:
                user.top_up_amount = rounded_amount
                fixed_count += 1

                # Only log if significant difference (> 0.01)
                if abs(original_amount - rounded_amount) > 0.01:
                    print(f"🔧 User {user.telegram_id}: {original_amount:.10f} → {rounded_amount:.2f}")

        # Commit changes
        if fixed_count > 0:
            await session.commit()
            print(f"\n✅ Fixed {fixed_count} wallet balances")
            if negative_count > 0:
                print(f"⚠️  Fixed {negative_count} negative balances")
        else:
            print("\n✅ All wallet balances are already correctly rounded")


if __name__ == "__main__":
    print("=" * 60)
    print("Wallet Rounding Migration")
    print("=" * 60)
    print()

    try:
        asyncio.run(fix_wallet_rounding())
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
