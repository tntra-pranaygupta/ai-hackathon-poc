---
feature: product-crud
status: approved   # draft -> in-review -> approved
owner: pranay.gupta
created: 2026-09-22
# approved-by: <name>
# approved-date: <YYYY-MM-DD>
---

# Spec: Product CRUD

> Do not mix "what the system must do" with "how it will be built." Tech stack and implementation choices belong in `plan.md`.

## Context

`ecommerce_mgmt` needs a persistent catalog of products that other e-commerce capabilities (orders, inventory, etc.) can later build on. This feature establishes the first working slice of the system: create, read, update, and delete product records through a REST API backed by PostgreSQL, with write operations restricted to authenticated callers.

## Technical requirements

- The system must persist products in PostgreSQL with the fields: `id`, `name`, `description`, `price`, `sku`, `stock_quantity`, `is_active`, `created_at`, `updated_at`.
- The API must expose REST endpoints for: create product, list products, get product by ID, update product, delete product.
- `sku` must be unique across products.
- `price` must be a positive, non-zero decimal value; `stock_quantity` must be a non-negative integer.
- Delete must be a hard delete — the row is permanently removed.
- List Products must support pagination (`limit`/`offset` or `page`/`page_size`), filtering by `name` (partial match) and `is_active`, and sorting by `price` or `created_at` (ascending/descending).
- Create, Update, and Delete must require a valid JWT (per the `user-auth` feature); the identity of the authenticated caller is not otherwise used by product logic in v1. Get All / Get by ID are publicly readable and do not require authentication.
- All request payloads must be validated (required fields, types, constraints) before reaching business logic; invalid input must return 422 with field-level errors.
- All API errors must follow a consistent JSON error shape.
- All database access must go through the ORM (SQLAlchemy) — no raw string-built SQL.
- Database connection details must come from environment variables, never hardcoded.

## Acceptance criteria

- [ ] **FR-001:** Create a product
      Given a valid JWT and a valid product payload (unique `sku`, positive `price`, non-negative `stock_quantity`, required `name`)
      When a client POSTs to the create-product endpoint
      Then the system persists the product and returns 201 with the created product including its generated `id`, `created_at`, and `updated_at`

- [ ] **FR-002:** Reject invalid product input
      Given a valid JWT and a payload missing `name`, or with a zero/negative `price`, or a negative `stock_quantity`
      When a client POSTs to the create-product endpoint
      Then the system returns 422 with field-level validation errors and persists nothing

- [ ] **FR-003:** Reject duplicate SKU
      Given a product already exists with a given `sku`
      When a client POSTs a new product using that same `sku`
      Then the system returns 409 Conflict and persists nothing

- [ ] **FR-004:** Reject unauthenticated create
      Given no JWT, or an invalid/expired JWT, is provided
      When a client POSTs to the create-product endpoint
      Then the system returns 401 and persists nothing

- [ ] **FR-005:** List products with pagination
      Given at least one page of products exist
      When a client GETs the list-products endpoint with pagination parameters
      Then the system returns 200 with the requested page of products and pagination metadata (e.g. total count), without requiring authentication

- [ ] **FR-006:** Filter and sort the product list
      Given products with varying `name`, `is_active`, `price`, and `created_at` values
      When a client GETs the list-products endpoint with a `name` filter, an `is_active` filter, and/or a `sort` parameter for `price` or `created_at`
      Then the system returns only products matching the filters, ordered as requested

- [ ] **FR-007:** Get a product by ID
      Given a product with a given `id` exists
      When a client GETs the product-by-ID endpoint with that `id`
      Then the system returns 200 with that product's full data, without requiring authentication

- [ ] **FR-008:** Get a non-existent product by ID
      Given no product exists with a given `id`
      When a client GETs the product-by-ID endpoint with that `id`
      Then the system returns 404

- [ ] **FR-009:** Update a product
      Given a valid JWT and an existing product, and a valid update payload
      When a client PUTs/PATCHes the update-product endpoint for that product's `id`
      Then the system persists the changes and returns 200 with the updated product, with `updated_at` refreshed

- [ ] **FR-010:** Reject update with invalid data or duplicate SKU
      Given a valid JWT and an existing product
      When a client submits an update with an invalid field value (e.g. negative `price`) or a `sku` already used by a different product
      Then the system returns 422 (invalid data) or 409 (duplicate SKU) respectively, and persists no change

- [ ] **FR-011:** Update a non-existent product
      Given no product exists with a given `id`
      When a client submits an update for that `id`
      Then the system returns 404

- [ ] **FR-012:** Reject unauthenticated update
      Given no JWT, or an invalid/expired JWT, is provided
      When a client submits an update to an existing product
      Then the system returns 401 and persists no change

- [ ] **FR-013:** Delete a product
      Given a valid JWT and an existing product
      When a client DELETEs that product's `id`
      Then the system permanently removes the row and returns 204

- [ ] **FR-014:** Delete a non-existent product
      Given no product exists with a given `id`
      When a client DELETEs that `id`
      Then the system returns 404

- [ ] **FR-015:** Reject unauthenticated delete
      Given no JWT, or an invalid/expired JWT, is provided
      When a client DELETEs an existing product's `id`
      Then the system returns 401 and the product is not removed

## Out of scope

- User registration, login, and JWT issuance — owned by the `user-auth` feature; this feature only validates tokens it receives.
- Role-based permissions (e.g. admin vs regular user product management) — all authenticated users have equal write access in v1.
- Product categories, tags, images, or variants.
- Inventory movement tracking, orders, or any domain beyond the product record itself.
- Soft delete / audit trail of deleted products.
- Bulk create/update/delete endpoints.
- Search relevance ranking beyond simple partial-name filtering.

## Open questions

- None — resolved with stakeholder: hard delete, pagination + filter/sort on list, write endpoints require JWT auth (read endpoints public), auth itself is a separate `user-auth` feature this depends on.
