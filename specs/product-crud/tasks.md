---
feature: product-crud
status: approved
owner: pranay.gupta
created: 2026-09-22
execution-strategy: Dependency Order
---

# Tasks: Product CRUD

> `plan.md` is `status: approved`, constitution check fully ticked. Project scaffolding, the DB engine, and the `get_current_user` dependency are owned by `user-auth` (its T001, T002, T005, T010) — this feature's write-route tasks (T006) cannot start until those are done.

Task ID format: `T001`, `T002`, … `[P]` marks tasks that can run in parallel with other `[P]` tasks at the same dependency level. `Satisfies: FR-NNN` links each task to spec.md; foundational tasks that don't map to one specific FR are marked accordingly.

- [x] **T001:** Define the `Product` SQLAlchemy model and its Alembic migration for the `products` table (`id`, `name`, `description`, `price` with `CHECK (price > 0)`, `sku` unique, `stock_quantity` with `CHECK (stock_quantity >= 0)`, `is_active`, `created_at`, `updated_at`) plus indexes on `sku` (unique), `name`, `is_active`, per `plan.md`'s data model.
      Satisfies: Foundational (data model for all FRs)
      Verify: `alembic upgrade head` creates the table with exactly the columns/constraints/indexes in `plan.md`; a direct insert violating either CHECK constraint fails at the DB level.

- [x] **T002 [P]:** Implement `ProductRepository` (async: `create`, `get_by_id`, `get_by_sku`, `list` with pagination/filter/sort, `update`, `delete`), translating a unique-constraint `IntegrityError` on `sku` into a domain-level duplicate-sku exception.
      Satisfies: Foundational (data access for FR-001, FR-003, FR-005, FR-006, FR-007, FR-009, FR-010, FR-013)
      Verify: repository tests against the Dockerized test DB cover create+fetch round-trip, duplicate-sku insert raising the domain exception, `list` honoring `page`/`page_size`/`name`/`is_active`/`sort_by`/`sort_order` (including the documented defaults and the `page_size` max of 100), and delete removing the row.

- [x] **T003 [P]:** Define Pydantic schemas `ProductCreate`, `ProductUpdate` (all fields optional), `ProductRead`, and the list-query parameter model, encoding every validation rule from `plan.md` (required `name`, positive `price`, non-negative `stock_quantity`, `page_size` 1–100, `sort_by` in `{price, created_at}`, `sort_order` in `{asc, desc}`).
      Satisfies: FR-002, FR-006
      Verify: unit tests confirm invalid payloads (zero/negative `price`, negative `stock_quantity`, missing `name`, `page_size=101`, unknown `sort_by`) are all rejected with 422 and field-level `details`, before any service code runs.

- [x] **T004:** Implement `ProductService` (`create`, `list`, `get_by_id`, `update`, `delete`) — sku-uniqueness handling mapped to a 409 error, missing-product handling mapped to a 404 error, delegating all persistence to `ProductRepository`.
      Satisfies: FR-001, FR-003, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-013, FR-014
      Verify: service-level tests directly cover each FR's Given/When/Then from `spec.md` — duplicate sku on create and on update, update refreshing `updated_at`, get/update/delete on a missing id all raising the 404-mapped error, delete actually removing the row.

- [x] **T005:** Wire the public read routes — `GET /products` and `GET /products/{id}` — with no auth dependency, using the shared `{error, details?}` error-response shape.
      Satisfies: FR-005, FR-006, FR-007, FR-008
      Verify: `httpx.AsyncClient` integration tests against the full app + Dockerized Postgres confirm pagination metadata (`total`, `page`, `page_size`), filter (`name`, `is_active`) and sort (`price`, `created_at`, both directions) behavior, 200 on a found id, 404 on a missing id — all sent with no Authorization header.

- [x] **T006:** Wire the protected write routes — `POST /products`, `PATCH /products/{id}`, `DELETE /products/{id}` — each behind `Depends(get_current_user)` imported from `user-auth`'s shared security module. **Blocked on `user-auth` T005 and T010.**
      Satisfies: FR-001, FR-002, FR-003, FR-004, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015
      Verify: integration tests confirm 401 on all three routes with no/invalid/expired token, and correct 201/200/204/404/422/409 behavior when using a real JWT obtained from `user-auth`'s login endpoint.

- [x] **T007 [P]:** Add a Docker Compose smoke check (script or documented `README` steps) proving a clean environment — no host PostgreSQL — can run `docker compose up --build` and successfully call both `/api/v1/products` and `/api/v1/auth` routers.
      Satisfies: Foundational (project-level "runs entirely via Docker Compose" requirement)
      Verify: running the smoke check from a machine without PostgreSQL installed succeeds end-to-end.

## Dependencies between tasks

```
[external] user-auth T001 (project/Docker scaffold), T002 (DB engine + Alembic)
  └─► T001 (Product model + migration)
        └─► T002 [P] (ProductRepository)
        └─► T003 [P] (Pydantic schemas)
              T002 + T003 ──► T004 (ProductService)
                                 └─► T005 (public read routes)
                                 └─► T006 (protected write routes)
                                        ▲
                        [external] user-auth T005 (get_current_user), T010 (proven via integration test)
T005 + T006 ──► T007 (Docker Compose smoke check)
```

Execution note: T005 (public reads) can be implemented and shipped independently of `user-auth` entirely — only T006 (writes) is gated on that feature's auth work landing first.
