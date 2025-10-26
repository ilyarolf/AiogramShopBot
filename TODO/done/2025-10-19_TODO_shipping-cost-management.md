# Shipping Cost Management

**Date:** 2025-10-19
**Priority:** Medium
**Estimated Effort:** Medium-High (1.5-2 hours)

---

## Description
Implement a shipping cost system where items can optionally have shipping costs. When an order is created, the highest shipping cost among all items in the order is applied once. The shipping cost is included in the order total price but displayed as a separate line item in the invoice and cart view.

## User Story
As a shop administrator, I want to configure shipping costs for physical products, so that customers are charged the appropriate shipping fee based on the most expensive shipping method required in their order.

## Acceptance Criteria
- [ ] JSON import format supports optional shipping cost configuration
- [ ] Items without shipping cost have `shipping_cost = 0.0` (default)
- [ ] Items with shipping cost have a positive float value (e.g., 0.99, 1.50, 5.99)
- [ ] When order is created, calculate max shipping cost: `max(item.shipping_cost for item in order_items)`
- [ ] Order `total_price` includes shipping: `total_price = items_sum + max_shipping_cost`
- [ ] Order model stores shipping cost separately for invoice display
- [ ] Cart view displays shipping cost breakdown:
  - "Items: €15.00"
  - "Shipping: €5.99"
  - "Total: €20.99"
- [ ] Invoice displays shipping as separate line item
- [ ] Multiple identical items share single shipping cost (max shipping applies once per order)
- [ ] If all items have no shipping cost, order has €0.00 shipping

## Technical Notes

### NEW JSON Format
```json
{
  "category": "Tea",
  "subcategory": "Green Tea",
  "price": 12.25,
  "description": "Organic Dragon Well green tea",
  "private_data": "TEA-DRAGONWELL-UNIT061",
  "shipping_cost": 1.50
}
```

### Database Changes
- Add `Item.shipping_cost` field (Float, nullable=False, default=0.0)
- Add `Order.shipping_cost` field (Float, nullable=False, default=0.0)

### Order Calculation Example
```
Cart:
- 2x Green Tea (€12.00 each, €1.50 shipping)
- 1x Premium Tea (€25.00, €5.99 shipping)
- 1x eBook (€9.99, €0.00 shipping)

Calculation:
- Items total: €58.99
- Max shipping: max(€1.50, €5.99, €0.00) = €5.99
- Order total: €58.99 + €5.99 = €64.98
```

## Dependencies
- Requires database migration for `shipping_cost` fields in Item and Order tables
- Must update all cart/order display logic
- Localization updates required

---

**Status:** Planned