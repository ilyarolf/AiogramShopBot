# Contributing to AiogramShopBot

Thanks for your interest in improving AiogramShopBot.

## Before You Start

- Read [README.md](readme.md) and [docs.md](docs.md).
- Open an issue first for large changes, architectural changes, or behavior changes.
- Keep changes incremental and easy to review.

## Development Setup

```bash
git clone https://github.com/ilyarolf/AiogramShopBot.git
cd AiogramShopBot
pip install -r requirements.txt
python run.py
```

You will also need PostgreSQL, Redis, and environment variables configured.

## Contribution Guidelines

- Preserve existing architecture and naming style.
- Avoid broad refactors unless they are necessary.
- Keep payment, balance, invoice, callback, and order logic conservative.
- Update JSON localization files for user-facing text changes.
- Add or update tests for changed behavior.
- Keep pull requests focused.

## Pull Request Checklist

- The change is scoped and reviewable.
- Tests were added or updated when appropriate.
- Documentation was updated if behavior changed.
- No unrelated cleanup was bundled in.
- Sensitive financial behavior was not changed silently.

## Areas That Need Extra Care

- Payments and callbacks
- Balance updates
- Multibot behavior
- Database queries and migrations
- Localization keys and admin/user flows

## Questions

For discussion or coordination:

- Telegram: [@ilyarolf_dev](https://t.me/ilyarolf_dev)
