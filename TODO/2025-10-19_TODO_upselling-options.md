# Upselling Options (Optional Add-ons)

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** High (3-4 hours)

---

## Description
Implement an optional upselling system where items can offer additional options like premium packaging or insured shipping. Users select quantity first, then see upselling options in a second step before adding to cart. Each cart item can have different upselling selections.

## User Story
As a shop administrator, I want to offer optional add-ons like premium packaging and insured shipping for products, so that customers can customize their purchase and I can increase revenue through upselling.

## Acceptance Criteria
- [ ] JSON import format supports optional upselling configuration (**TXT format NOT supported**)
- [ ] Items without upsells go directly to cart after quantity selection (current behavior)
- [ ] Items with upsells show a second step with upselling options after quantity selection
- [ ] Two upsell types supported:
  - **Packaging:** Per-item option (e.g., "Standard" (free) vs "Premium" (+€4.00))
  - **Shipping Insurance:** Per-order option (e.g., "Standard shipping" vs "Insured shipping" (replaces standard shipping cost))
- [ ] User flow:
  1. Select quantity (e.g., "10x")
  2. See upselling options screen with toggleable buttons
  3. Click "Add to Cart" to confirm selection
- [ ] Upselling screen shows:
  - Selected item and quantity
  - Base price calculation
  - Packaging options (if configured)
  - Shipping options (if configured)
  - Total price preview
  - "Add to Cart" and "Cancel" buttons
- [ ] Each cart item stores its own upselling selections
- [ ] Multiple cart items of same product can have different upselling choices
- [ ] Cart displays upselling add-ons as sub-items with their prices
- [ ] Insured shipping replaces standard shipping cost (not additive)

## Technical Notes

### NEW JSON Format
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "price_tiers": [...],
  "shipping_cost": 1.50,
  "upsells": [
    {
      "type": "packaging",
      "name_key": "upsell_premium_packaging",
      "price": 4.00
    },
    {
      "type": "shipping_insurance",
      "name_key": "upsell_insured_shipping",
      "price": 3.00
    }
  ]
}
```

### Localization
Use localization keys (e.g., `upsell_premium_packaging`) instead of hardcoded names.

**In code:**
```python
upsell_name = Localizator.get_text(BotEntity.USER, upsell.name_key)
```

### Database Changes
- Create new `upsells` table with columns: `id`, `item_id`, `type`, `name_key`, `price`
- Update `CartItem` model: Add `selected_upsells` JSON field
- Upsell types enum: `PACKAGING`, `SHIPPING_INSURANCE`

### User Flow Example
```
Step 1: Quantity Selection
[1x] [5x] [10x] [25x]

↓ User clicks "10x"

Step 2: Upselling Screen
Green Tea - 10x
Basispreis: €75.00

📦 Verpackung:
[✓ Standard (inkl.)] [Komfort +€4.00]

🚚 Versand:
[✓ Standard €1.50] [Versichert €3.00]

Gesamt: €75.00

[✓ In Warenkorb legen] [✗ Abbrechen]
```

### Cart Display Example
```
Green Tea - 10x
  + Komfort-Verpackung €4.00
= €79.00

Green Tea - 10x = €75.00

Items: €154.00
Shipping: €3.00 (versichert)
Total: €157.00
```

## Dependencies
- Requires database migration for `upsells` table and `cart_items.selected_upsells` JSON field
- Requires callback data structure extension (careful: Telegram has 64-byte limit!)
- Requires new handler for upselling screen
- UI/UX requires careful design for toggle button behavior

## Technical Challenges
- **Callback Data Size Limit:** Telegram has 64-byte limit. Solution: Use compressed encoding `p123s456` for upsell IDs
- **N+1 Query Problem:** Use eager loading with JOINs
- **Upsell Consistency:** Store full upsell data in JSON (not just ID) to preserve pricing even if admin deletes upsell

---

**Status:** Planned