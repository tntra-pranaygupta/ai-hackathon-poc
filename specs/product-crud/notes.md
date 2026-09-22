---
feature: product-crud
---

# Notes: Product CRUD

Append-only log of decisions, deviations from the plan, and tradeoffs made during implementation. Do not edit or delete earlier entries — add new dated entries below.

## 2026-09-22

Sparring partner review of `plan.md` (Phase 2, pre-approval):

- **Attack:** (1) Planning against an unapproved `user-auth` spec risks rework if its JWT/claim shape changes. (2) HS256 shared-secret is a leaky coupling between two "features" — a real rewrite if they're ever split into separate services. (3) Async SQLAlchemy/asyncpg is added complexity (session lifecycle, ORM+async quirks) not proven necessary for a first-version CRUD service — possible YAGNI. (4) Integer PK + unauthenticated `GET /products/{id}` lets a caller enumerate the entire catalog by incrementing IDs. (5) Pagination defaults/bounds (`page_size` cap, sort defaults) were left unspecified in the original contract — a real gap, not just a risk.
- **Steelman:** (1) The plan already gates implementation tasks on `user-auth` approval, so no wasted build work — only planning risk, correctly documented. (2) HS256/shared-secret matches the actual deployment (one monolith, one Docker Compose stack); RS256 now would be premature abstraction for a hypothetical future split. (3) Async matches CLAUDE.md's explicit performance guidance and avoids a later async migration once more I/O-heavy features (orders, inventory) land. (4) ID enumeration only exposes catalog data, which is meant to be public read data anyway — not PII, comparable to any public storefront.
- **Verdict:** Items (1)–(3) and (5)-as-a-gap are accepted as documented tradeoffs/risks except (5), which was fixed directly in `plan.md` rather than left as a risk: `page`, `page_size` (default 20, max 100), `sort_by`/`sort_order` defaults are now pinned in the API contract table. (4) is accepted and called out explicitly as a risk in `plan.md` — no action needed unless a future requirement demands unpublished/inactive products be non-discoverable by ID. Biggest remaining risk going into Phase 3: the `user-auth` dependency contract (ADR-3 assumptions: `get_current_user`, `JWT_SECRET_KEY`/`JWT_ALGORITHM`, decodable user-id claim) is not yet locked — do not start tasks for auth-protected product routes until `user-auth/spec.md` is approved.

## 2026-09-22 (implementation)

Deviations/clarifications made during Phase 4 implementation; the approved data model, API contracts, and ADR-1 through ADR-5 in plan.md are all implemented as specified:

- `user-auth`'s T001/T002/T005/T010 were completed first (per both features' tasks.md dependency trees) before starting this feature's T006 (protected write routes). The `get_current_user` contract landed exactly as ADR-3 assumed (HS256, shared `JWT_SECRET_KEY`), so no rework was needed on this feature's auth-dependency usage.
- `name` filter (FR-006) now escapes SQL LIKE wildcard characters (`%`, `_`, `\`) before building the ILIKE pattern in `ProductRepository.list` (`app/repositories/product_repository.py`). Not called out in plan.md, but without escaping, a search term containing a literal `%` or `_` (e.g. a product named "100% Cotton") would silently behave as a wildcard instead of a literal substring match -- a correctness bug in the partial-match filter, not a SQL-injection risk (the value was always a bound parameter). Fixed and covered by a regression test.
- Transaction commits moved from `ProductRepository` to `ProductService`. Repository methods (create/update/delete) now flush() only; the service calls session.commit()/session.refresh() on success and session.rollback() on IntegrityError. Matches the layering principle in plan.md's constitution check ("no business logic in route handlers -- service layer owns it") and keeps the transaction boundary at the layer that will need to span multiple repositories as more e-commerce domains are added (per CLAUDE.md's stated extensibility goal).
- Docker Compose smoke check (T007) implemented as `scripts/smoke_check.sh`, a bash script (not a README-documented manual procedure) that runs `docker compose up --build`, waits for /health, and exercises register -> login -> unauthenticated-create-rejected -> authenticated-create -> public-list, then tears the stack down. Chose a script over README steps since it's directly re-runnable and asserts on status codes rather than relying on manual inspection.
