# Security Policy

## Supported versions

Security support is provided on a best-effort basis for the most actively maintained code in the default branch.

If versioned releases are introduced later, this table can be updated.

| Version                 | Supported |
|-------------------------|-----------|
| Default branch          | ✅         |
| Older snapshots / forks | ❌         |

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Instead, report vulnerabilities privately through one of the following channels:

- Telegram: [@ilyarolf_dev](https://t.me/ilyarolf_dev)

When possible, include:

- a short description of the issue
- affected component or feature
- steps to reproduce
- proof of concept if available
- impact assessment
- any suggested fix or mitigation

## What to expect

After a private report is received, the maintainer will try to:

1. confirm the issue
2. assess the severity and impact
3. prepare a fix or mitigation
4. publish the patch when appropriate

Response and remediation times are best-effort and may vary depending on the complexity of the issue.

## Scope

Examples of security-relevant areas may include:

- authentication and admin access
- webhook validation
- JWT handling
- SQLAdmin access control
- payment logic and forwarding logic
- secrets and environment variable handling
- deployment and reverse proxy misconfiguration

## Disclosure policy

Please allow reasonable time for the vulnerability to be reviewed and fixed before public disclosure.

Responsible disclosure helps protect users and deployments of the project.
