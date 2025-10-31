# Strike System and User Ban Management

**Date:** 2025-10-19
**Priority:** High
**Estimated Effort:** High (2-3 hours)

---

## Description
Implement a comprehensive strike and ban system to prevent users with multiple violations from placing orders. Users receive strikes for order timeouts and late cancellations. After reaching a strike limit, users are banned and shown a ban message instead of normal shop functionality.

## User Story
As a shop administrator, I want to automatically ban users who repeatedly cancel orders late or let them timeout, so that I can maintain order quality and prevent abuse of the reservation system.

## Acceptance Criteria
- [ ] User model includes `strikes` counter, `is_banned` flag, and `ban_reason` field
- [ ] Strikes are incremented when:
  - Order times out (TIMEOUT status)
  - User cancels order after grace period expires
- [ ] User is automatically banned when strike limit is reached (configurable, e.g., 3 strikes)
- [ ] Banned users see a ban message with:
  - Clear statement that they are banned
  - The reason for the ban (e.g., "Too many order cancellations/timeouts")
  - Instructions to contact support
- [ ] Banned users cannot:
  - Add items to cart
  - View cart (shows ban message instead)
  - Place orders
  - Access checkout
- [ ] Cart is automatically cleared when banned user tries to access it
- [ ] Localization keys for ban messages in German and English
- [ ] Admin can manually unban users (future enhancement)

## Technical Notes

### Database Changes
Add to User model:
```python
strikes = Column(Integer, default=0)
is_banned = Column(Boolean, default=False)
ban_reason = Column(String, nullable=True)
banned_at = Column(DateTime, nullable=True)
```

### Strike Logic
Implement in `OrderService`:
- `increment_strike(user_id, reason)` - Adds strike and checks ban threshold
- Auto-ban when `strikes >= BAN_STRIKE_THRESHOLD` (config value)

Call `increment_strike()` from:
- `OrderService.cancel_order_by_user()` when `within_grace_period == False`
- Timeout job when marking orders as TIMEOUT

### Ban Middleware/Guard
- Create `BanCheckMiddleware` or add to existing middleware
- Check `user.is_banned` on every cart/order operation
- Redirect banned users to ban message view
- Clear cart if banned user has items

### Ban Message View
Create `CartService.show_ban_message()` method displaying:
- Ban icon and header
- Ban reason (from `user.ban_reason`)
- Support contact link (from config)
- No action buttons (prevent any shopping actions)

### Localization Keys (DE/EN)
- `user_banned_title`: "Account Suspended" / "Account gesperrt"
- `user_banned_message`: Message template with {reason} and {support_link}
- `ban_reason_strikes`: "Multiple order violations (timeouts/late cancellations)"
- `ban_contact_support`: "Please contact support if you have questions"

### Configuration
- `BAN_STRIKE_THRESHOLD` (default: 3)
- `SUPPORT_LINK` (already exists in config)
- `UNBAN_FEE_MULTIPLIER` (e.g., 5.0 - makes it hurt 😈)

### TODO: Self-Unban (Paid Unban Feature)
**Priority:** Medium
**Evil Factor:** 💀💀💀💀💀

Allow banned users to pay their way out of ban (this should HURT):
- [ ] Add "Unban yourself" option in ban message
- [ ] Calculate unban fee: `unban_fee = order_value_average * strikes * UNBAN_FEE_MULTIPLIER`
  - Example: User with 3 strikes, average order €50 → Unban fee = €50 * 3 * 5.0 = €750
- [ ] Require payment via wallet deposit
- [ ] After payment:
  - Reset `strikes` to 0
  - Set `is_banned` to False
  - Log unban event with amount paid
  - Send notification to admin (user paid €XXX to get unbanned)
- [ ] Repeat offenders: Fee increases exponentially
  - First unban: 1x multiplier
  - Second unban: 2x multiplier (€1500 in example above)
  - Third unban: 4x multiplier (€3000 in example above)
- [ ] Track `unban_count` in User model
- [ ] Show warning: "Next ban will cost 2x as much"
- [ ] Localization:
  - `unban_offer`: "Möchten Sie Ihren Account freikaufen? Das kostet {unban_fee}€"
  - `unban_warning`: "Bei erneutem Verstoß verdoppelt sich die Freikauf-Gebühr!"
  - `unban_success`: "Account erfolgreich freigeschaltet. Verbleibende Gebühr: {unban_fee}€"

**Note:** This is intentionally designed to be expensive to discourage repeat violations while giving users a way to recover their account.

## Implementation Order
1. Database model changes (add strike/ban fields)
2. Strike increment logic in OrderService
3. Auto-ban logic when threshold reached
4. Ban check middleware
5. Ban message view
6. Cart clearing for banned users
7. Localization keys
8. Integration with timeout job
9. Testing with multiple scenarios

## Dependencies
- Requires timeout job to be implemented (for TIMEOUT strikes) ✅ DONE
- Requires User model migrations ✅ DONE

## Implementation Status

### Completed Features
- ✅ Database model with UserStrike table (separate table instead of counter)
- ✅ Strike increment logic in OrderService
- ✅ Auto-ban logic when threshold reached (configurable via MAX_STRIKES_BEFORE_BAN)
- ✅ Ban check via IsUserExistFilter
- ✅ Ban message with unban instructions
- ✅ Localization keys (DE/EN)
- ✅ Integration with timeout job
- ✅ Strike statistics display in user profile
- ✅ Wallet top-up unban system (UNBAN_TOP_UP_AMOUNT config)
- ✅ Admin exemption from bans (EXEMPT_ADMINS_FROM_BAN config)
- ✅ Banned users can access Support/FAQ
- ✅ Informative ban message with unban instructions

### Pending Features
- ⏳ Admin manual unban functionality
- ⏳ Admin notification when user gets banned
- ⏳ Testing with multiple scenarios

---

**Status:** Testing