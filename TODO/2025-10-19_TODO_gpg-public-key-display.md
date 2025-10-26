# GPG Public Key Display

**Date:** 2025-10-19
**Priority:** Low
**Estimated Effort:** Low (30 minutes)

---

## Description
Display the shop administrator's public GPG key in the main menu to enable users to verify encrypted communications and understand encryption options for sensitive data like shipping addresses.

## User Story
As a privacy-conscious customer, I want to see the shop's public GPG key, so that I can verify the identity of the shop and optionally encrypt sensitive information before sending it.

## Acceptance Criteria
- [ ] Main menu has "🔐 GPG Public Key" button
- [ ] Clicking button shows formatted public key in message
- [ ] Message includes:
  - Full ASCII-armored public key block
  - Key fingerprint
  - Key expiration date (if applicable)
  - Short explanation of what GPG is
  - Link to GPG tutorial (optional)
- [ ] "Copy Key" functionality (user can select and copy)
- [ ] Back button to return to main menu
- [ ] Localization (DE/EN)

## Technical Notes

### Configuration (.env)
```bash
GPG_PUBLIC_KEY_FILE=/path/to/pubkey.asc
GPG_KEY_FINGERPRINT=ABCD1234EFGH5678...
```

### Implementation
Simple handler that reads public key file and displays it as monospace text with fingerprint and instructions.

## Implementation Order
1. Add GPG configuration to `.env` and `config.py`
2. Store public key file in project directory
3. Add "GPG Public Key" button to main user menu
4. Implement `show_gpg_public_key()` handler
5. Add localization keys
6. Testing: View key, verify formatting, copy key

## Dependencies
- Requires GPG public key file
- No database changes needed

---

**Status:** Planned