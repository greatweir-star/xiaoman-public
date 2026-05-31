# Xiaoman Legacy TypeScript Backend

This directory is kept as legacy/reference code.

For V0.03 SaaS migration, the main backend is:

```text
backend-py
```

Do not add new product behavior to this TypeScript backend unless a migration task explicitly asks to port logic from it.

Recommended use of this directory:

- Read older implementation ideas.
- Compare API or gateway behavior during migration.
- Port useful logic into `backend-py` with tests.

Non-goals:

- No new SaaS auth implementation here.
- No new PostgreSQL repository implementation here.
- No new WebSocket gateway behavior here.
- No production deployment path from this directory.
