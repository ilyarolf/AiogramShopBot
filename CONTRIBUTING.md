# Contributing to AiogramShopBot

Thank you for your interest in contributing to AiogramShopBot.

This document explains how to propose changes, report bugs, and submit pull requests in a way that is easy to review and maintain.

## Ways to contribute

You can help by:

- reporting bugs
- improving documentation
- fixing typos and broken links
- proposing new features
- submitting code improvements
- improving tests, deployment, and developer experience

## Before you start

Please:

1. Search existing issues and pull requests first.
2. Open an issue before starting large changes.
3. Keep changes focused and easy to review.

For small fixes such as typos, wording, or broken links, you can usually open a pull request directly.

## Reporting bugs

When reporting a bug, include as much useful context as possible:

- what you expected to happen
- what actually happened
- steps to reproduce the issue
- logs or error messages
- environment details
  - Python version
  - OS
  - database type and version
  - Redis version
  - deployment method (local, Docker, VPS)

## Suggesting features

When suggesting a feature, please describe:

- the problem you are trying to solve
- why the feature is useful
- a possible implementation idea
- whether it affects users, admins, deployment, or integrations

## Pull request guidelines

Please follow these rules when opening a pull request:

- keep PRs small and focused
- update documentation when behavior changes
- avoid unrelated refactors in the same PR
- use clear commit messages
- explain the purpose of the change in the PR description

A good pull request usually includes:

- a short summary
- the motivation for the change
- screenshots or logs if relevant
- notes about backward compatibility

## Code style

General expectations:

- prefer readable and explicit code
- keep functions focused and maintainable
- avoid unnecessary complexity
- preserve existing project structure unless refactoring is justified

If you introduce a new dependency, explain why it is needed.

## Documentation changes

Documentation improvements are very welcome.

If you change:

- setup flow
- environment variables
- admin behavior
- user-facing flows
- referral or payment logic

please update the related documentation as part of the same pull request.

## Security-related changes

Do not open a public issue for sensitive vulnerabilities.

Please follow the instructions in [SECURITY.md](SECURITY.md).

## Review process

Maintainers may request:

- code changes
- documentation updates
- a smaller scope
- clarification about architecture decisions

Not every contribution can be merged, but thoughtful contributions are appreciated.

## License

By contributing to this repository, you agree that your contributions will be licensed under the same license as the project.
