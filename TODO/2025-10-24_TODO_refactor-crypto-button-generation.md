# Refactor Crypto Button Generation

**Date:** 2025-10-24
**Priority:** Low
**Estimated Effort:** Low (30-45 minutes)

---

## Description
Refactor the cryptocurrency payment button generation from hardcoded repetitive button calls into a generic loop-based approach. Currently, `_show_crypto_selection_screen()` contains 8 individual button creation calls that are repetitive and error-prone.

## User Story
As a developer, I want to maintain cryptocurrency payment buttons in a centralized, declarative way, so that adding/removing cryptocurrencies or changing button order is simple and less error-prone.

## Acceptance Criteria
- [ ] Replace 8 individual `kb_builder.button()` calls with a loop
- [ ] Create mapping between Cryptocurrency enum and localization keys
- [ ] Support mixed `BotEntity` values (COMMON vs USER) in mapping
- [ ] Maintain current button order and layout (2 columns via `adjust(2)`)
- [ ] No functional changes to user-facing behavior
- [ ] Apply same pattern to `show_crypto_selection_without_physical_check()` (duplicate code)

## Technical Notes

### Current Code (Repetitive)
```python
def _show_crypto_selection_screen() -> tuple[str, InlineKeyboardBuilder]:
    kb_builder = InlineKeyboardBuilder()

    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
        callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.BTC)
    )
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "eth_top_up"),
        callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.ETH)
    )
    # ... 6 more identical blocks
```

### Proposed Refactoring - Option A: Enum Method
Add method to `Cryptocurrency` enum:
```python
class Cryptocurrency(str, Enum):
    BTC = "BTC"
    ETH = "ETH"
    # ...

    def get_localization_key(self) -> tuple[BotEntity, str]:
        """Returns (entity, key) for top-up button text"""
        mapping = {
            Cryptocurrency.BTC: (BotEntity.COMMON, "btc_top_up"),
            Cryptocurrency.ETH: (BotEntity.COMMON, "eth_top_up"),
            Cryptocurrency.LTC: (BotEntity.COMMON, "ltc_top_up"),
            Cryptocurrency.SOL: (BotEntity.COMMON, "sol_top_up"),
            Cryptocurrency.BNB: (BotEntity.COMMON, "bnb_top_up"),
            Cryptocurrency.USDT_TRC20: (BotEntity.USER, "usdt_trc20_top_up"),
            Cryptocurrency.USDT_ERC20: (BotEntity.USER, "usdt_erc20_top_up"),
            Cryptocurrency.USDC_ERC20: (BotEntity.USER, "usdc_erc20_top_up"),
        }
        return mapping[self]

    @staticmethod
    def get_payment_options() -> list['Cryptocurrency']:
        """Returns list of cryptocurrencies available for payment"""
        return [
            Cryptocurrency.BTC,
            Cryptocurrency.ETH,
            Cryptocurrency.LTC,
            Cryptocurrency.SOL,
            Cryptocurrency.BNB,
            Cryptocurrency.USDT_TRC20,
            Cryptocurrency.USDT_ERC20,
            Cryptocurrency.USDC_ERC20,
        ]
```

Then refactor button generation:
```python
def _show_crypto_selection_screen() -> tuple[str, InlineKeyboardBuilder]:
    message_text = Localizator.get_text(BotEntity.USER, "choose_payment_crypto")
    kb_builder = InlineKeyboardBuilder()

    for crypto in Cryptocurrency.get_payment_options():
        entity, key = crypto.get_localization_key()
        kb_builder.button(
            text=Localizator.get_text(entity, key),
            callback_data=CartCallback.create(4, cryptocurrency=crypto)
        )

    kb_builder.adjust(2)
    kb_builder.row(CartCallback.create(0).get_back_button(0))

    return message_text, kb_builder
```

### Proposed Refactoring - Option B: Config Constant
Create constant in `config.py` or separate config file:
```python
PAYMENT_CRYPTO_CONFIG = [
    (Cryptocurrency.BTC, BotEntity.COMMON, "btc_top_up"),
    (Cryptocurrency.ETH, BotEntity.COMMON, "eth_top_up"),
    (Cryptocurrency.LTC, BotEntity.COMMON, "ltc_top_up"),
    (Cryptocurrency.SOL, BotEntity.COMMON, "sol_top_up"),
    (Cryptocurrency.BNB, BotEntity.COMMON, "bnb_top_up"),
    (Cryptocurrency.USDT_TRC20, BotEntity.USER, "usdt_trc20_top_up"),
    (Cryptocurrency.USDT_ERC20, BotEntity.USER, "usdt_erc20_top_up"),
    (Cryptocurrency.USDC_ERC20, BotEntity.USER, "usdc_erc20_top_up"),
]
```

### Inconsistent Localization Keys (Blocker?)
Current keys use mixed `BotEntity` values:
- `BotEntity.COMMON`: BTC, ETH, LTC, SOL, BNB
- `BotEntity.USER`: USDT_TRC20, USDT_ERC20, USDC_ERC20

**Decision needed:** Keep mixed entities in mapping, or first migrate all keys to `BotEntity.COMMON`?

### Implementation Order
1. **Choose approach:** Enum method (Option A) vs Config constant (Option B)
2. Add localization mapping structure
3. Refactor `_show_crypto_selection_screen()`
4. Refactor `show_crypto_selection_without_physical_check()` (same pattern)
5. Test all crypto button selections in bot
6. Verify button order and layout unchanged

## Dependencies
- None (self-contained refactoring)

## Future Enhancements
- Could extend to wallet top-up buttons (duplicate code in wallet handlers)
- Consider standardizing all crypto-related localization keys to `BotEntity.COMMON`

---

**Status:** Planned
