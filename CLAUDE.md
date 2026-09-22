# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project description

`ecommerce_mgmt` is an E-commerce Management backend service.

The first version focuses solely on CRUD for products:

- Create Product
- Get All Products
- Get Product by ID
- Update Product
- Delete Product

Additional e-commerce domains (orders, customers, inventory, etc.) are expected later — the architecture must stay easy to extend, but do not build for them yet.

## Stack

Language: Python 3
Framework: FastAPI
Database: PostgreSQL
Database access: SQLAlchemy ORM + `psycopg` (or `psycopg2-binary`) driver
Package manager: pip (`requirements.txt`)
Containerization: Docker
Orchestration: Docker Compose
API style: REST
Testing: Pytest
Configuration: environment variables / `.env` (never hardcode DB credentials or connection strings)

## Running the project

The entire stack (app + PostgreSQL + any other infra) must run via Docker Compose. PostgreSQL must never be required directly on the host.

- `docker compose up --build` — build and run the full stack
- `docker compose down` — stop and remove containers
- App and DB config come from `.env` / environment variables, not hardcoded values

If these commands don't exist yet, that's expected until the Implementation phase produces them — don't invent behavior that doesn't exist in the repo.

## Architecture

Strict layering, top to bottom:

```
API Routes  →  Service / Business Logic  →  Repository / Data Access  →  PostgreSQL
```

- **API routes** (FastAPI routers): request/response handling, request validation (Pydantic schemas), HTTP status codes/errors. No business logic here.
- **Service layer**: business rules and orchestration. This is the only layer allowed to make decisions about *what* should happen.
- **Repository layer**: SQLAlchemy models/queries only. No business logic here — just data access.
- Each layer only calls the layer directly below it. Routes never touch the DB/repository directly, and repositories never contain business logic.

Suggested module layout (adjust as needed, keep the separation):

```
app/
  api/          # FastAPI routers
  schemas/      # Pydantic request/response models
  services/     # business logic
  repositories/ # SQLAlchemy data access
  models/       # SQLAlchemy ORM models
  core/         # config, DB session/engine setup
tests/
```

## Project conventions

- No business logic in route handlers — the service layer owns it.
- API errors should use a consistent, predictable JSON error shape.
- All DB access goes through SQLAlchemy — no raw string-built SQL.
- Config (DB URL, credentials, ports) comes from environment variables / `.env`, never hardcoded.
- Keep the folder structure modular so new e-commerce domains (orders, inventory, customers, ...) can be added as sibling modules without restructuring what exists.

## Security notes

- All SQL via the ORM — no string interpolation into queries.
- Never commit real credentials; `.env` files with secrets stay out of version control (`.env.example` is fine).
- Validate all incoming request data via Pydantic schemas before it reaches the service layer.

## Performance notes

- Use async endpoints/DB calls where FastAPI + the chosen driver support it, especially for I/O-bound operations.
- Avoid N+1 query patterns in the repository layer.

## Org process — Spec-Driven Development

This project follows the mandatory phase workflow. **Do not write implementation code before the Specification and Implementation Plan have been reviewed and approved.**

```
Requirement → Specification → Implementation Plan → Tasks → Implementation → Testing
```

- Each stage must be completed and approved before the next one starts. Do not collapse phases to save time.
- Specs, plans, and tasks live under `specs/<feature-slug>/` (e.g. `specs/product-crud/`), using the templates and phase-owner agents defined in `.claude/agents/` and `.claude/skills/` (already scaffolded in this repo from the [ai-engineering-playbook](https://github.com/Tntra/ai-engineering-playbook)).
- The current feature in scope is product CRUD — start there before anything else.
- Follow the full workflow rationale in the playbook: https://github.com/Tntra/ai-engineering-playbook
