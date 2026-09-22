---
feature: user-auth
status: approved   # draft -> in-review -> approved
owner: pranay.gupta
created: 2026-09-22
# approved-by: <name>
# approved-date: <YYYY-MM-DD>
---

# Plan: User Authentication

> `spec.md` is `status: approved`. This feature is a dependency of `product-crud` (its plan already assumes HS256 + a shared `JWT_SECRET_KEY` + a `get_current_user` dependency — see ADR-3 below, which locks that contract).

## Architecture overview

Lives in the same FastAPI monolith as `product-crud`, as its own router and a shared security module other features consume:

```
Client
  │
  ▼
FastAPI app (uvicorn, in Docker container "api")
  └─ /api/v1/auth/*
        │
        ▼
  AuthService (business logic: duplicate check, password hashing/verification, token issuance)
        ▼
  UserRepository (SQLAlchemy async queries)
        ▼
  PostgreSQL (Docker container "db", table "users")

Shared module: app/core/security.py
  - create_access_token(user_id)      ← used by AuthService (this feature)
  - get_current_user (FastAPI dependency) ← consumed by product-crud's protected routes
```

`get_current_user` decodes the JWT, verifies signature + expiry, and returns the user id from the `sub` claim, or raises `401`. It has no dependency on `AuthService` or the `users` table at request time — decoding is stateless — so `product-crud` can depend on it without a runtime call back into this feature.

## Tech stack & rationale

- **FastAPI** + **Uvicorn** + **SQLAlchemy 2.0 (async)** + **asyncpg** + **Alembic** — same as `product-crud`, one shared stack across the monolith (see that feature's ADR-1/ADR-4; not repeated here).
- **passlib[bcrypt]** — password hashing (see ADR-1).
- **PyJWT** — token creation here, verification shared with `product-crud` (see ADR-3; consistent with that feature's ADR-3).
- **Pydantic v2** — request/response schemas.
- **Pytest** + **httpx.AsyncClient** + **pytest-asyncio** — same testing approach as `product-crud`.

## Data model

Table `users`:

| Column | Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | PK, autoincrement |
| `email` | `VARCHAR(255)` | NOT NULL, UNIQUE |
| `password_hash` | `VARCHAR(255)` | NOT NULL |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, server default `now()` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, server default `now()`, updated on write |

Indexes: unique index on `email`.

`id` uses the same integer-autoincrement strategy as `product-crud.products.id`, for the same reason (no stated need to hide row count/order, and `id` is never exposed via a public listing endpoint in this feature — there is no `GET /users` in scope). It becomes the JWT `sub` claim (as a string).

Single identifier field (`email`), not a separate `username` + `email` — see ADR-2.

## API contracts

Base path: `/api/v1/auth`. Errors use the same shape as `product-crud`: `{ "error": "<message>", "details"?: [...] }` (`details` only on `422`).

| Method & path | Auth | Request | Success | Errors |
|---|---|---|---|---|
| `POST /auth/register` | none | `{email, password}` | `201` `{id, email, created_at}` | `422` (invalid email / password too short), `409` (email already registered) |
| `POST /auth/login` | none | `{email, password}` | `200` `{access_token, token_type: "bearer", expires_in}` | `401` (generic "invalid credentials" — never distinguishes missing user from wrong password), `422` (malformed body) |

Password rule enforced at the schema level: minimum 8 characters, **maximum 72 bytes** (bcrypt's hard input limit — see ADR-1). Registration response never includes `password` or `password_hash`.

### Shared dependency contract (consumed by `product-crud` and future features)

`get_current_user(token: str = Depends(oauth2_scheme)) -> int`:
- Decodes the bearer JWT using `JWT_SECRET_KEY` / `JWT_ALGORITHM`.
- Raises `401` (via the standard error shape) if the token is missing, malformed, expired, or has an invalid signature.
- Returns the integer user id from the `sub` claim.
- Does **not** hit the database — a valid signature + unexpired `exp` is sufficient; no revocation list in v1 (consistent with "no refresh/logout" being out of scope).

## Integration points

- **PostgreSQL** (Docker Compose service `db`, table `users`) — no other tables.
- **`product-crud` feature** (internal, same app): consumes `get_current_user` and the `JWT_SECRET_KEY`/`JWT_ALGORITHM` env vars this feature defines. No network call between features — same process, same env.
- No other external services.

## Constitution check

- [x] No new infrastructure dependency introduced without an ADR. *(passlib/bcrypt — ADR-1; PyJWT — ADR-3, shared with `product-crud`)*
- [x] All API errors follow `{ error: string }` shape. *(extended with optional `details`, same convention as `product-crud`)*
- [x] No business logic in route handlers — service layer owns it. *(routes only parse/validate + call `AuthService`)*
- [x] All secrets managed via environment variables, never hardcoded. *(`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL`)*
- [x] Passwords are never logged, returned in a response, or stored anywhere but as a bcrypt hash.
- [x] Login failure responses are identical (status, body, and approximate timing — see Risks) whether the email doesn't exist or the password is wrong.

## Architecture Decision Records (ADRs)

### ADR-1: Password hashing

- **Problem:** Choose how passwords are hashed for storage/verification.
- **Options considered:** (a) `argon2-cffi` (Argon2id) — currently the strongest recommended KDF, but a native dependency with more build complexity. (b) `passlib[bcrypt]` — mature, the de facto standard in FastAPI tutorials/production code, simpler dependency footprint, well-understood cost-factor tuning.
- **Chosen solution:** `passlib[bcrypt]`.
- **Reasoning:** bcrypt is sufficiently strong for this system's threat model (a backend service, not a high-value target requiring Argon2's specific memory-hardness), and it's simpler to install/operate. Accepted tradeoff: bcrypt silently truncates/rejects inputs beyond 72 bytes, so password length is capped at 72 bytes in the request schema to make that limit explicit rather than a silent truncation bug.

### ADR-2: Login identifier field

- **Problem:** The spec says "username/email" without committing to one — decide the actual unique identifier field.
- **Options considered:** (a) Separate `username` and `email` fields, each unique — supports login by either, but doubles the uniqueness/validation surface for no stated requirement. (b) Single `email` field as the unique identifier.
- **Chosen solution:** Single `email` field.
- **Reasoning:** Nothing in the spec requires a distinct display username; email is already required for any real account system (contact/reset), so using it as the sole identifier avoids redundant state. Revisit only if a future requirement calls for a separate public-facing username.

### ADR-3: JWT signing/verification contract

- **Problem:** Lock the exact JWT mechanism so `product-crud` (and future features) can depend on it without re-deriving it independently.
- **Options considered:** (a) RS256 asymmetric keys — decouples signer/verifier, unneeded operational overhead for a single-process monolith. (b) HS256 with one shared secret, consistent with `product-crud/plan.md`'s ADR-3 (written before this plan, now confirmed here).
- **Chosen solution:** HS256. Claims: `sub` (user id, string), `iat`, `exp`. Env vars: `JWT_SECRET_KEY` (required, no default), `JWT_ALGORITHM` (default `HS256`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default `30`). Library: **PyJWT**.
- **Reasoning:** Matches the single-deployment reality and the assumption `product-crud` already planned against. This ADR is the authoritative source for the contract — if it ever changes, `product-crud/plan.md`'s ADR-3 and Risks section must be updated in the same change.

## Risks

- **Login timing side-channel.** If "user not found" short-circuits before any hashing work while "wrong password" always hashes, response times differ and could let an attacker enumerate valid emails. *Mitigation:* always run the bcrypt verification step (against a real hash if the user exists, against a dummy hash if not) before returning `401`, so both paths take comparable time. The dummy hash must be a **fixed, precomputed** bcrypt hash of a constant string, computed once at module import/startup — never recomputed per request — so its cost stays stable and comparable to a real lookup.
- **Cross-feature contract drift.** `product-crud` already depends on the exact claims/env-var names fixed in ADR-3. *Mitigation:* any future change to token shape must update both features' plans and notes in the same change — do not change one side silently.
- **No revocation/logout.** Tokens are valid until they naturally expire; a compromised token can't be invalidated early in v1. *Mitigation:* keep `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` short (default 30 min); explicitly out of scope per spec, but worth remembering when choosing the expiry value at implementation time.
