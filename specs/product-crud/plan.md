---
feature: product-crud
status: approved   # draft -> in-review -> approved
owner: pranay.gupta
created: 2026-09-22
# approved-by: <name>
# approved-date: <YYYY-MM-DD>
---

# Plan: Product CRUD

> `spec.md` is `status: approved`. This feature depends on the `user-auth` feature (spec.md still `status: draft`) for JWT issuance — see Risks.

## Architecture overview

Single FastAPI application (monolith), containerized, with strict layering:

```
Client
  │
  ▼
FastAPI app (uvicorn, in Docker container "api")
  ├─ /api/v1/auth/*      (user-auth feature — separate spec/plan)
  └─ /api/v1/products/*  (this feature)
        │  Depends(get_current_user)  ← required only on POST/PATCH/DELETE
        ▼
  ProductService (business logic: sku uniqueness, existence checks)
        ▼
  ProductRepository (SQLAlchemy async queries)
        ▼
  PostgreSQL (Docker container "db")
```

- `GET /products` and `GET /products/{id}` skip the auth dependency entirely (public reads).
- `POST /products`, `PATCH /products/{id}`, `DELETE /products/{id}` require `Depends(get_current_user)`, a shared dependency owned by the `user-auth` feature that decodes the JWT and returns the caller's user id (or raises 401).
- `db` runs only inside Docker Compose; the app never talks to a host-installed PostgreSQL.

## Tech stack & rationale

- **FastAPI** + **Uvicorn** — already the project standard.
- **SQLAlchemy 2.0 (async engine)** + **asyncpg** driver — async end-to-end so product endpoints don't block the event loop under concurrent load (see ADR-1).
- **Alembic** — schema migrations, versioned alongside SQLAlchemy models (see ADR-4).
- **Pydantic v2** — request/response schemas and validation (ships with FastAPI).
- **PyJWT** — JWT decode/verify on the product side (see ADR-3); actual signing lives in `user-auth`.
- **Pytest** + **httpx.AsyncClient** + **pytest-asyncio** — API-level tests against the FastAPI app; a disposable test schema/DB (via Docker Compose or testcontainers) for repository-level tests.

No deviation from the project's declared stack in CLAUDE.md; this section only makes specific library choices explicit.

## Data model

Table `products`:

| Column | Type | Constraints |
|---|---|---|
| `id` | `INTEGER` | PK, autoincrement |
| `name` | `VARCHAR(255)` | NOT NULL |
| `description` | `TEXT` | NULL |
| `price` | `NUMERIC(10,2)` | NOT NULL, CHECK (`price > 0`) |
| `sku` | `VARCHAR(64)` | NOT NULL, UNIQUE |
| `stock_quantity` | `INTEGER` | NOT NULL, DEFAULT 0, CHECK (`stock_quantity >= 0`) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `true` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, server default `now()` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, server default `now()`, updated on write |

Indexes: unique index on `sku` (constraint-backed); index on `name` (supports partial-match filter); index on `is_active`.

No relationships to other tables in this feature (no FK to a `users` table — product rows don't record which user created/modified them in v1, per spec's out-of-scope).

## API contracts

Base path: `/api/v1/products`. All error responses use the shape:
```json
{ "error": "<human-readable message>", "details": [ { "field": "price", "message": "must be greater than 0" } ] }
```
`details` is present only for 422 field-validation errors; omitted otherwise (see ADR-5).

| Method & path | Auth | Request | Success | Errors |
|---|---|---|---|---|
| `POST /products` | required | `ProductCreate` `{name, description?, price, sku, stock_quantity?, is_active?}` | `201` `ProductRead` | `401`, `422`, `409` (duplicate sku) |
| `GET /products` | none | query: `page` (default `1`, min `1`), `page_size` (default `20`, min `1`, max `100`), `name?`, `is_active?`, `sort_by?` (`price`\|`created_at`, default `created_at`), `sort_order?` (`asc`\|`desc`, default `desc`) | `200` `{items: ProductRead[], total, page, page_size}` | `422` (bad query params, e.g. `page_size` > 100) |
| `GET /products/{id}` | none | — | `200` `ProductRead` | `404` |
| `PATCH /products/{id}` | required | `ProductUpdate` (all fields optional) | `200` `ProductRead` | `401`, `404`, `422`, `409` |
| `DELETE /products/{id}` | required | — | `204` | `401`, `404` |

`ProductRead`: `{id, name, description, price, sku, stock_quantity, is_active, created_at, updated_at}`.

## Integration points

- **`user-auth` feature** (internal, same app): owns `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, and the `get_current_user` FastAPI dependency. Product-crud only *consumes* that dependency and the shared `JWT_SECRET_KEY` / algorithm — it does not sign or issue tokens. **This contract is not yet locked**: `user-auth/spec.md` is still `draft`. If its shape changes (e.g. claim names, algorithm), this plan's auth dependency usage must be revisited before implementation starts.
- **PostgreSQL** (Docker Compose service `db`) — only integration external to the app process.
- No other external services, queues, or third-party APIs.

## Constitution check

- [x] No new infrastructure dependency introduced without an ADR. *(Alembic, async driver — see ADR-1, ADR-4)*
- [x] All API errors follow `{ error: string }` shape. *(extended with optional `details`; see ADR-5)*
- [x] No business logic in route handlers — service layer owns it. *(routes only parse/validate + call `ProductService`)*
- [x] All secrets managed via environment variables, never hardcoded. *(`DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM` all env-sourced)*
- [x] `sku` uniqueness is enforced at the database level (unique constraint), not only in application logic, to close the race-condition gap between a pre-check and the insert.

## Architecture Decision Records (ADRs)

### ADR-1: Sync vs. async SQLAlchemy

- **Problem:** Choose how the app talks to PostgreSQL — sync SQLAlchemy (`psycopg2`) or async SQLAlchemy 2.0 (`asyncpg`).
- **Options considered:** (a) Sync SQLAlchemy + psycopg2 — simpler mental model, more tutorials/examples, but blocks the event loop per request under FastAPI. (b) Async SQLAlchemy 2.0 + asyncpg — non-blocking I/O, matches FastAPI's async nature and the project's stated performance guidance (async endpoints for I/O).
- **Chosen solution:** Async SQLAlchemy 2.0 + asyncpg.
- **Reasoning:** CLAUDE.md explicitly calls for async I/O where the driver supports it, and product listing/filtering is the endpoint most likely to see concurrent load. Accepted tradeoff: async session/engine setup and async test fixtures are more code than the sync equivalent.

### ADR-2: Primary key strategy

- **Problem:** Choose the type of `products.id` — integer autoincrement or UUID.
- **Options considered:** (a) UUID (via `pgcrypto`/`gen_random_uuid()`) — non-guessable, safe to expose, but adds a Postgres extension dependency and 16 bytes vs 4/8 per row. (b) Integer autoincrement — simplest, no extension, smaller index; leaks row count/creation order.
- **Chosen solution:** Integer autoincrement.
- **Reasoning:** `sku` is already the unique, externally-meaningful business key; `id` is only used as an internal/URL identifier. No stated requirement to hide product counts or ordering. Revisit if products are ever exposed in a context where ID enumeration is a real concern.

### ADR-3: JWT verification approach

- **Problem:** How `product-crud`'s protected routes verify a JWT issued by `user-auth`, given both live in the same deployable app.
- **Options considered:** (a) Asymmetric signing (RS256) with a public key distributed to verifiers — decouples signer/verifier, useful across separate services. (b) Symmetric signing (HS256) with one shared secret read from `JWT_SECRET_KEY` by both features.
- **Chosen solution:** HS256 with a shared `JWT_SECRET_KEY` env var, decoded via **PyJWT**.
- **Reasoning:** There is exactly one deployable process today (a monolith); asymmetric keys add operational overhead (key generation/rotation/distribution) with no current benefit. Accepted tradeoff: if `user-auth`'s issuance and `product-crud`'s verification are ever split into separate deployments, this must migrate to RS256 — noted as a risk below.

### ADR-4: Schema migrations

- **Problem:** How schema changes to `products` (and future tables) are applied to PostgreSQL.
- **Options considered:** (a) Hand-written SQL run manually/ad hoc — no dependency, but no history or rollback story. (b) Alembic — versioned, autogeneratable from SQLAlchemy models, standard in the ecosystem.
- **Chosen solution:** Alembic.
- **Reasoning:** The schema will grow as more e-commerce features land; versioned migrations with rollback are worth the one added dependency, and Alembic integrates directly with the SQLAlchemy models this plan already requires.

### ADR-5: Error response shape

- **Problem:** The org constitution mandates `{ error: string }` for all API errors, but FR-002/FR-003/FR-010 require returning field-level validation detail on `422`s.
- **Options considered:** (a) Strictly `{ "error": "<message>" }` only, flattening all field errors into one string — loses structure clients need to highlight specific fields. (b) Replace `error` with a nested object — breaks the constitution's literal shape. (c) Keep `error` as the required top-level string, add an optional `details` array only present on 422 responses.
- **Chosen solution:** (c).
- **Reasoning:** Satisfies the constitution's literal requirement (`error` is always a string) while still giving clients structured, field-level errors when they matter most (create/update validation). `details` is additive and never required by a consumer that only reads `error`.

## Risks

- **`user-auth` contract not yet approved.** This plan assumes: a `get_current_user` dependency exists, HS256 + `JWT_SECRET_KEY`/`JWT_ALGORITHM` env vars, and a decodable user-id claim. If `user-auth`'s approved spec/plan diverges from these assumptions, the auth-dependency integration in this feature must be revisited before Phase 3 tasks are written for the protected endpoints. *Mitigation:* do not start implementation tasks touching auth-dependent routes until `user-auth/spec.md` (and ideally its `plan.md`) is approved.
- **Race condition on `sku` uniqueness.** A pre-check-then-insert pattern has a TOCTOU gap under concurrent requests. *Mitigation:* rely on the DB unique constraint as the source of truth; catch the resulting `IntegrityError` in the repository/service layer and translate it to the 409 response, rather than trusting the pre-check alone.
- **Async stack adds complexity for a small, greenfield team.** *Mitigation:* keep the repository layer thin and consistently patterned so the async boilerplate is copy-paste predictable across future features.
- **HS256 shared-secret approach doesn't survive splitting into microservices later.** *Mitigation:* documented in ADR-3; revisit with RS256 if/when `user-auth` and product-crud are ever deployed separately.
- **Sequential integer IDs let a caller enumerate the entire catalog** by incrementing `id` against the public `GET /products/{id}`. *Accepted:* product catalog data isn't sensitive (no PII, comparable to any public storefront), and hiding it would contradict the spec's requirement that reads stay public/unauthenticated. Revisit only if inactive/unpublished products must not be discoverable by ID guessing — not a stated requirement today.
