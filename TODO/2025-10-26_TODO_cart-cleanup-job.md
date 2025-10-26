# Cart Cleanup Job

**Date:** 2025-10-26
**Priority:** Medium
**Estimated Effort:** Low (1-2 hours)

---

## Description
Implement automated cleanup for abandoned carts and cart items from inactive users. Currently, carts accumulate indefinitely which can lead to database bloat and stale data.

## User Story
As a system administrator, I want old carts to be automatically cleaned up so that the database stays lean and I can identify truly active vs inactive users.

## Acceptance Criteria
- [ ] Cleanup job runs daily (integrated with `data_retention_cleanup_job.py`)
- [ ] Deletes cart items from users inactive for > 90 days (configurable)
- [ ] Preserves carts from recently active users
- [ ] Logs cleanup statistics (number of carts/items deleted)
- [ ] Does NOT delete the Cart model itself (one cart per user)
- [ ] Only deletes CartItem entries

## Technical Implementation

### Configuration
Add to `config.py`:
```python
CART_CLEANUP_INACTIVE_DAYS = 90  # Clean carts from users inactive > 90 days
```

### Cleanup Logic
Add to `jobs/data_retention_cleanup_job.py`:

```python
async def cleanup_inactive_user_carts():
    """
    Deletes cart items from users who haven't been active in CART_CLEANUP_INACTIVE_DAYS.
    Activity is determined by last_active timestamp in User model.
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.CART_CLEANUP_INACTIVE_DAYS)

        # Find users inactive for > cutoff_date
        inactive_users_stmt = select(User).where(User.last_active < cutoff_date)
        result = await session.execute(inactive_users_stmt)
        inactive_users = result.scalars().all()

        if not inactive_users:
            logging.info(f"[Cart Cleanup] No inactive users (> {config.CART_CLEANUP_INACTIVE_DAYS} days)")
            return

        inactive_user_ids = [user.id for user in inactive_users]

        # Count cart items to delete
        count_stmt = select(CartItem).join(Cart).where(Cart.user_id.in_(inactive_user_ids))
        result = await session.execute(count_stmt)
        cart_items = result.scalars().all()
        count = len(cart_items)

        if count == 0:
            logging.info(f"[Cart Cleanup] No cart items from inactive users")
            return

        # Delete cart items (keep Cart model)
        delete_stmt = delete(CartItem).where(
            CartItem.cart_id.in_(
                select(Cart.id).where(Cart.user_id.in_(inactive_user_ids))
            )
        )
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Cart Cleanup] ✅ Deleted {count} cart items from {len(inactive_users)} inactive users")
```

### Integration
Add to `run_data_retention_cleanup()` in `data_retention_cleanup_job.py`:
```python
await cleanup_inactive_user_carts()
```

## Alternative Approach: Time-based (without user activity tracking)

If `User.last_active` doesn't exist, use cart item creation time:

```python
async def cleanup_old_cart_items():
    """
    Deletes cart items older than CART_CLEANUP_INACTIVE_DAYS.
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.CART_CLEANUP_INACTIVE_DAYS)

        # Assuming CartItem has created_at field
        count_stmt = select(CartItem).where(CartItem.created_at < cutoff_date)
        result = await session.execute(count_stmt)
        count = len(result.scalars().all())

        if count == 0:
            logging.info(f"[Cart Cleanup] No cart items older than {config.CART_CLEANUP_INACTIVE_DAYS} days")
            return

        delete_stmt = delete(CartItem).where(CartItem.created_at < cutoff_date)
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Cart Cleanup] ✅ Deleted {count} cart items older than {config.CART_CLEANUP_INACTIVE_DAYS} days")
```

## Testing
- [ ] Add cart items to test user
- [ ] Mock last_active timestamp to > 90 days ago
- [ ] Run cleanup job manually: `python -m jobs.data_retention_cleanup_job`
- [ ] Verify cart items deleted but Cart model remains
- [ ] Verify active user carts untouched

## Notes
- Cart model itself should NOT be deleted (one cart per user by design)
- Only CartItem entries are removed
- This prevents cart table bloat while preserving user cart structure
- Consider adding `last_modified` timestamp to Cart model for better tracking

---

**Status:** Planned
