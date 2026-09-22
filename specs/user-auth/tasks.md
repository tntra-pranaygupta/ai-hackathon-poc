---
feature: user-auth
status: approved
owner: pranay.gupta
created: 2026-09-22
execution-strategy: Dependency Order
---

# Tasks: User Authentication

> `plan.md` is `status: approved`, constitution check fully ticked. This feature is foundational: `product-crud`'s tasks depend on T001/T002 (project/DB scaffolding) and T005/T010 (`get_current_user`) below.

Task ID format: `T001`, `T002`, … `[P]` marks tasks that can run in parallel with other `[P]` tasks at the same dependency level. `Satisfies: FR-NNN` links each task to spec.md; foundational tasks that don't map to one specific FR are marked accordingly.

- [x] **T001:** Scaffold the project: FastAPI app skeleton (`app/api`, `app/services`, `app/repositories`, `app/models`, `app/schemas`, `app/core`), Dockerfile, `docker-compose.yml` (services `api` + `db`), `requirements.txt` (fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, passlib[bcrypt], pyjwt, pytest, pytest-asyncio, httpx), `.env.example`.
      Satisfies: Foundational (blocks all FRs; also the project-level "runs entirely via Docker Compose, no host Postgres" requirement)
      Verify: `docker compose up --build` starts both containers with no PostgreSQL installed on the host; a root/health endpoint returns 200.

- [x] **T002:** Configure the async SQLAlchemy engine/session factory (reading `DATABASE_URL` from env) and initialize Alembic.
      Satisfies: Foundational
      Verify: `alembic upgrade head` runs against the Dockerized Postgres from a clean volume with no error.

- [x] **T003:** Define the `User` SQLAlchemy model and its Alembic migration for the `users` table (`id`, `email` unique, `password_hash`, `created_at`, `updated_at`) per `plan.md`'s data model.
      Satisfies: Foundational (data model for FR-001–FR-007)
      Verify: after `alembic upgrade head`, inspecting the `users` table shows exactly the columns/constraints/unique index specified in `plan.md`.

- [x] **T004 [P]:** Implement password hashing helpers (`hash_password`, `verify_password`) via `passlib[bcrypt]`, and enforce the 8–72 byte password length rule at the Pydantic schema level (ADR-1).
      Satisfies: FR-001, FR-003
      Verify: unit test confirms a 73-byte password is rejected with 422 (not silently truncated); a correct password verifies against its hash and an incorrect one does not.

- [x] **T005 [P]:** Implement `create_access_token` and `get_current_user` in `app/core/security.py` using PyJWT / HS256, reading `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default `30`) from env; claims `sub`/`iat`/`exp`.
      Satisfies: FR-006, FR-007
      Verify: unit tests — a token signed with the configured secret decodes to the correct user id; an expired token, a wrong-signature token, and a malformed token each raise 401.

- [x] **T006:** Implement `UserRepository` (async: `get_by_email`, `create`).
      Satisfies: Foundational (data access for FR-001, FR-002, FR-004, FR-005)
      Verify: repository test against the Dockerized test DB confirms create + `get_by_email` round-trip, and that inserting a duplicate email raises the DB-level unique-constraint error.

- [x] **T007:** Implement `AuthService.register` (duplicate-email check → hash → persist) plus `UserCreate`/`UserRead` Pydantic schemas.
      Satisfies: FR-001, FR-002, FR-003
      Verify: service-level tests — new email registers successfully and the returned object has no password field; duplicate email raises the error mapped to 409; invalid input (bad email format, short password) is rejected by the schema with 422 `details` before the service runs.

- [x] **T008:** Implement `AuthService.login`, including the timing-safe dummy-hash comparison for a non-existent email (dummy hash precomputed once at import time, per plan.md's Risks).
      Satisfies: FR-004, FR-005
      Verify: correct credentials return a decodable JWT with the expected claims; wrong password and non-existent email both return an identical 401 body; code review confirms the dummy hash is a module-level constant, not recomputed per request.

- [x] **T009:** Wire `POST /auth/register` and `POST /auth/login` routes (thin — delegate to `AuthService` only) plus the shared `{error, details?}` error-response formatter.
      Satisfies: FR-001, FR-002, FR-003, FR-004, FR-005
      Verify: `httpx.AsyncClient` integration test against the full app + Dockerized Postgres gets the exact status codes/bodies from `plan.md`'s API contract table for both endpoints.

- [x] **T010:** Confirm `get_current_user` is importable from a stable module path and add an integration test (using a throwaway protected test route) proving 401 on missing/expired/malformed/wrong-signature tokens and correct user-id resolution on a valid one.
      Satisfies: FR-006, FR-007
      Verify: the throwaway route returns 401 for each invalid-token case and 200 with the correct user id for a valid token, via `httpx.AsyncClient` against the real app.

## Dependencies between tasks

```
T001 (project/Docker scaffold)
  └─► T002 (DB engine + Alembic)
        └─► T003 (User model + migration)
              └─► T006 (UserRepository)
                    └─► T007 (AuthService.register)
                          └─► T008 (AuthService.login)
                                └─► T009 (routes)
                                      └─► T010 (get_current_user integration proof)
T001 ──► T004 [P] (password hashing — only needs deps installed)
T001 ──► T005 [P] (JWT helpers — only needs env config)
T005 ──► T008 (login needs create_access_token)
T005 ──► T010 (needs get_current_user)
```

`product-crud`'s tasks require T001, T002 (shared project/DB foundation) and T005, T010 (`get_current_user` contract proven) to be complete before its auth-protected routes can be wired.
