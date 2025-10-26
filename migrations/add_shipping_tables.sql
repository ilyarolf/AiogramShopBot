-- Migration: Add shipping-related tables and fields
-- Date: 2025-01-23
-- Branch: feature/shipping-management-v2
-- Description: Adds shipping_addresses table and shipping_cost field to orders table

-- Add shipping_cost column to orders table
ALTER TABLE orders ADD COLUMN shipping_cost REAL NOT NULL DEFAULT 0.0;

-- Add shipped_at column to orders table
ALTER TABLE orders ADD COLUMN shipped_at DATETIME;

-- Create shipping_addresses table
CREATE TABLE IF NOT EXISTS shipping_addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    encrypted_address BLOB NOT NULL,
    nonce BLOB NOT NULL,
    tag BLOB NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_shipping_addresses_order_id ON shipping_addresses(order_id);

-- Verify tables and columns
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='orders';
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='shipping_addresses';
