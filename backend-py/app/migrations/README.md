# SaaS Database Migrations

This directory contains forward SQL migrations for the V0.03 SaaS schema.

The first phase keeps migrations as plain SQL so the project can move carefully
before choosing a full migration runner such as Alembic.

Rules:

- Migration filenames use an ordered prefix, for example `0001_auth.sql`.
- Migrations are written for PostgreSQL.
- Local file storage remains supported until `XIAOMAN_STORAGE_BACKEND=postgres`
  is fully implemented.

Current migrations:

- `0001_auth.sql`: tenants, users, auth sessions, and devices.
- `0002_core_storage.sql`: companions, profiles, chat sessions, messages, chunks,
  world layers, memory facts, memory documents, and life events.
