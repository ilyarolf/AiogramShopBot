"""
Migration script: Convert from Category+Subcategory to tree-based Category model.

This script:
1. Creates new categories table with tree structure
2. Migrates old categories and subcategories to tree structure
3. Updates items to reference new product categories
4. Updates cart_items to reference new product categories
5. Cleans up old subcategories table

IMPORTANT: Backup your database before running this migration!

Usage:
    python -m migrations.migrate_to_tree_categories
"""

import asyncio
import sqlite3
import os
from pathlib import Path


def migrate_database(db_path: str = "shop.db"):
    """
    Migrate from old category/subcategory structure to tree-based categories.
    """
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    # Create backup
    backup_path = f"{db_path}.backup"
    print(f"Creating backup at {backup_path}...")
    import shutil
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Check if migration is needed
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subcategories'")
        if not cursor.fetchone():
            print("No subcategories table found. Migration may have already been applied.")
            return True

        print("Starting migration...")

        # Step 2: Create new categories table if it doesn't have the new columns
        cursor.execute("PRAGMA table_info(categories)")
        columns = {col[1] for col in cursor.fetchall()}

        if 'parent_id' not in columns:
            print("Adding new columns to categories table...")
            cursor.execute("ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE")
            cursor.execute("ALTER TABLE categories ADD COLUMN is_product BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE categories ADD COLUMN image_file_id TEXT")
            cursor.execute("ALTER TABLE categories ADD COLUMN description TEXT")
            cursor.execute("ALTER TABLE categories ADD COLUMN price REAL")

        # Step 3: Get all old categories and subcategories
        cursor.execute("SELECT id, name FROM categories")
        old_categories = cursor.fetchall()
        print(f"Found {len(old_categories)} old categories")

        cursor.execute("SELECT id, name, category_id FROM subcategories")
        old_subcategories = cursor.fetchall()
        print(f"Found {len(old_subcategories)} old subcategories")

        # Step 4: Get price and description from items (grouped by subcategory)
        cursor.execute("""
            SELECT subcategory_id, price, description
            FROM items
            WHERE subcategory_id IS NOT NULL
            GROUP BY subcategory_id
        """)
        subcategory_prices = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        # Step 5: Create mapping of old subcategory_id to new category_id
        # We'll create product categories as children of navigation categories
        subcategory_to_new_category = {}

        for subcat_id, subcat_name, old_cat_id in old_subcategories:
            price, description = subcategory_prices.get(subcat_id, (0.0, None))

            # Insert new product category as child of old category
            cursor.execute("""
                INSERT INTO categories (name, parent_id, is_product, price, description)
                VALUES (?, ?, 1, ?, ?)
            """, (subcat_name, old_cat_id, price, description))

            new_cat_id = cursor.lastrowid
            subcategory_to_new_category[subcat_id] = new_cat_id
            print(f"  Created product category '{subcat_name}' (id={new_cat_id}) under parent {old_cat_id}")

        # Step 6: Update items to reference new product categories
        print("Updating items to reference new product categories...")
        for old_subcat_id, new_cat_id in subcategory_to_new_category.items():
            cursor.execute("""
                UPDATE items
                SET category_id = ?
                WHERE subcategory_id = ?
            """, (new_cat_id, old_subcat_id))
            rows_updated = cursor.rowcount
            print(f"  Updated {rows_updated} items from subcategory {old_subcat_id} to category {new_cat_id}")

        # Step 7: Update cart_items to reference new product categories
        print("Updating cart_items to reference new product categories...")
        cursor.execute("PRAGMA table_info(cart_items)")
        cart_columns = {col[1] for col in cursor.fetchall()}

        if 'subcategory_id' in cart_columns:
            for old_subcat_id, new_cat_id in subcategory_to_new_category.items():
                cursor.execute("""
                    UPDATE cart_items
                    SET category_id = ?
                    WHERE subcategory_id = ?
                """, (new_cat_id, old_subcat_id))
                rows_updated = cursor.rowcount
                if rows_updated > 0:
                    print(f"  Updated {rows_updated} cart_items from subcategory {old_subcat_id}")

        # Step 8: Drop subcategory_id columns and subcategories table
        print("Cleaning up old structure...")

        # SQLite doesn't support DROP COLUMN directly, so we need to recreate tables
        # For items table
        cursor.execute("PRAGMA table_info(items)")
        items_columns = cursor.fetchall()
        if any(col[1] == 'subcategory_id' for col in items_columns):
            print("  Removing subcategory_id from items table...")
            cursor.execute("""
                CREATE TABLE items_new (
                    id INTEGER PRIMARY KEY,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    private_data TEXT NOT NULL,
                    is_sold BOOLEAN DEFAULT 0,
                    is_new BOOLEAN DEFAULT 1
                )
            """)
            cursor.execute("""
                INSERT INTO items_new (id, category_id, private_data, is_sold, is_new)
                SELECT id, category_id, private_data, is_sold, is_new FROM items
            """)
            cursor.execute("DROP TABLE items")
            cursor.execute("ALTER TABLE items_new RENAME TO items")

        # For cart_items table
        if 'subcategory_id' in cart_columns:
            print("  Removing subcategory_id from cart_items table...")
            cursor.execute("""
                CREATE TABLE cart_items_new (
                    id INTEGER PRIMARY KEY,
                    cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                    quantity INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                INSERT INTO cart_items_new (id, cart_id, category_id, quantity)
                SELECT id, cart_id, category_id, quantity FROM cart_items
            """)
            cursor.execute("DROP TABLE cart_items")
            cursor.execute("ALTER TABLE cart_items_new RENAME TO cart_items")

        # Drop old subcategories table
        print("  Dropping subcategories table...")
        cursor.execute("DROP TABLE IF EXISTS subcategories")

        # Step 9: Update old navigation categories to have is_product=0
        cursor.execute("UPDATE categories SET is_product = 0 WHERE is_product IS NULL")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print(f"Backup saved at: {backup_path}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        print(f"Database restored from backup")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "shop.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
