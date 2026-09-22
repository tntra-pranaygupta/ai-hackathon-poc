# eCommerce Management

E-commerce Management backend service. First version: user authentication (JWT) and full CRUD for products, built with FastAPI and PostgreSQL, running entirely through Docker Compose.

## Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 (async via SQLAlchemy 2.0 + asyncpg)
- **Migrations:** Alembic
- **Auth:** JWT (HS256, via PyJWT), passwords hashed with bcrypt (passlib)
- **Testing:** Pytest + httpx
- **Containerization:** Docker / Docker Compose

## Architecture

```
API routes  →  Service / business logic  →  Repository / data access  →  PostgreSQL
```

```
app/
  api/v1/        # FastAPI routers (auth, products)
  schemas/       # Pydantic request/response models
  services/      # business logic (AuthService, ProductService)
  repositories/  # SQLAlchemy data access (UserRepository, ProductRepository)
  models/        # SQLAlchemy ORM models
  core/          # config, DB engine/session, security (JWT, password hashing)
alembic/         # schema migrations
tests/           # pytest suite
scripts/         # smoke_check.sh — end-to-end Docker Compose check
specs/           # spec-driven development artifacts (spec/plan/tasks/notes per feature)
```

Full stack/architecture rules live in [CLAUDE.md](CLAUDE.md); feature specs, plans, and task lists live under [specs/](specs/).

## Running the project

Everything — the API and PostgreSQL — runs in Docker Compose. **No PostgreSQL install is required on the host.**

```bash
cp .env.example .env   # adjust values if needed, especially JWT_SECRET_KEY
docker compose up --build
```

This builds the `api` image, starts `db` (PostgreSQL, no host port exposed) and `api` (port `8000`), waits for the database to be healthy, runs `alembic upgrade head`, then starts the app.

- API base URL: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Health check: `GET /health`

Stop and remove containers:

```bash
docker compose down
```

Stop and also wipe the database volume:

```bash
docker compose down -v
```

### End-to-end smoke check

```bash
./scripts/smoke_check.sh
```

Brings up the full stack from scratch, exercises register → login → unauthenticated create (expects 401) → authenticated create → public list, then tears the stack down. Requires `docker`, `curl`, and `python3` on the host.

### Running tests

```bash
docker compose exec api pytest -q
```

(Run `docker compose up -d` first if the stack isn't already running.)

## Configuration

All configuration is via environment variables — see [.env.example](.env.example):

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials, used by both `db` and `api` |
| `DATABASE_URL` | SQLAlchemy async connection string |
| `JWT_SECRET_KEY` | Secret used to sign/verify JWTs — **must** be set to a long random value outside local dev |
| `JWT_ALGORITHM` | JWT signing algorithm (default `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime in minutes (default `30`) |

## API overview

### Auth (`/api/v1/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | none | Register a new user (`email`, `password`) |
| POST | `/auth/login` | none | Log in, returns a JWT access token |

### Products (`/api/v1/products`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/products` | none | List products — pagination (`page`, `page_size`), filter (`name`, `is_active`), sort (`sort_by`, `sort_order`) |
| GET | `/products/{id}` | none | Get a product by ID |
| POST | `/products` | required | Create a product |
| PATCH | `/products/{id}` | required | Update a product |
| DELETE | `/products/{id}` | required | Delete a product |

Protected endpoints require `Authorization: Bearer <access_token>` from `/auth/login`. All API errors follow `{ "error": "<message>", "details"?: [...] }`, with `details` present only on `422` validation errors.

Full request/response contracts, data model, and design rationale (ADRs) are documented in [specs/user-auth/plan.md](specs/user-auth/plan.md) and [specs/product-crud/plan.md](specs/product-crud/plan.md).

## Development process

This project follows spec-driven development: **Requirement → Specification → Implementation Plan → Tasks → Implementation → Testing**, with each stage approved before the next starts. See [CLAUDE.md](CLAUDE.md) and `specs/<feature-slug>/` for the live artifacts of each feature.
