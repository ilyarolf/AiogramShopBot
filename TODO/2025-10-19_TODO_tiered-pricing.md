# Tiered Pricing (Staffelpreise)

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** High (3-4 hours)

---

## Description
Implement a flexible tiered pricing system where items can have different price points based on quantity purchased. Each item can define its own quantity tiers (e.g., 1, 5, 10, 25) with corresponding unit prices. Customers are incentivized to buy larger quantities as the unit price decreases with higher tiers. Customers manually select tier quantities and are responsible for choosing the optimal combination themselves.

## User Story
As a shop administrator, I want to configure tiered pricing for individual products, so that customers receive quantity discounts and are encouraged to purchase larger amounts.

## Acceptance Criteria
- [ ] JSON import format supports tiered pricing configuration (**TXT format NOT supported**)
- [ ] Each item can have 1-N price tiers (quantity → unit price)
- [ ] Items with single tier (e.g., only "1: €10.50") have fixed pricing
- [ ] Items with multiple tiers offer quantity discounts
- [ ] Quantity selector shows ONLY available tier quantities as buttons (e.g., "1x", "5x", "10x", "25x")
- [ ] **NO free-text quantity input** - customer can only select from configured tier buttons
- [ ] Price details are displayed in the message text above buttons
- [ ] Buttons show only quantity labels (e.g., "1x", "5x"), NOT prices
- [ ] Customer can add multiple quantities of the same tier to cart
  - Example: Customer can click "10x" button three times to get 30 units total (3 separate cart items)
- [ ] Each tier quantity added to cart is a separate cart item with its tier price
- [ ] Customer is responsible for choosing optimal combination (no automatic optimization)

## Technical Notes

### NEW JSON Format
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "description": "Organic Dragon Well green tea",
  "private_data": "TEA-DRAGONWELL-UNIT061",
  "price_tiers": [
    {"quantity": 1, "unit_price": 11.00},
    {"quantity": 5, "unit_price": 9.00},
    {"quantity": 10, "unit_price": 7.50},
    {"quantity": 25, "unit_price": 6.00}
  ]
}
```

### Database Changes
- Create new `price_tiers` table with columns: `id`, `item_id`, `quantity`, `unit_price`
- Relationship: `Item.price_tiers` (one-to-many)
- Repository: `PriceTierRepository` with CRUD operations

### UI Example
```
Green Tea - Organic Dragon Well

Prices:
• 1 pc: €11.00/pc (€11.00 total)
• 5 pc: €9.00/pc (€45.00 total)
• 10 pc: €7.50/pc (€75.00 total)

Select quantity:
[1x] [5x] [10x] [25x]
```

## Dependencies
- Requires database migration for `price_tiers` table
- Must update `ItemRepository.add_many()` to return created items (for getting IDs)
- UI changes to quantity selector

---

**Status:** Planned