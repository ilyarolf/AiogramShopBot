-- Migration: Add shipping fields to items table
-- Date: 2025-01-23
-- Branch: feature/shipping-management-v2
-- Description: Adds is_physical, shipping_cost, and allows_packstation columns to items table

-- Add is_physical column (default: false for existing items)
ALTER TABLE items ADD COLUMN is_physical BOOLEAN NOT NULL DEFAULT 0;

-- Add shipping_cost column (default: 0.0 for existing items)
ALTER TABLE items ADD COLUMN shipping_cost REAL NOT NULL DEFAULT 0.0;

-- Add allows_packstation column (default: false for existing items)
ALTER TABLE items ADD COLUMN allows_packstation BOOLEAN NOT NULL DEFAULT 0;

-- Verify columns were added
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='items';
